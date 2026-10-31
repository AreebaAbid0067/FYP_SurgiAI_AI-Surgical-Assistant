import io
import logging
import os
import tempfile
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from groq import AuthenticationError
from PIL import Image
from pydantic import BaseModel, Field

import nfr
import post_surgery_service
import procedures
import security
import store
import verification
from security import current_user, require_admin, require_surgeon

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("surgiai")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
AI_UNAVAILABLE = (
    "Clinical AI assistance is temporarily unavailable. No guidance was generated; "
    "please rely on your clinical judgement and local protocols, then try again shortly."
)


# ---- request models --------------------------------------------------------
class DuringSurgery(BaseModel):
    surgeon_query: str = Field(min_length=1, max_length=4000)
    patient_history: str = Field(default="", max_length=20000)
    case_id: str | None = None


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class Registration(Credentials):
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class NewCase(BaseModel):
    patient_label: str = Field(min_length=1, max_length=120)
    procedure_id: str | None = None
    procedure_name: str = Field(min_length=2, max_length=160)
    intake: dict = Field(default_factory=dict)
    notes: str = Field(default="", max_length=8000)


class IntraopSummary(BaseModel):
    summary: dict


class PostSurgeryRequest(BaseModel):
    current_status: str = Field(default="", max_length=2000)


class SuggestRequest(BaseModel):
    symptoms: list[str] = Field(default_factory=list, max_length=30)
    free_text: str = Field(default="", max_length=500)


class VerificationReview(BaseModel):
    run_id: int
    status: Literal["pass", "partial", "fail", "needs_expert_review"]
    reviewer_name: str = Field(min_length=1, max_length=160)
    comments: str = Field(default="", max_length=5000)
    harmful_error: bool = False
    reference_answer: str = Field(default="", max_length=12000)
    source_notes: str = Field(default="", max_length=4000)
    reference_approved: bool = False


class VerificationSignoff(BaseModel):
    reviewer_name: str = Field(min_length=1, max_length=160)
    clinician_attested: bool


# ---- app setup -------------------------------------------------------------
app = FastAPI(title="SurgiAI API", docs_url=None, redoc_url=None)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

_WINDOWS: dict[str, deque] = defaultdict(deque)


