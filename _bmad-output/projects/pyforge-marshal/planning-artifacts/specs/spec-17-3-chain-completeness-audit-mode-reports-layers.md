---
title: Chain-completeness audit mode reports layers
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 3f4b28838bdbca05c7f425450c19d2d8240358f9
---

<intent-contract>

## Intent

**Problem:** Chain-completeness audit (FR-150 residual / `spec-fleet-chain-completeness` CAP-3) and per-project invocation (FR-152; AD-72) are incomplete — operators still hand-check which Dream/Spec/brief/PRD/architecture/epics/stories layers exist.

**Approach:** Add a read-only audit mode on doctor board/chain sources that reports, for a named project, which chain layers exist and which are missing. Seed layer computation from `generate.py`'s existing derivation (never a second derivation). Invocable per-project without touching another's tree.

## Boundaries & Constraints

**Always:** Reuse `docs/dashboard/generate.py` `FLEET_STAGES` + `_stage_globs` + `_resolve` (via `_load_dashboard_generate`); report every layer that computation names; scope globs to one named project; read-only; fixture-covered; distinct from `--dreams` and INV-0..3 / INV-A..D.

**Block If:** Generating a second independent layer graph becomes necessary to satisfy ACs.

**Never:** Implement orchestrated regeneration (FR-148 / Story 17.4) or orphan cleanup (FR-151). Never invent a parallel layer graph. Finalize marshal ledger only (doctor code surface).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Complete primary chain | `--layers --project pyforge-x` with fixtures covering stages | One summary finding; evidence lists all `FLEET_STAGES` present/missing; status OK when no missing among non-`na` stages examined | No error |
| Missing layers | Same, omit brief/prd files | Summary finding WARN; evidence.missing names absent layers | No error |
| Unknown project | `--project` slug with no planning tree | Unevaluable WARN naming the project | No crash |
| Isolation | Two projects under target; audit A only | Findings/evidence name only A; B paths not required | No error |
| Wrong host source | `--layers` on non-`chain-completeness` | argparse error exit 2 | CLI rejects |
| Conflict with INV path | `chain-completeness` without `--layers` | Existing INV-A..D gather unchanged | No error |
| Missing generate.py | target lacks `docs/dashboard/generate.py` | Unevaluable WARN | degrade, never raise |

</intent-contract>

## Code Map

- `docs/dashboard/generate.py` — seed only: `FLEET_STAGES` (~1569), `_stage_globs` (~1900), `_resolve` (~1757), `FLEET_NA` / `FLEET_UX` / `GOVERNANCE_DIR`; do not fork globs
- `src/.../sources/board.py` — `_load_dashboard_generate` (~922); add `gather_chain_layers_audit(target, project)`; temporarily set `mod.REPO_ROOT = target` so `_resolve` hits the fixture/live tree
- `src/.../sources/__main__.py` — `--layers` + `--project` on `chain-completeness` (mirror `--dreams` on `dream-chain`)
- `src/.../models.py` — `Source.CHAIN_LAYERS_AUDIT = "chain-layers-audit"`
- `src/.../sources/__init__.py` — REGISTRY row (not a DISPATCH name)
- `src/.../data/report-schema.json` — add enum member
- `tests/meta/test_source_independence.py` — `SOURCE_MODULE` map to `board.py`
- `pixi.toml` — `chain-layers-audit-check` task
- Continuity: Story 17-2 `dream-chain --dreams` pattern; existing `gather_chain_completeness` INV path must stay byte-identical when flag absent
- Parent: `spec-fleet-chain-completeness/SPEC.md` CAP-3; epics Story 17.3

## Tasks & Acceptance

**Execution:**
- `models.py` + `report-schema.json` + `__init__.py` REGISTRY + `SOURCE_MODULE` — add `chain-layers-audit` Source member (DISPATCH stays INV-only)
- `board.py` — implement `gather_chain_layers_audit`; load generate.py; set `REPO_ROOT`; for `primary=True` globs of the named project, report each `FLEET_STAGES` layer present/absent (handle `verify` via generate's task gate or mark absent when no pixi tasks in fixture)
- `__main__.py` — `--layers` (host=`chain-completeness`) requires `--project <slug>`; mutual exclusion with unrelated flags as needed; default INV path unchanged
- `pixi.toml` — task `chain-layers-audit-check` documenting CLI
- `tests/unit/test_sources_board_chain_layers_audit.py` + dispatch CLI cases — cover I/O matrix (incl. isolation)

**Acceptance Criteria:**
- Given a named project fixture, when `chain-completeness --layers --project <slug> --json`, then findings report presence/absence for every `FLEET_STAGES` layer from generate.py
- Given two projects under one target, when auditing only A, then B is never named in evidence and A's missing layers still report
- Given no `--layers`, when `chain-completeness` runs, then INV-A..D gather behavior is unchanged
- Given `--layers` on another source or without `--project`, when CLI parses, then exit 2 with a clear error

## Design Notes

- **CLI:** `python -m pyforge.doctor.sources chain-completeness --layers --project <slug>` — not a new DISPATCH entry (keeps INV default identical).
- **Seed mechanic:** import generate via existing `_load_dashboard_generate`; assign `mod.REPO_ROOT = target.resolve()` for the gather duration so `_resolve`/`_stage_globs` operate on `target` without copying glob tables.
- **Severity:** warn-only summary (OK when no missing among applicable stages; WARN when any missing or unevaluable) — report mode, not a replacement for INV FAIL gates.
- **"stories" in epic prose:** report generate.py's own stage names (`epics`, `sprint`, `code`, …); do not invent a separate `stories` layer.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py -q` -- expected: PASS
- Live: `python -m pyforge.doctor.sources chain-completeness --layers --project pyforge-marshal --json` -- expected: layer matrix, no writes

## Spec Change Log

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` Aligned pixi task name to `chain-layers-audit-check` per Code Map; CLI spelling documented (`--layers --project`)

## Auto Run Result

Status: done
Summary: Added read-only `chain-completeness --layers --project <slug>` audit mode on pyforge-doctor board sources. Layer presence/absence is seeded from `docs/dashboard/generate.py` (`FLEET_STAGES` / `_stage_globs` / `_resolve`) — no second derivation. Distinct from INV-A..D and `--dreams`.
Files:
- `board.py` — `gather_chain_layers_audit`
- `__main__.py` — `--layers` / `--project` CLI
- `models.py` / REGISTRY / report-schema / SOURCE_MODULE — `chain-layers-audit`
- `test_sources_board_chain_layers_audit.py` — I/O matrix + isolation + CLI
- `pixi.toml` — `chain-layers-audit-check`
Review: low patch only (task name); followup_review_recommended=false (score 1).
Verification: unit+meta PASS (146); live marshal audit reports 14/15 layers (missing: retro); INV path and `--dreams` unchanged.
Residual: primary-chain-only report (epic "named project"); satellite chains under the same project are deferred to Epic 21 extensions.
