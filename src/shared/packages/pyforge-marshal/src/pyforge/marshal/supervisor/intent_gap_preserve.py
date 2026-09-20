"""Intent-gap attempt preservation (Story 20.4, FR-189 / CAP-1 + CAP-2).

Proactive supervisor snapshot while a story worktree is dirty or carries
commits above baseline; on intent-gap escalation with empty ``preserve_ref``,
parks ``attempt-preserve/{run}-{head8}`` (committed work) or
``failed/<story>/changes.patch`` (uncommitted only) under bmad-loop's own run
dir. Git via subprocess only — never imports ``bmad_loop`` (AD-3).
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text
from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ..ports.harness import TaskPhaseSnapshot

# bmad-loop's own ``devcontract.AUTO_RUN_HEADING_RE`` spelling — duplicated
# here so this module never imports ``bmad_loop``.
_AUTO_RUN_HEADING_RE = re.compile(r"^##\s+Auto Run Result\s*$", re.MULTILINE)

# Closed intent-gap vocabulary (spec Design Notes): reason and/or Auto Run
# Result body — never a broad "any escalation" / bare "blocking condition"
# match (those fire for unrelated HALTs too).
_INTENT_GAP_MARKERS = (
    "intent gap",
    "intent_gap",
    "intent-gap",
)

_PRESERVE_SYNTH_NOTE = (
    "_Appended by the Marshal supervisor (Story 20.4 intent-gap preserve): "
    "the attempt was parked before the intent-gap halt reverted the worktree._"
)

_GIT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class AttemptSnapshot:
    """One proactive capture of a story worktree's recoverable attempt state.

    ``head_sha`` is the tip at capture time (needed to name
    ``attempt-preserve/{run}-{head8}`` even after a later revert).
    ``commits_above_baseline`` is the enumerated ``baseline..HEAD`` range.
    ``dirty_patch`` holds a pre-captured unified diff when only uncommitted
    work existed (or complements commits when both were present at capture).
    """

    story_key: str
    worktree_path: str
    baseline_commit: str
    head_sha: str
    commits_above_baseline: tuple[str, ...]
    dirty_patch: str | None = None


class GitPreserveError(PyforgeError, Exception):
    """A git subprocess failed during capture or park."""


def looks_like_intent_gap(
    paused_reason: str | None,
    *,
    auto_run_result_text: str | None = None,
) -> bool:
    """True when ``paused_reason`` and/or Auto Run Result text names an intent-gap halt."""
    haystacks: list[str] = []
    if paused_reason:
        haystacks.append(paused_reason.casefold())
    if auto_run_result_text:
        haystacks.append(auto_run_result_text.casefold())
    if not haystacks:
        return False
    combined = "\n".join(haystacks)
    return any(marker in combined for marker in _INTENT_GAP_MARKERS)


def capture_attempt_snapshot(task: TaskPhaseSnapshot) -> AttemptSnapshot | None:
    """Capture recoverable attempt state from ``task``'s worktree, or ``None``.

    Returns ``None`` when there is no worktree/baseline, the tree is clean
    (no commits above baseline and no uncommitted diff), or git fails.
    """
    if not task.worktree_path or not task.baseline_commit:
        return None
    repo = Path(task.worktree_path)
    if not repo.is_dir():
        return None
    baseline = task.baseline_commit
    try:
        head = _rev_parse_head(repo)
        commits = _commits_above(repo, baseline)
        dirty_patch: str | None = None
        if not commits:
            patch = _capture_diff(repo, baseline)
            if not patch:
                return None
            dirty_patch = patch
        else:
            # Commits above baseline — still capture dirty overlay if present
            # (park prefers the branch; patch is fallback metadata only).
            patch = _capture_diff(repo, baseline)
            dirty_patch = patch or None
        return AttemptSnapshot(
            story_key=task.story_key,
            worktree_path=task.worktree_path,
            baseline_commit=baseline,
            head_sha=head,
            commits_above_baseline=tuple(commits),
            dirty_patch=dirty_patch,
        )
    except GitPreserveError:
        return None


def park_preserve_artifact(
    snapshot: AttemptSnapshot,
    *,
    harness_run_id: str,
    bmad_run_dir: Path,
) -> str | None:
    """Park ``snapshot`` under bmad-loop's deferred naming convention.

    Returns the recovery ref (branch name or patch path), or ``None`` when
    there is nothing to park or git/write fails.
    """
    repo = Path(snapshot.worktree_path)
    if snapshot.commits_above_baseline:
        slug = _safe_ref_segment(harness_run_id)
        # Concatenation (not f"{a}-{b}") — AD-23 forbids the two-placeholder
        # story-key shape outside core/identity.py.
        ref_name = "attempt-preserve/" + slug + "-" + snapshot.head_sha[:8]
        try:
            # Park the *captured* tip — after an intent-gap revert HEAD is
            # already at baseline, so ``branch … HEAD`` would be a no-op.
            parked = _preserve_commits(repo, ref_name, snapshot.head_sha)
        except GitPreserveError:
            parked = None
        # When a dirty overlay was also captured, park it too so uncommitted
        # work on top of attempt commits is not silently dropped (deferred
        # path parks both halves).
        patch_ref: str | None = None
        if snapshot.dirty_patch:
            patch_ref = _write_failed_patch(bmad_run_dir, snapshot.story_key, snapshot.dirty_patch)
        if parked is not None:
            return parked
        return patch_ref
    if snapshot.dirty_patch:
        return _write_failed_patch(bmad_run_dir, snapshot.story_key, snapshot.dirty_patch)
    return None


def _write_failed_patch(bmad_run_dir: Path, story_key: str, patch_body: str) -> str | None:
    if not patch_body:
        return None
    patch_path = bmad_run_dir / "failed" / _safe_segment(story_key) / "changes.patch"
    try:
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_text(patch_body, encoding="utf-8")
        return patch_path.as_posix()
    except OSError:
        return None


def append_preserve_notice(
    spec_path: Path,
    preserve_ref: str,
    *,
    status: str = "escalated",
) -> bool:
    """Name ``preserve_ref`` on the spec's ``## Auto Run Result`` surface.

    When ARR is absent, synthesizes a section. When ARR already exists —
    the common intent-gap case — inserts a ``preserve_ref=…`` block
    immediately after the ARR heading so CAP-2 recovery needs only the ARR
    text. Idempotent when the same ref is already named.
    """
    if not spec_path.is_file():
        return False
    try:
        text = spec_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError, OSError:
        return False
    nl = "\r\n" if "\r\n" in text else "\n"
    detail_line = f"preserve_ref={preserve_ref}"
    if detail_line in text:
        return False
    recovery = (
        "Recovery: checkout the named ref, or run `bmad-loop resolve --restore-patch` when the ref is a patch path."
    )
    notice = f"{nl}{_PRESERVE_SYNTH_NOTE}{nl}{nl}{detail_line}{nl}{recovery}{nl}"
    match = _AUTO_RUN_HEADING_RE.search(text)
    if match:
        # Insert immediately after the ARR heading line (+ its newline).
        insert_at = match.end()
        if insert_at < len(text) and text[insert_at] == "\n":
            insert_at += 1
        elif insert_at + 1 < len(text) and text[insert_at : insert_at + 2] == "\r\n":
            insert_at += 2
        new_text = text[:insert_at] + notice + text[insert_at:]
        try:
            atomic_write_text(spec_path, new_text)
        except OSError:
            return False
        return True
    status = status.strip().lower()
    if text.endswith("\r"):
        text += "\n"
    elif text and not text.endswith("\n"):
        text += nl
    section = f"## Auto Run Result{nl}{nl}Status: {status}{nl}{notice}"
    try:
        atomic_write_text(spec_path, text + section)
    except OSError:
        return False
    return True


def resolve_spec_path(home: Path, spec_file: str | None) -> Path | None:
    """Resolve ``spec_file`` (project-relative or absolute) under ``home``.

    Relative paths that escape ``home`` via ``..`` are refused.
    """
    if not spec_file:
        return None
    raw = Path(spec_file)
    try:
        if raw.is_absolute():
            candidate = raw.resolve()
        else:
            candidate = (home / raw).resolve()
            home_resolved = home.resolve()
            if not candidate.is_relative_to(home_resolved):
                return None
    except OSError, RuntimeError, ValueError:
        return None
    return candidate if candidate.is_file() else None


def _git(repo: Path, *args: str, timeout_s: float = _GIT_TIMEOUT_S) -> tuple[int, str, str]:
    try:
        result = PosixProcess().run(["git", "-C", str(repo), *args], cwd=Path.cwd(), timeout_s=timeout_s)
    except ProcessError as exc:
        raise GitPreserveError(str(exc.__cause__ or exc)) from exc
    stdout = result.stdout if result.stdout else ""
    stderr = result.stderr.strip() if result.stderr else ""
    return result.returncode, stdout.strip(), stderr


def _rev_parse_head(repo: Path) -> str:
    rc, out, detail = _git(repo, "rev-parse", "HEAD")
    if rc != 0:
        raise GitPreserveError(f"git rev-parse HEAD failed: {detail}")
    return out


def _commits_above(repo: Path, baseline: str) -> list[str]:
    rc, out, detail = _git(repo, "rev-list", f"{baseline}..HEAD")
    if rc != 0:
        raise GitPreserveError(f"git rev-list {baseline}..HEAD failed: {detail}")
    return [line for line in out.splitlines() if line]


def _capture_diff(repo: Path, baseline: str) -> str:
    """Unified diff of tracked + untracked changes against ``baseline``."""
    rc, out, detail = _git(repo, "diff", baseline, "--")
    if rc != 0:
        raise GitPreserveError(f"git diff {baseline} failed: {detail}")
    parts = [out]
    rc, untracked, detail = _git(repo, "ls-files", "--others", "--exclude-standard")
    if rc != 0:
        raise GitPreserveError(f"git ls-files --others failed: {detail}")
    for rel in untracked.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        u_rc, u_out, u_detail = _git(repo, "diff", "--no-index", "--", os.devnull, rel)
        if u_rc not in (0, 1):
            raise GitPreserveError(f"git diff --no-index for untracked {rel!r} failed: {u_detail}")
        parts.append(u_out)
    return "".join(parts)


def _preserve_commits(repo: Path, ref_name: str, tip_sha: str) -> str | None:
    rc, out, detail = _git(repo, "branch", "-f", ref_name, tip_sha)
    if rc != 0:
        raise GitPreserveError(f"git branch -f {ref_name} {tip_sha} failed: {detail or out}")
    return ref_name


def _safe_segment(name: str) -> str:
    """Minimal path-segment sanitizer mirroring bmad-loop's ``safe_segment`` contract."""
    illegal = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    cleaned = illegal.sub("_", name).rstrip(". ")[:200]
    if not cleaned:
        cleaned = "_"
    if cleaned == name:
        return name
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    suffix = f"-{digest}"
    return cleaned[: 200 - len(suffix)] + suffix


def _safe_ref_segment(name: str) -> str:
    """Minimal ref-component sanitizer mirroring bmad-loop's ``safe_ref_segment``."""
    illegal = re.compile(r"[\x00-\x1f ~^:?*[\\]")
    cleaned = illegal.sub("_", name.replace("..", "__").replace("@{", "_{"))
    if cleaned.startswith("."):
        cleaned = "_" + cleaned[1:]
    cleaned = cleaned.rstrip(". ")[:200]
    if not cleaned:
        cleaned = "_"
    if cleaned == name:
        return name
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    suffix = f"-{digest}"
    return cleaned[: 200 - len(suffix)] + suffix
