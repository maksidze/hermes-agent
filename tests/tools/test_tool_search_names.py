"""A word-spelled MCP tool name must beat incidental description matches."""

from tools.tool_search_catalog import build_catalog, search_catalog


def test_word_spelled_mcp_name_is_retrievable_without_prefix_in_description():
    def tool(name, description):
        return {"type": "function", "function": {"name": name, "description": description, "parameters": {}}}
    catalog = build_catalog([
        tool("mcp__blender__get_scene_info", "MCP Blender facts, use look to see it"),
        tool("mcp__blender__look", "See the current scene as an image"),
        tool("gui_tour", "Look at the MCP Blender panel")
    ])
    assert search_catalog(catalog, "mcp blender look", limit=1)[0].name == "mcp__blender__look"
    assert search_catalog(catalog, "mcp__blender__look", limit=1)[0].name == "mcp__blender__look"
