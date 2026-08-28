"""Story 12.7 -- CAP-2 clause 4 for Slice 2 ("Recipe Lifecycle"): prove the
Skill-Forge-compiled replacement (`cfe-recipe-lifecycle`) is a faithful copy
of the live originals, not a from-scratch reimplementation that happens to
match by coincidence.

Modeled on `test_slice1_equivalence.py`'s pattern: a self-contained `_run()`
subprocess helper (no shared `conftest.py` machinery), a module-level
`pytest.mark.skipif` guard keyed on the compiled package's presence, and
`@pytest.mark.slow` (no dedicated `equivalence` marker exists -- `pytest.ini`
has `--strict-markers`, so this reuses `slow` per Slice 1's own precedent).

Per this story's own Design Notes (spec's "Equivalence-harness scope is
proportional, not exhaustive" guidance): Slice 2 is ~7x Slice 1's script
count, so this harness scales its *breadth* (a `--help`-output-identity check
across every one of Slice 2's 20 directly CLI-invocable canonical scripts)
without scaling *depth* uniformly -- three deeper behavioral checks cover one
write-oriented script (`recipe_editor.py`), one network-touching script
(`github_version_checker.py`), and one error-path script (`validate_recipe.py`),
the same curated-sample shape Slice 1's own harness used (3 scripts, 4
functions).

**Known, documented divergence -- not silently hidden, not asserted as a
passing check.** Compiling relocates every script two directory levels
deeper than the live tree (`.claude/skills/<name>/<version>/<name>/scripts/`
vs. `.claude/skills/conda-forge-expert/scripts/`). Four of Slice 2's own 25
files compute a repo-root or skill-data-dir path via a *hardcoded* parent-hop
count from `__file__` rather than a directory-depth-independent marker walk:
`_path_guard.py` (`REPO_ROOT = Path(__file__).resolve().parents[4]`),
`_paths.py`'s own `get_repo_root()` (the SAME pattern -- ironic, since this
module's own docstring, written for a past Rule-2 retro, Story 5.5, already
documents ~30-35 *other* live-tree scripts sharing this exact fragile
pattern), `gen_yml_reference.py` (`REPO_ROOT`, same pattern, visible in its
own `--help` text's embedded default output path), `mapping_manager.py` and
`vulnerability_scanner.py` (`Path(__file__).parent.parent.parent.parent`, the
un-`.resolve()`d shape `_paths.py`'s docstring calls out by name). At the
compiled package's deeper nesting, all of these resolve two levels short of
the real repo root -- e.g. `.claude/skills` instead of the repo root -- which
is a REAL behavioral divergence for any caller that passes a *relative* path
or otherwise depends on the correct value (confirmed for
`recipe_editor.py` with a `recipes/`-relative path; NOT triggered by the
existing regression suite, which never asserts against an independent
oracle for these constants -- see `test_path_guard.py::test_defaults_to_repo_recipes_dir`,
which compares the module's own (possibly-wrong) computed value against
itself).

This is a *pre-existing, campaign-wide* concern (any future slice with
similarly-hardcoded scripts will hit the same pattern once compiled two
levels deeper), not specific to Slice 2's own content -- fixing it is a
Skill-Forge / campaign-structure decision, not a single-slice patch this
story's own scope covers (`campaign-state.yaml`'s slice-2 `next_action`
records it for the campaign's attention). `local_builder.py`'s own
`Path(__file__).resolve().parents[3]` occurrence is NOT part of this
finding: it is only a *fallback* after a robust, depth-independent
`pixi.toml` marker-walk (`_repo_root_candidate()`, this same file's own
sibling script), so it does not diverge in practice -- and it is not merely
an absence of the problem, it is an already-proven FIX TEMPLATE: the same
marker-walk-with-hardcoded-fallback shape is the natural pattern to port
into the five affected scripts above in place of their own hardcoded
`parents[N]`/`parent.parent.parent.parent` constants, rather than inventing
a new relocation-aware mechanism from scratch.

Every check below is written to legitimately assert zero divergence for the
invocation pattern it exercises (using the module's own sanctioned
`CFE_RECIPES_ROOT` env-var + absolute-path integration seam for the
write-oriented deep check, exactly as `tests/conftest.py`'s own
`copy_recipe` fixture does for the live suite) -- none of them paper over the
finding above by asserting something false; the finding is recorded here in
prose and in `campaign-state.yaml` / `evidence-report.md`, not inside a test
assertion that would misrepresent it as either "passing" or "failing".
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent
_ORIGINAL_SCRIPTS_DIR = _SKILL_DIR / "scripts"
_COMPILED_PACKAGE_DIR = (
    # {skills_output_folder}/{name}/{version-or-active}/{name}/ -- see
    # skf-create-skill/references/generate-artifacts.md § "1. Create
    # Directory Structure" (same shape test_slice1_equivalence.py documents).
    _SKILL_DIR.parent / "cfe-recipe-lifecycle" / "active" / "cfe-recipe-lifecycle"
)
_COMPILED_SCRIPTS_DIR = _COMPILED_PACKAGE_DIR / "scripts"

# Slice 2's 22 canonical scripts + the 3 sanctioned Slice-5 shared-infra
# runtime deps (_http.py, _paths.py, _cfy_template.py) -- the brief's own
# scope.include list, minus nothing (this is the presence check, not the
# CLI-invocable subset used by test_help_output_identical below).
_SLICE2_ALL_SCRIPTS = (
    "validate_recipe.py", "recipe_editor.py", "recipe_optimizer.py",
    "recipe_updater.py", "npm_updater.py", "dependency-checker.py",
    "license-checker.py", "mapping_manager.py", "feedstock-migrator.py",
    "local_builder.py", "failure_analyzer.py", "submit_pr.py",
    "feedstock_lookup.py", "feedstock_context.py", "feedstock_enrich.py",
    "_path_guard.py", "gen_yml_reference.py", "test-skill.py",
    "vulnerability_scanner.py", "pr_artifacts.py", "github_version_checker.py",
    "health_check.py", "_http.py", "_paths.py", "_cfy_template.py",
)

# The 20 of the above with their own `if __name__ == "__main__":` + argparse
# CLI (the other 5 -- _path_guard.py, test-skill.py, _http.py, _paths.py,
# _cfy_template.py -- are library modules / a non-CLI ad-hoc script, per
# slice-map.md and this story's own compile-time confirmation).
_CLI_INVOCABLE_SCRIPTS = (
    "validate_recipe.py", "recipe_editor.py", "recipe_optimizer.py",
    "recipe_updater.py", "npm_updater.py", "dependency-checker.py",
    "license-checker.py", "mapping_manager.py", "feedstock-migrator.py",
    "local_builder.py", "failure_analyzer.py", "submit_pr.py",
    "feedstock_lookup.py", "feedstock_context.py", "feedstock_enrich.py",
    "vulnerability_scanner.py", "pr_artifacts.py", "github_version_checker.py",
    "health_check.py",
    # gen_yml_reference.py is deliberately excluded here -- see
    # test_gen_yml_reference_help_diverges_by_known_path_depth_bug below,
    # which documents and proves the one known, explained exception rather
    # than silently omitting it from this file entirely.
)


def _compiled_package_available() -> bool:
    return _COMPILED_SCRIPTS_DIR.is_dir() and all(
        (_COMPILED_SCRIPTS_DIR / name).is_file() for name in _SLICE2_ALL_SCRIPTS
    )


pytestmark = pytest.mark.skipif(
    not _compiled_package_available(),
    reason=(
        "compiled replacement not found at "
        f"{_COMPILED_SCRIPTS_DIR} -- run skf-brief-skill + skf-create-skill "
        "against slice-2's scope first (see campaign-state.yaml)"
    ),
)


def _run(scripts_dir: Path, script: str, *args: str, timeout: int = 30, env=None):
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, str(scripts_dir / script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=run_env,
    )


@pytest.mark.slow
@pytest.mark.parametrize("script", _CLI_INVOCABLE_SCRIPTS)
def test_help_output_identical(script):
    """`--help` output must be byte-identical between the original and the
    compiled replacement's copy -- proves the copy operation preserved the
    argparse-derived usage text verbatim, a cheap, deterministic, fully
    offline proxy for "the file itself did not change" (same rationale as
    Slice 1's own version of this check)."""
    original = _run(_ORIGINAL_SCRIPTS_DIR, script, "--help")
    compiled = _run(_COMPILED_SCRIPTS_DIR, script, "--help")
    assert original.returncode == compiled.returncode == 0
    assert original.stdout == compiled.stdout


@pytest.mark.slow
def test_gen_yml_reference_help_diverges_by_known_path_depth_bug():
    """`gen_yml_reference.py` is excluded from the parametrized
    byte-identity check above because its `--help` text embeds a
    `Path(__file__).resolve().parents[4]`-derived default output directory
    (`REPO_ROOT`) that is genuinely, unavoidably different at the compiled
    package's deeper nesting -- this is the module docstring's documented
    finding, proven here rather than merely asserted in prose. Everything
    OTHER than that one embedded path must still agree, so this test
    verifies the divergence is exactly, and only, that one known cause."""
    original = _run(_ORIGINAL_SCRIPTS_DIR, "gen_yml_reference.py", "--help")
    compiled = _run(_COMPILED_SCRIPTS_DIR, "gen_yml_reference.py", "--help")
    assert original.returncode == compiled.returncode == 0
    if original.stdout == compiled.stdout:
        # If a future re-run of this test finds the outputs now agree (e.g.
        # the campaign adopted a relocation-aware path helper), that is
        # good news, not a failure -- nothing left to prove here.
        return
    original_lines = original.stdout.splitlines()
    compiled_lines = compiled.stdout.splitlines()
    assert len(original_lines) == len(compiled_lines), (
        "expected only the wrapped embedded-path lines to differ, not a "
        "structural change in --help's own line count"
    )
    diverging = [
        (o, c) for o, c in zip(original_lines, compiled_lines) if o != c
    ]
    assert len(diverging) == 1, (
        f"expected exactly one diverging line (the embedded REPO_ROOT "
        f"default path), found {len(diverging)}: {diverging}"
    )
    orig_line, comp_line = diverging[0]
    # The live original's line ends mid-word in "conda-forge-" (argparse
    # wraps the long default path across lines, so "expert" is the next
    # line's own content, not this one's); the compiled copy's
    # corresponding line has an EXTRA ".claude/skills" segment inserted --
    # the exact signature of the parents[4]-at-the-wrong-depth bug this test
    # exists to pin down (one level short of the real repo root), not some
    # unrelated content change.
    assert orig_line.endswith("conda-forge-")
    assert comp_line == orig_line.replace(
        ".claude/skills/conda-forge-", ".claude/skills/.claude/skills/conda-forge-"
    )


@pytest.mark.slow
def test_recipe_editor_update_action_identical(tmp_path):
    """`recipe_editor.py <path> <actions_json>` end-to-end, run against both
    locations via the module's own sanctioned `CFE_RECIPES_ROOT` env-var +
    absolute-path integration seam (the same pattern `tests/conftest.py`'s
    `copy_recipe` fixture uses for the live regression suite), must produce
    byte-identical output files and JSON results.

    This is Slice 2's representative WRITE-ORIENTED deep check (per the
    spec's Design Notes: one write-oriented, one network-touching, one
    error-path script). Deliberately does NOT probe a relative-path
    invocation -- see this module's own docstring for why that specific
    pattern is a known, separately-documented divergence, not something this
    check would legitimately assert "identical" for.
    """
    original_dir = tmp_path / "original"
    compiled_dir = tmp_path / "compiled"
    original_dir.mkdir()
    compiled_dir.mkdir()
    recipe_body = (
        "schema_version: 1\n"
        "context:\n  version: 1.0.0\n"
        "package:\n  name: equiv-test\n  version: ${{ version }}\n"
        "build:\n  number: 0\n"
    )
    (original_dir / "recipe.yaml").write_text(recipe_body)
    (compiled_dir / "recipe.yaml").write_text(recipe_body)
    actions = json.dumps([{"action": "update", "path": "build.number", "value": 42}])

    original = _run(
        _ORIGINAL_SCRIPTS_DIR, "recipe_editor.py",
        str(original_dir / "recipe.yaml"), actions,
        env={"CFE_RECIPES_ROOT": str(original_dir)},
    )
    compiled = _run(
        _COMPILED_SCRIPTS_DIR, "recipe_editor.py",
        str(compiled_dir / "recipe.yaml"), actions,
        env={"CFE_RECIPES_ROOT": str(compiled_dir)},
    )
    assert original.returncode == 0, f"original failed: {original.stdout}{original.stderr}"
    assert compiled.returncode == 0, f"compiled failed: {compiled.stdout}{compiled.stderr}"
    assert json.loads(original.stdout) == json.loads(compiled.stdout)
    assert (original_dir / "recipe.yaml").read_text() == (compiled_dir / "recipe.yaml").read_text()


@pytest.mark.slow
def test_validate_recipe_missing_path_error_shape_identical():
    """A deliberately-nonexistent recipe path exercises `validate_recipe.py`'s
    error path fully offline and deterministically -- Slice 2's
    representative ERROR-PATH deep check."""
    bogus = "/tmp/definitely-not-a-real-recipe-path-xyz-equivalence-probe.yaml"
    original = _run(_ORIGINAL_SCRIPTS_DIR, "validate_recipe.py", bogus, "--json")
    compiled = _run(_COMPILED_SCRIPTS_DIR, "validate_recipe.py", bogus, "--json")
    assert original.returncode == compiled.returncode
    assert original.stdout == compiled.stdout
    assert json.loads(original.stdout)["passed"] is False


@pytest.mark.slow
def test_github_version_checker_network_error_shape_identical():
    """A deliberately-bogus GitHub repo exercises `github_version_checker.py`'s
    full network-touching path -- Slice 2's representative NETWORK-TOUCHING
    deep check (same shape as Slice 1's own `github_updater.py` gap-closure
    test). Deterministic regardless of the live network response: a 404, a
    rate-limit response, or a transient failure all still produce a clean
    JSON `error` string via the script's own exception handling, never an
    uncaught traceback, on either side."""
    original = _run(
        _ORIGINAL_SCRIPTS_DIR, "github_version_checker.py",
        "--repo", "example/definitely-not-a-real-repo-xyz-equiv-probe", "--json",
        timeout=60,
    )
    compiled = _run(
        _COMPILED_SCRIPTS_DIR, "github_version_checker.py",
        "--repo", "example/definitely-not-a-real-repo-xyz-equiv-probe", "--json",
        timeout=60,
    )
    assert original.returncode == compiled.returncode
    assert original.stdout == compiled.stdout
    assert json.loads(original.stdout)["success"] is False
