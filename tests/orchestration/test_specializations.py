"""Specialist choice is independent of capacity, bounded and privacy-aware."""

import json

import pytest

from agent.orchestration.availability import Availability
from agent.orchestration.config import parse_config
from agent.orchestration.controller import OrchestrationController
from agent.orchestration.planner import execute_plan
from agent.orchestration.specializations import explicit_category, task_config
from agent.orchestration.types import TaskAttempt, TaskRequest


def configuration(**extra):
    return parse_config({"enabled": True, "profiles": {
        level: {"enabled": True, "provider": "custom:local", "model": level, "level": level}
        for level in ("fast", "balanced", "deep")},
        "routes": {"general": ["deep"], "specialist": ["fast"]},
        "automation": {"planner_profile": "deep"},
        "verification": {"semantic": "off"},
        "specializations": {
            "roleplay": {"enabled": True, "description": "Character dialogue", "route": "specialist", "local_only": False},
            "private": {"enabled": True, "description": "Private task", "route": "specialist", "local_only": True},
            "disabled": {"enabled": False, "description": "Unavailable", "route": "specialist", "local_only": False}},
        **extra})


def transfer(category):
    return 'ORCHESTRATION_SPECIALIST: ' + json.dumps({"category": category, "reason": "Character dialogue expertise"})


class Executor:
    def __init__(self, answers, evidence=None):
        self.answers = iter(answers)
        self.calls = []
        self.evidence = evidence or {}

    def execute(self, request, profile, context, budget, **kwargs):
        budget.before_request(None)
        self.calls.append((request, profile.id, context))
        return TaskAttempt(budget.snapshot().attempts, profile.id, "completed", next(self.answers),
                           evidence=dict(self.evidence))


def available(*_args):
    return Availability(True, runtime={"base_url": "http://127.0.0.1:1234/v1"})


def test_deep_requests_small_specialist_and_preserves_attempts_without_escalation():
    executor = Executor([transfer("roleplay"), '{"ok": true}'], {"files_changed": ["dialogue.txt"]})
    request = TaskRequest("Write character dialogue", level="deep", output_schema={"type": "object"})
    result = OrchestrationController(configuration(), executor, availability=available).run(request)
    assert result.status == "completed"
    assert [call[1] for call in executor.calls] == ["deep", "fast"]
    assert all(call[0].task_id == request.task_id for call in executor.calls)
    assert result.route == "specialist"
    assert result.budget.escalations == 0
    assert result.budget.attempts == result.budget.model_calls == 2
    assert "dialogue.txt" in executor.calls[-1][2]
    assert "Character dialogue expertise" in executor.calls[-1][2]
    assert result.attempts[0].evidence["specialist_request"]["category"] == "roleplay"


@pytest.mark.parametrize("category, expected", [("missing", "specialization_unavailable"),
    ("disabled", "specialization_unavailable"), ("private", "local_selection_required")])
def test_unknown_disabled_or_late_private_transfer_stops_before_next_worker(category, expected):
    executor = Executor([transfer(category)])
    result = OrchestrationController(configuration(), executor, availability=available).run(TaskRequest("Dialogue"))
    assert result.status == "blocked"
    assert result.reason.startswith(expected)
    assert len(executor.calls) == 1


@pytest.mark.parametrize("evidence, expected", [({"failure_reason": "content_policy_blocked"}, "refused"),
    ({"failure_reason": "permission_denied"}, "refused"),
    ({"uncertain_side_effects": ["service changed"]}, "uncertain_side_effects")])
def test_refusal_and_uncertain_external_effects_take_priority_over_transfer(evidence, expected):
    executor = Executor([transfer("roleplay")], evidence)
    result = OrchestrationController(configuration(), executor, availability=available).run(TaskRequest("Dialogue"))
    assert result.status == "blocked"
    assert result.reason.startswith(expected)
    assert len(executor.calls) == 1


@pytest.mark.parametrize("switches, expected, calls", [(0, "specialist_switch_limit", 1), (2, "specialist_cycle", 2)])
def test_specialist_transfers_are_bounded(switches, expected, calls):
    executor = Executor([transfer("roleplay"), transfer("roleplay")])
    config = configuration(routing={"max_specialist_switches": switches})
    result = OrchestrationController(config, executor, availability=available).run(TaskRequest("Dialogue"))
    assert result.status == "blocked"
    assert result.reason.startswith(expected)
    assert len(executor.calls) == calls


