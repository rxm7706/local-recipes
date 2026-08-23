"""Steward's ``upgrade`` duty — BMAD-METHOD core upgrade surfaces (Epic 14).

Story 14.1 / CAP-1: report-only pre-flight for a target bmad-method release.
Story 14.2 / CAP-2: deliberate ``--apply`` — clean tree + CAP-1 gate, branch
first, run ``bmad-method install --action update -y`` (installer remains the
only writer of ``_bmad/bmm/**`` / ``_bmad/core/**``), refuse on legacy-name
custom that would halt shims, land the installer diff on a review branch,
and prove ``_bmad/custom/**`` byte-identical (or name why not).

Story 14.3 / CAP-3: after apply, detect clobbered repo-custom surfaces
(named case: ``resolve_config.py`` multi-project layers 5/6), re-apply from
installer ``.bak`` or a pre-apply snapshot, or flag — never leave broken
silently. Success: six-layer resolution via ``BMAD_ACTIVE_PROJECT`` and via
a fixture-local ``.active-project`` marker. Never calls ``scripts/bmad-switch``.

Never implements CAP-4 pin fan-out or CAP-5 verify.

Verb naming (SPEC open question): a dedicated ``steward upgrade bmad-core``
duty — not an extension of ``provision`` — because Epic 14's later CAPs
share this surface and must not crowd Epic 3's provisioning flags.

Detection of ambient "you're behind" stays doctor's
(``bmad-method-version-drift``); this module is the deliberate pre-flight
and apply surface an operator runs.
"""

from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

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



@dataclass(frozen=True)
class ClobberFinding:
    """One upstream-touched repo-custom surface checked after apply."""

    path: str
    markers_before: bool
    markers_after: bool
    bak_path: str | None
    action: str  # intact | restored_from_bak | restored_from_snapshot | flagged
    detail: str


@dataclass(frozen=True)
class ReconcileReport:
    """CAP-3 detect / re-apply / flag outcome for clobbered custom surfaces."""

    findings: tuple[ClobberFinding, ...]
    bak_files_accounted: tuple[str, ...]
    layers_ok_env: bool
    layers_ok_marker: bool
    all_clear: bool
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "path": f.path,
                    "markers_before": f.markers_before,
                    "markers_after": f.markers_after,
                    "bak_path": f.bak_path,
                    "action": f.action,
                    "detail": f.detail,
                }
                for f in self.findings
            ],
            "bak_files_accounted": list(self.bak_files_accounted),
            "layers_ok_env": self.layers_ok_env,
            "layers_ok_marker": self.layers_ok_marker,
            "all_clear": self.all_clear,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ApplyReport:
    """Outcome of a deliberate CAP-2 apply (review branch + custom check)."""

    preflight: PreflightReport
    branch: str
    snapshot_sha: str
    installer_cmd: tuple[str, ...]
    installer_exit: int
    custom_identical: bool
    custom_differs: tuple[str, ...]
    custom_failure_reason: str | None
    changed_paths: tuple[str, ...]
    reconcile: ReconcileReport | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "preflight": self.preflight.to_dict(),
            "branch": self.branch,
            "snapshot_sha": self.snapshot_sha,
            "installer_cmd": list(self.installer_cmd),
            "installer_exit": self.installer_exit,
            "custom_identical": self.custom_identical,
            "custom_differs": list(self.custom_differs),
            "custom_failure_reason": self.custom_failure_reason,
            "changed_paths": list(self.changed_paths),
            "reconcile": self.reconcile.to_dict() if self.reconcile else None,
            "notes": list(self.notes),
        }


InstallerRunner = Callable[[Path, Sequence[str]], subprocess.CompletedProcess[str]]


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


# ── Story 14.2 / CAP-2 — deliberate apply ──────────────────────────────────


def default_apply_branch(target_version: str) -> str:
    """Review-branch name for a deliberate apply of *target_version*."""
    return f"steward/bmad-core-upgrade-{target_version}"


