---
title: '81.3: The campaign supervisor keeps --retry-environment-blocks across its cycles'
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `cli/dispatch.py::_spawn_campaign_supervisor` starts the detached `dispatch_fleet_supervisor` with the
campaign's mode, cycle bounds, station, story list, harness and in-flight cap (Story 22.11 threads the scoping flags so
"every SUPERVISED tick re-runs the SAME scoped/sequenced" campaign), but not `retry_environment_blocks`. A campaign
launched with `--retry-environment-blocks` therefore skips an environment-classified block only in its foreground first
cycle; every supervised cycle after it runs without the flag, stops on the same block (MRS-DRAIN-005) and the campaign
ends. Found 2026-10-01: campaign `pyforge-marshal-20261001T214108388Z-9418f6e6` exited after one cycle on 81.1's
OAuth-refresh block while 81.2 was still running.

**Approach:** `_spawn_campaign_supervisor` takes `retry_environment_blocks` and passes it on the supervisor's argv;
the supervisor parses it and hands it to every `run_fleet_drain` cycle it runs. False stays the default.

Ledger key: `81-3-the-campaign-supervisor-keeps-retry-environment-blocks-across-its-cycles`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 22.11 (FR-193 CAP-10, the campaign's flags threaded through every supervised tick). A defect of shipped
  behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a campaign launched with `--retry-environment-blocks` When its supervisor is spawned Then the spawn argv carries the flag and the supervisor's parsed arguments read it true
- Given that campaign's second cycle and an environment-blocked story When the cycle runs Then the story is skipped (MRS-DRAIN-004) and the next eligible story is dispatched
- Given a campaign launched without the flag When its supervisor runs Then cycles behave as today
- Given the flag dropped from the spawn argv When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Thread the flag the way Story 22.11 threads station and stories.

**Never:** Do not change how a block is classified. Do not retry or skip a story-classified block.

</intent-contract>

## Binding

Parent: Story 22.11 (FR-193 CAP-10); defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (night) entry.
Ledger key: `81-3-the-campaign-supervisor-keeps-retry-environment-blocks-across-its-cycles`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 under the operator's ruling to fix the drain defects found that day now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
