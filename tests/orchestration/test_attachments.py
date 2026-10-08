"""Attachment payloads survive automatic entry, planning, and child message construction."""

from types import SimpleNamespace
import json

import pytest

from agent.orchestration.attachments import child_message, turn_input
from agent.orchestration.tool import parse_request
from agent.orchestration.types import TaskAttempt, TaskRequest, VerificationResult


@pytest.mark.parametrize("part", [
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,YQ==", "detail": "high"}},
    {"type": "input_audio", "input_audio": {"data": "YQ==", "format": "wav"}},
    {"type": "file", "file": {"filename": "manual.pdf", "file_data": "data:application/pdf;base64,YQ=="}},
    {"type": "video_url", "video_url": {"url": "https://example.invalid/demo.mp4"}},
])
def test_structured_attachment_reaches_child_without_stringification(part):
    original = [{"type": "text", "text": "Inspect this attachment"}, part]
    state = SimpleNamespace(original_user_message=original, user_message=original)
    goal, images, attachments = turn_input(state)
    request = parse_request({"goal": goal, "images": images, "attachments": attachments})
    output = child_message("Worker goal with workspace note", request.attachments)
    assert goal == "Inspect this attachment"
    assert output == [{"type": "text", "text": "Worker goal with workspace note"}, part]
    output[1]["type"] = "changed"
    assert original[1] == part
    assert request.attachments[0] == part


def test_text_mode_images_and_expanded_files_survive_entry(tmp_path):
    image = str(tmp_path / "reference with spaces.png")
    original = f'Inspect @file:manual.pdf\n@image:"{image}"'
    admitted = original + "\n\n--- Attached Context ---\nAbsolute path: /uploads/manual.pdf\nmanual content"
    goal, images, attachments = turn_input(SimpleNamespace(
        original_user_message=original, user_message=admitted))
    assert images == [image]
    assert goal == original
    assert attachments == [{"type": "text", "text": admitted}]
    assert "manual content" in child_message("worker", attachments)[1]["text"]


def test_large_admitted_text_file_is_not_rejected_as_an_oversized_goal():
    prompt = "Summarize @file:notes.txt"
    expanded = prompt + "\n\n--- Attached Context ---\n" + "notes " * 4000
    goal, images, attachments = turn_input(SimpleNamespace(
        original_user_message=expanded, user_message=expanded))
    request = parse_request({"goal": goal, "images": images, "attachments": attachments})
    assert request.goal == prompt
    assert request.attachments[0]["text"] == expanded


def test_attachment_only_turn_has_a_valid_goal():
    message = [{"type": "input_audio", "input_audio": {"data": "YQ==", "format": "wav"}}]
    goal, images, attachments = turn_input(SimpleNamespace(
        original_user_message=message, user_message=message))
    request = parse_request({"goal": goal, "images": images, "attachments": attachments})
    assert request.goal == "Inspect the supplied attachments."
    assert list(request.attachments) == message


def test_planner_and_all_workers_receive_the_same_attachments():
    from agent.orchestration.planner import execute_plan
    from agent.orchestration.controller import OrchestrationController
    from agent.orchestration.availability import Availability
    from agent.orchestration.config import parse_config

    config = parse_config({"enabled": True, "profiles": {
        "worker": {"enabled": True, "provider": "openrouter", "model": "test", "capabilities": {"vision": True}}},
        "routes": {"general": ["worker"]}, "automation": {"planner_profile": "worker"},
        "verification": {"semantic": "off"}})
    seen = []

    class Executor:
        def execute(self, request, profile, context, budget, *, reviewer=False, retained_effects=()):
            seen.append(request)
            plan = {"architecture": "Inspect supplied files", "execution": "staged",
                    "decomposition_reason": "Two independent deliverables", "tasks": [
                        {"id": name, "goal": "Inspect attachment", "acceptance": "Explain it"}
                        for name in ("first", "second")]}
            return TaskAttempt(budget.snapshot().attempts, profile.id, "completed",
                               json.dumps(plan) if reviewer else "done")

    controller = OrchestrationController(config, Executor(), availability=lambda *_: Availability(True),
        verifier=lambda *_: VerificationResult("pass"))
    request = TaskRequest("Inspect", images=("https://example.invalid/photo.png",), attachments=(
        {"type": "file", "file": {"filename": "manual.pdf", "file_data": "YQ=="}},
        {"type": "input_audio", "input_audio": {"data": "Yg==", "format": "wav"}},))
    assert execute_plan(request, controller)["status"] == "completed"
    assert len(seen) == 3
    assert all(r.images == request.images and r.attachments == request.attachments for r in seen)


@pytest.mark.parametrize("value", ["file.pdf", ["file.pdf"], [{}], [{"type": None}]])
def test_malformed_attachments_are_rejected_before_launch(value):
    with pytest.raises(ValueError, match="typed message content"):
        parse_request({"goal": "Inspect", "attachments": value})
