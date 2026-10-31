from langgraph.graph.state import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from .nodes.anatomy_node import anatomy_node
from .nodes.complication_management_node import complication_management_node
from .nodes.evidence_synthesis_node import evidence_synthesis_node
from .nodes.expert_surgeon_node import expert_surgeon_node
from .nodes.infection_prevention_node import infection_prevention_node
from .nodes.insights_accumulator_node import insight_accumulator_node
from .nodes.response_generation_node import response_generation_node
from .nodes.rewrite_node import rewrite

from .routing_functions.grade_document import grade_document

from .tools.query_database import query_database
from state import State


def no_evidence_node(state: State):
    """Return a safe response when retrieval evidence is insufficient."""
    answer = (
        "I couldn't find sufficiently relevant evidence in SurgiAI's "
        "knowledge base to answer this question reliably. Please ask a "
        "question related to surgical care."
    )
    return {"answer": answer}


def _build_agent():
    builder = StateGraph(State)

    # The Expert Surgeon / Retriever pair uses ONE unified tool.
    tool_node = ToolNode([query_database])

    builder.add_node("Anatomy Specialist", anatomy_node)
    builder.add_node("Infection Prevention Specialist", infection_prevention_node)
    builder.add_node("Complication Manager", complication_management_node)
    builder.add_node("Expert Surgeon", expert_surgeon_node)
    builder.add_node("Retriever", tool_node)
    builder.add_node("Rewrite", rewrite)
    builder.add_node("Evidence Synthesis", evidence_synthesis_node)
    builder.add_node("Insight Accumulator", insight_accumulator_node)
    builder.add_node("Answer Generation", response_generation_node)
    builder.add_node("No Evidence", no_evidence_node)

    builder.add_edge(START, "Anatomy Specialist")
    builder.add_edge("Anatomy Specialist", "Infection Prevention Specialist")
    builder.add_edge("Infection Prevention Specialist", "Complication Manager")
    builder.add_edge("Complication Manager", "Expert Surgeon")
    builder.add_edge("Expert Surgeon", "Retriever")
    builder.add_conditional_edges(
        "Retriever",
        grade_document,
        {
            "Evidence Synthesis": "Evidence Synthesis",
            "Rewrite": "Rewrite",
            "No Evidence": "No Evidence",
        },
    )
    builder.add_edge("Rewrite", "Expert Surgeon")
    builder.add_edge("Evidence Synthesis", "Insight Accumulator")
    builder.add_edge("Insight Accumulator", "Answer Generation")
    builder.add_edge("Answer Generation", END)
    builder.add_edge("No Evidence", END)
    return builder.compile()


def surgical_agent(state):
    result = _build_agent().invoke(state)
    return result["answer"]
