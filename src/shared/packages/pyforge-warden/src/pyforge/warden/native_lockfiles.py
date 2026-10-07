"""Non-Python lockfiles delegated to osv-scanner (Story 16.4, CAP-26).

This module lives OUTSIDE ``extract/`` — osv-scanner owns parsing; Warden
only discovers lockfile paths, invokes ``-L <parser>:<path>``, and maps the
JSON ``results[].packages[]`` shape into ``Component`` rows + ``vuln:``
findings. No manifest parsing and no execution primitives here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .inventory import Component, Provenance, derive_purl
from .models import (
    AXIS_VULNERABILITY,
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
)
from .vuln import (
    DB_MAX_AGE_DAYS,
    OsvParse,
    db_snapshot_at,
    db_zip_path,
    ecosystem_db_unavailable_finding,
    is_db_stale,
    offline_db_unavailable_finding,
    parse_osv_output,
    resolve_cache_dir,
    stale_vuln_data_finding,
)
from .vuln import _db_has_valid_advisory as db_has_valid_advisory

NON_PYTHON_ECOSYSTEMS_FLAG = "pyforge.warden.non_python_ecosystems"

PACKAGE_LOCK_KIND = "package-lock.json"
YARN_LOCK_KIND = "yarn.lock"
PNPM_LOCK_KIND = "pnpm-lock.yaml"
GO_MOD_KIND = "go.mod"
GO_SUM_KIND = "go.sum"
CARGO_LOCK_KIND = "Cargo.lock"
GEMFILE_LOCK_KIND = "Gemfile.lock"
COMPOSER_LOCK_KIND = "composer.lock"

NATIVE_LOCKFILE_KINDS: tuple[str, ...] = (
    PACKAGE_LOCK_KIND,
    YARN_LOCK_KIND,
    PNPM_LOCK_KIND,
    GO_MOD_KIND,
    GO_SUM_KIND,
    CARGO_LOCK_KIND,
    GEMFILE_LOCK_KIND,
    COMPOSER_LOCK_KIND,
)

_NATIVE_SECTION = "lockfile"

# osv-scanner 2.4.0 / osv-scalibr 0.4.5 parser ids (``-L <parser>:<path>``).
_PARSER_ID: dict[str, str] = {
    PACKAGE_LOCK_KIND: PACKAGE_LOCK_KIND,
    YARN_LOCK_KIND: YARN_LOCK_KIND,
    PNPM_LOCK_KIND: PNPM_LOCK_KIND,
    GO_MOD_KIND: GO_MOD_KIND,
    GO_SUM_KIND: GO_MOD_KIND,  # go.sum has no dedicated parser in 2.4.0; sibling go.mod path
    CARGO_LOCK_KIND: CARGO_LOCK_KIND,
    GEMFILE_LOCK_KIND: GEMFILE_LOCK_KIND,
    COMPOSER_LOCK_KIND: COMPOSER_LOCK_KIND,
}

# Map manifest kind -> Warden ``Ecosystem`` (inventory + purl type).
_KIND_ECOSYSTEM: dict[str, Ecosystem] = {
    PACKAGE_LOCK_KIND: Ecosystem.NPM,
    YARN_LOCK_KIND: Ecosystem.NPM,
    PNPM_LOCK_KIND: Ecosystem.NPM,
    GO_MOD_KIND: Ecosystem.GO,
    GO_SUM_KIND: Ecosystem.GO,
    CARGO_LOCK_KIND: Ecosystem.CRATES_IO,
    GEMFILE_LOCK_KIND: Ecosystem.RUBYGEMS,
    COMPOSER_LOCK_KIND: Ecosystem.PACKAGIST,
}

# osv-scanner JSON ``package.ecosystem`` string -> Warden ``Ecosystem``.
_OSV_ECOSYSTEM_TO_ENUM: dict[str, Ecosystem] = {
    "npm": Ecosystem.NPM,
    "Go": Ecosystem.GO,
    "crates.io": Ecosystem.CRATES_IO,
    "RubyGems": Ecosystem.RUBYGEMS,
    "Packagist": Ecosystem.PACKAGIST,
    "PyPI": Ecosystem.PYPI,
}


def is_native_lockfile_kind(kind: str) -> bool:
    return kind in _PARSER_ID


def osv_ecosystem_for_kind(kind: str) -> Ecosystem:
    return _KIND_ECOSYSTEM[kind]


def is_non_python_native_ecosystem(ecosystem: Ecosystem) -> bool:
    """Components whose hygiene/license/currency axes are honestly N/A."""
    return ecosystem not in (Ecosystem.PYPI, Ecosystem.CONDA)


@dataclass(frozen=True)
class NativeLockfileScan:
    """One osv-scanner lockfile invocation's outcome (components + vuln axis)."""

    components: tuple[Component, ...]
    parse: OsvParse
    ecosystem: Ecosystem
    db_consulted: bool
    db_zip: Path | None
    snapshot_at: str | None


