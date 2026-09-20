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
``regions/`` is deliberately dependency-light, and ``state/store.py``'s
import surface is AST-guarded and admits no ``detect``/``regions`` name at
all. (Only the second of those two has mechanical enforcement. An earlier
revision claimed "an import-linter contract already forbids one direction
of that edge"; the sole ``regions`` contract in ``pyproject.toml`` forbids
``seed.regions -> seed.model.manifest``, Story 8.4's package-cycle guard,
and says nothing about ``regions``/``state`` -- review finding.)
``detect/`` is the first layer above both in the architecture's chain
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
3. State carries a ``managed[]`` entry for ``entry.id`` AND ``entry.path``
   whose ``inserted_region_span.name`` is this name, AND ``text`` has real
   content, AND no ``marshal-seed`` marker line for this name survives
   anywhere in ``text``, AND the opt-out grammar can spell the pair ->
   ``OPTED_OUT``. Genesis installed this region once and the markers are
   gone now; the maintainer deleted them, and FR-112 says that deletion is
   the opt-out. This is the rung the AC's first test exercises. The claim
   (``_claims_region``) is the rung's PREMISE; the other three conjuncts
   are each a guard against deriving a PERMANENT opt-out from something
   that is not a deletion, and each names the case it closes:
   ``_has_content`` (there is no file here to have deleted markers from),
   ``marker_region_names`` (a marker for this region is still sitting in
   the text), and ``opt_out_key_or_none`` (the pair is unspellable, so a
   derived opt-out could never be recorded -- see ``_disposition``).
4. Otherwise ``MISSING`` -- declared, never installed, nothing recorded.

**Why rung 3 requires a ``text`` with real content, and rungs 1-2 do not.**
FR-112 sanctions deleting the MARKERS, not deleting the FILE. An absent,
empty, or unreadable artifact reaches this module as ``text=""`` -- and a
file a botched script truncated to a newline, or to a BOM, is the same fact
with one or two more bytes, which is why the gate is ``_has_content``
rather than ``text`` or ``text.strip()`` -- the same ``""``
``plan/build.py::_current_text_verbose`` hands back for
``ArtifactState.ABSENT``, and the same one
``detect/inventory.py::_classify_hybrid`` degrades to for a target it
cannot read -- and ``parse_regions("")`` then finds nothing, so
without this guard ``rm AGENTS.md`` would read as "every claimed region's
markers were deliberately deleted" and silently record a PERMANENT opt-out
for every one of them. Whether the file itself is absent or unreadable is
the artifact-level ``ArtifactState`` classification's business, not this
per-region ladder's; re-offering the region (``MISSING``, whose shipped
remedy re-inserts it) is the conservative, non-destructive direction, and
the same "cannot safely read the file, so degrade rather than guess" rule
the unparseable-file case below already applies. A RECORDED opt-out (rung 2)
is deliberately NOT gated this way: it is a fact stated by a verb, not
inferred from a file, and staying sticky through a vanished file is exactly
what makes it permanent.

**The sequencing contract between this module and ``plan/build.py``.**
``classify_regions`` DERIVES an opt-out from a surviving ``managed[]`` claim
(rung 3), while ``build_plan`` suppresses insertion only on the RECORDED key
set it is handed (``frozenset(state.opted_out)``). The two halves therefore
agree only if a MUTATING verb records what detect derived: it must call
``state.record_opt_out(...)`` for every pair ``opt_outs_to_record`` returns,
and persist the result, BEFORE it calls ``build_plan``. Without that
ordering a verb reports "opted out" and, in the same breath, builds a plan
that re-inserts the region. ``opt_outs_to_record`` returns the DERIVED pairs
only -- a pair rung 2 read back out of ``state`` is already recorded, and
handing it to the mutator again would drop a claim that is still standing
(see that function). A READ-ONLY ``check`` does the opposite and
records nothing at all -- FR-88 forbids ``check`` writing anything, state
included -- so it reports the derivation and leaves the recording to the
next mutating run.

**A known limitation of rung 3: one recorded region span per artifact.**
``SeedState.__post_init__`` rejects duplicate ``managed[].id``, so one
artifact carries at most one ``ManagedArtifact`` and therefore at most one
``inserted_region_span``. For a hybrid entry declaring several regions,
state can attest to only ONE of them having been installed; rung 3 can fire
for that one, and every other declared region falls through to ``MISSING``
and stays eligible for insertion no matter how many were really installed
and then deleted. That is a pre-existing property of the schema S-10.2
shipped, which Story 8.5 does not change -- recorded in both places (see
``state/store.py::record_opt_out``) so nobody reads rung 3 as covering every
declared region.

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

