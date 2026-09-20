"""Unit tests for ``pyforge.doctor.sources.live_proof_surfaces`` (Story
26.1, ``spec-pyforge-doctor`` CAP-77) -- covers every row of the spec's I/O
& Edge-Case Matrix, plus the Boundaries' own "hard, testable gate": zero
false positives against the REAL tracked catalog and REAL tracked repo
tree.

Every ``gather()``-level test drives a REAL tmp git repository (mirrors
``test_sources_frozen_path.py``'s own convention: never a mocked subprocess
call), including the same ``origin/main`` local-branch trick (``git branch
origin/main <sha>`` resolves via ``git rev-parse``/``git diff`` with no real
remote needed).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import live_proof_surfaces as lps

# --- live-tree fixtures: same `_REPO_ROOT` / skip-guard idiom as
# test_sources_board.py (this file sits at the same tests/unit/ depth) -----

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _require_repo_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")
    return _REPO_ROOT


# --- synthetic git repo fixtures (mirrors test_sources_frozen_path.py) ------

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


def _write_catalog(repo: Path, text: str) -> Path:
    path = repo / lps._CATALOG_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_file(repo: Path, rel: str, text: str = "content\n") -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _table_row(station: str, surface: str, how_to_prove: str, globs: str) -> str:
    return f"| {station} | {surface} | why | {how_to_prove} | cost | {globs} |\n"


_CATALOG_HEADER = (
    "| Station | Surface | Why a static/self-report pass misses it | "
    "How to prove it live | Cost | Surface globs |\n"
    "|---|---|---|---|---|---|\n"
)

_HERALD_GLOB = "`src/shared/packages/pyforge-herald/src/pyforge/herald/transport/**`"
_HERALD_PROOF = "run `herald deck push --prove` against a live Design credential."
_ATLAS_GLOB = "`src/shared/packages/pyforge-atlas/wasm/**`"
_ATLAS_PROOF = "No single documented live-proof command as of this writing -- named gap."

_MINIMAL_CATALOG = (
    _CATALOG_HEADER
    + _table_row("herald", "Claude Design MCP bridge", _HERALD_PROOF, _HERALD_GLOB)
    + _table_row("atlas", "Chromium/DuckDB/WASM pipeline", _ATLAS_PROOF, _ATLAS_GLOB)
    + _table_row("scribe", "Empty-glob row", "some proof text", "")
)

# The exact three real tracked paths the first attempt's keyword-substring
# fallback (cluster/deck/docker) matched against catalog rows they have
# nothing to do with -- the review's own regression fixture.
_FIRST_ATTEMPT_FALSE_POSITIVES = (
    "docs/how-to/ocp-cluster-bringup.md",
    "docs/how-to/presentation-deck.md",
    "recipes/docker/recipe.yaml",
)


# --- parse_catalog -----------------------------------------------------------


def test_parse_catalog_extracts_rows_and_glob_tokens() -> None:
    rows = lps.parse_catalog(_MINIMAL_CATALOG)
    assert len(rows) == 3
    herald, atlas, scribe = rows
    assert herald.station == "herald"
    assert herald.surface == "Claude Design MCP bridge"
    assert herald.how_to_prove == _HERALD_PROOF
    assert herald.surface_globs == ("src/shared/packages/pyforge-herald/src/pyforge/herald/transport/**",)
    assert atlas.surface_globs == ("src/shared/packages/pyforge-atlas/wasm/**",)
    assert "named gap" in atlas.how_to_prove


def test_parse_catalog_empty_globs_cell_yields_empty_tuple() -> None:
    rows = lps.parse_catalog(_MINIMAL_CATALOG)
    scribe = rows[2]
    assert scribe.station == "scribe"
    assert scribe.surface_globs == ()


def test_parse_catalog_skips_separator_row() -> None:
    rows = lps.parse_catalog(_MINIMAL_CATALOG)
    assert all(row.station != "---" for row in rows)


def test_parse_catalog_no_header_raises() -> None:
    with pytest.raises(ValueError, match="no table header"):
        lps.parse_catalog("just some prose\nwith no table at all\n")


def test_parse_catalog_wrong_column_count_raises() -> None:
    malformed = _CATALOG_HEADER + "| herald | only three | cells |\n"
    with pytest.raises(ValueError, match="expected 6 columns"):
        lps.parse_catalog(malformed)


def test_parse_catalog_stops_at_table_end() -> None:
    """Prose after the table (e.g. the real catalog's own 'Reference
    pattern' section) must not be mistaken for more rows."""
    text = _MINIMAL_CATALOG + "\n## Reference pattern already solved elsewhere\n\nprose\n"
    rows = lps.parse_catalog(text)
    assert len(rows) == 3


# --- _glob_to_re / _row_match -------------------------------------------------


def test_glob_to_re_exact_match_no_wildcard() -> None:
    pattern = lps._glob_to_re("scripts/deck_export.py")
    assert pattern.match("scripts/deck_export.py")
    assert not pattern.match("scripts/deck_export.py.bak")


def test_glob_to_re_double_star_spans_separators() -> None:
    pattern = lps._glob_to_re("src/shared/packages/pyforge-herald/**")
    assert pattern.match("src/shared/packages/pyforge-herald/a/b/c.py")
    assert not pattern.match("src/shared/packages/pyforge-warden/a.py")


def test_glob_to_re_single_star_does_not_span_separators() -> None:
    pattern = lps._glob_to_re("scripts/container-gates*")
    assert pattern.match("scripts/container-gates.py")
    assert not pattern.match("scripts/container-gates/extra.py")


def test_row_match_never_matches_via_keyword_or_substring() -> None:
    """The exact defect class the amendment fixed: a bare substring/keyword
    of the row's own Surface/station text must never match an unrelated
    real path, even when that path contains the word verbatim."""
    row = lps.CatalogRow(
        station="scribe",
        surface="Postgres+pgvector cluster",
        how_to_prove="scribe-pg-up",
        cost="a real local Postgres process",
        surface_globs=("src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py",),
    )
    matched = lps._row_match(row, ["docs/how-to/ocp-cluster-bringup.md"])
    assert matched == ()


def test_row_match_empty_globs_never_matches() -> None:
    row = lps.CatalogRow(station="x", surface="y", how_to_prove="z", cost="w", surface_globs=())
    assert lps._row_match(row, ["any/path/at/all.py"]) == ()


def test_row_match_returns_matches_in_changed_paths_order() -> None:
    row = lps.CatalogRow(
        station="herald",
        surface="bridge",
        how_to_prove="--prove",
        cost="cheap",
        surface_globs=("a/*.py", "b/*.py"),
    )
    matched = lps._row_match(row, ["z/unrelated.py", "b/two.py", "a/one.py"])
    assert matched == ("b/two.py", "a/one.py")


# --- gather() -- I/O & Edge-Case Matrix, real git-repo fixtures --------------


def test_touching_a_catalogued_surface_reports_warn_quoting_how_to_prove(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MINIMAL_CATALOG)
    base_sha = _commit_all(repo, "seed catalog")
    _branch_at(repo, "origin/main", base_sha)

    touched = "src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py"
    _write_file(repo, touched)
    _commit_all(repo, "touch the herald bridge transport")

    findings = lps.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.LIVE_PROOF_SURFACE
    assert finding.check == "live-proof-surface"
    assert finding.status is DoctorStatus.WARN
    assert "herald" in finding.message
    assert "--prove" in finding.message
    assert finding.evidence["station"] == "herald"
    assert finding.evidence["changed_paths"] == [touched]
    assert finding.evidence["how_to_prove"] == _HERALD_PROOF
    assert finding.evidence["cost"] == "cost"


_WARDEN_GLOBS_CELL = (
    "`src/shared/packages/pyforge-warden/src/pyforge/warden/feeds.py`, "
    "`src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py`"
)
_WARDEN_PROOF = "warden scan queries the live feeds directly at scan time."

_MULTI_ROW_CATALOG = (
    _CATALOG_HEADER
    + _table_row("warden", "Live OSV/CISA-KEV/EPSS feeds", _WARDEN_PROOF, _WARDEN_GLOBS_CELL)
    + _table_row("herald", "Claude Design MCP bridge", _HERALD_PROOF, _HERALD_GLOB)
)


def test_multi_row_and_multi_glob_gather_accumulates_correctly(tmp_path: Path) -> None:
    """Three gaps in one fixture: (1) parse_catalog extracting more than one
    backtick-quoted token from a single Surface globs cell (warden's row);
    (2) a diff touching more than one catalogued surface in the same commit
    yields one Finding per matching row; (3) a row matching more than one
    changed path carries every one of them, in order, in
    evidence["changed_paths"], while the message cites only matched[0]."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MULTI_ROW_CATALOG)
    base_sha = _commit_all(repo, "seed catalog")
    _branch_at(repo, "origin/main", base_sha)

    feeds = "src/shared/packages/pyforge-warden/src/pyforge/warden/feeds.py"
    vuln = "src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py"
    bridge = "src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py"
    _write_file(repo, feeds)
    _write_file(repo, vuln)
    _write_file(repo, bridge)
    _commit_all(repo, "touch two catalogued surfaces at once")

    findings = lps.gather(repo)

    assert len(findings) == 2
    by_station = {f.evidence["station"]: f for f in findings}

    warden_finding = by_station["warden"]
    assert warden_finding.evidence["changed_paths"] == [feeds, vuln]
    assert feeds in warden_finding.message
    assert vuln not in warden_finding.message

    herald_finding = by_station["herald"]
    assert herald_finding.evidence["changed_paths"] == [bridge]


def test_no_matching_changed_path_reports_zero_findings(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MINIMAL_CATALOG)
    base_sha = _commit_all(repo, "seed catalog")
    _branch_at(repo, "origin/main", base_sha)

    _write_file(repo, "docsite/build.py")
    _commit_all(repo, "unrelated change")

    findings = lps.gather(repo)

    assert findings == ()


def test_first_attempt_false_positives_report_zero_findings(tmp_path: Path) -> None:
    """The I/O & Edge-Case Matrix's own regression fixture: the three real
    files the keyword-substring fallback used to mis-match must report
    nothing against real glob-only matching."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MINIMAL_CATALOG)
    base_sha = _commit_all(repo, "seed catalog")
    _branch_at(repo, "origin/main", base_sha)

    for rel in _FIRST_ATTEMPT_FALSE_POSITIVES:
        _write_file(repo, rel)
    _commit_all(repo, "touch the three known false-positive paths")

    findings = lps.gather(repo)

    assert findings == ()


def test_empty_glob_cell_row_never_fires(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MINIMAL_CATALOG)
    base_sha = _commit_all(repo, "seed catalog")
    _branch_at(repo, "origin/main", base_sha)

    # Touch a path that textually matches the empty-glob row's own station/
    # surface words -- it must still never fire (Boundaries: an empty cell
    # is never diff-matched, regardless of what the changed path is named).
    _write_file(repo, "scribe/empty-glob/row.py")
    _commit_all(repo, "touch something scribe-ish")

    findings = lps.gather(repo)

    assert findings == ()


def test_no_mechanism_yet_row_states_the_gap_honestly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MINIMAL_CATALOG)
    base_sha = _commit_all(repo, "seed catalog")
    _branch_at(repo, "origin/main", base_sha)

    touched = "src/shared/packages/pyforge-atlas/wasm/loader.wasm"
    _write_file(repo, touched)
    _commit_all(repo, "touch the atlas wasm pipeline")

    findings = lps.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "named gap" in finding.message
    assert "atlas" in finding.message


