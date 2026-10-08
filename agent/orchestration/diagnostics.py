"""Explicit profile probes through AIAgent; no alternate auth or provider client."""

import json

from .availability import check_profile
from .budget import BudgetLedger
from .config import load_config
from .events import diagnostics
from .profiles import is_local_runtime
from .executor import ExecutionPolicy
from .types import TaskRequest
from agent.execution_policy import execution_scope


def snapshot():
    config = load_config()
    statuses = {p.id: check_profile(p, config.settings["availability"]) for p in config.profiles.values() if p.enabled}
    return {"mode": "on" if config.active else "off", "events": diagnostics(),
            "profiles": [{"id": p.id, "enabled": p.enabled, "provider": p.provider, "model": p.model,
                          "status": ("available" if statuses[p.id].available else statuses[p.id].reason) if p.enabled else "disabled"}
                         for p in config.profiles.values()]}


def test_profile(profile_id):
    from run_agent import AIAgent
    from hermes_constants import parse_reasoning_effort
    from agent.message_metadata import append_message
    config = load_config()
    profile = config.profiles.get(profile_id)
    if profile is None:
        raise ValueError("Unknown execution profile")
    available = check_profile(profile, config.settings["availability"], force=True)
    if not available.available:
        return {"status": available.reason}
    runtime = available.runtime
    if not config.settings["privacy"]["cloud_allowed"] and not is_local_runtime(runtime):
        return {"status": "cloud_disallowed"}
    kwargs = {key: runtime[key] for key in ("provider", "api_key", "base_url", "api_mode") if key in runtime}
    child = AIAgent(**kwargs, model=profile.model, requested_provider=profile.provider,
                    reasoning_config=parse_reasoning_effort(profile.reasoning_effort) if profile.reasoning_effort else None,
                    max_iterations=3, enabled_toolsets=[], quiet_mode=True, skip_memory=True, skip_context_files=True,
                    save_trajectories=False)
    ledger = BudgetLedger({**config.settings["budget"], "max_model_calls": 3, "timeout_seconds": 45})
    policy = ExecutionPolicy(ledger, TaskRequest("Test profile"), config.settings["privacy"]["cloud_allowed"], {})
    policy.configure(child)
    called = []
    use_tools = profile.capabilities.get("tools", "auto") is not False
    if use_tools:
        child.tools = [{"type": "function", "function": {"name": "profile_probe_ping", "description": "Harmless profile test.",
                        "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]
        child.valid_tool_names = {"profile_probe_ping"}

        def ping(message, messages, effective_task_id, api_call_count=0):
            for call in message.tool_calls:
                called.append(call.function.name == "profile_probe_ping")
                append_message(messages, {"role": "tool", "tool_call_id": call.id, "content": json.dumps({"ok": called[-1]})})
        child._execute_tool_calls = ping
    try:
        goal = "Call profile_probe_ping once, then reply PROFILE_OK." if use_tools else "Reply exactly PROFILE_OK."
        with execution_scope(policy):
            result = child.run_conversation(goal)
        if "PROFILE_OK" not in str(result.get("final_response", "")):
            return {"status": "completion_failed"}
        if use_tools and not any(called):
            return {"status": "tool_calling_unsupported"}
        return {"status": "available", "model_calls": ledger.snapshot().model_calls}
    finally:
        child.close()
