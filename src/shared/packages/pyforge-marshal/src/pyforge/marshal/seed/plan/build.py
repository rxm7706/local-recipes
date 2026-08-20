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
per-entry branching here that could produce more than one, or skip one
that qualifies, beyond the plain state-membership test itself.

**Why this module resolves paths directly rather than re-deriving
`detect.inventory._resolve_within_repo`'s containment check.** `classify()`
has ALREADY run that check once, for every entry, to produce the very
`ArtifactState` this module switches on: an entry classified `ABSENT`
because its path escapes `repo_root` is indistinguishable here from one
genuinely missing (both are `ABSENT`, and this module's own `_current_text`
never touches the filesystem for that state at all -- see below). An entry
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
already-read `state.opted_out` keys, and a hybrid entry whose PENDING
regions -- declared, minus present, minus opted-out -- are empty produces no
`Action` at all, so an opted-out region is never re-inserted. Keeping the
read out of this module preserves S-9.6's purity property and its
byte-identical-output determinism: the verb layer already owns reading
state, and passes `frozenset(state.opted_out)` straight through. The one
thing imported from `seed/state/` is `opt_out_key`, a pure key-spelling
function, so the `<artifact-id>#<region>` wire form is spelled once for the
whole package rather than re-derived here.

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
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_bytes
from pyforge.core.process import PosixProcess

from ..detect.hashes import hash_content
from ..detect.inventory import ArtifactState, Inventory
from ..model.manifest import ArtifactClass, Manifest, ManifestEntry, Region
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions, resolve_anchor
from ..state import opt_out_key
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


def _current_text(state: ArtifactState, repo_root: Path, entry_path: str) -> str:
    """The one text both `_chosen_anchor` and `build_plan`'s own
    `artifact_hashes` computation read/hash -- a single shared definition
    so the two can never see a different byte stream for the same
    artifact.

    `ABSENT` never touches the filesystem: `''` is `classify()`'s own
    reported truth about this artifact (genuinely missing, or resolving
    outside `repo_root` -- either way, nothing safe to read). A
    present-but-non-regular-file, unreadable, or non-UTF-8 target also
    degrades to `''` -- the identical fallback `detect.inventory.
    _classify_hybrid` already applies when its own read hits the same
    failure (this story's Always bullet: "`current_text` is `\"\"` for an
    absent or unreadable target").

    Only ever reads a real path for a `PRESENT_DIVERGENT` entry, and only
    because `classify()` has ALREADY proven -- to produce that very state
    -- that `entry_path` resolves to an existing target within
    `repo_root` (see the module docstring)."""
    if state is ArtifactState.ABSENT:
        return ""
    return _read_text_or_blank(repo_root, entry_path)


def _read_text_or_blank(repo_root: Path, entry_path: str) -> str:
    """The READ half of `_current_text`, with no `ArtifactState` gate in
    front of it: the target's UTF-8 text, degrading to `''` for an absent,
    non-regular-file, unreadable, or non-UTF-8 target.

    Factored out of `_current_text` (rather than duplicated inside
    `fingerprint_drift`) so the one degradation rule this module applies at
    plan-BUILD time is byte-for-byte the same rule it applies at
    VERIFICATION time -- two independent spellings of "unreadable means
    `''`" is exactly the producer/verifier drift `fingerprint_drift` living
    beside `build_plan` exists to prevent. `_current_text` keeps its own
    `ABSENT` short-circuit in front of this call; `fingerprint_drift`
    deliberately does not (see its docstring)."""
    text, _readable = _read_text_or_blank_verbose(repo_root, entry_path)
    return text


def _read_text_or_blank_verbose(repo_root: Path, entry_path: str) -> tuple[str, bool]:
    """`_read_text_or_blank`'s answer, plus whether the target was actually
    READ (`True`) or merely degraded to `''` (`False`).

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
    and compares READABILITY as well as bytes. `_current_text` discards it,
    preserving `build_plan`'s behavior byte-for-byte."""
    target = repo_root / entry_path
    if not target.is_file():
        return "", False
    try:
        return target.read_text(encoding="utf-8"), True
    except (OSError, UnicodeDecodeError):
        return "", False


