"""Story 15.2 — CAP-22 suite advance orchestration (fixture-covered chain)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from pyforge.steward import suite_advance as sa
from pyforge.steward.cli import build_parser
from pyforge.steward.suite import (
    BASELINE_2026_08_22,
    BASELINE_ID_2026_08_22,
    SUITE_PACKAGES,
    SuiteDuty,
    build_pipeline_truth_report,
    hooks_from_baseline,
)
from pyforge.steward.suite_advance import (
    AdvanceHooks,
    AdvanceReport,
    advance_from_namespace,
    detect_autotick_mode,
    format_advance_report,
    is_advance_stale,
    recipe_path_for,
    run_advance,
)


def _marker_repo(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    return tmp_path


def _ok_stage(*_a, **_k):
    return {"ok": True}


def _ok_open_pr(repo, package, dry_run):
    del repo, package
    return {
        "ok": True,
        "merged": False,
        "pr_url": None if dry_run else "https://github.com/example/repo/pull/42",
        "dry_run": dry_run,
    }


def _success_hooks() -> AdvanceHooks:
    return AdvanceHooks(
        autotick=lambda repo, package, mode, dry_run: {
            "ok": True,
            "mode": mode,
            "dry_run": dry_run,
        },
        build=_ok_stage,
        test=_ok_stage,
        publish=_ok_stage,
        listing=_ok_stage,
        open_pr=_ok_open_pr,
    )


def test_detect_autotick_mode_tag_vs_head(tmp_path: Path):
    tag = tmp_path / "tag.yaml"
    tag.write_text(
        "context:\n  version: '1.0.0'\nabout:\n  cfe-source-kind: github-tag\n",
        encoding="utf-8",
    )
    head = tmp_path / "head.yaml"
    head.write_text(
        "context:\n  version: '1.0.0.dev0'\n  commit: abcdef\nabout:\n  cfe-source-kind: github-commit\n",
        encoding="utf-8",
    )
    assert detect_autotick_mode(tag) == "tag"
    assert detect_autotick_mode(head) == "head"


def test_baseline_method_is_advance_stale_utility_skills_is_not(tmp_path: Path):
    repo = _marker_repo(tmp_path)
    report = build_pipeline_truth_report(
        repo,
        hooks=hooks_from_baseline(BASELINE_2026_08_22),
        baseline_id=BASELINE_ID_2026_08_22,
    )
    by_name = {p.name: p for p in report.packages}
    assert is_advance_stale(by_name["bmad-method"]) is True
    assert "channel" in by_name["bmad-method"].drifts
    assert is_advance_stale(by_name["bmad-utility-skills"]) is False
    assert by_name["bmad-utility-skills"].drifts == ("wired",)


def test_advance_dry_run_chain_tag_mode_never_merges(tmp_path: Path):
    repo = _marker_repo(tmp_path)
    recipe_dir = repo / "recipes" / "bmad-method"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "recipe.yaml").write_text(
        "context:\n  version: '6.11.0'\nabout:\n  cfe-source-kind: github-tag\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def tracking(name: str):
        def _runner(*args, **kwargs):
            del kwargs
            calls.append(name)
            if name == "autotick":
                return {"ok": True, "mode": args[2], "dry_run": args[3]}
            if name == "open_pr":
                return _ok_open_pr(args[0], args[1], args[2])
            return {"ok": True, "dry_run": True, "skipped": True}

        return _runner

    hooks = AdvanceHooks(
        autotick=tracking("autotick"),
        build=tracking("build"),
        test=tracking("test"),
        publish=tracking("publish"),
        listing=tracking("listing"),
        open_pr=tracking("open_pr"),
    )
    report = run_advance(
        repo,
        "bmad-method",
        dry_run=True,
        baseline=True,
        hooks=hooks,
    )
    assert report.ok is True
    assert report.mode == "tag"
    assert report.merged is False
    assert report.dry_run is True
    assert calls == ["autotick", "build", "test", "publish", "listing", "open_pr"]
    stage_names = [s["stage"] for s in report.stages]
    assert stage_names[0] == "resolve"
    assert stage_names[1:] == calls
    assert "merged=false" in report.summary


def test_advance_head_mode_for_commit_pinned_recipe(tmp_path: Path):
    repo = _marker_repo(tmp_path)
    recipe_dir = repo / "recipes" / "bmad-method"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "recipe.yaml").write_text(
        "context:\n  version: '6.12.0.dev0'\n  commit: deadbeefcafebabe\nabout:\n  cfe-source-kind: github-commit\n",
        encoding="utf-8",
    )
    seen_modes: list[str] = []

    def autotick(repo, package, mode, dry_run):
        del repo, package, dry_run
        seen_modes.append(mode)
        return {"ok": True, "mode": mode}

    report = run_advance(
        repo,
        "bmad-method",
        dry_run=True,
        baseline=True,
        hooks=AdvanceHooks(
            autotick=autotick,
            build=_ok_stage,
            test=_ok_stage,
            publish=_ok_stage,
            listing=_ok_stage,
            open_pr=_ok_open_pr,
        ),
    )
    assert report.ok is True
    assert report.mode == "head"
    assert seen_modes == ["head"]
    assert report.merged is False


def test_advance_refuses_not_stale_and_unknown(tmp_path: Path):
    repo = _marker_repo(tmp_path)
    (repo / "recipes" / "bmad-utility-skills").mkdir(parents=True)
    (repo / "recipes" / "bmad-utility-skills" / "recipe.yaml").write_text(
        "context:\n  version: '2.0.0'\n  commit: abc\nabout:\n  cfe-source-kind: github-commit\n",
        encoding="utf-8",
    )
    not_stale = run_advance(
        repo,
        "bmad-utility-skills",
        dry_run=True,
        baseline=True,
        hooks=_success_hooks(),
    )
    assert not_stale.ok is False
    assert "not stale" in not_stale.summary

    unknown = run_advance(repo, "not-a-suite-pkg", dry_run=True, baseline=True, hooks=_success_hooks())
    assert unknown.ok is False
    assert "unknown suite package" in unknown.summary


def test_advance_refuses_open_pr_hook_that_claims_merge(tmp_path: Path):
    repo = _marker_repo(tmp_path)
    recipe_dir = repo / "recipes" / "bmad-method"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "recipe.yaml").write_text(
        "context:\n  version: '6.11.0'\nabout:\n  cfe-source-kind: github-tag\n",
        encoding="utf-8",
    )

    def merge_happy(repo, package, dry_run):
        del repo, package, dry_run
        return {
            "ok": True,
            "merged": True,
            "pr_url": "https://github.com/example/repo/pull/99",
        }

    report = run_advance(
        repo,
        "bmad-method",
        dry_run=False,
        baseline=True,
        hooks=AdvanceHooks(
            autotick=lambda *a, **k: {"ok": True},
            build=_ok_stage,
            test=_ok_stage,
            publish=_ok_stage,
            listing=_ok_stage,
            open_pr=merge_happy,
        ),
    )
    assert report.ok is False
    assert report.merged is False
    assert "auto-merge" in report.summary


def test_cli_advance_verb_wired_and_duty_dispatches(tmp_path: Path):
    del tmp_path
    parser = build_parser()
    ns = parser.parse_args(["suite", "advance", "--package", "bmad-method", "--dry-run", "--baseline"])
    assert ns.suite_verb == "advance"
    assert ns.package == "bmad-method"
    assert ns.dry_run is True
    assert ns.baseline is True

    from pyforge.steward import suite_advance as sa

    original = sa.run_advance

    def fake_run(repo, package, **kwargs):
        del repo, kwargs
        assert package == "bmad-method"
        return AdvanceReport(
            package=package,
            ok=True,
            mode="tag",
            dry_run=True,
            summary="suite advance: would advance bmad-method; merged=false",
            merged=False,
        )

    sa.run_advance = fake_run  # type: ignore[method-assign]
    try:
        duty = SuiteDuty()
        result = duty.run(ns)
        assert result.ok is True
        assert "merged=false" in result.summary
        assert "advance" in result.details
    finally:
        sa.run_advance = original  # type: ignore[method-assign]

    assert "advance" in parser.format_help()


def test_format_advance_report_json_roundtrip(tmp_path: Path):
    repo = _marker_repo(tmp_path)
    recipe_dir = repo / "recipes" / "bmad-method"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "recipe.yaml").write_text(
        "context:\n  version: '6.11.0'\nabout:\n  cfe-source-kind: github-tag\n",
        encoding="utf-8",
    )
    report = run_advance(repo, "bmad-method", dry_run=True, baseline=True, hooks=_success_hooks())
    text = format_advance_report(report, as_json=True)
    assert '"merged": false' in text
    assert '"package": "bmad-method"' in text


def test_suite_roster_still_thirteen():
    assert len(SUITE_PACKAGES) == 13


# ---------------------------------------------------------------------------
# Story 124.2 (integrator ruling 2026-11-12, item 3): the paths the chain above leaves unexercised -- each refusal at
# resolve, a failing stage, the text report and the CLI entry, and the default stage runners. Every tree is under
# tmp_path; no runner reaches a subprocess, the network or gh: each is handed a recording stand-in.
# ---------------------------------------------------------------------------

_TAG_RECIPE = "context:\n  version: '6.11.0'\nabout:\n  cfe-source-kind: github-tag\n"


def _stale_repo(tmp_path: Path, recipe: str | None = _TAG_RECIPE) -> Path:
    """A marker repo whose bmad-method is advance-stale under the 2026-08-22 baseline; ``recipe=None`` omits it."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo = _marker_repo(tmp_path)
    if recipe is not None:
        recipe_dir = repo / "recipes" / "bmad-method"
        recipe_dir.mkdir(parents=True)
        (recipe_dir / "recipe.yaml").write_text(recipe, encoding="utf-8")
    return repo


