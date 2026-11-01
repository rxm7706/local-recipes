"""Fix-target solver seam (Stories 14.1, 14.4).

The default implementation copies the scan target (without ``.pixi/`` or
``.git``) into a throwaway directory, sets the candidate floor in the one
manifest that declares the package through
``manifest_edit.edit_requirement_to_floor`` -- the edit path Story 14.2's fix
takes, so ``pixi.toml``, ``pyproject.toml`` and recipe declarations are all
probed -- and runs ``pixi lock`` through ``engines.run_pixi_lock``.
``resolve_fix_target`` tries at most ``MAX_FIX_CANDIDATES`` candidates within a
total ``FIX_SOLVE_BUDGET_SECONDS``; an overrun is a failed resolution. Tests
inject a fake seam -- no subprocess, no manifest touch.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from packaging.version import InvalidVersion, Version
from pyforge.core.errors import PyforgeError

from .engines import PIXI_LOCK_TIMEOUT_SECONDS, PIXI_VERSION_RANGE, run_pixi_lock
from .manifest_edit import MANIFEST_FILE_NAMES, edit_requirement_to_floor
from .manifest_fixup import copy_scan_target

SolverVerdict = str  # "accepted" | "rejected"

# Story 14.4 (WAR-M-D5): the candidate loop is bounded. At most this many
# OSV-fixed candidates are tried, lowest first...
MAX_FIX_CANDIDATES = 5
# ...within this total solve budget per finding. The default solver's
# ``pixi lock`` gets the smaller of ``PIXI_LOCK_TIMEOUT_SECONDS`` and what is
# left of the budget, so one solve cannot outrun it.
FIX_SOLVE_BUDGET_SECONDS = 1800.0


@runtime_checkable
class FixTargetSolver(Protocol):
    """Whether ``floor_version`` is acceptable for ``package`` in ``scan_target``."""

    def __call__(self, *, scan_target: Path, package: str, floor_version: str) -> SolverVerdict: ...


@dataclass(frozen=True)
class FixTargetResolution:
    """The outcome of trying OSV fixed candidates for one upgrade finding."""

    target: str | None
    candidates: tuple[str, ...]
    attempts: tuple[tuple[str, SolverVerdict], ...]
    solver: str
    failure_detail: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "candidates": list(self.candidates),
            "attempts": [{"candidate": candidate, "verdict": verdict} for candidate, verdict in self.attempts],
            "solver": self.solver,
            "failure_detail": self.failure_detail,
        }


def _current_version_from_finding_id(finding_id: str) -> Version | None:
    if "@" not in finding_id:
        return None
    segment = finding_id.rsplit("@", 1)[-1]
    if segment == "unspecified":
        return None
    try:
        return Version(segment)
    except InvalidVersion:
        return None


def eligible_candidates(
    finding_id: str,
    raw_candidates: Sequence[str] | None,
) -> tuple[str, ...]:
    """Drop fixed events below the scanned version; sort ascending by PEP 440."""
    if not raw_candidates:
        return ()
    current = _current_version_from_finding_id(finding_id)
    parsed: list[tuple[Version, str]] = []
    for candidate in raw_candidates:
        try:
            version = Version(candidate)
        except InvalidVersion:
            continue
        if current is not None and version < current:
            continue
        parsed.append((version, candidate))
    parsed.sort(key=lambda item: item[0])
    return tuple(candidate for _version, candidate in parsed)


def resolve_fix_target(
    finding_id: str,
    raw_candidates: Sequence[str] | None,
    *,
    dry_run: bool,
    scan_target: Path | None,
    solver: FixTargetSolver | None = None,
    max_candidates: int = MAX_FIX_CANDIDATES,
    solve_budget_seconds: float = FIX_SOLVE_BUDGET_SECONDS,
    pixi_lock_timeout_seconds: float = PIXI_LOCK_TIMEOUT_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> FixTargetResolution:
    """Pick the lowest acceptable fixed release, or report failure.

    The real path tries at most ``max_candidates`` candidates and starts no
    solve once ``solve_budget_seconds`` have passed; either bound ends the
    loop with a resolution whose ``failure_detail`` names it."""
    candidates = eligible_candidates(finding_id, raw_candidates)
    if not candidates:
        return FixTargetResolution(
            target=None,
            candidates=(),
            attempts=(),
            solver="not-run",
            failure_detail="no fixed-version candidates at or above the current release",
        )
    if dry_run:
        return FixTargetResolution(
            target=candidates[0],
            candidates=candidates,
            attempts=(),
            solver="not-run",
        )
    if scan_target is None or not scan_target.is_dir():
        return FixTargetResolution(
            target=None,
            candidates=candidates,
            attempts=(),
            solver="pixi-lock",
            failure_detail="no scan target directory for the solver seam",
        )
    package = _package_from_finding_id(finding_id)
    attempts: list[tuple[str, SolverVerdict]] = []
    started = clock()
    for candidate in candidates[:max_candidates]:
        remaining = solve_budget_seconds - (clock() - started)
        if remaining <= 0:
            return FixTargetResolution(
                target=None,
                candidates=candidates,
                attempts=tuple(attempts),
                solver="pixi-lock",
                failure_detail=(
                    f"solve budget of {solve_budget_seconds:g}s exhausted after "
                    f"{len(attempts)} of {len(candidates)} candidate(s)"
                ),
            )
        if solver is None:
            verdict = default_pixi_lock_solver(
                scan_target=scan_target,
                package=package,
                floor_version=candidate,
                timeout=min(pixi_lock_timeout_seconds, remaining),
            )
        else:
            verdict = solver(scan_target=scan_target, package=package, floor_version=candidate)
        attempts.append((candidate, verdict))
        if verdict == "accepted":
            return FixTargetResolution(
                target=candidate,
                candidates=candidates,
                attempts=tuple(attempts),
                solver="pixi-lock",
            )
    if len(candidates) > max_candidates:
        failure_detail = (
            f"candidate cap of {max_candidates} reached: the solver accepted none of the "
            f"first {max_candidates} of {len(candidates)} candidates"
        )
    else:
        failure_detail = "no candidate was accepted by the solver seam"
    return FixTargetResolution(
        target=None,
        candidates=candidates,
        attempts=tuple(attempts),
        solver="pixi-lock",
        failure_detail=failure_detail,
    )


def _package_from_finding_id(finding_id: str) -> str:
    """The subject segment between the second ``:`` and the ``@`` version."""
    parts = finding_id.split(":", 2)
    if len(parts) < 3:
        return ""
    tail = parts[2]
    if "@" in tail:
        return tail.rsplit("@", 1)[0]
    return tail


def _editable_manifests(root: Path) -> list[Path]:
    """Every manifest ``edit_requirement_to_floor`` can edit under ``root``, sorted."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        found.extend(Path(dirpath) / name for name in sorted(filenames) if name.lower() in MANIFEST_FILE_NAMES)
    return found


