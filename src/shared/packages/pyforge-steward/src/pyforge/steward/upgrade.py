"""Steward's ``upgrade`` duty — BMAD-METHOD core upgrade surfaces (Epic 14).

Story 14.1 / CAP-1: report-only pre-flight for a target bmad-method release.
Never applies, never mutates ``_bmad/`` or custom surfaces. Apply lands in
Story 14.2+.

Verb naming (SPEC open question): a dedicated ``steward upgrade bmad-core``
duty — not an extension of ``provision`` — because Epic 14's later CAPs
(apply, reconcile, pin fan-out, verify) share this surface and must not
crowd Epic 3's environment/module provisioning flags.

Detection of ambient "you're behind" stays doctor's
(``bmad-method-version-drift``); this module is the deliberate pre-flight
report an operator runs before apply.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from .interfaces import DutyResult

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_MANIFEST_RELATIVE_PATH = Path("_bmad/_config/manifest.yaml")
_CUSTOM_RELATIVE_PATH = Path("_bmad/custom")
_SKILL_MANIFEST_RELATIVE_PATH = Path("_bmad/_config/skill-manifest.csv")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Trap IDs from failure-modes.md that CAP-1 must retrodict for 6.10→6.11.
TRAP_LOCAL_MOD = 1
TRAP_LEGACY_CUSTOM = 2
TRAP_REMOVALS = 3
TRAP_PREREQUISITES = 4
TRAP_FORWARDER = 9
TRAP_CONFIG_MIGRATION = 11


class UpgradeError(RuntimeError):
    """A pre-flight request failed in a duty-level (ok=False) way."""


def repo_root() -> Path:
    """Return the local-recipes checkout root (same marker as provision)."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return candidate
    raise UpgradeError(
        "cannot locate repo root (scripts/bmad-loop-worktree not found walking up)"
    )


@dataclass(frozen=True)
class SkillChange:
    """One skill add / remove / rename the target release would introduce."""

    kind: str  # add | remove | rename
    name: str
    to: str | None = None
    shim_disposition: str | None = None
    source: str = "catalog"  # catalog | removals.txt


@dataclass(frozen=True)
class LocalModFinding:
    """An upstream-touched path the repo has locally customized."""

    path: str
    reason: str
    trap_id: int = TRAP_LOCAL_MOD


@dataclass(frozen=True)
class LegacyCustomFinding:
    """A ``_bmad/custom/**`` override that would halt a deprecation shim."""

    path: str
    legacy_name: str
    successor: str | None
    trap_id: int = TRAP_LEGACY_CUSTOM


@dataclass(frozen=True)
class PrerequisiteFinding:
    """A hard prerequisite the target release introduces."""

    name: str
    severity: str
    notes: str
    min_version: str | None = None
    trap_id: int = TRAP_PREREQUISITES


@dataclass(frozen=True)
class ForwarderFinding:
    """Upstream forwarder / orchestrator contract change (trap 9)."""

    skill: str
    forwards_to: str | None
    notes: str
    suite_min_versions: dict[str, str] = field(default_factory=dict)
    trap_id: int = TRAP_FORWARDER


@dataclass(frozen=True)
class ConfigMigrationFinding:
    """Staged config-format migration warning (trap 11)."""

    status: str
    notes: str
    trap_id: int = TRAP_CONFIG_MIGRATION


