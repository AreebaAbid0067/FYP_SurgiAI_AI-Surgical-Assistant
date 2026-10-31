"""Application data store: users, per-surgeon patient cases and audit trail.

Privacy: every case row carries its owner and every query filters on it, so a
surgeon can never read another surgeon's patients. Patient content is stored
only as an encrypted blob; the audit log never contains clinical content.
"""
import logging
import os
import re
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import security

DATABASE_PATH = Path(__file__).with_name("surgiai_app.sqlite3")
logger = logging.getLogger("surgiai.store")


@contextmanager
def _connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('surgeon', 'admin')),
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS patient_cases (
                case_id TEXT PRIMARY KEY,
                owner_id INTEGER NOT NULL REFERENCES users(user_id),
                procedure_id TEXT,
                stage TEXT NOT NULL DEFAULT 'pre',
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cases_owner ON patient_cases(owner_id);
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                case_id TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        has_admin = db.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone()
        configured = os.getenv("ADMIN_PASSWORD")
        if has_admin and configured:
            # Keep the admin credentials in sync with the environment configuration.
            db.execute(
                "UPDATE users SET username = ?, password_hash = ? WHERE role = 'admin'",
                (os.getenv("ADMIN_USERNAME", "admin").lower(), security.hash_password(configured)),
            )
    if not has_admin:
        password = os.getenv("ADMIN_PASSWORD")
        generated = password is None
        password = password or secrets.token_urlsafe(12)
        username = os.getenv("ADMIN_USERNAME", "admin")
        create_user(username, "SurgiAI Administrator", password, "admin")
        if generated:
            logger.warning(
                "Created admin account '%s' with one-time password: %s "
                "(set ADMIN_PASSWORD in .env to choose your own)",
                username, password,
            )


# ---- users -----------------------------------------------------------------
_USERNAME = re.compile(r"^[A-Za-z0-9_.@-]{3,40}$")


def create_user(username: str, full_name: str, password: str, role: str = "surgeon") -> dict:
    if not _USERNAME.match(username):
        raise ValueError("Username must be 3-40 characters (letters, numbers, . _ - @).")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    try:
        with _connect() as db:
            cursor = db.execute(
                "INSERT INTO users (username, full_name, role, password_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username.lower(), full_name.strip(), role, security.hash_password(password), _now()),
            )
            return get_user(cursor.lastrowid, db)
    except sqlite3.IntegrityError as exc:
        raise ValueError("That username is already taken.") from exc


def get_user(user_id: int, db=None) -> dict | None:
    query = "SELECT user_id, username, full_name, role FROM users WHERE user_id = ?"
    if db is not None:
        row = db.execute(query, (user_id,)).fetchone()
    else:
        with _connect() as connection:
            row = connection.execute(query, (user_id,)).fetchone()
    return dict(row) if row else None


def authenticate(username: str, password: str) -> dict | None:
    with _connect() as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (username.lower(),)).fetchone()
    if row is None:
        security.verify_password(password, "scrypt$AAAA$AAAA")  # keep timing similar
        return None
    if not security.verify_password(password, row["password_hash"]):
        return None
    return {k: row[k] for k in ("user_id", "username", "full_name", "role")}


# ---- audit -----------------------------------------------------------------
def audit(user_id: int | None, action: str, case_id: str | None = None) -> None:
    with _connect() as db:
        db.execute(
            "INSERT INTO audit_log (user_id, action, case_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, case_id, _now()),
        )


# ---- patient cases ---------------------------------------------------------
def build_history_text(intake: dict, notes: str = "") -> str:
    """Flatten structured intake into the plain text the AI agents consume."""
    lines = []
    labels = [
        ("age", "Age"), ("sex", "Sex"), ("urgency", "Urgency"), ("asa", "ASA class"),
        ("smoking", "Smoking"), ("alcohol", "Alcohol"), ("prior_surgery", "Prior surgery"),
    ]
    for key, label in labels:
        if intake.get(key):
            lines.append(f"{label}: {intake[key]}")
    lists = [
        ("symptoms", "Presenting features"), ("comorbidities", "Comorbidities"),
        ("allergies", "Allergies"), ("medications", "Current medications"),
        ("custom_comorbidities", "Other conditions"), ("custom_allergies", "Other allergies"),
        ("custom_medications", "Other medications"),
    ]
    for key, label in lists:
        values = intake.get(key) or []
        if values:
            lines.append(f"{label}: {', '.join(values)}")
    if notes and notes.strip():
        lines.append(f"Additional notes: {notes.strip()}")
    return "\n".join(lines) or "No history provided."


