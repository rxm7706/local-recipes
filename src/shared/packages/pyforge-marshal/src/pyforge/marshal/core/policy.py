"""Layered policy composition with provenance and validation (Story 1.3,
architecture spine AD-10/AD-16/AD-26/AD-35).

``compose()`` is the pure fold ``defaults -> repo_defaults -> project -> flags,
last wins`` (AD-16) over Marshal's own CLOSED 22-key policy vocabulary
(FR-49/50/51/53/54, plus FR-12's ``idle_threshold_minutes`` (Story 3.5),
FR-13's 4 budget ceilings (Story 3.6), AD-27's ``epic_surfaces`` (Story 2.3),
and AD-40's 4 landing keys (Story 4.7)) -- not a mirror of the harness's much
larger ``.bmad-loop/policy.toml`` key surface (that mapping is Story 1.10's
rendering concern). Every field is wrapped in a ``PolicyField{value, layer,
raw_source}`` so an operator can always answer "why is this value what it
is?" (AD-16).

**The 4-layer precedence (as of Story 1.10):** ``DEFAULT_POLICY`` (code) ->
``repo_defaults`` (tracked at `_bmad-output/policy-defaults.toml`, for repo-wide
decisions like ``max_followup_reviews``) -> ``project`` (tracked per-station,
like `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`)
-> ``flags`` (invocation ``--set``). A layer is only consulted if it provides a
value for a key; if its value is malformed, that layer is skipped for that key
and the previous (better) layer's value stands.

**Static vs seed (AD-26).** 12 fields are STATIC -- public ``EffectivePolicy``
attributes, each a ``PolicyField``: ``verify_commands``,
``worktree_seed_paths``, ``merge_subject_template``, ``model_tier_map``,
(Story 2.3) ``epic_surfaces`` -- AD-27's per-epic writable-surface
allowlist, STATIC because it is project/policy-declared and never narrowed
at runtime by a journal entry, unlike ``frozen_surfaces`` below -- and
(Story 4.7) the 4 landing keys ``landing_rules``, ``landing_merge_strategy``,
``landing_branch_retirement``, ``landing_resync`` (AD-40), plus (Story 4.4)
a 5th, ``landing_base_branch`` -- ``marshal deploy batch-pr``'s own target
base branch, checked against Story 4.7's four before adding a new one, plus
(Story 4.5) a 6th, ``landing_resync_commands`` -- the ``landing_resync``
toggle's own allowlist of commands ``marshal deploy refresh-feed`` runs,
validated identically to ``verify_commands`` --
STATIC for the same reason: declared and validated here, consumed and acted
on by later stories (4.5, 4.8, 4.10), never narrowed by a journal entry, plus
(Story 6.9) ``mcp_servers`` -- AD-43's project-declared MCP tool surface,
STATIC for the identical reason ``epic_surfaces``/``model_tier_map`` are:
declared and validated here, rendered by ``cli/init.py::run_init`` into a
loop home's ``.mcp.json`` and probed for resolvability by ``run_preflight``,
never narrowed by a journal entry. 10
fields are SEED -- epics.md's own named examples ("frozen surfaces, gate
mode, attempt counts"): ``gate_mode``, ``frozen_surfaces``,
``max_dev_attempts``, ``max_review_cycles``, ``max_followup_reviews``,
(Story 3.5) ``idle_threshold_minutes``, and (Story 3.6) the 4 budget
ceilings ``max_tokens_per_story``, ``max_tokens_per_run``,
``max_wall_clock_minutes_per_story``, ``max_wall_clock_minutes_per_run`` --
each the closest existing analog to that same "operator-tunable numeric
ceiling" shape. Seed fields live ONLY in a private ``_seed`` mapping;
``seed_view()`` is the sole whitelisted
accessor (closing F-8: it is what lets ``marshal config``/FR-54 and FR-53
validation range over every key without contradicting "reading a seed
field outside the journal fold fails a meta-test"). A composed
``EffectivePolicy`` only ever holds the INITIAL seed values -- the LIVE value
during a run comes solely from ``core/journal``'s fold (AD-26); this module
has no notion of a run at all.

**compose() never raises on malformed input** -- the same "reported, not
raised" convention as ``core/identity.py``'s ``resolve_feed()``: an unknown
top-level key in the project/flags layer is excluded from composition
(``MRS-POLICY-001``); a known field given a malformed/out-of-range value by
one layer is excluded FOR THAT LAYER ONLY -- composition falls through to
whatever the previous (better) layer already established for that field,
floored at Marshal's own built-in default if no layer ever supplied a valid
value (``MRS-POLICY-002`` for a malformed STATIC field, ``MRS-POLICY-003``
for a malformed SEED field). The ``project_slug`` itself is shape-validated
too (FR-53's shape-only spirit -- it becomes a literal path segment of the
generated ``worktree_seed_paths``): a MISSING slug (empty string) reports
``MRS-POLICY-005`` (severity ``warn`` -- a bare ``marshal config`` with no
active project is a legitimate show-me-the-defaults invocation, so it still
exits 0); a MALFORMED slug (path separators, ``.``/``..``, characters
outside the slug charset) reports ``MRS-POLICY-006`` (severity ``error`` --
the operator explicitly supplied garbage, matching the malformed ``--set``
precedent). Either way the project-derived seed path is OMITTED rather than
generated around a bad slug -- never a ``projects//`` or traversal-shaped
path. **Stated assumption** (the spec's prose reads
"falls back to Marshal's default value for that field", which is ambiguous
about a THIRD scenario neither the spec's own I/O matrix nor its Acceptance
Criteria exercises: project sets a field validly, flags then sets the SAME
field invalidly): this module treats an invalid layer as excluded, not as a
poison pill for the whole field -- a single malformed ``--set`` typo does
not silently discard an otherwise-valid project-layer decision. Both
enumerated I/O-matrix scenarios (a lone malformed project value, a lone
malformed flag value) produce the SAME observable result either way, since
neither has a valid prior layer to preserve.

**MRS-POLICY-002 vs MRS-POLICY-003, the exact split.** The spec's own two
enumerated examples are: -002 for ``verify_commands``/``model_tier_map``
(both STATIC), -003 for ``gate_mode``/attempt-counts (all SEED). This module
extends that pairing to the two STATIC/SEED fields the spec's examples don't
individually name (``merge_subject_template``, ``frozen_surfaces``) by the
same static/seed tag rather than inventing a fourth code: **every STATIC
field's shape violation is MRS-POLICY-002; every SEED field's shape/range
violation is MRS-POLICY-003.**

**Never** (see the spec's Boundaries & Constraints for the full list): no
``core/identity.py`` import -- ``merge_subject_template`` is validated as a
non-empty ``str`` only, never for placeholder shape. No ``shutil.which``/PATH
check for ``verify_commands`` (FR-53 assigns that to preflight, Story 1.7).
No modeling of the harness's full ``.bmad-loop/policy.toml`` key surface. No
``policy_surface ∩ spec_surface`` allowlist (Story 2.3's concern). No
resolution of a story's difficulty class against ``model_tier_map``. No
support for ``--set`` on the five list/mapping-typed fields
(``verify_commands``, ``worktree_seed_paths``, ``model_tier_map``,
``frozen_surfaces``, ``epic_surfaces``) -- that is a ``cli/config.py`` UX
restriction on which flags it exposes, not a restriction this module
enforces (``compose()`` itself layers all 15 keys uniformly across all 3
layers, matching AD-16's "no per-key reordering").

**Marshal's own built-in defaults** (``DEFAULT_POLICY``) are a DIFFERENT
thing from any one project's ``.bmad-loop/policy.toml`` -- that file
encodes one operator's tuned choices for one project; this module's defaults
are the product's own out-of-the-box posture, chosen conservative-safe
where the spec leaves the literal unstated: ``gate_mode`` defaults to the
strictest oversight tier (``per-story-spec-approval``) rather than the
unattended one. ``worktree_seed_paths`` carries no ``DEFAULT_POLICY`` entry
-- FR-50 makes it GENERATED from ``project_slug``, never a literal default.

This module is pure data: no I/O, no subprocess, no clock, no
``pyforge.marshal.adapters`` (AD-4) -- only ``copy``, ``hashlib``, ``json``,
``dataclasses``, ``enum``, ``types``, ``collections.abc``, ``.landing``, and
``.model``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .landing import LandingRule, landing_rule_to_dict
from .model import Finding, Severity

# --- the closed 22-key vocabulary -------------------------------------------

_STATIC_KEYS: frozenset[str] = frozenset(
    {
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        # Story 2.3's 15th key (AD-27): a per-epic writable-surface
        # allowlist. STATIC, not SEED -- it is project/policy-declared and
        # never narrowed at runtime by a journal entry, unlike
        # `frozen_surfaces` (which DOES accumulate live, via the journal
        # fold). See `_valid_epic_surfaces`'s own docstring for the shape.
        "epic_surfaces",
        # Story 4.7's 4 landing keys (AD-40): declared and validated here,
        # consumed by later stories (4.8's `marshal land`, 4.10's fleet-wide
        # branch retirement). STATIC, not SEED -- like `epic_surfaces`, none
        # of the four is ever narrowed at runtime by a journal entry.
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
        # Story 4.4's 5th landing key (AD-40): `marshal deploy batch-pr`'s
        # target base branch, checked against Story 4.7's own four before
        # adding a new one (none of the four covers "which branch a batch PR
        # targets") -- STATIC for the same reason its four siblings are:
        # declared and validated here, never narrowed by a journal entry.
        "landing_base_branch",
        # Story 4.5's 6th landing key (AD-40): the `landing_resync`
        # toggle's own allowlist of commands to run when it composes
        # `True` (`marshal deploy refresh-feed`) -- validated identically
        # to `verify_commands` (a tuple of non-empty str), same reason
        # every other landing key is STATIC: declared and validated here,
        # never narrowed by a journal entry.
        "landing_resync_commands",
        # Story 6.9's 16th key (AD-43, the Q-11 resolution): the project's
        # declared MCP tool surface, Mapping[str, {command, args?, env?}]
        # keyed by server name. STATIC, not SEED -- like `epic_surfaces`/
        # `model_tier_map`, it is project/policy-declared and never
        # narrowed at runtime by a journal entry; `cli/init.py::run_init`
        # renders it into the loop home's `.mcp.json` (seed-not-overwrite,
        # Story 1.7's pattern) and `run_preflight` probes each declared
        # server's command for resolvability.
        "mcp_servers",
    }
)
_SEED_KEYS: frozenset[str] = frozenset(
    {
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
        # Story 3.5's 10th key, joining the vocabulary alongside its closest
        # existing analogs (max_dev_attempts/max_review_cycles/
        # max_followup_reviews) -- see this module's own docstring for why.
        "idle_threshold_minutes",
        # Story 3.6's 4 budget-ceiling keys (FR-13, AD-32) -- per-story/
        # per-run x tokens/wall-clock, reusing idle_threshold_minutes's own
        # validator (`_valid_positive_number`), the closest existing analog:
        # both are operator-tunable numeric ceilings with no coherent
        # "zero or unbounded" reading.
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
    }
)
_ALL_KEYS: frozenset[str] = _STATIC_KEYS | _SEED_KEYS

_STAGE_NAMES: frozenset[str] = frozenset({"dev", "review", "triage"})
_GATE_MODES: frozenset[str] = frozenset({"none", "per-epic", "per-story-spec-approval"})
# Story 4.7's closed vocabulary for `landing_merge_strategy` -- "merge" is
# the default because it matches this repo's own observed real practice
# (`git log --merges` shows real, non-squash merge commits throughout).
_MERGE_STRATEGIES: frozenset[str] = frozenset({"merge", "squash", "rebase"})
# `LandingRule.trigger_mode`'s closed vocabulary (**corrected in review,
# 2026-08-06**): no default -- every rule states its own match direction
# explicitly. Same closed-vocabulary shape as `_MERGE_STRATEGIES`.
_TRIGGER_MODES: frozenset[str] = frozenset({"exclude", "include"})

# FR-24's gate-mode ladder: each of _GATE_MODES's 3 values IS an autonomy
# declaration, keyed by exactly those 3 values -- DATA, never an
# interpolated prose string, so a caller renders or compares it without
# re-deriving the mapping. Verbatim from the PRD/glossary's own table:
# `per-story-spec-approval` -> L2 "Task-Based / Operator" (human approves
# each unit's contract before work proceeds); `per-epic` -> L3 "Conditional
# / Context Gates" (machine-readable boundaries, human at epic seams -- the
# production ceiling); `none` -> L4 "Approver" (runs independently,
# surfaces only at blockers or pre-specified conditions). L5 "Observer" is
# the table's fourth row, but it names an unbuilt gate mode with no
# `_GATE_MODES` counterpart, so it has no entry here.
# `core/gate.py::describe_gate_mode` is the sole consumer that shapes one
# entry into an envelope-ready report; see that module for why an
# out-of-vocabulary key raises rather than returning a Finding.
GATE_MODE_AUTONOMY_LABELS: Mapping[str, Mapping[str, str]] = {
    "per-story-spec-approval": {
        "level": "L2",
        "name": "Task-Based / Operator",
        "meaning": "Human approves each unit's contract before work proceeds.",
    },
    "per-epic": {
        "level": "L3",
        "name": "Conditional / Context Gates",
        "meaning": (
            "Machine-readable boundaries; human at epic seams. The "
            "production ceiling."
        ),
    },
    "none": {
        "level": "L4",
        "name": "Approver",
        "meaning": (
            "Runs independently; surfaces only at blockers or "
            "pre-specified conditions."
        ),
    },
}

# The conservative charset a project slug may draw from -- it is interpolated
# as ONE literal path segment of the generated worktree_seed_paths entry
# (`_bmad-output/projects/<slug>/implementation-artifacts`), so anything that
# could split or escape that segment is out.
_SLUG_CHARS: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)

# Marshal's OWN built-in defaults for the 8 literal-valued keys -- see the
# module docstring for why this is independent of any one project's rendered
# policy file, and why `worktree_seed_paths` has no entry here.
DEFAULT_POLICY: Mapping[str, object] = {
    "verify_commands": (),
    "merge_subject_template": "Merge {key} into main",
    "model_tier_map": {},
    "gate_mode": "per-story-spec-approval",
    "frozen_surfaces": (),
    "max_dev_attempts": 2,
    "max_review_cycles": 3,
    # 2, not 1, because this is a REPO-WIDE decision and this is the only
    # repo-wide home for one. A cap of 1 damped five still-recommended
    # follow-up reviews across three projects (atlas 10.5/10.6, marshal 1.1,
    # warden 6.3/5.1) into a GITIGNORED ledger -- the incident behind
    # DW-AD23-3 and behind `deferred-work-check` existing at all. Story
    # 1.10's own review named the placement rule: the value "has nothing to
    # do with marshal", so supplying it from a project layer under-scopes the
    # fix and hand-copies one decision into every station. Seeded here, no
    # project layer needs to restate it and a new station inherits it.
    "max_followup_reviews": 2,
    # Story 3.5's FR-12: the supervisor's idle-ladder threshold, materially
    # below the session budget (NFR requires it configurable with this
    # default). 25 minutes -- long enough that a session mid-thought on a
    # slow tool call is never mistaken for wedged, short enough to catch a
    # genuinely stuck run in minutes rather than burning the multi-million-
    # token session cap it exists to protect.
    "idle_threshold_minutes": 25,
    # Story 3.6's FR-13: the 4 externally-enforced budget ceilings (AD-32).
    #
    # RE-CALIBRATED against measured data (review finding). The first pass
    # picked these by analogy (2x bmad-loop's own in-session per-story guard,
    # ~1.5x a cited 25.8M blowout, 4h/10h) WITHOUT measuring what this
    # factory's stories actually cost -- and every one of the four landed
    # BELOW ordinary observed behaviour, which would have hard-stopped
    # essentially every run in its first story. Measured across 30 real
    # bmad-loop runs / 53 completed stories on this factory:
    #
    #   per-story weighted tokens: max 21.7M; 46 of 53 stories exceeded the
    #     old 4M default (the story that INTRODUCED these ceilings cost 12.9M)
    #   per-run   weighted tokens: max 111.6M (an 8-story wave) vs the old 40M
    #   per-story wall clock:      max 518 min; 5 of 40 exceeded the old 240
    #   per-run   wall clock:      max 1040 min; 2 of 30 exceeded the old 600
    #
    # A ceiling is a RUNAWAY BACKSTOP, not a routine trip: each default below
    # sits at roughly 2.5-4.5x the observed maximum, so it fires only on
    # behaviour with no precedent in this corpus while still bounding the run
    # (C-6: "every run has a ceiling; there is no unbounded mode"). The
    # per-run token ceiling carries the widest margin because a run's total
    # scales with its story count -- 500M is ~36 stories at the observed
    # ~14M average, comfortably above any wave shape seen so far. All four
    # stay operator-tunable via the same policy layers idle_threshold_minutes
    # already uses; a project running materially heavier or lighter stories
    # should set its own.
    "max_tokens_per_story": 50_000_000,
    "max_tokens_per_run": 500_000_000,
    "max_wall_clock_minutes_per_story": 1_440,
    "max_wall_clock_minutes_per_run": 2_880,
    # Story 2.3's `epic_surfaces` (AD-27): no epic has a declared allowlist
    # until a project's own policy says otherwise -- an empty mapping, the
    # same "nothing declared yet" posture `model_tier_map`'s own empty-dict
    # default already carries for the identical STATIC/mapping shape.
    "epic_surfaces": {},
    # Story 4.7's 4 landing keys (AD-40). No rule fires until a project
    # declares one -- the same "nothing declared yet" posture `epic_surfaces`
    # already carries for the identical STATIC/empty-collection shape.
    "landing_rules": (),
    # "merge", not "squash"/"rebase": matches this repo's own observed real
    # practice (see `_MERGE_STRATEGIES`'s own comment).
    "landing_merge_strategy": "merge",
    # True: retirement/resync are the safe, expected default -- an operator
    # who wants a story's branch left behind or its surfaces left unsynced
    # opts OUT explicitly via their own project policy layer.
    "landing_branch_retirement": True,
    "landing_resync": True,
    # Story 4.4's `landing_base_branch` (AD-40): the target base branch for
    # `marshal deploy batch-pr` -- "main", matching this repo's own real
    # practice (never the forge's own "default branch" concept, which for a
    # fork defaults to the UPSTREAM's default, not this repo's own main).
    "landing_base_branch": "main",
    # Story 4.5's `landing_resync_commands` (AD-40): no command runs until a
    # project declares one -- the same "nothing declared yet" posture
    # `verify_commands` already carries for the identical STATIC/tuple-of-
    # str shape.
    "landing_resync_commands": (),
    # Story 6.9's `mcp_servers` (AD-43): no MCP server renders into a loop
    # home's `.mcp.json` until a project declares one -- the same "nothing
    # declared yet" posture `epic_surfaces`/`model_tier_map` already carry
    # for the identical STATIC/empty-mapping shape.
    "mcp_servers": {},
}

# Secret redaction (Boundaries & Constraints): a case-insensitive suffix
# match against a field NAME renders a fixed sentinel instead of the value.
# None of the 14 real fields match today -- proven via a synthetic fixture in
# tests/unit/test_policy.py, mirroring findings.py/verdict.py's own
# "empty/unused registry, mechanism proven synthetically" precedent.
SECRET_KEY_SUFFIXES: frozenset[str] = frozenset({"_TOKEN", "_KEY", "_SECRET", "_PASSWORD"})
REDACTED_SENTINEL = "***REDACTED***"


class PolicyLayer(StrEnum):
    """The 3-member precedence chain (AD-16): Marshal defaults -> project
    policy -> invocation flags, last wins, no fourth layer."""

    DEFAULT = "default"
    PROJECT = "project"
    FLAG = "flag"


def _freeze_raw(value: object) -> object:
    """An immutable, UNALIASED snapshot of a field's ``value`` and
    ``raw_source``: any ``Mapping`` becomes a ``MappingProxyType`` over a
    fresh dict, any ``list``/``tuple`` becomes a tuple, scalars pass through.
    ``content_hash`` covers both halves, so storing the caller's own
    list/dict object (or exposing a mutable one through either attribute)
    would let a mutation AFTER construction silently change the hash --
    breaking AD-35's content-addressing and the documented "immutable
    ``EffectivePolicy``" guarantee (AD-10). Applied uniformly by
    ``PolicyField.__post_init__``, so EVERY construction path is covered --
    ``compose()``'s merges and a directly constructed ``PolicyField`` alike.
    The wire shape is unchanged: ``_to_plain`` projects proxies/tuples back
    to dicts/lists."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_raw(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_raw(item) for item in value)
    # A `LandingRule` is already immutable (a frozen dataclass over plain
    # str/bool/None fields) -- nothing further to snapshot, unlike a
    # Mapping/list/tuple a caller could still hold a mutable alias to.
    return value