def test_local_category_blocks_cloud_before_architect_and_keeps_config_immutable():
    config = configuration()
    request = TaskRequest("Private text", specialization="private", specialization_reason="Explicit user choice")
    scoped = task_config(config, request)
    executor = Executor([])
    cloud = lambda *_: Availability(True, runtime={"base_url": "https://example.invalid/v1"})
    controller = OrchestrationController(scoped, executor, availability=cloud)
    with pytest.raises(ValueError, match="Architect profile is unavailable"):
        execute_plan(request, controller)
    assert not executor.calls
    assert scoped.settings["automation"]["planner_profile"] == "fast"
    assert scoped.settings["verification"]["verifier_profile"] == "fast"
    assert scoped.settings["privacy"]["cloud_allowed"] is False
    assert config.settings["privacy"]["cloud_allowed"] is True
    assert config.settings["automation"]["planner_profile"] == "deep"
    assert explicit_category("@local_private confidential input", config) == "local_private"
    with pytest.raises(ValueError, match="specialization_unavailable"):
        task_config(config, TaskRequest("secret", specialization="local_private", specialization_reason="User choice"))


@pytest.mark.parametrize("category", ["roleplay", "private", "disabled"])
def test_architect_selects_specialist_or_rejects_entire_plan_before_writing(category):
    tasks = [{"id": "scene", "goal": "Write a scene", "level": "fast", "depends_on": [], "acceptance": "Dialogue"},
             {"id": "voices", "goal": "Refine voices", "level": "fast", "depends_on": ["scene"],
              "acceptance": "Distinct voices", "specialization": category, "specialization_reason": "Dialogue expertise"}]
    executor = Executor([json.dumps({"architecture": "Two character scene", "tasks": tasks}), "draft", "final"],
                        {"verification": {"status": "passed"}})
    controller = OrchestrationController(configuration(), executor, availability=available)
    if category != "roleplay":
        with pytest.raises(ValueError, match="local_selection_required|specialization_unavailable"):
            execute_plan(TaskRequest("Write a scene"), controller)
        assert len(executor.calls) == 1
    else:
        result = execute_plan(TaskRequest("Write a scene"), controller)
        assert result["status"] == "completed"
        assert [call[1] for call in executor.calls] == ["deep", "deep", "fast"]
        assert result["results"][1]["specialization"] == "roleplay"


@pytest.mark.parametrize("explicit", [None, "private"])
def test_invented_architect_category_keeps_original_route_and_privacy(explicit):
    request = TaskRequest("Create a site", specialization=explicit,
                          specialization_reason="Explicit user choice" if explicit else "")
    config = task_config(configuration(), request)
    task = {"id": "site", "goal": "Build site", "level": "fast", "depends_on": [], "acceptance": "Working page",
            "specialization": "frontend", "specialization_reason": "Website development"}
    executor = Executor([json.dumps({"architecture": "Static site", "tasks": [task]}), "done"],
                        {"verification": {"status": "passed"}})
    controller = OrchestrationController(config, executor, availability=available)
    result = execute_plan(request, controller)
    assert result["status"] == "completed"
    assert len(executor.calls) == 2
    assert result["results"][0]["specialization"] == explicit
    assert "specialization" not in result["plan"]["tasks"][0]
    assert config.settings["privacy"]["cloud_allowed"] is (explicit is None)


def test_category_uses_its_reviewer_and_retains_local_privacy_on_transfer():
    config = configuration(verification={"semantic": "always", "verifier_profile": "deep"})
    config.settings["specializations"]["roleplay"]["verifier_profile"] = "balanced"
    request = TaskRequest("Private dialogue", specialization="private", specialization_reason="User choice")
    scoped = task_config(config, request)
    # Only the original private profile is local. Moving to a non-private category
    # must never relax the original run's model privacy, including its reviewer.
    executor = Executor([transfer("roleplay"), "dialogue"])
    def probe(profile, settings):
        return available() if profile.id == "fast" else Availability(True, runtime={"base_url": "https://example.invalid"})
    result = OrchestrationController(scoped, executor, availability=probe).run(request)
    assert result.status != "completed"
    assert [call[1] for call in executor.calls] == ["fast", "fast"]
    assert result.attempts[-1].verification.reasons == ("verifier_unavailable",)
    assert config.settings["privacy"]["cloud_allowed"] is True


def test_category_reviewer_override_is_used_even_when_smaller_than_main_reviewer():
    config = configuration(verification={"semantic": "always", "verifier_profile": "deep"})
    config.settings["specializations"]["roleplay"]["verifier_profile"] = "fast"
    executor = Executor(["dialogue", '{"verdict": "pass", "reasons": []}'])
    request = TaskRequest("Dialogue", specialization="roleplay", specialization_reason="Character voices")
    result = OrchestrationController(config, executor, availability=available).run(request)
    assert result.status == "completed"
    assert [call[1] for call in executor.calls] == ["fast", "fast"]
    assert executor.calls[-1][0].specialization == "roleplay"
