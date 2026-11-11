"""Unit tests for ``pyforge.doctor.sources.frozen_path`` (Story 56.1,
spec-pyforge-doctor:CAP-94; first built by Story 20.3).

Every ``gather()``-level test drives a REAL tmp git repository (mirrors
``test_sources_ledger.py``'s own convention: never a mocked subprocess call);
``origin/main`` is a real remote-tracking ref (``git update-ref
refs/remotes/origin/main <sha>``), no remote needed -- never a local branch
named ``origin/main``, the shadow Story 31.1 made the source read past.

Every ledger is built under ``tmp_path`` with path joins, and every frozen path
is an invented one: the module reads nothing of the repository it lives in,
so it runs in the package half of the doctor suite and carries no mark.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import frozen_path

# A contributor's own git config must not decide whether this suite passes --
# same rationale, and same autouse-fixture-on-os.environ shape, as
# test_sources_ledger.py's own `_isolate_git_env` (`cli_bridge.run_git` does
# `env = dict(os.environ)` at call time, so a fixture-local env dict would
# never reach it).
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
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
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
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _origin_main_at(repo: Path, sha: str) -> None:
    """The remote-tracking ref `refs/remotes/origin/main` at `sha` (Story 31.1: never a local
    branch named `origin/main`, the very shadow the sources now read past)."""
    _git(repo, "update-ref", "refs/remotes/origin/main", sha)


def _ledger_file(repo: Path) -> Path:
    return repo / "docs" / "foundry" / "capability-ledger.yaml"


def _write_ledger(repo: Path, text: str) -> Path:
    path = _ledger_file(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _touch(repo: Path, rel: str, text: str = "# touched\n") -> None:
    path = repo.joinpath(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo_with_change(tmp_path: Path, ledger_text: str, changed: str) -> Path:
    """A repo whose `origin/main` holds `ledger_text` and whose HEAD adds one commit changing `changed`."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, ledger_text)
    _origin_main_at(repo, _commit_all(repo, "seed ledger"))
    _touch(repo, changed)
    _commit_all(repo, "change one path")
    return repo


def _only(findings: tuple[Finding, ...]) -> Finding:
    assert len(findings) == 1, findings
    finding = findings[0]
    assert finding.source is Source.FROZEN_PATH_CHANGED
    return finding


def _assert_unevaluable(findings: tuple[Finding, ...]) -> Finding:
    finding = _only(findings)
    assert finding.status is DoctorStatus.WARN
    assert finding.check == "frozen-path-changed-unevaluable"
    assert finding.evidence["unevaluable"] is True
    return finding


# Invented paths, never a tracked one.
_FROZEN_DIR = "kernel/leaf"
_UNDER_FROZEN = "kernel/leaf/mod.py"
_ROW_ID = "pyforge-testing-charter:CAP-4"


def _row(state: str, *, row_id: str = _ROW_ID, frozen: str | None = _FROZEN_DIR) -> str:
    text = (
        f"  - id: {row_id}\n"
        "    spec: pyforge-testing-charter\n"
        "    station: pyforge-marshal\n"
        "    heading: Coverage gate enforced, not just measured\n"
        "    mode: rebuild\n"
        f"    state: {state}\n"
    )
    if frozen is not None:
        text += f"    frozen_paths:\n      - {frozen}\n"
    return text


def _ledger(*rows: str, header: str = "schema: pyforge.capability-ledger/v1\n") -> str:
    return header + "capabilities:\n" + "".join(rows)


# The v1 header of modes.md § Schema v1 (steward Story 120.2): every key, in order.
_V1_HEADER = (
    "schema: pyforge.capability-ledger/v1\n"
    "generated_by: pyforge steward cutover plan\n"
    'updated: "2026-11-10"\n'
    'source_sha: "0000000000000000000000000000000000000000"\n'
    "extract: planning/specs/spec-foundry-capability-ledger/extract.md\n"
    "modes: [rebuild, retire, A-only, B-only, pending]\n"
    "states: [planned, rebuilding, verified-in-foundry, cut]\n"
    "frozen_states: [rebuilding]\n"
)


