"""Classify observed MCP outcomes without application-specific retry exceptions."""

import hashlib
import json

DISCOVERY = {"tool_search", "tool_describe"}
LOCAL_TOOLS = {"read_file", "write_file", "patch", "search_files", "list_directory", "web_search", "web_extract",
               "todo", "todo_list", "vision_analyze", "skills_list", "skill_view"}


def mcp_read_only(name):
    if not name.startswith("mcp__"):
        return False
    from tools import mcp_tool
    from tools.mcp_tool_scope import _resolve_server_key
    from tools.mcp_tool_schema import mcp_prefixed_tool_name
    server = mcp_tool._mcp_tool_server_names.get(name)
    if not server:
        return False
    hints = mcp_tool._tool_read_only_hints.get(_resolve_server_key(server), {})
    return any(value is True and mcp_prefixed_tool_name(server, tool) == name for tool, value in hints.items())


def argument_hash(arguments):
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return hashlib.sha256(arguments.encode()).hexdigest()
    return hashlib.sha256(json.dumps(arguments, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def call_arguments(call):
    arguments = call.get("arguments", "")
    if call.get("name") != "tool_call":
        return arguments
    try:
        wrapper = json.loads(arguments) if isinstance(arguments, str) else arguments
    except ValueError:
        return arguments
    return wrapper.get("arguments", {}) if isinstance(wrapper, dict) else arguments


def effect_kind(name, content, disposition, arguments):
    from .handoff import verification_command
    if disposition == "none" or name in LOCAL_TOOLS | DISCOVERY or mcp_read_only(name):
        return "none"
    if name == "terminal" and verification_command(arguments):
        return "none"
    # A successful MCP response confirms execution, not business correctness.
    # Failed/abandoned writes can have partially executed and remain uncertain.
    from agent.display import _detect_tool_failure
    if (name.startswith("mcp__") and disposition != "unknown" and content is not None
            and not _detect_tool_failure(name, content)[0]):
        return "confirmed"
    return "uncertain"


def retained_effects(attempts):
    return tuple(row for attempt in attempts for row in attempt.evidence.get("tool_results", ())
                 if row.get("effect") in {"confirmed", "uncertain"})
