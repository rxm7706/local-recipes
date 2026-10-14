---
title: "102.2: `estate reconcile` writes the bmad-suite floors from the batch, not the network"
type: 'fix'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: '846d8383f5b4a1f86cbb09f6fd8ae8616b34950f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-3-every-derived-surface-regenerates-from-the-lock-by-its-own-generator.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-7-the-first-refresh-lands-through-the-path.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/scripts/bmad_suite_metapackage.py
  - .claude/scripts/conda-forge-expert/bmad_suite_metapackage.py
  - .claude/skills/conda-forge-expert/tests/unit/test_bmad_suite_metapackage_rewrite.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_reconcile.py
  - src/shared/packages/pyforge-steward/tests/unit/test_estate_reconcile.py
  - recipes/bmad-suite/recipe.yaml
  - recipes/bmad-suite/suite-members.yaml
  - .steward/estate-refresh/2026-10-14.json
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `estate reconcile` regenerates `recipes/bmad-suite/recipe.yaml` with the conda-forge-expert generator
`bmad_suite_metapackage.py`, which sets each member's floor to its upstream latest and silently falls back to the
member recipe's version when a lookup fails. So the floors reconcile commits depend on the network at that moment,
can rise past anything the estate builds or locks, and reconcile journals only the generator's exit code. Line
numbers are at `846d8383f5`.

- **The generator.** `generate` (`bmad_suite_metapackage.py:331`) resolves every active member of
  `recipes/bmad-suite/suite-members.yaml` through `_resolve_upstream` (`:183`): the registry its recipe's
  `extra.cfe-upstream-registry` names (`github`, `pypi`, `npm`), a second registry when the first fails (`pypi`
  falls to `npm`; an undeclared registry tries `npm`, then `github`), and the member recipe's `context.version` when
  every lookup fails (`source` `recipe-floor`). `_prefer_floor` (`:170`) never goes below the recipe's version and
  takes any higher upstream release. The table it prints names each row's source; nothing machine-readable leaves it.
- **The reconcile.** `_build_generators` (`estate_reconcile.py:68`) appends `generate-bmad-suite` (`:98`-`:105`)
  when the batch's `moves` name `bmad-method` or a `bmad-*` package, and `_run_generator` (`:210`) records only its
  argv, exit code and seconds (`estate._record_step`, `estate.py:470`).
- **What happened (Story 100.7).** On branch `dispatch/pyforge-steward/100.7`, commit `fe9679af8d` wrote
  `bmad-loop >=0.13.2`, TEA `>=2.0.3` and `bmad-eval-quality >=8.0.0` (`[github]`), none of which the batch moved.
  The next reconcile wrote `>=0.12.0`, `>=1.27.2` and `>=4.3.0`, the member-recipe floors (CFE v8.100.3). A
  `--dry-run` an hour later read 0.13.2 and 2.0.3 again. `pixi.lock` held bmad-loop 0.12.0 and TEA 1.27.2 throughout.
  The landed reconcile, `d8ad5ca53c`, kept main's floors for those members; `bmad-method >=6.12.2` and
  `bmad-module-skill-forge >=3.0.0` followed the batch's moves (journal `.steward/estate-refresh/2026-10-14.json`,
  `moves`: `bmad-method` 6.12.0 → 6.12.2, `bmad-module-skill-forge` 2.2.0 → 3.0.0). Its `reconcile.generators` row
  for the generator holds `exit: 0` and nothing else.
- **Main today.** The suite floors `bmad-method >=6.12.2` and `bmad-module-skill-forge >=3.0.0` sit above their member
  recipes (`recipes/bmad-method` builds 6.12.1, `recipes/bmad-module-skill-forge` 2.2.0); both are the locked
  versions the batch moved to. A plain `--offline` regeneration would lower them to 6.12.1 and 2.2.0.
