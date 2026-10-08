"""Thin lifecycle adapter, with inherited permissions and shared request accounting."""

from contextlib import contextmanager
import json
import os
import threading

from agent.subagent_lifecycle import SubagentLaunchRequest, SubagentLifecycleService, SubagentState
from agent.execution_policy import execution_scope
from .budget import BudgetExceeded
from .handoff import capture_evidence
from .profiles import is_local_runtime
from .types import TaskAttempt

_LOCK = threading.Lock()
_WORKSPACES = {}
_CANCELLING = {}
_PROFILE_ACTIVE = {}


@contextmanager
def profile_slot(profile, budget, policy):
    from hermes_constants import hermes_home_key
    key = (hermes_home_key(), profile.id)
    while True:
        budget.check()
        with _LOCK:
            if _PROFILE_ACTIVE.get(key, 0) < profile.max_parallel:
                _PROFILE_ACTIVE[key] = _PROFILE_ACTIVE.get(key, 0) + 1
                break
        budget.cancelled.wait(0.1)
    def release(_future=None):
        with _LOCK:
            _PROFILE_ACTIVE[key] -= 1
            if not _PROFILE_ACTIVE[key]:
                del _PROFILE_ACTIVE[key]
    try:
        yield
    finally:
        if policy.worker is not None and not policy.worker.done():
            policy.worker.add_done_callback(release)
        else:
            release()


def workspace_key(parent):
    from tools.terminal_tool import get_session_cwd
    from hermes_cli.config import load_config_readonly
    cwd = get_session_cwd(getattr(parent, "_current_task_id", None))
    cwd = cwd or (load_config_readonly().get("terminal") or {}).get("cwd") or os.getcwd()
    return os.path.normcase(os.path.abspath(cwd))


@contextmanager
def execution_slot(budget, parent):
    """MVP serializes writers per workspace, including concurrent orchestration calls.

    This preserves changes across repairs even when delegation's optional
    worktrees are unavailable. The configured parallel limits remain ceilings.
    """
    key = workspace_key(parent)
    with _LOCK:
        lock = _WORKSPACES.setdefault(key, threading.RLock())
    while not lock.acquire(timeout=0.1):
        if getattr(parent, "_interrupt_requested", False):
            budget.cancelled.set()
        budget.check()
    try:
        if getattr(parent, "_interrupt_requested", False):
            budget.cancelled.set()
        budget.check()
        with _LOCK:
            pending = _CANCELLING.get(key)
            if pending and (not pending[0].wait(pending[1], timeout_seconds=0).completed
                            or (pending[2].worker is not None and not pending[2].worker.done())):
                raise BudgetExceeded("previous_writer_still_cancelling")
            _CANCELLING.pop(key, None)
        yield
    finally:
        lock.release()


def validate_delegation(parent):
    from tools.delegate_tool import (
        _get_max_spawn_depth, _get_max_concurrent_children, _get_orchestrator_enabled,
        _oneshot_spawn_budget, is_spawn_paused,
    )
    depth = getattr(parent, "_delegate_depth", 0)
    if is_spawn_paused():
        raise ValueError("Delegation spawning is paused")
    if depth >= _get_max_spawn_depth() or (depth and not _get_orchestrator_enabled()):
        raise ValueError("Delegation depth or orchestrator limit reached")
    if len(getattr(parent, "_active_children", ())) >= _get_max_concurrent_children():
        raise ValueError("delegation.max_concurrent_children reached")
    error = _oneshot_spawn_budget(parent, 1)
    if error:
        raise ValueError(error)