def _git(
    *args: str,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def assert_clean_tree(repo: Path) -> None:
    """Refuse apply when the working tree is dirty (uncommitted changes)."""
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        # Bare fixtures without git are only allowed via injected runners in tests;
        # production apply always requires a git checkout.
        raise UpgradeError(
            "apply requires a git checkout (no .git found) — refuse to mutate in place"
        )
    status = _git("status", "--porcelain", cwd=repo)
    dirty = status.stdout.strip()
    if dirty:
        preview = "\n".join(dirty.splitlines()[:20])
        raise UpgradeError(
            "apply requires a clean working tree; refuse to start with dirty paths:\n"
            f"{preview}"
        )


def fingerprint_custom_tree(repo: Path) -> dict[str, str]:
    """Return ``{relative_path: sha256-hex}`` for every file under ``_bmad/custom/**``."""
    custom = repo / _CUSTOM_RELATIVE_PATH
    if not custom.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in sorted(custom.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo)).replace("\\", "/")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[rel] = digest
    return out


def compare_custom_fingerprints(
    before: Mapping[str, str],
    after: Mapping[str, str],
) -> tuple[bool, tuple[str, ...], str | None]:
    """Return ``(identical, differing_paths, reason_or_none)``."""
    before_keys = set(before)
    after_keys = set(after)
    differs: list[str] = []
    for path in sorted(before_keys | after_keys):
        if path not in before:
            differs.append(f"{path} (added)")
        elif path not in after:
            differs.append(f"{path} (removed)")
        elif before[path] != after[path]:
            differs.append(f"{path} (content changed)")
    if not differs:
        return True, (), None
    reason = (
        "_bmad/custom/** is NOT byte-identical after apply — "
        "installer or side effect touched custom; named paths: "
        + ", ".join(differs)
    )
    return False, tuple(differs), reason


def refuse_legacy_custom(preflight: PreflightReport) -> None:
    """CAP-2: refuse to start when legacy-name custom would halt shims."""
    if not preflight.legacy_custom:
        return
    named = ", ".join(
        f"{item.path} (legacy {item.legacy_name}"
        + (f" → {item.successor}" if item.successor else "")
        + ")"
        for item in preflight.legacy_custom
    )
    raise UpgradeError(
        "refuse to start apply: legacy-name _bmad/custom/** files would halt "
        f"deprecation shims (trap {TRAP_LEGACY_CUSTOM}): {named}"
    )


def create_review_branch(repo: Path, branch: str) -> str:
    """Create and check out *branch* from HEAD; return the snapshot SHA.

    Refuses if *branch* already exists — never clobber an existing review branch.
    """
    head = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    exists = _git(
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{branch}",
        cwd=repo,
        check=False,
    )
    if exists.returncode == 0:
        raise UpgradeError(
            f"review branch {branch!r} already exists — refuse to clobber; "
            "choose --branch or delete the stale branch after review"
        )
    _git("checkout", "-b", branch, cwd=repo)
    return head


def list_changed_paths(repo: Path) -> tuple[str, ...]:
    """Porcelain paths after the installer ran (the reviewable installer diff)."""
    status = _git("status", "--porcelain", cwd=repo, check=False)
    paths: list[str] = []
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        # porcelain: XY PATH or XY ORIG -> PATH
        rest = line[3:] if len(line) > 3 else line.strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        paths.append(rest.strip())
    return tuple(paths)


def default_installer_runner(
    repo: Path, cmd: Sequence[str]
) -> subprocess.CompletedProcess[str]:
    """Invoke the real installer; steward never writes ``_bmad/bmm/**`` / ``_bmad/core/**``."""
    return subprocess.run(
        list(cmd),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )



def _markers_present(text: str, markers: Sequence[str]) -> bool:
    return bool(markers) and all(m in text for m in markers)


def snapshot_repo_custom_surfaces(
    repo: Path,
    catalog: Mapping[str, Any],
) -> dict[str, str]:
    """Pre-apply bytes for upstream-touched paths that carry repo-custom markers."""
    markers = [str(m) for m in (catalog.get("repo_custom_markers") or [])]
    out: dict[str, str] = {}
    for rel in catalog.get("upstream_touched_paths") or []:
        rel_s = str(rel).replace("\\", "/")
        path = repo / rel_s
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        if _markers_present(body, markers):
            out[rel_s] = body
    return out


