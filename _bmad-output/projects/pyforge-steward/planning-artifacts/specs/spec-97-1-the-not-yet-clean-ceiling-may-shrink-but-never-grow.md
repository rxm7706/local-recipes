---
title: '97.1: The not-yet-clean ceiling may shrink but never grow'
type: 'fix'
created: '2026-10-12'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-93-1-the-lint-gate-covers-the-nine-django-portal-packages-and-its-not-yet-clean-list-only-shrinks.md
  - scripts/lint_types.py
  - src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py
  - src/shared/packages/pyforge-steward/tests/unit/test_lint_types_not_yet_clean.py
  - .github/workflows/pyforge-station-tests.yml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** steward's ceiling test pins the lint gate's not-yet-clean list to its seed by equality, so the first
station that cleaned its portal package, exactly as Story 93.1 designed, turned `steward-test` red on `main`. Line
numbers below are at `f1be3236b9`.

- **What 93.1 built.** `scripts/lint_types.py` holds `NOT_YET_CLEAN_CEILING` (:41-:50), "Seeded from measurement on
  Story 93.1's base (2026-10-11). Only shrinks — each station's fix story removes its own entry; never re-add a package
  or verb" (:39-:40), and `NOT_YET_CLEAN` (:53-:55), derived from the ceiling, "Live map — only shrinks; fix stories
  remove entries here and in NOT_YET_CLEAN_CEILING together" (:52). 93.1's AC4: "A steward test holds the seeded map as
  a ceiling: every live entry's package and verbs must be in it. Adding a package or a verb back fails the test.
  Removing an entry passes it."
- **What the test does instead.** `src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py`
  freezes the nine-entry seed as `SEEDED_NOT_YET_CLEAN` (:30-:40), and
  `test_not_yet_clean_within_ceiling_and_seeded_map` (:67-:76) asserts `mod.NOT_YET_CLEAN_CEILING ==
  SEEDED_NOT_YET_CLEAN` (:70). Equality fails on any removal, which AC4 says must pass. The rest of the test (each
  `NOT_YET_CLEAN` entry within the ceiling, every entry a live django package) is right and stays.
- **What broke.** Herald Story 38.1 (merge `e0b8ceae0c`, 2026-10-11) lint-cleaned `django-herald` and removed its line
  from `NOT_YET_CLEAN_CEILING` (`scripts/lint_types.py`, 1 deletion), so `NOT_YET_CLEAN` dropped it too.

**Evidence:**
- **Reproduced 2026-10-12** on `f1be3236b9`, with pyforge-steward's interpreter:
  `python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py -q` gives
  "1 failed, 2 passed"; the failure is `AssertionError` at :70, "Right contains 1 more item: {'django-herald':
  frozenset({'ruff-format', 'ruff'})}".
- **Blast radius.** Every PR whose CI runs `steward-test` (`.github/workflows/pyforge-station-tests.yml`, job
  `steward-test`, `pixi run --frozen -e pyforge-steward pyforge-steward-test`) is red; warden 16.5's PR #2146 is blocked
  by it.
- **Why 38.1 landed green.** Its CI never ran `steward-test`. The workflow's `changes` job sets `steward=true` only
  when `src/shared/packages/pyforge-steward` or the shared surface (`src/shared/packages/pyforge-core`,
  `src/shared/packages/pyforge-testing-kit`, `pixi.toml`, `pixi.lock`, the workflow file) differs from the base; 38.1's
  diff moved `scripts/lint_types.py`, `src/shared/packages/django-herald/**`, herald's tests and planning files, none of
  them on it. The dispatch's own verification ran herald's `verify_commands`. `lint-types.yml` did run (its paths
  include `scripts/lint_types.py`), but it runs the gate, not steward's meta-test.

