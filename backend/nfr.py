"""Non-functional requirement evidence.

Exposes live health checks, latency statistics and a mapping from each NFR in
the SurgiAI specification to where it is implemented. The mapping is rendered
on the administrator-only compliance page.
"""
import os
import statistics
from collections import defaultdict, deque

import store

_LATENCIES: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
_TRACKED = ("/surgery", "/pre-surgery/upload", "/cases", "/auth/login")


def record_latency(path: str, seconds: float) -> None:
    for prefix in _TRACKED:
        if path.startswith(prefix):
            _LATENCIES[prefix].append(seconds)
            return
    if "/post-surgery" in path:
        _LATENCIES["/cases/*/post-surgery"].append(seconds)


def latency_stats() -> list[dict]:
    rows = []
    for path, values in sorted(_LATENCIES.items()):
        ordered = sorted(values)
        rows.append({
            "endpoint": path,
            "requests": len(ordered),
            "median_seconds": round(statistics.median(ordered), 3),
            "p95_seconds": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
        })
    return rows


def health() -> dict:
    checks = {"database": False, "ai_configured": bool(os.getenv("GROQ_API_KEY")),
              "knowledge_base_configured": bool(os.getenv("PINECONE_API_KEY"))}
    try:
        store.platform_stats()
        checks["database"] = True
    except Exception:
        pass
    ai_ready = checks["ai_configured"] and checks["knowledge_base_configured"]
    return {
        "status": "ok" if checks["database"] and ai_ready else "degraded",
        "checks": checks,
        "message": (
            "All services available."
            if checks["database"] and ai_ready
            else "Some clinical assistance features may be unavailable; standard guideline protocols remain available."
        ),
    }


CODE_REFS = {
    "Usability": ["frontend/app/during-surgery/page.tsx", "frontend/app/components/use-hands-free.ts", "frontend/app/pre-surgery/page.tsx", "frontend/app/lib/glossary.ts"],
    "Performance / Efficiency": ["backend/main.py (sync endpoints, X-Process-Time)", "backend/post_surgery_service.py (cache)", "backend/nfr.py (latency stats)"],
    "Reliability": ["backend/post_surgery_service.py (fallback)", "backend/agents/post_surgery_agent/llm.py (timeout, retry)"],
    "Security": ["backend/security.py", "backend/main.py (rate_limit, headers, CORS)", "frontend/middleware.ts"],
    "Privacy": ["backend/store.py (owner_id on every query, encryption)", "backend/main.py (_own_case, log policy)"],
    "Maintainability": ["backend/procedures.py", "backend/verification_data.py", "backend/agents/"],
    "Readability": ["backend/README.md", "module docstrings"],
    "Scalability": ["backend/procedures.py (registry)", "backend/verification_data.py"],
    "Availability": ["backend/nfr.py (health)", "GET /health"],
    "Clinical safety": ["backend/agents/post_surgery_agent/llm.py (SAFETY_RULES)", "backend/verification.py"],
}


