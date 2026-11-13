"""Chain regeneration read against the repository: the live planning tree and the real ledger renderer.

Story 116.1 (spec-pyforge-marshal:CAP-305): the one ``test_chain_regen.py`` test that reads the tracked tree
moved here, marked ``live_tree``; it fails, never skips, when the planning tree it reads is absent.

Story 116.2 (spec-pyforge-marshal:CAP-305): every ``test_chain_regen.py`` test that seeds a sprint ledger with the
repository's own ``scripts/promote_sprint_status.py`` (or guards with its ``regressions``) moved here too; the script
is loaded when a test runs, never at import, so the module imports off the tree. The seed and the recording invoker
both files use live in ``_chain_regen_support.py``. Every other chain-regeneration test stays in
``test_chain_regen.py``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

import pytest
from _chain_regen_support import RecordingInvoker as _RecordingInvoker
from _chain_regen_support import seed_project

from pyforge.marshal.core.chain_regen import (
    CHAIN_PHASES,
    FULL_CHAIN_PHASES,
    MINIMAL_SKIP_PHASES,
    PlanPhaseRunner,
    apply_status_guard,
    ledger_file,
    load_journal,
    parse_ledger_statuses,
    run_orchestrated_chain,
    run_regeneration,
    verify_code_linkage,
    write_ledger_statuses,
)
from pyforge.marshal.core.verdict import EXIT_OK

pytestmark = pytest.mark.live_tree

_DETAIL = re.compile(r"^read-only verify: (\d+) spec cite\(s\); (\d+) missing(?:: (.+))?$")


def _repo_root() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages -> shared -> src -> repo root, found when a test runs
    return Path(__file__).resolve().parents[6]


def _load_promote():
    """``scripts/promote_sprint_status.py``: the ``regressions`` guard and ledger renderer."""
    path = _repo_root() / "scripts" / "promote_sprint_status.py"
    spec = importlib.util.spec_from_file_location("_promote_sprint_status_chain_regen", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_project(root: Path, slug: str, *, statuses: dict[str, str] | None = None) -> Path:
    """The shared planning-tree seed, plus a sprint ledger rendered by the repository's own script."""
    planning = seed_project(root, slug)
    if statuses is not None:
        promote = _load_promote()
        ledger = planning / "sprint-status-ledger.yaml"
        ledger.write_text(
            promote.render(slug, "implementation-artifacts/sprint-status.yaml", statuses),
            encoding="utf-8",
        )
    return planning


def test_code_linkage_on_the_live_tree_names_only_story_spec_ids_and_completes():
    """The live tree: marshal's verify completes, and each missing cite it counts is named."""
    repo_root = _repo_root()
    epics = repo_root / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "epics.md"
    assert epics.is_file(), f"live planning tree not present: {epics}"
    outcome = verify_code_linkage(repo_root, "pyforge-marshal")
    assert outcome.status == "complete"
    match = _DETAIL.match(outcome.detail)
    assert match is not None, outcome.detail
    named = match.group(3).split(", ") if match.group(3) else []
    assert len(named) == int(match.group(2))
    assert all(re.match(r"^spec-\d{1,3}-\d{1,3}(?:-|$)", cite) for cite in named), named
    assert "spec-surface" not in outcome.detail


# ---------------------------------------------------------------------------
# Story 17.4 — the regeneration guard over a rendered ledger
# ---------------------------------------------------------------------------


def test_phases_run_in_order(tmp_path: Path):
    promote = _load_promote()
    _seed_project(tmp_path, "acme", statuses={"1-1-demo": "done", "1-2-next": "backlog"})
    runner = PlanPhaseRunner()
    report = run_regeneration(
        root=tmp_path,
        project="acme",
        runner=runner,
        regressions_fn=promote.regressions,
        apply=False,
    )
    assert [p.name for p in report.phases] == list(CHAIN_PHASES)
    assert runner.phase_order == list(CHAIN_PHASES)
    assert report.wrote_ledger is False


