"""Orchestration contracts. No clients, credentials or hidden reasoning live here."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

LEVELS = ("fast", "balanced", "deep")


class TaskState(str, Enum):
    CREATED = "CREATED"
    ROUTING = "ROUTING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    REPAIRING = "REPAIRING"
    ESCALATING = "ESCALATING"
    WAITING_INPUT = "WAITING_INPUT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ExecutionProfile:
    id: str
    enabled: bool
    provider: str
    model: str
    level: str = "fast"
    description: str = ""
    reasoning_effort: str | None = None
    priority: int = 0
    max_parallel: int = 1
    capabilities: dict[str, bool | str] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskRequest:
    goal: str
    context: str = ""
    route: str | None = None
    level: str = "auto"
    output_schema: dict | None = None
    images: tuple[str, ...] = ()
    task_id: str = field(default_factory=lambda: uuid4().hex)
    specialization: str | None = None
    specialization_reason: str = ""
    start_node: str | None = None
    start_reason: str = ""
    attachments: tuple[dict, ...] = ()
    visual_check: bool = False
    artifact_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskRoute:
    name: str
    level: str
    profiles: tuple[ExecutionProfile, ...]


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    reasons: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    suggested_action: str = "accept"


@dataclass
class TaskAttempt:
    number: int
    profile: str
    status: str = "running"
    summary: str = ""
    verification: VerificationResult | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    api_calls: int = 0
    repair: bool = False


@dataclass(frozen=True)
class EscalationDecision:
    action: str
    reason: str


@dataclass
class BudgetState:
    attempts: int = 0
    escalations: int = 0
    model_calls: int = 0


@dataclass
class HandoffContext:
    original_goal: str
    constraints: str = ""
    acceptance_criteria: dict | None = None
    verified_facts: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    previous_attempt_summary: str = ""
    artifacts: list[str] = field(default_factory=list)
    remaining_work: list[str] = field(default_factory=list)
    confirmed_side_effects: list[str] = field(default_factory=list)
    uncertain_side_effects: list[str] = field(default_factory=list)
    attempt_number: int = 0
    remaining_budget: dict = field(default_factory=dict)
    specialization: str | None = None
    specialization_reason: str = ""


@dataclass
class TaskResult:
    task_id: str
    status: str
    route: str = ""
    summary: str = ""
    reason: str = ""
    attempts: list[TaskAttempt] = field(default_factory=list)
    budget: BudgetState = field(default_factory=BudgetState)
    state: TaskState = TaskState.CREATED
    specialization: str | None = None
    specialization_reason: str = ""
