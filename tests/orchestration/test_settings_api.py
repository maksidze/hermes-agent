"""The existing config API owns validation, collection deletion and persistence."""

from starlette.testclient import TestClient


def test_settings_roundtrip_rejects_invalid_routes_and_keeps_unrelated_config():
    from hermes_cli.config import load_config, save_config
    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app
    save_config({"display": {"skin": "ares"}})
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    profile = {"enabled": True, "provider": "custom:local", "model": "small", "level": "fast"}
    graph = {"entry": "local", "nodes": [{"id": "local", "profiles": ["local"], "position": {"x": 100, "y": 200}}], "edges": []}
    settings = {"enabled": True, "profiles": {"local": profile}, "routes": {"general": ["local"]},
                "graphs": {"general": graph}}
    response = client.put("/api/config", json={"config": {"orchestration": settings}})
    assert response.status_code == 200, response.text
    loaded = client.get("/api/config").json()
    assert loaded["orchestration"]["profiles"] == settings["profiles"]
    assert loaded["orchestration"]["graphs"] == {"general": graph}
    assert loaded["display"]["skin"] == "ares"
    response = client.put("/api/config", json={"config": {"orchestration": {"profiles": {}}}})
    assert response.status_code == 400
    assert load_config()["orchestration"]["profiles"] == settings["profiles"]
    response = client.put("/api/config", json={"config": {"orchestration": {
        "enabled": False, "profiles": {}, "routes": {}, "graphs": {},
    }}})
    assert response.status_code == 200, response.text
    assert load_config()["orchestration"]["profiles"] == {}
    assert load_config()["orchestration"]["routes"] == {}
    assert load_config()["orchestration"]["graphs"] == {}


def test_profile_probe_requires_existing_session_auth():
    from hermes_cli.web_server import app
    response = TestClient(app).post("/api/orchestration/test-profile/missing")
    assert response.status_code in (401, 403)


def test_specialization_references_survive_roundtrip_and_block_dangling_deletions():
    from hermes_cli.config import load_config, save_config
    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app
    save_config({})
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    profile = {"enabled": True, "provider": "custom:local", "model": "small", "level": "fast"}
    category = {"enabled": True, "description": "Character dialogue", "route": "dialogue", "local_only": False,
                "verifier_profile": "reviewer", "isolate_workspace": False}
    settings = {"enabled": True, "profiles": {"local": profile, "reviewer": profile},
                "routes": {"general": ["local"], "dialogue": ["local"]}, "specializations": {"roleplay": category}}
    response = client.put("/api/config", json={"config": {"orchestration": settings}})
    assert response.status_code == 200, response.text
    assert client.get("/api/config").json()["orchestration"]["specializations"] == {"roleplay": category}
    for update in ({"routes": {"general": ["local"]}}, {"profiles": {"local": profile}}):
        response = client.put("/api/config", json={"config": {"orchestration": update}})
        assert response.status_code == 400
        assert load_config()["orchestration"]["specializations"] == {"roleplay": category}
    response = client.put("/api/config", json={"config": {"orchestration": {"specializations": {},
        "routes": {"general": ["local"]}, "profiles": {"local": profile}}}})
    assert response.status_code == 200, response.text
    assert load_config()["orchestration"]["specializations"] == {}
