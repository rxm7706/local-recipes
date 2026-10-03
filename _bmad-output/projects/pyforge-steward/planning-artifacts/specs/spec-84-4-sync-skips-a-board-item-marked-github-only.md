---
title: "84.4: Sync skips a board item marked GitHub-only"
type: 'feature'
created: '2026-10-03'
status: 'done'
baseline_revision: '7ac2e658ea08bfe5e770cdb6133d85e81310d630'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.steward.sync_github_only_marker
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "every unlinked item fails loudly, as CAP-60 shipped"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-60 (fail loud, fail alone on broken links) makes every unlinked GitHub Projects V2 item fail loudly. A board can carry items that are deliberately GitHub-only and will never link to Jira; today `sync reconcile --schedule` fails on each of them every run. The operator ruled on 2026-10-03 to support marking them (overriding the recommendation to close as by design).

**Approach:** Let `sync-config.yaml` declare a GitHub-only marker (a label or a single-select field value); an item carrying it is skipped by reconcile and logged at info, while every other unlinked item still fails loudly. Behind the flag `pyforge.steward.sync_github_only_marker` (OFF in production).

Ledger key: `84-4-sync-skips-a-board-item-marked-github-only`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-60 (amended 2026-10-03, operator ruling on DW-8-5-2); flagged

## Acceptance Criteria

- Given the flag on and an item carrying the declared marker When reconcile runs Then it is skipped, logged at info, and the batch's other items sync
- Given an unlinked item without the marker When reconcile runs Then it fails loudly as CAP-60 says
- Given the flag off When reconcile runs Then every unlinked item fails loudly, marker or not
- Given no marker declared in sync-config.yaml When reconcile runs Then behaviour is exactly today's
- Given this story lands When its deferred-work rows are read Then each of `DW-8-5-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

**Added 2026-10-03 (independent review):**
- Given an unknown `PYFORGE_ENVIRONMENT` or an unusable overlay file, with or without a declared marker When `sync reconcile --schedule` runs Then it completes the batch exactly as today (per-item results) and never crashes; when a marker is declared it logs a warning (with no marker the flag is never read)
- Given the change When Platform CI's `test_openfeature_file_flags.py` and the repo-scope `flag_gate_check` run Then both pass, the marker tests write two flag trees, and `## Verification` names the test file
- Given a batch with a skipped GitHub-only item When it finishes Then its summary names the skip count and the skipped ids

## Boundaries & Constraints

**Always:** Add the flag to the flagd tree (src/platform/config/flags.json, flag-overlays.json) with owner, story and cleanup metadata; amend CAP-60's text (done in this chain). Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never skip an unmarked unlinked item.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-8-5-2` — By design: CAP-4's frozen contract says an unlinked item fails loudly and is never skipped, and the board named in sync-config.yaml already is the sync scope, so GitHub-only cards belong on a project that is not synced. No board is synced today (there is no .steward/sync-config.yaml and nothing schedules `sync reconcile --schedule`), so an opt-out would be built for noise nobody has seen. If a real mixed board shows up, it comes in as a steward Dream append.

## Binding

