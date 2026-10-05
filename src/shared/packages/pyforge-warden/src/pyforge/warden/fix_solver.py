"""Fix-target solver seam (Story 14.1).

The default implementation copies the scan target into a throwaway directory,
applies a solver-internal floor probe to ``pixi.toml`` (not Story 14.2's PR
diff plan), and runs ``pixi lock`` through ``engines.run_pixi_lock``. Tests
inject a fake seam — no subprocess, no manifest touch.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from packaging.version import InvalidVersion, Version

from .engines import PIXI_VERSION_RANGE, run_pixi_lock

SolverVerdict = str  # "accepted" | "rejected"


@runtime_checkable
class FixTargetSolver(Protocol):
    """Whether ``floor_version`` is acceptable for ``package`` in ``scan_target``."""

    def __call__(self, *, scan_target: Path, package: str, floor_version: str) -> SolverVerdict:
        ...


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
) -> FixTargetResolution:
    """Pick the lowest acceptable fixed release, or report failure."""
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
    seam = solver if solver is not None else default_pixi_lock_solver
    attempts: list[tuple[str, SolverVerdict]] = []
    for candidate in candidates:
        verdict = seam(scan_target=scan_target, package=_package_from_finding_id(finding_id), floor_version=candidate)
        attempts.append((candidate, verdict))
        if verdict == "accepted":
            return FixTargetResolution(
                target=candidate,
                candidates=candidates,
                attempts=tuple(attempts),
                solver="pixi-lock",
            )
    return FixTargetResolution(
        target=None,
        candidates=candidates,
        attempts=tuple(attempts),
        solver="pixi-lock",
        failure_detail="no candidate was accepted by the solver seam",
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


def _probe_pixi_toml_floor(pixi_toml: Path, package: str, floor: str) -> bool:
    """Solver-internal: set one pypi dependency line to ``>=floor`` for probing."""
    if not pixi_toml.is_file():
        return False
    text = pixi_toml.read_text(encoding="utf-8")
    pattern = re.compile(
        rf'^(\s*"{re.escape(package)}"\s*=\s*")([^"]*)(")\s*$',
        re.MULTILINE,
    )
    if not pattern.search(text):
        pattern = re.compile(
            rf"^(\s*{re.escape(package)}\s*=\s*')([^']*)(')\s*$",
            re.MULTILINE,
        )
    replacement = rf'\1>={floor}\3'
    updated, count = pattern.subn(replacement, text, count=1)
    if count == 0:
        return False
    pixi_toml.write_text(updated, encoding="utf-8")
    return True


def default_pixi_lock_solver(*, scan_target: Path, package: str, floor_version: str) -> SolverVerdict:
    """Copy ``scan_target``, probe ``pixi.toml``, run ``pixi lock``; never writes the scan tree."""
    temp_dir = Path(tempfile.mkdtemp(prefix="warden-fix-solver-"))
    try:
        shutil.copytree(scan_target, temp_dir, dirs_exist_ok=True)
        pixi_toml = temp_dir / "pixi.toml"
        if not _probe_pixi_toml_floor(pixi_toml, package, floor_version):
            return "rejected"
        error, exit_code = run_pixi_lock(cwd=temp_dir)
        if error is not None:
            if "outside" in error.message or "incompatible" in error.message:
                raise PixiVersionOutOfRangeError(str(PIXI_VERSION_RANGE))
            return "rejected"
        if exit_code != 0:
            return "rejected"
        return "accepted"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class PixiVersionOutOfRangeError(RuntimeError):
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