def test_done_key_drop_refused(tmp_path: Path):
    promote = _load_promote()
    before = {"1-1-demo": "done", "1-2-next": "backlog"}
    _seed_project(tmp_path, "acme", statuses=before)
    # Proposal drops the done key entirely.
    runner = PlanPhaseRunner(proposal={"1-2-next": "backlog", "1-3-new": "backlog"})
    writes: list[dict[str, str]] = []

    def _write(path: Path, statuses: dict[str, str]) -> None:
        writes.append(dict(statuses))
        path.write_text("should-not-matter\n", encoding="utf-8")

    report = run_regeneration(
        root=tmp_path,
        project="acme",
        runner=runner,
        regressions_fn=promote.regressions,
        apply=True,
        write_ledger=_write,
    )
    assert report.wrote_ledger is False
    assert writes == []
    assert report.regressions_blocked == (("1-1-demo", "done", "<absent>"),)
    assert report.statuses_after == before
    assert "1-1-demo" in report.preserved_done_keys


def test_backlog_restructure_allowed_preserves_done(tmp_path: Path):
    promote = _load_promote()
    before = {"1-1-demo": "done", "1-2-old": "backlog"}
    _seed_project(tmp_path, "acme", statuses=before)
    proposed = {"1-1-demo": "done", "1-3-new": "backlog"}
    runner = PlanPhaseRunner(proposal=proposed)
    written: dict[str, str] = {}

    def _write(path: Path, statuses: dict[str, str]) -> None:
        written.update(statuses)
        path.write_text(
            promote.render("acme", "implementation-artifacts/sprint-status.yaml", statuses),
            encoding="utf-8",
        )

    report = run_regeneration(
        root=tmp_path,
        project="acme",
        runner=runner,
        regressions_fn=promote.regressions,
        apply=True,
        write_ledger=_write,
    )
    assert report.wrote_ledger is True
    assert written["1-1-demo"] == "done"
    assert "1-2-old" not in written
    assert written["1-3-new"] == "backlog"
    ledger_text = (tmp_path / "_bmad-output/projects/acme/planning-artifacts/sprint-status-ledger.yaml").read_text(
        encoding="utf-8"
    )
    assert "1-1-demo: done" in ledger_text


def test_orphans_reported_not_deleted(tmp_path: Path):
    promote = _load_promote()
    planning = _seed_project(tmp_path, "acme", statuses={"1-1-demo": "done"})
    orphan_dir = planning / "specs" / "spec-orphan"
    orphan_dir.mkdir()
    orphan_spec = orphan_dir / "SPEC.md"
    orphan_spec.write_text(
        "---\nowner-dream: docs/dreams/missing-forever.md\n---\n# Orphan\n",
        encoding="utf-8",
    )
    (planning / "epics.md").write_text(
        "# Epics\n\nDepends on spec-orphan and spec-missing.\n",
        encoding="utf-8",
    )
    before = orphan_spec.read_text(encoding="utf-8")
    runner = PlanPhaseRunner()
    report = run_regeneration(
        root=tmp_path,
        project="acme",
        runner=runner,
        regressions_fn=promote.regressions,
        apply=True,
        write_ledger=lambda p, s: None,
    )
    assert any(o.kind == "spec" and "missing-forever" in o.reason for o in report.orphans)
    assert any(o.kind == "epic" for o in report.orphans)
    assert orphan_spec.is_file()
    assert orphan_spec.read_text(encoding="utf-8") == before


