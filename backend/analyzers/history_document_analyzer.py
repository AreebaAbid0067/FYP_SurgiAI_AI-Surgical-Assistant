"""Extract structured patient history from an uploaded document so the surgeon
does not have to type it. Supports images (vision model), PDFs and text files.
"""
import base64
import json
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "qwen/qwen3.8-27b"
MAX_TEXT_CHARS = 8000


def _prompt(options: dict) -> str:
    return f"""Read the patient document and extract ONLY information that is explicitly written in it. Do not guess.
Return a single JSON object with these keys and nothing else:
{{
  "age": "number or empty string",
  "sex": "Male | Female | Other | empty string",
  "symptoms": ["free-text presenting features found in the document"],
  "comorbidities": ["choose only from: {', '.join(options['comorbidities'])}"],
  "allergies": ["choose only from: {', '.join(options['allergies'])}"],
  "medications": ["choose only from: {', '.join(options['medications'])}"],
  "other": "anything clinically relevant that did not fit the lists, as one short sentence"
}}"""


def _text_from_pdf(content: bytes) -> str:
    import pymupdf

    with pymupdf.open(stream=content, filetype="pdf") as document:
        return "\n".join(page.get_text() for page in document)[:MAX_TEXT_CHARS]


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0)) if match else {}


def extract_history(content: bytes, content_type: str, options: dict) -> dict:
    client = Groq()
    prompt = _prompt(options)
    if content_type.startswith("image/"):
        encoded = base64.b64encode(content).decode()
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{encoded}"}},
            ],
        }]
    else:
        if content_type == "application/pdf":
            text = _text_from_pdf(content)
        else:
            text = content.decode("utf-8", errors="ignore")[:MAX_TEXT_CHARS]
        if not text.strip():
            raise ValueError("No readable text was found in the document.")
        messages = [{"role": "user", "content": f"{prompt}\n\nDocument:\n{text}"}]

    reply = client.chat.completions.create(
        messages=messages, model=MODEL, max_tokens=600, temperature=0
    ).choices[0].message.content
    data = _parse_json(reply)

    def only(values, allowed):
        return [v for v in (values or []) if v in allowed]

    return {
        "age": str(data.get("age") or ""),
        "sex": data.get("sex") if data.get("sex") in options["sex"] else "",
        "symptoms": [str(s) for s in (data.get("symptoms") or [])][:10],
        "comorbidities": only(data.get("comorbidities"), options["comorbidities"]),
        "allergies": only(data.get("allergies"), options["allergies"]),
        "medications": only(data.get("medications"), options["medications"]),
        "other": str(data.get("other") or ""),
    }
