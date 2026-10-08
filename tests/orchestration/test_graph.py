"""Execute real LangGraph transitions with Hermes budget and privacy contracts."""

from copy import deepcopy
import pytest

from agent.orchestration.config import parse_config
from agent.orchestration.controller import OrchestrationController
from agent.orchestration.types import VerificationResult
from tests.orchestration.test_controller import Executor, available, configuration, request


def workflow():
    return {"entry": "front", "nodes": [
        {"id": "front", "profiles": ["deep", "fast"], "description": "Build the frontend"},
        {"id": "review", "profiles": ["balanced"]}],
        "edges": [{"source": "front", "target": "review", "on": "failure"}]}


def config(graph=None, **extra):
    return configuration(graphs={"coding": graph or workflow()}, escalation={"same_profile_repairs": 0}, **extra)


def test_multiple_models_in_group_then_explicit_transition_with_evidence():
    executor = Executor(['{"ok": false}', '{"ok": false}', '{"ok": true}'])
    result = OrchestrationController(config(), executor, availability=available).run(request(level="deep"))
    assert result.status == "completed"
    assert executor.calls == ["deep", "fast", "balanced"]
    assert "schema_failed" in executor.contexts[-1]
    assert "Build the frontend" in executor.contexts[0]
    assert result.budget.model_calls == 3


def test_uncertain_has_its_own_transition_without_repeating_implementation():
    graph = workflow()
    graph["edges"][0]["on"] = "uncertain"
    executor = Executor(["needs a check", '{"ok": true}'])
    def verifier(_request, attempt, *_args):
        return VerificationResult("uncertain" if attempt.profile == "deep" else "pass")
    result = OrchestrationController(config(graph), executor, availability=available, verifier=verifier).run(request())
    assert result.status == "completed"
    assert executor.calls == ["deep", "balanced"]


def test_success_connection_continues_and_cycles_stop_at_shared_budget():
    graph = workflow()
    graph["edges"][0]["on"] = "success"
    graph["edges"].append({"source": "review", "target": "front", "on": "success"})
    executor = Executor(['{"ok": true}'] * 4)
    result = OrchestrationController(config(graph, budget={"max_model_calls": 3}), executor, availability=available).run(request())
    assert result.reason == "max_model_calls"
    assert executor.calls == ["deep", "balanced", "deep"]


def test_graph_cannot_override_local_only_or_refusal():
    executor = Executor(['{"ok": true}'])
    result = OrchestrationController(config(privacy={"cloud_allowed": False}), executor, availability=available).run(request())
    assert result.status == "completed"
    assert executor.calls == ["fast"]
    executor = Executor(["ORCHESTRATION_REFUSED: permission required"])
    result = OrchestrationController(config(), executor, availability=available).run(request())
    assert result.status == "blocked"
    assert executor.calls == ["deep"]


@pytest.mark.parametrize("issue", ["unreachable", "duplicate_port", "unknown_profile"])
def test_reject_invalid_graph_before_execution(issue):
    graph = deepcopy(workflow())
    if issue == "unreachable":
        graph["edges"] = []
    elif issue == "duplicate_port":
        graph["edges"] *= 2
    else:
        graph["nodes"][0]["profiles"] = ["missing"]
    with pytest.raises(ValueError):
        config(graph, routing={"adaptive_entry": False})


def test_description_and_profiles_without_legacy_levels_roundtrip():
    value = parse_config({"profiles": {"local": {"enabled": True, "provider": "local", "model": "m", "description": "Frontend"}}})
    assert value.profiles["local"].description == "Frontend"


def test_unavailable_cycle_is_bounded_without_model_calls():
    from agent.orchestration.availability import Availability
    graph = workflow()
    graph["edges"] = [{"source": "front", "target": "review", "on": "unavailable"},
                      {"source": "review", "target": "front", "on": "unavailable"}]
    executor = Executor([])
    result = OrchestrationController(config(graph), executor, availability=lambda *_: Availability(False, "offline")).run(request())
    assert result.reason == "graph_transition_limit"
    assert executor.calls == []
