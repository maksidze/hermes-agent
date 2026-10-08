"""Optional provider routing for the public lifecycle, using delegation's resolver."""


def build_routed_child(request, parent, execution=None):
    from tools.delegate_tool import (
        DEFAULT_MAX_ITERATIONS, _build_child_preserving_parent_tools,
        _load_config, _resolve_delegation_credentials,
    )
    cfg = {"provider": request.provider, "model": request.model}
    creds = _resolve_delegation_credentials(cfg, parent)
    if execution is not None:
        execution.validate_runtime(creds)
    child = _build_child_preserving_parent_tools(
        task_index=0, goal=request.goal, context=request.context,
        toolsets=list(request.allowed_toolsets) if request.allowed_toolsets else None,
        model=request.model, max_iterations=_load_config().get("max_iterations", DEFAULT_MAX_ITERATIONS),
        task_count=1, parent_agent=parent, role=request.role,
        override_provider=creds["provider"], override_base_url=creds["base_url"],
        override_api_key=creds["api_key"], override_api_mode=creds["api_mode"],
        override_request_overrides=creds.get("request_overrides"),
        override_acp_command=creds.get("command"), override_acp_args=creds.get("args"), routing_cfg=cfg,
    )
    if request.reasoning_effort is not None:
        from hermes_constants import parse_reasoning_effort
        child.reasoning_config = parse_reasoning_effort(request.reasoning_effort)
    if execution is not None:
        execution.configure(child)
    return child