def _is_opted_out(entry_id: str, region_name: str, opted_out: frozenset[str]) -> bool:
    """Whether `opted_out` records this entry/region pair, keyed through
    `state.opt_out_key` so the wire spelling lives in exactly one place.

    An entry id `opt_out_key` REFUSES answers `False` rather than
    propagating its `ValueError`. `ManifestEntry` requires only a non-blank
    `id`, so an id carrying an interior space (or a literal `#`) is legally
    constructible while the state schema's `opted_out` grammar cannot spell
    it -- and a key that grammar rejects can never appear in a schema-valid
    `opted_out` set, so "not opted out" is the correct and total answer.
    Raising here instead would make `build_plan` crash on a manifest it
    planned perfectly well before this story. (A region name cannot reach
    that branch at all: `Region.__post_init__` already requires
    `REGION_NAME_PATTERN`, which is the key's own region half verbatim.)"""
    try:
        key = opt_out_key(entry_id, region_name)
    except ValueError:
        return False
    return key in opted_out


def _pending_regions(
    entry: ManifestEntry, state: ArtifactState, current_text: str, opted_out: frozenset[str]
) -> tuple[Region, ...] | None:
    """The declared regions that still need inserting this run -- declared,
    minus those already present, minus those opted out -- or `None` when
    this entry has no trustworthy pending-region verdict at all.

    THE one place pendency is computed. `build_plan`'s suppression rule and
    `_chosen_anchor` both consume this single result, so the two can never
    disagree about which regions a run still owes, and the entry's file is
    parsed exactly once per `build_plan` call rather than once per consumer.

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

    For a hybrid entry: every declared region when `state is ABSENT`
    (nothing on disk, so nothing can already be present -- and nothing is
    parsed, so an absent entry is never `None`); otherwise only the regions
    `parse_regions` does not find (present but structurally non-conformant,
    so some -- not necessarily all -- declared regions are missing)."""
    if entry.artifact_class is not ArtifactClass.HYBRID_MANAGED_REGION:
        return None
    # ManifestEntry.__post_init__ guarantees a hybrid-managed-region entry
    # carries a non-None format -- narrows for the type checker, matching
    # `_classify_hybrid`'s own identical assertion.
    assert entry.format is not None
    try:
        if state is ArtifactState.ABSENT:
            not_present: tuple[Region, ...] = entry.regions
        else:
            found_spans = parse_regions(current_text, entry.format)
            found_names = {span.name for span in found_spans}
            not_present = tuple(
                region for region in entry.regions if region.name not in found_names
            )
    except (RegionParseError, MarkerError, NotImplementedError):
        return None
    return tuple(
        region
        for region in not_present
        if not _is_opted_out(entry.id, region.name, opted_out)
    )


def _chosen_anchor(
    entry: ManifestEntry, current_text: str, pending: tuple[Region, ...] | None
) -> tuple[tuple[str, str | None], ...]:
    """One `(region_name, matched_anchor)` pair per PENDING region --
    `_pending_regions`'s result, resolved to the anchor each one would be
    inserted at.

    `()` when `pending is None` (see `_pending_regions`: a whole-file
    artifact has no region to anchor, and an unparseable file must not be
    guessed at), and `()` when a `resolve_anchor` call itself raises
    `RegionParseError`/`MarkerError`/`NotImplementedError` -- degrading the
    WHOLE entry's `chosen_anchor`, never a partial list, the same rule
    `_pending_regions` applies to its own parse."""
    if pending is None:
        return ()
    # Non-None `pending` is only ever produced for a hybrid entry, which
    # `ManifestEntry.__post_init__` guarantees carries a format.
    assert entry.format is not None
    try:
        return tuple(
            (region.name, resolve_anchor(current_text, entry.format, region.anchor).matched)
            for region in pending
        )
    except (RegionParseError, MarkerError, NotImplementedError):
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


