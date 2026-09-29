"""REFERENCED-dependency presence + floor verification (Story 11.5, FR-95).

Genesis verifies every manifest ``referenced`` entry against its declared
``pin`` and **never installs** any of them. Missing or below-floor yields
``referenced-dep-missing`` at **DRIFT** severity -- the repo may still be
conformant, but the machine is not ready to run the factory.

**Doctor delegation.** When ``doctor`` is on ``PATH``, this module tries
``python -m pyforge.doctor.sources genesis-referenced-deps --json`` first
(subprocess only -- never ``import pyforge.doctor``; Doctor holds verdicts
on Marshal, not the reverse). A successful JSON payload is converted into
Marshal ``Finding``s with a ``[doctor]`` message prefix. Any failure
(nonzero exit, malformed JSON, unknown source) falls through to the local
probe below -- so repos without ``pyforge-doctor`` still get a complete
check.

**Local probe (no network).** Per entry id:
* ``bmad-method`` / ``bmad-installed-skills`` / ``bmad-skill-forge`` --
  read ``_bmad/_config/manifest.yaml`` ``installation.version``;
* ``copier`` / ``pixi`` / ``tmux`` / ``bmad-loop`` -- ``shutil.which`` +
  one ``--version``/``-V`` subprocess;
* every other referenced id -- treat ``id`` as the conda package name and
  read ``.pixi/envs/*/conda-meta/{id}-<ver>-<build>.json`` filenames (the
  same filename-parse discipline ``pyforge.doctor.sources.bmad_method`` uses
  for suite pins: no file reads, no network).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version
from pyforge.core.process import PosixProcess, ProcessError

from ..model.manifest import ArtifactClass, Manifest, ManifestEntry
from .findings import Finding, FindingType, Severity

__all__ = ("referenced_dep_findings",)

# Future Doctor ``sources/__main__.py`` DISPATCH key -- delegation tries this
# name first; until Doctor lands the source, argparse rejects it and the
# local probe runs instead.
_DOCTOR_SOURCE = "genesis-referenced-deps"
_DOCTOR_TIMEOUT_S = 5.0
_CLI_TIMEOUT_S = 5.0

_BMAD_MANIFEST_VERSION_IDS = frozenset({"bmad-method", "bmad-installed-skills", "bmad-skill-forge"})

_CLI_PROBES: dict[str, tuple[str, ...]] = {
    "copier": ("--version",),
    "pixi": ("--version",),
    "tmux": ("-V",),
    "bmad-loop": ("--version",),
}

_VERSION_TOKEN_RE = re.compile(r"(\d+(?:\.\d+)*(?:[a-zA-Z][\w.]*)?(?:_\d+)?)")


@dataclass(frozen=True)
class _ProbeResult:
    installed: str | None
    delegated: bool


def _satisfies_pin(installed: str, pin: str) -> bool:
    try:
        return Version(installed) in SpecifierSet(pin)
    except InvalidVersion, ValueError:
        return False


def _first_version_token(text: str) -> str | None:
    match = _VERSION_TOKEN_RE.search(text.strip())
    return match.group(1) if match else None


def _read_bmad_core_version(repo_root: Path) -> str | None:
    manifest_path = repo_root / "_bmad" / "_config" / "manifest.yaml"
    if not manifest_path.is_file():
        return None
    try:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except OSError, yaml.YAMLError, UnicodeDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    installation = payload.get("installation")
    if not isinstance(installation, dict):
        return None
    version = installation.get("version")
    if version is None:
        return None
    text = str(version).strip()
    return text or None


def _cli_installed_version(repo_root: Path, command: str, args: tuple[str, ...]) -> str | None:
    if shutil.which(command) is None:
        return None
    try:
        result = PosixProcess().run([command, *args], cwd=repo_root, timeout_s=_CLI_TIMEOUT_S)
    except ProcessError:
        return None
    if result.returncode != 0:
        return None
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    return _first_version_token(combined)


def _conda_installed_version(repo_root: Path, package: str) -> str | None:
    envs_dir = repo_root / ".pixi" / "envs"
    if not envs_dir.is_dir():
        return None
    best: tuple[Version, str] | None = None
    try:
        env_dirs = list(envs_dir.iterdir())
    except OSError:
        return None
    for env_dir in env_dirs:
        meta_dir = env_dir / "conda-meta"
        try:
            meta_files = list(meta_dir.iterdir())
        except OSError:
            continue
        for meta_file in meta_files:
            if meta_file.suffix != ".json":
                continue
            parts = meta_file.stem.rsplit("-", 2)
            if len(parts) != 3:
                continue
            name, version_text, _build = parts
            if name != package:
                continue
            try:
                parsed = Version(version_text)
            except InvalidVersion:
                continue
            if best is None or parsed > best[0]:
                best = (parsed, version_text)
    return best[1] if best is not None else None


def _probe_entry(repo_root: Path, entry: ManifestEntry) -> _ProbeResult:
    if entry.id in _BMAD_MANIFEST_VERSION_IDS:
        return _ProbeResult(_read_bmad_core_version(repo_root), delegated=False)
    cli_args = _CLI_PROBES.get(entry.id)
    if cli_args is not None:
        return _ProbeResult(_cli_installed_version(repo_root, entry.id, cli_args), delegated=False)
    return _ProbeResult(_conda_installed_version(repo_root, entry.id), delegated=False)


def _finding_for_entry(entry: ManifestEntry, *, installed: str | None, delegated: bool) -> Finding | None:
    if installed is None:
        message = f"{entry.id}: referenced dependency is not installed (manifest pin {entry.pin!r})"
    elif not _satisfies_pin(installed, entry.pin or ""):
        message = f"{entry.id}: installed version {installed!r} is below manifest floor {entry.pin!r}"
    else:
        return None
    if delegated:
        message = f"[doctor] {message}"
    return Finding.new(
        Severity.DRIFT,
        FindingType.REFERENCED_DEP_MISSING,
        entry.id,
        message,
    )


def _doctor_findings(repo_root: Path) -> tuple[Finding, ...] | None:
    """Return Doctor-normalized findings, or ``None`` to fall back to local probe."""
    if shutil.which("doctor") is None:
        return None
    cmd = [sys.executable, "-m", "pyforge.doctor.sources", _DOCTOR_SOURCE, "--json"]
    try:
        result = PosixProcess().run(cmd, cwd=repo_root, timeout_s=_DOCTOR_TIMEOUT_S)
    except ProcessError:
        return None
    # Unknown source → exit 2; any other hard failure → local probe.
    if result.returncode == 2:
        return None
    if result.returncode not in (0, 1):
        return None
    raw = result.stdout
    if raw is None or not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    findings: list[Finding] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("artifact_id") or item.get("path") or "").strip()
        message = str(item.get("message") or "").strip()
        if not artifact_id or not message:
            continue
        findings.append(
            Finding.new(
                Severity.DRIFT,
                FindingType.REFERENCED_DEP_MISSING,
                artifact_id,
                f"[doctor] {message}",
            )
        )
    return tuple(findings)


def _local_findings(manifest: Manifest, repo_root: Path) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for entry in manifest.entries:
        if entry.artifact_class is not ArtifactClass.REFERENCED:
            continue
        probe = _probe_entry(repo_root, entry)
        finding = _finding_for_entry(entry, installed=probe.installed, delegated=False)
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def referenced_dep_findings(manifest: Manifest, repo_root: Path) -> tuple[Finding, ...]:
    """Verify every ``referenced`` manifest entry; DRIFT ``referenced-dep-missing`` only."""
    delegated = _doctor_findings(repo_root)
    if delegated is not None:
        return delegated
    return _local_findings(manifest, repo_root)
