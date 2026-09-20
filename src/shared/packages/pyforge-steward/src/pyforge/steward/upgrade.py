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

Story 14.4 / CAP-4: report-only pin fan-out enumeration for a bmad-method or
bmad-loop version change — every known pin site with moved/not-moved status.
Foreign-station sites (marshal, loop-home relays) are reported, never edited.

Story 14.5 / CAP-5: post-apply prove-landed — one command runs bmad-drift
integrity, CFE skill meta-tests, and per-loop-home ``bmad-loop init`` relay
refresh + ``validate``, then reports a single verdict. The only foreign-tree
mutation is the documented relay refresh (``bmad-loop init``); gates themselves
are report-only.

Story 15.4 / CAP-4 dual-path orbit: prove-landed also advisory-spot-checks one
cited native command per install-matrix class (dashboards = check-by-doc).
Spot-check failures never flip CAP-5 ``verdict`` / ``DutyResult.ok``.

Story 14.6 / CAP-6: the installer is driven on purpose — the argv carries
``--directory <repo> --modules <every module the installed manifest lists,
core first>``, stdin is closed, and ``node`` / ``bmad-method`` resolve from the
repo's ``.pixi/envs/pyforge-guild/bin`` only when absent from PATH. An exit-0
run that changed nothing is a refusal (``ApplyReport.zero_diff``, trap 12),
never a green; a manifest that names no modules stops the apply before the
review branch exists (trap 13). No wrapper script.

Story 14.7 / CAP-7: custom modules survive the core apply. The release catalog's
``custom_modules:`` list annotates each ``source: custom`` manifest module (own
installer argv, config paths, optional pin, optional packaged source); selection
still comes from the manifest — Story 14.6's design already guarantees every
``source: custom`` module is on ``--modules`` (it selects the manifest's full
module list), so the apply's own custom-module-selected check is a structural
invariant / defense-in-depth assertion, not a live catch. The pre-flight lists
catalog vs manifest (mismatch = trap 13 finding). The apply adds
``--pin <name>=<pin>`` when the catalog sets one, snapshots each config path's
bytes before the core installer and restores them verbatim afterwards, runs the
module's own installer from the repo root through an injectable runner, verifies
``.claude/skills/<name>-*`` against the packaged source (a finding, never a
gate), reports the regenerated ``[modules.<name>]`` block of ``_bmad/config.toml``
as a diff (never edited), and gates ``custom_modules_ok`` on own-installer exit 0
plus every config path restored. ``zero_diff`` keeps its CAP-6 meaning — judged
on the core installer's own diff, before this phase runs; the CAP-7 phase itself
(config restore + own installer) is what addresses trap 14.

Verb naming (SPEC open question): a dedicated ``steward upgrade bmad-core``
duty — not an extension of ``provision`` — because Epic 14's later CAPs
share this surface and must not crowd Epic 3's provisioning flags.

Detection of ambient "you're behind" stays doctor's
(``bmad-method-version-drift``); this module is the deliberate pre-flight
and apply surface an operator runs.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Protocol

import yaml

from .interfaces import DutyResult

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_MANIFEST_RELATIVE_PATH = Path("_bmad/_config/manifest.yaml")
_CUSTOM_RELATIVE_PATH = Path("_bmad/custom")
# CAP-7: where a custom module's IDE skill dirs land (verified, never written by
# steward) and the installer-generated TOML whose `[modules.<name>]` block is
# reported as a diff, never edited.
_IDE_SKILLS_RELATIVE_PATH = Path(".claude/skills")
_CONFIG_TOML_RELATIVE_PATH = Path("_bmad/config.toml")
_SKILL_MANIFEST_RELATIVE_PATH = Path("_bmad/_config/skill-manifest.csv")
# CAP-8: best-effort default location of a rattler/conda package cache, used to
# resolve the INSTALLED version's unpacked bmad-method package when
# --installed-package-root is not passed.
_RATTLER_PKGS_CACHE_RELATIVE_PATH = Path(".cache/rattler/cache/pkgs")
# CAP-6: where the installer's `node` / `bmad-method` live when they are not on
# PATH — always derived from the repo path, never a machine path.
# Story 63.6 (spec-pyforge-steward CAP-152): the Guild env is the only runtime env.
_PIXI_LOCAL_RECIPES_BIN_RELATIVE_PATH = Path(".pixi/envs/pyforge-guild/bin")
# Stable ``X.Y.Z`` plus optional npm prerelease suffix (e.g. ``6.12.1-next.0``).
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[\w.]+)?$")

# Trap IDs from failure-modes.md that CAP-1 must retrodict for 6.10→6.11.
TRAP_LOCAL_MOD = 1
TRAP_LEGACY_CUSTOM = 2
TRAP_REMOVALS = 3
TRAP_PREREQUISITES = 4
TRAP_PIN_FANOUT = 5  # CAP-4 report surface (not a CAP-1 preflight trap)
TRAP_LOOP_RELAY = 7  # CAP-5: stale hook relays → init + validate
TRAP_FORWARDER = 9
TRAP_CONFIG_MIGRATION = 11
# CAP-6 (Story 14.6) apply traps from the 2026-09-06 first 6.12 apply.
TRAP_SILENT_NOOP_APPLY = 12  # exit 0, nothing written (cancelled directory prompt)
TRAP_CUSTOM_MODULE_DESELECTED = 13  # `-y` deletes an unselected cached custom module
# CAP-7 (Story 14.7): the installer regenerates a custom module's config.yaml
# from module.yaml defaults and honours its marketplace.json skill list.
TRAP_CUSTOM_MODULE_CONFIG_REGENERATED = 14
# CAP-8 (Story 14.8): a marker-free byte-diff scan finds any OTHER
# installer-owned skill file or `_bmad/scripts/*.py` script edited in place
# (trap 15 is CAP-5's env gate — unrelated, never reused).
TRAP_LOCAL_CUSTOMIZATION = 16

# 2026-08-21 worked example: eight loop homes validate clean, zero warnings.
WORKED_EXAMPLE_LOOP_HOME_COUNT = 8
_CFE_META_TEST_REL = Path(
    ".claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py"
)
_INSTALL_MATRIX_REL = Path(
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/"
    "spec-bmad-suite-channel-product/install-matrix.md"
)
# Matrix table native URL for bmad-loop (uv-from-git class). Mirrors the
# install-matrix.md `bmad-loop` row verbatim — the two move together
# (DW-FU-15-4-3 closed 2026-09-06: v0.11.0 sat here while the matrix said v0.11.1).
_BMAD_LOOP_UV_GIT_SPEC = (
    "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.1"
)
# Matrix table custom-source URL for bmad-manticore.
_MANTICORE_CUSTOM_SOURCE_URL = (
    "https://github.com/bmad-code-org/bmad-manticore"
)

# Relative paths for the trap-5 pin fan-out catalog (2026-08-21 session).
_MARSHAL_PKG = Path("src/shared/packages/pyforge-marshal")
_PIN_ROOT_PIXI = Path("pixi.toml")
_PIN_MARSHAL_PYPROJECT = _MARSHAL_PKG / "pyproject.toml"
_PIN_MARSHAL_PIXI = _MARSHAL_PKG / "pixi.toml"
_PIN_HARNESS = (
    _MARSHAL_PKG / "src" / "pyforge" / "marshal" / "adapters" / "harness_bmadloop.py"
)
_PIN_SEED_MANIFEST = (
    _MARSHAL_PKG / "src" / "pyforge" / "marshal" / "seed" / "templates" / "manifest.yaml"
)
_PIN_DRIFT_TEST = (
    _MARSHAL_PKG / "tests" / "unit" / "test_seed_templates_manifest.py"
)
_HOOK_SCRIPT_REL = Path(".bmad-loop") / "bmad_loop_hook.py"
_VERSION_CORE_RE = re.compile(r"(\d+\.\d+\.\d+)")
_PIN_LOWER_RE = re.compile(r">=\s*(\d+\.\d+\.\d+)")
_HARNESS_RANGE_RE = re.compile(
    r"""HARNESS_VERSION_RANGE_TEXT\s*=\s*["']([^"']+)["']"""
)
_DRIFT_MAP_ENTRY_RE = re.compile(
    r"""["'](?P<id>bmad-(?:loop|method|installed-skills))["']\s*:\s*["'](?P<pin>[^"']+)["']"""
)


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
class CustomModuleFinding:
    """CAP-7 pre-flight row: one catalog ``custom_modules`` entry vs the installed manifest.

    ``matched`` is True only when the catalog names the module AND the manifest
    lists it with ``source: custom``. Any other combination is a trap-13
    finding (catalog stale, module deleted, or an installed custom module the
    catalog does not know — which the apply could not restore, trap 14).
    """

    name: str
    in_catalog: bool
    manifest_source: str | None
    matched: bool
    own_installer: tuple[str, ...]
    pin: str | None
    detail: str
    trap_id: int = TRAP_CUSTOM_MODULE_DESELECTED
    # The catalog's own authored narrative (``CustomModuleDef.notes``) — empty
    # when the module is not in the catalog at all.
    notes: str = ""


@dataclass(frozen=True)
class LocalCustomizationFinding:
    """CAP-8: an installer-owned skill file or script edited in place (no marker needed)."""

    path: str
    reason: str
    trap_id: int = TRAP_LOCAL_CUSTOMIZATION


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
    # CAP-7 (Story 14.7) — appended after ``notes`` so positional constructors
    # written before it stay valid.
    custom_modules: tuple[CustomModuleFinding, ...] = ()
    # CAP-8 (Story 14.8) — appended last for the same reason.
    local_customizations: tuple[LocalCustomizationFinding, ...] = ()
    # CAP-9 (Story 14.9) — appended last for the same reason. A preview of what
    # a future `--no-shims` run would remove; never a trap (see Design Notes).
    shims_to_retire: tuple[str, ...] = ()

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
class ConfigRestore:
    """One catalog ``config_paths`` entry after the core installer ran (CAP-7)."""

    path: str
    status: str  # restored | unchanged | missing
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class CustomizationReapplyFinding:
    """CAP-8: one pre-flight-flagged file's outcome after the core installer ran."""

    path: str
    # merged_clean | conflict_needs_manual_merge | unchanged | skipped_no_snapshot |
    # skipped_no_package_match | skipped_installer_removed_file
    action: str
    detail: str
    conflict_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "action": self.action,
            "detail": self.detail,
            "conflict_path": self.conflict_path,
        }


@dataclass(frozen=True)
class CustomizationReapplyReport:
    """CAP-8 outcome: three-way re-apply of every pre-flight-flagged local customization."""

    findings: tuple[CustomizationReapplyFinding, ...]
    all_clean: bool
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "all_clean": self.all_clean,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class SkillDirVerification:
    """``.claude/skills/<name>-*`` compared against the catalog's packaged source (CAP-7).

    A finding, never a gate: a missing pixi env or a deliberately patched skill
    must not turn a coherent apply red.
    """

    packaged_source: str
    expected: int
    equal: int
    mismatched: tuple[str, ...]
    missing: tuple[str, ...]
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "packaged_source": self.packaged_source,
            "expected": self.expected,
            "equal": self.equal,
            "mismatched": list(self.mismatched),
            "missing": list(self.missing),
            "ok": self.ok,
        }


@dataclass(frozen=True)
class CustomModuleReport:
    """CAP-7 outcome for one catalog custom module during the apply.

    ``ok`` is own-installer exit 0 AND every config path restored/unchanged; an
    unselected module (catalog names it, manifest does not list it as custom)
    reports ``selected=False`` and never gates ``custom_modules_ok``.
    """

    name: str
    selected: bool
    pin: str | None
    config_paths: tuple[ConfigRestore, ...]
    own_installer_cmd: tuple[str, ...]
    own_installer_exit: int | None
    own_installer_error: str | None
    verification: SkillDirVerification | None
    config_toml_block_changed: bool
    config_toml_block_diff: str
    ok: bool
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "selected": self.selected,
            "pin": self.pin,
            "config_paths": [c.to_dict() for c in self.config_paths],
            "own_installer_cmd": list(self.own_installer_cmd),
            "own_installer_exit": self.own_installer_exit,
            "own_installer_error": self.own_installer_error,
            "verification": self.verification.to_dict() if self.verification else None,
            "config_toml_block_changed": self.config_toml_block_changed,
            "config_toml_block_diff": self.config_toml_block_diff,
            "ok": self.ok,
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
    # CAP-6: strictly ``installer_exit == 0 and not changed_paths`` — the trap-12
    # shape (a cancelled prompt or a no-op). A non-zero exit is already a failure
    # through the exit gate and is never double-reported here. Judged on the
    # CORE installer's diff, before the CAP-7 custom-module phase runs.
    zero_diff: bool = False
    # CAP-7 (Story 14.7): one report per catalog custom module; the gate is
    # ``all(m.ok for m in custom_modules if m.selected)``.
    custom_modules: tuple[CustomModuleReport, ...] = ()
    custom_modules_ok: bool = True
    # CAP-8 (Story 14.8): three-way re-apply of pre-flight-flagged local
    # customizations, run after the CAP-7 custom-module phase.
    local_customizations_reapply: CustomizationReapplyReport | None = None
    local_customizations_ok: bool = True

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
            "zero_diff": self.zero_diff,
            "custom_modules": [m.to_dict() for m in self.custom_modules],
            "custom_modules_ok": self.custom_modules_ok,
            "local_customizations_reapply": (
                self.local_customizations_reapply.to_dict()
                if self.local_customizations_reapply
                else None
            ),
            "local_customizations_ok": self.local_customizations_ok,
        }


