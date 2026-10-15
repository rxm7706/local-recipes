#!/usr/bin/env python3
"""Download a producer's newest live workflow artifact into a Pages mount source (steward Story 102.4).

The Pages workflow runs this before ``pages-check`` (CAP-168). With the defaults it fetches atlas's
``kedro-viz-export`` (atlas Story 30.1's ``kedro-viz-publish.yml``) into ``docs/dashboard/kedro-viz/``,
the path herald's assembler mounts at ``/dashboard/kedro-viz/`` (herald Story 42.2). Another artifact
mount is the same step with its own ``--workflow``, ``--artifact``, ``--dest`` and ``--env-prefix``
(atlas 30.2's ``vizro-static-export`` into ``docs/dashboard/vizro/`` is the second).

* The selection reads the artifact, not a window of recent runs (102.4's re-review): every page of
  ``gh api repos/{owner}/{repo}/actions/artifacts?name=<artifact>`` is listed, then the run behind the
  newest live one is read (``gh api repos/{owner}/{repo}/actions/runs/<id>``) to confirm it is
  ``--workflow``'s, succeeded and ran on ``--branch``. Atlas 30.2's producer runs each export job only
  when its own paths change, so a fixed window of runs would lose a live export behind one-sided runs.
* Present: ``gh run download <id> -n <artifact> -D <dest>``; ``<PREFIX>=present``, ``<PREFIX>_RUN``
  and ``<PREFIX>_AT`` (the run's ``created_at``) are written to ``$GITHUB_ENV`` (or ``--github-env``,
  else stdout). Exit 0.
* Absent (no artifact of that name, only expired ones, or none from a successful ``--workflow`` run on
  ``--branch``): prints ``<artifact>: none found; mount skipped``, writes ``<PREFIX>=absent``. Exit 0:
  absence is a normal build.
* A ``gh`` error is never read as absence: a failing call, a missing ``gh``, invalid JSON, a payload of
  the wrong shape or a listing longer than :data:`MAX_ARTIFACT_PAGES` pages exits 1 naming the argv.
  So does a ``--dest`` that already holds files (nothing is deleted).
* Only a run on ``--branch`` (default ``main``) is eligible: a producer dispatched on an unmerged branch
  never reaches the production Pages origin.
* ``pyforge.steward.pages_duty`` off: returns before any ``gh`` call; ``--flag-env`` prints
  ``PYFORGE_PAGES_DUTY=1|0`` for the workflow step's ``if:``.

``gh`` is reached by subprocess only (AD-1); the selection is ``pyforge.steward.pages.newest_export_run``.
The workflow sets ``GH_HOST`` (from ``GITHUB_SERVER_URL``) and ``GH_REPO`` so ``gh`` talks to the host
that runs it, a GitHub Enterprise Server included.
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
    ARTIFACTS_PER_PAGE,
    EXPORT_BRANCH,
    KEDRO_VIZ_ARTIFACT,
    KEDRO_VIZ_DEST_REL,
    KEDRO_VIZ_ENV_PREFIX,
    KEDRO_VIZ_WORKFLOW,
    PAGES_DUTY_FLAG,
    export_artifacts_endpoint,
    newest_export_run,
)

FLAG_ENV = "PYFORGE_PAGES_DUTY"
#: A listing longer than this many pages of :data:`ARTIFACTS_PER_PAGE` fails, never truncates: a
#: truncated listing could miss the newest live artifact and read ``absent``.
MAX_ARTIFACT_PAGES = 20
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


def _list_artifacts(runner: Runner, artifact: str) -> list[Any]:
    """Every page of the repository's artifacts named ``artifact``, until a page is short."""
    listed: list[Any] = []
    for page in range(1, MAX_ARTIFACT_PAGES + 1):
        argv = ["gh", "api", export_artifacts_endpoint(artifact, page=page)]
        payload = _gh_json(runner, argv, shape=dict)
        items = payload.get("artifacts")
        if not isinstance(items, list):
            raise GhError(f"`{' '.join(argv)}` gave no artifacts list")
        for item in (
            items
        ):  # a live artifact of this name must name its run (102.4's lane-B re-review)
            if (
                isinstance(item, dict)
                and item.get("name") == artifact
                and item.get("expired") is False
            ):
                run = item.get("workflow_run")
                if not isinstance(run, dict) or not isinstance(run.get("id"), int):
                    raise GhError(
                        f"`{' '.join(argv)}` gave live artifact {artifact} (id {item.get('id')!r}) "
                        "with no readable workflow_run.id"
                    )
        listed.extend(items)
        if len(items) < ARTIFACTS_PER_PAGE:
            return listed
    raise GhError(
        f"`gh api {export_artifacts_endpoint(artifact, page=MAX_ARTIFACT_PAGES)}` still gave a full page: "
        f"more than {MAX_ARTIFACT_PAGES * ARTIFACTS_PER_PAGE} {artifact} artifacts; the listing is not read partially"
    )


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
        "--workflow",
        default=KEDRO_VIZ_WORKFLOW,
        help="the producer workflow's file name under .github/workflows/",
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
    artifacts = _list_artifacts(runner, args.artifact)
    runs: dict[int, dict[str, Any]] = {}

    def fetch(run_id: int) -> dict[str, Any]:
        argv = ["gh", "api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}"]
        payload = _gh_json(runner, argv, shape=dict)
        if not isinstance(payload.get("path"), str):
            raise GhError(f"`{' '.join(argv)}` gave no workflow path")
        runs[run_id] = payload
        return payload

    chosen = newest_export_run(
        artifacts,
        fetch,
        artifact=args.artifact,
        workflow=args.workflow,
        branch=args.branch,
    )
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
    created = str(runs[chosen].get("created_at") or "")
    print(f"{args.artifact}: run {chosen} ({created}) downloaded into {args.dest}")
    _write_env(
        [f"{prefix}=present", f"{prefix}_RUN={chosen}", f"{prefix}_AT={created}"],
        args.github_env,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
