"""The spine — ``Component`` + ``ResolvedInventory`` (Story 1.1).

One shared model: every pipeline stage annotates the *same* objects; no stage
re-defines a parallel shape. Identity and merge logic (the Gap-B rules) live
ONLY here. Identity is ``(ecosystem, canonical_name, concrete_version)`` —
PEP-503-canonical for pypi names — and an empty-string version normalizes to
``None``. The purl is *derived*; purl comparisons must go through
``strip_purl_qualifiers`` first (non-identity qualifiers never influence
identity).

Merge policy (C0): **merge never upgrades confidence.** When two records of
the same identity disagree on a field, the merged value is the conservative
one (least-confident match level, most-degraded extraction mode, AND-ed
coverage booleans, ambiguity withheld rather than guessed), and the policy is
commutative — ``merge(a, b) == merge(b, a)`` for every field.

This module is pure data + ordering: no I/O, no subprocess, no network.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from urllib.parse import quote

from .models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)

_PEP503_RUNS = re.compile(r"[-_.]+")

# Withhold reasons the FOLD resolves (they existed only because the bare
# record had no concrete version); every other reason survives a fold.
_VERSION_DRIVEN_REASONS = frozenset(
    {WithholdReason.NO_VERSION, WithholdReason.RANGE_ONLY}
)


@dataclass(frozen=True)
class PypiIdentity:
    """A component's resolved PyPI identity (Gap-C: resolved only from
    trustworthy provenance — lock, explicit PyPI section, or the bundled map).

    An empty-string version normalizes to ``None`` at construction, so
    ``("torch", "")`` and ``("torch", None)`` are one identity."""

    name: str
    version: str | None

    def __post_init__(self) -> None:
        if self.version == "":
            object.__setattr__(self, "version", None)


@dataclass(frozen=True)
class Provenance:
    """Where a component was declared: ``(manifest, section)``."""

    manifest: str
    section: str


@dataclass(frozen=True)
class Component:
    """One dependency, frozen whole — the full 15-field contract.

    ``mapping_confidence`` carries the map's per-pair tier verbatim; the
    vocabulary is owned by Story 2.1, so it is a plain ``str | None`` here
    (only ``CveMatchLevel`` and ``WithholdReason`` are sanctioned growable
    enums).

    ``license_covered``/``currency_covered`` (Story 6.1): plain binary "was
    this axis even attempted" flags, mirroring ``hygiene_covered`` (a pure
    AND under merge/fold, NOT ``vuln_matchable``'s identity-gated formula).
    Defaultless like every other field — every construction site passes them
    explicitly. Per-component verdict data (SPDX expression, tier, ``lag``,
    ``eol_date``) lives on the ``Finding``, never here.
    """

    name: str
    version: str | None
    ecosystem: Ecosystem
    pypi_identity: PypiIdentity | None
    identity_source: IdentitySource
    mapping_confidence: str | None
    cve_match_level: CveMatchLevel
    extraction_mode: ExtractionMode
    purl: str
    provenance: tuple[Provenance, ...]
    hygiene_covered: bool
    vuln_matchable: bool
    license_covered: bool
    currency_covered: bool
    indeterminate_reason: WithholdReason | None

    def __post_init__(self) -> None:
        # Closed enums coerce (a raw string either resolves to a member or
        # fails loud at construction); the two GROWABLE enums
        # (cve_match_level, indeterminate_reason) are deliberately NOT
        # coerced — an unknown future token must degrade downstream
        # (match_level_rung -> indeterminate), never raise here.
        object.__setattr__(self, "ecosystem", Ecosystem(self.ecosystem))
        object.__setattr__(
            self, "identity_source", IdentitySource(self.identity_source)
        )
        object.__setattr__(
            self, "extraction_mode", ExtractionMode(self.extraction_mode)
        )
        if not self.name:
            raise ValueError("Component.name must be a non-empty string")
        if self.version == "":
            object.__setattr__(self, "version", None)
        if self.vuln_matchable and (
            self.pypi_identity is None or self.version is None
        ):
            raise ValueError(
                "vuln_matchable=True requires a resolved pypi_identity AND a "
                "concrete version (the Gap-C predicate) — got "
                f"pypi_identity={self.pypi_identity!r}, version={self.version!r}"
            )
        if self.vuln_matchable and self.indeterminate_reason is not None:
            raise ValueError(
                "vuln_matchable=True contradicts indeterminate_reason="
                f"{self.indeterminate_reason!r} (the reason says this component "
                "was withheld from vuln matching)"
            )
        if self.cve_match_level == CveMatchLevel.EXACT and self.version is None:
            raise ValueError(
                "cve_match_level 'exact' claims an exact-version match but "
                "version is None"
            )


def canonical_name(ecosystem: Ecosystem, name: str) -> str:
    """Canonical identity spelling for a component name.

    * ``pypi`` — PEP 503 normalization: runs of ``-``, ``_``, ``.`` collapse
      to a single ``-`` and the result is lowercased (``Django`` ==
      ``django``; ``typing_extensions`` == ``typing-extensions``).
    * ``conda`` — returned unchanged (conda package names are already
      canonical in the channel index).
    """
    if ecosystem is Ecosystem.PYPI:
        return _PEP503_RUNS.sub("-", name).lower()
    return name


def identity(component: Component) -> tuple[Ecosystem, str, str | None]:
    """The merge key: ``(ecosystem, canonical_name, concrete_version)``.

    Field-derived, so purl qualifiers can never influence identity (compare
    purls only through ``strip_purl_qualifiers``). The name key is
    PEP-503-canonical for pypi; an empty-string version normalizes to
    ``None`` (a bare, version-less record).
    """
    version = component.version if component.version else None
    return (
        component.ecosystem,
        canonical_name(component.ecosystem, component.name),
        version,
    )


def derive_purl(ecosystem: Ecosystem, name: str, version: str | None) -> str:
    """Derive the canonical purl (no qualifiers): ``pkg:<eco>/<name>[@<version>]``.

    The purl name is the ecosystem's canonical purl form — pypi: PEP 503
    (runs of ``-_.`` -> ``-``, lowercased); conda: VERBATIM (conda names are
    already canonical in the channel index, and mutating them can name a
    DIFFERENT real package — ``typing_extensions`` and ``typing-extensions``
    are distinct conda-forge packages; external conda purl producers, incl.
    this repo's cfe-purls, use the name verbatim). Name and version segments
    are percent-encoded per the purl spec, so a malformed (RAW_MALFORMED)
    name can never smuggle a ``@``/``?``/``#``/``/`` into the purl syntax. A
    ``None`` or empty-string version omits the ``@<version>`` suffix.
    Comparisons against externally-sourced purls must go through
    ``strip_purl_qualifiers`` first.
    """
    if ecosystem is Ecosystem.PYPI:
        purl_name = _PEP503_RUNS.sub("-", name).lower()
    else:
        purl_name = name
    purl_name = quote(purl_name, safe="")
    if not version:
        return f"pkg:{ecosystem.value}/{purl_name}"
    return f"pkg:{ecosystem.value}/{purl_name}@{quote(version, safe='')}"


def strip_purl_qualifiers(purl: str) -> str:
    """Strip non-identity qualifiers (``?...``) and subpath (``#...``) before
    any purl comparison — raw purls are never compared directly."""
    return purl.split("?", 1)[0].split("#", 1)[0]


# Confidence order for CVE-match levels (higher = more confident). A future,
# unrecognized level ranks below every known one — merging with it can only
# degrade, never upgrade (C0). Ties among unknowns break lexicographically.
_CVE_MATCH_CONFIDENCE: dict[CveMatchLevel, int] = {
    CveMatchLevel.EXACT: 2,
    CveMatchLevel.NAME_ONLY: 1,
    CveMatchLevel.NONE: 0,
}

# Degradation ladder for extraction modes (higher = more degraded); the
# most-degraded mode survives a merge. Closed enum — total by construction.
_EXTRACTION_DEGRADATION: dict[ExtractionMode, int] = {
    ExtractionMode.PARSED: 0,
    ExtractionMode.UNION_MARKED: 1,
    ExtractionMode.NAME_ONLY: 2,
    ExtractionMode.RAW_MALFORMED: 3,
}

# Trust order for identity sources (higher = more trustworthy); when two
# records agree on the resolved identity but disagree on where it came from,
# the LEAST trustworthy source survives — merge never upgrades confidence.
_IDENTITY_SOURCE_TRUST: dict[IdentitySource, int] = {
    IdentitySource.NATIVE: 4,
    IdentitySource.LOCK: 3,
    IdentitySource.PYPI_SECTION: 2,
    IdentitySource.MAP: 1,
    IdentitySource.NONE: 0,
}


def merge_components(components: Iterable[Component]) -> tuple[Component, ...]:
    """Apply the Gap-B merge rules; deterministic output ordering.

    * Same identity (any manifests/sections) → ONE component, provenance
      union, non-provenance conflicts resolved by the conservative policy of
      ``_merge_group`` — **merge never upgrades confidence** (C0). The merge
      is computed over the full same-identity GROUP with order-independent
      reducers (set/min/max/AND), so it is commutative AND associative:
      ``merge(a, b) == merge(b, a)`` always, and no feed order of three or
      more records can resurrect withheld information.
    * Bare ``(name, None)`` folds into a concrete version ONLY when exactly one
      concrete version of the same ``(ecosystem, name)`` exists; with zero or
      ≥2 concrete versions it stays a distinct indeterminate component — never
      guess-attribute a version. The fold resolves ONLY the bare record's
      version-driven deficiencies; every non-version-driven signal merges as
      conservatively as a same-identity merge (see ``_fold_bare``).
    * Distinct versions of the same ``(ecosystem, name)`` stay distinct (honest
      count inflation, stated).
    """
    grouped: dict[tuple[Ecosystem, str, str | None], list[Component]] = {}
    for component in components:
        grouped.setdefault(identity(component), []).append(component)
    merged: dict[tuple[Ecosystem, str, str | None], Component] = {
        key: _merge_group(group) for key, group in grouped.items()
    }

    result: dict[tuple[Ecosystem, str, str | None], Component] = {}
    for key, component in merged.items():
        ecosystem, name, version = key
        if version is None:
            concrete_keys = [
                k
                for k in merged
                if k[0] is ecosystem and k[1] == name and k[2] is not None
            ]
            if len(concrete_keys) == 1:
                target = concrete_keys[0]
                # Folded into the sole concrete version below (when reached).
                folded = result.get(target, merged[target])
                result[target] = _fold_bare(folded, component)
                continue
        existing = result.get(key)
        if existing is not None:
            # The bare entry already folded provenance into this key.
            result[key] = replace(
                existing,
                provenance=_union_provenance(existing.provenance, component.provenance),
            )
        else:
            result[key] = component

    return tuple(
        sorted(
            result.values(),
            key=lambda c: (c.ecosystem.value, c.name, c.version is not None, c.version or ""),
        )
    )


def _merge_group(group: list[Component]) -> Component:
    """Merge ALL records of the SAME identity — conservative and
    feed-order independent (every reducer is a set/min/max/AND over the whole
    group, so the result is commutative AND associative; a pairwise fold
    could let a later record resurrect information an earlier conflict had
    withheld).

    **Merge never upgrades confidence** (C0):

    * ``provenance`` — union (sorted, deduplicated).
    * ``name`` — the canonical spelling when the spellings differ.
    * ``purl`` — if the inputs differ, re-derived from the merged identity
      (which also strips any qualifiers).
    * ``cve_match_level`` — the LEAST confident present
      (``exact`` > ``name-only`` > ``none`` > any unrecognized future value;
      ties among unknowns break to the lexicographically-smallest token).
    * ``vuln_matchable`` / ``hygiene_covered`` — logical AND.
    * ``indeterminate_reason`` — any non-None value wins over None; multiple
      differing non-None values keep the lexicographically-smallest token
      (determinism, not semantics).
    * ``extraction_mode`` — the most degraded on the ladder
      ``parsed < union-marked < name-only < raw-malformed``.
    * ``pypi_identity`` — two or more identities DISTINCT after
      canonicalization (PEP-503 name, ``""``→``None`` version) → ``None``
      with ``identity_source=none``, ``mapping_confidence=None``,
      ``vuln_matchable=False``, and ``indeterminate_reason``
      ``ambiguous-identity`` (ambiguity is withheld, never guessed — and a
      component whose identity was just withheld can never stay matchable,
      the Gap-C predicate); exactly one canonical identity → kept in its
      canonical spelling, with the LEAST trustworthy ``identity_source``
      among the records carrying it and their unanimous
      ``mapping_confidence`` (else ``None`` — the vocabulary is owned by
      Story 2.1 and cannot be ranked here).
    """
    if len(group) == 1:
        # Singletons are already normalized: Component.__post_init__ owns the
        # ""->None version normalization, so no group-path divergence exists.
        return group[0]
    first = group[0]
    ecosystem = first.ecosystem
    version = first.version if first.version else None
    names = {component.name for component in group}
    name = first.name if len(names) == 1 else canonical_name(ecosystem, first.name)
    purls = {component.purl for component in group}
    purl = first.purl if len(purls) == 1 else derive_purl(ecosystem, name, version)
    (
        pypi_identity,
        identity_source,
        mapping_confidence,
        identity_withheld,
    ) = _merge_group_pypi_identity(group)
    reason_set = {
        component.indeterminate_reason
        for component in group
        if component.indeterminate_reason is not None
    }
    if identity_withheld:
        reason_set.add(WithholdReason.AMBIGUOUS_IDENTITY)
    reasons = sorted(reason_set, key=str)
    # Gap-C: no resolved identity, no vuln matching — a withheld identity can
    # never leave the merged record matchable.
    vuln_matchable = (
        all(component.vuln_matchable for component in group)
        and pypi_identity is not None
    )
    provenance_union = {
        entry for component in group for entry in component.provenance
    }
    return Component(
        name=name,
        version=version,
        ecosystem=ecosystem,
        pypi_identity=pypi_identity,
        identity_source=identity_source,
        mapping_confidence=mapping_confidence,
        cve_match_level=min(
            (component.cve_match_level for component in group),
            key=lambda level: (_CVE_MATCH_CONFIDENCE.get(level, -1), str(level)),
        ),
        extraction_mode=max(
            (component.extraction_mode for component in group),
            key=_EXTRACTION_DEGRADATION.__getitem__,
        ),
        purl=purl,
        provenance=tuple(
            sorted(provenance_union, key=lambda p: (p.manifest, p.section))
        ),
        hygiene_covered=all(component.hygiene_covered for component in group),
        vuln_matchable=vuln_matchable,
        license_covered=all(component.license_covered for component in group),
        currency_covered=all(component.currency_covered for component in group),
        indeterminate_reason=reasons[0] if reasons else None,
    )


def _canonical_identity_key(pypi_identity: PypiIdentity) -> tuple[str, str | None]:
    """Canonical comparison key for a PyPI identity: PEP-503-canonical name +
    ``""``→``None``-normalized version — ``PyYAML`` vs ``pyyaml`` is ONE
    identity, never a false ambiguity."""
    return (
        _PEP503_RUNS.sub("-", pypi_identity.name).lower(),
        pypi_identity.version if pypi_identity.version else None,
    )


def _merge_group_pypi_identity(
    group: list[Component],
) -> tuple[PypiIdentity | None, IdentitySource, str | None, bool]:
    """Resolve the group's PyPI identity; the fourth element reports whether
    ambiguity forced a withhold (the caller must degrade matchability)."""
    by_key = {
        _canonical_identity_key(component.pypi_identity): component.pypi_identity
        for component in group
        if component.pypi_identity is not None
    }
    if len(by_key) > 1:
        # Distinct resolved identities: ambiguity is withheld, never guessed.
        return (None, IdentitySource.NONE, None, True)
    if len(by_key) == 1:
        key = next(iter(by_key))
        # Keep the canonical spelling (identity IS canonical; deterministic
        # regardless of which raw spelling was fed).
        resolved = PypiIdentity(name=key[0], version=key[1])
        carriers = [c for c in group if c.pypi_identity is not None]
    else:
        resolved = None
        carriers = group
    source = min(
        (component.identity_source for component in carriers),
        key=_IDENTITY_SOURCE_TRUST.__getitem__,
    )
    confidences = {component.mapping_confidence for component in carriers}
    confidence = next(iter(confidences)) if len(confidences) == 1 else None
    return (resolved, source, confidence, False)


def _fold_bare(concrete: Component, bare: Component) -> Component:
    """Fold a bare (version-less) record into the sole concrete version.

    The fold resolves ONLY the bare record's version-driven deficiencies —
    the missing version itself, its ``no-version``/``range-only``
    withholding, and the unmatchability/weak match level they caused. Every
    non-version-driven signal merges as conservatively as a same-identity
    merge (C0: a fold never upgrades confidence):

    * ``provenance`` — union.
    * ``hygiene_covered`` / ``license_covered`` / ``currency_covered`` — AND
      (a bare record an axis never covered stays uncovered after the fold).
    * ``extraction_mode`` — the most degraded of the two.
    * ``pypi_identity`` — a bare-side identity whose canonical pypi NAME
      conflicts with the concrete side's is withheld exactly like a
      same-identity conflict (``None``/``none``/``None`` +
      ``vuln_matchable=False`` + ``ambiguous-identity``); an absent or
      name-agreeing bare identity keeps the concrete side's.
    * ``indeterminate_reason`` — the bare side's version-driven reasons
      (``no-version``, ``range-only``) are resolved by the fold and dropped;
      any other surviving reason forces ``vuln_matchable=False`` (smallest
      token wins for determinism).
    """
    hygiene_covered = concrete.hygiene_covered and bare.hygiene_covered
    license_covered = concrete.license_covered and bare.license_covered
    currency_covered = concrete.currency_covered and bare.currency_covered
    extraction_mode = max(
        (concrete.extraction_mode, bare.extraction_mode),
        key=_EXTRACTION_DEGRADATION.__getitem__,
    )
    pypi_identity = concrete.pypi_identity
    identity_source = concrete.identity_source
    mapping_confidence = concrete.mapping_confidence
    vuln_matchable = concrete.vuln_matchable
    reason_set: set[WithholdReason] = set()
    if concrete.indeterminate_reason is not None:
        reason_set.add(concrete.indeterminate_reason)
    if (
        bare.indeterminate_reason is not None
        and bare.indeterminate_reason not in _VERSION_DRIVEN_REASONS
    ):
        reason_set.add(bare.indeterminate_reason)
    if (
        bare.pypi_identity is not None
        and concrete.pypi_identity is not None
        and _canonical_identity_key(bare.pypi_identity)[0]
        != _canonical_identity_key(concrete.pypi_identity)[0]
    ):
        pypi_identity = None
        identity_source = IdentitySource.NONE
        mapping_confidence = None
        vuln_matchable = False
        reason_set.add(WithholdReason.AMBIGUOUS_IDENTITY)
    if reason_set:
        vuln_matchable = False
    return replace(
        concrete,
        pypi_identity=pypi_identity,
        identity_source=identity_source,
        mapping_confidence=mapping_confidence,
        hygiene_covered=hygiene_covered,
        vuln_matchable=vuln_matchable,
        license_covered=license_covered,
        currency_covered=currency_covered,
        extraction_mode=extraction_mode,
        indeterminate_reason=min(reason_set, key=str) if reason_set else None,
        provenance=_union_provenance(concrete.provenance, bare.provenance),
    )


def _union_provenance(
    first: tuple[Provenance, ...], second: tuple[Provenance, ...]
) -> tuple[Provenance, ...]:
    seen: list[Provenance] = []
    for entry in (*first, *second):
        if entry not in seen:
            seen.append(entry)
    return tuple(sorted(seen, key=lambda p: (p.manifest, p.section)))


@dataclass(frozen=True)
class ResolvedInventory:
    """The single cross-stage object: post-merge components + the resolved
    scan set. The root project never enters the inventory (it is the SBOM's
    ``metadata.component``, not a dependency).

    The inventory is post-merge BY CONTRACT: two components sharing an
    ``identity()`` is a construction error (feed them through
    ``merge_components`` first).
    """

    components: tuple[Component, ...]
    resolved_scan_set: tuple[ScannedManifest, ...]

    def __post_init__(self) -> None:
        seen: set[tuple[Ecosystem, str, str | None]] = set()
        for component in self.components:
            key = identity(component)
            if key in seen:
                raise ValueError(
                    f"duplicate component identity {key!r}: ResolvedInventory "
                    "is post-merge by contract — run merge_components first"
                )
            seen.add(key)

    @property
    def count(self) -> int:
        """Post-merge component count (``report.inventory_count`` source)."""
        return len(self.components)
