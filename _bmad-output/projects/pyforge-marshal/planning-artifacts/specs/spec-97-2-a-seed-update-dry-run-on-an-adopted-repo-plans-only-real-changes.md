---
title: "97.2: A seed update dry run on an adopted repo plans only real changes"
type: 'fix'
created: '2026-10-12'
status: 'in-review'
baseline_revision: 'bd92843ef255a6daa94e0ed6d14cc46abe575396'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-97-1-seed-accept-records-an-intended-edit-and-repo-owned-files-leave-the-guard.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-86-2-local-recipes-is-genesis-adopted-so-the-seed-adopt-oracle-goes-green.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/derive/adapters.py
  - src/shared/packages/pyforge-marshal/tests/integration/test_local_recipes_empty_plan.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_update.py
---

<intent-contract>

## Intent

**Problem:** Story 86.2's AC6 says "A `marshal seed update` dry run in a fresh clone plans zero actions". Its landing
left that check as a manual residual, and it does not hold: run at `f478cfbc5a` in this checkout,
`marshal seed update --repo-root .` plans 12 actions. On a fixture of this repo's claimed files, `--run --yes` exits
2 inside `materialize()` ("staged path(s) outside the manifest boundary"), so the plan is one `--run` cannot apply.
Line numbers below are at `f478cfbc5a`.