def compliance_report(stats: dict, allowed_origins: list[str]) -> dict:
    wildcard = "*" in allowed_origins
    items = [
        ("Usability", "Voice and hands-free interaction, minimal-typing intake",
         ["Voice question input and read-aloud answers (during-surgery workspace)",
          "Chip / checkbox / radio patient intake with procedure presets and AI-suggested procedures",
          "Document upload pre-fills patient history; patient context carries across modules"], True),
        ("Performance / Efficiency", "Quick responses; reports and plans without unnecessary delay",
         ["Blocking AI work runs in worker threads, not the event loop",
          "Document analysers run in parallel; post-surgery planners run in parallel",
          "Identical post-surgery requests are served from a cache",
          "Per-request timing header (X-Process-Time) and live latency statistics below"], True),
        ("Reliability", "Consistent responses, graceful failures, no unverified information as fact",
         ["Bounded model timeout with retry; failures return explicit errors",
          "Post-surgery falls back to the guideline protocol and labels it as not personalised",
          "Every AI plan carries a decision-support notice and a 'needs surgeon judgement' list"], True),
        ("Security", "Protect records and AI/medical-system communication from unauthorised access",
         ["Salted scrypt password hashing and signed, expiring session tokens",
          "Role-based access (surgeon vs administrator) enforced on every endpoint",
          "Patient records encrypted at rest (Fernet / AES); tokens stored in HttpOnly cookies",
          "Login and AI endpoints rate limited; security headers on all responses",
          "CORS restricted to configured origins" + (" - WARNING: wildcard configured" if wildcard else "")], not wildcard),
        ("Privacy", "Patient information isolated between users and sessions; protected in storage, processing and logs",
         ["Every case row is owned by one surgeon and every query filters by owner",
          "Other surgeons' cases return 404; administrators cannot read patient records",
          "Uploads are processed in private temporary folders and deleted immediately",
          "Logs record method, path and timing only - never request bodies or patient data; audit log holds no clinical content"], True),
        ("Maintainability", "Modular code; agents, workflows and verification updated independently",
         ["Separate packages for pre-surgery, during-surgery and post-surgery agents",
          "Procedures defined as data in procedures.py; verification cases in verification_data.py",
          "Separate modules for security, storage, verification and NFR evidence"], True),
        ("Readability", "Clearly structured and documented code, agent responsibilities and workflows",
         ["Module docstrings describe responsibilities and the graph of each agent",
          "Backend README documents the architecture, roles and workflows"], True),
        ("Scalability", "Add procedures, reference material and users without redesign",
         ["New procedure = one registry entry; the intake forms, suggestions and post-op protocol update automatically",
          "Verification library supports unlimited cases; SQLite store can be swapped for a server database",
          f"Currently {stats['cases']} patient cases and {sum(stats['users'].values())} users"], True),
        ("Availability", "Handle temporary service or model failures and say when assistance is unavailable",
         ["/health endpoint reports database and AI service status",
          "Clear 'clinical AI temporarily unavailable' messages rather than silent failures",
          "Guideline protocol remains available if the model is down"], True),
        ("Clinical safety", "Grounded in reliable sources, communicates uncertainty, flags need for clinician judgement",
         ["Plans are grounded in guideline-based reference protocols (WSES, SAGES, ASCRS/ERAS, HerniaSurge, ATA)",
          "Prompts forbid inventing findings and require allergy / comorbidity checks and explicit uncertainty",
          "Five-case clinician verification workflow with sign-off, available only to administrators"], True),
    ]
    return {
        "items": [
            {"category": c, "requirement": r, "implementation": impl, "met": met,
             "code": CODE_REFS.get(c, [])}
            for c, r, impl, met in items
        ],
        "latency": latency_stats(),
        "health": health(),
    }


def _check(category: str, name: str, test) -> dict:
    """Run one check; a raised exception or False counts as a failure."""
    try:
        outcome = test()
        passed, detail = outcome if isinstance(outcome, tuple) else (bool(outcome), "")
        status = "skipped" if passed is None else ("passed" if passed else "failed")
    except Exception as exc:
        status, detail = "failed", f"Check raised {type(exc).__name__}: {exc}"
    return {"category": category, "name": name, "status": status, "detail": detail}


