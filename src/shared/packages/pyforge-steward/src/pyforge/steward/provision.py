"""Steward's `provision` duty-adapter module (AD-1/AD-5) — Epic 3's single
file, mirrors `deploy.py`'s "one module per duty" precedent.

Epic 3 is a thin CLI face over the existing pixi estate and
`scripts/bmad-loop-worktree` — this module never reimplements pixi's own
environment-resolution logic, nor `bmad-loop-worktree`'s own worktree
provisioning (AD-1/AD-5). Every primitive below is either a read of
`pixi.toml`'s own declared `[environments]` table, or a thin `subprocess`
wrap of the real `pixi`/`bmad-loop-worktree` binaries.

Story 3.1 slice: `load_pixi_environments` (a read-only `tomllib` parse of
`pixi.toml`'s `[environments]` table — name -> composing features, handling
both the shorthand list form and the explicit `{ features = [...] }` table
form) and `materialize_environment` (a `pixi install -e <name>` subprocess
wrap). Wired as `steward provision --env <name>`.

Story 5.1 RETIRED the Story 3.2 slice. `provision --runner bmad-loop` used to
wrap the LEGACY `scripts/bmad-loop-worktree`; `marshal init` is a strict
superset (worktree + marker/symlink agreement + the AD-11 never-write proof +
an idempotent step report), so two stations were shipping two ways to make the
same thing, one of them the weaker one. `--runner` now REPORTS and points at
`marshal init <slug>`; it never provisions. `run_bmad_loop_worktree` and its
stdout parser are deleted rather than left importable — a retirement that
leaves the old path callable is a deprecation, not a removal.
`_BMAD_LOOP_WORKTREE_RELATIVE_PATH` survives: `repo_root()` locates the
monorepo by finding that script, which is unrelated to running it.

Story 3.3 slice: `format_environments` — read-only text/`--json` rendering
of `load_pixi_environments`'s own output. Wired as `steward provision
--list [--json]`.

Story 3.4 slice: `check_environment_sync` — wraps the EXACT sync-gate
comparison `.github/workflows/scripts/linter.py` already runs on every PR
(read `environment.yaml`, run `pixi project export conda-environment -e
build`, compare both `.rstrip()`'d) rather than reimplementing the
comparison a second way (AD-1). Wired as `steward provision --verify`.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from .interfaces import DutyResult

# ── Repo-root resolution (mirrors `deploy.py`'s/`keys.py`'s own walk-up
# precedent, keyed on a marker unique to the repo root that THIS duty
# actually cares about — `pixi.toml` itself is NOT a safe marker, because
# `src/shared/packages/pyforge-steward/pixi.toml` is a second, unrelated
# pixi.toml belonging to this very package, which a naive walk-up would hit
# FIRST when searching from this file's own location) ─────────────────────

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_PIXI_TOML_RELATIVE_PATH = Path("pixi.toml")
_ENVIRONMENT_YAML_RELATIVE_PATH = Path("environment.yaml")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    Walks up from this file's own resolved location looking for
    `scripts/bmad-loop-worktree` — unlike `pixi.toml`, that path exists
    exactly once in this repo, at the true root, so it cannot be confused
    with the package-local `pixi.toml` this very module ships alongside.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"provision.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


# ── Environment inventory (FR-12, Story 3.1) ────────────────────────────────


def load_pixi_environments(*, cwd: str | Path) -> dict[str, tuple[str, ...]]:
    """Parse `pixi.toml`'s `[environments]` table into `{name: features}`.

    Read-only — Steward never writes to `pixi.toml` (AD-5). Handles both
    shapes pixi's own manifest allows: the shorthand list form (`name =
    ["feat1", "feat2"]`, where the list doubles as both the environment's
    membership and its feature composition) and the explicit table form
    (`name = { features = [...], no-default-feature = true }`). An entry of
    neither shape degrades to an empty feature tuple rather than raising —
    this primitive reports what pixi.toml declares, it does not validate
    pixi's own manifest schema (that is `pixi`'s job, exercised the moment
    `materialize_environment` actually shells out to it).

    Raises `FileNotFoundError` if `pixi.toml` doesn't exist at `cwd`, and
    `tomllib.TOMLDecodeError` for a malformed manifest — both propagated,
    not swallowed.
    """
    pixi_toml = Path(cwd) / _PIXI_TOML_RELATIVE_PATH
    with pixi_toml.open("rb") as f:
        document = tomllib.load(f)
    raw = document.get("environments", {})
    environments: dict[str, tuple[str, ...]] = {}
    for name, value in raw.items():
        if isinstance(value, list):
            environments[name] = tuple(value)
        elif isinstance(value, dict):
            environments[name] = tuple(value.get("features", ()))
        else:
            environments[name] = ()
    return environments


def format_environments(environments: dict[str, tuple[str, ...]], *, as_json: bool) -> str:
    """Render `environments` for `steward provision --list`.

    `as_json=True`: a JSON object, `{name: [features...]}`, sorted by name —
    `{}` for no environments, the correct machine-parseable empty state.
    `as_json=False`: an aligned text table (name + composing features); a
    plain sentence for no environments.
    """
    if as_json:
        return json.dumps(
            {name: list(environments[name]) for name in sorted(environments)}, indent=2
        )
    if not environments:
        return "provision --list: no environments found in pixi.toml"
    width = max(len(name) for name in environments)
    lines = [
        f"{name:<{width}}  {', '.join(environments[name])}" for name in sorted(environments)
    ]
    return "\n".join(lines)


# ── Environment materialization (FR-12, Story 3.1) ──────────────────────────


def materialize_environment(name: str, *, cwd: str | Path) -> subprocess.CompletedProcess[str]:
    """`pixi install -e <name>` as a subprocess (AD-1/AD-5) — no reimplemented
    environment-resolution logic; this only shells out to the real `pixi`
    binary. `cwd` is the pixi project root to install into — the main repo
    root for `--env`, or a freshly provisioned worktree for `--runner
    bmad-loop --env` (Story 3.2).

    Raises `subprocess.CalledProcessError` on a non-zero exit — propagated,
    not swallowed — caught only at `ProvisionDuty`'s boundary.
    """
    return subprocess.run(
        ["pixi", "install", "-e", name],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


# ── Runner provisioning (FR-13, Story 3.2) ──────────────────────────────────

def _run_list(ns: argparse.Namespace) -> DutyResult:
    """`provision --list [--json]` (Story 3.3)."""
    root = repo_root()
    environments = load_pixi_environments(cwd=root)
    return DutyResult(
        ok=True, summary=format_environments(environments, as_json=getattr(ns, "json", False))
    )


# ── Sync-gate check (FR-15, Story 3.4) ──────────────────────────────────────

_SYNC_EXPORT_CMD: tuple[str, ...] = ("pixi", "project", "export", "conda-environment", "-e", "build")


def check_environment_sync(*, cwd: str | Path) -> tuple[bool, str]:
    """Wrap the EXACT sync-gate check `.github/workflows/scripts/linter.py`
    already runs on every PR to this repo (AD-1: reuse, never reimplement
    the comparison) — reads `environment.yaml`, runs `pixi project export
    conda-environment -e build`, and compares both `.rstrip()`'d, exactly
    like the linter's own logic.

    Returns `(in_sync, diff_text)`. `diff_text` is empty when in sync,
    otherwise a unified diff (`environment.yaml` vs. the freshly exported
    text).

    Raises `FileNotFoundError` if `environment.yaml` doesn't exist at `cwd`,
    and `subprocess.CalledProcessError` if `pixi project export` itself
    fails — both propagated, not swallowed.
    """
    root = Path(cwd)
    original = (root / _ENVIRONMENT_YAML_RELATIVE_PATH).read_text(encoding="utf-8").rstrip()
    exported = subprocess.run(
        list(_SYNC_EXPORT_CMD),
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.rstrip()
    if original == exported:
        return True, ""
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            exported.splitlines(keepends=True),
            fromfile="environment.yaml",
            tofile="pixi project export conda-environment -e build",
        )
    )
    return False, diff


def _run_verify(ns: argparse.Namespace) -> DutyResult:  # noqa: ARG001 -- no flags yet
    """`provision --verify` (Story 3.4)."""
    root = repo_root()
    in_sync, diff = check_environment_sync(cwd=root)
    if in_sync:
        return DutyResult(
            ok=True, summary="provision --verify: environment.yaml is in sync with pixi.toml"
        )
    return DutyResult(
        ok=False,
        summary=(
            "provision --verify: environment.yaml is out of sync with pixi.toml. "
            "Fix by running `pixi project export conda-environment -e build > "
            f"environment.yaml`.\n{diff}"
        ),
    )


