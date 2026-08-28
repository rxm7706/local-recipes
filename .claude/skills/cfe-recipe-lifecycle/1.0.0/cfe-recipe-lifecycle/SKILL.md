---
name: cfe-recipe-lifecycle
description: >
  Everything a conda-forge recipe goes through after it exists: validate, optimize,
  security-scan, diagnose a failed build, autotick/update against upstream
  (GitHub/npm/PyPI), migrate v0-to-v1, and submit to staged-recipes -- plus the
  feedstock-context and pre-submission checks that gate a safe push. Use when a
  recipe.yaml already exists and needs to progress through review, CI, or a version
  bump; recipe creation from an upstream source is cfe-recipe-generation's job, not
  this skill's.
---

# cfe-recipe-lifecycle

## Overview

Packages conda-forge/local-recipes' Slice 2 "Recipe Lifecycle" scripts -- 22 canonical
scripts (10,124 lines) plus 3 sanctioned Slice-5 shared-infrastructure runtime
dependencies (`_http.py`, `_paths.py`, `_cfy_template.py` -- 1,483 lines) -- as a
standalone, source-cited skill. 25 scripts, 10,809 lines total. Source: local path
`.claude/skills/conda-forge-expert/` (source_ref: `local`). Forge tier: **Quick**
(source-reading extraction via the Python `ast` module -- deterministic, non-fabricating,
T1-low confidence throughout; no ast-grep CLI available at compile time). 265 exports
documented (177 public: 169 top-level functions + 8 top-level classes; 88 internal
underscore-prefixed helpers).

Companion to `cfe-recipe-generation` (Slice 1, recipe *creation*). This is Slice 2 of
the `conda-forge-expert` rebuild campaign (mason Epic 12, Story 12.7). Governing
artifacts: `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/
spec-conda-forge-expert-rebuild/{SPEC.md,slice-map.md,campaign-state.yaml}`.

**Parallel-run only.** This compiled package is not wired to any caller (no pixi task,
no MCP tool, no `pyforge.mason.cfe` adapter resolves here). The live
`.claude/skills/conda-forge-expert/` tree remains the sole authoritative implementation
until the campaign's single end cutover (SPEC.md CAP-3 clause c).

## Quick Start

22 independent CLIs, one per canonical script, invoked as `python <script>.py [args]`
from the compiled package's `scripts/` directory (or via the live skill's pixi tasks,
which call the *live*, not this compiled, copy). Grouped by function below; full
signatures and provenance in `references/`.

**Validate + optimize a recipe:**
```bash
python scripts/validate_recipe.py recipes/<name>/recipe.yaml
python scripts/recipe_optimizer.py recipes/<name>/recipe.yaml
```

**Check + update dependencies/version:**
```bash
python scripts/dependency-checker.py recipes/<name>/recipe.yaml
python scripts/recipe_updater.py recipes/<name>
python scripts/npm_updater.py recipes/<name>
python scripts/github_version_checker.py owner/repo --current-version 1.2.3
```

**Build locally + diagnose a failure:**
```bash
python scripts/local_builder.py recipes/<name>
python scripts/failure_analyzer.py <build-log-path>
```

**Security scan:**
```bash
python scripts/vulnerability_scanner.py recipes/<name>/recipe.yaml
```

**Pre-submission feedstock context, then submit:**
```bash
python scripts/feedstock_lookup.py <package-name>
python scripts/feedstock_context.py <package-name>
python scripts/submit_pr.py recipes/<name> --prepare-only   # phase 1: push branch
python scripts/submit_pr.py recipes/<name>                  # phase 2: open PR
```

**Migrate v0 -> v1:**
```bash
python scripts/feedstock-migrator.py <feedstock-name>
```

Every CLI prints a JSON result to stdout; see each `references/*.md` file for the
CLI-wrapper / pixi-task / MCP-tool mapping and full per-script export list.

## Common Workflows

**Pre-submission gate (G58: check before you submit):**
`lookup_feedstock` [SRC:scripts/feedstock_lookup.py] confirms the package is not already
on conda-forge -> `get_feedstock_context` [SRC:scripts/feedstock_context.py] surfaces open
issues on the existing feedstock (if any) -> `enrich_from_feedstock`
[SRC:scripts/feedstock_enrich.py] folds live feedstock metadata into a freshly-generated
recipe before it is submitted.