That degrade rule covers *input* defects, and one class of failure is
deliberately NOT swallowed by it (review finding): rung 3 reaches
``opt_out_key_or_none``, which reads the PACKAGED state schema, and a
corrupt or unreadable install raises ``InternalError`` (exit 10) straight
out of ``classify_regions``. That is not a degrade case -- a broken
install is not a repo whose regions should be guessed at -- and it matches
what ``plan/build.py`` already documents for its own consumer of the same
function. So "degrades rather than crashes" is true of every fact this
module reads about the REPO, and false of the one thing it reads about
itself.

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

import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from ..model.manifest import ArtifactClass, ManifestEntry
from ..regions.markers import MarkerError, parse_marker_line
from ..regions.parse import RegionParseError, parse_regions
from ..state import SeedState, is_opted_out, opt_out_key_or_none
from .findings import Finding, FindingType, Severity

# Unicode general categories that carry no visible content -- the WHOLE
# `C` (Other) class, not a subset of it: `Cc` (control characters, e.g.
# NUL), `Cf` (format characters, e.g. U+FEFF BOM and U+200B ZERO WIDTH
# SPACE), `Cs` (surrogates, which cannot appear in well-formed text at
# all), `Co` (private use) and `Cn` (unassigned). `str.strip()` removes
# none of them -- see `_has_content`.
#
# `Cs`/`Co`/`Cn` were missing (review finding, confirmed by execution:
# `_has_content("\U000f0000")` returned `True`), so a file holding only
# private-use or unassigned code points still read as real content and
# rung 3 retired every claimed region of it PERMANENTLY -- the third route
# to the outcome `bool(text)` and then `bool(text.strip())` had each been
# widened to close. Naming the whole class rather than the members that
# happened to be tried is the point; over-classifying a file as empty only
# ever re-offers its regions, which is the non-destructive direction.
#
# What this deliberately does NOT try to be is a test for "invisible"
# (review finding: `_has_content("⠀")`, BRAILLE PATTERN BLANK, is
# `So`, and `_has_content("ㅤ")`, HANGUL FILLER, is `Lo` -- both still
# read as content). "Invisible when rendered" is a property of a font and a
# renderer, not a Unicode class, and chasing it has no closing move. The
# question this guard actually asks is narrower and IS closed: is this the
# residue of a file having been emptied -- nothing at all, whitespace, or
# the control/format bytes a truncating writer leaves behind (`Z*` via
# `str.isspace()`, plus the whole `C` class here)? A file whose only
# character is a Braille blank is not that residue; it is a file with
# content, and rung 3 reading it as one is the correct answer.
#
# `Cs` is named for completeness of the class rather than for reach: a
# lone surrogate cannot come off the strict-UTF-8 read path callers use,
# and `regions/parse.py::_iter_lines` raises `UnicodeEncodeError` on such
# a text before `_has_content` is ever consulted.
_EMPTY_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})


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


def _has_content(text: str) -> bool:
    """Whether ``text`` carries at least one character that is neither
    whitespace nor a Unicode ``C`` (Other) code point -- rung 3's "is there
    a FILE here to have deleted markers from" test, and NOT a test for
    "invisible" (see ``_EMPTY_CATEGORIES`` on why that has no closing move
    and is the wrong question here).

    Not ``bool(text.strip())`` (review finding, confirmed by execution).
    ``str.strip()`` removes whitespace and nothing else, so a file holding
    only a UTF-8 BOM (``"\\ufeff"`` -- what ``Path.write_text(``''``,
    encoding="utf-8-sig")`` leaves behind), a zero-width space, or a NUL
    byte read back as non-empty and re-opened the exact hole widening
    ``bool(text)`` to ``bool(text.strip())`` had closed one byte earlier:
    every claimed region of an effectively empty file retired PERMANENTLY.
    Categories rather than a hand-listed character set, so the rule covers
    the whole class instead of the three members that happened to be
    tested."""
    return any(not char.isspace() and unicodedata.category(char) not in _EMPTY_CATEGORIES for char in text)


