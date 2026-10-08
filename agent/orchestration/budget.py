"""One atomic ledger for executor, repair and reviewer API requests."""

from dataclasses import asdict, replace
import threading
import time

from .types import BudgetState


class BudgetExceeded(RuntimeError):
    pass


class BudgetLedger:
    def __init__(self, limits, *, clock=time.monotonic):
        self.limits = dict(limits)
        self.state = BudgetState()
        self.clock = clock
        self.deadline = clock() + limits["timeout_seconds"]
        self.cancelled = threading.Event()
        self.awaiting_input = threading.Event()
        self.lock = threading.RLock()
        self.blocked_reason = ""

    def check(self):
        if self.cancelled.is_set():
            raise BudgetExceeded("cancelled")
        if not self.awaiting_input.is_set() and self.clock() >= self.deadline:
            raise BudgetExceeded("timeout_seconds")

    def charge(self, field, limit):
        with self.lock:
            self.check()
            if getattr(self.state, field) >= self.limits[limit]:
                self.blocked_reason = limit
                raise BudgetExceeded(limit)
            setattr(self.state, field, getattr(self.state, field) + 1)

    def before_request(self, agent):
        self.charge("model_calls", "max_model_calls")

    def attempt(self):
        self.charge("attempts", "max_attempts")

    def escalate(self):
        self.charge("escalations", "max_escalations")

    def snapshot(self):
        with self.lock:
            return replace(self.state)

    def remaining(self):
        with self.lock:
            return {name: self.limits[f"max_{name}"] - value for name, value in asdict(self.state).items()}
