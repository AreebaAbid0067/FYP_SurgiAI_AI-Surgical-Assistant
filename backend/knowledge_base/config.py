"""Single source of truth for the SurgiAI knowledge base.

Imported by the retrieval tool (runtime) AND the ingestion scripts, so the
namespaces searched at question time always match the ones you uploaded to.
This file must stay dependency-free (no pymupdf / sentence-transformers).
"""
import os

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "surgical-assistant")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"   # 768 dimensions
EMBEDDING_DIM = 768

# label -> Pinecone namespace.  "" is Pinecone's default namespace
# (the original knowledge base that was already in the index).
GUIDELINES_NS = os.getenv("SURGIAI_GUIDELINES_NS", "surgiai-guidelines-v2")
UCT_NS = os.getenv("SURGIAI_UCT_NS", "uct-general-surgery-v2")

KNOWLEDGE_NAMESPACES = {
    "legacy": "",
    "guidelines": GUIDELINES_NS,
    "uct-textbook": UCT_NS,
}

# Namespaces no ingestion script is ever allowed to write to / wipe.
PROTECTED_NAMESPACES = {"", "default", "production", "prod"}