def marker_region_names(text: str, entry: ManifestEntry) -> frozenset[str]:
    """Every region name that appears in a ``marshal-seed`` BEGIN or END
    marker line anywhere in ``text`` -- including lines ``parse_regions``
    deliberately skips.

    Rung 3's premise is "the markers are GONE", and ``parse_regions``
    answers the narrower "no well-formed span was FOUND". Those diverge
    (review finding, confirmed by execution): ``parse_regions`` is
    fence-aware by design -- a managed region's own body may DOCUMENT the
    marker grammar inside a fenced code block, and honoring such a line
    would be the AR-1 corruption ``regions/parse.py`` exists to prevent --
    so a real region a maintainer later wrapped in a closed ``` fence is
    invisible to it while sitting, markers and all, in the file. Rung 3
    read that as a deletion and derived a PERMANENT opt-out for a live
    region.

    Asked through ``markers.parse_marker_line``, never a hand-written
    substring or regex: that function owns the line-level grammar, and a
    second spelling of it here is exactly what this story's Always bullets
    forbid. A ``MarkerError`` line is SKIPPED rather than raised, because a
    fenced block documenting a malformed marker is legitimate content and
    must not degrade the whole entry to ``()`` -- ``parse_regions`` skips
    the same line for the same reason.

    Both marker halves count, not only BEGIN: either one surviving means
    the markers were not cleanly deleted, and re-offering the region is the
    conservative direction this module takes everywhere else.

    **Each line is asked twice, raw and whitespace-stripped** (review
    finding, confirmed by execution). ``parse_marker_line`` GUARANTEES
    recognition of the exact canonical single-space grammar and nothing
    else -- its own docstring says a line whose delimiter spacing varies is
    unspecified, and in fact ``_strip_delimiters`` returns ``None`` for it,
    i.e. "ordinary content". So an intact, plainly-visible region whose
    marker line had merely picked up a trailing space or an indent was
    invisible to ``parse_regions`` AND to this scan, and rung 3 read it as
    a deletion: a live region retired permanently, its ``body_sha`` dropped
    with the claim, on a whitespace change. Re-asking the SAME grammar
    after ``str.strip()`` is normalization, not a second spelling of it --
    it is exactly what ``markers.py`` says S-8.2 will do wholesale ("re-
    normalizes a file before consulting this grammar").

    **PUBLIC, because the planner needs the same answer** (review finding,
    confirmed by execution). ``plan/build.py::_pendency`` derived its
    ``retained`` set -- the consent gate deciding whether a fully-opted-out
    entry may leave the ``RepoFingerprint`` -- from ``parse_regions`` alone,
    so a region physically present but invisible to the parser (fenced, or
    marker lines carrying a trailing space) read as released there while
    rung 1 here answered ``PRESENT`` for the same input. That is the
    identical hole this function was added to close, one layer over, and
    the fix is this function rather than a copy of it: ``plan`` already
    imports ``detect.hashes``/``detect.inventory``, so the edge is
    precedented, and the alternative was a second spelling of a grammar
    scan in a story whose Always bullets forbid exactly that.

    **Over-detection is CHEAP, not free** (review finding, confirmed by
    execution). Both consumers take a name found here in the conservative
    direction -- rung 3 stands down and re-offers the region; ``retained``
    keeps the entry and its hash -- so a false positive destroys nothing.
    But it is not harmless: a marker-shaped line in ordinary prose that
    ``parse_regions`` skips (an INDENTED code block demonstrating the
    grammar, which ``str.strip()`` normalizes straight into recognition)
    puts the name here on every run, so rung 3 can never fire for that
    region. A maintainer who then deletes those markers gets
    ``managed-region-missing`` and a re-insertion on every ``update``,
    forever, with no diagnostic saying why FR-112 is not being honoured for
    that artifact. The trade is deliberate -- silently retiring a LIVE
    region is the worse failure, and this direction never does that -- and
    the residual is tracked as ``DW-FU-8-5-11``.

    Under-detection has a residual of its own: this closes the
    leading/trailing-whitespace variants and no others. A marker whose
    INNER spacing moved (``<!--marshal-seed:begin ...-->``) or which
    acquired a non-whitespace line prefix (a ``>`` blockquote, a list
    bullet) is still unrecognized, still reads as a deletion, and still
    derives a permanent opt-out. Closing that needs the looser grammar
    S-8.2 owns; hand-writing one here is what this module's Always bullets
    forbid. Tracked as ``DW-FU-8-5-10``."""
    assert entry.format is not None
    names: set[str] = set()
    for raw_line in text.splitlines():
        for line in {raw_line, raw_line.strip()}:
            try:
                marker = parse_marker_line(entry.format, line)
            except MarkerError:
                continue
            if marker is not None:
                names.add(marker.region)
    return frozenset(names)


