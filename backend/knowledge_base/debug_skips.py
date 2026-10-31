
import sys
from pathlib import Path

from .pdf_extract import (
    extract_pages,
    chunk_paragraphs,
    is_nonclinical,
)

pdf_path = Path(sys.argv[1])
pages, stats = extract_pages(pdf_path)

print("PDF:", pdf_path.name)
print("Extraction stats:", stats)

total_paragraphs = 0
total_table = 0
total_chunks = 0

for pg in pages:
    paragraphs = pg["paragraphs"]
    total_paragraphs += len(paragraphs)

    table_count = sum(p["table_like"] for p in paragraphs)
    total_table += table_count

    kept = [p["text"] for p in paragraphs if not p["table_like"]]
    chunks = chunk_paragraphs(kept)
    total_chunks += len(chunks)

    print(
        f"\nPage {pg['page_number']}: "
        f"paragraphs={len(paragraphs)}, "
        f"table_like={table_count}, "
        f"chunks={len(chunks)}"
    )

    for p in paragraphs:
        if p["table_like"]:
            print("  TABLE:", repr(p["text"][:160]))

    for chunk in chunks:
        if is_nonclinical(chunk):
            print("  NONCLINICAL:", repr(chunk[:160]))
        elif len(chunk) < 120:
            print("  SHORT CHUNK:", repr(chunk[:160]))

print("\nTOTAL PARAGRAPHS:", total_paragraphs)
print("TOTAL TABLE-LIKE:", total_table)
print("TOTAL PRE-FILTER CHUNKS:", total_chunks)
