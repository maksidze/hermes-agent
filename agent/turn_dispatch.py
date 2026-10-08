"""Turn owners that complete before the ordinary model/tool iteration loop."""


def dispatch_owned_turn(agent, state):
    from agent.orchestration.automatic import run_automatic
    automatic = run_automatic(agent, state)
    if automatic is not None:
        return automatic
    if agent.api_mode != "codex_app_server":
        return None
    # The app-server owns a whole turn. A failed transport can activate the
    # existing generic-loop fallback without discarding its transcript or usage.
    result = agent._run_codex_app_server_turn(
        user_message=state.user_message, original_user_message=state.original_user_message,
        messages=state.messages, effective_task_id=state.effective_task_id,
        should_review_memory=state._should_review_memory,
    )
    from agent.turn_recovery import activate_codex_app_server_fallback
    if not activate_codex_app_server_fallback(agent, result):
        return result
    from agent.conversation_loop import _sync_failover_system_message
    state.api_call_count = int(result.get("api_calls") or 0)
    state.active_system_prompt = _sync_failover_system_message(agent, None, state.active_system_prompt)
    return None
