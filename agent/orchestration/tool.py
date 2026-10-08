"""Model-facing request parsing and existing background completion delivery."""

from dataclasses import asdict
import json

from .config import load_config
from .controller import OrchestrationController
from .executor import LifecycleExecutor
from .types import LEVELS, TaskRequest


def parse_request(raw):
    from tools.delegate_tool_tasks import _normalize_task_images
    from tools.delegation_output_schema import coerce_output_schema
    allowed = {"goal", "context", "route", "level", "output_schema", "images", "attachments", "specialization", "specialization_reason"}
    if not isinstance(raw, dict) or raw.keys() - allowed:
        raise ValueError("Task accepts goal, context, route, level, output_schema, images, attachments and specialization/reason")
    goal, context = raw.get("goal"), raw.get("context") or ""
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 16000:
        raise ValueError("goal must contain 1–16000 characters")
    if not isinstance(context, str) or len(context) > 8000:
        raise ValueError("context must contain at most 8000 characters")
    level = raw.get("level", "auto")
    if level not in (*LEVELS, "auto"):
        raise ValueError("level must be auto, fast, balanced or deep")
    route = raw.get("route")
    if route is not None and not isinstance(route, str):
        raise ValueError("route must be a configured route ID")
    schema, error = coerce_output_schema(raw.get("output_schema"))
    if error:
        raise ValueError(error)
    if schema and len(json.dumps(schema)) > 4000:
        raise ValueError("output_schema must fit within 4000 characters")
    images, error = _normalize_task_images(raw, 0)
    if error:
        raise ValueError(error)
    from .specializations import selection
    from .attachments import validate_attachments
    return TaskRequest(goal, context, route, level, schema, tuple(images or ()),
                       attachments=validate_attachments(raw.get("attachments")),
                       **selection(raw.get("specialization"), raw.get("specialization_reason", "")))


def run_tasks(args, parent):
    config = load_config()
    if not config.active:
        return {"status": "blocked", "reason": "orchestration_disabled"}
    if parent is None:
        return {"status": "blocked", "reason": "No active parent session"}
    if args.get("plan") is True:
        if args.get("background") or "tasks" in args:
            raise ValueError("Planning accepts one foreground goal")
        from .planner import run_plan
        request = parse_request({k: v for k, v in args.items() if k not in {"plan", "background"}})
        output = run_plan(request, parent, config)
        parent._orchestration_turn_result = output
        return output
    if "plan" in args and type(args["plan"]) is not bool:
        raise ValueError("plan must be boolean")
    background = args.get("background", False)
    if type(background) is not bool:
        raise ValueError("background must be boolean")
    raw = {k: v for k, v in args.items() if k not in {"background", "plan"}}
    if "tasks" in raw:
        if set(raw) != {"tasks"} or not isinstance(raw["tasks"], list) or not raw["tasks"]:
            raise ValueError("Supply either a single goal or a non-empty tasks array")
        items = raw["tasks"]
    else:
        items = [raw]
    from tools.delegate_tool import _get_max_concurrent_children
    cap = min(config.settings["budget"]["max_parallel_tasks"], _get_max_concurrent_children())
    if len(items) > cap:
        raise ValueError(f"At most {cap} tasks per call; split this batch")
    requests = [parse_request(item) for item in items]
    # Reject the whole malformed batch before launching any work.
    from .router import route_task
    for request in requests:
        route_task(request, config)
    from .specializations import task_config
    configs = [task_config(config, request) for request in requests]
    controllers = [OrchestrationController(scoped, LifecycleExecutor(parent, scoped)) for scoped in configs]

    def runner():
        results = []
        for index, (controller, request) in enumerate(zip(controllers, requests)):
            result = asdict(controller.run(request))
            try:
                result["artifacts"] = controller.executor.finish(result["status"] == "completed")
            except ValueError as exc:
                result.update(status="blocked", reason=str(exc))
                result["artifacts"] = controller.executor.finish(False)
            result["task_index"] = index
            results.append(result)
        return {"results": results}

    if not background or getattr(parent, "_delegate_depth", 0) > 0:
        return runner()
    from tools.async_delegation import dispatch_async_delegation_batch
    from tools.delegate_tool_dispatch import _capture_origin, _resolve_async_session_key
    wake, ui, *_ = _capture_origin()
    session_key, ui = _resolve_async_session_key(parent, ui)

    def interrupt():
        for controller in controllers:
            controller.budget.cancelled.set()

    return dispatch_async_delegation_batch(
        goals=[request.goal for request in requests], context=None, toolsets=None, role="leaf", model=None,
        session_key=session_key, parent_session_id=getattr(parent, "session_id", None), runner=runner,
        origin_ui_session_id=ui, origin_session_id=wake, interrupt_fn=interrupt,
        max_async_children=_get_max_concurrent_children(),
    )


def handle(args, **kwargs):
    from agent.subagent_lifecycle import get_active_subagent_parent
    parent = get_active_subagent_parent()
    try:
        return json.dumps(run_tasks(args, parent), ensure_ascii=False)
    except (ValueError, TypeError) as exc:
        result = {"status": "blocked", "reason": str(exc)}
        if parent is not None and args.get("plan") is True:
            parent._orchestration_turn_result = result
        return json.dumps(result, ensure_ascii=False)
