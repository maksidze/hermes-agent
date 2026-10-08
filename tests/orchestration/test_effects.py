"""Observed success is not an unknown outcome; uncertain writes still stop automatic retry."""

import json
from types import SimpleNamespace

import pytest

from agent.orchestration.budget import BudgetLedger
from agent.orchestration.config import DEFAULTS
from agent.orchestration.controller import OrchestrationController
from agent.orchestration.executor import ExecutionPolicy
from agent.orchestration.handoff import capture_evidence
from agent.orchestration.types import TaskAttempt, TaskRequest
from tests.orchestration.test_controller import available, configuration, request


def evidence(result, disposition=None):
    messages = [
        {"role":"assistant", "tool_calls":[{"id":"1", "function":{"name":"tool_call",
            "arguments": json.dumps({"name":"mcp__editor__update", "arguments":{"value":3}})}}]},
        {"role":"tool", "tool_call_id":"1", "tool_name":"mcp__editor__update", "content":result,
         "effect_disposition":disposition}
    ]
    return capture_evidence(SimpleNamespace(_session_messages=messages), {})


@pytest.mark.parametrize("outcome, disposition, expected", [('{"result":"updated"}', None, "confirmed"),
    ('{"error":"failed after partial update"}', None, "uncertain"), ('timeout', "unknown", "uncertain"),
    ('{"error":"blocked before dispatch"}', "none", "none")])
def test_external_outcomes_are_classified_from_observation(outcome, disposition, expected):
    result = evidence(outcome, disposition)
    assert result["tool_results"][0]["effect"] == expected
    assert bool(result["uncertain_side_effects"]) is (expected == "uncertain")


def test_limit_does_not_escalate_without_user_consent():
    class Executor:
        calls = []
        retained = ()
        def execute(self, request, profile, context, budget, **kwargs):
            self.calls.append(profile.id)
            if len(self.calls) == 1:
                observed = evidence('{"result":"updated"}')
                observed["failure_reason"] = "attempt_model_calls"
                return TaskAttempt(1, profile.id, "failed", "limit", evidence=observed)
            self.retained = kwargs["retained_effects"]
            assert "do not repeat" in context
            return TaskAttempt(2, profile.id, "completed", '{"ok":true}')
    executor = Executor()
    result = OrchestrationController(configuration(), executor, availability=available).run(request())
    assert result.status == "blocked"
    assert executor.calls == ["fast"]
    policy = ExecutionPolicy(BudgetLedger(DEFAULTS["budget"]), TaskRequest("Continue"), True, {},
                             retained_effects=evidence('{"result":"updated"}')["tool_results"])
    assert policy.tool_block("mcp__editor__update", {"value":3}, None)
    assert policy.tool_block("mcp__editor__update", {"value":4}, None) is None


def test_uncertain_external_write_does_not_escalate():
    class Executor:
        def execute(self, request, profile, context, budget, **kwargs):
            observed = evidence('{"error":"partial update"}')
            observed["failure_reason"] = "attempt_model_calls"
            return TaskAttempt(1, profile.id, "failed", "limit", evidence=observed)
    result = OrchestrationController(configuration(), Executor(), availability=available).run(request())
    assert result.status == "blocked"
    assert result.reason == "model_calls_continuation_not_approved"
    assert len(result.attempts) == 1


def test_mcp_read_only_annotation_resolves_through_profile_scoped_discovery(monkeypatch):
    from tools import mcp_tool
    from tools.mcp_tool_scope import _resolve_server_key
    monkeypatch.setitem(mcp_tool._mcp_tool_server_names, "mcp__editor__inspect", "editor")
    monkeypatch.setitem(mcp_tool._tool_read_only_hints, _resolve_server_key("editor"), {"inspect": True})
    child = SimpleNamespace(_session_messages=[{"role":"tool", "tool_name":"mcp__editor__inspect", "content":"facts"}])
    observed = capture_evidence(child, {})
    assert observed["uncertain_side_effects"] == []
    assert observed["confirmed_side_effects"] == []


def test_current_attempt_does_not_repeat_a_write_after_an_error():
    policy = ExecutionPolicy(BudgetLedger(DEFAULTS["budget"]), TaskRequest("Create artifact"), True, {})
    child = SimpleNamespace(base_url="http://localhost:1234", tools=[], disabled_toolsets=[], tool_complete_callback=None)
    policy.configure(child)
    args = {"path":"output.project", "content":"artifact"}
    child.tool_complete_callback("1", "mcp__editor__save", args, '{"error":"partial save"}')
    assert policy.tool_block("mcp__editor__save", dict(reversed(list(args.items()))), None)
    assert policy.tool_block("mcp__editor__save", {**args, "path":"corrected/output.project"}, None) is None
