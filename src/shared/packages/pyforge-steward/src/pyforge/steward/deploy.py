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
"""

from __future__ import annotations

import argparse
import subprocess
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
    """`git add` the `docs/dashboard/` diff, commit it, and push to the
    currently checked-out branch on `origin` — direct push, no new Actions
    workflow (AD-4). Returns the new commit's full SHA.

    Raises `subprocess.CalledProcessError` on any failing step (nothing to
    commit, a detached HEAD with no branch, a rejected push) — propagated,
    not swallowed, caught only at `DeployDuty`'s boundary. Each step runs in
    sequence rather than a single scripted command so a failure is
    attributable to a specific step by its own `exc.cmd` (see this story's
    spec, "Design Notes" — a push failure after a successful local commit is
    a known, accepted partial-completion state, not silently retried or
    rolled back).
    """
    subprocess.run(
        ["git", "add", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "dashboard: refresh status (steward deploy dashboard)"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    return sha


# ── DeployDuty (Duty-protocol adapter) ──────────────────────────────────────

_DEPLOY_VERBS: tuple[str, ...] = ("dashboard",)


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


class DeployDuty:
    """The real `deploy` duty — dispatches the `dashboard` verb.

    Bare `steward deploy` (no verb) degrades to `DutyResult(ok=True, ...)`
    naming the available verbs (AD-7), matching `KeysDuty`'s identical
    precedent. A subprocess failure (pixi) is caught here as
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
            return _run_dashboard(ns)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            cmd_name = exc.cmd[0] if exc.cmd else "subprocess"
            return DutyResult(
                ok=False,
                summary=f"deploy {verb}: {cmd_name} exited {exc.returncode}: {stderr}",
            )
