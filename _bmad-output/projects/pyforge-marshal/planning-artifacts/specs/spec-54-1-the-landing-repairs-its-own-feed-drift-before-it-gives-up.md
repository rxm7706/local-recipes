---
title: '54.1: The hand ledger sync repairs unrelated feed drift instead of refusing'
type: 'feature'
created: '2026-09-24'
updated: '2026-09-28'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - scripts/promote_sprint_status.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Re-scoped 2026-09-28 (operator ruling; CAP-265 amended).** The contract minted on 2026-09-24 had `dispatch_land_finalize` repair feed drift before promoting. Its premise was a misread. Doctor 24.2's and 24.3's automatic finalizes computed the promotion (24.2's journaled INTENT names the key) and died pushing to `main` inside the pre-push hook's `pr-preflight` — CAP-277, Story 68.1. The automatic promotion never depended on the feed: `cli/land._promote_sprint_ledger` reports a feed-sync refusal as an `MRS-LAND-011` WARN and still advances the landed key in the tracked twin directly (`render_ledger_advancements`). Feed drift blocked only the human fallback. The ledger key, the epic and the CAP number are kept; the automated landing path is out of this story.

**Problem:** `pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>` runs `scripts/promote_sprint_status.py::main`. Its per-key guard (`:394-445`) compares the Tier-3 feed with the tracked twin and refuses the whole project when the feed is behind on any key — a `done` or story `blocked` value the feed has lost (`regressions`) or a twin key the feed lacks (`missing`) — even when those keys have nothing to do with the story being promoted. The operator then runs `--repair-feed` (the same pull-forward, `repair_feed`, `:241-285`), hand-flips the one key again and re-syncs; doctor 24.2 and 24.3 each carried the fix in a separate PR (#1578, #1580). And `repair_feed` rewrites the feed as "everything before `development_status:`" plus the sorted map, so a feed whose top-level metadata follows the map loses it (`DW-marshal-repair-feed-drops-trailing-metadata-2026-09-27`; marshal's own feed carries `generated`, `last_updated`, `project`, `project_key`, `tracking_system` and `story_location` after the map).

**Approach:**
- On a bare sync, when `regressions` or `missing` is non-empty, `main()` runs the repair itself instead of refusing: `repair_feed(src, statuses, existing)` pulls the twin's values for those keys into the feed, and the sync proceeds with the merged map. This is exactly today's `--repair-feed` branch (`:406-434`), taken by default.
- The repair only ever moves the feed toward the twin: a key the feed advances past the twin (the promotion, e.g. `backlog → done`, `blocked → done`) is not in `regressions`/`missing`, so it is promoted as written and never rewritten; no key moves away from `done`.
- The report names every repaired key: one `REPAIRED <project>: …` line (as today) followed by one line per key, `  <key>: feed <value-or-absent> -> twin <value>`.
- `--allow-regression` stays the one way to move a key out of `done`: it skips the repair and writes the feed's regression, naming each key (today's `WARNING` line). `--repair-feed` stays accepted and means the same as a bare sync (help text says so).
- `repair_feed` splits the feed at the end of the `development_status:` block — the first following line that starts a top-level key — and writes `head + block + tail`, so trailing metadata survives byte-for-byte.
- The module docstring, the two flags' help text, AGENTS.md's § Running and verifying line, `docs/how-to/one-chain-station-ops.md` and `docs/how-to/troubleshoot-bmad-agent-loops.md` say that a bare sync repairs and names the repaired keys, and that `--allow-regression` is the one way out of `done`.
- Unchanged: the `--rekey` path, the empty-feed refusal, `_write_ledger_locked`, `regressions()`, `apply_epic_rollups`, and every caller that imports `repair_feed`/`regressions` (`cli/deploy.py`, `cli/land.py`, `cli/chain.py`, `core/chain_regen.py`).

Ledger key: `54-1-the-landing-repairs-its-own-feed-drift-before-it-gives-up` (unchanged at the re-scope).
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-265 (FR-211), amended 2026-09-28.
- Kinship: `spec-pyforge-marshal` CAP-234 (absorbed from `spec-sprint-status-promotion-regression-guard`: any drift away from a tracked `done` is caught and named before it can overwrite the ledger — kept; the catch now repairs the feed instead of stopping the sync); CAP-277 (Story 68.1, the automatic promotion's real failure).

## Acceptance Criteria

- Given doctor 24.2's hand-sync shape in a fixture (a twin with 13 story keys `done` that the feed reads `backlog` or lacks, and the promoted key `backlog` in the twin, `done` in the feed) When `main(["--project", "<key>"])` runs with no flag Then it exits 0, the twin reads the promoted key `done`, the feed carries the 13 twin values, and stdout names each of the 13 keys with its feed and twin values
- Given a feed whose `generated`/`last_updated`/`project`/`project_key`/`tracking_system`/`story_location` lines follow the `development_status:` map When the repair runs Then those lines are present byte-for-byte afterwards
- Given a feed that moves a twin-`done` key to `backlog` When `main` runs with `--allow-regression` Then the twin is written with that regression and stdout names the key
- Given a feed that advances a key the twin reads `backlog` (or `blocked`) to `done` When `main` runs Then that key is promoted `done` and not rewritten by the repair
- Given a twin-`blocked` key the feed reads `backlog` When `main` runs Then the feed is restored to `blocked` and the key is named as repaired
- Given `--repair-feed` When `main` runs on the 24.2 fixture Then the result is identical to the bare sync
- Given the `--rekey` fixtures and an empty feed When `main` runs Then both behave exactly as today
- Given `test_main_refuses_missing_twin_key`'s fixture When the suite runs Then it asserts repair-and-report (exit 0, the key restored and named), not a refusal
- Given the default repair removed from `main` When the 24.2 fixture runs Then it refuses and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 54.1. The repair is exactly `repair_feed`'s one-directional pull of the tracked twin's values into the feed; only keys the feed is behind on are touched. Name every repaired key. Keep `--allow-regression` the one way to move a key out of `done`. Physical `_bmad-output/projects/<slug>/` paths.

**Never:**
- Do not change `dispatch_land_finalize`, `cli/land.py` or any marshal landing code; the automated promotion is out of scope (CAP-277 owns its failure).
- Do not change `regressions()` (CAP-234's detection), the `--rekey` path, the empty-feed refusal or the ledger lock.
- Do not write a key away from `done`, or rewrite a key the feed advances, without `--allow-regression`.
- Do not mint a new story key or flip `sprint-status-ledger.yaml` by hand; do not run `scripts/bmad-switch`.
- Do not hand-edit `SPEC.md`.

Co-governing Specs of `scripts/promote_sprint_status.py` in the spec-surface baseline: `spec-pyforge-marshal` (owner) and `spec-quick-dev-reconciliation` (absorbed into it) — reconcile each one the detector names. AGENTS.md is the cross-tool contract: keep its `sprint-ledger-sync` line one sentence, pointing, not copying (`spec-pyforge-scribe` CAP-27's parity meta-test).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| unrelated drift, bare sync | feed behind the twin on N keys it does not promote | feed repaired from the twin, promotion written, N keys named | exit 0 |
| promotion only | feed ahead of the twin on the promoted key | promoted as written | none |
| twin `blocked`, feed `backlog` | lost protected state | feed restored to `blocked`, key named | none |
| deliberate regression | `--allow-regression`, feed moves `done` → `backlog` | regression written, key named | none |
| trailing metadata | metadata after the map | kept byte-for-byte | none |
| `--repair-feed` | any of the above | same as a bare sync | none |
| empty feed | feed parses 0 statuses | skipped, as today | as today |
| `--rekey` | a fold's re-key map | as today | as today |

</intent-contract>

## Source

Contract first authored 2026-09-24 from `docs/dreams/pyforge-marshal.md`'s 2026-09-24 Realization-log entry and `spec-pyforge-marshal` CAP-265; re-scoped 2026-09-28 from the operator's ruling recorded in that entry's *Re-scoped 2026-09-28* note and in the Spec's `.memlog.md` (the 2026-09-28 (later) direction entry's item (4), and the 2026-09-28 decision entry re-scoping CAP-265).

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-265 (FR-211, amended 2026-09-28).
Ledger key: `54-1-the-landing-repairs-its-own-feed-drift-before-it-gives-up` (kept).
Ledger status: `backlog` (kept).
Deferred-work row closed by this story when it lands: `DW-marshal-repair-feed-drops-trailing-metadata-2026-09-27`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"54"` admits `scripts/promote_sprint_status.py`, `AGENTS.md` and the two how-to guides beside the default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` (or the scribe parity meta-test alone) — expected: pass after the AGENTS.md line changes.
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.
