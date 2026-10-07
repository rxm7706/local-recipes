"""Throwaway-copy manifest fix preparation (Story 14.2)."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .engines import run_pixi_lock
from .manifest_edit import edit_requirement_to_floor, parse_manifest_path_from_location


@dataclass(frozen=True)
class ManifestFileChange:
    path: str
    content: str


@dataclass(frozen=True)
class ManifestFixPlan:
    files: tuple[ManifestFileChange, ...]


@dataclass(frozen=True)
class ManifestFixOutcome:
    plan: ManifestFixPlan | None
    failure_detail: str | None = None


def tree_content_digest(root: Path) -> str:
    """Stable digest of every file under ``root`` (relative paths, sorted)."""
    hasher = hashlib.sha256()
    if not root.is_dir():
        return hasher.hexdigest()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        hasher.update(rel)
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _select_manifest_paths(locations: Sequence[str]) -> tuple[str, ...] | None:
    manifests = {path for loc in locations if (path := parse_manifest_path_from_location(loc)) is not None}
    if not manifests:
        return None
    if len(manifests) > 1:
        return ()
    return (next(iter(manifests)),)


def prepare_manifest_fix(
    *,
    scan_target: Path,
    package: str,
    floor: str,
    manifest_locations: Mapping[str, Sequence[str]],
    location_keys: Sequence[str],
) -> ManifestFixOutcome:
    """Copy ``scan_target``, edit one requirement, re-solve lock when present."""
    locations: list[str] = []
    for key in location_keys:
        locations.extend(manifest_locations.get(key, ()))
    if not locations:
        return ManifestFixOutcome(plan=None, failure_detail="no manifest location for package")
    manifest_paths = _select_manifest_paths(locations)
    if manifest_paths == ():
        return ManifestFixOutcome(plan=None, failure_detail="requirement declared in more than one manifest")
    assert manifest_paths is not None
    (manifest_rel,) = manifest_paths

    temp_dir = Path(tempfile.mkdtemp(prefix="warden-manifest-fix-"))
    try:
        os.chmod(temp_dir, 0o700)
        shutil.copytree(scan_target, temp_dir, dirs_exist_ok=True)
        manifest_path = temp_dir / manifest_rel
        edit_result = edit_requirement_to_floor(manifest_path, package=package, floor=floor)
        if not edit_result.ok:
            return ManifestFixOutcome(plan=None, failure_detail=edit_result.failure_reason)

        if (temp_dir / "pixi.lock").is_file():
            error, exit_code = run_pixi_lock(cwd=temp_dir)
            if error is not None:
                return ManifestFixOutcome(
                    plan=None,
                    failure_detail=f"pixi lock re-solve failed: {error.message}",
                )
            if exit_code != 0:
                return ManifestFixOutcome(plan=None, failure_detail="pixi lock re-solve failed")

        changed: list[ManifestFileChange] = []
        for rel in (manifest_rel, "pixi.lock"):
            edited = temp_dir / rel
            original = scan_target / rel
            if not edited.is_file():
                continue
            new_content = edited.read_text(encoding="utf-8")
            if original.is_file() and original.read_text(encoding="utf-8") == new_content:
                continue
            changed.append(ManifestFileChange(path=rel, content=new_content))
        if not changed:
            return ManifestFixOutcome(plan=None, failure_detail="edit produced no diff")
        return ManifestFixOutcome(plan=ManifestFixPlan(files=tuple(changed)))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
