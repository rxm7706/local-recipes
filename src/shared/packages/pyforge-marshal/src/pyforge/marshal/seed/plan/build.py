"""The plan builder: `Classification` -> `Action` (Story 9.6, architecture
FR-82/AD-57/AD-59/AD-60/NFR-12/P-04/P-05/P-07).

`detect.inventory.classify` already answers "what state is this manifest
entry in" for a target repo. `build_plan` is the one function that turns
that answer into the artifact a human reviews before Genesis writes
anything: one `Action` per entry that actually needs a change
(`ArtifactState.ABSENT` or `PRESENT_DIVERGENT`), each carrying its own
rationale and, for a `hybrid-managed-region` entry, which anchor a missing
region would be inserted at -- plus a `RepoFingerprint` tying the whole
`Plan` to the repo state it was computed against (AD-57).

**Which classifications produce an `Action`.** `PRESENT_CONFORMANT` and
`PRESENT_LEGACY` never do (AD-59/AD-60) -- a `referenced` entry is always
`PRESENT_CONFORMANT` per `classify()` itself, so it never reaches this rule
either; it simply never appears among the qualifying classifications.
Every entry that DOES qualify gets EXACTLY one `Action` -- there is no
per-entry branching here that could produce more than one -- with one
narrow exception, added by Story 8.5 and stated here so this invariant is
not read as still absolute: a `hybrid-managed-region` entry whose
NOT-PRESENT regions are ALL opted out qualifies and produces NONE, because
the run owes it no insertion. That is the only path on which a qualifying
entry is skipped, it requires a non-empty `opted_out`, and an entry with
nothing not-present in the first place is deliberately not on it (see
`_Pendency`).

**Why this module resolves paths directly rather than re-deriving
`detect.inventory._resolve_within_repo`'s containment check.** `classify()`
has ALREADY run that check once, for every entry, to produce the very
`ArtifactState` this module switches on: an entry classified `ABSENT`
because its path escapes `repo_root` is indistinguishable here from one
genuinely missing (both are `ABSENT`, and this module's own
`_current_text_verbose` never touches the filesystem for that state at all
-- see below). An entry
classified `PRESENT_DIVERGENT` can ONLY be `hybrid-managed-region`, and
`_classify_entry` can only reach that state once the SAME containment
check has already confirmed the path resolves within `repo_root` -- so a
second, private-function-reaching re-check here would test nothing that
is not already proven by the state itself. `detect/inventory.py` is
reference-only for this story (its own Never bullet), and its containment
helper is a private, unexported function this module does not import.

**Why `pyforge.core.process.PosixProcess` directly, not
`adapters.vcs_git.GitVcs`.** See this story's spec Design Notes: `GitVcs`
serves `ports.vcs.VcsPort`'s much larger worktree-provisioning surface and
sits in `adapters/`, a layer `seed/` (which sits below `adapters/` in the
architecture's module-dependency chain) must not import from for two
read-only git calls. `pyforge.core.process`, like `pyforge.core.
atomic_write` (already imported by `seed/fs.py`), is a precedented
cross-package import for this package's low layers.

**Opt-outs arrive as a parameter, never as a state read (Story 8.5,
FR-112).** `build_plan` takes a keyword-only `opted_out` frozenset of
already-read `state.opted_out` keys, and a hybrid entry that is owed
insertions but whose owed regions are ALL opted out produces no `Action` at
all, so an opted-out region is never re-inserted. Keeping the read out of
this module preserves S-9.6's no-state-I/O property and its
byte-identical-output determinism. Precisely: no STATE read. The key
spelling arrives via `opt_out_key_or_none`, which consults the packaged
schema, so this module does touch packaged data -- read once per process
and identical for every caller, so determinism is untouched, but "pure" in
the strict sense would be a claim too strong to make.

That read is an OBLIGATION on the caller, not a service already rendered:
no verb calls `build_plan` today (`cli/seed.py` is still six unimplemented
stubs), so this paragraph states what a caller must do rather than what one
already does. A caller must (1) `read_state`, (2) record every pair
`detect.optout.opt_outs_to_record` derives -- `classify_regions` DERIVES an
opt-out from a surviving `managed[]` claim, which this module never sees,
so a derivation left unrecorded is one the plan below will re-insert over
-- (3) persist that state, and only THEN (4) pass
`frozenset(state.opted_out)` here. Record-before-plan, in that order; a
read-only `check` skips steps 2-3 (FR-88 forbids it writing anything) and
reports the derivation without acting on it. The one thing imported from
`seed/state/` is `opt_out_key_or_none`, a pure key-spelling function, so the
`<artifact-id>#<region>` wire form -- and the rule for a pair that cannot be
spelled in it -- live once for the whole package rather than re-derived
here.

Never in this module (see the spec's own Never bullets for the full
list): no read of `.marshal/seed-state.yml` -- this module performs no
state READ of any kind, and the opted-out key set is a `build_plan`
parameter (Story 8.5 amended this bullet; it previously claimed
`seed/state/` was an empty stub, true only until S-10.2 built it); no CLI
wiring (`build_plan`/
`write_plan`/`load_plan`/`default_plan_path` are library functions only);
no fingerprint-based REFUSAL (Story 10.3 added `fingerprint_drift`, which
only REPORTS how a repo has diverged from a `Plan`'s fingerprint -- turning
a non-empty report into a raised `PreconditionFailure` is
`seed/apply/run.py`'s job, and this module still imports nothing from
`seed/apply/`); no re-matching of `manifest.never_write`/`effective_never_write` beyond
the `PRESENT_LEGACY` skip `classify()` already computes (`fs.py`'s own
guard is the defense-in-depth backstop at actual write time, a later
story).
"""

