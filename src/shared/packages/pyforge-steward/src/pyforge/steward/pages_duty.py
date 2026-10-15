"""``steward pages build|deploy|status`` -- the Pages duty (Story 102.3 / CAP-168, FR-41).

The duct's duty: it speaks to the one Pages workflow (``.github/workflows/pages.yml``), never to a
branch. It replaces ``deploy dashboard`` and ``deploy status`` (retired by this story; AD-5's
2026-08-09 rule, deleted rather than deprecated).

* ``build`` writes the fleet board's build input (``docsite/content/fleet-status.json``, from
  ``sprint-ledger-query --format json`` reshaped by :func:`pages.fleet_status_document`, in-process),
  runs ``pixi run --frozen -e site pages-check`` by subprocess and reports the built tree's hash
  (:func:`pages.tree_hash`). ``--stamp`` then runs ``scripts/pages_build_stamp.py`` as the workflow
  does; ``--dry-run`` prints what would run and runs nothing.
* ``deploy`` runs ``gh workflow run pages.yml --ref main``, then names the run it started through
  ``gh run list``; ``--wait`` watches it to the end. ``--dry-run`` prints both argv lines and runs
  nothing. The workflow's own hash compare is the no-diff gate (AD-4 as amended 2026-10-14): the
  dispatch bypasses only the pause switches (the ``pages.deploy`` row renders ``dispatch: pause-only``),
  so a dispatched run of an identical tree builds and skips its deploy.
* ``status`` reads: the live root (``curl`` for ``last-modified`` and ``build.json``), the last run
  (``gh run list``) and the ``pages`` row's registry verdict (``ci.py``'s reader -- one status reader,
  AD-1). It never triggers a run or writes a variable.

Every verb reads ``pyforge.steward.pages_duty`` first and, off, refuses with
:data:`EXIT_PAGES_REFUSAL` before any subprocess. ``pixi``, ``gh`` and ``curl`` are reached by
subprocess only (AD-1); no verb commits or pushes. Returns ``DutyResult`` only (AD-8).
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from .interfaces import DutyResult
from .pages import FLEET_STATUS_REL, PAGES_DUTY_FLAG, SITE_ROOT_REL, fleet_status_document, tree_hash

#: The refusal domain ``ci.py`` uses (``EXIT_CI_REFUSAL``): the flag is off. Documented in ``cli.py``.
EXIT_PAGES_REFUSAL = 3
PAGES_VERBS: tuple[str, ...] = ("build", "deploy", "status")
PAGES_WORKFLOW = "pages.yml"
#: The ``docs/governance/ci-surfaces.yaml`` row whose verdict ``status`` reports.
PAGES_SURFACE = "pages"

BUILD_ARGV: tuple[str, ...] = ("pixi", "run", "--frozen", "-e", "site", "pages-check")
DISPATCH_ARGV: tuple[str, ...] = ("gh", "workflow", "run", PAGES_WORKFLOW, "--ref", "main")
DEPLOY_LIST_ARGV: tuple[str, ...] = (
    "gh",
    "run",
    "list",
    "--workflow",
    PAGES_WORKFLOW,
    "--event",
    "workflow_dispatch",
    "--limit",
    "1",
    "--json",
    "databaseId,url,status,event,createdAt",
)
STATUS_RUN_ARGV: tuple[str, ...] = (
    "gh",
    "run",
    "list",
    "--workflow",
    PAGES_WORKFLOW,
    "--limit",
    "1",
    "--json",
    "databaseId,conclusion,status,event,createdAt,url",
)
SITE_URL_ARGV: tuple[str, ...] = ("gh", "api", "repos/{owner}/{repo}/pages", "--jq", ".html_url")
STAMP_SCRIPT_REL = "scripts/pages_build_stamp.py"
#: ``deploy`` looks for the run it started this many times, ``_LIST_INTERVAL_SECONDS`` apart: GitHub
#: lists a dispatched run a few seconds after ``gh workflow run`` returns.
_LIST_ATTEMPTS = 5
_LIST_INTERVAL_SECONDS = 3.0
#: A run created this long before the dispatch is not the one it started (clock skew allowance).
_DISPATCH_SKEW = timedelta(seconds=30)
_TAIL_LINES = 20


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


SubprocessRunner = Callable[[list[str], Path], _Completed]


def _default_runner(argv: list[str], cwd: Path) -> _Completed:
    import subprocess

    return subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


@dataclass
class PagesDeps:
    """Everything a verb reaches outside itself; tests replace each with a fake."""

    root: Path
    runner: SubprocessRunner
    flag_on: Callable[[], bool]
    #: ``(verdict, reason)``: the ``pages`` row's verdict, or ``None`` and why it is unavailable.
    registry_verdict: Callable[[], tuple[str | None, str]]
    #: Writes ``docsite/content/fleet-status.json`` under the given root; returns the path written.
    write_fleet_status: Callable[[Path], Path]
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    sleep: Callable[[float], None] = field(default=time.sleep)


def head_commit_time(root: Path) -> str | None:
    """``git log -1 --format=%cI HEAD`` at ``root`` -- the snapshot time the workflow passes -- or
    ``None`` when ``root`` is not a git checkout (``git`` by subprocess, AD-1)."""
    import subprocess

    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "log", "-1", "--format=%cI", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    stamp = proc.stdout.strip()
    return stamp if proc.returncode == 0 and stamp else None


def write_fleet_status(root: Path) -> Path:
    """The fleet board's input from the tracked ledgers: ``sprint-ledger-query --format json``
    (the engine, in-process, without the live ``marshal watch`` call) reshaped for herald, stamped
    with HEAD's commit time as the workflow stamps it, so a local build writes the CI run's file
    (the query time only where ``root`` is no git checkout)."""
    from .sprint_ledger_query import SprintLedgerQueryEngine

    engine = SprintLedgerQueryEngine(root_dir=root)
    payload = json.loads(engine.export(engine.query(), format_name="json"))
    document = fleet_status_document(payload, generated_at=head_commit_time(root))
    out = root / FLEET_STATUS_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return out


def ci_registry_verdict(root: Path, runner: SubprocessRunner) -> tuple[str | None, str]:
    """The ``pages`` row's verdict through ``ci status``'s reader, or why it is unavailable (the
    reader refuses the way ``ci status`` does: flag off, ``gh`` unauthenticated, rate limit)."""
    from pyforge.core.flags import read_boolean

    from . import ci

    deps = ci.CiDeps(root=root, runner=runner, flag_on=lambda: read_boolean(ci.CI_FLAG_KEY, default=False))
    try:
        result = ci.run_status(deps, json_out=True)
    except Exception as exc:  # noqa: BLE001 -- a reader that degrades: the line reads unavailable, never a crash
        return None, f"{type(exc).__name__}: {exc}"
    payload = result.details.get("payload")
    if not isinstance(payload, dict):
        return None, (result.summary or "ci status gave no payload").strip()
    for row in payload.get("rows") or []:
        if isinstance(row, dict) and row.get("id") == PAGES_SURFACE:
            return str(row.get("verdict")), ""
    return None, f"no {PAGES_SURFACE!r} row in the ci status payload"


def _production_deps(root: Path) -> PagesDeps:
    from pyforge.core.flags import read_boolean

    return PagesDeps(
        root=root,
        runner=_default_runner,
        flag_on=lambda: read_boolean(PAGES_DUTY_FLAG, default=False),
        registry_verdict=lambda: ci_registry_verdict(root, _default_runner),
        write_fleet_status=write_fleet_status,
    )


def _refusal(verb: str) -> DutyResult:
    return DutyResult(
        ok=False,
        summary=f"pages {verb}: refused — flag {PAGES_DUTY_FLAG} is off",
        details={"exit_code": EXIT_PAGES_REFUSAL},
    )


def _argv_text(argv: Sequence[str]) -> str:
    return " ".join(argv)


def _tail(proc: _Completed) -> str:
    text = (proc.stderr or proc.stdout or "").strip()
    return "\n".join(text.splitlines()[-_TAIL_LINES:])


def _gh_failure(verb: str, argv: Sequence[str], proc: _Completed) -> DutyResult:
    return DutyResult(
        ok=False,
        summary=f"pages {verb}: `{_argv_text(argv)}` exited {proc.returncode}: {_tail(proc)}",
        details={"argv": list(argv), "exit": proc.returncode},
    )


def _site_url(deps: PagesDeps, site_url: str | None) -> tuple[str | None, str]:
    """``--site-url``, else ``gh api repos/{owner}/{repo}/pages --jq .html_url``; ``(None, why)`` on failure."""
    if site_url:
        return site_url, ""
    proc = deps.runner(list(SITE_URL_ARGV), deps.root)
    url = (proc.stdout or "").strip()
    if proc.returncode != 0 or not url:
        return None, f"`{_argv_text(SITE_URL_ARGV)}` exited {proc.returncode}: {_tail(proc)}"
    return url, ""


def _stamp_argv(site_url: str) -> list[str]:
    return [
        "pixi",
        "run",
        "--frozen",
        "-e",
        "pyforge-guild",
        "python",
        STAMP_SCRIPT_REL,
        "--root",
        SITE_ROOT_REL,
        "--live-url",
        f"{site_url.rstrip('/')}/build.json",
    ]


# ── build ────────────────────────────────────────────────────────────────────────────────────────


def run_build(
    deps: PagesDeps, *, json_out: bool = False, dry_run: bool = False, stamp: bool = False, site_url: str | None = None
) -> DutyResult:
    if not deps.flag_on():
        return _refusal("build")
    argv = list(BUILD_ARGV)
    if dry_run:
        lines = [
            f"pages build (dry-run): would write {FLEET_STATUS_REL} from sprint-ledger-query --format json",
            f"pages build (dry-run): {_argv_text(argv)}",
        ]
        if stamp:
            lines.append(f"pages build (dry-run): {_argv_text(_stamp_argv(site_url or '<site url>'))}")
        return DutyResult(ok=True, summary="\n".join(lines), details={"argv": [argv], "dry_run": True})

    try:
        written = deps.write_fleet_status(deps.root)
    except (OSError, ValueError) as exc:
        return DutyResult(ok=False, summary=f"pages build: could not write {FLEET_STATUS_REL}: {exc}")
    proc = deps.runner(argv, deps.root)
    site_root = deps.root / SITE_ROOT_REL
    digest = tree_hash(site_root) if proc.returncode == 0 and site_root.is_dir() else None
    payload: dict[str, Any] = {
        "exit": proc.returncode,
        "tree_hash": digest,
        "root": SITE_ROOT_REL,
        "fleet_status": str(written),
    }
    if proc.returncode != 0:
        summary = f"pages build: pages-check exit {proc.returncode}"
        tail = _tail(proc)
        return DutyResult(
            ok=False,
            summary=json.dumps(payload, indent=2) if json_out else f"{summary}\n{tail}".rstrip(),
            details={"argv": [argv], **payload},
        )
    if digest is None:
        return DutyResult(ok=False, summary=f"pages build: pages-check exit 0 but {SITE_ROOT_REL} is not a directory")

    lines = [f"pages build: pages-check exit 0; tree {digest}"]
    argvs = [argv]
    if stamp:
        url, why = _site_url(deps, site_url)
        if url is None:
            return DutyResult(ok=False, summary=f"pages build: --stamp needs the site url: {why}")
        stamp_argv = _stamp_argv(url)
        argvs.append(stamp_argv)
        stamped = deps.runner(stamp_argv, deps.root)
        payload["stamp"] = {"exit": stamped.returncode, "output": (stamped.stdout or "").strip()}
        if stamped.returncode != 0:
            return _gh_failure("build --stamp", stamp_argv, stamped)
        lines.append(f"pages build: stamp {' '.join((stamped.stdout or '').split())}")
    summary = json.dumps(payload, indent=2) if json_out else "\n".join(lines)
    return DutyResult(ok=True, summary=summary, details={"argv": argvs, **payload})


# ── deploy ───────────────────────────────────────────────────────────────────────────────────────


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _find_started_run(deps: PagesDeps, dispatched_at: datetime) -> tuple[dict[str, Any] | None, DutyResult | None]:
    """The dispatched run ``gh run list`` names once it is listed, or the newest one with a note."""
    argv = list(DEPLOY_LIST_ARGV)
    newest: dict[str, Any] | None = None
    for attempt in range(_LIST_ATTEMPTS):
        proc = deps.runner(argv, deps.root)
        if proc.returncode != 0:
            return None, _gh_failure("deploy", argv, proc)
        try:
            runs = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError as exc:
            return None, DutyResult(ok=False, summary=f"pages deploy: `{_argv_text(argv)}` gave invalid JSON: {exc}")
        if isinstance(runs, list) and runs and isinstance(runs[0], dict):
            newest = runs[0]
            created = _parse_time(newest.get("createdAt"))
            if created is None or created >= dispatched_at - _DISPATCH_SKEW:
                return newest, None
        if attempt + 1 < _LIST_ATTEMPTS:
            deps.sleep(_LIST_INTERVAL_SECONDS)
    if newest is None:
        return None, DutyResult(ok=False, summary=f"pages deploy: `{_argv_text(argv)}` listed no run")
    newest = {**newest, "note": "not yet listed; this is the newest earlier dispatch"}
    return newest, None


def run_deploy(deps: PagesDeps, *, dry_run: bool = False, wait: bool = False) -> DutyResult:
    if not deps.flag_on():
        return _refusal("deploy")
    dispatch = list(DISPATCH_ARGV)
    listing = list(DEPLOY_LIST_ARGV)
    if dry_run:
        argvs = [dispatch, listing, *([["gh", "run", "watch", "<run id>", "--exit-status"]] if wait else [])]
        summary = "\n".join(f"pages deploy (dry-run): {_argv_text(argv)}" for argv in argvs)
        return DutyResult(ok=True, summary=summary, details={"argv": argvs, "dry_run": True})

    dispatched_at = deps.now()
    proc = deps.runner(dispatch, deps.root)
    if proc.returncode != 0:
        return _gh_failure("deploy", dispatch, proc)
    run, failure = _find_started_run(deps, dispatched_at)
    if failure is not None:
        return failure
    assert run is not None
    run_id = run.get("databaseId")
    lines = [f"pages deploy: run {run_id} {run.get('url')} ({run.get('status')})"]
    if run.get("note"):
        lines[0] += f" -- {run['note']}"
    details: dict[str, Any] = {"run": run}
    if not wait:
        return DutyResult(ok=True, summary="\n".join(lines), details=details)

    watch = ["gh", "run", "watch", str(run_id), "--exit-status"]
    watched = deps.runner(watch, deps.root)
    details["watch_exit"] = watched.returncode
    if watched.returncode != 0:
        failure = _gh_failure("deploy --wait", watch, watched)
        return DutyResult(ok=False, summary="\n".join([*lines, failure.summary]), details=details)
    url, why = _site_url(deps, None)
    details["page_url"] = url
    lines.append(
        f"pages deploy: run {run_id} succeeded; page {url}"
        if url
        else f"pages deploy: run {run_id} succeeded; page url unavailable ({why})"
    )
    return DutyResult(ok=True, summary="\n".join(lines), details=details)


# ── status ───────────────────────────────────────────────────────────────────────────────────────


def _header(text: str, name: str) -> str | None:
    """The last value of header ``name`` in ``curl -sIL`` output (the final response's)."""
    value = None
    for line in text.splitlines():
        key, sep, rest = line.partition(":")
        if sep and key.strip().lower() == name:
            value = rest.strip()
    return value


def _http_status(text: str) -> int | None:
    status = None
    for line in text.splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) > 1 and parts[1].isdigit():
                status = int(parts[1])
    return status