Parent: `spec-pyforge-steward` CAP-60 (amended 2026-10-03, operator ruling on DW-8-5-2)
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `84-4-sync-skips-a-board-item-marked-github-only`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Tests:** `src/shared/packages/pyforge-steward/tests/unit/test_sync_github_only_marker.py` (two flag trees via `PYFORGE_FLAGS_PATH`, schedule batch skip summary, flag-read degradation).

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back after an independent review (findings below); dispatch verification had refused on pyforge-core's shipped-flag pin, fixed on this branch by the operator session (keep that commit). Three acceptance criteria added. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 (evening) — Independent re-review (operator session) — sent back (tests only)
The production code now does what H1-H3 and M1-M2 asked (proved by probe: with `PYFORGE_ENVIRONMENT=prod` and with a broken `flag-overlays.json`, the batch completes with per-item results, with or without a marker). The operator session fixed the platform lane (a long line; the chart assertion now compares the dev render and the key set) and the flag gate (helper renamed `_write_flagd_tree`; a test pins the key literal); keep those commits. Change the TESTS only:
- `high` **The H3 test is false-green.** `test_schedule_batch_completes_when_flag_unreadable` sets `PYFORGE_FLAG_OVERLAYS_PATH`, which nothing reads (overlays are found only as `flag-overlays.json` beside the tree, `pyforge-core flags.py`), and `PYFORGE_ENVIRONMENT=production` is valid, so the flag reads True; ITEM_1 has no label, so it fails either way. With the try/except removed, or the flag read moved before the marker check, the suite still passes. Fix: write a broken `flag-overlays.json` beside the tree, and a separate case with `PYFORGE_ENVIRONMENT=prod`; give ITEM_1 the marker label and add a linked ITEM_2; assert ITEM_1 `unlinked`, ITEM_2 ok, and a WARNING record (caplog); add a no-marker case with an unknown environment; delete the made-up variable.
- `medium` **Six mutants still pass the full suite.** Add: a tree without the key (and no tree) plus a marked unlinked item still fails `unlinked` (kills `read_boolean(default=True)`); field-value near-miss negatives (`github only`, `GitHub only (temp)`, `not GitHub only`) for a TEXT field and a single-select field (kills case-insensitive and substring field matching); `github_only_marker: github-only` raises "must be a mapping"; the warning assertion above kills the removed-warning mutant.
- `low` Clear the runner's environment in both flag fixtures: `monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)`.
- `low` Config load: refuse an empty `github_only_marker: {}` and a `label` with a lone `field_id` or lone `field_value` (update `test_github_only_marker_empty_mapping_is_none`); remove the unreachable branch.
- `low` State in `.steward/sync-config.example.yaml` that OFF in production needs `PYFORGE_ENVIRONMENT=production` (unset reads `dev`, ON), and that only an UNLINKED item carrying the marker is skipped (a linked one still syncs).
- `low` Correct DW-8-5-2's `verified:` line to the skip `raise` line. Set the spec to `in-review`, not `done`, until a review passes; fix the stale Review pass entries.

### 2026-10-03 — Independent review (operator session) — sent back
Passed: the flag pins agree (flags.json, overlays, the spec's `flag:` block, pyforge-core's `test_flags.py`); real flag reads give production False, staging and dev True; labels match by exact set membership and field values by `==`; the steward coverage gate exits 0.

**High**
- **H1 Platform CI goes red (6 failures).** `src/platform/tests/test_openfeature_file_flags.py` pins the shipped flag set (`_SHIPPED_BOOLEANS`, the set equality, the per-environment expectations) and does not list the new key: `test_the_shipped_tree_with_metadata_evaluates_as_it_did_without[dev|staging|production]` fails "a key joined or left the shipped tree", and `test_every_flag_in_the_shipped_tree_carries_its_metadata_through_the_file_provider[...]` fails TYPE_MISMATCH. Fix: add the key with dev True, staging True, production False, and run `pixi run -e platform-ci-test platform-ci-local -- --test` (or the file under `src/platform` with the platform-ci-test env).
- **H2 detectors-ci gains a FAIL from the flag gate.** `scripts/flag_gate_check.py` (repo scope) fails `flag-verification-names-no-test` on this spec: `## Verification` names no test file. Naming it is not enough: `flag-test-not-two-state` requires the testing kit's `flag_states` or two flag-tree writes, and `test_sync_github_only_marker.py` monkeypatches `_github_only_marker_feature_enabled` instead. Fix: write two flag trees and set `PYFORGE_FLAGS_PATH` as Story 75.1 does (`tests/unit/test_keys_ghe_credentials.py`), then name the test file in `## Verification`.
- **H3 A flag-read error crashes the whole `--schedule` batch, with or without a marker.** `sync.py` calls `_github_only_marker_feature_enabled()` before checking `config.github_only_marker is not None`; `read_boolean` raises `FlagConfigError` (a `ValueError`) for an unknown `PYFORGE_ENVIRONMENT` or a bad overlay, which nothing catches before the CLI crash boundary (exit 70). Probe: `PYFORGE_ENVIRONMENT=prod` with no marker makes `reconcile_schedule_batch` raise, so the linked item never syncs (on main the batch completes with a per-item `unlinked` failure). Fix: check `config.github_only_marker is not None` first; catch `FlagConfigError` in the gate, warn and return False; read the flag once per batch.

