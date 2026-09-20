"""Unit tests for ``pyforge.doctor.sources.frozen_path`` (Story 20.3, Epic
20) -- covers every row of the spec's I/O & Edge-Case Matrix. Every
``gather()``-level test drives a REAL tmp git repository (mirrors
``test_sources_ledger.py``'s own convention: never a mocked subprocess
call), including the same ``origin/main`` local-branch trick (``git branch
origin/main <sha>`` resolves via ``git rev-parse``/``git diff`` with no real
remote needed).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
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


def _branch_at(repo: Path, name: str, sha: str) -> None:
    _git(repo, "branch", name, sha)


def _write_manifest(repo: Path, text: str, *, name: str = "manifest.yaml") -> Path:
    path = repo / "docs" / "foundry" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


_ONE_REBUILDING_CAPABILITY = (
    "capabilities:\n"
    "  - capability: mason-recipe-writer\n"
    "    state: rebuilding\n"
    "    frozen_paths:\n"
    "      - src/shared/packages/pyforge-mason\n"
)
_FROZEN_PATH_TOUCHED = "src/shared/packages/pyforge-mason/recipe_writer.py"


# --- _find_manifest ----------------------------------------------------------


def test_find_manifest_none_when_docs_foundry_absent(tmp_path: Path) -> None:
    assert frozen_path._find_manifest(tmp_path) is None


def test_find_manifest_finds_yaml(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "capabilities: []\n", name="manifest.yaml")
    assert frozen_path._find_manifest(tmp_path) == path


def test_find_manifest_finds_yml(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "capabilities: []\n", name="manifest.yml")
    assert frozen_path._find_manifest(tmp_path) == path


def test_find_manifest_finds_json(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, '{"capabilities": []}\n', name="manifest.json")
    assert frozen_path._find_manifest(tmp_path) == path


def test_find_manifest_prefers_yaml_over_yml_and_json(tmp_path: Path) -> None:
    yaml_path = _write_manifest(tmp_path, "capabilities: []\n", name="manifest.yaml")
    _write_manifest(tmp_path, "capabilities: []\n", name="manifest.yml")
    _write_manifest(tmp_path, '{"capabilities": []}\n', name="manifest.json")
    assert frozen_path._find_manifest(tmp_path) == yaml_path


def test_find_manifest_prefers_yml_over_json(tmp_path: Path) -> None:
    yml_path = _write_manifest(tmp_path, "capabilities: []\n", name="manifest.yml")
    _write_manifest(tmp_path, '{"capabilities": []}\n', name="manifest.json")
    assert frozen_path._find_manifest(tmp_path) == yml_path


# --- _load_capabilities -------------------------------------------------------


def test_load_capabilities_valid_yaml(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, _ONE_REBUILDING_CAPABILITY)
    assert frozen_path._load_capabilities(path) == [
        {
            "capability": "mason-recipe-writer",
            "state": "rebuilding",
            "frozen_paths": ["src/shared/packages/pyforge-mason"],
        }
    ]


def test_load_capabilities_valid_json(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        '{"capabilities": [{"capability": "x", "state": "planned", "frozen_paths": []}]}\n',
        name="manifest.json",
    )
    assert frozen_path._load_capabilities(path) == [{"capability": "x", "state": "planned", "frozen_paths": []}]


def test_load_capabilities_malformed_yaml_raises(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "capabilities: [this is not: valid: yaml\n")
    with pytest.raises(Exception):
        frozen_path._load_capabilities(path)


def test_load_capabilities_malformed_json_raises(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "{not valid json", name="manifest.json")
    with pytest.raises(Exception):
        frozen_path._load_capabilities(path)


def test_load_capabilities_missing_capabilities_key_raises(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "some_other_key: true\n")
    with pytest.raises(ValueError):
        frozen_path._load_capabilities(path)


def test_load_capabilities_non_list_capabilities_raises(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "capabilities: not-a-list\n")
    with pytest.raises(ValueError):
        frozen_path._load_capabilities(path)


def test_load_capabilities_non_mapping_document_raises(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(ValueError):
        frozen_path._load_capabilities(path)


# --- _is_frozen ----------------------------------------------------------------


def test_is_frozen_exact_match() -> None:
    assert frozen_path._is_frozen("src/foo", "src/foo") is True


def test_is_frozen_proper_subpath_match() -> None:
    assert frozen_path._is_frozen("src/foo/bar.py", "src/foo") is True


def test_is_frozen_false_match_guard_on_lookalike_sibling() -> None:
    assert frozen_path._is_frozen("src/foobar/x.py", "src/foo") is False


def test_is_frozen_trailing_slash_in_prefix_normalized() -> None:
    assert frozen_path._is_frozen("src/foo/bar.py", "src/foo/") is True
    assert frozen_path._is_frozen("src/foo", "src/foo/") is True


def test_is_frozen_unrelated_path_is_false() -> None:
    assert frozen_path._is_frozen("docs/readme.md", "src/foo") is False


# --- gather() -- I/O & Edge-Case Matrix, real git-repo fixtures ---------------


def test_no_ledger_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("no capability ledger here\n", encoding="utf-8")
    _commit_all(repo, "seed, no ledger")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.FROZEN_PATH_CHANGED
    assert finding.check == "frozen-path-changed"
    assert finding.status is DoctorStatus.OK
    assert finding.message == "no capability ledger found (pre-cutover)"


def test_ledger_present_nothing_frozen_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(
        repo,
        "capabilities:\n"
        "  - capability: alpha\n"
        "    state: planned\n"
        "    frozen_paths: []\n"
        "  - capability: beta\n"
        "    state: verified-in-foundry\n"
        "    frozen_paths: []\n"
        "  - capability: gamma\n"
        "    state: cut\n"
        "    frozen_paths: []\n",
    )
    base_sha = _commit_all(repo, "seed ledger, nothing frozen")
    _branch_at(repo, "origin/main", base_sha)

    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "unrelated change")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK
    assert finding.check == "frozen-path-changed"


def test_frozen_path_violation_reports_fail_naming_capability_and_path(
    tmp_path: Path,
) -> None:
    """The exact fixture the AC names: one `rebuilding` capability frozen
    over `src/shared/packages/pyforge-mason`, a HEAD commit changing
    `src/shared/packages/pyforge-mason/recipe_writer.py`."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(repo, _ONE_REBUILDING_CAPABILITY)
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    changed = repo / _FROZEN_PATH_TOUCHED
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("# touched during rebuild\n", encoding="utf-8")
    _commit_all(repo, "touch a frozen path")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.FROZEN_PATH_CHANGED
    assert finding.check == "frozen-path-changed"
    assert finding.status is DoctorStatus.FAIL
    assert "mason-recipe-writer" in finding.message
    assert _FROZEN_PATH_TOUCHED in finding.message
    assert finding.evidence["capability"] == "mason-recipe-writer"
    assert finding.evidence["path"] == _FROZEN_PATH_TOUCHED