class InstallerRunner(Protocol):
    """Runs the installer argv in *repo*; ``env`` is the CAP-6 resolved environment."""

    def __call__(
        self,
        repo: Path,
        cmd: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]: ...


# Pre-14.6 injected runners take only ``(repo, cmd)``; they stay accepted and are
# called without ``env`` (see ``_call_installer_runner``).
LegacyInstallerRunner = Callable[[Path, Sequence[str]], subprocess.CompletedProcess[str]]


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
        raise UpgradeError(
            f"target version must be X.Y.Z or X.Y.Z-prerelease, got {version!r}"
        )
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


@dataclass(frozen=True)
class CustomModuleDef:
    """One release-catalog ``custom_modules`` entry (CAP-7, Story 14.7).

    The catalog only ANNOTATES: selection comes from the installed manifest.
    ``own_installer`` is the argv steward runs from the repo root after the
    core apply; ``config_paths`` are the module-owned files steward snapshots
    before and restores verbatim after; ``pin`` (optional) lands on the core
    argv as ``--pin <name>=<pin>``; ``packaged_source`` (optional, repo-relative)
    is used only to verify ``.claude/skills/<name>-*`` afterwards.
    """

    name: str
    own_installer: tuple[str, ...]
    config_paths: tuple[str, ...]
    pin: str | None
    packaged_source: str | None
    notes: str


def load_custom_modules(catalog: Mapping[str, Any]) -> tuple[CustomModuleDef, ...]:
    """Parse ``custom_modules`` from a loaded catalog (tolerant of a missing key).

    Raises ``UpgradeError`` naming the catalog key on a non-list value, a
    non-mapping entry, an empty ``name``, or an ``own_installer`` that is not a
    non-empty list of strings. ``pin`` is ``None`` unless a non-empty string.
    """
    raw = catalog.get("custom_modules") or []
    if not isinstance(raw, list):
        raise UpgradeError(
            f"release catalog key `custom_modules` must be a list, got {type(raw).__name__}"
        )
    out: list[CustomModuleDef] = []
    for index, entry in enumerate(raw):
        key = f"custom_modules[{index}]"
        if not isinstance(entry, Mapping):
            raise UpgradeError(f"release catalog key `{key}` is not a mapping")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise UpgradeError(f"release catalog key `{key}.name` must be a non-empty string")
        own = entry.get("own_installer")
        if (
            not isinstance(own, list)
            or not own
            or not all(isinstance(part, str) and part.strip() for part in own)
        ):
            raise UpgradeError(
                f"release catalog key `{key}.own_installer` must be a non-empty list "
                "of argv strings (e.g. [bmad-module-skill-forge, update])"
            )
        config_paths_raw = entry.get("config_paths") or []
        if not isinstance(config_paths_raw, list):
            raise UpgradeError(f"release catalog key `{key}.config_paths` must be a list")
        config_paths = tuple(
            str(p).replace("\\", "/") for p in config_paths_raw if str(p).strip()
        )
        pin_raw = entry.get("pin")
        pin = pin_raw.strip() if isinstance(pin_raw, str) and pin_raw.strip() else None
        source_raw = entry.get("packaged_source")
        packaged_source = (
            str(source_raw).replace("\\", "/")
            if isinstance(source_raw, str) and source_raw.strip()
            else None
        )
        out.append(
            CustomModuleDef(
                name=name.strip(),
                own_installer=tuple(part.strip() for part in own),
                config_paths=config_paths,
                pin=pin,
                packaged_source=packaged_source,
                notes=str(entry.get("notes") or "").strip(),
            )
        )
    return tuple(out)


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


def read_installed_modules(repo: Path) -> tuple[str, ...]:
    """Module names from ``modules:`` in ``_bmad/_config/manifest.yaml``.

    ``core`` first, manifest order otherwise, de-duplicated. Never hardcoded:
    every listed module (built-in and ``source: custom``) must be selected on
    the installer argv, because ``--action update -y`` deletes an installed
    custom module it is not told to keep (trap 13). An empty list is therefore
    a refusal, not a fallback — raised before any review branch exists.
    """
    manifest = repo / _MANIFEST_RELATIVE_PATH
    if not manifest.is_file():
        raise UpgradeError(f"missing installed manifest: {manifest}")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    names = [name for name, _source in _manifest_module_entries(data)]
    if not names:
        raise UpgradeError(
            f"manifest lists no modules ({manifest}) — refuse to apply: "
            "`bmad-method install --action update -y` deletes every installed "
            "module it is not told to select, so an apply that cannot name the "
            f"installed modules is the trap {TRAP_CUSTOM_MODULE_DESELECTED} shape"
        )
    if "core" in names:
        names.remove("core")
        names.insert(0, "core")
    return tuple(names)


def _manifest_module_entries(data: Any) -> list[tuple[str, str | None]]:
    """``(name, source)`` pairs from a parsed manifest's ``modules:`` list.

    Manifest order, de-duplicated on name (first occurrence wins). A bare
    string entry (``- bmm``) carries no ``source`` → ``None``; a missing or
    empty ``modules:`` yields ``[]``. Shared by ``read_installed_modules`` and
    ``read_installed_module_sources`` so the two never disagree.
    """
    raw = data.get("modules") or [] if isinstance(data, Mapping) else []
    out: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if isinstance(entry, Mapping):
            name = entry.get("name")
            source_raw = entry.get("source")
        else:
            name = entry
            source_raw = None
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        if name in seen:
            continue
        seen.add(name)
        source = (
            source_raw.strip()
            if isinstance(source_raw, str) and source_raw.strip()
            else None
        )
        out.append((name, source))
    return out


def read_installed_module_sources(repo: Path) -> dict[str, str | None]:
    """``{module name: source}`` from ``_bmad/_config/manifest.yaml`` (CAP-7).

    Never raises for a missing manifest or a missing/empty ``modules:`` —
    both yield ``{}``; the pre-flight is report-only and the apply already
    refused through ``read_installed_modules`` in that shape.
    """
    manifest = repo / _MANIFEST_RELATIVE_PATH
    if not manifest.is_file():
        return {}
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    return dict(_manifest_module_entries(data))


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


def _custom_module_findings(
    repo: Path, catalog: Mapping[str, Any]
) -> list[CustomModuleFinding]:
    """CAP-7 pre-flight: each catalog ``custom_modules`` entry vs the installed manifest.

    Four shapes: matched (catalog + manifest ``source: custom``); catalog names
    a module the manifest does not list; catalog names a module the manifest
    lists with another source; an installed ``source: custom`` module absent
    from the catalog (nothing would restore its config — trap 14). Malformed
    catalog entries raise ``UpgradeError`` here, before any review branch.
    """
    definitions = load_custom_modules(catalog)
    sources = read_installed_module_sources(repo)
    findings: list[CustomModuleFinding] = []
    for module in definitions:
        source = sources.get(module.name)
        trap_id = TRAP_CUSTOM_MODULE_DESELECTED
        if module.name not in sources:
            matched = False
            detail = (
                "catalog names it as a custom module but the installed manifest does "
                "not list it — nothing for the apply to select; stale catalog entry "
                f"or an already-deleted module (trap {TRAP_CUSTOM_MODULE_DESELECTED})"
            )
        elif source == "custom":
            matched = True
            detail = (
                "installed source: custom; own installer: "
                f"{' '.join(module.own_installer)}; config paths: "
                f"{', '.join(module.config_paths) or '(none)'}; "
                f"pin: {module.pin or '(none)'}"
            )
        else:
            matched = False
            detail = (
                f"installed with source {source!r}, not custom — the catalog's "
                "own-installer / config-restore handling does not apply; reconcile "
                f"the catalog or the manifest (trap {TRAP_CUSTOM_MODULE_DESELECTED})"
            )
        findings.append(
            CustomModuleFinding(
                name=module.name,
                in_catalog=True,
                manifest_source=source,
                matched=matched,
                own_installer=module.own_installer,
                pin=module.pin,
                detail=detail,
                trap_id=trap_id,
                notes=module.notes,
            )
        )
    catalog_names = {module.name for module in definitions}
    for name, source in sources.items():
        if source != "custom" or name in catalog_names:
            continue
        findings.append(
            CustomModuleFinding(
                name=name,
                in_catalog=False,
                manifest_source=source,
                matched=False,
                own_installer=(),
                pin=None,
                detail=(
                    "installed source: custom but absent from the release catalog's "
                    "custom_modules — the core apply would regenerate its config with "
                    "nothing to restore it and never run its own installer "
                    f"(trap {TRAP_CUSTOM_MODULE_CONFIG_REGENERATED}); add a catalog entry"
                ),
                trap_id=TRAP_CUSTOM_MODULE_CONFIG_REGENERATED,
            )
        )
    return findings


def default_installed_package_root(
    installed_version: str, *, cache_root: Path | None = None
) -> Path | None:
    """Best-effort glob for the CACHED INSTALLED version's unpacked bmad-method package.

    Never raises. Returns ``None`` when *cache_root* (default: the machine's
    rattler package cache) is not a directory or no matching package is found.
    """
    try:
        root = (
            cache_root if cache_root is not None else Path.home() / _RATTLER_PKGS_CACHE_RELATIVE_PATH
        )
        if not root.is_dir():
            return None
        for candidate in sorted(root.glob(f"bmad-method-{installed_version}-*")):
            pkg = candidate / "lib" / "node_modules" / "bmad-method"
            if pkg.is_dir():
                return pkg
        return None
    except (OSError, RuntimeError):
        # e.g. Path.home() cannot resolve a home directory — best-effort,
        # never an error (this scan is always optional).
        return None


def _find_packaged_skill_dir(package_root: Path, name: str) -> Path | None:
    """Locate installer-owned skill dir *name* under bmm-skills/ or core-skills/.

    Skips anything under a ``v6-shims`` subtree — those are never scanned or
    re-applied by CAP-8.
    """
    for sub in ("bmm-skills", "core-skills"):
        root = package_root / "src" / sub
        if not root.is_dir():
            continue
        for candidate in sorted(root.rglob(name)):
            if candidate.is_dir() and "v6-shims" not in candidate.relative_to(root).parts:
                return candidate
    return None


def _scripts_package_path(package_root: Path, script_name: str) -> Path:
    return package_root / "src" / "scripts" / script_name


def _is_pycache_noise(relpath: str) -> bool:
    """True when *relpath* is scan noise CAP-8 itself would otherwise re-flag.

    ``__pycache__`` dirs and ``.pyc``/``.pyo`` files churn on every interpreter
    run and are never a genuine in-place edit. A ``.customization-conflict``
    sibling is CAP-8's OWN prior-run output artifact — left behind by a
    conflicted re-apply, it has no packaged counterpart either, so without
    this exclusion it would self-pollute the next pre-flight scan as a "new"
    local customization. Neither is a genuine in-place edit.
    """
    if relpath.endswith((".pyc", ".pyo", ".customization-conflict")):
        return True
    return "__pycache__" in relpath.split("/")


def _skill_customization_findings(
    repo: Path, installed_package_root: Path, *, exclude: frozenset[str]
) -> list[LocalCustomizationFinding]:
    """CAP-8: every installed skill file that byte-differs from its package copy.

    *exclude* names paths already governed by CAP-3's marker-based mechanism
    (the catalog's ``upstream_touched_paths``) — never double-covered.
    """
    findings: list[LocalCustomizationFinding] = []
    for name in sorted(_read_installed_skill_names(repo)):
        installed_dir = repo / _IDE_SKILLS_RELATIVE_PATH / name
        if not installed_dir.is_dir():
            continue
        packaged_dir = _find_packaged_skill_dir(installed_package_root, name)
        if packaged_dir is None:
            continue
        installed_fp = _fingerprint_tree(installed_dir, installed_dir)
        packaged_fp = _fingerprint_tree(packaged_dir, packaged_dir)
        for relpath in sorted(set(installed_fp) | set(packaged_fp)):
            if _is_pycache_noise(relpath):
                continue
            if installed_fp.get(relpath) != packaged_fp.get(relpath):
                full_rel = str((installed_dir / relpath).relative_to(repo)).replace(
                    "\\", "/"
                )
                if full_rel in exclude:
                    continue
                findings.append(
                    LocalCustomizationFinding(
                        path=full_rel,
                        reason=(
                            "differs from the installed-version package copy — "
                            "installer-owned skill file edited in place"
                        ),
                    )
                )
    return findings


def _scripts_customization_findings(
    repo: Path, installed_package_root: Path, *, exclude: frozenset[str]
) -> list[LocalCustomizationFinding]:
    """CAP-8: every ``_bmad/scripts/*.py`` that byte-differs from its package copy.

    *exclude* names paths already governed by CAP-3's marker-based mechanism
    (the catalog's ``upstream_touched_paths``) — never double-covered.
    """
    scripts_dir = repo / "_bmad" / "scripts"
    if not scripts_dir.is_dir():
        return []
    findings: list[LocalCustomizationFinding] = []
    for path in sorted(scripts_dir.glob("*.py")):
        rel = str(path.relative_to(repo)).replace("\\", "/")
        if rel in exclude:
            continue
        packaged = _scripts_package_path(installed_package_root, path.name)
        if not packaged.is_file():
            continue
        if path.read_bytes() != packaged.read_bytes():
            findings.append(
                LocalCustomizationFinding(
                    path=rel,
                    reason=(
                        "differs from the installed-version package copy — "
                        "installer-owned script edited in place"
                    ),
                )
            )
    return findings


