"""Unit tests for ``pyforge.doctor.sources.hygiene.gather`` (Story 9.2,
CAP-8) -- one test per row of the story spec's I/O & Edge-Case Matrix.

The orphan-file class needs a REAL ``git`` repository (``run_git`` is the
only subprocess this module drives) -- this test file is not restricted to
``cli_bridge.py`` itself, only the package source under ``pyforge/doctor/``
is; a test file driving real ``git`` to set up a fixture is fine, mirroring
``test_sources_ledger.py``'s own precedent, including its leaky-git-env
scrub (``GIT_DIR``/``GIT_WORK_TREE`` inherited from a nested worktree's own
environment would otherwise point every fixture repo's ``git`` calls at
THIS repo instead of the tmp one).

The two live-repo tests (zero false positives against warden; >=1 true
positive elsewhere) run ``gather`` against the real monorepo root, resolved
the same guarded way ``test_hygiene_definitions.py`` does (this file sits at
the identical ``tests/unit/`` depth, so the same ``parents[6]`` lands at the
monorepo root; an ``IndexError`` degrades to a skip).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.hygiene_definitions import HygieneFindingKind
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import hygiene

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _require_repo_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")
    return _REPO_ROOT


# --- git fixture plumbing (mirrors test_sources_ledger.py) ------------------

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


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_station_scaffold(repo: Path, slug: str) -> Path:
    """A minimal, well-formed station (real README, real ledger, real
    epics.md) with none of the 5 hygiene classes present -- the shared
    starting point several tests build a single defect on top of."""
    project_dir = repo / "_bmad-output" / "projects" / slug
    _write(project_dir / "README.md", f"{slug} is a real station with real prose.\n")
    _write(
        project_dir / "planning-artifacts" / "sprint-status-ledger.yaml",
        "development_status:\n  1-1-foo: done\n",
    )
    return project_dir


# --- Row: fixture reproduction, all 5 classes -------------------------------


def _seed_all_classes_fixture(repo: Path, slug: str) -> Path:
    """A committed fixture tree reproducing all 5 hygiene classes at once --
    shared by the all-classes reproduction test and the never-mutates test,
    which both need the identical starting tree."""
    _init_repo(repo)
    project_dir = repo / "_bmad-output" / "projects" / slug

    # dead-test-scaffolding: a tests/ tree with scaffold but zero test_*.py.
    _write(project_dir / "tests" / "conftest.py", "# fixtures only\n")
    _write(project_dir / "tests" / "unit" / "__init__.py", "")

    # readme-placeholder: the unfilled template stub. Also carries a real
    # mention of "sprint-status.yaml" so THAT filename resolves an inbound
    # reference and is not double-counted as an orphan-file candidate below.
    _write(
        project_dir / "README.md",
        "acme is a [role] station in the PyForge factory, responsible for "
        "[responsibilities]. See planning-artifacts/sprint-status.yaml for "
        "historical context.\n",
    )

    # hollow-sprint-status: the Tier-3 non-ledger feed, scaffolded but empty.
    _write(
        project_dir / "planning-artifacts" / "sprint-status.yaml",
        "epics: []\nstories: []\nsummary:\n  completion_percentage: 0%\n",
    )

    # stale-dream-status: ledger 100% done, Dream frontmatter still "specified".
    _write(
        project_dir / "planning-artifacts" / "sprint-status-ledger.yaml",
        "development_status:\n  1-1-foo: done\n",
    )
    _write(
        repo / "docs" / "dreams" / f"{slug}.md",
        "---\ntitle: Acme\nstatus: specified\n---\n\n# Acme\n",
    )

    # orphan-file: a non-conventional name, no directory convention, and (once
    # committed) no inbound reference anywhere else in the tracked repo.
    _write(
        project_dir / "planning-artifacts" / "orphan-notes.md",
        "one-time notes, never linked from anywhere else.\n",
    )

    _commit_all(repo, "seed the all-classes fixture")
    return project_dir


def test_gather_emits_exactly_five_findings_for_a_synthetic_all_classes_fixture(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _seed_all_classes_fixture(repo, "pyforge-acme")

    findings = hygiene.gather(repo)

    assert len(findings) == 5
    kinds = {f.check for f in findings}
    assert kinds == {kind.value for kind in HygieneFindingKind}
    assert all(f.source is Source.BMAD_OUTPUT_HYGIENE for f in findings)
    assert all(f.evidence["station"] == "acme" for f in findings)
    assert all(isinstance(f.evidence.get("path"), str) and f.evidence["path"] for f in findings)
    by_check = {f.check: f for f in findings}
    assert by_check[HygieneFindingKind.DEAD_TEST_SCAFFOLDING.value].evidence["path"] == "tests"


# --- Row: gather() invocation never mutates the tree it scans --------------


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    """Every file's repo-relative path and raw bytes under ``root``,
    excluding ``.git`` -- ``gather()`` never reads/writes git's own internal
    bookkeeping directly (its one subprocess call, ``git grep``, is
    read-only), so ``.git``'s own incidental churn is not evidence about
    THIS module's own filesystem behavior."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def test_gather_never_mutates_the_fixture_tree_it_scans(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _seed_all_classes_fixture(repo, "pyforge-acme")

    before = _snapshot_tree(repo)
    findings = hygiene.gather(repo)
    after = _snapshot_tree(repo)

    assert len(findings) == 5
    assert set(after) == set(before)
    assert after == before