def _disposition(
    entry: ManifestEntry,
    region_name: str,
    present_names: frozenset[str],
    marker_names: frozenset[str],
    state: SeedState | None,
    *,
    derive_from_claim: bool,
) -> RegionDisposition:
    """The four-rung ladder for ONE region name -- see the module docstring
    for why the order is the design.

    ``present_names`` is passed in already computed so a multi-region entry
    parses its file exactly once, never once per declared region.

    ``derive_from_claim`` is rung 3's gate: ``False`` for a ``text`` with no
    non-whitespace content, where "no region found" means "no file to find
    one in" rather than "the markers were deleted" (module docstring).
    Rungs 1 and 2 are untouched by it.

    **Rung 3 also requires a pair the opt-out grammar can spell.** Rung 2
    already has that property for free -- ``is_opted_out`` answers through
    ``opt_out_key_or_none``, so an inadmissible pair can never match a
    schema-valid ``opted_out`` entry. Rung 3 derived from the raw
    ``managed[].id``, which is the LOOSER grammar (``SeedState`` accepts an
    id the ``opted_out`` item pattern rejects -- e.g. one carrying a space),
    so a derived ``OPTED_OUT`` could name a pair ``record_opt_out`` refuses.
    That broke the sanctioned verb sequence at its own seam:
    ``opt_outs_to_record`` handed the caller a pair, and feeding it straight
    to ``record_opt_out`` -- the exact loop this module documents -- raised
    ``ValueError``. It also disagreed three ways with ``plan/build.py``,
    which degrades the same pair to "not opted out" and re-inserts the
    region regardless. Gating here makes all three layers apply the ONE
    grammar, and an unspellable pair falls through to ``MISSING`` -- the
    non-destructive direction, matching the empty-``text`` rule above."""
    if region_name in present_names:
        return RegionDisposition.PRESENT
    if is_opted_out(state, entry.id, region_name):
        return RegionDisposition.OPTED_OUT
    if (
        derive_from_claim
        and region_name not in marker_names
        and state is not None
        and opt_out_key_or_none(entry.id, region_name) is not None
        and _claims_region(state, entry, region_name)
    ):
        return RegionDisposition.OPTED_OUT
    return RegionDisposition.MISSING


def _claims_region(state: SeedState, entry: ManifestEntry, region_name: str) -> bool:
    """Whether ``state.managed`` still records Genesis having installed this
    exact region of this exact artifact, at the path the manifest declares
    for it today.

    All three halves of the match are required -- the ``id``, the recorded
    span's ``name``, AND the recorded ``path`` -- never a subset: an
    artifact's whole-file claim, or its claim on a DIFFERENT region, says
    nothing about this region. The span-present-iff-hybrid invariant
    ``ManagedArtifact.__post_init__`` enforces means the ``is not None``
    guard below is also the class check.

    **Why the path is compared too** (review finding, confirmed by
    execution). AD-55 makes ``id``, not ``path``, the stable address, so a
    manifest entry's ``path`` can move while its ``id`` does not, and
    state's claim still records the OLD path. Matching on ``id`` alone then
    derived an opt-out for a path that had never carried the region at all,
    and ``record_opt_out`` would have dropped the claim describing the
    region still installed at the old path -- leaving that one with no
    ``body_sha`` and no way to rebuild it. A moved path falls through to
    ``MISSING`` instead, which re-offers the region: the same conservative,
    non-destructive direction the empty-``text`` and surviving-marker gates
    above take.

    ``state/store.py::_without_region_claim`` matches on ``id`` and span
    name only, because ``record_opt_out``/``clear_opt_out`` are handed no
    path to compare -- a divergence between the two spellings of this
    predicate tracked as `DW-FU-8-5-9`.

    That divergence was described here as "latent today" for one pass while
    it was in fact LIVE (review finding, confirmed by execution). The gate
    added above governs rung 3 only, and ``opt_outs_to_record`` used to hand
    back rung-2 pairs as well -- so a recorded opt-out on an entry whose
    manifest ``path`` had since moved travelled the module's own documented
    verb loop into the path-blind filter and dropped the claim describing
    the region still installed at the OLD path. It is latent NOW because
    ``opt_outs_to_record`` returns only the pairs this rung derived, and
    this rung compares the path; see that function."""
    return any(
        artifact.id == entry.id
        and artifact.path == entry.path
        and artifact.inserted_region_span is not None
        and artifact.inserted_region_span.name == region_name
        for artifact in state.managed
    )