from __future__ import annotations

import json
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_bytes
from pyforge.core.process import PosixProcess

from ..detect.hashes import hash_content
from ..detect.inventory import ArtifactState, Inventory
from ..detect.optout import marker_region_names
from ..model.manifest import ArtifactClass, Manifest, ManifestEntry, Region
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions, resolve_anchor
from ..state import is_opt_out_key, opt_out_key_or_none
from .types import Action, Plan, RepoFingerprint

# Classifications this module ever turns into an Action -- everything else
# (PRESENT_CONFORMANT, PRESENT_LEGACY) is conformant or intentionally
# frozen, and produces no Action (AD-59/AD-60).
_ACTIONABLE_STATES = frozenset({ArtifactState.ABSENT, ArtifactState.PRESENT_DIVERGENT})

# Query-style git calls (never a checkout/push) -- matches
# `adapters/vcs_git.py::_GIT_TIMEOUT_S`'s identical value for the identical
# class of call, so a hung `git` process fails fast instead of blocking
# `build_plan` indefinitely (review finding: `PosixProcess.run` defaults to
# no timeout at all).
_GIT_TIMEOUT_S = 30.0


def _current_text_verbose(state: ArtifactState, repo_root: Path, entry_path: str) -> tuple[str, bool]:
    """The one text both `_chosen_anchor` and `build_plan`'s own
    `artifact_hashes` computation read/hash -- a single shared definition
    so the two can never see a different byte stream for the same artifact
    -- plus whether that text is what the artifact actually HOLDS (`True`)
    rather than the `''` an unreadable target degrades to (`False`).

    `ABSENT` never touches the filesystem and answers `("", True)`: the
    blank is `classify()`'s own reported truth about this artifact
    (genuinely missing, or resolving outside `repo_root` -- either way,
    nothing safe to read), so it is a fact about the file and a consumer
    may reason from it. A present-but-non-regular-file, unreadable, or
    non-UTF-8 target degrades to `''` too, but answers `False` -- the
    identical fallback `detect.inventory._classify_hybrid` already applies
    when its own read hits the same failure (this story's Always bullet:
    "`current_text` is `\"\"` for an absent or unreadable target"), with the
    one bit that tells the two blanks apart kept rather than discarded.

    Only ever reads a real path for a `PRESENT_DIVERGENT` entry, and only
    because `classify()` has ALREADY proven -- to produce that very state --
    that `entry_path` resolves to an existing target within `repo_root`
    (see the module docstring).

    The second value exists so `_is_fully_opted_out` can refuse to infer
    consent from a file nobody could read (review finding, confirmed by
    execution -- see its docstring). Consumers that have nothing to do with
    it (`hash_content` has nothing better to hash than the blank;
    `_chosen_anchor` already degrades to `()` on the same input by its own
    route) simply discard it. This is the same `(text, readable)` pair
    `fingerprint_drift` consumes through `_read_text_or_blank_verbose`,
    with an `ABSENT` short-circuit in front of it.

    A plain-`str` wrapper (`_current_text`) stood here for one pass after
    every consumer had been rewired onto this function, calling it and
    dropping the second value for nobody -- removed as dead surface in a
    story that argues against exactly that (review finding)."""
    if state is ArtifactState.ABSENT:
        return "", True
    return _read_text_or_blank_verbose(repo_root, entry_path)


def _read_text_or_blank_verbose(repo_root: Path, entry_path: str) -> tuple[str, bool]:
    """The READ half of `_current_text_verbose`, with no `ArtifactState`
    gate in front of it: the target's UTF-8 text, degrading to `''` for an
    absent, non-regular-file, unreadable, or non-UTF-8 target -- plus
    whether the target was actually READ (`True`) or merely degraded
    (`False`).

    Factored out of `_current_text_verbose` (rather than duplicated inside
    `fingerprint_drift`) so the one degradation rule this module applies at
    plan-BUILD time is byte-for-byte the same rule it applies at
    VERIFICATION time -- two independent spellings of "unreadable means
    `''`" is exactly the producer/verifier drift `fingerprint_drift` living
    beside `build_plan` exists to prevent. `_current_text_verbose` keeps its
    own `ABSENT` short-circuit in front of this call; `fingerprint_drift`
    deliberately does not (see its docstring).

    Review finding, verified by execution: collapsing "absent", "not a
    regular file", "unreadable" and "not valid UTF-8" all onto the same
    `''` is correct for plan BUILD (`build_plan` has nothing better to hash)
    but reopens, at VERIFICATION time, the exact hole `fingerprint_drift`
    exists to close. An artifact `ABSENT` when the plan was built is
    recorded as `hash_content("")`; if a file appears at that path before
    apply and is binary, unreadable, or empty, it degrades back to `''`,
    re-hashes identically, and the stale plan is accepted -- apply then
    destroys a file a human put there. Content alone cannot distinguish
    those cases, so `fingerprint_drift` needs the second half of the answer
    and compares READABILITY as well as bytes. `build_plan`'s hashing
    discards it, preserving its behavior byte-for-byte."""
    target = repo_root / entry_path
    if not target.is_file():
        return "", False
    try:
        return target.read_text(encoding="utf-8"), True
    except OSError, UnicodeDecodeError:
        return "", False


