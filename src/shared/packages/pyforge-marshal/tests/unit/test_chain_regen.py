"""Story 17.4 — orchestrated chain regeneration that cannot lose code status.

Story 86.5 retired the ``marshal chain regenerate`` verb (``marshal planning
chain-regenerate`` is the one verb) and made the code-linkage verify and the
epic orphan scan count only cites that name a story spec or a Spec folder.

Story 116.2 (spec-pyforge-marshal:CAP-305): the tests that render a sprint ledger with
the repository's own ``scripts/promote_sprint_status.py`` moved to
``test_chain_regen_live_tree.py``; every test here builds its own tree under ``tmp_path``.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pytest
from _chain_regen_support import RecordingInvoker as _RecordingInvoker
from _chain_regen_support import seed_project as _seed_project

from pyforge.marshal.core.chain_regen import (
    CHAIN_PHASES,
    find_orphans,
)
from pyforge.marshal.core.verdict import EXIT_USAGE


def test_chain_phases_dependency_order():
    assert CHAIN_PHASES == ("spec", "prd", "architecture", "epics")


def test_chain_regenerate_verb_is_retired(capsys: pytest.CaptureFixture[str]):
    """DW-FU-21-2-2: ``marshal chain`` is no verb; ``planning chain-regenerate`` is the one verb."""
    from pyforge.marshal.cli.main import _build_parser, main

    parser = _build_parser()
    with pytest.raises(SystemExit) as parsed:
        parser.parse_args(["chain", "regenerate", "--project", "acme"])
    assert parsed.value.code == 2
    assert "invalid choice: 'chain'" in capsys.readouterr().err

    assert main(["chain", "regenerate", "--project", "acme"]) == EXIT_USAGE

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("pyforge.marshal.cli.chain")

    args = parser.parse_args(["planning", "chain-regenerate", "--project", "acme", "--dream", "docs/dreams/demo.md"])
    assert (args.command, args.planning_command) == ("planning", "chain-regenerate")


def test_find_orphans_empty_when_dreams_present(tmp_path: Path):
    _seed_project(tmp_path, "acme")
    assert find_orphans(tmp_path, "acme") == ()


# ---------------------------------------------------------------------------
# Story 21.2 — orchestrated Full / minimal chain
# ---------------------------------------------------------------------------

from pyforge.marshal.core.chain_regen import (
    apply_orphans_hook,
    apply_preserved_code_statuses,
    preserve_code_status_hook,
    run_orchestrated_chain,
    snapshot_code_statuses,
    stage_hook,
)


def test_parse_status_markers_and_silent_exit():
    from pyforge.marshal.adapters.skill_invoke_harness import _parse_status

    assert _parse_status("STATUS: COMPLETE\nok", 0) == "complete"
    assert _parse_status("STATUS:BLOCKED", 0) == "blocked"
    assert _parse_status("STATUS: failed\n", 0) == "failed"
    assert _parse_status("no marker at all", 0) == "failed"
    assert _parse_status("", 1) == "failed"


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


# ---------------------------------------------------------------------------
# Story 86.5 — code-linkage verify counts only cites that name a real spec
# ---------------------------------------------------------------------------

from pyforge.marshal.core.chain_regen import verify_code_linkage

# Words that read like a spec id but cite nothing: the old count took each one
# as a missing spec (marshal: 42 of 87 on the live tree).
_PROSE = (
    "The spec-surface gate and spec-surface-check, the tracked-spec-only row,\n"
    "`spec-template.md`, `{spec-folder}/stories/`, `notes-spec-9-8.txt`,\n"
    "adversarial-review-pyforge-warden-spec-2026-07-15.md and `spec-2026-07-15.md`.\n"
)
# Cites that resolve: this project's Spec folder, a story spec by short id, by
# its stem, and by a stem whose slug has since changed; another project's Spec
# folder and story spec; a governance Spec; an archived Spec folder.
_RESOLVED = (
    "`spec-acme-kernel` CAP-1, spec-3-7, `spec-3-7-escalation-deferral.md`,\n"
    "spec-3-7-an-old-slug, spec-other-kernel, `spec-5-1-their-story.md`,\n"
    "spec-charter and spec-retired-kernel.\n"
)


def _seed_linkage(root: Path, epics: str) -> Path:
    planning = root / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    (planning / "specs" / "spec-acme-kernel").mkdir(parents=True)
    (planning / "specs" / "spec-3-7-escalation-deferral.md").write_text("# 3.7\n", encoding="utf-8")
    other = root / "_bmad-output" / "projects" / "other" / "planning-artifacts" / "specs"
    (other / "spec-other-kernel").mkdir(parents=True)
    (other / "spec-5-1-their-story.md").write_text("# 5.1\n", encoding="utf-8")
    (root / "docs" / "governance" / "spec-charter").mkdir(parents=True)
    archived = root / "archive" / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "specs"
    (archived / "spec-retired-kernel").mkdir(parents=True)
    (planning / "epics.md").write_text(f"# Epics\n\n{epics}", encoding="utf-8")
    return planning


def test_code_linkage_counts_only_story_spec_and_spec_folder_cites(tmp_path: Path):
    """DW-FU-21-2: prose words are no cites; every real cite resolves, so none is missing."""
    _seed_linkage(tmp_path, _PROSE + _RESOLVED)
    outcome = verify_code_linkage(tmp_path, "acme")
    assert outcome.status == "complete"
    assert outcome.detail == "read-only verify: 8 spec cite(s); 0 missing"


def test_code_linkage_names_each_missing_cite_and_stays_complete(tmp_path: Path):
    """DW-FU-21-2: a story-spec cite that resolves nowhere is named; the phase never blocks."""
    _seed_linkage(tmp_path, _PROSE + "Gone: `spec-4-2-gone.md`, spec-9-9; kept: spec-3-7.\n")
    outcome = verify_code_linkage(tmp_path, "acme")
    assert outcome.status == "complete"
    assert outcome.detail == "read-only verify: 3 spec cite(s); 2 missing: spec-4-2-gone, spec-9-9"


def test_code_linkage_counts_path_form_missing_cite(tmp_path: Path):
    """Story 86.8: ``specs/spec-…`` cites count as missing when the file exists nowhere."""
    _seed_linkage(
        tmp_path,
        _PROSE + "Full record: `specs/spec-a1-old-name-that-is-gone.md`.\n",
    )
    outcome = verify_code_linkage(tmp_path, "acme")
    assert outcome.status == "complete"
    assert "1 missing: spec-a1-old-name-that-is-gone" in outcome.detail


def test_code_linkage_prose_spec_template_is_not_a_cite(tmp_path: Path):
    """Story 86.8: bare ``spec-template`` prose is not counted (no ``specs/`` path prefix)."""
    _seed_linkage(tmp_path, "Follow spec-template when drafting a story spec.\n")
    outcome = verify_code_linkage(tmp_path, "acme")
    assert outcome.status == "complete"
    assert outcome.detail == "read-only verify: 0 spec cite(s); 0 missing"


def test_epic_orphan_scan_ignores_prose_and_reports_missing_and_orphaned_specs(tmp_path: Path):
    """The epic half of ``find_orphans`` reads cites the way the verify does."""
    planning = _seed_project(tmp_path, "acme")
    (planning / "specs" / "spec-orphan").mkdir()
    (planning / "specs" / "spec-orphan" / "SPEC.md").write_text(
        "---\nowner-dream: docs/dreams/missing-forever.md\n---\n# Orphan\n",
        encoding="utf-8",
    )
    (planning / "epics.md").write_text(
        "# Epics\n\n" + _PROSE + "Cites spec-demo, spec-orphan and spec-9-9.\n",
        encoding="utf-8",
    )
    epic_reasons = sorted(o.reason for o in find_orphans(tmp_path, "acme") if o.kind == "epic")
    assert epic_reasons == [
        "references missing spec spec-9-9",
        "references orphaned spec spec-orphan",
    ]
