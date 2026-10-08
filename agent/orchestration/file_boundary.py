"""Keep orchestration's file tools inside the assigned worktree after hook rewrites."""

from pathlib import Path


def file_write_block(workspace, name, args, task_id):
    if not workspace or name not in {"write_file", "patch"}:
        return None
    paths = [args.get("path")]
    if name == "patch" and args.get("mode") == "patch":
        from tools.patch_parser import parse_v4a_patch
        operations, error = parse_v4a_patch(args.get("patch") or "")
        if error:
            return error
        paths = [path for op in operations for path in (op.file_path, op.new_path) if path]
    from agent.file_safety import is_nt_namespace_path
    from tools.file_tools_paths import _resolve_path_for_task
    root = Path(workspace["path"]).resolve()
    for path in paths:
        if not isinstance(path, str) or not path or is_nt_namespace_path(path):
            return "Orchestration requires an ordinary file path inside its worktree"
        resolved = _resolve_path_for_task(path, task_id or "default").resolve()
        if not resolved.is_relative_to(root):
            return f"Write outside orchestration worktree blocked. Use paths beneath {root}"
    return None
