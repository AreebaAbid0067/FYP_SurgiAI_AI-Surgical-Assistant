"""Unified retrieval tool: ONE tool searches every configured knowledge namespace.

legacy (default namespace) + guidelines + UCT textbook are queried with a single
query embedding, results are merged by score, de-duplicated, thresholded, and
returned with a numbered source/page citation for each passage.
"""
import os
import re
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.tools import tool

from knowledge_base.config import EMBEDDING_MODEL, INDEX_NAME, KNOWLEDGE_NAMESPACES
from knowledge_base.textutil import norm_key

load_dotenv()

TOP_K_PER_NAMESPACE = int(os.getenv("SURGIAI_TOP_K_PER_NAMESPACE", "5"))
MAX_RESULTS = int(os.getenv("SURGIAI_MAX_RESULTS", "6"))
# Cosine similarity floor. all-mpnet-base-v2 scores for on-topic passages are usually
# 0.35-0.70; tune with `python -m knowledge_base.test_retrieval`.
MIN_SCORE = float(os.getenv("SURGIAI_MIN_SCORE", "0.30"))
MAX_PASSAGE_CHARS = 1500

NO_EVIDENCE = "NO_RELEVANT_PASSAGES_FOUND"


@lru_cache(maxsize=1)
def _index():
    from pinecone import Pinecone
    return Pinecone(api_key=os.getenv("PINECONE_API_KEY")).Index(INDEX_NAME)


@lru_cache(maxsize=1)
def _embedder():
    # Loaded once per process (the old code reloaded the model on every call).
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def _normalise(match, label):
    md = match.metadata or {}
    text = md.get("text") or md.get("page_content") or md.get("chunk_text") or ""
    source = md.get("source_title") or md.get("source") or md.get("source_file") or "Unknown source"
    page = md.get("page_number", md.get("page", md.get("page_start", "?")))
    if isinstance(page, float) and page.is_integer():
        page = int(page)
    return {"text": text.strip(), "source": str(source), "page": page,
            "score": float(match.score), "namespace": label, "id": match.id}


def retrieve_passages(query: str, namespaces=None, min_score=None, max_results=None):
    """Return (passages, diagnostics). Used by the tool AND by test_retrieval.py."""
    namespaces = namespaces or KNOWLEDGE_NAMESPACES
    min_score = MIN_SCORE if min_score is None else min_score
    max_results = max_results or MAX_RESULTS

    vector = _embedder().embed_query(query)
    raw, diag = [], {"per_namespace": {}, "errors": {}, "dropped_low_score": 0, "dropped_duplicate": 0}
    for label, ns in namespaces.items():
        try:
            res = _index().query(vector=vector, top_k=TOP_K_PER_NAMESPACE,
                                 namespace=ns, include_metadata=True)
            hits = [_normalise(m, label) for m in res.matches]
            diag["per_namespace"][label] = len(hits)
            raw.extend(hits)
        except Exception as e:                      # one bad namespace must not kill the answer
            diag["errors"][label] = str(e)[:200]

    raw.sort(key=lambda p: p["score"], reverse=True)
    seen, out = set(), []
    for p in raw:
        if not p["text"]:
            continue
        if p["score"] < min_score:
            diag["dropped_low_score"] += 1
            continue
        key = norm_key(p["text"][:300])
        if key in seen:
            diag["dropped_duplicate"] += 1
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= max_results:
            break
    return out, diag


def format_passages(passages):
    blocks = []
    for i, p in enumerate(passages, 1):
        text = re.sub(r"\s+", " ", p["text"])[:MAX_PASSAGE_CHARS]
        blocks.append(f"[{i}] {p['source']} | page {p['page']} | {p['namespace']} | "
                      f"score {p['score']:.2f}\n{text}")
    return "\n\n".join(blocks)


@tool
def query_database(surgeon_query: str) -> str:
    """Search the SurgiAI surgical knowledge base (clinical guidelines and the UCT
    general surgery textbook) and return numbered passages with source and page."""
    print("Searching the unified surgical knowledge base")
    passages, diag = retrieve_passages(surgeon_query)
    print(f"  hits per namespace: {diag['per_namespace']} | errors: {diag['errors']} | "
          f"kept: {len(passages)}")
    if not passages:
        reason = f" Retrieval errors: {diag['errors']}" if diag["errors"] else ""
        return f"{NO_EVIDENCE}: nothing in the knowledge base matched this query.{reason}"
    return format_passages(passages)