class ExecutionPolicy:
    def __init__(self, budget, request, cloud_allowed, workspace, reviewer=False, retained_effects=()):
        self.budget = budget
        self.request = request
        self.cloud_allowed = cloud_allowed
        self.reviewer = reviewer
        self.workspace = workspace
        self.evidence = {}
        self.worker = None
        self.calls = 0
        self.call_limit = budget.limits.get("max_calls_per_attempt", 12)
        if reviewer:
            self.call_limit = min(self.call_limit, 4 if reviewer == "planner" else 2)
        self.limit_reached = False
        self.retained_effects = list(retained_effects)
        self.effect_lock = threading.Lock()

    def validate_runtime(self, runtime):
        if not self.cloud_allowed and not is_local_runtime(runtime):
            raise ValueError("cloud_allowed=false: execution requires a loopback endpoint")

    def configure(self, child):
        self.validate_runtime({"base_url": getattr(child, "base_url", "")})
        child._orchestration_execution = self
        child._skip_mcp_refresh = True
        # The controller owns model selection; inherited fallback chains must
        # not silently replace a selected profile (including on refusals).
        child._fallback_chain = []
        child._fallback_index = 0
        child._fallback_model = None
        child._delegate_images = list(self.request.images) or None
        original_complete = child.tool_complete_callback

        def completed(call_id, name, args, result):
            from .effects import argument_hash, effect_kind
            effect = effect_kind(name, result, None, json.dumps(args))
            if effect == "uncertain":
                with self.effect_lock:
                    self.retained_effects.append({"tool": name, "arguments_hash": argument_hash(args), "effect": effect})
            if original_complete:
                original_complete(call_id, name, args, result)

        child.tool_complete_callback = completed
        # Fix the child's tool surface BEFORE its first turn. Recursion is
        # deliberately disabled in the MVP, so no descendant escapes the ledger.
        blocked = {"delegate_task", "orchestrate_task"}
        readable = {"read_file", "search_files", "list_directory"}
        child.tools = [tool for tool in (child.tools or [])
                       if (not self.reviewer and tool.get("function", {}).get("name") not in blocked)
                       or (self.reviewer == "planner" and tool.get("function", {}).get("name") in readable)]
        child.valid_tool_names = {tool["function"]["name"] for tool in child.tools}
        child.disabled_toolsets = list(dict.fromkeys([*(child.disabled_toolsets or []), "delegation", "orchestration"]))
        if self.reviewer:
            child.enabled_toolsets = []
        if hasattr(self, "profile"):
            from .progress import observe_tools
            observe_tools(child, self.profile, self.request.task_id)

    def before_request(self, child):
        self.validate_runtime({"base_url": getattr(child, "base_url", "")})
        with self.budget.lock:
            self.budget.check()
            from .continuation import extend_calls
            if not extend_calls(self, child):
                self.limit_reached = True
                self.limit_reason = ("max_model_calls" if self.budget.state.model_calls >= self.budget.limits["max_model_calls"]
                                     else "attempt_model_calls")
                raise BudgetExceeded(self.limit_reason)
            self.budget.before_request(child)
            self.calls += 1

    def input_message(self, message):
        from .attachments import child_message
        from .media_evidence import REFERENCE_CONTRACT
        note = REFERENCE_CONTRACT
        if self.request.visual_check:
            note += " A fresh candidate image after the final edit is required for review."
        if self.request.artifact_paths:
            note += " Required output files beneath the assigned workspace: " + json.dumps(self.request.artifact_paths)
        if isinstance(message, str):
            message += "\n\n" + note
        else:
            message = [*message, {"type": "text", "text": note}]
        return child_message(message, self.request.attachments)

    def capture(self, child, raw):
        evidence = capture_evidence(child, raw)
        if self.evidence.get("tool_results") and not evidence["tool_results"]:
            for key in ("tool_results", "commands_executed", "files_changed", "uncertain_side_effects"):
                evidence[key] = self.evidence[key]
        self.evidence = evidence

    def worker_started(self, future):
        self.worker = future

    def tool_block(self, name, args, task_id):
        from .file_boundary import file_write_block
        from .effects import argument_hash
        with self.effect_lock:
            repeated = any(row["tool"] == name and row["arguments_hash"] == argument_hash(args) for row in self.retained_effects)
        if repeated:
            return ("This external operation was already dispatched. Inspect existing state "
                    "and continue retained work; do not replay the same side effect.")
        return file_write_block(self.workspace.get("worktree"), name, args, task_id)

    def workspace_note(self, info):
        return (f"\n\n[ORCHESTRATION WORKSPACE] Work only inside {info['path']}. "
                "Use project-relative paths for terminal/file tools. External apps and MCP servers have their "
                "OWN cwd: use explicit absolute save/render paths beneath this root, not getcwd()/abspath(relative). "
                "Never write to the original checkout. "
                "Inspect retained changes from earlier attempts. Checkpointing and final application are handled "
                "by the controller; do not commit, reset, merge, or remove this worktree.")

    def worktree(self, parent, parent_task_id, subagent_id):
        from pathlib import Path
        from tools.delegate_tool_child_run import _create_isolated_worktree
        if self.reviewer:
            return None
        previous = self.workspace.get("worktree")
        if previous and Path(previous["path"]).is_dir():
            return previous
        created = _create_isolated_worktree(parent, parent_task_id, subagent_id)
        self.workspace["worktree"] = created
        return created


