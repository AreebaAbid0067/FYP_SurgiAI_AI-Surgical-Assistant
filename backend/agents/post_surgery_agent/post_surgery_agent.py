"""Post-surgery agent: LangGraph workflow.

START -> (medication | care | monitoring planners in parallel) -> accumulator
"""
from langgraph.graph.state import END, START, StateGraph

from state import PostSurgeryState

from .nodes.planner_nodes import (
    accumulator_node,
    care_planner_node,
    medication_planner_node,
    monitoring_planner_node,
)

_PLANNERS = {
    "Medication Planner": medication_planner_node,
    "Care Planner": care_planner_node,
    "Monitoring Planner": monitoring_planner_node,
}


def _build():
    builder = StateGraph(PostSurgeryState)
    for name, node in _PLANNERS.items():
        builder.add_node(name, node)
        builder.add_edge(START, name)
    builder.add_node("Accumulator", accumulator_node)
    builder.add_edge(list(_PLANNERS), "Accumulator")
    builder.add_edge("Accumulator", END)
    return builder.compile()


_agent = None


def post_surgical_plan_agent(state: PostSurgeryState) -> str:
    global _agent
    if _agent is None:
        _agent = _build()
    return _agent.invoke(state)["postop_plan"]
