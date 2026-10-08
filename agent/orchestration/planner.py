"""A bounded architect plan followed by dependency-ordered verified execution."""

from dataclasses import asdict
import json

from .budget import BudgetExceeded
from .controller import OrchestrationController
from .events import emit
from .executor import LifecycleExecutor, execution_slot
from .graph_config import planning_catalog
from .router import route_task
from .specializations import catalog_instructions, normalize_plan_categories, reroute_request, selection, task_config
from .types import TaskRequest
from .verifier import validate_schema
from .media_evidence import REFERENCE_CONTRACT

PLAN_SCHEMA = {
    "type": "object", "required": ["architecture", "tasks"], "additionalProperties": False,
    "properties": {
        "execution": {"enum": ["single", "staged"]},
        "decomposition_reason": {"type": "string", "maxLength": 1000},
        "architecture": {"type": "string", "maxLength": 5000},
        "tasks": {"type": "array", "minItems": 1, "maxItems": 12, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "goal", "acceptance"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-zA-Z][a-zA-Z0-9_-]{0,31}$"},
                "goal": {"type": "string", "minLength": 1, "maxLength": 4000},
                "level": {"enum": ["auto", "fast", "balanced", "deep"]},
                "start_node": {"type": "string", "pattern": "^[a-zA-Z][a-zA-Z0-9_-]{0,63}$"},
                "start_reason": {"type": "string", "minLength": 1, "maxLength": 1000},
                "depends_on": {"type": "array", "items": {"type": "string"}, "uniqueItems": True,
                               "default": [], "description": "Earlier task IDs; omission means no dependencies."},
                "acceptance": {"type": "string", "minLength": 1, "maxLength": 1500},
                "visual_check": {"type": "boolean", "description": "Require a fresh candidate image for visual deliverables."},
                "artifacts": {"type": "array", "items": {"type": "string", "minLength": 1}, "maxItems": 12,
                              "description": "Expected output files, relative to the isolated workspace."},
                "specialization": {"type": "string", "minLength": 1, "maxLength": 64},
                "specialization_reason": {"type": "string", "minLength": 1, "maxLength": 500},
            },
        }},
    },
}


def parse_plan(summary, max_tasks):
    from tools.delegation_output_schema import extract_json_candidate
    valid, errors = validate_schema(summary, PLAN_SCHEMA)
    if not valid:
        raise ValueError("Invalid architecture plan: " + "; ".join(errors))
    plan = json.loads(extract_json_candidate(summary))
    tasks = plan["tasks"]
    if len(tasks) > max_tasks:
        raise ValueError("Architecture plan exceeds automation.max_tasks")
    seen = set()
    for task in tasks:
        task.setdefault("depends_on", [])
        task.setdefault("level", "auto")
        if task["id"] in seen or not set(task["depends_on"]).issubset(seen):
            raise ValueError("Plan must use unique IDs and dependencies on earlier tasks only")
        seen.add(task["id"])
    return plan


def plan_selection(task, request, config):
    chosen = task.get("specialization", request.specialization)
    reason = task.get("specialization_reason", request.specialization_reason if chosen == request.specialization else "")
    fields = selection(chosen, reason)
    if chosen and chosen != request.specialization:
        reroute_request(request, {"category": chosen, "reason": reason}, config)
    if task.get("start_node") and config.settings["routing"]["adaptive_entry"] and not config.settings["routing"]["preferred_profile"]:
        if not task.get("start_reason", "").strip():
            raise ValueError("Architect start_node requires start_reason")
        fields.update(start_node=task["start_node"], start_reason=task["start_reason"])
    if not config.settings["routing"]["adaptive_entry"] and not config.settings["routing"]["preferred_profile"]:
        from .graph_config import graph_for_route
        route = route_task(TaskRequest(goal=task["goal"], route=request.route, level="fast", **fields), config)
        fields.update(start_node=graph_for_route(config, route.name)["entry"], start_reason="configured_entry")
    return fields


def compact_plan(plan, request):
    """One deliverable is one worker session; staged work must be justified."""
    if plan.get("execution") == "staged":
        if not plan.get("decomposition_reason", "").strip():
            raise ValueError("Staged execution requires a reason for separate deliverables")
        return plan
    tasks = plan["tasks"]
    if len(tasks) == 1:
        return plan
    categories = {t.get("specialization", request.specialization) for t in tasks}
    if len(categories) > 1:
        return {**plan, "execution": "staged", "decomposition_reason": "Different specialist routes"}
    first = tasks[0]
    return {**plan, "execution": "single", "tasks": [{
        **{k: v for k, v in first.items() if k in {"level", "specialization", "specialization_reason", "start_node", "start_reason"}},
        "id": "deliver", "goal": request.goal, "depends_on": [],
        "visual_check": any(t.get("visual_check", False) for t in tasks),
        "artifacts": list(dict.fromkeys(path for task in tasks for path in task.get("artifacts", ()))),
        "acceptance": "Deliver the original user request end to end. Check the main user flow and fix functional "
                      "errors. Use checks proportionate to the change; optional features are not requirements.",
    }]}


