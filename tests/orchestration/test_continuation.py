"""Call limits require consent and retain the running worker's accounting."""

from types import SimpleNamespace

import pytest

from agent.orchestration.budget import BudgetExceeded, BudgetLedger
from agent.orchestration.config import DEFAULTS
from agent.orchestration.executor import ExecutionPolicy
from agent.orchestration.types import TaskRequest


@pytest.mark.parametrize("total", [1, 20])
def test_consent_extends_one_block_without_resetting_counters(total):
    limits = {**DEFAULTS["budget"], "max_model_calls": total, "max_calls_per_attempt": 1}
    now = [0]
    ledger = BudgetLedger(limits, clock=lambda: now[0])
    policy = ExecutionPolicy(ledger, TaskRequest("Continue artifact"), True, {})
    child = SimpleNamespace(base_url="http://localhost:1234")
    asked = []
    def answer(questions):
        asked.append(questions)
        assert ledger.snapshot().model_calls == 1
        now[0] = 1000
        ledger.check()  # Human response time must not consume the execution timeout.
        return {"outcome": "submitted", "answers": {"q0": "Продолжить"}}
    policy.continuation_callback = answer
    policy.before_request(child)
    policy.before_request(child)
    assert len(asked) == 1
    assert ledger.snapshot().model_calls == policy.calls == 2
    assert limits["max_model_calls"] == total
    assert ledger.deadline == 1600


@pytest.mark.parametrize("reply", [
    {"outcome": "submitted", "answers": {"q0": "Остановить"}},
    {"outcome": "cancelled", "answers": {}},
    {"outcome": "timed_out", "answers": {}},
    {"outcome": "submitted", "answers": {"q0": "maybe"}},
])
def test_no_request_is_charged_after_non_approval(reply):
    ledger = BudgetLedger({**DEFAULTS["budget"], "max_calls_per_attempt": 1})
    policy = ExecutionPolicy(ledger, TaskRequest("Continue"), True, {})
    policy.continuation_callback = lambda questions: reply
    child = SimpleNamespace(base_url="http://localhost:1234")
    policy.before_request(child)
    with pytest.raises(BudgetExceeded, match="attempt_model_calls"):
        policy.before_request(child)
    assert policy.calls == ledger.snapshot().model_calls == 1


def test_successful_unannotated_observations_can_repeat_in_same_worker():
    policy = ExecutionPolicy(BudgetLedger(DEFAULTS["budget"]), TaskRequest("Inspect"), True, {})
    child = SimpleNamespace(base_url="http://localhost:1234", tools=[], disabled_toolsets=[], tool_complete_callback=None)
    policy.configure(child)
    child.tool_complete_callback("1", "mcp__editor__preview", {}, '{"result":"image"}')
    assert policy.tool_block("mcp__editor__preview", {}, None) is None
