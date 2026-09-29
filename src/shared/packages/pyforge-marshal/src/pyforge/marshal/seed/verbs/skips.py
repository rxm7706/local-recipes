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
  function's own docstring.

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
never-write rung in `preconditions.py` matches the same action's path after
`Path.resolve()` has made it repo-relative. The two therefore see the same
string for every ordinary manifest path, and the normalization exists
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
import fnmatch
from collections.abc import Sequence
from typing import Protocol, TypeVar

from ..errors import UsageError
from ..plan.types import Plan, SkippedArtifact


def _materialize_patterns(patterns: Sequence[str]) -> tuple[str, ...]:
    """`patterns` as a tuple, EXACTLY as given (no strip), having consumed
    the argument exactly ONCE.

    A bare `str` is a valid `Sequence[str]` to both Python and a type
    checker, but iterating one yields single CHARACTERS -- and one of those
    characters is very often `*`, which matches everything. A caller who
    passed `"docs/*"` where a one-element tuple was meant would therefore
    skip EVERY action and get a plan that applies as a successful no-op,
    with no error anywhere. `NeverWrite.__post_init__` rejects exactly this
    shape for the never-write set; this is its equivalent for skips, which
    have no dataclass boundary of their own to hang it on.

    The one-consumption discipline is the point of this being a separate
    function (found in review): `patterns` may be any iterable, including a
    generator, and a generator read twice is EMPTY the second time --
    `record_skip((p for p in ("a/*", "b/*")), "c/*")` used to return
    `("c/*",)`, silently discarding both existing skips, because the
    validator consumed the generator and the builder then re-consumed the
    exhausted husk. Every caller here materializes through this function
    once and passes the resulting TUPLE onward."""
    if isinstance(patterns, str):
        raise UsageError(
            f"skip patterns must be a sequence of glob strings, got a bare str {patterns!r}",
            remedy=(f"wrap a single pattern in a tuple or list -- ({patterns!r},) rather than {patterns!r}"),
        )
    materialized = tuple(patterns)
    for pattern in materialized:
        if not isinstance(pattern, str):
            raise UsageError(
                f"every skip pattern must be a str, got {pattern!r}",
                remedy="remove or quote the non-string entry in the skip pattern list",
            )
    return materialized


def _require_patterns(patterns: Sequence[str]) -> tuple[str, ...]:
    """`patterns` as a tuple of STRIPPED, non-blank strings, rejecting every
    shape that would otherwise fail silently and catastrophically.

    Stripping mirrors `NeverWrite.__post_init__`/`Manifest.never_write`'s
    own construction-time strip, and is what makes this function's answers
    identical to `fs._matches`'s for every input rather than only for
    already-normalized ones: `_matches` only ever sees stripped patterns
    because `NeverWrite` strips before storing them, so a matcher that did
    not strip would disagree with it the moment a padded pattern reached it
    from a hand-edited `state.skips[]` -- and would disagree by silently
    matching NOTHING, which for a skip means writing a file the operator
    asked to leave alone.

    A pattern that is BLANK once stripped is rejected rather than kept
    (found in review): `("   ",)` used to normalize to `("",)`, which
    matches nothing at all -- the precise "looks like an active rule while
    protecting nothing" failure the strip above exists to prevent, arrived
    at through the strip itself. Both siblings already reject this shape
    (`NeverWrite.__post_init__` for the never-write set, `record_skip` for
    the pattern it is handed), so accepting it here was the odd one out. It
    also keeps `first_match`'s return honest: `first_match(("",), "")`
    returned `""` -- a FALSY non-`None` value that any `if
    first_match(...)` caller would read as a miss.

    Raises `UsageError` (exit 2) rather than returning a degraded result:
    every shape it rejects is a caller-supplied argument that is invalid,
    and there is no safe interpretation of any of them."""
    materialized = _materialize_patterns(patterns)
    stripped = tuple(pattern.strip() for pattern in materialized)
    for original, pattern in zip(materialized, stripped):
        if not pattern:
            raise UsageError(
                f"every skip pattern must be non-blank once stripped, got {original!r}",
                remedy=(
                    "remove the blank entry from the skip pattern list, or replace it"
                    " with a glob naming the artifact path to skip"
                ),
            )
    return stripped


