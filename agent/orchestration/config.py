"""Validated, profile-scoped config; read once per orchestration operation."""

from copy import deepcopy
from dataclasses import dataclass
import re

from .types import ExecutionProfile, LEVELS

DEFAULTS = {
    "enabled": False,
    "mode": "auto",
    "automation": {"mode": "all", "planner_profile": "", "max_tasks": 6},
    "workspace": {"enabled": False, "apply_on_success": True},
    "routing": {"strategy": "agent", "default_route": "general", "default_level": "fast",
                "allow_direct_deep": True, "preferred_profile": "", "max_specialist_switches": 2, "adaptive_entry": True},
    "profiles": {},
    "routes": {},
    "graphs": {},
    "specializations": {},
    "escalation": {"enabled": True, "same_profile_repairs": 1, "max_escalations": 2,
                   "triggers": {"verification_failed": True, "schema_failed": True,
                                "repetition_detected": True, "explicit_request": True}},
    "verification": {"deterministic": True, "semantic": "risk_based", "verifier_profile": "",
                     "uncertain_action": "escalate", "main_agent_stop_gate": False},
    "availability": {"cache_seconds": 30, "failure_cooldown_seconds": 60},
    "budget": {"max_attempts": 4, "max_escalations": 2, "max_model_calls": 40,
               "max_parallel_tasks": 4, "timeout_seconds": 600, "max_calls_per_attempt": 12},
    "privacy": {"cloud_allowed": True},
    "logging": {"decisions": True, "attempts": True, "verification": True},
}
_IDENTIFIER = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")


@dataclass(frozen=True)
class OrchestrationConfig:
    settings: dict
    profiles: dict[str, ExecutionProfile]

    @property
    def active(self):
        return self.settings["enabled"]


def _merge_known(defaults, value, path="orchestration"):
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    unknown = value.keys() - defaults.keys()
    if unknown:
        raise ValueError(f"Unknown {path} keys: {', '.join(sorted(unknown))}")
    result = deepcopy(defaults)
    for key, item in value.items():
        if isinstance(defaults[key], dict) and defaults[key]:
            result[key] = _merge_known(defaults[key], item, f"{path}.{key}")
        else:
            result[key] = item
    return result


def _choice(value, choices, path):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{path} must be one of {', '.join(choices)}")


def _integer(value, minimum, path):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{path} must be an integer >= {minimum}")


def _validate_scalars(cfg, defaults=DEFAULTS, path="orchestration"):
    for key, default in defaults.items():
        value = cfg[key]
        name = f"{path}.{key}"
        if isinstance(default, dict):
            if not isinstance(value, dict):
                raise ValueError(f"{name} must be an object")
            if default:
                _validate_scalars(value, default, name)
        elif isinstance(default, bool) and type(value) is not bool:
            raise ValueError(f"{name} must be a boolean")
        elif type(default) is int:
            minimum = 0 if key in {"same_profile_repairs", "max_escalations", "max_specialist_switches", "cache_seconds", "failure_cooldown_seconds"} else 1
            _integer(value, minimum, name)
        elif isinstance(default, str) and not isinstance(value, str):
            raise ValueError(f"{name} must be a string")


def _profile(name, value):
    if not _IDENTIFIER.fullmatch(name) or not isinstance(value, dict):
        raise ValueError("Profile IDs must be simple identifiers and profiles must be objects")
    required = {"enabled", "provider", "model"}
    allowed = required | {"level", "description", "reasoning_effort", "priority", "max_parallel", "capabilities"}
    if required - value.keys() or value.keys() - allowed:
        raise ValueError(f"Profile {name}: require enabled/provider/model/level; credentials and endpoints belong in provider settings")
    if type(value["enabled"]) is not bool:
        raise ValueError(f"Profile {name}: enabled must be boolean")
    for key in ("provider", "model"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError(f"Profile {name}: {key} is required")
    if value["provider"] == "auto":
        raise ValueError(f"Profile {name}: select an explicit configured provider")
    _choice(value.get("level", "fast"), LEVELS, f"{name}.level")
    if not isinstance(value.get("description", ""), str) or len(value.get("description", "")) > 1000:
        raise ValueError(f"Profile {name}: description must be at most 1000 characters")
    effort = value.get("reasoning_effort")
    if effort is not None:
        _choice(effort, ("none", "minimal", "low", "medium", "high", "xhigh", "max"), f"{name}.reasoning_effort")
    _integer(value.get("max_parallel", 1), 1, f"{name}.max_parallel")
    _integer(value.get("priority", 0), 0, f"{name}.priority")
    caps = value.get("capabilities", {})
    if not isinstance(caps, dict) or caps.keys() - {"tools", "vision", "structured_output"}:
        raise ValueError(f"Profile {name}: invalid capabilities")
    if any(type(v) is not bool and v != "auto" for v in caps.values()):
        raise ValueError(f"Profile {name}: capabilities must be auto, true or false")
    return ExecutionProfile(id=name, **value)


def parse_config(raw=None):
    cfg = _merge_known(DEFAULTS, {} if raw is None else raw)
    _validate_scalars(cfg)
    _choice(cfg["mode"], ("off", "observe", "auto"), "mode")
    _choice(cfg["automation"]["mode"], ("manual", "development", "all"), "automation.mode")
    # Legacy selectors remain readable; enabled is now the sole run switch.
    cfg["mode"] = "auto"
    cfg["automation"]["mode"] = "all"
    if cfg["automation"]["max_tasks"] > 12:
        raise ValueError("automation.max_tasks must not exceed 12")
    # The classifier is deliberately a second-phase feature, never a silent no-op.
    _choice(cfg["routing"]["strategy"], ("agent",), "routing.strategy (MVP)")
    _choice(cfg["routing"]["default_level"], LEVELS, "routing.default_level")
    _choice(cfg["verification"]["semantic"], ("off", "risk_based", "always"), "verification.semantic")
    _choice(cfg["verification"]["uncertain_action"], ("accept", "repair", "escalate"), "verification.uncertain_action")
    profiles = {name: _profile(name, value) for name, value in cfg["profiles"].items()}
    from .graph_config import compile_routes
    compile_routes(cfg, profiles)
    for name, route in cfg["routes"].items():
        if not _IDENTIFIER.fullmatch(name) or not isinstance(route, list) or not route:
            raise ValueError("Routes must be named non-empty arrays of profile IDs")
        if any(not isinstance(p, str) or p not in profiles for p in route) or len(set(route)) != len(route):
            raise ValueError(f"Route {name} references an unknown or duplicate profile")
    verifier = cfg["verification"]["verifier_profile"]
    if verifier and verifier not in profiles:
        raise ValueError("verification.verifier_profile references an unknown profile")
    planner = cfg["automation"]["planner_profile"]
    if planner and planner not in profiles:
        raise ValueError("automation.planner_profile references an unknown profile")
    preferred = cfg["routing"]["preferred_profile"]
    if preferred and preferred not in profiles:
        raise ValueError("routing.preferred_profile references an unknown profile")
    if cfg["enabled"] and cfg["mode"] != "off" and cfg["routing"]["default_route"] not in cfg["routes"]:
        raise ValueError("routing.default_route must reference an existing route")
    from .specializations import validate_categories
    validate_categories(cfg)
    return OrchestrationConfig(cfg, profiles)


def load_config():
    from hermes_cli.config import load_config_readonly
    return parse_config(load_config_readonly().get("orchestration"))


def enabled():
    try:
        return load_config().active
    except ValueError:
        return False