def rate_limit(key: str, limit: int, window: int = 60) -> None:
    now = time.monotonic()
    hits = _WINDOWS[key]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment and try again.")
    hits.append(now)


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def timing_and_security_headers(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    response.headers["X-Process-Time"] = f"{elapsed:.3f}"
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    nfr.record_latency(request.url.path, elapsed)
    # Only method, path and timing are logged - never bodies or patient data.
    logger.info("%s %s -> %s in %.2fs", request.method, request.url.path, response.status_code, elapsed)
    return response


@app.on_event("startup")
def startup():
    store.initialize()
    verification.initialize()


@app.exception_handler(AuthenticationError)
async def groq_auth_error(request: Request, exc: AuthenticationError):
    logger.error("Groq rejected the configured API key")
    return JSONResponse(status_code=503, content={"status": "error", "message": AI_UNAVAILABLE, "detail": AI_UNAVAILABLE})


# ---- public ------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to SurgiAI"}


@app.get("/health")
def health():
    return nfr.health()


# ---- authentication --------------------------------------------------------
@app.post("/auth/login")
def login(credentials: Credentials, request: Request):
    rate_limit(f"login:{request.client.host if request.client else 'unknown'}", limit=10)
    user = store.authenticate(credentials.username, credentials.password)
    if user is None:
        store.audit(None, "login.failed")
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    store.audit(user["user_id"], "login.success")
    return {"token": security.create_token(user["user_id"], user["role"]), "user": user}


@app.post("/auth/register")
def register(registration: Registration, request: Request):
    rate_limit(f"register:{request.client.host if request.client else 'unknown'}", limit=5)
    try:
        user = store.create_user(registration.username, registration.full_name, registration.password, "surgeon")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.audit(user["user_id"], "user.register")
    return {"token": security.create_token(user["user_id"], user["role"]), "user": user}


@app.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return user


# ---- procedure catalogue ---------------------------------------------------
@app.get("/procedures")
def procedure_catalog(user: dict = Depends(require_surgeon)):
    return procedures.procedure_catalog()


@app.post("/procedures/suggest")
def suggest(body: SuggestRequest, user: dict = Depends(require_surgeon)):
    return {"suggestions": procedures.suggest_procedures(body.symptoms, body.free_text)}


# ---- patient cases (per-surgeon isolation) ---------------------------------
def _own_case(case_id: str, user: dict) -> dict:
    case = store.get_case(case_id, user["user_id"])
    if case is None:
        # Identical response for "missing" and "someone else's" so ids cannot be probed.
        raise HTTPException(status_code=404, detail="Patient case not found.")
    return case


@app.get("/cases")
def list_cases(user: dict = Depends(require_surgeon)):
    return store.list_cases(user["user_id"])


@app.post("/cases")
def create_case(body: NewCase, user: dict = Depends(require_surgeon)):
    return store.create_case(
        user["user_id"], body.patient_label, body.procedure_id,
        body.procedure_name, body.intake, body.notes,
    )


@app.get("/cases/{case_id}")
def get_case(case_id: str, user: dict = Depends(require_surgeon)):
    case = _own_case(case_id, user)
    store.audit(user["user_id"], "case.view", case_id)
    return case


@app.delete("/cases/{case_id}")
def delete_case(case_id: str, user: dict = Depends(require_surgeon)):
    _own_case(case_id, user)
    store.delete_case(case_id, user["user_id"])
    return {"deleted": True}


@app.post("/cases/{case_id}/intraop-summary")
def save_intraop_summary(case_id: str, body: IntraopSummary, user: dict = Depends(require_surgeon)):
    case = _own_case(case_id, user)
    intraop = {**case["data"].get("intraop", {"notes": []}), "summary": body.summary}
    return store.update_case(case_id, user["user_id"], {"intraop": intraop}, stage="intra")


@app.post("/cases/{case_id}/post-surgery")
def post_surgery(case_id: str, body: PostSurgeryRequest, user: dict = Depends(require_surgeon)):
    rate_limit(f"ai:{user['user_id']}", limit=20)
    case = _own_case(case_id, user)
    result = post_surgery_service.generate(case["data"], case["procedure_id"], body.current_status)
    store.update_case(
        case_id, user["user_id"],
        {"postop": {"plan": result["plan"], "mode": result["mode"], "status": body.current_status}},
        stage="post",
    )
    store.audit(user["user_id"], "postop.generate", case_id)
    return result


# ---- during surgery --------------------------------------------------------
def _generate_surgical_answer(surgeon_query: str, patient_history: str):
    from agents.surgery_agent.surgery_agent import surgical_agent

    state = {
        "surgeon_query": surgeon_query,
        "patient_history": patient_history,
        "conversation": [],
        "messages": [],
        "insight_accumulator_response": "",
        "max_iteration": 2,
        "current_iteration": 0,
        "search_query": "",
        "retrieved_context": "",
    }
    return surgical_agent(state)


@app.post("/surgery")
def surgical_query(body: DuringSurgery, user: dict = Depends(require_surgeon)):
    rate_limit(f"ai:{user['user_id']}", limit=30)
    history = body.patient_history
    case = None
    if body.case_id:
        case = _own_case(body.case_id, user)
        history = case["data"]["history_text"]
    try:
        answer = _generate_surgical_answer(body.surgeon_query, history)
    except Exception as exc:
        logger.exception("During-surgery assistant failed")
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE) from exc
    if case is not None and isinstance(answer, str):
        intraop = case["data"].get("intraop", {"summary": None, "notes": []})
        notes = [*intraop.get("notes", []), {"question": body.surgeon_query, "answer": answer}][-20:]
        store.update_case(body.case_id, user["user_id"], {"intraop": {**intraop, "notes": notes}}, stage="intra")
    return answer


# ---- pre surgery -----------------------------------------------------------
def _read_image(upload: UploadFile | None, label: str) -> bytes | None:
    if upload is None or not upload.filename:
        return None
    content = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{label} is larger than 10 MB.")
    try:
        Image.open(io.BytesIO(content)).verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{label} is not a valid image.") from exc
    return content


