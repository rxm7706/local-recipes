---
title: 'Profile-driven adapter selection, project-scoped'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '27ccab3ab7f505c1b79ac645e220c6043118b067'
---

<intent-contract>

## Intent

**Problem:** two loop homes configured for different agents must resolve their own adapter and per-stage models independently, with zero cross-configuration and zero adapter-name branching anywhere in Marshal itself (AD-19) -- today `render_policy_toml`'s own `difficulty: str | None` parameter already renders `[adapter.<stage>].model` overrides from `core.policy.EffectivePolicy.model_tier_map` (an already-shipped STATIC key), but NOTHING resolves which difficulty a given story actually declares -- every caller passes `difficulty=None`, so the tiering machinery is fully built and permanently unused. FR-48/FR-51/AD-19 close this final gap.

**Approach:** a new, pure `core/spec_difficulty.py::parse_declared_difficulty(spec_text) -> str | None` (mirroring `core/spec_surface.py::parse_declared_surface`'s established three-way "absent (mechanical default) / present-and-parseable / present-and-malformed" discipline exactly) reads a story spec's own `difficulty:` frontmatter scalar. `cli/spin.py::run_spin` resolves the in-scope story/stories' own declared difficulty via this reader, computes the resolved per-stage models for the ACTUAL render (reusing `model_tier_map`'s already-shipped shape, never a new lookup mechanism), passes the resolved difficulty into the ALREADY-EXISTING `render_policy_toml(effective, difficulty=...)` call, and echoes + journals the resolution (adapter name, binary, resolved per-stage models) via the SAME intent/outcome journal entries `run_spin` already writes -- additive payload fields, never a new journal mechanism. Multiple in-scope stories with DIFFERENT declared difficulties (a multi-story, unscoped launch) are BATCHED: one difficulty governs the actual render (the harness supports only run-level model selection, FR-51's own explicit v1 constraint), and every story whose own declared difficulty does not match the governing one is named in a new `data.model_tier_batching` report field -- never silently ignored. A `tests/meta/test_ad19_no_adapter_branch.py` (AST-scanning, mirroring `test_ad23_inline_key_format_guard.py`'s established shape) makes the ALREADY-CLEAN "no `if adapter == '...'`" invariant an ENFORCED contract going forward, not merely an accident of today's code.

## Boundaries & Constraints

