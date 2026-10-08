"""Optional, once-per-turn nudge from confirmed Hermes verification failure."""


def stop_nudge(agent):
    from .config import load_config
    config = load_config()
    if not config.active or config.settings["mode"] != "auto" or not config.settings["verification"]["main_agent_stop_gate"]:
        return None
    turn = getattr(agent, "_current_turn_id", None)
    if not turn or getattr(agent, "_orchestration_nudged_turn", None) == turn:
        return None
    changed = sorted(getattr(agent, "_turn_file_mutation_paths", ()) or ())
    if not changed:
        return None
    from agent.verification_stop import _verification_snapshot
    snapshot = _verification_snapshot(session_id=getattr(agent, "session_id", None), changed_paths=changed)
    if not snapshot or snapshot[0].get("status") != "failed":
        return None
    agent._orchestration_nudged_turn = turn
    return ("The current attempt did not satisfy verification. Delegate this task through orchestrate_task "
            "using at least BALANCED level. Preserve existing changes and include the failed verification evidence.")
