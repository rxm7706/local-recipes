"""Verification-refusal fix turn orchestration (Story 85.1, CAP-286).

Impure edge: harness launch, wait, re-verify. Pure decision/prompt in
``core/dispatch_verify_fix.py``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.flags import read_boolean
from pyforge.core.process import ProcessPort

from .adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from .core import dispatch as dispatch_core
from .core.dispatch_verify_fix import (
    VERIFY_FIX_LOOP_FLAG_KEY,
    VerifyFixLaunchMode,
    build_verify_fix_prompt,
    choose_verify_fix_launch_mode,
    decide_verify_fix_turn,
    extract_failed_verify_commands,
)
from .core.egress import to_redacted_text
from .core.harness_profile import HarnessProfile, WireWrap, wire_port_for_worktree
from .core.harness_profile import render_verify_fix_argv as _render_verify_fix_argv
from .core.harness_profile import resolve_wire_wrap as _resolve_wire_wrap
from .core.journal import JournalEntryId, Phase, build_entry
from .core.policy import EffectivePolicy, resolve_verify_fix_settings
from .dispatch_verify import evaluate_dispatch_verification, resolve_spec_text_for_story
from .ports.build_harness import HarnessResolution
from .ports.fs import FsPort
from .ports.vcs import VcsPort


@dataclass(frozen=True)
class VerifyFixTurnResult:
    completed: bool
    timed_out: bool
    launch_failed: bool
    re_verified: bool
    verified_after_fix: bool
    message: str


def verify_fix_loop_enabled(*, repo_root: Path) -> bool:
    return read_boolean(VERIFY_FIX_LOOP_FLAG_KEY, default=False, flags_path=None)


def _failed_commands_payload(
    command_reports: tuple[dict[str, object], ...],
    findings: tuple,
    *,
    tail_bytes: int,
) -> list[dict[str, object]]:
    failed = extract_failed_verify_commands(command_reports, findings)
    payload: list[dict[str, object]] = []
    for item in failed:
        combined = "\n".join(part for part in (item.stdout, item.stderr) if part.strip())
        tail = combined[-tail_bytes:] if tail_bytes > 0 else ""
        if len(combined.encode("utf-8", errors="replace")) > tail_bytes:
            tail = combined.encode("utf-8", errors="replace")[-tail_bytes:].decode("utf-8", errors="replace")
        payload.append(
            {
                "command": item.command,
                "exit_code": item.exit_code,
                "output_tail": to_redacted_text(tail),
            }
        )
    return payload


def launch_verify_fix_session(
    harness: BmadBuildHarness,
    *,
    resolution: HarnessResolution,
    worktree: Path,
    prompt: str,
    model: str | None,
    log_path: Path,
    wire_layer: dict[str, object] | None,
    launch_mode: VerifyFixLaunchMode,
) -> tuple[int, tuple[str, ...]]:
    if not resolution or resolution.spec is None or resolution.binary_path is None:
        raise BuildHarnessError("no resolved harness profile for verify fix turn")
    profile = resolution.spec
    wire = _resolve_wire_wrap(
        profile,
        wire_layer=wire_layer,
        home=worktree,
        wrapper_binary_path=resolution.wrapper_binary_path,
    )
    if wire.applied and wire.store_dir is not None:
        Path(wire.store_dir).mkdir(parents=True, exist_ok=True)
    argv, _, _ = _render_verify_fix_argv(
        profile,
        mode=launch_mode.value,
        binary_path=resolution.binary_path,
        worktree=worktree,
        prompt=prompt,
        model=model,
        wire=wire,
        wire_port=wire_port_for_worktree(worktree),
    )
    return harness.launch_argv(
        argv,
        worktree=worktree,
        profile=profile,
        resolution=resolution,
        log_path=log_path,
        wire=wire,
        budget_env={},
        project_slug="",
    )


def wait_for_process(
    process: ProcessPort,
    pid: int,
    *,
    timeout_s: float,
    poll_s: float = 1.0,
) -> bool:
    """Wait until ``pid`` exits or ``timeout_s`` elapses. Returns True if exited."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not process.is_alive(pid):
            return True
        time.sleep(poll_s)
    return not process.is_alive(pid)
