"""Column-aware PDF text extraction + page-aware chunking.

Why this exists: journal articles and the UCT textbook are two-column PDFs.
`page.get_text("text", sort=True)` sorts purely by y-position, which weaves the
left and right columns together line by line ("...the appendix by the uterus
and the  implicated but not always required..."). Embedding that text gives
poor retrieval and unreadable passages. Here every page is split into bands
separated by full-width blocks, and inside a band the left column is read
before the right column.
"""
import hashlib
import re
from pathlib import Path

import pymupdf

from .textutil import norm_key  # noqa: F401  (re-exported)

HEADER_FOOTER_BAND = 0.045     # ignore blocks fully inside top/bottom 4.5% of page
TARGET_CHARS = 1000
MAX_CHARS = 1400
OVERLAP_CHARS = 150
MIN_CHARS = 120

NONCLINICAL_PATTERNS = [
    r"open access this article is licensed",
    r"publisher.s note",
    r"springer nature remains neutral",
    r"creative commons",
    r"conflicts? of interest",
    r"ethics approval",
    r"all rights reserved",
    r"orcid",
]
AFFILIATION_RE = re.compile(
    r"\b(Department of|University of|Hospital|Institute of|School of Medicine|"
    r"Division of|Correspondence to|Corresponding author)\b", re.I)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_full_width(b, page_width):
    x0, x1 = b[0], b[2]
    mid = page_width / 2
    return (x1 - x0) > 0.6 * page_width or (x0 < mid - 0.05 * page_width and x1 > mid + 0.05 * page_width)


def ordered_blocks(page):
    """Text blocks in reading order (bands of full-width blocks / left col / right col)."""
    w, h = page.rect.width, page.rect.height
    blocks = [b for b in page.get_text("blocks")
              if b[6] == 0 and b[4].strip()
              and not (b[3] <= h * HEADER_FOOTER_BAND or b[1] >= h * (1 - HEADER_FOOTER_BAND))]
    blocks.sort(key=lambda b: (b[1], b[0]))

    out, band = [], []

    def flush():
        left = sorted([b for b in band if (b[0] + b[2]) / 2 < w / 2], key=lambda b: (b[1], b[0]))
        right = sorted([b for b in band if (b[0] + b[2]) / 2 >= w / 2], key=lambda b: (b[1], b[0]))
        out.extend(left + right)
        band.clear()

    for b in blocks:
        if _is_full_width(b, w):
            flush()
            out.append(b)
        else:
            band.append(b)
    flush()
    return out


def clean_block_text(t: str) -> str:
    t = t.replace("\u00a0", " ").replace("\u00ad", "").replace("\u0007", " ")
    for lig, rep in (("\ufb01", "fi"), ("\ufb02", "fl"), ("\ufb00", "ff"), ("\ufb03", "ffi"), ("\ufb04", "ffl")):
        t = t.replace(lig, rep)
    t = re.sub(r"(\w)-\n([a-z])", r"\1\2", t)       # de-hyphenate line breaks
    t = re.sub(r"\s*\n\s*", " ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()



def is_table_like(raw: str) -> bool:
    """Table = number-heavy or tiny cells without running prose."""
    lines = [line.strip() for line in raw.split("\n") if line.strip()]

    if len(lines) < 4:
        return False

    text = " ".join(lines)
    chars = [char for char in text if not char.isspace()]
    digit_ratio = sum(char.isdigit() for char in chars) / max(1, len(chars))
    avg_words = sum(len(line.split()) for line in lines) / len(lines)

    # Detect prose containing four or more consecutive words.
    prose_runs = len(
        re.findall(r"\b[a-z]{2,}(?:\s+[a-z]{2,}){3,}", text)
    )

    if digit_ratio > 0.40:
        return True

    if digit_ratio > 0.25 and prose_runs < 2:
        return True

    return avg_words < 2.5 and prose_runs < 2


def is_references_heading(raw: str) -> bool:
    return re.fullmatch(r"\s*(references?|bibliography)\s*", raw, re.I) is not None


def _running_keys(doc):
    """Short blocks that repeat (ignoring digits) on many pages = running headers/footers."""
    from collections import Counter
    cnt = Counter()
    for page in doc:
        keys = {re.sub(r"\d+", "#", re.sub(r"\s+", " ", b[4]).strip().lower())
                for b in ordered_blocks(page) if len(b[4].strip()) < 100}
        cnt.update(keys)
    threshold = max(3, int(0.25 * len(doc)))
    return {k for k, v in cnt.items() if v >= threshold}


def extract_pages(pdf_path, stop_at_references=True):
    """Return (pages, stats). pages = [{page_number, paragraphs:[{text, table_like}]}]"""
    doc = pymupdf.open(pdf_path)
    running = _running_keys(doc)
    pages, stats = [], {"pages": len(doc), "table_like_blocks": 0, "stopped_at_references_page": None,
                        "running_header_keys": len(running)}
    stop = False
    for pno, page in enumerate(doc, start=1):
        paras = []
        for b in ordered_blocks(page):
            raw = b[4]
            if re.sub(r"\d+", "#", re.sub(r"\s+", " ", raw).strip().lower()) in running:
                continue
            if stop_at_references and is_references_heading(raw):
                stop = True
                stats["stopped_at_references_page"] = pno
                break
            text = clean_block_text(raw)
            if not text:
                continue
            tl = is_table_like(raw)
            stats["table_like_blocks"] += tl
            paras.append({"text": text, "table_like": tl})
        pages.append({"page_number": pno, "paragraphs": paras})
        if stop:
            break
    doc.close()
    return pages, stats


def _split_sentences(text):
    return re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)