@dataclass(frozen=True)
class PolicyField:
    """One policy value plus its provenance (AD-16): the effective
    ``value``, the ``layer`` that won it, and ``raw_source`` -- the
    unwrapped original value from that winning layer (for provenance
    display; equals ``value`` when the winning layer is ``default``).
    BOTH ``value`` and ``raw_source`` are snapshotted via ``_freeze_raw``
    at construction, so no ``PolicyField`` ever aliases a caller-mutable
    container regardless of how it was constructed. The generated ``repr``
    shows raw values: a bare ``PolicyField`` does not know its own field
    NAME, which is what secret-shape redaction keys on -- name-aware
    egresses (``EffectivePolicy.__repr__``, ``cli/config.py``'s renders,
    ``_malformed_finding``) each apply ``redact()`` themselves."""

    value: object
    layer: PolicyLayer
    raw_source: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "layer", PolicyLayer(self.layer))
        object.__setattr__(self, "value", _freeze_raw(self.value))
        object.__setattr__(self, "raw_source", _freeze_raw(self.raw_source))


def is_secret_key(field_name: str) -> bool:
    """``True`` if ``field_name`` ends, case-insensitively, with one of
    ``SECRET_KEY_SUFFIXES``."""
    upper = field_name.upper()
    return any(upper.endswith(suffix) for suffix in SECRET_KEY_SUFFIXES)


