---
skill_name: cfe-recipe-lifecycle
generated: 2026-08-28
forge_tier: Quick
t2_future_count: 0
---

# Compilation Evidence Report — cfe-recipe-lifecycle 1.0.0

## Source

- Source type: `source` (local path)
- Source repo: `.` (local-recipes, this repo)
- Source root: `.claude/skills/conda-forge-expert`
- Source commit: `ffcdcce7163b05efb701bb0bb11c4e8bfd74dca5`
- Source ref: `local`
- Brief: `_bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/cfe-recipe-lifecycle/skill-brief.yaml`
  (recovered verbatim from Story 12.6's session transcript, schema-validated `valid: true`
  before this compile ran)

## Tool Versions

- skf: 2.0.1
- ast-grep: unavailable (Quick tier)
- qmd: unavailable (Quick tier)
- gh_cli: 2.98.0 (available, not used by this extraction)

## Forge Tier

**Quick.** No `ast-grep`/`qmd`/`ccc` detected in this worktree
(`_bmad/_memory/forger-sidecar/forge-tier.yaml`, written by `skf-setup --headless` at the
start of this story). Per Story 12.3's finding, `forge-tier.yaml` is gitignored
per-worktree state and does not carry forward from a prior worktree — it was regenerated
fresh here via the real `skf-detect-tools.py` / `skf-forge-tier-rw.py` scripts.

## Extraction Summary

- 25 source files scanned (22 canonical Slice-2 scripts + 3 sanctioned Slice-5
  cross-slice runtime dependencies: `_http.py`, `_paths.py`, `_cfy_template.py`)
- 10,809 total source lines
- 265 exports extracted: 169 top-level functions (public), 88 internal
  (underscore-prefixed) functions/methods, 8 top-level classes (public)
- 0 parse failures (`extraction-rules.yaml`'s `python3 ast.parse` ran clean on all 25 files)
- Extraction method: deterministic Python-`ast`-module parse (`python-ast-quick-tier`,
  see `extraction-rules.yaml`) — not a manual/LLM source read. Every entry in
  `provenance-map.json` traces to a real `ast.FunctionDef`/`AsyncFunctionDef`/`ClassDef`
  node at a real line number in the live source tree; nothing was inferred or guessed.
- Confidence distribution: 265 T1-low, 0 T1, 0 T2, 0 T3 (Quick tier ceiling — see
  `metadata.json.confidence_distribution`)
- All 25 files copied byte-identical into `scripts/` and sha256-verified against the live
  source before this report was written

## Provenance-Map Persistence

Unlike Slice 1's original compile (Stories 6.1–6.3), which ran in an ephemeral agent
worktree and never persisted `provenance-map.json` anywhere durable — forcing Story 12.3
to reconstruct a `file_entries[]`-only substitute with an empty `entries[]` — this compile
writes a real, non-empty per-export baseline (265 `entries[]` rows) directly to
`forge-data/cfe-recipe-lifecycle/1.0.0/provenance-map.json` in this tracked worktree, and
that file is committed alongside this report per Story 12.7's own explicit task ("this one
must not be allowed to go unpersisted").

## CLI-Wrapper / Package Scope Decision

Slice 2's brief lists 17 `.claude/scripts/conda-forge-expert/*.py` CLI wrapper files under
`scope.include` alongside the 22 canonical scripts. This compile does **not** copy those
wrapper files into the package's `scripts/` directory: each is a ~15-line `subprocess`
shim with a hardcoded path back into the LIVE `.claude/skills/conda-forge-expert/scripts/`
tree (confirmed by reading `validate_recipe.py`'s and `prepare_pr.py`'s wrapper source
directly), so a verbatim copy would not be a self-contained replacement — it would still
delegate to the live original at runtime, which would silently corrupt the equivalence
harness's "compiled vs. live" comparison for the wrapped script and defeat the point of
"compiled". This mirrors Slice 1's own precedent: `cfe-recipe-generation`'s package
likewise omits every doc/guide file its own brief's `scope.include` named (they were
folded into `references/*.md` content, not copied as literal files) — `scope.include` is
this campaign's source-citation list, not a byte-for-byte manifest. Each wrapper's
pixi-task/MCP-tool role is documented in prose in the relevant `references/*.md` file and
in `SKILL.md`'s own Design Notes section instead.

## Regression Pass: Two Genuine Gaps Found and Closed

