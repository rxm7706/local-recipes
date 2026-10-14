"""THE ONLY module permitted to invoke the steward CI-status CLI (Story 100.1, CAP-292).

Follows ``adapters/scribe_cli.py`` discipline: probe ``pyforge`` on ``PATH``, then the
repo's pixi env bin dirs; run ``pyforge steward ci status --json`` through the injected
``ProcessPort`` with a timeout; turn every failure into a reason and raise nothing.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessPort

from ..core.landing_ci_pauses import envelope_is_valid, record_from_envelope, unknown_record

__all__ = (
    "PYFORGE_BINARY",
    "STEWARD_FALLBACK_BIN_DIRS",
    "StewardCli",
    "StewardCiStatusOutcome",
)

PYFORGE_BINARY = "pyforge"

STEWARD_FALLBACK_BIN_DIRS: tuple[str, ...] = (
    ".pixi/envs/pyforge-steward/bin",
    ".pixi/envs/pyforge-guild/bin",
)

_CI_STATUS_TIMEOUT_S = 120.0

_STEWARD_CI_STATUS_ARGV_TAIL = ("steward", "ci", "status", "--json")


@dataclass(frozen=True)
class StewardCiStatusOutcome:
    ok: bool
    envelope: dict[str, object] | None = None
    reason: str | None = None
    argv: tuple[str, ...] = field(default_factory=tuple)


def _first_stderr_line(stderr: str) -> str:
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "<no stderr>"


class StewardCli:
    def __init__(self, process: ProcessPort) -> None:
        self._process = process

    def resolve_binary(
        self,
        repo_root: Path | None = None,
        *,
        fallback_bin_dirs: Sequence[str] = STEWARD_FALLBACK_BIN_DIRS,
    ) -> str | None:
        on_path = shutil.which(PYFORGE_BINARY)
        if on_path is not None:
            return on_path
        if repo_root is None:
            return None
        for rel_dir in fallback_bin_dirs:
            candidate = Path(repo_root) / rel_dir / PYFORGE_BINARY
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None

    def ci_status(
        self,
        *,
        repo_root: Path,
        binary_path: str | None = None,
    ) -> StewardCiStatusOutcome:
        resolved = binary_path if binary_path is not None else self.resolve_binary(repo_root)
        if resolved is None:
            return StewardCiStatusOutcome(
                ok=False,
                reason="no pyforge binary on PATH or in the repo pixi env bin dirs",
            )
        argv = (resolved, *_STEWARD_CI_STATUS_ARGV_TAIL)
        try:
            result = self._process.run(argv, cwd=Path(repo_root), timeout_s=_CI_STATUS_TIMEOUT_S)
        except ProcessError as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                return StewardCiStatusOutcome(
                    ok=False,
                    argv=argv,
                    reason=f"steward ci status timed out after {_CI_STATUS_TIMEOUT_S}s",
                )
            return StewardCiStatusOutcome(
                ok=False,
                argv=argv,
                reason=f"steward ci status could not run ({exc})",
            )
        stderr_first = _first_stderr_line(result.stderr or "")
        if result.returncode == 1:
            return StewardCiStatusOutcome(
                ok=False,
                argv=argv,
                reason=f"steward ci status partial read (exit 1): {stderr_first}",
            )
        if result.returncode != 0:
            return StewardCiStatusOutcome(
                ok=False,
                argv=argv,
                reason=f"steward ci status refused (exit {result.returncode}): {stderr_first}",
            )
        stdout = (result.stdout or "").strip()
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return StewardCiStatusOutcome(
                ok=False,
                argv=argv,
                reason="steward ci status stdout is not JSON",
            )
        if not envelope_is_valid(parsed):
            return StewardCiStatusOutcome(
                ok=False,
                argv=argv,
                reason="steward ci status stdout is not the ci-status envelope",
            )
        return StewardCiStatusOutcome(ok=True, envelope=parsed, argv=argv)

    def ci_status_record(
        self,
        *,
        repo_root: Path,
        binary_path: str | None = None,
    ) -> dict[str, object]:
        """Return the landing journal record (``read`` or ``unknown``). Never raises."""
        outcome = self.ci_status(repo_root=repo_root, binary_path=binary_path)
        if outcome.ok and outcome.envelope is not None:
            return record_from_envelope(outcome.envelope)
        return unknown_record(outcome.reason or "steward ci status failed")
