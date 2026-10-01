---
title: "82.1: The session check's kit remedy applies the kit"
type: 'fix'
created: '2026-10-01'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `session.py::_seed_kit_findings` gives every non-ok `token-kit` / `codegraph-index` finding the remedy
`pixi run -e pyforge-guild marshal seed kit`. Without `--apply`, `marshal seed kit` only plans ("kit: dry-run; re-run
with --apply"), so the printed remedy never clears the finding.

**Approach:** the remedy becomes `pixi run -e pyforge-guild marshal seed kit --apply`, everywhere `_seed_kit_findings`
sets it.

Ledger key: `82-1-the-session-check-s-kit-remedy-applies-the-kit`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- CAP-5 (Story 63.4, the session check's remedy text) and CAP-162 (its kit reading). A defect of the remedy text, so no new CAP; `spec-feature-flag-governance` Q1:
  a `fix` needs no flag.

## Acceptance Criteria

- Given any non-ok `token-kit` or `codegraph-index` finding When `_seed_kit_findings` builds it Then its remedy is `pixi run -e pyforge-guild marshal seed kit --apply` (which provisions a `missing` or `stale` item; an `instrument-unavailable` item still needs its instrument installed)
- Given an ok finding When it is built Then its remedy stays `None`

## Boundaries & Constraints

**Always:** Steward shells marshal's CLI and never imports it.

**Never:** Do not change which findings are non-ok (Story 81.1's silent-status rule stands).

</intent-contract>

## Binding

Parent capabilities: CAP-5 (Story 63.4) and CAP-162 (defect of the remedy text; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 (evening) entry.
Ledger key: `82-1-the-session-check-s-kit-remedy-applies-the-kit`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: fix it now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

Review 1 (2026-10-01): an independent read-only reviewer confirmed `--apply` is `marshal seed kit`'s provisioning flag
(`cli/seed.py`; the default is a dry run), that it is idempotent and needs no other argument, that every non-ok path uses the
remedy while ok findings keep `None`, and that the four exact-equality assertions fail on revert. No high findings:

- `[medium]` `[patch]` The spec and ledger rows read `backlog`; a merged story left there respawns on every drain. Fixed at
  landing: `done`.
- `[low]` `[patch]` The epic and Dream said the remedy clears `instrument-unavailable` and "could not run"; `--apply` skips a
  layer whose instrument is missing. Fixed: the Given names `missing` / `stale`, and the AC notes the exception.
- `[low]` `[patch]` "a defect of CAP-162's remedy text": the remedy came from Story 63.4 under CAP-5. Fixed in the epic,
  the Dream and this spec.

## Auto Run Result

Hand-built in an interactive session on the operator's ruling of 2026-10-01 (fix it now). Verification:

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_session.py -q`
  — exit 0: 62 passed, 2 skipped.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — run by `pr-preflight` on push.
