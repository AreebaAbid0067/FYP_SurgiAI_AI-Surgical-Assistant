"""Shared LLM access for the post-surgery agent.

Bounded timeout and retries keep responses fast (Performance) and make
failures explicit so the caller can degrade gracefully (Availability).
"""
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

_model = None


class AIUnavailable(RuntimeError):
    """Raised when the language model cannot produce an answer."""


def _get_model():
    global _model
    if _model is None:
        _model = ChatGroq(
            model="qwen/qwen3.8-27b",
            temperature=0.3,
            max_tokens=700,
            timeout=40,
            max_retries=1,
            api_key=os.getenv("GROQ_API_KEY"),
        )
    return _model


def ask(prompt: str) -> str:
    try:
        text = _get_model().invoke(prompt).content
    except Exception as exc:
        raise AIUnavailable(str(exc)) from exc
    if not isinstance(text, str) or not text.strip():
        raise AIUnavailable("The model returned an empty answer.")
    return text.strip()


SAFETY_RULES = """
Rules you must follow:
- Use ONLY the patient data and the reference protocol below. Do not invent findings.
- Name drug classes and typical regimens; always say doses must be confirmed against the local formulary, renal function and weight.
- Check every suggestion against the listed allergies, comorbidities and current medications; state explicitly when something is contraindicated.
- If information is missing or uncertain, say so and flag it for the surgeon's judgement.
- Be concise: short bullet points, no preamble.
"""
