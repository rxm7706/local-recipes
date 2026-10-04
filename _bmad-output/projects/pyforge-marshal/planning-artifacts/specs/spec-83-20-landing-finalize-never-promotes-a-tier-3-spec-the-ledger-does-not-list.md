---
title: "83.20: Landing finalize never promotes a Tier-3 spec the ledger does not list"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/rekey-2026-09-17.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-03 the landing finalize for atlas Story 27.1 (`python -m pyforge.marshal.dispatch_land_finalize pyforge-atlas 27.1 <worktree>`) made a local-main commit, cb80aeac52 "marshal: promote 3 story spec(s) to tracked artifacts". It added `spec-13-5-downstream-handoff-to-mason.md`, `spec-14-4-air-gap-asset-rewriting.md` and `spec-15-3-kedro-pipeline-surfacing.md` to atlas's tracked `planning-artifacts/specs/`. All three were Tier-3 leftovers in atlas's `implementation-artifacts/` from before the 2026-09-17 rekey. Their stories had already landed and been promoted under the new keys (`spec-12-5-downstream-handoff-to-mason-fr-68.md`, `spec-13-4-air-gap-asset-rewriting-cap-4.md`, `spec-14-3-kedro-pipeline-surfacing-cap-4.md`, ledger rows `done`). Two copies were byte-identical to their tracked twins, and the third was older than its twin. None of the three keys has a row in atlas's sprint-status ledger. The commit was never pushed: the operator kept it on a local branch and moved the three files out of Tier-3 by hand. Promotion classifies a candidate by its `N.M` story number, so a renumbered story's stale Tier-3 copy reads as durable and unpromoted, and every later finalize for that station promotes it again.

**Approach:** Promotion refuses to promote a Tier-3 spec unless both hold:
- its full key (the filename after `spec-`) is a row in that station's tracked `sprint-status-ledger.yaml`;
- no tracked spec for the same story already exists under a different key, where "the same story" means the same title slug with the `N-M-` prefix removed.

A candidate that fails either check is reported as an orphan, as a WARN finding naming the file and the reason, and is never promoted. The finalize commit and `deploy promote` carry the same rule, because they share `_scan_promotions`. First reproduce the atlas case with the real scan, to find which landing evidence made the three keys read as merged, and record that root cause in the Review Triage Log.

Ledger key: `83-20-landing-finalize-never-promotes-a-tier-3-spec-the-ledger-does-not-list`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- The tracked-spec promotion path (Stories 4.2, 51.2, 79.1). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a Tier-3 spec whose full key has no row in the station's ledger, and whose story number reads as merged, When promotion runs (`deploy promote`, or the landing finalize) Then it is not promoted and a WARN finding names the file and "no ledger row"
- Given a Tier-3 spec whose title slug matches a tracked spec under a different key When promotion runs Then it is not promoted and a WARN finding names both files
- Given the atlas case reproduced in a real git fixture (the three pre-rekey Tier-3 specs, their rekeyed tracked twins and ledger rows, and the landing evidence that made them read as merged) When the finalize runs Then no promotion commit is made and three orphan findings are reported
- Given a Tier-3 spec whose key is a ledger row and that has no twin When its story has landed Then it is promoted exactly as before
- Given either rule removed When its new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:** Read the ledger and the tracked specs from the same root the scan reads; keep one implementation in `_scan_promotions` / `core.promotion`; keep the classification pure where it is pure today.

**Never:** Never delete or move a Tier-3 file. Never promote a spec the rules refuse. Never change promotion for a candidate that passes both rules.

</intent-contract>

## Binding

Parent: Story 79.1 (finalize carries the promotion to `origin/main`) and Story 4.2 (`_scan_promotions`).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 entry.
Ledger key: `83-20-landing-finalize-never-promotes-a-tier-3-spec-the-ledger-does-not-list`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 at the operator's request (the "Stop finalize promoting pre-rekey Tier-3 specs" task, taken up in session).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
