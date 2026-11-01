---
title: "113.3: dispatch runs the readiness stage before the dev session starts"
type: 'feature'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.marshal.egm_dispatch_readiness
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "marshal factory dispatch launches the harness session with no pre-launch challenge; the launch is byte-identical to today's"
  cleanup: "90 days after ON in every environment (Q4); the date is set when the switch turns ON everywhere"
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
---

<intent-contract>

## Intent

**Problem:** a dispatched story bounces on a Spec gap or contradiction most weeks (a bmad-loop CRITICAL escalation, a review send-back, a post-merge fix story). The gap is in the story spec before the session starts; nobody reads it cold.

**Approach:**
- When the materialized `[challenge].stages` includes `readiness` and the key is on, `marshal factory dispatch` runs CAP-298's `readiness` stage — the `implementation-readiness` persona alone — on the story's spec before the harness launches.
- The hook is an intent/outcome pair on the dispatch run's journal (AD-5, AD-26, AD-28); the report path sits on the run record; a red report is visible in `marshal watch` and the journal.
- v1 reports only (operator-informed session default of 2026-11-01): the story spec's `status` is not moved and the ledger is never written. The automatic move to `draft` is wave 2 behind its own switch.
- With the key off the launch is byte-identical to today's.

Ledger key: `113-3-dispatch-runs-the-readiness-stage-before-the-dev-session-starts`.
Type / Effort / Deps: feature / M / 113.1, 113.2.

### Living CAP citations

- **CAP-300** — the capability this story realizes.
- **CAP-298** / **CAP-299** — the verb and the block the hook reads (Stories 113.1, 113.2).
- **`spec-feature-flag-governance:CAP-1`** — the flag block; Q3, Q4, Q6.

## Acceptance Criteria

- **AC1 — The key.** `pyforge.marshal.egm_dispatch_readiness` is in `flags.json` (`defaultVariant: off`) and `flag-overlays.json` (`off` everywhere) with the clock fields; `test_flags.py` and `flag-inventory` name it against CAP-300.
- **AC2 — ON.** With the key on and `readiness` in the materialized stages, dispatch runs the readiness stage on the story spec before launch; the journal carries the intent and the outcome; the run record carries the report path; `marshal watch` shows a red report.
- **AC3 — Report only.** The story spec's `status` and every ledger are byte-identical before and after the hook, red or green; a test pins both.
- **AC4 — OFF.** With the key off, or `readiness` absent from the stages, the launch sequence is byte-identical to today's (the journal has no challenge entries).
- **AC5 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_readiness_hook.py`), with the harness session stubbed.
- **AC6 — The domain.** No new exit code; a hook refusal (plugin absent) is journaled and the dispatch proceeds as if the hook were off.

## Boundaries & Constraints

**Always:**
- Journal the intent before the spawn and the outcome after; keep the hook before launch and outside the landing surface.

**Never:**
- Never move a story spec's `status`, never write a ledger, never block or fail the dispatch on a red report in v1; never spawn more than the one persona.

</intent-contract>

## Binding

- Parent capability: CAP-300.

Parent: CAP-300

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-3-dispatch-runs-the-readiness-stage-before-the-dev-session-starts`.
- Deps: 113.1, 113.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass.

**Run before the push:**
- Two-state flag coverage: `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_readiness_hook.py` — `@flag_states("pyforge.marshal.egm_dispatch_readiness")`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger); session default 4 (report only in v1) binds here.

## Review Triage Log

- (none yet)