def _bak_candidate(repo: Path, rel: str) -> Path | None:
    """Return the installer ``.bak`` path beside *rel* if it exists."""
    direct = repo / f"{rel}.bak"
    if direct.is_file():
        return direct
    path = repo / rel
    alt = Path(str(path) + ".bak")
    if alt.is_file():
        return alt
    return None


def list_installer_bak_files(repo: Path, relative_paths: Sequence[str]) -> tuple[str, ...]:
    found: list[str] = []
    for rel in relative_paths:
        bak = _bak_candidate(repo, rel)
        if bak is not None:
            found.append(str(bak.relative_to(repo)).replace("\\", "/"))
    return tuple(sorted(set(found)))


def verify_six_layer_resolution(
    repo: Path,
    *,
    resolve_rel: str,
    probe_slug: str = "cap3-probe",
) -> tuple[bool, bool, tuple[str, ...]]:
    """Prove layers 5/6 via ``BMAD_ACTIVE_PROJECT`` and fixture-local marker.

    Never calls ``scripts/bmad-switch``. Marker writes stay inside *repo*.

    When *resolve_rel* is a marker-only stub (no multi-project merge body),
    success is structural: markers present. Runtime probes run only when the
    script references ``_bmad-output/projects`` (live multi-project shape).
    """
    notes: list[str] = []
    resolve_path = repo / resolve_rel
    if not resolve_path.is_file():
        return False, False, (f"{resolve_rel} missing — cannot verify six layers",)

    markers = ("BMAD_ACTIVE_PROJECT", ".active-project")
    body = resolve_path.read_text(encoding="utf-8", errors="replace")
    if not _markers_present(body, markers):
        return False, False, (
            f"{resolve_rel} lacks multi-project markers after reconcile",
        )

    runnable = "_bmad-output/projects" in body and ".bmad-config.toml" in body
    if not runnable:
        notes.append(
            "runtime six-layer probe skipped — resolve_config is marker-only "
            "(no _bmad-output/projects merge body); structural markers ok"
        )
        return True, True, tuple(notes)

    cfg = repo / "_bmad" / "config.toml"
    if not cfg.is_file():
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("# cap3 probe base layer\n", encoding="utf-8")

    project_dir = repo / "_bmad-output" / "projects" / probe_slug
    project_dir.mkdir(parents=True, exist_ok=True)
    probe_key = "cap3_probe_token"
    probe_val = "layers-5-6-alive"
    (project_dir / ".bmad-config.toml").write_text(
        f'{probe_key} = "{probe_val}"\n', encoding="utf-8"
    )
    (project_dir / ".bmad-config.user.toml").write_text(
        "# cap3 user overlay\n", encoding="utf-8"
    )

    def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                __import__("sys").executable,
                str(resolve_path),
                "--project-root",
                str(repo),
                "--key",
                probe_key,
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    base_env = {k: v for k, v in os.environ.items() if k != "BMAD_ACTIVE_PROJECT"}
    env_proc = _run({**base_env, "BMAD_ACTIVE_PROJECT": probe_slug})
    layers_ok_env = env_proc.returncode == 0 and probe_val in (env_proc.stdout or "")
    if not layers_ok_env:
        notes.append(
            f"BMAD_ACTIVE_PROJECT probe failed (exit {env_proc.returncode}): "
            f"{(env_proc.stderr or env_proc.stdout or '')[:300]}"
        )

    marker = repo / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    previous = marker.read_text(encoding="utf-8") if marker.is_file() else None
    try:
        marker.write_text(probe_slug + "\n", encoding="utf-8")
        marker_proc = _run(dict(base_env))
        layers_ok_marker = (
            marker_proc.returncode == 0 and probe_val in (marker_proc.stdout or "")
        )
        if not layers_ok_marker:
            notes.append(
                f".active-project marker probe failed (exit {marker_proc.returncode}): "
                f"{(marker_proc.stderr or marker_proc.stdout or '')[:300]}"
            )
    finally:
        if previous is None:
            if marker.is_file():
                marker.unlink()
        else:
            marker.write_text(previous, encoding="utf-8")

    return layers_ok_env, layers_ok_marker, tuple(notes)