# --- _is_frozen ------------------------------------------------------------------


def test_is_frozen_exact_match() -> None:
    assert frozen_path._is_frozen("src/foo", "src/foo") is True


def test_is_frozen_proper_subpath_match() -> None:
    assert frozen_path._is_frozen("src/foo/bar.py", "src/foo") is True


def test_is_frozen_false_match_guard_on_lookalike_sibling() -> None:
    assert frozen_path._is_frozen("src/foobar/x.py", "src/foo") is False


def test_is_frozen_trailing_slash_and_leading_dot_slash_normalized() -> None:
    assert frozen_path._is_frozen("src/foo/bar.py", "src/foo/") is True
    assert frozen_path._is_frozen("src/foo", "src/foo/") is True
    assert frozen_path._is_frozen("src/foo/bar.py", "./src/foo") is True


def test_is_frozen_unrelated_path_is_false() -> None:
    assert frozen_path._is_frozen("docs/readme.md", "src/foo") is False


# --- the subject: the capability ledger, and nothing else -------------------------


def test_ledger_path_is_the_capability_ledger(tmp_path: Path) -> None:
    assert frozen_path._ledger_path(tmp_path) == tmp_path / "docs" / "foundry" / "capability-ledger.yaml"


def test_a_retired_manifest_file_is_never_read(tmp_path: Path) -> None:
    """Pointed back at the retired manifest, the source would FAIL here; it reads only the ledger."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    manifest = repo / "docs" / "foundry" / "manifest.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(_ledger(_row("rebuilding")), encoding="utf-8")
    _origin_main_at(repo, _commit_all(repo, "seed a manifest, no ledger"))
    _touch(repo, _UNDER_FROZEN)
    _commit_all(repo, "touch the manifest's frozen path")

    _assert_unevaluable(frozen_path.gather(repo))


# --- AC4: each rule has its case --------------------------------------------------


def test_rebuilding_row_with_changed_path_fails_naming_row_and_path(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("rebuilding")), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.check == "frozen-path-changed"
    assert _ROW_ID in finding.message and _UNDER_FROZEN in finding.message
    assert finding.evidence["id"] == _ROW_ID
    assert finding.evidence["path"] == _UNDER_FROZEN


def test_rebuilding_row_without_paths_fails_guards_nothing(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("rebuilding", frozen=None)), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert "guards nothing" in finding.message
    assert finding.evidence["id"] == _ROW_ID


def test_planned_row_reports_zero_frozen_of_one_rows(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("planned")), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "0 frozen of 1 rows" in finding.message
    assert finding.evidence["frozen"] == 0


def test_no_ledger_is_unevaluable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _touch(repo, "README.md", "no capability ledger here\n")
    _origin_main_at(repo, _commit_all(repo, "seed, no ledger"))

    finding = _assert_unevaluable(frozen_path.gather(repo))
    assert "missing" in finding.message


def test_unparseable_ledger_is_unevaluable(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, "capabilities: [this is not: valid: yaml\n", _UNDER_FROZEN)

    _assert_unevaluable(frozen_path.gather(repo))


def test_origin_main_unresolvable_is_unevaluable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, _ledger(_row("rebuilding")))
    _commit_all(repo, "seed ledger")
    # deliberately never create refs/remotes/origin/main

    finding = _assert_unevaluable(frozen_path.gather(repo))
    assert "could not diff origin/main..HEAD" in finding.message


def test_v1_fixture_header_parses_with_only_the_ok(tmp_path: Path) -> None:
    """The full v1 header (schema, generated_by, updated, source_sha, extract, modes, states,
    frozen_states), one planned row and the `cells:` list: one OK and nothing else."""
    text = (
        _V1_HEADER
        + "capabilities:\n"
        + _row("planned", frozen=None)
        + "cells:\n"
        + "  - id: cell:conda-forge-expert/skill\n"
        + "    path: skills/cfe/\n"
        + "    mode: A-only\n"
        + '    expiry: "mason:39.2"\n'
    )
    repo = _repo_with_change(tmp_path, text, _UNDER_FROZEN)

    findings = frozen_path.gather(repo)

    assert [(f.status, f.message) for f in findings] == [
        (DoctorStatus.OK, "0 frozen of 1 rows in docs/foundry/capability-ledger.yaml")
    ]


# --- the frozen set is the constant {rebuilding} ------------------------------------


def test_header_frozen_states_is_never_read(tmp_path: Path) -> None:
    header = _V1_HEADER.replace("frozen_states: [rebuilding]", "frozen_states: [planned]")
    repo = _repo_with_change(tmp_path, _ledger(_row("planned"), header=header), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "0 frozen of 1 rows" in finding.message


def test_the_moving_state_freezes_nothing(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("moving")), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "0 frozen of 1 rows" in finding.message


@pytest.mark.parametrize("state", ["planned", "verified-in-foundry", "cut"])
def test_every_other_state_freezes_nothing(tmp_path: Path, state: str) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row(state)), _UNDER_FROZEN)

    assert _only(frozen_path.gather(repo)).status is DoctorStatus.OK


def test_a_cells_entry_is_never_frozen(tmp_path: Path) -> None:
    text = _ledger(_row("planned")) + (
        f"cells:\n  - id: cell:conda-forge-expert/scripts\n    state: rebuilding\n    frozen_paths:\n      - {_FROZEN_DIR}\n"
    )
    repo = _repo_with_change(tmp_path, text, _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "0 frozen of 1 rows" in finding.message


def test_a_v0_ledger_without_state_reads_zero_frozen(tmp_path: Path) -> None:
    """Today's v0 file: rows carry no `state`, so nothing is frozen until steward Story 121.3."""
    text = (
        "schema: pyforge.capability-ledger/v0\n"
        "never_move: true\n"
        "capabilities:\n"
        "  - id: alpha:CAP-1\n    mode: rebuild\n"
        "  - id: alpha:CAP-2\n    mode: retire\n"
    )
    repo = _repo_with_change(tmp_path, text, _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert finding.message == "0 frozen of 2 rows in docs/foundry/capability-ledger.yaml"


# --- the frozen rows ------------------------------------------------------------------


def test_a_frozen_row_left_untouched_reports_ok(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("rebuilding")), "unrelated.txt")

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "1 frozen of 1 rows" in finding.message


