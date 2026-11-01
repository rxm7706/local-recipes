---
title: "113.13: resolve writes only marshal's Spec and prints the memlog command for any other"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad/scripts/memlog.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
---

<intent-contract>

## Intent

**Problem:** `marshal factory challenge resolve` writes other stations' memlogs and takes the owner from the report.
Line numbers are at `03a7aff5d9`.

- `run_resolve` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:576-605`) appends one
  `memlog.py` event per accepted finding to whichever Spec the report's `spec_workspace` names (`with_provenance`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:429-446`). That breaks two absolute
  Constraints of the same Spec: Marshal "never edits another project's artifacts" (`SPEC.md:1154`) and "No Marshal code
  path writes into another station's artifacts" (`SPEC.md:1158`) (EGM audit MAR-M-Z5).
- `audit_plan` (`cli/challenge.py:484-498`) runs the `AGENTS.md` and `CHAIN-STANDARD.md` rules targets under
  `pyforge-marshal`, so their findings carry `spec-pyforge-marshal` as owner, and resolve would write them to the wrong
  memlog: `AGENTS.md` is governed by `spec-pyforge-scribe`, `CHAIN-STANDARD.md` by `spec-one-chain-per-station`
  (MAR-M-C5).
- CAP-303's intent names a story-spec-edit route (`SPEC.md:1138`) that no code or check carries.

**Approach (operator ruling 2026-11-01: resolve appends to marshal's Spec and prints the exact `memlog.py` command for
any other owning Spec):**
- **The owner, checked.** `resolve` derives the expected owning Spec from `--project` (or, for a rules target, from the
  per-target owner override below) and refuses with the usage code a report whose `spec_workspace` matches neither, so a
  report can never name its own write target.
- **Marshal writes only marshal.** When the owning Spec is `spec-pyforge-marshal`, `resolve` runs `memlog.py` as today.
  For any other owning Spec it writes nothing there and prints, per accepted finding, the exact command the operator
  runs: `uv run _bmad/scripts/memlog.py append --workspace <spec-folder> --type event --text "<acceptance text>"`. The
  rejected ids and reasons still go back into the report (Tier 3).
- **Rules findings carry their governor.** `audit_plan` gives `AGENTS.md` findings the
  `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe` workspace and `CHAIN-STANDARD.md`
  findings `docs/governance/spec-one-chain-per-station`, through a per-target owner override recorded on the report.
- **The contract follows the code.** The memlog events for MAR-M-Z5 and MAR-M-C5 and the operator's decision are
  already on `spec-pyforge-marshal` (commit `7dde4a0202`). Re-derive CAP-303 with `bmad-spec`: the success line shows
  `--accept ID[:NOTE]`, `--reject ID[:REASON]` and `--type event`; resolve writes only marshal's Spec and prints the
  command for any other; the story-spec-edit route is dropped from the intent or given a check. The ruling keeps
  `SPEC.md:1154` and `:1158` as written, so no named exception and no AD note is needed. Then the cascade re-stamp and
  the scoped stamp.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the subverb stays behind
  `pyforge.marshal.egm_resolve_bridge`.

Ledger key: `113-13-resolve-writes-only-marshal-s-spec-and-prints-the-memlog-command-for-any-other`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-303** (FR-245): an accepted finding travels the chain's only write path.
- The Constraints at `SPEC.md:1154` and `:1158` bound it; they are unchanged.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL8: MAR-M-Z5, MAR-M-C5); the operator's ruling of 2026-11-01 on cross-station writes.

## Acceptance Criteria

- **AC1 — The refusal.** `resolve --project pyforge-marshal` on a report whose `spec_workspace` names
  `spec-pyforge-atlas` (and no owner override) refuses with the usage code and writes nothing
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC2 — Marshal's own Spec.** An accepted finding owned by `spec-pyforge-marshal` is appended through `memlog.py`
  exactly as today.
- **AC3 — Any other Spec.** An accepted finding owned by another Spec (a station `--project`, or a rules override) is
  never written; stdout carries one exact `uv run _bmad/scripts/memlog.py append --workspace <spec-folder> --type event
  --text "…"` line per finding, with the workspace and text the finding carries; the memlog stub records no call.
- **AC4 — The overrides.** `audit_plan` gives `AGENTS.md` the `spec-pyforge-scribe` workspace and `CHAIN-STANDARD.md`
  `docs/governance/spec-one-chain-per-station`; a station skill and every mint and decompose target keep their station
  Spec.
- **AC5 — Rejections.** Rejected ids and reasons are written back into the report as today.
- **AC6 — The contract.** CAP-303 reads as the Approach states, re-derived by `bmad-spec` (both self-validate passes
  logged); `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC7 — Mutation.** Letting `resolve` call `memlog.py` for a non-marshal Spec fails AC3's test. Restore it.
- **AC8 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Print a command the operator can paste as is; quote the text so a shell reads it as one argument.

**Ask first:**
- Any write outside `spec-pyforge-marshal`, or a named exception to `SPEC.md:1154` / `:1158`.

**Never:**
- Never write another station's memlog, `SPEC.md`, ledger or story spec; never hand-edit `SPEC.md`.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

**Residual risk:**
- A report written before this story carries no owner override, so a rules finding from it resolves under
  `spec-pyforge-marshal` only if its `spec_workspace` says so; the operator re-runs the target to get the override.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-303 (FR-245).

Parent: `spec-pyforge-marshal` CAP-303 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL8).
- Epic: Epic 113.
- Ledger key: `113-13-resolve-writes-only-marshal-s-spec-and-prints-the-memlog-command-for-any-other`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` and the re-derived `SPEC.md`; within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: backlog

Summary: not yet implemented.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL8: MAR-M-Z5, MAR-M-C5)
  and the operator's ruling of 2026-11-01 (resolve appends to marshal's Spec and prints the exact `memlog.py` command for
  any other owning Spec; implement in the Story 113.7 landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- (none yet)