**The evidence (the 12 actions, and where each comes from):**
- **Seven wholesale regenerations:** `bmad-switch`, `bmad-loop-worktree`, `detector-registry`,
  `detectors-ci-workflow` and `dreams-readme` (`copied-managed`), and `gitignore` and `readme-badge` (hybrid
  regions). `_wholesale_regenerate_actions` (`seed/verbs/update.py:500`-`:616`) plans one action for every state
  record whose current class is in `_WHOLESALE_CLASSES` (`:257`), whatever its content. No whole-file payload ships
  for any `copied-managed` entry (`adopt.py`'s known limitation (1)), so those five actions can only fail at `--run`:
  `_staged_bytes_for` raises `InternalError` (`:704`-`:728`) where `materialize()` stages at all. The two hybrid
  regions would be rewritten with the bytes they already hold: the packaged `model-ignores` and `model-badge`
  fragments hash to the recorded `6dfa035c` and `f66b7e29`.
- **One loop-home entry in a primary checkout:** `bmad-loop-policy` (`.bmad-loop/policy.toml`, `required_in:
  loop-home`).
- **One `unclassified-deferred` glob:** `claude-skills` (`.claude/skills/**`).
- **Three literal `{{ slug }}` paths:** `deck-scaffolding`, `project-config` and `project-subtree`. That is Story
  86.2's AC8 ("no literal `{{ slug }}` path is written") failing on the update side.
- **Why the scoping differs.** `_manifest_for_update` (`update.py:339`-`:347`) filters `applies_to` only. Its
  docstring says it "mirrors `_manifest_for_adopt` verbatim", but `_manifest_for_adopt` (`adopt.py:486`-`:513`) has
  since Story 86.2 also dropped `unclassified-deferred` entries, loop-home entries outside a loop home and slug
  entries with no resolved slug, and rendered `{{ slug }}` through Story 70.1's renderer. `seed update` has no
  `--project` flag, so it cannot resolve a slug at all.

**Approach.**
1. **One scoping function.** `adopt` and `update` scope the manifest through the same function: `applies_to`,
   `unclassified-deferred`, `required_in: loop-home` and slug rendering through `model.manifest.render_slug_paths`. It
   lives in one module (`seed/model/manifest.py` beside `render_slug_paths`, or one `seed/verbs/` module both import),
   and neither verb keeps its own copy. `seed update` gains `--project` with `adopt`'s resolution (`--project`, then
   `BMAD_ACTIVE_PROJECT`, then the target's `_bmad/custom/.active-project` marker) and `adopt`'s loop-home detection.
2. **A regeneration is planned only when it would change something.** For each record the wholesale pass reads now,
   it computes what `--run` would write and plans an action only when that differs from the file on disk:
   - for a hybrid region, the body `_region_body_for` returns against the span's current body;
   - for a `generated-derived` adapter, `derive.adapters.render_adapter` against the whole file;
   - for any other whole-file entry, the packaged payload, if one exists.

   An entry with no packaged payload gets no action. It is named in `plan.skipped` with that reason, and the update
   plan renderer prints it as such, never as `matched --skip`. The pass reads no content it does not need, and it
   never runs `materialize()` in a dry run.
3. **The oracle checks it.** `tests/integration/test_local_recipes_empty_plan.py` gains a slow update leg beside the
   adopt leg: `run_update` in dry-run mode against this checkout plans zero actions, and its `plan.skipped` ids equal
   a documented constant with each reason. So Story 86.2's AC6 is checked by the CI lane that already runs the oracle
   (`marshal-local-recipes-seed-oracle`).

Ledger key: `97-2-a-seed-update-dry-run-on-an-adopted-repo-plans-only-real-changes`.
Type / Effort / Deps: fix / M / S-97.1.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-15 (`seed update` writes a plan and changes nothing until
  `--run`), CAP-12 (Story 86.2's adoption of this repo, whose AC6 and AC8 this story makes true for `update`) and
  CAP-279 (Story 70.1's slug renderer and loop-home scope, which `check` and `adopt` already use). No CAP is minted,
  and no `SPEC.md` text changes.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: a dry run that plans actions its own
  `--run` cannot apply is the defect.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-12 (seed accept and repo-owned managed
  artifacts), and the operator's ruling of that date ("Sign off + fix story (Recommended)"). This is its `update`
  half: the remedy the ruling corrects promised what `update` would do.

## Acceptance Criteria

- **AC1 — One scope for both verbs.** `run_adopt` and `run_update` call the same scoping function, and neither module
  defines its own copy. A unit test asserts that both verbs resolve the same entries for each `(slug, in_loop_home)`
  pair: with a slug, `None`, `True` and `False`. A meta-test fails if either module grows a private
  `_manifest_for_*` that bypasses it.
- **AC2 — No placeholder, loop-home or deferred entry in an update plan.** On a fixture with no project resolved, no
  planned or skipped path in `run_update`'s plan contains `{{`. With `--project demo`, the slug entries render to
  `demo` paths. On a primary checkout (`in_loop_home=False`), `bmad-loop-policy` is not planned, and in a loop home
  it is. `claude-skills`, `pixi-toml-tasks` and `library-llms-full` are never planned. `marshal seed update
  --project` resolves exactly as `marshal seed adopt --project` does, and a CLI test pins it.
- **AC3 — A region already current is not rewritten.** In a fixture adopted with the packaged `model-ignores` and
  `model-badge` fragments, the update dry run plans no action for `gitignore` or `readme-badge`. After the packaged
  body changes (a test `template_path` whose fragment differs), it plans one action for each, and `--run`
  substitutes the span byte for byte (FR-99).
- **AC4 — No action without a payload.** For a `copied-managed` record with no packaged payload (`bmad-switch` with
  the packaged template), the dry run plans no action and lists the id in `plan.skipped` with the no-payload reason.
  The text renderer prints that reason, and `--json` carries it. With a test `template_path` that ships the file
  with different content, the dry run plans one action and `--run` writes it.
- **AC5 — An adapter that is current is not rewritten.** A `generated-derived` adapter record (`cursor-rules`)
  whose file equals `render_adapter`'s output gets no action. A different file gets one.
- **AC6 — Zero actions on this repo.** `run_update` in dry-run mode against this checkout plans zero actions. Its
  `plan.skipped` ids equal a documented constant in `test_local_recipes_empty_plan.py`, each with its reason: the
  recorded skips that `update` honours, plus the no-payload entries. The constant is not
  `LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS` widened (K-02). `pixi run --frozen -e pyforge-marshal marshal seed
  update --repo-root .` prints a plan with zero actions, in this checkout and in a fresh `git clone` of the branch.
- **AC7 — Mutation.** Each change below makes a named test fail:
  - Restore update's `applies_to`-only filter: AC2's test and AC6's oracle leg.
  - Plan every record unconditionally again: AC3, AC5 and AC6.
  - Plan an action for an entry with no payload: AC4 and AC6.
  - Let `{{ slug }}` reach a planned path: AC2.

## Boundaries & Constraints

**Always:**
- Keep the three plan sources disjoint, exactly as `run_update` enforces today (`_merge_plan_sources`).
- Keep `update --force` FR-101's discard: when content differs, `--force` still regenerates it.
- Compare with the same text normalization the guard uses (`detect.hashes.normalize_line_endings`), so a CRLF
  checkout does not read as changed.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item
  5).

**Never:**
- Never widen the oracle's exclusion set or its skip table to reach zero (K-02). The new constant names the
  no-payload entries and why each has no payload.
- Never run `materialize()` in a dry run, and never write anything but `.marshal/plan.json` in one.
- Never change `adopt`'s plan for any repo. Its oracle leg stays as it is.
- Never edit the claimed files or `.marshal/seed-state.yml` to reach an empty plan.

**Residual risk:**
- A repo that relied on `update` re-planning every managed record now sees an empty plan when nothing differs. That
  is the contract FR-94 and Story 86.2's AC6 describe.

## I/O & Edge-Case Matrix

| Record or entry | On disk vs. what `--run` would write | Planned |
|---|---|---|
| hybrid region | equal body | nothing |
| hybrid region | different body | one action (substitute) |
| `generated-derived` adapter | equal file | nothing |
| `generated-derived` adapter | different file | one action |
| whole-file entry with a packaged payload | equal / different | nothing / one action |
| whole-file entry with no packaged payload | — | nothing; listed in `plan.skipped` with the reason |
| `copied-seeded` (Story 97.1's three ids among them) | — | nothing (never touched) |
| `{{ slug }}` entry, no project resolved | — | not in the plan |
| `required_in: loop-home`, primary checkout | — | not in the plan |
| `unclassified-deferred` | — | not in the plan |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-15, CAP-12 and CAP-279. No CAP is minted, and no `SPEC.md`
  text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (seed accept and repo-owned managed
  artifacts) entry.
- Requirements and architecture: FR-94, FR-98, FR-99 and FR-101; AD-55 and AD-57, unchanged.
- Epic: Epic 97 (new), minted with Story 97.1.
- Ledger key: `97-2-a-seed-update-dry-run-on-an-adopted-repo-plans-only-real-changes`.
- Ledger status at mint: `backlog`.
- Deps: S-97.1. Both stories edit `update.py`'s record handling, and 97.1's reclassification decides which records
  the wholesale pass reads.
- Surface: `marshal-policy.toml` `[epic_surfaces]."97"`, added with this mint.
- Spec: the `spec-pyforge-marshal` memlog records the evidence, the design and this mint. Story 86.2's done spec is
  not edited. The memlog records that its AC6 did not hold.
- Minted 2026-10-12 in one chain commit with Story 97.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1-AC5 and AC7's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal marshal-local-recipes-seed-oracle` — expected: pass, with both legs (AC6), in this checkout and in a fresh `git clone` of the branch run from a temp directory.
- `pixi run --frozen -e pyforge-marshal marshal seed update --repo-root .` — expected: zero actions; `git status --porcelain` empty afterwards.
- `pixi run --frozen -e pyforge-marshal marshal seed adopt --repo-root .` — expected: the plan is empty, as before.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The four mutations of AC7 — expected: each fails its named test. Restore each.

## Named, not fixed here

- **Template payloads.** No `copied-managed` entry ships whole-file content, so `update` cannot regenerate one. This
  story stops planning an action it cannot apply. It does not author the payloads.
- **`seed init` on the packaged template.** `marshal seed init` exits 2 in `materialize()` ("staged path(s) outside
  the manifest boundary", measured 2026-10-12): the same missing payloads, on the `init` path.

## Spec Change Log

- 2026-10-12: minted with Story 97.1 from the operator's ruling "Sign off + fix story (Recommended)". The update dry
  run's 12 actions at `f478cfbc5a` are this story's evidence. Story 86.2's AC6 is recorded as not holding on the
  `spec-pyforge-marshal` memlog, and its spec is unchanged.

## Review Triage Log

- No review has run yet.
