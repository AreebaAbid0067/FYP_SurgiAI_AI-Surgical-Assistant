"""Shared embed + upsert helper used by the two ingest scripts."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import EMBEDDING_DIM, EMBEDDING_MODEL, INDEX_NAME, PROTECTED_NAMESPACES

BATCH = 64


def check_namespace(ns: str):
    if ns.strip().lower() in PROTECTED_NAMESPACES:
        sys.exit(f"Refusing to write to protected/default namespace {ns!r}.")


def clean_metadata(md: dict) -> dict:
    """Pinecone metadata cannot contain None / nested dicts."""
    out = {}
    for k, v in md.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
            out[k] = v
    return out


def upload(chunks, namespace: str, replace: bool = False):
    """chunks: [{id, text, metadata}]. Idempotent: ids are deterministic, so
    re-running overwrites instead of duplicating."""
    check_namespace(namespace)
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    key = os.getenv("PINECONE_API_KEY")
    if not key:
        sys.exit("PINECONE_API_KEY missing in backend/.env")

    from pinecone import Pinecone
    from sentence_transformers import SentenceTransformer

    pc = Pinecone(api_key=key)
    desc = pc.describe_index(INDEX_NAME)
    if getattr(desc, "dimension", None) != EMBEDDING_DIM:
        sys.exit(f"Index dimension is {desc.dimension}, model needs {EMBEDDING_DIM}. Stopped.")
    metric = getattr(desc, "metric", "?")
    if metric != "cosine":
        print(f"WARNING: index metric is {metric!r}; scores/thresholds below assume cosine.")
    index = pc.Index(INDEX_NAME)

    stats = index.describe_index_stats()
    existing = stats.namespaces.get(namespace)
    n_existing = existing.vector_count if existing else 0
    if n_existing and replace:
        print(f"--replace: deleting {n_existing} existing vectors in {namespace!r}")
        index.delete(delete_all=True, namespace=namespace)
    elif n_existing:
        print(f"Namespace {namespace!r} already has {n_existing} vectors; "
              "same ids will be overwritten, stale ids stay. Use --replace for a clean rebuild.")

    print(f"Loading {EMBEDDING_MODEL} ...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    done = 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        vecs = model.encode([c["text"] for c in batch], show_progress_bar=False).tolist()
        index.upsert(
            vectors=[{"id": c["id"], "values": v, "metadata": clean_metadata(c["metadata"])}
                     for c, v in zip(batch, vecs)],
            namespace=namespace,
        )
        done += len(batch)
        print(f"  uploaded {done}/{len(chunks)}")
    print(f"Done. {done} vectors in namespace {namespace!r}. Next: python -m knowledge_base.verify_coverage")
