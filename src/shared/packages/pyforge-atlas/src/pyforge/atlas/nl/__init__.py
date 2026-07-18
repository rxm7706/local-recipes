"""Natural-language interface seam for the atlas MCP surface (Story D3, FR-9, AD-7/AD-8).

The ``nl/`` subpackage is the single glue layer the thin ``query_vizro_ai`` MCP tool (AD-7)
delegates to. It owns the LLM-backend resolution (repo model-backend config, Q3 §11 — never a
hardcoded public endpoint) and the BSL-grounded (deferred) Vizro-AI call, keeping all NL/LLM
logic OUT of the tool body. It is also the ONLY package subtree permitted to import
``vizro_ai`` (AD-1, enforced by ``tests/catalog/test_no_inline_io.py``).
"""

from __future__ import annotations

from .backend import BackendConfig, resolve_backend, unconfigured_reason
from .query import (
    STATUS_DEFERRED,
    STATUS_UNCONFIGURED,
    build_bsl_context,
    bsl_model_names,
    query_vizro_ai,
    vizro_ai_available,
)

__all__ = [
    "BackendConfig",
    "STATUS_DEFERRED",
    "STATUS_UNCONFIGURED",
    "build_bsl_context",
    "bsl_model_names",
    "query_vizro_ai",
    "resolve_backend",
    "unconfigured_reason",
    "vizro_ai_available",
]
