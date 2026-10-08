"""User-configured expertise routes, independent of model capacity tiers."""

from copy import deepcopy
from dataclasses import replace
import json
import re

_ID = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
_MARKER = "ORCHESTRATION_SPECIALIST:"
_BUILTIN_CATEGORIES = {"reverse_engineering", "roleplay", "sensitive_analysis", "local_private"}


def validate_categories(settings):
    categories = settings["specializations"]
    if len(categories) > 12:
        raise ValueError("At most 12 specializations are supported")
    for name, item in categories.items():
        required = {"enabled", "description", "route", "local_only"}
        if not _ID.fullmatch(name) or not isinstance(item, dict) or not required.issubset(item):
            raise ValueError("Specializations require an ID, enabled, description, route and local_only")
        if item.keys() - (required | {"verifier_profile", "planner_profile", "isolate_workspace"}):
            raise ValueError(f"Unknown specialization fields: {name}")
        if type(item["enabled"]) is not bool or type(item["local_only"]) is not bool:
            raise ValueError(f"Specialization {name}: enabled/local_only must be boolean")
        if "isolate_workspace" in item and type(item["isolate_workspace"]) is not bool:
            raise ValueError(f"Specialization {name}: isolate_workspace must be boolean")
        if not isinstance(item["description"], str) or not 1 <= len(item["description"].strip()) <= 500:
            raise ValueError(f"Specialization {name}: description must contain 1–500 characters")
        if not isinstance(item["route"], str) or item["route"] not in settings["routes"]:
            raise ValueError(f"Specialization {name}: select an existing route")
        for role in ("verifier_profile", "planner_profile"):
            profile = item.get(role, "")
            if not isinstance(profile, str) or (profile and profile not in settings["profiles"]):
                raise ValueError(f"Specialization {name}: unknown {role}")


def selection(category=None, reason=""):
    if category is not None and (not isinstance(category, str) or not _ID.fullmatch(category)):
        raise ValueError("specialization must be a configured category ID")
    if not isinstance(reason, str) or len(reason) > 500 or (category and not reason.strip()):
        raise ValueError("A specialization requires a brief specialization_reason (1–500 characters)")
    return {"specialization": category, "specialization_reason": reason}


def category_for(request, config):
    if not request.specialization:
        return None
    selection(request.specialization, request.specialization_reason)
    category = config.settings["specializations"].get(request.specialization)
    if not category or not category["enabled"]:
        raise ValueError(f"specialization_unavailable: {request.specialization}; configure and enable its route")
    return category


def task_config(config, request):
    category = category_for(request, config)
    if not category:
        return config
    from .config import OrchestrationConfig
    settings = deepcopy(config.settings)
    candidates = [p for p in settings["routes"][category["route"]] if config.profiles[p].enabled]
    local_default = candidates[-1] if candidates and category["local_only"] else ""
    if category["local_only"]:
        settings["privacy"]["cloud_allowed"] = False
    if "isolate_workspace" in category:
        settings["workspace"]["enabled"] = category["isolate_workspace"]
    roles = (("planner_profile", "automation"), ("verifier_profile", "verification"))
    for role, section in roles:
        target = category.get(role) or local_default
        if target:
            settings[section][role] = target
    return OrchestrationConfig(settings, config.profiles)


def catalog_instructions(config):
    catalog = {name: {"description": c["description"][:240], "local_only": c["local_only"],
                      "levels": sorted({config.profiles[p].level for p in config.settings["routes"][c["route"]]
                                        if config.profiles[p].enabled})}
               for name, c in config.settings["specializations"].items() if c["enabled"]}
    if not catalog:
        return ("\nNo specializations are enabled. Omit specialization and specialization_reason from every task. "
                "Use the ordinary route for all work, including frontend/backend development. Do not invent categories.")
    return ("\nConfigured specializations (expertise, not capacity levels): " + json.dumps(catalog, ensure_ascii=False)
            + "\nOnly these exact configured IDs may be chosen; never invent a category such as frontend or backend. "
            "Choose one only for a concrete task fit. In a plan, set specialization and specialization_reason "
            "on the relevant task and use an available level; otherwise omit them. An executor may return ONLY "
            'ORCHESTRATION_SPECIALIST: {"category":"configured_id","reason":"specific task fit"}. '
            "This is a routing request, not a successful result. It must not be used to bypass a policy or permission refusal. "
            "A local-only category must be selected before any cloud planning; later discovery stops for a new local task.")


def normalize_plan_categories(plan, request, config):
    """Discard invented expertise labels, never explicit or configured privacy routes."""
    from .progress import publish
    known = set(config.settings["specializations"]) | _BUILTIN_CATEGORIES | {request.specialization}
    tasks = []
    for task in plan["tasks"]:
        chosen = task.get("specialization")
        if chosen and chosen not in known:
            publish("specialization_ignored", category=chosen,
                    detail=f"Unknown architect category '{chosen}'; continuing with the requested route.")
            task = {k: v for k, v in task.items() if k not in {"specialization", "specialization_reason"}}
        tasks.append(task)
    return {**plan, "tasks": tasks}


def requested_specialist(attempt):
    summary = attempt.summary.strip()
    if not summary.startswith(_MARKER):
        return None
    try:
        value = json.loads(summary[len(_MARKER):].strip())
    except ValueError as exc:
        raise ValueError("invalid_specialist_request: expected category/reason JSON") from exc
    if not isinstance(value, dict) or set(value) != {"category", "reason"} or not value["category"]:
        raise ValueError("invalid_specialist_request: expected category/reason JSON")
    selection(value["category"], value["reason"])
    return value


def reroute_request(request, proposal, config):
    target = replace(request, level="fast", start_node=None, start_reason="",
                     **selection(proposal["category"], proposal["reason"]))
    category = category_for(target, config)
    if category["local_only"] and task_config(config, request).settings["privacy"]["cloud_allowed"]:
        raise ValueError(f"local_selection_required: start a new task with @{target.specialization} before cloud planning")
    if (not task_config(config, request).settings["privacy"]["cloud_allowed"]
            and task_config(config, target).settings["privacy"]["cloud_allowed"]):
        raise ValueError("local_scope_required: a specialist transfer cannot relax the original cloud ban")
    return target


def explicit_category(message, config):
    """A user-owned prefix is resolved before the architect receives the text."""
    if not isinstance(message, str):
        return None
    matched = re.match(r"^@([a-zA-Z][a-zA-Z0-9_-]{0,63})(?:\s|$)", message)
    if matched and (matched[1] in config.settings["specializations"] or matched[1] in _BUILTIN_CATEGORIES):
        return matched[1]
    return None