Running the 21 mapped unit-test files (per Story 12.7's Code Map) with
`CFE_TEST_SCRIPTS_DIR` pointed at this compiled package initially surfaced 3 failures
against the 206-pass/1-xpass/3-deselected baseline (unmodified `CFE_TEST_SCRIPTS_DIR`,
live originals). Both root causes were genuine, previously-undocumented gaps in
slice-map.md / the brief's `scope.include` — closed by porting sanctioned dependencies,
the same precedent Story 6.3 established for Slice 1's `github_version_checker.py`:

1. **`scripts/cross-shims/install_name_tool`** (2 test failures,
   `test_local_builder.py::test_cross_shim_dir_ships_install_name_tool` and
   `::test_build_one_platform_prepends_cross_shim_dir_for_osx`) — `local_builder.py`
   hardcodes `Path(__file__).resolve().parent / "cross-shims"` at runtime for osx
   cross-compile shimming. A genuine Slice-2 functional asset, not named anywhere in
   slice-map.md or the brief. Ported byte-identical (sha256-verified), tracked in
   `provenance-map.json` `file_entries[]` as `file_type: "asset"`, and reflected in
   `metadata.json.assets[]` / `stats.assets_count: 1`.
2. **`scripts/github_updater.py` + `scripts/recipe-generator.py`** (1 test failure,
   `test_recipe_updater_interpreter.py::test_all_internal_recipe_editor_callers_agree_on_resolution_pattern`)
   — both Slice 1's own canonical scripts. No Slice-2 script imports either at runtime
   (re-confirmed; not a code-level cross-slice dependency). The failing test is a
   repo-wide interpreter-resolution drift guard that loads `recipe_updater.py` +
   `github_updater.py` + `npm_updater.py` + `recipe-generator.py` together from one
   `SCRIPTS_DIR` — a structural coupling in the live test suite that spans both slices'
   scripts and cannot be satisfied by any single slice's compiled package alone. Ported
   byte-identical from the live source purely as cross-slice test-fixture siblings;
   **not** added to `metadata.json.scripts[]` or `stats.scripts_count` (stays 25 — Slice
   2's real functional inventory is unchanged), tracked only via `provenance-map.json`
   `file_entries[]` (`extraction_method: "file-copy-cross-slice-test-fixture"`) for
   honesty.

After both ports, the full 21-file regression suite reports **206 passed, 3 deselected
(network), 1 xpassed** against the compiled package — identical to the unmodified-
`CFE_TEST_SCRIPTS_DIR` baseline, with zero test-body edits on either side.

## Equivalence Harness: Path-Depth Finding (documented, not patched)

`test_slice2_equivalence.py` (23 checks, all passing) proves and documents a genuine,
pre-existing fragility that ships with this compiled package rather than hiding it:
five of the 25 scripts (`_path_guard.py`, `_paths.py`, `gen_yml_reference.py`,
`mapping_manager.py`, `vulnerability_scanner.py`) compute a repo-root or skill-data-dir
path via a hardcoded `Path(__file__)` parent-hop count rather than a directory-depth-
independent marker walk. At this package's deeper nesting
(`.claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/scripts/` vs. the live
tree's `.claude/skills/conda-forge-expert/scripts/`), those constants resolve one
directory level short of the real repo root. Confirmed live for `recipe_editor.py`
(imports `_path_guard`) with a `recipes/`-relative path: the original succeeds, the
compiled copy rejects it as "Recipe directory does not exist:
.../.claude/skills/recipes/...". `_paths.py`'s own module docstring (Story 5.5, a past
Rule-2 retro) already documents ~30-35 live-tree scripts sharing this exact
hardcoded-depth pattern, so this is inherited, campaign-wide technical debt, not
something this compile introduced — expected to recur for every future slice with
similarly-hardcoded scripts.

**Deliberately not patched.** This story's scope is compile + validate, not remediate
pre-existing CFE debt; every one of the 25 tracked scripts (plus the 1 asset and the 2
test-fixture-only scripts) remains sha256-identical to its live source. Every existing
regression test and every `test_slice2_equivalence.py` check legitimately reports zero
divergence because each was written to avoid this specific landmine — using absolute
paths plus `_path_guard`'s own sanctioned `CFE_RECIPES_ROOT` override, exactly as
`tests/conftest.py`'s own `copy_recipe` fixture does for the live suite. Recorded here,
in `SKILL.md`'s Design Notes, and in `campaign-state.yaml`'s slice-2 `next_action` — not
inside a test assertion that would misrepresent it as passing or failing.

## Validation

- `skf-validate-brief-schema.py` on the brief (pre-compile): `valid: true`, 0 errors, 0 warnings
- `skf-render-metadata-stats.py` coherence check: `ok: true`, 0 violations (265 documented
  exports, distribution sums to 265, matching `len(entries)` exactly — the exact class of
  miscount this helper exists to prevent)

## Warnings

None. No parse failures, no missing source files, no schema violations.

## Auto-Decisions

No auto-decisions — this compile was driven directly via the shared deterministic scripts
(`skf-detect-tools.py`, `skf-forge-tier-rw.py`, `skf-validate-brief-schema.py`,
`skf-render-metadata-stats.py`) plus a dedicated AST-extraction script, not the interactive
gate-driven `skf-create-skill` conversation flow — there were no confirmation/choice gates
to auto-resolve.
