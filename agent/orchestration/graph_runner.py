"""LangGraph drives transitions; Hermes retains its tool, budget and workspace gates."""

from functools import partial
from dataclasses import replace
from typing import TypedDict

from .budget import BudgetExceeded
from .events import emit
from .graph_config import OUTCOMES, graph_for_route, legacy_graph


class RouteState(TypedDict):
    destination: str
    hops: int


def _pool(controller, request, node, result, has_next):
    action = "skip"
    for index, profile_id in enumerate(node["profiles"]):
        controller.budget.check()
        profile = controller.config.profiles[profile_id]
        if not profile.enabled or not controller.available(profile, request):
            continue
        emit(controller.settings, "profile_selected", task_id=request.task_id, profile=profile.id,
             provider=profile.provider, model=profile.model)
        action = controller._run_profile(request, profile, has_next or index + 1 < len(node["profiles"]), result)
        if action in {"accept", "needs_input", "specialist"}:
            return action
        if result.attempts[-1].verification and result.attempts[-1].verification.verdict == "uncertain":
            return "uncertain"
        if action == "fail":
            return action
        if action != "skip" and index + 1 < len(node["profiles"]):
            controller.budget.escalate()
    return action


def _step(state, *, controller, request, result, node, edges, end):
    controller.budget.check()
    # Unavailable-only cycles consume no model calls; cap transitions separately.
    if state["hops"] >= 128:
        raise BudgetExceeded("graph_transition_limit")
    emit(controller.settings, "graph_node_started", task_id=request.task_id, node=node["id"],
         detail=node.get("label") or node["id"])
    if node.get("description"):
        request = replace(request, context=request.context + "\nCurrent workflow group: " + node["description"])
    action = _pool(controller, request, node, result, any(key != "success" for key in edges))
    outcome = {"accept": "success", "skip": "unavailable", "uncertain": "uncertain"}.get(action, "failure")
    target = edges.get(outcome)
    # Refusals, ambiguous external effects and specialist isolation remain hard gates.
    if action in {"specialist", "needs_input", "fail"}:
        target = None
    if target and outcome in {"failure", "uncertain"}:
        controller.budget.escalate()
    if target:
        emit(controller.settings, "graph_transition", task_id=request.task_id, node=node["id"],
             target=target, reason=outcome, detail=f"{node['id']} → {target}: {outcome}")
    else:
        result.status = {"accept": "completed", "needs_input": "blocked", "skip": "blocked",
                         "uncertain": "blocked"}.get(action, "failed")
        if action == "skip":
            result.reason = result.reason or "no_available_profile"
            result.status = "failed" if result.attempts else "blocked"
    return {"destination": target or end, "hops": state["hops"] + 1}


def execute_graph(controller, request, route, result):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise ValueError("LangGraph is unavailable. Install the orchestration extra with Hermes PM.") from exc
    graph = controller.settings["graphs"].get(route.name) if not controller.settings["routing"]["preferred_profile"] else None
    graph = graph or legacy_graph(route)
    if controller.settings["routing"]["adaptive_entry"] and graph.get("entry_nodes") and graph["entry"] not in graph["entry_nodes"]:
        graph = {**graph, "entry": graph["entry_nodes"][0]}
    if request.start_node and not controller.settings["routing"]["preferred_profile"]:
        graph = {**graph_for_route(controller.config, route.name), "entry": request.start_node}
        emit(controller.settings, "entry_selected", task_id=request.task_id, node=request.start_node,
             detail=request.start_reason or request.start_node)
    if not graph["nodes"]:
        result.status, result.reason = "blocked", "no_available_profile"
        return
    builder = StateGraph(RouteState)
    for node in graph["nodes"]:
        edges = {e["on"]: e["target"] for e in graph["edges"] if e["source"] == node["id"] and e["on"] in OUTCOMES}
        builder.add_node(node["id"], partial(_step, controller=controller, request=request, result=result,
                                              node=node, edges=edges, end=END))
        builder.add_conditional_edges(node["id"], lambda state: state["destination"])
    builder.add_edge(START, graph["entry"])
    builder.compile().invoke({"destination": graph["entry"], "hops": 0}, {"recursion_limit": 130})
