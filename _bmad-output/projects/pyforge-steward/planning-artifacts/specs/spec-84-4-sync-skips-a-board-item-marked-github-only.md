---
title: "84.4: Sync skips a board item marked GitHub-only"
type: 'feature'
created: '2026-10-03'
status: 'done'
baseline_revision: '2360e20e336e1e5edbd180ced25d4cede6832019'
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

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 0, false 3, reject 1
- findings:
  - `[false]` `[reject]` Skip path only runs on `--github-item` entry, not `--jira-issue` — unlinked GitHub-only items are always discovered by GitHub item id in schedule/single-item flows; jira-first entry is for linked pairs.
  - `[false]` `[reject]` Single-select marker values other than `name` unsupported — GraphQL fragment reads `ProjectV2ItemFieldSingleSelectValue.name`, matching spec “single-select field value”.
  - `[false]` `[reject]` Flag on with empty `github_only_marker: {}` would skip all items — empty mapping loads as `None`, behaviour unchanged.
  - `[reject]` `[reject]` Missing integration test against live flagd — unit tests monkeypatch the flag gate; sufficient for CAP-60 oracle per story verification commands.

## Auto Run Result

Status: done

Summary: Added optional `github_only_marker` in sync config, flag `pyforge.steward.sync_github_only_marker` (off in production via overlays), and reconcile skip with info logging for unlinked marked items when the flag is on; closed DW-8-5-2.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` — config load, marker detection, skip exception path
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_github_only_marker.py` — acceptance tests
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_config.py` — marker load validation
- `src/platform/config/flags.json` and `flag-overlays.json` — new flag and env defaults
- `.steward/sync-config.example.yaml` — operator docs
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — DW-8-5-2 closed

Review: 0 patches; 4 findings rejected/false.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2003 passed, 5 skipped
- `pixi run --frozen -e pyforge-guild lint-types` — green after ruff import fix on steward
- `python scripts/spec_surface_reconcile.py` — OK after memlog reconcile