def redact(field_name: str, value: object) -> object:
    """Return ``REDACTED_SENTINEL`` if ``field_name`` is secret-shaped
    (``is_secret_key``), else ``value`` unchanged."""
    return REDACTED_SENTINEL if is_secret_key(field_name) else value


# --- per-field shape/range validators (FR-53) -------------------------------
# Each returns the coerced value on success or None on failure -- never
# raises. None means the SUPPLYING layer is excluded for that field; compose()
# falls through to whatever the previous (better) layer already established.

_Validator = Callable[[object], object]


def _valid_str_tuple(value: object) -> tuple[str, ...] | None:
    """A list/tuple of NON-EMPTY strings. The empty string is rejected for
    the same reason ``_valid_merge_subject_template`` rejects it for the
    scalar field: an empty verify command or an empty frozen surface is not
    a degenerate instance of the concept, it is no instance at all."""
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return None
    if not all(isinstance(item, str) and item != "" for item in value):
        return None
    return tuple(value)


def _valid_seed_path_extras(value: object) -> tuple[str, ...] | None:
    """``worktree_seed_paths`` extras: each entry must be a clean RELATIVE
    path (shape-only, FR-53) -- the same threat model as the slug guard,
    because every extra becomes a literal seed path inside a worktree. Two
    checks per entry, and BOTH are needed: every character must come from
    the slug charset plus ``/`` (rejecting backslash separators, drive
    colons, ``~`` expansion targets, NUL bytes, whitespace -- anything the
    slug guard would reject in a single segment), and, splitting on ``/``,
    no segment may be empty (absolute paths, ``//``, trailing ``/``),
    ``.``, or ``..`` (segment aliasing/escape). Together they guarantee a
    traversal-shaped, absolute, or non-portable path can no more enter
    through the extras than through the generated base."""
    base = _valid_str_tuple(value)
    if base is None:
        return None
    allowed = _SLUG_CHARS | {"/"}
    for entry in base:
        if not set(entry) <= allowed:
            return None
        if any(part in ("", ".", "..") for part in entry.split("/")):
            return None
    return base


