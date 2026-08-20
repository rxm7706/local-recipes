"""Per-region disposition: present, opted out, or missing (Story 8.5,
architecture FR-112/AD-58/AD-53, PRD J4).

A maintainer who DELETES a managed region's markers and one who never had
the region are, as of S-10.2, indistinguishable to every layer that looks:
``detect/inventory.py::_classify_hybrid`` collapses both to
``present-divergent``, ``plan/build.py::_chosen_anchor`` schedules a
re-insert for both, and nothing at all consumes ``state.opted_out``, which
S-10.2 shipped empty. FR-112 requires the first of those two to be a
*permanent, recorded* opt-out the tool thereafter respects. This module is
the one join that answers the question: it reads a file's PARSED spans and
the RECORDED state together, per declared region, and says which of the
three things is true.

**Why the join lives in ``detect/`` and not in ``regions/parse.py``.** Its
two inputs sit in peer modules that must not import each other --
``regions/`` is deliberately dependency-light (and an import-linter contract
already forbids one direction of that edge), while ``state/store.py``'s
import surface is AST-guarded and admits no ``detect``/``regions`` name at
all. ``detect/`` is the first layer above both in the architecture's chain
(``cli -> verbs -> detect|plan -> model|state|regions``), and the vocabulary
the answer is reported in -- ``opted-out`` versus ``managed-region-missing``
-- is ``detect/findings.py``'s, which ``regions/parse.py`` cannot import
upward in any case. ``parse_regions`` already returns everything needed, so
``parse.py`` is left untouched rather than growing a pass-through helper
that exists only to satisfy a surface line.

**The four rungs, in order, per declared region.** The order is the whole
design; each rung is a different fact about the same name.

1. The name is among ``parse_regions(text, entry.format)`` -> ``PRESENT``.
   What is actually in the file wins over anything state believes.
2. ``is_opted_out(state, entry.id, name)`` -> ``OPTED_OUT``. A RECORDED
   opt-out is sticky: it survives the ``managed[]`` claim being gone, which
   is precisely the state ``record_opt_out`` leaves behind, and it is what
   makes the opt-out permanent rather than re-derived.
3. State carries a ``managed[]`` entry for ``entry.id`` whose
   ``inserted_region_span.name`` is this name -> ``OPTED_OUT``. Genesis
   installed this region once and the markers are gone now; the maintainer
   deleted them, and FR-112 says that deletion is the opt-out. This is the
   rung the AC's first test exercises.
4. Otherwise ``MISSING`` -- declared, never installed, nothing recorded.

**Why ``MISSING`` is ``DRIFT`` and ``OPTED_OUT`` is ``INFO``.** ``HARD`` is
reserved for corruption and refusals (``managed-*-modified``,
``never-write-violation``, ``uncovered``); ``INFO`` for intentional,
no-action states (``legacy-present`` per AD-59, and now ``opted-out``). A
declared region simply not inserted yet is actionable and safe to fix -- its
shipped remedy already says "Run ``marshal seed update`` to re-insert" --
which is exactly the middle rung. These are the first emitting call sites
either ``FindingType`` has ever had.

**Degrading rather than guessing.** ``classify_regions`` returns ``()`` for
a non-``hybrid-managed-region`` entry (nothing declares a region there) and
for a file ``parse_regions`` refuses -- ``RegionParseError``,
``MarkerError``, or the reserved-format ``NotImplementedError`` -- the
identical rule ``detect/inventory.py::_classify_hybrid`` and
``plan/build.py``'s own pending-region computation already apply for the
same three types. A structural defect must never retire a region: a file
with an unterminated fence would otherwise read as "every region is gone",
which rung 3 would then convert into permanent opt-outs for all of them.

Never in this module: it never WRITES and never persists anything --
recording is ``state.record_opt_out`` returning a new ``SeedState`` for a
future verb to write through the existing ``write_state``. It performs no
I/O at all (the caller passes ``text`` in, P-03), no content hashing (P-07,
``detect/hashes.py``'s layer), and no ``Action``/plan construction
(``plan/build.py``'s). It does not touch ``detect/inventory.py`` or
``detect/hashes.py``: their per-file ``ArtifactState`` and their "no state
read" boundaries stay exactly as shipped, and this finer per-region
granularity lives beside them rather than inside them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..model.manifest import ArtifactClass, ManifestEntry
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions
from ..state import SeedState, is_opted_out
from .findings import Finding, FindingType, Severity


class RegionDisposition(StrEnum):
    """What is true of one declared managed region right now, kebab-case
    wire values matching ``ArtifactClass``/``ArtifactState``/``FindingType``'s
    established convention.

    Three members, not four: there is deliberately no "was present, is now
    modified" here. Region CONTENT is ``detect/hashes.py``'s question
    (P-07); this enum answers only whether the region is there, was
    intentionally given up, or was never installed."""

    PRESENT = "present"
    OPTED_OUT = "opted-out"
    MISSING = "missing"


@dataclass(frozen=True)
class RegionStatus:
    """One declared region's disposition, addressed the way a finding
    addresses it: the owning artifact's manifest ``id``, its repo-relative
    ``path``, and the region ``name``.

    Both addresses are carried because they answer different questions and
    neither derives the other here: ``artifact_id`` is AD-55's stable
    addressing (what ``explain <id>`` and ``state.managed[]`` key on), while
    ``path`` is what a human reads in a finding. Carries no
    ``__post_init__`` validation, matching ``detect/inventory.py``'s
    ``Classification``/``LegacyRecord``: this is ``classify_regions``'s own
    COMPUTED OUTPUT, built from an already-validated ``ManifestEntry``'s
    fields plus a member this module itself produced -- never externally
    supplied data to police."""

    artifact_id: str
    path: str
    region: str
    disposition: RegionDisposition


def _disposition(
    entry: ManifestEntry, region_name: str, present_names: frozenset[str], state: SeedState | None
) -> RegionDisposition:
    """The four-rung ladder for ONE region name -- see the module docstring
    for why the order is the design.

    ``present_names`` is passed in already computed so a multi-region entry
    parses its file exactly once, never once per declared region."""
    if region_name in present_names:
        return RegionDisposition.PRESENT
    if is_opted_out(state, entry.id, region_name):
        return RegionDisposition.OPTED_OUT
    if state is not None and _claims_region(state, entry.id, region_name):
        return RegionDisposition.OPTED_OUT
    return RegionDisposition.MISSING


def _claims_region(state: SeedState, artifact_id: str, region_name: str) -> bool:
    """Whether ``state.managed`` still records Genesis having installed this
    exact region of this exact artifact.

    Both halves of the match are required -- the ``id`` AND the recorded
    span's ``name`` -- never either alone: an artifact's whole-file claim, or
    its claim on a DIFFERENT region, says nothing about this region. The
    span-present-iff-hybrid invariant ``ManagedArtifact.__post_init__``
    enforces means the ``is not None`` guard below is also the class
    check."""
    return any(
        artifact.id == artifact_id
        and artifact.inserted_region_span is not None
        and artifact.inserted_region_span.name == region_name
        for artifact in state.managed
    )


def classify_regions(
    entry: ManifestEntry, text: str, state: SeedState | None
) -> tuple[RegionStatus, ...]:
    """One ``RegionStatus`` per region ``entry`` declares, in DECLARED
    order (never parse order, never sorted) -- the order the manifest's
    author wrote and the order a reader of both documents can follow.

    ``()`` for a non-``hybrid-managed-region`` entry, and ``()`` for a file
    that cannot be safely re-parsed (``RegionParseError``/``MarkerError``/
    ``NotImplementedError``) -- see the module docstring's degrade rule.
    ``state`` may be ``None`` (a never-adopted repo, exactly what
    ``read_state`` returns there): every region then falls through to
    ``MISSING`` unless the file itself carries it.

    Pure: ``text`` is passed in already read, nothing is written, and
    ``state`` is only ever queried."""
    if entry.artifact_class is not ArtifactClass.HYBRID_MANAGED_REGION:
        return ()
    # `ManifestEntry.__post_init__` requires a non-None `format` on every
    # hybrid-managed-region entry -- narrows for the type checker, matching
    # `_classify_hybrid`/`_chosen_anchor`'s own identical assertion.
    assert entry.format is not None
    try:
        spans = parse_regions(text, entry.format)
    except (RegionParseError, MarkerError, NotImplementedError):
        return ()
    present_names = frozenset(span.name for span in spans)
    return tuple(
        RegionStatus(
            artifact_id=entry.id,
            path=entry.path,
            region=region.name,
            disposition=_disposition(entry, region.name, present_names, state),
        )
        for region in entry.regions
    )


def region_findings(statuses: tuple[RegionStatus, ...]) -> tuple[Finding, ...]:
    """One ``Finding`` per non-``PRESENT`` status, in the order given: INFO
    ``opted-out`` for ``OPTED_OUT``, DRIFT ``managed-region-missing`` for
    ``MISSING``, and nothing at all for ``PRESENT`` (a region that is where
    it belongs is not a conformance problem to report).

    Messages are shaped ``f"{path}#{region}: ..."``, matching
    ``detect/hashes.py::check_managed_region``'s existing region-message
    convention, so the two region-level finding producers address a region
    the same way in every report. Built with ``Finding.new`` (never bare
    ``Finding(...)``), matching every real call site in ``detect/``, so
    ``remedy`` always resolves from ``REMEDIES`` rather than being
    hand-typed here."""
    findings: list[Finding] = []
    for status in statuses:
        if status.disposition is RegionDisposition.OPTED_OUT:
            findings.append(
                Finding.new(
                    Severity.INFO,
                    FindingType.OPTED_OUT,
                    status.path,
                    f"{status.path}#{status.region}: opted out; the tool will not"
                    " re-insert this region",
                )
            )
        elif status.disposition is RegionDisposition.MISSING:
            findings.append(
                Finding.new(
                    Severity.DRIFT,
                    FindingType.MANAGED_REGION_MISSING,
                    status.path,
                    f"{status.path}#{status.region}: declared managed region is not"
                    " present and was never installed",
                )
            )
    return tuple(findings)