@dataclass(frozen=True)
class PreflightReport:
    """Report-only upgrade pre-flight — never applied."""

    installed_version: str
    target_version: str
    skill_changes: tuple[SkillChange, ...]
    removals: tuple[str, ...]
    locally_modified: tuple[LocalModFinding, ...]
    legacy_custom: tuple[LegacyCustomFinding, ...]
    hard_prerequisites: tuple[PrerequisiteFinding, ...]
    forwarder_changes: tuple[ForwarderFinding, ...]
    config_migration: ConfigMigrationFinding | None
    trap_ids: tuple[int, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def catalog_dir() -> Path:
    """Packaged release-catalog directory (importlib.resources when installed)."""
    try:
        root = resources.files("pyforge.steward.data.bmad_core_releases")
        # Traversable → Path when on a real filesystem; fixtures use Path.
        as_path = Path(str(root))
        if as_path.is_dir():
            return as_path
    except (TypeError, ModuleNotFoundError, AttributeError):
        pass
    return Path(__file__).resolve().parent / "data" / "bmad_core_releases"


def load_release_catalog(version: str, *, directory: Path | None = None) -> dict[str, Any]:
    """Load the curated catalog for *version* (``X.Y.Z.yaml``)."""
    if not _VERSION_RE.match(version):
        raise UpgradeError(f"target version must be X.Y.Z, got {version!r}")
    base = directory or catalog_dir()
    path = base / f"{version}.yaml"
    if not path.is_file():
        raise UpgradeError(
            f"no release catalog for {version} at {path} "
            "(Story 14.1 ships curated catalogs; unknown targets need a catalog entry)"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise UpgradeError(f"release catalog {path} is not a mapping")
    if str(data.get("version", "")) != version:
        raise UpgradeError(
            f"catalog version mismatch: file declares {data.get('version')!r}, "
            f"expected {version!r}"
        )
    return data


def read_installed_version(repo: Path) -> str:
    """``installation.version`` from ``_bmad/_config/manifest.yaml``."""
    manifest = repo / _MANIFEST_RELATIVE_PATH
    if not manifest.is_file():
        raise UpgradeError(f"missing installed manifest: {manifest}")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    version = (data.get("installation") or {}).get("version")
    if not version or not isinstance(version, str):
        raise UpgradeError(f"manifest lacks installation.version: {manifest}")
    return version.strip()


def _read_installed_skill_names(repo: Path) -> set[str]:
    """Skill names from the installed skill-manifest.csv (canonicalId column)."""
    path = repo / _SKILL_MANIFEST_RELATIVE_PATH
    if not path.is_file():
        return set()
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("canonicalId") or line.startswith("#"):
            continue
        # CSV: "canonicalId","name",...
        if line.startswith('"'):
            parts = [p.strip().strip('"') for p in line.split(",")]
            if parts:
                names.add(parts[0])
        else:
            names.add(line.split(",")[0].strip())
    return names


def _parse_removals_txt(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line.split()[0])
    return out


def load_package_version(package_root: Path) -> str | None:
    """Read ``package.json`` ``version`` from an unpacked bmad-method tree."""
    path = package_root / "package.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    version = data.get("version")
    return str(version).strip() if version else None


def load_package_removals(package_root: Path) -> list[str]:
    """Read the target package's ``removals.txt`` when a package root is supplied."""
    path = package_root / "removals.txt"
    if not path.is_file():
        return []
    return _parse_removals_txt(path.read_text(encoding="utf-8"))


def _rename_successor_map(catalog: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in catalog.get("skill_renames") or []:
        mapping[str(row["from"])] = str(row["to"])
    return mapping


def _skill_changes(
    catalog: dict[str, Any],
    *,
    installed_skills: set[str],
    package_removals: list[str] | None,
) -> tuple[list[SkillChange], list[str]]:
    changes: list[SkillChange] = []
    removals = list(catalog.get("removals") or [])
    if package_removals:
        # Prefer the live package list when it is a SUPERSET of the catalog
        # (catalog stays the trap-3 contract; package may add historical rows).
        for name in package_removals:
            if name not in removals and name in installed_skills:
                removals.append(name)

    rename_from = {str(r["from"]) for r in (catalog.get("skill_renames") or [])}
    rename_to = {str(r["to"]) for r in (catalog.get("skill_renames") or [])}
    for row in catalog.get("skill_renames") or []:
        changes.append(
            SkillChange(
                kind="rename",
                name=str(row["from"]),
                to=str(row["to"]),
                shim_disposition=str(row.get("shim_disposition") or "forward"),
                source="catalog",
            )
        )

    for name in catalog.get("skill_adds") or []:
        n = str(name)
        # Renames already express the new ID as `to` — don't also list it as add.
        if n in rename_from or n in rename_to:
            continue
        changes.append(SkillChange(kind="add", name=n, source="catalog"))

    for name in removals:
        changes.append(
            SkillChange(
                kind="remove",
                name=name,
                source="removals.txt" if package_removals and name in package_removals else "catalog",
            )
        )

    return changes, removals


def _local_mod_findings(
    repo: Path,
    catalog: dict[str, Any],
    *,
    package_root: Path | None,
) -> list[LocalModFinding]:
    findings: list[LocalModFinding] = []
    markers = [str(m) for m in (catalog.get("repo_custom_markers") or [])]
    for rel in catalog.get("upstream_touched_paths") or []:
        rel_s = str(rel)
        local = repo / rel_s
        if not local.is_file():
            continue
        text = local.read_text(encoding="utf-8", errors="replace")
        hit_markers = [m for m in markers if m in text]
        upstream_lacks = False
        if package_root is not None:
            # Installer source path for resolve_config.py (and peers).
            candidates = [package_root / "src" / "scripts" / Path(rel_s).name]
            if rel_s.startswith("_bmad/"):
                candidates.append(package_root / Path(rel_s).relative_to("_bmad"))
            else:
                candidates.append(package_root / Path(rel_s).name)
            for up in candidates:
                if up.is_file():
                    up_text = up.read_text(encoding="utf-8", errors="replace")
                    if hit_markers and not any(m in up_text for m in hit_markers):
                        upstream_lacks = True
                    break
        if hit_markers or upstream_lacks:
            reason = (
                "repo-custom multi-project layers 5/6 present; "
                "upstream rewrite would drop them"
                if hit_markers
                else "local file differs from upstream package copy"
            )
            findings.append(LocalModFinding(path=rel_s, reason=reason))
    return findings


def _legacy_custom_findings(
    repo: Path,
    catalog: dict[str, Any],
) -> list[LegacyCustomFinding]:
    custom = repo / _CUSTOM_RELATIVE_PATH
    if not custom.is_dir():
        return []
    successors = _rename_successor_map(catalog)
    findings: list[LegacyCustomFinding] = []
    for legacy in catalog.get("legacy_custom_names") or []:
        base = str(legacy)
        # Accept either "bmad-dev-auto" or "bmad-dev-auto.user" as basename stem.
        path = custom / f"{base}.toml"
        if not path.is_file():
            continue
        # Map "bmad-dev-auto.user" → skill "bmad-dev-auto"
        skill = base.removesuffix(".user")
        findings.append(
            LegacyCustomFinding(
                path=str(path.relative_to(repo)),
                legacy_name=base,
                successor=successors.get(skill),
            )
        )
    return findings


def _prerequisite_findings(catalog: dict[str, Any]) -> list[PrerequisiteFinding]:
    out: list[PrerequisiteFinding] = []
    for row in catalog.get("hard_prerequisites") or []:
        out.append(
            PrerequisiteFinding(
                name=str(row["name"]),
                severity=str(row.get("severity") or "hard"),
                notes=str(row.get("notes") or "").strip(),
                min_version=(
                    str(row["min_version"]) if row.get("min_version") is not None else None
                ),
            )
        )
    return out


def _forwarder_findings(catalog: dict[str, Any]) -> list[ForwarderFinding]:
    out: list[ForwarderFinding] = []
    for row in catalog.get("forwarder_contract_changes") or []:
        suite = {str(k): str(v) for k, v in (row.get("suite_min_versions") or {}).items()}
        out.append(
            ForwarderFinding(
                skill=str(row["skill"]),
                forwards_to=(str(row["forwards_to"]) if row.get("forwards_to") else None),
                notes=str(row.get("notes") or "").strip(),
                suite_min_versions=suite,
            )
        )
    return out


def _config_migration_finding(catalog: dict[str, Any]) -> ConfigMigrationFinding | None:
    block = catalog.get("config_migration")
    if not isinstance(block, dict):
        return None
    return ConfigMigrationFinding(
        status=str(block.get("status") or "unknown"),
        notes=str(block.get("notes") or "").strip(),
    )


def build_preflight_report(
    *,
    repo: Path,
    target_version: str,
    installed_version: str | None = None,
    catalog_directory: Path | None = None,
    package_root: Path | None = None,
) -> PreflightReport:
    """Compute the report-only pre-flight for *target_version* against *repo*.

    Never mutates the filesystem. ``package_root``, when set, contributes a
    live ``removals.txt`` and upstream file comparison — still read-only.
    """
    catalog = load_release_catalog(target_version, directory=catalog_directory)
    installed = installed_version or read_installed_version(repo)
    installed_skills = _read_installed_skill_names(repo)
    package_removals = load_package_removals(package_root) if package_root else None

    skill_changes, removals = _skill_changes(
        catalog, installed_skills=installed_skills, package_removals=package_removals
    )
    locally_modified = _local_mod_findings(repo, catalog, package_root=package_root)
    legacy_custom = _legacy_custom_findings(repo, catalog)
    hard_prerequisites = _prerequisite_findings(catalog)
    forwarder_changes = _forwarder_findings(catalog)
    config_migration = _config_migration_finding(catalog)

    trap_ids: list[int] = []
    if locally_modified:
        trap_ids.append(TRAP_LOCAL_MOD)
    if legacy_custom:
        trap_ids.append(TRAP_LEGACY_CUSTOM)
    if removals:
        trap_ids.append(TRAP_REMOVALS)
    if hard_prerequisites:
        trap_ids.append(TRAP_PREREQUISITES)
    if forwarder_changes:
        trap_ids.append(TRAP_FORWARDER)
    if config_migration is not None:
        trap_ids.append(TRAP_CONFIG_MIGRATION)

    notes: list[str] = [
        "report-only — no apply / no mutation of _bmad/ or _bmad/custom/**",
    ]
    pair_from = catalog.get("baseline_pair_from")
    if pair_from:
        notes.append(
            f"catalog baseline pair: {pair_from} → {target_version} "
            "(failure-modes.md traps 1–4, 9, 11)"
        )
        if installed != str(pair_from) and installed != target_version:
            notes.append(
                f"installed {installed} differs from catalog baseline_pair_from "
                f"{pair_from} — trap retrodiction is calibrated for that pair"
            )
    if package_root is not None:
        pkg_ver = load_package_version(package_root)
        if pkg_ver and pkg_ver != target_version:
            notes.append(
                f"warning: --package-root package.json version is {pkg_ver}, "
                f"but --target is {target_version}"
            )
    if installed == target_version:
        notes.append(
            "installed version already equals target — report still lists "
            "what this release introduced (useful for audit / retrodiction)"
        )

    return PreflightReport(
        installed_version=installed,
        target_version=target_version,
        skill_changes=tuple(skill_changes),
        removals=tuple(removals),
        locally_modified=tuple(locally_modified),
        legacy_custom=tuple(legacy_custom),
        hard_prerequisites=tuple(hard_prerequisites),
        forwarder_changes=tuple(forwarder_changes),
        config_migration=config_migration,
        trap_ids=tuple(sorted(set(trap_ids))),
        notes=tuple(notes),
    )


def format_preflight(report: PreflightReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        f"steward upgrade bmad-core — pre-flight (report-only)",
        f"installed: {report.installed_version}",
        f"target:    {report.target_version}",
        f"traps:     {', '.join(str(t) for t in report.trap_ids) or '(none)'}",
        "",
        "## Skill changes (adds / removes / renames)",
    ]
    if not report.skill_changes:
        lines.append("(none)")
    for ch in report.skill_changes:
        if ch.kind == "rename":
            lines.append(
                f"- rename: {ch.name} → {ch.to} "
                f"(shim: {ch.shim_disposition}; source: {ch.source})"
            )
        else:
            lines.append(f"- {ch.kind}: {ch.name} (source: {ch.source})")

    lines.extend(["", f"## removals.txt deletions [trap {TRAP_REMOVALS}]"])
    if not report.removals:
        lines.append("(none)")
    for name in report.removals:
        lines.append(f"- [trap {TRAP_REMOVALS}] {name}")

    lines.extend(["", "## Upstream-touched files with local modifications"])
    if not report.locally_modified:
        lines.append("(none detected)")
    for item in report.locally_modified:
        lines.append(f"- [trap {item.trap_id}] {item.path}: {item.reason}")

    lines.extend(["", "## Legacy _bmad/custom/** overrides that halt shims"])
    if not report.legacy_custom:
        lines.append("(none)")
    for item in report.legacy_custom:
        succ = f" → rename to {item.successor}" if item.successor else ""
        lines.append(
            f"- [trap {item.trap_id}] {item.path} (legacy {item.legacy_name}{succ})"
        )

    lines.extend(["", "## New hard prerequisites"])
    if not report.hard_prerequisites:
        lines.append("(none)")
    for item in report.hard_prerequisites:
        ver = f" >={item.min_version}" if item.min_version else ""
        lines.append(
            f"- [trap {item.trap_id}] {item.name}{ver} ({item.severity}): {item.notes}"
        )

    lines.extend(["", "## Forwarder / orchestrator contract changes"])
    if not report.forwarder_changes:
        lines.append("(none)")
    for item in report.forwarder_changes:
        suite = (
            ", ".join(f"{k}>={v}" for k, v in sorted(item.suite_min_versions.items()))
            or "(no suite mins)"
        )
        dest = f" → {item.forwards_to}" if item.forwards_to else ""
        lines.append(
            f"- [trap {item.trap_id}] {item.skill}{dest}: {item.notes} [{suite}]"
        )

    lines.extend(["", "## Config-format migration"])
    if report.config_migration is None:
        lines.append("(none)")
    else:
        cm = report.config_migration
        lines.append(f"- [trap {cm.trap_id}] status={cm.status}: {cm.notes}")

    if report.notes:
        lines.extend(["", "## Notes"])
        for note in report.notes:
            lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


class UpgradeDuty:
    """``steward upgrade …`` — Epic 14 upgrade surfaces (14.1 = bmad-core pre-flight)."""

    name = "upgrade"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "upgrade_verb", None)
        if not verb:
            return DutyResult(
                ok=True,
                summary="upgrade: available verbs are bmad-core (report-only pre-flight)",
            )
        try:
            if verb == "bmad-core":
                return self._bmad_core(ns)
            return DutyResult(ok=False, summary=f"upgrade: unknown verb {verb!r}")
        except UpgradeError as exc:
            return DutyResult(ok=False, summary=f"upgrade: {exc}")
        except (OSError, yaml.YAMLError) as exc:
            return DutyResult(ok=False, summary=f"upgrade: {exc}")

    def _bmad_core(self, ns: argparse.Namespace) -> DutyResult:
        target = getattr(ns, "target", None)
        if not target:
            return DutyResult(
                ok=False,
                summary="upgrade bmad-core: --target X.Y.Z is required (report-only)",
            )
        repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
        package_root = Path(ns.package_root) if getattr(ns, "package_root", None) else None
        catalog_directory = (
            Path(ns.catalog_dir) if getattr(ns, "catalog_dir", None) else None
        )
        installed_override = getattr(ns, "installed_version", None)
        report = build_preflight_report(
            repo=repo,
            target_version=target,
            installed_version=installed_override,
            catalog_directory=catalog_directory,
            package_root=package_root,
        )
        as_json = bool(getattr(ns, "json", False))
        return DutyResult(
            ok=True,
            summary=format_preflight(report, as_json=as_json),
            details={"report": report.to_dict(), "trap_ids": list(report.trap_ids)},
        )
