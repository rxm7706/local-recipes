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

Story 28.2 (SPEC-marshal-token-economy CAP-2) adds the wire-compression
seam to the same launch: when policy's declared ``[context]`` ``wire``
layer is enabled and the resolved profile declares a ``[wrapper]`` whose
binary resolves, the CLI launches THROUGH it (``headroom wrap claude --
<the same argv as before>``) with the reversible CCR store scoped inside
the dispatch worktree. The decision itself is pure
(``core/harness_profile.py::resolve_wire_wrap``); this module owns only
its impure halves -- probing the wrapper binary, creating the store
directory, and composing the child environment. An unavailable wrapper
disables the layer with a reason on the returned ``DispatchLaunchResult``
and launches unwrapped: never a blocked run.

Detached launch only: subprocess ``Popen`` with ``start_new_session=True``
(never a CLI's own self-backgrounding flag, which would double-detach and
orphan the PID the dispatch supervisor tracks), ``BMAD_ACTIVE_PROJECT``
passed per-invocation, never ``scripts/bmad-switch``."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import BinaryIO

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ..core.dispatch_verify_fix import VERIFY_FIX_PROMPT_FILENAME
from ..core.harness_profile import (
    HarnessProfile,
    HarnessProfileError,
    WireWrap,
    load_profiles,
    verify_fix_prompt_on_stdin,
    wire_port_for_worktree,
)
from ..core.harness_profile import render_dispatch_argv as _render_dispatch_argv
from ..core.harness_profile import render_verify_fix_argv as _render_verify_fix_argv
from ..core.harness_profile import resolve_wire_wrap as _resolve_wire_wrap
from ..ports.build_harness import (
    DispatchLaunchResult,
    HarnessCandidateSkip,
    HarnessResolution,
)
from .harness_bmadloop import _SURFACE_RECONCILE_COMMAND


class BuildHarnessError(PyforgeError, Exception):
    """Raised when the session harness could not be launched."""


#: Ceiling for one authcheck probe. Generous for a status command (cursor's
#: and claude's both answer in well under a second) while bounding a
#: wedged/prompting CLI -- a probe that cannot answer inside this window is
#: treated as an auth failure (skip with reason), never a hang.
_AUTHCHECK_TIMEOUT_S = 20.0

#: Story 53.1 (spec-53-1, CAP-261a): states the S-13.7 obligation verbatim
#: in the dispatched session's OWN prompt. A bmad-loop session reads its
#: verify commands straight out of its rendered ``policy.toml`` and finds
#: the guard (``adapters.harness_bmadloop._SURFACE_RECONCILE_COMMAND``)
#: sitting there; a dispatched session never reads ``policy.toml`` or this
#: module at all, so without this text it has no way to know the guard is
#: coming until ``dispatch_verify.py`` -- which runs AFTER the session has
#: already exited (CAP-3) -- refuses it. Names the same command the guard
#: actually runs, so a session that greps its own prompt for the command
#: can find it.
_SPEC_SURFACE_OBLIGATION = (
    "This run's own verification includes "
    f"`{_SURFACE_RECONCILE_COMMAND}` -- the same S-13.7 guard bmad-loop "
    "sessions already run. Before finishing, name every governed path you "
    "changed on the owning Spec's `.memlog.md` and on each co-governor "
    "`spec-surface` names; the guard fails your verification naming any "
    "path you leave out. Never pass --write-baseline: a producer that "
    "stamps its own baseline launders drift instead of reconciling it. "
    "Every `deferred:` entry you write must cite a real repo path in "
    "`location:`.\n"
)