def _live_block(deps: PagesDeps, site_url: str | None) -> dict[str, Any]:
    url, why = _site_url(deps, site_url)
    if url is None:
        return {"url": None, "error": f"unavailable ({why})"}
    block: dict[str, Any] = {"url": url}
    head = deps.runner(["curl", "-sIL", "--max-time", "30", url], deps.root)
    code = _http_status(head.stdout or "")
    if head.returncode != 0 or code is None or code >= 400:
        block["error"] = f"unreachable (curl exit {head.returncode}{f', HTTP {code}' if code else ''})"
        return block
    block["last_modified"] = _header(head.stdout or "", "last-modified")
    built = deps.runner(["curl", "-fsS", "--max-time", "30", f"{url.rstrip('/')}/build.json"], deps.root)
    if built.returncode != 0:
        block["build_json_error"] = f"unreachable (curl exit {built.returncode})"
        return block
    try:
        document = json.loads(built.stdout or "")
    except json.JSONDecodeError:
        document = None
    if not isinstance(document, dict):
        block["build_json_error"] = "build.json is not a JSON object"
        return block
    block["tree_hash"] = document.get("tree_hash")
    block["built_from"] = document.get("built_from")
    return block


def _run_block(deps: PagesDeps) -> tuple[dict[str, Any], bool]:
    argv = list(STATUS_RUN_ARGV)
    proc = deps.runner(argv, deps.root)
    if proc.returncode != 0:
        return {"error": f"`{_argv_text(argv)}` exited {proc.returncode}: {_tail(proc)}"}, False
    try:
        runs = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        return {"error": f"invalid JSON from gh run list: {exc}"}, False
    if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
        return {"error": "no run of pages.yml listed"}, True
    return dict(runs[0]), True


