"""The AI Software Factory layer — Wave H (§ 7, FR-22, AD-22).

The factory maps the ``cf_atlas`` data layer onto the 4-Layer AI Software Factory blueprint
(§ 7): a **workforce** of five personas (:mod:`.personas`) drives crews that read pipeline
outputs and maintain the **Karpathy wiki** (:mod:`.wiki`) — a strict ``raw/ -> compiled/ ->
outputs/`` knowledge tree backed by conda-forge MinIO/PostgreSQL (:mod:`.storage`).

**The AD-22 write-boundary is the defining invariant of this whole layer:** factory components
*read* atlas datasets (via the Kedro catalog / BSL) and *write* ONLY the wiki tree and, in H3,
the Wagtail CMS — never an atlas dataset. Story H1 lands the storage shape + the workforce; H2
adds the agno crews, H3 the CMS sync, H4 the Dagster triggering.

This ``__init__`` re-exports the H1 surface; deeper layers import the submodules directly.
"""

from __future__ import annotations

from .crews import (
    CompileCrew,
    CompileResult,
    Grounding,
    LintCrew,
    LintReport,
    LintViolation,
    QAAnswer,
    QACrew,
    keyword_retriever,
)
from .personas import (
    DEFAULT_PERSONAS,
    FACTORY_TOOLS,
    PERSONA_NAMES,
    Persona,
    resolve_personas,
)
from .storage import WikiStorageConfig, resolve_storage_config
from .wiki import WIKI_STAGES, WikiLayout, scaffold_wiki

__all__ = [
    "DEFAULT_PERSONAS",
    "FACTORY_TOOLS",
    "PERSONA_NAMES",
    "Persona",
    "resolve_personas",
    "WikiStorageConfig",
    "resolve_storage_config",
    "WIKI_STAGES",
    "WikiLayout",
    "scaffold_wiki",
    "CompileCrew",
    "CompileResult",
    "LintCrew",
    "LintReport",
    "LintViolation",
    "QACrew",
    "QAAnswer",
    "Grounding",
    "keyword_retriever",
]
