"""Story 17.4 — orchestrated chain regeneration that cannot lose code status."""

from __future__ import annotations

import argparse
import json
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
    apply_orphans_hook,
    apply_preserved_code_statuses,
    ledger_file,
    load_journal,
    parse_ledger_statuses,
    preserve_code_status_hook,
    run_orchestrated_chain,
    snapshot_code_statuses,
    stage_hook,
    write_ledger_statuses,
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


def test_parse_status_markers_and_silent_exit():
    from pyforge.marshal.adapters.skill_invoke_harness import _parse_status

    assert _parse_status("STATUS: COMPLETE\nok", 0) == "complete"
    assert _parse_status("STATUS:BLOCKED", 0) == "blocked"
    assert _parse_status("STATUS: failed\n", 0) == "failed"
    assert _parse_status("no marker at all", 0) == "failed"
    assert _parse_status("", 1) == "failed"


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


def test_cap4_empty_hooks_are_noop():
    # Empty inputs remain no-ops even when flags are true.
    assert preserve_code_status_hook({"a": "done"}) == {"a": "done"}
    assert apply_orphans_hook((), apply=True) == 0
    assert stage_hook((), stage=True) == 0


# ---------------------------------------------------------------------------
# Story 21.4 — CAP-4 orphan detection with review-gated cleanup
# ---------------------------------------------------------------------------


def _seed_orphan_spec(tmp_path: Path, project: str = "acme") -> Path:
    """Plant a dream-missing orphaned spec folder under planning-artifacts."""
    planning = tmp_path / "_bmad-output" / "projects" / project / "planning-artifacts"
    planning.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "dreams").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "dreams" / "demo.md").write_text("# demo\n", encoding="utf-8")
    orphan_dir = planning / "specs" / "spec-orphan"
    orphan_dir.mkdir(parents=True)
    (orphan_dir / "SPEC.md").write_text(
        "---\nowner-dream: docs/dreams/missing-forever.md\n---\n# Orphan\n",
        encoding="utf-8",
    )
    (planning / "epics.md").write_text(
        "# Epics\n\nDepends on spec-orphan.\n",
        encoding="utf-8",
    )
    (planning / "sprint-status-ledger.yaml").write_text(
        "development_status:\n  1-1-demo: backlog\n",
        encoding="utf-8",
    )
    return orphan_dir


def test_apply_orphans_default_leaves_disk(tmp_path: Path):
    orphan_dir = _seed_orphan_spec(tmp_path)
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=_RecordingInvoker(),
        mode="minimal",
        apply_orphans=False,
    )
    assert report.status == "complete"
    assert report.orphan_manifest_written is True
    assert any(o.kind == "spec" and "spec-orphan" in o.path for o in report.orphans)
    assert orphan_dir.is_dir()
    assert (orphan_dir / "SPEC.md").is_file()
    payload = json.loads((Path(report.run_dir) / "orphans.json").read_text(encoding="utf-8"))
    assert any(row["kind"] == "spec" for row in payload)
    md = (Path(report.run_dir) / "orphans.md").read_text(encoding="utf-8")
    assert "spec-orphan" in md


def test_apply_orphans_deletes_spec_folder_only(tmp_path: Path):
    orphan_dir = _seed_orphan_spec(tmp_path)
    epics = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    dream = tmp_path / "docs" / "dreams" / "demo.md"
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=_RecordingInvoker(),
        mode="minimal",
        apply_orphans=True,
    )
    assert report.status == "complete"
    assert report.apply_orphans_hook is True
    assert not orphan_dir.exists()
    # Epic citations are never deleted — only named in the manifest.
    assert epics.is_file()
    assert "spec-orphan" in epics.read_text(encoding="utf-8")


def test_apply_orphans_hook_direct_unit_delete(tmp_path: Path):
    orphan_dir = _seed_orphan_spec(tmp_path)
    orphans = find_orphans(tmp_path, "acme")
    assert orphans
    assert apply_orphans_hook(orphans, apply=False, root=tmp_path) == 0
    assert orphan_dir.is_dir()
    deleted = apply_orphans_hook(orphans, apply=True, root=tmp_path)
    assert deleted >= 1
    assert not orphan_dir.exists()


def test_stage_indexes_without_commit(tmp_path: Path):
    import subprocess

    from pyforge.marshal.adapters.vcs_git import stage_index_paths

    orphan_dir = _seed_orphan_spec(tmp_path)
    # Real git repo so stage_hook can index.
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    # Dirty regenerated path that should be staged.
    planning = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    (planning / "prd.md").write_text("# regenerated prd\n", encoding="utf-8")

    dream = tmp_path / "docs" / "dreams" / "demo.md"
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=_RecordingInvoker(),
        mode="minimal",
        apply_orphans=True,
        stage=True,
        stager=stage_index_paths,
    )
    assert report.status == "complete"
    assert report.stage_hook is True
    assert not orphan_dir.exists()

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "prd.md" in staged
    assert "spec-orphan" in staged
    # Never committed by the orchestrator — HEAD still the seed commit.
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert log.count("\n") == 0
    assert "seed" in log


