"""The token-economy kit's closed item vocabulary (Story 28.3,
SPEC-marshal-token-economy CAP-3/CAP-4).

Story 28.1 gave marshal a declared ``[context]`` block -- five layer names,
each on or off -- and Story 28.2 taught ONE launch seam to act on one of
them (``wire``). Nothing yet PROVISIONS anything a layer needs: the caveman
skill has to be in a loop home's agent-skills directory before a dev session
can compress its own speech, the reversible CCR store directory has to exist
before ``headroom wrap`` can put anything in it, and the codegraph index has
to be built before a structure question can be answered from a graph instead
of a file re-read. This module is the DATA half of closing that gap: the
closed set of kit items, what each one is FOR, which ``[context]`` layer
declares it, which instrument it needs, and where it materializes inside a
loop home.

Pure data, and deliberately a LEAF under ``model/`` (the architecture's
lowest seed layer, importable by both ``detect`` and ``verbs``): no
filesystem read, no ``shutil.which``, no policy import. Two modules consume
it -- ``seed/detect/kit.py`` (read-only verification, the ``marshal seed
check`` half) and ``seed/verbs/kit.py`` (provisioning, the ``marshal seed
kit`` half) -- and neither re-derives any of the values below.

**Why ``layer`` is a plain ``str`` here rather than an import of
``core.policy.CONTEXT_LAYER_NAMES``.** Keeping ``model/`` a dependency-free
leaf is worth more than the import: ``core/policy.py`` is a 2000-line module
whose import would drag marshal's whole policy vocabulary into every
``seed.model`` consumer for three string constants. The binding is enforced
INSTEAD by ``tests/unit/test_seed_kit.py``'s own
``test_every_kit_item_names_a_real_context_layer`` -- a build-breaking
assertion that each ``KitItem.layer`` is a member of
``CONTEXT_LAYER_NAMES``, so a renamed layer cannot silently orphan a kit
item. Same rationale ``core/harness_profile.py`` gives for keeping
``BMADLOOP_ADAPTER_BY_PROFILE`` a code constant rather than a TOML field:
data that must stay testable as pure data.

**Why ``CCR_STORE_RELPATH`` is pinned rather than derived.** The value is
Story 28.2's own ``[wrapper] store_relpath`` in
``data/harness_profiles/claude.toml``. Deriving it here would mean reading
packaged TOML from a ``model/`` leaf (import-time I/O, or a lazy loader every
caller has to remember to use). It is pinned as a constant and bound to the
packaged profile by
``test_ccr_store_relpath_matches_the_packaged_claude_wrapper`` -- exactly the
drift Story 28.2's own review flagged as still-open on its meta test
(a store relocated in the TOML while a hardcoded path elsewhere kept
passing). A move in either place now fails the suite.

**The articulate carve-out (AC 2, the spec's `Never compress the
contract`).** The upstream caveman skill compresses everything the agent
says. The spec's constraint is narrower: dev-session speech compresses,
while review verdicts, journal entries, escalation context, and the story
contract itself stay fully articulated. That carve-out is not a convention
this package hopes an agent follows -- it is a Genesis-managed REGION
appended to the deployed skill (``regions/markers.py``'s
``marshal-seed:begin/end`` grammar, the same idiom every hybrid manifest
artifact already uses), whose presence ``seed/detect/kit.py`` verifies as
part of the caveman-skill check. A deployed skill without the region is
reported as an incomplete deployment, not as a conformant one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = (
    "ARTICULATE_REGION",
    "ARTICULATE_SURFACES",
    "CAVEMAN_SKILL_RELPATH",
    "CCR_STORE_RELPATH",
    "CODEGRAPH_INDEX_RELPATH",
    "KIT_ITEMS",
    "KitItem",
    "KitItemId",
    "articulate_region_body",
    "kit_item",
    "kit_items_for_layer",
)


class KitItemId(StrEnum):
    """The closed three-item vocabulary AC 1 names ("caveman-skill
    deployment, the CCR store dir, and a present+fresh codegraph index,
    each as a distinct check"). Kebab-case wire values, matching this
    package's established ``StrEnum`` convention (``ArtifactClass``,
    ``FindingType``, ``ArtifactState``)."""

    CAVEMAN_SKILL = "caveman-skill"
    CCR_STORE = "ccr-store"
    CODEGRAPH_INDEX = "codegraph-index"


#: Where the deployed caveman skill lands inside a loop home. Claude Code
#: reads PROJECT-scoped skills from ``<project>/.claude/skills/<name>/
#: SKILL.md``, which is the only scope that is per-loop-home: the upstream
#: installer's own Claude mechanism is ``claude plugin install`` (a
#: user-global marketplace install) plus ``npx skills add`` (network), and
#: its ``--config-dir`` scopes hook files and ``settings.json`` only -- its
#: own ``--help`` says so. Neither can be scoped to one worktree, which is
#: why Genesis deploys the skill's bytes itself rather than shelling out to
#: the installer.
CAVEMAN_SKILL_RELPATH = ".claude/skills/caveman/SKILL.md"

#: The reversible compress-cache-retrieve store Story 28.2's packaged
#: ``claude`` wrapper points ``HEADROOM_WORKSPACE_DIR`` at. A DIRECTORY, not
#: a file -- headroom creates ``ccr_store.db`` inside it.
CCR_STORE_RELPATH = ".marshal/wire"

#: codegraph's own index file. ``dist/directory.js``'s ``isInitialized``
#: requires BOTH the ``.codegraph/`` directory and ``codegraph.db`` inside
#: it, so the db file -- not the directory -- is the presence signal.
CODEGRAPH_INDEX_RELPATH = ".codegraph/codegraph.db"

#: The Genesis-managed region name appended to the deployed caveman skill.
#: Must satisfy ``regions/markers.py``'s ``REGION_NAME_PATTERN``
#: (lowercase alnum, then alnum/hyphen).
ARTICULATE_REGION = "token-economy-articulate"

#: The surfaces that stay fully articulated no matter how compressed the
#: session's ordinary speech is (SPEC-marshal-token-economy's "Never
#: compress the contract" constraint, and this story's own AC 2). Data, not
#: prose, so the carve-out body below and the test that pins it read from
#: ONE list -- a fifth surface is added here once.
ARTICULATE_SURFACES: tuple[str, ...] = (
    "review verdicts (the reviewer's own PASS/FAIL rationale)",
    "journal entries and any status/verdict line marshal will parse",
    "escalation context handed to a human or to the next session",
    "the story contract itself: spec text, acceptance criteria, gate results",
)


@dataclass(frozen=True)
class KitItem:
    """One piece of the per-loop-home kit.

    ``layer`` names the ``[context]`` layer whose declaration gates this
    item: when the layer is off, this item is neither provisioned nor
    checked (AC 4 -- "the kit is declared-off, not missing"). ``instrument``
    is the recipe/package an operator would have to install, and
    ``probe_binary`` is the executable whose presence proves it -- the two
    differ (``caveman`` ships ``caveman-install``), and a degradation
    finding must name the INSTRUMENT the operator has to act on, not the
    binary they have never heard of.

    ``is_dir`` distinguishes the CCR store (a directory Genesis creates)
    from the two file-shaped items. It is what
    ``seed/detect/kit.py::item_present`` keys its presence probe off, so
    "is this here?" is answered from DATA for all three rather than from a
    per-item branch -- the per-item branching that remains in ``kit_checks``
    is about what ELSE each item needs verified once it is present (a
    carve-out region, an index's freshness), never about presence itself.

    ``summary`` is what a report says the item is FOR, in one clause. Read
    by ``seed/verbs/kit.py``'s dry-run outcome, so ``marshal seed kit``
    explains what it would provision instead of only naming a path the
    operator may never have seen."""

    id: KitItemId
    layer: str
    instrument: str
    probe_binary: str
    relpath: str
    is_dir: bool
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", KitItemId(self.id))


KIT_ITEMS: tuple[KitItem, ...] = (
    KitItem(
        id=KitItemId.CAVEMAN_SKILL,
        layer="output",
        instrument="caveman",
        probe_binary="caveman-install",
        relpath=CAVEMAN_SKILL_RELPATH,
        is_dir=False,
        summary=(
            "the caveman output-compression skill, deployed into this loop home's"
            " Claude Code project skills directory with Genesis's articulate carve-out"
        ),
    ),
    KitItem(
        id=KitItemId.CCR_STORE,
        layer="wire",
        instrument="headroom-ai",
        probe_binary="headroom",
        relpath=CCR_STORE_RELPATH,
        is_dir=True,
        summary=(
            "the loop-home-scoped reversible compress-cache-retrieve store the wire wrapper writes originals into"
        ),
    ),
    KitItem(
        id=KitItemId.CODEGRAPH_INDEX,
        layer="structure-graph",
        instrument="codegraph",
        probe_binary="codegraph",
        relpath=CODEGRAPH_INDEX_RELPATH,
        is_dir=False,
        summary=("the pre-built local code-structure index a session queries instead of re-reading files"),
    ),
)


def kit_item(item_id: KitItemId | str) -> KitItem:
    """The ``KitItem`` for ``item_id``. Raises ``ValueError`` for anything
    outside the closed vocabulary -- never returns ``None``, so no caller
    has to invent a "missing item" branch that the enum already makes
    unreachable."""
    resolved = KitItemId(item_id)
    for item in KIT_ITEMS:
        if item.id is resolved:
            return item
    raise ValueError(f"{resolved.value}: no KIT_ITEMS entry -- every KitItemId needs one")


def kit_items_for_layer(layer: str) -> tuple[KitItem, ...]:
    """Every kit item gated by ``layer`` -- ``()`` for a layer that
    provisions nothing (``derived-context`` and ``planning-graph`` are
    Stories 28.8/28.9's surfaces, and have no loop-home artifact of their
    own yet)."""
    return tuple(item for item in KIT_ITEMS if item.layer == layer)


def articulate_region_body() -> str:
    """The body Genesis inserts into the deployed caveman skill's managed
    region -- the AC-2 carve-out, rendered from ``ARTICULATE_SURFACES`` so
    the instruction and the tested list can never disagree.

    Written as an instruction to the agent reading the skill, in ordinary
    articulated prose (compressing the rule that says "do not compress
    these" would be its own joke)."""
    lines = [
        "## Marshal carve-out: what never compresses",
        "",
        "This loop home runs under marshal's token-economy kit. Compression applies to",
        "your ordinary working speech and NOTHING else. Write the following at full",
        "length, in normal articulated prose, every time:",
        "",
    ]
    lines.extend(f"- {surface}" for surface in ARTICULATE_SURFACES)
    lines.extend(
        [
            "",
            "These are contract surfaces: another process or a human reads them and acts",
            "on them. A dropped article is a style choice; a dropped qualifier in a",
            "verdict is a false green. When in doubt about whether something is",
            "contract, write it out.",
        ]
    )
    return "\n".join(lines)
