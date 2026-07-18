"""RAG (retrieval-augmented generation) surface for the migrated atlas — Story F3 (FR-5).

Semantic retrieval over embedded artifacts runs in the SAME single engine as everything else
(AD-4): the similarity ranking is a DuckDB ``vss`` query, never a rival vector engine. The
default embedder is deterministic + offline (:class:`HashingEmbedder`); ``vss`` is LOADed from
the local extension cache offline (:func:`load_vss_offline`) with a clear
:class:`VssNotProvisionedError` when unprovisioned (AD-13) — the network ``INSTALL`` lives only
in the attended :func:`provision_vss`.
"""

from __future__ import annotations

from .embedding import DEFAULT_EMBEDDING_DIM, Embedder, HashingEmbedder
from .store import (
    DuckdbVssRagStore,
    VssNotProvisionedError,
    load_vss_offline,
    provision_vss,
)

__all__ = [
    "DEFAULT_EMBEDDING_DIM",
    "DuckdbVssRagStore",
    "Embedder",
    "HashingEmbedder",
    "VssNotProvisionedError",
    "load_vss_offline",
    "provision_vss",
]
