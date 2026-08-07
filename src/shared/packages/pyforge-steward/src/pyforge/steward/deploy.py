"""Steward's `deploy` duty-adapter module (AD-1/AD-4) — Epic 2's single file,
mirrors `keys.py`'s "one module per duty" precedent.

Story 2.1 slice: `build_dashboard` — a thin `subprocess` wrap of the existing
`dashboard-gen` pixi task (`pixi run -e local-recipes dashboard-gen`), never a
reimplementation of `docs/dashboard/generate.py`'s own logic (AD-1). `DeployDuty`
is the `Duty`-conforming adapter `cli.py`'s `resolve_duty("deploy")` now
returns, wiring `steward deploy dashboard --build`.

Story 2.2 slice: `dashboard_diff` (git-diff the freshly built `docs/dashboard/`
tree against the committed one) and `commit_and_push_dashboard` (git add +
commit + push to the currently checked-out branch) — together the FR-9
reconciled-push behavior: bare `steward deploy dashboard` builds, diffs, and
only commits+pushes on a real difference (AD-4 — no daemon, no new workflow;
the operator or an existing workflow invokes the CLI).

Story 2.3 slice: `--dry-run` on the same `dashboard` verb — build+diff,
print, never commit/push. No new primitive; `_run_dashboard` just gains a
third branch alongside `--build`/bare-reconcile.

Story 2.4 slice: `last_deploy_commit` — reads the last commit that touched
`docs/dashboard/` straight from `git log` (no separate state file, per
FR-11). Wired as `steward deploy status`.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .interfaces import DutyResult

# ── Repo-root resolution (mirrors `keys.py`'s `locate_http_module`/`repo_root`
# walk-up precedent, keyed on a marker this duty actually cares about rather
# than importing `keys.py` — that module's own top-level import reaches into
# `.claude/skills/conda-forge-expert/scripts/_http.py` and refuses to load
# outside a local-recipes checkout, which `cli.py`'s `resolve_duty` docstring
# already flags as a reason NOT to import it eagerly from an unrelated duty) ──

_DASHBOARD_GENERATE_MARKER = Path("docs/dashboard/generate.py")
_DASHBOARD_RELATIVE_PATH = Path("docs/dashboard")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    Walks up from this file's own resolved location looking for
    `docs/dashboard/generate.py` — robust to whatever depth the installed/
    editable `pyforge-steward` package ends up at relative to the repo root,
    same rationale as `keys.py`'s `locate_http_module`.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _DASHBOARD_GENERATE_MARKER).is_file():
            return ancestor
    raise RuntimeError(
        f"deploy.py: could not locate {_DASHBOARD_GENERATE_MARKER} by walking "
        f"up from {here} — this module must live inside a local-recipes checkout."
    )


# ── Build primitive (FR-8, Story 2.1) ───────────────────────────────────────

_DEFAULT_BUILD_CMD: tuple[str, ...] = ("pixi", "run", "-e", "local-recipes", "dashboard-gen")


def build_dashboard(
    *, cwd: str | Path, cmd: Sequence[str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the `dashboard-gen` pixi task as a subprocess (AD-1).

    `cmd` defaults to the real invocation (`pixi run -e local-recipes
    dashboard-gen`) — the exact pixi task named in `pixi.toml`'s
    `[feature.local-recipes.tasks.dashboard-gen]`. Overridable so a test can
    substitute a fast fixture command without installing the ~9.8GB
    `local-recipes` env (see this story's spec, "Design Notes").

    Raises `subprocess.CalledProcessError` on a non-zero exit — propagated,
    not swallowed — caught only at `DeployDuty`'s boundary (mirrors
    `KeysDuty`'s existing `age`-failure handling).
    """
    return subprocess.run(
        list(cmd) if cmd is not None else list(_DEFAULT_BUILD_CMD),
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


# ── Diff + reconciled push (FR-9, Story 2.2) ────────────────────────────────


def dashboard_diff(*, cwd: str | Path) -> str:
    """Return the `git diff` text for `docs/dashboard/` against the committed
    tree (unstaged changes to already-tracked files only — `dashboard-gen`
    only ever rewrites the existing tracked `data.js` in place, never adds a
    new file).

    Empty string means no diff. Raises `subprocess.CalledProcessError` if
    `git diff` itself fails (e.g. `cwd` is not a git worktree) — propagated,
    not swallowed.
    """
    result = subprocess.run(
        ["git", "diff", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def commit_and_push_dashboard(*, cwd: str | Path) -> str:
    """`git add` the `docs/dashboard/` diff, commit it (scoped to that same
    pathspec), and push to the currently checked-out branch on `origin` —
    direct push, no new Actions workflow (AD-4). Returns the new commit's
    full SHA.

    Review finding: the branch is now resolved (`git symbolic-ref --short
    HEAD`) FIRST, before any write -- a detached-HEAD checkout used to
    commit successfully and only fail resolving the push branch AFTER an
    orphan commit already existed, silently, with no record it was ever
    made once garbage-collected. Refusing before the commit means a
    detached-HEAD failure leaves the working tree exactly as it was.

    Review finding: `git commit` is now scoped to `-- docs/dashboard`
    (mirrors the preceding `git add`'s own pathspec) rather than a bare
    `git commit`, which commits the ENTIRE index regardless of what `git
    add` staged -- any unrelated file staged by the operator or another
    process sharing this working tree at call time would otherwise ride
    along into this commit and get pushed under a misleading message.

    Raises `subprocess.CalledProcessError` on any failing step (a detached
    HEAD with no branch, nothing to commit, a rejected push) — propagated,
    not swallowed, caught only at `DeployDuty`'s boundary, which now names
    the exact failing command (see `DeployDuty.run`) rather than a bare
    `"git"`. A push failure after a successful local commit is a known,
    accepted partial-completion state -- not rolled back here, but the next
    `deploy dashboard` invocation now detects and retries it (see
    `_push_pending_commit_if_ahead`) rather than silently reporting "nothing
    to deploy".
    """
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "add", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "dashboard: refresh status (steward deploy dashboard)",
         "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    return sha


def _push_pending_commit_if_ahead(*, cwd: str | Path) -> str | None:
    """Review finding: if an earlier `commit_and_push_dashboard` call
    committed successfully but its push failed, the local branch is left
    AHEAD of `origin` with a real, already-committed change. The next
    `steward deploy dashboard` run would previously build fresh content
    identical to what's already committed, see an EMPTY `dashboard_diff`
    (the working tree already matches the ahead-of-origin HEAD), and report
    "nothing to deploy" -- permanently hiding the earlier push failure;
    `deploy status` would also report the unpushed commit as if it were a
    completed deploy.

    Called before the diff check (never during `--dry-run`, which must
    never push): if HEAD is ahead of its upstream, push it now and return
    the pushed SHA. Returns `None` if not ahead (the ordinary case,
    including "no upstream configured" or a detached HEAD -- `@{u}`
    resolution failing here is treated as "cannot tell", not an error; the
    normal build/diff/commit flow's own git calls surface a clearer error
    if something about the checkout is genuinely broken).
    """
    ahead = subprocess.run(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        cwd=str(cwd), capture_output=True, text=True,
    )
    if ahead.returncode != 0:
        return None
    count = ahead.stdout.strip()
    if not count.isdigit() or int(count) == 0:
        return None
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()


# ── Deploy status (FR-11, Story 2.4) ────────────────────────────────────────


@dataclass(frozen=True)
class DeployRecord:
    """The last commit that touched `docs/dashboard/` — SHA + committer
    timestamp, read straight from `git log`. No separate state file exists
    anywhere (FR-11's explicit constraint); this IS the record."""

    sha: str
    timestamp: str


_LOG_FORMAT = "%H\x1f%cI"  # full SHA + strict-ISO committer date, unit-separated


def last_deploy_commit(*, cwd: str | Path) -> DeployRecord | None:
    """Return the last commit touching `docs/dashboard/`, or `None` if none
    exists.

    Reads git history directly (`git log -1`) — never a separate state file
    (per FR-11's "no separate state store" constraint; see this story's
    spec, "Design Notes" for why no Steward-provenance filter is applied).

    Raises `subprocess.CalledProcessError` if `git log` itself fails (e.g.
    `cwd` is not a git worktree) — propagated, not swallowed.
    """
    result = subprocess.run(
        ["git", "log", "-1", f"--format={_LOG_FORMAT}", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    output = result.stdout.strip()
    if not output:
        return None
    sha, timestamp = output.split("\x1f")
    return DeployRecord(sha=sha, timestamp=timestamp)


# ── DeployDuty (Duty-protocol adapter) ──────────────────────────────────────

_DEPLOY_VERBS: tuple[str, ...] = ("dashboard", "status")


def _run_dashboard(ns: argparse.Namespace) -> DutyResult:
    """`deploy dashboard [--build] [--dry-run]`.

    `--build` always wins over `--dry-run` if both are passed (build-only is
    the narrower operation; ACs don't define combining them, so this is a
    documented judgment call, not a silent one — see this story's spec,
    "Design Notes") — builds and returns without ever computing a diff.

    Otherwise: build, then diff `docs/dashboard/` against the committed
    tree. No diff → `ok=True`, "nothing to deploy", regardless of
    `--dry-run` (FR-9's zero-commit-on-no-diff property). A real diff with
    `--dry-run` → the diff is printed; `commit_and_push_dashboard` is never
    called, so `git log`/`git status` are left unchanged. A real diff with
    neither flag → commit + push (Story 2.2's FR-9 reconciled-push
    behavior).
    """
    root = repo_root()
    build_dashboard(cwd=root)

    if getattr(ns, "build", False):
        return DutyResult(ok=True, summary="deploy dashboard: build complete (docs/dashboard/ refreshed)")

    if not getattr(ns, "dry_run", False):
        # Review finding: check for (and retry) an earlier run's unpushed
        # commit BEFORE the diff-based no-op check below -- otherwise a
        # stuck unpushed commit permanently masquerades as "nothing to
        # deploy" forever (see `_push_pending_commit_if_ahead`'s own
        # docstring). Never runs during `--dry-run`, which must never push.
        pending_sha = _push_pending_commit_if_ahead(cwd=root)
        if pending_sha is not None:
            return DutyResult(
                ok=True,
                summary=(
                    f"deploy dashboard: pushed previously-committed {pending_sha} "
                    "(an earlier run's push had failed and was retried)"
                ),
            )

    diff_text = dashboard_diff(cwd=root)
    if not diff_text.strip():
        return DutyResult(ok=True, summary="deploy dashboard: no diff — nothing to deploy")

    if getattr(ns, "dry_run", False):
        return DutyResult(
            ok=True,
            summary=f"deploy dashboard: pending diff (dry-run, not committed):\n{diff_text}",
        )

    sha = commit_and_push_dashboard(cwd=root)
    return DutyResult(ok=True, summary=f"deploy dashboard: committed and pushed {sha}")


def _run_status(ns: argparse.Namespace) -> DutyResult:  # noqa: ARG001 -- no flags yet
    """`deploy status` — reports the last commit touching `docs/dashboard/`.

    Review finding: previously reported the last commit's SHA/timestamp
    unconditionally, even if that commit was never actually pushed (a prior
    `deploy dashboard` committed but its push failed) -- misreporting a
    local-only commit as a completed deploy. Now appends an explicit note
    when HEAD is ahead of its upstream, using the SAME `@{u}`-based check
    `_push_pending_commit_if_ahead` uses (read-only here -- `status` never
    pushes) -- still no separate state file (FR-11)."""
    root = repo_root()
    record = last_deploy_commit(cwd=root)
    if record is None:
        return DutyResult(ok=True, summary="deploy status: no dashboard deploy commit found in git history")
    ahead = subprocess.run(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        cwd=str(root), capture_output=True, text=True,
    )
    unpushed_note = ""
    if ahead.returncode == 0:
        count = ahead.stdout.strip()
        if count.isdigit() and int(count) > 0:
            unpushed_note = " -- HEAD is ahead of origin; the most recent commit(s) may not be pushed yet"
    return DutyResult(
        ok=True,
        summary=f"deploy status: last deploy {record.sha} at {record.timestamp}{unpushed_note}",
    )


class DeployDuty:
    """The real `deploy` duty — dispatches the `dashboard`/`status` verbs.

    Bare `steward deploy` (no verb) degrades to `DutyResult(ok=True, ...)`
    naming the available verbs (AD-7), matching `KeysDuty`'s identical
    precedent. A subprocess failure (pixi, git) is caught here as
    `subprocess.CalledProcessError` and reported as a duty-level failure,
    never conflated with an internal crash (AD-8 — that boundary is
    `cli.main()`'s alone).
    """

    name = "deploy"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "deploy_verb", None)
        if verb not in _DEPLOY_VERBS:
            return DutyResult(
                ok=True,
                summary=f"deploy: available verbs are {', '.join(_DEPLOY_VERBS)}",
            )
        try:
            if verb == "dashboard":
                return _run_dashboard(ns)
            return _run_status(ns)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            # Review finding: `exc.cmd[0]` was always the literal string
            # "git" (every subprocess call in this module starts with it),
            # so the summary never actually named which step failed despite
            # this module's own docstrings claiming per-step attribution.
            # The full command line does.
            cmd_name = " ".join(str(part) for part in exc.cmd) if exc.cmd else "subprocess"
            return DutyResult(
                ok=False,
                summary=f"deploy {verb}: `{cmd_name}` exited {exc.returncode}: {stderr}",
            )