**Validate -> optimize -> scan, before opening a PR:**
`validate_recipe` [SRC:scripts/validate_recipe.py] (schema + policy conformance) ->
`optimize_recipe`/`recipe_optimizer` [SRC:scripts/recipe_optimizer.py] (style/quality
check codes, preserved verbatim per Mason FR-11) -> `scan_for_vulnerabilities`
[SRC:scripts/vulnerability_scanner.py] (CVE-DB closure scan) -- all three findings sets
are rendered without local severity/threshold policy (Mason FR-12).

**Build failed -> diagnose -> fix:**
`local_builder` [SRC:scripts/local_builder.py] produces a build log ->
`failure_analyzer` [SRC:scripts/failure_analyzer.py] names a cause + proposed fix from
the failure-catalog knowledge base, or states plainly that no diagnosis was produced
(Mason FR-10's "no cause, guess, or suggestion of its own" contract).

**Autotick-style version refresh:**
`recipe_updater` [SRC:scripts/recipe_updater.py] (generic/PyPI-sourced) or `npm_updater`
[SRC:scripts/npm_updater.py] (npm-sourced) -- both compare the pinned version against the
latest upstream release and show the diff before writing (Mason FR-14: "never apply a
change I have not read").

**Two-phase staged-recipes submission:**
`submit_pr` [SRC:scripts/submit_pr.py] `--prepare-only` (phase 1: push the recipe branch
to the user's fork) then `submit_pr` without the flag (phase 2: open the PR) -- the
`prepare_pr` CLI wrapper is a thin `--prepare-only` alias over the same script, not a
second implementation.

**v0 feedstock migration:**
`feedstock-migrator` [SRC:scripts/feedstock-migrator.py] is a REMOTE-feedstock tool (G84)
-- it converts an existing conda-forge feedstock's `meta.yaml` to `recipe.yaml`; it
cannot convert a local `recipes/<name>/` directory.

## Key API Summary

| Script | Top public export(s) | Purpose |
|---|---|---|
| `validate_recipe.py` | see `references/validation-and-optimization.md` | Validate a recipe.yaml/meta.yaml against conda-forge policy |
| `recipe_optimizer.py` | see `references/validation-and-optimization.md` | Quality/style check codes (`optimize_recipe`) |
| `recipe_editor.py` | see `references/validation-and-optimization.md` | Programmatic recipe.yaml field edits (`edit_recipe` MCP tool) |
| `recipe_updater.py` | see `references/autotick-and-update.md` | Version/source update from PyPI/generic sources |
| `npm_updater.py` | see `references/autotick-and-update.md` | Autotick-style update for npm-sourced recipes |
| `github_version_checker.py` | see `references/autotick-and-update.md` | GitHub release/tag + HEAD lookup |
| `dependency-checker.py` | see `references/dependency-and-license.md` | Cross-check run/host deps against conda-forge |
| `license-checker.py` | see `references/dependency-and-license.md` | Verify/derive LICENSE metadata |
| `mapping_manager.py` | see `references/dependency-and-license.md` | PyPI<->conda-forge name mapping cache |
| `local_builder.py` | see `references/build-and-diagnose.md` | Native/local rattler-build orchestration |
| `failure_analyzer.py` | see `references/build-and-diagnose.md` | Diagnose a failed build log |
| `feedstock-migrator.py` | see `references/migration.md` | v0 meta.yaml -> v1 recipe.yaml (remote feedstock only) |
| `submit_pr.py` | see `references/submission-and-feedstock-context.md` | Two-phase staged-recipes PR submission |
| `feedstock_lookup.py` | see `references/submission-and-feedstock-context.md` | Does this package already exist on conda-forge? |
| `feedstock_context.py` | see `references/submission-and-feedstock-context.md` | Pre-submission feedstock health/issue checks |
| `feedstock_enrich.py` | see `references/submission-and-feedstock-context.md` | Enrich a draft recipe from live feedstock context |
| `_path_guard.py` | see `references/submission-and-feedstock-context.md` | Confine file ops to `<cfe-root>/recipes/` |
| `vulnerability_scanner.py` | see `references/security-and-artifacts.md` | Scan a recipe closure against the local CVE DB |
| `pr_artifacts.py` | see `references/security-and-artifacts.md` | Download CI artifacts from a staged-recipes PR |
| `gen_yml_reference.py` | see `references/dev-tooling.md` | Regenerate `*-reference-full.md` docs |
| `health_check.py` | see `references/dev-tooling.md` | conda-forge-expert environment health check |
| `test-skill.py` | see `references/dev-tooling.md` | Ad-hoc smoke script (not the real test harness) |
| `_http.py` / `_paths.py` / `_cfy_template.py` | see `references/shared-infrastructure.md` | Shared helpers (Slice 5, no wrapper/MCP of their own) |

Full 265-export inventory (per-script signatures, source lines, params, return types):
one `references/*.md` file per functional group, listed above.

## Key Types

The 8 top-level classes are all lightweight result records (`NamedTuple`/dataclass
field containers with no behavior methods -- confirmed by AST extraction, not assumed):
`ValidationResult` [SRC:scripts/validate_recipe.py:L34] (`NamedTuple`),
`OptimizationSuggestion` [SRC:scripts/recipe_optimizer.py:L65] (`NamedTuple`),
`DependencyCheck` [SRC:scripts/dependency-checker.py:L149],
`ErrorPattern` [SRC:scripts/failure_analyzer.py:L28],
`MigrationResult` [SRC:scripts/feedstock-migrator.py:L29],
`FeedstockLookupResult` [SRC:scripts/feedstock_lookup.py:L52],
`IssueSummary` [SRC:scripts/feedstock_context.py:L49],
`FeedstockContext` [SRC:scripts/feedstock_context.py:L62].

## Architecture at a Glance

- **Validation/quality tier**: `validate_recipe.py` (schema + policy) and
  `recipe_optimizer.py` (style/quality check codes) run independently; both preserve
  CFE's identifiers verbatim (no renumbering/re-severitying, per Mason FR-8/FR-11).
- **Dependency tier**: `dependency-checker.py` (run/host dep existence),
  `license-checker.py` (LICENSE metadata), `mapping_manager.py` (the PyPI<->conda-forge
  name cache both of the above and Slice 1's `name_resolver.py` read).
- **Update tier**: `recipe_updater.py` / `npm_updater.py` / `github_version_checker.py`
  (the last is a sanctioned Slice-1 cross-slice runtime dependency of
  `github_updater.py`'s HEAD-advance path -- see slice-map.md's Slice-5
  cross-slice-shared-imports table -- but stays Slice 2 canonical here, with its own
  wrapper and MCP tool).
- **Build/diagnose tier**: `local_builder.py` produces a build log,
  `failure_analyzer.py` consumes it against a failure-catalog knowledge base
  (`config/failure-catalog.yaml`, generated by the out-of-scope
  `failure_catalog_generator.py` -- see Design Notes below).
- **Security tier**: `vulnerability_scanner.py` reads a local CVE database file that
  Slice 3's `cve_manager.py` builds -- a DATA dependency, not a CODE import (re-confirmed
  clean by Story 12.6's cross-slice re-derivation; no Python `import cve_manager` line
  exists in this slice).
- **Submission tier**: `submit_pr.py` (two-phase: prepare branch, then open PR) is
  gated by the pre-submission checks (`feedstock_lookup.py`, `feedstock_context.py`,
  `feedstock_enrich.py`) and confines all file writes via `_path_guard.py`.
- **Migration tier**: `feedstock-migrator.py` is a standalone remote-feedstock v0->v1
  converter, decoupled from the rest of this slice.
- **Shared infrastructure** (Slice 5, ported verbatim per the sanctioned cross-slice
  pattern `_cfy_template.py` established in Slice 1): `_http.py` (enterprise-safe HTTP
  client), `_paths.py` (repo-root/CFE-root resolution), `_cfy_template.py`
  (`conda-forge.yml` rendering, imported by `submit_pr.py`).

## CLI

```bash
python scripts/validate_recipe.py <recipe-path>
python scripts/recipe_optimizer.py <recipe-path>
python scripts/recipe_updater.py <recipe-dir> [--dry-run]
python scripts/npm_updater.py <recipe-dir> [--dry-run]
python scripts/dependency-checker.py <recipe-path>
python scripts/license-checker.py <recipe-path>
python scripts/mapping_manager.py [--refresh]
python scripts/feedstock-migrator.py <feedstock-name>
python scripts/local_builder.py <recipe-dir>
python scripts/failure_analyzer.py <build-log-path>
python scripts/submit_pr.py <recipe-dir> [--prepare-only]
python scripts/feedstock_lookup.py <package-name>
python scripts/feedstock_context.py <package-name>
python scripts/gen_yml_reference.py
python scripts/vulnerability_scanner.py <recipe-path>
python scripts/pr_artifacts.py <pr-number>
python scripts/github_version_checker.py <owner/repo> [--current-version X]
python scripts/health_check.py
```
Every CLI prints a JSON result to stdout; see `references/*.md` per-script sections for
the exact argv shape and the pixi-task/MCP-tool mapping each one backs in the live skill.

## Scripts & Assets

25 scripts (Slice 2's own functional inventory), 10,809 lines, copied byte-identical
from source (sha256-verified, content preserved per skf-create-skill's own
script-bundling contract). Plus 1 genuine functional asset
(`scripts/cross-shims/install_name_tool`, hardcoded-path-referenced by
`local_builder.py` at runtime) and 2 cross-slice test-fixture-only script copies
(`scripts/github_updater.py`, `scripts/recipe-generator.py` -- Slice 1's own scripts,
NOT counted in the 25 above or in `metadata.json.stats.scripts_count`) -- see Design
Notes below for why. `config/failure-catalog.yaml` is a knowledge source folded into
`references/build-and-diagnose.md`, not a runtime-loaded asset of any in-scope script --
also see Design Notes.

| Script | Lines |
|---|---|
| `scripts/validate_recipe.py` | 484 |
| `scripts/recipe_editor.py` | 184 |
| `scripts/recipe_optimizer.py` | 1,123 |
| `scripts/recipe_updater.py` | 172 |
| `scripts/npm_updater.py` | 509 |
| `scripts/dependency-checker.py` | 838 |
| `scripts/license-checker.py` | 347 |
| `scripts/mapping_manager.py` | 251 |
| `scripts/feedstock-migrator.py` | 301 |
| `scripts/local_builder.py` | 688 |
| `scripts/failure_analyzer.py` | 1,026 |
| `scripts/submit_pr.py` | 438 |
| `scripts/feedstock_lookup.py` | 259 |
| `scripts/feedstock_context.py` | 237 |
| `scripts/feedstock_enrich.py` | 266 |
| `scripts/_path_guard.py` | 97 |
| `scripts/gen_yml_reference.py` | 326 |
| `scripts/test-skill.py` | 11 |
| `scripts/vulnerability_scanner.py` | 486 |
| `scripts/pr_artifacts.py` | 747 |
| `scripts/github_version_checker.py` | 313 |
| `scripts/health_check.py` | 223 |
| `scripts/_http.py` | 1,321 |
| `scripts/_paths.py` | 58 |
| `scripts/_cfy_template.py` | 104 |

<!-- [MANUAL:additional-notes] -->
**Design Notes (compile-time, non-manual but preserved for reader context):**
- `.claude/scripts/conda-forge-expert/*.py` CLI wrapper files (17 of them, named in this
  skill's own brief `scope.include`) are **not** copied into this package's `scripts/`
  directory. Each wrapper is a ~15-line `subprocess` shim whose `_SKILL_SCRIPT` path is
  hardcoded to the LIVE `.claude/skills/conda-forge-expert/scripts/` tree (confirmed by
  reading `validate_recipe.py`/`prepare_pr.py` wrappers directly) -- copying them verbatim
  would not make them self-contained replacements, it would just make a second file that
  still delegates to the live original, corrupting any equivalence comparison. This
  matches Slice 1's own precedent: `cfe-recipe-generation`'s compiled package likewise
  contains zero CLI-wrapper files even though its brief's `scope.include` listed guide/
  reference `.md` docs that also did not appear as literal copied files (they were folded
  into `references/*.md` content instead, the same treatment given here). The wrapper
  files' role -- which pixi task and MCP tool each script backs -- is documented in prose
  in each `references/*.md` file instead.
- `failure_catalog_generator.py` is deliberately NOT part of this package. Slice 2's own
  brief documents it as a new, previously-unclassified script (added 2026-08-22, one
  commit after slice-map.md's derivation) that operationally supports this slice's
  build-failure-diagnosis knowledge but is flagged for a future slice-map.md correction
  pass, not silently absorbed here.
- **Two genuine, previously-undocumented gaps surfaced by the regression pass** (Story
  12.7's own BLOCKED-then-retry budget, resolved by porting sanctioned dependencies, same
  precedent as Slice 1's `github_version_checker.py` port):
  1. `scripts/cross-shims/install_name_tool` -- `local_builder.py` hardcodes
     `Path(__file__).resolve().parent / "cross-shims"` at runtime for osx cross-compile
     shimming. This is a genuine Slice-2 functional asset, not named in slice-map.md or
     the brief's `scope.include`. Ported byte-identical (sha256-verified) alongside
     `local_builder.py`; `test_local_builder.py`'s two `CROSS_SHIMS_DIR`-dependent tests
     now pass identically to baseline.
  2. `scripts/github_updater.py` + `scripts/recipe-generator.py` -- both Slice 1's OWN
     canonical scripts, with **no** runtime import from any Slice-2 script (re-confirmed;
     this is not a code-level cross-slice dependency). Ported byte-identical from the
     LIVE source purely as cross-slice TEST-FIXTURE siblings, because
     `test_recipe_updater_interpreter.py::test_all_internal_recipe_editor_callers_agree_on_resolution_pattern`
     loads `recipe_updater.py` + `github_updater.py` + `npm_updater.py` +
     `recipe-generator.py` together from one `SCRIPTS_DIR` as a repo-wide interpreter-
     resolution drift guard spanning both slices. **Not** counted in
     `metadata.json.stats.scripts_count` (stays 25 -- Slice 2's real functional inventory
     is unchanged) or `scripts[]`; tracked only via `provenance-map.json`'s
     `file_entries[]` for honesty. This is a structural gap in the campaign's own
     per-slice-package test-harness model (a live-tree test file can span two slices'
     scripts; no single compiled package alone can satisfy it) -- expected to recur for
     future slices whenever a test file cross-references scripts split across slice
     boundaries; flagged in `campaign-state.yaml`'s slice-2 `next_action` for the
     campaign's own future attention, not fixed at the campaign-structure level here.
- **A third, broader finding (documented, not patched): hardcoded `Path(__file__)`
  parent-hop-count path arithmetic breaks at the compiled package's deeper nesting.**
  `test_slice2_equivalence.py`'s own module docstring proves this for
  `gen_yml_reference.py`'s `--help` text; the same root cause also affects
  `_path_guard.py` (`REPO_ROOT`, used by `recipe_editor.py`/`submit_pr.py`),
  `_paths.py`'s own `get_repo_root()` (used by `recipe_optimizer.py`,
  `feedstock_lookup.py`, `feedstock_context.py`), and `mapping_manager.py` /
  `vulnerability_scanner.py`'s un-`.resolve()`d `Path(__file__).parent.parent.parent.parent`
  data-dir constant -- five files total, all resolving one directory level short of the
  real repo root when invoked from this package's `scripts/` dir (confirmed for
  `recipe_editor.py` with a `recipes/`-relative path: rejected as
  "Recipe directory does not exist" against a nonexistent `.claude/skills/recipes/...`
  path). This is a genuinely **pre-existing, campaign-wide** fragility, not something
  this compile introduced: `_paths.py`'s own docstring (written for a past Rule-2 retro,
  Story 5.5) already documents ~30-35 live-tree scripts sharing this exact hardcoded-depth
  pattern, several already wrong even in the live tree. Deliberately **not patched** here
  (this story's own scope is compile + validate, not remediate pre-existing upstream
  debt, and patching would trade a clean, fully sha256-verifiable byte-identical script
  set for a partially-patched one); every script in this package remains byte-identical
  to its live source. Every existing regression test and every check in
  `test_slice2_equivalence.py` legitimately reports zero divergence because each is
  scoped to avoid this specific landmine (absolute paths + the module's own sanctioned
  `CFE_RECIPES_ROOT` override, exactly as `tests/conftest.py`'s own `copy_recipe` fixture
  does) -- this finding is recorded here and in `campaign-state.yaml`'s `next_action`,
  not hidden inside a passing or failing assertion. Not resolved at the
  campaign-structure level by this story; a durable fix (e.g. a relocation-aware shared
  path helper, or Skill-Forge itself compensating for its own directory-depth change)
  is future campaign work, worth deciding before any future slice with similarly-hardcoded
  scripts compiles.
<!-- [/MANUAL:additional-notes] -->

## Full API Reference

See `references/validation-and-optimization.md`, `references/dependency-and-license.md`,
`references/autotick-and-update.md`, `references/build-and-diagnose.md`,
`references/migration.md`, `references/submission-and-feedstock-context.md`,
`references/security-and-artifacts.md`, `references/dev-tooling.md`,
`references/shared-infrastructure.md` for the complete 265-entry export inventory (177
public, 88 internal) with full signatures, source lines, and provenance citations. See
`references/knowledge-gotchas.md` for slice 2's full gotcha-citation list (verbatim from
the brief, itself extracted programmatically from live SKILL.md) and the cross-slice
dependency re-derivation record (CVE-DB/Slice-3 data dependency confirmed clean;
`native-build.sh`/`build-locally.py` cutover scope decided permanently out of campaign
scope).

<!-- [MANUAL:api-notes] -->
<!-- Add custom API notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