# ── ProvisionDuty (Duty-protocol adapter) ───────────────────────────────────

_PROVISION_HELP = (
    "available flags: --env <name> | --runner bmad-loop --env <name> | "
    "--list [--json] | --verify"
)


def _run_env(ns: argparse.Namespace) -> DutyResult:
    """`provision --env <name>` (Story 3.1)."""
    root = repo_root()
    environments = load_pixi_environments(cwd=root)
    name = ns.env
    if name not in environments:
        valid = ", ".join(sorted(environments))
        return DutyResult(
            ok=False,
            summary=(
                f"provision --env: {name!r} is not a valid pixi environment. "
                f"Valid environments: {valid}"
            ),
        )
    materialize_environment(name, cwd=root)
    return DutyResult(
        ok=True, summary=f"provision --env: {name!r} materialized (pixi install -e {name})"
    )


def _run_runner(ns: argparse.Namespace) -> DutyResult:
    """`provision --runner bmad-loop` — RETIRED (Story 5.1, AD-5).

    This wrapped the *legacy* `scripts/bmad-loop-worktree` while `marshal init`
    (Marshal Epic 1, 10 shipped stories) is a strict superset: the same worktree
    plus the marker/symlink agreement invariant, the AD-11 never-write proof, and
    an idempotent `done | skipped | failed` step report. Two stations shipping
    two ways to make the same thing, one of them the weaker one.

    It REPORTS rather than DELEGATES, deliberately. This station imports nothing
    from `pyforge.marshal` and shells to no `marshal` binary; proxying the front
    door would create the first cross-station coupling and re-wrap exactly the
    machinery this story removes. The Marshal/Steward seam puts judgment with the
    owning station and the front door with Marshal, so Steward points at it.

    Never silently provisions: the legacy path is gone, not deprecated-but-live.
    `--env <name>` alone (pixi environments, genuinely Steward's) is untouched.
    """
    runner = ns.runner
    if runner != "bmad-loop":
        return DutyResult(
            ok=False,
            summary=f"provision --runner: unknown runner {runner!r} (only 'bmad-loop' is supported)",
        )
    slug = ns.env or "<slug>"
    return DutyResult(
        ok=False,
        summary=(
            f"provision --runner bmad-loop is RETIRED (Story 5.1). Use "
            f"`marshal init {slug}` — it provisions the same worktree plus the "
            f"marker/symlink agreement check, the never-write proof and an "
            f"idempotent step report, none of which the legacy "
            f"scripts/bmad-loop-worktree this wrapped provides. "
            f"`steward provision --env {slug}` still materializes the pixi "
            f"environment, which remains Steward's."
        ),
    )


