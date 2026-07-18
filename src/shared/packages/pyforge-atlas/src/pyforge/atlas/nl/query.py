"""The Vizro-AI NL interface — grounded in the BSL knowledge graph (Story D3, FR-9).

``query_vizro_ai`` is the buildable-now half of D3: it resolves the LLM backend from repo
model-backend config (:mod:`.backend`, Q3 §11 — never a hardcoded endpoint), grounds the
natural-language query in the D1 Boring Semantic Layer models (AD-8 — the query is bound to
the semantic knowledge graph, never raw tables/SQL), and returns a STRUCTURED result.

The live Vizro-AI NL->chart invocation is the **attended Q3 backend event** (DW-D3) — it is
DEFERRED here: with no backend configured (the in-container default) the function returns a
"backend not configured" advisory; with a backend configured it returns a "live call
deferred" receipt naming the repo-config-resolved endpoint. No live LLM call, no network,
and no fabricated chart happen in-container in EITHER path.

``vizro_ai`` is REPLACEABLE NL glue confined to this ``nl/`` subpackage (AD-1, mirroring the
dashboard's ``vizro`` containment): it is imported ONLY lazily + guarded (its top-level
``VizroAI`` is absent in the pinned version and its live entrypoint needs a backend), so the
tool and the gate never require ``vizro_ai`` at import/build time.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import backend as _backend

# Advisory status vocabulary (stable, agent-legible).
STATUS_UNCONFIGURED = "backend-not-configured"
STATUS_DEFERRED = "backend-configured-live-call-deferred"

_DW = "DW-D3"


def bsl_model_names() -> list[str]:
    """The D1 BSL semantic model names the NL query is grounded in (AD-8).

    Derived from the semantic package's ``build_<name>_model`` builders so this stays in
    lock-step with D1 without hardcoding — the same seam the D2 dashboard consumes.
    """
    from .. import semantic  # the BSL seam (never boring_semantic_layer directly — AD-8)

    return sorted(
        name
        for attr in dir(semantic)
        if attr.startswith("build_")
        and attr.endswith("_model")
        and (name := attr[len("build_"):-len("_model")])  # drop a bare ``build__model`` → ""
    )


def build_bsl_context(query: str) -> dict[str, Any]:
    """Ground a natural-language query in the BSL knowledge graph (AD-8).

    Returns the semantic-layer context the (deferred) Vizro-AI call is handed instead of raw
    tables: the declared BSL models and their metric surface (``METRIC_PROVENANCE`` keys). The
    NL request is therefore anchored to the D1 semantic models, never free SQL over raw
    Parquet.
    """
    from .. import semantic

    return {
        "layer": "boring-semantic-layer",
        "grounding": "AD-8 — NL query is bound to the D1 BSL models, never raw tables/SQL",
        "models": bsl_model_names(),
        "metrics": sorted(semantic.METRIC_PROVENANCE),
        "query": query,
    }


def vizro_ai_available() -> bool:
    """Guarded probe: is the ``vizro_ai`` NL backend importable in this environment?

    Lazy + fully guarded so a missing / import-incompatible ``vizro_ai`` never breaks the tool
    or the gate. The live NL->chart entrypoint (``VizroAI``) is NOT exposed at the top level in
    the pinned version — instantiating and invoking it is the attended Q3 event (DW-D3); this
    probe only reports importability for the advisory, it makes no LLM call.
    """
    try:
        import vizro_ai  # noqa: F401  (lazy, guarded — never imported at module load)
    except Exception:
        return False
    return True


def query_vizro_ai(query: str, *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Answer a natural-language query with a Vizro-AI chart/insight (LIVE PATH DEFERRED).

    Resolves the backend from repo model-backend config and grounds the query in the BSL
    models, then returns a structured result:

    * NO backend configured (the in-container default) -> a ``backend-not-configured``
      advisory (attended Q3 bring-up, DW-D3). No network, no LLM call, no fabricated chart.
    * a backend configured -> a ``backend-configured-live-call-deferred`` receipt naming the
      repo-config-resolved endpoint. The actual Vizro-AI NL->chart invocation is the attended
      Q3 event (DW-D3) — still no live call in-container.

    ``chart`` is always ``None`` here (the live generation is deferred); ``bsl_context`` proves
    the query is grounded in the semantic layer (AD-8).
    """
    context = build_bsl_context(query)
    config = _backend.resolve_backend(env)

    if config is None:
        return {
            "status": STATUS_UNCONFIGURED,
            "advisory": (
                "Vizro-AI NL backend not configured — attended Q3 bring-up "
                f"({_DW}). {_backend.unconfigured_reason(env)}."
            ),
            "deferred_work": _DW,
            "query": query,
            "bsl_context": context,
            "chart": None,
        }

    return {
        "status": STATUS_DEFERRED,
        "advisory": (
            "Vizro-AI NL backend resolved from repo model-backend config; the live "
            f"NL->chart invocation is the attended Q3 event ({_DW})."
        ),
        "deferred_work": _DW,
        "provider": config.provider,
        "endpoint": config.base_url,
        "model": config.model,
        "vizro_ai_importable": vizro_ai_available(),
        "query": query,
        "bsl_context": context,
        "chart": None,
    }