def _lockfile_scan_path(target: Path, manifest: ScannedManifest) -> Path:
    if manifest.kind == GO_SUM_KIND:
        sibling = target / manifest.path
        parent = sibling.parent
        go_mod = parent / GO_MOD_KIND
        if go_mod.is_file():
            return go_mod
    return target / manifest.path


def _components_from_osv_document(
    document: object,
    *,
    manifest_path: str,
    default_ecosystem: Ecosystem,
) -> tuple[Component, ...]:
    if not isinstance(document, dict):
        return ()
    results = document.get("results")
    if not isinstance(results, list):
        return ()
    provenance = (Provenance(manifest=manifest_path, section=_NATIVE_SECTION),)
    by_identity: dict[tuple[Ecosystem, str, str | None], Component] = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        packages = result.get("packages")
        if not isinstance(packages, list):
            continue
        for package_entry in packages:
            if not isinstance(package_entry, dict):
                continue
            package = package_entry.get("package")
            if not isinstance(package, dict):
                continue
            name = package.get("name")
            if not isinstance(name, str) or not name:
                continue
            version_raw = package.get("version")
            version = version_raw if isinstance(version_raw, str) and version_raw else None
            eco_raw = package.get("ecosystem")
            ecosystem = default_ecosystem
            if isinstance(eco_raw, str) and eco_raw in _OSV_ECOSYSTEM_TO_ENUM:
                ecosystem = _OSV_ECOSYSTEM_TO_ENUM[eco_raw]
            key = (ecosystem, name, version)
            if key in by_identity:
                continue
            by_identity[key] = Component(
                name=name,
                version=version,
                ecosystem=ecosystem,
                pypi_identity=None,
                identity_source=IdentitySource.LOCK,
                mapping_confidence=None,
                cve_match_level=CveMatchLevel.EXACT if version else CveMatchLevel.NAME_ONLY,
                extraction_mode=ExtractionMode.PARSED,
                purl=derive_purl(ecosystem, name, version),
                provenance=provenance,
                hygiene_covered=False,
                vuln_matchable=version is not None,
                license_covered=False,
                currency_covered=False,
                indeterminate_reason=None,
            )
    return tuple(
        sorted(
            by_identity.values(),
            key=lambda c: (c.ecosystem.value, c.name, c.version or ""),
        )
    )


def scan_native_lockfile(target: Path, manifest: ScannedManifest) -> NativeLockfileScan:
    """Run osv-scanner on one native lockfile (subprocess owned by ``engines``)."""
    from .engines import (
        _OSV_SCANNER_VERSION_PATTERN,
        OSV_SCANNER_VERSION_RANGE,
        OSV_TIMEOUT_SECONDS,
        _check_engine_version,
        _engine_env,
    )

    kind = manifest.kind
    ecosystem = osv_ecosystem_for_kind(kind)
    lock_path = _lockfile_scan_path(target, manifest)
    parser_id = _PARSER_ID[kind]
    cache_dir = resolve_cache_dir()
    zip_path = db_zip_path(cache_dir, ecosystem) if cache_dir is not None else None
    db_ok = zip_path is not None and db_has_valid_advisory(zip_path, ecosystem)
    snapshot_at = db_snapshot_at(zip_path) if db_ok and zip_path is not None else None
    stale = db_ok and snapshot_at is not None and is_db_stale(snapshot_at, DB_MAX_AGE_DAYS, now=datetime.now(UTC))
    stale_findings = (stale_vuln_data_finding(),) if stale else ()

    if cache_dir is None or not db_ok:
        withheld = (ecosystem_db_unavailable_finding(ecosystem),)
        return NativeLockfileScan(
            components=(),
            parse=OsvParse(findings=withheld, errors=()),
            ecosystem=ecosystem,
            db_consulted=False,
            db_zip=None,
            snapshot_at=None,
        )

    version_error = _check_engine_version(
        owner="osv-scanner",
        argv=["osv-scanner", "--version"],
        version_pattern=_OSV_SCANNER_VERSION_PATTERN,
        expected=OSV_SCANNER_VERSION_RANGE,
        cwd=target,
    )
    if version_error is not None:
        return NativeLockfileScan(
            components=(),
            parse=OsvParse(findings=(), errors=(version_error,)),
            ecosystem=ecosystem,
            db_consulted=False,
            db_zip=zip_path,
            snapshot_at=snapshot_at,
        )

    text, error, exit_code = _engine_env(
        lambda output_path: [
            "osv-scanner",
            "scan",
            "--offline",
            "--format",
            "json",
            "--output-file",
            output_path,
            "-L",
            f"{parser_id}:{lock_path}",
        ],
        owner="osv-scanner",
        cwd=target,
        timeout=OSV_TIMEOUT_SECONDS,
        extra_env={"OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": cache_dir},
    )
    if error is not None:
        return NativeLockfileScan(
            components=(),
            parse=OsvParse(findings=(), errors=(error,)),
            ecosystem=ecosystem,
            db_consulted=True,
            db_zip=zip_path,
            snapshot_at=snapshot_at,
        )

    raw = text or ""
    parse = parse_osv_output(raw)
    findings = parse.findings
    if stale_findings:
        findings = tuple(sorted((*findings, *stale_findings), key=lambda f: f.id))
    if exit_code == 128:
        try:
            exit128_document = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            exit128_document = {}
        findings = tuple(
            sorted(
                (
                    *findings,
                    *tuple(
                        offline_db_unavailable_finding(c)
                        for c in _components_from_osv_document(
                            exit128_document,
                            manifest_path=manifest.path,
                            default_ecosystem=ecosystem,
                        )
                    ),
                ),
                key=lambda f: f.id,
            )
        )
    elif exit_code not in (0, 1, 127):
        from .models import ErrorKind, ErrorRecord

        parse = OsvParse(
            findings=findings,
            errors=(
                *parse.errors,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                    owner="osv-scanner",
                    message=f"osv-scanner exited with unexpected code {exit_code} on {manifest.path!r}",
                ),
            ),
        )

    try:
        document = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        document = {}
    components = _components_from_osv_document(
        document,
        manifest_path=manifest.path,
        default_ecosystem=ecosystem,
    )
    if exit_code == 127 and not components:
        findings = tuple(
            sorted(
                (*findings, ecosystem_db_unavailable_finding(ecosystem)),
                key=lambda f: f.id,
            )
        )
    elif exit_code == 127:
        findings = tuple(
            sorted(
                (
                    *findings,
                    *tuple(offline_db_unavailable_finding(c) for c in components),
                ),
                key=lambda f: f.id,
            )
        )

    return NativeLockfileScan(
        components=components,
        parse=OsvParse(findings=findings, errors=parse.errors, kev_candidates=parse.kev_candidates),
        ecosystem=ecosystem,
        db_consulted=True,
        db_zip=zip_path,
        snapshot_at=snapshot_at,
    )