def _resolve_binary(binary: str, fallback_bin_dirs: Sequence[str], repo_root: Path | None) -> str | None:
    """``PATH`` first, then the given repo-root-relative fallback dirs (the
    pixi-env CLIs are invisible to a bare operator PATH -- honest probing
    rather than assuming dispatch always runs under ``pixi run``). Returns
    the resolved path string, or ``None``.

    Story 28.2 widened the parameters from a whole ``HarnessProfile`` to
    the two fields it actually reads, so the profile's ``[wrapper]`` binary
    resolves through the IDENTICAL probe rather than a second copy of it."""
    on_path = shutil.which(binary)
    if on_path is not None:
        return on_path
    if repo_root is None:
        return None
    for rel_dir in fallback_bin_dirs:
        candidate = Path(repo_root) / rel_dir / binary
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
        result = PosixProcess().run(argv, cwd=Path.cwd(), timeout_s=_AUTHCHECK_TIMEOUT_S)
    except ProcessError as exc:
        return f"authcheck {argv!r} could not run: {exc.__cause__ or exc}"
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        tail = output.strip().splitlines()[-1] if output.strip() else ""
        return f"authcheck {argv!r} exited {result.returncode}" + (f" ({tail})" if tail else "")
    if profile.authcheck_ok_pattern and not re.search(profile.authcheck_ok_pattern, output):
        tail = output.strip().splitlines()[-1] if output.strip() else "<no output>"
        return f"authcheck {argv!r} output did not confirm login (wanted /{profile.authcheck_ok_pattern}/, got: {tail})"
    return None