def _summary(row: sqlite3.Row, payload: dict) -> dict:
    return {
        "case_id": row["case_id"],
        "stage": row["stage"],
        "patient_label": payload.get("patient_label", ""),
        "procedure_id": row["procedure_id"],
        "procedure_name": payload.get("procedure_name", ""),
        "has_preop": bool(payload.get("preop_report")),
        "has_intraop": bool(payload.get("intraop", {}).get("summary")),
        "has_postop": bool(payload.get("postop")),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_case(owner_id: int, patient_label: str, procedure_id: str | None,
                procedure_name: str, intake: dict, notes: str) -> dict:
    payload = {
        "patient_label": patient_label.strip(),
        "procedure_name": procedure_name.strip(),
        "intake": intake,
        "notes": notes,
        "history_text": build_history_text(intake, notes),
        "preop_report": "",
        "intraop": {"summary": None, "notes": []},
        "postop": None,
    }
    case_id = uuid.uuid4().hex
    now = _now()
    with _connect() as db:
        db.execute(
            "INSERT INTO patient_cases (case_id, owner_id, procedure_id, stage, payload, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pre', ?, ?, ?)",
            (case_id, owner_id, procedure_id, security.encrypt_json(payload), now, now),
        )
    audit(owner_id, "case.create", case_id)
    return get_case(case_id, owner_id)


def list_cases(owner_id: int) -> list[dict]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM patient_cases WHERE owner_id = ? ORDER BY updated_at DESC", (owner_id,)
        ).fetchall()
    return [_summary(row, security.decrypt_json(row["payload"])) for row in rows]


def get_case(case_id: str, owner_id: int) -> dict | None:
    """Return the case only if it belongs to `owner_id`."""
    with _connect() as db:
        row = db.execute(
            "SELECT * FROM patient_cases WHERE case_id = ? AND owner_id = ?", (case_id, owner_id)
        ).fetchone()
    if row is None:
        return None
    payload = security.decrypt_json(row["payload"])
    return {**_summary(row, payload), "data": payload}


def update_case(case_id: str, owner_id: int, changes: dict, stage: str | None = None) -> dict | None:
    case = get_case(case_id, owner_id)
    if case is None:
        return None
    payload = {**case["data"], **changes}
    with _connect() as db:
        db.execute(
            "UPDATE patient_cases SET payload = ?, updated_at = ?, stage = COALESCE(?, stage) "
            "WHERE case_id = ? AND owner_id = ?",
            (security.encrypt_json(payload), _now(), stage, case_id, owner_id),
        )
    return get_case(case_id, owner_id)


def delete_case(case_id: str, owner_id: int) -> bool:
    with _connect() as db:
        cursor = db.execute(
            "DELETE FROM patient_cases WHERE case_id = ? AND owner_id = ?", (case_id, owner_id)
        )
    if cursor.rowcount:
        audit(owner_id, "case.delete", case_id)
    return bool(cursor.rowcount)


def platform_stats() -> dict:
    """Aggregate, non-identifying counts for the admin NFR view."""
    with _connect() as db:
        users = db.execute("SELECT role, COUNT(*) c FROM users GROUP BY role").fetchall()
        cases = db.execute("SELECT COUNT(*) FROM patient_cases").fetchone()[0]
    return {"users": {r["role"]: r["c"] for r in users}, "cases": cases}


def security_summary(user_id: int) -> dict:
    """What the signed-in user can verify about their own data: counts, encryption and access history."""
    with _connect() as db:
        rows = db.execute("SELECT payload FROM patient_cases WHERE owner_id = ?", (user_id,)).fetchall()
        activity = db.execute(
            "SELECT action, case_id, created_at FROM audit_log WHERE user_id = ? ORDER BY id DESC LIMIT 25",
            (user_id,),
        ).fetchall()
    readable = sum(1 for row in rows if "patient_label" in row["payload"])
    return {
        "case_count": len(rows),
        "cases_encrypted": len(rows) - readable,
        "cases_readable_in_storage": readable,
        "activity": [
            {"action": a["action"], "case": (a["case_id"] or "")[:8], "at": a["created_at"]} for a in activity
        ],
    }
