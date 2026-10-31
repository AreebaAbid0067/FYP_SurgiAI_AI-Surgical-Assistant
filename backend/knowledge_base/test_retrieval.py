"""Run sample questions through the SAME retrieval code the app uses.

    python -m knowledge_base.test_retrieval
    python -m knowledge_base.test_retrieval "your own question"

Prints, per question: hits per namespace, kept passages with score/source/page,
and how many were dropped as low-score or duplicates. Use the scores to tune
SURGIAI_MIN_SCORE in .env.
"""
import sys

from agents.surgery_agent.tools.query_database import MIN_SCORE, retrieve_passages

SAMPLES = [
    "What imaging is recommended for suspected appendicitis in adults?",
    "Should uncomplicated appendicitis be treated with antibiotics alone or appendicectomy?",
    "Post-operative antibiotics after appendectomy for complicated appendicitis",
    "What are the essential recommendations for emergency general surgery in low-resource settings?",
    "Management of acute limb ischaemia",           # textbook only
    "How do I fix a flat bicycle tyre?",            # off-topic: should return NOTHING
]


def run(q):
    passages, diag = retrieve_passages(q, min_score=0.0, max_results=50)   # raw view
    kept, _ = retrieve_passages(q)
    print("\n" + "=" * 78 + f"\nQ: {q}\n  per-namespace hits: {diag['per_namespace']}  errors: {diag['errors']}")
    print(f"  kept after MIN_SCORE={MIN_SCORE}: {len(kept)}   (duplicates dropped in raw view: {diag['dropped_duplicate']})")
    for p in (kept or passages[:3]):
        tag = "KEPT " if kept else "below threshold"
        print(f"  [{tag}] {p['score']:.3f} | {p['namespace']:12} | p.{p['page']} | {p['source'][:70]}")
        print(f"          {p['text'][:160]!r}")


if __name__ == "__main__":
    for q in (sys.argv[1:] or SAMPLES):
        run(q)