def _is_opted_out(entry_id: str, region_name: str, opted_out: frozenset[str]) -> bool:
    """Whether `opted_out` records this entry/region pair, keyed through
    `state.opt_out_key_or_none` so the wire spelling lives in exactly one
    place.

    An entry id the grammar REFUSES answers `False`, and that answer is the
    state package's own, not a rule re-derived here: `opt_out_key_or_none`
    is the "asking, not minting" half of the key function, returning `None`
    exactly where `opt_out_key` raises. (An earlier revision wrapped
    `opt_out_key` in a local `try`/`except ValueError` -- the same rule, in
    a second place, free to drift from the first.) `ManifestEntry` requires
    only a non-blank `id`, so an id carrying an interior space (or a literal
    `#`) is legally constructible while the state schema's `opted_out`
    grammar cannot spell it -- and a key that grammar rejects can never
    appear in a schema-valid `opted_out` set, so "not opted out" is the
    correct and total answer. Raising here instead would make `build_plan`
    crash on a manifest it planned perfectly well before this story. (A
    region name cannot reach that branch at all: `Region.__post_init__`
    already requires `REGION_NAME_PATTERN`, which is the key's own region
    half verbatim.)

    The degradation covers the INADMISSIBLE-KEY case and nothing wider: this
    call still reaches `state.store._load_schema`, which raises
    `InternalError` (exit 10) for a missing or corrupt packaged
    `schema.json`. That is deliberate and is not caught here -- a broken
    INSTALLATION is a loud failure by design, never a plan quietly built as
    if nothing were opted out."""
    key = opt_out_key_or_none(entry_id, region_name)
    return key is not None and key in opted_out


@dataclass(frozen=True)
class _Pendency:
    """One hybrid entry's region verdict, in the two facts `build_plan` needs
    to tell apart: the declared regions NOT PRESENT in the file, and the
    subset of those still PENDING after opt-outs are removed.

    `pending` alone is not enough, and collapsing the two was a real defect
    (review finding). The suppression rule below fires on "nothing left to
    insert", but "nothing left" has two causes that must NOT behave alike:
    every owed region was opted out (suppress -- FR-112's whole point), or
    nothing was owed in the first place (do NOT suppress -- that is a
    `PRESENT_DIVERGENT` entry whose file already carries every declared
    region at build time, which `classify()` saw as divergent a moment
    earlier). Suppressing the second silently drops the entry from BOTH
    `actions` AND `artifact_hashes`, which removes it from the
    `RepoFingerprint` and leaves `fingerprint_drift` blind to any later
    change to that file -- and it would have happened under the DEFAULT
    empty `opted_out`, to callers predating this story. Carrying both facts
    makes the rule say what it means: suppress only when the emptiness was
    CAUSED by opt-outs.

    `retained` is the third fact, and it is what stops the suppression rule
    from firing on a file the tool STILL OWNS CONTENT IN (review finding,
    confirmed by execution). `not_present`/`pending` describe only the
    regions a run OWES; a hybrid entry declaring `tiers` (present, inserted
    by Genesis, not opted out) and `model-badge` (absent, opted out) owes
    nothing after opt-outs -- `not_present == (model-badge,)`, `pending ==
    ()` -- and so satisfied both earlier conditions and vanished from
    `actions` AND `artifact_hashes`, taking `CLAUDE.md` out of the
    `RepoFingerprint` while a live managed region sat inside it. Hand-
    editing that region's body afterwards produced no `fingerprint_drift`
    at all. `_is_fully_opted_out`'s consent argument ("no managed content
    left in it to drift") is only true when NOTHING is retained, which is
    exactly what this field measures.

    **`retained` counts a region that IS in the file even when a recorded
    key opts it out** (review finding, confirmed by execution). An earlier
    revision excluded those, which defeated the field on the very case it
    was added for: with `tiers` present, conformant and opted out, and
    `model-badge` absent and opted out, `retained` came back `()` and the
    entry was suppressed anyway -- the live `tiers` body left the
    `RepoFingerprint` and `fingerprint_drift` went blind to it, reachable
    by nothing worse than opting out and then `git checkout`-ing the file
    back. It also put the two layers in flat contradiction about one input:
    `detect/optout.py` rung 1 answers `PRESENT` for that same region ("what
    is actually in the file wins over anything state believes"), while the
    planner was treating it as released. Physical presence is the fact;
    `retained` reports it, and consent is measured against what is really
    there rather than against what the key set says should be.

    **And "in the file" is asked the way `detect/optout.py` asks it, not
    the way `parse_regions` does** (review finding, confirmed by
    execution). An earlier revision derived `retained` from the parse
    alone, which put the field back in the same contradiction with rung 1
    one layer down: `parse_regions` is fence-aware by design and recognizes
    only the exact canonical marker grammar, so a region sitting in the
    file inside a closed ``` fence -- or one whose marker lines had picked
    up a trailing space -- landed in `not_present`, `retained` came back
    `()`, and a fully-keyed entry was suppressed with a live managed region
    still in it. `marker_region_names` is the scan `optout.py` added for
    exactly this premise ("the markers are GONE", not "no span was
    FOUND"), and it is imported rather than re-spelled -- `plan` already
    imports `detect.hashes`/`detect.inventory`, so the edge is
    precedented. Over-detection there only ever keeps an entry, which is
    the safe direction here (see that function).

    Frozen, like every other value object in this package (`Plan`,
    `Action`, `RepoFingerprint`, `fs.NeverWrite`)."""

    not_present: tuple[Region, ...]
    pending: tuple[Region, ...]
    retained: tuple[Region, ...]


