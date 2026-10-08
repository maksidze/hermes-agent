"""Real loader, profile scope and disabled-tool contracts."""
import pytest

from agent.orchestration.config import load_config, parse_config
from agent.orchestration.settings import validate_update
from agent.orchestration.tool import handle, parse_request


def test_absent_config_preserves_disabled_surface(monkeypatch):
    from tools import orchestration_tool
    from agent.orchestration import controller
    assert not load_config().active
    assert not orchestration_tool.check_requirements()
    def forbidden(*args, **kwargs):
        pytest.fail("disabled orchestration constructed a controller")
    monkeypatch.setattr(controller.OrchestrationController, "__init__", forbidden)
    assert "orchestration_disabled" in handle({"goal": "hello"})


def test_config_scope_and_roundtrip(tmp_path):
    from hermes_cli.config import save_config
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override
    homes = [tmp_path / "first", tmp_path / "second"]
    for home in homes:
        home.mkdir()
    token = set_hermes_home_override(homes[0])
    try:
        save_config({"orchestration": {"enabled": False, "budget": {"max_attempts": 7}}})
        assert load_config().settings["budget"]["max_attempts"] == 7
    finally:
        reset_hermes_home_override(token)
    token = set_hermes_home_override(homes[1])
    try:
        assert load_config().settings["budget"]["max_attempts"] == 4
    finally:
        reset_hermes_home_override(token)


@pytest.mark.parametrize("raw", [
    {"privacy": {"cloud_allowed": "false"}}, {"budget": {"max_model_calls": True}},
    {"profiles": {"x": {"enabled": True, "provider": "local", "model": "m", "level": "fast", "api_key": "forbidden"}}},
    {"routes": {"general": ["missing"]}},
])
def test_invalid_settings_are_rejected(raw):
    with pytest.raises(ValueError):
        parse_config(raw)


def test_collection_deletion_does_not_resurrect_profiles():
    merged = {"orchestration": {"profiles": {"old": {}}, "routes": {"general": ["old"]}}}
    validate_update(merged, {"orchestration": {"profiles": {}, "routes": {}}})
    assert merged["orchestration"] == {"profiles": {}, "routes": {}}


def test_tool_cannot_supply_credentials_or_arbitrary_provider():
    with pytest.raises(ValueError):
        parse_request({"goal": "x", "provider": "evil", "api_key": "secret"})


def test_new_session_schema_observes_enable_disable_without_availability_grace():
    from hermes_cli.config import save_config
    from tools import orchestration_tool
    from tools.registry import registry
    assert orchestration_tool.check_requirements() is False
    assert not registry.get_definitions({"orchestrate_task"}, quiet=True)
    settings = {"enabled": True, "profiles": {"local": {
        "enabled": True, "provider": "custom:local", "model": "m", "level": "fast",
    }}, "routes": {"general": ["local"]}}
    save_config({"orchestration": settings})
    active_schema = registry.get_definitions({"orchestrate_task"}, quiet=True)
    assert len(active_schema) == 1
    settings["enabled"] = False
    save_config({"orchestration": settings})
    assert not registry.get_definitions({"orchestrate_task"}, quiet=True)
    assert active_schema[0]["function"]["name"] == "orchestrate_task"
