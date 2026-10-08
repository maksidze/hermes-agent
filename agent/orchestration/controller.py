"""Bounded task state machine. The main Hermes agent is never replaced."""

from .availability import check_profile
from .budget import BudgetExceeded, BudgetLedger
from .escalation import decide
from .events import emit
from .handoff import build_handoff, render_handoff
from .profiles import compatible, is_local_runtime, vision_compatible
from .router import route_task
from .specializations import catalog_instructions, requested_specialist, reroute_request, task_config
from .types import EscalationDecision, TaskResult, TaskState
from .verifier import verify

INFRASTRUCTURE_FAILURES = {"provider_unavailable", "network_error", "rate_limit", "authentication_error",
                           "auth", "billing", "api_error", "connection_error"}


class OrchestrationController:
    def __init__(self, config, executor, *, availability=check_profile, verifier=verify, budget=None):
        self.config = config
        self.settings = config.settings
        self.executor = executor
        self.availability = availability
        self.verifier = verifier
        limits = dict(self.settings["budget"])
        limits["max_escalations"] = min(limits["max_escalations"], self.settings["escalation"]["max_escalations"])
        self.budget = budget or BudgetLedger(limits)

    def transition(self, result, state):
        result.state = state
        emit(self.settings, "task_state_changed", task_id=result.task_id, route=result.route, state=state.value)

    def available(self, profile, request, *, reviewer=False):
        status = self.availability(profile, self.settings["availability"])
        reason = status.reason
        settings = task_config(self.config, request).settings
        if status.available and not settings["privacy"]["cloud_allowed"] and not is_local_runtime(status.runtime):
            reason = "cloud_disallowed"
        from .attachments import has_images
        capabilities_ok = (not has_images(request) or vision_compatible(profile, status.runtime)) if reviewer \
            else compatible(profile, request, status.runtime)
        if status.available and not capabilities_ok:
            reason = "insufficient_capability"
        if reason:
            emit(self.settings, "profile_unavailable", task_id=request.task_id, profile=profile.id, reason=reason)
            return False
        return status.available

    def run(self, request):
        if not self.config.active:
            return TaskResult(request.task_id, "blocked", reason="orchestration_disabled", state=TaskState.WAITING_INPUT)
        route = route_task(request, self.config)
        result = TaskResult(request.task_id, "blocked", route.name, specialization=request.specialization,
                            specialization_reason=request.specialization_reason)
        self.transition(result, TaskState.ROUTING)
        emit(self.settings, "route_decision", task_id=request.task_id, route=route.name, level=route.level)
        try:
            self._run_routes(request, route, result)
        except BudgetExceeded as exc:
            result.status = "cancelled" if str(exc) == "cancelled" else "blocked"
            result.reason = str(exc)
            self.transition(result, TaskState.CANCELLED if result.status == "cancelled" else TaskState.BUDGET_EXHAUSTED)
            emit(self.settings, "budget_exhausted", task_id=request.task_id, reason=result.reason)
        except ValueError as exc:
            # Config/permission/launch errors are blocked, never model-quality failures.
            result.status, result.reason = "blocked", str(exc)
        result.budget = self.budget.snapshot()
        if result.state not in {TaskState.BUDGET_EXHAUSTED, TaskState.CANCELLED}:
            self.transition(result, {"completed": TaskState.SUCCEEDED,
                                     "blocked": TaskState.WAITING_INPUT}.get(result.status, TaskState.FAILED))
        emit(self.settings, "task_completed" if result.status == "completed" else "task_failed",
             task_id=request.task_id, route=result.route, reason=result.reason,
             calls=result.budget.model_calls, escalations=result.budget.escalations)
        if self.settings["workspace"]["enabled"]:
            self.executor.record_result(result)
        return result

    def _run_routes(self, request, route, result):
        visited = {request.specialization}
        switches = 0
        while True:
            from .graph_runner import execute_graph
            execute_graph(self, request, route, result)
            if result.reason != "specialist_requested":
                return
            proposal = result.attempts[-1].evidence["specialist_request"]
            if proposal["category"] in visited:
                raise ValueError("specialist_cycle: inspect the requests before retrying")
            if switches >= self.settings["routing"]["max_specialist_switches"]:
                raise ValueError("specialist_switch_limit")
            request = reroute_request(request, proposal, self.config)
            route = route_task(request, self.config)
            visited.add(request.specialization)
            switches += 1
            result.route, result.reason = route.name, ""
            result.specialization, result.specialization_reason = request.specialization, request.specialization_reason
            emit(self.settings, "specialist_selected", task_id=request.task_id,
                 category=request.specialization, route=route.name, reason="task_specialization")

    def _run_profile(self, request, profile, has_next, result):
        repairs = 0
        while True:
            self.budget.attempt()
            context = render_handoff(build_handoff(request, result.attempts, self.budget))
            context += catalog_instructions(self.config)
            event = "repair_started" if repairs else "attempt_started"
            self.transition(result, TaskState.REPAIRING if repairs else TaskState.RUNNING)
            emit(self.settings, event, task_id=request.task_id, attempt=self.budget.snapshot().attempts, profile=profile.id)
            from .effects import retained_effects
            attempt = self.executor.execute(request, profile, context, self.budget,
                                            retained_effects=retained_effects(result.attempts))
            attempt.repair = repairs > 0
            previous = list(result.attempts)
            result.attempts.append(attempt)
            result.summary = attempt.summary
            emit(self.settings, "attempt_completed", task_id=request.task_id, attempt=attempt.number, profile=profile.id)
            if attempt.evidence.get("failure_reason") in {"attempt_model_calls", "max_model_calls"}:
                result.reason = "model_calls_continuation_not_approved"
                return "needs_input"
            if (attempt.evidence.get("failure_reason") in {"content_policy_blocked", "refused", "permission_denied"}
                    or attempt.summary.strip().startswith("ORCHESTRATION_REFUSED:")):
                result.reason = "refused: inspect the refusal; model size escalation cannot resolve permission or policy restrictions"
                return "needs_input"
            if attempt.evidence.get("failure_reason") in {"error", "timeout"}:
                result.reason = "executor_error: inspect diagnostics before retrying"
                return "needs_input"
            if attempt.evidence.get("failure_reason") in INFRASTRUCTURE_FAILURES:
                result.reason = attempt.evidence["failure_reason"]
                return "skip"
            proposal = requested_specialist(attempt)
            if proposal:
                attempt.evidence["specialist_request"] = proposal
                if attempt.evidence.get("uncertain_side_effects"):
                    result.reason = "uncertain_side_effects: inspect external state before specialist transfer"
                    return "needs_input"
                result.reason = "specialist_requested"
                return "specialist"
            self.transition(result, TaskState.VERIFYING)
            verification = self.verifier(request, attempt, previous, task_config(self.config, request),
                                         self.executor, self.budget, self.available)
            attempt.verification = verification
            emit(self.settings, "verification_" + ("passed" if verification.verdict == "pass" else "failed"),
                 task_id=request.task_id, attempt=attempt.number, profile=profile.id,
                 reason="; ".join(verification.reasons) if verification.reasons else verification.verdict)
            decision = decide(verification, self.settings, repairs, has_next)
            if decision.action == "repair" and has_next and self.budget.remaining()["attempts"] == 1:
                # Preserve the last attempt for a stronger profile instead of
                # consuming the entire route budget on same-profile repairs.
                decision = EscalationDecision("escalate", decision.reason)
            result.reason = decision.reason
            if decision.action in {"repair", "escalate"} and attempt.evidence.get("uncertain_side_effects"):
                result.reason = "uncertain_side_effects: inspect external state before retrying"
                return "needs_input"
            if decision.action != "repair":
                return decision.action
            repairs += 1
