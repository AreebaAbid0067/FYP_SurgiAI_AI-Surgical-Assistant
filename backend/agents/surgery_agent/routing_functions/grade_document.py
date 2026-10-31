
import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from agents.surgery_agent.tools.query_database import NO_EVIDENCE
from state import State

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)

PROMPT = PromptTemplate(
    template="""You are grading whether retrieved passages answer a surgeon's question.

Question:
{question}

Retrieved passages:
{context}

Return ONLY a JSON object in this exact format:
{{"grade": "yes"}} or {{"grade": "no"}}

Use "yes" only if the passages directly help answer the question.
Use "no" if they are unrelated, loosely related, or insufficient.""",
    input_variables=["context", "question"],
)


def grade_document(state: State):
    print("---CHECK RELEVANCE---")

    context = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, ToolMessage):
            context = (
                msg.content if isinstance(msg.content, str)
                else str(msg.content)
            )
            break

    question = state.get("surgeon_query", "")
    max_iteration = state.get("max_iteration", 1)
    current_iteration = state.get("current_iteration", 0)

    relevant = False

    if context.strip() and not context.startswith(NO_EVIDENCE):
        try:
            response = model.invoke(
                PROMPT.format(context=context, question=question)
            )
            content = str(response.content).strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()
            result = json.loads(content)
            relevant = str(result.get("grade", "")).strip().lower() == "yes"
        except Exception as exc:
            print(f"Relevance grading failed: {exc}")
            relevant = False


    if not relevant and current_iteration < max_iteration:
        print("---DECISION: NOT RELEVANT -> rewrite query---")
        return "Rewrite"

    if not relevant:
        print("---DECISION: NO GOOD EVIDENCE -> safe response---")
        return "No Evidence"

    print("---DECISION: relevant -> evidence synthesis---")
    return "Evidence Synthesis"