def _valid_model_tier_map(value: object) -> dict[str, dict[str, str]] | None:
    """Difficulty and model names must be NON-EMPTY strings for the same
    reason ``_valid_str_tuple`` rejects the empty string: an empty
    difficulty class or an empty model name is not a degenerate instance of
    the concept, it is no instance at all -- an Epic 3/4 consumer resolving
    a stage against it would inherit the garbage silently."""
    if not isinstance(value, Mapping):
        return None
    result: dict[str, dict[str, str]] = {}
    for difficulty, stages in value.items():
        if not isinstance(difficulty, str) or difficulty == "" or not isinstance(stages, Mapping):
            return None
        stage_map: dict[str, str] = {}
        for stage, model in stages.items():
            if stage not in _STAGE_NAMES or not isinstance(model, str) or model == "":
                return None
            stage_map[stage] = model
        result[difficulty] = stage_map
    return result


def _valid_epic_surfaces(value: object) -> dict[str, tuple[str, ...]] | None:
    """``epic_surfaces``: ``Mapping[str, tuple[str, ...]]`` keyed by epic
    number AS A STRING (``"2"``, ``"3"`` -- matching AD-23's own
    ``<epic>.<seq>`` story-key numeric-epic identity), each value a
    non-empty tuple of non-empty glob strings (reuses ``_valid_str_tuple``'s
    own per-entry shape rather than inventing a second one). Mirrors
    ``_valid_model_tier_map``'s shape-checking pattern exactly: reject a
    non-mapping, reject a non-string key, reject a value that is not a
    valid string tuple -- the whole field is excluded for THAT layer on any
    single malformed entry (the same "one bad entry poisons the layer, not
    the whole field" semantics every other mapping-typed validator in this
    module already applies).

    A key must also be a plain digit string (``key.isdigit()``, review
    finding: Blind Hunter) -- matching how ``str(story_key.epic)`` is
    always rendered elsewhere in this codebase (``AD-23``'s numeric-epic
    identity). Without this check a typo'd key like ``"epic-2"`` or ``"2 "``
    composed successfully with no diagnostic and could never match any real
    epic -- a permanently dead, silently-inert allowlist entry with no
    signal to the operator that it will never take effect."""
    if not isinstance(value, Mapping):
        return None
    result: dict[str, tuple[str, ...]] = {}
    for epic, surface in value.items():
        if not isinstance(epic, str) or epic == "" or not epic.isdigit():
            return None
        globs = _valid_str_tuple(surface)
        if globs is None:
            return None
        result[epic] = globs
    return result


def _valid_mcp_servers(value: object) -> dict[str, dict[str, object]] | None:
    """``mcp_servers`` (Story 6.9, AD-43): ``Mapping[str, {command: str,
    args?: tuple[str, ...], env?: Mapping[str, str]}]`` keyed by non-empty
    server name -- the project's declared MCP tool surface, rendered into a
    loop home's ``.mcp.json`` by ``cli/init.py::run_init`` (seed-not-overwrite,
    mirroring Story 1.7's adapter-seed pattern) and probed for resolvability
    by ``run_preflight``. Mirrors ``_valid_model_tier_map``'s/
    ``_valid_epic_surfaces``'s shape-checking pattern exactly: reject a
    non-mapping, reject a non-string/empty key, reject an entry with an
    unknown field or a malformed ``command``/``args``/``env`` -- the whole
    field is excluded for THAT layer on any single malformed entry (the
    same "one bad entry poisons the layer, not the whole field" semantics
    every other mapping-typed validator in this module already applies).
    ``command`` is REQUIRED and must be a non-empty str (the value
    ``run_preflight``'s resolvability probe checks against ``PATH``/disk);
    ``args`` defaults to an empty tuple, validated by the shared
    ``_valid_str_tuple`` (non-empty strings only, matching every other
    str-tuple field in this module); ``env`` defaults to an empty mapping,
    each key/value a plain ``str`` (an empty value is permitted -- an
    intentionally blank env var is a legitimate declaration, unlike an
    empty command or an empty server name, which name no server at all)."""
    if not isinstance(value, Mapping):
        return None
    result: dict[str, dict[str, object]] = {}
    for name, spec in value.items():
        if not isinstance(name, str) or name == "":
            return None
        if isinstance(spec, str) or not isinstance(spec, Mapping):
            return None
        if not set(spec.keys()) <= {"command", "args", "env"}:
            return None
        command = spec.get("command")
        if not isinstance(command, str) or command == "":
            return None
        args = _valid_str_tuple(spec.get("args", ()))
        if args is None:
            return None
        env_raw = spec.get("env", {})
        if isinstance(env_raw, str) or not isinstance(env_raw, Mapping):
            return None
        env: dict[str, str] = {}
        for env_key, env_value in env_raw.items():
            if not isinstance(env_key, str) or env_key == "" or not isinstance(env_value, str):
                return None
            env[env_key] = env_value
        result[name] = {"command": command, "args": args, "env": env}
    return result


def _valid_bool(value: object) -> bool | None:
    """``landing_branch_retirement``/``landing_resync``: a plain ``bool``
    only. ``isinstance(value, bool)`` alone is enough (unlike
    ``_valid_attempt_count``'s explicit ``not isinstance(value, bool)``
    exclusion) because THIS validator's whole job is accepting exactly that
    type."""
    if isinstance(value, bool):
        return value
    return None


def _valid_merge_strategy(value: object) -> str | None:
    if isinstance(value, str) and value in _MERGE_STRATEGIES:
        return value
    return None


