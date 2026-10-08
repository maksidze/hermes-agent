"""Fresh candidate media and actual output files, independent of the external application."""

import base64
import json
from types import SimpleNamespace

from agent.orchestration.budget import BudgetLedger
from agent.orchestration.config import DEFAULTS
from agent.orchestration.handoff import capture_evidence
from agent.orchestration.media_evidence import result_images
from agent.orchestration.types import TaskAttempt, TaskRequest
from agent.orchestration.verifier import deterministic, verify
from tests.orchestration.test_controller import configuration


def test_latest_external_write_invalidates_old_preview():
    image = {"type": "image_url", "image_url": {"url": "data:image/png;base64,TEST"}}
    messages = [
        {"role": "tool", "tool_name": "mcp__studio__preview", "content": [image]},
        {"role": "tool", "tool_name": "mcp__studio__edit", "content": '{"result":"changed"}'}
    ]
    attempt = TaskAttempt(1, "worker", "completed", "done", evidence=capture_evidence(SimpleNamespace(_session_messages=messages), {}))
    request = TaskRequest("Reproduce the reference", attachments=(image,), visual_check=True)
    assert deterministic(request, attempt).reasons == ("visual_evidence_missing_after_final_edit",)
    messages.append({"role": "tool", "tool_name": "mcp__studio__preview", "content": [image]})
    assert capture_evidence(SimpleNamespace(_session_messages=messages), {})["visual_evidence"] == [image]


def test_mcp_cached_image_is_reviewable_but_arbitrary_local_paths_are_not(tmp_path):
    from gateway.platforms.base import cache_image_from_bytes
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    path = cache_image_from_bytes(png, ext=".png")
    assert result_images(json.dumps({"result": "MEDIA:" + path + "\nPreview complete"}))[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert result_images("MEDIA:" + str(tmp_path / "private.png")) == []


def test_reviewer_sees_reference_and_candidate_even_when_code_checks_pass():
    reference = {"type": "image_url", "image_url": {"url": "data:image/png;base64,REFERENCE"}}
    candidate = {"type": "image_url", "image_url": {"url": "data:image/png;base64,CANDIDATE"}}
    request = TaskRequest("Reproduce reference", attachments=(reference,), visual_check=True)
    attempt = TaskAttempt(1, "worker", "completed", "done", evidence={
        "visual_evidence": [candidate], "verification": {"status": "passed"}})
    config = configuration(verification={"semantic": "risk_based", "verifier_profile": "deep"})
    class Reviewer:
        def execute(self, request, *args, **kwargs):
            assert reference in request.attachments and candidate in request.attachments
            return TaskAttempt(2, "reviewer", "completed", '{"verdict":"fail","reasons":["wrong proportions"]}')
    result = verify(request, attempt, [], config, Reviewer(), BudgetLedger(DEFAULTS["budget"]), lambda *a, **k: True)
    assert result.verdict == "fail"
    assert "wrong proportions" in result.reasons


def test_claimed_save_outside_workspace_is_not_accepted(tmp_path):
    request = TaskRequest("Save the project", artifact_paths=("model.project",))
    attempt = TaskAttempt(1, "worker", "completed", "saved", evidence={"checkpoint": {"workspace": str(tmp_path)},
                            "verification": {"status": "passed"}})
    assert deterministic(request, attempt).reasons[0] == "artifact_missing_from_workspace"
    (tmp_path / "model.project").write_text("project", encoding="utf-8")
    assert deterministic(request, attempt).verdict == "pass"


def test_vision_reviewer_needs_images_but_does_not_need_write_tools():
    from agent.orchestration.controller import OrchestrationController
    from tests.orchestration.test_controller import available
    config = configuration(profiles={"review": {"enabled":True, "provider":"openrouter", "model":"review-model",
                            "capabilities":{"vision":True, "tools":False}}}, routes={"general":["review"]})
    controller = OrchestrationController(config, None, availability=available)
    assert controller.available(config.profiles["review"], TaskRequest("Compare", images=("ref.png",)), reviewer=True)
    assert not controller.available(config.profiles["review"], TaskRequest("Build", images=("ref.png",)))


def test_worker_receives_required_artifact_and_preview_contract():
    from agent.orchestration.executor import ExecutionPolicy
    request = TaskRequest("Create", visual_check=True, artifact_paths=("output.project",))
    policy = ExecutionPolicy(BudgetLedger(DEFAULTS["budget"]), request, True, {})
    message = policy.input_message("Create")
    assert "output.project" in message
    assert "candidate image" in message
