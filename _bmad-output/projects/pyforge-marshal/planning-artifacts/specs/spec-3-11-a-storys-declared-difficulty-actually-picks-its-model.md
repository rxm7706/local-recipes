---
title: "A story's declared difficulty actually picks its model"
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering/SPEC.md']
warnings: ['oversized']
difficulty: 'heavy'
baseline_revision: '99f7415d14721c8b0e25d4308be8b047b032919a'
final_revision: '6f8d81d627'
---

<intent-contract>

## Intent

**Problem:** Story 6.1 shipped the full `model_tier_map` consumption chain (`core/policy.py`'s field, `render_policy_toml`'s tier-batching, `cli/spin.py`'s `_story_declared_difficulty`/`_resolve_governing_difficulty`/`_resolve_model_tiering`) but it has never been fed real data: grep-confirmed zero of the 8 loop-home `marshal-policy.toml` files declare a non-empty `model_tier_map`, zero tracked story specs declare `difficulty:`, and pyforge-marshal's own policy file still carries the pre-Story-6.1 placeholder comment ("vocabulary does not exist yet").

**Approach:** Populate pyforge-marshal's own `marshal-policy.toml` with a real two-tier `model_tier_map` (`heavy`/`easy`, reusing Story 6.1's own test-fixture shape), add a documented, authored `difficulty:` frontmatter field to both story-spec templates (`bmad-dev-auto`/`bmad-quick-dev` — the only two skills whose output `_story_declared_difficulty` reads), declare this spec's own `difficulty: heavy` as the first real end-to-end declaration, and add a regression test proving a populated-map launch renders differently from an empty-map one for the identical story set. No change to the already-shipped resolution chain.

## Boundaries & Constraints

**Always:** treat `core/policy.py`'s `model_tier_map` shape, `render_policy_toml`'s tier-batching (`harness_bmadloop.py:462-471`), and `cli/spin.py`'s resolution chain (`:455-730`) as complete and correct (Story 6.1) — feed it real data, never re-implement it. `difficulty:` is authored (human or drafting agent) in a story's own Tier-3 spec frontmatter, never derived from `epics.md`'s separate PM-time `Effort:` field. One difficulty governs a whole launch; a mismatched story in a batch is still reported via the existing `batching_report`/`model_tier_batching` mechanism, unchanged.

**Block If:** nothing identified — this story edits two skill templates, one project policy file, one test file, and this spec's own frontmatter; none requires a human decision mid-implementation.