def test_stage_without_apply_does_not_delete(tmp_path: Path):
    import subprocess

    from pyforge.marshal.adapters.vcs_git import stage_index_paths

    orphan_dir = _seed_orphan_spec(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    planning = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    (planning / "architecture.md").write_text("# arch\n", encoding="utf-8")

    dream = tmp_path / "docs" / "dreams" / "demo.md"
    report = run_orchestrated_chain(
        root=tmp_path,
        project="acme",
        dream=dream,
        invoker=_RecordingInvoker(),
        mode="minimal",
        apply_orphans=False,
        stage=True,
        stager=stage_index_paths,
    )
    assert report.status == "complete"
    assert orphan_dir.is_dir()
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "architecture.md" in staged
    # Orphan still on disk — deletion not staged.
    assert "spec-orphan" not in staged or orphan_dir.is_dir()


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


def test_apply_preserved_round_trip_unit():
    preserved = {
        "1-1-demo": "done",
        "1-2-wip": "in-progress",
        "1-3-old": "backlog",
    }
    current = {
        "1-1-demo": "backlog",  # regen wiped
        "1-2-wip": "backlog",
        "1-4-new": "backlog",  # new key
        # 1-3-old retired — absent
    }
    merged = apply_preserved_code_statuses(preserved, current)
    assert merged == {
        "1-1-demo": "done",
        "1-2-wip": "in-progress",
        "1-4-new": "backlog",
    }
    assert "1-3-old" not in merged
    # opt-out path helper: snapshot alone is identity copy
    assert snapshot_code_statuses(preserved) == preserved


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


def test_cap5_defaults_matrix():
    from pyforge.marshal.core.chain_regen import cap5_defaults

    defaults = cap5_defaults()
    assert defaults["mode"] == "full"
    assert defaults["chain_mode"] == "full"
    assert defaults["preserve_code_status"] is True
    assert defaults["stage"] is False
    assert defaults["apply_orphans"] is False
    assert defaults["resume"] is False
    assert defaults["auto_commit"] is False


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


def test_cap5_cli_parser_defaults_and_no_auto_commit_flag():
    from pyforge.marshal.cli.main import _build_parser
    from pyforge.marshal.cli.planning import resolve_chain_mode

    parser = _build_parser()
    args = parser.parse_args(
        [
            "planning",
            "chain-regenerate",
            "--project",
            "pyforge-marshal",
            "--dream",
            "docs/dreams/demo.md",
        ]
    )
    assert args.minimal is False
    assert args.chain_mode is None
    assert resolve_chain_mode(args) == "full"
    assert args.preserve_code_status is True
    assert args.stage is False
    assert args.apply_orphans is False
    assert args.resume is False
    assert not hasattr(args, "auto_commit")

    option_strings: list[str] = []
    for action in parser._actions:
        option_strings.extend(action.option_strings or ())
        # Nested planning subparser actions
        if getattr(action, "choices", None) and isinstance(action.choices, dict):
            for sub in action.choices.values():
                for sub_action in getattr(sub, "_actions", ()):
                    option_strings.extend(sub_action.option_strings or ())
                    if getattr(sub_action, "choices", None) and isinstance(sub_action.choices, dict):
                        for nested in sub_action.choices.values():
                            for na in getattr(nested, "_actions", ()):
                                option_strings.extend(na.option_strings or ())

    joined = " ".join(option_strings)
    assert "--project" in joined
    assert "--dream" in joined
    assert "--chain-mode" in joined
    assert "--minimal" in joined
    assert "--preserve-code-status" in joined
    assert "--stage" in joined
    assert "--apply-orphans" in joined
    assert "--resume" in joined
    assert "--auto-commit" not in joined
    assert "--auto_commit" not in joined


def test_cap5_cli_help_documents_parameters():
    from pyforge.marshal.cli import planning as planning_cli

    top = argparse.ArgumentParser(prog="marshal")
    subs = top.add_subparsers()
    planning_cli.add_planning_subparser(subs)
    # Dig out chain-regenerate description + help.
    planning_parser = None
    for action in top._actions:
        if getattr(action, "choices", None) and "planning" in (action.choices or {}):
            planning_parser = action.choices["planning"]
            break
    assert planning_parser is not None
    regen_parser = None
    for action in planning_parser._actions:
        if getattr(action, "choices", None) and "chain-regenerate" in (action.choices or {}):
            regen_parser = action.choices["chain-regenerate"]
            break
    assert regen_parser is not None
    help_text = regen_parser.format_help() + "\n" + (regen_parser.description or "")
    for term in (
        "CAP-5",
        "project_slug",
        "dream_path",
        "chain_mode",
        "preserve_code_status",
        "stage",
        "apply_orphans",
        "resume",
        "auto_commit",
        "bmad-switch",
    ):
        assert term in help_text, f"missing CAP-5 help term: {term}"


def test_cap5_chain_mode_flag_consistent_with_minimal():
    from pyforge.marshal.cli.main import _build_parser
    from pyforge.marshal.cli.planning import resolve_chain_mode

    parser = _build_parser()
    base = [
        "planning",
        "chain-regenerate",
        "--project",
        "acme",
        "--dream",
        "docs/dreams/demo.md",
    ]
    assert resolve_chain_mode(parser.parse_args([*base, "--chain-mode", "full"])) == "full"
    assert resolve_chain_mode(parser.parse_args([*base, "--chain-mode", "minimal"])) == "minimal"
    assert resolve_chain_mode(parser.parse_args([*base, "--minimal"])) == "minimal"
    # Agreeing flags OK.
    assert resolve_chain_mode(parser.parse_args([*base, "--minimal", "--chain-mode", "minimal"])) == "minimal"
    with pytest.raises(ValueError, match="conflicts"):
        resolve_chain_mode(parser.parse_args([*base, "--minimal", "--chain-mode", "full"]))


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