def _valid_landing_rule(value: object) -> LandingRule | None:
    """One ``LandingRule`` entry: a ``Mapping`` with non-empty str ``name``/
    ``trigger_path_glob``, a required ``trigger_mode`` drawn from the closed
    ``_TRIGGER_MODES`` vocabulary (**corrected in review, 2026-08-06** --
    same closed-vocabulary validation shape as ``landing_merge_strategy``'s
    own ``_valid_merge_strategy``; a missing or invalid ``trigger_mode`` is a
    malformed rule, rejected exactly like every other bad landing-rule
    case), an optional str-or-``None`` ``label``/``required_check`` (at
    least one of the two set), and an optional ``bool`` ``ungated``
    (defaults ``False``). Unknown keys inside the mapping are rejected too
    -- the same closed-shape discipline ``_valid_model_tier_map``'s
    stage-name check already applies, so a typo'd field name never silently
    vanishes into a rule nobody notices is missing what the operator
    actually meant to set. ``ungated=True`` requires ``required_check`` to
    be set (review finding P3): "ungated" describes a check that can't be
    suppressed by a label, which is meaningless on a label-only rule."""
    if not isinstance(value, Mapping):
        return None
    allowed_keys = {
        "name",
        "trigger_path_glob",
        "trigger_mode",
        "label",
        "required_check",
        "ungated",
    }
    if not set(value.keys()) <= allowed_keys:
        return None
    name = value.get("name")
    trigger = value.get("trigger_path_glob")
    if not isinstance(name, str) or name == "":
        return None
    if not isinstance(trigger, str) or trigger == "":
        return None
    trigger_mode = value.get("trigger_mode")
    if not isinstance(trigger_mode, str) or trigger_mode not in _TRIGGER_MODES:
        return None
    label = value.get("label")
    if label is not None and (not isinstance(label, str) or label == ""):
        return None
    required_check = value.get("required_check")
    if required_check is not None and (
        not isinstance(required_check, str) or required_check == ""
    ):
        return None
    if label is None and required_check is None:
        return None
    ungated = value.get("ungated", False)
    if not isinstance(ungated, bool):
        return None
    if ungated and required_check is None:
        return None
    return LandingRule(
        name=name,
        trigger_path_glob=trigger,
        trigger_mode=trigger_mode,
        label=label,
        required_check=required_check,
        ungated=ungated,
    )


def _valid_landing_rules(value: object) -> tuple[LandingRule, ...] | None:
    """``landing_rules``: a list/tuple of ``LandingRule``-shaped mappings
    (mirrors ``_valid_epic_surfaces``'s own shape-checking pattern -- reject
    a non-list/tuple, reject any single malformed entry, the whole field is
    excluded for THAT layer on any one bad entry). A duplicate ``name``
    within the same tuple is rejected too -- two rules sharing a name is a
    collision no consumer could resolve unambiguously."""
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return None
    rules: list[LandingRule] = []
    seen_names: set[str] = set()
    for entry in value:
        rule = _valid_landing_rule(entry)
        if rule is None or rule.name in seen_names:
            return None
        seen_names.add(rule.name)
        rules.append(rule)
    return tuple(rules)


def _identify_bad_landing_rule(value: object) -> str:
    """Best-effort identification of the FIRST ``landing_rules`` entry that
    fails validation (review finding P6): the generic
    ``_malformed_finding``'s message dumps the ENTIRE raw layer value, which
    buries the one bad entry among any number of valid siblings once a
    project declares more than a couple of rules. Returns a fragment naming
    the offending rule by its own ``name`` when that field is itself usable,
    else its position -- always giving the operator something to search
    for. Never raises: mirrors every validator in this module in never
    trusting the shape of ``value``."""
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return f"the value is not a list of rules: {value!r}"
    seen_names: set[str] = set()
    for index, entry in enumerate(value):
        rule = _valid_landing_rule(entry)
        if rule is None:
            name = entry.get("name") if isinstance(entry, Mapping) else None
            if isinstance(name, str) and name != "":
                return f"rule {name!r} (index {index}) is malformed"
            return f"the rule at index {index} is malformed"
        if rule.name in seen_names:
            return f"rule {rule.name!r} (index {index}) duplicates an earlier rule's name"
        seen_names.add(rule.name)
    return "an unidentified entry is malformed"


def _malformed_landing_rules_finding(layer_name: str, raw_value: object) -> Finding:
    """``landing_rules``'s own malformed-value finding (review finding P6):
    same code/severity/path shape as ``_malformed_finding``, but names the
    SPECIFIC offending rule via ``_identify_bad_landing_rule`` instead of
    dumping the whole raw layer value -- the AC's own "an invalid landing
    policy is a preflight finding naming the layer that introduced each bad
    key" extends, per the spec's I/O matrix, to naming the bad rule itself
    when the bad key is one entry in a list of several."""
    return Finding(
        code="MRS-POLICY-002",
        severity=Severity.ERROR,
        message=(
            f"malformed value for policy key 'landing_rules' in the "
            f"{layer_name} layer: {_identify_bad_landing_rule(raw_value)} "
            "-- this layer's value is ignored"
        ),
        path=layer_name,
    )


def _to_plain(value: object) -> object:
    """Recursively convert any ``Mapping`` (incl. ``MappingProxyType``) to
    ``dict`` and any ``tuple`` to ``list``, for ``json.dumps``. A small,
    intentional duplicate of ``cli/config.py``'s own ``_json_safe`` --
    ``core/policy.py`` cannot import from ``cli`` (AD-4/the dependency
    direction), and the helper is a few lines, not worth a shared module."""
    if isinstance(value, Mapping):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, LandingRule):
        # Shared with `cli/config.py`'s `_json_safe` via
        # `core/landing.py::landing_rule_to_dict` (review finding P4) --
        # never hand-roll this field list a second time.
        return landing_rule_to_dict(value)
    return value


def _valid_merge_subject_template(value: object) -> str | None:
    if isinstance(value, str) and value != "":
        return value
    return None


def _valid_landing_base_branch(value: object) -> str | None:
    """``landing_base_branch``: a non-empty ``str`` only -- the same shape
    ``_valid_merge_subject_template`` validates, deliberately a separate
    function rather than a shared alias: the two fields answer unrelated
    questions (a subject template vs. a branch name), and a future
    branch-name-specific check (e.g. rejecting whitespace) must not silently
    apply to the subject template too."""
    if isinstance(value, str) and value != "":
        return value
    return None


def _valid_gate_mode(value: object) -> str | None:
    if isinstance(value, str) and value in _GATE_MODES:
        return value
    return None


