"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_live_proof_surfaces.py``.

The Boundaries' own "hard, testable gate" (Story 26.1, ``spec-pyforge-doctor`` CAP-77) walks the repository's own
``git ls-files`` against its own tracked catalog, so it runs here; every test that drives a tmp git repository stays
in the package half (``test_sources_live_proof_surfaces.py``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.sources import live_proof_surfaces as lps

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

# A hook-set GIT_DIR/GIT_WORK_TREE would retarget `git ls-files` at the wrong repository: the same scrub as
# test_sources_live_proof_surfaces.py's own `_isolate_git_env` (mirrors test_sources_frozen_path.py).
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


# The exact three real tracked paths the first attempt's keyword-substring
# fallback (cluster/deck/docker) matched against catalog rows they have
# nothing to do with -- the review's own regression fixture (the package half
# spells the same three as path joins for its tmp-repository case).
_FIRST_ATTEMPT_FALSE_POSITIVES = (
    "docs/how-to/ocp-cluster-bringup.md",
    "docs/how-to/presentation-deck.md",
    "recipes/docker/recipe.yaml",
)


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

# The herald *PPTX export* row names one real, currently-tracked path
# outside src/shared/packages/pyforge-herald/ (`scripts/deck_export.py`) --
# confirmed via `git ls-files` against the live tree. A strict
# single-package-prefix station check would false-fail on that catalog
# content, so this one path is a named exception here, mirroring the
# Boundaries' own "or the named cross-station paths for the container row"
# carve-out.
_HERALD_NAMED_NON_PACKAGE_PATHS = ("scripts/deck_export.py",)


def test_zero_false_positives_against_the_live_tracked_tree() -> None:
    """Walks `git ls-files` of the real repo against every REAL catalog
    row's own Surface globs, and asserts every hit (a) is independently
    reproducible by a literal glob walk from the repo root -- proving the
    matcher never does anything a keyword, substring, or fuzzy match could
    have done instead, (b) is not one of the three named legacy false
    positives, and (c) sits under the row's own station (or the container
    row's / herald's own named cross-station paths) -- the Boundaries' own
    "hard, testable gate" wording."""
    repo_root = Path(__file__).resolve().parents[6]
    # The live half runs only where the tree exists: a checkout without .claude/ or without the catalog is a
    # failure, never a silent skip.
    assert (repo_root / ".claude").is_dir(), f"{repo_root} carries no .claude directory: not the repository checkout"
    catalog_path = repo_root / lps._CATALOG_RELATIVE
    assert catalog_path.is_file(), f"{catalog_path} (live-proof-surfaces.md) is missing from the checkout"

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
        # or the container row's named cross-station paths, or herald's one
        # named non-package live-proof mechanism.
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
