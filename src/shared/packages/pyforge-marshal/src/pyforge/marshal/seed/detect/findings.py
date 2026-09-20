"""``Finding`` data layer: severity, type, remedy (Story 9.1, architecture
AD-54/P-10, PRD NFR-M3).

Epic 9 ("Detect & Plan") has no shared vocabulary yet for a conformance
problem -- every later `detect`/`plan`/`check` story needs one typed, closed
shape to report a finding in, with a remedy a human or CI can act on without
reading Genesis's own source. This module is that shape: a `Severity`
ladder, a closed `FindingType` enum, a `REMEDIES` mapping giving every
member a documented remedy string, and a frozen `Finding` dataclass tying
one instance of each together.

AD-54 is explicit that Genesis **borrows the proven design** from
`bmad_drift_check.py` -- the `Finding(severity, type, path, message)` shape
and the HARD/DRIFT/INFO severity ladder -- without importing, vendoring, or
extracting the script itself: that file is ~85% `local-recipes`
factory-specific and meaningless in another repo. Nothing in this module
imports from or references `bmad_drift_check.py`, or from any other
`pyforge.marshal.*` module -- this is a leaf under `detect/`, needing
nothing beyond the stdlib (the architecture's module-dependency rules place
`detect` below `model`/`state`/`regions`/`engine`, and this story ships the
model only, not a real finding-emission call site).

`remedy` is validated against `REMEDIES` in `__post_init__` rather than left
free-text, for the same reason `Artifact.__post_init__` (`model/artifact.py`)
validates its own entry/behavior pairing: NFR-M3 and P-10 both frame the
remedy as a property of the *type*, documented once, not a per-instance
convenience a caller could word differently each time. Making that
invariant structural (rather than a convention callers might drift from)
means a `FindingType` member added without a `REMEDIES` entry raises
immediately from every construction site, not only from the completeness
test. `Finding.new(...)` exists so no real call site has to hand-copy the
`REMEDIES` text (and risk a typo raising `ValueError`) to get a valid
instance.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class Severity(StrEnum):
    """The HARD/DRIFT/INFO ladder AD-54 borrows from `bmad_drift_check.py`
    (uppercase wire values, matching `pyforge.doctor.sources.factory`'s own
    port of the identical ladder): `HARD` breaks the conformance contract
    outright, `DRIFT` means the repo is stale but the contract still holds,
    `INFO` is advisory only. Which severity a given `FindingType` actually
    carries at a real call site is a later detect/plan story's decision --
    see the module's own Never boundary; this enum only closes the
    vocabulary."""

    HARD = "HARD"
    DRIFT = "DRIFT"
    INFO = "INFO"


class FindingType(StrEnum):
    """The closed conformance-problem vocabulary every later detect/plan
    story emits against -- the 12 members the epics AC names plus Story
    28.3's three token-economy-kit members, kebab-case wire values matching
    this package's existing `ArtifactClass` convention
    (`model/manifest.py`).

    The three `KIT_*` members (Story 28.3, SPEC-marshal-token-economy
    CAP-3/CAP-4) are deliberately DISTINCT types rather than reuses of
    `artifact-missing`/`derived-stale`: a kit item is not a manifest
    artifact (nothing in `templates/manifest.yaml` declares it, `seed
    adopt`/`update` never materialize it), its remedy is a different
    command, and -- the reason that matters -- `artifact-missing` is HARD
    while every kit finding must be non-blocking. The spec's own constraint
    is "an unavailable instrument disables its layer with a named finding,
    never blocks a run"; borrowing a HARD type would have made a missing
    optional instrument fail `marshal seed check`, which is exactly the
    outcome that constraint forbids."""

    ARTIFACT_MISSING = "artifact-missing"
    MANAGED_FILE_MODIFIED = "managed-file-modified"
    MANAGED_REGION_MODIFIED = "managed-region-modified"
    MANAGED_REGION_MISSING = "managed-region-missing"
    DERIVED_STALE = "derived-stale"
    MODEL_BEHIND = "model-behind"
    STATE_INVALID = "state-invalid"
    NEVER_WRITE_VIOLATION = "never-write-violation"
    REFERENCED_DEP_MISSING = "referenced-dep-missing"
    UNCOVERED = "uncovered"
    LEGACY_PRESENT = "legacy-present"
    OPTED_OUT = "opted-out"
    KIT_ITEM_MISSING = "kit-item-missing"
    KIT_ITEM_STALE = "kit-item-stale"
    KIT_INSTRUMENT_UNAVAILABLE = "kit-instrument-unavailable"


# Read-only, and with NO module-level mutable name behind it -- same reason
# as `artifact.py`'s `CLASS_BEHAVIOR`: `Finding.__post_init__` validates
# every constructed instance against this same table, so a rebound entry
# would corrupt that check from inside while still passing it. A
# `MappingProxyType` wrapping a dict that stays reachable under its own name
# does not close that (the proxy is a read-only VIEW; mutating the
# underlying dict is fully visible through it), so the literal is built
# inline and never bound elsewhere.
REMEDIES: Mapping[FindingType, str] = MappingProxyType(
    {
        FindingType.ARTIFACT_MISSING: (
            "Run `marshal seed adopt` (or `init`, for a first-ever install) to materialize it."
        ),
        FindingType.MANAGED_FILE_MODIFIED: (
            "The file is tool-owned -- revert the local edit, or run `marshal "
            "seed update --force` to accept it as the new baseline."
        ),
        FindingType.MANAGED_REGION_MODIFIED: (
            "Revert edits inside the managed region, or run `marshal seed "
            "update --force` to overwrite it; content outside the markers is "
            "untouched."
        ),
        FindingType.MANAGED_REGION_MISSING: (
            "Run `marshal seed update` to re-insert the region at its declared anchor."
        ),
        FindingType.DERIVED_STALE: (
            "Run `marshal seed update` to recompute it; this class is always safe to regenerate."
        ),
        FindingType.MODEL_BEHIND: (
            "Run `marshal seed update` to upgrade the repo to the currently installed model version."
        ),
        FindingType.STATE_INVALID: (
            "Restore `.marshal/seed-state.yml` from version control, or run "
            "`marshal seed adopt` to rebuild it; never hand-edit state."
        ),
        FindingType.NEVER_WRITE_VIOLATION: (
            "No repo action needed -- this names a bug in the plan builder or manifest; file an issue against Genesis."
        ),
        FindingType.REFERENCED_DEP_MISSING: (
            "Install the missing dependency at or above its declared floor "
            "(`marshal doctor check` can do this where available)."
        ),
        FindingType.UNCOVERED: (
            "Fix the manifest entry -- give it a valid `class`, or `unclassified-deferred` with a `rationale`."
        ),
        FindingType.LEGACY_PRESENT: (
            "Informational only, no action required; migrate to the named successor by hand when ready."
        ),
        FindingType.OPTED_OUT: (
            "Informational -- while this opt-out stands the tool will not "
            "re-insert this region. To bring it back under management, run "
            "`marshal seed adopt --reinstate <artifact>#<region>`."
        ),
        FindingType.KIT_ITEM_MISSING: (
            "Run `marshal seed kit --apply` in the loop home to provision it, "
            "or turn its `[context]` layer off if this home does not want it."
        ),
        FindingType.KIT_ITEM_STALE: (
            "Run `marshal seed kit --apply` to refresh it; the item is there but no longer matches what produced it."
        ),
        FindingType.KIT_INSTRUMENT_UNAVAILABLE: (
            "Advisory -- install the named instrument (or accept the platform "
            "gap); the layer stays off and nothing is blocked."
        ),
    }
)


def _remedy_for(finding_type: FindingType) -> str:
    """Look up ``REMEDIES[finding_type]``, raising the same ``ValueError``
    (never a bare ``KeyError``) from every caller -- ``__post_init__`` and
    ``Finding.new`` both route through this one function so a `FindingType`
    member added without a `REMEDIES` entry fails identically regardless of
    which construction path reaches it first."""
    try:
        return REMEDIES[finding_type]
    except KeyError:
        raise ValueError(
            f"{finding_type.value}: no REMEDIES entry -- every FindingType member must have a documented remedy"
        ) from None


@dataclass(frozen=True)
class Finding:
    """One conformance problem: severity, type, the artifact path it names,
    a human-readable message, and its type's documented remedy.

    `remedy` is not free text -- `__post_init__` requires it to equal
    `REMEDIES[type]` exactly, so a `Finding` can never carry a hand-typed or
    mismatched remedy (see the module docstring). `severity`/`type` coerce
    through their own `StrEnum` constructors, so a plain matching string
    (e.g. `"HARD"`, `"uncovered"`) is accepted and normalized the same way
    `ManifestEntry.__post_init__` coerces `artifact_class`/`applies_to`; an
    invalid value raises `ValueError` directly from the enum constructor,
    unmodified -- there is nothing to add to that message.

    `Finding.new(...)` is the sanctioned constructor for real call sites: it
    resolves `remedy` from `REMEDIES` so no caller hand-copies remedy text.
    Direct `Finding(...)` construction stays legal (tests, the completeness
    check)."""

    severity: Severity
    type: FindingType
    path: str
    message: str
    remedy: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", Severity(self.severity))
        object.__setattr__(self, "type", FindingType(self.type))
        if not isinstance(self.path, str) or not self.path.strip():
            raise ValueError(f"path must be a non-empty, non-blank str, got {self.path!r}")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError(f"message must be a non-empty, non-blank str, got {self.message!r}")
        object.__setattr__(self, "path", self.path.strip())
        object.__setattr__(self, "message", self.message.strip())
        # Routed through `_remedy_for` (never a direct `REMEDIES[...]`
        # subscript) so a `FindingType` member missing a `REMEDIES` entry
        # raises this module's own `ValueError` here too, not only from
        # `Finding.new` -- the same guard, the same message, from every
        # construction site.
        expected_remedy = _remedy_for(self.type)
        if self.remedy != expected_remedy:
            raise ValueError(f"{self.type.value}: remedy must be {expected_remedy!r}, got {self.remedy!r}")

    @classmethod
    def new(cls, severity: Severity | str, type: FindingType | str, path: str, message: str) -> Finding:
        """Construct a `Finding` with `remedy` resolved from `REMEDIES`,
        so a real call site never hand-copies remedy text.

        Both `severity` and `type` are resolved through their own `StrEnum`
        constructor before construction (not left to `__post_init__` alone):
        `type` must be resolved here regardless, to key the `REMEDIES`
        lookup below, and resolving `severity` the same way keeps this
        method's own signature precisely typed rather than widening it to
        accept whatever `__post_init__` would otherwise coerce."""
        resolved_severity = Severity(severity)
        resolved_type = FindingType(type)
        return cls(
            severity=resolved_severity,
            type=resolved_type,
            path=path,
            message=message,
            remedy=_remedy_for(resolved_type),
        )

    def to_json_dict(self) -> dict[str, str]:
        """The `--json` stability the epics AC requires: plain `str` values,
        fixed key order."""
        return {
            "severity": self.severity.value,
            "type": self.type.value,
            "path": self.path,
            "message": self.message,
            "remedy": self.remedy,
        }
