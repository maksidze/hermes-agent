"""Settings integration, preserving the existing config endpoint and writer."""

from copy import deepcopy
from .config import parse_config


def validate_update(merged, incoming):
    if "orchestration" not in incoming:
        return
    update = incoming["orchestration"]
    if not isinstance(update, dict):
        raise ValueError("orchestration must be an object")
    # Profiles/routes are editable collections. Omitted entries in a supplied
    # collection are deletions; other config sections retain normal deep merge.
    for key in ("profiles", "routes", "graphs", "specializations"):
        if key in update:
            merged["orchestration"][key] = deepcopy(update[key])
    parse_config(merged["orchestration"])


def schema_fields():
    choices = {
        "routing.strategy": ["agent"],
        "routing.default_level": ["fast", "balanced", "deep"],
        "verification.semantic": ["off", "risk_based", "always"],
        "verification.uncertain_action": ["accept", "repair", "escalate"],
    }
    fields = {f"orchestration.{key}": {"type": "select", "options": options, "category": "orchestration",
                                        "description": key.replace("_", " ")} for key, options in choices.items()}
    fields.update({f"orchestration.{key}": {"type": "object", "category": "orchestration", "description": key}
                   for key in ("profiles", "routes", "graphs", "specializations")})
    return fields
