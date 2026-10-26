"""Tiny helpers shared by runtime retrieval and ingestion (no heavy dependencies)."""
import hashlib
import re


def norm_key(text: str) -> str:
    return hashlib.sha1(re.sub(r"\W+", " ", text.lower()).strip().encode()).hexdigest()
