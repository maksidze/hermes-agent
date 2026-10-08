"""Orchestration activity survives hidden tool chrome and result offloading."""

import json


def test_scoped_progress_and_durable_completion_metadata(monkeypatch):
    import tui_gateway.server as server
    from tui_gateway.contracts.registry import check_payload
    entries = [{"event": "verification_failed", "time": 1.0, "detail": "Missing module",
                "fields": {"profile": "fast"}}]
    frames = []
    monkeypatch.setitem(server._sessions, "owner", {"tool_progress_mode": "off"})
    monkeypatch.setattr(server, "_emit", lambda kind, sid, payload: frames.append((kind, sid, payload)))
    server._on_tool_progress("owner", "orchestration.progress", "orchestrate_task", None,
                             tool_id="call-1", entries=entries, journal="D:/test/progress.jsonl")
    kind, sid, payload = frames[-1]
    assert sid == "owner"
    check_payload(kind, payload)
    assert payload["entries"] == entries

    output = {"status": "blocked", "reason": "max_model_calls", "timeline": entries,
              "progress_journal": "D:/test/progress.jsonl", "results": [{"evidence": "large" * 10000}]}
    prepared = server._prepare_tool_result_metadata("owner", "call-1", "orchestrate_task", {}, json.dumps(output))
    assert "results" not in prepared["tool_result_metadata"]["orchestration"]
    assert prepared["tool_result_metadata"]["orchestration"]["timeline"] == entries
    monkeypatch.setattr(server, "_emit_tool_lifecycle",
                        lambda kind, sid, name, args, payload: frames.append((kind, sid, payload)))
    server._on_tool_complete("owner", "call-1", "orchestrate_task", {}, json.dumps(output))
    kind, sid, payload = frames[-1]
    assert kind == "tool.complete" and sid == "owner"
    check_payload(kind, payload)
    assert payload["orchestration"] == prepared["tool_result_metadata"]["orchestration"]