**Never:** touch `core/policy.py`, `core/spec_difficulty.py`, `harness_bmadloop.py`'s tier-batching logic, or `cli/spin.py`'s resolution functions — all four are already correct per Story 6.1. Never invent a closed enum of difficulty/model names — both stay free-form strings, matching the existing validator. Never add `difficulty:` to `bmad-create-story`'s generic template — Marshal's `_story_declared_difficulty` only reads Tier-3 `spec-<key>*.md` files, which `bmad-create-story` does not produce.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Declared, mapped | Story declares `difficulty: heavy`; pyforge-marshal's `model_tier_map` has a `heavy` entry | Rendered `.bmad-loop/policy.toml` differs from baseline in exactly the `heavy` tier's stages; journaled via the existing `resolved_models`/`adapter_name` echo | No error expected |
| Undeclared | No in-scope story declares `difficulty:` | Rendered policy is the flat baseline, unchanged from today | No error expected |
| Declared, unmapped | Story declares a difficulty absent from the map | Resolves to "no override" — flat baseline, unchanged (existing behavior) | No error expected |
| Mismatched batch | Two in-scope stories declare different difficulties | Existing `_resolve_governing_difficulty` tie-break governs; `model_tier_batching` names the mismatch (existing mechanism, unchanged) | No error — WARN-shaped report only |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` -- EDIT. Replace the stale `model_tier_map` "deliberately ABSENT" placeholder bullet (lines 20-24) with a real `[model_tier_map.heavy]` (`dev = "opus"`, `review = "opus"`) / `[model_tier_map.easy]` (`dev = "haiku"`) block placed AFTER the `[[landing_rules]]` array-of-tables at the file's end (TOML scopes a bare `key = value` line to the most recently opened table — placing it earlier would silently swallow `verify_commands`/`gate_mode` into `model_tier_map.easy`; verified live). Also correct the comment's stale "`[adapter.review] model = 'fable'`" claim to the real baseline, `"opus"` (`harness_bmadloop.py:302`).
- `.claude/skills/bmad-dev-auto/spec-template.md` -- EDIT. Add `difficulty: ''` to the frontmatter block after `warnings: []`, documented inline: optional, free-form, matches a `model_tier_map` key, authored not derived, absent = mechanical default.
- `.claude/skills/bmad-quick-dev/spec-template.md` -- EDIT. Mirror the same field into its shorter frontmatter block, after `context: []`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` -- EDIT. New regression test reusing the real `_model_tier_map_policy_path` fixture (Story 6.1's own `heavy`/`easy` shape, `:3242-3256`) to prove a populated-map `run_spin` launch renders a different `.bmad-loop/policy.toml` than an empty-map launch for the identical declared-`heavy` story, and that the populated-map run's journaled outcome carries `resolved_models`/`adapter_name` via the existing `_tiering_journal_fields` echo (`:717-730`, called at `:1614` and `:1651`).
- This spec file's own frontmatter -- already declares `difficulty: 'heavy'` (see above) — the "at least one real story declares a real difficulty end to end" demonstration the AC asks for.

## Tasks & Acceptance

**Execution:**
- [x] `marshal-policy.toml` -- populate a real `model_tier_map` (`heavy`, `easy`); correct the stale review-model comment; keep TOML table placement valid (tables last).
- [x] `bmad-dev-auto/spec-template.md` -- add documented `difficulty:` frontmatter field.
- [x] `bmad-quick-dev/spec-template.md` -- mirror the same field.
- [x] `tests/unit/test_spin.py` -- new regression test: populated-map vs. empty-map render diff for the identical story set, plus journal-field assertion.

**Acceptance Criteria:**
*(Story 3.11's ACs from `epics.md`, preserved as the contract of record.)*
- Given pyforge-marshal's real, non-empty `model_tier_map` and an in-scope story declaring a matching `difficulty:`, when policy is composed and rendered, then the rendered `policy.toml` differs from the undeclared baseline in exactly the mapped stages, and the resolution is journaled at launch via the existing `_resolve_model_tiering` echo — no second mechanism
- And a documented convention exists for how a story acquires a difficulty — authored, in the story's own Tier-3 spec frontmatter (this story's own design choice per the Spec's open question)
- And pyforge-marshal's own `marshal-policy.toml` carries a real `model_tier_map` in place of the stale placeholder, and this story's own spec declares a real difficulty end to end
- And a mismatched or undeclared story within the same batch is still reported via the existing `batching_report` path, unchanged (verified, not modified)
- And a regression test proves a populated-map launch renders a different `policy.toml` than an empty-map launch for the identical story set

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel, blind)
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 2, low 1)
- defer: 0
- reject: 6 (low 6)
- addressed_findings:
  - `[medium]` `[patch]` Both `spec-template.md`'s `difficulty:` field comment said "leave blank/omit" for the mechanical default, but writing `difficulty:` with no inline value (as opposed to omitting the whole line) is a *different* case (`spec_difficulty.py`'s multi-line-block form) that raises `DifficultyParseError` → `MRS-SPIN-013` WARN, not the documented silent no-override. Fixed: reworded both templates to say "OMIT THE WHOLE LINE" and explicitly flag the bare-key trap.
  - `[medium]` `[patch]` No test guarded the *real, committed* `marshal-policy.toml` against the TOML table-ordering footgun the file's own new comment warns about, and the `easy` tier was never driven end-to-end (only `heavy` was, via the populated-vs-empty test). Fixed: new `test_the_real_pyforge_marshal_policy_declares_a_working_model_tier_map` in `test_spin.py` reads the real file directly, asserts root-level keys (`gate_mode`/`verify_commands`/`landing_rules`) survived the table placement, and renders the `easy` tier through `render_policy_toml` confirming `dev→haiku` while `review` stays at its own `opus` baseline.
  - `[low]` `[patch]` `marshal-policy.toml`'s new comment claimed "an absent stage still inherits `[adapter].model`" — false for `review`, which carries its own `[adapter.review]` baseline table distinct from `[adapter].model`; the `easy` tier (dev-only) therefore leaves review at `opus`, not a comment-implied fallback to the dev baseline. Fixed: reworded to name `review`'s own baseline explicitly and cite `easy` as the live example.
  - `[low]` `[reject]` This story's own Tier-3 spec (the "real story declares a real difficulty end to end" demonstration) lives in gitignored `implementation-artifacts/` and isn't promoted to tracked `planning-artifacts/specs/` within this diff. Not a gap: per this repo's own established convention, promotion happens as a separate post-merge action — sibling stories 3.12/3.13 (already `done`) have not been promoted either as of this pass, confirming this is normal sequencing, not something this story's own diff owns.
  - `[low]` `[reject]` The "real difficulty declared end to end" demonstration is this very story's own spec, not an independent downstream story picking a tier for unrelated reasons — called "circular." By design: the spec's own Design Notes already reason through this as deliberate dogfooding: it proves the plumbing round-trips with real, tracked data, which is exactly what the AC asks for.
  - `[low]` `[reject]` Seven of the other eight loop-home projects still carry the stale `model_tier_map` placeholder this diff replaces only for `pyforge-marshal`. Not a gap: the AC's literal wording (preserved verbatim from `epics.md`) only requires "pyforge-marshal's own `marshal-policy.toml`" — populating the other seven is out of this story's stated scope.
  - `[low]` `[reject]` The new populated-vs-empty test's "populated" half re-runs assertions similar to two pre-existing tests. Not a defect — the overlap demonstrates consistency with already-shipped coverage; the empty-map half and the cross-run diff assertions are the genuinely new contribution the AC asks for.
  - `[low]` `[reject]` Neither `bmad-dev-auto` nor `bmad-quick-dev`'s procedural steps (step-01/step-02) prompt the authoring agent to consider setting `difficulty:`, so an agent following only the steps (not reading the raw template comment) may never learn the field exists. Beyond this story's AC, which only asks for "a documented convention" — satisfied by the template's own inline documentation; wiring it into the procedural steps is a reasonable future enhancement, not a defect in this diff.
  - `[low]` `[reject]` The template's `difficulty:` field comment doesn't enumerate `spec_difficulty.py`'s full accepted syntax (bare vs. quoted forms). Low-value scope creep — the field's own parser docstring is the authoritative syntax reference; the template comment's job is pointing authors at the convention, not restating the parser contract.