def classify_regions(entry: ManifestEntry, text: str, state: SeedState | None) -> tuple[RegionStatus, ...]:
    """One ``RegionStatus`` per region ``entry`` declares, in DECLARED
    order (never parse order, never sorted) -- the order the manifest's
    author wrote and the order a reader of both documents can follow.

    ``()`` for a non-``hybrid-managed-region`` entry, and ``()`` for a file
    that cannot be safely re-parsed (``RegionParseError``/``MarkerError``/
    ``NotImplementedError``) -- see the module docstring's degrade rule.
    ``state`` may be ``None`` (a never-adopted repo, exactly what
    ``read_state`` returns there): every region then falls through to
    ``MISSING`` unless the file itself carries it.

    A ``text`` with no real content -- an absent, empty, or unreadable
    artifact, all three of which the callers spell ``""``, and equally a
    file truncated to a newline or to a byte-order mark -- still produces
    one status per declared region, but never a DERIVED ``OPTED_OUT``: rung
    3 is switched off, so a deleted file re-offers its regions rather than
    retiring them permanently (module docstring, ``_has_content``). Nor is
    a region whose marker lines are still in the file derived from, however
    they got out of ``parse_regions``'s sight (``marker_region_names``).

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
    except RegionParseError, MarkerError, NotImplementedError:
        return ()
    present_names = frozenset(span.name for span in spans)
    # Every region name whose marker line survives ANYWHERE in the raw
    # text, fenced or not -- so rung 3 tests its own premise ("the markers
    # are gone") rather than the parser's narrower one ("no span found").
    marker_names = marker_region_names(text, entry)
    return tuple(
        RegionStatus(
            artifact_id=entry.id,
            path=entry.path,
            region=region.name,
            disposition=_disposition(
                entry,
                region.name,
                present_names,
                marker_names,
                state,
                # Not a bare truthiness test, and not `.strip()` either:
                # the guard's whole point is "is there a FILE here to have
                # deleted markers from", and a file truncated to a single
                # newline -- or to a BOM, or to a NUL -- answers that no
                # just as much as a zero-byte one does. See `_has_content`
                # for the two revisions this test has already outlived.
                derive_from_claim=_has_content(text),
            ),
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
    hand-typed here.

    **The ``opted-out`` message names the opt-out KEY as well as the path,
    because its remedy asks for the key and only the path was reachable.**
    A region has two addresses -- ``AGENTS.md#tiers`` (path) and
    ``agents-md#tiers`` (``opt_out_key``) -- and ``RegionStatus`` carries
    both precisely because they answer different questions. ``Finding``
    carries only ``path``, so before this the report showed one address
    while ``REMEDIES[FindingType.OPTED_OUT]`` told the operator to run
    ``--reinstate <artifact>#<region>`` with the OTHER, and the obvious
    copy-paste was the wrong token. The message keeps the
    ``f"{path}#{region}: ..."`` prefix ``check_managed_region`` shares -- so
    the two region-level producers still address a region identically -- and
    spells the key in the tail, where the remedy can be acted on. The
    ``managed-region-missing`` message needs no such tail: its remedy
    (``marshal seed update``) takes no region argument.

    **What the ``opted-out`` message does NOT promise.** It says the tool
    will not re-insert the region *while the opt-out stands*, never that the
    opt-out is already durable. For a DERIVED opt-out (rung 3 -- claim
    present, nothing recorded) durability depends on the caller having
    recorded ``opt_outs_to_record``'s pairs before the plan is built; a
    read-only ``check`` deliberately does not (FR-88), so an unconditional
    "will not re-insert" would be exactly the unprovable claim the
    ``managed-region-missing`` message below had removed from it."""
    findings: list[Finding] = []
    for status in statuses:
        if status.disposition is RegionDisposition.OPTED_OUT:
            # Asked of `opt_out_key_or_none`, never interpolated here
            # (review finding): the wire spelling of the key lives once for
            # the whole package, in `state/store.py` against the packaged
            # schema's own pattern, and this module's docstrings argue at
            # length that a second spelling is the defect. Hand-rendering
            # `f"{id}#{region}"` printed a token no `--reinstate` would
            # accept the moment that grammar moved, and the assertion
            # pinning the message tests a literal, so nothing would fail.
            # Never `None` in practice -- both rungs that can produce
            # `OPTED_OUT` already gate on this same function -- so the tail
            # is simply omitted rather than guessed at if that ever
            # changes.
            key = opt_out_key_or_none(status.artifact_id, status.region)
            key_tail = "" if key is None else f" (opt-out key {key})"
            findings.append(
                Finding.new(
                    Severity.INFO,
                    FindingType.OPTED_OUT,
                    status.path,
                    f"{status.path}#{status.region}: opted out; while this"
                    " opt-out stands the tool will not re-insert the region"
                    f"{key_tail}",
                )
            )
        elif status.disposition is RegionDisposition.MISSING:
            findings.append(
                Finding.new(
                    Severity.DRIFT,
                    FindingType.MANAGED_REGION_MISSING,
                    status.path,
                    # "and was never installed" used to follow, and was a
                    # claim this code cannot make: the one-span-per-artifact
                    # limit above means a region whose artifact's single
                    # claim slot is occupied by a SIBLING region reaches this
                    # branch having been installed, deleted, and forgotten,
                    # and the message would have asserted otherwise. What is
                    # actually known is what is now said.
                    f"{status.path}#{status.region}: declared managed region is not present",
                )
            )
    return tuple(findings)


