"""Plan and Action types, and the tamper-evident repo fingerprint (Story
9.6, architecture FR-82/AD-57/AD-59/AD-60/P-04/P-05/P-07).

Detect (S-9.1--9.5) can already classify every manifest entry against a
target repo (`detect.inventory.classify`), but a `Classification` is not
the artifact a human reviews before Genesis writes anything: it names a
STATE, not a proposed CHANGE, and it carries no record of what repo state
it was computed against. This module is that artifact's shape --
`Action` (P-05: "Every `Action` in a `Plan` names its artifact id, class,
current state, target state, and rationale"), `RepoFingerprint` (AD-57's
tamper-evidence: a git HEAD + dirty flag + per-artifact content hash, so a
later `apply` story can refuse a `Plan` whose fingerprint no longer
matches), and `Plan` itself (P-04: "`Plan` is a serializable dataclass.
Apply consumes only a `Plan` -- never re-derives state").

`seed.plan.build.build_plan` is this module's one producer; nothing here
computes a `Plan` itself (P-03's purity discipline, mirrored across every
`detect`/`regions` module this package ships) -- these are plain data
carriers plus their own JSON codec.

**JSON convention.** `to_json_dict`/`from_json_dict` are hand-rolled, never
`dataclasses.asdict`/a generic decoder -- mirroring `detect.findings.Finding
.to_json_dict`'s "plain values, fixed key order" convention, extended here
to round-trip through `from_json_dict` as well (this package's first: no
prior `from_json_dict` precedent exists to follow beyond `to_json_dict`'s
own shape). A JSON array has no tuple type, so every tuple field
(`Action.chosen_anchor`, `RepoFingerprint.artifact_hashes`, `Plan.actions`,
`Plan.skipped`)
serializes as a JSON array and is rebuilt as a tuple on the way back in --
`Plan.from_json_dict(json.loads(json.dumps(plan.to_json_dict()))) == plan`
must hold for every `Plan` `build_plan()` can produce (the Always bullet's
own round-trip requirement), which only holds if `from_json_dict` rebuilds
tuples-of-tuples exactly, never leaves a list sitting where the original
carried a tuple.

`from_json_dict` is this module's one boundary between TRUSTED data
(`build_plan`'s own computed output, constructed directly via
`Action(...)`/`RepoFingerprint(...)`/`Plan(...)` with no validation of its
own -- mirroring `detect.inventory.Classification`/`LegacyRecord`'s
identical "computed output needs no `__post_init__` re-check" stance) and
UNTRUSTED data (a hand-corrupted `.marshal/plan.json` a human or a bug
might have edited). Every `from_json_dict` raises a plain `ValueError`
naming the missing key or the offending value for anything that does not
fit -- never `SeedError`/one of its six leaves (this story's own Never
bullet: nothing here is a `seed/verbs`-level operational failure, it is a
caller-contract violation on load, the same class `manifest.py::
load_manifest`'s own `_require_text` reports before wrapping as
`ManifestError` one layer up -- there is no such wrapping layer for a plan,
so the plain `ValueError` is the final word here).

No `__post_init__` validation on `Action`/`RepoFingerprint`/`Plan`
themselves, for the same reason `Classification`/`LegacyRecord`
(`detect/inventory.py`) carry none: each is a well-typed COMPUTED shape by
construction inside `build_plan`, not externally supplied data a
constructor must defend against -- `from_json_dict` is where untrusted
input is checked, once, at the one boundary it actually crosses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..detect.inventory import ArtifactState
from ..model.manifest import ArtifactClass


def _require_key(data: dict[str, Any], key: str, *, context: str) -> Any:
    """Look up `key` in `data`, raising `ValueError` naming both the
    missing key and which type's `from_json_dict` was reading it --
    `KeyError` alone would not say WHICH document key is missing without a
    caller re-reading the traceback, and every other malformed-input path
    in this module reports its own location the same explicit way."""
    if key not in data:
        raise ValueError(f"{context}: missing required key {key!r}")
    return data[key]


def _require_str(value: Any, *, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context}: expected a str, got {value!r}")
    return value


def _require_non_blank_str(value: Any, *, context: str) -> str:
    """`_require_str` plus a blank rejection, for the fields where an empty
    string is not a value but a hole.

    `SkippedArtifact`'s three fields are all identifiers a human READS out
    of `plan.json` -- an artifact id, the path it names, and the `--skip`
    glob responsible -- so a blank one renders as an empty line in the
    artifact under review, saying nothing while looking like a record
    (review finding). Both of this field's siblings already refuse the same
    shape at their own boundaries: `NeverWrite.__post_init__` for a
    never-write pattern, `seed.verbs.skips.record_skip` for the skip pattern
    it is handed. This is that rule at the load boundary."""
    text = _require_str(value, context=context)
    if not text.strip():
        raise ValueError(f"{context}: expected a non-blank str, got {value!r}")
    return text


def _require_optional_str(value: Any, *, context: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{context}: expected a str or null, got {value!r}")
    return value


def _require_bool(value: Any, *, context: str) -> bool:
    # `isinstance(value, bool)`, not a truthy check -- `bool` is a subtype
    # of `int` in Python, and JSON's own `true`/`false` decode to real
    # Python `bool`, so a JSON `0`/`1` (never emitted by `to_json_dict`,
    # but a hand-corrupted file may carry one) must be reported as
    # malformed rather than silently coerced.
    if not isinstance(value, bool):
        raise ValueError(f"{context}: expected a bool, got {value!r}")
    return value


def _require_pair_list(value: Any, *, context: str) -> list[Any]:
    """Every 2-element-list-of-`[key, value]`-pairs field
    (`chosen_anchor`, `artifact_hashes`) shares this one shape check --
    a JSON array of 2-element JSON arrays, never a JSON object (a mapping
    cannot preserve `chosen_anchor`'s deliberate duplicate-region-name-safe
    ordering, and neither field is keyed by anything unique enough to be a
    JSON object key in the general case)."""
    if not isinstance(value, list) or not all(isinstance(item, list) and len(item) == 2 for item in value):
        raise ValueError(f"{context}: expected a list of 2-element [key, value] pairs, got {value!r}")
    return value


@dataclass(frozen=True)
class Action:
    """One proposed change to a single manifest artifact -- P-05's own
    field list, verbatim: `artifact_id`, `artifact_class`, `current_state`,
    `target_state`, `target_path`, plus `rationale` (the human-reviewer
    framing P-05 names) and `chosen_anchor` (this story's own addition, see
    below).

    `target_state` is always `ArtifactState.PRESENT_CONFORMANT` for every
    `Action` this story's `build_plan` ever constructs -- typed as the
    FULL `ArtifactState` enum rather than narrowed to that one member, so a
    future story adding a different target state (e.g. a migration's own
    plan-producing function, AD-62) is not a breaking change to this
    dataclass's shape.

    `chosen_anchor` is `tuple[tuple[str, str | None], ...]`, one
    `(region_name, matched_anchor)` pair per declared region on a
    `hybrid-managed-region` entry that needs inserting this run -- PAIRS,
    not a bare positional tuple of anchors, so a human reading the plan
    JSON does not have to cross-reference the manifest to know which region
    an anchor belongs to (a `hybrid-managed-region` entry may declare more
    than one region -- the packaged manifest's `agents-md` entry declares
    3, `claude-md` declares 2 -- so a single scalar anchor field could not
    represent "two regions were both missing, resolved against two
    different anchors" without silently dropping one). `matched_anchor` is
    `regions.parse.AnchorResolution.matched` -- the literal anchor string
    that resolved, or `None` for the EOF-append fallback. Empty tuple `()`
    for every non-hybrid class, and for a hybrid entry needing no
    insertion at all (`seed.plan.build` degrades to `()` whenever the
    target cannot be safely re-parsed, rather than guessing)."""

    artifact_id: str
    artifact_class: ArtifactClass
    current_state: ArtifactState
    target_state: ArtifactState
    target_path: str
    chosen_anchor: tuple[tuple[str, str | None], ...]
    rationale: str

    def to_json_dict(self) -> dict[str, Any]:
        """Fixed key order, matching `Finding.to_json_dict`'s own
        convention -- enum fields serialize as their wire `.value`, and
        `chosen_anchor`'s tuple-of-tuples becomes a JSON array of
        2-element arrays (JSON has no tuple type)."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_class": self.artifact_class.value,
            "current_state": self.current_state.value,
            "target_state": self.target_state.value,
            "target_path": self.target_path,
            "chosen_anchor": [[name, anchor] for name, anchor in self.chosen_anchor],
            "rationale": self.rationale,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Action:
        """The inverse of `to_json_dict`. Raises `ValueError` naming the
        problem for a missing key, a wrong-shaped value, or an
        `artifact_class`/`current_state`/`target_state` value outside its
        enum's registered members (the bare `ValueError` the `StrEnum`
        constructor itself raises, unmodified -- matching
        `Finding.__post_init__`'s identical "nothing to add to that
        message" stance for the same kind of failure)."""
        if not isinstance(data, dict):
            raise ValueError(f"Action: expected a JSON object, got {data!r}")
        raw_pairs = _require_pair_list(
            _require_key(data, "chosen_anchor", context="Action"),
            context="Action.chosen_anchor",
        )
        chosen_anchor = tuple(
            (
                _require_str(name, context="Action.chosen_anchor[].region_name"),
                _require_optional_str(anchor, context="Action.chosen_anchor[].matched_anchor"),
            )
            for name, anchor in raw_pairs
        )
        return cls(
            artifact_id=_require_str(_require_key(data, "artifact_id", context="Action"), context="Action.artifact_id"),
            artifact_class=ArtifactClass(_require_key(data, "artifact_class", context="Action")),
            current_state=ArtifactState(_require_key(data, "current_state", context="Action")),
            target_state=ArtifactState(_require_key(data, "target_state", context="Action")),
            target_path=_require_str(_require_key(data, "target_path", context="Action"), context="Action.target_path"),
            chosen_anchor=chosen_anchor,
            rationale=_require_str(_require_key(data, "rationale", context="Action"), context="Action.rationale"),
        )


@dataclass(frozen=True)
class RepoFingerprint:
    """A tamper-evident snapshot of the repo state a `Plan` was computed
    against (AD-57): the git HEAD commit, whether the worktree is dirty,
    and a content hash per actioned artifact -- what a future `apply` story
    (Epic 10, out of this story's scope) checks before trusting a `Plan` is
    still safe to apply.

    `git_head` is `None` when the target is not a git repo, or has no
    commits yet -- `seed.plan.build` never raises for either case (P-03/the
    epics' own "no error" row for a non-git target). `dirty` defaults to
    `True` -- the conservative direction -- whenever cleanliness cannot be
    confirmed, for the identical reason.

    `artifact_hashes` covers only the artifacts THIS plan's `actions` name,
    never the whole manifest: AD-57 frames the fingerprint's purpose as
    catching drift between plan-build time and apply time for exactly the
    artifacts a `Plan` intends to touch -- hashing all 40+ manifest entries
    regardless of whether they have a pending action would not serve that
    purpose, and would make an empty plan's fingerprint needlessly
    expensive to compute. Sorted by artifact id, matching `Plan.actions`'s
    own determinism requirement -- two `build_plan()` calls against
    identical repo state must produce byte-identical `plan.json`."""

    git_head: str | None
    dirty: bool
    artifact_hashes: tuple[tuple[str, str], ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "git_head": self.git_head,
            "dirty": self.dirty,
            "artifact_hashes": [[artifact_id, sha] for artifact_id, sha in self.artifact_hashes],
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> RepoFingerprint:
        if not isinstance(data, dict):
            raise ValueError(f"RepoFingerprint: expected a JSON object, got {data!r}")
        raw_pairs = _require_pair_list(
            _require_key(data, "artifact_hashes", context="RepoFingerprint"),
            context="RepoFingerprint.artifact_hashes",
        )
        artifact_hashes = tuple(
            (
                _require_str(artifact_id, context="RepoFingerprint.artifact_hashes[].artifact_id"),
                _require_str(sha, context="RepoFingerprint.artifact_hashes[].sha"),
            )
            for artifact_id, sha in raw_pairs
        )
        return cls(
            git_head=_require_optional_str(
                _require_key(data, "git_head", context="RepoFingerprint"),
                context="RepoFingerprint.git_head",
            ),
            dirty=_require_bool(
                _require_key(data, "dirty", context="RepoFingerprint"),
                context="RepoFingerprint.dirty",
            ),
            artifact_hashes=artifact_hashes,
        )


@dataclass(frozen=True)
class SkippedArtifact:
    """One artifact a caller's `--skip` glob removed from this run
    (Story 10.4, FR-87), recorded IN the plan rather than only in a
    rendering of it.

    A `Plan` is a serialized artifact (`build.write_plan`/`build.load_plan`)
    that a human reviews as a diff, so "a skip is visible rather than
    invisible" only holds if the skip survives into `plan.json` itself --
    a skip that exists solely in a terminal rendering would leave the
    reviewed file lying by omission about the one thing the requirement
    exists to surface.

    `pattern` is the glob that matched -- the FIRST one in the caller's
    given order when several match (`seed.verbs.skips.first_match`'s own
    rule), so the reviewer can see WHICH `--skip` argument is responsible
    rather than having to re-derive it from the pattern list.

    Deliberately a separate carrier from `Action`, and a separate `Plan`
    field rather than a flag on a member of `Plan.actions`: an apply runner
    iterates `plan.actions`, so an artifact it must not touch is
    structurally unreachable here instead of merely protected by every
    future consumer remembering to test a flag."""

    artifact_id: str
    target_path: str
    pattern: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "target_path": self.target_path,
            "pattern": self.pattern,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> SkippedArtifact:
        if not isinstance(data, dict):
            raise ValueError(f"SkippedArtifact: expected a JSON object, got {data!r}")
        return cls(
            artifact_id=_require_non_blank_str(
                _require_key(data, "artifact_id", context="SkippedArtifact"),
                context="SkippedArtifact.artifact_id",
            ),
            target_path=_require_non_blank_str(
                _require_key(data, "target_path", context="SkippedArtifact"),
                context="SkippedArtifact.target_path",
            ),
            pattern=_require_non_blank_str(
                _require_key(data, "pattern", context="SkippedArtifact"),
                context="SkippedArtifact.pattern",
            ),
        )


@dataclass(frozen=True)
class Plan:
    """The single artifact a human reviews before Genesis writes anything
    (P-04): an ordered, deterministic list of `Action`s plus the
    `RepoFingerprint` they were computed against, plus whatever this run's
    `--skip` globs took OUT of that list.

    `actions` is sorted by `artifact_id` (`seed.plan.build.build_plan`'s
    own determinism requirement, mirrored here rather than re-validated --
    this class carries no `__post_init__` of its own, see the module
    docstring). `Plan(actions=(), repo_fingerprint=...)` is a fully valid,
    constructible, serializable result (AD-60: idempotence is defined as
    plan-emptiness) -- nothing in this class, or in `to_json_dict`/
    `from_json_dict`, special-cases an empty `actions` tuple.

    `skipped` (Story 10.4) is `()` for every `Plan` `build_plan` itself
    produces -- it is populated only by `seed.verbs.skips.apply_skips`,
    which MOVES an entry out of `actions` into it. Last field, with a
    default, so every existing `Plan(actions=..., repo_fingerprint=...)`
    construction site keeps working unchanged. It is sorted by
    `artifact_id`, unique, and shares no id with `actions` -- an artifact
    is either being acted on or being skipped, never both -- all three
    re-checked in `from_json_dict` against a hand-corrupted file, the same
    boundary discipline `actions` already gets."""

    actions: tuple[Action, ...]
    repo_fingerprint: RepoFingerprint
    skipped: tuple[SkippedArtifact, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "actions": [action.to_json_dict() for action in self.actions],
            "repo_fingerprint": self.repo_fingerprint.to_json_dict(),
            "skipped": [entry.to_json_dict() for entry in self.skipped],
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Plan:
        if not isinstance(data, dict):
            raise ValueError(f"Plan: expected a JSON object, got {data!r}")
        raw_actions = _require_key(data, "actions", context="Plan")
        if not isinstance(raw_actions, list):
            raise ValueError(f"Plan.actions: expected a list, got {raw_actions!r}")
        actions = tuple(Action.from_json_dict(raw_action) for raw_action in raw_actions)
        # `build_plan` guarantees `actions` is sorted by unique `artifact_id`
        # (the epics AC's own determinism requirement) -- `from_json_dict`
        # is this module's boundary against UNTRUSTED data (see the module
        # docstring), so a hand-corrupted `plan.json` with a duplicate or
        # out-of-order id must fail loudly here rather than silently loading
        # a `Plan` that no longer holds its own stated invariant (review
        # finding).
        ids = [action.artifact_id for action in actions]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Plan.actions: artifact_id values must be unique, got {ids!r}")
        if ids != sorted(ids):
            raise ValueError(f"Plan.actions: entries must be ordered by artifact_id, got {ids!r}")
        # Each key is required AND ITS VALUE VALIDATED in `to_json_dict`'s
        # own emission order -- `actions`, `repo_fingerprint`, then
        # `skipped` -- so a document broken in several places reports the
        # FIRST problem a reader would look for rather than whichever this
        # method happens to reach first. The fingerprint is parsed HERE, not
        # deferred into the `cls(...)` call below (review finding): deferred,
        # a document with both a malformed `repo_fingerprint` and an
        # out-of-order `skipped` reported only the `skipped` error and never
        # mentioned the broken fingerprint at all, which made the ordering
        # claim above false for exactly the documents it matters for.
        raw_fingerprint = _require_key(data, "repo_fingerprint", context="Plan")
        fingerprint = RepoFingerprint.from_json_dict(raw_fingerprint)
        # `skipped` is REQUIRED, not defaulted-on-absence: the dataclass
        # default exists so Python construction sites stay short, but a
        # `plan.json` missing the key is a file this module's own
        # `to_json_dict` did not write, and silently reading it as "nothing
        # was skipped" would turn a truncated or foreign document into a
        # plan that looks complete. Every other `Plan` key is required for
        # the same reason.
        raw_skipped = _require_key(data, "skipped", context="Plan")
        if not isinstance(raw_skipped, list):
            raise ValueError(f"Plan.skipped: expected a list, got {raw_skipped!r}")
        skipped = tuple(SkippedArtifact.from_json_dict(entry) for entry in raw_skipped)
        skipped_ids = [entry.artifact_id for entry in skipped]
        if len(set(skipped_ids)) != len(skipped_ids):
            raise ValueError(f"Plan.skipped: artifact_id values must be unique, got {skipped_ids!r}")
        if skipped_ids != sorted(skipped_ids):
            raise ValueError(f"Plan.skipped: entries must be ordered by artifact_id, got {skipped_ids!r}")
        # Disjointness: `apply_skips` MOVES an action into `skipped`, so an
        # id appearing on both sides means the file was hand-edited into a
        # state no producer can reach -- and one whose meaning is genuinely
        # ambiguous ("write it" and "leave it alone" at once), so it must
        # not load at all rather than resolve silently in either direction.
        shared = sorted(set(ids) & set(skipped_ids))
        if shared:
            raise ValueError(f"Plan: an artifact_id may appear in actions or skipped, never both, got {shared!r}")
        return cls(actions=actions, repo_fingerprint=fingerprint, skipped=skipped)