def test_isolation_other_project_untouched(tmp_path: Path):
    promote = _load_promote()
    _seed_project(tmp_path, "alpha", statuses={"1-1-a": "done"})
    _seed_project(tmp_path, "beta", statuses={"9-9-b": "done"})
    beta_ledger = tmp_path / "_bmad-output/projects/beta/planning-artifacts/sprint-status-ledger.yaml"
    beta_before = beta_ledger.read_text(encoding="utf-8")
    runner = PlanPhaseRunner(proposal={"1-1-a": "done", "1-2-new": "backlog"})

    def _write(path: Path, statuses: dict[str, str]) -> None:
        path.write_text(
            promote.render("alpha", "implementation-artifacts/sprint-status.yaml", statuses),
            encoding="utf-8",
        )

    run_regeneration(
        root=tmp_path,
        project="alpha",
        runner=runner,
        regressions_fn=promote.regressions,
        apply=True,
        write_ledger=_write,
    )
    assert beta_ledger.read_text(encoding="utf-8") == beta_before
    alpha_text = (tmp_path / "_bmad-output/projects/alpha/planning-artifacts/sprint-status-ledger.yaml").read_text(
        encoding="utf-8"
    )
    assert "1-2-new: backlog" in alpha_text
    assert "9-9-b" not in alpha_text


def test_apply_status_guard_reuses_regressions():
    promote = _load_promote()
    safe, blocked = apply_status_guard(
        {"a": "done"},
        {"a": "backlog"},
        promote.regressions,
    )
    assert safe is None
    assert blocked == (("a", "done", "backlog"),)


# ---------------------------------------------------------------------------
# Story 21.2 — orchestrated Full / minimal chain over a seeded ledger
# ---------------------------------------------------------------------------


def _seed_orchestrated(root: Path, slug: str = "acme") -> Path:
    planning = _seed_project(root, slug, statuses={"1-1-demo": "done"})
    return planning


def test_full_phase_sequence(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    invoker = _RecordingInvoker()
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=invoker,
        mode="full",
    )
    assert report.status == "complete"
    assert [p.name for p in report.phases] == list(FULL_CHAIN_PHASES)
    assert all(p.status == "complete" for p in report.phases)
    assert invoker.calls == [
        "bmad-spec",
        "bmad-deep-recon",
        "bmad-product-brief",
        "bmad-prd",
        "bmad-architecture",
        "bmad-create-epics-and-stories",
    ]
    assert report.orphan_manifest_written is True
    assert (Path(report.run_dir) / "state.yaml").is_file()
    assert (Path(report.run_dir) / "orphans.json").is_file()
    assert (Path(report.run_dir) / "orphans.md").is_file()
    assert report.auto_commit is False


def test_minimal_skips_research_and_brief(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    invoker = _RecordingInvoker()
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=invoker,
        mode="minimal",
    )
    assert report.status == "complete"
    assert report.mode == "minimal"
    by_name = {p.name: p for p in report.phases}
    for skipped in MINIMAL_SKIP_PHASES:
        assert by_name[skipped].status == "skipped"
    assert invoker.calls == [
        "bmad-spec",
        "bmad-prd",
        "bmad-architecture",
        "bmad-create-epics-and-stories",
    ]


def test_resume_from_journal(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    # First run blocks at prd.
    blocked = _RecordingInvoker(blocked_at="prd")
    first = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=blocked,
        mode="full",
    )
    assert first.status == "blocked"
    journal = load_journal(Path(first.run_dir))
    assert journal is not None
    assert journal.status == "blocked"
    assert journal.phases["spec"]["status"] == "complete"
    assert journal.phases["prd"]["status"] == "blocked"

    # Resume with a healthy invoker — completed phases are not re-run.
    resume_invoker = _RecordingInvoker()
    second = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=resume_invoker,
        mode="full",
        resume=True,
    )
    assert second.status == "complete"
    assert second.run_id == first.run_id
    # spec/research/brief already complete → not re-invoked; prd onward are.
    assert resume_invoker.calls == [
        "bmad-prd",
        "bmad-architecture",
        "bmad-create-epics-and-stories",
    ]


def test_blocked_halts_without_later_phases(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    invoker = _RecordingInvoker(blocked_at="architecture")
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=invoker,
        mode="full",
    )
    assert report.status == "blocked"
    names = [p.name for p in report.phases]
    assert "architecture" in names
    assert "epics" not in names
    assert "orphan_report" not in names
    assert report.orphan_manifest_written is True
    assert (Path(report.run_dir) / "orphans.json").is_file()