def execute_plan(request, controller, output=None):
    config, executor, budget = controller.config, controller.executor, controller.budget
    policy = config.settings["automation"]
    route = config.settings["routes"].get(request.route or config.settings["routing"]["default_route"], [])
    fallback = next((p for p in reversed(route) if config.profiles[p].enabled), "")
    profile = config.profiles.get(policy["planner_profile"] or fallback)
    if not profile or not profile.enabled or not controller.available(profile, request, reviewer=True):
        raise ValueError("Architect profile is unavailable; select an enabled planner profile")
    emit(config.settings, "planning_started", task_id=request.task_id, profile=profile.id)
    plan_request = TaskRequest(
        goal="Design an architecture and an executable dependency-ordered plan for the user's goal. "
             "Do not execute it. Default to execution=single with ONE end-to-end task, including implementation "
             "and a proportionate check. A small website, utility, text or bug fix is one deliverable: do not "
             "split HTML, CSS, JS, polish and testing into separate agent sessions. Use execution=staged only "
             "for independently substantial deliverables or different specialists and explain why in "
             "decomposition_reason. Do not invent extra features or elaborate acceptance rituals; for a coin "
             "flip, check that the button produces either side, not hundreds of statistical trials. "
             "Omit level for configured graph workflows. Include concrete acceptance checks in every task "
             "and a final validation appropriate to the goal (tests for code, requirements review for prose). "
             "Each task receives the existing workspace and previous results. "
             "Set visual_check=true for creating/modifying visual artifacts from references. Include comparison "
             "with the actual reference in acceptance, not just generic object names or successful saving. "
             "List expected saved deliverable files in artifacts using workspace-relative paths. External "
             "applications may have a different cwd: workers must use absolute workspace output paths. "
             "Use project-relative file paths, never absolute paths to the original checkout. "
             f"Use at most {policy['max_tasks']} tasks. Return only the plan JSON." + catalog_instructions(config)
             + planning_catalog(config) + "\n" + REFERENCE_CONTRACT,
        output_schema=PLAN_SCHEMA, images=request.images, attachments=request.attachments,
        specialization=request.specialization, specialization_reason=request.specialization_reason,
    )
    budget.attempt()
    planned = executor.execute(plan_request, profile, json.dumps({"goal": request.goal, "context": request.context,
                               "route": request.route or config.settings["routing"]["default_route"]}),
                               budget, reviewer="planner")
    if planned.status != "completed":
        if planned.evidence.get("failure_reason") in {"attempt_model_calls", "max_model_calls"}:
            raise ValueError("model_calls_continuation_not_approved")
        raise ValueError("Architect did not complete the plan")
    plan = normalize_plan_categories(parse_plan(planned.summary, policy["max_tasks"]), request, config)
    plan = compact_plan(plan, request)
    if len(plan["tasks"]) > budget.remaining()["attempts"]:
        raise ValueError("Plan exceeds remaining attempts; increase budget.max_attempts")
    # Validate the entire plan before any writer starts, including category availability/privacy.
    selections = [plan_selection(task, request, config) for task in plan["tasks"]]
    for task, fields in zip(plan["tasks"], selections):
        route_task(TaskRequest(goal=task["goal"], route=request.route, level=task["level"],
                               images=request.images, attachments=request.attachments, **fields), config)
    emit(config.settings, "plan_created", task_id=request.task_id, profile=profile.id, tasks=len(plan["tasks"]))
    from .progress import publish
    publish("plan", detail=plan["architecture"] + "\n\n" + "\n".join(
        f"{i + 1}. {task['id']}: {task['goal']}" for i, task in enumerate(plan["tasks"])))
    if config.settings["workspace"]["enabled"]:
        executor.record_plan(plan)
    results = []
    if output is not None:
        output.update(plan=plan, results=results)
    for task, fields in zip(plan["tasks"], selections):
        budget.check()
        publish("plan_task_started", detail=task["goal"], plan_task=task["id"])
        context = json.dumps({"original_goal": request.goal[:4000], "constraints": request.context[:1500],
                              "architecture": plan["architecture"],
                              "completed": [{"id": r["plan_task"], "summary": r["summary"][-700:]} for r in results]},
                             ensure_ascii=False)
        subtask = TaskRequest(goal=task["goal"] + "\nAcceptance checks: " + task["acceptance"], context=context,
                              route=request.route or config.settings["routing"]["default_route"], level=task["level"],
                              images=request.images, attachments=request.attachments,
                              visual_check=task.get("visual_check", False), artifact_paths=tuple(task.get("artifacts", ())), **fields)
        result = controller.run(subtask)
        results.append({**asdict(result), "plan_task": task["id"]})
        if result.status != "completed":
            return {"status": result.status, "reason": result.reason, "plan": plan, "results": results}
    return {"status": "completed", "plan": plan, "results": results}


def run_plan(request, parent, config):
    from .progress import RunProgress
    with RunProgress(parent) as progress:
        output = _run_plan(request, parent, config)
        progress.append("run_completed", status=output["status"], detail=output.get("reason", ""))
        return progress.attach(output)


def _run_plan(request, parent, config):
    config = task_config(config, request)
    executor = LifecycleExecutor(parent, config)
    controller = OrchestrationController(config, executor)
    output = {"status": "blocked", "results": []}
    try:
        with execution_slot(controller.budget, parent):
            output.update(execute_plan(request, controller, output))
            output["artifacts"] = executor.finish(output["status"] == "completed")
    except (ValueError, BudgetExceeded) as exc:
        output.update(status="blocked", reason=str(exc))
        output["artifacts"] = executor.finish(False)
    output["budget"] = asdict(controller.budget.snapshot())
    output["instruction"] = (
        "Report the plan outcome, checks and artifacts. If blocked or refused, explain the reason; "
        "do not silently redo the task outside orchestration or repeat external effects."
    )
    return output
