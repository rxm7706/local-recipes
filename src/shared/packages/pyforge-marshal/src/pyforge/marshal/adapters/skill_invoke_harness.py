"""FR-52 adapter for planning-skill invocation (Story 21.2).

Default behaviour is **plan/dry-run**: record the intended skill and return
``complete`` without launching an LLM. Live mode optionally drives the same
session-harness binary ``BmadBuildHarness`` uses (``cursor agent``), with
``BMAD_ACTIVE_PROJECT`` per invocation and physical planning-artifact paths —
never ``scripts/bmad-switch``.

Live launches are synchronous (wait for exit) because the chain orchestrator
needs a ``complete`` / ``blocked`` / ``failed`` result before advancing.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from pyforge.core.errors import PyforgeError

from ..ports.skill_invoke import SkillInvokeResult


class SkillInvokeError(PyforgeError, Exception):
    """Raised when a live skill invocation could not be launched."""


_CURSOR_AGENT_BINARY = "cursor"
# Live skill phases can take a long time; bound so a hung agent cannot
# freeze the orchestrator forever. Override via MARSHAL_SKILL_TIMEOUT.
_DEFAULT_SKILL_TIMEOUT_S = 3600.0
_STATUS_RE = re.compile(r"STATUS:\s*(BLOCKED|FAILED|COMPLETE)\b", re.IGNORECASE)


class PlanSkillInvoker:
    """Default injectable: plan-only; never touches an LLM or git."""

    def __init__(self) -> None:
        self.invocations: list[str] = []

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
        del root, dream, run_dir  # plan runner only records intent
        self.invocations.append(skill)
        return SkillInvokeResult(
            status="complete",
            detail=f"planned: {skill} phase={phase} project={project}",
        )


class HarnessSkillInvoker:
    """Live FR-52 adapter: session harness with ``BMAD_ACTIVE_PROJECT``.

    When ``live`` is False (default), delegates to ``PlanSkillInvoker``.
    When True, launches ``cursor agent`` synchronously against ``root``.
    """

    def __init__(self, *, live: bool = False) -> None:
        self._live = live
        self._plan = PlanSkillInvoker()

    def binary_present(self) -> bool:
        return shutil.which(_CURSOR_AGENT_BINARY) is not None

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
        if not self._live:
            return self._plan.invoke_planning_skill(
                skill,
                root=root,
                project=project,
                dream=dream,
                phase=phase,
                run_dir=run_dir,
            )
        if not self.binary_present():
            return SkillInvokeResult(
                status="failed",
                detail="session harness binary not found on PATH (cursor)",
            )
        planning = root / "_bmad-output" / "projects" / project / "planning-artifacts"
        prompt = (
            f"Run the BMAD skill {skill!r} headlessly for planning-chain "
            f"phase {phase!r}.\n"
            f"Station: {project}\n"
            f"Dream (physical path): {dream}\n"
            f"Planning artifacts (physical path): {planning}\n"
            f"Run journal dir: {run_dir}\n"
            f"Use BMAD_ACTIVE_PROJECT={project} and physical artifact paths "
            f"under _bmad-output/projects/{project}/ — never "
            f"scripts/bmad-switch.\n"
            f"Drive the skill's memlog-derivation path (append-then-rerender); "
            f"never hand-overwrite derived SPEC.md / prd.md / architecture / "
            f"epics artifacts.\n"
            f"When finished, print exactly one of: STATUS:complete, "
            f"STATUS:blocked, STATUS:failed.\n"
        )
        argv = [
            _CURSOR_AGENT_BINARY,
            "agent",
            "--trust",
            "--workspace",
            str(root),
            prompt,
        ]
        child_env = {**os.environ, "BMAD_ACTIVE_PROJECT": project}
        log_path = run_dir / f"phase_{phase}_{skill}.log"
        timeout_s = _skill_timeout_s()
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            with open(log_path, "wb") as log_file:
                # Story 14.4, CAP-6: stays raw subprocess, exempted
                # file-level in test_process_sole_ownership.py -- same
                # capability gap as harness_bmadbuild.py's Popen site:
                # PosixProcess.run has no env= override (by design, always
                # inherits os.environ exactly) and does not redirect
                # stdout/stderr to a file, both required here
                # (BMAD_ACTIVE_PROJECT per invocation + a synchronous,
                # file-logged wait-for-exit). Mutating process-global
                # os.environ as a workaround would race a concurrent
                # invocation for a different project.
                completed = subprocess.run(
                    argv,
                    cwd=root,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=child_env,
                    check=False,
                    timeout=timeout_s,
                )
        except subprocess.TimeoutExpired as exc:
            return SkillInvokeResult(
                status="failed",
                detail=f"skill harness timed out after {timeout_s}s: {exc}",
            )
        except (OSError, ValueError) as exc:
            raise SkillInvokeError(f"cannot launch skill harness {argv!r}: {exc}") from exc

        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            log_text = ""

        status = _parse_status(log_text, completed.returncode)
        return SkillInvokeResult(
            status=status,
            detail=f"exit={completed.returncode} log={log_path.name}",
        )


def _skill_timeout_s() -> float:
    raw = os.environ.get("MARSHAL_SKILL_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_SKILL_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_SKILL_TIMEOUT_S
    return value if value > 0 else _DEFAULT_SKILL_TIMEOUT_S


def _parse_status(log_text: str, returncode: int) -> str:
    """Map harness log + exit code to ``complete`` / ``blocked`` / ``failed``.

    Explicit ``STATUS:`` markers win (whitespace-tolerant). Bare exit 0
    without a marker is ``failed`` so a silent/partial agent run cannot
    advance the chain as success.
    """
    del returncode  # markers are authoritative; bare exit is never success
    match = _STATUS_RE.search(log_text)
    if match is None:
        return "failed"
    token = match.group(1).upper()
    if token == "BLOCKED":
        return "blocked"
    if token == "FAILED":
        return "failed"
    return "complete"