# --- Regression: a frontmatter value containing a literal "---" substring --


def test_dream_frontmatter_status_survives_an_embedded_triple_dash_in_an_earlier_field(
    tmp_path: Path,
) -> None:
    # A naive `text.split("---", 2)` mis-splits here: parts[1] would be just
    # ' Acme\nnotes: "see --- below for context"\n', truncating BEFORE the
    # real closing fence and losing `status` entirely -- reproduced by Edge
    # Case Hunter during review. The fence must be recognized only on a line
    # that is EXACTLY `---` once stripped.
    dream = tmp_path / "acme.md"
    _write(
        dream,
        '---\ntitle: Acme\nnotes: "see --- below for context"\nstatus: specified\n---\n\n# Acme\n',
    )
    assert hygiene._dream_frontmatter_status(dream) == "specified"


def test_dream_frontmatter_status_returns_none_without_a_closing_fence(
    tmp_path: Path,
) -> None:
    dream = tmp_path / "acme.md"
    _write(dream, "---\ntitle: Acme\nstatus: specified\n# no closing fence\n")
    assert hygiene._dream_frontmatter_status(dream) is None


# --- Row: fully clean synthetic sweep ---------------------------------------


def test_gather_returns_one_ok_finding_for_a_fully_clean_sweep(tmp_path: Path) -> None:
    repo = tmp_path
    _seed_station_scaffold(repo, "pyforge-acme")
    _seed_station_scaffold(repo, "pyforge-beta")

    findings = hygiene.gather(repo)

    assert len(findings) == 1
    assert findings[0].source is Source.BMAD_OUTPUT_HYGIENE
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence["stations"] == 2


def test_gather_returns_one_ok_finding_when_no_projects_dir_exists(
    tmp_path: Path,
) -> None:
    findings = hygiene.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence["stations"] == 0


# --- Row: one station's file is unreadable ----------------------------------


