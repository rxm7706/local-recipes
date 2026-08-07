"""Steward's `deploy` duty-adapter module (AD-1/AD-4) — Epic 2's single file,
mirrors `keys.py`'s "one module per duty" precedent.

Story 2.1 slice: `build_dashboard` — a thin `subprocess` wrap of the existing
`dashboard-gen` pixi task (`pixi run -e local-recipes dashboard-gen`), never a
reimplementation of `docs/dashboard/generate.py`'s own logic (AD-1). `DeployDuty`
is the `Duty`-conforming adapter `cli.py`'s `resolve_duty("deploy")` now
returns, wiring `steward deploy dashboard --build`.
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


# ── DeployDuty (Duty-protocol adapter) ──────────────────────────────────────

_DEPLOY_VERBS: tuple[str, ...] = ("dashboard",)


def _run_dashboard(ns: argparse.Namespace) -> DutyResult:
    """`deploy dashboard --build` (Story 2.1's only wired flag).

    Builds and returns — no diff/commit/push logic yet (Story 2.2).
    """
    root = repo_root()
    build_dashboard(cwd=root)
    return DutyResult(ok=True, summary="deploy dashboard: build complete (docs/dashboard/ refreshed)")


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