def _looks_like_bmad_method_package(root: Path) -> bool:
    """True when *root* contains at least one expected bmad-method subtree.

    A real, existing directory that lacks all three of ``src/bmm-skills``,
    ``src/core-skills``, and ``src/scripts`` is not a bmad-method package —
    it would otherwise silently scan to zero findings, indistinguishable
    from a genuinely clean repo (the exact trap-16 false-confidence CAP-8
    exists to prevent).
    """
    return any(
        (root / "src" / sub).is_dir() for sub in ("bmm-skills", "core-skills", "scripts")
    )


def _local_customization_findings(
    repo: Path, installed_package_root: Path | None, catalog: Mapping[str, Any]
) -> list[LocalCustomizationFinding]:
    """CAP-8: report-only scan of every installer-owned file for local edits.

    Returns ``[]`` (never raises) when no installed-package-root is resolvable
    — the scan is always optional.
    """
    if installed_package_root is None or not installed_package_root.is_dir():
        return []
    if not _looks_like_bmad_method_package(installed_package_root):
        return []
    exclude = frozenset(
        str(p).replace("\\", "/") for p in (catalog.get("upstream_touched_paths") or [])
    )
    return _skill_customization_findings(
        repo, installed_package_root, exclude=exclude
    ) + _scripts_customization_findings(repo, installed_package_root, exclude=exclude)


def build_preflight_report(
    *,
    repo: Path,
    target_version: str,
    installed_version: str | None = None,
    catalog_directory: Path | None = None,
    package_root: Path | None = None,
    installed_package_root: Path | None = None,
) -> PreflightReport:
    """Compute the report-only pre-flight for *target_version* against *repo*.

    Never mutates the filesystem. ``package_root``, when set, contributes a
    live ``removals.txt`` and upstream file comparison — still read-only.
    ``installed_package_root`` (CAP-8), when set or resolvable from the local
    rattler cache, additionally scans every installer-owned skill/script file
    for local edits — also report-only, and never required.
    """
    catalog = load_release_catalog(target_version, directory=catalog_directory)
    installed = installed_version or read_installed_version(repo)
    installed_skills = _read_installed_skill_names(repo)
    package_removals = load_package_removals(package_root) if package_root else None
    resolved_installed_root = installed_package_root or default_installed_package_root(
        installed
    )
    local_customizations = _local_customization_findings(
        repo, resolved_installed_root, catalog
    )

    skill_changes, removals = _skill_changes(
        catalog, installed_skills=installed_skills, package_removals=package_removals
    )
    locally_modified = _local_mod_findings(repo, catalog, package_root=package_root)
    legacy_custom = _legacy_custom_findings(repo, catalog)
    hard_prerequisites = _prerequisite_findings(catalog)
    forwarder_changes = _forwarder_findings(catalog)
    config_migration = _config_migration_finding(catalog)
    custom_modules = _custom_module_findings(repo, catalog)
    # CAP-9 (Story 14.9): preview-only — never a trap (see module docstring's
    # Design Notes in the story spec). Computed unconditionally, independent
    # of any --no-shims flag, so a plain pre-flight can audit it too.
    shims_to_retire = tuple(
        sorted(
            {
                name
                for name in (catalog.get("shims_to_retire") or [])
                if name in installed_skills
            }
        )
    )

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
    for finding in custom_modules:
        if not finding.matched:
            trap_ids.append(finding.trap_id)
    if local_customizations:
        trap_ids.append(TRAP_LOCAL_CUSTOMIZATION)

    notes: list[str] = [
        "report-only — no apply / no mutation of _bmad/ or _bmad/custom/**",
    ]
    if resolved_installed_root is None or not resolved_installed_root.is_dir():
        if resolved_installed_root is None:
            reason = (
                "no --installed-package-root and no cached package found for "
                f"installed version {installed}"
            )
        else:
            reason = f"--installed-package-root {resolved_installed_root} is not a directory"
        notes.append(
            f"local-customization scan skipped — {reason} (report-only, never required)"
        )
    elif not _looks_like_bmad_method_package(resolved_installed_root):
        notes.append(
            "local-customization scan skipped — --installed-package-root "
            f"{resolved_installed_root} exists but does not look like a bmad-method "
            "package (missing src/bmm-skills, src/core-skills, and src/scripts); "
            "'(none detected)' below reflects this skip, not a verified-clean scan "
            "(report-only, never required)"
        )
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
        custom_modules=tuple(custom_modules),
        local_customizations=tuple(local_customizations),
        shims_to_retire=shims_to_retire,
    )


def format_preflight(report: PreflightReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "steward upgrade bmad-core — pre-flight (report-only)",
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

    lines.extend(["", "## Custom modules (catalog vs installed manifest)"])
    if not report.custom_modules:
        lines.append("(none in catalog or manifest)")
    for custom in report.custom_modules:
        if custom.matched:
            lines.append(f"- [ok] {custom.name}: {custom.detail}")
        else:
            lines.append(
                f"- [MISMATCH] [trap {custom.trap_id}] {custom.name}: {custom.detail}"
            )
        if custom.notes:
            lines.append(f"  - catalog notes: {custom.notes}")

    lines.extend(["", "## Local customizations (installer-owned files edited in place)"])
    if not report.local_customizations:
        lines.append("(none detected — see Notes below if the scan was skipped)")
    for entry in report.local_customizations:
        lines.append(f"- [trap {entry.trap_id}] {entry.path}: {entry.reason}")

    lines.extend(
        ["", f"## Shims to retire (--no-shims candidates) [{len(report.shims_to_retire)}]"]
    )
    if not report.shims_to_retire:
        lines.append("(none)")
    for name in report.shims_to_retire:
        lines.append(f"- {name}")

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


def _fingerprint_tree(repo: Path, root: Path) -> dict[str, str]:
    """``{path relative to repo: sha256-hex}`` for every file under *root*.

    Pass ``root`` as *repo* too to key a tree by its own root (CAP-7 compares an
    installed skill dir against the packaged copy that way).
    """
    if not root.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo)).replace("\\", "/")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[rel] = digest
    return out


