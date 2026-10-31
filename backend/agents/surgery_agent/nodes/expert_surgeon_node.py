import uuid

from langchain_core.messages import AIMessage

from state import State


def expert_surgeon_node(state: State):
    """Issue the retrieval request.

    The Expert Surgeon uses exactly ONE tool, `query_database`, which searches the
    legacy namespace, the guideline namespace and the UCT textbook namespace.
    The tool call is built deterministically (no LLM round-trip), so retrieval
    always happens and cannot be skipped or mis-routed by the model. After a
    failed relevance grade, the Rewrite node supplies an improved `search_query`.
    """
    print("Expert Surgeon -> retrieval request")

    query = (state.get("search_query") or "").strip() or state["surgeon_query"]
    request = AIMessage(
        content="",
        tool_calls=[{
            "name": "query_database",
            "args": {"surgeon_query": query},
            "id": f"call_{uuid.uuid4().hex[:12]}",
            "type": "tool_call",
        }],
    )
    return {"messages": [request]}
