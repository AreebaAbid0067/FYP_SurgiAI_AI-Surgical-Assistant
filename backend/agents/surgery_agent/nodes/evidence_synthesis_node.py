import os

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_groq import ChatGroq

from agents.surgery_agent.tools.query_database import NO_EVIDENCE
from state import State

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY"),
)

INSTRUCTIONS = """You are a surgical clinical decision-support assistant for surgical trainees.

Surgeon's query:
{surgeon_query}

Patient history:
{patient_history}

Retrieved passages (numbered, with source and page):
{context}

Rules:
1. Answer using ONLY the retrieved passages. Cite the passage number(s) in square
   brackets after each claim, e.g. [2].
2. If the passages only partly answer the query, say exactly which part is not
   covered. Do not fill gaps from memory and do not invent references.
3. Where passages disagree, say so and cite both.
4. Be concise. This is decision support and does not replace the senior surgeon's judgement.
5. The knowledge base content is not clinically verified; do not present it as final authority.
"""


def evidence_synthesis_node(state: State):
    """Turn the retrieved passages into the Expert Surgeon's grounded answer.

    This is the step that makes the retrieved documents actually reach the final
    answer: previously the Insight Accumulator received the (empty) text of the
    tool-call message instead of the passages.
    """
    print("Evidence Synthesis")
    context = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            context = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    if not context.strip() or context.startswith(NO_EVIDENCE):
        answer = ("INSUFFICIENT EVIDENCE: no passage in the knowledge base "
                  "(guidelines / UCT textbook) matched this query. Do not treat any "
                  "knowledge-base support as available for it.")
        return {"expert_surgeon_response": answer, "retrieved_context": context}

    prompt = INSTRUCTIONS.format(
        surgeon_query=state["surgeon_query"],
        patient_history=state["patient_history"],
        context=context,
    )
    response = model.invoke(prompt)
    return {"expert_surgeon_response": response.content or "", "retrieved_context": context}