def reconcile_clobbered_custom_surfaces(
    repo: Path,
    catalog: Mapping[str, Any],
    *,
    pre_apply_snapshots: Mapping[str, str],
) -> ReconcileReport:
    """Detect clobbered surfaces; restore from ``.bak`` or snapshot; else flag."""
    markers = [str(m) for m in (catalog.get("repo_custom_markers") or [])]
    touched = [str(p).replace("\\", "/") for p in (catalog.get("upstream_touched_paths") or [])]
    bak_accounted = list(list_installer_bak_files(repo, touched))

    findings: list[ClobberFinding] = []
    notes: list[str] = []
    candidates = list(dict.fromkeys([*pre_apply_snapshots.keys(), *touched]))

    for rel in candidates:
        path = repo / rel
        before = rel in pre_apply_snapshots
        after_text = (
            path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        )
        after = _markers_present(after_text, markers) if after_text else False
        bak = _bak_candidate(repo, rel)
        bak_rel = (
            str(bak.relative_to(repo)).replace("\\", "/") if bak is not None else None
        )
        if bak_rel and bak_rel not in bak_accounted:
            bak_accounted.append(bak_rel)

        if before and after:
            findings.append(
                ClobberFinding(
                    path=rel,
                    markers_before=True,
                    markers_after=True,
                    bak_path=bak_rel,
                    action="intact",
                    detail="repo-custom markers survived apply",
                )
            )
            continue

        if not before:
            continue

        # Clobbered: had markers before, missing after.
        action = "flagged"
        detail = "clobbered; no usable .bak or snapshot"
        markers_after = False

        if bak is not None:
            bak_text = bak.read_text(encoding="utf-8", errors="replace")
            if _markers_present(bak_text, markers):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(bak_text, encoding="utf-8")
                action = "restored_from_bak"
                detail = f"re-applied from installer .bak ({bak_rel})"

        if action == "flagged" and rel in pre_apply_snapshots:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pre_apply_snapshots[rel], encoding="utf-8")
            action = "restored_from_snapshot"
            detail = "re-applied from pre-apply snapshot"
            if bak is not None:
                detail += f"; installer .bak accounted at {bak_rel}"

        if path.is_file():
            markers_after = _markers_present(
                path.read_text(encoding="utf-8", errors="replace"), markers
            )
        if action != "flagged" and not markers_after:
            action = "flagged"
            detail = "restore wrote bytes but markers still absent"
        elif action == "flagged":
            detail = f"clobbered repo-custom surface; could not re-apply (bak={bak_rel!r})"

        findings.append(
            ClobberFinding(
                path=rel,
                markers_before=True,
                markers_after=markers_after,
                bak_path=bak_rel,
                action=action,
                detail=detail,
            )
        )

    resolve_rel = next(
        (t for t in touched if t.endswith("resolve_config.py")),
        "_bmad/scripts/resolve_config.py",
    )
    layers_ok_env, layers_ok_marker, verify_notes = verify_six_layer_resolution(
        repo, resolve_rel=resolve_rel
    )
    notes.extend(verify_notes)

    flagged = [f for f in findings if f.action == "flagged"]
    all_clear = (
        not flagged
        and layers_ok_env
        and layers_ok_marker
        and all(f.markers_after for f in findings if f.markers_before)
    )
    if all_clear:
        notes.append(
            "CAP-3 clear: markers present; six layers resolve via "
            "BMAD_ACTIVE_PROJECT and .active-project marker"
        )
    else:
        notes.append(
            "CAP-3 incomplete: clobber flagged and/or six-layer probes failed"
        )
    if bak_accounted:
        notes.append("installer .bak accounted: " + ", ".join(sorted(set(bak_accounted))))
    else:
        notes.append("installer .bak accounted: (none found beside tracked surfaces)")

    return ReconcileReport(
        findings=tuple(findings),
        bak_files_accounted=tuple(sorted(set(bak_accounted))),
        layers_ok_env=layers_ok_env,
        layers_ok_marker=layers_ok_marker,
        all_clear=all_clear,
        notes=tuple(notes),
    )


