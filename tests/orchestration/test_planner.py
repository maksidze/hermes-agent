"""Architecture, dependency and refusal behavior without provider traffic."""

import json

import pytest

from agent.orchestration.availability import Availability
from agent.orchestration.config import parse_config
from agent.orchestration.controller import OrchestrationController
from agent.orchestration.planner import compact_plan, execute_plan, parse_plan
from agent.orchestration.router import route_task
from agent.orchestration.types import TaskAttempt, TaskRequest


def configuration(**extra):
    return parse_config({"enabled": True, "profiles": {
        level: {"enabled": True, "provider": "openrouter", "model": level, "level": level}
        for level in ("fast", "balanced", "deep")}, "routes": {"general": ["fast", "balanced", "deep"]},
        "automation": {"mode": "development", "planner_profile": "deep"},
        "verification": {"semantic": "off"}, **extra})


def task(id, deps=(), level="fast"):
    return {"id": id, "goal": "Implement module", "level": level, "depends_on": list(deps), "acceptance": "Run tests"}


def test_dependency_validation():
    for tasks in ([task("a", ["a"])], [task("a"), task("a")], [task("a", ["b"]), task("b")]):
        with pytest.raises(ValueError, match="dependencies"):
            parse_plan(json.dumps({"architecture": "design", "tasks": tasks}), 6)


def test_omitted_dependencies_mean_none_but_invalid_dependencies_still_fail():
    single = task("site")
    del single["depends_on"]
    parsed = parse_plan(json.dumps({"architecture": "Static site", "tasks": [single]}), 6)
    assert parsed["tasks"][0]["depends_on"] == []
    for invalid in (None, "site", ["site"], ["missing"]):
        with pytest.raises(ValueError):
            parse_plan(json.dumps({"architecture": "Static site", "tasks": [{**single, "depends_on": invalid}]}), 6)


def test_invalid_plan_error_names_field_without_dumping_schema():
    broken = {**task("site"), "goal": 42}
    with pytest.raises(ValueError) as error:
        parse_plan(json.dumps({"architecture": "Static site", "tasks": [broken]}), 6)
    assert "tasks.0.goal" in str(error.value)
    assert "Failed validating" not in str(error.value)
    assert len(str(error.value)) < 200


def test_architect_then_workers_dependencies_and_shared_budget():
    class Executor:
        calls = []
        def execute(self, request, profile, context, budget, *, reviewer=False, retained_effects=()):
            budget.before_request(None)
            self.calls.append((profile.id, context))
            summary = json.dumps({"architecture": "design", "execution": "staged",
                                  "decomposition_reason": "Independent implementation and integration deliverables",
                                  "tasks": [task("a"), task("b", ["a"], "balanced")]})
            return TaskAttempt(budget.snapshot().attempts, profile.id, "completed", summary if reviewer else "done",
                               evidence={"verification": {"status": "passed"}})
    executor = Executor()
    controller = OrchestrationController(configuration(), executor, availability=lambda *_: Availability(True))
    output = execute_plan(TaskRequest("Develop a module"), controller)
    assert output["status"] == "completed"
    assert [p for p, _ in executor.calls] == ["deep", "fast", "balanced"]
    handoff_text = executor.calls[-1][1]
    handoff, _ = json.JSONDecoder().raw_decode(handoff_text[handoff_text.index("{"):])
    assert json.loads(handoff["constraints"])["completed"] == [{"id": "a", "summary": "done"}]
    assert controller.budget.snapshot().attempts == 3
    assert controller.budget.snapshot().model_calls == 3


def test_refusal_stops_without_retry_and_fixed_worker_ignores_rank():
    class Executor:
        calls = 0
        def execute(self, request, profile, context, budget, *, retained_effects=()):
            self.calls += 1
            return TaskAttempt(1, profile.id, "completed", "ORCHESTRATION_REFUSED: permission denied")
    executor = Executor()
    config = configuration(routing={"preferred_profile": "fast"})
    request = TaskRequest("Complex architecture", level="deep")
    assert [p.id for p in route_task(request, config).profiles] == ["fast"]
    output = OrchestrationController(config, executor, availability=lambda *_: Availability(True)).run(request)
    assert output.status == "blocked"
    assert output.reason.startswith("refused")
    assert executor.calls == 1


def test_single_deliverable_does_not_spawn_a_worker_for_each_file_and_validation():
    request = TaskRequest("Create a coin flip website")
    plan = {"architecture": "HTML CSS JS", "tasks": [task("html"), task("css", ["html"]),
            task("js", ["css"]), task("validate", ["js"])]}
    compact = compact_plan(parse_plan(json.dumps(plan), 6), request)
    assert len(compact["tasks"]) == 1
    assert compact["tasks"][0]["goal"] == request.goal
    assert compact["tasks"][0]["depends_on"] == []
    with pytest.raises(ValueError, match="reason"):
        compact_plan({**plan, "execution": "staged"}, request)