def test_frozen_capability_no_matching_change_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(repo, _ONE_REBUILDING_CAPABILITY)
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "unrelated change")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK
    assert finding.check == "frozen-path-changed"


def test_multiple_simultaneous_violations_report_one_fail_per_pair(
    tmp_path: Path,
) -> None:
    """Two frozen capabilities, each hit once in the same diff -- gather()
    must return one FAIL Finding per (capability, path) pair, not collapse
    them into one."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(
        repo,
        "capabilities:\n"
        "  - capability: mason-recipe-writer\n"
        "    state: rebuilding\n"
        "    frozen_paths:\n"
        "      - src/shared/packages/pyforge-mason\n"
        "  - capability: warden-engine\n"
        "    state: moving\n"
        "    frozen_paths:\n"
        "      - src/shared/packages/pyforge-warden\n",
    )
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    mason_path = repo / _FROZEN_PATH_TOUCHED
    mason_path.parent.mkdir(parents=True, exist_ok=True)
    mason_path.write_text("# touched\n", encoding="utf-8")
    warden_touched = "src/shared/packages/pyforge-warden/engine.py"
    warden_path = repo / warden_touched
    warden_path.parent.mkdir(parents=True, exist_ok=True)
    warden_path.write_text("# touched\n", encoding="utf-8")
    _commit_all(repo, "touch two frozen paths")

    findings = frozen_path.gather(repo)

    assert len(findings) == 2
    assert all(f.status is DoctorStatus.FAIL for f in findings)
    pairs = {(f.evidence["capability"], f.evidence["path"]) for f in findings}
    assert pairs == {
        ("mason-recipe-writer", _FROZEN_PATH_TOUCHED),
        ("warden-engine", warden_touched),
    }


def test_gather_skips_a_stray_non_dict_capability_entry(tmp_path: Path) -> None:
    """A `capabilities` list containing a bare string alongside a normal
    dict entry must not crash `_gather` -- the non-dict entry is simply
    skipped, the real entry still freezes normally."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(
        repo,
        "capabilities:\n"
        "  - a stray string, not a mapping\n"
        "  - capability: mason-recipe-writer\n"
        "    state: rebuilding\n"
        "    frozen_paths:\n"
        "      - src/shared/packages/pyforge-mason\n",
    )
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    changed = repo / _FROZEN_PATH_TOUCHED
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("# touched\n", encoding="utf-8")
    _commit_all(repo, "touch a frozen path")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["capability"] == "mason-recipe-writer"