def test_one_stations_unreadable_file_warns_without_discarding_another_stations_positive(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    broken_dir = _seed_station_scaffold(repo, "pyforge-broken")
    # Undecodable bytes -- read_text(encoding="utf-8") raises UnicodeDecodeError.
    (broken_dir / "README.md").write_bytes(b"\xff\xfe not valid utf-8 \xfa")

    good_dir = _seed_station_scaffold(repo, "pyforge-good")
    _write(good_dir / "tests" / "conftest.py", "# fixtures only\n")

    findings = hygiene.gather(repo)

    by_station = {f.evidence.get("station"): f for f in findings}
    assert by_station["broken"].check == "station-unevaluable"
    assert by_station["broken"].status is DoctorStatus.WARN
    assert by_station["good"].check == HygieneFindingKind.DEAD_TEST_SCAFFOLDING.value
    assert len(findings) == 2


# --- Row: orphan-file, no inbound references --------------------------------


def test_orphan_file_with_no_inbound_references_resolves_true_not_a_warn(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    project_dir = _seed_station_scaffold(repo, "pyforge-acme")
    _write(
        project_dir / "planning-artifacts" / "orphan-notes.md",
        "never linked from anywhere else.\n",
    )
    _commit_all(repo, "seed an unreferenced orphan candidate")

    findings = hygiene.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == HygieneFindingKind.ORPHAN_FILE.value
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["path"] == "planning-artifacts/orphan-notes.md"


# --- Row: orphan-file, git errors -------------------------------------------


def test_orphan_file_git_error_warns_that_one_candidate_without_affecting_others(
    tmp_path: Path,
) -> None:
    # Deliberately NOT a git repository -- `git grep` there exits >=2
    # ("not a git repository"), which run_git's default-outside-{0,1}
    # handling still raises as CliBridgeError.
    not_a_repo = tmp_path / "not-a-repo"
    acme_dir = _seed_station_scaffold(not_a_repo, "pyforge-acme")
    _write(
        acme_dir / "planning-artifacts" / "orphan-notes.md",
        "would be an orphan, but git itself is unavailable here.\n",
    )
    good_dir = _seed_station_scaffold(not_a_repo, "pyforge-good")
    _write(good_dir / "tests" / "conftest.py", "# fixtures only\n")

    findings = hygiene.gather(not_a_repo)

    by_station: dict[str, list] = {}
    for f in findings:
        by_station.setdefault(f.evidence.get("station"), []).append(f)

    assert len(by_station["acme"]) == 1
    assert by_station["acme"][0].check == "orphan-file-unevaluable"
    assert by_station["acme"][0].status is DoctorStatus.WARN

    assert len(by_station["good"]) == 1
    assert by_station["good"][0].check == HygieneFindingKind.DEAD_TEST_SCAFFOLDING.value


# --- Row: dead-test-scaffolding, no marker dir ------------------------------


def test_dead_test_scaffolding_is_not_even_considered_without_a_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A stub that would ALWAYS fire if it were ever called -- proves the
    # station is never even considered a candidate, not merely classified
    # negative.
    monkeypatch.setattr(hygiene, "is_dead_test_scaffolding", lambda relpaths: True)
    project_dir = _seed_station_scaffold(tmp_path, "pyforge-acme")
    assert not (project_dir / "tests").exists()
    assert not (project_dir / "pytest.ini").exists()
    assert not (project_dir / "playwright.config.ts").exists()

    findings: list = []
    hygiene._check_dead_test_scaffolding(project_dir, "acme", findings)

    assert findings == []


# --- Row: dead-test-scaffolding, marker-file-only ---------------------------


def test_dead_test_scaffolding_path_names_the_marker_file_when_no_tests_dir_exists(
    tmp_path: Path,
) -> None:
    project_dir = _seed_station_scaffold(tmp_path, "pyforge-acme")
    _write(project_dir / "pytest.ini", "[pytest]\n")
    assert not (project_dir / "tests").exists()

    findings: list = []
    hygiene._check_dead_test_scaffolding(project_dir, "acme", findings)

    assert len(findings) == 1
    assert findings[0].check == HygieneFindingKind.DEAD_TEST_SCAFFOLDING.value
    assert findings[0].evidence["path"] == "pytest.ini"


# --- Row: hollow-sprint-status, no non-ledger file --------------------------


def test_hollow_sprint_status_is_not_even_considered_without_the_non_ledger_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hygiene, "is_hollow_sprint_status", lambda parsed: True)
    project_dir = _seed_station_scaffold(tmp_path, "pyforge-acme")
    assert not (project_dir / "planning-artifacts" / "sprint-status.yaml").exists()
    assert (project_dir / "planning-artifacts" / "sprint-status-ledger.yaml").exists()

    findings: list = []
    hygiene._check_hollow_sprint_status(project_dir, "acme", findings)

    assert findings == []


# --- Row: zero false positives against warden (live) -----------------------


def test_live_repo_gather_reports_no_finding_naming_warden() -> None:
    repo_root = _require_repo_root()
    findings = hygiene.gather(repo_root)
    assert not any(f.evidence.get("station") == "warden" for f in findings)


# --- Row: >=1 true positive elsewhere (live) --------------------------------


def _git_grep_matches(repo_root: Path, basename: str) -> list[str]:
    result = subprocess.run(
        ["git", "grep", "-l", "--fixed-strings", "-e", basename],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), f"git grep itself failed: {result.stderr}"
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_live_repo_gather_surfaces_at_least_one_true_positive_naming_a_non_warden_station() -> None:
    repo_root = _require_repo_root()

    # Re-verify the cited herald fixture is STILL grounded before asserting
    # against it -- fail loud (not silently) if this fact has changed.
    #
    # Built from two parts (not one literal) so this line's own text is
    # never a contiguous match for the full basename: `_git_grep_matches`
    # below scans this very file among everything else in the repo, and a
    # bare literal here would make THIS test the fixture's one and only
    # "inbound reference" -- self-sabotaging both this pre-check and
    # `gather()`'s own identical git-grep-based check.
    basename = "deckcraft-board-epics-displaced-2026-08-08" + ".json"
    own_relpath = "_bmad-output/projects/pyforge-herald/planning-artifacts/" + basename
    herald_file = repo_root / own_relpath
    assert herald_file.is_file(), (
        f"the cited herald fixture {own_relpath} no longer exists -- re-verify "
        "a live true positive and update this test to cite it instead"
    )
    others = [m for m in _git_grep_matches(repo_root, basename) if m != own_relpath]
    assert not others, (
        f"the cited herald fixture is no longer unreferenced repo-wide "
        f"(now referenced by {others}) -- re-verify a live true positive "
        "and update this test to cite it instead"
    )

    findings = hygiene.gather(repo_root)

    assert any(
        f.check == HygieneFindingKind.ORPHAN_FILE.value
        and f.evidence.get("station") == "herald"
        and f.evidence.get("path") == "planning-artifacts/" + basename
        for f in findings
    ), "expected the re-verified herald orphan file to be reported"
    assert any(f.evidence.get("station") not in (None, "warden") for f in findings)