- **The CFE rule today.** conda-forge-expert v8.100.3 (Story 100.7's retro) states the rule for a hand run: read each
  changed row's source before committing, commit a floor only when its source is a registry, and commit a floor above
  what the member recipe builds only together with that member's move. Nothing enforces it.

**Approach:**
- **The generator gains a batch mode** (conda-forge-expert's script; invoke the `conda-forge-expert` skill first):
  - `--journal <path>` reads the estate journal's `moves`. A member *moves* when an entry names it with `to` different
    from `from`; its `moved_to` is the highest such `to` (by `packaging.version`).
  - In batch mode the generator makes **no upstream lookup**: no `_fetch_*` call, no network. Reconcile never asks for
    one, so no fallback can occur. Each active member's floor is:
    - its `moved_to` when it moves, raised to the current suite floor if that is higher (source `batch-move`);
    - otherwise the higher of its current suite floor (the GENERATED block, `_parse_existing_pins`, `:267`) and its
      member recipe's `context.version` (source `suite-floor` or `member-recipe`, whichever gave the floor).
  - So a floor never falls, and it rises above what the member recipe builds only when that member moves in the
    batch, and then only to the version the batch moved it to.
  - The CalVer stamp and the rewrite are unchanged: the version moves only when a floor does.
- **A machine-readable report.** `--json` prints one JSON object on stdout in place of the table:
  `{"version_before", "version", "written", "members": [...]}`, one member object per active member with `name`,
  `registry`, `recipe_version`, `moved_to` (or `null`), `floor_before` (or `null`), `floor`, `source` and
  `fallback`. In batch mode `fallback` is always `false`. Without `--journal`, `source` is today's (`github`,
  `pypi+floor`, `recipe-floor`, …) and `fallback` is `true` when the floor did not come from the registry
  `cfe-upstream-registry` names: `recipe-floor` after a failed lookup, `npm` for a `pypi` member, `npm-fallback`,
  `github-fallback`. `--offline` is asked for, so it is no fallback.
- **The hand path is unchanged.** Without `--journal` and `--json` the generator prints the same table, resolves
  upstream latest, and writes what it wrote at `846d8383f5`. That is conda-forge-expert's suite-advance path.
- **Reconcile uses batch mode and journals the floors.** `generate-bmad-suite` runs
  `bmad_suite_metapackage.py --journal <the reconcile's journal> --json`. Reconcile parses the report and writes it to
  the journal's `reconcile.bmad_suite` (`version_before`, `version`, `written` and every member row), and its summary
  names each floor that changed (`<name> <floor_before> -> <floor> [<source>]`). A non-zero exit, or stdout that is
  not the report, makes reconcile return exit 1 naming `generate-bmad-suite`, journaled, never a silent pass.
- **The retro.** The effort closes with a conda-forge-expert retro: `SKILL.md`'s `cfe-upstream-registry` section
  states that `--journal` is the mode reconcile uses and the v8.100.3 hand rule now holds by construction there;
  `CHANGELOG.md` gains the entry; the skill's version bumps (MINOR: a new flag and output mode), with
  `MANIFEST.yaml` and `config/skill-config.yaml` in step.

**Rejected:**
- **Keep the lookups and cap the result.** Capping upstream latest at the batch's version gives the same floors as no
  lookup at all, so the lookup is only a way to fail. A failed lookup would still need a rule to keep it from
  lowering a floor.
- **Reconcile runs `--offline`.** It sets every floor to its member recipe's version, which lowers `bmad-method` and
  `bmad-module-skill-forge` below the versions the batch locked.
- **Change the generator's default.** Its upstream-latest default is conda-forge-expert's suite-advance path, run by
  hand when member recipes move. Reconcile asks for batch mode explicitly.
- **Steward computes the floors itself.** Steward wraps the generator by subprocess (AD-1, CAP-167's "every derived
  surface by its own generator"); a second floor rule in steward could drift from the generator's.
- **Widen the trigger beyond `bmad-*`** (to `mybmad-dashboard`). CAP-167 says the generator runs "when a `bmad-*`
  floor moved"; changing the trigger is a Spec change, not this fix.

Ledger key: `102-2-estate-reconcile-writes-the-bmad-suite-floors-from-the-batch-not-the-network`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-167 (Story 100.3, `estate reconcile`): every derived surface
  regenerates by its own generator, the `bmad-suite` metapackage by `generate-bmad-suite` when a `bmad-*` floor moved,
  and the run is journaled. Story 100.7 ran it first and found the floors network-dependent. This story makes the
  generator's reconcile run deterministic and journaled. It mints no CAP and changes no `SPEC.md`.
- **conda-forge-expert.** `bmad_suite_metapackage.py` and its tests are conda-forge-expert's. AGENTS.md § *Where
  things are*: invoke the `conda-forge-expert` skill before any edit there, and close the effort with a retro that
  edits the skill's `SKILL.md` and `CHANGELOG.md` with a semver bump; the effort is not done until it lands.
- **Governance.** `bmad_suite_metapackage.py` is on `spec-pyforge-steward`'s, `spec-conda-forge-expert-rebuild`'s and
  `spec-packaging-factory`'s surfaces; its tests, `SKILL.md` and `CHANGELOG.md` on the two mason Specs';
  `estate_reconcile.py` on `spec-pyforge-steward`'s and `spec-pyforge-core`'s; `recipes/bmad-suite/recipe.yaml` on
  `spec-pyforge-steward`'s (`scripts/.spec-surface-baseline.json`).
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. `estate reconcile` is already behind
  steward's estate flag.
- **Origin.** `DW-steward-100-7-2` (steward `deferred-work-ledger.md`, from Story 100.7's Rule-2 retro, CFE v8.100.3);
  `docs/dreams/pyforge-steward.md` Realization log, 2026-10-14 (CI and estate follow-ups).

## Acceptance Criteria

No criterion touches the network: each CFE test arms `_fetch_json` and `get_latest_github_release` to raise, and each
steward test runs reconcile against a fake runner and a tmp tree.

- **AC1 — Batch mode makes no lookup.** With every fetcher armed to raise, `generate(root, journal=<fixture>)` and
  `bmad_suite_metapackage.py --journal <fixture> --json` complete, and the report's every member has `fallback`
  `false`.
- **AC2 — The floor rule.** On a fixture suite whose GENERATED block and member recipes mirror `846d8383f5`'s, and a
  journal shaped like `.steward/estate-refresh/2026-10-14.json`:
  - `bmad-method` moving 6.12.0 → 6.12.2 with a recipe at 6.12.1 writes `>=6.12.2`, source `batch-move`;
  - `bmad-loop` not moving, recipe 0.12.0, suite floor 0.12.0, writes `>=0.12.0`; the same with upstream fixed at
    0.13.2 still writes `>=0.12.0`;
  - a member not moving whose suite floor (6.12.2) is above its recipe (6.12.1) keeps `>=6.12.2`, source
    `suite-floor`;
  - a member not moving whose recipe (2.3.0) is above its suite floor (2.2.0) writes `>=2.3.0`, source
    `member-recipe`;
  - an entry with `from` equal to `to` is not a move;
  - two entries for one member with different `to` give the highest;
  - no floor falls in any case, and the CalVer stamp moves exactly when a floor does.
- **AC3 — The report.** `--json` prints one JSON object (and no table) whose `members` list has one object per
  active member, in manifest order, with exactly the keys `name`, `registry`, `recipe_version`, `moved_to`,
  `floor_before`, `floor`, `source` and `fallback`, plus top-level `version_before`, `version` and `written`. With
  `--dry-run`, `written` is `false` and the recipe is byte-identical.
- **AC4 — Fallbacks are named on the hand path.** Without `--journal`, with fixed fetchers: a `github` member whose
  lookup fails reads `source` `recipe-floor`, `fallback` `true`; a `pypi` member answered by npm reads `npm`, `true`;
  a member whose declared registry answers below its recipe reads `github+floor`, `false`; `--offline` reads
  `offline`, `false`.
- **AC5 — The hand path is unchanged.** Without `--journal` or `--json`, the stdout table and the written recipe are
  byte-identical to `846d8383f5`'s for the same fixed fetchers. Every existing test in
  `test_bmad_suite_metapackage_rewrite.py` passes with no assertion weakened or deleted.
- **AC6 — Reconcile journals the floors.** `run_reconcile` with a journal whose `moves` name a `bmad-*` member runs
  the generator as `[python, ".claude/scripts/conda-forge-expert/bmad_suite_metapackage.py", "--journal",
  <journal path>, "--json"]`, writes the parsed report to the journal's `reconcile.bmad_suite`, and its summary names
  each changed floor. `test_ac1_generators_order_and_conditional` still holds: no `bmad-*` move, no generator.
- **AC7 — A broken generator run is not a pass.** A generator exit 1, and an exit 0 whose stdout is not a JSON object
  with a `members` list, each make `run_reconcile` return `ok=False` with `exit_code` 1 naming
  `generate-bmad-suite`, and the journal records why.
- **AC8 — Mutation.** Each change below fails a named test, and the Auto Run Result records which:
  - batch mode calling a fetcher (AC1);
  - a non-moving member taking upstream latest (AC2's `bmad-loop`);
  - a moving member taking the recipe's version instead of `moved_to` (AC2's `bmad-method`);
  - reconcile ignoring a generator exit 1 (AC7).
- **AC9 — The conda-forge-expert retro lands.** In its own commit whose subject starts `retro(cfe):` and which also
  carries `CHANGELOG.md` (the `branch_diff_guard` rule the station meta-tests enforce): `SKILL.md`'s
  `cfe-upstream-registry` section names `--journal` and `--json`; the skill's version bumps MINOR in `SKILL.md`,
  `MANIFEST.yaml` and `config/skill-config.yaml`; `CHANGELOG.md`'s TL;DR and history gain the entry.
- **AC10 — Green, and the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` exits 0,
  and so does `pixi run --frozen -e local-recipes test` (the conda-forge-expert offline suite). Every changed governed
  path gets a surface-reconcile entry on each governing Spec's memlog (`spec-pyforge-steward`, `spec-pyforge-core`,
  `spec-conda-forge-expert-rebuild`, `spec-packaging-factory`), then one scoped stamp per Spec, and
  `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Invoke the `conda-forge-expert` skill before editing anything under `.claude/skills/conda-forge-expert/` or
  `.claude/scripts/conda-forge-expert/`; where this story and the skill disagree, the skill wins and the story
  records the deviation.
- Keep the generator's default path (no `--journal`, no `--json`) byte-for-byte as it is.
- Keep every conda-forge-expert change in a `retro(cfe):` commit that carries its `CHANGELOG.md` entry, apart from any
  steward or mason path.
- Reconcile every governed path the change touches on each governing Spec's memlog, then stamp each scoped (AGENTS.md
  pre-PR item 5).

**Never:**
- Never let batch mode touch the network, and never let a floor written by batch mode fall.
- Never regenerate `recipes/bmad-suite/recipe.yaml` on `main`'s floors in this story: the tests use fixtures, and the
  recipe moves only when a real estate refresh moves it.
- Never edit `suite-members.yaml`, a member recipe, `pixi.toml` or `pixi.lock`.
- Never open a feedstock, staged-recipes or upstream PR.

**Residual risk:**
- A member that moves alone without a `bmad-` prefix (`mybmad-dashboard`) does not trigger the generator, as CAP-167
  states. A Spec change, not this fix.
- The hand path still resolves upstream latest and can still fall back. `--json` names the fallback, and the CFE rule
  of v8.100.3 still governs a hand commit.

## I/O & Edge-Case Matrix

| Situation | Today (`846d8383f5`) | After (reconcile's batch mode) |
|---|---|---|
| member not moving, upstream newer than the lock | floor = upstream latest | floor unchanged (`suite-floor`) |
| member not moving, every lookup fails | floor = member recipe's version (may fall) | floor unchanged; no lookup is made |
| member moving 6.12.0 → 6.12.2, recipe 6.12.1 | floor = upstream latest (6.12.2 that day) | `>=6.12.2` (`batch-move`) |
| member recipe bumped above the suite floor, not moving | floor = upstream latest | floor = the recipe's version (`member-recipe`) |
| `from` equal to `to` in a move entry | counted by the trigger | not a move |
| generator exits 1 | journaled exit, reconcile continues | reconcile exit 1, names `generate-bmad-suite` |
| hand run, no flags | table, upstream latest | unchanged |
| hand run `--json`, a lookup fails | — | `source` `recipe-floor`, `fallback` `true` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (Story 100.3's `estate reconcile`, first run by Story 100.7).
  No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, item 2.
- Epic: Epic 102 (new). Epic 100, which shipped CAP-167, is `done`.
- Ledger key: `102-2-estate-reconcile-writes-the-bmad-suite-floors-from-the-batch-not-the-network`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Closes: `DW-steward-100-7-2` (steward `deferred-work-ledger.md`); close it citing this story's merge.
- Closes with: a conda-forge-expert retro (AC9), not deferrable.
- Spec: the `spec-pyforge-steward` memlog records the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"` (added with this mint) covers the generator, its CLI wrapper,
  its tests and the skill files.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding), and it runs `test_estate_reconcile.py`.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_bmad_suite_metapackage_rewrite.py -q` — expected: exit 0 (AC1-AC5).
- `pixi run --frozen -e local-recipes test` — expected: exit 0 (the conda-forge-expert offline suite, AC10).
- The AC8 mutations, one at a time, re-running the named test each time — expected: each fails the named test. Revert each.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert/` — expected: every subject starts `retro(cfe):` or `retro:`, and each such commit carries `CHANGELOG.md` (AC9).
- `git diff origin/main...HEAD --stat -- recipes/` — expected: empty.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC10).
- `pixi run --as-is -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-14: minted from `DW-steward-100-7-2` (Story 100.7's Rule-2 retro, CFE v8.100.3). `type: fix`, no flag,
  no CAP. Bound to `spec-pyforge-steward` CAP-167 through Stories 100.3 and 100.7.
