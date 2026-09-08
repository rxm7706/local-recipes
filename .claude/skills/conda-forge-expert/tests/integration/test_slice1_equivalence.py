"""Story 6.3 -- CAP-2 clause 4: prove the Skill-Forge-compiled replacement of
Slice 1 ("Recipe Generation" -- `recipe-generator.py`, `name_resolver.py`,
`github_updater.py`) is a faithful copy of the live original, not a
from-scratch reimplementation that happens to match by coincidence.

Per `skf-create-skill/references/generate-artifacts.md` Section "Files 4b",
scripts named in a brief's `scripts_inventory` are copied into the compiled
package "with content preserved" -- this suite proves that claim held for
this specific compile run by running the SAME inputs through both the live
original scripts and the compiled replacement's copied scripts and diffing
the results, mirroring the "run both, diff the result" shape
`src/shared/packages/pyforge-mason/tests/integration/
test_delegation_fidelity.py` established for a structurally similar
old-path-vs-new-path comparison.

Skips cleanly (never fails the suite) when the compiled replacement package
does not exist on disk -- e.g. a checkout that has this test file but not
yet a compiled `cfe-recipe-generation` skill (the brief/compile step is a
separate, sometimes-gitignored artifact chain; see skill-brief.yaml's
location under `forge-data/`, which IS gitignored, vs. the compiled package
under `.claude/skills/`, which is tracked).

Story 6.3 (initial pass) found one load-bearing gap: `github_updater.py`'s
`update_recipe()` imports a sibling module, `github_version_checker.py`,
which slice-map.md classifies as a **Slice 2** ("Recipe Lifecycle") canonical
script -- outside Slice 1's original brief scope. That gap is now closed:
`github_version_checker.py` was ported byte-for-byte into the compiled
package as a sanctioned cross-slice runtime dependency (same shape as the
already-sanctioned `_cfy_template.py`), without reclassifying it out of
Slice 2's canonical-scripts inventory (`_bmad-output/projects/pyforge-mason/
planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md` §
"Slice 1: Recipe Generation" and § "Slice 5: Shared Infrastructure" cross-
slice-shared-imports table both document it). `test_github_updater_gap_closed`
below asserts the import now succeeds on both sides. This was the one
pre-existing regression test (`test_dry_run_live_against_actionlint`) that
previously did not pass unmodified against the compiled replacement -- it
now passes on both sides; see the story's own campaign-state.yaml note for
the full CAP-2 clause 3 accounting.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent
_ORIGINAL_SCRIPTS_DIR = _SKILL_DIR / "scripts"
_COMPILED_PACKAGE_DIR = (
    # {skills_output_folder}/{name}/{version-or-active}/{name}/ -- the skill
    # name appears twice (see skf-create-skill/references/generate-artifacts.md
    # § "1. Create Directory Structure": {skill_package} =
    # {skills_output_folder}/{name}/{version}/{name}/).
    _SKILL_DIR.parent / "cfe-recipe-generation" / "active" / "cfe-recipe-generation"
)
_COMPILED_SCRIPTS_DIR = _COMPILED_PACKAGE_DIR / "scripts"

_SLICE1_SCRIPTS = ("recipe-generator.py", "name_resolver.py", "github_updater.py")


def _compiled_package_available() -> bool:
    return _COMPILED_SCRIPTS_DIR.is_dir() and all(
        (_COMPILED_SCRIPTS_DIR / name).is_file() for name in _SLICE1_SCRIPTS
    )


pytestmark = pytest.mark.skipif(
    not _compiled_package_available(),
    reason=(
        "compiled replacement not found at "
        f"{_COMPILED_SCRIPTS_DIR} -- run skf-brief-skill + skf-create-skill "
        "against slice-1's scope first (see campaign-state.yaml)"
    ),
)


def _run(scripts_dir: Path, script: str, *args: str, timeout: int = 30):
    return subprocess.run(
        [sys.executable, str(scripts_dir / script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.mark.slow
@pytest.mark.parametrize("script", _SLICE1_SCRIPTS)
def test_help_output_identical(script):
    """`--help` output must be byte-identical between the original and the
    compiled replacement's copy -- proves the copy operation preserved the
    argparse-derived usage text verbatim (a cheap, deterministic, fully
    offline proxy for "the file itself did not change")."""
    original = _run(_ORIGINAL_SCRIPTS_DIR, script, "--help")
    compiled = _run(_COMPILED_SCRIPTS_DIR, script, "--help")
    assert original.returncode == compiled.returncode == 0
    assert original.stdout == compiled.stdout


@pytest.mark.slow
def test_recipe_generator_template_output_identical(tmp_path):
    """`recipe-generator.py template python-noarch` end-to-end, run against
    both locations, must produce byte-identical `recipe.yaml` output.

    This is the one Slice-1 functional path that is fully offline and
    deterministic AND exercises a real runtime dependency beyond the script
    file itself (`{skill_root}/templates/python/noarch-recipe.yaml`,
    resolved via `Path(__file__).parent.parent`) -- so it proves the
    compiled package's directory layout, not just the script's own bytes,
    reproduces the original's behavior.
    """
    original_out = tmp_path / "original"
    compiled_out = tmp_path / "compiled"
    original = _run(
        _ORIGINAL_SCRIPTS_DIR, "recipe-generator.py",
        "template", "python-noarch",
        "--name", "equiv-test", "--version", "1.0.0",
        "--output", str(original_out),
    )
    compiled = _run(
        _COMPILED_SCRIPTS_DIR, "recipe-generator.py",
        "template", "python-noarch",
        "--name", "equiv-test", "--version", "1.0.0",
        "--output", str(compiled_out),
    )
    assert original.returncode == 0, f"original failed: {original.stdout}{original.stderr}"
    assert compiled.returncode == 0, f"compiled failed: {compiled.stdout}{compiled.stderr}"
    original_recipe = (original_out / "recipe.yaml").read_text()
    compiled_recipe = (compiled_out / "recipe.yaml").read_text()
    assert original_recipe == compiled_recipe


@pytest.mark.slow
def test_name_resolver_error_shape_identical():
    """A deliberately-unresolvable PyPI name exercises `resolve_name()`'s
    full fallback chain (local cache miss -> metadata API -> repodata
    fallback -> not-found) without touching the network in a way that could
    flake -- both locations must agree on the JSON error shape."""
    bogus = "definitely-not-a-real-pypi-package-xyz-equivalence-probe"
    original = _run(_ORIGINAL_SCRIPTS_DIR, "name_resolver.py", bogus, timeout=60)
    compiled = _run(_COMPILED_SCRIPTS_DIR, "name_resolver.py", bogus, timeout=60)
    assert original.returncode == compiled.returncode
    assert original.stdout == compiled.stdout


@pytest.mark.slow
@pytest.mark.network
def test_github_updater_gap_closed(tmp_path):
    """Story 6.3 gap-closure: `github_updater.py` imports Slice 2's
    `github_version_checker.py`, which was previously absent from the
    compiled Slice-1 package (Slice 1's original brief scope did not bundle
    it). It has since been ported into the compiled package byte-for-byte as
    a sanctioned cross-slice runtime dependency (same shape as the already-
    sanctioned `_cfy_template.py`) without reclassifying it out of Slice 2's
    canonical-scripts inventory -- see slice-map.md § "Slice 1: Recipe
    Generation" and § "Slice 5: Shared Infrastructure". Both sides now
    resolve the import identically; this test proves that rather than
    silently dropping the old cross-slice-gap assertion.

    `update_recipe()` checks `_CHECKER_AVAILABLE` before anything else and
    returns immediately (no network access) if the import failed -- that
    early-return path is what this test targets. Once the import succeeds
    (both sides, post gap-closure), `update_recipe()` proceeds to a real
    GitHub API lookup for this fixture's deliberately bogus `example/
    equiv-test` repo, which 404s -- so this test does make a live network
    call on both sides now (it did not, pre-fix, on the compiled side,
    which returned before reaching network code). The assertions below are
    deterministic regardless of that network outcome: they parse the
    printed result as JSON and check the specific `error` field, so a 404,
    a rate-limit response, or a transient network failure all still produce
    a clean (non-import-failure) `error` string via `update_recipe()`'s own
    exception handling, never an uncaught traceback.
    """
    recipe_dir = tmp_path / "equiv-test"
    recipe_dir.mkdir()
    (recipe_dir / "recipe.yaml").write_text(
        "schema_version: 1\n"
        "context:\n  version: 1.0.0\n"
        "package:\n  name: equiv-test\n  version: ${{ version }}\n"
        "source:\n  url: https://github.com/example/equiv-test/archive/v${{ version }}.tar.gz\n"
        "  sha256: " + "0" * 64 + "\n"
        "build:\n  number: 0\n"
        "about:\n  homepage: https://github.com/example/equiv-test\n"
        "  license: MIT\n  summary: x\n"
        "extra:\n  recipe-maintainers:\n    - rxm7706\n"
    )
    original = _run(_ORIGINAL_SCRIPTS_DIR, "github_updater.py", "--dry-run", str(recipe_dir))
    compiled = _run(_COMPILED_SCRIPTS_DIR, "github_updater.py", "--dry-run", str(recipe_dir))

    # Parse each side's printed result as JSON -- proves the process ran to
    # completion and printed update_recipe()'s result dict (rules out an
    # early crash producing empty/garbled stdout that would also happen not
    # to contain the substring below), then check the specific `error`
    # field rather than a raw stdout substring match. main() may print a
    # "Checking GitHub releases for..." progress line before the JSON dict
    # (once the import succeeds and repo resolution proceeds), so parse
    # from the first '{' rather than the whole stdout.
    original_result = json.loads(original.stdout[original.stdout.index("{"):])
    compiled_result = json.loads(compiled.stdout[compiled.stdout.index("{"):])

    # Original: github_version_checker.py is present alongside it in the
    # live skill tree, so the import succeeds (the dry-run may still fail
    # for other reasons -- e.g. no real GitHub repo at this bogus URL -- but
    # NOT with the "could not be imported" error).
    assert "could not be imported" not in original_result.get("error", "")

    # Compiled replacement: github_version_checker.py was ported alongside
    # github_updater.py, so the import now succeeds here too -- the gap is
    # closed, not just documented.
    assert "could not be imported" not in compiled_result.get("error", "")
