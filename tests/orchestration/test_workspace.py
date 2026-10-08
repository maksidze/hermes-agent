"""Real Git/shadow-store contracts: preserve dirty input and refuse stale apply."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.orchestration.config import parse_config
from agent.orchestration.types import TaskAttempt, TaskResult, VerificationResult
from agent.orchestration.workspace import WorkspaceJournal, git_bytes


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    from hermes_cli.config import save_config
    source = tmp_path / "project"
    source.mkdir()
    monkeypatch.chdir(source)
    git_bytes(["init"], source)
    (source / "module.py").write_text("original = True\n", encoding="utf-8")
    (source / "removed.py").write_text("old = True\n", encoding="utf-8")
    (source / "payload.dat").write_bytes(b"old\x00data")
    git_bytes(["add", "."], source)
    git_bytes(["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
               "commit", "-m", "initial"], source)
    (source / "module.py").write_text("user_change = True\n", encoding="utf-8")
    (source / "notes.txt").write_text("untracked user file\n", encoding="utf-8")
    save_config({"terminal": {"backend": "local", "cwd": str(source)}})
    journal = WorkspaceJournal(SimpleNamespace(_current_task_id=None), parse_config({"workspace": {"enabled": True}}))
    return source, journal


def test_attempt_snapshot_dirty_baseline_binary_deletion_and_apply(workspace):
    source, journal = workspace
    before = journal.start_attempt(1)
    checkout = Path(journal.info["path"])
    assert (checkout / "module.py").read_text() == "user_change = True\n"
    assert (checkout / "notes.txt").read_text() == "untracked user file\n"
    assert not (source / ".gitignore").exists()
    (checkout / "module.py").write_text("user_change = True\nimplementation = True\n", encoding="utf-8")
    (checkout / "new.py").write_text("new = True\n", encoding="utf-8")
    (checkout / "removed.py").unlink()
    (checkout / "payload.dat").write_bytes(b"new\x00data\xff")
    attempt = TaskAttempt(1, "fast", "completed", "implemented")
    journal.finish_attempt(attempt, before)
    attempt.verification = VerificationResult("pass", evidence=("tests passed",))
    journal.record_result(TaskResult("test", "completed", attempts=[attempt]))
    assert (source / "module.py").read_text() == "user_change = True\n"
    result = journal.finish(True)
    assert result["applied"]
    assert (source / "module.py").read_text() == "user_change = True\nimplementation = True\n"
    assert (source / "new.py").exists()
    assert not (source / "removed.py").exists()
    assert (source / "payload.dat").read_bytes() == b"new\x00data\xff"
    assert (source / "notes.txt").read_text() == "untracked user file\n"
    data = json.loads(Path(result["journal"]).read_text(encoding="utf-8"))
    assert data["attempts"][0]["verification"]["verdict"] == "pass"
    assert Path(attempt.evidence["checkpoint"]["patch"]).is_file()
    assert checkout.is_dir()


def test_failed_changes_retained_and_user_edits_block_apply(workspace):
    source, journal = workspace
    before = journal.start_attempt(1)
    checkout = Path(journal.info["path"])
    (checkout / "module.py").write_text("failed attempt\n", encoding="utf-8")
    journal.finish_attempt(TaskAttempt(1, "fast", "failed", "tests failed"), before)
    assert journal.finish(False)["applied"] is False
    assert (checkout / "module.py").read_text() == "failed attempt\n"
    (source / "module.py").write_text("user changed meanwhile\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Source changed"):
        journal.finish(True)
    assert (source / "module.py").read_text() == "user changed meanwhile\n"
    assert (journal.root / "result.patch").exists()


def test_handoff_paths_are_idempotent_and_leave_sibling_projects_alone(workspace):
    source, journal = workspace
    journal.prepare()
    target = Path(journal.info["path"]).as_posix()
    for root in (str(source), source.as_posix()):
        payload = json.dumps({"original": root + "/src/main.js", "retained": target + "/src/main.js",
                              "sibling": root + "-other/src/main.js"})
        mapped = journal.remap_paths(payload)
        assert json.loads(mapped) == {"original": target + "/src/main.js", "retained": target + "/src/main.js",
                                     "sibling": root + "-other/src/main.js"}
        assert journal.remap_paths(mapped) == mapped
        assert journal.remap_paths(root + "/src/main.js") == target + "/src/main.js"
