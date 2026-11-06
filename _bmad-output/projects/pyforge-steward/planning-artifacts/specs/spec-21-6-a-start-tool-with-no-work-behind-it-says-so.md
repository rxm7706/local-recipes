---
title: "21.6: A start tool with no work behind it says so"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: 'cdb8879b8d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-3-start-get-survives-disconnect.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-4-the-other-seven-mcp-faces.md
  - docs/dreams/pyforge-unifying-strategy.md
deferred:
  - id: start-tools-wire-to-the-cli
    summary: "Second half of the operator's ruling on N1: wire the seven start tools to the CLI grammar. It needs a capability, an allowlist of verbs per face, and a check of what the host image can run. A worker subprocess sits outside the session hook, so an unlisted verb on start_duty or start_build would reach what an agent is refused at the shell. Scribe's face closes DW-scribe-5-2 when wired."
    location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-6-a-start-tool-with-no-work-behind-it-says-so.md:41
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Seven station MCP faces (doctor, herald, marshal, mason, scribe, steward, warden) answer `start_*` with a runner that
does no work and returns `{"target": target, "completed": True}`. `execute_supervised_run` records anything a runner returns as
`SUCCEEDED`, so a caller reads a finished run for work that never happened. The audit of 2026-11-05 found this as N1.

**Approach:** Operator ruling 2026-11-05: "honest runner first then wire to cli". This story is the first half. Each runner raises
through one shared helper, because only an exception ends a run `FAILED`. A returned `{"completed": False}` would still read
`SUCCEEDED`.

Ledger key: `21-6-a-start-tool-with-no-work-behind-it-says-so`. Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-4** — every station has a service face (canopy:FR-11, canopy:FR-12).

## Acceptance Criteria

- **AC1 — The seven runners.** `run_scan`, `run_notice`, `run_loop`, `run_build`, `run_recall`, `run_duty` and `run_audit` each raise `RunnerNotWiredError`, with a message that names the station and the tool and says nothing ran.
- **AC2 — The run.** A run started on each of the seven faces ends `FAILED`, and `get_*` returns the message in `result.error`. Warden's portal status page shows both.
- **AC3 — What stays.** Atlas's runner does its work and does not change. `execute_supervised_run` does not change. No station CLI is called.
- **AC4 — The record.** No `mcp_asgi.py` under `src/shared/packages/django-*/` keeps `"completed": True`. CAP-4's `verified:` note says which face does work. `DW-steward-egm-2026-11-05-1` closes, and the wiring half stands as `DW-steward-21-6-2`.

## Boundaries & Constraints

- Scope is the seven runners. The `start_*` and `get_*` tools stay listed, and their handles, assertions and bounds stay as they are.
- Station skills are out of scope. Story 29.5 AC3 has each skill say what its runner does as the code stands, so it recompiles after this story lands.

**Never:**
- Never call a station CLI or import `pyforge.*` from a runner here; that is the second half, with its allowlist.
- Never return a dict from a runner that did no work: the worker records any return as `SUCCEEDED`.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-4

- Closes: `DW-steward-egm-2026-11-05-1`.
- Opens: `DW-steward-21-6-2`.
- Epic: Epic 21.

## Verification

**Commands:**

- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0.
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: exit 0.
- `grep -l '"completed": True' src/shared/packages/django-*/src/*/mcp_asgi.py` — expected: no match.

## Spec Change Log

- 2026-11-05: minted on the operator's ruling, "honest runner first then wire to cli".
