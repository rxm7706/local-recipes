"""Story 102.3 (CAP-168 FR-41): ``steward pages build|deploy|status`` replaces ``deploy dashboard|status``.

Every verb runs against a fake subprocess and fake readers: no test calls a live ``gh``, ``curl`` or
``pixi`` (AC8), and every root is a scratch directory.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.steward import ci, deploy, pages_duty
from pyforge.steward.cli import DUTIES, EXIT_FAILED, EXIT_OK, EXIT_USAGE, build_parser, main, resolve_duty
from pyforge.steward.interfaces import DutyResult
from pyforge.steward.pages import FLEET_STATUS_REL, SITE_ROOT_REL, fleet_status_document, tree_hash
from pyforge.steward.pages_duty import (
    BUILD_ARGV,
    DEPLOY_LIST_ARGV,
    DISPATCH_ARGV,
    EXIT_PAGES_REFUSAL,
    SITE_URL_ARGV,
    STATUS_RUN_ARGV,
    PagesDeps,
    PagesDuty,
    run_build,
    run_deploy,
    run_status,
)

_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
_SITE = "https://rxm7706.github.io/local-recipes/"


@dataclass
class _Proc:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakeRunner:
    """Answers each argv from ``responses`` (first key that prefixes it); records every call."""

    def __init__(self, responses: dict[tuple[str, ...], _Proc | list[_Proc]] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], cwd: Path) -> _Proc:
        self.calls.append(list(argv))
        for key, answer in self.responses.items():
            if tuple(argv[: len(key)]) == key:
                if isinstance(answer, list):
                    return answer.pop(0) if len(answer) > 1 else answer[0]
                return answer
        return _Proc(returncode=127, stderr=f"no fake for {argv}")


def _deps(
    tmp_path: Path,
    runner: FakeRunner,
    *,
    flag_on: bool = True,
    verdict: tuple[str | None, str] = ("live", ""),
    write: Callable[[Path], Path] | None = None,
) -> PagesDeps:
    def _write(root: Path) -> Path:
        out = root / FLEET_STATUS_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('{"stations": []}\n', encoding="utf-8")
        return out

    return PagesDeps(
        root=tmp_path,
        runner=runner,
        flag_on=lambda: flag_on,
        registry_verdict=lambda: verdict,
        write_fleet_status=write or _write,
        now=lambda: _NOW,
        sleep=lambda _seconds: None,
    )


def _built_site(tmp_path: Path) -> Path:
    site = tmp_path / SITE_ROOT_REL
    (site / "herald").mkdir(parents=True)
    (site / "index.html").write_text("<html>docs</html>", encoding="utf-8")
    (site / "herald" / "index.html").write_text("<html>herald</html>", encoding="utf-8")
    return site


# --- AC1: build ------------------------------------------------------------------------------------


def test_ac1_build_green_runs_pages_check_and_names_the_tree(tmp_path: Path) -> None:
    site = _built_site(tmp_path)
    runner = FakeRunner({BUILD_ARGV: _Proc(0)})
    result = run_build(_deps(tmp_path, runner))
    assert result.ok is True
    assert runner.calls == [list(BUILD_ARGV)]
    assert runner.calls[0] == ["pixi", "run", "--frozen", "-e", "site", "pages-check"]
    digest = tree_hash(site)
    assert result.summary == f"pages build: pages-check exit 0; tree {digest}"
    assert (tmp_path / FLEET_STATUS_REL).is_file()  # the fleet board's input is written first


def test_ac1_build_json(tmp_path: Path) -> None:
    site = _built_site(tmp_path)
    result = run_build(_deps(tmp_path, FakeRunner({BUILD_ARGV: _Proc(0)})), json_out=True)
    payload = json.loads(result.summary)
    assert payload["exit"] == 0
    assert payload["tree_hash"] == tree_hash(site)
    assert payload["root"] == SITE_ROOT_REL
    assert not (site / "build.json").exists()  # build never writes build.json itself


def test_ac1_build_red_names_the_exit(tmp_path: Path) -> None:
    _built_site(tmp_path)
    runner = FakeRunner({BUILD_ARGV: _Proc(2, stderr="assemble_pages: broken link")})
    result = run_build(_deps(tmp_path, runner))
    assert result.ok is False
    assert "pages-check exit 2" in result.summary
    assert "broken link" in result.summary


def test_ac1_build_red_is_exit_failed_from_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _built_site(tmp_path)
    runner = FakeRunner({BUILD_ARGV: _Proc(2)})
    monkeypatch.setattr(pages_duty, "_production_deps", lambda root: _deps(tmp_path, runner))
    assert main(["pages", "build"]) == EXIT_FAILED


def test_build_refuses_before_pages_check_when_the_input_cannot_be_written(tmp_path: Path) -> None:
    def _broken(root: Path) -> Path:
        raise OSError("disk full")

    runner = FakeRunner({BUILD_ARGV: _Proc(0)})
    result = run_build(_deps(tmp_path, runner, write=_broken))
    assert result.ok is False
    assert FLEET_STATUS_REL in result.summary and "disk full" in result.summary
    assert runner.calls == []


def test_build_dry_run_runs_nothing(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = run_build(_deps(tmp_path, runner), dry_run=True)
    assert result.ok is True
    assert runner.calls == []
    assert result.details["argv"] == [list(BUILD_ARGV)]
    assert "pixi run --frozen -e site pages-check" in result.summary
    assert not (tmp_path / FLEET_STATUS_REL).exists()


def test_build_stamp_runs_the_workflows_stamp_after_a_green_build(tmp_path: Path) -> None:
    _built_site(tmp_path)
    runner = FakeRunner(
        {
            BUILD_ARGV: _Proc(0),
            ("pixi", "run", "--frozen", "-e", "pyforge-guild"): _Proc(0, "tree_hash=ab\nchanged=true\n"),
        }
    )
    result = run_build(_deps(tmp_path, runner), stamp=True, site_url=_SITE)
    assert result.ok is True
    assert runner.calls[1] == [
        "pixi",
        "run",
        "--frozen",
        "-e",
        "pyforge-guild",
        "python",
        "scripts/pages_build_stamp.py",
        "--root",
        SITE_ROOT_REL,
        "--live-url",
        "https://rxm7706.github.io/local-recipes/build.json",
    ]
    assert "changed=true" in result.summary


# --- AC2: deploy -----------------------------------------------------------------------------------

_RUN = {
    "databaseId": 4242,
    "url": "https://github.com/o/r/actions/runs/4242",
    "status": "queued",
    "event": "workflow_dispatch",
    "createdAt": "2026-10-15T12:00:03Z",
}


def test_ac2_deploy_dry_run_prints_both_argv_and_calls_nothing(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = run_deploy(_deps(tmp_path, runner), dry_run=True)
    assert result.ok is True
    assert runner.calls == []
    lines = result.summary.splitlines()
    assert lines[0] == "pages deploy (dry-run): gh workflow run pages.yml --ref main"
    assert lines[1].startswith("pages deploy (dry-run): gh run list --workflow pages.yml")


def test_ac2_deploy_dispatches_then_names_the_run(tmp_path: Path) -> None:
    runner = FakeRunner({DISPATCH_ARGV: _Proc(0), DEPLOY_LIST_ARGV: _Proc(0, json.dumps([_RUN]))})
    result = run_deploy(_deps(tmp_path, runner))
    assert result.ok is True
    assert runner.calls == [list(DISPATCH_ARGV), list(DEPLOY_LIST_ARGV)]
    assert result.summary == "pages deploy: run 4242 https://github.com/o/r/actions/runs/4242 (queued)"


def test_ac2_deploy_waits_for_the_dispatched_run_to_be_listed(tmp_path: Path) -> None:
    earlier = {**_RUN, "databaseId": 4100, "createdAt": "2026-10-14T08:00:00Z"}
    runner = FakeRunner(
        {DISPATCH_ARGV: _Proc(0), DEPLOY_LIST_ARGV: [_Proc(0, json.dumps([earlier])), _Proc(0, json.dumps([_RUN]))]}
    )
    result = run_deploy(_deps(tmp_path, runner))
    assert result.ok is True
    assert "run 4242" in result.summary
    assert runner.calls.count(list(DEPLOY_LIST_ARGV)) == 2


def test_ac2_deploy_names_no_run_when_none_is_listed(tmp_path: Path) -> None:
    runner = FakeRunner({DISPATCH_ARGV: _Proc(0), DEPLOY_LIST_ARGV: _Proc(0, "[]")})
    result = run_deploy(_deps(tmp_path, runner))
    assert result.ok is False
    assert "listed no run" in result.summary
    assert runner.calls.count(list(DEPLOY_LIST_ARGV)) == 5  # noqa: PLR2004 -- every attempt


def test_ac2_deploy_names_the_newest_earlier_dispatch_with_a_note(tmp_path: Path) -> None:
    earlier = {**_RUN, "databaseId": 4100, "createdAt": "2026-10-14T08:00:00Z"}
    runner = FakeRunner({DISPATCH_ARGV: _Proc(0), DEPLOY_LIST_ARGV: _Proc(0, json.dumps([earlier]))})
    result = run_deploy(_deps(tmp_path, runner))
    assert result.ok is True
    assert "run 4100" in result.summary and "newest earlier dispatch" in result.summary


def test_ac2_deploy_run_list_failure_names_the_argv(tmp_path: Path) -> None:
    runner = FakeRunner({DISPATCH_ARGV: _Proc(0), DEPLOY_LIST_ARGV: _Proc(1, stderr="HTTP 502")})
    result = run_deploy(_deps(tmp_path, runner))
    assert result.ok is False
    assert "`gh run list --workflow pages.yml" in result.summary and "HTTP 502" in result.summary


def test_ac2_deploy_gh_failure_names_argv_and_stderr(tmp_path: Path) -> None:
    runner = FakeRunner({DISPATCH_ARGV: _Proc(1, stderr="HTTP 403: Resource not accessible")})
    result = run_deploy(_deps(tmp_path, runner))
    assert result.ok is False
    assert "`gh workflow run pages.yml --ref main` exited 1" in result.summary
    assert "HTTP 403" in result.summary
    assert runner.calls == [list(DISPATCH_ARGV)]


def _jobs(deploy: str | None) -> _Proc:
    jobs = [{"name": "build", "conclusion": "success"}]
    if deploy is not None:
        jobs.append({"name": "deploy", "conclusion": deploy})
    return _Proc(0, json.dumps({"jobs": jobs}))


def test_ac2_deploy_wait_watches_the_run_and_reports_the_page(tmp_path: Path) -> None:
    runner = FakeRunner(
        {
            DISPATCH_ARGV: _Proc(0),
            DEPLOY_LIST_ARGV: _Proc(0, json.dumps([_RUN])),
            ("gh", "run", "watch"): _Proc(0),
            ("gh", "run", "view"): _jobs("success"),
            SITE_URL_ARGV: _Proc(0, _SITE + "\n"),
        }
    )
    result = run_deploy(_deps(tmp_path, runner), wait=True)
    assert result.ok is True
    assert runner.calls[2] == ["gh", "run", "watch", "4242", "--exit-status"]
    assert runner.calls[3] == ["gh", "run", "view", "4242", "--json", "jobs"]
    assert result.summary.splitlines()[-1] == f"pages deploy: run 4242 succeeded; deployed; page {_SITE}"
    assert result.details["deploy_job"] == "success"


def test_ac2_deploy_wait_says_a_skipped_deploy_was_skipped(tmp_path: Path) -> None:
    """102.3's re-review: a dispatch of an unchanged tree succeeds with its deploy job skipped; the
    duty says so instead of naming a deploy that did not happen."""
    runner = FakeRunner(
        {
            DISPATCH_ARGV: _Proc(0),
            DEPLOY_LIST_ARGV: _Proc(0, json.dumps([_RUN])),
            ("gh", "run", "watch"): _Proc(0),
            ("gh", "run", "view"): _jobs("skipped"),
            SITE_URL_ARGV: _Proc(0, _SITE + "\n"),
        }
    )
    result = run_deploy(_deps(tmp_path, runner), wait=True)
    assert result.ok is True
    assert result.summary.splitlines()[-1] == "pages deploy: run 4242 succeeded; tree unchanged; deploy skipped"
    assert "deployed" not in result.summary and "page " not in result.summary
    assert list(SITE_URL_ARGV) not in runner.calls  # no page is named for a deploy that did not run


@pytest.mark.parametrize(
    ("view", "expected"),
    [
        (
            _Proc(1, stderr="HTTP 502"),
            "deploy job conclusion unavailable (`gh run view 4242 --json jobs` exited 1: HTTP 502)",
        ),
        (_Proc(0, "not json"), "deploy job conclusion unavailable (`gh run view 4242 --json jobs` gave invalid JSON"),
        (
            _jobs(None),
            "deploy job conclusion unavailable (`gh run view 4242 --json jobs` names no concluded 'deploy' job)",
        ),
        (_jobs("neutral"), "deploy job concluded 'neutral'"),
    ],
    ids=["view-fails", "not-json", "no-deploy-job", "other-conclusion"],
)
def test_ac2_deploy_wait_names_an_unreadable_deploy_job(tmp_path: Path, view: _Proc, expected: str) -> None:
    runner = FakeRunner(
        {
            DISPATCH_ARGV: _Proc(0),
            DEPLOY_LIST_ARGV: _Proc(0, json.dumps([_RUN])),
            ("gh", "run", "watch"): _Proc(0),
            ("gh", "run", "view"): view,
            SITE_URL_ARGV: _Proc(0, _SITE + "\n"),
        }
    )
    result = run_deploy(_deps(tmp_path, runner), wait=True)
    assert result.ok is True  # the run itself succeeded; only the job's conclusion is unread
    assert expected in result.summary
    assert "tree unchanged" not in result.summary


def test_ac2_deploy_dry_run_with_wait_prints_the_watch_and_the_job_read(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = run_deploy(_deps(tmp_path, runner), dry_run=True, wait=True)
    assert runner.calls == []
    assert result.summary.splitlines()[2:] == [
        "pages deploy (dry-run): gh run watch <run id> --exit-status",
        "pages deploy (dry-run): gh run view <run id> --json jobs",
    ]


def test_ac2_deploy_wait_propagates_a_failed_run(tmp_path: Path) -> None:
    runner = FakeRunner(
        {
            DISPATCH_ARGV: _Proc(0),
            DEPLOY_LIST_ARGV: _Proc(0, json.dumps([_RUN])),
            ("gh", "run", "watch"): _Proc(1, stderr="run failed"),
        }
    )
    result = run_deploy(_deps(tmp_path, runner), wait=True)
    assert result.ok is False
    assert "run failed" in result.summary


def test_no_pages_verb_commits_or_pushes(tmp_path: Path) -> None:
    _built_site(tmp_path)
    runner = FakeRunner(
        {
            BUILD_ARGV: _Proc(0),
            DISPATCH_ARGV: _Proc(0),
            DEPLOY_LIST_ARGV: _Proc(0, json.dumps([_RUN])),
            ("gh", "run", "watch"): _Proc(0),
            SITE_URL_ARGV: _Proc(0, _SITE),
            ("curl",): _Proc(0, "HTTP/2 200\n"),
            STATUS_RUN_ARGV: _Proc(0, "[]"),
        }
    )
    deps = _deps(tmp_path, runner)
    run_build(deps)
    run_deploy(deps, wait=True)
    run_status(deps)
    assert not [argv for argv in runner.calls if argv[0] == "git"]


# --- AC3: status -----------------------------------------------------------------------------------

_HEAD = "HTTP/2 200\r\nlast-modified: Wed, 15 Oct 2026 06:23:00 GMT\r\ncontent-type: text/html\r\n"
_BUILD_JSON = {"tree_hash": "9f86d08", "built_from": "835a38d8d6", "run_id": "77", "built_at": "2026-10-15T06:20:00Z"}
_LAST = [
    {
        "databaseId": 4242,
        "conclusion": "success",
        "status": "completed",
        "event": "schedule",
        "createdAt": "2026-10-15T06:23:00Z",
        "url": "https://github.com/o/r/actions/runs/4242",
    }
]


def _status_runner(*, head: _Proc | None = None) -> FakeRunner:
    return FakeRunner(
        {
            SITE_URL_ARGV: _Proc(0, _SITE + "\n"),
            ("curl", "-sIL"): head or _Proc(0, _HEAD),
            ("curl", "-fsS"): _Proc(0, json.dumps(_BUILD_JSON)),
            STATUS_RUN_ARGV: _Proc(0, json.dumps(_LAST)),
        }
    )


def test_ac3_status_prints_the_live_root_the_last_run_and_the_verdict(tmp_path: Path) -> None:
    runner = _status_runner()
    result = run_status(_deps(tmp_path, runner, verdict=("paused", "")))
    assert result.ok is True
    live, run, registry = result.summary.splitlines()
    assert live == (
        f"live root: {_SITE} last-modified Wed, 15 Oct 2026 06:23:00 GMT; tree 9f86d08 built from 835a38d8d6"
    )
    assert run == "last run: 4242 schedule success 2026-10-15T06:23:00Z https://github.com/o/r/actions/runs/4242"
    assert registry == "registry verdict: pages paused"
    assert runner.calls[0] == list(SITE_URL_ARGV)
    assert ["curl", "-fsS", "--max-time", "30", "https://rxm7706.github.io/local-recipes/build.json"] in runner.calls


def test_ac3_site_url_overrides_the_gh_lookup(tmp_path: Path) -> None:
    runner = _status_runner()
    result = run_status(_deps(tmp_path, runner), site_url="https://pages.example.com/docs/")
    assert list(SITE_URL_ARGV) not in runner.calls
    assert "live root: https://pages.example.com/docs/" in result.summary


def test_ac3_an_unreachable_site_is_a_fact(tmp_path: Path) -> None:
    runner = _status_runner(head=_Proc(22))
    result = run_status(_deps(tmp_path, runner))
    assert result.ok is True
    live, run, registry = result.summary.splitlines()
    assert live == f"live root: {_SITE} unreachable (curl exit 22)"
    assert run.startswith("last run: 4242")
    assert registry == "registry verdict: pages live"


def test_ac3_an_unavailable_registry_verdict_keeps_ok(tmp_path: Path) -> None:
    reason = "ci: gh api rate_limit failed: gh auth login required"
    result = run_status(_deps(tmp_path, _status_runner(), verdict=(None, reason)))
    assert result.ok is True
    assert result.summary.splitlines()[2] == f"registry verdict: unavailable ({reason})"


def test_ac3_json_emits_the_three_blocks(tmp_path: Path) -> None:
    result = run_status(_deps(tmp_path, _status_runner()), json_out=True)
    payload = json.loads(result.summary)
    assert set(payload) == {"live", "last_run", "registry"}
    assert payload["live"]["tree_hash"] == "9f86d08"
    assert payload["last_run"]["databaseId"] == 4242
    assert payload["registry"] == {"surface": "pages", "verdict": "live"}


def test_status_with_every_gh_call_failing_reads_unavailable_and_fails(tmp_path: Path) -> None:
    """A really unauthenticated `gh`: the site lookup, the run list and the ci reader all fail. The
    lines say so; the run list is the duty's own fact, so `ok` is false (the spec's matrix row)."""
    runner = FakeRunner({("gh",): _Proc(4, stderr="gh auth login required")})
    result = run_status(_deps(tmp_path, runner, verdict=(None, "ci: gh api rate_limit failed: gh auth login required")))
    assert result.ok is False
    live, run, registry = result.summary.splitlines()
    assert live.startswith("live root: unavailable (`gh api repos/{owner}/{repo}/pages --jq .html_url` exited 4")
    assert run.startswith("last run: `gh run list --workflow pages.yml") and "auth login" in run
    assert registry.startswith("registry verdict: unavailable (")
    assert not [argv for argv in runner.calls if argv[0] == "curl"]


def test_status_cannot_read_the_last_run(tmp_path: Path) -> None:
    runner = _status_runner()
    runner.responses[STATUS_RUN_ARGV] = _Proc(4, stderr="gh: not logged in")
    result = run_status(_deps(tmp_path, runner))
    assert result.ok is False
    assert "not logged in" in result.summary.splitlines()[1]


def test_the_registry_verdict_is_ci_status_s_pages_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"rows": [{"id": "pages.build", "verdict": "live"}, {"id": "pages", "verdict": "stuck"}]}
    monkeypatch.setattr(
        ci, "run_status", lambda deps, json_out: DutyResult(ok=True, summary="{}", details={"payload": payload})
    )
    assert pages_duty.ci_registry_verdict(tmp_path, FakeRunner()) == ("stuck", "")


def test_the_registry_verdict_is_unavailable_when_ci_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    refused = DutyResult(
        ok=False, summary="ci: refused — flag pyforge.steward.ci_pause_control is off", details={"exit_code": 3}
    )
    monkeypatch.setattr(ci, "run_status", lambda deps, json_out: refused)
    assert pages_duty.ci_registry_verdict(tmp_path, FakeRunner()) == (None, refused.summary)

    def _crash(deps, json_out):
        raise FileNotFoundError("docs/governance/ci-surfaces.yaml")

    monkeypatch.setattr(ci, "run_status", _crash)
    verdict, reason = pages_duty.ci_registry_verdict(tmp_path, FakeRunner())
    assert verdict is None and "ci-surfaces.yaml" in reason


# --- AC4: the flag (the two-state test is test_pages_duty_flag_states.py) ---------------------------


@pytest.mark.parametrize("verb", ["build", "deploy", "status"])
def test_ac4_each_verb_refuses_with_the_flag_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, verb: str
) -> None:
    runner = FakeRunner()
    monkeypatch.setattr(pages_duty, "_production_deps", lambda root: _deps(tmp_path, runner, flag_on=False))
    assert main(["pages", verb]) == EXIT_PAGES_REFUSAL == 3
    assert "pyforge.steward.pages_duty is off" in capsys.readouterr().err
    assert runner.calls == []
    assert not (tmp_path / FLEET_STATUS_REL).exists()


# --- AC5: the retirement ----------------------------------------------------------------------------


@pytest.mark.parametrize("verb", ["dashboard", "status"])
def test_ac5_the_retired_deploy_verbs_are_usage_errors(verb: str) -> None:
    assert main(["deploy", verb]) == EXIT_USAGE


def test_ac5_nothing_of_the_old_path_stays_importable() -> None:
    for name in (
        "build_dashboard",
        "dashboard_diff",
        "commit_and_push_dashboard",
        "_push_pending_commit_if_ahead",
        "last_deploy_commit",
        "DeployRecord",
        "_run_dashboard",
        "_run_status",
        "_tracked_ledger_refusal",
    ):
        assert not hasattr(deploy, name), name
    assert deploy._DEPLOY_VERBS == ("perimeter", "static")


def test_ac5_deploy_static_help_says_a_pull_request_lands_the_file(capsys) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["deploy", "static", "--help"])
    assert "pull request" in capsys.readouterr().out


# --- AC6: the duty count -----------------------------------------------------------------------------


def test_ac6_pages_follows_ci_and_restore_keeps_its_slot() -> None:
    assert len(DUTIES) == 31  # noqa: PLR2004 -- Story 102.3 adds pages
    assert DUTIES.index("pages") == DUTIES.index("ci") + 1
    assert DUTIES.index("restore") == 13  # noqa: PLR2004
    assert isinstance(resolve_duty("pages"), PagesDuty)


def test_ac6_help_lists_pages(capsys) -> None:
    assert main(["--help"]) == EXIT_OK
    out = capsys.readouterr().out
    assert ",ci,pages,preflight}" in out  # the duty choices line, not deploy's help text
    assert any(line.strip().startswith("pages ") for line in out.splitlines())


def test_ac6_bare_pages_names_the_three_verbs(capsys) -> None:
    assert main(["pages"]) == EXIT_OK
    assert capsys.readouterr().out.strip() == "pages: available verbs are build, deploy, status"
    assert PagesDuty().run(argparse.Namespace(pages_verb=None)).ok is True


# --- the fleet board's input (herald 42.1's reader; closes the 102.2 gap) -----------------------------

_EPICS = """# Epics