def test_a_lookalike_sibling_change_is_not_under_the_frozen_path(tmp_path: Path) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("rebuilding")), "kernel/leafy/mod.py")

    assert _only(frozen_path.gather(repo)).status is DoctorStatus.OK


def test_one_fail_per_row_and_path_pair(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(
        repo,
        _ledger(_row("rebuilding"), _row("rebuilding", row_id="alpha:CAP-2", frozen="kernel/stem")),
    )
    _origin_main_at(repo, _commit_all(repo, "seed ledger"))
    _touch(repo, _UNDER_FROZEN)
    _touch(repo, "kernel/stem/engine.py")
    _commit_all(repo, "touch two frozen paths")

    findings = frozen_path.gather(repo)

    assert all(f.status is DoctorStatus.FAIL for f in findings)
    assert {(f.evidence["id"], f.evidence["path"]) for f in findings} == {
        (_ROW_ID, _UNDER_FROZEN),
        ("alpha:CAP-2", "kernel/stem/engine.py"),
    }


def test_a_guards_nothing_row_and_a_violation_are_both_named(tmp_path: Path) -> None:
    ledger = _ledger(_row("rebuilding"), _row("rebuilding", row_id="alpha:CAP-2", frozen=None))
    repo = _repo_with_change(tmp_path, ledger, _UNDER_FROZEN)

    findings = frozen_path.gather(repo)

    assert len(findings) == 2
    assert {(f.status, f.evidence["id"]) for f in findings} == {
        (DoctorStatus.FAIL, _ROW_ID),
        (DoctorStatus.FAIL, "alpha:CAP-2"),
    }
    assert any("guards nothing" in f.message for f in findings)


def test_frozen_paths_holding_no_usable_string_guards_nothing(tmp_path: Path) -> None:
    row = _row("rebuilding", frozen=None) + "    frozen_paths:\n      - null\n      - ''\n"
    repo = _repo_with_change(tmp_path, _ledger(row), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert "guards nothing" in finding.message


def test_a_non_string_frozen_paths_entry_is_skipped(tmp_path: Path) -> None:
    row = _row("rebuilding", frozen=None) + f"    frozen_paths:\n      - null\n      - {_FROZEN_DIR}\n"
    repo = _repo_with_change(tmp_path, _ledger(row), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["path"] == _UNDER_FROZEN


def test_a_stray_non_mapping_row_is_counted_and_skipped(tmp_path: Path) -> None:
    stray = "  - a stray string, not a mapping\n"
    repo = _repo_with_change(tmp_path, _ledger(stray, _row("rebuilding")), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["id"] == _ROW_ID


def test_an_unhashable_state_freezes_nothing(tmp_path: Path) -> None:
    row = _row("planned").replace("state: planned", "state: [rebuilding]")
    repo = _repo_with_change(tmp_path, _ledger(row), _UNDER_FROZEN)

    finding = _only(frozen_path.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "0 frozen of 1 rows" in finding.message


# --- cannot-evaluate (spec-pyforge-doctor:AD-15) ------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "some_other_key: true\n",
        "capabilities: not-a-list\n",
        "- just\n- a\n- list\n",
        "",
    ],
    ids=["no-capabilities-key", "capabilities-not-a-list", "not-a-mapping", "empty-file"],
)
def test_a_ledger_without_a_capabilities_list_is_unevaluable(tmp_path: Path, text: str) -> None:
    repo = _repo_with_change(tmp_path, text, _UNDER_FROZEN)

    _assert_unevaluable(frozen_path.gather(repo))


def test_a_non_utf8_ledger_is_unevaluable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    path = _ledger_file(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"capabilities:\n  - id: \xff\xfe\n")

    _assert_unevaluable(frozen_path.gather(repo))


def test_a_non_repository_target_is_unevaluable(tmp_path: Path) -> None:
    target = tmp_path / "not-a-repo"
    _write_ledger(target, _ledger(_row("rebuilding")))

    _assert_unevaluable(frozen_path.gather(target))


def test_an_unexpected_error_still_meets_the_degrade_net(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("rebuilding")), _UNDER_FROZEN)

    def _boom(*_args: object, **_kwargs: object) -> set[str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(frozen_path, "_changed_paths", _boom)

    finding = _only(frozen_path.gather(repo))
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence == {"exception": "RuntimeError"}


# --- the dispatcher: python -m pyforge.doctor.sources frozen-path-changed ------------------


def test_the_dispatcher_exits_2_naming_the_row_and_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("rebuilding")), _UNDER_FROZEN)
    monkeypatch.chdir(repo)

    assert dispatch.main(["frozen-path-changed"]) == 2
    out = capsys.readouterr().out
    assert _ROW_ID in out and _UNDER_FROZEN in out


def test_the_dispatcher_exits_0_for_a_planned_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo_with_change(tmp_path, _ledger(_row("planned")), _UNDER_FROZEN)
    monkeypatch.chdir(repo)

    assert dispatch.main(["frozen-path-changed"]) == 0
    assert "0 frozen of 1 rows" in capsys.readouterr().out


def test_the_dispatcher_exits_0_on_a_cannot_evaluate_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    monkeypatch.chdir(repo)

    assert dispatch.main(["frozen-path-changed"]) == 0
    assert "frozen-path-changed-unevaluable: warn" in capsys.readouterr().out