## Design Notes

**Why "authored," not "derived."** The parent Spec (`spec-adaptive-model-tiering/SPEC.md`) explicitly left this open, deferring to "a downstream story's design call." `epics.md`'s own `Effort:` field (S/M/L) is a PM-time estimate `_story_declared_difficulty` never reads — a derivation heuristic off it would be a second, silently-diverging signal. Authored keeps the two axes honest: this story's own `Effort: M` in epics.md and its declared `difficulty: heavy` here are legitimately different signals, not a restatement of each other.

**Why `heavy`/`easy`, not a new vocabulary.** Story 6.1's own test fixture (`test_spin.py::_model_tier_map_policy_path`) already used exactly this shape (`heavy: {dev: opus, review: opus}`, `easy: {dev: haiku}`) as its synthetic example — reusing it for the real config keeps one vocabulary instead of two competing ones.

**Why the `model_tier_map` table sits at the file's end.** TOML scopes a bare `key = value` line to the most recently opened `[table]`; `model_tier_map` is a dotted-table key (`[model_tier_map.heavy]`), so placing it before `verify_commands = [...]` would silently nest that assignment under `model_tier_map.easy` instead of the document root. Verified live: `tomllib.load` parses the intended shape, `policy.compose(project=..., project_slug="pyforge-marshal", flags={})` resolves `model_tier_map` at the `project` layer with zero findings, and `render_policy_toml` produces three distinct renders (baseline / `heavy` / `easy`) confirmed by direct call.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- `marshal config --project-policy _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml --format json` shows `model_tier_map` populated with `heavy`/`easy`, `layer: project`, no findings.

## Auto Run Result

Status: done

**Summary of this pass.** The dev + review work for this story was already complete (commit
`ea0da8801c`, Review Triage Log entry dated 2026-08-13 already recorded) when this pass began,
but the story's own landing had failed bmad-loop's S-13.7 `spec_surface_reconcile.py` verify
gate: `marshal-policy.toml` had drifted under `spec-adaptive-model-tiering`'s surface and
`tests/unit/test_spin.py` under `spec-pyforge-marshal`'s broad package glob, without either
owning spec's `.memlog.md` naming the changed paths first. This pass repaired exactly that
gate — no code, test, or `<intent-contract>` content was touched.

**Files changed this pass** (commit `6f8d81d627`):
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering/.memlog.md`
  -- appended a Story 3.11 event entry naming `marshal-policy.toml`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- appended a Surface reconcile entry naming `tests/unit/test_spin.py`.
- `scripts/.spec-surface-baseline.json` -- re-stamped for both specs via the mutation-only
  `python scripts/spec_surface_check.py --write-baseline --spec ...`, matching the established
  precedent (story 2.8's own reconciliation pass) so future drift compares against a clean
  checkpoint rather than a baseline permanently stale since 2026-08-13.

**Review findings breakdown:** none -- this pass performed no code review; the story's own
review already completed in the prior pass (patch: 3, defer: 0, reject: 6; see the existing
Review Triage Log entry above).

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- OK: every tracked file governed or allowlisted;
  no drift (was: 2 gating `drift` findings).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3591 passed, 9 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 74 passed.
- `python3 -c "import tomllib; tomllib.load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml','rb'))"` -- no exception.

**Residual risks:** none introduced by this pass. The two `.claude/skills/{bmad-dev-auto,bmad-quick-dev}/spec-template.md`
edits from the original story commit remain covered by the general `.claude/**` allowlist, not
a spec surface -- confirmed unaffected by this repair.

