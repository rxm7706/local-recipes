"""Story 34.2: explicit ``factory checkpoint`` entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessPort

from ..adapters.fs_local import LocalFs
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core.model import Finding, Severity
from ..core.verdict import compute_verdict, exit_code_for
from ..core.worktree_checkpoint import WorktreeCheckpointResult, commit_worktree_checkpoint
from ..ports.fs import FsPort
from ..ports.vcs import VcsPort
from .dispatch import _load_latest_dispatch_context
from .init import _home_path


def run_factory_checkpoint(args: argparse.Namespace) -> int:
    return _run_factory_checkpoint(
        args.slug,
        fs=LocalFs(),
        vcs=GitVcs(),
        process=PosixProcess(),
    )


def _run_factory_checkpoint(
    slug: str,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    """Checkpoint the in-flight dispatch or spin worktree for ``slug``."""
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    process = process if process is not None else PosixProcess()
    findings: list[Finding] = []

    dispatch_ctx = _load_latest_dispatch_context(fs=fs, vcs=vcs, process=process, slug=slug)
    if dispatch_ctx is not None:
        repo_root, _run_dir, _run_id, journal, _policy = dispatch_ctx
        if journal.worktree_path is None or journal.story_key is None:
            findings.append(
                Finding(
                    code="MRS-CHK-001",
                    severity=Severity.ERROR,
                    message=f"no dispatch worktree to checkpoint for station {slug!r}",
                )
            )
            return exit_code_for(compute_verdict(tuple(findings)))

        worktree = Path(journal.worktree_path)
        result = commit_worktree_checkpoint(
            vcs,
            repo_root=repo_root,
            worktree=worktree,
            story_key=journal.story_key,
        )
        return _emit_checkpoint_result(result, worktree=worktree)

    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-CHK-002",
                severity=Severity.ERROR,
                message=f"not inside a git repository: {exc}",
            )
        )
        return exit_code_for(compute_verdict(tuple(findings)))

    home = _home_path(slug)
    if not home.is_dir():
        findings.append(
            Finding(
                code="MRS-CHK-003",
                severity=Severity.ERROR,
                message=(f"no in-flight dispatch or spin worktree to checkpoint for station {slug!r}"),
            )
        )
        return exit_code_for(compute_verdict(tuple(findings)))

    result = commit_worktree_checkpoint(
        vcs,
        repo_root=repo_root,
        worktree=home,
        story_key=slug,
    )
    return _emit_checkpoint_result(result, worktree=home)


def _emit_checkpoint_result(result: WorktreeCheckpointResult, *, worktree: Path) -> int:
    if result.committed:
        print(
            f"checkpointed {worktree} at {result.head_sha}",
            file=sys.stdout,
        )
        return 0
    reason = result.skipped_reason or "nothing to commit"
    print(f"checkpoint skipped for {worktree}: {reason}", file=sys.stderr)
    return 0 if reason == "clean worktree" else 1
