---
title: '34.4: Each station has a checked-in flag inventory of its runtime capabilities'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
flag-exempt: flag-infrastructure   # the retrofit's own infrastructure (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py
  - src/platform/config/flags.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-7 retrofits the rule onto work that predates it: every station's existing
capabilities whose code is reachable at runtime go behind flags that default ON (one flag per CAP, Q6), so each flag
works as a kill switch; and every pre-rule backlog story gains a flag block or an exemption, so the CAP-2 gate's warnings
reach zero. The retrofit stories are each Smith's, minted after an inventory exists. Nothing lists, per station, which
CAPs reach a user at runtime and which of them a flag gates.

**Approach:** `scripts/flag_inventory.py` (a report, never a gate: exit 0 unless it cannot run, exit 2 then) writes one
checked-in Markdown report per station to `docs/governance/flag-inventory/pyforge-<station>.md`; a `flag-inventory` pixi
task runs it. For each station:
- every CAP declared by an open Spec folder the station hosts, joined to its code the way
  `pyforge.doctor.sources.capability_effect` already joins them (the citing story's `Surface:` line in `epics.md`) —
  reuse that join, never invent a second one;
- whether that code is reachable at runtime and through what: a CLI verb (the station's CLI), an MCP tool (the station's
  MCP registry), a REST route or a portal view (the station's `dashboard/` URLs);
- the flag key in the one tree that gates it, or `none`;
- every pre-rule `type: feature` story spec the gate (Story 34.2) warns on, with its key and status.
Each report's header names the SHA it read and two counts — runtime CAPs with no flag, warned specs — the numbers each
Smith's retrofit stories are minted against after this lands. The output is deterministic, so a second run on the same
tree is byte-identical.

Ledger key: `34-4-each-station-has-a-checked-in-flag-inventory-of-its-runtime-capabilities`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-34.2.

### Living CAP citations

- `spec-feature-flag-governance` CAP-7 (the inventory half; the retrofit half is each Smith's, minted after this lands).

## Acceptance Criteria

- Given the live tree When `pixi run -e pyforge-guild flag-inventory` runs Then it writes eight reports under `docs/governance/flag-inventory/` and exits 0
- Given a fixture station with one CAP whose story's `Surface:` names a CLI verb module and no flag in the tree When the inventory runs Then that CAP is listed with its verb and `none`
- Given the same CAP with its key in the tree When the inventory runs Then it lists the key
- Given a CAP whose surface is only a planning document When the inventory runs Then it is listed as not reachable at runtime, never counted as unflagged
- Given a pre-rule `type: feature` spec with neither block nor exemption When the inventory runs Then it appears in its station's warned list with its key and status, matching the gate's WARN list for that station
- Given a second run on the same tree When the reports are compared Then they are byte-identical
- Given an unreadable tree When the inventory runs Then it exits 2 naming the input and writes no partial report
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep the script in `scripts/`, its tests in `tests/scripts/`, its reports in `docs/governance/flag-inventory/`; add the
  script's reason-tagged line to `scripts/spec_surface_allowlist.txt`; register the task in `pixi.toml` and regenerate
  `environment.yaml` in the same change; record the new paths in the Guild Spec's `.memlog.md` via `memlog.py`.
- Reuse the gate's classifier (Story 34.1's `scripts/flag_rule.py`) for the warned list, so the inventory and the gate
  can never disagree.
- Treat a CAP whose code the join cannot resolve as its own `unresolved` row, never as unflagged and never dropped.

**Never:**
- Do not mint, draft or propose any station's retrofit stories: each Smith mints its own after this lands.
- Do not add a flag to the tree or change any station's code.
- Do not make the inventory a detector (no `DETECTOR` marker, no `detectors-ci` row): it reports, the gate judges.
- Do not import a station's internals; do not edit `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CLI CAP, no flag | verb module in `Surface:` | row with the verb, `none` | — |
| flagged CAP | key in the tree | row with the key | — |
| planning-only CAP | no runtime surface | listed, not counted as unflagged | — |
| unresolvable CAP | no citing story | `unresolved` row | — |
| warned spec | pre-rule, `neither` | in the station's warned list | — |
| rerun | same tree | byte-identical reports | — |
| unreadable tree | malformed JSON | nothing written | exit 2 |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-7 and the Q6 ruling (memlog 23), the
Dream's *What it looks like when real* (the retrofit runs in two steps), decomposed 2026-09-28 (night) as Epic 34's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-7 (Guild-owned; the inventory is
Doctor's, the retrofit stories each Smith's).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-4-each-station-has-a-checked-in-flag-inventory-of-its-runtime-capabilities`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_inventory.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-inventory` twice — expected: exit 0, and `git diff --exit-code docs/governance/flag-inventory/` after the second run.

## Review Triage Log
