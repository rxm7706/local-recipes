"""``SkillInvokePort`` -- FR-52 sibling seam for headless BMAD planning-skill
invocation (Story 21.2 / FR-192 CAP-1).

``BuildHarnessPort`` launches detached ``bmad-build-auto`` sessions; this
port drives synchronous planning-chain skills (``bmad-spec``,
``bmad-deep-recon``, …) with per-invocation ``BMAD_ACTIVE_PROJECT`` and
physical ``_bmad-output/projects/<slug>/planning-artifacts/`` paths — never
``scripts/bmad-switch``. Implemented solely by
``adapters/skill_invoke_harness.py`` (live/plan) and injectable fakes in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

SkillStatus = Literal["complete", "blocked", "failed"]


@dataclass(frozen=True)
class SkillInvokeResult:
    """Outcome of one planning-skill invocation."""

    status: SkillStatus
    detail: str = ""


class SkillInvokePort(Protocol):
    def invoke_planning_skill(
        self,
        skill: str,
        *,
        root: Path,
        project: str,
        dream: Path,
        phase: str,
        run_dir: Path,
    ) -> SkillInvokeResult:
        """Run one BMAD planning skill against ``project``.

        Must set ``BMAD_ACTIVE_PROJECT=project`` for the child and address
        artifacts by physical path under
        ``_bmad-output/projects/<project>/planning-artifacts/``. Must never
        call ``scripts/bmad-switch``. Must never hand-overwrite memlog-
        derived artifacts — skills own append-then-rerender.
        """
        ...