@app.post("/pre-surgery/upload")
def upload_files(
    operation: str = Form(..., max_length=160),
    patient_history: str = Form("", max_length=20000),
    case_id: str | None = Form(None),
    prescription: UploadFile | None = File(None),
    scan: UploadFile | None = File(None),
    lab_report: UploadFile | None = File(None),
    user: dict = Depends(require_surgeon),
):
    rate_limit(f"ai:{user['user_id']}", limit=20)
    case = _own_case(case_id, user) if case_id else None
    if case is not None:
        patient_history = case["data"]["history_text"]

    from analyzers.lab_reports_analyzer import lab_reports_analyzer
    from analyzers.prescription_analyzer import prescription_analyzer
    from analyzers.scans_analyzer import scans_analyzer
    from agents.pre_surgery_agent.surgical_procedure_agent import pre_surgical_report_agent

    files = {
        "prescription": (_read_image(prescription, "Prescription"), prescription_analyzer),
        "scan": (_read_image(scan, "Scan"), scans_analyzer),
        "lab_report": (_read_image(lab_report, "Lab report"), lab_reports_analyzer),
    }
    not_provided = "Not provided by the surgeon."

    try:
        # Files live only in a private temp folder that is deleted afterwards.
        with tempfile.TemporaryDirectory() as workdir:
            def analyse(item):
                name, (content, analyzer) = item
                if content is None:
                    return name, not_provided
                path = Path(workdir) / f"{name}.jpg"
                path.write_bytes(content)
                return name, analyzer(str(path))

            with ThreadPoolExecutor(max_workers=3) as pool:
                reports = dict(pool.map(analyse, files.items()))

        state = {
            "prescription_report": reports["prescription"],
            "scan_report": reports["scan"],
            "lab_report": reports["lab_report"],
            "operation": operation,
            "patient_history": patient_history or "No history provided.",
            "prescription_report_analyzer_node": "",
            "lab_report_analyzer_node": "",
            "scan_report_analyzer_node": "",
            "instrumentation_report": "",
            "risk_analyzer_report": "",
            "anesthesia_consultant_report": "",
            "surgical_workflow_report": "",
            "emergency_protocol_advicer": "",
            "accumulator": "",
        }
        report = pre_surgical_report_agent(state)
    except HTTPException:
        raise
    except AuthenticationError:
        raise
    except Exception as exc:
        logger.exception("Pre-surgery report generation failed")
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE) from exc

    if case is not None:
        store.update_case(case_id, user["user_id"], {"preop_report": report}, stage="pre")
        store.audit(user["user_id"], "preop.generate", case_id)
    return report


@app.post("/pre-surgery/history-from-document")
def history_from_document(
    document: UploadFile = File(...),
    user: dict = Depends(require_surgeon),
):
    rate_limit(f"ai:{user['user_id']}", limit=20)
    content_type = document.content_type or ""
    allowed = content_type.startswith("image/") or content_type in {"application/pdf", "text/plain"}
    if not allowed:
        raise HTTPException(status_code=415, detail="Upload an image, PDF or text file.")
    content = document.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The document is larger than 10 MB.")
    from analyzers.history_document_analyzer import extract_history

    try:
        return extract_history(content, content_type, procedures.COMMON_INTAKE)
    except AuthenticationError:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("History extraction failed")
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE) from exc


# ---- verification (administrators only) -----------------------------------
@app.get("/verification")
def verification_dashboard(case_id: str = verification.CASE_ID, admin: dict = Depends(require_admin)):
    try:
        return verification.get_dashboard(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/verification/questions/{question_id}/run")
def run_verification_question(question_id: int, admin: dict = Depends(require_admin)):
    question = verification.get_question(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Verification question not found.")
    try:
        answer = _generate_surgical_answer(question["prompt"], verification.PATIENT_CONTEXT)
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("The SurgiAI pipeline returned an empty answer.")
        run_id = verification.save_run(question_id, answer)
        return {"run_id": run_id, "question_id": question_id, "response": answer}
    except Exception as exc:
        logger.exception("SurgiAI verification run failed for question %s", question_id)
        raise HTTPException(
            status_code=502,
            detail="Could not generate and save a SurgiAI response for this test. Check backend logs and try again.",
        ) from exc


@app.post("/verification/questions/{question_id}/review")
def review_verification_question(
    question_id: int, review: VerificationReview, admin: dict = Depends(require_admin)
):
    question = verification.get_question(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Verification question not found.")
    try:
        verification.save_assessment(
            question_id=question_id,
            run_id=review.run_id,
            status=review.status,
            reviewer_name=review.reviewer_name,
            comments=review.comments,
            harmful_error=review.harmful_error,
            reference_answer=review.reference_answer,
            source_notes=review.source_notes,
            reference_approved=review.reference_approved,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return verification.get_dashboard(question["case_id"])


@app.post("/verification/cases/{case_id}/signoff")
def signoff_verification_case(case_id: str, signoff: VerificationSignoff, admin: dict = Depends(require_admin)):
    try:
        verification.sign_off(case_id, signoff.reviewer_name, signoff.clinician_attested)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return verification.get_dashboard(case_id)


@app.get("/verification/report.csv")
def verification_report(admin: dict = Depends(require_admin)):
    return Response(
        content=verification.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="surgiai-verification-report.csv"'},
    )


# ---- administration --------------------------------------------------------
@app.get("/admin/nfr")
def admin_nfr(admin: dict = Depends(require_admin)):
    return nfr.compliance_report(store.platform_stats(), allowed_origins)


@app.post("/admin/nfr/self-check")
def admin_nfr_self_check(admin: dict = Depends(require_admin)):
    store.audit(admin["user_id"], "nfr.self_check")
    return nfr.run_self_checks(rate_limit, SECURITY_HEADERS, allowed_origins)


# ---- own security summary (any signed-in user) ------------------------------
@app.get("/me/security")
def my_security(user: dict = Depends(current_user)):
    return store.security_summary(user["user_id"])