def _pendency(
    entry: ManifestEntry, state: ArtifactState, current_text: str, opted_out: frozenset[str]
) -> _Pendency | None:
    """This entry's region verdict -- the declared regions not present, and
    the ones still pending after opt-outs -- or `None` when the entry has no
    trustworthy verdict at all.

    THE one place pendency is computed. `build_plan`'s suppression rule and
    `_chosen_anchor` both consume this single result, so the two can never
    disagree about which regions a run still owes, and the entry's file is
    parsed once per entry for BOTH of them rather than once per consumer --
    which is what the pre-story single-consumer shape already cost, and what
    adding a second consumer would otherwise have doubled.

    `None` means "no verdict", and it covers exactly two cases that must
    behave identically downstream: a non-`hybrid-managed-region` entry
    (nothing declares a region, so pendency is not a question about it) and
    a file `parse_regions` refuses -- `RegionParseError`/`MarkerError`/the
    reserved-format `NotImplementedError`. Both keep their `Action` and both
    get `chosen_anchor == ()`. That is what stops an unparseable file from
    reading as "zero pending" and silently retiring every region in it,
    which is the same "cannot safely re-parse, so degrade rather than guess"
    rule `detect.inventory._classify_hybrid` applies for the same three
    types.

    `not_present` is every declared region when `state is ABSENT` (nothing
    on disk, so nothing can already be present -- and nothing is parsed, so
    an absent entry is never `None`); otherwise only the regions
    `parse_regions` does not find (present but structurally non-conformant,
    so some -- not necessarily all -- declared regions are missing, and
    possibly none of them). `pending` is `not_present` minus the opted-out
    ones, and `retained` is every region the file physically still holds --
    the complement of `not_present`, WIDENED by any region whose marker
    lines survive somewhere `parse_regions` does not look
    (`detect/optout.py::marker_region_names`; see `_Pendency` for the
    suppression this protects). Only `retained` is widened that way:
    `pending` is what a run would INSERT, and a region the parser cannot
    see is one an insertion still owes."""
    if entry.artifact_class is not ArtifactClass.HYBRID_MANAGED_REGION:
        return None
    # ManifestEntry.__post_init__ guarantees a hybrid-managed-region entry
    # carries a non-None format -- narrows for the type checker, matching
    # `_classify_hybrid`'s own identical assertion.
    assert entry.format is not None
    try:
        if state is ArtifactState.ABSENT:
            not_present: tuple[Region, ...] = entry.regions
            surviving: frozenset[str] = frozenset()
        else:
            found_spans = parse_regions(current_text, entry.format)
            found_names = {span.name for span in found_spans}
            not_present = tuple(region for region in entry.regions if region.name not in found_names)
            surviving = marker_region_names(current_text, entry)
    except RegionParseError, MarkerError, NotImplementedError:
        return None
    not_present_names = {region.name for region in not_present}
    return _Pendency(
        not_present=not_present,
        pending=tuple(region for region in not_present if not _is_opted_out(entry.id, region.name, opted_out)),
        retained=tuple(
            region for region in entry.regions if region.name not in not_present_names or region.name in surviving
        ),
    )


def _is_fully_opted_out(pendency: _Pendency | None, *, content_known: bool) -> bool:
    """Whether this entry's every owed region is opted out -- the ONLY
    condition on which `build_plan` skips an otherwise-qualifying entry.

    `content_known` is `_current_text_verbose`'s second value: whether the
    `current_text` behind `pendency` is what the artifact actually holds,
    rather than the `''` an unreadable target degrades to.

    Requires a real verdict (`None` is never suppressed -- a whole-file
    entry declares no regions, and an unparseable file must not be guessed
    at), a NON-EMPTY `not_present` (something actually had to be owed), an
    empty `pending` (all of it opted out), and an empty `retained` (nothing
    the tool still owns is left in the file). An entry with nothing owed
    keeps the `Action` it produced before Story 8.5, `chosen_anchor == ()`
    and all -- see `_Pendency` for what suppressing it would have cost.

    **The case this DOES suppress pays that same cost knowingly.** A
    fully-opted-out entry leaves `artifact_hashes` too, so it drops out of
    the `RepoFingerprint` and `fingerprint_drift` stops seeing later changes
    to that file. That is not an oversight carried over from the defect
    `_Pendency` describes: a maintainer who opted every declared region out
    has taken the file out of the tool's supervision by their own
    deliberate act (FR-112), so there is no managed content left in it to
    drift. The difference from the nothing-owed case is exactly consent --
    and the `retained` clause is what makes that sentence TRUE rather than
    merely intended: without it a PARTIALLY opted-out entry, still holding
    a live managed region, satisfied the other three conditions and paid
    the same cost without having consented to it (review finding,
    `_Pendency`). The absence itself going unrecorded in `plan.json` is the
    separate, real gap tracked as `DW-FU-8-5`.

    **`content_known` is the fourth requirement, and it is what keeps that
    consent argument honest for a file nobody could read** (review finding,
    confirmed by execution). `_current_text_verbose` degrades a present-but-
    unreadable, non-regular-file or non-UTF-8 target to `''`, and `''`
    parses as "no region found", so every declared region landed in
    `not_present` and `retained` came back `()` -- not because the file
    holds no managed content, but because nothing could be measured about
    it. A `PRESENT_DIVERGENT` `CLAUDE.md` written as non-UTF-8 bytes was
    suppressed on that reasoning and left `artifact_hashes` while its
    markers, for all this module knows, sat right there in it. Consent is
    something the file has to be able to demonstrate: an unreadable one
    keeps its `Action`, which is the same "cannot safely re-parse, degrade
    rather than guess" direction `_pendency` takes for a file
    `parse_regions` refuses, and the same one `detect/optout.py::
    _has_content` takes before deriving an opt-out from a blank file.
    `ABSENT` is NOT this case and stays suppressible: its `''` is
    `classify()`'s own reported truth about the artifact, not a failed
    read, and the `<intent-contract>` names `ABSENT` explicitly."""
    return (
        pendency is not None
        and content_known
        and bool(pendency.not_present)
        and not pendency.pending
        and not pendency.retained
    )


