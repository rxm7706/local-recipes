"""Manifest schema + loader (Story 7.4, architecture A-02/AD-55/AD-59/AD-61).

A-02: "the model is a declarative manifest; the engine knows only the
classes" -- this module is the one place that reads ``templates/manifest.yaml``
(a future story's content; this story ships the loader only, per the spec's
Never bullet) and turns it into typed, validated data. Every later seed
story (7.5's real manifest, 7.3's write guard, detect/plan/migrate) trusts
``load_manifest``'s output rather than re-parsing YAML itself.

``ArtifactClass`` is the six-member classification vocabulary the
extraction-manifest's own five product classes plus ``unclassified-deferred``
resolve to (a V1-only escape hatch for artifacts "too repo-specific to
classify confidently", extraction-manifest's own closing section).

Two validation layers, matching ``core/model.py``'s own idiom:
``Region``/``ManifestEntry``/``Manifest`` are ``@dataclass(frozen=True)``
with ``__post_init__`` raising ``ValueError`` on any shape violation --
useful on their own for anyone constructing these directly (tests, a future
in-memory manifest builder). ``load_manifest`` is a thin YAML-shape adapter
around that: per-entry fields route through ``_build_entry`` into
``ManifestEntry``'s ``__post_init__`` for the real checking, with no
parallel field-by-field re-validation of its own that could drift from the
dataclass's own rules. The two top-level collection fields
(``never_write``, ``artifacts``) are the one deliberate exception: they get
their own loader-side shape check, because the final ``Manifest(...)``
construction below is not itself wrapped in a ``ValueError``-to-
``ManifestError`` translation (unlike ``_build_entry``, which is) -- without
that pre-check a malformed top-level field would raise a raw ``ValueError``
instead of ``ManifestError``. Either way, every raised ``ManifestError`` is
prefixed with the offending id (or ``"manifest"`` for a top-level failure,
or ``"artifacts[N]"`` for an entry whose own ``id`` could not be
determined) -- the AC's "raise ManifestError naming the offending id"
contract in exactly one place, the loader.

Top-level ``artifacts:`` is a LIST with an explicit ``id:`` field per entry,
not a ``{id: {...}}`` mapping, even though AD-55/P-11 describe entries as
"keyed by stable artifact id": PyYAML's default (safe) loader silently
overwrites duplicate mapping keys, which would make "duplicate ids are a
load-time error" unenforceable -- the addressing scheme AD-55 names is a
downstream concern (state, ``explain <id>``), not the wire shape. That same
silent-overwrite hazard applies to every OTHER mapping in the document
(two ``model_version:`` keys, two ``path:`` keys in one entry), so parsing
goes through ``_StrictLoader``, which rejects any repeated key. Keys are
also a closed vocabulary at all three levels -- an unrecognized key is an
error, never ignored, because a typo in an optional field (``untl:``) is
otherwise undetectable in the only review this file ever gets: a git diff.

``since``/``until`` bounds are half-open (``[since, until)``,
``version.in_range``) -- an undocumented-upstream, this-story's-own
decision matching the common ``>=since,<until`` versioning convention.
After validation, ``load_manifest`` filters ``entries`` to those in range at
the manifest's OWN top-level ``model_version`` (not an externally supplied
"current" version -- architecture reserves that name for installed *state*,
a later-story concern): the manifest is an append-only historical ledger,
so future-staged and retired entries stay in the reviewable diff without
deletion (AD-55's "the manifest is the product's actual contract").

No pydantic, no runtime ``jsonschema`` validation path (no precedent for
that pattern in this package; ``schemas/*.json`` is for cross-process
wire contracts, not internal loading) -- this story's own Never bullet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from .version import InvalidVersionError, ModelVersion, in_range


class ArtifactClass(StrEnum):
    """The extraction-manifest's classification vocabulary (six members:
    the five product classes plus ``unclassified-deferred``, its own V1
    escape hatch)."""

    REFERENCED = "referenced"
    COPIED_MANAGED = "copied-managed"
    COPIED_SEEDED = "copied-seeded"
    GENERATED_DERIVED = "generated-derived"
    HYBRID_MANAGED_REGION = "hybrid-managed-region"
    UNCLASSIFIED_DEFERRED = "unclassified-deferred"


class AppliesTo(StrEnum):
    """Which seed verb(s) an entry participates in (AD-55)."""

    INIT = "init"
    ADOPT = "adopt"
    BOTH = "both"


class ManifestError(Exception):
    """Raised by ``load_manifest`` for any schema violation. The message is
    always prefixed with a locator: ``"<id>: "`` (the offending entry's id),
    ``"artifacts[N]: "`` (an entry whose own ``id`` could not be read, so it
    is addressed by position), or ``"manifest: "`` (a top-level failure)."""


class _StrictLoader(yaml.SafeLoader):
    """``SafeLoader`` that rejects a repeated mapping key rather than
    silently keeping the last one.

    This module's own wire shape (``artifacts`` as a LIST, not an
    ``{id: {...}}`` mapping) exists precisely because PyYAML's default
    loader drops duplicate keys silently -- but that hazard is not confined
    to the entry list. A manifest with two ``model_version:`` keys, or an
    entry with two ``path:`` keys, would otherwise load clean with the
    SECOND value winning, so the file a human reviewed in the diff is not
    the file the engine loaded. ``ConstructorError`` is a ``YAMLError``, so
    ``load_manifest``'s existing handler reports it as a ``ManifestError``.
    """

    def construct_mapping(self, node: Any, deep: bool = False) -> dict:
        mapping = super().construct_mapping(node, deep=deep)
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            seen.add(key)
        return mapping


# Closed key vocabularies. An unrecognized key is an error, never ignored:
# the manifest is a hand-authored contract whose only reviewer is a git
# diff, and a one-character typo in an OPTIONAL field is otherwise
# undetectable -- `untl:` means the entry never retires, a misspelled
# `legacy_of` or `pin` simply vanishes.
_DOCUMENT_KEYS = frozenset({"model_version", "never_write", "artifacts"})
_ENTRY_KEYS = frozenset(
    {
        "id",
        "class",
        "path",
        "applies_to",
        "rationale",
        "pin",
        "format",
        "regions",
        "since",
        "until",
        "legacy_of",
    }
)
_REGION_KEYS = frozenset({"name", "anchor"})


def _reject_unknown_keys(raw_mapping: dict, allowed: frozenset[str], what: str) -> None:
    unknown = sorted(str(key) for key in raw_mapping if key not in allowed)
    if unknown:
        raise ValueError(f"unrecognized {what} key(s): {', '.join(unknown)}")


@dataclass(frozen=True)
class Region:
    """One hybrid-managed-region declaration: a name and an ordered anchor
    list (AD-56's line-prefix matchers). Both fields are required and
    non-empty -- an unnamed or anchorless region cannot be inserted."""

    name: str
    anchor: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"region name must be a non-empty str, got {self.name!r}")
        object.__setattr__(self, "anchor", tuple(self.anchor) if isinstance(self.anchor, list) else self.anchor)
        if not isinstance(self.anchor, tuple) or not self.anchor:
            raise ValueError(f"anchor must be a non-empty tuple, got {self.anchor!r}")
        if not all(isinstance(item, str) and item for item in self.anchor):
            raise ValueError(f"anchor must contain only non-empty str, got {self.anchor!r}")


@dataclass(frozen=True)
class ManifestEntry:
    """One manifest entry. ``artifact_class`` (not ``class`` -- a reserved
    word) deserializes from the YAML key literally spelled ``class``."""

    id: str
    artifact_class: ArtifactClass
    path: str
    applies_to: AppliesTo
    rationale: str
    pin: str | None = None
    format: str | None = None
    regions: tuple[Region, ...] = ()
    since: ModelVersion | None = None
    until: ModelVersion | None = None
    legacy_of: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError(f"id must be a non-empty str, got {self.id!r}")
        object.__setattr__(self, "artifact_class", ArtifactClass(self.artifact_class))
        if not isinstance(self.path, str) or not self.path:
            raise ValueError(f"path must be a non-empty str, got {self.path!r}")
        object.__setattr__(self, "applies_to", AppliesTo(self.applies_to))
        if not isinstance(self.rationale, str) or not self.rationale:
            raise ValueError(f"rationale must be a non-empty str, got {self.rationale!r}")

        for name, value in (("pin", self.pin), ("format", self.format), ("legacy_of", self.legacy_of)):
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{name} must be a non-empty str or None, got {value!r}")

        object.__setattr__(
            self, "regions", tuple(self.regions) if isinstance(self.regions, list) else self.regions
        )
        if not isinstance(self.regions, tuple):
            raise ValueError(f"regions must be a list or tuple, got {self.regions!r}")
        for region in self.regions:
            if not isinstance(region, Region):
                raise ValueError(f"regions must contain only Region instances, got {region!r}")
        # A region's name is its identity in the `marshal-seed:*` marker
        # wire format (AD-64) -- two same-named regions give the writer two
        # conflicting spans for one marker pair, and the idempotency check
        # can no longer tell which span it owns.
        region_names = [region.name for region in self.regions]
        if len(set(region_names)) != len(region_names):
            raise ValueError(f"region names must be unique within an entry, got {region_names!r}")

        # Class-appropriate fields, both directions. Requiring a field on
        # its own class but ignoring it everywhere else is the silent
        # failure this schema exists to prevent: an author who puts
        # `regions:` on a `copied-managed` entry believes a region is
        # managed, and nothing ever tells them it is not.
        if self.artifact_class is ArtifactClass.REFERENCED:
            if not self.pin:
                raise ValueError("referenced entries require a non-empty pin")
        elif self.pin is not None:
            raise ValueError(f"pin is only valid on referenced entries, got {self.pin!r}")
        if self.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            if not self.format:
                raise ValueError("hybrid-managed-region entries require a non-empty format")
            if not self.regions:
                raise ValueError("hybrid-managed-region entries require at least one region")
        else:
            if self.format is not None:
                raise ValueError(
                    f"format is only valid on hybrid-managed-region entries, got {self.format!r}"
                )
            if self.regions:
                raise ValueError(
                    f"regions are only valid on hybrid-managed-region entries, got {self.regions!r}"
                )

        for name, value in (("since", self.since), ("until", self.until)):
            if value is not None and not isinstance(value, ModelVersion):
                raise ValueError(f"{name} must be a ModelVersion or None, got {value!r}")
        if self.since is not None and self.until is not None and not (self.since < self.until):
            raise ValueError(
                f"until ({self.until}) must be strictly greater than since ({self.since})"
            )


@dataclass(frozen=True)
class Manifest:
    """The loaded, validated, version-filtered manifest."""

    model_version: ModelVersion
    never_write: tuple[str, ...]
    entries: tuple[ManifestEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.model_version, ModelVersion):
            raise ValueError(
                f"model_version must be a ModelVersion, got {self.model_version!r}"
            )
        object.__setattr__(
            self,
            "never_write",
            tuple(self.never_write) if isinstance(self.never_write, list) else self.never_write,
        )
        if not isinstance(self.never_write, tuple) or not all(
            isinstance(item, str) for item in self.never_write
        ):
            raise ValueError(f"never_write must contain only str, got {self.never_write!r}")
        object.__setattr__(
            self, "entries", tuple(self.entries) if isinstance(self.entries, list) else self.entries
        )
        if not isinstance(self.entries, tuple):
            raise ValueError(f"entries must be a list or tuple, got {self.entries!r}")
        for entry in self.entries:
            if not isinstance(entry, ManifestEntry):
                raise ValueError(
                    f"entries must contain only ManifestEntry instances, got {entry!r}"
                )


def _build_region(raw_region: Any) -> Region:
    if not isinstance(raw_region, dict):
        raise ValueError(f"region must be a mapping, got {raw_region!r}")
    _reject_unknown_keys(raw_region, _REGION_KEYS, "region")
    # Extracted as Any, not the raw dict's own inferred `Unknown | None` --
    # these values are validated at runtime by Region.__post_init__, which
    # is the actual type boundary here; a static str/tuple annotation on a
    # YAML-sourced value pyright cannot itself prove would just be wrong.
    raw_name: Any = raw_region.get("name")
    raw_anchor: Any = raw_region.get("anchor")
    return Region(
        name=raw_name,
        anchor=tuple(raw_anchor) if isinstance(raw_anchor, list) else raw_anchor,
    )


def _parse_bound(field_name: str, raw_value: Any) -> ModelVersion | None:
    if raw_value is None:
        return None
    try:
        return ModelVersion.parse(raw_value)
    except InvalidVersionError as exc:
        # Name the bound. With both `since` and `until` present, an
        # un-prefixed message leaves the operator guessing which line to
        # edit -- and the top-level path already does this correctly
        # ("manifest: model_version: ..."), so the loader was inconsistent
        # with itself.
        raise ValueError(f"{field_name}: {exc}") from exc


def _build_entry(raw_entry: dict) -> ManifestEntry:
    _reject_unknown_keys(raw_entry, _ENTRY_KEYS, "entry")
    raw_regions = raw_entry.get("regions")
    if raw_regions is None:
        raw_regions = []
    if not isinstance(raw_regions, list):
        raise ValueError(f"regions must be a list, got {raw_regions!r}")
    regions = tuple(_build_region(raw_region) for raw_region in raw_regions)

    # Same rationale as _build_region above: ManifestEntry.__post_init__ is
    # the real type boundary, validating every one of these at runtime.
    raw_id: Any = raw_entry.get("id")
    raw_class: Any = raw_entry.get("class")
    raw_path: Any = raw_entry.get("path")
    raw_applies_to: Any = raw_entry.get("applies_to")
    raw_rationale: Any = raw_entry.get("rationale")
    return ManifestEntry(
        id=raw_id,
        artifact_class=raw_class,
        path=raw_path,
        applies_to=raw_applies_to,
        rationale=raw_rationale,
        pin=raw_entry.get("pin"),
        format=raw_entry.get("format"),
        regions=regions,
        since=_parse_bound("since", raw_entry.get("since")),
        until=_parse_bound("until", raw_entry.get("until")),
        legacy_of=raw_entry.get("legacy_of"),
    )


def load_manifest(path: Path) -> Manifest:
    """Read, validate, and version-filter one manifest YAML document.

    Raises ``ManifestError`` for every AC-listed schema violation (see the
    module docstring's two-layer explanation): an unreadable, non-UTF-8, or
    malformed-YAML file, a repeated mapping key anywhere in the document, a
    non-mapping document, an unrecognized key at any level, a malformed
    top-level ``model_version``, a ``never_write`` that is not a list of
    non-empty str, a non-list ``artifacts``, any entry-level shape
    violation (missing/wrong-type required field, an unrecognized
    ``class``, a ``hybrid-managed-region`` entry missing
    ``format``/``regions``, a ``referenced`` entry missing ``pin``, a
    ``pin``/``format``/``regions`` on a class that does not take one,
    duplicate region names within an entry, an unparseable
    ``since``/``until``, or ``until <= since``), and a duplicate ``id``
    across entries.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            # _StrictLoader is a SafeLoader subclass -- no arbitrary-object
            # construction, just SafeLoader plus duplicate-key rejection.
            raw_document = yaml.load(handle, Loader=_StrictLoader)
    except OSError as exc:
        raise ManifestError(f"manifest: could not read {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        # A ValueError, NOT an OSError -- so a manifest saved in any
        # non-UTF-8 encoding escaped the ManifestError-only contract.
        raise ManifestError(f"manifest: {path} is not valid UTF-8: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"manifest: invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw_document, dict):
        raise ManifestError(
            f"manifest: top-level document must be a mapping, got {raw_document!r}"
        )

    try:
        _reject_unknown_keys(raw_document, _DOCUMENT_KEYS, "top-level")
    except ValueError as exc:
        raise ManifestError(f"manifest: {exc}") from exc

    raw_model_version: Any = raw_document.get("model_version")
    try:
        model_version = ModelVersion.parse(raw_model_version)
    except ValueError as exc:
        # ValueError, not just InvalidVersionError: its own superclass also
        # covers the numeric components parse() cannot convert.
        raise ManifestError(f"manifest: model_version: {exc}") from exc

    raw_never_write = raw_document.get("never_write")
    if raw_never_write is None:
        raw_never_write = []
    if not isinstance(raw_never_write, list) or not all(
        isinstance(item, str) and item for item in raw_never_write
    ):
        # Non-empty, like every other string field here: an empty pattern
        # reaching S-7.3's guard could match every path.
        raise ManifestError("manifest: never_write must be a list of non-empty str")
    never_write = tuple(raw_never_write)

    raw_artifacts = raw_document.get("artifacts")
    if raw_artifacts is None:
        raw_artifacts = []
    if not isinstance(raw_artifacts, list):
        raise ManifestError("manifest: artifacts must be a list")

    seen_ids: set[str] = set()
    entries: list[ManifestEntry] = []
    for index, raw_entry in enumerate(raw_artifacts):
        if not isinstance(raw_entry, dict):
            raise ManifestError(
                f"manifest: artifacts[{index}] must be a mapping, got {raw_entry!r}"
            )
        raw_id = raw_entry.get("id")
        entry_label = raw_id if isinstance(raw_id, str) and raw_id else f"artifacts[{index}]"
        try:
            entry = _build_entry(raw_entry)
        except ValueError as exc:
            raise ManifestError(f"{entry_label}: {exc}") from exc
        if entry.id in seen_ids:
            raise ManifestError(f"{entry.id}: duplicate id")
        seen_ids.add(entry.id)
        entries.append(entry)

    filtered_entries = tuple(
        entry for entry in entries if in_range(model_version, entry.since, entry.until)
    )
    return Manifest(model_version=model_version, never_write=never_write, entries=filtered_entries)