def inventory_count_for_axis(inventory_components: tuple[Component, ...], axis: str) -> int:
    """Per-axis denominator: Python-scoped deps only on non-vuln axes."""

    if axis == AXIS_VULNERABILITY:
        return len(inventory_components)
    return sum(1 for c in inventory_components if not is_non_python_native_ecosystem(c.ecosystem))


def merge_native_scans_into_vuln_result(
    result: object,
    native_scans: tuple[NativeLockfileScan, ...],
    *,
    inventory_count: int,
) -> object:
    """Merge pre-scanned native lockfile outcomes into ``OsvEngine``'s result."""
    from .engines import EngineResult
    from .interfaces import AxisCoverage, VulnData
    from .models import ResolutionDepth

    if not native_scans:
        return result
    assert isinstance(result, EngineResult)
    native_findings: list = []
    native_errors: list = []
    native_assessed = 0
    vuln_data = result.vuln_data
    for scan in native_scans:
        native_findings.extend(scan.parse.findings)
        native_errors.extend(scan.parse.errors)
        native_assessed += sum(1 for c in scan.components if c.vuln_matchable)
        if scan.db_consulted and scan.db_zip is not None:
            native_max_age_ok = True
            if scan.snapshot_at is not None:
                native_max_age_ok = not is_db_stale(scan.snapshot_at, DB_MAX_AGE_DAYS, now=datetime.now(UTC))
            prior_ok = result.vuln_data.max_age_ok if result.vuln_data else True
            vuln_data = VulnData(
                source=str(scan.db_zip),
                snapshot_at=scan.snapshot_at,
                max_age_ok=prior_ok and native_max_age_ok,
            )
    findings = tuple(
        sorted(
            {f.id: f for f in (*result.findings, *native_findings)}.values(),
            key=lambda f: f.id,
        )
    )
    errors = tuple([*result.errors, *native_errors])
    existing_coverage = result.coverage[0] if result.coverage else None
    deps_assessed = (existing_coverage.deps_assessed if existing_coverage else 0) + native_assessed
    coverage = (
        AxisCoverage(
            axis=AXIS_VULNERABILITY,
            manifests_found=existing_coverage.manifests_found if existing_coverage else 0,
            manifests_parsed=existing_coverage.manifests_parsed if existing_coverage else 0,
            deps_total=inventory_count,
            deps_assessed=min(deps_assessed, inventory_count),
            resolution_depth=ResolutionDepth.LOCKED_CLOSURE.value,
        ),
    )
    return EngineResult(
        findings=findings,
        errors=errors,
        coverage=coverage,
        axis=result.axis,
        vuln_data=vuln_data,
        kev_data=result.kev_data,
        epss_data=result.epss_data,
        fixed_versions=result.fixed_versions,
    )
