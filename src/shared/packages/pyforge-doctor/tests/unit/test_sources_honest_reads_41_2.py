"""Story 41.2: the ledger and story-status sources degrade honestly.

One pin per deferred-work row the story closes. Each test fails if its fix is
reverted -- the row's own named failure mode is the assertion. Real tmp git
repositories, like ``test_sources_ledger.py`` / ``test_sources_frozen_path.py``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import frozen_path, ledger, marshal

_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _origin_main_at(repo: Path, sha: str) -> None:
    _git(repo, "update-ref", "refs/remotes/origin/main", sha)


def _ledger_path(repo: Path, project: str) -> Path:
    return repo / "_bmad-output" / "projects" / project / "planning-artifacts" / "sprint-status-ledger.yaml"


def _write_ledger(repo: Path, project: str, statuses: dict[str, str]) -> Path:
    path = _ledger_path(repo, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:", *(f"  {k}: {v}" for k, v in statuses.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _seeded(tmp_path: Path, ledgers: dict[str, dict[str, str]]) -> Path:
    repo = tmp_path / "repo"
    _init_repo(repo)
    for project, statuses in ledgers.items():
        _write_ledger(repo, project, statuses)
    _origin_main_at(repo, _commit_all(repo, "seed"))
    return repo


# --- DW-FU-6-4-4: a failed ls-tree is not "no ledgers" --------------------------


def test_a_failed_ls_tree_is_one_inventory_warn_not_an_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _seeded(tmp_path, {"doctor": {"1-1-foo": "done"}})
    _commit_all(repo, "head moves")
    real_git = ledger._git

    def _git_without_ls_tree(target: Path, *args: str) -> str | None:
        return None if "ls-tree" in args else real_git(target, *args)

    monkeypatch.setattr(ledger, "_git", _git_without_ls_tree)

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].check == "ledger-inventory"
    assert "ls-tree failed" in findings[0].message


def test_ledger_paths_distinguishes_a_failed_listing_from_an_empty_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _seeded(tmp_path, {})
    assert ledger._ledger_paths(repo, "HEAD") == []
    monkeypatch.setattr(ledger, "_git", lambda *_a, **_k: None)
    assert ledger._ledger_paths(repo, "HEAD") is None


# --- DW-FU-6-4-7: a UnicodeDecodeError out of run_git degrades, never raises ----


def test_both_git_wrappers_degrade_a_decode_error_to_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a: object, **_k: object) -> str:
        raise UnicodeDecodeError("utf-8", b"\xe9", 0, 1, "invalid continuation byte")

    monkeypatch.setattr(ledger, "run_git", _boom)
    monkeypatch.setattr(marshal, "run_git", _boom)

    assert ledger._git(tmp_path, "status") is None
    assert marshal._git(tmp_path, "status") is None


# --- DW-FU-6-4-23: a subdirectory target is never reported as a clean subtree ---


def test_a_subdirectory_target_warns_naming_both_paths(tmp_path: Path) -> None:
    repo = _seeded(tmp_path, {"doctor": {"1-1-foo": "done"}})
    sub = repo / "_bmad-output"
    _commit_all(repo, "head moves")

    findings = ledger.gather(sub, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert "not the repository root" in findings[0].message
    assert str(sub) in findings[0].message
    assert str(repo.resolve()) in findings[0].message
    assert findings[0].evidence["repo_top"] == str(repo.resolve())


# --- DW-FU-6-4-18: a quoted (non-ASCII) ledger path is still compared ----------


def test_a_non_ascii_project_ledger_is_listed_and_its_regression_is_found(tmp_path: Path) -> None:
    project = "pyforge-caf\u00e9"
    repo = _seeded(tmp_path, {project: {"1-1-foo": "done"}})
    expected = f"_bmad-output/projects/{project}/planning-artifacts/sprint-status-ledger.yaml"
    assert ledger._ledger_paths(repo, "HEAD") == [expected]

    _write_ledger(repo, project, {"1-1-foo": "in-progress"})
    _commit_all(repo, "regress")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert [(f.check, f.status) for f in findings] == [("done-key-regressed", DoctorStatus.FAIL)]
    assert findings[0].evidence["path"] == expected


# --- DW-FU-20-3: the changed-path listing is NUL-split --------------------------


def test_changed_paths_keeps_a_filename_containing_a_newline(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    base = _commit_all(repo, "seed")
    odd = "src/caf\u00e9\nx.py"
    (repo / "src").mkdir()
    (repo / odd).write_text("x = 1\n", encoding="utf-8")
    head = _commit_all(repo, "odd name")

    assert frozen_path._changed_paths(repo, base=base, head=head) == {odd}


# --- DW-FU-6-4-5: an unrelated new key with a matching tail cannot mask a deletion


def test_an_unrelated_new_key_with_the_same_tail_does_not_mask_a_deletion(tmp_path: Path) -> None:
    repo = _seeded(tmp_path, {"doctor": {"1-1-foo": "done", "1-2-bar": "done"}})
    # 1-1-foo is deleted; 7-1-foo is a coincidental NEW done key sharing the tail, and
    # a second done key with that tail was already there, so it is not a one-key rename.
    _write_ledger(repo, "doctor", {"1-2-bar": "done", "7-1-foo": "done", "8-1-foo": "done"})
    _commit_all(repo, "delete one, add two")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert [(f.check, f.status) for f in findings] == [("done-key-regressed", DoctorStatus.FAIL)]
    assert findings[0].evidence["keys"] == ["1-1-foo"]


# --- DW-FU-6-4-6: a done key that moved to another project's ledger reads as moved


def test_a_done_key_moved_to_another_projects_ledger_is_info_not_a_regression(tmp_path: Path) -> None:
    repo = _seeded(
        tmp_path,
        {"alpha": {"1-1-foo": "done", "1-2-bar": "done"}, "beta": {"2-1-baz": "done"}},
    )
    _write_ledger(repo, "alpha", {"1-2-bar": "done"})
    _write_ledger(repo, "beta", {"2-1-baz": "done", "1-1-foo": "done"})
    _commit_all(repo, "move 1-1-foo to beta")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert [(f.check, f.status) for f in findings] == [("ledger-key-moved", DoctorStatus.OK)]
    assert findings[0].evidence["keys"] == ["1-1-foo"]
    assert not any(f.status is DoctorStatus.FAIL for f in findings)


def test_a_key_deleted_while_a_sibling_ledger_already_held_it_is_still_a_regression(tmp_path: Path) -> None:
    repo = _seeded(tmp_path, {"alpha": {"1-1-foo": "done", "1-2-bar": "done"}, "beta": {"1-1-foo": "done"}})
    _write_ledger(repo, "alpha", {"1-2-bar": "done"})
    _commit_all(repo, "delete alpha 1-1-foo; beta always had its own")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert [(f.check, f.status) for f in findings] == [("done-key-regressed", DoctorStatus.FAIL)]


# --- DW-FU-6-4-24: an undecodable working-tree ledger is a WARN -----------------


def test_durability_warns_on_a_non_utf8_working_tree_ledger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    path = _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "seed")
    path.write_bytes(b"development_status:\n  1-1-f\xe9o: done\n")

    findings = marshal.gather(repo)

    unreadable = [f for f in findings if f.check == "ledger-unreadable"]
    assert len(unreadable) == 1
    assert unreadable[0].status is DoctorStatus.WARN
    assert not any(f.status is DoctorStatus.FAIL for f in findings)


# --- DW-FU-6-4-9: an alias-form key gets its hand-landed commit evaluated -------


def _alias_feed_repo(tmp_path: Path, subject: str | None) -> tuple[Path, Path]:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _git(target, "commit", "-q", "--allow-empty", "-m", "chore: initialize fixture")
    feed = target / "_bmad-output" / "projects" / "pyforge-atlas" / "implementation-artifacts" / "sprint-status.yaml"
    feed.parent.mkdir(parents=True)
    feed.write_text("development_status:\n  a1-scaffold-the-kedro: done\n", encoding="utf-8")
    if subject is not None:
        _git(target, "commit", "-q", "--allow-empty", "-m", subject)
    loop_root = tmp_path / "loop_root"
    state = loop_root / "pyforge-atlas" / ".bmad-loop" / "runs" / "run1" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps({"tasks": {"a1-scaffold-the-kedro": {"phase": "deferred", "commit_sha": None}}}),
        encoding="utf-8",
    )
    return target, loop_root


def test_an_alias_key_with_a_hand_landed_commit_is_not_a_false_green(tmp_path: Path) -> None:
    target, loop_root = _alias_feed_repo(tmp_path, "atlas: land a1 scaffold the kedro project")

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert [f.status for f in findings] == [DoctorStatus.OK]


def test_an_alias_key_with_no_landing_commit_is_still_a_false_green(tmp_path: Path) -> None:
    target, loop_root = _alias_feed_repo(tmp_path, "atlas: unrelated change to b1")

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert [f.status for f in findings] == [DoctorStatus.FAIL]
    assert findings[0].evidence["key"] == "a1-scaffold-the-kedro"


# --- DW-FU-6-4-10 / 6-4-19 / 6-4-25: which feed rows are audited ---------------


def _feed_repo(tmp_path: Path, feed_text: str) -> Path:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _git(target, "commit", "-q", "--allow-empty", "-m", "chore: initialize fixture")
    feed = target / "_bmad-output" / "projects" / "pyforge-warden" / "implementation-artifacts" / "sprint-status.yaml"
    feed.parent.mkdir(parents=True)
    feed.write_text(feed_text, encoding="utf-8")
    return target


def _audited(tmp_path: Path, feed_text: str) -> int:
    target = _feed_repo(tmp_path, feed_text)
    findings = marshal.gather_story_status(target, loop_root=tmp_path / "loop_root")
    assert [f.status for f in findings] == [DoctorStatus.OK]
    return int(findings[0].evidence["audited"])


def test_a_duplicate_done_line_is_audited_once(tmp_path: Path) -> None:
    assert _audited(tmp_path, "development_status:\n  1-1-foo: done\n  1-1-foo: done\n") == 1


def test_epic_rows_are_not_audited_or_counted_as_missing_records(tmp_path: Path) -> None:
    text = "development_status:\n  epic-1: done\n  epic-1-retrospective: done\n  1-1-foo: done\n"
    assert _audited(tmp_path, text) == 1


def test_every_feed_shape_the_parser_accepts_is_audited(tmp_path: Path) -> None:
    text = "development_status:\n  # note\n  1-1-foo: 'done'\n  1-2-bar: done  # landed\n  1-3-baz: backlog\n"
    assert _audited(tmp_path, text) == 2


# --- DW-FU-6-4-15: zero ledgers at both revisions is a WARN, not an OK ----------


def test_zero_ledgers_at_both_revisions_is_an_inventory_warn(tmp_path: Path) -> None:
    repo = _seeded(tmp_path, {})
    _commit_all(repo, "head moves")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert [(f.check, f.status) for f in findings] == [("ledger-inventory", DoctorStatus.WARN)]
    assert findings[0].evidence["ledgers"] == 0


# --- DW-FU-6-4-16 / 6-4-17: the shared status parser --------------------------


def test_the_parser_ignores_column_zero_comments_and_strips_quotes_and_inline_comments() -> None:
    text = "development_status:\n# column zero\n  1-1-foo: 'done'\n\n  1-2-bar: done  # landed\n  1-3-baz: backlog\n"
    expected = {"1-1-foo": "done", "1-2-bar": "done", "1-3-baz": "backlog"}
    assert ledger._parse_statuses(text) == expected
    assert marshal._parse_statuses(text) == expected


# --- DW-FU-6-4-21: the working-tree guard names its own check -------------------


def test_the_durability_guard_never_borrows_the_ledger_regression_check_name(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    path = _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "seed")
    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    assert path.exists()

    findings = marshal.gather(repo)

    assert {f.check for f in findings if f.status is DoctorStatus.FAIL} == {
        "marshal-durability-regression",
        "marshal-durability-total",
    }
    assert {f.source for f in findings} == {Source.MARSHAL_DURABILITY}
    assert not any("ledger-regression" in f.check for f in findings)


def test_the_durability_guard_outside_a_repository_names_its_own_check(tmp_path: Path) -> None:
    path = _write_ledger(tmp_path, "doctor", {"1-1-foo": "done"})
    assert path.exists()

    findings = marshal.gather(tmp_path)

    assert [(f.check, f.status) for f in findings] == [("marshal-durability-git", DoctorStatus.WARN)]


# --- DW-FU-6-9-4: --base/--head/--inv reach the gathers they scope --------------


def test_base_and_head_reach_ledger_gather(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def _stub(target: Path, *, base: str, head: str) -> tuple:
        seen.update(base=base, head=head)
        return ()

    monkeypatch.setattr(ledger, "gather", _stub)

    assert dispatch.main(["ledger-regression", "--base", "abc123", "--head", "def456"]) == 0
    assert seen == {"base": "abc123", "head": "def456"}


def test_base_on_a_source_that_cannot_use_it_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        dispatch.main(["story-status", "--base", "main"])
    assert exc.value.code == 2
    assert "--base" in capsys.readouterr().err


@pytest.mark.parametrize("source", ["dream-chain", "chain-completeness"])
def test_inv_filters_the_findings_of_the_two_chain_sources(
    source: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pyforge.doctor.models import Finding

    def _finding(inv: str) -> Finding:
        return Finding(
            source=Source.DREAM_CHAIN,
            check=f"check-{inv}",
            status=DoctorStatus.OK,
            message=inv,
            evidence={"inv": inv},
        )

    monkeypatch.setitem(dispatch.DISPATCH, source, lambda target: (_finding("INV-0"), _finding("INV-1")))

    assert dispatch.main([source, "--inv", "INV-1", "--json"]) == 0
    assert [f["check"] for f in json.loads(capsys.readouterr().out)] == ["check-INV-1"]


def test_inv_on_another_source_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        dispatch.main(["story-status", "--inv", "INV-1"])
    assert exc.value.code == 2
    assert "--inv" in capsys.readouterr().err

