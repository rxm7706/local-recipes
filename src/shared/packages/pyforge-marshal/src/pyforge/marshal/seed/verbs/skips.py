"""`--skip`: the verbs layer's one glob semantic, plus the two operations
built on it (Story 10.4, FR-87).

Until this module, `--skip` existed nowhere in the package except inside a
remedy string suggesting a caller use it. Two distinct operations are
needed, and they belong to different lifetimes:

* `record_skip` is the STATE-side half -- it returns the updated pattern
  tuple its caller persists into `state.skips[]`, so a skip a human chose
  once survives the next run. It returns the tuple rather than writing it:
  `seed/state/` is a sibling story's surface, and this module reads and
  writes no state of its own.
* `apply_skips` is the PLAN-side half -- a pure transform that partitions a
  `Plan`, moving every matched action into `Plan.skipped` (Story 10.4's own
  additive `plan/types.py` field). The skip therefore lands in the
  serialized artifact a human reviews as a diff, not merely in a terminal
  rendering that `plan.json` would contradict by omission.
* `managed_after_skips` is the seam between the two halves and the
  PRECONDITION side -- it drops the `ManagedRecord`s a skip already took out
  of this run, so a caller can hand `preconditions.check_preconditions` a
  `managed` sequence that agrees with the plan it is checking. Without it,
  `--skip` cannot protect a hand-edit: rungs 3-5 walk `plan.actions` and are
  therefore skip-aware for free, but rung 6 walks the CALLER's records by
  contract ("rung 6 checks every `ManagedRecord` the caller supplies"), so
  the filtering has to happen on the caller's side of that call or not at
  all. It is not done inside `check_preconditions` deliberately -- see that
  function's own docstring. It drops a record two ways: its artifact is in
  `plan.skipped`, OR its path matches a skip PATTERN the caller passes. The
  second is the one that matters for a hand-edited `copied-managed` file,
  which `classify` marks `PRESENT_CONFORMANT` and therefore never gives an
  action -- so it can never enter `plan.skipped`, and a skip that named only
  `plan.skipped` was a silent no-op for exactly the file it was meant to
  protect (Story 82.12).
* `with_recorded_skips` closes the loop between the two lifetimes: it puts
  the patterns `state.skips[]` recorded on earlier runs in front of this
  run's own, so a skip is honoured on every later run rather than only the
  one that recorded it (Story 86.1, FR-87).

**Why `fnmatch.fnmatchcase`, deliberately identical to `fs._matches`.**
A skip glob and a never-write glob are the same KIND of rule -- both say
"do not write anything matching this" -- so they must not answer the same
`(pattern, path)` question two different ways; a user who learns that
`docs/*` covers `docs/a/b.md` for one must not discover it does not for the
other. `fnmatch.fnmatchcase` treats a run of `*` as matching ANYTHING
including `/`, which makes `docs/*` and `docs/**` behave identically and
OVER-matches rather than under-matches -- the safe direction for a rule
whose whole purpose is to withhold a write. `fnmatchcase`, never
`fnmatch.fnmatch`, for `fs._matches`' own stated reason: `fnmatch` folds
case through `os.path.normcase` (a no-op on POSIX, lowercasing on Windows),
so only `fnmatchcase` gives one platform-independent answer. The identity
extends to NORMALIZATION, not just to the matcher: `fs._matches` only ever
sees stripped patterns (its `NeverWrite` carrier strips at construction),
so this module strips too -- see `_require_patterns` for why a padded
pattern that silently matches nothing is the dangerous direction here.

The two implementations are pinned to each other by an agreement test
(`tests/unit/test_seed_verbs_skips.py`) over a shared pattern x path table
rather than by a shared helper: `fs.py`'s matcher is a module-private of a
module this story may not edit, and importing a private across a module
boundary is the shape this package guards against elsewhere. Stated plainly
so this reads as a chosen trade with a guard on it, not an oversight --
the same pattern `tests/meta/test_supervisor_run_path_agreement.py` already
uses for its own duplicated helpers.

**Lexical here, resolution-based there -- a stated, guarded difference.**
`apply_skips` matches an `Action.target_path` after a purely LEXICAL POSIX
normalization (a leading `./` stripped, duplicate `/` collapsed); the
never-write rung in `preconditions.py` (via `fs.never_write_match`) matches the
same action's path both as written (lexically normalized the same way) and
after `Path.resolve()` has made it repo-relative. The two therefore see the
same string for every ordinary manifest path, and the normalization exists
precisely so the ONE cheap way they used to disagree is closed: without it,
`target_path="./AGENTS.md"` was not skipped by `--skip AGENTS.md` while the
never-write rung refused it naming `resolved: 'AGENTS.md'` -- so an operator
copying the pattern out of a refusal into `--skip` got silence. Full
resolution is not available here by construction: this module is pure
(P-03), takes no `repo_root`, and touches no disk, so a symlinked ancestor
or a `..` segment is a shape only the resolution-based rung can see through.

This module imports only `dataclasses`, `fnmatch`, `typing`, `plan.types`,
and `errors` -- no state, no apply, no engine, no filesystem access of any
kind. `apply_skips` is pure (P-03): it reads no disk and re-derives nothing,
it only re-shapes the `Plan` it is handed.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Protocol, TypeVar

from ..detect.skip_match import _materialize_patterns, _normalize_relative_posix, _require_patterns, first_match
from ..errors import UsageError
from ..plan.types import Plan, SkippedArtifact


def record_skip(patterns: Sequence[str], pattern: str) -> tuple[str, ...]:
    """`patterns` with `pattern` appended, unless it is already present.

    Returns a new tuple; never mutates its argument (a caller persists the
    result into `state.skips[]` -- this module writes no state itself).
    Append order is preserved rather than sorted: the order a human added
    their skips in is the order `first_match` resolves them in, so
    re-sorting here would silently change WHICH pattern a
    `SkippedArtifact` reports.

    `pattern` is stripped before both the blank check and the
    duplicate check, matching `NeverWrite.__post_init__`/
    `Manifest.never_write`'s identical construction-time strip -- a padded
    pattern (`" docs/*"`) is non-blank yet matches no real path, so it
    would look like an active rule while protecting nothing. The
    duplicate check compares STRIPPED forms on both sides: an already-stored
    padded entry (from a hand-edited `state.skips[]`) must not let the same
    rule be recorded a second time, which would grow the list by one dead
    entry on every run. The stored entries themselves are returned
    untouched -- this function adds a pattern, it does not rewrite a
    caller's existing state.

    Raises `UsageError` (exit 2) for a blank or non-`str` pattern, and for
    a `patterns` that is a bare `str` rather than a sequence of them (see
    `_require_patterns`): each is a caller-supplied argument that is
    invalid, which is exactly the leaf `errors.py` defines that outcome for
    -- never a silent no-op, which would leave the caller believing a skip
    was recorded."""
    if not isinstance(pattern, str) or not pattern.strip():
        raise UsageError(
            f"skip pattern must be a non-blank string, got {pattern!r}",
            remedy=("pass a glob naming the artifact path to skip, e.g. --skip 'docs/dreams/*.md'"),
        )
    # ONE consumption of `patterns`, reused for both the comparison and the
    # result (found in review): a generator read a second time is empty, so
    # validating and then re-materializing silently dropped every existing
    # pattern. `_materialize_patterns` also rejects the bare-`str` shape,
    # which would otherwise tuple() into a tuple of characters.
    existing = _materialize_patterns(patterns)
    normalized = _require_patterns(existing)
    stripped = pattern.strip()
    if stripped in normalized:
        return existing
    return (*existing, stripped)


def with_recorded_skips(recorded: Sequence[str], patterns: Sequence[str]) -> tuple[str, ...]:
    """The skip patterns a run applies: every pattern `state.skips[]` recorded
    on an earlier run, then each of this run's own `patterns` not already among
    them (Story 86.1, FR-87, `DW-FU-11-4`).

    FR-87 says a skip is "honored on every subsequent run", and `adopt` records
    one into `state.skips[]` for exactly that reason -- but until this function
    nothing read it back, so a skip lasted one run: the next `update` or
    re-adopt planned the artifact again (a skipped file created, a skipped
    hand-edit regenerated or refused at rung 6). `adopt` and `update` both hand
    the result to `apply_skips` and `managed_after_skips`, so a recorded skip and
    a `--skip` given now mean the same thing to the plan and to rung 6.

    Recorded patterns come first, in their stored order, so the pattern a
    `SkippedArtifact` names is the one the operator chose first; a run pattern
    is added by `record_skip`, which strips it and drops a duplicate. Both
    arguments are validated the way every other entry point here validates
    them -- a bare `str` or a blank pattern raises `UsageError`. This function
    writes no state: what `adopt` records into `state.skips[]` is still decided
    by `adopt`."""
    combined = _materialize_patterns(recorded)
    _require_patterns(combined)
    for pattern in _materialize_patterns(patterns):
        combined = record_skip(combined, pattern)
    return combined


def apply_skips(plan: Plan, patterns: Sequence[str]) -> Plan:
    """A new `Plan` with every action whose `target_path` matches one of
    `patterns` MOVED out of `actions` and into `skipped`.

    Pure: reads no disk, re-derives nothing, and never mutates `plan`.

    Three properties, each of which is easy to get wrong:

    * **The fingerprint moves with the action.** A skipped artifact's pair
      is dropped from `repo_fingerprint.artifact_hashes` as its action
      leaves `actions`. An apply runner's drift check cross-references
      those two collections in BOTH directions -- a hashed id carrying no
      action is an integrity failure that refuses the whole plan -- so
      filtering only one side would produce a plan every subsequent apply
      rejects as corrupt. A skipped artifact is deliberately not re-keyed
      into the fingerprint under another name either: it is not going to be
      written, so this plan asserts nothing about its on-disk state.
    * **Idempotent.** `apply_skips(apply_skips(p, pats), pats)` equals
      `apply_skips(p, pats)`. That holds only because an already-`skipped`
      entry is CARRIED THROUGH rather than recomputed: on the second pass
      nothing in `actions` matches any more, so a rebuild-from-actions-only
      would silently empty `skipped` again -- turning the second call into
      a quiet un-skip.
    * **Matching is lexical, not resolution-based.** An action's
      `target_path` is normalized with `_normalize_relative_posix` (leading
      `./` stripped, duplicate `/` collapsed) before it is matched, so the
      same pattern an operator copies out of a never-write refusal also
      skips the artifact. Anything deeper -- a `..` segment, a symlinked
      ancestor -- is only visible to the resolution-based rung; see the
      module docstring.
    * **Order and identity are preserved.** Surviving `actions` keep their
      relative order (`build_plan` sorted them by `artifact_id`, and this
      function only removes members), `skipped` is sorted by `artifact_id`
      to match, and -- for any `plan` that already holds it -- the two stay
      disjoint, because an action is MOVED, never copied. All three are
      re-validated at the `Plan.from_json_dict` boundary.

    A pattern matching nothing is not an error -- the result equals `plan`
    -- and a pattern matching everything is not either: the resulting empty
    `actions` tuple is a legitimate no-op run (AD-60 defines idempotence as
    plan-emptiness), not a failure. Only an artifact that carries an
    `Action` can be skipped; there is nothing to withhold from a repo for
    an artifact this plan was never going to touch.

    `patterns` is validated ONCE, before the loop rather than inside it
    (found in review): validation reached only through `first_match` was
    data-dependent, so `apply_skips(Plan(actions=(), ...), "docs/*")` -- a
    bare `str`, the exact typo the validator exists to catch -- returned
    cleanly with no `UsageError` at all, and a one-shot iterable was
    re-consumed once per action, leaving every action after the first
    matched against nothing."""
    normalized = _require_patterns(patterns)
    kept = []
    newly_skipped = []
    for action in plan.actions:
        matched = first_match(normalized, _normalize_relative_posix(action.target_path))
        if matched is None:
            kept.append(action)
            continue
        newly_skipped.append(
            SkippedArtifact(
                artifact_id=action.artifact_id,
                target_path=action.target_path,
                pattern=matched,
            )
        )
    if not newly_skipped:
        # Nothing moved -- return `plan` itself rather than an equal rebuild.
        # Equality would hold either way (every type here is a frozen
        # dataclass compared by value), but returning the identical object
        # makes "a pattern matching nothing changes nothing" true by
        # construction rather than by a value comparison a future field
        # addition could quietly break.
        return plan
    skipped_ids = {entry.artifact_id for entry in newly_skipped}
    skipped = tuple(sorted((*plan.skipped, *newly_skipped), key=lambda entry: entry.artifact_id))
    # `dataclasses.replace`, never a field-by-field reconstruction (found in
    # review): naming every field here would silently DROP any field a
    # future story adds to `RepoFingerprint` or `Plan` -- a data-loss bug
    # with no error and no failing test at the moment it is introduced,
    # since the new field simply reverts to its default. `replace` carries
    # everything this function does not explicitly change.
    fingerprint = dataclasses.replace(
        plan.repo_fingerprint,
        artifact_hashes=tuple(
            (artifact_id, sha)
            for artifact_id, sha in plan.repo_fingerprint.artifact_hashes
            if artifact_id not in skipped_ids
        ),
    )
    return dataclasses.replace(plan, actions=tuple(kept), repo_fingerprint=fingerprint, skipped=skipped)


class _ManagedLike(Protocol):
    """A managed record as `managed_after_skips` sees it: the two attributes it needs.

    A structural type rather than a `preconditions.ManagedRecord` import:
    `preconditions` is the verbs-layer module that owns the record, so naming
    its type here would couple this pure module to it for the sake of two
    string fields. Declared as read-only properties so a frozen dataclass
    (which `ManagedRecord` is) satisfies it."""

    @property
    def artifact_id(self) -> str: ...

    @property
    def path(self) -> str: ...


_RecordT = TypeVar("_RecordT", bound=_ManagedLike)


def managed_after_skips(managed: Sequence[_RecordT], plan: Plan, patterns: Sequence[str] = ()) -> tuple[_RecordT, ...]:
    """`managed` without the records for artifacts `plan` has SKIPPED, and
    without those whose path matches one of `patterns`.

    The affordance that makes `--skip` able to protect a hand-edit. Rungs
    3-5 of `preconditions.check_preconditions` walk `plan.actions`, from
    which `apply_skips` has already removed every skipped artifact, so they
    are skip-aware for free. Rung 6 is not: it walks the `managed` sequence
    the CALLER supplies, and by contract it checks every record in it. So
    without this function a hand-edited artifact stayed refused even after
    the operator skipped it, and the refusal's only offered remedy was
    `--force` -- which discards EVERY hand-edit in the repo, including the
    one they were trying to protect.

    **Why it takes patterns.** `plan.skipped` only ever holds an artifact that
    carried an `Action` (`apply_skips` MOVES an action there), and a
    hand-edited `copied-managed` file never has one: `classify` marks it
    `PRESENT_CONFORMANT` whatever its bytes say (P-07) and `build_plan` emits
    actions only for `ABSENT`/`PRESENT_DIVERGENT`. A filter by `plan.skipped`
    alone therefore left `--skip <that file's path>` a silent no-op, with
    `--force` -- which discards every hand-edit -- as rung 6's only remaining
    override. So a record is ALSO dropped when its `path` matches a pattern
    the operator passed, by the identical lexical rule `apply_skips` applies
    to an action's `target_path` (`_normalize_relative_posix`, then
    `first_match`), so one `--skip` glob means the same thing to both.
    `adopt` and `update` both pass their `--skip` patterns together with the
    ones `state.skips[]` recorded (`with_recorded_skips`); a caller with no
    patterns passes none and gets the `plan.skipped` filter alone.

    Pure: reads no disk, preserves `managed`'s order, never mutates it, and
    raises `UsageError` for a bad `patterns` (see below) even when `managed`
    is empty. It matches a plan-skipped artifact on `artifact_id` only (a `SkippedArtifact`
    and a `ManagedRecord` for the same artifact may legitimately name
    different paths -- state records where the artifact IS, the plan's action
    names where it WOULD go). A record naming an artifact this plan never
    mentions and matching no pattern is kept, as is every record when
    `plan.skipped` and `patterns` are both empty. `patterns` is validated by
    the same `_require_patterns` as every other entry point here, so a bare
    `str` or a blank entry raises `UsageError` rather than silently skipping
    everything or nothing.

    Deliberately a caller-side filter rather than something
    `check_preconditions` does internally: rung 6's contract is that it
    checks every record it is handed, which is what lets a caller decide the
    question ("did the operator ask to leave this alone?") in the one place
    that actually knows the answer."""
    normalized = _require_patterns(patterns)
    skipped_ids = {entry.artifact_id for entry in plan.skipped}
    return tuple(
        record
        for record in managed
        if record.artifact_id not in skipped_ids
        and first_match(normalized, _normalize_relative_posix(record.path)) is None
    )
