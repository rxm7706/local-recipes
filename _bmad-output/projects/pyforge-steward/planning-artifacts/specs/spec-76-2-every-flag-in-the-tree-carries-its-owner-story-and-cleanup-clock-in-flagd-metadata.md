---
title: "76.2: Every flag in the tree carries its owner, story and cleanup clock in flagd metadata"
type: 'feature'
created: '2026-09-28'
status: 'in-review'
baseline_revision: bce4a0ce7f1b8e712010482f26f22efb4c1c2482
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: flag-infrastructure
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/platform/tests/test_openfeature_file_flags.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Guild's gate (`spec-feature-flag-governance` CAP-2, doctor's) must red a flag still in the tree 90 days
after it went ON in every environment (Q4), and must name each flag's owner so the owning station files the removal story.
The tree records none of that: `pyforge.three_surfaces` and `pyforge.cutover_root` carry `state`, `variants` and
`defaultVariant` only, so the clock could only be reconstructed from git history, differently by each reader.

**Approach:** every flag in `src/platform/config/flags.json` carries flagd flag-level `metadata` (string values):

- `owner` — the station token (`steward`, `doctor`, …);
- `story` — the ledger key of the story that introduced the flag;
- `created` — `YYYY-MM-DD`, the day the key entered the tree;
- `on_everywhere` — `YYYY-MM-DD`, the day the flag first read ON in every environment's rendered tree (Story 76.1), or `""`
  while it does not; for a flag with no boolean ON variant (`pyforge.cutover_root`) it stays `""`, so no clock runs;
- `cleanup_by` — `on_everywhere` plus 90 days, or `""` when `on_everywhere` is `""`.

`pyforge.core.flags` gains the check, run wherever the tree is composed, each failure a named error: a missing field, a
malformed date, `on_everywhere` set while some environment's rendered value is not ON (or empty while every one is ON), and
`cleanup_by` other than `on_everywhere` + 90 days. The two existing flags get their real dates from the tree's history
(`git log --follow src/platform/config/flags.json`: `pyforge.three_surfaces` entered with Story 26.4 on 2026-08-25,
`7a194d3f57`, reading `on` everywhere, so its `cleanup_by` is 2026-11-23; `pyforge.cutover_root` entered with Story 44.12
on 2026-09-13). `pyforge.three_surfaces`'s clock runs out on 2026-11-23. The operator ruled on 2026-09-28 (night) to
remove it rather than keep it as a kill switch: Story 76.4 (`Deps: S-76.2`) removes it after this story lands. So this
story writes its metadata like any other flag's, and its result names it and its date as owed to Story 76.4. The result
also names every other flag whose `cleanup_by` has passed at landing as owing a removal story or a keep decision from its
owner (Q4); filing either is the owner's act, not this story's.

Ledger key: `76-2-every-flag-in-the-tree-carries-its-owner-story-and-cleanup-clock-in-flagd-metadata`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-76.1.

### Living CAP citations

- `spec-feature-flag-governance` CAP-5 ("each flag carries its owner, story key, created date, ON-everywhere date and
  cleanup date in flagd `metadata`"), Q4 (the 90-day clock); CAP-2 reads what this story writes.
- canopy:AD-11 (amended 2026-09-28; the metadata clause).

## Acceptance Criteria

- Given the tree When it is composed Then every flag carries `owner`, `story`, `created`, `on_everywhere` and `cleanup_by` as strings
- Given a flag missing a field, or with `created: 2026-9-1` When the tree is composed Then a named error names the flag and the field
- Given `on_everywhere` set on a flag some environment renders OFF, or empty on a flag every environment renders ON When the tree is composed Then a named error names the mismatch
- Given `cleanup_by` not equal to `on_everywhere` + 90 days When the tree is composed Then a named error names both dates
- Given `pyforge.cutover_root` (string variants) When the tree is composed Then its `on_everywhere` and `cleanup_by` are empty and no error is raised
- Given the tree with metadata When the host's FILE provider and `pyforge.core.flags.evaluate_boolean` evaluate every key in every environment Then the values equal those before the story
- Given `pyforge.three_surfaces` When its metadata is written Then `on_everywhere` is 2026-08-25 and `cleanup_by` is 2026-11-23, and the story's result names it as removed by Story 76.4 (the operator's 2026-09-28 ruling), which lands after this story
- Given the landing When a flag's `cleanup_by` is before the landing date Then the story's result names it and its owner as owing a removal story or a keep decision (Q4)
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep metadata values primitive (strings) so flagd's schema and the in-process provider accept them.
- Read the dates from the tree's own history; record the commands used in the story's result.
- Reconcile every Spec `spec-surface-check` names, then stamp each scoped with `--spec`.

