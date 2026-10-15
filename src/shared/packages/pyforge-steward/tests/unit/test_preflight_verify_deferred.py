"""``steward preflight verify-deferred`` lists what pushes left to CI and runs the full preflight (Story 103.6).

The duty reads ``.steward/preflight-runs.jsonl`` and ``.steward/preflight-skips.log``, prints every run that
deferred lanes and every push that skipped the preflight since ``--since``, then runs
``pixi run --frozen -e pyforge-guild pr-preflight`` with ``PYFORGE_PREFLIGHT_SCOPE=full``. The runner is injected;
nothing here runs pixi.
"""

from __future__ import annotations

import argparse
import io
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

import pytest

from pyforge.steward import bootstrap, preflight, preflight_verify
from pyforge.steward.cli import DUTIES, EXIT_USAGE, build_parser, main, resolve_duty
from pyforge.steward.preflight_verify import PreflightDuty, VerifyDeps


def _run(run_id: str, started: str, *, mode: str | None, deferred: list[tuple[str, str]], verdict: str = "ok") -> dict:
    record: dict = {
        "run_id": run_id,
        "started_at": started,
        "head_sha": f"{run_id}0123456789abcdef",
        "branch": f"branch-{run_id}",
        "verdict": verdict,
        "lanes": [],
    }
    if mode is not None:
        record["mode"] = mode
        record["deferred"] = [{"lane": task, "environment": env, "reason": "CI arbitrates"} for task, env in deferred]
    return record


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    steward = root / ".steward"
    steward.mkdir(parents=True)
    runs = [
        json.dumps({"phase": "install", "run_id": "aaa", "seconds": 1.0}),
        json.dumps(_run("old", "2026-10-13T09:00:00+00:00", mode=None, deferred=[])),
        json.dumps(_run("full", "2026-10-15T08:00:00+00:00", mode="full", deferred=[])),
        json.dumps(
            _run(
                "touch",
                "2026-10-15T09:00:00+00:00",
                mode="touched",
                deferred=[("test-ci", "local-recipes"), ("pyforge-atlas-test", "pyforge-atlas")],
            )
        ),
        json.dumps(
            _run("early", "2026-10-14T23:59:00+00:00", mode="touched", deferred=[("detectors-ci", "pyforge-guild")])
        ),
        "{not json",
        json.dumps(_run("nodate", "yesterday", mode="touched", deferred=[("x", "e")])),
        "",
    ]
    (steward / "preflight-runs.jsonl").write_text("\n".join(runs) + "\n", encoding="utf-8")
    skips = [
        "2026-10-15T08:15:52Z\trefs/heads/main\t6c2acb7db4\tmarshal landing publish 6c2acb7db4",
        "2026-10-15T08:30:33Z\trefs/heads/dispatch/pyforge-doctor/48.1\t2d9eebe439\tdispatch/* branch: supervisor-gated",
        "2026-10-15T08:40:00Z\trefs/heads/gone\t0000000000\tbranch delete: nothing to preflight",
        "2026-10-14T10:00:00Z\trefs/heads/older\tabcdef1234\toperator reason",
        "too\tfew",
        "not-a-time\trefs/heads/x\t1234567890\treason",
    ]
    (steward / "preflight-skips.log").write_text("\n".join(skips) + "\n", encoding="utf-8")
    return root


class Recorder:
    def __init__(self, code: int = 0, raises: BaseException | None = None) -> None:
        self.code = code
        self.raises = raises
        self.calls: list[tuple[tuple[str, ...], Path, dict[str, str]]] = []

    def __call__(self, argv: Sequence[str], cwd: Path, env: Mapping[str, str]) -> int:
        self.calls.append((tuple(argv), cwd, dict(env)))
        if self.raises is not None:
            raise self.raises
        return self.code


