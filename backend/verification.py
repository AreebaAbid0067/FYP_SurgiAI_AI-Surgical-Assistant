import csv
import io
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from verification_data import CASES, PATIENT_CONTEXT


DATABASE_PATH = Path(__file__).with_name("clinical_verification.sqlite3")
CASE_ID = CASES[0]["case_id"]  # default case (appendectomy pilot)

PHASES = ("preoperative", "intraoperative", "postoperative")


@contextmanager
def _connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize():
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                procedure TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                signoff_reviewer TEXT,
                signoff_at TEXT,
                signoff_attested INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES cases(case_id),
                phase TEXT NOT NULL,
                prompt TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                UNIQUE(case_id, phase, sort_order)
            );
            CREATE TABLE IF NOT EXISTS source_references (
                source_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(case_id),
                title TEXT NOT NULL,
                version TEXT NOT NULL,
                url TEXT NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'pending_clinician_review'
            );
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL REFERENCES questions(question_id),
                response TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS reviewer_assessments (
                assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL REFERENCES questions(question_id),
                run_id INTEGER NOT NULL REFERENCES evaluation_runs(run_id),
                status TEXT NOT NULL,
                reviewer_name TEXT NOT NULL,
                comments TEXT NOT NULL DEFAULT '',
                harmful_error INTEGER NOT NULL DEFAULT 0,
                reference_answer TEXT NOT NULL DEFAULT '',
                source_notes TEXT NOT NULL DEFAULT '',
                reference_approved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        question_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(questions)")
        }
        if "expected_answer" not in question_columns:
            connection.execute(
                "ALTER TABLE questions ADD COLUMN expected_answer TEXT NOT NULL DEFAULT ''"
            )
        for case in CASES:
            connection.execute(
                """
                INSERT OR IGNORE INTO cases (case_id, title, procedure, summary)
                VALUES (?, ?, ?, ?)
                """,
                (case["case_id"], case["title"], case["procedure"], case["summary"]),
            )
            for order, (phase, prompt, expected) in enumerate(case["questions"], start=1):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO questions
                        (case_id, phase, prompt, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (case["case_id"], phase, prompt, order),
                )
                connection.execute(
                    "UPDATE questions SET expected_answer = ? WHERE case_id = ? AND sort_order = ?",
                    (expected, case["case_id"], order),
                )
            for source in case["sources"]:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO source_references
                        (source_id, case_id, title, version, url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (source[0], case["case_id"], source[1], source[2], source[3]),
                )


def _dict_or_none(row):
    return dict(row) if row is not None else None