class LifecycleExecutor:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.service = SubagentLifecycleService(lambda: parent)
        self.workspace = {}
        self.journal = None
        if config.settings["workspace"]["enabled"]:
            from .workspace import WorkspaceJournal
            self.journal = WorkspaceJournal(parent, config)

    def finish(self, successful):
        return self.journal.finish(successful) if self.journal else {}

    def record_result(self, result):
        if self.journal:
            self.journal.record_result(result)

    def record_plan(self, plan):
        if self.journal:
            import json
            self.workspace["worktree"] = self.journal.prepare()
            (self.journal.root / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    def execute(self, request, profile, context, budget, *, reviewer=False, retained_effects=()):
        from tools.delegation_output_schema import append_output_contract
        from .specializations import task_config
        policy = ExecutionPolicy(budget, request, task_config(self.config, request).settings["privacy"]["cloud_allowed"],
                                 self.workspace if not reviewer else {}, reviewer, retained_effects)
        policy.profile = profile
        policy.continuation_callback = getattr(self.parent, "clarify_callback", None)
        from .progress import publish
        publish("execution_started", task_id=request.task_id, profile=profile.id, model=profile.model,
                role="architect" if reviewer == "planner" else "reviewer" if reviewer else "executor",
                detail="" if reviewer else request.goal)
        if request.output_schema:
            context = append_output_contract(context, request.output_schema)
            if not reviewer:
                context += ("\nOrchestration control exception: if unable to complete the task, you may instead return "
                            "ORCHESTRATION_ESCALATE: or ORCHESTRATION_REFUSED: with a reason, or the exact "
                            "ORCHESTRATION_SPECIALIST: JSON request described above. These are not successful answers. "
                            "A successful answer must satisfy the output contract.")
        if len(context) > 32000:
            raise ValueError("Handoff and output contract exceed lifecycle context limit")
        with execution_slot(budget, self.parent), profile_slot(profile, budget, policy), execution_scope(policy):
            validate_delegation(self.parent)
            before = None
            if self.journal and not reviewer:
                self.workspace["worktree"] = self.journal.prepare()
                before = self.journal.start_attempt(budget.snapshot().attempts, profile.id)
            goal = request.goal
            if self.journal and not reviewer:
                goal, context = self.journal.remap_paths(goal), self.journal.remap_paths(context)
            handle = self.service.launch(SubagentLaunchRequest(
                goal=goal, context=context, provider=profile.provider, model=profile.model,
                reasoning_effort=profile.reasoning_effort, correlation_id=f"{request.task_id}-{budget.snapshot().attempts}-{reviewer}",
            ), _execution=policy)
            while not self.service.wait(handle, timeout_seconds=0.2).completed:
                try:
                    budget.check()
                    if getattr(self.parent, "_interrupt_requested", False):
                        raise BudgetExceeded("cancelled")
                except BudgetExceeded:
                    self.service.cancel(handle, reason="orchestration budget or cancellation")
                    with _LOCK:
                        _CANCELLING[workspace_key(self.parent)] = (self.service, handle, policy)
                    # Do not start a repair while an interrupted writer still runs.
                    raise
            result = self.service.result(handle)
            if policy.evidence.get("failure_reason") == "timeout":
                with _LOCK:
                    _CANCELLING[workspace_key(self.parent)] = (self.service, handle, policy)
                raise BudgetExceeded("executor_timeout")
            budget.check()
            if budget.blocked_reason:
                raise BudgetExceeded(budget.blocked_reason)
            status = "completed" if result.terminal_state == SubagentState.SUCCEEDED else "failed"
            if not policy.limit_reached and result.terminal_state in {SubagentState.CANCELLED, SubagentState.INTERRUPTED}:
                raise BudgetExceeded("cancelled")
            if policy.limit_reached:
                status = "failed"
                policy.evidence.update(truncated=True, failure_reason=policy.limit_reason)
            summary = ("Attempt model-call limit reached. Inspect the retained changes and checks before continuing."
                       if policy.limit_reached else result.summary or "")
            attempt = TaskAttempt(budget.snapshot().attempts, profile.id, status, summary,
                                  evidence=policy.evidence, api_calls=policy.calls)
            if not reviewer:
                publish("execution_completed", task_id=request.task_id, profile=profile.id, model=profile.model,
                        status=status, detail=attempt.summary)
            if before:
                self.journal.finish_attempt(attempt, before)
        return attempt