**Approach:** replace the equality with the subset rule 93.1 specified; change nothing else.
- **Ceiling within the seed.** For every package in `mod.NOT_YET_CLEAN_CEILING`: the package is a key of
  `SEEDED_NOT_YET_CLEAN`, and its verb set is a subset of the seed's verb set for that package. A failure names the
  package (and, for a verb, the extra verbs).
- **Live map within the ceiling.** Keep the existing loop: every `mod.NOT_YET_CLEAN` package is in the ceiling and its
  verbs are a subset of the ceiling's. Keep the live-django check (`set(mod.NOT_YET_CLEAN) <= live_django`).
- **The seed stays the seed.** `SEEDED_NOT_YET_CLEAN` keeps its nine entries, herald included: it records 93.1's
  measurement, the most the ceiling may ever hold. It is not edited each time a station cleans up.
- **Rename only if it reads better.** The test may be renamed to say what it now checks (for example
  `test_not_yet_clean_ceiling_only_shrinks_from_seed`); its docstring names the three mutations.
- **Rejected:** editing the seed to drop herald (a seed that follows the live map proves nothing and breaks again at
  the next station's fix); asserting `NOT_YET_CLEAN == NOT_YET_CLEAN_CEILING` (true today, since `NOT_YET_CLEAN` is
  derived, but 93.1's comment lets a fix story shrink them separately within one landing, and AC4 asks only for
  containment); touching `scripts/lint_types.py` (it already does what 93.1 designed).

Ledger key: `97-1-the-not-yet-clean-ceiling-may-shrink-but-never-grow`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-153** (lint and types gate the ten `pyforge-*` packages, locally and on the runners).
  Story 66.1 built it and Story 93.1 extended the same gate to the nine django portal packages, with a ceiling that
  "only shrinks" (93.1 AC4). This story makes the ceiling test match that AC. It changes no behaviour CAP-153 names, so
  it needs no new CAP and no `SPEC.md` change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag, and this one changes only a test.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-12 (the not-yet-clean ceiling may shrink).
  Authority: the operator's standing direction, "keep going, merge and dispatch when green", with failures fixed at
  once. The fix restores 93.1's stated design, so it needs no new ruling.

## Acceptance Criteria

- **AC1 — Subset, not equality.** The meta-test asserts, for every package in `NOT_YET_CLEAN_CEILING`, that the package
  is in `SEEDED_NOT_YET_CLEAN` and that its verbs are a subset of the seed's verbs for that package; and, for every
  package in `NOT_YET_CLEAN`, that the package is in `NOT_YET_CLEAN_CEILING` and its verbs are a subset of the
  ceiling's. It no longer asserts `NOT_YET_CLEAN_CEILING == SEEDED_NOT_YET_CLEAN`. The live-django check stays.
- **AC2 — Main's tree passes.** On a tree with `scripts/lint_types.py` as at `f1be3236b9` (eight entries, herald gone),
  `test_lint_types_django_tables.py` passes, 3 of 3. `SEEDED_NOT_YET_CLEAN` keeps its nine entries and every line.
- **AC3 — Mutations, each reverted.** Each of these, applied alone to a scratch copy of `scripts/lint_types.py` (or the
  loaded module in a test), makes the meta-test fail:
  - a package added to `NOT_YET_CLEAN_CEILING` that is not in the seed (e.g. `"django-extra": frozenset({"ruff"})`);
  - a verb added to a ceiling entry beyond the seed's (e.g. `django-doctor` gains `"ruff-format"`), including
    re-adding `django-herald` with a verb set wider than the seed's;
  - a `NOT_YET_CLEAN` entry whose package is absent from `NOT_YET_CLEAN_CEILING`.
  Removing a ceiling entry, or a verb from one, passes. The spec's Auto Run Result records each mutation and its
  verdict. Mutations may be committed as parametrized tests that build the maps in memory, never as edits to
  `scripts/lint_types.py`.
- **AC4 — Only the meta-test moves.** `git diff origin/main...HEAD --stat` outside `_bmad-output/` and
  `scripts/.spec-surface-baseline.json` names only
  `src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py`. `scripts/lint_types.py`, the
  `django-*` packages and `.github/workflows/` do not change.