def _chosen_anchor(
    entry: ManifestEntry, current_text: str, pendency: _Pendency | None
) -> tuple[tuple[str, str | None], ...]:
    """One `(region_name, matched_anchor)` pair per PENDING region --
    `_pendency`'s `pending`, resolved to the anchor each one would be
    inserted at.

    `()` when `pendency is None` (see `_pendency`: a whole-file artifact has
    no region to anchor, and an unparseable file must not be guessed at),
    and `()` when a `resolve_anchor` call itself raises
    `RegionParseError`/`MarkerError`/`NotImplementedError` -- degrading the
    WHOLE entry's `chosen_anchor`, never a partial list, the same rule
    `_pendency` applies to its own parse.

    Reads `pendency.pending`, never `not_present`: an opted-out region is
    not going to be inserted, so naming an anchor for it would put a
    proposed insertion point for a region nobody is inserting in front of
    the human reviewing the plan."""
    if pendency is None:
        return ()
    # A non-None `_Pendency` is only ever produced for a hybrid entry, which
    # `ManifestEntry.__post_init__` guarantees carries a format.
    assert entry.format is not None
    try:
        return tuple(
            (region.name, resolve_anchor(current_text, entry.format, region.anchor).matched)
            for region in pendency.pending
        )
    except RegionParseError, MarkerError, NotImplementedError:
        return ()


def _rationale(entry: ManifestEntry, state: ArtifactState) -> str:
    """A one-line justification for the proposed change -- P-05's own
    "human reviewing a change" framing -- distinct from `entry.rationale`
    (the MANIFEST's own "why this artifact exists at all", authored once,
    never about a specific run's proposed action)."""
    if state is ArtifactState.ABSENT:
        return f"{entry.path!r} is absent; materialize it as {entry.artifact_class.value}"
    # The only other actionable state is PRESENT_DIVERGENT, which only ever
    # occurs for hybrid-managed-region (see `_chosen_anchor`'s own guard).
    return (
        f"{entry.path!r} is present but missing one or more declared managed "
        "regions; insert them at their resolved anchors"
    )


def _git_head(process: PosixProcess, repo_root: Path) -> str | None:
    """`git rev-parse HEAD`'s stdout, stripped -- `None` on a non-zero exit
    (no commits yet, or `repo_root` is not a git repo at all).
    `PosixProcess.run` never raises for a non-zero exit -- only for a
    launch failure -- so a missing `git` executable is the one case this
    function does not degrade; that is a host misconfiguration, not an
    ordinary "not a git repo" outcome."""
    result = process.run(["git", "rev-parse", "HEAD"], cwd=repo_root, timeout_s=_GIT_TIMEOUT_S)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _repo_is_dirty(process: PosixProcess, repo_root: Path) -> bool:
    """`True` iff `git status --porcelain --untracked-files=normal`
    produces any output, OR the command exits non-zero (cannot confirm
    clean -- the conservative direction, per this story's Always bullet)."""
    result = process.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        timeout_s=_GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        return True
    return bool(result.stdout)