class _Runs:
    """A ``subprocess`` stand-in for suite_advance: records each argv and answers with one completed process."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self._answer = (returncode, stdout, stderr)

    def run(self, cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(cmd), kwargs))
        returncode, stdout, stderr = self._answer
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)


def _patch_runs(monkeypatch: pytest.MonkeyPatch, runs: _Runs) -> None:
    monkeypatch.setattr(sa, "subprocess", SimpleNamespace(run=runs.run))


def test_recipe_path_for_names_the_missing_recipe(tmp_path: Path):
    with pytest.raises(sa.SuiteError, match="no recipe.yaml"):
        recipe_path_for(tmp_path, "bmad-method")
    repo = _stale_repo(tmp_path)
    assert recipe_path_for(repo, "bmad-method") == repo / "recipes" / "bmad-method" / "recipe.yaml"


def test_advance_refuses_a_stale_package_without_a_recipe_at_resolve(tmp_path: Path):
    calls: list[str] = []
    hooks = AdvanceHooks(autotick=lambda *a: calls.append("autotick") or {"ok": True})
    report = run_advance(_stale_repo(tmp_path, recipe=None), "bmad-method", dry_run=True, baseline=True, hooks=hooks)
    assert report.ok is False
    assert report.mode == ""
    assert [s["stage"] for s in report.stages] == ["resolve"]
    assert report.stages[0]["ok"] is False
    assert "no recipe.yaml" in report.stages[0]["error"]
    assert report.summary.startswith("suite advance: no recipe.yaml")
    assert calls == []


def test_advance_refuses_a_package_the_truth_report_omits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sa, "build_pipeline_truth_report", lambda repo, **_: SimpleNamespace(packages=[]))
    report = run_advance(_stale_repo(tmp_path), "bmad-method", dry_run=True, baseline=True, hooks=_success_hooks())
    assert report.ok is False
    assert report.stages == [{"stage": "resolve", "ok": False, "error": "missing from truth"}]
    assert "missing from truth report" in report.summary


def test_a_failing_stage_stops_the_chain_and_names_the_stage(tmp_path: Path):
    calls: list[str] = []

    def stage(name: str, ok: bool = True):
        def _runner(*_args):
            calls.append(name)
            return {"ok": ok, "detail": name}

        return _runner

    hooks = AdvanceHooks(
        autotick=stage("autotick"),
        build=stage("build", ok=False),
        test=stage("test"),
        publish=stage("publish"),
        listing=stage("listing"),
        open_pr=stage("open_pr"),
    )
    report = run_advance(_stale_repo(tmp_path), "bmad-method", dry_run=True, baseline=True, hooks=hooks)
    assert report.ok is False
    assert calls == ["autotick", "build"]
    assert report.stages[-1] == {"stage": "build", "ok": False, "detail": "build"}
    assert report.summary == "suite advance: failed at stage 'build' for bmad-method"
    assert report.pr_url is None


def test_a_live_advance_names_its_pr_and_never_merges(tmp_path: Path):
    report = run_advance(_stale_repo(tmp_path), "bmad-method", dry_run=False, baseline=True, hooks=_success_hooks())
    assert report.ok is True
    assert report.merged is False
    assert report.pr_url == "https://github.com/example/repo/pull/42"
    assert report.summary.startswith("suite advance: advanced bmad-method via tag-mode (")
    assert report.summary.endswith("merged=false pr=https://github.com/example/repo/pull/42")

    no_pr = AdvanceHooks(**{**_success_hooks().__dict__, "open_pr": lambda *_: {"ok": True, "merged": False}})
    quiet = run_advance(_stale_repo(tmp_path / "quiet"), "bmad-method", dry_run=False, baseline=True, hooks=no_pr)
    assert quiet.ok is True
    assert quiet.pr_url is None
    assert quiet.summary.endswith("; merged=false")

    dry = run_advance(_stale_repo(tmp_path / "dry"), "bmad-method", dry_run=True, baseline=True, hooks=no_pr)
    assert dry.summary.startswith("suite advance: would advance bmad-method")
    assert dry.summary.endswith("merged=false (dry-run, no PR)")


def test_the_text_report_lists_each_stage_and_the_pr(tmp_path: Path):
    report = run_advance(_stale_repo(tmp_path), "bmad-method", dry_run=False, baseline=True, hooks=_success_hooks())
    text = format_advance_report(report, as_json=False)
    lines = text.splitlines()
    assert lines[0] == "steward suite advance — bmad-method"
    assert "ok: True" in lines
    assert "mode: tag" in lines
    assert "merged: False" in lines
    assert f"drifts: {','.join(report.drifts)}" in lines
    assert "pr: https://github.com/example/repo/pull/42" in lines
    stages = lines[lines.index("stages:") + 1 : -1]
    assert stages == [f"  - {name}: ok" for name in sa._STAGE_ORDER]
    assert lines[-1] == report.summary
    assert text.endswith("\n")

    refused = format_advance_report(
        AdvanceReport(package="x", ok=False, mode="", dry_run=True, stages=[{"stage": "resolve", "ok": False}]),
        as_json=False,
    )
    assert "mode: -" in refused.splitlines()
    assert "drifts: -" in refused.splitlines()
    assert "  - resolve: FAIL" in refused.splitlines()
    assert not any(line.startswith("pr: ") for line in refused.splitlines())


def test_advance_from_namespace_requires_a_package_and_reads_the_given_root(tmp_path: Path):
    missing = advance_from_namespace(argparse.Namespace(package=None))
    assert missing.ok is False
    assert missing.summary == "suite advance: --package is required"

    ns = argparse.Namespace(package="bmad-method", repo_root=str(_stale_repo(tmp_path)), dry_run=True, baseline=True)
    ns.json = True
    result = advance_from_namespace(ns, hooks=_success_hooks())
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["package"] == "bmad-method"
    assert payload["dry_run"] is True
    assert payload["merged"] is False
    assert result.details["advance"] == payload


def test_default_autotick_runs_the_updater_on_the_recipe_and_reads_its_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _stale_repo(tmp_path)
    runs = _Runs(stdout='progress\n{"version": "6.12.0"}\n')
    _patch_runs(monkeypatch, runs)
    payload = sa._default_autotick(repo, "bmad-method", "head", True)
    ((cmd, kwargs),) = runs.calls
    skills_updater = repo / ".claude" / "skills" / "conda-forge-expert" / "scripts" / "github_updater.py"
    assert cmd[1:] == [
        str(skills_updater),
        str(repo / "recipes" / "bmad-method" / "recipe.yaml"),
        "--head",
        "--dry-run",
    ]
    assert kwargs["cwd"] == repo
    assert payload["ok"] is True
    assert payload["result"] == {"version": "6.12.0"}
    assert payload["mode"] == "head"
    assert payload["dry_run"] is True

    scripts_updater = repo / ".claude" / "scripts" / "conda-forge-expert" / "github_updater.py"
    scripts_updater.parent.mkdir(parents=True)
    scripts_updater.write_text("", encoding="utf-8")
    failing = _Runs(returncode=2, stdout="{not json}\n", stderr="boom")
    _patch_runs(monkeypatch, failing)
    payload = sa._default_autotick(repo, "bmad-method", "tag", False)
    ((cmd, _),) = failing.calls
    assert cmd[1:] == [str(scripts_updater), str(repo / "recipes" / "bmad-method" / "recipe.yaml")]
    assert payload["ok"] is False
    assert payload["returncode"] == 2
    assert payload["stderr"] == "boom"
    assert "result" not in payload


def test_default_build_skips_on_a_dry_run_and_builds_the_recipe_otherwise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runs = _Runs(returncode=1, stdout="built?", stderr="no")
    _patch_runs(monkeypatch, runs)
    assert sa._default_build(tmp_path, "bmad-method", True) == {"ok": True, "dry_run": True, "skipped": True}
    assert runs.calls == []
    result = sa._default_build(tmp_path, "bmad-method", False)
    ((cmd, kwargs),) = runs.calls
    assert cmd == [
        "rattler-build",
        "build",
        "--recipe",
        str(tmp_path / "recipes" / "bmad-method"),
        "--output-dir",
        str(tmp_path / "output"),
    ]
    assert kwargs["cwd"] == tmp_path
    assert result == {"ok": False, "returncode": 1, "stdout": "built?", "stderr": "no"}


def test_default_test_publish_and_listing_stages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    skipped = {"ok": True, "dry_run": True, "skipped": True}
    assert sa._default_test(tmp_path, "bmad-method", True) == skipped
    assert sa._default_test(tmp_path, "bmad-method", False) == {
        "ok": True,
        "note": "recipe tests covered by build stage",
    }
    assert sa._default_publish(tmp_path, "bmad-method", True) == skipped
    publish = sa._default_publish(tmp_path, "bmad-method", False)
    assert publish["ok"] is False
    assert "operator credentials" in publish["error"]

    asked: list[str] = []
    versions = {"bmad-method": "6.12.0"}
    monkeypatch.setattr(sa, "fetch_channel_version", lambda package: asked.append(package) or versions.get(package))
    assert sa._default_listing(tmp_path, "bmad-method", True) == skipped
    assert asked == []
    assert sa._default_listing(tmp_path, "bmad-method", False) == {"ok": True, "channel_version": "6.12.0"}
    assert sa._default_listing(tmp_path, "bmad-loop", False) == {"ok": False, "channel_version": None}
    assert asked == ["bmad-method", "bmad-loop"]


def test_default_open_pr_opens_a_reviewable_pr_and_never_merges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runs = _Runs()
    _patch_runs(monkeypatch, runs)
    dry = sa._default_open_pr(tmp_path, "bmad-method", True)
    assert dry == {"ok": True, "dry_run": True, "skipped": True, "merged": False, "pr_url": None}
    assert runs.calls == []

    opened = _Runs(stdout="Creating pull request\nhttps://github.com/example/repo/pull/7\n")
    _patch_runs(monkeypatch, opened)
    result = sa._default_open_pr(tmp_path, "bmad-method", False)
    ((cmd, kwargs),) = opened.calls
    assert cmd[:3] == ["gh", "pr", "create"]
    assert cmd[cmd.index("--head") + 1] == "steward/suite-advance-bmad-method"
    assert "advance bmad-method" in cmd[cmd.index("--title") + 1]
    assert "Do not auto-merge" in cmd[cmd.index("--body") + 1]
    assert "merge" not in cmd[:3] and "--auto" not in cmd
    assert kwargs["cwd"] == tmp_path
    assert result["ok"] is True
    assert result["pr_url"] == "https://github.com/example/repo/pull/7"
    assert result["merged"] is False
    assert result["branch"] == "steward/suite-advance-bmad-method"

    _patch_runs(monkeypatch, _Runs(stdout="created\nexample/repo#8\n"))
    assert sa._default_open_pr(tmp_path, "bmad-method", False)["pr_url"] == "example/repo#8"

    _patch_runs(monkeypatch, _Runs(returncode=1, stderr="no auth"))
    refused = sa._default_open_pr(tmp_path, "bmad-method", False)
    assert refused["ok"] is False
    assert refused["pr_url"] is None
    assert refused["merged"] is False
    assert refused["stderr"] == "no auth"
