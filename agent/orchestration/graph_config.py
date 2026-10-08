"""Declarative model pools and transitions. No executable code in saved graphs."""

import math
import json
import re

OUTCOMES = ("success", "failure", "unavailable", "uncertain")
_ID = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")


def _node(node, profiles):
    if not isinstance(node, dict) or node.keys() - {"id", "label", "description", "profiles", "position"}:
        raise ValueError("Graph node has unsupported fields")
    if not isinstance(node.get("id"), str) or not _ID.fullmatch(node["id"]):
        raise ValueError("Graph node needs a simple ID")
    for field, limit in (("label", 100), ("description", 1000)):
        if not isinstance(node.get(field, ""), str) or len(node.get(field, "")) > limit:
            raise ValueError(f"Graph node {field} is too long")
    pool = node.get("profiles")
    if not isinstance(pool, list) or not pool or len(pool) > 32:
        raise ValueError("Graph node needs 1–32 model profiles")
    if any(not isinstance(p, str) or p not in profiles for p in pool) or len(set(pool)) != len(pool):
        raise ValueError("Graph node references unknown or duplicate profiles")
    position = node.get("position", {"x": 0, "y": 0})
    if not isinstance(position, dict) or set(position) != {"x", "y"}:
        raise ValueError("Graph node position needs x and y")
    if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in position.values()):
        raise ValueError("Graph position must contain finite coordinates")


def validate_graph(graph, profiles, *, adaptive_entry=False):
    if not isinstance(graph, dict) or set(graph) - {"entry", "nodes", "edges", "entry_nodes"} or not {"entry", "nodes", "edges"}.issubset(graph):
        raise ValueError("Graph requires entry, nodes and edges")
    nodes, edges = graph["nodes"], graph["edges"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 64:
        raise ValueError("Graph requires 1–64 nodes")
    for node in nodes:
        _node(node, profiles)
    ids = {node["id"] for node in nodes}
    if len(ids) != len(nodes) or not isinstance(graph["entry"], str) or graph["entry"] not in ids:
        raise ValueError("Graph requires unique node IDs and a valid entry")
    if not isinstance(edges, list) or len(edges) > 256:
        raise ValueError("Graph has too many connections")
    ports = set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {"source", "target", "on"}:
            raise ValueError("Graph connection requires source, target and on")
        if any(not isinstance(v, str) for v in edge.values()):
            raise ValueError("Graph connection fields must be strings")
        port = (edge["source"], edge["on"])
        if edge["source"] not in ids or edge["target"] not in ids or edge["on"] not in OUTCOMES or port in ports:
            raise ValueError("Each output port can connect to one existing node")
        ports.add(port)
    entries = graph.get("entry_nodes", list(ids))
    if not isinstance(entries, list) or not entries or any(not isinstance(n, str) or n not in ids for n in entries) or len(set(entries)) != len(entries):
        raise ValueError("Architect connections must reference unique existing nodes")
    reachable = set(entries) if adaptive_entry else {graph["entry"]}
    for _ in nodes:
        reachable.update(e["target"] for e in edges if e["source"] in reachable)
    if reachable != ids:
        raise ValueError("Every graph node must be reachable from the entry")


def compile_routes(settings, profiles):
    """Keep the route membership index used by specialization/privacy checks."""
    for name, graph in settings["graphs"].items():
        if not _ID.fullmatch(name):
            raise ValueError("Graph route ID must be a simple identifier")
        validate_graph(graph, profiles, adaptive_entry=settings["routing"]["adaptive_entry"])
        settings["routes"][name] = list(dict.fromkeys(p for node in graph["nodes"] for p in node["profiles"]))


def legacy_graph(route):
    nodes = [{"id": f"step_{i}", "label": profile.id, "profiles": [profile.id]} for i, profile in enumerate(route.profiles)]
    edges = [{"source": a["id"], "target": b["id"], "on": outcome}
             for a, b in zip(nodes, nodes[1:]) for outcome in ("failure", "unavailable", "uncertain")]
    return {"entry": nodes[0]["id"] if nodes else "", "nodes": nodes, "edges": edges}


def planning_catalog(config):
    profiles = {p.id: {"model": p.model, "description": p.description} for p in config.profiles.values() if p.enabled}
    graphs = {name: {"entry": graph["entry"], "entry_nodes": graph.get("entry_nodes", [n["id"] for n in graph["nodes"]]), "groups": [{k: n.get(k, "") for k in ("id", "label", "description", "profiles")}
                                                         for n in graph["nodes"]]}
              for name in config.settings["routes"] for graph in [graph_for_route(config, name)]}
    return ("\nModel and workflow catalog (configuration data): " + json.dumps({"profiles": profiles, "workflows": graphs},
                                                                           ensure_ascii=False)[:16000]
            + "\nFor each task choose start_node ONLY from that workflow's entry_nodes (architect connections) and give start_reason. "
              "Use model suitability descriptions, task complexity, risk and required capabilities. "
              "Prefer the economical entry for routine tasks; for a difficult task start directly at a "
              "suitable capable group rather than forcing a weak model to fail first. "
              "Model size or a profile name alone is not proof of capability. Do not invent group IDs. "
              "The selected group executes the task; all later transitions still follow the saved graph. "
              f"Adaptive entry enabled: {config.settings['routing']['adaptive_entry']}.")


def graph_for_route(config, name):
    from .types import TaskRoute
    return config.settings["graphs"].get(name) or legacy_graph(TaskRoute(
        name, "graph", tuple(config.profiles[p] for p in config.settings["routes"][name])))
