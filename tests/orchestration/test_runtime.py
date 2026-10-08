"""End-to-end provider resolution and lifecycle against a local OpenAI-wire server."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading

import pytest


@pytest.fixture
def endpoint():
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def reply(self, payload, content_type="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.reply({"data": [{"id": "local-fast"}, {"id": "local-deep"}, {"id": "local-balanced"}]})

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path != "/v1/chat/completions":
                self.send_error(404)
                return
            requests.append(data)
            answer = '{"ok": true}'
            probe = any(t.get("function", {}).get("name") == "profile_probe_ping" for t in data.get("tools", []))
            has_tool_result = any(m.get("role") == "tool" for m in data["messages"])
            if probe:
                answer = "PROFILE_OK"
            last_user = next(str(m.get("content", "")) for m in reversed(data["messages"]) if m["role"] == "user")
            if "Design an architecture and an executable" in last_user:
                answer = json.dumps({"architecture": "A tiny module", "tasks": [{"id": "implementation",
                    "goal": "Describe the module", "level": "fast", "acceptance": "Explain the result"}]})
            elif "Review the candidate against the goal and evidence" in last_user:
                answer = '{"verdict": "pass", "reasons": ["candidate satisfies acceptance"]}'
            elif "SPECIALIST_TRANSFER_PROBE" in last_user and data["model"] == "local-deep":
                answer = 'ORCHESTRATION_SPECIALIST: {"category":"roleplay","reason":"Character dialogue expertise"}'
            result = {"id": "orchestration-test", "created": 1, "model": data["model"], "object": "chat.completion",
                      "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
                      "usage": {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25}}
            if probe and not has_tool_result:
                result["choices"][0].update(message={"role": "assistant", "content": None, "tool_calls": [
                    {"id": "probe-1", "type": "function", "function": {"name": "profile_probe_ping", "arguments": "{}"}}]},
                    finish_reason="tool_calls")
            continue_probe = "CONTINUATION_PROBE" in last_user and sum(m["role"] == "tool" for m in data["messages"]) < 2
            if ("ATTEMPT_LIMIT_PROBE" in last_user or continue_probe) and data["model"] == "local-fast":
                result["choices"][0].update(message={"role": "assistant", "content": None, "tool_calls": [
                    {"id": "read-" + str(len(requests)), "type": "function", "function": {"name": "read_file",
                     "arguments": json.dumps({"path": "missing-probe-" + str(len(requests)) + ".txt"})}}]},
                    finish_reason="tool_calls")
            target = re.search(r"BOUNDARY_TARGET=(.+)", last_user)
            if target and not has_tool_result:
                result["choices"][0].update(message={"role": "assistant", "content": None, "tool_calls": [
                    {"id": "write-1", "type": "function", "function": {"name": "write_file",
                     "arguments": json.dumps({"path": json.loads(target[1]), "content": "safe test"})}}]},
                    finish_reason="tool_calls")
            if data.get("stream"):
                result["object"] = "chat.completion.chunk"
                result["choices"][0]["delta"] = result["choices"][0].pop("message")
                for call in result["choices"][0]["delta"].get("tool_calls", []):
                    call["index"] = 0
                self.reply(f"data: {json.dumps(result)}\n\ndata: [DONE]\n\n".encode(), "text/event-stream")
            else:
                self.reply(result)

        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize("background, specialist", [(False, False), (True, False), (False, True)])
def test_real_runtime_lifecycle_and_tool_registration(endpoint, monkeypatch, background, specialist):
    from hermes_cli.config import save_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from agent.orchestration.config import load_config
    from agent.orchestration.availability import check_profile
    from agent.orchestration.tool import run_tasks
    from run_agent import AIAgent
    from tools import orchestration_tool
    url, requests = endpoint
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    save_config({
        "providers": {"orchestration-local": {"base_url": url, "key_env": "OPENAI_API_KEY", "transport": "chat_completions"}},
        "model": {"provider": "custom:orchestration-local", "default": "local-fast", "base_url": url, "context_length": 128000},
        "orchestration": {"enabled": True, "privacy": {"cloud_allowed": False}, "verification": {"semantic": "off"},
                          "profiles": {"local": {"enabled": True, "provider": "custom:orchestration-local",
                                                  "model": "local-fast", "level": "fast", "reasoning_effort": "low"},
                                       "architect": {"enabled": True, "provider": "custom:orchestration-local",
                                                  "model": "local-deep", "level": "deep", "reasoning_effort": "low"}},
                          "routes": {"general": ["local", "architect"], "dialogue": ["local"]},
                          "specializations": {"roleplay": {"enabled": True, "description": "Character dialogue",
                                                              "local_only": False, "route": "dialogue"}}},
    })
    config = load_config()
    runtime = resolve_runtime_provider(requested="custom:orchestration-local", target_model="local-fast")
    assert runtime["base_url"].rstrip("/") == url
    assert check_profile(config.profiles["local"], config.settings["availability"]).available
    assert orchestration_tool.check_requirements()
    parent = AIAgent(model="local-fast", provider=runtime["provider"], requested_provider="custom:orchestration-local",
                     api_key=runtime["api_key"], base_url=url, api_mode="chat_completions", enabled_toolsets=[],
                     quiet_mode=True, skip_memory=True, skip_context_files=True, save_trajectories=False)
    try:
        output = run_tasks({"goal": "SPECIALIST_TRANSFER_PROBE Write dialogue" if specialist else "Return the requested JSON",
                            "level": "deep" if specialist else "fast", "background": background,
                            "output_schema": {"type": "object", "required": ["ok"]}}, parent)
        if background:
            from tools.process_registry import process_registry
            assert output["status"] == "dispatched"
            dispatched = output["delegation_id"]
            output = process_registry.completion_queue.get(timeout=30)
            assert output["delegation_id"] == dispatched
            assert output["parent_session_id"] == parent.session_id
        assert output["results"][0]["status"] == "completed", output
        assert [r["model"] for r in requests] == (["local-deep", "local-fast"] if specialist else ["local-fast"])
        assert requests[0].get("reasoning_effort") == "low"
        assert output["results"][0]["budget"]["model_calls"] == len(requests)
        if specialist:
            result = output["results"][0]
            assert result["specialization"] == "roleplay"
            assert result["budget"]["escalations"] == 0
            assert result["attempts"][0]["evidence"]["specialist_request"]["reason"] == "Character dialogue expertise"
        assert all(tool["function"]["name"] != "orchestrate_task" for tool in requests[0].get("tools", []))
    finally:
        parent.close()
        if background:
            from tools.async_delegation import _reset_for_tests
            _reset_for_tests()


def test_live_switch_uses_every_message_without_changing_cached_tools(endpoint, monkeypatch):
    from copy import deepcopy
    from hermes_cli.config import save_config
    from run_agent import AIAgent
    url, requests = endpoint
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    provider = "custom:orchestration-local"
    save_config({
        "providers": {"orchestration-local": {"base_url": url, "key_env": "OPENAI_API_KEY", "transport": "chat_completions"}},
        "model": {"provider": provider, "default": "local-fast", "base_url": url, "context_length": 128000},
        "orchestration": {"enabled": False, "automation": {"mode": "manual"},
            "verification": {"verifier_profile": "balanced"},
            "profiles": {level: {"enabled": True, "provider": provider, "model": "local-" + level, "level": level}
                         for level in ("fast", "balanced", "deep")},
            "routes": {"general": ["fast", "balanced", "deep"]}},
    })
    parent = AIAgent(model="local-fast", provider=provider, requested_provider=provider, api_key="local-test-key",
                     base_url=url, api_mode="chat_completions", enabled_toolsets=[], quiet_mode=True,
                     skip_memory=True, skip_context_files=True, save_trajectories=False, max_iterations=5)
    before = deepcopy(parent.tools)
    try:
        first = parent.run_conversation("Привет")
        assert [r["model"] for r in requests] == ["local-fast"]
        assert "orchestrate_task" not in parent.valid_tool_names
        save_config({"orchestration": {"enabled": True}}, merge_existing=True)
        second = parent.run_conversation("Продолжай", conversation_history=first["messages"])
        assert [r["model"] for r in requests] == ["local-fast", "local-deep", "local-fast", "local-balanced"]
        assert "Оркестрация завершена" in second["final_response"]
        assert parent.tools == before
        assert "orchestrate_task" not in parent.valid_tool_names
        save_config({"orchestration": {"enabled": False}}, merge_existing=True)
        parent.run_conversation("Создай страницу", conversation_history=second["messages"])
        assert len(requests) == 5
        assert requests[-1]["model"] == "local-fast"
        save_config({"orchestration": {"enabled": True}}, merge_existing=True)
        parent._turn_origin = "background_review"
        parent.run_conversation("Review session skills")
        assert len(requests) == 6
        assert requests[-1]["model"] == "local-fast"
    finally:
        parent.close()


@pytest.mark.parametrize("outside", [False, True])
def test_real_tool_dispatch_confines_orchestration_file_writes(endpoint, tmp_path, outside):
    from agent.orchestration.budget import BudgetLedger
    from agent.orchestration.config import DEFAULTS
    from agent.orchestration.executor import ExecutionPolicy
    from agent.orchestration.types import TaskRequest
    from run_agent import AIAgent
    from tools.terminal_tool import record_session_cwd
    url, requests = endpoint
    worktree = tmp_path / "isolated"
    worktree.mkdir()
    destination = (tmp_path if outside else worktree) / "proof.txt"
    task_id = "orchestration-boundary-" + str(outside)
    record_session_cwd(task_id, str(worktree))
    child = AIAgent(model="local-fast", provider="custom", api_key="test", base_url=url, api_mode="chat_completions",
                    enabled_toolsets=["file"], quiet_mode=True, skip_memory=True, skip_context_files=True,
                    save_trajectories=False, max_iterations=3)
    policy = ExecutionPolicy(BudgetLedger(DEFAULTS["budget"]), TaskRequest("test"), False,
                             {"worktree": {"path": str(worktree)}})
    policy.configure(child)
    try:
        result = child.run_conversation("Write a file.\nBOUNDARY_TARGET=" + json.dumps(str(destination)), task_id=task_id)
        assert destination.exists() is not outside
        assert len(requests) == 2
        rows = [m for m in result["messages"] if m.get("role") == "tool"]
        if outside:
            assert "outside orchestration worktree blocked" in rows[0]["content"]
        else:
            assert destination.read_text() == "safe test"
    finally:
        child.close()


def test_profile_probe_performs_only_harmless_tool_call(endpoint, monkeypatch):
    from agent.orchestration.diagnostics import test_profile
    from hermes_cli.config import save_config
    url, requests = endpoint
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    save_config({
        "providers": {"orchestration-local": {"base_url": url, "key_env": "OPENAI_API_KEY", "transport": "chat_completions"}},
        "model": {"provider": "custom:orchestration-local", "default": "local-fast", "base_url": url, "context_length": 128000},
        "orchestration": {"privacy": {"cloud_allowed": False}, "profiles": {
            "local": {"enabled": True, "provider": "custom:orchestration-local", "model": "local-fast", "level": "fast"},
            "missing": {"enabled": True, "provider": "custom:orchestration-local", "model": "not-installed", "level": "fast"},
        }},
    })
    assert test_profile("missing")["status"] == "model_not_found"
    assert not requests
    result = test_profile("local")
    assert result == {"status": "available", "model_calls": 2}
    assert len(requests) == 2
    assert {tool["function"]["name"] for tool in requests[0]["tools"]} == {"profile_probe_ping"}
    assert any(m.get("role") == "tool" for m in requests[1]["messages"])


@pytest.mark.parametrize("graph", [False, True])
@pytest.mark.parametrize("approve", [False, True])
def test_worker_asks_before_continuing_same_session(endpoint, monkeypatch, graph, approve):
    from hermes_cli.config import save_config
    from agent.orchestration.tool import run_tasks
    from run_agent import AIAgent
    url, requests = endpoint
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    provider = "custom:orchestration-local"
    save_config({"providers": {"orchestration-local": {"base_url": url, "key_env": "OPENAI_API_KEY",
        "transport": "chat_completions"}}, "orchestration": {"enabled": True,
        "budget": {"max_model_calls": 8, "max_calls_per_attempt": 2}, "verification": {"semantic": "off"},
        "profiles": {level: {"enabled": True, "provider": provider, "model": "local-" + level, "level": level}
                     for level in ("fast", "balanced")}, "routes": {"general": ["fast", "balanced"]},
        "graphs": {"general": {"entry": "start", "nodes": [{"id": "start", "profiles": ["fast"]},
                    {"id": "continue", "profiles": ["balanced"]}],
                    "edges": [{"source": "start", "target": "continue", "on": "failure"}]}} if graph else {}}})
    parent = AIAgent(model="local-fast", provider=provider, requested_provider=provider, api_key="local-test-key",
                     base_url=url, api_mode="chat_completions", enabled_toolsets=["file"], quiet_mode=True,
                     skip_memory=True, skip_context_files=True, save_trajectories=False)
    questions = []
    def consent(items):
        questions.append(items)
        assert len(requests) == 2
        return {"outcome": "submitted", "answers": {"q0": "Продолжить" if approve else "Остановить"}}
    parent.clarify_callback = consent
    try:
        output = run_tasks({"goal": "CONTINUATION_PROBE", "output_schema": {"type": "object", "required": ["ok"]}}, parent)
        result = output["results"][0]
        assert len(questions) == 1
        assert result["status"] == ("completed" if approve else "blocked"), result
        assert [r["model"] for r in requests] == ["local-fast"] * (3 if approve else 2)
        assert result["budget"]["model_calls"] == (3 if approve else 2)
        assert result["attempts"][0]["api_calls"] == (3 if approve else 2)
        assert len(result["attempts"]) == 1
        if approve:
            assert requests[0]["messages"][0] == requests[-1]["messages"][0]
            assert sum(m["role"] == "tool" for m in requests[-1]["messages"]) == 2
        else:
            assert result["reason"] == "model_calls_continuation_not_approved"
        assert [row["tool"] for row in result["attempts"][0]["evidence"]["tool_results"]] == ["read_file", "read_file"]
    finally:
        parent.close()


@pytest.mark.parametrize("max_calls, category", [(1, False), (10, False), (10, True)])
def test_normal_user_turn_automatically_plans_executes_and_reviews(endpoint, monkeypatch, max_calls, category):
    from hermes_cli.config import save_config
    from run_agent import AIAgent
    from pathlib import Path
    # The orchestration owns its deadline, not the ordinary tool's deadline.
    monkeypatch.setattr("agent.tool_executor._resolve_sequential_tool_timeout", lambda: 0.000001)
    progress = []
    url, requests = endpoint
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    provider = "custom:orchestration-local"
    save_config({
        "providers": {"orchestration-local": {"base_url": url, "key_env": "OPENAI_API_KEY", "transport": "chat_completions"}},
        "model": {"provider": provider, "default": "local-fast", "base_url": url, "context_length": 128000},
        "orchestration": {"enabled": True, "privacy": {"cloud_allowed": category},
            "budget": {"max_model_calls": max_calls},
            "automation": {"mode": "manual" if category else "development", "planner_profile": "deep"},
            "specializations": {"local_private": {"enabled": True, "route": "specialist", "local_only": True,
                "description": "Local analysis", "isolate_workspace": False}} if category else {},
            "workspace": {"enabled": category},
            "verification": {"verifier_profile": "balanced"},
            "profiles": {level: {"enabled": True, "provider": provider, "model": "local-" + level, "level": level}
                         for level in ("fast", "balanced", "deep")},
            "routes": {"general": ["fast", "balanced", "deep"], "specialist": ["fast"]}},
    })
    parent = AIAgent(model="local-fast", provider=provider, requested_provider=provider, api_key="local-test-key",
                     base_url=url, api_mode="chat_completions", enabled_toolsets=["orchestration"], quiet_mode=True,
                     skip_memory=True, skip_context_files=True, save_trajectories=False, max_iterations=5)
    parent.tool_progress_callback = lambda event, *args, **kw: progress.append((event, kw))
    try:
        result = parent.run_conversation("@local_private Обсуди сюжет" if category else
                                        "Создай страницу с 3D кубик-рубика. Используй HTML и JS и tree.js")
        expected = ["local-deep"] if max_calls == 1 else ["local-deep", "local-fast", "local-balanced"]
        if category:
            expected = ["local-fast"] * 3
        assert [r["model"] for r in requests] == expected, result
        rows = [m for m in result["messages"] if m.get("role") == "tool"]
        output = json.loads(rows[0]["content"])
        assert output["status"] == ("blocked" if max_calls == 1 else "completed"), output
        assert output["budget"]["model_calls"] == len(expected)
        if max_calls > 1:
            assert output["results"][0]["attempts"][0]["verification"]["verdict"] == "pass"
        assert len(rows) == 1
        frames = [kw for event, kw in progress if event == "orchestration.progress"]
        assert frames
        assert {frame["tool_id"] for frame in frames} == {rows[0]["tool_call_id"]}
        assert frames[-1]["entries"] == output["timeline"]
        saved = [json.loads(line) for line in Path(output["progress_journal"]).read_text(encoding="utf-8").splitlines()]
        assert saved == output["timeline"]
        assert saved[-1]["fields"]["status"] == output["status"]
        if category:
            assert output["results"][0]["specialization"] == "local_private"
            assert "@local_private" in result["final_response"]
        assert all(t["function"]["name"] != "orchestrate_task" for r in requests[:3] for t in r.get("tools", []))
    finally:
        parent.close()


@pytest.mark.parametrize("referenced", [False, True])
def test_automatic_attachments_reach_architect_and_worker_on_wire(endpoint, monkeypatch, tmp_path, referenced):
    from hermes_cli.config import save_config
    from run_agent import AIAgent

    url, requests = endpoint
    provider = "custom:orchestration-local"
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    save_config({
        "providers": {"orchestration-local": {"base_url": url, "key_env": "OPENAI_API_KEY",
                                              "transport": "chat_completions"}},
        "model": {"provider": provider, "default": "local-fast", "context_length": 128000,
                  "supports_vision": True},
        "orchestration": {"enabled": True, "privacy": {"cloud_allowed": False},
            "automation": {"mode": "development", "planner_profile": "deep"},
            "verification": {"verifier_profile": "deep"},
            "profiles": {level: {"enabled": True, "provider": provider, "model": "local-" + level,
                                  "level": level, "capabilities": {"vision": True}}
                         for level in ("fast", "deep")},
            "routes": {"general": ["fast", "deep"]}},
    })
    media = [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,YQ=="}},
        {"type": "input_audio", "input_audio": {"data": "Yg==", "format": "wav"}},
        {"type": "file", "file": {"filename": "manual.pdf", "file_data": "data:application/pdf;base64,Yw=="}},
        {"type": "video_url", "video_url": {"url": "https://example.invalid/demo.mp4"}},
    ]
    message = [{"type": "text", "text": "Describe all supplied attachments"}, *media]
    persisted = None
    if referenced:
        from PIL import Image
        from agent.context_references import preprocess_context_references, format_reference_value
        image = tmp_path / "reference image.png"
        Image.new("RGB", (2, 2), "red").save(image)
        notes = tmp_path / "notes.txt"
        notes.write_text("Attachment content survives planning.", encoding="utf-8")
        files = [tmp_path / name for name in ("manual.pdf", "recording.wav", "demo.mp4")]
        for path in files:
            path.write_bytes(b"\x00\x01binary attachment")
        prompt = "Describe all supplied attachments " + " ".join(
            f"@file:{format_reference_value(str(path))}" for path in [notes, *files])
        message = preprocess_context_references(
            prompt, cwd=tmp_path, allowed_root=tmp_path, context_length=128000).message
        persisted = message + f"\n@image:{format_reference_value(str(image))}"
    parent = AIAgent(model="local-fast", provider=provider, requested_provider=provider,
        api_key="local-test-key", base_url=url, api_mode="chat_completions",
        enabled_toolsets=["orchestration"], quiet_mode=True, skip_memory=True,
        skip_context_files=True, save_trajectories=False, max_iterations=5)
    try:
        result = parent.run_conversation(message, persist_user_message=persisted)
        output = json.loads(next(m["content"] for m in result["messages"] if m.get("role") == "tool"))
        assert output["status"] == "completed", output
        assert [r["model"] for r in requests] == ["local-deep", "local-fast", "local-deep"]
        for request in requests:
            user = next(m["content"] for m in reversed(request["messages"]) if m["role"] == "user")
            assert isinstance(user, list)
            if referenced:
                assert any(p["type"] == "image_url" for p in user)
                text = "\n".join(p["text"] for p in user if p["type"] == "text")
                assert "Attachment content survives planning." in text
                assert all(str(path) in text for path in files)
            else:
                assert [p for p in user if p["type"] != "text"] == media
    finally:
        parent.close()
