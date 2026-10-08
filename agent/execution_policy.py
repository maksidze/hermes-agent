"""Optional request policy inherited by Hermes worker contexts."""

from contextlib import contextmanager
from contextvars import ContextVar

current_policy = ContextVar("hermes_execution_policy", default=None)


@contextmanager
def execution_scope(policy):
    token = current_policy.set(policy)
    try:
        yield
    finally:
        current_policy.reset(token)
