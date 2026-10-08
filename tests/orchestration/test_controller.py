"""Contracts for profile routing, repair, escalation, privacy and bounded cost."""
import pytest

from agent.orchestration.availability import Availability
from agent.orchestration.config import parse_config
from agent.orchestration.controller import OrchestrationController
from agent.orchestration.router import route_task
from agent.orchestration.types import TaskAttempt, TaskRequest


def configuration(**overrides):
    profiles = {level: {"enabled": True, "provider": "local" if level == "fast" else "openrouter",
                        "model": f"model-{level}", "level": level} for level in ("fast", "balanced", "deep")}
    return parse_config({"enabled": True, "profiles": profiles,
                         "routes": {"general": list(profiles), "coding": list(profiles)},
                         "verification": {"semantic": "off"}, **overrides})


class Executor:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []
        self.contexts = []

    def execute(self, request, profile, context, budget, **kwargs):
        budget.before_request(None)
        self.calls.append(profile.id)
        self.contexts.append(context)
        return TaskAttempt(budget.snapshot().attempts, profile.id, "completed", next(self.results))


def available(profile, _settings):
    return Availability(True, runtime={"base_url": "http://127.0.0.1:1234/v1" if profile.id == "fast" else "https://example.invalid/v1"})


def request(**kwargs):
    return TaskRequest("Fix the unit test", output_schema={"type": "object", "properties": {"ok": {"const": True}},
                                                        "required": ["ok"]}, **kwargs)


def test_minimum_sufficient_route_and_direct_deep():
    config = configuration()
    assert route_task(TaskRequest("Translate this short text"), config).level == "fast"
    assert [p.id for p in route_task(TaskRequest("Design an architecture migration"), config).profiles] == ["deep"]
    assert route_task(request(), config).name == "coding"


def test_explicit_route_order_wins_over_legacy_profile_priority():
    profiles = {
        "first": {"enabled": True, "provider": "local", "model": "small", "level": "fast"},
        "backup": {"enabled": True, "provider": "local", "model": "other", "level": "fast", "priority": 99},
        "strong": {"enabled": True, "provider": "local", "model": "large", "level": "deep"},
    }
    config = configuration(profiles=profiles, routes={"general": list(profiles)})
    assert [p.id for p in route_task(TaskRequest("Hello", level="fast"), config).profiles] == list(profiles)
    assert [p.id for p in route_task(TaskRequest("Hello", level="deep"), config).profiles] == ["strong"]


def test_schema_repair_then_escalation_preserves_failed_evidence():
    executor = Executor(['{"ok": false}', 'still wrong', '{"ok": true}'])
    result = OrchestrationController(configuration(), executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast", "fast", "balanced"]
    assert result.attempts[1].repair
    assert "schema_failed" in executor.contexts[-1]
    assert result.budget.escalations == 1
    assert result.budget.model_calls == 3
    assert result.state == "SUCCEEDED"


def test_pass_never_calls_cloud():
    executor = Executor(['{"ok": true}'])
    result = OrchestrationController(configuration(), executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast"]


def test_deep_failure_terminates():
    executor = Executor(["bad fast", "bad balanced", "bad deep"])
    result = OrchestrationController(configuration(escalation={"same_profile_repairs": 0}), executor,
                                     availability=available).run(request())
    assert result.status == "failed"
    assert executor.calls == ["fast", "balanced", "deep"]
    assert result.budget.escalations == 2


def test_unavailable_local_is_not_escalation():
    executor = Executor(['{"ok": true}'])
    def probe(profile, settings):
        return Availability(False, "provider_unavailable") if profile.id == "fast" else available(profile, settings)
    result = OrchestrationController(configuration(), executor, availability=probe).run(request())
    assert executor.calls == ["balanced"]
    assert result.status == "completed"
    assert result.budget.escalations == 0


def test_cloud_policy_applies_even_after_local_failure():
    executor = Executor(["bad", "bad again"])
    result = OrchestrationController(configuration(privacy={"cloud_allowed": False}), executor,
                                     availability=available).run(request())
    assert result.status == "failed"
    assert set(executor.calls) == {"fast"}


@pytest.mark.parametrize("limits, expected", [({"max_attempts": 1}, "max_attempts"),
                                            ({"max_model_calls": 1}, "max_model_calls"),
                                            ({"max_escalations": 0}, "max_escalations")])
def test_budget_terminates_before_extra_request(limits, expected):
    executor = Executor(["bad", "wrong", "also wrong"])
    result = OrchestrationController(configuration(budget=limits, escalation={"same_profile_repairs": 0}),
                                     executor, availability=available).run(request())
    assert result.status == "blocked"
    assert result.reason == expected
    assert result.state == "BUDGET_EXHAUSTED"
    assert len(executor.calls) == 1


def test_disabled_spends_no_calls():
    executor = Executor([])
    result = OrchestrationController(configuration(enabled=False), executor, availability=available).run(request())
    assert result.status == "blocked"
    assert result.reason == "orchestration_disabled"
    assert not executor.calls


def test_repair_success_stays_on_fast():
    executor = Executor(['{"ok": false}', '{"ok": true}'])
    result = OrchestrationController(configuration(), executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast", "fast"]
    assert result.budget.escalations == 0


def test_semantic_reviewer_uses_shared_budget():
    executor = Executor(['{"ok": true}', '{"verdict": "pass", "reasons": []}'])
    config = configuration(verification={"semantic": "always", "verifier_profile": "balanced"})
    result = OrchestrationController(config, executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast", "balanced"]
    assert result.budget.model_calls == 2
    assert result.budget.attempts == 1


def test_vision_route_skips_explicitly_incompatible_profile():
    from agent.orchestration.profiles import compatible
    from dataclasses import replace
    config = configuration()
    config.profiles["fast"] = replace(config.profiles["fast"], capabilities={"vision": False})
    config.profiles["balanced"] = replace(config.profiles["balanced"], capabilities={"vision": True})
    task = request(images=("https://example.invalid/picture.png",))
    assert not compatible(config.profiles["fast"], task, {})
    executor = Executor(['{"ok": true}'])
    result = OrchestrationController(config, executor, availability=available).run(task)
    assert result.status == "completed"
    assert executor.calls == ["balanced"]


def test_cancelled_task_never_starts_an_executor():
    from agent.orchestration.budget import BudgetLedger
    config = configuration()
    ledger = BudgetLedger(config.settings["budget"])
    ledger.cancelled.set()
    executor = Executor([])
    result = OrchestrationController(config, executor, availability=available, budget=ledger).run(request())
    assert result.state == "CANCELLED"
    assert not executor.calls


def test_explicit_help_request_skips_same_profile_repair():
    executor = Executor(['needs_escalation: cannot solve this', '{"ok": true}'])
    result = OrchestrationController(configuration(), executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast", "balanced"]


def test_default_budget_reserves_last_attempt_for_deep():
    executor = Executor(['bad fast', 'failed repair', 'bad balanced', '{"ok": true}'])
    result = OrchestrationController(configuration(), executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast", "fast", "balanced", "deep"]
    assert result.budget.attempts == 4