def build_plan(manifest: Manifest, inventory: Inventory, *, opted_out: frozenset[str] = frozenset()) -> Plan:
    """Map each qualifying `Classification` in `inventory` to one `Action`,
    plus a `RepoFingerprint` of `inventory.repo_root` (`inventory.
    repo_root` supplies the target repo -- there is no separate `repo_root`
    parameter, per this story's Always bullet).

    `opted_out` (Story 8.5) is a set of already-read `state.opt_out_key`
    strings -- `frozenset(state.opted_out)`, which the calling verb owes
    this function AFTER recording whatever `detect.optout` derived (see the
    module docstring's record-before-plan sequencing). Keyword-only and
    defaulted to empty, so every caller predating this story keeps
    byte-identical output. A `hybrid-managed-region` entry that was owed one
    or more region insertions and has had ALL of them opted out produces NO
    `Action` at all, for `PRESENT_DIVERGENT` and `ABSENT` alike, and
    therefore no `artifact_hashes` entry either: an opted-out region is
    never re-inserted, which is FR-112's whole requirement.

    Two entries are deliberately NOT suppressed, both of which would be a
    behavior change under the default empty `opted_out`: one whose file
    cannot be parsed (never "zero pending" -- see `_pendency`), and one that
    was owed NOTHING to begin with, whose emptiness no opt-out caused (see
    `_Pendency` and `_is_fully_opted_out`). The second keeps its `Action`
    and its `artifact_hashes` pair exactly as it did before this story,
    which is what keeps `fingerprint_drift` able to see it.

    `inventory.classifications` is already in manifest entry order (one
    `Classification` per `manifest.entries`, `classify()`'s own contract);
    `Plan.actions` is re-sorted by `artifact_id` here regardless, since
    manifest-entry order and artifact-id order are not the same thing and
    determinism must not depend on manifest authoring order -- two
    `build_plan()` calls against identical repo state must produce
    byte-identical `plan.json` (the epics AC's own requirement).

    Reads only what it needs: `_current_text_verbose` is called once per actionable
    entry and its result is reused for BOTH `chosen_anchor` resolution and
    `artifact_hashes` -- never read twice for the same artifact.

    Raises `ValueError` if `inventory` was not built from `manifest`
    (`classify(this_manifest, ...)`'s own contract is one `Classification`
    per `manifest.entries`, so any `entry_id` this loop cannot find in
    `manifest.entries` means the two arguments are a mismatched pair --
    review finding: without this check, the lookup below raised a bare,
    unnamed `KeyError` instead of the named, context-carrying `ValueError`
    every other caller-contract violation in this package reports).

    Raises `ValueError` for an `opted_out` that cannot answer `in` the way
    a key set does, for the same reason `opt_out_key_or_none` re-checks its
    own two halves: a type hint is not runtime enforcement, and the failure
    here is SILENT rather than loud.

    The guard tests the two things that actually go wrong, not the declared
    type (review finding, confirmed by execution). A bare `str` (or
    `bytes`) is the silent hazard: `in` against one is SUBSTRING
    containment, so passing one key as a string instead of a one-element
    set makes every key that happens to be a substring of it -- and, for a
    single-region entry, the key itself -- read as opted out, dropping
    entries from `actions` AND from `artifact_hashes` with no error at any
    layer. ELEMENTS THE GRAMMAR DOES NOT ADMIT are the other one: a
    `frozenset` of `(id, region)` PAIRS is the right container holding the
    wrong thing, matches no key, and silently suppresses nothing.

    That second check asks `state.is_opt_out_key`, not `isinstance(...,
    str)` (review finding, confirmed by execution). Testing only the TYPE
    left the failure it exists to catch wide open for every malformed key
    STRING: `'h#Tiers'`, `'h tiers'` and a bare `'h'` are all perfectly
    ordinary `str`s that match no key, suppress nothing, and re-insert a
    region FR-112 says must never be re-inserted, with no error at any
    layer. Every key `read_state` produces already satisfies the grammar --
    `opted_out` is schema-validated on the way in against the very pattern
    `is_opt_out_key` asks -- so this can only fire on a hand-minted key.

    It stops at the GRAMMAR and deliberately does not ask whether the
    artifact half names an entry of THIS manifest. The schema's artifact
    half is `[^\\s#]+`, so the path form `region_findings` prints beside the
    key (`CLAUDE.md#tiers` against an entry id of `h`) is itself a
    grammatical key and passes -- the one copy-paste hazard this check
    cannot close. Closing it would mean matching against `entries_by_id`,
    which would also hard-fail the documented natural call
    (`opted_out=state.opted_out`) whenever state carries a key for an entry
    the manifest has since dropped -- an orphan nothing prunes today. A
    caller error that suppresses nothing is the lesser of those two.

    Any other `Collection` of `str` is accepted, `frozenset` or not. The
    earlier revision demanded `set`/`frozenset` and rejected `tuple`,
    `list` and `dict.keys()` -- including `state.opted_out`'s OWN declared
    type, so `build_plan(m, i, opted_out=state.opted_out)` hard-failed --
    citing substring containment as the reason, which is false for every
    one of them: `in` is exact membership there. Rejecting a correct
    argument with an incorrect diagnosis is worse than accepting it."""
    if isinstance(opted_out, (str, bytes)) or not isinstance(opted_out, Collection):
        raise ValueError(
            "build_plan(opted_out=...) must be a collection of opt_out_key strings, not "
            f"{type(opted_out).__name__} -- `in` against a bare str is substring "
            "containment and would silently suppress entries"
        )
    inadmissible = sorted(
        {key if isinstance(key, str) else type(key).__name__ for key in opted_out if not is_opt_out_key(key)}
    )
    if inadmissible:
        raise ValueError(
            "build_plan(opted_out=...) must hold rendered opt_out_key strings; got "
            f"{inadmissible!r} -- an element the seed-state opted_out grammar does "
            "not admit matches no key and would silently suppress nothing"
        )
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    unknown_ids = sorted(
        {
            classification.entry_id
            for classification in inventory.classifications
            if classification.entry_id not in entries_by_id
        }
    )
    if unknown_ids:
        raise ValueError(
            "inventory references entry id(s) absent from manifest.entries -- "
            f"inventory was not built from this manifest: {unknown_ids!r}"
        )
    # A plain loop rather than the comprehension this used to be: the
    # suppression rule below has to see each entry's own pending-region
    # verdict, and that verdict must be computed exactly once and then
    # REUSED by `_chosen_anchor` -- a comprehension would either recompute
    # it (re-parsing the same file twice per entry) or let the two consumers
    # drift onto separately-computed answers.
    actioned: list[tuple[ManifestEntry, ArtifactState, str, _Pendency | None]] = []
    for classification in inventory.classifications:
        if classification.state not in _ACTIONABLE_STATES:
            continue
        entry = entries_by_id[classification.entry_id]
        current_text, content_known = _current_text_verbose(classification.state, inventory.repo_root, entry.path)
        pendency = _pendency(entry, classification.state, current_text, opted_out)
        if _is_fully_opted_out(pendency, content_known=content_known):
            # A hybrid entry that was owed insertions, has had every one of
            # them opted out, and retains no region the tool still owns:
            # nothing to insert, and no `Action` to review (Story 8.5). An
            # entry owed NOTHING is not this case and keeps its `Action`;
            # nor is `None` -- a whole-file entry, or a file that could not
            # be parsed; nor is one whose text could not be READ.
            continue
        actioned.append((entry, classification.state, current_text, pendency))

    actions = tuple(
        sorted(
            (
                Action(
                    artifact_id=entry.id,
                    artifact_class=entry.artifact_class,
                    current_state=state,
                    target_state=ArtifactState.PRESENT_CONFORMANT,
                    target_path=entry.path,
                    chosen_anchor=_chosen_anchor(entry, current_text, pendency),
                    rationale=_rationale(entry, state),
                )
                for entry, state, current_text, pendency in actioned
            ),
            key=lambda action: action.artifact_id,
        )
    )
    artifact_hashes = tuple(
        sorted(
            ((entry.id, hash_content(current_text)) for entry, _state, current_text, _pendency in actioned),
            key=lambda pair: pair[0],
        )
    )
    process = PosixProcess()
    repo_fingerprint = RepoFingerprint(
        git_head=_git_head(process, inventory.repo_root),
        dirty=_repo_is_dirty(process, inventory.repo_root),
        artifact_hashes=artifact_hashes,
    )
    return Plan(actions=actions, repo_fingerprint=repo_fingerprint)