**Always:**
- **`parse_declared_difficulty` is pure (AD-4)** -- no I/O, mirrors `parse_declared_surface`'s exact three-way contract: `None` for a spec with no `difficulty:` frontmatter key at all (the mechanical-default case, never an error); the parsed scalar string for a well-formed single-line `difficulty: <value>` entry; a dedicated `DifficultyParseError` for a PRESENT-but-unsupported form (e.g. a multi-line/flow-sequence value) -- never silently collapsed into "absent."
- **The resolved per-stage models reuse `model_tier_map` verbatim** -- no new tiering data structure; a difficulty string absent from the map (including `None`, the undeclared-story case) resolves to "no override" (`render_policy_toml`'s own already-established `difficulty=None` behavior -- no `[adapter.<stage>].model` block rendered at all, the harness's own baseline model applies), never a fabricated default model.
- **Multi-story batching is REPORTED, never silently resolved.** When in-scope stories declare more than one distinct difficulty, ONE difficulty governs the actual render (the harness's own real v1 constraint: run-level, not per-story, model selection); `data.model_tier_batching` names every story whose own declared difficulty differs from the governing one, plus which difficulty actually governed and why (e.g. "most stories in this batch," "first in launch order" -- pick ONE deterministic tie-break rule and document it).
- **An unknown/unrecognized adapter name is `Verdict.UNEVALUABLE`, never a crash** -- `HarnessPort.adapter_binary`'s own already-documented `HarnessError` for an unknown adapter is caught at `run_spin`'s own boundary and reported as a registered finding, exactly like every other `HarnessError` this module already catches.
- **The resolved adapter name, binary, and per-stage models are echoed in `run_spin`'s own `data` AND journaled in the SAME outcome entry `run_spin` already writes** (`{"pid": ..., "harness_run_id": ...}` -- additive fields: `"adapter_name"`, `"resolved_models"`, `"model_tier_batching"` when applicable) -- never a second journal write, never a second echo mechanism.
- **`tests/meta/test_ad19_no_adapter_branch.py` is a NEW, non-vacuous AST-scanning meta-test** (mirrors `test_ad23_inline_key_format_guard.py`'s established shape: walks every module in `pyforge.marshal.cli`/`core`/`supervisor`/`ports` -- excluding `adapters/harness_bmadloop.py`, the one module structurally permitted to know adapter identities -- for an `ast.Compare` node testing equality between a name/attribute plausibly named `adapter`/`adapter_name` and a string constant) -- proven non-vacuous via a synthetic violation the test itself constructs and asserts the detector actually catches.
- **Marshal contains zero `if adapter == "..."` branches anywhere this story's own new code touches** -- confirmed already true today (verified by direct search before writing this spec); this story's job is to KEEP it true under the new meta-test's enforcement, not to fix an existing violation.

**Never:**
- No new per-adapter branching logic anywhere in `cli/`/`core/`/`supervisor/` -- every adapter-specific fact stays sourced from `HarnessPort`'s own existing profile-backed methods (`adapter_binary`/`adapter_seed_files`/`adapter_first_run_note`).
- No re-implementation of `render_policy_toml`'s own `difficulty` parameter or its `[adapter.<stage>].model` rendering -- reused exactly as already shipped.
- No actual multi-run orchestration for the batching case -- ONE render, ONE governing difficulty, a REPORT naming the mismatch; splitting a multi-story launch into per-tier sub-runs is out of this story's own scope (not asked for by FR-51's own explicit "batches... and reports the batching" wording).
- Do not build the probe-record read (Story 6.4's own unbuilt deliverable, referenced only forward by this AC's own text, not a formal dependency).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| A single in-scope story with no `difficulty:` frontmatter | Undeclared, mechanical default | `resolved_models: {}` (no override), reported and journaled as such | No finding |
| A single in-scope story with a declared difficulty present in `model_tier_map` | Normal case | Per-stage models resolved and rendered via `difficulty=<value>` | No finding |
| A declared difficulty NOT present in `model_tier_map` | Unmapped tier | Treated identically to undeclared (no override) -- never an error, `model_tier_map` is this project's own declared vocabulary | No finding |
| A spec's `difficulty:` frontmatter is present but malformed (multi-line/unsupported form) | Parse failure | `DifficultyParseError`, surfaced as a registered finding, never silently "absent" | Registered finding |
| Multiple in-scope stories, all declaring the SAME difficulty | Homogeneous batch | One render, no batching report | No finding |
| Multiple in-scope stories, declaring DIFFERENT difficulties | Heterogeneous batch | One governing difficulty (deterministic tie-break), `data.model_tier_batching` names every non-matching story | No finding (reported, not an error) |
| An unknown/unrecognized adapter name | Configuration error | `Verdict.UNEVALUABLE`, never a crash | Registered finding |
| Two loop homes with different configured adapters launched independently | Cross-configuration check | Each resolves its own adapter/models with zero leakage between them | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/spec_difficulty.py` -- NEW. `parse_declared_difficulty(spec_text: str) -> str | None`, `DifficultyParseError` (mirrors `core/spec_surface.py`'s exact shape/style).
- `src/pyforge/marshal/cli/spin.py` -- EDIT. `run_spin` resolves in-scope stories' declared difficulty (reading each story's own spec file, reusing whatever existing "resolve a story's own spec file path" helper this module or `cli/deploy.py` already has), computes the governing difficulty + batching report, passes it into the existing `render_policy_toml(effective, difficulty=...)` call, echoes + journals the resolution.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. Register + classify "malformed difficulty declaration" (ERROR-ish/registered finding) and "unknown adapter" (UNEVALUABLE) codes.
- `tests/meta/test_ad19_no_adapter_branch.py` -- NEW. AST-scanning meta-test, non-vacuous (a synthetic-violation self-test).
- `tests/unit/test_spec_difficulty.py` -- NEW. Full three-way parse matrix.
- `tests/unit/test_spin.py` -- EDIT. Difficulty resolution + batching + unknown-adapter matrix.

## Design Notes

- **Why `parse_declared_difficulty` mirrors `parse_declared_surface` so literally:** Story 2.3's own reader already solved the exact shape of problem this story needs solved again (a frontmatter scalar with an absent/malformed/unsupported three-way split) -- reusing its established discipline (never its code, since the two fields are semantically unrelated) keeps this codebase's own frontmatter-reading convention singular rather than letting a second, subtly-different parser drift in.
- **Why batching is a REPORT, not an orchestration:** FR-51's own PRD text is explicit -- "Where the harness supports only run-level model selection, Marshal batches stories by tier and reports the batching. [ASSUMPTION: batching is acceptable v1 behaviour; a per-story upstream key is an FR-58 request.]" -- the assumption is already accepted; this story implements exactly that assumption, not a v2 multi-run splitter.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **2715 passed** (2709 baseline + 6 new tests from the review patch pass below).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 2 failed, both the pre-existing accepted `pyforge-steward` baseline (`_http` module-alias gap, `age` conda-only run-dep), unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- AD-3, AD-4, AD-9 all KEPT.

## Review Triage Log

### 2026-08-07 -- Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 1, medium 2, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` (Blind Hunter) **The resolved model-tier policy never reached the harness.** `_resolve_model_tiering` rendered the difficulty-tiered policy in-memory (`render_policy_toml`) only to extract `adapter_name` for the preflight check, then discarded it -- the ACTUAL `.bmad-loop/policy.toml` `bmad-loop run` reads is only ever written by `write_policy_toml`, whose sole caller (`marshal config --write-harness-policy`) always passes `difficulty=None`. The outcome journal's own `resolved_models` field therefore described a model tier the spawned process never actually applied. Fixed: once the adapter resolves, `_resolve_model_tiering` now calls `write_policy_toml(effective_policy, home, difficulty=governing)`, persisting the SAME resolution it reports. A write failure (new `MRS-SPIN-015`, `Verdict.WARN`, alongside 007/013's identical "reported, never blocks an already-viable launch" tier) degrades to whatever policy was already on disk rather than aborting the launch. New tests: `test_spin_persists_the_resolved_model_tier_to_the_loop_homes_policy_toml`, `test_spin_unwritable_loop_home_degrades_policy_write_to_mrs_spin_015`.
  - `medium` `patch` (Edge Case Hunter) A trailing YAML comment on an otherwise well-formed declaration (`difficulty: heavy  # rationale`) silently fell through to `None` -- the bare-token charset check saw the comment text and rejected the whole value, discarding a real, deliberate declaration exactly the module's own docstring says must never happen. Fixed: `_strip_trailing_comment` (YAML's own whitespace-preceded/not-inside-a-quote rule) strips the comment before either the `ast.literal_eval` or bare-token branch runs. New tests: `test_present_bare_scalar_with_trailing_comment_returns_the_value`, `test_present_quoted_scalar_with_trailing_comment_returns_the_value`, `test_present_bare_scalar_with_immediately_adjacent_hash_is_not_a_comment` (a `#` not preceded by whitespace is correctly NOT treated as a comment).
  - `medium` `patch` (Edge Case Hunter) `_story_declared_difficulty`'s first-readable-candidate-wins short circuit could mask a valid declaration behind an earlier, stale, malformed sibling spec file (e.g. a `-2` re-run's well-formed `difficulty:` shadowed by the original's malformed multi-line block) -- diverging from `_large_spec_bytes`'s own "scan every candidate" discipline for the identical re-run scenario. Fixed: every candidate is now consulted; the first one that yields an actual declared value wins, and `MRS-SPIN-013` is only registered if NO candidate ultimately resolves a real value. New test: `test_spin_valid_sibling_spec_file_is_not_masked_by_an_earlier_malformed_one`.

**Follow-up review recommendation: false** -- all three findings are isolated, each covered by a dedicated new test proving the fix; no new design questions opened.

</intent-contract>
