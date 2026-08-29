"""THE ONLY module permitted to invoke a session-harness CLI for
``bmad-build-auto`` dispatch (Story 22.1, FR-52 second engine, AD-3
extended) -- enforced by the same import-linter discipline as
``harness_bmadloop.py``. Story 22.8 (FR-193 CAP-8) makes the seam
adapter-plural: the launch is profile-driven across coding-agent CLIs
(claude / cursor / gemini / copilot / devin / overlay-extensible), selected
by policy's ordered ``harness_preference`` -- the hardcoded ``cursor
agent`` invocation this module started life as survives verbatim as the
``cursor`` profile.

Everything subprocess-shaped lives here and only here: ``shutil.which`` +
fallback-dir binary probing, the per-profile authcheck subprocess (the
2026-08-27 lesson: three real dispatches died on ``cursor agent``'s auth
wall while ``shutil.which`` reported the harness present -- binary presence
is necessary-but-insufficient), and the detached launch. The pure half --
profile shape, parsing, loading, argv rendering, model translation -- is
``core/harness_profile.py``.

Detached launch only: subprocess ``Popen`` with ``start_new_session=True``
(never a CLI's own self-backgrounding flag, which would double-detach and
orphan the PID the dispatch supervisor tracks), ``BMAD_ACTIVE_PROJECT``
passed per-invocation, never ``scripts/bmad-switch``."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ..core.harness_profile import HarnessProfile, load_profiles
from ..core.harness_profile import render_dispatch_argv as _render_dispatch_argv
from ..ports.build_harness import (
    DispatchLaunchResult,
    HarnessCandidateSkip,
    HarnessResolution,
)


class BuildHarnessError(PyforgeError, Exception):
    """Raised when the session harness could not be launched."""


#: Ceiling for one authcheck probe. Generous for a status command (cursor's
#: and claude's both answer in well under a second) while bounding a
#: wedged/prompting CLI -- a probe that cannot answer inside this window is
#: treated as an auth failure (skip with reason), never a hang.
_AUTHCHECK_TIMEOUT_S = 20.0


def _resolve_binary(profile: HarnessProfile, repo_root: Path | None) -> str | None:
    """``PATH`` first, then the profile's repo-root-relative fallback dirs
    (the pixi-env CLIs are invisible to a bare operator PATH -- honest
    probing rather than assuming dispatch always runs under ``pixi run``).
    Returns the resolved path string, or ``None``."""
    on_path = shutil.which(profile.binary)
    if on_path is not None:
        return on_path
    if repo_root is None:
        return None
    for rel_dir in profile.fallback_bin_dirs:
        candidate = Path(repo_root) / rel_dir / profile.binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _authcheck_failure(profile: HarnessProfile, binary_path: str) -> str | None:
    """Run the profile's declared authcheck; ``None`` on pass, else the
    skip reason. No declared authcheck passes vacuously (the profile's
    ``authcheck_note`` documents why none exists). Output-matched when the
    profile declares ``authcheck_ok_pattern`` -- exit code alone is NOT
    sufficient (cursor's trust prompt and gemini's trust refusal both exit
    0, verified live 2026-08-27)."""
    if not profile.authcheck_args:
        return None
    argv = [binary_path, *profile.authcheck_args]
    try:
        result = PosixProcess().run(
            argv, cwd=Path.cwd(), timeout_s=_AUTHCHECK_TIMEOUT_S
        )
    except ProcessError as exc:
        return f"authcheck {argv!r} could not run: {exc.__cause__ or exc}"
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        tail = output.strip().splitlines()[-1] if output.strip() else ""
        return (
            f"authcheck {argv!r} exited {result.returncode}"
            + (f" ({tail})" if tail else "")
        )
    if profile.authcheck_ok_pattern and not re.search(
        profile.authcheck_ok_pattern, output
    ):
        tail = output.strip().splitlines()[-1] if output.strip() else "<no output>"
        return (
            f"authcheck {argv!r} output did not confirm login "
            f"(wanted /{profile.authcheck_ok_pattern}/, got: {tail})"
        )
    return None


class BmadBuildHarness:
    """``BuildHarnessPort``'s sole implementation (Story 22.1; profile-
    driven since Story 22.8)."""

    def binary_present(
        self, preference: Sequence[str] = (), repo_root: Path | None = None
    ) -> HarnessResolution:
        profiles, profile_errors = load_profiles(repo_root)
        skipped: list[HarnessCandidateSkip] = []
        for name in preference:
            profile = profiles.get(name)
            if profile is None:
                skipped.append(
                    HarnessCandidateSkip(
                        profile=name,
                        reason=(
                            "unknown harness profile (not packaged, no "
                            f"overlay under {'_bmad-output/harness-profiles'!r})"
                        ),
                    )
                )
                continue
            binary_path = _resolve_binary(profile, repo_root)
            if binary_path is None:
                skipped.append(
                    HarnessCandidateSkip(
                        profile=name,
                        reason=f"binary {profile.binary!r} not found on PATH",
                    )
                )
                continue
            failure = _authcheck_failure(profile, binary_path)
            if failure is not None:
                skipped.append(HarnessCandidateSkip(profile=name, reason=failure))
                continue
            return HarnessResolution(
                profile=name,
                binary_path=binary_path,
                spec=profile,
                skipped=tuple(skipped),
                profile_errors=profile_errors,
            )
        return HarnessResolution(
            profile=None,
            skipped=tuple(skipped),
            profile_errors=profile_errors,
        )

    def dispatch(
        self,
        worktree: Path,
        *,
        resolution: HarnessResolution,
        project_slug: str,
        story_key: str,
        spec_path: Path,
        model: str | None,
        budget_env: Mapping[str, str],
        log_path: Path,
    ) -> DispatchLaunchResult:
        if not resolution or resolution.spec is None or resolution.binary_path is None:
            raise BuildHarnessError(
                "cannot launch session harness: no resolved profile "
                f"(skipped: {[s.profile for s in resolution.skipped]!r})"
            )
        profile = resolution.spec
        prompt = (
            f"Run bmad-build-auto for this single story only.\n"
            f"Station: {project_slug}\n"
            f"Story: {story_key}\n"
            f"Spec (physical path): {spec_path}\n"
            f"Use BMAD_ACTIVE_PROJECT={project_slug} and physical artifact "
            f"paths under _bmad-output/projects/{project_slug}/ — never "
            f"scripts/bmad-switch.\n"
        )
        argv, rendered_model, model_omitted_reason = _render_dispatch_argv(
            profile,
            binary_path=resolution.binary_path,
            worktree=worktree,
            prompt=prompt,
            model=model,
        )

        # Precedence, lowest to highest: the operator's environment, the
        # profile's own declared vars, marshal's per-invocation project pin,
        # the policy budget env -- a profile may tune its CLI but never
        # repoint the dispatched project or the budget ceilings.
        child_env = {
            **os.environ,
            **dict(profile.env),
            "BMAD_ACTIVE_PROJECT": project_slug,
            **dict(budget_env),
        }
        try:
            log_file = open(log_path, "wb")  # noqa: SIM115
        except (OSError, ValueError) as exc:
            raise BuildHarnessError(
                f"cannot open dispatch log {str(log_path)!r}: {exc}"
            ) from exc
        with log_file:
            try:
                # Story 14.4, CAP-6: stays raw subprocess, exempted
                # file-level in test_process_sole_ownership.py -- needs a
                # capability pyforge.core.process does NOT offer. Neither
                # PosixProcess.run (waits synchronously, no file-redirected
                # stdout) nor spawn_detached (no env= override -- inherits
                # os.environ exactly, by design) supports a DETACHED launch
                # with a per-invocation custom env (BMAD_ACTIVE_PROJECT +
                # profile env + budget env). Mutating process-global
                # os.environ as a workaround would race concurrent
                # dispatches for different projects -- the exact class of
                # bug the "never scripts/bmad-switch" convention exists to
                # avoid.
                process = subprocess.Popen(
                    list(argv),
                    cwd=worktree,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    env=child_env,
                )
            except (OSError, ValueError) as exc:
                raise BuildHarnessError(
                    f"cannot launch session harness {list(argv)!r}: {exc}"
                ) from exc
        return DispatchLaunchResult(
            pid=process.pid,
            command=tuple(argv),
            model=rendered_model,
            budget_env=dict(budget_env),
            profile=profile.name,
            model_omitted_reason=model_omitted_reason,
        )