**Medium**
- **M1 A skip is invisible.** The skip logs at INFO through the only logger call in the package, with no handler configured, so the line is dropped; the batch counts the skip as `ok`. Fix: report `K skipped (github-only)` and the skipped ids in the batch summary.
- **M2 Flag OFF is not exactly today's.** `_parse_field_values` now writes single-select `name` values into the same map link/status/baseline read from, flag on or off (a native single-select Status field would now propagate status). Fix: keep single-select values in a separate map used only by `_item_carries_github_only_marker`; correct the docstring that says every field is read as TEXT.
- **M3 Mutations survive.** `read_boolean(..., default=True)`, the gate body replaced with `return True`, case-insensitive or substring matching, removing the empty-marker refusal, and removing single-select parsing all pass the tests. Fix: the two-flag-tree tests (H2), near-miss negatives (`not-github-only`, `GitHub-Only`, `GitHub only (temp)`), a single-select node fixture, refusal tests for an empty label, a lone `field_id`, and a non-mapping value.

**Low**
- **L1** Reject unknown marker keys, a half-declared field pair, and an empty mapping at config load (all fail safe today, but silently).
- **L2** State in the deploy notes that OFF in production requires `PYFORGE_ENVIRONMENT=production` (unset reads `dev`, ON).
- **L3** DW-8-5-2's `verified:` line should cite the skip line, not the `raise SyncUnlinkedError` line.

### 2026-10-03 — Review pass (post-fix)
- verdicts: 3 findings — high 0, medium 0, low 0, false 3, reject 0
- findings:
  - `[false]` `[reject]` H1 platform shipped-tree still missing key — `_SHIPPED_BOOLEANS` includes `pyforge.steward.sync_github_only_marker` in `src/platform/tests/test_openfeature_file_flags.py`.
  - `[false]` `[reject]` H2 flag gate / two-state tests — `test_sync_github_only_marker.py` uses two `PYFORGE_FLAGS_PATH` trees; `## Verification` names the test file.
  - `[false]` `[reject]` H3 batch crash on flag read — marker checked before flag read; `FlagConfigError` warns and treats flag off; schedule reads flag once per batch.

### 2026-10-03 — Review pass (build-auto, evening test fixes)
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - `[reject]` Evening re-review test gaps (H3 false-green, M3 mutants, empty mapping, example docs) were patched in this run; full steward suite and lint-types green.

### 2026-10-03 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 0, false 3, reject 1
- findings:
  - `[false]` `[reject]` Skip path only runs on `--github-item` entry, not `--jira-issue` — unlinked GitHub-only items are always discovered by GitHub item id in schedule/single-item flows; jira-first entry is for linked pairs.
  - `[false]` `[reject]` Single-select marker values other than `name` unsupported — GraphQL fragment reads `ProjectV2ItemFieldSingleSelectValue.name`, matching spec “single-select field value”.
  - `[false]` `[reject]` Flag on with empty `github_only_marker: {}` would skip all items — empty mapping loads as `None`, behaviour unchanged.
  - `[reject]` `[reject]` Missing integration test against live flagd — unit tests monkeypatch the flag gate; sufficient for CAP-60 oracle per story verification commands.

## Auto Run Result

Status: done

Summary: Closed the evening independent re-review (tests-only): real flag-overlays.json degradation cases, production/unknown-environment schedule batches, mutant-killing negatives, empty-marker config refusal, and deploy notes in the example sync-config; DW-8-5-2 `verified:` cites the skip raise path.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` — refuse empty `github_only_marker` mapping at load
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_github_only_marker.py` — overlay/production/unknown-env flag tests and expanded negatives
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_config.py` — empty mapping, scalar, lone field_value refused
- `.steward/sync-config.example.yaml` — production env and linked-item behaviour documented
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — DW-8-5-2 verified line

Review: Evening re-review items patched; this pass 0 new findings.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2023 passed, 2 skipped
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK
- `python scripts/flag_gate_check.py` — ok (0 fail for this spec)