def test_transient_failure_retries_then_completes(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    invoker = _RecordingInvoker(fail_times=1)
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=invoker,
        mode="full",
    )
    assert report.status == "complete"
    by_name = {p.name: p for p in report.phases}
    assert by_name["spec"].attempts == 2
    assert by_name["spec"].status == "complete"


def test_exhausted_failures_halt_chain(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    # First attempt + 2 retries = 3 failures exhaust MAX_PHASE_RETRIES.
    invoker = _RecordingInvoker(fail_times=3)
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=invoker,
        mode="full",
    )
    assert report.status == "failed"
    names = [p.name for p in report.phases]
    assert names == ["spec"]
    assert report.phases[0].attempts == 3
    assert "prd" not in names
    assert report.orphan_manifest_written is True


def test_no_auto_commit_even_when_requested(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    with pytest.raises(ValueError, match="auto_commit"):
        run_orchestrated_chain(
            root=tmp_path,
            project="acme",
            dream=dream,
            invoker=_RecordingInvoker(),
            mode="full",
            auto_commit=True,
        )


# ---------------------------------------------------------------------------
# Story 21.3 — CAP-2 code-status preservation
# ---------------------------------------------------------------------------


class _EpicsWipeInvoker(_RecordingInvoker):
    """On epics phase, rewrite the ledger with a regenerated key set (all backlog)."""

    def __init__(
        self,
        *,
        regenerated: dict[str, str],
        blocked_at: str | None = None,
        fail_times: int = 0,
    ) -> None:
        super().__init__(blocked_at=blocked_at, fail_times=fail_times)
        self._regenerated = dict(regenerated)

    def invoke_planning_skill(
        self,
        skill: str,
        *,
        root: Path,
        project: str,
        dream: Path,
        phase: str,
        run_dir: Path,
    ) -> object:
        result = super().invoke_planning_skill(
            skill,
            root=root,
            project=project,
            dream=dream,
            phase=phase,
            run_dir=run_dir,
        )
        if phase == "epics" and getattr(result, "status", None) in ("complete", "done"):
            write_ledger_statuses(ledger_file(root, project), self._regenerated)
        return result


def test_preserve_survives_full_and_minimal_regen(tmp_path: Path):
    before = {
        "1-1-demo": "done",
        "1-2-wip": "in-progress",
        "1-3-old": "backlog",
    }
    _seed_project(tmp_path, "acme", statuses=before)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    regenerated = {
        "1-1-demo": "backlog",
        "1-2-wip": "backlog",
        "1-4-new": "backlog",
    }

    for mode in ("full", "minimal"):
        write_ledger_statuses(ledger_file(tmp_path, "acme"), before)
        invoker = _EpicsWipeInvoker(regenerated=regenerated)
        report = run_orchestrated_chain(
            root=tmp_path,
            project="acme",
            dream=dream,
            invoker=invoker,
            mode=mode,  # type: ignore[arg-type]
            preserve_code_status=True,
        )
        assert report.status == "complete"
        after = parse_ledger_statuses(ledger_file(tmp_path, "acme").read_text(encoding="utf-8"))
        assert after["1-1-demo"] == "done"
        assert after["1-2-wip"] == "in-progress"
        assert after["1-4-new"] == "backlog"
        assert "1-3-old" not in after
        # byte-identical for matching keys
        assert after["1-1-demo"] == before["1-1-demo"]
        assert after["1-2-wip"] == before["1-2-wip"]


def test_preserve_opt_out_leaves_regenerated_statuses(tmp_path: Path):
    before = {"1-1-demo": "done", "1-2-wip": "in-progress"}
    _seed_project(tmp_path, "acme", statuses=before)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    regenerated = {"1-1-demo": "backlog", "1-2-wip": "backlog", "1-4-new": "backlog"}
    invoker = _EpicsWipeInvoker(regenerated=regenerated)
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=invoker,
        mode="minimal",
        preserve_code_status=False,
    )
    assert report.status == "complete"
    assert report.preserve_code_status_hook is False
    after = parse_ledger_statuses(ledger_file(tmp_path, "acme").read_text(encoding="utf-8"))
    assert after == regenerated


