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

### 2026-09-30 — Review pass
- verdicts: 28 findings — high 4, medium 1, low 21, false 2, maybe-false 0
- findings:
  - `[high]` `[patch]` Blind Hunter 1 — a kill switch on a dated flag makes every compose refuse the tree. Reproduced: after `disable_flag` on the shipped `pyforge.three_surfaces`, `read_boolean` raised `FlagClockMismatchError` for that key and for `pyforge.steward.ghe_fleet_credentials`. Patched: `_rendered_variant` returns the tree's own `defaultVariant` for a `DISABLED` flag (`compose` ignores its overlay) and `_renders_on` no longer judges `state`; the killed key reads False and the siblings read as before.
  - `[low]` `[reject]` Blind Hunter 2 — one flag's bad metadata breaks reads of every other flag. Intended: the contract runs the check "wherever the tree is composed", each failure a named error, and 76.1's overlay errors already raise out of `read_boolean` the same way; steward's `main` maps a `FlagConfigError` to its usage code. A per-flag WARN-and-default path would add branches the intent excludes.
  - `[low]` `[patch]` Blind Hunter 3 — the `compose` docstring says no path that composes the tree accepts a wrong clock, but the chart's Go-template composition does not run the check. Patched: the docstring now names the `pyforge.core` paths that refuse and says the chart does not run the check and that the tests compose the shipped tree through `compose`.
  - `[low]` `[reject]` Blind Hunter 4 — only the shape of the dates is checked (no `created <= on_everywhere`, no future-date check). The intent lists exactly four failures and Boundaries leave the Guild's gate to doctor's Story 34.3; each added check is a new branch and a new error class.
  - `[false]` `[reject]` Blind Hunter 5 — a temporary rollback erases the 90-day clock. The intent states the rule: `on_everywhere` is `""` while some environment's rendered value is not ON, and set while every one is ON. The code enforces that sentence; the docstring's "first read ON" is the intent's own wording.
  - `[low]` `[reject]` Blind Hunter 6 — the test helpers `_stamp` and `_fixture_flags` recompute "renders ON in every environment" as `_renders_on` does. They only date overlay fixtures so they compose; the clock's own tests use hand-written dates. The kill-switch patch updated both helpers to the new rule.
  - `[low]` `[reject]` Blind Hunter 7 — the same metadata block is copied in five test and source places. Test-fixture duplication; a shared helper across `pyforge-core`, steward and platform tests would cross package boundaries for no failing case. `cutover.py` already holds the story key as one constant.
  - `[low]` `[reject]` Blind Hunter 8 — the shipped-tree tests in `test_flags.py` reach into `src/platform` and can skip. `test_flags.py` already did this before the story (its `pytest.skip` on a missing checkout); `test_openfeature_file_flags.py` asserts the shipped tree with no skip and its FILE-provider legs ran (107 passed; the skips are helm and object-storage tests).
  - `[low]` `[patch]` Blind Hunter 9 — `src/platform/tests/test_object_store_seam.py` moved without a memlog entry naming it. Patched: an entry on `spec-pyforge-unifying-strategy` and on `spec-pyforge-steward` (the two Specs whose memlogs already name it) names the path and the reason; the other paths this pass changed are named on `spec-pyforge-core` and `spec-pyforge-doctor`.
  - `[low]` `[reject]` Blind Hunter 10 — thin `flip_root` tests (`created` from `date.today()` is unasserted; no metadata-less existing-flag case). A flip into a metadata-less tree already refuses through the `compose` call with the named entry; the date source is not injectable and the `created` value is not part of the contract's I/O matrix.
  - `[low]` `[reject]` Blind Hunter 11 — `owner` and `story` are not validated against a station token or a ledger key. The intent asks for the fields to be present strings; validating against a registry adds a dependency `pyforge.core` (a leaf) must not have.
  - `[low]` `[reject]` Blind Hunter 12 — the metadata contract is documented only in the module docstring; no schema or how-to. No file outside the five is in the intent; the docstring and the tests state the contract.
  - `[high]` `[patch]` Edge Case Hunter 1 — the kill switch with a dated flag (`check_metadata` and `disable_flag`); reproduced by the reviewer and by me. Same root cause and same patch as Blind Hunter 1.
  - `[false]` `[reject]` Edge Case Hunter 2 — a production-overlay rollback on a flag with a running clock fails the whole tree. Same claim as Blind Hunter 2 and 5: the contract requires the named error, and the fix the reviewer proposes (WARN and default per key) removes the refusal the intent asks for. Logged `false` on the same evidence.
  - `[medium]` `[patch]` Edge Case Hunter 3 — the `check_metadata` docstring says a kill switch clears its clock in the same edit, and nothing does. Patched with the kill-switch fix: the docstrings now say a kill leaves the clock as it was.
  - `[low]` `[reject]` Edge Case Hunter 4 — the chart's composition does not run the check, so `helm install` can ship a wrong clock. The chart renders the checked-in `flags.json`, which the core and platform tests compose through `pyforge.core` on every run, so a wrong clock cannot merge; a Go-template validator is new machinery outside the intent's `pyforge.core.flags`. The docstring overstatement is Blind Hunter 3's patch.
  - `[low]` `[reject]` Edge Case Hunter 5 — `on_everywhere` later than today or earlier than `created` is accepted. Same as Blind Hunter 4.
  - `[low]` `[reject]` Edge Case Hunter 6 — a sixth metadata field is accepted. The Never clause binds authors ("do not add a field without a Guild memlog entry"); the intent's failure list has no unknown-field error, and the gate reads exactly the five and ignores the rest.
  - `[low]` `[reject]` Edge Case Hunter 7 — `flip_root` does not backfill metadata into an existing metadata-less entry. Such a tree already fails `compose`, so the flip refuses loudly before writing either file; the shipped tree carries the metadata.
  - `[low]` `[reject]` Edge Case Hunter 8 — AC 6 names `pyforge.core.flags.evaluate_boolean`, which does not exist. The fix edits this spec's intent contract, which triage rejects; the tests check the reader that exists (`django_pyforge.flags.evaluate_boolean`, the FILE provider, `evaluate_from_source` and `read_boolean`) in every environment.
  - `[high]` `[patch]` Verification Gap 1 — no test kills a dated flag and then composes. Patched: `test_flag_kill_switch.py` copies the shipped tree and overlay, runs `disable_flag` on `pyforge.three_surfaces` and reads it and a sibling in every environment; three `test_flags.py` cases pin a killed flag that renders ON, one that renders OFF with an empty clock and one that renders OFF with a dated clock. Both new tests fail against the old `state`-judging logic (checked with a temporary monkeypatch).
  - `[high]` `[patch]` Verification Gap, other 1 — `disable_flag` does not clear the clock the way the docstring said. Same root cause as Blind Hunter 1; resolved by making the check agree with the actuator, not the reverse (the actuator is doctor's and edits `state` only).
  - `[low]` `[reject]` Verification Gap, other 2 — `scripts/flag_gate_check.py:21` says the metadata checks are Story 34.3's. The gate that reads the clock stays doctor's; `compose` refuses a malformed tree and does not replace it, so the comment is still true.
  - `[low]` `[reject]` Intent Alignment 1 — the chart (`platform.flags.rendered`) is untouched and does not run the check. Same as Edge Case Hunter 4.
  - `[low]` `[reject]` Intent Alignment 2 — a tree with no sibling `flag-overlays.json` is not composed, so the check does not run (the in-cluster mount, the `django_pyforge` fallback). Pinned by `test_a_tree_read_as_it_is_is_not_composed_so_the_check_does_not_run`; the mounted tree is the rendering of a tree that was checked at source.
  - `[low]` `[reject]` Intent Alignment 3 — AC 6's `evaluate_boolean` names a function `pyforge.core.flags` lacks. Same as Edge Case Hunter 8.
  - `[low]` `[reject]` Intent Alignment 4 — the "values before the story" are literal constants and the platform FILE-provider legs `importorskip`. The constants equal the pre-story tree (the diff changes no `state`, `variants` or `defaultVariant`); the legs ran under `platform-ci-local` (exit 0) and again with `-rs` (107 passed; only helm and object-storage tests skip).
  - `[low]` `[reject]` Intent Alignment 5 — most new test volume is fixture-driven and only a few tests read the shipped tree. The AC-bearing shipped-tree assertions are four core tests plus the platform evaluation and provider-metadata tests, all run; the fixture tests are the matrix rows.

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
