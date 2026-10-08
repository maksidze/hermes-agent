"""Deterministic routing for agent-selected levels; no extra classifier call."""

import re

from .types import LEVELS, TaskRoute

_COMPLEX = re.compile(r"architecture|architectural|race condition|security audit|distributed|архитектур|миграци|гонк", re.I)
_CODING = re.compile(r"code|coding|debug|unit test|bug|reconnect|код|ошибк|тест|рефактор", re.I)
_RESEARCH = re.compile(r"research|investigate|исслед|источник", re.I)


def route_task(request, config):
    from .specializations import category_for
    category = category_for(request, config)
    settings = config.settings
    routing = settings["routing"]
    routes = settings["routes"]
    name = category["route"] if category else request.route
    if name is None:
        from .attachments import has_images
        candidates = [("vision", has_images(request)), ("coding", _CODING.search(request.goal)),
                      ("research", _RESEARCH.search(request.goal))]
        name = next((key for key, matches in candidates if matches and key in routes), routing["default_route"])
    if name not in routes:
        raise ValueError(f"Unknown orchestration route: {name}")
    if request.start_node and not routing["preferred_profile"]:
        from .graph_config import graph_for_route
        graph = graph_for_route(config, name)
        if request.start_node not in {n["id"] for n in graph["nodes"]}:
            raise ValueError(f"Unknown start_node for route {name}: {request.start_node}")
        if routing["adaptive_entry"] and request.start_node not in graph.get("entry_nodes", [n["id"] for n in graph["nodes"]]):
            raise ValueError("start_node is not connected to the architect")
        return TaskRoute(name, "graph", tuple(config.profiles[p] for p in routes[name]))
    if name in settings["graphs"] and not routing["preferred_profile"]:
        return TaskRoute(name, "graph", tuple(config.profiles[p] for p in routes[name] if config.profiles[p].enabled))
    if routing["preferred_profile"]:
        if category and routing["preferred_profile"] not in routes[name]:
            raise ValueError("fixed_worker_conflicts_with_specialization: select a compatible route or clear the fixed worker")
        profile = config.profiles[routing["preferred_profile"]]
        return TaskRoute(name, profile.level, (profile,) if profile.enabled else ())
    level = "fast" if category and request.level == "auto" else request.level
    if level == "auto":
        level = "deep" if _COMPLEX.search(request.goal) else routing["default_level"]
    if level == "deep" and not routing["allow_direct_deep"]:
        level = "balanced"
    profiles = tuple(config.profiles[p] for p in routes[name]
                     if config.profiles[p].enabled and LEVELS.index(config.profiles[p].level) >= LEVELS.index(level))
    return TaskRoute(name, level, profiles)