def _write_private_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` readable by its owner only (0600, also when the file already exists) -- a fix
    turn's prompt carries scrubbed command output, never meant for another account (Story 85.3)."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(text)
    except OSError as exc:
        raise BuildHarnessError(f"cannot write fix-turn prompt file {str(path)!r}: {exc}") from exc


class BmadBuildHarness:
    """``BuildHarnessPort``'s sole implementation (Story 22.1; profile-
    driven since Story 22.8)."""

    def launch_argv(
        self,
        argv: Sequence[str],
        *,
        worktree: Path,
        profile: HarnessProfile,
        resolution: HarnessResolution,
        log_path: Path,
        wire: WireWrap,
        budget_env: Mapping[str, str],
        project_slug: str,
        stdin_path: Path | None = None,
    ) -> tuple[int, tuple[str, ...]]:
        """Detach-launch an already-rendered argv; return ``(pid, command)``.

        ``stdin_path`` (Story 85.3): a fix turn's prompt file, opened read-only as the session's stdin; every
        other launch keeps ``/dev/null``.

        The one launcher behind both ``dispatch`` (the story session, Story
        22.1) and ``dispatch_verify_fix`` (Story 85.1's fix turn): the child
        env, the wire layer's PATH and the detached ``Popen`` live here once.
        ``BMAD_ACTIVE_PROJECT`` is set unconditionally, as ``dispatch``
        always set it -- an empty ``project_slug`` pins an empty project
        rather than inheriting the operator shell's.
        """
        # Precedence, lowest to highest: the operator's environment, the
        # profile's own declared vars, the wire layer's own vars (Story
        # 28.2), marshal's per-invocation project pin, the policy budget
        # env -- a profile or a wrapper may tune its CLI but never repoint
        # the dispatched project or the budget ceilings.
        child_env = {
            **os.environ,
            **dict(profile.env),
            **dict(wire.env),
            "BMAD_ACTIVE_PROJECT": project_slug,
            **dict(budget_env),
        }
        if wire.applied and resolution.binary_path is not None:
            # Wrapping replaces the resolved CLI path with the wrapper's
            # prefix, and the wrapper then resolves the CLI itself off
            # PATH. A CLI that only lives in a profile `fallback_bin_dirs`
            # entry (the pixi-env case this repo runs on) would vanish at
            # that point, so its own directory is prepended -- restoring
            # exactly the reachability the unwrapped launch already had,
            # and nothing more.
            binary_dir = str(Path(resolution.binary_path).parent)
            existing_path = child_env.get("PATH", "")
            child_env["PATH"] = f"{binary_dir}{os.pathsep}{existing_path}" if existing_path else binary_dir
        try:
            log_file = open(log_path, "wb")  # noqa: SIM115
        except (OSError, ValueError) as exc:
            raise BuildHarnessError(f"cannot open dispatch log {str(log_path)!r}: {exc}") from exc
        with contextlib.ExitStack() as handles:
            handles.enter_context(log_file)
            stdin_source: int | BinaryIO = subprocess.DEVNULL
            if stdin_path is not None:
                try:
                    stdin_source = handles.enter_context(open(stdin_path, "rb"))
                except OSError as exc:
                    raise BuildHarnessError(f"cannot open fix-turn prompt file {str(stdin_path)!r}: {exc}") from exc
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
                    stdin=stdin_source,
                    stdout=log_file,
                    stderr=log_file,
                    env=child_env,
                )
            except (OSError, ValueError) as exc:
                raise BuildHarnessError(f"cannot launch session harness {list(argv)!r}: {exc}") from exc
        return process.pid, tuple(argv)

    def dispatch_verify_fix(
        self,
        worktree: Path,
        *,
        resolution: HarnessResolution,
        prompt: str,
        model: str | None,
        log_path: Path,
        wire_layer: Mapping[str, object] | None = None,
        launch_mode: str,
        project_slug: str,
        budget_env: Mapping[str, str] | None = None,
        harness_session_id: str = "",
        run_dir: Path | None = None,
    ) -> DispatchLaunchResult:
        """Launch one fix-only or resume session (Story 85.1, not bmad-build-auto)."""
        if not resolution or resolution.spec is None or resolution.binary_path is None:
            raise BuildHarnessError("cannot launch verify fix turn: no resolved profile")
        profile = resolution.spec
        wire = _resolve_wire_wrap(
            profile,
            wire_layer=wire_layer,
            home=worktree,
            wrapper_binary_path=resolution.wrapper_binary_path,
        )
        if wire.applied and wire.store_dir is not None:
            try:
                Path(wire.store_dir).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                wire = WireWrap(
                    applied=False,
                    reason=(
                        f"wire-compression store {wire.store_dir!r} could not be "
                        f"created: {exc} -- the layer is off for this launch"
                    ),
                    aggressiveness=wire.aggressiveness,
                )
        try:
            prompt_on_stdin = verify_fix_prompt_on_stdin(profile, mode=launch_mode)
        except HarnessProfileError as exc:
            raise BuildHarnessError(str(exc)) from exc
        prompt_dir = run_dir if run_dir is not None else log_path.parent
        prompt_path = (prompt_dir / VERIFY_FIX_PROMPT_FILENAME).resolve()
        _write_private_text(prompt_path, prompt)
        argv, rendered_model, model_omitted_reason = _render_verify_fix_argv(
            profile,
            mode=launch_mode,
            binary_path=resolution.binary_path,
            worktree=worktree,
            model=model,
            wire=wire,
            wire_port=wire_port_for_worktree(worktree),
            session_id=harness_session_id,
            prompt_file=str(prompt_path),
        )
        pid, command = self.launch_argv(
            argv,
            worktree=worktree,
            profile=profile,
            resolution=resolution,
            log_path=log_path,
            wire=wire,
            budget_env=budget_env or {},
            project_slug=project_slug,
            stdin_path=prompt_path if prompt_on_stdin else None,
        )
        return DispatchLaunchResult(
            pid=pid,
            command=command,
            model=rendered_model,
            budget_env=dict(budget_env or {}),
            profile=profile.name,
            model_omitted_reason=model_omitted_reason,
            wire=wire,
        )

    def binary_present(self, preference: Sequence[str] = (), repo_root: Path | None = None) -> HarnessResolution:
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
            binary_path = _resolve_binary(profile.binary, profile.fallback_bin_dirs, repo_root)
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
            # Story 28.2: probe the wire-compression wrapper's binary while
            # `repo_root` is in hand. Deliberately AFTER the candidate has
            # already won -- an unresolvable wrapper degrades its own layer
            # (MRS-DISP-033) and never disqualifies an otherwise
            # dispatchable profile, and no authcheck runs against it (the
            # wrapper carries no credentials of its own; it launches the
            # CLI whose auth was just confirmed).
            wrapper_binary_path = (
                _resolve_binary(profile.wrapper.binary, profile.wrapper.fallback_bin_dirs, repo_root)
                if profile.wrapper is not None
                else None
            )
            return HarnessResolution(
                profile=name,
                binary_path=binary_path,
                spec=profile,
                skipped=tuple(skipped),
                profile_errors=profile_errors,
                wrapper_binary_path=wrapper_binary_path,
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
        wire_layer: Mapping[str, object] | None = None,
        harness_session_id: str = "",
    ) -> DispatchLaunchResult:
        if not resolution or resolution.spec is None or resolution.binary_path is None:
            raise BuildHarnessError(
                "cannot launch session harness: no resolved profile "
                f"(skipped: {[s.profile for s in resolution.skipped]!r})"
            )
        profile = resolution.spec
        try:
            spec_path.resolve().relative_to(worktree.resolve())
        except ValueError as exc:
            raise BuildHarnessError(
                f"spec_path {str(spec_path)!r} is not inside dispatch "
                f"worktree {str(worktree)!r} — refusing to leak writes "
                f"onto the primary tree"
            ) from exc
        prompt = (
            f"Run bmad-build-auto for this single story only.\n"
            f"Station: {project_slug}\n"
            f"Story: {story_key}\n"
            f"Spec (physical path): {spec_path}\n"
            f"Use BMAD_ACTIVE_PROJECT={project_slug} and physical artifact "
            f"paths under _bmad-output/projects/{project_slug}/ — never "
            f"scripts/bmad-switch.\n"
            f"{_SPEC_SURFACE_OBLIGATION}"
        )
        # Story 28.2 (SPEC-marshal-token-economy CAP-2): the wire-
        # compression decision, resolved from the SAME `[context]` payload
        # `core/policy.py::resolve_context_layers` hands both engines. The
        # store directory is created HERE -- `core/harness_profile.py` is
        # pure (AD-4) and may not touch the filesystem, and a store the
        # wrapper cannot write to would make its compression irreversible,
        # so an uncreatable store DISABLES the layer rather than launching
        # into it (reversible or absent).
        wire = _resolve_wire_wrap(
            profile,
            wire_layer=wire_layer,
            home=worktree,
            wrapper_binary_path=resolution.wrapper_binary_path,
        )
        if wire.applied and wire.store_dir is not None:
            try:
                Path(wire.store_dir).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                wire = WireWrap(
                    applied=False,
                    reason=(
                        f"wire-compression store {wire.store_dir!r} could not be "
                        f"created: {exc} -- the layer is off for this launch (a "
                        "store the wrapper cannot write to makes its compression "
                        "irreversible) and the session runs unwrapped"
                    ),
                    aggressiveness=wire.aggressiveness,
                )
        argv, rendered_model, model_omitted_reason = _render_dispatch_argv(
            profile,
            binary_path=resolution.binary_path,
            worktree=worktree,
            prompt=prompt,
            model=model,
            wire=wire,
            wire_port=wire_port_for_worktree(worktree),
            session_id=harness_session_id,
        )
        pid, command = self.launch_argv(
            argv,
            worktree=worktree,
            profile=profile,
            resolution=resolution,
            log_path=log_path,
            wire=wire,
            budget_env=budget_env,
            project_slug=project_slug,
        )
        return DispatchLaunchResult(
            pid=pid,
            command=command,
            model=rendered_model,
            budget_env=dict(budget_env),
            profile=profile.name,
            model_omitted_reason=model_omitted_reason,
            wire=wire,
        )