def _deps(
    root: Path, runner: Recorder, environ: Mapping[str, str] | None = None
) -> tuple[VerifyDeps, io.StringIO, io.StringIO]:
    out, err = io.StringIO(), io.StringIO()
    deps = VerifyDeps(
        root=root,
        runner=runner,
        out=out,
        err=err,
        environ=environ
        if environ is not None
        else {"PATH": "/usr/bin", "GIT_DIR": "/x/.git", "GIT_INDEX_FILE": "/x/i"},
        head=lambda _root: ("cafe0123456789", "the-branch"),
    )
    return deps, out, err


# ---- AC6: the listing ----------------------------------------------------------------------------


def test_since_lists_the_deferred_runs_and_the_skipped_pushes_and_nothing_else(tmp_path: Path) -> None:
    runner = Recorder()
    deps, out, err = _deps(_root(tmp_path), runner)
    result = preflight_verify.verify_deferred(deps, since=date(2026, 10, 15))
    text = out.getvalue()
    listed = [line.strip() for line in text.splitlines() if line.startswith("  ")]
    assert listed == [
        "2026-10-15T08:15:52Z  refs/heads/main  6c2acb7db4  every lane  (skipped: marshal landing publish 6c2acb7db4)",
        "2026-10-15T08:30:33Z  refs/heads/dispatch/pyforge-doctor/48.1  2d9eebe439  every lane  "
        "(skipped: dispatch/* branch: supervisor-gated)",
        "2026-10-15T09:00:00+00:00  branch-touch  touch01234  test-ci@local-recipes, pyforge-atlas-test@pyforge-atlas  "
        "(2 deferred, CI arbitrates; the run was ok)",
    ]
    assert (
        "verify-deferred: 1 run(s) deferred lanes to CI and 2 push(es) skipped the preflight since 2026-10-15" in text
    )
    assert "running the full preflight on the-branch@cafe012345" in text
    assert "PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight" in text
    warnings = err.getvalue()
    assert "preflight-runs.jsonl line 6 is not JSON" in warnings
    assert "preflight-runs.jsonl line 7 has no readable started_at" in warnings
    assert "preflight-skips.log line 5 has 2 fields, not 4" in warnings
    assert "preflight-skips.log line 6 has no readable time" in warnings
    assert result.ok
    assert (result.details["runs_deferred"], result.details["pushes_skipped"]) == (1, 2)


def test_without_since_every_journaled_one_is_listed(tmp_path: Path) -> None:
    deps, out, _ = _deps(_root(tmp_path), Recorder())
    preflight_verify.verify_deferred(deps, since=None)
    text = out.getvalue()
    assert "2 run(s) deferred lanes to CI and 3 push(es) skipped the preflight in the journals" in text
    assert "branch-early  early01234  detectors-ci@pyforge-guild" in text
    assert "refs/heads/older  abcdef1234  every lane  (skipped: operator reason)" in text
    assert "refs/heads/gone" not in text  # a branch delete pushes no commits
    assert "branch-full" not in text and "branch-old" not in text  # nothing deferred


