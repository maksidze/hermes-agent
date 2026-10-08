"""Opt-in turn entry, using the ordinary tool dispatch and persistence boundary."""

import json
import re
from uuid import uuid4

from .config import load_config
from .specializations import explicit_category

def run_automatic(agent, state):
    if (getattr(agent, "_delegate_depth", 0) or getattr(agent, "_orchestration_execution", None)
            or getattr(agent, "_turn_origin", None) == "background_review"
            or getattr(agent, "_interrupt_requested", False)):
        return
    config = load_config()
    from .attachments import turn_input
    goal, images, attachments = turn_input(state)
    category = explicit_category(goal, config)
    if not config.active:
        return
    from agent.transports.types import NormalizedResponse, ToolCall
    from agent.message_metadata import append_message
    from agent.message_content import flatten_message_text

    # Only public, recent text is forwarded. Historic messages and the cached
    # system prefix are untouched; the tool transcript belongs to this new turn.
    context = json.dumps([
        {"role": m["role"], "content": flatten_message_text(m.get("content", ""))[-1500:]}
        for m in state.messages[:-1] if m.get("role") in {"user", "assistant"} and m.get("content")
    ][-4:], ensure_ascii=False)
    args = {"goal": goal, "context": context, "plan": True, "images": images, "attachments": attachments}
    if category:
        args.update(specialization=category, specialization_reason="Explicit user category: @" + category)
    arguments = json.dumps(args, ensure_ascii=False)
    call = ToolCall(id="call_" + uuid4().hex[:24], name="orchestrate_task", arguments=arguments)
    message = {"role": "assistant", "content": None, "tool_calls": [
        {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": arguments}}]}
    append_message(state.messages, message)
    if agent._flush_messages_to_session_db(state.messages, state.conversation_history) is False:
        raise RuntimeError("Cannot persist automatic orchestration before execution")
    agent._emit_interim_assistant_message(message)
    if "orchestrate_task" not in agent.valid_tool_names:
        # Own the turn without changing the cached tool surface. Still retain
        # its public tool transcript and the same live progress card.
        return run_owned_plan(agent, state, args, config, call.id)
    agent._orchestration_turn_result = None
    agent._execute_tool_calls(NormalizedResponse(content=None, tool_calls=[call], finish_reason="tool_calls"),
                              state.messages, state.effective_task_id, 0)
    output = agent._orchestration_turn_result
    if output is None:
        failure = next((m.get("content") for m in reversed(state.messages)
                        if m.get("tool_call_id") == call.id), "Orchestration dispatch did not return a result")
        output = {"status": "blocked", "reason": str(failure)}
    return finish_automatic(agent, state, output)


def run_owned_plan(agent, state, args, config, call_id):
    from .planner import run_plan
    from .tool import parse_request
    from agent.message_metadata import append_message
    from agent.tool_executor import _safe_callback
    from tools.approval_context import _approval_tool_call_id
    _safe_callback(agent.tool_start_callback, "Orchestration start", call_id, "orchestrate_task", args)
    token = _approval_tool_call_id.set(call_id)
    try:
        output = run_plan(parse_request({k: v for k, v in args.items() if k != "plan"}), agent, config)
    except (ValueError, TypeError) as exc:
        output = {"status": "blocked", "reason": str(exc)}
    finally:
        _approval_tool_call_id.reset(token)
    content = json.dumps(output, ensure_ascii=False)
    message = {"role": "tool", "tool_call_id": call_id, "name": "orchestrate_task", "content": content}
    from .progress import display_result
    message["display_metadata"] = {"tool_result_metadata": {"orchestration": display_result(content)}}
    append_message(state.messages, message)
    if agent._flush_messages_to_session_db(state.messages, state.conversation_history) is False:
        raise RuntimeError("Cannot persist automatic orchestration result")
    _safe_callback(agent.tool_complete_callback, "Orchestration complete", call_id, "orchestrate_task", args, content)
    return finish_automatic(agent, state, output)


def outcome_text(output, russian):
    success = output.get("status") == "completed"
    labels = ("Оркестрация завершена.", "Оркестрация остановлена.") if russian else (
        "Orchestration completed.", "Orchestration stopped.")
    lines = [labels[0 if success else 1]]
    if output.get("reason"):
        reasons = {"max_model_calls": "Исчерпан лимит обращений к моделям.",
                   "model_calls_continuation_not_approved": "Лимит обращений достигнут. Продолжение не подтверждено; работа сохранена.",
                   "timeout_seconds": "Истекло время, выделенное на оркестрацию.",
                   "max_attempts": "Исчерпан лимит попыток.", "cancelled": "Выполнение отменено."}
        lines.append(reasons.get(output["reason"], str(output["reason"])) if russian else str(output["reason"]))
    budget = output.get("budget") or {}
    if budget:
        lines.append(("Обращений к моделям: " if russian else "Model calls: ") + str(budget.get("model_calls", 0)))
    for result in output.get("results", []):
        lines.append(f"{result.get('plan_task', result['task_id'])}: {result['status']}")
        if result.get("specialization"):
            lines.append(f"@{result['specialization']}: {result.get('specialization_reason', '')}")
        for attempt in result.get("attempts", []):
            proposal = attempt.get("evidence", {}).get("specialist_request")
            if proposal:
                lines.append(("Запрос передачи: " if russian else "Transfer requested: ")
                             + f"@{proposal['category']} — {proposal['reason']}")
    if success and output.get("results"):
        lines.append(output["results"][-1]["summary"][-4000:])
    artifacts = output.get("artifacts") or {}
    if artifacts.get("workspace"):
        lines.append(("Рабочая копия: " if russian else "Worktree: ") + artifacts["workspace"])
    if artifacts.get("journal"):
        lines.append(("Журнал попыток: " if russian else "Attempt journal: ") + artifacts["journal"])
    if output.get("progress_journal"):
        lines.append(("Журнал процесса: " if russian else "Activity journal: ") + output["progress_journal"])
    if artifacts.get("applied"):
        lines.append("Проверенные изменения применены к проекту." if russian else "Verified changes applied to the project.")
    elif artifacts:
        lines.append("Файловые изменения к исходному проекту не применены. Состояние внешних приложений не откатывалось."
                     if russian else "File changes were not applied to the source project. External application state was not rolled back.")
    return "\n\n".join(lines)


def finish_automatic(agent, state, output):
    from agent.turn_finalizer import finalize_turn
    # No unrestricted main-model turn after a bounded run: a textual request
    # not to retry is insufficient, especially after a refusal or budget stop.
    success = output.get("status") == "completed"
    return finalize_turn(
        agent, final_response=outcome_text(output, bool(re.search("[А-Яа-я]", str(state.original_user_message)))),
        api_call_count=0, interrupted=getattr(agent, "_interrupt_requested", False), failed=not success,
        messages=state.messages, conversation_history=state.conversation_history,
        effective_task_id=state.effective_task_id, turn_id=state.turn_id, user_message=state.user_message,
        original_user_message=state.original_user_message, _should_review_memory=state._should_review_memory,
        _turn_exit_reason="completed" if success else "orchestration_blocked",
    )