class ProvisionDuty:
    """The real `provision` duty — dispatches the `--env`/`--runner`/`--list`/
    `--verify` flags (Epic 3 grows this class one flag per story; Story 3.4
    adds `--verify`, the last of the four).

    Unlike `keys`/`deploy`, `provision` has no verb subcommands — every
    action is a flag on the bare `provision` duty parser, matching each
    story's own `steward provision --env <name>` shape. Precedence when
    more than one flag is passed: `--verify` > `--list` > `--runner` >
    `--env` (a documented judgment call, not a silent one — mirrors
    `DeployDuty`'s own `--build`-wins-over-`--dry-run` precedent; no AC
    defines combining them). Bare `steward provision` (no flags) degrades
    to `DutyResult(ok=True, ...)` naming the available flags (AD-7),
    matching `KeysDuty`'s/`DeployDuty`'s identical precedent. A subprocess
    failure (pixi, bmad-loop-worktree) is caught here as `subprocess.
    CalledProcessError` and reported as a duty-level failure, never
    conflated with an internal crash (AD-8 — that boundary is
    `cli.main()`'s alone).
    """

    name = "provision"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        try:
            if getattr(ns, "verify", False):
                return _run_verify(ns)
            if getattr(ns, "list", False):
                return _run_list(ns)
            if getattr(ns, "runner", None):
                return _run_runner(ns)
            if getattr(ns, "env", None):
                return _run_env(ns)
            return DutyResult(ok=True, summary=f"provision: {_PROVISION_HELP}")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            cmd_name = " ".join(str(part) for part in exc.cmd) if exc.cmd else "subprocess"
            message = f"`{cmd_name}` exited {exc.returncode}: {stderr}"
            return DutyResult(ok=False, summary=self._render_error(ns, message))
        except (RuntimeError, FileNotFoundError, tomllib.TOMLDecodeError) as exc:
            return DutyResult(ok=False, summary=self._render_error(ns, str(exc)))

    @staticmethod
    def _render_error(ns: argparse.Namespace, message: str) -> str:
        """Every success path this duty has (`_run_list`'s own
        `format_environments(..., as_json=...)`) already honors `--json`;
        an error raised on ANY flag's path must too (review finding: an
        earlier draft only formatted the happy path, so `--list --json`
        against e.g. a malformed `pixi.toml` emitted a plain-text summary
        `cli.main()` prints verbatim -- unparseable by a caller that
        `json.loads()`s the output because `--json` was passed)."""
        if getattr(ns, "json", False):
            return json.dumps({"error": message}, indent=2)
        return f"provision: {message}"