def test_preserve_default_true_and_never_auto_commits(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    # default preserve_code_status=True
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=_RecordingInvoker(),
        mode="minimal",
    )
    assert report.preserve_code_status_hook is True
    assert report.auto_commit is False
    snap = Path(report.run_dir) / "code-status-snapshot.yaml"
    assert snap.is_file()
    with pytest.raises(ValueError, match="auto_commit"):
        run_orchestrated_chain(
            root=tmp_path,
            project="acme",
            dream=dream,
            invoker=_RecordingInvoker(),
            mode="minimal",
            auto_commit=True,
        )


# ---------------------------------------------------------------------------
# Story 21.5 — CAP-5 configurable per-project invocation
# ---------------------------------------------------------------------------


class _ProjectTrackingInvoker(_RecordingInvoker):
    """Records per-invoke project + physical planning path for multi-slug tests."""

    def __init__(self) -> None:
        super().__init__()
        self.projects: list[str] = []
        self.planning_paths: list[Path] = []

    def invoke_planning_skill(
        self,
        skill: str,
        *,
        root: Path,
        project: str,
        dream: Path,
        phase: str,
        run_dir: Path,
    ) -> object:
        self.projects.append(project)
        self.planning_paths.append(root / "_bmad-output" / "projects" / project / "planning-artifacts")
        return super().invoke_planning_skill(
            skill,
            root=root,
            project=project,
            dream=dream,
            phase=phase,
            run_dir=run_dir,
        )


def test_cap5_orchestrated_defaults_match_spec(tmp_path: Path):
    from pyforge.marshal.core.chain_regen import cap5_defaults

    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=_RecordingInvoker(),
    )
    d = cap5_defaults()
    assert report.mode == d["mode"]
    assert report.preserve_code_status_hook is d["preserve_code_status"]
    assert report.stage_hook is d["stage"]
    assert report.apply_orphans_hook is d["apply_orphans"]
    assert report.auto_commit is d["auto_commit"]