def _case_overview(connection):
    rows = connection.execute(
        """
        SELECT c.case_id, c.title, c.procedure, c.signoff_reviewer, c.signoff_at,
            (SELECT COUNT(*) FROM questions q WHERE q.case_id = c.case_id) AS question_count,
            (SELECT COUNT(DISTINCT r.question_id) FROM evaluation_runs r
                JOIN questions q ON q.question_id = r.question_id
                WHERE q.case_id = c.case_id) AS tested_count,
            (SELECT COUNT(*) FROM questions q WHERE q.case_id = c.case_id
                AND (SELECT a.status FROM reviewer_assessments a
                     WHERE a.question_id = q.question_id
                     ORDER BY a.assessment_id DESC LIMIT 1) IN ('pass', 'partial', 'fail')
            ) AS reviewed_count
        FROM cases c ORDER BY c.rowid
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_dashboard(case_id=CASE_ID):
    initialize()
    with _connect() as connection:
        case = _dict_or_none(
            connection.execute(
                "SELECT * FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        )
        if case is None:
            raise ValueError("Unknown verification case.")
        overview = _case_overview(connection)
        rows = connection.execute(
            """
            SELECT q.*,
                (SELECT COUNT(*) FROM evaluation_runs r
                 WHERE r.question_id = q.question_id) AS run_count,
                (SELECT r.response FROM evaluation_runs r
                 WHERE r.question_id = q.question_id
                 ORDER BY r.run_id DESC LIMIT 1) AS latest_response,
                (SELECT r.run_id FROM evaluation_runs r
                 WHERE r.question_id = q.question_id
                 ORDER BY r.run_id DESC LIMIT 1) AS latest_run_id,
                (SELECT r.created_at FROM evaluation_runs r
                 WHERE r.question_id = q.question_id
                 ORDER BY r.run_id DESC LIMIT 1) AS latest_run_at,
                (SELECT a.status FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS review_status,
                (SELECT a.reviewer_name FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS reviewer_name,
                (SELECT a.comments FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS review_comments,
                (SELECT a.harmful_error FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS harmful_error,
                (SELECT a.reference_answer FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS reference_answer,
                (SELECT a.source_notes FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS source_notes,
                (SELECT a.reference_approved FROM reviewer_assessments a
                 WHERE a.question_id = q.question_id
                 ORDER BY a.assessment_id DESC LIMIT 1) AS reference_approved
            FROM questions q
            WHERE q.case_id = ?
            ORDER BY q.sort_order
            """,
            (case_id,),
        ).fetchall()
        questions = [dict(row) for row in rows]
        sources = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM source_references WHERE case_id = ? ORDER BY source_id",
                (case_id,),
            ).fetchall()
        ]
        completed_statuses = {"pass", "partial", "fail"}
        completed = [
            q for q in questions if q["review_status"] in completed_statuses
        ]
        approved_references = sum(
            bool(q["reference_approved"]) for q in questions
        )
        evaluated = sum(q["run_count"] > 0 for q in questions)
        pending = sum(
            q["review_status"] is None
            or q["review_status"] == "needs_expert_review"
            for q in questions
        )
        return {
            "case": case,
            "cases": overview,
            "questions": questions,
            "sources": sources,
            "metrics": {
                "case_count": len(overview),
                "case_target": 200,
                "cases_reviewed": sum(bool(c["signoff_at"]) for c in overview),
                "cases_with_reference": sum(c["question_count"] > 0 for c in overview),
                "questions_tested": evaluated,
                "questions_reviewed": len(completed),
                "pending_reviews": pending,
                "pass_count": sum(q["review_status"] == "pass" for q in completed),
                "partial_count": sum(q["review_status"] == "partial" for q in completed),
                "fail_count": sum(q["review_status"] == "fail" for q in completed),
                "critical_errors": sum(
                    bool(q["harmful_error"])
                    for q in completed
                ),
                "approved_references": approved_references,
                "reference_count": len(questions),
                "expert_approval": (
                    "Approved"
                    if case["signoff_at"]
                    else "Pending"
                ),
                "report_status": (
                    "Complete"
                    if case["signoff_at"]
                    else "In progress"
                ),
            },
        }


def get_question(question_id):
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM questions WHERE question_id = ?",
            (question_id,),
        ).fetchone()
        return _dict_or_none(row)


def save_run(question_id, response):
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT INTO evaluation_runs (question_id, response) VALUES (?, ?)",
            (question_id, response),
        )
        return cursor.lastrowid


def save_assessment(
    question_id,
    run_id,
    status,
    reviewer_name,
    comments,
    harmful_error,
    reference_answer,
    source_notes,
    reference_approved,
):
    if not reviewer_name.strip():
        raise ValueError("Reviewer name is required.")
    with _connect() as connection:
        run = connection.execute(
            """
            SELECT MAX(run_id) AS latest_run_id FROM evaluation_runs
            WHERE question_id = ?
            """,
            (question_id,),
        ).fetchone()
        if run["latest_run_id"] is None:
            raise ValueError("Run a real SurgiAI answer before reviewing it.")
        if run_id != run["latest_run_id"]:
            raise ValueError("Review the latest saved SurgiAI response for this question.")
        if reference_approved and (not reference_answer.strip() or not source_notes.strip()):
            raise ValueError(
                "An approved reference requires a clinician-written answer and source citations."
            )
        connection.execute(
            """
            INSERT INTO reviewer_assessments (
                question_id, run_id, status, reviewer_name, comments,
                harmful_error, reference_answer, source_notes, reference_approved
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question_id,
                run_id,
                status,
                reviewer_name.strip(),
                comments.strip(),
                int(harmful_error),
                reference_answer.strip(),
                source_notes.strip(),
                int(reference_approved),
            ),
        )


def sign_off(case_id, reviewer_name, clinician_attested):
    if case_id not in {case["case_id"] for case in CASES}:
        raise ValueError("Unknown verification case.")
    if not reviewer_name.strip():
        raise ValueError("Reviewer name is required for case sign-off.")
    if not clinician_attested:
        raise ValueError("Qualified clinician attestation is required for case sign-off.")
    with _connect() as connection:
        total, approved = connection.execute(
            """
            SELECT COUNT(*),
                SUM(CASE
                    WHEN latest.reference_approved = 1
                     AND latest.status IN ('pass', 'partial', 'fail')
                     AND latest.run_id = runs.latest_run_id
                    THEN 1 ELSE 0 END)
            FROM questions q
            LEFT JOIN (
                SELECT question_id, MAX(run_id) AS latest_run_id
                FROM evaluation_runs GROUP BY question_id
            ) runs ON runs.question_id = q.question_id
            LEFT JOIN (
                SELECT a.question_id, a.reference_approved, a.status, a.run_id
                FROM reviewer_assessments a
                JOIN (
                    SELECT question_id, MAX(assessment_id) AS latest_id
                    FROM reviewer_assessments GROUP BY question_id
                ) newest ON newest.latest_id = a.assessment_id
            ) latest ON latest.question_id = q.question_id
            WHERE q.case_id = ?
            """,
            (case_id,),
        ).fetchone()
        if not total or approved != total:
            raise ValueError(
                "A qualified reviewer must approve a sourced reference answer for every question before case sign-off."
            )
        connection.execute(
            """
            UPDATE cases
            SET signoff_reviewer = ?, signoff_at = CURRENT_TIMESTAMP,
                signoff_attested = 1
            WHERE case_id = ?
            """,
            (reviewer_name.strip(), case_id),
        )


def export_csv():
    output = io.StringIO(newline="")
    columns = [
        "case_id",
        "procedure",
        "phase",
        "question",
        "expected_answer",
        "run_count",
        "latest_ai_response",
        "review_status",
        "reviewer_name",
        "review_comments",
        "harmful_error",
        "reference_answer",
        "source_notes",
        "reference_approved",
        "available_sources",
        "case_signoff_reviewer",
        "case_signoff_at",
    ]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for case in CASES:
        dashboard = get_dashboard(case["case_id"])
        for question in dashboard["questions"]:
            writer.writerow(
                {
                    "case_id": dashboard["case"]["case_id"],
                    "procedure": dashboard["case"]["procedure"],
                    "phase": question["phase"],
                    "question": question["prompt"],
                    "expected_answer": question["expected_answer"],
                    "run_count": question["run_count"],
                    "latest_ai_response": question["latest_response"] or "",
                    "review_status": question["review_status"] or "pending",
                    "reviewer_name": question["reviewer_name"] or "",
                    "review_comments": question["review_comments"] or "",
                    "harmful_error": bool(question["harmful_error"]),
                    "reference_answer": question["reference_answer"] or "",
                    "source_notes": question["source_notes"] or "",
                    "reference_approved": bool(question["reference_approved"]),
                    "available_sources": " | ".join(
                        f"{source['title']} ({source['version']}) {source['url']}"
                        for source in dashboard["sources"]
                    ),
                    "case_signoff_reviewer": dashboard["case"]["signoff_reviewer"] or "",
                    "case_signoff_at": dashboard["case"]["signoff_at"] or "",
                }
            )
    return output.getvalue()