def _live_line(block: dict[str, Any]) -> str:
    if "error" in block:
        where = f"{block['url']} " if block.get("url") else ""
        return f"live root: {where}{block['error']}"
    line = f"live root: {block['url']} last-modified {block.get('last_modified') or '—'}"
    if "build_json_error" in block:
        return f"{line}; build.json {block['build_json_error']}"
    return f"{line}; tree {block.get('tree_hash') or '—'} built from {block.get('built_from') or '—'}"


def _run_line(block: dict[str, Any]) -> str:
    if "error" in block:
        return f"last run: {block['error']}"
    state = block.get("conclusion") or block.get("status") or "—"
    return (
        f"last run: {block.get('databaseId')} {block.get('event')} {state} "
        f"{block.get('createdAt') or ''} {block.get('url') or ''}".rstrip()
    )


def run_status(deps: PagesDeps, *, json_out: bool = False, site_url: str | None = None) -> DutyResult:
    if not deps.flag_on():
        return _refusal("status")
    live = _live_block(deps, site_url)
    run, run_read = _run_block(deps)
    verdict, reason = deps.registry_verdict()
    registry: dict[str, Any] = {"surface": PAGES_SURFACE, "verdict": verdict}
    if verdict is None:
        registry["unavailable"] = reason
    if json_out:
        summary = json.dumps({"live": live, "last_run": run, "registry": registry}, indent=2)
    else:
        registry_line = (
            f"registry verdict: {PAGES_SURFACE} {verdict}"
            if verdict is not None
            else f"registry verdict: unavailable ({reason})"
        )
        summary = "\n".join([_live_line(live), _run_line(run), registry_line])
    # An unreachable site and an unavailable registry verdict are facts; a run list gh cannot read is not.
    return DutyResult(ok=run_read, summary=summary, details={"live": live, "last_run": run, "registry": registry})


# ── the duty ─────────────────────────────────────────────────────────────────────────────────────


class PagesDuty:
    name = "pages"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "pages_verb", None)
        if verb not in PAGES_VERBS:
            return DutyResult(ok=True, summary=f"pages: available verbs are {', '.join(PAGES_VERBS)}")
        deps: PagesDeps | None = getattr(ns, "_pages_deps", None)
        if deps is None:
            from .bootstrap import repo_root

            deps = _production_deps(repo_root())
        site_url = getattr(ns, "site_url", None)
        if verb == "build":
            return run_build(
                deps,
                json_out=bool(getattr(ns, "json", False)),
                dry_run=bool(getattr(ns, "dry_run", False)),
                stamp=bool(getattr(ns, "stamp", False)),
                site_url=site_url,
            )
        if verb == "deploy":
            return run_deploy(deps, dry_run=bool(getattr(ns, "dry_run", False)), wait=bool(getattr(ns, "wait", False)))
        return run_status(deps, json_out=bool(getattr(ns, "json", False)), site_url=site_url)
