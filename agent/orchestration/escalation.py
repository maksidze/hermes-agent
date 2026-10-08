"""Policy for repairs and capability escalation, independent of provider fallback."""

from .types import EscalationDecision

_TRIGGERS = {"schema_failed": "schema_failed", "repetition_detected": "repetition_detected",
             "same_failure_repeated": "repetition_detected", "tool_loop_detected": "repetition_detected",
             "executor_requested_escalation": "explicit_request"}


def decide(verification, settings, repairs, has_next):
    reason = verification.reasons[0] if verification.reasons else "passed" if verification.verdict == "pass" else "verification_failed"
    action = verification.suggested_action
    if verification.verdict == "uncertain":
        action = settings["verification"]["uncertain_action"]
    if verification.verdict == "pass" or action == "accept":
        return EscalationDecision("accept", reason)
    if action == "needs_input":
        return EscalationDecision("needs_input", reason)
    policy = settings["escalation"]
    trigger = _TRIGGERS.get(reason, "verification_failed")
    if not policy["enabled"] or not policy["triggers"][trigger]:
        return EscalationDecision("fail", reason)
    if action == "repair" and repairs < policy["same_profile_repairs"]:
        return EscalationDecision("repair", reason)
    return EscalationDecision("escalate" if has_next else "fail", reason)