def build_plan(
    manifest: Manifest, inventory: Inventory, *, opted_out: frozenset[str] = frozenset()
) -> Plan:
    """Map each qualifying `Classification` in `inventory` to one `Action`,
    plus a `RepoFingerprint` of `inventory.repo_root` (`inventory.
    repo_root` supplies the target repo -- there is no separate `repo_root`
    parameter, per this story's Always bullet).

    `opted_out` (Story 8.5) is a set of already-read `state.opt_out_key`
    strings -- `frozenset(state.opted_out)`, passed by the verb layer that
    owns the state read. Keyword-only and defaulted to empty, so every
    caller predating this story keeps byte-identical output. A
    `hybrid-managed-region` entry whose pending regions are empty -- every
    declared region already present, or opted out -- produces NO `Action` at
    all, for `PRESENT_DIVERGENT` and `ABSENT` alike, and therefore no
    `artifact_hashes` entry either: an opted-out region is never
    re-inserted, which is FR-112's whole requirement. An entry whose file
    cannot be parsed is never "zero pending" and keeps its `Action` (see
    `_pending_regions`).

    `inventory.classifications` is already in manifest entry order (one
    `Classification` per `manifest.entries`, `classify()`'s own contract);
    `Plan.actions` is re-sorted by `artifact_id` here regardless, since
    manifest-entry order and artifact-id order are not the same thing and
    determinism must not depend on manifest authoring order -- two
    `build_plan()` calls against identical repo state must produce
    byte-identical `plan.json` (the epics AC's own requirement).

    Reads only what it needs: `_current_text` is called once per actionable
    entry and its result is reused for BOTH `chosen_anchor` resolution and
    `artifact_hashes` -- never read twice for the same artifact.

    Raises `ValueError` if `inventory` was not built from `manifest`
    (`classify(this_manifest, ...)`'s own contract is one `Classification`
    per `manifest.entries`, so any `entry_id` this loop cannot find in
    `manifest.entries` means the two arguments are a mismatched pair --
    review finding: without this check, the lookup below raised a bare,
    unnamed `KeyError` instead of the named, context-carrying `ValueError`
    every other caller-contract violation in this package reports)."""
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
    actioned: list[tuple[ManifestEntry, ArtifactState, str, tuple[Region, ...] | None]] = []
    for classification in inventory.classifications:
        if classification.state not in _ACTIONABLE_STATES:
            continue
        entry = entries_by_id[classification.entry_id]
        current_text = _current_text(classification.state, inventory.repo_root, entry.path)
        pending = _pending_regions(entry, classification.state, current_text, opted_out)
        if pending is not None and not pending:
            # A hybrid entry with a real verdict and nothing left pending:
            # every declared region is already present or opted out, so
            # there is nothing to insert and no `Action` to review (Story
            # 8.5). `None` -- a whole-file entry, or a file that could not
            # be parsed -- is deliberately NOT suppressed.
            continue
        actioned.append((entry, classification.state, current_text, pending))

    actions = tuple(
        sorted(
            (
                Action(
                    artifact_id=entry.id,
                    artifact_class=entry.artifact_class,
                    current_state=state,
                    target_state=ArtifactState.PRESENT_CONFORMANT,
                    target_path=entry.path,
                    chosen_anchor=_chosen_anchor(entry, current_text, pending),
                    rationale=_rationale(entry, state),
                )
                for entry, state, current_text, pending in actioned
            ),
            key=lambda action: action.artifact_id,
        )
    )
    artifact_hashes = tuple(
        sorted(
            (
                (entry.id, hash_content(current_text))
                for entry, _state, current_text, _pending in actioned
            ),
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
    `_current_text` short-circuits that state without reading anything. The
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
        drift.append(
            f"git_head: the plan was built at {fingerprint.git_head!r},"
            f" the repo is now at {current_head!r}"
        )

    current_dirty = _repo_is_dirty(process, repo_root)
    if current_dirty != fingerprint.dirty:
        drift.append(
            f"dirty: the plan was built with dirty={fingerprint.dirty},"
            f" the repo is now dirty={current_dirty}"
        )

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
            drift.append(
                f"{artifact_id}: hashed in the plan's fingerprint but no Action carries it"
            )
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
                    f"{artifact_id}: {target_path!r} was absent when the plan was built"
                    " and something exists there now"
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
    atomic_write_bytes(
        path, json.dumps(plan.to_json_dict(), indent=2, ensure_ascii=False).encode("utf-8")
    )


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