def test_gather_skips_a_non_string_frozen_paths_entry(tmp_path: Path) -> None:
    """A `frozen_paths` list containing `null` alongside a normal string
    entry must not crash `_gather` -- the non-string entry is simply
    skipped, the real string entry still freezes normally."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(
        repo,
        "capabilities:\n"
        "  - capability: mason-recipe-writer\n"
        "    state: rebuilding\n"
        "    frozen_paths:\n"
        "      - null\n"
        "      - src/shared/packages/pyforge-mason\n",
    )
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    changed = repo / _FROZEN_PATH_TOUCHED
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("# touched\n", encoding="utf-8")
    _commit_all(repo, "touch a frozen path")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["path"] == _FROZEN_PATH_TOUCHED


def test_moving_state_also_freezes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(
        repo,
        "capabilities:\n"
        "  - capability: mason-recipe-writer\n"
        "    state: moving\n"
        "    frozen_paths:\n"
        "      - src/shared/packages/pyforge-mason\n",
    )
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    changed = repo / _FROZEN_PATH_TOUCHED
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("# touched during move\n", encoding="utf-8")
    _commit_all(repo, "touch a frozen path")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


def test_malformed_ledger_reports_one_generic_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(repo, "capabilities: [this is not: valid: yaml\n")
    _commit_all(repo, "seed malformed ledger")

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.FROZEN_PATH_CHANGED
    assert finding.check == "frozen-path-changed"
    assert finding.status is DoctorStatus.WARN


def test_unresolvable_git_ref_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_manifest(repo, _ONE_REBUILDING_CAPABILITY)
    _commit_all(repo, "seed ledger")
    # deliberately never create an "origin/main" branch/ref

    findings = frozen_path.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.FROZEN_PATH_CHANGED
    assert finding.check == "frozen-path-changed"
    assert finding.status is DoctorStatus.WARN
    assert "could not diff" in finding.message


def test_gather_never_raises_on_a_non_repository_target(tmp_path: Path) -> None:
    """A target that is not a git repository at all is still degraded to a
    WARN by _changed_paths's own git failure path -- exercised here via a
    ledger that DOES have a frozen capability (so gather reaches the git
    diff step) inside a directory with no .git at all."""
    non_repo = tmp_path / "not-a-repo"
    _write_manifest(non_repo, _ONE_REBUILDING_CAPABILITY)

    findings = frozen_path.gather(non_repo)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