**Never:**
- Do not remove a flag or file its removal story here; do not implement the Guild's gate (doctor's CAP-2 stories).
- Do not add a metadata field outside the five without a Guild memlog entry (the gate reads exactly these).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| complete | five fields, consistent | composes | — |
| missing field | no `owner` | — | named error |
| bad date | `2026-9-1` | — | named error |
| clock without ON | `on_everywhere` set, production OFF | — | named error |
| ON without clock | ON everywhere, `on_everywhere` empty | — | named error |
| wrong cleanup | `cleanup_by` ≠ +90 days | — | named error |
| string flag | `pyforge.cutover_root` | empty clock | — |
| running clock | `pyforge.three_surfaces`, `cleanup_by` 2026-11-23 | named in the result with its date, as owed to Story 76.4 | — |
| expired clock | `cleanup_by` before landing | named in the result as owing removal or a keep decision | — |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-5 and Q4, and the `spec-pyforge-steward`
memlog note of 2026-09-28 (night) recording Epic 76's shape.

## Spec Change Log

- 2026-09-30 -- operator decision, unblocked (contract unchanged): the blocking condition below is cleared. Story 76.1 landed on `main` as `177f67e991` (PR #1683), so the Deps gate S-76.1 is met, and `src/platform/config/flag-overlays.json` and `pyforge.core.flags.evaluate_boolean` are on `main`. First bring `origin/main` into this branch (merge, never rebase). The re-plan notes under Auto Run Result still apply: `flags.json` holds three flags (`pyforge.steward.ghe_fleet_credentials` gets `owner`/`story`/`created` with an empty clock), and `pyforge.three_surfaces` stays owed to Story 76.4.

## Binding

Parent Spec capability: `spec-feature-flag-governance` CAP-5 (the Guild's Spec; no station CAP or FR is minted).
Dream: `docs/dreams/feature-flag-governance.md`.
Ledger key: `76-2-every-flag-in-the-tree-carries-its-owner-story-and-cleanup-clock-in-flagd-metadata`.
Ledger status at mint: `backlog`.
Deps: S-76.1 (the rendered per-environment trees the clock is defined over).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q` — expected: pass
  (the metadata check's cases).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: `test_openfeature_file_flags.py` passes with the
  metadata-bearing tree.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log

## Auto Run Result

Status: implemented, awaiting review (`in-review`). Implementation and review stay separate: this section is the implementer's record.

**What changed**

- `src/shared/packages/pyforge-core/src/pyforge/core/flags.py`: `METADATA_FIELDS`, `CLEANUP_DAYS`, `check_metadata(flags, overlays)` and five named errors under `FlagMetadataError` (a `FlagConfigError`): `FlagMetadataMissingError` (no metadata object, a missing field, an empty `owner`/`story`), `FlagMetadataNotAStringError`, `FlagMetadataDateError` (not a real `YYYY-MM-DD`; `created` may not be empty), `FlagClockMismatchError` (`on_everywhere` set where an environment does not render ON, or empty where every one does) and `FlagCleanupDateError` (`cleanup_by` is not `on_everywhere` + 90 days). `compose` runs it after the overlay validation, so `read_boolean`, `render` and `read_cutover_root` refuse a tree that breaks it; each message names the flag and the field (the cleanup message names both dates). "ON" is a boolean-true rendered variant per environment (the overlay applied; a `DISABLED` flag renders the tree's own variant), never a judgement of `state`. A string flag (`pyforge.cutover_root`) is never ON, so its clock stays empty and raises nothing. A tree with no `flag-overlays.json` beside it is not composed and reads as it did.
- `src/platform/config/flags.json`: every flag carries the five string fields (values below). No `state`, `variants` or `defaultVariant` changed.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py`: `flip_root`'s create-if-absent `pyforge.cutover_root` entry carries an empty-clock metadata block, so a flip into a tree that lacks the key still composes.
- Tests: `pyforge-core` `test_flags.py` (about 70 cases: each error, the matrix rows, date arithmetic across month/year/leap boundaries, overlay-driven ON everywhere, DISABLED and string flags, `read_boolean`/`render` refusing and never reading `default`, the shipped tree's dates) and `test_cutover_root.py` (fixture); `pyforge-steward` `test_cutover.py`; `src/platform/tests/test_openfeature_file_flags.py` (fixtures carry consistent metadata; new tests pin every shipped key's evaluation in every environment across the FILE provider, `evaluate_from_source` and `read_boolean`, and that the FILE provider surfaces each flag's metadata); `src/platform/tests/test_object_store_seam.py` (the shipped-tree assertion now allows the metadata key).
- Three Spec memlogs carry the surface reconcile: `spec-pyforge-core`, `spec-pyforge-steward`, `spec-pyforge-unifying-strategy`, each stamped scoped with `--spec`.

**The dates (read from the tree's own history)**

Commands: `git log --follow --format='%h %ad %s' --date=iso -- src/platform/config/flags.json`, then per key `git log -S'"<key>"' --format='%h %ad %s' --date=short --reverse -- src/platform/config/flags.json`, and the ledger keys from `sprint-status-ledger.yaml`. Dates are the commit author dates `git log` prints.

| Flag | Introduced by | `created` | `on_everywhere` | `cleanup_by` |
|---|---|---|---|---|
| `pyforge.three_surfaces` | `7a194d3f57`, Story 26.4 | 2026-08-25 | 2026-08-25 | 2026-11-23 |
| `pyforge.cutover_root` | `d021af5df0`, Story 44.12 | 2026-09-13 | empty | empty |
| `pyforge.steward.ghe_fleet_credentials` | `7eb54cd87e`, Story 75.1 | 2026-09-29 | empty | empty |
| `pyforge.steward.object_store_consumer` | `09f515cc9f`, Story 74.1 | 2026-09-29 | empty | empty |

All four are `owner: steward`; `story` holds the full ledger key. `flags.json` holds four flags, not the two the contract names or the three the change log names: Story 74.1 added `pyforge.steward.object_store_consumer` after that note. It is OFF in every environment, so its clock is empty. `object_store_consumer`'s commit is 2026-09-29 20:27 -0500 (2026-09-30 01:27 UTC, merged to `main` 2026-09-30 02:13 -0500); `created` follows the commit's own date, the way the 26.4 date above does.

**Owed at landing (Q4), landing date 2026-09-30**

- `pyforge.three_surfaces` (owner steward): its clock runs out on 2026-11-23. The operator's 2026-09-28 (night) ruling removes it: Story 76.4 (`Deps: S-76.2`) removes it after this story lands. It is owed to Story 76.4 and needs no keep decision.
- No other flag has a `cleanup_by`, and none is before the landing date. No flag owes a removal story or a keep decision today.

**Verification**

- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: exit 0, 1896 passed, 2 skipped.
- `pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests -q`: 2138 passed.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0. Platform `ruff check .`, `ruff format --check .` and `mypy platformapp config tests` (the `platform-ci-local` test-stage lint steps, run against the same envs): clean.
- `src/platform` `pytest tests/test_openfeature_file_flags.py test_object_store_seam.py test_chart_invariants.py test_django_pyforge_assertion.py test_golden_path_promotion_closure.py`: 285 passed, 6 skipped (helm on PATH). The full `platform-ci-local -- --test` needs PostgreSQL and Redis and was not run; these are every platform test that reads the flag tree.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the three scoped stamps.
- `pixi run -e pyforge-guild pr-preflight`: exit 0 (lint-types, target-version, precommit-config, `detectors-ci`, and the rest of its bundle), read from the exit code. The first run exited 1 on `bmad_estate_check` alone (`skills` section drifted); the cause is the gitignored, dispatch-deployed `.claude/skills/caveman/` that the catalog counts. This diff touches no `.claude/` or `docs/reference/` path. With that directory moved aside (and restored afterwards) the run exits 0. A `dispatch/*` push therefore needs the same aside, or scribe Story 25.1 landed.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the three scoped stamps (`pyforge-marshal/spec-pyforge-core`, `pyforge-steward/spec-pyforge-steward`, `pyforge-steward/spec-pyforge-unifying-strategy`); the baseline diff against `origin/main` names only paths those Specs govern.

**Risks**

- The chart composes the tree in Go templates (`_helpers.tpl`), not through `pyforge.core.flags`, so it does not run the metadata check. The shipped tree reaches the chart only after `test_openfeature_file_flags.py` and `test_flags.py` compose it through `pyforge.core`.
- Killing a flag (doctor's `disable_flag` sets only `state: DISABLED`) leaves its clock consistent: the check judges the rendered variant `compose` produces, never `state`. A `DISABLED` flag renders the tree's own `defaultVariant` (its overlay is ignored), so a killed, dated `pyforge.three_surfaces` still composes and `read_boolean` still reads it False. `test_flag_kill_switch.py` pins this against a copy of the shipped tree and overlay. Reading the clock off the rendered variant means a killed flag is still "ON everywhere" for the 90-day clock; whether a killed flag should stop the clock is doctor's gate's call (Story 34.3), not this story's.
- The Guild's gate (doctor's CAP-2, Story 34.3) reads these five fields; it is not implemented here.