def test_missing_journals_list_nothing(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    deps, out, _ = _deps(root, Recorder())
    assert preflight_verify.verify_deferred(deps, since=None).ok
    assert "0 run(s) deferred lanes to CI and 0 push(es) skipped the preflight" in out.getvalue()


# ---- AC7: the full run and its exit codes --------------------------------------------------------


def test_the_full_preflight_runs_once_from_the_root_with_scope_full(tmp_path: Path) -> None:
    root = _root(tmp_path)
    runner = Recorder()
    deps, _, _ = _deps(root, runner, environ={"PATH": "/usr/bin", "GIT_DIR": "/x", "GIT_WORK_TREE": "/y", "KEEP": "1"})
    preflight_verify.verify_deferred(deps, since=None)
    ((argv, cwd, env),) = runner.calls
    assert argv == ("pixi", "run", "--frozen", "-e", "pyforge-guild", "pr-preflight")
    assert cwd == root
    assert env[preflight.SCOPE_ENV] == preflight.SCOPE_FULL
    assert env["KEEP"] == "1"
    assert not set(preflight_verify.GIT_HOOK_VARIABLES) & set(env)


@pytest.mark.parametrize(
    ("preflight_exit", "ok", "exit_code", "words"),
    [
        (0, True, None, "is green"),
        (1, False, None, "is red (exit 1)"),
        (7, False, None, "is red (exit 7)"),
        (2, False, 3, "could not run (exit 2)"),
        (130, False, 130, "was interrupted"),
    ],
)
def test_the_duty_projects_the_preflight_exit(
    tmp_path: Path, preflight_exit: int, ok: bool, exit_code: int | None, words: str
) -> None:
    deps, _, _ = _deps(_root(tmp_path), Recorder(code=preflight_exit))
    result = preflight_verify.verify_deferred(deps, since=None)
    assert result.ok is ok
    assert result.details.get("exit_code") == exit_code
    assert result.details["preflight_exit"] == preflight_exit
    assert words in result.summary


def test_no_pixi_on_path_could_not_run(tmp_path: Path) -> None:
    deps, _, _ = _deps(_root(tmp_path), Recorder(raises=FileNotFoundError("pixi")))
    result = preflight_verify.verify_deferred(deps, since=None)
    assert (result.ok, result.details["exit_code"]) == (False, preflight_verify.EXIT_CANNOT_RUN)
    assert "pixi is not on PATH" in result.summary


def _main_with(deps: VerifyDeps, argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    real_parse = argparse.ArgumentParser.parse_args

    def parse_args(
        self: argparse.ArgumentParser, args: Sequence[str] | None = None, namespace: object = None
    ) -> argparse.Namespace:
        ns = real_parse(self, args, namespace)  # type: ignore[arg-type]
        ns._preflight_deps = deps
        return ns

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", parse_args)
    return main(argv)


@pytest.mark.parametrize(("preflight_exit", "steward_exit"), [(0, 0), (1, 1), (2, 3), (130, 130)])
def test_main_exits_with_the_projected_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, preflight_exit: int, steward_exit: int
) -> None:
    runner = Recorder(code=preflight_exit)
    deps, out, _ = _deps(_root(tmp_path), runner)
    assert _main_with(deps, ["preflight", "verify-deferred", "--since", "2026-10-15"], monkeypatch) == steward_exit
    assert len(runner.calls) == 1
    assert "since 2026-10-15" in out.getvalue()


@pytest.mark.parametrize("since", ["2026-13-01", "yesterday", "2026-1-5", "2026-10-15T00:00"])
def test_a_bad_since_is_a_usage_error_and_runs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], since: str
) -> None:
    runner = Recorder()
    deps, _, _ = _deps(_root(tmp_path), runner)
    assert _main_with(deps, ["preflight", "verify-deferred", "--since", since], monkeypatch) == EXIT_USAGE
    assert runner.calls == []
    assert since in capsys.readouterr().err


def test_preflight_without_a_verb_is_a_usage_error() -> None:
    assert main(["preflight"]) == EXIT_USAGE


def test_the_duty_without_its_verb_refuses() -> None:
    result = PreflightDuty().run(argparse.Namespace(duty="preflight"))
    assert not result.ok and "verify-deferred" in result.summary


def test_the_duty_finds_the_repository_root_when_nothing_is_injected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: list[VerifyDeps] = []
    monkeypatch.setattr(preflight_verify, "verify_deferred", lambda deps, since: seen.append(deps) or None)
    PreflightDuty().run(argparse.Namespace(duty="preflight", preflight_verb="verify-deferred", since=None))
    (deps,) = seen
    assert deps.root == bootstrap.repo_root()


# ---- AC8: the CLI --------------------------------------------------------------------------------


def test_preflight_is_the_last_duty() -> None:
    assert DUTIES[-1] == "preflight"
    assert len(DUTIES) == 31  # noqa: PLR2004 -- + pages (Story 102.3), before preflight
    assert isinstance(resolve_duty("preflight"), PreflightDuty)
    ns = build_parser().parse_args(["preflight", "verify-deferred", "--since", "2026-10-01"])
    assert (ns.duty, ns.preflight_verb, ns.since) == ("preflight", "verify-deferred", date(2026, 10, 1))
    assert build_parser().parse_args(["preflight", "verify-deferred"]).since is None
