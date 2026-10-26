
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage

from agents.surgery_agent.tools.query_database import (
    NO_EVIDENCE,
    retrieve_passages,
)
from state import State

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)


def response_generation_node(state: State):
    """Generate an answer only when relevant surgical evidence is available."""

    print("Response Generation")

    surgeon_query = state["surgeon_query"]

    # Recheck the original question so an unrelated query cannot receive
    # an answer based only on general LLM knowledge.
    passages, _ = retrieve_passages(surgeon_query)

    if not passages or all(
        p["score"] < 0.30 for p in passages
    ):
        answer = (
            "I couldn't find sufficiently relevant evidence in SurgiAI's "
            "knowledge base to answer this question reliably. "
            "Please ask a question related to surgical care."
        )
        state["answer"] = answer
        state.setdefault("conversation", []).append(answer)
        return state

    insights = state.get("insight_accumulator_response", "")

    if not str(insights).strip() or NO_EVIDENCE in str(insights):
        answer = (
            "I couldn't establish a sufficiently supported answer from the "
            "available surgical evidence. Please consult an appropriately "
            "qualified clinician for guidance."
        )
        state["answer"] = answer
        state.setdefault("conversation", []).append(answer)
        return state

    instructions = """
Answer the surgeon's question using ONLY the supplied retrieved insights.

Question: {surgeon_query}

Retrieved insights:
{insights}

Rules:
- Do not invent facts or unsupported recommendations.
- If the insights do not answer the question, say the available evidence
  is insufficient.
- Keep the answer under 50 words and two sentences.
- This is educational decision support, not a replacement for clinical
  judgment.
"""

    prompt = instructions.format(
        surgeon_query=surgeon_query,
        insights=insights,
    )

    response: BaseMessage = model.invoke(prompt)
    answer = str(response.content).strip()

    state.setdefault("conversation", []).append(answer)
    state["answer"] = answer

    return state
