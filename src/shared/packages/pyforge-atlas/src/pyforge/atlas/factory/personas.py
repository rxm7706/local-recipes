"""The 5 AI-Software-Factory personas + their BMAD customization-layer resolution
(Story H1, FR-22(a), § 2.2 / § 7.3).

The autonomous factory workforce is governed by exactly FIVE personas (§ 2.2), each a
mapped BMAD agent role, each owning a wiki stage and a set of physical tools (§ 7.3):

===========  =====================  =============  ===================================
Persona      BMAD role              Wiki stage     Governs tools
===========  =====================  =============  ===================================
Ingester     Analyst                raw            search_ops, pdf_parser
Compiler     Architect              compiled       markdown_generator
Linker       Developer              compiled       markdown_generator
Linter       QA/Reviewer (+ TEA)    compiled       search_ops
Oracle       Product Owner          outputs        lasuite_client, markdown_generator
===========  =====================  =============  ===================================

**Resolution through the BMAD customization layers (ARCHITECTURE-SPINE § "Factory layer").**
BMAD resolves configuration by a layered merge — a frozen installer/team baseline overlaid
by successively higher-priority *customization* layers (global-custom → project-custom, the
CLAUDE.md six-layer merge), highest priority winning. :func:`resolve_personas` models exactly
that: :data:`DEFAULT_PERSONAS` is the baseline, and each positional ``*overlays`` mapping is a
higher customization layer applied on top (later overlay wins). An overlay may only *refine*
an EXISTING persona (override a field) — it can neither introduce a sixth persona nor drop one
of the five (the workforce is fixed at five by § 2.2; a typo'd persona name in an overlay is a
loud error, not a silent new agent).
"""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

#: The BMAD agent roles the five personas map onto (§ 2.2). A persona's role is one of these.
BmadRole = Literal["Analyst", "Architect", "Developer", "QA/Reviewer", "Product Owner"]

#: The physical tools the workforce executes (§ 7.3). A persona governs a subset.
FACTORY_TOOLS: tuple[str, ...] = (
    "lasuite_client",  # REST push to the Wagtail/La Suite CMS (H3)
    "markdown_generator",  # writes wiki markdown pages
    "search_ops",  # retrieval over compiled content (RAG, F3)
    "pdf_parser",  # deep-research ingestion of source documents
)


class Persona(BaseModel):
    """One factory persona — immutable, no unknown fields (a stray overlay key is rejected,
    not silently carried, mirroring the a2a schema family)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    role: BmadRole
    #: The wiki stage this persona primarily writes (one of :data:`wiki.WIKI_STAGES`).
    wiki_stage: Literal["raw", "compiled", "outputs"]
    #: The physical tools (§ 7.3) this persona is allowed to execute — a subset of
    #: :data:`FACTORY_TOOLS`, validated on construction.
    tools: tuple[str, ...] = Field(default_factory=tuple)

    def model_post_init(self, _ctx: Any) -> None:
        unknown = tuple(t for t in self.tools if t not in FACTORY_TOOLS)
        if unknown:
            raise ValueError(
                f"persona {self.name!r} governs unknown tool(s) {unknown}; "
                f"expected a subset of {FACTORY_TOOLS}"
            )


def _persona(name: str, role: BmadRole, stage: str, tools: tuple[str, ...]) -> Persona:
    return Persona(name=name, role=role, wiki_stage=stage, tools=tools)


#: The FROZEN baseline workforce (§ 2.2 / § 7.3) — the lowest customization layer. Keyed by
#: persona name so an overlay refines a persona by name. The five names are the workforce
#: identity; :func:`resolve_personas` forbids adding/removing any.
DEFAULT_PERSONAS: dict[str, Persona] = {
    "Ingester": _persona("Ingester", "Analyst", "raw", ("search_ops", "pdf_parser")),
    "Compiler": _persona("Compiler", "Architect", "compiled", ("markdown_generator",)),
    "Linker": _persona("Linker", "Developer", "compiled", ("markdown_generator",)),
    "Linter": _persona("Linter", "QA/Reviewer", "compiled", ("search_ops",)),
    "Oracle": _persona(
        "Oracle", "Product Owner", "outputs", ("lasuite_client", "markdown_generator")
    ),
}

#: The immutable set of persona names (§ 2.2). An overlay may not stray outside it.
PERSONA_NAMES: frozenset[str] = frozenset(DEFAULT_PERSONAS)


def resolve_personas(
    *overlays: Mapping[str, Mapping[str, Any]],
) -> dict[str, Persona]:
    """Resolve the five personas by merging customization ``overlays`` onto the baseline.

    Each overlay is a ``{persona_name: {field: value}}`` mapping representing one higher BMAD
    customization layer; overlays are applied left-to-right so a LATER overlay wins (highest
    priority last — the CLAUDE.md six-layer semantics). An overlay may only refine an EXISTING
    persona: an unknown persona name raises (it would be a silent sixth agent), and the
    workforce always comes back exactly five strong.

    Returns a fresh ``{name: Persona}`` dict; :data:`DEFAULT_PERSONAS` is never mutated.
    """
    merged: dict[str, dict[str, Any]] = {
        name: p.model_dump() for name, p in DEFAULT_PERSONAS.items()
    }
    for layer in overlays:
        for name, overrides in layer.items():
            if name not in merged:
                raise ValueError(
                    f"customization overlay names unknown persona {name!r}; the workforce is "
                    f"fixed at the five § 2.2 personas {sorted(PERSONA_NAMES)} — an overlay may "
                    "only refine an existing persona, not add one"
                )
            if "name" in overrides and overrides["name"] != name:
                # The persona name IS its identity (and its registry key). Letting an overlay
                # rename it would decouple the dict key from `.name` — two personas could then
                # report the same `.name` — so refuse it (a rename is add+drop, not a refine).
                raise ValueError(
                    f"customization overlay may not rename persona {name!r} to "
                    f"{overrides['name']!r}: a persona's name is its fixed identity (§ 2.2); an "
                    "overlay refines fields, it does not re-key the workforce"
                )
            merged[name].update(overrides)
    # Re-validate each merged persona through the model (an overlay that set a bad role / tool
    # / stage fails HERE, loudly, not at first use).
    return {name: Persona(**fields) for name, fields in merged.items()}
