---
title: "25.2: A poll-cursor sensor refreshes the history over Warden's fleet inventory"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - docs/dreams/pyforge-atlas.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/event_source.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-25-1-a-per-repo-dependency-history-dataset-from-git-pkgs-and-an-estate-pixi-parser.md
flag:
  key: pyforge.atlas.dependency_history_sensor
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "the sensor skips every tick with a flag-off reason; the history refreshes only when its job is run by hand"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.1 builds each repo's history when its job runs, but nothing notices that a repo moved. Webhooks
were rejected as Atlas's default trigger (`orchestration/event_source.py:17-18`: an inbound webhook needs a public
ingress and cannot be exercised offline), and the operator ruled on 2026-09-28 that a poll cursor drives this refresh,
over the repos Warden inventories (`spec-pyforge-warden:CAP-26`).

**Approach:** A raw catalog dataset, `warden_fleet_inventory`, reads Warden's JSON inventory export from a configured
path (AD-2; no import of `pyforge.warden` or `django_warden_fabric`). A dagster-free decision module beside
`event_source.py` compares each inventoried repo's default-branch head SHA with the cursor (a JSON map of repo → last
processed head), coalesces every moved head of one tick into one run decision for the Story 25.1 job with a stable
`run_key`, and returns the advanced cursor; unchanged heads skip with a reason. The production source is injectable and
defaults offline (`[]`), the way `offline_event_source` does; the attended live wiring reads the real export once
Warden's Story 16.1 lands. Only `orchestration/definitions.py` wraps the decision in a Dagster sensor (AD-1), and
`dagster-dryrun` still loads the definitions. The flag is read through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); OFF, every tick
skips with a `flag off` reason.

Ledger key: `25-2-a-poll-cursor-sensor-refreshes-the-history-over-warden-s-fleet-inventory`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-25.1.

### Living CAP citations

- `spec-pyforge-atlas` CAP-61 (FR-69); AD-1, AD-2, AD-6 (one sensor, coalesced run requests).
- `spec-pyforge-warden:CAP-26` (the export's producer); `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture inventory export of three repos and a cursor naming their current heads, When the sensor decides, Then it skips with a reason and the cursor is unchanged
- Given two of those heads moved, When the sensor decides, Then it returns one run decision naming both repos, a stable `run_key`, and the advanced cursor
- Given a repo newly added to the inventory, When the sensor decides, Then it is treated as moved
- Given the default production source, When the sensor ticks, Then it sees no events and opens no network connection
- Given `orchestration/`, When `kedro-catalog-check`'s AD-1 meta-test runs, Then only `definitions.py` imports Dagster, and nothing imports `pyforge.warden` or `django_warden_fabric`
- Given the flag OFF, When the sensor ticks, Then it skips with a `flag off` reason

## Boundaries & Constraints

**Always:**
- Keep the decision a pure function over (inventory snapshot, cursor), testable offline with fixtures (AD-11).
- Read the inventory as a catalog dataset (AD-2); the only cross-station contract is the export's JSON shape.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile `spec-pyforge-atlas` and every co-governor `spec-surface-check` names; scoped stamps only.

**Never:**
- Add a webhook, an inbound endpoint or a daemon.
- Re-fetch anything in the sensor; the job's dataset owns incrementality (AD-5).
- Import `pyforge.warden` or `django_warden_fabric`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| nothing moved | heads equal the cursor | skip with a reason | cursor unchanged |
| two moved | two heads differ | one run decision, both repos | cursor advanced |
| new repo | not in the cursor | treated as moved | — |
| repo removed | in the cursor, not the inventory | dropped from the cursor | no run |
| unreadable export | malformed JSON | skip with a reason | cursor unchanged |
| flag OFF | key off | skip, `flag off` | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-atlas` CAP-61 (FR-69).
Dream: `docs/dreams/pyforge-atlas.md` § Realization log → *2026-09-28 (night) — Proposed: Atlas keeps each scanned repo's dependency history, so a fix knows when a dependency arrived and which other repos carry it*.
Ledger key: `25-2-a-poll-cursor-sensor-refreshes-the-history-over-warden-s-fleet-inventory`.
Ledger status at mint: `backlog`.
Deps: S-25.1.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; the AD-1 import-direction meta-test).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.atlas.dependency_history_sensor` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON decides over the fixture export, OFF skips with `flag off`.
- `pixi run -e pyforge-atlas dagster-dryrun` — expected: pass (the definitions load with the new sensor).
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28). Implementation and review stay separate.