def fingerprint_drift(plan: Plan, repo_root: Path) -> tuple[str, ...]:
    """Every way `repo_root` has diverged from the `RepoFingerprint` `plan`
    was built against -- one human-readable line per divergence, `()` when
    the plan is still a true description of the repo (AD-57).

    Covers all three `RepoFingerprint` fields, in that order: `git_head`
    (against a fresh `_git_head`), `dirty` (against a fresh
    `_repo_is_dirty`), and every `artifact_hashes` pair (against a fresh
    `hash_content` of that artifact's target). The correspondence between
    `actions` and `artifact_hashes` is checked in BOTH directions, and a
    mismatch either way is itself reported as a divergence: `build_plan`
    emits exactly one hash per action, so an orphan pair -- or an action
    with no pair -- means the `Plan` no longer holds its own construction
    invariant. `Plan.from_json_dict` validates that `actions` are unique and
    sorted but never cross-checks them against `artifact_hashes`, so a
    hand-edited `plan.json` that DROPS one pair would otherwise leave that
    artifact silently unverified -- the one hole through which the stale
    content this function exists to catch could still reach `apply`. A
    corrupted plan is refused, never partially verified.

    **Why this lives here, in the fingerprint's sole producer, and not in
    `seed/apply/`.** P-07 ("hash guards are checked in detect, never in
    apply; apply trusts the plan") is enforced structurally by
    `tests/meta/test_p07_no_hash_comparison_in_apply.py`, an import ban on
    `seed/apply/**`. This function asks a different question from the
    per-artifact hand-edit guard P-07 constrains (`detect.hashes.
    check_managed_file`): not "was THIS artifact hand-edited, and what
    becomes of it", but "is this whole `Plan` still true", whose only two
    outcomes are proceed-with-everything or refuse-everything. Placing it
    beside `build_plan` -- the one function that WRITES a `RepoFingerprint`
    -- satisfies the meta test without weakening it, and keeps producer and
    verifier in one file so they cannot drift apart.

    **Why content alone is not enough, and what is compared instead.** Every
    recorded hash for an `ABSENT` artifact is `hash_content("")`, because
    `_current_text_verbose` short-circuits that state without reading anything. The
    read this function performs degrades an absent, non-regular-file,
    unreadable, or non-UTF-8 target to `''` too -- so a pure content
    comparison silently equates "still absent" with "a binary, unreadable,
    or empty file appeared here since the plan was built", and apply would
    destroy that file. (An earlier revision of this function compared
    content alone and did exactly that; a review pass reproduced it by
    executing the real code, writing latin-1 bytes at an absent artifact's
    path and watching apply overwrite them.) Content is therefore compared
    only where content can decide, and STATE is compared everywhere else:
    an `ABSENT` artifact must still not exist (existence, not hash); a
    present one must still be readable as text (readability, not hash)
    before its hash means anything. Two accepted, fail-closed divergences
    from `build_plan`'s own read, both refusing rather than proceeding: an
    entry whose path escapes `repo_root` (classified `ABSENT` for that
    reason) may find a real file there and report drift, and a
    `present-divergent` entry that `build_plan` itself could not read is
    reported as unreadable rather than matched on its `''` hash. Both are
    already-pathological inputs, accepted rather than special-cased.

    Never raises for a non-git or empty `repo_root`: `_git_head`/
    `_repo_is_dirty` already degrade to `None`/`True` there, and comparing
    those against what `build_plan` recorded the same way is the whole
    point."""
    fingerprint = plan.repo_fingerprint
    process = PosixProcess()
    drift: list[str] = []

    current_head = _git_head(process, repo_root)
    if current_head != fingerprint.git_head:
        drift.append(f"git_head: the plan was built at {fingerprint.git_head!r}, the repo is now at {current_head!r}")

    current_dirty = _repo_is_dirty(process, repo_root)
    if current_dirty != fingerprint.dirty:
        drift.append(f"dirty: the plan was built with dirty={fingerprint.dirty}, the repo is now dirty={current_dirty}")

    # Review finding: a dict comprehension over `plan.actions` silently
    # collapses two actions sharing an `artifact_id` onto the last one,
    # leaving the first one's target unverified while this function still
    # reports `()`. `Plan.from_json_dict` rejects duplicate ids, but a
    # `Plan` built by direct construction (a supported entry path -- the
    # class carries no `__post_init__`) does not, and the runner's contract
    # is over an arbitrary `Plan`. A duplicate is itself a corrupted plan.
    actions_by_id: dict[str, Action] = {}
    duplicate_ids: set[str] = set()
    for action in plan.actions:
        if action.artifact_id in actions_by_id:
            duplicate_ids.add(action.artifact_id)
        actions_by_id[action.artifact_id] = action
    for artifact_id in sorted(duplicate_ids):
        drift.append(
            f"{artifact_id}: carried by more than one Action, so the plan cannot say"
            " which target that id's recorded hash describes"
        )

    # The mirror of the duplicate-ACTION-id check above. Review finding: only
    # one side was guarded, so `artifact_hashes=(("a", h), ("a", h))` reported
    # `()` while the equivalent duplicate on the actions side was refused --
    # against this function's own "a corrupted plan is refused, never partially
    # verified". `Plan.from_json_dict` validates uniqueness for `actions` only,
    # and direct construction validates neither, so both sides need it here.
    seen_hashed: set[str] = set()
    duplicate_hashed: set[str] = set()
    for artifact_id, _sha in fingerprint.artifact_hashes:
        if artifact_id in seen_hashed:
            duplicate_hashed.add(artifact_id)
        seen_hashed.add(artifact_id)
    for artifact_id in sorted(duplicate_hashed):
        drift.append(
            f"{artifact_id}: hashed more than once in the plan's fingerprint, so the"
            " plan cannot say which recorded hash that id's target must match"
        )

    hashed_ids = {artifact_id for artifact_id, _sha in fingerprint.artifact_hashes}
    for artifact_id in actions_by_id:
        if artifact_id not in hashed_ids:
            drift.append(
                f"{artifact_id}: carried by an Action but absent from the plan's"
                " fingerprint, so its content could not be verified"
            )
    for artifact_id, recorded_sha in fingerprint.artifact_hashes:
        action = actions_by_id.get(artifact_id)
        if action is None:
            drift.append(f"{artifact_id}: hashed in the plan's fingerprint but no Action carries it")
            continue
        target_path = action.target_path
        current_text, readable = _read_text_or_blank_verbose(repo_root, target_path)
        if action.current_state is ArtifactState.ABSENT:
            # The recorded hash is `hash_content("")` and CANNOT distinguish
            # "still absent" from "a binary/unreadable/empty file appeared
            # here since" -- all four degrade to `''`. Existence is what
            # separates them, so it is checked instead of the hash. Review
            # finding, verified by execution: without this, a hand-written
            # latin-1 file appearing at an absent artifact's path was
            # accepted as fresh and then destroyed by apply.
            target = repo_root / target_path
            # `.exists()` ALONE, matching `detect/inventory.py::_classify_entry`
            # ("if target is None or not target.exists(): return ABSENT") byte
            # for byte. Review finding, verified by execution: an added
            # `or target.is_symlink()` made the verifier stricter than the
            # producer, and a DANGLING symlink sitting at an absent artifact's
            # path is the state where they disagree -- `.exists()` follows the
            # broken link and reports False, so `build_plan` records ABSENT,
            # while `is_symlink()` reports True, so `fingerprint_drift` refused
            # the plan the instant it was produced. Re-planning yielded the
            # identical plan, so apply was unreachable until a human deleted the
            # link, and no remedy string could say so. Producer and verifier
            # agreeing is exactly why this function lives beside `build_plan`;
            # a symlinked target's own rollback bound is filed separately.
            if target.exists():
                drift.append(
                    f"{artifact_id}: {target_path!r} was absent when the plan was built and something exists there now"
                )
            continue
        if not readable:
            # Present when the plan was built, and now absent, not a regular
            # file, unreadable, or no longer valid UTF-8. A hash comparison
            # alone would MISS this whenever the recorded hash happens to be
            # `hash_content("")` -- a genuinely empty artifact -- so
            # readability is compared rather than inferred. Fail-closed: a
            # legitimately unreadable `present-divergent` artifact (which
            # `build_plan` would itself have hashed as `''`) is refused
            # rather than applied over. Only `hybrid-managed-region` entries
            # ever reach `PRESENT_DIVERGENT`, and one that is not readable
            # text is already pathological.
            drift.append(
                f"{artifact_id}: {target_path!r} was readable text when the plan was"
                " built and cannot be read as text now"
            )
            continue
        current_sha = hash_content(current_text)
        if current_sha != recorded_sha:
            drift.append(
                f"{artifact_id}: {target_path!r} hashed {recorded_sha} when the plan was"
                f" built, hashes {current_sha} now"
            )

    return tuple(drift)