def test_cap5_cli_handler_chain_mode_minimal_reaches_orchestrator(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """``run_planning_chain_regenerate`` must honor ``--chain-mode minimal``."""
    from pyforge.marshal.cli.planning import run_planning_chain_regenerate

    _seed_orchestrated(tmp_path, "acme")
    ns = argparse.Namespace(
        project="acme",
        dream="docs/dreams/demo.md",
        root=str(tmp_path),
        format="json",
        live=False,
        resume=False,
        minimal=False,
        chain_mode="minimal",
        preserve_code_status=True,
        apply_orphans=False,
        stage=False,
    )
    code = run_planning_chain_regenerate(ns)
    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    regen = payload["data"]["planning_chain_regeneration"]
    assert regen["mode"] == "minimal"
    assert regen["status"] == "complete"
    assert regen["auto_commit"] is False


def test_cap5_cli_handler_chain_mode_conflict_emits_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Conflicting ``--minimal`` + ``--chain-mode full`` must not start a chain."""
    from pyforge.marshal.cli.planning import run_planning_chain_regenerate

    _seed_orchestrated(tmp_path, "acme")
    ns = argparse.Namespace(
        project="acme",
        dream="docs/dreams/demo.md",
        root=str(tmp_path),
        format="json",
        live=False,
        resume=False,
        minimal=True,
        chain_mode="full",
        preserve_code_status=True,
        apply_orphans=False,
        stage=False,
    )
    code = run_planning_chain_regenerate(ns)
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert "planning_chain_regeneration" not in payload.get("data", {})
    findings = payload.get("findings") or []
    assert any(f.get("code") == "MRS-CHAIN-001" and "conflicts" in f.get("message", "") for f in findings)
    assert any(f.get("path") == "flags: --minimal/--chain-mode" for f in findings)


def test_cap5_two_project_slugs_same_workflow(tmp_path: Path):
    """Same orchestrated workflow against two stations; trees stay isolated."""
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    slugs = ("pyforge-marshal", "pyforge-doctor")
    invoker = _ProjectTrackingInvoker()
    reports = []
    for slug in slugs:
        _seed_orchestrated(tmp_path, slug)
        report = run_orchestrated_chain(
            root=tmp_path,
            project=slug,
            dream=dream,
            invoker=invoker,
            mode="minimal",
        )
        reports.append(report)
        assert report.status == "complete"
        assert report.project == slug
        run_dir = Path(report.run_dir)
        assert run_dir.is_dir()
        # Physical path under this slug only.
        assert f"_bmad-output/projects/{slug}/" in str(run_dir).replace("\\", "/")
        other = slugs[0] if slug == slugs[1] else slugs[1]
        assert f"/projects/{other}/" not in str(run_dir).replace("\\", "/")
        assert (run_dir / "state.yaml").is_file()

    assert set(invoker.projects) == set(slugs)
    for slug, planning in zip(invoker.projects, invoker.planning_paths, strict=True):
        assert planning.name == "planning-artifacts"
        assert slug in planning.parts
        assert planning == (tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts")
    marshal_planning = tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    doctor_planning = tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts"
    assert marshal_planning.is_dir() and doctor_planning.is_dir()
    assert marshal_planning != doctor_planning
    assert Path(reports[0].run_dir).is_relative_to(marshal_planning)
    assert Path(reports[1].run_dir).is_relative_to(doctor_planning)


def test_cap5_auto_commit_still_rejected(tmp_path: Path):
    _seed_orchestrated(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    with pytest.raises(ValueError, match="auto_commit"):
        run_orchestrated_chain(
            root=tmp_path,
            project="acme",
            dream=dream,
            invoker=_RecordingInvoker(),
            mode="full",
            auto_commit=True,
        )


def test_cap5_harness_env_uses_bmad_active_never_switch(tmp_path: Path, monkeypatch):
    """Live harness sets BMAD_ACTIVE_PROJECT; argv never runs bmad-switch."""
    import subprocess

    from pyforge.marshal.adapters.skill_invoke_harness import HarnessSkillInvoker

    _seed_orchestrated(tmp_path, "pyforge-marshal")
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    run_dir = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / ".chain-regen" / "cap5-test"
    )
    run_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):  # noqa: ANN001
        captured["argv"] = list(argv)
        captured["env"] = dict(kwargs.get("env") or {})
        log_file = kwargs.get("stdout")
        if log_file is not None:
            log_file.write(b"STATUS: COMPLETE\n")
        return subprocess.CompletedProcess(argv, 0)

    invoker = HarnessSkillInvoker(live=True)
    monkeypatch.setattr(invoker, "binary_present", lambda: True)
    monkeypatch.setattr(
        "pyforge.marshal.adapters.skill_invoke_harness.subprocess.run",
        fake_run,
    )
    result = invoker.invoke_planning_skill(
        "bmad-spec",
        root=tmp_path,
        project="pyforge-marshal",
        dream=dream,
        phase="spec",
        run_dir=run_dir,
    )
    assert result.status == "complete"
    env = captured["env"]
    assert isinstance(env, dict)
    assert env.get("BMAD_ACTIVE_PROJECT") == "pyforge-marshal"
    argv = captured["argv"]
    assert isinstance(argv, list)
    # Never launch bmad-switch as an argv token / executable.
    assert "bmad-switch" not in argv
    assert not any(str(part).endswith("/bmad-switch") or str(part).endswith("scripts/bmad-switch") for part in argv)
    assert argv[0] == "cursor"
    # Prompt forbids switch and names the physical station path.
    prompt = argv[-1] if argv else ""
    assert "BMAD_ACTIVE_PROJECT=pyforge-marshal" in prompt
    assert "never" in prompt.lower() and "scripts/bmad-switch" in prompt
    assert "never scripts/bmad-switch" in prompt.lower().replace("`", "")
    assert "_bmad-output/projects/pyforge-marshal/" in prompt
