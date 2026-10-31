"""Post-surgery service: builds agent input from a saved case and degrades
gracefully to the guideline protocol when the AI service is unavailable."""
import hashlib
import json
import logging
import time
from collections import OrderedDict

import procedures

logger = logging.getLogger("surgiai.postop")

DISCLAIMER = (
    "Decision support only. Confirm every recommendation against the patient's "
    "clinical picture, local protocols and the formulary before acting."
)

_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_CACHE_MAX = 64


def format_protocol(procedure: dict | None) -> str:
    if procedure is None:
        return "No registered reference protocol for this operation; rely on general post-operative principles and flag uncertainty."
    protocol = procedure["protocol"]
    sections = [
        ("Expected recovery", [protocol["recovery_time"]]),
        ("Medications", protocol["medications"]),
        ("Wound care", protocol["wound_care"]),
        ("Diet and activity", protocol["diet_activity"]),
        ("Discharge criteria", protocol["discharge_criteria"]),
        ("Follow-up", protocol["follow_up"]),
        ("Red flags", protocol["red_flags"]),
    ]
    lines = []
    for title, items in sections:
        lines.append(f"## {title}")
        lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)


def format_intraop(summary: dict | None, notes: list[dict]) -> str:
    lines = []
    for key, value in (summary or {}).items():
        if value:
            rendered = ", ".join(value) if isinstance(value, list) else value
            lines.append(f"{key.replace('_', ' ').capitalize()}: {rendered}")
    for note in notes[-5:]:
        lines.append(f"Q: {note['question']} -> {note['answer'][:300]}")
    return "\n".join(lines)


def generate(case_data: dict, procedure_id: str | None, current_status: str) -> dict:
    procedure = procedures.get_procedure(procedure_id)
    protocol_text = format_protocol(procedure)
    intraop = case_data.get("intraop", {})
    state = {
        "operation": case_data.get("procedure_name", ""),
        "patient_history": case_data.get("history_text", ""),
        "preop_summary": (case_data.get("preop_report") or "")[:3500],
        "intraop_summary": format_intraop(intraop.get("summary"), intraop.get("notes", [])),
        "current_status": current_status.strip(),
        "reference_protocol": protocol_text,
        "medication_plan": "",
        "care_plan": "",
        "monitoring_plan": "",
        "postop_plan": "",
    }

    key = hashlib.sha256(
        json.dumps(
            {k: state[k] for k in ("operation", "patient_history", "preop_summary", "intraop_summary", "current_status")},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return {**_CACHE[key], "cached": True}

    started = time.perf_counter()
    try:
        from agents.post_surgery_agent.post_surgery_agent import post_surgical_plan_agent

        plan = post_surgical_plan_agent(state)
        result = {
            "mode": "ai",
            "plan": plan,
            "notice": DISCLAIMER,
        }
    except Exception:
        logger.exception("Post-surgery AI planning failed; serving reference protocol")
        result = {
            "mode": "protocol_only",
            "plan": protocol_text,
            "notice": (
                "AI personalisation is temporarily unavailable. Showing the standard "
                "guideline protocol only - it has NOT been tailored to this patient. "
                + DISCLAIMER
            ),
        }
    result["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    result["sources"] = ["WSES / SAGES / ACS / ATA clinical guidance summarised in SurgiAI verification checklists"]
    if result["mode"] == "ai":
        _CACHE[key] = result
        if len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
    return {**result, "cached": False}