## Epic 1: First

### Story 1.1: Done one
**Deps:** —

### Story 1.2: Blocked one
**Deps:** —

## Epic 2: Second

### Story 2.1: Backlog one
**Deps:** —
"""
_LEDGER = """development_status:
  epic-1: in-progress
  1-1-done-one: done
  1-2-blocked-one: blocked
  epic-2: backlog
  2-1-backlog-one: backlog
"""


def test_write_fleet_status_reads_the_tracked_ledgers(tmp_path: Path) -> None:
    station = tmp_path / "_bmad-output" / "projects" / "pyforge-demo" / "planning-artifacts"
    station.mkdir(parents=True)
    (station / "epics.md").write_text(_EPICS, encoding="utf-8")
    (station / "sprint-status-ledger.yaml").write_text(_LEDGER, encoding="utf-8")

    out = pages_duty.write_fleet_status(tmp_path)

    assert out == tmp_path / FLEET_STATUS_REL
    document = json.loads(out.read_text(encoding="utf-8"))
    (row,) = document["stations"]
    assert (row["station"], row["epics"], row["total"], row["done"], row["blocked"], row["backlog"]) == (
        "pyforge-demo",
        2,
        3,
        1,
        1,
        1,
    )
    assert {(s["story_id"], s["status"]) for s in document["stories"]} == {
        ("1.1", "done"),
        ("1.2", "blocked"),
        ("2.1", "backlog"),
    }
    assert document["generated_at"]


def test_write_fleet_status_stamps_head_commit_time(tmp_path: Path) -> None:
    """Local == CI: the snapshot time is HEAD's commit time, as the workflow's `--generated-at` passes."""
    import subprocess

    station = tmp_path / "_bmad-output" / "projects" / "pyforge-demo" / "planning-artifacts"
    station.mkdir(parents=True)
    (station / "epics.md").write_text(_EPICS, encoding="utf-8")
    (station / "sprint-status-ledger.yaml").write_text(_LEDGER, encoding="utf-8")
    env = {"GIT_AUTHOR_DATE": "2026-10-14T01:56:19+00:00", "GIT_COMMITTER_DATE": "2026-10-14T01:56:19+00:00"}
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "ledgers"],
    ):
        subprocess.run(argv, cwd=tmp_path, check=True, capture_output=True, env={**os.environ, **env})
    assert pages_duty.head_commit_time(tmp_path) == "2026-10-14T01:56:19+00:00"
    document = json.loads(pages_duty.write_fleet_status(tmp_path).read_text(encoding="utf-8"))
    assert document["generated_at"] == "2026-10-14T01:56:19+00:00"
    assert "next_running" not in document["stations"][0]
    assert pages_duty.head_commit_time(tmp_path / "not-a-repo") is None


def test_the_fleet_status_document_is_the_shape_herald_reads() -> None:
    """herald 42.1's contract (docsite/tools/status_pages.py): ``stations`` a list, each with
    non-negative integer ``done`` and ``total``; ``stories`` rows with ``story_id`` and ``status``."""
    payload = {
        "generated_at": "2026-10-15T00:00:00+00:00",
        "summary": {
            "stations": {
                "pyforge-b": {
                    "station": "pyforge-b",
                    "total_stories": 4,
                    "done": 3,
                    "backlog": 1,
                    "blocked": 0,
                    "in_progress": 0,
                },
                "pyforge-a": {
                    "station": "pyforge-a",
                    "total_stories": 0,
                    "done": 0,
                    "backlog": 0,
                    "blocked": 0,
                    "in_progress": 0,
                },
            }
        },
        "epics": [{"station": "pyforge-b", "epic_id": "1"}, {"station": "pyforge-b", "epic_id": "2"}],
        "stories": [{"story_id": "1.1", "station": "pyforge-b", "status": "backlog", "title": "t", "jira_key": None}],
    }
    document = fleet_status_document(payload, generated_at="2026-10-15T06:00:00+00:00")
    assert document["generated_at"] == "2026-10-15T06:00:00+00:00"
    assert [s["station"] for s in document["stations"]] == ["pyforge-a", "pyforge-b"]
    for station in document["stations"]:
        assert isinstance(station["done"], int) and isinstance(station["total"], int)
    assert document["stations"][1]["epics"] == 2  # noqa: PLR2004
    assert document["stories"] == [
        {"story_id": "1.1", "station": "pyforge-b", "epic_id": None, "title": "t", "status": "backlog"}
    ]
    with pytest.raises(ValueError, match="summary.stations"):
        fleet_status_document({"summary": {}})
