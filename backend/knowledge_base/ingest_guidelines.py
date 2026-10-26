"""Embed the guideline PDFs in data/guidelines/ and upload them to Pinecone.

Run from the backend/ folder:
    python -m knowledge_base.ingest_guidelines              # dry run, nothing uploaded
    python -m knowledge_base.ingest_guidelines --upload     # embed + upload
    python -m knowledge_base.ingest_guidelines --upload --replace   # wipe THIS namespace first
"""
import argparse
from pathlib import Path

from .config import GUIDELINES_NS
from .pdf_extract import build_chunks

DATA = Path(__file__).resolve().parent / "data" / "guidelines"

# Human-readable source names (shown to the surgeon as the citation).
GUIDELINES = {
    "SAGES_appendicitis_2024.pdf": {
        "source": "SAGES guideline for the diagnosis and treatment of appendicitis (Surg Endosc 2024)",
        "doc_type": "guideline", "specialty": "general surgery", "condition": "appendicitis"},
    "zrac005.pdf": {
        "source": "Global guidelines for emergency general surgery: systematic review and Delphi prioritization (BJS Open 2022)",
        "doc_type": "guideline", "specialty": "emergency general surgery"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--replace", action="store_true", help="delete the target namespace before uploading")
    ap.add_argument("--include-tables", action="store_true",
                    help="also embed table-like blocks (usually garbled when extracted as text)")
    ap.add_argument("--namespace", default=GUIDELINES_NS)
    a = ap.parse_args()

    all_chunks, ids = [], set()
    for pdf in sorted(DATA.glob("*.pdf")):
        meta = GUIDELINES.get(pdf.name)
        if meta is None:
            print(f"SKIP {pdf.name}: add it to GUIDELINES in this script to give it a citation name")
            continue
        chunks, rep = build_chunks(pdf, meta, include_tables=a.include_tables)
        print(rep)
        for c in chunks:
            assert c["id"] not in ids, f"duplicate id {c['id']}"
            ids.add(c["id"])
        all_chunks += chunks

    print(f"\nTotal chunks: {len(all_chunks)} -> namespace {a.namespace!r}")
    if all_chunks:
        print("Sample:", all_chunks[0]["metadata"]["source"], "| p.", all_chunks[0]["metadata"]["page"])
        print(all_chunks[0]["text"][:300])
    if not a.upload:
        print("\nDRY RUN: nothing embedded or uploaded. Add --upload to proceed.")
        return
    from ._upload import upload
    upload(all_chunks, a.namespace, a.replace)


if __name__ == "__main__":
    main()
