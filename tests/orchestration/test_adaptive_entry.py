"""Architect choice is scoped to configured groups and respects a fixed start."""
import json

import pytest

from agent.orchestration.controller import OrchestrationController
from agent.orchestration.planner import execute_plan
from agent.orchestration.types import TaskAttempt, TaskRequest
from tests.orchestration.test_controller import available, configuration


@pytest.mark.parametrize("chosen, adaptive, expected", [("complex", True, "deep"), ("routine", True, "fast"),
                                                       ("complex", False, "fast")])
def test_architect_selects_entry_without_spending_calls_on_weaker_models(chosen, adaptive, expected):
    executor, config = setup(chosen, adaptive)
    output = execute_plan(TaskRequest("Implement the requested module", route="general"),
                          OrchestrationController(config, executor, availability=available))
    assert output["status"] == "completed"
    assert executor.calls == ["deep", expected]
    assert output["results"][0]["budget"]["model_calls"] == 2


def setup(chosen, adaptive=True):
    graph = {"entry": "routine", "nodes": [{"id": "routine", "profiles": ["fast"]},
                                            {"id": "complex", "profiles": ["deep"]}],
             "edges": [{"source": "routine", "target": "complex", "on": "failure"}]}
    config = configuration(graphs={"general": graph}, routing={"adaptive_entry": adaptive})
    class Executor:
        def __init__(self):
            self.calls = []

        def execute(self, request, profile, context, budget, *, reviewer=False, retained_effects=()):
            budget.before_request(None)
            self.calls.append(profile.id)
            plan = {"architecture": "Module design", "tasks": [{"id": "module", "goal": "Implement module",
                    "acceptance": "Tests pass", "start_node": chosen, "start_reason": "Required reasoning and integration complexity"}]}
            return TaskAttempt(budget.snapshot().attempts, profile.id, "completed", json.dumps(plan) if reviewer else "done",
                               evidence={"verification": {"status": "passed"}})
    return Executor(), config


def test_unknown_group_stops_before_any_worker():
    executor, config = setup("invented")
    with pytest.raises(ValueError, match="Unknown start_node"):
        execute_plan(TaskRequest("Build module", route="general"), OrchestrationController(config, executor, availability=available))
    assert executor.calls == ["deep"]


@pytest.mark.parametrize("chosen", ["fast", "balanced", "deep"])
def test_architect_can_select_any_independent_group(chosen):
    executor, _ = setup(chosen)
    graph = {"entry": "fast", "nodes": [{"id": name, "profiles": [name]}
             for name in ("fast", "balanced", "deep")], "edges": [], "entry_nodes": ["fast", "balanced", "deep"]}
    config = configuration(graphs={"general": graph}, routing={"adaptive_entry": True})
    output = execute_plan(TaskRequest("Create artifact", route="general"),
                          OrchestrationController(config, executor, availability=available))
    assert output["status"] == "completed"
    assert executor.calls == ["deep", chosen]


def test_architect_cannot_start_at_unconnected_fallback_group():
    executor, _ = setup("complex")
    graph = {"entry": "routine", "entry_nodes": ["routine"],
             "nodes": [{"id": "routine", "profiles": ["fast"]}, {"id": "complex", "profiles": ["deep"]}],
             "edges": [{"source": "routine", "target": "complex", "on": "failure"}]}
    config = configuration(graphs={"general": graph})
    with pytest.raises(ValueError, match="not connected"):
        execute_plan(TaskRequest("Create artifact", route="general"),
                     OrchestrationController(config, executor, availability=available))
    assert executor.calls == ["deep"]