def chunk_paragraphs(paragraphs):
    """Greedy-pack paragraphs into ~TARGET_CHARS chunks (never crossing pages)."""
    units = []
    for p in paragraphs:
        if len(p) <= MAX_CHARS:
            units.append(p)
        else:                                   # very long paragraph -> sentence units
            units.extend(s for s in _split_sentences(p) if s.strip())
    chunks, cur = [], ""
    for u in units:
        if cur and len(cur) + 1 + len(u) > TARGET_CHARS:
            chunks.append(cur)
            tail = cur[-OVERLAP_CHARS:]
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            cur = (tail + " " + u).strip()
        else:
            cur = (cur + " " + u).strip()
    if cur:
        chunks.append(cur)
    if len(chunks) > 1 and len(chunks[-1]) < MIN_CHARS:      # fold tiny tail
        chunks[-2] = chunks[-2] + " " + chunks[-1]
        chunks.pop()
    return [c for c in chunks if len(c) >= MIN_CHARS]



def is_nonclinical(text: str) -> bool:
    low = text.lower()

    # Remove publisher and other known nonclinical material.
    if any(re.search(pattern, low) for pattern in NONCLINICAL_PATTERNS):
        return True

    # Only reject clear affiliation-heavy blocks.
    # Bullet points are common in surgical textbooks and must be preserved.
    return len(AFFILIATION_RE.findall(text)) >= 4



def build_chunks(pdf_path, doc_meta, include_tables=False, stop_at_references=True):
    """Extract + chunk one PDF. Returns (chunks, report)."""
    pdf_path = Path(pdf_path)
    digest = sha256_file(pdf_path)
    pages, stats = extract_pages(pdf_path, stop_at_references)
    chunks = []
    report = {"file": pdf_path.name, **stats, "chunks": 0, "skipped_table": 0,
              "skipped_nonclinical": 0, "skipped_duplicate": 0}
    seen = set()
    for pg in pages:
        text_paras, skipped_tables = [], 0
        for p in pg["paragraphs"]:
            if p["table_like"] and not include_tables:
                skipped_tables += 1
                continue
            text_paras.append(p["text"])
        report["skipped_table"] += skipped_tables
        for i, ch in enumerate(chunk_paragraphs(text_paras), start=1):
            if is_nonclinical(ch):
                report["skipped_nonclinical"] += 1
                continue
            k = norm_key(ch)
            if k in seen:
                report["skipped_duplicate"] += 1
                continue
            seen.add(k)
            chunks.append({
                "id": f"{digest[:10]}-p{pg['page_number']}-c{i}",
                "text": ch,
                "metadata": {
                    "text": ch,
                    "source": doc_meta["source"],              # same key the legacy namespace uses
                    "source_title": doc_meta["source"],
                    "source_file": pdf_path.name,
                    "source_sha256": digest,
                    "doc_type": doc_meta["doc_type"],
                    "page": pg["page_number"],
                    "page_number": pg["page_number"],
                    "chunk_index": i,
                    "content_type": "narrative",
                    "clinical_verification_status": "NOT_CLINICALLY_VERIFIED",
                    **{k2: v for k2, v in doc_meta.items() if k2 not in ("source", "doc_type")},
                },
            })
    report["chunks"] = len(chunks)
    return chunks, report