def _probe_floor(root: Path, package: str, floor: str) -> bool:
    """Set ``package`` to ``>=floor`` in the copy at ``root`` through the fix's own edit path.

    True when exactly one manifest declares it; a package declared in more than
    one manifest is refused, as ``prepare_manifest_fix`` refuses it."""
    edited = sum(
        1
        for manifest in _editable_manifests(root)
        if edit_requirement_to_floor(manifest, package=package, floor=floor).ok
    )
    return edited == 1


def default_pixi_lock_solver(
    *,
    scan_target: Path,
    package: str,
    floor_version: str,
    timeout: float = PIXI_LOCK_TIMEOUT_SECONDS,
) -> SolverVerdict:
    """Copy ``scan_target``, set the floor, run ``pixi lock``; never writes the scan tree."""
    if not package:
        return "rejected"
    temp_dir = Path(tempfile.mkdtemp(prefix="warden-fix-solver-"))
    try:
        copy_scan_target(scan_target, temp_dir)
        if not _probe_floor(temp_dir, package, floor_version):
            return "rejected"
        error, exit_code = run_pixi_lock(cwd=temp_dir, timeout=timeout)
        if error is not None:
            if "outside" in error.message or "incompatible" in error.message:
                raise PixiVersionOutOfRangeError(str(PIXI_VERSION_RANGE))
            return "rejected"
        if exit_code != 0:
            return "rejected"
        return "accepted"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class PixiVersionOutOfRangeError(PyforgeError, RuntimeError):
    """Raised when ``pixi`` on PATH is outside ``PIXI_VERSION_RANGE``."""


def rejecting_solver(**_kwargs: object) -> SolverVerdict:
    return "rejected"


def accepting_solver(**_kwargs: object) -> SolverVerdict:
    return "accepted"


def selective_solver(refuse: set[str]) -> FixTargetSolver:
    def _seam(*, scan_target: Path, package: str, floor_version: str) -> SolverVerdict:
        del scan_target, package
        return "rejected" if floor_version in refuse else "accepted"

    return _seam
