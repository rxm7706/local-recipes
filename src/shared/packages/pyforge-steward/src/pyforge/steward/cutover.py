"""Cutover plan / apply / flip (Story 44.12 / fnd:CAP-8)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pyforge.core.atomic_write import atomic_write_text
from pyforge.core.cutover_root import (
    CUTOVER_FLAG,
    CUTOVER_VARIANTS,
    DEFAULT_CUTOVER_ROOT,
    CutoverRootError,
    read_cutover_root,
    resolve_flags_path,
)

from .interfaces import DutyResult

_CUTOVER_VERBS: tuple[str, ...] = ("plan", "apply", "flip")
DEFAULT_MANIFEST = Path("docs/foundry/manifest.json")
FOUNDRY_EPOCH = "6e0607b530f5fa5db2faffd12cbc49da9d880083"
REALIZATION_LOG = Path("docs/dreams/pyforge-unifying-strategy.md")
ENV_FOUNDRY = "CUTOVER_FOUNDRY_ROOT"

# Launch apply trees only — 44.1 still owns 100% coverage.
_PHASE_RULES: dict[str, tuple[str, ...]] = {
    "1a": ("src/shared/packages/",),
    "1b": (
        ".claude/skills/",
        "_bmad/",
        "_bmad-output/projects/",
        "docs/dreams/",
        "presentations/",
    ),
}

_CFE_PREFIX = ".claude/skills/conda-forge-expert/"


def _repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def _source_sha(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def _ls_files(root: Path) -> tuple[str, ...]:
    text = _git(root, "ls-files", "-z")
    return tuple(part for part in text.split("\0") if part)


def _dest_for(path: str, phase: str) -> str:
    if phase == "1a" and path.startswith("src/shared/packages/"):
        return "src/packages/" + path[len("src/shared/packages/") :]
    return path


def _kind_for(path: str) -> str:
    name = Path(path).name.lower()
    if name in {".env", ".netrc"} or name.endswith(".pem"):
        return "secret"
    return "file"


def _phase_for(path: str) -> str | None:
    if path.startswith(_CFE_PREFIX):
        return None
    for phase, prefixes in _PHASE_RULES.items():
        if any(path.startswith(prefix) for prefix in prefixes):
            return phase
    return None


def _row(path: str, phase: str, status: str = "planned") -> dict[str, Any]:
    return {
        "path": path,
        "dest": _dest_for(path, phase),
        "status": status,
        "kind": _kind_for(path),
        "phase": phase,
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"source_sha": "", "foundry_epoch": FOUNDRY_EPOCH, "rows": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"source_sha": "", "foundry_epoch": FOUNDRY_EPOCH, "rows": []}
    raw.setdefault("rows", [])
    raw.setdefault("foundry_epoch", FOUNDRY_EPOCH)
    return raw


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _preserve_moved(existing: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    kept: dict[str, dict[str, Any]] = {}
    for row in existing:
        if isinstance(row, dict) and row.get("status") == "moved" and row.get("path"):
            kept[str(row["path"])] = row
    return kept


def plan_regenerate(root: Path, manifest_path: Path) -> dict[str, Any]:
    existing = _load_manifest(manifest_path)
    moved = _preserve_moved(list(existing.get("rows") or []))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in _ls_files(root):
        phase = _phase_for(path)
        if phase is None:
            continue
        if path in moved:
            rows.append(moved[path])
        else:
            rows.append(_row(path, phase))
        seen.add(path)
    for path, row in moved.items():
        if path not in seen:
            rows.append(row)
    payload = {
        "source_sha": _source_sha(root),
        "foundry_epoch": FOUNDRY_EPOCH,
        "rows": rows,
    }
    _write_manifest(manifest_path, payload)
    return payload


def plan_append(root: Path, manifest_path: Path) -> dict[str, Any]:
    existing = _load_manifest(manifest_path)
    by_path = {str(row["path"]): row for row in existing.get("rows") or [] if isinstance(row, dict) and row.get("path")}
    old_sha = str(existing.get("source_sha") or "")
    candidates: set[str] = set(_ls_files(root))
    if old_sha:
        try:
            delta = _git(root, "diff", "--name-only", old_sha, "HEAD")
            candidates.update(line for line in delta.splitlines() if line)
        except RuntimeError:
            pass
    for path in sorted(candidates):
        phase = _phase_for(path)
        if phase is None:
            continue
        current = by_path.get(path)
        if current and current.get("status") == "moved":
            continue
        if current is None:
            by_path[path] = _row(path, phase)
    payload = {
        "source_sha": _source_sha(root),
        "foundry_epoch": FOUNDRY_EPOCH,
        "rows": list(by_path.values()),
    }
    _write_manifest(manifest_path, payload)
    return payload


def _foundry_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    raw = os.environ.get(ENV_FOUNDRY)
    if raw:
        return Path(raw)
    sibling = _repo_root().parent / "python-foundry"
    return sibling


def apply_phase(
    root: Path,
    manifest_path: Path,
    phase: str,
    dest_root: Path,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    copied = 0
    skipped = 0
    for row in manifest.get("rows") or []:
        if not isinstance(row, dict) or row.get("phase") != phase:
            continue
        src = root / str(row["path"])
        dest = dest_root / str(row["dest"])
        if not src.is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and dest.read_bytes() == src.read_bytes():
            skipped += 1
            row["status"] = "moved"
            continue
        shutil.copy2(src, dest)
        row["status"] = "moved"
        copied += 1
    _write_manifest(manifest_path, manifest)
    return {"copied": copied, "skipped": skipped, "phase": phase}


def loops_running(home: Path | None = None) -> bool:
    base = home or (Path.home() / ".bmad-loops")
    if not base.is_dir():
        return False
    for state in base.rglob("state.json"):
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            continue
        status = str(data.get("status") or data.get("state") or "").lower()
        if status in {"running", "in_progress", "active", "live"}:
            return True
    return False


def flip_root(
    flags_path: Path,
    target: str,
    realization: Path,
    *,
    loop_home: Path | None = None,
) -> None:
    if target not in CUTOVER_VARIANTS:
        raise CutoverRootError(f"unknown cutover_root variant {target!r}")
    if loops_running(loop_home):
        raise CutoverRootError("flip refused: a Marshal loop is running")
    payload = json.loads(flags_path.read_text(encoding="utf-8"))
    flags = payload.setdefault("flags", {})
    entry = flags.setdefault(
        CUTOVER_FLAG,
        {
            "state": "ENABLED",
            "variants": {k: k for k in CUTOVER_VARIANTS},
            "defaultVariant": DEFAULT_CUTOVER_ROOT,
        },
    )
    entry["defaultVariant"] = target
    atomic_write_text(flags_path, json.dumps(payload, indent=2) + "\n")
    if realization.is_file():
        stamp = f"\n- **cutover flip** — `pyforge.cutover_root` → `{target}`\n"
        realization.write_text(realization.read_text(encoding="utf-8") + stamp, encoding="utf-8")


class CutoverDuty:
    name = "cutover"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "cutover_verb", None)
        if verb not in _CUTOVER_VERBS:
            return DutyResult(ok=False, summary="cutover: need plan, apply, or flip")
        root = _repo_root()
        manifest = Path(getattr(ns, "manifest", None) or root / DEFAULT_MANIFEST)
        try:
            if verb == "plan":
                if getattr(ns, "regenerate", False):
                    payload = plan_regenerate(root, manifest)
                    mode = "regenerate"
                elif getattr(ns, "append", False):
                    payload = plan_append(root, manifest)
                    mode = "append"
                else:
                    return DutyResult(
                        ok=False,
                        summary="cutover plan: pass --regenerate or --append",
                    )
                n = len(payload.get("rows") or [])
                return DutyResult(
                    ok=True,
                    summary=f"cutover plan --{mode}: {n} rows → {manifest}",
                    details={"rows": n, "path": str(manifest)},
                )
            if verb == "apply":
                phase = str(getattr(ns, "phase", "") or "")
                if phase not in _PHASE_RULES:
                    return DutyResult(
                        ok=False,
                        summary="cutover apply: --phase must be 1a or 1b",
                    )
                dest = _foundry_root(Path(ns.foundry_root) if getattr(ns, "foundry_root", None) else None)
                stats = apply_phase(root, manifest, phase, dest)
                return DutyResult(
                    ok=True,
                    summary=(f"cutover apply --phase {phase}: copied {stats['copied']}, skipped {stats['skipped']}"),
                    details=stats,
                )
            target = str(getattr(ns, "to", "") or "")
            flags = resolve_flags_path(getattr(ns, "flags", None))
            if flags is None:
                return DutyResult(ok=False, summary="cutover flip: no flags.json")
            flip_root(flags, target, root / REALIZATION_LOG)
            return DutyResult(
                ok=True,
                summary=f"cutover flip → {read_cutover_root(flags)}",
            )
        except (CutoverRootError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            return DutyResult(ok=False, summary=f"cutover: {exc}")
