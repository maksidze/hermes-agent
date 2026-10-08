"""Run-scoped public activity, streamed to the owning chat and retained on disk."""

from contextvars import ContextVar
import json
import logging
from pathlib import Path
import threading
import time
from uuid import uuid4

_CURRENT = ContextVar("orchestration_progress", default=None)
logger = logging.getLogger(__name__)


def publish(event, **fields):
    progress = _CURRENT.get()
    if progress is not None:
        progress.append(event, **fields)


def display_result(result):
    """Keep the UI history even when large tool evidence is spilled to a file."""
    try:
        output = json.loads(result)
    except (ValueError, TypeError):
        return {"status": "blocked", "reason": str(result)}
    if not isinstance(output, dict):
        return {}
    return {key: output[key] for key in ("status", "reason", "timeline", "progress_journal") if key in output}


class RunProgress:
    def __init__(self, parent):
        from hermes_constants import get_hermes_home
        from tools.approval_context import _approval_tool_call_id
        self.callback = getattr(parent, "tool_progress_callback", None)
        self.tool_id = _approval_tool_call_id.get() or ""
        self.path = Path(get_hermes_home()) / "orchestration" / "progress" / (uuid4().hex + ".jsonl")
        self.entries = []
        self.lock = threading.RLock()
        self.active = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.active = True
        self.token = _CURRENT.set(self)
        return self

    def __exit__(self, *_exc):
        with self.lock:
            self.active = False
        _CURRENT.reset(self.token)

    def append(self, event, **fields):
        with self.lock:
            if not self.active:
                return
            entry = {"event": event, "time": time.time(), "detail": str(fields.pop("detail", ""))[:6000],
                     "fields": {k: str(v)[:1500] for k, v in fields.items() if v is not None}}
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.entries.append(entry)
            self.entries = self.entries[-500:]
            if self.callback and self.tool_id:
                # A detached UI must never abort the writer or its checkpointing.
                try:
                    self.callback("orchestration.progress", "orchestrate_task", None,
                                  tool_id=self.tool_id, entries=list(self.entries), journal=str(self.path))
                except Exception:
                    logger.warning("Could not deliver orchestration progress", exc_info=True)

    def attach(self, output):
        output.update(timeline=list(self.entries), progress_journal=str(self.path))
        return output


def observe_tools(child, profile, task_id):
    """Public tool actions only; never mirror private reasoning/token streams."""
    progress = _CURRENT.get()
    if progress is None:
        return
    original = child.tool_start_callback

    def started(call_id, name, args):
        if original:
            original(call_id, name, args)
        detail = str(args.get("path") or args.get("command") or args.get("query") or "")[:1000]
        progress.append("tool_started", profile=profile.id, model=profile.model,
                        task_id=task_id, detail=f"{name}: {detail}" if detail else name)

    child.tool_start_callback = started
    original_complete = child.tool_complete_callback

    def completed(call_id, name, args, result):
        if original_complete:
            original_complete(call_id, name, args, result)
        if name.startswith("mcp__"):
            from .media_evidence import cached_image_paths
            for path in cached_image_paths(result):
                progress.append("tool_image", profile=profile.id, task_id=task_id,
                                detail=name, image_path=path)

    child.tool_complete_callback = completed
