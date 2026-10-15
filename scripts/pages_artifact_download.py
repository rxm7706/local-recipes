#!/usr/bin/env python3
"""Download a producer's newest unexpired workflow artifact into a Pages mount source (steward Story 102.4).

The Pages workflow runs this before ``pages-check`` (CAP-168). With the defaults it fetches atlas's
``kedro-viz-export`` (atlas Story 30.1's ``kedro-viz-publish.yml``) into ``docs/dashboard/kedro-viz/``,
the path herald's assembler mounts at ``/dashboard/kedro-viz/`` (herald Story 42.2). Another artifact
mount is the same step with its own ``--workflow``, ``--artifact``, ``--dest`` and ``--env-prefix``.

* Present: ``gh run download <id> -n <artifact> -D <dest>``; ``<PREFIX>=present``, ``<PREFIX>_RUN``
  and ``<PREFIX>_AT`` (the run's ``createdAt``) are written to ``$GITHUB_ENV`` (or ``--github-env``,
  else stdout). Exit 0.
* Absent (no successful run, no artifact of that name, or only expired ones): prints
  ``<artifact>: none found; mount skipped``, writes ``<PREFIX>=absent``. Exit 0: absence is a normal build.
* A ``gh`` error is never read as absence: it exits 1 naming the argv. So does a ``--dest`` that already
  holds files (nothing is deleted).
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
    KEDRO_VIZ_ARTIFACT,
    KEDRO_VIZ_DEST_REL,
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


def _failure(argv: Sequence[str], proc: subprocess.CompletedProcess[str]) -> int:
    detail = (proc.stderr or proc.stdout or "").strip()
    print(
        f"pages_artifact_download: `{' '.join(argv)}` exited {proc.returncode}: {detail}",
        file=sys.stderr,
    )
    return 1


def _gh_json(runner: Runner, argv: list[str]) -> tuple[Any, int]:
    proc = runner(argv)
    if proc.returncode != 0:
        return None, _failure(argv, proc)
    try:
        return json.loads(proc.stdout or "null"), 0
    except json.JSONDecodeError as exc:
        print(
            f"pages_artifact_download: `{' '.join(argv)}` gave invalid JSON: {exc}",
            file=sys.stderr,
        )
        return None, 1


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
        "--env-prefix", default="KEDRO_VIZ_EXPORT", help="names the three env lines"
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
    prefix = args.env_prefix

    list_argv = [
        "gh",
        "run",
        "list",
        "--workflow",
        args.workflow,
        "--status",
        "success",
        "--limit",
        str(args.limit),
        "--json",
        "databaseId,createdAt,conclusion",
    ]
    runs, failed = _gh_json(runner, list_argv)
    if failed:
        return failed
    runs = runs if isinstance(runs, list) else []
    fetched: dict[int, Any] = {}
    chosen = None
    for run in sorted(
        (r for r in runs if isinstance(r, dict) and r.get("conclusion") == "success"),
        key=lambda r: str(r.get("createdAt") or ""),
        reverse=True,
    ):
        run_id = run.get("databaseId")
        if not isinstance(run_id, int):
            continue
        payload, failed = _gh_json(
            runner,
            ["gh", "api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/artifacts"],
        )
        if failed:
            return failed
        fetched[run_id] = payload
        chosen = newest_export_run(runs, fetched, artifact=args.artifact)
        if chosen is not None:
            break

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
    download_argv = [
        "gh",
        "run",
        "download",
        str(chosen),
        "-n",
        args.artifact,
        "-D",
        args.dest,
    ]
    proc = runner(download_argv)
    if proc.returncode != 0:
        return _failure(download_argv, proc)
    created = next(
        (str(r.get("createdAt") or "") for r in runs if r.get("databaseId") == chosen),
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
