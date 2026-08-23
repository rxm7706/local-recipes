"""``BuildHarnessPort`` -- the FR-52 seam for the second engine
(``bmad-build-auto`` / a plain background agent session), sibling to
``HarnessPort``'s bmad-loop coverage (Story 22.1, spec-marshal-single-story-
dispatch CAP-1).

A Protocol definition only; implemented solely by
``adapters/harness_bmadbuild.py``. Every subprocess invocation of the
session harness lives there -- never scattered through ``cli/`` or
``core/`` (AD-4 / FR-52)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


@dataclass(frozen=True)
class DispatchLaunchResult:
    """Detached ``BuildHarnessPort.dispatch`` result (Story 22.1): facts the
    caller could not know before launch."""

    pid: int
    command: tuple[str, ...]
    model: str | None
    budget_env: Mapping[str, str]


class BuildHarnessPort(Protocol):
    def binary_present(self) -> bool:
        """``True`` iff the session harness CLI resolves on ``PATH``. Never
        raises."""
        ...

    def dispatch(
        self,
        worktree: Path,
        *,
        project_slug: str,
        story_key: str,
        spec_path: Path,
        model: str | None,
        budget_env: Mapping[str, str],
        log_path: Path,
    ) -> DispatchLaunchResult:
        """Detach-launch one plain background agent session running
        ``bmad-build-auto`` against ``spec_path`` inside ``worktree``.
        ``BMAD_ACTIVE_PROJECT`` is set to ``project_slug`` in the child's
        environment; artifact paths are physical under the worktree (never
        ``scripts/bmad-switch``). Raises ``BuildHarnessError`` only when the
        process could not be LAUNCHED."""
        ...