- **AC5 — The station suite is green as CI runs it.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` exits
  0 with no `ruff` on `PATH` (the steward env carries none, as on the CI runner).
- **AC6 — The surface is reconciled.** The memlog of every Spec `spec-surface-check` names for the test file gets a
  surface-reconcile entry naming the file and this story, each is stamped scoped (`--spec <project>/<spec>`, one each),
  and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py`, plus this story's
  memlog entries and scoped stamps.
- Keep `SEEDED_NOT_YET_CLEAN` as 93.1 seeded it (nine entries) and the other two tests in the file unchanged.
- Load `scripts/lint_types.py` as the test does today (`importlib` from the file); never import it any other way.

**Never:**
- Never change `scripts/lint_types.py`, either map, a `django-*` package or a workflow.
- Never edit the seed to follow the live map, skip the test, mark it `xfail` or weaken it beyond the subset rule.

**Out of scope, recorded (a CI-trigger gap):**
- `pyforge-station-tests.yml` does not run `steward-test` when `scripts/lint_types.py`, a `src/shared/packages/django-*`
  package or `.github/workflows/lint-types.yml` moves, though this meta-test reads all three. Its `on.paths` list names
  none of them except `django-pyforge`, and the `changes` job's steward filter is `src/shared/packages/pyforge-steward`
  plus the shared surface. That is how herald 38.1 merged with the meta-test red. Closing it changes a workflow (and
  `pr-preflight`'s lane selection, which reads the workflows), which is outside this test-only fix; it is named here
  for a later steward fix story.

**Residual risk:**
- Until a fix story adds the trigger, the next station that cleans its package can again land without `steward-test`
  running. After this story, that landing passes the meta-test, so the gap only matters for a wrong edit to the maps.

## I/O & Edge-Case Matrix

| Ceiling vs seed | Today (`f1be3236b9`) | After |
|---|---|---|
| equal to the seed (nine entries) | passes | passes |
| one entry removed (herald, main today) | fails (`==`) | passes |
| a verb removed from an entry | fails (`==`) | passes |
| a package the seed lacks added | fails | fails |
| a verb the seed lacks added to an entry | fails | fails |
| `NOT_YET_CLEAN` names a package the ceiling lacks | fails | fails |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-153, as built by Story 66.1 and extended by Story 93.1 (whose AC4
  this restores). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (the not-yet-clean ceiling may shrink)
  entry.
- Epic: Epic 97 (new). Epic 93, which shipped the ceiling and its test, is `done`, so the fix opens its own epic.
  `epic-97` and `epic-97-retrospective` are minted with it.
- Ledger key: `97-1-the-not-yet-clean-ceiling-may-shrink-but-never-grow`.
- Ledger status at mint: `backlog`.
- Deps: none. It unblocks every PR whose CI runs `steward-test`, warden 16.5's PR #2146 among them.
- Spec: the `spec-pyforge-steward` memlog records the evidence and design, and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."97"` (added with this mint) covers the station default, which holds
  the meta-test, and every Spec memlog.
- Minted 2026-10-12 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It runs the changed meta-test.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py -q` — expected: exit 0, 3 passed (AC2), or more if AC3's mutations are committed as parametrized cases.
- The AC3 mutations, one at a time against a scratch copy, re-running the meta-test each time — expected: each fails; removing an entry passes. Revert each.
- `env PATH="$(dirname "$(command -v pixi)"):/usr/bin:/bin" pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 with no `ruff` on `PATH` (AC5).
- `git diff origin/main...HEAD --stat` — expected: AC4's one code path.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC6).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-12: minted under the operator's standing direction "keep going, merge and dispatch when green". `type: fix`,
  no flag, no CAP; bound to `spec-pyforge-steward` CAP-153 through Stories 66.1 and 93.1.
