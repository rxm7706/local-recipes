---
title: '25.3: The ledger-regression verdict reads a re-key map, so a rebase moves done rows as done'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A fold renumbers every ledger key and fixes slug divergences. ledger-regression's `_tail` continuity survives a numeric-prefix change but not a slug change or an `epic-N` row; story-status confirms a done story by merge subjects naming its OLD id. Each reads as a regression or false green on a rebase — a red the standard says must not exist. (Corrected 2026-09-16: not every row, the slug-changed and epic rows.)

**Approach:** The fold PR ships planning-artifacts/rekey-<date>.md (one `old -> new` per line, # comments). When that file is in the PR diff, ledger-regression applies the map to main's ledger before comparing; promote_sprint_status.py --rekey regenerates the tracked twin through the same map, refusing collisions or dropped done rows; story-status-check reads the same map.

## Boundaries & Constraints

**Always:**
- A done row whose key moves per the map and stays done is not a finding.
- The map moves keys, never statuses: done -> backlog through the map is still a FAIL.
- Dangling map lines (old key absent on main, or new key absent in head) are rekey-map-dangling FAIL.
- Without a map in the diff, behaviour is byte-identical to today; existing ledger.py tests pass unchanged.
- --rekey is byte-stable on a second run.

**Never:**
- Do not let the map carry statuses or any syntax beyond old -> new and comments.
- Do not silently drop a done row whose key is in neither the map nor the head.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| rebase, statuses kept | 3-epic ledger renumbered via map | zero findings | none |
| status flipped through map | done -> backlog on one mapped row | exactly one ledger-regression FAIL | fail |
| dangling old key | map line old key not on main | rekey-map-dangling FAIL naming the line | fail |
| no map in diff | ordinary PR | identical to current behaviour | as today |
| --rekey collision | two old keys -> one new key | promote refuses, non-zero | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-one-chain-per-station CAP-3(g)`.
Standard: `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`.
Surface: doctor sources/ledger.py, pyforge/doctor/rekey.py, scripts/promote_sprint_status.py --rekey, pixi.toml sprint-ledger-sync passthrough, story-status-check, doctor fixture tests.
Ledger key: `25-3-the-ledger-regression-verdict-reads-a-re-key-map-so-a-rebase-moves-done-rows-as-done`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-25-3-the-ledger-regression-verdict-reads-a-re-key-map-so-a-rebase-moves-done-rows-as-done.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `a0a7f38713` (2026-09-16, "Merge pull request #1390 from rxm7706/doctor-25-3-rekey-classify"). Ledger row `25-3-the-ledger-regression-verdict-reads-a-re-key-map-so-a-rebase-moves-done-rows-as-done: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `scripts/.spec-surface-baseline.json`, `scripts/bmad_drift_check.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `25-3-the-ledger-regression-verdict-reads-a-re-key-map-so-a-rebase-moves-done-rows-as-done: done`).
- `## Auto Run Result` reconstructed from git (none survived).
