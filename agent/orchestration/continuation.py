"""Explicit user consent extends call allowances without restarting the worker."""

import json


def extend_calls(policy, child):
    from .progress import publish
    from tools.clarify_tool import clarify_tool

    budget = policy.budget
    local_exhausted = policy.calls >= policy.call_limit
    total_exhausted = budget.state.model_calls >= budget.limits["max_model_calls"]
    if not local_exhausted and not total_exhausted:
        return True
    if getattr(child, "_interrupt_requested", False):
        return False
    block = budget.limits.get("max_calls_per_attempt", 12)
    callback = getattr(policy, "continuation_callback", None)
    publish("budget_waiting", detail=f"{budget.state.model_calls} model calls; +{block} requested")
    started = budget.clock()
    budget.awaiting_input.set()
    try:
        reply = json.loads(clarify_tool([{
            "question": f"Лимит обращений к модели достигнут ({budget.state.model_calls}). "
                        f"Продолжить текущую работу ещё на {block} обращений? "
                        "Контекст и выполненные действия сохранятся; дополнительные обращения могут оплачиваться.",
            "choices": ["Продолжить", "Остановить"],
        }], callback=callback))
    finally:
        budget.deadline += budget.clock() - started
        budget.awaiting_input.clear()
    answers = reply.get("responses", [])
    approved = (reply.get("outcome") == "submitted" and len(answers) == 1
                and answers[0].get("user_response") == "Продолжить"
                and not getattr(child, "_interrupt_requested", False) and not budget.cancelled.is_set())
    if approved:
        # One consent grants one block, shared by main and auxiliary requests.
        policy.call_limit = max(policy.call_limit, policy.calls + block)
        budget.limits["max_model_calls"] = max(budget.limits["max_model_calls"], budget.state.model_calls + block)
    publish("budget_extended" if approved else "budget_declined", detail=str(block) if approved else "")
    return approved
