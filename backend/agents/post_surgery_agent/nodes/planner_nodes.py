"""Specialist nodes of the post-surgery agent.

Each node reads shared state and returns only the key it owns, so the three
planners can run in parallel and be changed independently.
"""
from state import PostSurgeryState

from ..llm import SAFETY_RULES, ask


def _context(state: PostSurgeryState) -> str:
    return f"""
Operation: {state['operation']}

Patient history (pre-surgery module):
{state['patient_history']}

Pre-operative planning summary:
{state['preop_summary'] or 'Not available.'}

Intra-operative record:
{state['intraop_summary'] or 'Not recorded.'}

Current post-operative status reported by the surgeon:
{state['current_status'] or 'No issues reported.'}

Reference protocol for this operation (guideline based):
{state['reference_protocol']}
"""


def medication_planner_node(state: PostSurgeryState):
    """Specific post-operative medications tailored to the patient."""
    prompt = f"""You are a surgical pharmacology advisor.
Produce the post-operative MEDICATION plan: analgesia, antibiotics (only if indicated by the intra-operative findings), antiemetics, VTE prophylaxis, and chronic medications to resume, hold or adjust.
Explain briefly why for each item, and list medications to AVOID for this patient.
{SAFETY_RULES}
{_context(state)}"""
    return {"medication_plan": ask(prompt)}


def care_planner_node(state: PostSurgeryState):
    """Wound, drain, diet, activity, discharge criteria and follow-up."""
    prompt = f"""You are a surgical recovery nurse specialist.
Produce the post-operative CARE plan with these headings: Wound and drain care, Diet, Mobilisation and activity limits, Discharge criteria, Follow-up schedule.
Adapt to the approach used (laparoscopic/open), any drain, stoma or mesh, and the patient's comorbidities.
{SAFETY_RULES}
{_context(state)}"""
    return {"care_plan": ask(prompt)}


def monitoring_planner_node(state: PostSurgeryState):
    """Complications to watch for and when to escalate."""
    prompt = f"""You are a surgical safety officer.
Produce the MONITORING and ESCALATION plan: the most likely complications for this operation and this patient (considering what happened intra-operatively), what to monitor, warning signs for the patient to report, and clear triggers for urgent surgeon review.
{SAFETY_RULES}
{_context(state)}"""
    return {"monitoring_plan": ask(prompt)}


def accumulator_node(state: PostSurgeryState):
    """Merge the specialist plans into a single post-operative plan."""
    prompt = f"""Combine the three specialist plans into ONE concise post-operative recovery plan for the surgeon.
Use these markdown sections: ## Medications, ## Wound & Care, ## Diet & Activity, ## Discharge & Follow-up, ## Warning Signs & Escalation.
Remove duplication, resolve conflicts in favour of the more cautious option, and end with a short "Needs surgeon judgement" list of any uncertainties.
{SAFETY_RULES}

Operation: {state['operation']}

MEDICATION PLAN:
{state['medication_plan']}

CARE PLAN:
{state['care_plan']}

MONITORING PLAN:
{state['monitoring_plan']}
"""
    return {"postop_plan": ask(prompt)}
