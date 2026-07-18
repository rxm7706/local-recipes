"""Deterministic, offline, dependency-light embedder for the F3 RAG surface (FR-5).

The RAG gate proves the DuckDB ``vss`` RANKING mechanism (AD-4) — NOT a particular
model's semantic quality. So the *default* embedder is a fixed-dimension **feature-hash**
(hashing-trick) vectorizer that needs **no model download and no network**: it is a pure
function of the input text, so the ranked-results fixture is bit-for-bit reproducible
across processes and machines (``hashlib`` — never Python's per-process-salted ``hash()``).

The embedder is **injectable** (``DuckdbVssRagStore(embedder=...)``): a real learned model
(e.g. ``sentence-transformers``) is the DEFERRED upgrade point (DW-F3-1). Any object with an
integer ``dim`` and an ``embed(text) -> list[float]`` method satisfies :class:`Embedder`; a
learned model that only produces vectors is fine — the *ranking* still runs in DuckDB, so
swapping the embedder never re-introduces a rival vector engine (AD-4).

Design notes:
- Tokens are lowercased word tokens PLUS character 3-grams, so near-duplicate strings share
  buckets and rank close (the gate asserts a nearest-first order, not a distance value).
- The signed hashing trick (a second hash bit picks +1/-1) reduces collision bias.
- Vectors are **L2-normalized**, EXCEPT the zero vector (empty / all-out-of-vocab text) which
  stays all-zeros — never a divide-by-zero. ``array_distance`` (L2) is well-defined on a zero
  vector (unlike cosine, which is NaN), which is exactly why the store ranks with L2 (AD-13:
  never a silent NaN/wrong answer).
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

# Default embedding width. Small enough to keep the offline gate fast, wide enough that
# the hashing-trick collision rate is low on short artifact texts.
DEFAULT_EMBEDDING_DIM = 256

_TOKEN_RE = re.compile(r"[0-9a-z]+")


@runtime_checkable
class Embedder(Protocol):
    """The injectable embedding contract: a fixed ``dim`` and a pure ``embed``.

    The default is :class:`HashingEmbedder`; a learned model (DW-F3-1) that exposes the
    same two members is a drop-in replacement. The store NEVER assumes anything beyond
    this protocol, so no rival vector engine is implied (AD-4)."""

    dim: int

    def embed(self, text: str) -> list[float]:
        ...


def _tokens(text: str) -> list[str]:
    """Lowercased word tokens + character 3-grams (padded per token).

    Char n-grams give related strings (``requests`` / ``request``) overlapping features so
    they rank near each other; word tokens carry the coarse signal. Pure + deterministic.
    """
    low = str(text).lower()
    words = _TOKEN_RE.findall(low)
    grams: list[str] = []
    for w in words:
        padded = f"^{w}$"
        if len(padded) <= 3:
            grams.append(padded)
        else:
            grams.extend(padded[i : i + 3] for i in range(len(padded) - 2))
    return words + grams


def _bucket_and_sign(token: str, dim: int) -> tuple[int, float]:
    """Map a token to a (bucket, sign) via a stable digest — the signed hashing trick.

    ``hashlib.blake2b`` (not ``hash()``) so the mapping is identical across processes;
    the low bit of the digest picks the sign, the rest picks the bucket."""
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    bucket = value % dim
    sign = 1.0 if (value >> 1) & 1 else -1.0
    return bucket, sign


class HashingEmbedder:
    """Deterministic, offline feature-hash embedder (the F3 default — DW-F3-1 defers a
    real learned model). ``embed`` is a pure function of the text; no network, no model
    file, no global RNG state."""

    def __init__(self, dim: int = DEFAULT_EMBEDDING_DIM) -> None:
        if dim <= 0:
            raise ValueError(f"embedding dim must be > 0; got {dim!r}")
        self.dim = int(dim)

    def embed(self, text: str) -> list[float]:
        """Embed ``text`` into an L2-normalized ``dim``-vector (the zero vector — empty /
        all-out-of-vocab text — stays all-zeros; never divides by zero)."""
        vec = [0.0] * self.dim
        for tok in _tokens(text):
            bucket, sign = _bucket_and_sign(tok, self.dim)
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec  # zero vector — L2 distance stays well-defined (never NaN)
        return [v / norm for v in vec]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
