"""Layered policy composition with provenance and validation (Story 1.3,
architecture spine AD-10/AD-16/AD-26/AD-35).

``compose()`` is the pure fold ``defaults -> project -> flags, last wins``
(AD-16) over Marshal's own CLOSED 9-key policy vocabulary (FR-49/50/51/53/54)
-- not a mirror of the harness's much larger ``.bmad-loop/policy.toml`` key
surface (that mapping is Story 1.10's rendering concern). Every field is
wrapped in a ``PolicyField{value, layer, raw_source}`` so an operator can
always answer "why is this value what it is?" (AD-16).

**Static vs seed (AD-26).** 4 fields are STATIC -- public ``EffectivePolicy``
attributes, each a ``PolicyField``: ``verify_commands``,
``worktree_seed_paths``, ``merge_subject_template``, ``model_tier_map``. 5
fields are SEED -- epics.md's own named examples ("frozen surfaces, gate
mode, attempt counts"): ``gate_mode``, ``frozen_surfaces``,
``max_dev_attempts``, ``max_review_cycles``, ``max_followup_reviews``. Seed
fields live ONLY in a private ``_seed`` mapping; ``seed_view()`` is the sole
whitelisted accessor (closing F-8: it is what lets ``marshal config``/FR-54
and FR-53 validation range over every key without contradicting "reading a
seed field outside the journal fold fails a meta-test"). A composed
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
for a malformed SEED field). **Stated assumption** (the spec's prose reads
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
support for ``--set`` on the three list/mapping-typed fields -- that is a
``cli/config.py`` UX restriction on which flags it exposes, not a
restriction this module enforces (``compose()`` itself layers all 9 keys
uniformly across all 3 layers, matching AD-16's "no per-key reordering").

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
``dataclasses``, ``enum``, ``types``, ``collections.abc``, and ``.model``.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .model import Finding, Severity

# --- the closed 9-key vocabulary --------------------------------------------

_STATIC_KEYS: frozenset[str] = frozenset(
    {"verify_commands", "worktree_seed_paths", "merge_subject_template", "model_tier_map"}
)
_SEED_KEYS: frozenset[str] = frozenset(
    {
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
    }
)
_ALL_KEYS: frozenset[str] = _STATIC_KEYS | _SEED_KEYS

_STAGE_NAMES: frozenset[str] = frozenset({"dev", "review", "triage"})
_GATE_MODES: frozenset[str] = frozenset({"none", "per-epic", "per-story-spec-approval"})

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
    "max_followup_reviews": 1,
}

# Secret redaction (Boundaries & Constraints): a case-insensitive suffix
# match against a field NAME renders a fixed sentinel instead of the value.
# None of the 9 real fields match today -- proven via a synthetic fixture in
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


@dataclass(frozen=True)
class PolicyField:
    """One policy value plus its provenance (AD-16): the effective
    ``value``, the ``layer`` that won it, and ``raw_source`` -- the
    unwrapped original value from that winning layer (for provenance
    display; equals ``value`` when the winning layer is ``default``)."""

    value: object
    layer: PolicyLayer
    raw_source: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "layer", PolicyLayer(self.layer))


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
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def _valid_model_tier_map(value: object) -> dict[str, dict[str, str]] | None:
    if not isinstance(value, Mapping):
        return None
    result: dict[str, dict[str, str]] = {}
    for difficulty, stages in value.items():
        if not isinstance(difficulty, str) or not isinstance(stages, Mapping):
            return None
        stage_map: dict[str, str] = {}
        for stage, model in stages.items():
            if stage not in _STAGE_NAMES or not isinstance(model, str):
                return None
            stage_map[stage] = model
        result[difficulty] = stage_map
    return result


def _freeze_model_tier_map(
    value: Mapping[str, Mapping[str, str]],
) -> Mapping[str, Mapping[str, str]]:
    """Deep-freeze a merged ``model_tier_map`` value: ``MappingProxyType``
    at both levels. Every other field is an immutable tuple/str/int, so a
    caller holding a reference to it cannot mutate what ``content_hash``
    computes afterward -- ``model_tier_map`` is the one nested-mapping field
    and needs this explicit step (``copy.deepcopy`` cannot run on an
    already-frozen ``MappingProxyType``, so this is applied ONCE, after
    ``_merge_field`` finishes with a plain dict, never baked into
    ``DEFAULT_POLICY`` or a validator's return value)."""
    return MappingProxyType(
        {difficulty: MappingProxyType(dict(stages)) for difficulty, stages in value.items()}
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
    return value


def _valid_merge_subject_template(value: object) -> str | None:
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


def _malformed_finding(code: str, key: str, layer_name: str, raw_value: object) -> Finding:
    # redact() before formatting -- a secret-shaped key given a malformed
    # value must not leak its raw value into the finding message, the one
    # egress path that read `raw_value` directly instead of `field.value`/
    # `field.raw_source` (both already routed through redact() by callers).
    safe_value = redact(key, raw_value)
    return Finding(
        code=code,
        severity=Severity.ERROR,
        message=(
            f"malformed value for policy key {key!r} in the {layer_name} "
            f"layer: {safe_value!r} -- falling back to the Marshal default"
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


def _base_worktree_seed_paths(project_slug: str) -> tuple[str, str]:
    """FR-50: the two paths every project gets, GENERATED from
    ``project_slug`` -- never a hardcoded project name."""
    return (
        f"_bmad-output/projects/{project_slug}/implementation-artifacts",
        "_bmad/custom/.active-project",
    )


def _compose_worktree_seed_paths(
    project_slug: str,
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
    list-typed field."""
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
        coerced = _valid_str_tuple(raw)
        if coerced is None:
            findings.append(_malformed_finding("MRS-POLICY-002", key, layer_name, raw))
        else:
            extras, layer, raw_source = coerced, layer_enum, raw
    return PolicyField(value=base + extras, layer=layer, raw_source=raw_source)


@dataclass(frozen=True)
class EffectivePolicy:
    """The composed, immutable policy value (AD-10): 4 public STATIC
    ``PolicyField`` attributes plus a private ``_seed`` mapping holding the
    5 SEED fields (AD-26). ``seed_view()`` is the sole whitelisted accessor
    for ``_seed`` -- ``tests/meta/test_ad26_seed_field_access_guard.py``
    fails the build if any module OTHER than this one accesses the ``_seed``
    attribute directly. ``content_hash`` is AD-35's naming primitive: a
    ``sha256`` hex digest over a canonical sorted-key JSON serialization of
    every field's value (static and seed), deterministic across identical
    ``compose()`` inputs.
    """

    verify_commands: PolicyField
    worktree_seed_paths: PolicyField
    merge_subject_template: PolicyField
    model_tier_map: PolicyField
    _seed: Mapping[str, PolicyField]

    def __post_init__(self) -> None:
        for name in (
            "verify_commands",
            "worktree_seed_paths",
            "merge_subject_template",
            "model_tier_map",
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

    def seed_view(self) -> Mapping[str, PolicyField]:
        """The sole whitelisted accessor for the 5 seed-tagged fields
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
        (4 static + 5 seed) -- AD-35's naming primitive. Hashing only
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
        }
        payload.update(
            {key: _field_payload(field) for key, field in self._seed.items()}
        )
        canonical = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compose(
    *, project_slug: str, project: Mapping[str, object], flags: Mapping[str, object]
) -> tuple[EffectivePolicy, tuple[Finding, ...]]:
    """The pure fold ``defaults -> project -> flags``, last wins (AD-16),
    over Marshal's closed 9-key policy vocabulary. Never reads a file or an
    env var -- ``project``/``flags`` arrive as already-parsed mappings; the
    CLI boundary (``cli/config.py``) does the file/env I/O and calls this.

    Never raises for malformed CONTENT within ``project``/``flags`` --see
    the module docstring for the exact "excluded, not poisoned" fallback
    semantics and the MRS-POLICY-001/002/003 code split. Still raises
    ``TypeError`` for a CONTRACT violation (a non-``str`` ``project_slug``,
    or a ``project``/``flags`` that isn't a ``Mapping`` -- including a bare
    ``str``, which satisfies neither layer's intended shape), matching
    ``core/identity.py``'s own type-guard convention.
    """
    if not isinstance(project_slug, str):
        raise TypeError(f"project_slug must be a str, got {project_slug!r}")
    if isinstance(project, str) or not isinstance(project, Mapping):
        raise TypeError(f"project must be a Mapping, not a bare str: {project!r}")
    if isinstance(flags, str) or not isinstance(flags, Mapping):
        raise TypeError(f"flags must be a Mapping, not a bare str: {flags!r}")

    findings: list[Finding] = []

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
    worktree_seed_paths = _compose_worktree_seed_paths(project_slug, project, flags, findings)
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
    # Deep-freeze AFTER the merge (never inside DEFAULT_POLICY or the
    # validator): `_merge_field`'s `copy.deepcopy(default_value)` cannot run
    # on an already-frozen MappingProxyType, so this is the one place the
    # freeze can apply uniformly regardless of which layer won.
    model_tier_map = PolicyField(
        value=_freeze_model_tier_map(model_tier_map.value),
        layer=model_tier_map.layer,
        raw_source=model_tier_map.raw_source,
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
    }

    effective = EffectivePolicy(
        verify_commands=verify_commands,
        worktree_seed_paths=worktree_seed_paths,
        merge_subject_template=merge_subject_template,
        model_tier_map=model_tier_map,
        _seed=seed,
    )
    return effective, tuple(findings)
