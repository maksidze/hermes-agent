"""Durable public history and run isolation, including late child callbacks."""

import json
from pathlib import Path
from types import SimpleNamespace

from agent.orchestration.progress import RunProgress, display_result, observe_tools, publish


def test_progress_is_run_scoped_durable_and_independent_of_logging():
    from agent.orchestration.config import DEFAULTS
    from agent.orchestration.events import emit
    from tools.approval_context import _approval_tool_call_id
    delivered = []
    parent = SimpleNamespace(tool_progress_callback=lambda *a, **kw: delivered.append(kw))
    child = SimpleNamespace(tool_start_callback=None, tool_complete_callback=None)
    token = _approval_tool_call_id.set("parent-call")
    try:
        with RunProgress(parent) as outer:
            observe_tools(child, SimpleNamespace(id="fast", model="small"), "task")
            emit({**DEFAULTS, "logging": dict.fromkeys(DEFAULTS["logging"], False)}, "planning_started", profile="deep")
            child.tool_start_callback("child-call", "write_file", {"path": "site/index.html", "content": "private file body"})
            with RunProgress(parent) as inner:
                publish("plan_task_started", detail="Other run")
            publish("run_completed", status="blocked", detail="max_model_calls")
            output = outer.attach({"status": "blocked"})
        child.tool_start_callback("late", "write_file", {"path": "must-not-arrive"})
    finally:
        _approval_tool_call_id.reset(token)
    saved = [json.loads(line) for line in Path(output["progress_journal"]).read_text(encoding="utf-8").splitlines()]
    assert len(saved) == len(output["timeline"]) == 3
    assert saved[1]["detail"] == "write_file: site/index.html"
    assert inner.entries[0]["detail"] == "Other run"
    assert delivered[-1]["tool_id"] == "parent-call"
    assert delivered[-1]["entries"] == saved
    assert display_result(json.dumps({**output, "huge_private_evidence": "excluded"})) == output


def test_mcp_images_reach_durable_progress_without_base64_or_arbitrary_files(tmp_path):
    from gateway.platforms.base import get_image_cache_dir
    root = Path(get_image_cache_dir())
    root.mkdir(parents=True, exist_ok=True)
    image = root / "preview with spaces.png"
    image.write_bytes(b"cached preview")
    outside = tmp_path / "private.png"
    outside.write_bytes(b"private")
    child = SimpleNamespace(tool_start_callback=None, tool_complete_callback=None)
    with RunProgress(SimpleNamespace()) as progress:
        observe_tools(child, SimpleNamespace(id="worker", model="model"), "task")
        child.tool_complete_callback("call", "mcp__editor__preview", {}, json.dumps({"result": f"MEDIA:{image}\nMEDIA:{outside}"}))
        output = progress.attach({"status": "completed"})
    assert len(output["timeline"]) == 1
    assert output["timeline"][0]["fields"]["image_path"] == str(image)
    assert json.loads(progress.path.read_text(encoding="utf-8")) == output["timeline"][0]
