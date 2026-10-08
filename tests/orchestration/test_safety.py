"""No retry of uncertain writes, no writer overlap, no auxiliary budget escape."""

from concurrent.futures import Future
import json
from types import SimpleNamespace

import pytest

from agent.execution_policy import execution_scope
from agent.orchestration.budget import BudgetExceeded, BudgetLedger
from agent.orchestration.config import DEFAULTS
from agent.orchestration.executor import ExecutionPolicy, execution_slot
from agent.orchestration.handoff import capture_evidence
from agent.orchestration.types import TaskRequest


def test_auxiliary_sync_async_and_stream_fail_closed_before_network():
    import asyncio
    from openai import OpenAI, AsyncOpenAI
    from agent.auxiliary_client import _relay_sync_completion, _relay_async_completion, _relay_sync_stream
    ledger = BudgetLedger({**DEFAULTS["budget"], "max_model_calls": 1})
    policy = ExecutionPolicy(ledger, TaskRequest("local only"), False, {})
    kwargs = {"model": "example", "messages": [{"role": "user", "content": "hello"}]}
    with OpenAI(base_url="https://example.invalid/v1", api_key="test") as remote:
        with execution_scope(policy), pytest.raises(ValueError, match="loopback"):
            _relay_sync_completion(remote, kwargs)
    with OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="test") as local:
        with execution_scope(policy):
            assert _relay_sync_completion(local, kwargs, create=lambda _: "ok") == "ok"
            with pytest.raises(BudgetExceeded, match="max_model_calls"):
                _relay_sync_stream(local, kwargs)

    async def run():
        async with AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="test") as local:
            with execution_scope(policy), pytest.raises(BudgetExceeded, match="max_model_calls"):
                await _relay_async_completion(local, kwargs)
    asyncio.run(run())
    assert ledger.snapshot().model_calls == 1


def test_abandoned_worker_keeps_workspace_blocked_until_it_settles(monkeypatch):
    from agent.orchestration import executor
    monkeypatch.setattr(executor, "workspace_key", lambda _: "isolated-test-workspace")
    ledger = BudgetLedger(DEFAULTS["budget"])
    future = Future()
    service = SimpleNamespace(wait=lambda *a, **kw: SimpleNamespace(completed=True))
    monkeypatch.setitem(executor._CANCELLING, "isolated-test-workspace", (service, "handle", SimpleNamespace(worker=future)))
    with pytest.raises(BudgetExceeded, match="previous_writer_still_cancelling"):
        with execution_slot(ledger, None):
            pytest.fail("Writer started while abandoned worker was live")
    future.set_result(None)
    with execution_slot(ledger, None):
        assert "isolated-test-workspace" not in executor._CANCELLING


@pytest.mark.parametrize("command, uncertain", [("npm test", False), ("curl -X POST https://example.invalid", True),
                                                  ("npm test; curl https://example.invalid", True)])
def test_opaque_shell_side_effects_require_review(command, uncertain):
    child = SimpleNamespace(_session_messages=[
        {"role": "assistant", "reasoning": "private reasoning", "tool_calls": [
            {"id": "a", "function": {"name": "terminal", "arguments": json.dumps({"command": command})}}]},
        {"role": "tool", "tool_call_id": "a", "content": "done"},
    ])
    evidence = capture_evidence(child, {})
    assert bool(evidence["uncertain_side_effects"]) is uncertain
    assert "private reasoning" not in json.dumps(evidence)


def test_schema_validation_does_not_fetch_remote_references():
    from agent.orchestration.verifier import validate_schema
    valid, errors = validate_schema('{}', {"$ref": "https://example.invalid/schema"})
    assert not valid
    assert "Unresolvable" in errors[0]
