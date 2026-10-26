# SurgiAI backend

## Run the API
```
cd backend
copy .env.example .env      # then fill in GROQ_API_KEY and PINECONE_API_KEY
poetry install              # or: pip install .
uvicorn main:app --reload
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
