# SurgiAI backend

## Run the API
```
cd backend
copy .env.example .env      # then fill in GROQ_API_KEY and PINECONE_API_KEY
poetry install              # or: pip install .
uvicorn main:app --reload
```

## Roles, privacy and security

- **Surgeons** register at `/login`. Each surgeon only ever sees their own patient cases; another surgeon's case returns 404. Patient payloads are encrypted at rest (Fernet) in `surgiai_app.sqlite3`.
- **Admin** (seeded from `ADMIN_USERNAME` / `ADMIN_PASSWORD`; if no password is set a one-time password is written to the startup log) is the only role that can open `/verification` and `/admin/compliance`, and cannot read patient cases.
- Passwords use scrypt; sessions are signed 8h tokens held in an HttpOnly cookie by the Next.js proxy. Secrets come from env vars or an auto-generated, git-ignored `.secrets.json`.
- Set `FRONTEND_ORIGINS` for CORS. The frontend reads `BACKEND_URL` (default `http://127.0.0.1:8000`).

## Modules

Pre-surgery (`/pre-surgery/upload`, `/pre-surgery/history-from-document`), during surgery (`/surgery`, `/cases/{id}/intraop-summary`) and post-surgery (`/cases/{id}/post-surgery`, which falls back to the guideline protocol in `procedures.py` if the AI is unavailable). Procedures are data in `procedures.py`. NFR evidence is served to admins at `/admin/nfr`.

## Clinical verification

Five cases (appendectomy, laparoscopic cholecystectomy, inguinal hernia repair, colectomy, thyroidectomy) are seeded from `verification_data.py` with reference answers and sources. Sign-off still requires a qualified clinician in the dashboard.

## Clinical verification pilot (details)

The separate Next.js page at `/verification` provides an appendicitis/appendectomy
pilot with 18 pre-, intra-, and postoperative questions. The FastAPI backend
stores cases, actual answer runs, reviewer assessments, source citations, and
sign-off in the local SQLite file `clinical_verification.sqlite3`. This file is
ignored by Git and is created automatically on startup.

Use **Run SurgiAI** to call the same `surgical_agent` pipeline as `/surgery`.
This requires the configured Groq and Pinecone services. Reviews are not
automatic: a qualified clinician must write and source reference answers,
record their assessment, and self-attest before case sign-off is enabled.
Available references are starting points and must be checked for relevance and
currency. The dashboard and CSV export are for research/quality assurance only,
not patient-care decisions; reviewer names are self-reported, not authenticated.

Run the local verification-store tests from `backend/`:
```
python -m unittest discover -s tests -v
```

## Knowledge base (Pinecone index `surgical-assistant`, 768-dim, all-mpnet-base-v2)

| label        | namespace                  | content                                   |
|--------------|----------------------------|-------------------------------------------|
| legacy       | (default)                  | what was already in the index             |
| guidelines   | `surgiai-guidelines-v2`    | SAGES appendicitis 2024 + Global EGS 2022 |
| uct-textbook | `uct-general-surgery-v2`   | UCT General Surgery textbook              |

The app's single tool `query_database` searches all three. Namespaces are defined once in `knowledge_base/config.py`.

### Load the data (run from `backend/`)
```
pip install -r knowledge_base/requirements-ingest.txt

# 1) guideline PDFs (already in knowledge_base/data/guidelines)
python -m knowledge_base.ingest_guidelines            # dry run
python -m knowledge_base.ingest_guidelines --upload

# 2) textbook: point at the ORIGINAL textbook ZIP (or a folder of its PDFs)
python -m knowledge_base.ingest_uct --source "C:\path\textbook.zip"            # dry run
python -m knowledge_base.ingest_uct --source "C:\path\textbook.zip" --upload

# 3) check what is really in Pinecone, then test retrieval
python -m knowledge_base.verify_coverage
python -m knowledge_base.test_retrieval
```
Uploads use fixed chunk ids, so re-running overwrites instead of duplicating. `--replace` wipes only the target namespace (never the default one).

All content is `NOT_CLINICALLY_VERIFIED` (metadata flag). Tables are skipped by default because PDF text extraction garbles them.