def _valid_attempt_count(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _valid_positive_number(value: object) -> int | float | None:
    """Shared by ``idle_threshold_minutes`` (Story 3.5) and Story 3.6's four
    budget ceilings -- every operator-tunable numeric ceiling with no
    coherent "zero or unbounded" reading.

    Read the rationale below as written FOR ``idle_threshold_minutes``
    (review finding: it was, and the wording still is). It generalizes to
    the four budget ceilings in substance -- a zero or infinite ceiling is
    equally meaningless, and the same "a knob that quietly turns the feature
    off is worse than one that refuses the value" argument applies -- but
    two specifics do NOT: the token ceilings are counts, not minutes, and
    nothing converts them to seconds, so the ``* 60.0`` guard at the bottom
    binds them for no reason of their own. It is deliberately left shared
    anyway: it rejects only values above ~1.5e306, which no real token
    ceiling approaches, and one validator with one behaviour beats four
    near-identical copies. The only visible cost is that the resulting
    ``MRS-POLICY-003`` message reasons about seconds for a token count.

    ``idle_threshold_minutes``'s own validator (Story 3.5): mirrors
    ``_valid_attempt_count``'s shape but for a STRICTLY positive number
    rather than a non-negative int -- an idle threshold of zero has no
    coherent meaning (every tick would immediately cross it), unlike an
    attempt-count ceiling of zero (a legitimate "never retry" policy).
    ``int`` or ``float`` both accepted (unlike the int-only attempt-count
    fields): a synthetic test fixture may want a sub-minute threshold no
    whole-number minute value could express.

    Non-FINITE values are rejected alongside zero/negative ones (review
    finding). ``float('nan')`` already failed the ``> 0`` test (IEEE 754
    makes every relational comparison against NaN false), but
    ``float('inf')`` passed it -- and TOML 1.0 spells ``inf`` natively, so a
    project's own ``marshal-policy.toml`` could set it. An infinite
    threshold composes cleanly, renders as the effective value, and then
    silently disables the idle ladder FOREVER for every supervised run
    (``core/supervise.py`` floor-divides elapsed seconds by it, which is
    always ``0.0`` -- rung ``NONE``, permanently). A knob that can be set to
    a value which quietly turns the feature off with no diagnostic is worse
    than one that refuses the value, so this refuses it."""
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    # `float(value)` FIRST, and inside a guard (review finding). `math.
    # isfinite` takes a C double, so it raises `OverflowError` -- not
    # `ValueError`, not `TypeError` -- on a Python int too large to convert,
    # and NOTHING catches it: `compose()`'s own "never raises on malformed
    # CONTENT" guarantee breaks and the exception escapes to the caller.
    # `tomllib` does not enforce TOML's own 64-bit integer bound, so a
    # project's `marshal-policy.toml` carrying a long digit string (e.g.
    # `max_tokens_per_run = 999...9`, 300+ digits) reaches here as an
    # arbitrary-precision int. Story 3.6 is what makes this reachable in
    # practice: `idle_threshold_minutes` is a MINUTES value nobody writes 300
    # digits of, while the four new keys are TOKEN COUNTS -- exactly the kind
    # of knob an operator sets to "effectively unlimited" by mashing digits.
    #
    # The consequence is worst in `cli/spin.py::run_spin`, which calls
    # `compose()` only AFTER `harness.spin()` has already launched the run
    # and journaled its `run-launch` outcome: the traceback leaves a LIVE,
    # UNSUPERVISED harness and exits non-zero, which invites the caller to
    # retry and double-dispatch the very story the live run is already
    # working -- the exact hazard that module's own comments say the
    # surrounding `RecursionError` guard exists to prevent. Rejecting the
    # value here turns it back into the ordinary `MRS-POLICY-003`
    # malformed-value finding every other bad value already produces.
    try:
        as_float = float(value)
    except (OverflowError, ValueError):
        return None
    if not (as_float > 0 and math.isfinite(as_float)):
        return None
    # The DERIVED quantity must stay finite too (review finding). Every
    # consumer of this field converts it to seconds, and `1e308 * 60.0` is
    # `inf` -- a value that is finite here, composes cleanly, renders as the
    # effective policy, and is then rejected by the supervisor's own
    # `threshold_s` guard one process later. The sidecar exits 1 immediately
    # and silently (its stderr goes only to `supervisor.log`), while `spin`
    # has already printed a `supervisor_pid` and exited 0 -- so the operator
    # is told the run is supervised when nothing is watching it. Rejecting
    # it HERE turns that into the ordinary malformed-value finding the
    # operator can actually see and act on, which is this validator's whole
    # reason for rejecting `inf` in the first place.
    if not math.isfinite(as_float * 60.0):
        return None
    return value


def _malformed_finding(code: str, key: str, layer_name: str, raw_value: object) -> Finding:
    # redact() before formatting -- a secret-shaped key given a malformed
    # value must not leak its raw value into the finding message, the one
    # egress path that read `raw_value` directly instead of `field.value`/
    # `field.raw_source` (both already routed through redact() by callers).
    #
    # "ignored", never "falling back to the Marshal default": the excluded-
    # not-poisoned semantics mean the field keeps the previous VALID layer's
    # value when one exists (project-valid + flag-malformed retains the
    # project value), and the extras route retains the generated base --
    # claiming a default fallback would contradict the effective value
    # printed one line away in exactly those cases.
    safe_value = redact(key, raw_value)
    return Finding(
        code=code,
        severity=Severity.ERROR,
        message=(
            f"malformed value for policy key {key!r} in the {layer_name} "
            f"layer: {safe_value!r} -- this layer's value is ignored"
        ),
        path=layer_name,
    )


def _unknown_key_finding(key: str, layer_name: str) -> Finding:
    return Finding(
        code="MRS-POLICY-001",
        severity=Severity.ERROR,
        message=f"unknown policy key {key!r} in the {layer_name} layer -- ignored",
        path=layer_name,
    )


def _is_valid_project_slug(slug: str) -> bool:
    """Shape-only (FR-53): a project slug must be usable as ONE literal path
    segment of the generated ``worktree_seed_paths`` entry. Non-empty, at
    most 255 characters (POSIX NAME_MAX -- a longer slug is a path segment
    no target filesystem accepts, so validating it here reports the garbage
    at compose time instead of deferring an ENAMETOOLONG to every
    consumer; the charset is ASCII, so characters == bytes), drawn from the
    conservative ``_SLUG_CHARS`` charset, and not a pure-dot name
    (``.``/``..`` would alias or escape the ``projects/`` directory)."""
    return (
        bool(slug)
        and len(slug) <= 255
        and set(slug) <= _SLUG_CHARS
        and slug.strip(".") != ""
    )


def _project_slug_finding(slug: str) -> Finding:
    """A MISSING slug is ``warn`` (MRS-POLICY-005): a bare invocation with
    no active project legitimately shows the defaults, so the verdict stays
    in the exit-0 half of the lattice. A MALFORMED slug is ``error``
    (MRS-POLICY-006): the operator explicitly supplied a value that cannot
    be a path segment -- same posture as a malformed ``--set`` value."""
    if slug == "":
        return Finding(
            code="MRS-POLICY-005",
            severity=Severity.WARN,
            message=(
                "no project slug supplied -- worktree_seed_paths omits its "
                "project-derived path and carries only the marker path"
            ),
        )
    return Finding(
        code="MRS-POLICY-006",
        severity=Severity.ERROR,
        message=(
            f"malformed project slug {slug!r} -- must be one safe path "
            "segment (letters, digits, '.', '_', '-'; not '.' or '..'; "
            "at most 255 characters); worktree_seed_paths omits its "
            "project-derived path"
        ),
    )


def _merge_field(
    key: str,
    validator: _Validator,
    default_value: object,
    project: Mapping[str, object],
    flags: Mapping[str, object],
    findings: list[Finding],
    finding_code: str,
) -> PolicyField:
    """Apply the fixed ``defaults -> project -> flags`` precedence to one
    field (AD-16). A layer's malformed value is reported (never raised) via
    ``finding_code`` and excluded; the field keeps whatever the previous
    (better) layer already established -- see the module docstring's
    "compose() never raises" note for the stated assumption this encodes."""
    value = copy.deepcopy(default_value)
    layer = PolicyLayer.DEFAULT
    raw_source = value
    for layer_name, mapping, layer_enum in (
        ("project", project, PolicyLayer.PROJECT),
        ("flag", flags, PolicyLayer.FLAG),
    ):
        if key not in mapping:
            continue
        raw = mapping[key]
        coerced = validator(raw)
        if coerced is None:
            findings.append(_malformed_finding(finding_code, key, layer_name, raw))
        else:
            value, layer, raw_source = coerced, layer_enum, raw
    return PolicyField(value=value, layer=layer, raw_source=raw_source)


def _merge_landing_rules(
    project: Mapping[str, object],
    flags: Mapping[str, object],
    findings: list[Finding],
) -> PolicyField:
    """Same ``defaults -> project -> flags`` precedence as ``_merge_field``
    (AD-16), specialized for ``landing_rules`` so a malformed layer's
    finding names the SPECIFIC offending rule (review finding P6) via
    ``_malformed_landing_rules_finding`` instead of the generic
    ``_malformed_finding``'s whole-raw-value dump."""
    key = "landing_rules"
    value = copy.deepcopy(DEFAULT_POLICY[key])
    layer = PolicyLayer.DEFAULT
    raw_source = value
    for layer_name, mapping, layer_enum in (
        ("project", project, PolicyLayer.PROJECT),
        ("flag", flags, PolicyLayer.FLAG),
    ):
        if key not in mapping:
            continue
        raw = mapping[key]
        coerced = _valid_landing_rules(raw)
        if coerced is None:
            findings.append(_malformed_landing_rules_finding(layer_name, raw))
        else:
            value, layer, raw_source = coerced, layer_enum, raw
    return PolicyField(value=value, layer=layer, raw_source=raw_source)


def _base_worktree_seed_paths(project_slug: str | None) -> tuple[str, ...]:
    """FR-50: the base paths every project gets, GENERATED from
    ``project_slug`` -- never a hardcoded project name. ``None`` means the
    slug failed shape validation (missing or malformed -- already reported
    by ``compose()``): the project-derived path is OMITTED entirely rather
    than generated around a bad slug, so a ``projects//`` or
    traversal-shaped path can never enter a composed policy."""
    if project_slug is None:
        return ("_bmad/custom/.active-project",)
    return (
        f"_bmad-output/projects/{project_slug}/implementation-artifacts",
        "_bmad/custom/.active-project",
    )


def _compose_worktree_seed_paths(
    project_slug: str | None,
    project: Mapping[str, object],
    flags: Mapping[str, object],
    findings: list[Finding],
) -> PolicyField:
    """``worktree_seed_paths`` is GENERATED, never literal (FR-50): the base
    two paths always come from ``project_slug``; a layer may only APPEND
    extra paths on top. The winning layer is ``project`` only if the
    project layer contributed a valid extra-paths list, else ``default``
    (matching the spec's I/O matrix exactly). Flags are supported
    symmetrically for consistency with AD-16's uniform precedence, though
    ``cli/config.py`` deliberately never offers ``--set`` for this
    list-typed field. Extras are shape-validated by
    ``_valid_seed_path_extras`` (clean relative segments only), so the slug
    guard's traversal defense holds for BOTH ways content enters this
    field."""
    key = "worktree_seed_paths"
    base = _base_worktree_seed_paths(project_slug)
    extras: tuple[str, ...] = ()
    layer = PolicyLayer.DEFAULT
    raw_source: object = base
    for layer_name, mapping, layer_enum in (
        ("project", project, PolicyLayer.PROJECT),
        ("flag", flags, PolicyLayer.FLAG),
    ):
        if key not in mapping:
            continue
        raw = mapping[key]
        coerced = _valid_seed_path_extras(raw)
        if coerced is None:
            findings.append(_malformed_finding("MRS-POLICY-002", key, layer_name, raw))
        else:
            extras, layer, raw_source = coerced, layer_enum, raw
    return PolicyField(value=base + extras, layer=layer, raw_source=raw_source)


@dataclass(frozen=True)
class EffectivePolicy:
    """The composed, immutable policy value (AD-10): 4 public STATIC
    ``PolicyField`` attributes plus a private ``_seed`` mapping holding the
    10 SEED fields (AD-26). ``seed_view()`` is the sole whitelisted accessor
    for ``_seed`` -- ``tests/meta/test_ad26_seed_field_access_guard.py``
    fails the build if any other module IN THE INSTALLED PACKAGE accesses
    the ``_seed`` attribute directly (its scan surface; test code and
    external consumers are outside it -- see the guard's own stated
    bounds). ``content_hash`` is AD-35's naming primitive: a
    ``sha256`` hex digest over a canonical sorted-key JSON serialization of
    every field's value (static and seed), deterministic across identical
    ``compose()`` inputs.
    """

    verify_commands: PolicyField
    worktree_seed_paths: PolicyField
    merge_subject_template: PolicyField
    model_tier_map: PolicyField
    epic_surfaces: PolicyField
    landing_rules: PolicyField
    landing_merge_strategy: PolicyField
    landing_branch_retirement: PolicyField
    landing_resync: PolicyField
    landing_base_branch: PolicyField
    landing_resync_commands: PolicyField
    mcp_servers: PolicyField
    _seed: Mapping[str, PolicyField]

    def __post_init__(self) -> None:
        for name in (
            "verify_commands",
            "worktree_seed_paths",
            "merge_subject_template",
            "model_tier_map",
            "epic_surfaces",
            "landing_rules",
            "landing_merge_strategy",
            "landing_branch_retirement",
            "landing_resync",
            "landing_base_branch",
            "landing_resync_commands",
            "mcp_servers",
        ):
            value = getattr(self, name)
            if not isinstance(value, PolicyField):
                raise ValueError(f"{name} must be a PolicyField, got {value!r}")
        if isinstance(self._seed, str) or not isinstance(self._seed, Mapping):
            raise ValueError(f"_seed must be a Mapping, got {self._seed!r}")
        if set(self._seed.keys()) != _SEED_KEYS:
            raise ValueError(
                f"_seed must carry exactly the seed keys {sorted(_SEED_KEYS)}, "
                f"got {sorted(self._seed.keys())}"
            )
        for seed_key, field in self._seed.items():
            if not isinstance(field, PolicyField):
                raise ValueError(f"_seed[{seed_key!r}] must be a PolicyField, got {field!r}")
        object.__setattr__(self, "_seed", MappingProxyType(dict(self._seed)))

    def __repr__(self) -> str:
        """Name-aware and redaction-routed, unlike the dataclass-generated
        repr it replaces: every ``value``/``raw_source`` passes through
        ``redact()`` keyed on its field name, so a traceback, log line, or
        debugger that reprs a composed policy can never leak a
        secret-shaped field's raw value -- the same mechanism-completeness
        standard already applied to ``_malformed_finding``. Inert for the 9
        real fields (none is secret-shaped today), proven via the synthetic
        suffix fixture like every other redaction egress."""

        def _field_repr(name: str, field: PolicyField) -> str:
            return (
                f"PolicyField(value={redact(name, field.value)!r}, "
                f"layer={field.layer!r}, "
                f"raw_source={redact(name, field.raw_source)!r})"
            )

        static = ", ".join(
            f"{name}={_field_repr(name, getattr(self, name))}"
            for name in (
                "verify_commands",
                "worktree_seed_paths",
                "merge_subject_template",
                "model_tier_map",
                "epic_surfaces",
                "landing_rules",
                "landing_merge_strategy",
                "landing_branch_retirement",
                "landing_resync",
                "landing_base_branch",
                "landing_resync_commands",
                "mcp_servers",
            )
        )
        seed = ", ".join(
            f"{key!r}: {_field_repr(key, field)}" for key, field in sorted(self._seed.items())
        )
        return f"{type(self).__name__}({static}, _seed={{{seed}}})"

    def seed_view(self) -> Mapping[str, PolicyField]:
        """The sole whitelisted accessor for the 10 seed-tagged fields
        (AD-26, closing F-8): a read-only mapping keyed by field name. This
        is what lets ``marshal config`` (FR-54) print every effective key
        and FR-53 validation range over every key without contradicting
        "reading a seed field outside the journal fold fails a meta-test" --
        the meta-test whitelists exactly this accessor and nothing else."""
        return self._seed

    @property
    def content_hash(self) -> str:
        """``sha256`` hex digest over a canonical sorted-key JSON
        serialization of every field's FULL ``{value, layer, raw_source}``
        (5 static + 10 seed) -- AD-35's naming primitive. Hashing only
        ``value`` would let two compositions with identical values but
        DIFFERENT winning layers collide on the same hash, so
        ``materialize()``'s write-once check would silently keep stale
        provenance under a name that no longer matches what was written --
        this hashes exactly the same ``{value, layer, raw_source}`` shape
        ``cli/config.py`` persists, over the RAW (unredacted) values, so the
        hash correctly discriminates every distinct composition regardless
        of which fields, if any, are secret-shaped (redaction is a display/
        persistence concern, not an identity one). Deterministic: identical
        ``compose()`` inputs produce an identical hash."""

        def _field_payload(field: PolicyField) -> dict[str, object]:
            return {
                "value": _to_plain(field.value),
                "layer": field.layer.value,
                "raw_source": _to_plain(field.raw_source),
            }

        payload: dict[str, object] = {
            "verify_commands": _field_payload(self.verify_commands),
            "worktree_seed_paths": _field_payload(self.worktree_seed_paths),
            "merge_subject_template": _field_payload(self.merge_subject_template),
            "model_tier_map": _field_payload(self.model_tier_map),
            "epic_surfaces": _field_payload(self.epic_surfaces),
            "landing_rules": _field_payload(self.landing_rules),
            "landing_merge_strategy": _field_payload(self.landing_merge_strategy),
            "landing_branch_retirement": _field_payload(self.landing_branch_retirement),
            "landing_resync": _field_payload(self.landing_resync),
            "landing_base_branch": _field_payload(self.landing_base_branch),
            "landing_resync_commands": _field_payload(self.landing_resync_commands),
            "mcp_servers": _field_payload(self.mcp_servers),
        }
        payload.update(
            {key: _field_payload(field) for key, field in self._seed.items()}
        )
        canonical = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compose(
    *, project_slug: str, repo_defaults: Mapping[str, object] | None = None, project: Mapping[str, object], flags: Mapping[str, object]
) -> tuple[EffectivePolicy, tuple[Finding, ...]]:
    """The pure fold ``defaults -> repo_defaults -> project -> flags``, last
    wins (AD-16), over Marshal's closed 22-key policy vocabulary. Never reads a
    file or an env var -- ``repo_defaults``/``project``/``flags`` arrive as
    already-parsed mappings; the CLI boundary (``cli/config.py``) does the
    file/env I/O and calls this. The ``repo_defaults`` parameter was added in
    Story 1.10 to read repo-wide policy from `_bmad-output/policy-defaults.toml`
    and insert it between code defaults and project-layer overrides; it defaults
    to ``None`` (empty dict) for backward compatibility.

    Never raises for malformed CONTENT within ``project``/``flags`` --see
    the module docstring for the exact "excluded, not poisoned" fallback
    semantics and the MRS-POLICY-001/002/003 code split. A missing or
    malformed ``project_slug`` is likewise reported, never raised
    (MRS-POLICY-005 warn / MRS-POLICY-006 error), and the project-derived
    seed path is omitted. Still raises ``TypeError`` for a CONTRACT
    violation (a non-``str`` ``project_slug``, or a ``project``/``flags``
    that isn't a ``Mapping`` -- including a bare ``str``, which satisfies
    neither layer's intended shape), matching ``core/identity.py``'s own
    type-guard convention.
    """
    if not isinstance(project_slug, str):
        raise TypeError(f"project_slug must be a str, got {project_slug!r}")
    if isinstance(project, str) or not isinstance(project, Mapping):
        raise TypeError(f"project must be a Mapping, not a bare str: {project!r}")
    if isinstance(flags, str) or not isinstance(flags, Mapping):
        raise TypeError(f"flags must be a Mapping, not a bare str: {flags!r}")

    findings: list[Finding] = []

    slug_ok = _is_valid_project_slug(project_slug)
    if not slug_ok:
        findings.append(_project_slug_finding(project_slug))

    for layer_name, mapping in (("project", project), ("flag", flags)):
        for key in mapping:
            if key not in _ALL_KEYS:
                findings.append(_unknown_key_finding(key, layer_name))

    verify_commands = _merge_field(
        "verify_commands",
        _valid_str_tuple,
        DEFAULT_POLICY["verify_commands"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    worktree_seed_paths = _compose_worktree_seed_paths(
        project_slug if slug_ok else None, project, flags, findings
    )
    merge_subject_template = _merge_field(
        "merge_subject_template",
        _valid_merge_subject_template,
        DEFAULT_POLICY["merge_subject_template"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    model_tier_map = _merge_field(
        "model_tier_map",
        _valid_model_tier_map,
        DEFAULT_POLICY["model_tier_map"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    epic_surfaces = _merge_field(
        "epic_surfaces",
        _valid_epic_surfaces,
        DEFAULT_POLICY["epic_surfaces"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    landing_rules = _merge_landing_rules(project, flags, findings)
    landing_merge_strategy = _merge_field(
        "landing_merge_strategy",
        _valid_merge_strategy,
        DEFAULT_POLICY["landing_merge_strategy"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    landing_branch_retirement = _merge_field(
        "landing_branch_retirement",
        _valid_bool,
        DEFAULT_POLICY["landing_branch_retirement"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    landing_resync = _merge_field(
        "landing_resync",
        _valid_bool,
        DEFAULT_POLICY["landing_resync"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    landing_base_branch = _merge_field(
        "landing_base_branch",
        _valid_landing_base_branch,
        DEFAULT_POLICY["landing_base_branch"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    landing_resync_commands = _merge_field(
        "landing_resync_commands",
        _valid_str_tuple,
        DEFAULT_POLICY["landing_resync_commands"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    mcp_servers = _merge_field(
        "mcp_servers",
        _valid_mcp_servers,
        DEFAULT_POLICY["mcp_servers"],
        project,
        flags,
        findings,
        "MRS-POLICY-002",
    )
    seed = {
        "gate_mode": _merge_field(
            "gate_mode",
            _valid_gate_mode,
            DEFAULT_POLICY["gate_mode"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "frozen_surfaces": _merge_field(
            "frozen_surfaces",
            _valid_str_tuple,
            DEFAULT_POLICY["frozen_surfaces"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_dev_attempts": _merge_field(
            "max_dev_attempts",
            _valid_attempt_count,
            DEFAULT_POLICY["max_dev_attempts"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_review_cycles": _merge_field(
            "max_review_cycles",
            _valid_attempt_count,
            DEFAULT_POLICY["max_review_cycles"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_followup_reviews": _merge_field(
            "max_followup_reviews",
            _valid_attempt_count,
            DEFAULT_POLICY["max_followup_reviews"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "idle_threshold_minutes": _merge_field(
            "idle_threshold_minutes",
            _valid_positive_number,
            DEFAULT_POLICY["idle_threshold_minutes"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_tokens_per_story": _merge_field(
            "max_tokens_per_story",
            _valid_positive_number,
            DEFAULT_POLICY["max_tokens_per_story"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_tokens_per_run": _merge_field(
            "max_tokens_per_run",
            _valid_positive_number,
            DEFAULT_POLICY["max_tokens_per_run"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_wall_clock_minutes_per_story": _merge_field(
            "max_wall_clock_minutes_per_story",
            _valid_positive_number,
            DEFAULT_POLICY["max_wall_clock_minutes_per_story"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
        "max_wall_clock_minutes_per_run": _merge_field(
            "max_wall_clock_minutes_per_run",
            _valid_positive_number,
            DEFAULT_POLICY["max_wall_clock_minutes_per_run"],
            project,
            flags,
            findings,
            "MRS-POLICY-003",
        ),
    }

    effective = EffectivePolicy(
        verify_commands=verify_commands,
        worktree_seed_paths=worktree_seed_paths,
        merge_subject_template=merge_subject_template,
        model_tier_map=model_tier_map,
        epic_surfaces=epic_surfaces,
        landing_rules=landing_rules,
        landing_merge_strategy=landing_merge_strategy,
        landing_branch_retirement=landing_branch_retirement,
        landing_resync=landing_resync,
        landing_base_branch=landing_base_branch,
        landing_resync_commands=landing_resync_commands,
        mcp_servers=mcp_servers,
        _seed=seed,
    )
    return effective, tuple(findings)