def default_plan_path(repo_root: Path) -> Path:
    """`<repo_root>/.marshal/plan.json` -- already covered by the packaged
    `.gitignore` region's `model-ignores.gitignore.j2` template (confirmed
    present, not added by this story)."""
    return repo_root / ".marshal" / "plan.json"


def write_plan(plan: Plan, path: Path) -> None:
    """Write `plan` to `path` as indented JSON, atomically.

    Delegates entirely to `atomic_write_bytes` (Story 14.2), which already
    creates `path.parent` (`mkdir(parents=True, exist_ok=True)`) before
    writing -- this function adds no second, redundant `mkdir` of its own.

    `ensure_ascii=False`: `Plan` is "the single artifact a human reviews
    before Genesis writes anything" (P-04) -- a manifest-derived path,
    rationale, or anchor string carrying non-ASCII text should read as
    itself in `plan.json`, not as `\\uXXXX` escapes (review finding: the
    stdlib default escapes every non-ASCII code point)."""
    atomic_write_bytes(path, json.dumps(plan.to_json_dict(), indent=2, ensure_ascii=False).encode("utf-8"))


def load_plan(path: Path) -> Plan:
    """Read `path`, parse it as JSON, and rebuild a `Plan`.

    Raises `ValueError` naming the problem for malformed JSON CONTENT:
    `json.loads` raises `json.JSONDecodeError` for invalid JSON syntax --
    already a `ValueError` subclass, so it propagates unchanged and needs
    no translation here -- and `Plan.from_json_dict` (and the `Action`/
    `RepoFingerprint` calls it makes) raise a plain `ValueError` for a
    missing key, a wrong-shaped value, or an unrecognized enum value.

    A missing, unreadable, or directory `path` raises `read_text`'s own
    `OSError` (e.g. `FileNotFoundError`, `IsADirectoryError`) UNCHANGED --
    review finding: this function's docstring previously read as promising
    `ValueError` even for a file-access failure, which would contradict
    `fs.py`'s own established "never wraps a generic OSError" convention
    for this exact class of failure; this function draws the identical
    line `fs.py` already draws, one layer up."""
    return Plan.from_json_dict(json.loads(path.read_text(encoding="utf-8")))
