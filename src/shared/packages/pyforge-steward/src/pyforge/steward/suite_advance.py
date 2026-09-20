"""Story 15.2 — CAP-2 one-command advance of a stale bmad-suite package.

Chains autotick (tag | head) → build → test → publish → listing verify →
open a reviewable PR. Never auto-merges. Foreign stages are injectable so
unit tests never touch the network or ``gh``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .interfaces import DutyResult
from .suite import (
    BASELINE_2026_08_22,
    BASELINE_ID_2026_08_22,
    SUITE_PACKAGES,
    PackageTruth,
    SuiteError,
    SuitePackageDef,
    build_pipeline_truth_report,
    fetch_channel_version,
    hooks_from_baseline,
    repo_root,
)

# Drifts that mean the package needs an advance (recipe bump / channel publish).
# ``wired`` / ``installed`` alone are not advance triggers (15.3 owns wiring).
_ADVANCE_DRIFTS = frozenset({"recipe", "channel"})

_STAGE_ORDER: tuple[str, ...] = (
    "resolve",
    "autotick",
    "build",
    "test",
    "publish",
    "listing",
    "open_pr",
)

AutotickFn = Callable[[Path, str, str, bool], Mapping[str, Any]]
BuildFn = Callable[[Path, str, bool], Mapping[str, Any]]
TestFn = Callable[[Path, str, bool], Mapping[str, Any]]
PublishFn = Callable[[Path, str, bool], Mapping[str, Any]]
ListingFn = Callable[[Path, str, bool], Mapping[str, Any]]
OpenPrFn = Callable[[Path, str, bool], Mapping[str, Any]]


@dataclass
class AdvanceHooks:
    """Injectable stage runners. Defaults shell out; tests replace them."""

    autotick: AutotickFn | None = None
    build: BuildFn | None = None
    test: TestFn | None = None
    publish: PublishFn | None = None
    listing: ListingFn | None = None
    open_pr: OpenPrFn | None = None


@dataclass
class AdvanceReport:
    package: str
    ok: bool
    mode: str  # tag | head | ""
    dry_run: bool
    stages: list[dict[str, Any]] = field(default_factory=list)
    drifts: tuple[str, ...] = ()
    pr_url: str | None = None
    summary: str = ""
    merged: bool = False  # always False — AC: never auto-merge

    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "ok": self.ok,
            "mode": self.mode,
            "dry_run": self.dry_run,
            "stages": list(self.stages),
            "drifts": list(self.drifts),
            "pr_url": self.pr_url,
            "summary": self.summary,
            "merged": self.merged,
        }


def _suite_package(name: str) -> SuitePackageDef | None:
    return next((p for p in SUITE_PACKAGES if p.name == name), None)


def recipe_path_for(repo: Path, package: str) -> Path:
    """Return ``recipes/<package>/recipe.yaml`` (must exist for advance)."""
    path = repo / "recipes" / package / "recipe.yaml"
    if not path.is_file():
        raise SuiteError(f"no recipe.yaml at {path}")
    return path


def detect_autotick_mode(recipe_file: Path) -> str:
    """Return ``head`` for commit-pinned recipes, else ``tag``."""
    text = recipe_file.read_text(encoding="utf-8")
    if "cfe-source-kind: github-commit" in text or "\n  commit:" in text:
        return "head"
    return "tag"


def is_advance_stale(pkg: PackageTruth) -> bool:
    return bool(_ADVANCE_DRIFTS.intersection(pkg.drifts))


def _default_autotick(repo: Path, package: str, mode: str, dry_run: bool) -> Mapping[str, Any]:
    recipe = recipe_path_for(repo, package)
    script = repo / ".claude" / "scripts" / "conda-forge-expert" / "github_updater.py"
    if not script.is_file():
        script = repo / ".claude" / "skills" / "conda-forge-expert" / "scripts" / "github_updater.py"
    cmd = [sys.executable, str(script), str(recipe)]
    if mode == "head":
        cmd.append("--head")
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=False)
    payload: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "mode": mode,
        "dry_run": dry_run,
    }
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                payload["result"] = json.loads(line)
            except json.JSONDecodeError:
                pass
            break
    return payload


def _default_build(repo: Path, package: str, dry_run: bool) -> Mapping[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "skipped": True}
    recipe_dir = repo / "recipes" / package
    cmd = [
        "rattler-build",
        "build",
        "--recipe",
        str(recipe_dir),
        "--output-dir",
        str(repo / "output"),
    ]
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _default_test(repo: Path, package: str, dry_run: bool) -> Mapping[str, Any]:
    del repo, package  # stage kept for CAP-2 sequencing; build covers recipe tests
    if dry_run:
        return {"ok": True, "dry_run": True, "skipped": True}
    return {"ok": True, "note": "recipe tests covered by build stage"}


def _default_publish(repo: Path, package: str, dry_run: bool) -> Mapping[str, Any]:
    del repo, package
    if dry_run:
        return {"ok": True, "dry_run": True, "skipped": True}
    return {
        "ok": False,
        "error": (
            "live publish requires operator credentials; re-run without "
            "--dry-run only after configuring anaconda CLI for SelfExplainML "
            "(or inject a publish hook)"
        ),
    }


def _default_listing(repo: Path, package: str, dry_run: bool) -> Mapping[str, Any]:
    del repo
    if dry_run:
        return {"ok": True, "dry_run": True, "skipped": True}
    version = fetch_channel_version(package)
    return {"ok": version is not None, "channel_version": version}


def _default_open_pr(repo: Path, package: str, dry_run: bool) -> Mapping[str, Any]:
    """Open a reviewable PR. Never merges (CAP-2 / story AC)."""
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "skipped": True,
            "merged": False,
            "pr_url": None,
        }
    branch = f"steward/suite-advance-{package}"
    title = f"chore(suite): advance {package} (steward suite advance)"
    body = (
        f"Automated CAP-2 advance for `{package}` via "
        f"`steward suite advance`.\n\n"
        f"**Do not auto-merge** — human review required.\n"
    )
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--head",
            branch,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    pr_url = None
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            if "github.com" in line and "/pull/" in line:
                pr_url = line.strip()
                break
        if pr_url is None and proc.stdout.strip():
            pr_url = proc.stdout.strip().splitlines()[-1]
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "pr_url": pr_url,
        "merged": False,
        "branch": branch,
    }


def run_advance(
    repo: Path,
    package: str,
    *,
    dry_run: bool = False,
    baseline: bool = False,
    hooks: AdvanceHooks | None = None,
) -> AdvanceReport:
    """Execute the CAP-2 advance chain for *package*."""
    hooks = hooks or AdvanceHooks()
    report = AdvanceReport(package=package, ok=False, mode="", dry_run=dry_run)

    if _suite_package(package) is None:
        report.summary = f"suite advance: unknown suite package {package!r}"
        report.stages.append({"stage": "resolve", "ok": False, "error": "unknown package"})
        return report

    probe_hooks = hooks_from_baseline(BASELINE_2026_08_22) if baseline else None
    baseline_id = BASELINE_ID_2026_08_22 if baseline else None
    truth = build_pipeline_truth_report(repo, hooks=probe_hooks, baseline_id=baseline_id)
    pkg_truth = next((p for p in truth.packages if p.name == package), None)
    if pkg_truth is None:
        report.summary = f"suite advance: package {package!r} missing from truth report"
        report.stages.append({"stage": "resolve", "ok": False, "error": "missing from truth"})
        return report

    report.drifts = tuple(pkg_truth.drifts)
    if not is_advance_stale(pkg_truth):
        report.stages.append(
            {
                "stage": "resolve",
                "ok": False,
                "error": "not stale for advance",
                "drifts": list(pkg_truth.drifts),
            }
        )
        report.summary = (
            f"suite advance: {package} is not stale for advance "
            f"(drifts={list(pkg_truth.drifts) or 'none'}; need recipe/channel)"
        )
        return report

    try:
        recipe = recipe_path_for(repo, package)
        mode = detect_autotick_mode(recipe)
    except SuiteError as exc:
        report.stages.append({"stage": "resolve", "ok": False, "error": str(exc)})
        report.summary = f"suite advance: {exc}"
        return report

    report.mode = mode
    report.stages.append(
        {
            "stage": "resolve",
            "ok": True,
            "drifts": list(pkg_truth.drifts),
            "mode": mode,
        }
    )

    stage_runners: list[tuple[str, Callable[[], Mapping[str, Any]]]] = [
        (
            "autotick",
            lambda: (hooks.autotick or _default_autotick)(repo, package, mode, dry_run),
        ),
        (
            "build",
            lambda: (hooks.build or _default_build)(repo, package, dry_run),
        ),
        (
            "test",
            lambda: (hooks.test or _default_test)(repo, package, dry_run),
        ),
        (
            "publish",
            lambda: (hooks.publish or _default_publish)(repo, package, dry_run),
        ),
        (
            "listing",
            lambda: (hooks.listing or _default_listing)(repo, package, dry_run),
        ),
        (
            "open_pr",
            lambda: (hooks.open_pr or _default_open_pr)(repo, package, dry_run),
        ),
    ]

    for stage_name, runner in stage_runners:
        result = dict(runner())
        ok = bool(result.get("ok", False))
        entry = {
            "stage": stage_name,
            "ok": ok,
            **{k: v for k, v in result.items() if k != "ok"},
        }
        report.stages.append(entry)
        if stage_name == "open_pr":
            report.pr_url = result.get("pr_url")  # type: ignore[assignment]
            if result.get("merged"):
                report.ok = False
                report.summary = (
                    f"suite advance: refused — open_pr hook reported merged=True "
                    f"for {package} (advance PRs must never auto-merge)"
                )
                report.merged = False
                return report
        if not ok:
            report.summary = f"suite advance: failed at stage {stage_name!r} for {package}"
            return report

    report.ok = True
    report.merged = False
    action = "would advance" if dry_run else "advanced"
    if report.pr_url:
        pr_bit = f" pr={report.pr_url}"
    elif dry_run:
        pr_bit = " (dry-run, no PR)"
    else:
        pr_bit = ""
    report.summary = (
        f"suite advance: {action} {package} via {mode}-mode ({' → '.join(_STAGE_ORDER)}); merged=false{pr_bit}"
    )
    return report


def format_advance_report(report: AdvanceReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    lines = [
        f"steward suite advance — {report.package}",
        f"ok: {report.ok}",
        f"mode: {report.mode or '-'}",
        f"dry_run: {report.dry_run}",
        f"merged: {report.merged}",
        f"drifts: {','.join(report.drifts) if report.drifts else '-'}",
    ]
    if report.pr_url:
        lines.append(f"pr: {report.pr_url}")
    lines.append("stages:")
    for stage in report.stages:
        flag = "ok" if stage.get("ok") else "FAIL"
        lines.append(f"  - {stage.get('stage')}: {flag}")
    lines.append(report.summary)
    return "\n".join(lines) + "\n"


def advance_from_namespace(ns: argparse.Namespace, *, hooks: AdvanceHooks | None = None) -> DutyResult:
    """CLI entry for ``suite advance``."""
    package = getattr(ns, "package", None)
    if not package:
        return DutyResult(ok=False, summary="suite advance: --package is required")
    repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
    dry_run = bool(getattr(ns, "dry_run", False))
    baseline = bool(getattr(ns, "baseline", False))
    as_json = bool(getattr(ns, "json", False))
    report = run_advance(repo, package, dry_run=dry_run, baseline=baseline, hooks=hooks)
    return DutyResult(
        ok=report.ok,
        summary=format_advance_report(report, as_json=as_json),
        details={"advance": report.to_dict()},
    )