def opt_outs_to_record(statuses: tuple[RegionStatus, ...], state: SeedState | None) -> tuple[tuple[str, str], ...]:
    """The ``(artifact_id, region)`` pairs of every ``OPTED_OUT`` status
    ``state`` does not ALREADY record, in the order given -- the argument
    list a mutating verb feeds to ``state.record_opt_out`` before it builds
    a plan.

    Exists because the story's two halves key on DIFFERENT things and would
    otherwise silently disagree: ``classify_regions`` DERIVES an opt-out from
    a surviving ``managed[]`` claim, while ``build_plan`` suppresses only on
    the RECORDED ``state.opted_out`` key set. Making the derivation durable
    is a verb's obligation, and this makes it a mechanical one -- see the
    module docstring's sequencing contract for who must call it and when
    (a mutating verb, before ``build_plan``; never a read-only ``check``,
    which FR-88 forbids from writing).

    **Returns only the pairs rung 3 DERIVED, never the ones rung 2 read
    back out of ``state``** (review finding, confirmed by execution). An
    earlier revision returned every ``OPTED_OUT`` pair, on the argument that
    re-asking ``is_opted_out`` would be a second spelling of rung 2 and that
    ``record_opt_out`` is idempotent anyway. The first half was wrong about
    the function (asking rung 2's OWN function is not a second spelling of
    it), and the second was wrong about the mutator: ``record_opt_out`` is
    idempotent in the ``opted_out`` KEY and unconditional in the
    ``managed[]`` claim it drops. So re-recording an already-recorded pair
    is not a no-op -- it discards whatever claim still stands, and the two
    reachable ways for one to stand alongside a recorded key are exactly the
    two cases the rung-3 gates refuse to derive from:

    * the region is physically in the file but invisible to
      ``parse_regions`` (fenced, or a marker line that gained a trailing
      space), so rung 2 answers before ``marker_region_names`` is ever
      consulted -- and the claim dropped is a LIVE region's, taking its
      ``body_sha`` with it;
    * the entry's manifest ``path`` has moved since the claim was recorded,
      so the claim describes the region still installed at the OLD path and
      ``_without_region_claim``, which compares no path, drops that one.

    Both are the precondition ``record_opt_out``/``clear_opt_out`` document
    ("the region must not be PRESENT in the file") being violated by this
    module's own documented verb loop. A pair rung 2 answered needs no
    recording by definition -- it is already in ``state.opted_out``, and so
    already in the key set the verb hands ``build_plan`` -- so filtering it
    out costs the sequencing contract nothing and closes both.

    Takes ``SeedState | None`` for the reason ``is_opted_out`` does: a
    never-adopted repo records no opt-out, which makes every derived pair
    reportable rather than making the call an error.

    Returns plain pairs, never rendered ``opt_out_key`` strings: the
    mutators take the two halves separately, and rendering here would only
    force the caller to split them back apart. ``PRESENT`` and ``MISSING``
    contribute nothing -- neither is an opt-out."""
    return tuple(
        (status.artifact_id, status.region)
        for status in statuses
        if status.disposition is RegionDisposition.OPTED_OUT
        and not is_opted_out(state, status.artifact_id, status.region)
    )
