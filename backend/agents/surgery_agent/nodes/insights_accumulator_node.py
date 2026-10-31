
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage

from state import State

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)


def insight_accumulator_node(state: State):
    """Combine specialist insights without inventing missing evidence."""

    print("Insight Accumulator")

    surgeon_response = str(state.get("expert_surgeon_response", "")).strip()

    # Do not ask the LLM to synthesize evidence that is explicitly missing.
    if (
        not surgeon_response
        or "INSUFFICIENT EVIDENCE" in surgeon_response.upper()
    ):
        answer = (
            "INSUFFICIENT EVIDENCE: SurgiAI could not establish a supported "
            "answer from the retrieved surgical knowledge. Please consult "
            "an appropriately qualified clinician."
        )
        return {"insight_accumulator_response": answer}

    surgeon_query = state.get("surgeon_query", "")
    patient_history = state.get("patient_history", "")
    anatomy_response = state.get("anatomy_response", "")
    infection_prevention_response = state.get("infection_prevention_response", "")
    complication_response = state.get("complication_response", "")

    instructions = """
You are a surgical insight accumulator.

Question: {surgeon_query}
Patient history: {patient_history}
Relevant anatomy: {anatomy_response}
Infection prevention: {infection_prevention_response}
Potential complications: {complication_response}
Expert Surgeon response: {surgeon_response}

Rules:
- Preserve the evidence and citations supplied by the Expert Surgeon.
- Do not invent clinical facts or recommendations.
- Explicitly identify any unanswered part of the question.
- Do not treat missing patient history as known information.
- This is educational decision support, not a replacement for clinical judgment.

Provide a concise summary of the supported insights.
"""

    prompt = instructions.format(
        surgeon_query=surgeon_query,
        patient_history=patient_history,
        anatomy_response=anatomy_response,
        infection_prevention_response=infection_prevention_response,
        complication_response=complication_response,
        surgeon_response=surgeon_response,
    )

    response: BaseMessage = model.invoke(prompt)
    return {"insight_accumulator_response": response.content or ""}
