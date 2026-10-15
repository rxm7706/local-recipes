#!/usr/bin/env python3
"""Download a producer's newest unexpired workflow artifact into a Pages mount source (steward Story 102.4).

The Pages workflow runs this before ``pages-check`` (CAP-168). With the defaults it fetches atlas's
``kedro-viz-export`` (atlas Story 30.1's ``kedro-viz-publish.yml``) into ``docs/dashboard/kedro-viz/``,
the path herald's assembler mounts at ``/dashboard/kedro-viz/`` (herald Story 42.2). Another artifact
mount is the same step with its own ``--workflow``, ``--artifact``, ``--dest`` and ``--env-prefix``
(atlas 30.2's ``vizro-static-export`` into ``docs/dashboard/vizro/`` is the second).

* Present: ``gh run download <id> -n <artifact> -D <dest>``; ``<PREFIX>=present``, ``<PREFIX>_RUN``
  and ``<PREFIX>_AT`` (the run's ``createdAt``) are written to ``$GITHUB_ENV`` (or ``--github-env``,
  else stdout). Exit 0.
* Absent (no successful run, no artifact of that name, or only expired ones): prints
  ``<artifact>: none found; mount skipped``, writes ``<PREFIX>=absent``. Exit 0: absence is a normal build.
* A ``gh`` error is never read as absence: a failing call, a missing ``gh``, invalid JSON or a payload
  of the wrong shape exits 1 naming the argv. So does a ``--dest`` that already holds files (nothing is
  deleted).
* Only a run on ``--branch`` (default ``main``) is eligible: a producer dispatched on an unmerged branch
  never reaches the production Pages origin.
* ``pyforge.steward.pages_duty`` off: returns before any ``gh`` call; ``--flag-env`` prints
  ``PYFORGE_PAGES_DUTY=1|0`` for the workflow step's ``if:``.

``gh`` is reached by subprocess only (AD-1); the selection is ``pyforge.steward.pages.newest_export_run``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
for _pkg in ("pyforge-core", "pyforge-steward"):
    _src = REPO_ROOT / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from pyforge.steward.pages import (
    EXPORT_BRANCH,
    KEDRO_VIZ_ARTIFACT,
    KEDRO_VIZ_DEST_REL,
    KEDRO_VIZ_ENV_PREFIX,
    KEDRO_VIZ_WORKFLOW,
    PAGES_DUTY_FLAG,
    newest_export_run,
)

FLAG_ENV = "PYFORGE_PAGES_DUTY"
Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _runner_at(root: Path) -> Runner:
    def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv, cwd=root, capture_output=True, text=True, check=False
        )

    return _run


class GhError(Exception):
    """A ``gh`` call that failed, or answered in a shape this step cannot read; never absence."""


def _call(runner: Runner, argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        proc = runner(argv)
    except (
        FileNotFoundError
    ) as exc:  # no `gh` on the runner: name the argv, never a traceback
        raise GhError(f"`{' '.join(argv)}` could not run: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise GhError(f"`{' '.join(argv)}` exited {proc.returncode}: {detail}")
    return proc


def _gh_json(runner: Runner, argv: list[str], *, shape: type) -> Any:
    proc = _call(runner, argv)
    try:
        payload = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise GhError(f"`{' '.join(argv)}` gave invalid JSON: {exc}") from exc
    if not isinstance(payload, shape):
        raise GhError(
            f"`{' '.join(argv)}` gave {type(payload).__name__}, not a JSON {shape.__name__}"
        )
    return payload


def _write_env(lines: list[str], github_env: str | None) -> None:
    if github_env:
        with open(github_env, "a", encoding="utf-8") as handle:
            handle.write("".join(f"{line}\n" for line in lines))
    else:
        print("\n".join(lines))


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    flag_on: bool | None = None,
    root: Path | None = None,
) -> int:
    """``runner`` and ``root`` default to ``gh`` by subprocess at the repo root; tests pass fakes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--flag-env", action="store_true", help=f"print {FLAG_ENV}=1|0 and exit"
    )
    parser.add_argument(
        "--workflow", default=KEDRO_VIZ_WORKFLOW, help="the producer workflow file"
    )
    parser.add_argument(
        "--artifact", default=KEDRO_VIZ_ARTIFACT, help="the artifact name"
    )
    parser.add_argument(
        "--dest",
        default=KEDRO_VIZ_DEST_REL,
        help="the mount source, relative to the repo root",
    )
    parser.add_argument(
        "--env-prefix", default=KEDRO_VIZ_ENV_PREFIX, help="names the three env lines"
    )
    parser.add_argument(
        "--branch",
        default=EXPORT_BRANCH,
        help="only a producer run on this branch is mounted (default main)",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="producer runs to scan (default 10)"
    )
    parser.add_argument(
        "--github-env",
        default=os.environ.get("GITHUB_ENV"),
        help="file the env lines append to",
    )
    args = parser.parse_args(argv)

    if flag_on is None:
        from pyforge.core.flags import read_boolean

        flag_on = read_boolean(PAGES_DUTY_FLAG, default=False)
    if args.flag_env:
        print(f"{FLAG_ENV}={'1' if flag_on else '0'}")
        return 0
    if not flag_on:
        print(
            f"pages_artifact_download: {PAGES_DUTY_FLAG} is off; no artifact downloaded"
        )
        return 0
    root = root or REPO_ROOT
    runner = runner or _runner_at(root)
    try:
        return _download(args, runner, root)
    except GhError as exc:
        print(f"pages_artifact_download: {exc}", file=sys.stderr)
        return 1


def _download(args: argparse.Namespace, runner: Runner, root: Path) -> int:
    prefix = args.env_prefix
    list_argv = [
        "gh",
        "run",
        "list",
        "--workflow",
        args.workflow,
        "--branch",
        args.branch,
        "--status",
        "success",
        "--limit",
        str(args.limit),
        "--json",
        "databaseId,createdAt,conclusion,headBranch",
    ]
    runs = _gh_json(runner, list_argv, shape=list)

    def fetch(run_id: int) -> dict[str, Any]:
        argv = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/artifacts",
        ]
        payload = _gh_json(runner, argv, shape=dict)
        if not isinstance(payload.get("artifacts"), list):
            raise GhError(f"`{' '.join(argv)}` gave no artifacts list")
        return payload

    chosen = newest_export_run(runs, fetch, artifact=args.artifact, branch=args.branch)
    if chosen is None:
        print(f"{args.artifact}: none found; mount skipped")
        _write_env([f"{prefix}=absent"], args.github_env)
        return 0

    dest = root / args.dest
    if dest.is_dir() and any(dest.iterdir()):
        print(
            f"pages_artifact_download: {args.dest} already holds files; remove them first",
            file=sys.stderr,
        )
        return 1
    _call(
        runner,
        ["gh", "run", "download", str(chosen), "-n", args.artifact, "-D", args.dest],
    )
    created = next(
        (
            str(r.get("createdAt") or "")
            for r in runs
            if isinstance(r, dict) and r.get("databaseId") == chosen
        ),
        "",
    )
    print(f"{args.artifact}: run {chosen} ({created}) downloaded into {args.dest}")
    _write_env(
        [f"{prefix}=present", f"{prefix}_RUN={chosen}", f"{prefix}_AT={created}"],
        args.github_env,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
