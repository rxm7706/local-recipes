"""THE ONLY module permitted to invoke the session harness (``cursor agent``)
for ``bmad-build-auto`` dispatch (Story 22.1, FR-52 second engine, AD-3
extended) -- enforced by the same import-linter discipline as
``harness_bmadloop.py``.

Detached launch only: subprocess ``Popen`` with ``start_new_session=True``,
``BMAD_ACTIVE_PROJECT`` passed per-invocation, never ``scripts/bmad-switch``."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from pyforge.core.errors import PyforgeError

from ..ports.build_harness import DispatchLaunchResult


class BuildHarnessError(PyforgeError, Exception):
    """Raised when the session harness could not be launched."""


_CURSOR_AGENT_BINARY = "cursor"


class BmadBuildHarness:
    """``BuildHarnessPort``'s sole implementation (Story 22.1)."""

    def binary_present(self) -> bool:
        return shutil.which(_CURSOR_AGENT_BINARY) is not None

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
        prompt = (
            f"Run bmad-build-auto for this single story only.\n"
            f"Station: {project_slug}\n"
            f"Story: {story_key}\n"
            f"Spec (physical path): {spec_path}\n"
            f"Use BMAD_ACTIVE_PROJECT={project_slug} and physical artifact "
            f"paths under _bmad-output/projects/{project_slug}/ — never "
            f"scripts/bmad-switch.\n"
        )
        argv = [
            _CURSOR_AGENT_BINARY,
            "agent",
            "--trust",
            "--workspace",
            str(worktree),
        ]
        if model:
            argv.extend(["--model", model])
        argv.append(prompt)

        child_env = {**os.environ, "BMAD_ACTIVE_PROJECT": project_slug, **dict(budget_env)}
        try:
            log_file = open(log_path, "wb")  # noqa: SIM115
        except (OSError, ValueError) as exc:
            raise BuildHarnessError(
                f"cannot open dispatch log {str(log_path)!r}: {exc}"
            ) from exc
        with log_file:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=worktree,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    env=child_env,
                )
            except (OSError, ValueError) as exc:
                raise BuildHarnessError(
                    f"cannot launch session harness {argv!r}: {exc}"
                ) from exc
        return DispatchLaunchResult(
            pid=process.pid,
            command=tuple(argv),
            model=model,
            budget_env=dict(budget_env),
        )
