"""READ-ONLY: show what is actually inside each Pinecone namespace.

    python -m knowledge_base.verify_coverage
    python -m knowledge_base.verify_coverage --max-vectors 5000

Per namespace: vector count, which source documents are present, page range,
and how many vectors lack text / source / page metadata.
"""
import argparse
import os
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from .config import INDEX_NAME, KNOWLEDGE_NAMESPACES


def ids_in_namespace(index, ns, limit):
    ids = []
    for page in index.list(namespace=ns):          # serverless indexes
        ids.extend(page)
        if len(ids) >= limit:
            break
    return ids[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-vectors", type=int, default=3000, help="cap per namespace")
    a = ap.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    from pinecone import Pinecone
    index = Pinecone(api_key=os.environ["PINECONE_API_KEY"]).Index(INDEX_NAME)

    stats = index.describe_index_stats()
    print("All namespaces in index:")
    for name, info in stats.namespaces.items():
        flag = "" if name in KNOWLEDGE_NAMESPACES.values() else "   <-- NOT searched by the app"
        print(f"  {name or '(default)':40} {info.vector_count:>6} vectors{flag}")

    for label, ns in KNOWLEDGE_NAMESPACES.items():
        print(f"\n=== {label}  (namespace {ns or '(default)'!r}) ===")
        info = stats.namespaces.get(ns)
        if not info or not info.vector_count:
            print("  EMPTY - nothing to search here yet.")
            continue
        ids = ids_in_namespace(index, ns, a.max_vectors)
        by_src = defaultdict(lambda: {"n": 0, "pages": set()})
        missing = {"text": 0, "source": 0, "page": 0}
        for i in range(0, len(ids), 100):
            res = index.fetch(ids=ids[i:i + 100], namespace=ns)
            for v in res.vectors.values():
                md = v.metadata or {}
                src = md.get("source_title") or md.get("source") or md.get("source_file")
                page = md.get("page_number", md.get("page", md.get("page_start")))
                missing["text"] += not (md.get("text") or md.get("page_content"))
                missing["source"] += not src
                missing["page"] += page is None
                d = by_src[src or "UNKNOWN SOURCE"]
                d["n"] += 1
                if page is not None:
                    d["pages"].add(page)
        capped = " (sampled; raise --max-vectors for all)" if len(ids) < info.vector_count else ""
        print(f"  checked {len(ids)} of {info.vector_count} vectors{capped}")
        print(f"  missing metadata -> text: {missing['text']}  source: {missing['source']}  page: {missing['page']}")
        for src, d in sorted(by_src.items(), key=lambda x: -x[1]["n"]):
            pg = sorted(p for p in d["pages"] if isinstance(p, (int, float)))
            rng = f"pages {int(pg[0])}-{int(pg[-1])} ({len(pg)} distinct)" if pg else "no page data"
            print(f"  {d['n']:>5} chunks | {rng:32} | {src[:90]}")


if __name__ == "__main__":
    main()
