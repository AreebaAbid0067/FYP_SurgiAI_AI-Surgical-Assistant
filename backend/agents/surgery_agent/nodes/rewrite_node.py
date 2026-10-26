import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from state import State

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.3,
    api_key=os.getenv("GROQ_API_KEY"),
)


def rewrite(state: State):
    """Produce a better search query and count the retry.

    The old node incremented a local variable, so `current_iteration` never
    changed and a persistently irrelevant search could loop until LangGraph's
    recursion limit. It now returns the counter as a state update.
    """
    print("---TRANSFORM QUERY---")
    question = state["surgeon_query"]
    previous = (state.get("search_query") or "").strip() or question
    prompt = (
        "Rewrite this surgical question as a short, keyword-rich search query for a "
        "surgical guideline / textbook database. Use standard clinical terminology and "
        "include the condition and the aspect asked about (diagnosis, imaging, "
        "antibiotics, technique, complications...).\n\n"
        f"Original question: {question}\n"
        f"Previous query that retrieved poor results: {previous}\n\n"
        "Return ONLY the new search query, with no explanation."
    )
    new_query = (model.invoke(prompt).content or "").strip().strip('"').splitlines()[0:1]
    new_query = new_query[0].strip() if new_query else ""
    return {
        "search_query": new_query or previous,
        "current_iteration": state.get("current_iteration", 0) + 1,
    }