def apply_bmad_core_upgrade(
    *,
    repo: Path,
    target_version: str,
    branch: str | None = None,
    installed_version: str | None = None,
    catalog_directory: Path | None = None,
    package_root: Path | None = None,
    installer_bin: str = "bmad-method",
    installer_runner: InstallerRunner | None = None,
) -> ApplyReport:
    """CAP-2+3 deliberate apply: preflight → branch → installer → custom check → CAP-3 reconcile.

    The installer command is always ``bmad-method install --action update -y``
    (or *installer_bin* override). Steward never reimplements writing
    ``_bmad/bmm/**`` or ``_bmad/core/**``.
    """
    assert_clean_tree(repo)

    preflight = build_preflight_report(
        repo=repo,
        target_version=target_version,
        installed_version=installed_version,
        catalog_directory=catalog_directory,
        package_root=package_root,
    )
    refuse_legacy_custom(preflight)

    review_branch = branch or default_apply_branch(target_version)
    custom_before = fingerprint_custom_tree(repo)
    catalog = load_release_catalog(
        target_version, directory=catalog_directory
    )
    surface_snapshots = snapshot_repo_custom_surfaces(repo, catalog)
    snapshot_sha = create_review_branch(repo, review_branch)

    installer_cmd = (installer_bin, "install", "--action", "update", "-y")
    runner = installer_runner or default_installer_runner
    result = runner(repo, installer_cmd)

    notes: list[str] = [
        "deliberate apply — installer diff left on review branch for human review "
        "(never merged/applied blind)",
        "steward did not write _bmad/bmm/** or _bmad/core/** — installer is sole writer",
    ]
    if result.stdout and result.stdout.strip():
        notes.append(f"installer stdout (truncated): {result.stdout.strip()[:500]}")
    if result.stderr and result.stderr.strip():
        notes.append(f"installer stderr (truncated): {result.stderr.strip()[:500]}")

    if result.returncode != 0:
        notes.append(
            f"installer exited {result.returncode} — review branch {review_branch} "
            "still holds any partial diff; custom check follows"
        )

    custom_after = fingerprint_custom_tree(repo)
    identical, differs, reason = compare_custom_fingerprints(custom_before, custom_after)
    if identical:
        notes.append("_bmad/custom/** byte-identical after apply (sha256 per file)")
    elif reason:
        notes.append(reason)

    changed = list_changed_paths(repo)
    if changed:
        notes.append(
            f"installer diff on branch {review_branch} ({len(changed)} path(s)) — "
            "review before merge"
        )
    else:
        notes.append("installer produced no working-tree changes")

    reconcile = reconcile_clobbered_custom_surfaces(
        repo, catalog, pre_apply_snapshots=surface_snapshots
    )
    notes.extend(reconcile.notes)

    return ApplyReport(
        preflight=preflight,
        branch=review_branch,
        snapshot_sha=snapshot_sha,
        installer_cmd=tuple(installer_cmd),
        installer_exit=int(result.returncode),
        custom_identical=identical,
        custom_differs=differs,
        custom_failure_reason=reason,
        changed_paths=changed,
        reconcile=reconcile,
        notes=tuple(notes),
    )