def fingerprint_custom_tree(repo: Path) -> dict[str, str]:
    """Return ``{relative_path: sha256-hex}`` for every file under ``_bmad/custom/**``."""
    return _fingerprint_tree(repo, repo / _CUSTOM_RELATIVE_PATH)


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
    repo: Path,
    cmd: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the real installer; steward never writes ``_bmad/bmm/**`` / ``_bmad/core/**``.

    CAP-6: stdin is closed (``DEVNULL``) so the installer can never sit on a
    prompt, and *env* is the environment ``resolve_installer_environment`` built.
    """
    return subprocess.run(
        list(cmd),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def resolve_installer_environment(
    repo: Path, installer_bin: str
) -> tuple[dict[str, str], str]:
    """Environment for the installer run plus a human note on how it resolved.

    ``<repo>/.pixi/envs/pyforge-guild/bin`` is prepended to ``PATH`` only when
    *installer_bin* and/or ``node`` are absent from the current ``PATH``; the
    directory is derived from *repo*, never a machine path.
    """
    env = dict(os.environ)
    wanted = (installer_bin, "node")
    missing = [name for name in wanted if shutil.which(name) is None]
    if not missing:
        return env, f"installer binaries resolved from PATH: {', '.join(wanted)}"
    pixi_bin = repo / _PIXI_LOCAL_RECIPES_BIN_RELATIVE_PATH
    current = env.get("PATH", "")
    env["PATH"] = (
        f"{pixi_bin}{os.pathsep}{current}" if current else str(pixi_bin)
    )
    return env, (
        f"installer binaries not on PATH ({', '.join(missing)}) — "
        f"prepended {pixi_bin} to PATH for the installer run"
    )


def _runner_accepts_env(runner: Callable[..., Any]) -> bool:
    """True when *runner* declares an ``env`` parameter or ``**kwargs``."""
    try:
        params = inspect.signature(runner).parameters.values()
    except (TypeError, ValueError):
        return False
    for param in params:
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            return True
        if param.name == "env" and param.kind in (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            return True
    return False


def _call_installer_runner(
    runner: InstallerRunner | LegacyInstallerRunner,
    repo: Path,
    cmd: Sequence[str],
    *,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    """Pass ``env`` only to runners that accept it — two-positional fakes stay accepted."""
    if _runner_accepts_env(runner):
        return runner(repo, cmd, env=env)  # type: ignore[call-arg]
    return runner(repo, cmd)  # type: ignore[call-arg]


# ── Story 14.7 / CAP-7 — custom modules survive the core apply ─────────────

# Cap on the reported `[modules.<name>]` unified diff (report payload hygiene).
_CONFIG_TOML_DIFF_CAP = 4000


def _snapshot_custom_module_configs(
    repo: Path, modules: Sequence[CustomModuleDef]
) -> dict[str, dict[str, bytes | None]]:
    """Pre-installer bytes of every catalog ``config_paths`` entry (``None`` = absent)."""
    out: dict[str, dict[str, bytes | None]] = {}
    for module in modules:
        per_path: dict[str, bytes | None] = {}
        for rel in module.config_paths:
            path = repo / rel
            per_path[rel] = path.read_bytes() if path.is_file() else None
        out[module.name] = per_path
    return out


def _read_config_toml_text(repo: Path) -> str:
    path = repo / _CONFIG_TOML_RELATIVE_PATH
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _config_toml_module_block(text: str, name: str) -> str:
    """Lines of the ``[modules.<name>]`` table (header through the next table header)."""
    header = f"[modules.{name}]"
    block: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == header:
            inside = True
            block.append(line)
            continue
        if inside:
            if stripped.startswith("[") and stripped.endswith("]"):
                break
            block.append(line)
    return "\n".join(block).rstrip() + "\n" if block else ""


def _config_toml_block_diff(before: str, after: str, name: str) -> str:
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{_CONFIG_TOML_RELATIVE_PATH} [modules.{name}] (pre-apply)",
            tofile=f"{_CONFIG_TOML_RELATIVE_PATH} [modules.{name}] (post-apply)",
        )
    )
    if len(diff) > _CONFIG_TOML_DIFF_CAP:
        diff = diff[:_CONFIG_TOML_DIFF_CAP] + "\n… (diff truncated)\n"
    return diff


def _restore_custom_module_configs(
    repo: Path,
    snapshots: Mapping[str, bytes | None],
) -> tuple[ConfigRestore, ...]:
    """Write each snapshotted path back verbatim; report restored / unchanged / missing."""
    restores: list[ConfigRestore] = []
    for rel, before in snapshots.items():
        path = repo / rel
        if before is None:
            restores.append(
                ConfigRestore(
                    path=rel,
                    status="missing",
                    detail="absent before apply — nothing to restore",
                )
            )
            continue
        after = path.read_bytes() if path.is_file() else None
        if after == before:
            restores.append(
                ConfigRestore(
                    path=rel,
                    status="unchanged",
                    detail="the core installer left it unchanged",
                )
            )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(before)
        what = "regenerated" if after is not None else "deleted"
        restores.append(
            ConfigRestore(
                path=rel,
                status="restored",
                detail=(
                    f"pre-apply bytes restored verbatim ({len(before)} bytes) — the core "
                    f"installer {what} it (trap {TRAP_CUSTOM_MODULE_CONFIG_REGENERATED})"
                ),
            )
        )
    return tuple(restores)


def _run_own_installer(
    repo: Path,
    module: CustomModuleDef,
    runner: InstallerRunner | LegacyInstallerRunner,
    *,
    spawned_by_steward: bool,
) -> tuple[int | None, str | None, tuple[str, ...]]:
    """Run the module's own installer from the repo root; never raise.

    Returns ``(exit_code, error, notes)``: an unresolvable binary (default
    runner only) or an ``OSError`` from the spawn yields ``(None, <error>, …)``.
    """
    binary = module.own_installer[0]
    env, env_note = resolve_installer_environment(repo, binary)
    notes = [f"{module.name} own installer: {env_note}"]
    if spawned_by_steward and shutil.which(binary, path=env["PATH"]) is None:
        return (
            None,
            (
                f"own installer binary {binary!r} not found on PATH (searched including "
                f"{repo / _PIXI_LOCAL_RECIPES_BIN_RELATIVE_PATH}) — module tree not rebuilt"
            ),
            tuple(notes),
        )
    try:
        result = _call_installer_runner(runner, repo, module.own_installer, env=env)
    except OSError as exc:
        return (
            None,
            f"own installer {' '.join(module.own_installer)} could not be spawned: {exc}",
            tuple(notes),
        )
    if result.stdout and result.stdout.strip():
        notes.append(
            f"{module.name} own installer stdout (truncated): {result.stdout.strip()[:500]}"
        )
    if result.stderr and result.stderr.strip():
        notes.append(
            f"{module.name} own installer stderr (truncated): {result.stderr.strip()[:500]}"
        )
    return int(result.returncode), None, tuple(notes)


def _verify_custom_module_skill_dirs(
    repo: Path, module: CustomModuleDef
) -> tuple[SkillDirVerification | None, tuple[str, ...]]:
    """Compare every packaged ``<name>-*`` dir with ``.claude/skills/<dir>`` (finding only)."""
    if not module.packaged_source:
        return None, (
            f"{module.name}: no packaged_source in the catalog — skill-dir verification skipped",
        )
    source = repo / module.packaged_source
    if not source.is_dir():
        return None, (
            f"{module.name}: packaged source {module.packaged_source} absent — "
            "skill-dir verification skipped",
        )
    prefix = f"{module.name}-"
    installed_root = repo / _IDE_SKILLS_RELATIVE_PATH
    names = sorted(p.name for p in source.iterdir() if p.is_dir() and p.name.startswith(prefix))
    if not names:
        return None, (
            f"{module.name}: packaged source {module.packaged_source} holds no "
            f"{prefix}* dirs — skill-dir verification skipped",
        )
    equal = 0
    mismatched: list[str] = []
    missing: list[str] = []
    for name in names:
        installed = installed_root / name
        if not installed.is_dir():
            missing.append(name)
            continue
        packaged = source / name
        if _fingerprint_tree(installed, installed) == _fingerprint_tree(packaged, packaged):
            equal += 1
        else:
            mismatched.append(name)
    verification = SkillDirVerification(
        packaged_source=module.packaged_source,
        expected=len(names),
        equal=equal,
        mismatched=tuple(mismatched),
        missing=tuple(missing),
        ok=not mismatched and not missing,
    )
    if verification.ok:
        return verification, ()
    return verification, (
        f"{module.name}: {_IDE_SKILLS_RELATIVE_PATH}/{prefix}* differs from the packaged "
        f"source {module.packaged_source} — mismatched: {', '.join(mismatched) or '(none)'}; "
        f"missing: {', '.join(missing) or '(none)'} (finding only — does not gate ok)",
    )


def _run_custom_module_phase(
    repo: Path,
    *,
    definitions: Sequence[CustomModuleDef],
    module_sources: Mapping[str, str | None],
    selected_modules: Sequence[str],
    config_snapshots: Mapping[str, Mapping[str, bytes | None]],
    config_toml_before: str,
    core_exit: int,
    core_changed: bool,
    runner: InstallerRunner | LegacyInstallerRunner,
    spawned_by_steward: bool,
) -> tuple[tuple[CustomModuleReport, ...], tuple[str, ...]]:
    """CAP-7 after the core installer: restore configs, own installer, verify, diff.

    Order matters: the config restore runs FIRST because the own installer
    preserves an existing config file verbatim and only appends its own keys
    (the 2026-09-06 live recovery order). The own installer runs only when the
    core installer exited 0 and changed something — a zero-diff core run stays
    the trap-12 refusal it already is, and a failed core apply is not rebuilt on.
    """
    reports: list[CustomModuleReport] = []
    phase_notes: list[str] = []
    config_toml_after = _read_config_toml_text(repo)

    for module in definitions:
        source = module_sources.get(module.name)
        selected = module.name in selected_modules and source == "custom"
        if not selected:
            why = (
                "does not list it"
                if module.name not in module_sources
                else f"lists it with source {source!r}, not custom"
            )
            reports.append(
                CustomModuleReport(
                    name=module.name,
                    selected=False,
                    pin=module.pin,
                    config_paths=(),
                    own_installer_cmd=module.own_installer,
                    own_installer_exit=None,
                    own_installer_error=None,
                    verification=None,
                    config_toml_block_changed=False,
                    config_toml_block_diff="",
                    ok=True,
                    notes=(
                        f"catalog names {module.name} but the installed manifest {why} — "
                        "not selected; nothing snapshotted, restored or run "
                        f"(trap {TRAP_CUSTOM_MODULE_DESELECTED} finding in the pre-flight)",
                    ),
                )
            )
            continue

        module_notes: list[str] = []
        restores = _restore_custom_module_configs(
            repo, config_snapshots.get(module.name, {})
        )

        exit_code: int | None
        error: str | None
        if core_exit != 0:
            exit_code, error = None, (
                f"skipped — core installer exited {core_exit}; the module tree is not "
                "rebuilt on a failed core apply"
            )
        elif not core_changed:
            exit_code, error = None, (
                "skipped — core installer exited 0 but changed nothing "
                f"(trap {TRAP_SILENT_NOOP_APPLY}); refuse to run the own installer on a "
                "no-op apply"
            )
        else:
            exit_code, error, run_notes = _run_own_installer(
                repo, module, runner, spawned_by_steward=spawned_by_steward
            )
            module_notes.extend(run_notes)

        verification, verify_notes = _verify_custom_module_skill_dirs(repo, module)
        module_notes.extend(verify_notes)
        if verification is not None and not verification.ok:
            phase_notes.append(
                f"custom module {module.name}: skill dirs differ from the packaged source "
                f"({module.packaged_source}) — mismatched: "
                f"{', '.join(verification.mismatched) or '(none)'}; missing: "
                f"{', '.join(verification.missing) or '(none)'} (finding, not a gate)"
            )

        block_before = _config_toml_module_block(config_toml_before, module.name)
        block_after = _config_toml_module_block(config_toml_after, module.name)
        block_changed = block_before != block_after
        block_diff = (
            _config_toml_block_diff(block_before, block_after, module.name)
            if block_changed
            else ""
        )
        if block_changed:
            module_notes.append(
                f"the core installer regenerated the [modules.{module.name}] block of "
                f"{_CONFIG_TOML_RELATIVE_PATH} (trap {TRAP_CUSTOM_MODULE_CONFIG_REGENERATED}) "
                "— reported as a diff, never edited by steward; durable answers belong "
                "in _bmad/custom/config.toml"
            )

        ok = exit_code == 0 and all(r.status in ("restored", "unchanged") for r in restores)
        reports.append(
            CustomModuleReport(
                name=module.name,
                selected=True,
                pin=module.pin,
                config_paths=restores,
                own_installer_cmd=module.own_installer,
                own_installer_exit=exit_code,
                own_installer_error=error,
                verification=verification,
                config_toml_block_changed=block_changed,
                config_toml_block_diff=block_diff,
                ok=ok,
                notes=tuple(module_notes),
            )
        )
        restored = [r.path for r in restores if r.status == "restored"]
        summary = "; ".join(f"{r.path}: {r.status}" for r in restores) or "(no config paths)"
        exit_text = f"exit {exit_code}" if exit_code is not None else f"not run ({error})"
        phase_notes.append(
            f"custom module {module.name}: {'ok' if ok else 'NOT ok'} — config paths "
            f"{summary}; own installer {' '.join(module.own_installer)} {exit_text}"
            + (
                f"; restored {', '.join(restored)} after the core installer regenerated "
                f"it (trap {TRAP_CUSTOM_MODULE_CONFIG_REGENERATED})"
                if restored
                else ""
            )
        )

    catalog_names = {module.name for module in definitions}
    for name, source in module_sources.items():
        if source == "custom" and name not in catalog_names:
            phase_notes.append(
                f"installed custom module {name} is absent from the release catalog's "
                "custom_modules — its config was not snapshotted or restored and its own "
                f"installer did not run (trap {TRAP_CUSTOM_MODULE_CONFIG_REGENERATED}); "
                "add a catalog entry"
            )
    return tuple(reports), tuple(phase_notes)



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



def _three_way_merge(*, ours: bytes, base: bytes, theirs: bytes) -> tuple[bool, bytes]:
    """Real ``git merge-file -p ours base theirs`` in a temp dir; never mocked.

    Returns ``(clean, output_bytes)`` — ``output_bytes`` is the merged content
    on a clean merge (exit 0) or the raw conflict-marker output otherwise.
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "ours").write_bytes(ours)
        (tmp / "base").write_bytes(base)
        (tmp / "theirs").write_bytes(theirs)
        result = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                "-L",
                "repo customization",
                "-L",
                "old upstream (installed)",
                "-L",
                "new upstream (target)",
                str(tmp / "ours"),
                str(tmp / "base"),
                str(tmp / "theirs"),
            ],
            capture_output=True,
            check=False,
        )
    return result.returncode == 0, result.stdout


def snapshot_local_customizations(
    repo: Path, findings: Sequence[LocalCustomizationFinding]
) -> dict[str, bytes | None]:
    """Pre-apply bytes for every CAP-8-flagged file (``None`` when absent)."""
    return {
        f.path: ((repo / f.path).read_bytes() if (repo / f.path).is_file() else None)
        for f in findings
    }


def _installer_owned_package_paths(
    rel: str, *, old_root: Path, new_root: Path
) -> tuple[Path | None, Path | None]:
    """Map a CAP-8-flagged repo-relative path to its old/new packaged counterparts."""
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == ".claude" and parts[1] == "skills":
        name = parts[2]
        rest = Path(*parts[3:]) if len(parts) > 3 else None
        old_skill = _find_packaged_skill_dir(old_root, name)
        new_skill = _find_packaged_skill_dir(new_root, name)
        return (
            (old_skill / rest) if old_skill and rest is not None else old_skill,
            (new_skill / rest) if new_skill and rest is not None else new_skill,
        )
    if len(parts) == 3 and parts[0] == "_bmad" and parts[1] == "scripts" and rel.endswith(".py"):
        return (
            _scripts_package_path(old_root, parts[2]),
            _scripts_package_path(new_root, parts[2]),
        )
    return None, None


def reapply_local_customizations(
    repo: Path,
    *,
    pre_apply_snapshots: Mapping[str, bytes | None],
    installed_package_root: Path | None,
    package_root: Path | None,
) -> CustomizationReapplyReport:
    """CAP-8: three-way-merge every pre-flight-flagged file after the core installer ran.

    ``ours`` = the pre-apply snapshot (the repo's customization); ``base`` =
    the old (installed) package's matching copy; ``theirs`` = the new
    (target) package's matching copy. A clean merge (real ``git merge-file``,
    exit 0) lands the merged bytes in the repo; a conflict leaves the repo
    file exactly as the core installer wrote it and writes the raw conflict
    markers to a ``<path>.customization-conflict`` sibling.
    """
    if not pre_apply_snapshots:
        return CustomizationReapplyReport(findings=(), all_clean=True, notes=())
    if (
        installed_package_root is None
        or not installed_package_root.is_dir()
        or package_root is None
        or not package_root.is_dir()
    ):
        return CustomizationReapplyReport(
            findings=(),
            all_clean=True,
            notes=(
                (
                    "local-customization re-apply skipped — --installed-package-root "
                    "and/or --package-root unavailable"
                ),
            ),
        )

    findings: list[CustomizationReapplyFinding] = []
    for rel, ours in pre_apply_snapshots.items():
        # Clear any stale sibling left by a prior apply attempt; the conflict
        # branch below re-writes it fresh if THIS run's outcome is itself a
        # conflict — a customization that is no longer conflicted must never
        # keep looking conflicted.
        stale_conflict = repo / f"{rel}.customization-conflict"
        if stale_conflict.is_file():
            stale_conflict.unlink()

        if ours is None:
            findings.append(
                CustomizationReapplyFinding(
                    path=rel,
                    action="skipped_no_snapshot",
                    detail="file absent before apply — nothing to re-apply",
                )
            )
            continue

        target = repo / rel

        # Checked before the package-match lookup below: a more specific
        # diagnostic than `skipped_no_package_match` when both conditions
        # hold (e.g. a retired/renamed file the installer deleted AND that
        # has no packaged counterpart on one or both sides).
        if not target.is_file():
            findings.append(
                CustomizationReapplyFinding(
                    path=rel,
                    action="skipped_installer_removed_file",
                    detail=(
                        "installer removed this file outright — not re-created; "
                        "the pre-apply snapshot is not merged back"
                    ),
                )
            )
            continue

        old_path, new_path = _installer_owned_package_paths(
            rel, old_root=installed_package_root, new_root=package_root
        )
        old_missing = old_path is None or not old_path.is_file()
        new_missing = new_path is None or not new_path.is_file()
        if old_missing or new_missing:
            side = "old (--installed-package-root)" if old_missing else "new (--package-root)"
            findings.append(
                CustomizationReapplyFinding(
                    path=rel,
                    action="skipped_no_package_match",
                    detail=f"no matching packaged file on the {side} side",
                )
            )
            continue

        if target.read_bytes() == ours:
            findings.append(
                CustomizationReapplyFinding(
                    path=rel,
                    action="unchanged",
                    detail="installer left this flagged file untouched",
                )
            )
            continue

        assert old_path is not None and new_path is not None  # narrowed above
        clean, output = _three_way_merge(
            ours=ours, base=old_path.read_bytes(), theirs=new_path.read_bytes()
        )
        if clean:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(output)
            findings.append(
                CustomizationReapplyFinding(
                    path=rel,
                    action="merged_clean",
                    detail="three-way merge (repo edit + upstream delta) applied cleanly",
                )
            )
        else:
            conflict_rel = f"{rel}.customization-conflict"
            conflict_path = repo / conflict_rel
            conflict_path.parent.mkdir(parents=True, exist_ok=True)
            conflict_path.write_bytes(output)
            findings.append(
                CustomizationReapplyFinding(
                    path=rel,
                    action="conflict_needs_manual_merge",
                    detail=(
                        "three-way merge conflicted — repo bytes left as the installer "
                        f"wrote them; conflict markers written to {conflict_rel}"
                    ),
                    conflict_path=conflict_rel,
                )
            )

    all_clean = not any(f.action == "conflict_needs_manual_merge" for f in findings)
    return CustomizationReapplyReport(findings=tuple(findings), all_clean=all_clean, notes=())


def reconcile_clobbered_custom_surfaces(
    repo: Path,
    catalog: Mapping[str, Any],
    *,
    pre_apply_snapshots: Mapping[str, str],
    installed_package_root: Path | None = None,
    package_root: Path | None = None,
) -> ReconcileReport:
    """Detect clobbered surfaces; restore from ``.bak`` or snapshot; else flag."""
    markers = [str(m) for m in (catalog.get("repo_custom_markers") or [])]
    touched = [str(p).replace("\\", "/") for p in (catalog.get("upstream_touched_paths") or [])]
    bak_accounted = list(list_installer_bak_files(repo, touched))

    findings: list[ClobberFinding] = []
    notes: list[str] = []
    delta_replay_conflicts: list[str] = []
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

        # CAP-8 amendment (Story 14.8): replay the old→new upstream delta onto
        # the just-restored bytes instead of leaving a bare restore. Either
        # root missing ⇒ byte-identical to pre-14.8 behavior (regression guard).
        if action in ("restored_from_bak", "restored_from_snapshot") and (
            installed_package_root is not None and package_root is not None
        ):
            old_p = _scripts_package_path(installed_package_root, Path(rel).name)
            new_p = _scripts_package_path(package_root, Path(rel).name)
            if old_p.is_file() and new_p.is_file():
                clean, output = _three_way_merge(
                    ours=path.read_bytes(),
                    base=old_p.read_bytes(),
                    theirs=new_p.read_bytes(),
                )
                if clean:
                    path.write_bytes(output)
                    detail += " + upstream delta replayed"
                else:
                    detail += " + upstream delta conflict (see notes)"
                    delta_replay_conflicts.append(rel)
                    notes.append(
                        f"upstream delta conflict for {rel} — plain restore kept, "
                        "no .customization-conflict sibling written for this "
                        "marker-based path"
                    )
            else:
                notes.append(
                    f"delta-replay skipped for {rel} — no matching packaged file on "
                    f"the old (--installed-package-root, is_file={old_p.is_file()}) "
                    f"and/or new (--package-root, is_file={new_p.is_file()}) side; "
                    "plain restore kept"
                )

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
        and not delta_replay_conflicts
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
    installed_package_root: Path | None = None,
    installer_bin: str = "bmad-method",
    installer_runner: InstallerRunner | LegacyInstallerRunner | None = None,
    custom_installer_runner: InstallerRunner | LegacyInstallerRunner | None = None,
    no_shims: bool = False,
) -> ApplyReport:
    """CAP-2+3+6+7+8+9 deliberate apply: preflight → branch → installer → custom modules → custom check → CAP-3 reconcile.

    The installer command is always ``bmad-method install --action update -y
    --directory <repo> --modules <every module the manifest lists, core first>
    [--pin <name>=<pin> …]`` (or *installer_bin* override). Steward never
    reimplements writing ``_bmad/bmm/**`` or ``_bmad/core/**``. An exit-0 run
    that changed nothing is reported as ``zero_diff`` — a refusal, never a
    green (trap 12), judged on the core installer's diff alone.

    CAP-7: each catalog ``custom_modules`` entry the manifest lists with
    ``source: custom`` has its config paths snapshotted before the core
    installer and restored verbatim after, then its own installer runs from
    the repo root through *custom_installer_runner* (default:
    ``default_installer_runner``); the only bytes steward itself writes in
    that phase are the restored config paths.

    CAP-9: ``no_shims=True`` appends a literal ``--no-shims`` to the installer
    argv (right after ``--modules``, before any ``--pin`` pair), asking the
    installer to retire the release's deprecation shims (``installShims:
    false``); the sole refusal is the pre-existing trap-2 legacy-custom check
    above, which already halts unconditionally regardless of ``no_shims``.
    """
    assert_clean_tree(repo)

    preflight = build_preflight_report(
        repo=repo,
        target_version=target_version,
        installed_version=installed_version,
        catalog_directory=catalog_directory,
        package_root=package_root,
        installed_package_root=installed_package_root,
    )
    # CAP-8: re-derive the same cheap glob rather than growing PreflightReport's
    # shape just to carry a Path through.
    resolved_installed_root = installed_package_root or default_installed_package_root(
        preflight.installed_version
    )
    refuse_legacy_custom(preflight)
    # CAP-6: refuse before any branch exists when the manifest names no modules.
    modules = read_installed_modules(repo)
    # CAP-7: one source of truth for `--modules` — the manifest. Assert every
    # `source: custom` module is on it rather than adding a second selection path.
    module_sources = read_installed_module_sources(repo)
    unselected_custom = [
        name for name, source in module_sources.items()
        if source == "custom" and name not in modules
    ]
    if unselected_custom:
        raise UpgradeError(
            f"installed custom module(s) {', '.join(unselected_custom)} would not be "
            "selected on the installer argv — `--action update -y` deletes an unselected "
            f"cached custom module (trap {TRAP_CUSTOM_MODULE_DESELECTED}); refuse to apply "
            "before any review branch exists"
        )
    # CAP-6: resolve the installer environment before any branch exists. When
    # steward itself will spawn the installer, an unresolvable binary is a
    # refusal here — not a FileNotFoundError on a freshly switched checkout.
    env, env_note = resolve_installer_environment(repo, installer_bin)
    if installer_runner is None and shutil.which(installer_bin, path=env["PATH"]) is None:
        raise UpgradeError(
            f"installer binary {installer_bin!r} not found on PATH (searched "
            f"including {repo / _PIXI_LOCAL_RECIPES_BIN_RELATIVE_PATH}) — "
            "refuse to apply before any review branch exists"
        )

    review_branch = branch or default_apply_branch(target_version)
    custom_before = fingerprint_custom_tree(repo)
    catalog = load_release_catalog(
        target_version, directory=catalog_directory
    )
    # CAP-7: the catalog annotates; the manifest selects. Validated in the
    # pre-flight already (a malformed entry raised there, before any branch).
    custom_module_defs = load_custom_modules(catalog)
    installed_custom_defs = [
        module for module in custom_module_defs
        if module.name in modules and module_sources.get(module.name) == "custom"
    ]
    surface_snapshots = snapshot_repo_custom_surfaces(repo, catalog)
    # CAP-8: snapshot every pre-flight-flagged local customization's bytes at
    # the same point as the other pre-apply snapshots, before the core
    # installer runs.
    local_customization_pre_snapshots = snapshot_local_customizations(
        repo, preflight.local_customizations
    )
    config_snapshots = _snapshot_custom_module_configs(repo, installed_custom_defs)
    config_toml_before = _read_config_toml_text(repo)
    snapshot_sha = create_review_branch(repo, review_branch)

    modules_csv = ",".join(modules)
    pins = [f"{module.name}={module.pin}" for module in installed_custom_defs if module.pin]
    installer_cmd = (
        installer_bin,
        "install",
        "--action",
        "update",
        "-y",
        "--directory",
        str(repo.resolve()),
        "--modules",
        modules_csv,
        *(("--no-shims",) if no_shims else ()),
        *(part for pin in pins for part in ("--pin", pin)),
    )
    runner = installer_runner or default_installer_runner
    result = _call_installer_runner(runner, repo, installer_cmd, env=env)

    notes: list[str] = [
        "deliberate apply — installer diff left on review branch for human review "
        "(never merged/applied blind)",
        "steward did not write _bmad/bmm/** or _bmad/core/** — installer is sole writer",
        f"installer argv: {' '.join(installer_cmd)}",
    ]
    if no_shims:
        notes.append(
            "--no-shims requested: shim retirement is judged by the same trap-12 "
            "zero-diff refusal as any other apply — a same-version run that actually "
            "removes shim directories is a real diff, never treated as a no-op"
        )
    notes.extend(
        [
            (
                "installer modules selected from the installed manifest (core first): "
                f"{modules_csv} — every listed module is selected so `--action update -y` "
                f"cannot deselect a cached custom module (trap {TRAP_CUSTOM_MODULE_DESELECTED})"
            ),
            env_note,
        ]
    )
    if pins:
        notes.append(
            f"catalog pins on the installer argv: {', '.join(pins)} — stops the "
            "channel-cache drift for those custom modules at module-selection time"
        )
    if result.stdout and result.stdout.strip():
        notes.append(f"installer stdout (truncated): {result.stdout.strip()[:500]}")
    if result.stderr and result.stderr.strip():
        notes.append(f"installer stderr (truncated): {result.stderr.strip()[:500]}")

    if result.returncode != 0:
        notes.append(
            f"installer exited {result.returncode} — review branch {review_branch} "
            "still holds any partial diff; custom check follows"
        )

    # CAP-6: zero-diff is judged on the CORE installer's diff, before the CAP-7
    # phase — the own installer must never mask a trap-12 no-op as a "diff".
    core_changed = list_changed_paths(repo)
    zero_diff = result.returncode == 0 and not core_changed
    if zero_diff:
        notes.append(
            "installer exited 0 but changed nothing — a cancelled prompt or a no-op; "
            f"refuse to call this green (trap {TRAP_SILENT_NOOP_APPLY}); the checkout "
            f"was switched to review branch {review_branch} and is left there for the "
            "operator to inspect or delete"
        )

    # CAP-7: restore each custom module's config, run its own installer, verify.
    custom_modules, phase_notes = _run_custom_module_phase(
        repo,
        definitions=custom_module_defs,
        module_sources=module_sources,
        selected_modules=modules,
        config_snapshots=config_snapshots,
        config_toml_before=config_toml_before,
        core_exit=int(result.returncode),
        core_changed=bool(core_changed),
        runner=custom_installer_runner or default_installer_runner,
        spawned_by_steward=custom_installer_runner is None,
    )
    notes.extend(phase_notes)
    custom_modules_ok = all(module.ok for module in custom_modules if module.selected)

    # CAP-8: three-way re-apply every pre-flight-flagged local customization
    # after the core installer (and the CAP-7 custom-module phase) ran.
    local_reapply = reapply_local_customizations(
        repo,
        pre_apply_snapshots=local_customization_pre_snapshots,
        installed_package_root=resolved_installed_root,
        package_root=package_root,
    )
    notes.extend(local_reapply.notes)

    # Recomputed AFTER the custom-module phase so the custom check and the
    # review surface cover the own installer's output too.
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
    elif not zero_diff:
        notes.append("installer produced no working-tree changes")

    reconcile = reconcile_clobbered_custom_surfaces(
        repo,
        catalog,
        pre_apply_snapshots=surface_snapshots,
        installed_package_root=resolved_installed_root,
        package_root=package_root,
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
        zero_diff=zero_diff,
        custom_modules=custom_modules,
        custom_modules_ok=custom_modules_ok,
        local_customizations_reapply=local_reapply,
        local_customizations_ok=local_reapply.all_clean,
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
    ]
    if report.zero_diff:
        lines.append(
            "zero-diff: REFUSED — installer exited 0 and changed nothing "
            f"(trap {TRAP_SILENT_NOOP_APPLY}); branch {report.branch} left in place"
        )
    lines.extend([
        "",
        "## Review surface (installer diff paths)",
    ])
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

    lines.extend(["", "## CAP-7 custom modules"])
    if not report.custom_modules:
        lines.append("(none in catalog)")
    else:
        lines.append(f"custom_modules_ok={report.custom_modules_ok}")
    for module in report.custom_modules:
        lines.append(
            f"- {module.name}: selected={module.selected} "
            f"pin={module.pin or '(none)'} ok={module.ok}"
        )
        for restore in module.config_paths:
            lines.append(f"  - config {restore.path}: {restore.status} — {restore.detail}")
        if module.selected:
            exit_text = (
                f"exit {module.own_installer_exit}"
                if module.own_installer_exit is not None
                else f"not run — {module.own_installer_error}"
            )
            lines.append(
                f"  - own installer: {' '.join(module.own_installer_cmd)} ({exit_text})"
            )
            verification = module.verification
            if verification is None:
                lines.append("  - skill-dir verification: skipped")
            else:
                extra = ""
                if verification.mismatched:
                    extra += f"; mismatched: {', '.join(verification.mismatched)}"
                if verification.missing:
                    extra += f"; missing: {', '.join(verification.missing)}"
                lines.append(
                    f"  - skill-dir verification: {verification.equal}/{verification.expected} "
                    f"equal to {verification.packaged_source} ok={verification.ok}{extra}"
                )
            block_state = (
                "CHANGED by the installer (reported, never edited)"
                if module.config_toml_block_changed
                else "unchanged"
            )
            lines.append(
                f"  - {_CONFIG_TOML_RELATIVE_PATH} [modules.{module.name}]: {block_state}"
            )
            for diff_line in module.config_toml_block_diff.rstrip("\n").splitlines():
                lines.append(f"    {diff_line}")
        for note in module.notes:
            lines.append(f"  - note: {note}")

    lines.extend(["", "## CAP-8 local customizations re-applied"])
    reapply = report.local_customizations_reapply
    if reapply is None or not reapply.findings:
        lines.append("(none flagged)")
    else:
        for reapply_finding in reapply.findings:
            lines.append(
                f"- [{reapply_finding.action}] {reapply_finding.path}: "
                f"{reapply_finding.detail}"
            )
            if reapply_finding.conflict_path:
                lines.append(f"    conflict file: {reapply_finding.conflict_path}")

    if report.notes:
        lines.extend(["", "## Notes"])
        for note in report.notes:
            lines.append(f"- {note}")

    # Include the CAP-1 preflight body for the review checklist.
    lines.extend(["", "--- CAP-1 preflight consumed by this apply ---", ""])
    lines.append(format_preflight(report.preflight, as_json=False).rstrip())
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CAP-4 — pin fan-out report (report-only; foreign sites never edited)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PinSiteDef:
    """One enumerated pin site from the 2026-08-21 trap-5 inventory."""

    site_id: str
    package: str  # bmad-loop | bmad-method
    path: str
    kind: str
    foreign: bool


# Exact trap-5 site list the report must name (fixtures assert this set).
# Loop-home relays are dynamic (one row per home) under site_id prefix
# ``loop-home-relay:``.
KNOWN_PIN_SITES: tuple[PinSiteDef, ...] = (
    PinSiteDef(
        site_id="root-pixi-floor:bmad-loop",
        package="bmad-loop",
        path=str(_PIN_ROOT_PIXI),
        kind="pixi_floor",
        foreign=False,
    ),
    PinSiteDef(
        site_id="root-pixi-floor:bmad-method",
        package="bmad-method",
        path=str(_PIN_ROOT_PIXI),
        kind="pixi_floor",
        foreign=False,
    ),
    PinSiteDef(
        site_id="marshal-pyproject:bmad-loop",
        package="bmad-loop",
        path=str(_PIN_MARSHAL_PYPROJECT),
        kind="pyproject_dep",
        foreign=True,
    ),
    PinSiteDef(
        site_id="marshal-pixi:bmad-loop",
        package="bmad-loop",
        path=str(_PIN_MARSHAL_PIXI),
        kind="pixi_run_dep",
        foreign=True,
    ),
    PinSiteDef(
        site_id="harness-version-range:bmad-loop",
        package="bmad-loop",
        path=str(_PIN_HARNESS),
        kind="harness_constant",
        foreign=True,
    ),
    PinSiteDef(
        site_id="seed-manifest:bmad-loop",
        package="bmad-loop",
        path=str(_PIN_SEED_MANIFEST),
        kind="seed_manifest",
        foreign=True,
    ),
    PinSiteDef(
        site_id="seed-manifest:bmad-method",
        package="bmad-method",
        path=str(_PIN_SEED_MANIFEST),
        kind="seed_manifest",
        foreign=True,
    ),
    PinSiteDef(
        site_id="drift-test-map:bmad-loop",
        package="bmad-loop",
        path=str(_PIN_DRIFT_TEST),
        kind="drift_test_map",
        foreign=True,
    ),
    PinSiteDef(
        site_id="drift-test-map:bmad-method",
        package="bmad-method",
        path=str(_PIN_DRIFT_TEST),
        kind="drift_test_map",
        foreign=True,
    ),
)


@dataclass(frozen=True)
class PinSiteStatus:
    """Moved / not-moved status for one known pin site."""

    site_id: str
    path: str
    kind: str
    package: str
    foreign: bool
    current_value: str | None
    status: str  # moved | not_moved | missing | unknown | stale | current
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PinFanOutReport:
    """Report-only enumeration of pin sites for a version change."""

    package: str
    from_version: str
    to_version: str
    sites: tuple[PinSiteStatus, ...]
    trap_id: int = TRAP_PIN_FANOUT
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "trap_id": self.trap_id,
            "sites": [s.to_dict() for s in self.sites],
            "notes": list(self.notes),
        }


def _parse_version_tuple(version: str) -> tuple[int, int, int] | None:
    match = _VERSION_CORE_RE.search(version.strip())
    if not match:
        return None
    parts = match.group(1).split(".")
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        return None


def _pin_lower_bound(pin: str) -> str | None:
    match = _PIN_LOWER_RE.search(pin)
    return match.group(1) if match else None


def _classify_pin_value(
    current: str | None, *, from_version: str, to_version: str
) -> tuple[str, str]:
    """Return ``(status, detail)`` for a version-floor pin string."""
    if current is None:
        return "missing", "pin site not found or unreadable"
    lower = _pin_lower_bound(current)
    if lower is None:
        return "unknown", f"could not parse lower bound from {current!r}"
    to_t = _parse_version_tuple(to_version)
    from_t = _parse_version_tuple(from_version)
    lower_t = _parse_version_tuple(lower)
    if to_t is None or lower_t is None:
        return "unknown", f"unparseable versions lower={lower!r} to={to_version!r}"
    if lower_t >= to_t:
        return "moved", f"lower bound {lower} reflects target {to_version}"
    if from_t is not None and lower_t == from_t:
        return "not_moved", f"still at from-version floor {lower}"
    return "not_moved", f"lower bound {lower} is behind target {to_version}"


def _read_pixi_dep(path: Path, package: str) -> str | None:
    if not path.is_file():
        return None
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None

    # Root pixi: feature/dependency tables; package pixi: package.run-dependencies.
    candidates: list[Any] = []
    deps = data.get("dependencies")
    if isinstance(deps, dict) and package in deps:
        candidates.append(deps[package])
    pkg = data.get("package")
    if isinstance(pkg, dict):
        run_deps = pkg.get("run-dependencies")
        if isinstance(run_deps, dict) and package in run_deps:
            candidates.append(run_deps[package])
    for feature in (data.get("feature") or {}).values():
        if not isinstance(feature, dict):
            continue
        fdeps = feature.get("dependencies")
        if isinstance(fdeps, dict) and package in fdeps:
            candidates.append(fdeps[package])

    for raw in candidates:
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict) and "version" in raw:
            return str(raw["version"])
    return None


def _read_pyproject_dep(path: Path, package: str) -> str | None:
    if not path.is_file():
        return None
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    reqs = (data.get("project") or {}).get("dependencies") or []
    if not isinstance(reqs, list):
        return None
    needle = package.lower()
    for req in reqs:
        if not isinstance(req, str):
            continue
        name, _, rest = req.partition(">")
        # Also split on ==, <, etc. when no >
        if name.lower().strip() == needle or req.lower().startswith(needle):
            # Return the specifier tail if present, else whole string.
            match = re.match(rf"^{re.escape(package)}\s*(.*)$", req, re.IGNORECASE)
            if match:
                spec = match.group(1).strip()
                return spec or req
            return req
    return None


def _read_harness_range(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _HARNESS_RANGE_RE.search(text)
    return match.group(1) if match else None


def _read_seed_manifest_pin(path: Path, entry_id: str) -> str | None:
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    entries = data.get("entries") or data.get("artifacts") or []
    if not isinstance(entries, list):
        # Some manifests nest under a top-level key; fall back to scanning.
        for value in data.values() if isinstance(data, dict) else ():
            if isinstance(value, list):
                entries = value
                break
    for entry in entries if isinstance(entries, list) else ():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("id", "")) == entry_id:
            pin = entry.get("pin")
            return str(pin) if pin is not None else None
    return None


def _read_drift_test_map_pin(path: Path, entry_id: str) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for match in _DRIFT_MAP_ENTRY_RE.finditer(text):
        if match.group("id") == entry_id:
            return match.group("pin")
    return None


def _read_site_value(repo: Path, site: PinSiteDef) -> str | None:
    path = repo / site.path
    if site.kind == "pixi_floor":
        return _read_pixi_dep(path, site.package)
    if site.kind == "pixi_run_dep":
        return _read_pixi_dep(path, site.package)
    if site.kind == "pyproject_dep":
        return _read_pyproject_dep(path, site.package)
    if site.kind == "harness_constant":
        return _read_harness_range(path)
    if site.kind == "seed_manifest":
        return _read_seed_manifest_pin(path, site.package)
    if site.kind == "drift_test_map":
        return _read_drift_test_map_pin(path, site.package)
    return None


def _packaged_hook_text(*, repo: Path | None = None) -> str | None:
    """Return the wheel's canonical hook relay text, if discoverable.

    Steward's own pixi env does not always install ``bmad-loop``; fall back to
    any ``bmad_loop.data`` copy under the repo's ``.pixi/envs/*/`` trees so
    loop-home rows can still classify as moved/not_moved.
    """
    try:
        return (
            resources.files("bmad_loop.data")
            .joinpath("bmad_loop_hook.py")
            .read_text(encoding="utf-8")
        )
    except (OSError, ModuleNotFoundError, AttributeError, TypeError, ValueError):
        pass
    try:
        import bmad_loop

        data = Path(bmad_loop.__file__).resolve().parent / "data" / "bmad_loop_hook.py"
        if data.is_file():
            return data.read_text(encoding="utf-8")
    except (ImportError, OSError, TypeError):
        pass
    if repo is not None:
        search_roots = [repo, *repo.resolve().parents]
        seen: set[Path] = set()
        for root in search_roots:
            if root in seen:
                continue
            seen.add(root)
            pattern = ".pixi/envs/*/lib/python*/site-packages/bmad_loop/data/bmad_loop_hook.py"
            matches = sorted(root.glob(pattern))
            for candidate in matches:
                try:
                    return candidate.read_text(encoding="utf-8")
                except OSError:
                    continue
            # Stop once we have walked past a checkout that already has pixi envs
            # but none contain bmad_loop — avoid scanning the entire filesystem.
            if (root / ".pixi" / "envs").is_dir() and root != repo:
                break
    return None


def _enumerate_loop_home_relays(
    *,
    package: str,
    loops_home: Path | None,
    from_version: str,
    to_version: str,
    repo: Path | None = None,
) -> list[PinSiteStatus]:
    """Report each loop-home hook relay (bmad-loop upgrades only)."""
    if package != "bmad-loop":
        return []
    home = loops_home if loops_home is not None else Path.home() / ".bmad-loops"
    if not home.is_dir():
        return [
            PinSiteStatus(
                site_id="loop-home-relay:(none)",
                path=str(home),
                kind="loop_home_relay",
                package=package,
                foreign=True,
                current_value=None,
                status="missing",
                detail=f"loops home not found: {home}",
            )
        ]
    packaged = _packaged_hook_text(repo=repo)
    rows: list[PinSiteStatus] = []
    for child in sorted(p for p in home.iterdir() if p.is_dir()):
        relay = child / _HOOK_SCRIPT_REL
        site_id = f"loop-home-relay:{child.name}"
        if not relay.is_file():
            rows.append(
                PinSiteStatus(
                    site_id=site_id,
                    path=str(relay),
                    kind="loop_home_relay",
                    package=package,
                    foreign=True,
                    current_value=None,
                    status="missing",
                    detail="hook relay missing — run bmad-loop init",
                )
            )
            continue
        try:
            installed = relay.read_text(encoding="utf-8")
        except OSError as exc:
            rows.append(
                PinSiteStatus(
                    site_id=site_id,
                    path=str(relay),
                    kind="loop_home_relay",
                    package=package,
                    foreign=True,
                    current_value=None,
                    status="unknown",
                    detail=f"unreadable: {exc}",
                )
            )
            continue
        if packaged is None:
            rows.append(
                PinSiteStatus(
                    site_id=site_id,
                    path=str(relay),
                    kind="loop_home_relay",
                    package=package,
                    foreign=True,
                    current_value="(present)",
                    status="unknown",
                    detail=(
                        f"relay present; packaged bmad_loop.data source "
                        f"unavailable to compare (from={from_version} to={to_version})"
                    ),
                )
            )
            continue
        if installed == packaged:
            rows.append(
                PinSiteStatus(
                    site_id=site_id,
                    path=str(relay),
                    kind="loop_home_relay",
                    package=package,
                    foreign=True,
                    current_value="(matches packaged wheel)",
                    status="moved",
                    detail="relay matches installed bmad-loop wheel (refreshed)",
                )
            )
        else:
            rows.append(
                PinSiteStatus(
                    site_id=site_id,
                    path=str(relay),
                    kind="loop_home_relay",
                    package=package,
                    foreign=True,
                    current_value="(diverges from packaged wheel)",
                    status="not_moved",
                    detail=(
                        "relay stale vs installed bmad-loop — "
                        "run bmad-loop init (foreign; steward never edits)"
                    ),
                )
            )
    if not rows:
        rows.append(
            PinSiteStatus(
                site_id="loop-home-relay:(empty)",
                path=str(home),
                kind="loop_home_relay",
                package=package,
                foreign=True,
                current_value=None,
                status="missing",
                detail=f"no loop homes under {home}",
            )
        )
    return rows


def catalog_site_ids_for(package: str) -> tuple[str, ...]:
    """Static catalog ids for *package* (excludes dynamic loop-home rows)."""
    return tuple(s.site_id for s in KNOWN_PIN_SITES if s.package == package)


def build_pin_fan_out_report(
    *,
    repo: Path,
    package: str,
    from_version: str,
    to_version: str,
    loops_home: Path | None = None,
) -> PinFanOutReport:
    """Enumerate known pin sites with moved/not-moved — never edits anything."""
    if package not in {"bmad-loop", "bmad-method"}:
        raise UpgradeError(
            f"pin-fan-out package must be bmad-loop or bmad-method, got {package!r}"
        )
    if not _VERSION_RE.match(from_version) or not _VERSION_RE.match(to_version):
        raise UpgradeError(
            f"pin-fan-out versions must be X.Y.Z "
            f"(from={from_version!r} to={to_version!r})"
        )

    notes: list[str] = [
        "CAP-4 report-only: foreign-station sites are never edited by steward",
        f"trap {TRAP_PIN_FANOUT}: pin fan-out (2026-08-21 failure-modes)",
    ]
    sites: list[PinSiteStatus] = []
    for site in KNOWN_PIN_SITES:
        if site.package != package:
            continue
        current = _read_site_value(repo, site)
        status, detail = _classify_pin_value(
            current, from_version=from_version, to_version=to_version
        )
        if site.foreign and status == "not_moved":
            detail = f"{detail} (foreign; steward never edits)"
        sites.append(
            PinSiteStatus(
                site_id=site.site_id,
                path=site.path,
                kind=site.kind,
                package=site.package,
                foreign=site.foreign,
                current_value=current,
                status=status,
                detail=detail,
            )
        )

    sites.extend(
        _enumerate_loop_home_relays(
            package=package,
            loops_home=loops_home,
            from_version=from_version,
            to_version=to_version,
            repo=repo,
        )
    )

    return PinFanOutReport(
        package=package,
        from_version=from_version,
        to_version=to_version,
        sites=tuple(sites),
        notes=tuple(notes),
    )


def format_pin_fan_out(report: PinFanOutReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "steward upgrade pin-fan-out — CAP-4 report-only",
        f"package: {report.package}",
        f"from:    {report.from_version}",
        f"to:      {report.to_version}",
        f"trap:    {report.trap_id}",
        "",
        "## Pin sites",
    ]
    if not report.sites:
        lines.append("(none)")
    for site in report.sites:
        foreign = " foreign" if site.foreign else ""
        value = site.current_value if site.current_value is not None else "(missing)"
        lines.append(
            f"- [{site.status}]{foreign} {site.site_id}: {value} — {site.detail}"
        )
    if report.notes:
        lines.extend(["", "## Notes"])
        for note in report.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CAP-5 — post-apply prove-landed (single verdict)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateResult:
    """One gate in the CAP-5 prove-landed run."""

    name: str
    ok: bool
    detail: str
    exit_code: int | None = None
    warnings: int = 0
    mutated: bool = False  # True only for documented bmad-loop init relay refresh

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Story 15.4 — CAP-4 dual-path native-class advisory spot-checks (orbit CAP-5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NativePathClassDef:
    """One install-matrix class and its cited gate spot-check candidate."""

    class_id: str
    mode: str  # executable | check-by-doc
    argv: tuple[str, ...] | None
    citation: str


# Cited only from install-matrix.md Class → gate spot-check candidates.
NATIVE_PATH_SPOT_CHECK_CATALOG: tuple[NativePathClassDef, ...] = (
    NativePathClassDef(
        class_id="npm-cli",
        mode="executable",
        argv=("npx", "bmad-method", "--version"),
        citation="install-matrix.md Class → gate: npm CLI → npx bmad-method --version",
    ),
    NativePathClassDef(
        class_id="own-npx",
        mode="executable",
        argv=("npx", "bmad-module-skill-forge", "--help"),
        citation=(
            "install-matrix.md Class → gate: own-npx → "
            "npx bmad-module-skill-forge --help"
        ),
    ),
    NativePathClassDef(
        class_id="installer-selection",
        mode="executable",
        argv=("bmad-tea-install", "--help"),
        citation=(
            "install-matrix.md Class → gate: installer-selection → "
            "TEA via bmad-tea-install (conda parity)"
        ),
    ),
    NativePathClassDef(
        class_id="custom-source",
        mode="executable",
        # Matrix table: npx bmad-method install --custom-source <manticore URL>.
        # --help keeps the citation intact without mutating (dry-run surrogate).
        argv=(
            "npx",
            "bmad-method",
            "install",
            "--custom-source",
            _MANTICORE_CUSTOM_SOURCE_URL,
            "--help",
        ),
        citation=(
            "install-matrix.md Class → gate: custom-source → manticore dry-run "
            f"(--custom-source {_MANTICORE_CUSTOM_SOURCE_URL})"
        ),
    ),
    NativePathClassDef(
        class_id="plugin-marketplace",
        mode="executable",
        argv=("npx", "skills", "add", "--help"),
        citation=(
            "install-matrix.md Class → gate: plugin-marketplace → "
            "labs npx skills add --help"
        ),
    ),
    NativePathClassDef(
        class_id="uv-from-git",
        mode="executable",
        # `uv tool install` has no --dry-run (uv 0.12.10: "unexpected argument"),
        # and the real install resolves a git URL over the network — so the
        # executable probe is the command family itself; the native spec is
        # carried in the citation (and asserted against the matrix by tests).
        argv=("uv", "tool", "install", "--help"),
        citation=(
            "install-matrix.md Class → gate: uv-from-git → "
            "uv tool install --help (native: uv tool install "
            f'"{_BMAD_LOOP_UV_GIT_SPEC}" — network; not spot-checked)'
        ),
    ),
    NativePathClassDef(
        class_id="build-from-source",
        mode="check-by-doc",
        argv=None,
        citation=(
            "install-matrix.md Class → gate: build-from-source → "
            "dashboards excluded (check-by-doc)"
        ),
    ),
)


@dataclass(frozen=True)
class NativePathSpotCheck:
    """Advisory result for one native-method class spot-check."""

    class_id: str
    mode: str  # executable | check-by-doc | advisory
    ok: bool
    status: str  # ok | fail | warn | check-by-doc | missing-matrix
    detail: str
    argv: tuple[str, ...] | None = None
    exit_code: int | None = None
    advisory: bool = True  # spot-checks never hard-gate CAP-5

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.argv is not None:
            payload["argv"] = list(self.argv)
        return payload


CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


_NATIVE_SPOT_CHECK_TIMEOUT_SEC = 60


def _default_command_runner(
    argv: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=_NATIVE_SPOT_CHECK_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            list(argv),
            124,
            stdout=exc.stdout if isinstance(exc.stdout, str) else "",
            stderr=(
                (exc.stderr if isinstance(exc.stderr, str) else "")
                or f"timeout after {_NATIVE_SPOT_CHECK_TIMEOUT_SEC}s"
            ),
        )


def run_native_path_spot_checks(
    repo: Path,
    *,
    command_runner: CommandRunner | None = None,
    catalog: Sequence[NativePathClassDef] | None = None,
) -> tuple[NativePathSpotCheck, ...]:
    """Run ≥1 cited native command (or doc-check) per install-matrix class.

    Failures are advisory only — callers must not fold them into CAP-5
    ``verdict``. Commands are taken solely from
    ``NATIVE_PATH_SPOT_CHECK_CATALOG`` (install-matrix citations).
    """
    entries = tuple(catalog) if catalog is not None else NATIVE_PATH_SPOT_CHECK_CATALOG
    matrix_path = repo / _INSTALL_MATRIX_REL
    if not matrix_path.is_file():
        return (
            NativePathSpotCheck(
                class_id="(matrix)",
                mode="advisory",
                ok=False,
                status="missing-matrix",
                detail=f"missing citation source: {_INSTALL_MATRIX_REL}",
                argv=None,
                advisory=True,
            ),
        )

    try:
        matrix_text = matrix_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return (
            NativePathSpotCheck(
                class_id="(matrix)",
                mode="advisory",
                ok=False,
                status="missing-matrix",
                detail=f"unreadable citation source {_INSTALL_MATRIX_REL}: {exc}",
                argv=None,
                advisory=True,
            ),
        )

    runner = command_runner or _default_command_runner
    results: list[NativePathSpotCheck] = []
    for entry in entries:
        if entry.mode == "check-by-doc":
            # Dashboards: no build subprocess; require matrix still documents
            # the check-by-doc / dashboards exclusion so doc-only is not a noop.
            cited = (
                "check-by-doc" in matrix_text.lower()
                and "dashboard" in matrix_text.lower()
            )
            results.append(
                NativePathSpotCheck(
                    class_id=entry.class_id,
                    mode="check-by-doc",
                    ok=cited,
                    status="check-by-doc" if cited else "warn",
                    detail=(
                        "dashboards: check-by-doc only (no build subprocess); "
                        f"cited: {entry.citation}"
                        if cited
                        else (
                            "advisory warn: matrix lacks dashboards/check-by-doc "
                            f"citation — {entry.citation}"
                        )
                    ),
                    argv=None,
                    advisory=True,
                )
            )
            continue
        if entry.mode != "executable":
            results.append(
                NativePathSpotCheck(
                    class_id=entry.class_id,
                    mode=entry.mode,
                    ok=False,
                    status="warn",
                    detail=f"unknown mode {entry.mode!r} — not executed",
                    argv=entry.argv,
                    advisory=True,
                )
            )
            continue
        if not entry.argv:
            results.append(
                NativePathSpotCheck(
                    class_id=entry.class_id,
                    mode=entry.mode,
                    ok=False,
                    status="warn",
                    detail=(
                        f"class {entry.class_id!r} has no cited argv — "
                        "halt rather than invent (matrix citation required)"
                    ),
                    argv=None,
                    advisory=True,
                )
            )
            continue
        try:
            proc = runner(entry.argv, repo)
        except (OSError, UnicodeDecodeError, ValueError, TypeError) as exc:
            results.append(
                NativePathSpotCheck(
                    class_id=entry.class_id,
                    mode="executable",
                    ok=False,
                    status="fail",
                    detail=f"advisory: failed to launch {entry.argv[0]!r}: {exc}",
                    argv=entry.argv,
                    exit_code=None,
                    advisory=True,
                )
            )
            continue
        code = proc.returncode if proc.returncode is not None else -1
        ok = code == 0
        # On failure prefer stderr so real errors are not hidden by empty stdout.
        raw = (
            (proc.stderr or proc.stdout or "")
            if not ok
            else (proc.stdout or proc.stderr or "")
        )
        preview = raw.strip().splitlines()
        tail = " | ".join(preview[-2:])[:300] if preview else ""
        if ok:
            detail = f"advisory ok: {' '.join(entry.argv)}"
            if tail:
                detail += f" — {tail}"
            status = "ok"
        else:
            detail = f"advisory fail (exit {code}): {' '.join(entry.argv)}"
            if tail:
                detail += f" — {tail}"
            status = "fail"
        results.append(
            NativePathSpotCheck(
                class_id=entry.class_id,
                mode="executable",
                ok=ok,
                status=status,
                detail=detail,
                argv=entry.argv,
                exit_code=int(code),
                advisory=True,
            )
        )
    return tuple(results)


@dataclass(frozen=True)
class ProveLandedReport:
    """Single-verdict outcome of the post-apply verification gate."""

    verdict: str  # pass | fail
    gates: tuple[GateResult, ...]
    homes_ok: int
    homes_total: int
    trap_id: int = TRAP_LOOP_RELAY
    notes: tuple[str, ...] = ()
    # Story 15.4: advisory only — never drives verdict / DutyResult.ok.
    native_spot_checks: tuple[NativePathSpotCheck, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "gates": [g.to_dict() for g in self.gates],
            "homes_ok": self.homes_ok,
            "homes_total": self.homes_total,
            "trap_id": self.trap_id,
            "notes": list(self.notes),
            "native_spot_checks": [s.to_dict() for s in self.native_spot_checks],
        }


GateRunner = Callable[[], GateResult]
LoopHomeRunner = Callable[[Path, bool], GateResult]


# The repo task that IS the integrity verdict when pyforge.doctor is not
# importable from the steward env (it is a local-recipes-env module; the
# 2026-09-06 prove-landed FAILed on the import alone — failure-modes trap 15).
_BMAD_DRIFT_TASK_ARGV: tuple[str, ...] = (
    "pixi",
    "run",
    "-e",
    "pyforge-guild",
    "bmad-drift-check",
)


def _import_drift_factory() -> tuple[Any, Any]:
    """Import seam for tests; raises ImportError outside the Guild env."""
    from pyforge.doctor.models import DoctorStatus
    from pyforge.doctor.sources import factory as bmad_drift_factory

    return DoctorStatus, bmad_drift_factory


def _run_bmad_drift_task(
    repo: Path,
    runner: CommandRunner | None = None,
) -> GateResult:
    """Fallback: the documented pixi task, exit 0 pass / 1 findings / 2 could-not-run."""
    run = runner or _default_command_runner
    try:
        proc = run(_BMAD_DRIFT_TASK_ARGV, repo)
    except (OSError, subprocess.SubprocessError) as exc:
        return GateResult(
            name="bmad-drift-integrity",
            ok=False,
            detail=f"pyforge.doctor not importable here and the pixi task failed to launch: {exc}",
        )
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
    preview = "; ".join(line.strip() for line in tail[-3:]) if tail else "(no output)"
    if proc.returncode == 0:
        return GateResult(
            name="bmad-drift-integrity",
            ok=True,
            detail="no HARD/FAIL integrity findings (via `pixi run -e pyforge-guild bmad-drift-check`)",
        )
    kind = "findings" if proc.returncode == 1 else "could-not-run"
    return GateResult(
        name="bmad-drift-integrity",
        ok=False,
        detail=f"bmad-drift-check {kind} (exit {proc.returncode}) via pixi task: {preview[:300]}",
    )


def run_bmad_drift_integrity(
    repo: Path,
    *,
    fallback_runner: CommandRunner | None = None,
) -> GateResult:
    """HARD/FAIL findings from ``factory.gather`` (= bmad-drift-check integrity).

    When ``pyforge.doctor`` is not importable (the steward env does not ship
    it), the same verdict is taken from the repo's own pixi task instead of
    failing on the import.
    """
    try:
        DoctorStatus, bmad_drift_factory = _import_drift_factory()
    except ImportError:
        return _run_bmad_drift_task(repo, fallback_runner)
    try:
        findings = bmad_drift_factory.gather(repo)
    except Exception as exc:  # noqa: BLE001 — surface as gate failure
        return GateResult(
            name="bmad-drift-integrity",
            ok=False,
            detail=f"factory.gather raised: {exc}",
        )
    hard = [f for f in findings if f.status is DoctorStatus.FAIL]
    if hard:
        preview = "; ".join(f"[{f.check}] {f.message}" for f in hard[:5])
        return GateResult(
            name="bmad-drift-integrity",
            ok=False,
            detail=f"{len(hard)} HARD finding(s): {preview}",
        )
    return GateResult(
        name="bmad-drift-integrity",
        ok=True,
        detail="no HARD/FAIL integrity findings",
    )


def run_cfe_meta_tests(
    repo: Path,
    *,
    pytest_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
    | None = None,
) -> GateResult:
    """CFE skill meta-test ``test_bmad_artifacts_in_sync`` (integrity class)."""
    test_path = repo / _CFE_META_TEST_REL
    if not test_path.is_file():
        return GateResult(
            name="cfe-meta-tests",
            ok=False,
            detail=f"missing meta test: {_CFE_META_TEST_REL}",
        )

    def _default(
        argv: Sequence[str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    runner = pytest_runner or _default
    argv = [
        __import__("sys").executable,
        "-m",
        "pytest",
        str(test_path),
        "-q",
        "--tb=line",
    ]
    result = runner(argv, repo)
    ok = result.returncode == 0
    tail = (result.stdout or result.stderr or "").strip().splitlines()
    preview = tail[-3:] if tail else []
    detail = (
        "test_bmad_artifacts_in_sync green"
        if ok
        else f"pytest exit {result.returncode}: " + " | ".join(preview)[:400]
    )
    return GateResult(
        name="cfe-meta-tests",
        ok=ok,
        detail=detail,
        exit_code=int(result.returncode),
    )


def _list_loop_homes(loops_home: Path) -> list[Path]:
    if not loops_home.is_dir():
        return []
    return sorted(p for p in loops_home.iterdir() if p.is_dir())


def run_loop_home_gate(
    home: Path,
    *,
    refresh_relays: bool,
    loop_bin: str = "bmad-loop",
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
    | None = None,
) -> GateResult:
    """``bmad-loop init`` (optional relay refresh) then ``validate`` for one home.

    ``init`` is the only documented mutation of a foreign station tree.
    """
    name = f"loop-home:{home.name}"

    def _default(
        argv: Sequence[str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    run = runner or _default
    mutated = False
    if refresh_relays:
        init = run([loop_bin, "init", "--project", str(home)], home)
        mutated = True
        if init.returncode != 0:
            err = (init.stderr or init.stdout or "").strip()[:300]
            return GateResult(
                name=name,
                ok=False,
                detail=f"bmad-loop init failed (exit {init.returncode}): {err}",
                exit_code=int(init.returncode),
                mutated=True,
            )

    validate = run(
        [loop_bin, "validate", "--project", str(home), "--json"], home
    )
    if validate.returncode != 0 and not (validate.stdout or "").strip():
        err = (validate.stderr or "").strip()[:300]
        return GateResult(
            name=name,
            ok=False,
            detail=f"bmad-loop validate failed (exit {validate.returncode}): {err}",
            exit_code=int(validate.returncode),
            mutated=mutated,
        )
    try:
        payload = json.loads(validate.stdout or "{}")
    except json.JSONDecodeError as exc:
        return GateResult(
            name=name,
            ok=False,
            detail=f"validate JSON unreadable: {exc}",
            exit_code=int(validate.returncode),
            mutated=mutated,
        )
    counts = payload.get("counts") or {}
    warnings = int(counts.get("warning") or 0)
    problems = int(counts.get("problem") or 0)
    ok_flag = bool(payload.get("ok")) and warnings == 0 and problems == 0
    detail = (
        f"validate clean (warnings={warnings}, problems={problems})"
        if ok_flag
        else (
            f"validate not clean: ok={payload.get('ok')!r} "
            f"warnings={warnings} problems={problems}"
        )
    )
    return GateResult(
        name=name,
        ok=ok_flag,
        detail=detail,
        exit_code=int(validate.returncode),
        warnings=warnings,
        mutated=mutated,
    )


def build_prove_landed_report(
    *,
    repo: Path,
    loops_home: Path | None = None,
    refresh_relays: bool = True,
    drift_runner: GateRunner | None = None,
    cfe_runner: GateRunner | None = None,
    loop_home_runner: LoopHomeRunner | None = None,
    command_runner: CommandRunner | None = None,
    skip_native_spot_checks: bool = False,
) -> ProveLandedReport:
    """Run CAP-5 gates and return a single pass/fail verdict.

    Foreign-station trees are not edited beyond the documented ``bmad-loop
    init`` relay refresh when *refresh_relays* is True.

    Story 15.4: also runs advisory native-path spot-checks (install-matrix
    Class → gate candidates). Spot-check failures never flip *verdict*.
    """
    home_root = loops_home if loops_home is not None else Path.home() / ".bmad-loops"
    notes: list[str] = [
        "CAP-5 prove-landed: single verdict over drift integrity + CFE meta + loop homes",
        "foreign-tree mutation limited to documented bmad-loop init relay refresh",
        f"trap {TRAP_LOOP_RELAY}: loop-home hook relay stale (2026-08-21 failure-modes)",
    ]

    gates: list[GateResult] = []
    gates.append(
        drift_runner() if drift_runner is not None else run_bmad_drift_integrity(repo)
    )
    gates.append(
        cfe_runner() if cfe_runner is not None else run_cfe_meta_tests(repo)
    )

    homes = _list_loop_homes(home_root)
    if not homes:
        gates.append(
            GateResult(
                name="loop-homes",
                ok=False,
                detail=f"no loop homes under {home_root}",
            )
        )
        notes.append(
            f"worked-example target is {WORKED_EXAMPLE_LOOP_HOME_COUNT}/"
            f"{WORKED_EXAMPLE_LOOP_HOME_COUNT} homes clean; found 0"
        )
    else:
        for home in homes:
            if loop_home_runner is not None:
                gates.append(loop_home_runner(home, refresh_relays))
            else:
                gates.append(
                    run_loop_home_gate(home, refresh_relays=refresh_relays)
                )

    loop_gates = [g for g in gates if g.name.startswith("loop-home:")]
    homes_total = len(loop_gates)
    homes_ok = sum(1 for g in loop_gates if g.ok)
    if homes_total:
        notes.append(
            f"loop homes: {homes_ok}/{homes_total} clean "
            f"(worked example shape: {WORKED_EXAMPLE_LOOP_HOME_COUNT}/"
            f"{WORKED_EXAMPLE_LOOP_HOME_COUNT})"
        )
    mutated = [g.name for g in gates if g.mutated]
    if mutated:
        notes.append("relay refresh ran for: " + ", ".join(mutated))
    elif refresh_relays and homes_total:
        notes.append("refresh_relays requested but no loop-home gate recorded mutation")
    elif not refresh_relays:
        notes.append("--no-init: skipped relay refresh (validate-only)")

    # Story 15.4 — advisory orbit only; never folded into verdict.
    if skip_native_spot_checks:
        native_spot_checks: tuple[NativePathSpotCheck, ...] = ()
        notes.append("native path spot-checks: skipped")
    else:
        native_spot_checks = run_native_path_spot_checks(
            repo, command_runner=command_runner
        )
        ok_n = sum(1 for s in native_spot_checks if s.ok)
        total_n = len(native_spot_checks)
        fail_n = total_n - ok_n
        if fail_n:
            notes.append(
                f"native path spot-checks: {ok_n}/{total_n} ok, {fail_n} advisory "
                "fail/warn (do not affect CAP-5 verdict)"
            )
        else:
            notes.append(
                f"native path spot-checks: {ok_n}/{total_n} ok "
                "(advisory; not a hard gate)"
            )

    # Verdict follows Epic 14 hard gates only — never native spot-checks.
    verdict = "pass" if all(g.ok for g in gates) else "fail"
    return ProveLandedReport(
        verdict=verdict,
        gates=tuple(gates),
        homes_ok=homes_ok,
        homes_total=homes_total,
        notes=tuple(notes),
        native_spot_checks=native_spot_checks,
    )


def format_prove_landed(report: ProveLandedReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "steward upgrade prove-landed — CAP-5 post-apply verification",
        f"verdict:  {report.verdict.upper()}",
        f"homes:    {report.homes_ok}/{report.homes_total} clean",
        f"trap:     {report.trap_id}",
        "",
        "## Gates",
    ]
    for gate in report.gates:
        mark = "ok" if gate.ok else "FAIL"
        mut = " (relay refresh)" if gate.mutated else ""
        lines.append(f"- [{mark}]{mut} {gate.name}: {gate.detail}")

    lines.extend(["", "## Native path spot-checks (advisory)"])
    if not report.native_spot_checks:
        lines.append("(none)")
    for spot in report.native_spot_checks:
        mark = "ok" if spot.ok else spot.status
        lines.append(
            f"- [{mark}] {spot.class_id} ({spot.mode}): {spot.detail}"
        )

    if report.notes:
        lines.extend(["", "## Notes"])
        for note in report.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


class UpgradeDuty:
    """``steward upgrade …`` — Epic 14 (14.1–14.5: preflight through prove-landed)."""

    name = "upgrade"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "upgrade_verb", None)
        if not verb:
            return DutyResult(
                ok=True,
                summary=(
                    "upgrade: available verbs are bmad-core "
                    "(report-only pre-flight; pass --apply for CAP-2 deliberate apply), "
                    "pin-fan-out (CAP-4 report-only pin enumeration), "
                    "and prove-landed/verify (CAP-5 post-apply single-verdict gate)"
                ),
            )
        try:
            if verb == "bmad-core":
                return self._bmad_core(ns)
            if verb == "pin-fan-out":
                return self._pin_fan_out(ns)
            if verb == "prove-landed" or verb == "verify":
                return self._prove_landed(ns)
            return DutyResult(ok=False, summary=f"upgrade: unknown verb {verb!r}")
        except UpgradeError as exc:
            return DutyResult(ok=False, summary=f"upgrade: {exc}")
        except (OSError, yaml.YAMLError, subprocess.SubprocessError) as exc:
            return DutyResult(ok=False, summary=f"upgrade: {exc}")

    def _prove_landed(self, ns: argparse.Namespace) -> DutyResult:
        repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
        loops = (
            Path(ns.loops_home) if getattr(ns, "loops_home", None) else None
        )
        as_json = bool(getattr(ns, "json", False))
        refresh = not bool(getattr(ns, "no_init", False))
        report = build_prove_landed_report(
            repo=repo,
            loops_home=loops,
            refresh_relays=refresh,
        )
        return DutyResult(
            ok=report.verdict == "pass",
            summary=format_prove_landed(report, as_json=as_json),
            details={"report": report.to_dict(), "trap_id": TRAP_LOOP_RELAY},
        )

    def _pin_fan_out(self, ns: argparse.Namespace) -> DutyResult:
        package = getattr(ns, "pin_package", None)
        from_version = getattr(ns, "from_version", None)
        to_version = getattr(ns, "to_version", None)
        if not package or not from_version or not to_version:
            return DutyResult(
                ok=False,
                summary=(
                    "upgrade pin-fan-out: --package, --from, and --to are required"
                ),
            )
        repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
        loops = (
            Path(ns.loops_home) if getattr(ns, "loops_home", None) else None
        )
        as_json = bool(getattr(ns, "json", False))
        report = build_pin_fan_out_report(
            repo=repo,
            package=package,
            from_version=from_version,
            to_version=to_version,
            loops_home=loops,
        )
        return DutyResult(
            ok=True,
            summary=format_pin_fan_out(report, as_json=as_json),
            details={"report": report.to_dict(), "trap_id": TRAP_PIN_FANOUT},
        )

    def _bmad_core(self, ns: argparse.Namespace) -> DutyResult:
        target = getattr(ns, "target", None)
        if not target:
            return DutyResult(
                ok=False,
                summary="upgrade bmad-core: --target X.Y.Z is required",
            )
        repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
        package_root = Path(ns.package_root) if getattr(ns, "package_root", None) else None
        installed_package_root = (
            Path(ns.installed_package_root)
            if getattr(ns, "installed_package_root", None)
            else None
        )
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
                installed_package_root=installed_package_root,
            )
            return DutyResult(
                ok=True,
                summary=format_preflight(report, as_json=as_json),
                details={"report": report.to_dict(), "trap_ids": list(report.trap_ids)},
            )

        installer_bin = getattr(ns, "installer", None) or "bmad-method"
        branch = getattr(ns, "branch", None) or None
        no_shims = bool(getattr(ns, "no_shims", False))
        apply_report = apply_bmad_core_upgrade(
            repo=repo,
            target_version=target,
            branch=branch,
            installed_version=installed_override,
            catalog_directory=catalog_directory,
            package_root=package_root,
            installed_package_root=installed_package_root,
            installer_bin=installer_bin,
            no_shims=no_shims,
        )
        reconcile_ok = (
            apply_report.reconcile is not None and apply_report.reconcile.all_clear
        )
        ok = (
            apply_report.installer_exit == 0
            and not apply_report.zero_diff
            and apply_report.custom_identical
            and reconcile_ok
            # CAP-7: own installer exit 0 + every config path restored, per module.
            and apply_report.custom_modules_ok
            # CAP-8: every flagged local customization landed clean or was
            # correctly skipped — a conflict never gates a green silently.
            and apply_report.local_customizations_ok
        )
        return DutyResult(
            ok=ok,
            summary=format_apply(apply_report, as_json=as_json),
            details={
                "apply": apply_report.to_dict(),
                "trap_ids": list(apply_report.preflight.trap_ids),
            },
        )
