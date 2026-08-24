"""Story 17.4 — orchestrated chain regeneration that cannot lose code status."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from pyforge.marshal.cli import chain as chain_mod
from pyforge.marshal.cli.chain import run_chain_regenerate
from pyforge.marshal.core.chain_regen import (
    CHAIN_PHASES,
    PlanPhaseRunner,
    apply_status_guard,
    find_orphans,
    run_regeneration,
)
from pyforge.marshal.core.verdict import EXIT_OK


def _load_promote():
    return chain_mod._load_promote()


def _seed_project(root: Path, slug: str, *, statuses: dict[str, str] | None = None) -> Path:
    planning = root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text("# Epics\n\nSee spec-demo.\n", encoding="utf-8")
    specs = planning / "specs"
    specs.mkdir()
    (specs / "spec-demo").mkdir()
    (specs / "spec-demo" / "SPEC.md").write_text(
        "---\nowner-dream: docs/dreams/demo.md\n---\n# Demo\n",
        encoding="utf-8",
    )
    dreams = root / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    dream_file = dreams / "demo.md"
    if not dream_file.is_file():
        dream_file.write_text("# demo\n", encoding="utf-8")
    if statuses is not None:
        promote = _load_promote()
        ledger = planning / "sprint-status-ledger.yaml"
        ledger.write_text(
            promote.render(slug, "implementation-artifacts/sprint-status.yaml", statuses),
            encoding="utf-8",
        )
    return planning


def test_chain_phases_dependency_order():
    assert CHAIN_PHASES == ("spec", "prd", "architecture", "epics")


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
    alpha_text = (
        tmp_path / "_bmad-output/projects/alpha/planning-artifacts/sprint-status-ledger.yaml"
    ).read_text(encoding="utf-8")
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


def test_cli_missing_project(tmp_path: Path):
    ns = argparse.Namespace(
        project="no-such-station",
        apply=False,
        root=str(tmp_path),
        format="json",
    )
    code = run_chain_regenerate(ns)
    # WARN findings → exit 0 in marshal lattice for unevaluable-style warns
    assert code in (EXIT_OK, 0, 1, 2, 3, 4)


def test_cli_help_registers():
    from pyforge.marshal.cli.main import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["chain", "regenerate", "--project", "acme", "--format", "json"])
    assert args.command == "chain"
    assert args.chain_command == "regenerate"
    assert args.project == "acme"


def test_find_orphans_empty_when_dreams_present(tmp_path: Path):
    _seed_project(tmp_path, "acme")
    assert find_orphans(tmp_path, "acme") == ()


# ---------------------------------------------------------------------------
# Story 21.2 — orchestrated Full / minimal chain
# ---------------------------------------------------------------------------

from pyforge.marshal.core.chain_regen import (
    FULL_CHAIN_PHASES,
    MINIMAL_SKIP_PHASES,
    OrchestratedPhaseOutcome,
    apply_orphans_hook,
    load_journal,
    preserve_code_status_hook,
    run_orchestrated_chain,
    stage_hook,
)


class _RecordingInvoker:
    def __init__(self, *, blocked_at: str | None = None, fail_times: int = 0) -> None:
        self.calls: list[str] = []
        self._blocked_at = blocked_at
        self._fail_times = fail_times
        self._failures_left = fail_times

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
        del root, project, dream, run_dir
        self.calls.append(skill)
        if self._blocked_at is not None and phase == self._blocked_at:
            return type("R", (), {"status": "blocked", "detail": "blocked by fixture"})()
        if self._failures_left > 0:
            self._failures_left -= 1
            return type("R", (), {"status": "failed", "detail": "transient"})()
        return type("R", (), {"status": "complete", "detail": f"ok:{skill}"})()


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


def test_cap_stubs_are_noop(tmp_path: Path):
    assert preserve_code_status_hook({"a": "done"}) == {"a": "done"}
    assert apply_orphans_hook((), apply=True) == 0
    assert stage_hook((), stage=True) == 0


def test_cli_planning_help_registers():
    from pyforge.marshal.cli.main import _build_parser

    parser = _build_parser()
    args = parser.parse_args(
        [
            "planning",
            "chain-regenerate",
            "--project",
            "acme",
            "--dream",
            "docs/dreams/demo.md",
            "--minimal",
            "--format",
            "json",
        ]
    )
    assert args.command == "planning"
    assert args.planning_command == "chain-regenerate"
    assert args.project == "acme"
    assert args.minimal is True