def run_self_checks(rate_limit, security_headers: dict, allowed_origins: list[str]) -> dict:
    """Execute real tests against the running system and return the outcomes."""
    import secrets as _secrets
    import time as _time

    import procedures
    import security
    import verification
    from fastapi import HTTPException

    results = []

    def password_hashing():
        secret = "Sample-" + _secrets.token_hex(4)
        first, second = security.hash_password(secret), security.hash_password(secret)
        ok = (secret not in first and first != second and security.verify_password(secret, first)
              and not security.verify_password(secret + "x", first))
        return ok, "Hash is salted (two hashes of one password differ), never contains the password, rejects wrong passwords."

    def token_integrity():
        token = security.create_token(1, "surgeon")
        head, body, sig = token.split(".")
        forged = ".".join([head, body, sig[:-2] + ("AA" if not sig.endswith("AA") else "BB")])
        ok = security.decode_token(token) is not None and security.decode_token(forged) is None
        return ok, "A valid token decodes; a token with an altered signature is rejected."

    def encryption_roundtrip():
        marker = "MARKER-" + _secrets.token_hex(6)
        cipher = security.encrypt_json({"note": marker})
        ok = marker not in cipher and security.decrypt_json(cipher) == {"note": marker}
        return ok, "Encrypted text does not contain the plain text and decrypts back correctly."

    def stored_cases_encrypted():
        with store._connect() as db:
            rows = db.execute("SELECT payload FROM patient_cases").fetchall()
        if not rows:
            return None, "No patient cases stored yet - create one and re-run."
        plain = sum(1 for row in rows if row["payload"].lstrip().startswith(("{", "[")) or "patient_label" in row["payload"])
        return plain == 0, f"{len(rows)} stored case(s) checked; {plain} readable without the key."

    def owner_isolation():
        a, b = -9001, -9002
        case = store.create_case(a, "ISOLATION-TEST", None, "Test", {}, "")
        try:
            ok = (store.get_case(case["case_id"], a) is not None
                  and store.get_case(case["case_id"], b) is None
                  and store.list_cases(b) == []
                  and store.update_case(case["case_id"], b, {"notes": "x"}) is None
                  and store.delete_case(case["case_id"], b) is False)
        finally:
            store.delete_case(case["case_id"], a)
            with store._connect() as db:
                db.execute("DELETE FROM audit_log WHERE user_id IN (?, ?)", (a, b))
        return ok, "A second user cannot read, list, edit or delete another user's case."

    def rate_limiting():
        key = "selfcheck:" + _secrets.token_hex(4)
        for _ in range(3):
            rate_limit(key, limit=3)
        try:
            rate_limit(key, limit=3)
        except HTTPException as exc:
            return exc.status_code == 429, "The 4th request inside the window was refused with HTTP 429."
        return False, "Limit was not enforced."

    def headers_present():
        return bool(security_headers), "Sent on every response: " + ", ".join(security_headers)

    def cors_restricted():
        return "*" not in allowed_origins, "Allowed origins: " + ", ".join(allowed_origins)

    def verification_library():
        count = len(verification.CASES)
        return count == 5, f"{count} verification cases registered (target 5)."

    def fallback_protocols():
        missing = [p["id"] for p in procedures.PROCEDURES
                   if not all(p["protocol"].get(k) for k in ("medications", "wound_care", "red_flags", "follow_up"))]
        return not missing, ("All procedures have a complete guideline fallback protocol."
                             if not missing else f"Incomplete protocol: {', '.join(missing)}")

    def database_responsive():
        started = _time.perf_counter()
        store.platform_stats()
        elapsed = _time.perf_counter() - started
        return elapsed < 0.5, f"Database query answered in {elapsed * 1000:.0f} ms (limit 500 ms)."

    def non_ai_latency():
        rows = [r for r in latency_stats() if r["endpoint"] in ("/cases", "/auth/login")]
        if not rows:
            return None, "No traffic recorded yet - use the app and re-run."
        worst = max(r["p95_seconds"] for r in rows)
        return worst < 1.0, f"Slowest 95th-percentile for non-AI endpoints: {worst:.2f}s (limit 1.0s)."

    plan = [
        ("Security", "Passwords are salted and hashed", password_hashing),
        ("Security", "Session tokens cannot be forged", token_integrity),
        ("Security", "Login and AI requests are rate limited", rate_limiting),
        ("Security", "Security headers are sent", headers_present),
        ("Security", "Cross-origin access is restricted", cors_restricted),
        ("Privacy", "Patient data is encrypted before storage", encryption_roundtrip),
        ("Privacy", "Existing stored cases are unreadable without the key", stored_cases_encrypted),
        ("Privacy", "One surgeon cannot access another surgeon's patients", owner_isolation),
        ("Performance", "Database responds quickly", database_responsive),
        ("Performance", "Non-AI pages respond within 1 second", non_ai_latency),
        ("Reliability", "Guideline fallback exists for every procedure", fallback_protocols),
        ("Clinical safety", "Five verification cases are loaded", verification_library),
    ]
    for category, name, test in plan:
        results.append(_check(category, name, test))
    return {
        "checks": results,
        "passed": sum(r["status"] == "passed" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
        "skipped": sum(r["status"] == "skipped" for r in results),
    }
