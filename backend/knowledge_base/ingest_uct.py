
"""Re-extract the UCT General Surgery textbook using column-aware extraction.

Groups similarly named chapter PDFs, keeps the version with the most chunks,
removes duplicate text, and optionally uploads the result to Pinecone.

Examples:
    python -m knowledge_base.ingest_uct --source "C:/path/textbook.zip"
    python -m knowledge_base.ingest_uct --source "C:/path/textbook.zip" --upload
    python -m knowledge_base.ingest_uct --source "C:/path/textbook.zip" --upload --replace
"""

import argparse
import re
import tempfile
import zipfile
from pathlib import Path

from .config import UCT_NS
from .pdf_extract import build_chunks
from .textutil import norm_key


BOOK = "UCT Open Access Textbook of General Surgery"


def collect_pdfs(source: Path, tmp: Path):
    """Collect PDFs and remove exact duplicates using their content hashes."""
    if source.is_dir():
        pdfs = sorted(source.rglob("*.pdf"))
    else:
        with zipfile.ZipFile(source) as z:
            names = [
                name for name in z.namelist()
                if name.lower().endswith(".pdf")
            ]
            z.extractall(tmp, members=names)

        pdfs = sorted(tmp.rglob("*.pdf"))

    from .pdf_extract import sha256_file

    seen = set()
    unique = []

    for pdf in pdfs:
        file_hash = sha256_file(pdf)

        if file_hash not in seen:
            seen.add(file_hash)
            unique.append(pdf)

    return unique, len(pdfs) - len(unique)


def canon_key(path: Path) -> str:
    """Normalize chapter filenames for comparing different PDF versions."""
    s = path.stem.replace("+", " ").replace("_", " ")
    s = re.sub(r"-\d+$", "", s)
    s = re.sub(r"^\s*\d+(\s|\.)\d+\s*", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def chapter_title(path: Path) -> str:
    """Create a readable chapter title from the normalized filename."""
    return canon_key(path).title()


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--source",
        required=True,
        help="Textbook ZIP file or folder containing chapter PDFs",
    )
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--include-tables", action="store_true")
    ap.add_argument("--namespace", default=UCT_NS)

    args = ap.parse_args()

    source = Path(args.source)

    if not source.exists():
        ap.error(f"Source does not exist: {source}")

    if not source.is_dir() and not zipfile.is_zipfile(source):
        ap.error(f"Source must be a ZIP file or a folder: {source}")

    with tempfile.TemporaryDirectory() as temp_dir:
        pdfs, exact_duplicates = collect_pdfs(
            source,
            Path(temp_dir),
        )

        print(
            f"PDFs: {len(pdfs)} unique by hash "
            f"({exact_duplicates} exact duplicates skipped)"
        )

        # Phase 1: Extract PDFs and group similarly named chapters.
        by_chapter = {}

        for pdf in pdfs:
            title = chapter_title(pdf)

            metadata = {
                "source": f"{BOOK} - {title}",
                "doc_type": "textbook",
                "specialty": "general surgery",
                "book": BOOK,
                "chapter": title,
            }

            chunks, report = build_chunks(
                pdf,
                metadata,
                include_tables=args.include_tables,
            )

            key = canon_key(pdf)

            by_chapter.setdefault(key, []).append(
                (pdf, chunks, report)
            )

        # Phase 2: Keep the version with the most extracted chunks.
        all_chunks = []
        seen_text = set()
        seen_ids = set()

        totals = {
            "table": 0,
            "nonclinical": 0,
            "dup": 0,
            "version": 0,
        }

        for key, versions in sorted(by_chapter.items()):
            versions.sort(
                key=lambda version: len(version[1]),
                reverse=True,
            )

            pdf, chunks, report = versions[0]

            if len(versions) > 1:
                dropped = ", ".join(
                    version[0].name for version in versions[1:]
                )

                print(
                    f"  [near-dup] kept {pdf.name}; "
                    f"dropped {dropped}"
                )

                totals["version"] += len(versions) - 1

            # Count extraction statistics for every processed PDF.
            # Only the selected version contributes chunks.
            totals["table"] += report["skipped_table"]
            totals["nonclinical"] += report["skipped_nonclinical"]

            for chunk in chunks:
                text_key = norm_key(chunk["text"])

                if not text_key:
                    totals["dup"] += 1
                    continue

                if text_key in seen_text:
                    totals["dup"] += 1
                    continue

                chunk_id = chunk["id"]

                if chunk_id in seen_ids:
                    raise ValueError(
                        f"Duplicate chunk ID detected: {chunk_id}"
                    )

                seen_text.add(text_key)
                seen_ids.add(chunk_id)
                all_chunks.append(chunk)

            low_flag = (
                "  <-- LOW"
                if report["chunks"] < max(1, report["pages"] // 3)
                else ""
            )

            print(
                f"  {pdf.name}: "
                f"pages={report['pages']} "
                f"chunks={report['chunks']} "
                f"table_skipped={report['skipped_table']}"
                f"{low_flag}"
            )

        print(
            f"\nTotal chunks: {len(all_chunks)} "
            f"-> namespace {args.namespace!r}"
        )

        print(
            f"Skipped: table-like={totals['table']} "
            f"nonclinical={totals['nonclinical']} "
            f"duplicate/empty chunks={totals['dup']} "
            f"near-duplicate versions={totals['version']}"
        )

        if not args.upload:
            print(
                "\nDRY RUN: nothing embedded or uploaded. "
                "Add --upload to proceed."
            )
            return

        from ._upload import upload

        upload(
            all_chunks,
            args.namespace,
            args.replace,
        )


if __name__ == "__main__":
    main()
