"""Story 15.2 — CAP-2 suite advance orchestration (fixture-covered chain)."""

from __future__ import annotations

from pathlib import Path

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
    detect_autotick_mode,
    format_advance_report,
    is_advance_stale,
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