def _normalize_relative_posix(target_path: str) -> str:
    """`target_path` with its purely COSMETIC POSIX noise removed -- a
    leading `./`, and any run of duplicate `/` -- so a skip glob matches the
    same path the never-write rung would refuse.

    Lexical only, deliberately (see the module docstring): duplicate
    separators and a `./` prefix mean nothing to any filesystem, so removing
    them cannot change which file a path names. A `..` segment is left
    ALONE, because collapsing one lexically is a claim about the filesystem
    (`a/../b` is `b` only when `a` is not a symlink) and this module has no
    disk access to check it against -- resolving those is the
    resolution-based rung's job, not this one's."""
    normalized = target_path
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def first_match(patterns: Sequence[str], relative_posix: str) -> str | None:
    """The FIRST pattern in `patterns` that matches `relative_posix`, or
    `None` if none does. The returned pattern is the STRIPPED form (see
    `_require_patterns`), which is the one that actually decided the match
    and therefore the one worth reporting.

    `relative_posix` is a repo-relative POSIX path string (an
    `Action.target_path`, or a target path already made relative to
    `repo_root` -- never an absolute or OS-native-separator path), matching
    the shape `fs._matches` is called with. First hit wins; which pattern
    wins among several simultaneous matches matters only for the message
    (`SkippedArtifact.pattern` names it), never for the decision, which is
    binary either way -- so "first in the caller's own argument order" is
    the rule, needing no further tie-breaking."""
    for pattern in _require_patterns(patterns):
        if fnmatch.fnmatchcase(relative_posix, pattern):
            return pattern
    return None


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


class _HasArtifactId(Protocol):
    """The one attribute `managed_after_skips` needs.

    A structural type rather than a `preconditions.ManagedRecord` import:
    `preconditions` imports `first_match` from THIS module, so naming its
    record type here would close an import cycle for the sake of a single
    string field. Declared as a read-only property so a frozen dataclass
    (which `ManagedRecord` is) satisfies it."""

    @property
    def artifact_id(self) -> str: ...


_RecordT = TypeVar("_RecordT", bound=_HasArtifactId)


def managed_after_skips(managed: Sequence[_RecordT], plan: Plan) -> tuple[_RecordT, ...]:
    """`managed` without the records for artifacts `plan` has SKIPPED.

    The affordance that makes `--skip` able to protect a hand-edit. Rungs
    3-5 of `preconditions.check_preconditions` walk `plan.actions`, from
    which `apply_skips` has already removed every skipped artifact, so they
    are skip-aware for free. Rung 6 is not: it walks the `managed` sequence
    the CALLER supplies, and by contract it checks every record in it. So
    without this function a hand-edited artifact stayed refused even after
    the operator skipped it, and the refusal's only offered remedy was
    `--force` -- which discards EVERY hand-edit in the repo, including the
    one they were trying to protect.

    Pure and total: preserves `managed`'s order, never mutates it, and
    matches on `artifact_id` only (a `SkippedArtifact` and a `ManagedRecord`
    for the same artifact may legitimately name different paths -- state
    records where the artifact IS, the plan's action names where it WOULD
    go). A record naming an artifact this plan never mentions is kept, as is
    every record when `plan.skipped` is empty.

    Deliberately a caller-side filter rather than something
    `check_preconditions` does internally: rung 6's contract is that it
    checks every record it is handed, which is what lets a caller decide the
    question ("did the operator ask to leave this alone?") in the one place
    that actually knows the answer."""
    skipped_ids = {entry.artifact_id for entry in plan.skipped}
    return tuple(record for record in managed if record.artifact_id not in skipped_ids)
