"""Deterministic 32-dim SHA-256 bag-of-concepts for opt-in recall (Story 28.2).

Not an embedding model — a hardcoded 7-entry synonym map (`_CONCEPTS`) maps
distinct surface forms (`canine` / `dog`) onto one concept so pgvector cosine
can rank above zero lexical overlap. CAP-14 grades **lexical** recall; this
module backs the opt-in ``mode="semantic"`` / ``--semantic`` path only.
Bucket indices use SHA-256, never salted ``hash()``.
"""

from __future__ import annotations

import hashlib
import math
import re

EMBEDDING_DIM = 32
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "did",
        "do",
        "does",
        "we",
        "i",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "why",
        "what",
        "when",
        "how",
        "this",
        "that",
        "it",
        "be",
        "have",
        "has",
        "had",
        "with",
        "at",
        "by",
        "from",
        "our",
    }
)
_CONCEPTS = {
    "canine": "dog",
    "dog": "dog",
    "puppy": "dog",
    "hound": "dog",
    "feline": "cat",
    "cat": "cat",
    "kitten": "cat",
}


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS and len(token) > 1]


def _bucket(concept: str) -> int:
    digest = hashlib.sha256(concept.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % EMBEDDING_DIM


def embed_text(text: str) -> tuple[float, ...] | None:
    """Return an L2-normalized vector, or None when there is nothing to embed."""
    concepts = [_CONCEPTS.get(token, token) for token in _tokens(text)]
    if not concepts:
        return None
    vec = [0.0] * EMBEDDING_DIM
    for concept in concepts:
        vec[_bucket(concept)] += 1.0
    norm = math.sqrt(sum(value * value for value in vec))
    if norm == 0.0:
        return None
    return tuple(value / norm for value in vec)


def vector_literal(values: tuple[float, ...]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