def test_malformed_catalog_degrades_to_one_generic_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _CATALOG_HEADER + "| herald | only three | cells |\n")
    _commit_all(repo, "seed malformed catalog")

    findings = lps.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.LIVE_PROOF_SURFACE
    assert finding.check == "live-proof-surface"
    assert finding.status is DoctorStatus.WARN


def test_unresolvable_git_ref_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_catalog(repo, _MINIMAL_CATALOG)
    _commit_all(repo, "seed catalog")
    # deliberately never create an "origin/main" branch/ref

    findings = lps.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "could not diff" in finding.message


def test_missing_catalog_degrades_to_one_generic_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_file(repo, "README.md", "no catalog here\n")
    base_sha = _commit_all(repo, "seed, no catalog")
    _branch_at(repo, "origin/main", base_sha)

    findings = lps.gather(repo)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_gather_never_raises_on_a_non_repository_target(tmp_path: Path) -> None:
    non_repo = tmp_path / "not-a-repo"
    _write_catalog(non_repo, _MINIMAL_CATALOG)

    findings = lps.gather(non_repo)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- Boundaries' own "hard, testable gate": zero false positives against
# the REAL tracked catalog and REAL tracked repo tree ------------------------

# The container row's own named cross-station paths (Boundaries' own text).
_GUILD_CONTAINER_GLOBS = (
    "Containerfile",
    "src/platform/Containerfile",
    "src/platform/compose/**/Containerfile",
    ".dockerignore",
    "scripts/container-gates*",
)

