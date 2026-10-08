"""Bounded in-memory diagnostics per Hermes home; metadata only, no task content."""

from collections import deque
import logging
import threading
import time

logger = logging.getLogger("hermes.orchestration")
_EVENTS = {}
_LOCK = threading.Lock()
_FIELDS = {"task_id", "attempt", "route", "level", "profile", "provider", "model", "reason", "calls", "escalations", "state", "category", "node", "target"}


def emit(settings, event, **fields):
    from hermes_constants import hermes_home_key
    from .progress import publish
    publish(event, **fields)
    group = "verification" if event.startswith("verification_") else "attempts" if event.startswith("attempt_") else "decisions"
    if not settings["logging"][group]:
        return
    value = {"event": event, "time": time.time(), **{k: v for k, v in fields.items() if k in _FIELDS}}
    with _LOCK:
        _EVENTS.setdefault(hermes_home_key(), deque(maxlen=100)).append(value)
    logger.info("%s", value)


def diagnostics():
    from hermes_constants import hermes_home_key
    with _LOCK:
        return list(_EVENTS.get(hermes_home_key(), ()))