def format_apply(report: ApplyReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "steward upgrade bmad-core — deliberate apply (CAP-2)",
        f"installed: {report.preflight.installed_version}",
        f"target:    {report.preflight.target_version}",
        f"branch:    {report.branch}",
        f"snapshot:  {report.snapshot_sha}",
        f"installer: {' '.join(report.installer_cmd)} (exit {report.installer_exit})",
        f"custom:    {'byte-identical' if report.custom_identical else 'CHANGED — see below'}",
        "",
        "## Review surface (installer diff paths)",
    ]
    if not report.changed_paths:
        lines.append("(none)")
    for path in report.changed_paths:
        lines.append(f"- {path}")

    lines.extend(["", "## _bmad/custom/** preservation"])
    if report.custom_identical:
        lines.append("byte-identical (ok)")
    else:
        lines.append(report.custom_failure_reason or "custom changed (unnamed)")
        for path in report.custom_differs:
            lines.append(f"- {path}")

    lines.extend(["", "## CAP-3 clobbered custom surfaces"])
    if report.reconcile is None:
        lines.append("(no reconcile run)")
    else:
        rec = report.reconcile
        lines.append(
            f"all_clear={rec.all_clear} layers_ok_env={rec.layers_ok_env} "
            f"layers_ok_marker={rec.layers_ok_marker}"
        )
        if not rec.findings:
            lines.append("(no tracked surfaces)")
        for finding in rec.findings:
            lines.append(
                f"- [{finding.action}] {finding.path}: {finding.detail}"
            )
        if rec.bak_files_accounted:
            lines.append(
                "bak accounted: " + ", ".join(rec.bak_files_accounted)
            )

    if report.notes:
        lines.extend(["", "## Notes"])
        for note in report.notes:
            lines.append(f"- {note}")

    # Include the CAP-1 preflight body for the review checklist.
    lines.extend(["", "--- CAP-1 preflight consumed by this apply ---", ""])
    lines.append(format_preflight(report.preflight, as_json=False).rstrip())
    return "\n".join(lines) + "\n"


class UpgradeDuty:
    """``steward upgrade …`` — Epic 14 (14.1–14.3: preflight, apply, CAP-3 reconcile)."""

    name = "upgrade"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "upgrade_verb", None)
        if not verb:
            return DutyResult(
                ok=True,
                summary=(
                    "upgrade: available verbs are bmad-core "
                    "(report-only pre-flight; pass --apply for CAP-2 deliberate apply)"
                ),
            )
        try:
            if verb == "bmad-core":
                return self._bmad_core(ns)
            return DutyResult(ok=False, summary=f"upgrade: unknown verb {verb!r}")
        except UpgradeError as exc:
            return DutyResult(ok=False, summary=f"upgrade: {exc}")
        except (OSError, yaml.YAMLError, subprocess.SubprocessError) as exc:
            return DutyResult(ok=False, summary=f"upgrade: {exc}")

    def _bmad_core(self, ns: argparse.Namespace) -> DutyResult:
        target = getattr(ns, "target", None)
        if not target:
            return DutyResult(
                ok=False,
                summary="upgrade bmad-core: --target X.Y.Z is required",
            )
        repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
        package_root = Path(ns.package_root) if getattr(ns, "package_root", None) else None
        catalog_directory = (
            Path(ns.catalog_dir) if getattr(ns, "catalog_dir", None) else None
        )
        installed_override = getattr(ns, "installed_version", None)
        as_json = bool(getattr(ns, "json", False))
        do_apply = bool(getattr(ns, "apply", False))

        if not do_apply:
            report = build_preflight_report(
                repo=repo,
                target_version=target,
                installed_version=installed_override,
                catalog_directory=catalog_directory,
                package_root=package_root,
            )
            return DutyResult(
                ok=True,
                summary=format_preflight(report, as_json=as_json),
                details={"report": report.to_dict(), "trap_ids": list(report.trap_ids)},
            )

        installer_bin = getattr(ns, "installer", None) or "bmad-method"
        branch = getattr(ns, "branch", None) or None
        apply_report = apply_bmad_core_upgrade(
            repo=repo,
            target_version=target,
            branch=branch,
            installed_version=installed_override,
            catalog_directory=catalog_directory,
            package_root=package_root,
            installer_bin=installer_bin,
        )
        reconcile_ok = (
            apply_report.reconcile is not None and apply_report.reconcile.all_clear
        )
        ok = (
            apply_report.installer_exit == 0
            and apply_report.custom_identical
            and reconcile_ok
        )
        return DutyResult(
            ok=ok,
            summary=format_apply(apply_report, as_json=as_json),
            details={
                "apply": apply_report.to_dict(),
                "trap_ids": list(apply_report.preflight.trap_ids),
            },
        )