# The real catalog's own herald rows name two real, currently-tracked
# live-proof mechanisms that sit OUTSIDE src/shared/packages/pyforge-herald/
# (the live-demo webhook workflow, the PPTX-export script) -- confirmed via
# `git ls-files` against the live tree. A strict single-package-prefix
# station check would false-fail on this real, legitimate catalog content,
# so these two paths are named exceptions here, mirroring the Boundaries'
# own "or the named cross-station paths for the container row" carve-out.
_HERALD_NAMED_NON_PACKAGE_PATHS = (
    "scripts/deck_export.py",
    ".github/workflows/herald-live-demo.yml",
)


def test_zero_false_positives_against_the_live_tracked_tree() -> None:
    """Walks `git ls-files` of the real repo against every REAL catalog
    row's own Surface globs, and asserts every hit (a) is independently
    reproducible by a literal glob walk from the repo root -- proving the
    matcher never does anything a keyword, substring, or fuzzy match could
    have done instead, (b) is not one of the three named legacy false
    positives, and (c) sits under the row's own station (or the container
    row's / herald's own named cross-station paths) -- the Boundaries' own
    "hard, testable gate" wording."""
    repo_root = _require_repo_root()
    catalog_path = repo_root / lps._CATALOG_RELATIVE
    if not catalog_path.is_file():
        pytest.skip("live-proof-surfaces.md not present in this checkout")

    tracked = sorted(
        line.strip()
        for line in subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if line.strip()
    )

    rows = lps.parse_catalog(catalog_path.read_text(encoding="utf-8"))
    assert rows, "the real catalog parsed to zero rows"

    guild_patterns = [lps._glob_to_re(glob) for glob in _GUILD_CONTAINER_GLOBS]

    violations: list[str] = []
    for row in rows:
        matched = set(lps._row_match(row, tracked))
        if not matched:
            continue
        # Independent oracle: literal pathlib glob evaluation of THIS row's
        # own globs from the repo root -- never a keyword or substring, only
        # what the glob itself selects. Anything _row_match found that this
        # cannot reproduce is a false positive.
        expected: set[str] = set()
        for pattern in row.surface_globs:
            expected.update(p.relative_to(repo_root).as_posix() for p in repo_root.glob(pattern) if p.is_file())
        extra = matched - expected
        if extra:
            violations.append(
                f"{row.station}/{row.surface}: matched {sorted(extra)} not "
                f"reproducible by a literal glob walk of {row.surface_globs}"
            )
        for false_positive in _FIRST_ATTEMPT_FALSE_POSITIVES:
            if false_positive in matched:
                violations.append(f"{row.station}/{row.surface}: matched known false positive {false_positive!r}")

        # Station attribution: every hit sits under the row's own station,
        # or the container row's named cross-station paths, or herald's two
        # named non-package live-proof mechanisms.
        if row.station == "guild (cross-station)":
            for path in matched:
                if not any(pattern.match(path) for pattern in guild_patterns):
                    violations.append(
                        f"{row.station}/{row.surface}: {path!r} is not one "
                        "of the catalog's own named cross-station paths"
                    )
        else:
            expected_prefix = f"src/shared/packages/pyforge-{row.station}/"
            named_exceptions = _HERALD_NAMED_NON_PACKAGE_PATHS if row.station == "herald" else ()
            for path in matched:
                if not path.startswith(expected_prefix) and path not in named_exceptions:
                    violations.append(f"{row.station}/{row.surface}: {path!r} does not sit under {expected_prefix!r}")

    assert not violations, "\n".join(violations)
