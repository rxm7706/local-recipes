"""Unit tests for scripts/mason_cfe_surface_check.py (Story 5.2, FR-45/AD-15) --
covers every row of the spec's I/O & Edge-Case Matrix against REAL tmp git
repositories, mirroring pyforge-doctor's ``test_sources_ledger.py`` fixture
pattern (``_isolate_git_env``, ``_git``, ``_init_repo``, ``_commit_all``) and
reaching the module the same way ``test_detectors_doctor_sources.py`` reaches
``detectors.py`` (``scripts/`` has no ``__init__.py``).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import mason_cfe_surface_check as m  # noqa: E402  (sys.path must be set up first)

MASON_PATH = m.MASON_PATH
CFE_CHANGELOG = m.CFE_CHANGELOG

# A contributor's own git config must not decide whether this suite passes --
# see src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py for
# the full rationale (13 tests failed without this scrub, incl. a FAIL/WARN
# regression).
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
    # --initial-branch pins the default branch regardless of the contributor's
    # own init.defaultBranch; mason_commits() resolves HEAD, so the branch
    # name itself is not load-bearing, but a deterministic one keeps
    # failures readable.
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "mason-cfe-test@example.com")
    _git(repo, "config", "user.name", "Mason CFE Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _write(repo: Path, rel: str, content: str = "x") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


# --- I/O & Edge-Case Matrix ------------------------------------------------


def test_clean_history_zero_findings(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: add mason foo")
    _write(tmp_path, f"{MASON_PATH}/bar.py", "two")
    _commit_all(tmp_path, "feat: add mason bar")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    assert len(shas) == 2

    findings = m.scan(tmp_path, shas)
    assert findings == []


def test_unsanctioned_cfe_touch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")

    _write(tmp_path, f"{MASON_PATH}/foo.py", "two")
    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "edited")
    sha = _commit_all(tmp_path, "feat: sneaky mason+cfe change")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    findings = m.scan(tmp_path, shas)

    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "unsanctioned-cfe-touch"
    assert f["ref"] == sha[:10]
    assert ".claude/skills/conda-forge-expert/SKILL.md" in f["detail"]


def test_unsanctioned_cfe_touch_exact_server_file(tmp_path: Path) -> None:
    """CFE_SURFACE_FILES (exact match, not a prefix) -- the
    .claude/tools/conda_forge_server.py branch of is_cfe_path."""
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")

    _write(tmp_path, f"{MASON_PATH}/foo.py", "two")
    _write(tmp_path, ".claude/tools/conda_forge_server.py", "edited")
    sha = _commit_all(tmp_path, "feat: sneaky server-tool change")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    findings = m.scan(tmp_path, shas)

    assert len(findings) == 1
    assert findings[0]["kind"] == "unsanctioned-cfe-touch"
    assert findings[0]["ref"] == sha[:10]


def test_borrowed_retro_subject_without_changelog_still_unsanctioned(tmp_path: Path) -> None:
    """Subject alone never launders a CFE touch."""
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")

    _write(tmp_path, f"{MASON_PATH}/foo.py", "two")
    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "edited, no changelog move")
    sha = _commit_all(tmp_path, "retro: borrows the subject but not the changelog")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    findings = m.scan(tmp_path, shas)

    assert len(findings) == 1
    assert findings[0]["kind"] == "unsanctioned-cfe-touch"
    assert findings[0]["ref"] == sha[:10]


def test_sanctioned_single_retro_commit_zero_findings(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")

    _write(tmp_path, f"{MASON_PATH}/foo.py", "two")
    _write(tmp_path, CFE_CHANGELOG, "## new version entry")
    _commit_all(tmp_path, "retro: close out the mason-cli effort")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    findings = m.scan(tmp_path, shas)
    assert findings == []


def test_exception_reused_two_qualifying_commits(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")

    _write(tmp_path, f"{MASON_PATH}/foo.py", "two")
    _write(tmp_path, CFE_CHANGELOG, "## first retro entry")
    sha1 = _commit_all(tmp_path, "retro: first closing retro")

    _write(tmp_path, f"{MASON_PATH}/foo.py", "three")
    _write(tmp_path, CFE_CHANGELOG, "## second retro entry")
    sha2 = _commit_all(tmp_path, "retro: second closing retro")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    findings = m.scan(tmp_path, shas)

    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "exception-reused"
    assert sha1[:10] in f["ref"]
    assert sha2[:10] in f["ref"]


def test_multi_parent_merge_falls_back_to_first_parent_diff(tmp_path: Path) -> None:
    """A real 2-parent merge that resolves a conflict on the mason path and
    slips in a CFE-surface change during resolution must not be silently
    waved through just because plain `diff-tree` (no -m/-c) reports nothing
    for merge commits (Design Notes)."""
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "base")
    _commit_all(tmp_path, "feat: base mason commit")

    _git(tmp_path, "checkout", "-q", "-b", "branchA")
    _write(tmp_path, f"{MASON_PATH}/foo.py", "branchA change")
    _commit_all(tmp_path, "feat: branchA change")

    _git(tmp_path, "checkout", "-q", "main")
    _write(tmp_path, f"{MASON_PATH}/foo.py", "main change")
    _commit_all(tmp_path, "feat: main change")

    # Deliberately conflicting merge -- non-zero rc is expected here, the
    # conflict is resolved by hand below.
    subprocess.run(
        ["git", "merge", "branchA", "-m", "merge: conflict"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    _write(tmp_path, f"{MASON_PATH}/foo.py", "resolved")
    _write(tmp_path, ".claude/skills/conda-forge-expert/sneaky.txt",
           "slipped in during conflict resolution")
    merge_sha = _commit_all(tmp_path, "merge: conflict")

    shas = m.mason_commits(tmp_path)
    assert shas is not None
    assert merge_sha in shas

    # Confirm the fixture actually exercises the fallback path: plain
    # diff-tree reports nothing for this merge commit.
    assert m.git(tmp_path, "diff-tree", "--no-commit-id", "--name-only", "-r",
                 "--root", merge_sha) == ""

    findings = m.scan(tmp_path, shas)
    matching = [f for f in findings if f["ref"] == merge_sha[:10]]
    assert len(matching) == 1
    assert matching[0]["kind"] == "unsanctioned-cfe-touch"


def test_mason_commits_returns_none_when_git_log_cannot_run(tmp_path: Path) -> None:
    # tmp_path is not a git repository at all -- the exit-2 case.
    assert m.mason_commits(tmp_path) is None


def test_live_repo_today_is_clean() -> None:
    """Confirms the current state of the real repository is green (per the
    spec's Verification section) -- not a synthetic fixture."""
    shas = m.mason_commits(REPO_ROOT)
    assert shas is not None
    assert len(shas) > 0
    findings = m.scan(REPO_ROOT, shas)
    assert findings == []


# --- main() / CLI wiring ---------------------------------------------------


def test_main_exit_0_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                            capsys: pytest.CaptureFixture[str]) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["mason_cfe_surface_check.py"])
    rc = m.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "clean" in out


def test_main_exit_1_findings_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, f"{MASON_PATH}/foo.py", "one")
    _commit_all(tmp_path, "feat: mason baseline")
    _write(tmp_path, f"{MASON_PATH}/foo.py", "two")
    _write(tmp_path, ".claude/tools/conda_forge_server.py", "edited")
    sha = _commit_all(tmp_path, "feat: sneaky change")

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["mason_cfe_surface_check.py", "--json"])
    rc = m.main()
    out = capsys.readouterr().out

    assert rc == 1
    payload = json.loads(out)
    assert payload["commits_scanned"] == 2
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["kind"] == "unsanctioned-cfe-touch"
    assert payload["findings"][0]["ref"] == sha[:10]


def test_main_exit_2_not_a_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["mason_cfe_surface_check.py"])
    rc = m.main()
    captured = capsys.readouterr()

    assert rc == 2
    assert "UNKNOWN" in captured.err


def test_cli_against_live_repo_exits_zero() -> None:
    """`python scripts/mason_cfe_surface_check.py` -- exact command from the
    spec's Verification section."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "mason_cfe_surface_check.py")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "clean" in proc.stdout
