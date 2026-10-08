"""Attempt journals over Hermes checkpoints, with a retained isolated worktree.

Worktrees isolate file changes, not arbitrary process/network effects. Failed
attempts stay available; repairs inspect and continue them rather than erase them.
"""

from dataclasses import asdict
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from hermes_cli._subprocess_compat import harden_git_argv, noninteractive_repo_git_env, windows_hide_flags
from hermes_platform.resolver import locate_command
from tools.checkpoint_manager import CheckpointManager, _git_env, _store_path
from tools.subagent_worktree import create_subagent_worktree, local_backend_active, resolve_repo_root


def git_bytes(args, cwd, *, env=None):
    env = env if env is not None else noninteractive_repo_git_env(str(cwd))
    if env is None:
        raise ValueError("Cannot safely inspect Git filters")
    command = locate_command("git").command
    if not command:
        raise ValueError("Git is required for orchestration checkpoints")
    result = subprocess.run([*command, *harden_git_argv(args)], cwd=cwd, env=env,
                            capture_output=True, stdin=subprocess.DEVNULL, timeout=60,
                            creationflags=windows_hide_flags())
    if result.returncode:
        raise ValueError("Git operation failed: " + result.stderr.decode("utf-8", errors="replace")[:1000])
    return result.stdout


class WorkspaceJournal:
    def __init__(self, parent, config):
        from hermes_constants import get_hermes_home
        from .executor import workspace_key
        self.source = Path(workspace_key(parent)).resolve()
        self.root = Path(get_hermes_home()) / "orchestration" / "runs" / uuid4().hex
        self.config = config
        self.manager = CheckpointManager(enabled=True, max_snapshots=config.settings["budget"]["max_attempts"] * 2 + 8)
        self.info = None
        self.baseline = ""
        self.attempts = []

    def prepare(self):
        if self.info:
            return self.info
        if not local_backend_active() or resolve_repo_root(str(self.source)) is None:
            raise ValueError("Isolated orchestration requires a local Git project with an initial commit")
        # Capture from the repo root even when the session starts in a subdir.
        self.source = Path(resolve_repo_root(str(self.source))).resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        self.info = create_subagent_worktree(str(self.source), "o-" + self.root.name[:10], maintain_ignore=False)
        if not self.info:
            raise ValueError("Could not create isolated worktree; no executor was launched")
        self.baseline = self.checkpoint(self.source, "orchestration baseline")
        patch = git_bytes(["diff", "--binary", "HEAD", "--"], self.source)
        if patch:
            patch_path = self.root / "initial.patch"
            patch_path.write_bytes(patch)
            git_bytes(["apply", "--binary", str(patch_path)], self.info["path"])
        self._copy_untracked()
        self.write_manifest("prepared")
        return self.info

    def _copy_untracked(self):
        names = git_bytes(["ls-files", "--others", "--exclude-standard", "--exclude=.worktrees/", "-z"], self.source)
        target_root = Path(self.info["path"]).resolve()
        for raw in filter(None, names.split(b"\0")):
            relative = Path(os.fsdecode(raw))
            source = self.source / relative
            target = target_root / relative
            if (source.is_symlink() or not source.resolve().is_relative_to(self.source)
                    or not target.resolve().is_relative_to(target_root)):
                raise ValueError(f"Untracked link cannot be safely copied: {relative}")
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

    def remap_paths(self, content):
        target = Path(self.info["path"]).as_posix()
        sources = {str(self.source), self.source.as_posix()}
        targets = {str(Path(self.info["path"])), target}
        # Match existing worktree roots first, in ONE pass: the replacement
        # itself contains the source root and must never be remapped again.
        encoded_targets = targets | {json.dumps(p)[1:-1] for p in targets}
        roots = sources | {json.dumps(p)[1:-1] for p in sources} | encoded_targets
        pattern = "(?:" + "|".join(re.escape(p) for p in sorted(roots, key=len, reverse=True)) + r")(?=$|[/\\\s\"'`])"
        return re.sub(pattern, lambda match: match[0] if match[0] in encoded_targets else target, content)

    def checkpoint(self, path, reason):
        self.manager.new_turn()
        taken = self.manager.ensure_checkpoint(str(path), reason)
        points = self.manager.list_checkpoints(str(path))
        if not points:
            raise ValueError("Checkpoint unavailable; execution stopped before further writes")
        commit = points[0]["hash"]
        if not taken:
            diff = self.manager.diff(str(path), commit)
            if not diff.get("success") or diff.get("diff") or diff.get("stat"):
                raise ValueError("Cannot verify current checkpoint; execution stopped")
        return commit

    def start_attempt(self, number, profile=""):
        self.prepare()
        before = self.checkpoint(self.info["path"], f"before orchestration attempt {number}")
        self.attempts.append({"number": number, "profile": profile, "status": "running",
                              "evidence": {"checkpoint": {"before": before, "workspace": self.info["path"]}}})
        self.write_manifest("running")
        return before

    def patch(self, before, after):
        return git_bytes(["diff", "--binary", "--no-ext-diff", before, after, "--"], self.info["path"],
                         env=_git_env(_store_path(), self.info["path"]))

    def finish_attempt(self, attempt, before):
        after = self.checkpoint(self.info["path"], f"after orchestration attempt {attempt.number}")
        stem = f"attempt-{attempt.number:03d}"
        patch_path = self.root / (stem + ".patch")
        patch = self.patch(before, after)
        patch_path.write_bytes(patch)
        attempt.evidence["changes"] = patch.decode("utf-8", errors="replace")[:8000]
        cumulative = self.patch(self.baseline, after)
        attempt.evidence["cumulative_changes"] = cumulative.decode("utf-8", errors="replace")[:10000]
        attempt.evidence["checkpoint"] = {"before": before, "after": after, "patch": str(patch_path),
                                            "workspace": self.info["path"]}
        attempt.evidence.setdefault("artifacts", []).append(str(patch_path))
        self.attempts = [asdict(attempt) if a["number"] == attempt.number else a for a in self.attempts]
        self.write_manifest("running")

    def write_manifest(self, status, **extra):
        payload = {"status": status, "source": str(self.source), "worktree": self.info,
                   "baseline": self.baseline, "attempts": self.attempts,
                   "graphs": self.config.settings["graphs"], **extra}
        (self.root / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_result(self, result):
        # Verification runs after capture, so refresh journal entries with the verdict.
        by_number = {a.number: asdict(a) for a in result.attempts}
        self.attempts = [by_number.get(a["number"], a) for a in self.attempts]
        if self.info:
            self.write_manifest(result.status, reason=result.reason)

    def finish(self, successful):
        if not self.info:
            return {}
        details = {"workspace": self.info["path"], "journal": str(self.root / "run.json"), "applied": False}
        if not successful:
            self.write_manifest("retained", note="Inspect any running attempt before restoring; cancellation may still be settling.")
            return details
        final = self.checkpoint(self.info["path"], "orchestration completed")
        patch = self.patch(self.baseline, final)
        path = self.root / "result.patch"
        path.write_bytes(patch)
        details["patch"] = str(path)
        if self.config.settings["workspace"]["apply_on_success"]:
            current = self.checkpoint(self.source, "before orchestration apply")
            if self.patch(self.baseline, current):
                self.write_manifest("apply_conflict", **details)
                raise ValueError(f"Source changed during execution. Result retained at {path}; apply after review")
            if patch:
                git_bytes(["apply", "--check", "--binary", str(path)], self.source)
                git_bytes(["apply", "--binary", str(path)], self.source)
            details["applied"] = True
        self.write_manifest("completed", **details)
        return details
