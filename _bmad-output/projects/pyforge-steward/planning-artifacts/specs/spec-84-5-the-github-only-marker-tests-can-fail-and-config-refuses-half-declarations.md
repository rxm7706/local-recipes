---
title: "84.5: The GitHub-only marker tests can fail, and config refuses half declarations"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py
  - src/shared/packages/pyforge-steward/tests/unit/test_sync_github_only_marker.py
  - .steward/sync-config.example.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 84.4 landed by operator ruling with its follow-ups chained here (its Review Triage Log, the 2026-10-03 night entry). The production test is false-green: its flag tree has no metadata, so the read fails instead of the overlay saying off. The requested `PYFORGE_ENVIRONMENT=prod` marker case is missing. The no-marker unknown-environment test does not prove the flag is never read (the reorder mutants survive). Config still accepts a `label` with a lone `field_id` or `field_value`, and `sync.py` keeps an unreachable `isinstance(label, str)` branch. DW-8-5-2's `verified:` line cites `sync.py:1301` and `:1373-1376` where the skip `raise` is at `:1299` and the skip path at `:1371-1374`. Stale review-pass entries in 84.4's spec say H1-H3 are `[false]`, `{}` loads as None, and the tests monkeypatch the gate.

**Approach:** Make each test able to fail, refuse the half declarations, and correct the record.

Ledger key: `84-5-the-github-only-marker-tests-can-fail-and-config-refuses-half-declarations`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-60 (Story 84.4's follow-ups, by operator ruling 2026-10-03). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the production flag tree with all five metadata fields When the production test runs Then the overlay reads off and no WARNING is logged; and a `PYFORGE_ENVIRONMENT=prod` case with a marked unlinked item is covered
- Given no marker and an unknown environment When a batch runs Then the flag is never read (a test that fails if the read moves before the marker check)
- Given `github_only_marker` with a `label` plus a lone `field_id` or a lone `field_value` When config loads Then it refuses naming the field; the unreachable `isinstance(label, str)` branch is gone
- Given the deferred-work ledger When DW-8-5-2 is read Then its `verified:` line cites the skip `raise` and the skip path at their live lines; and Story 84.4's spec gains an entry correcting its stale review-pass lines (appended, never edited)
- Given each new test When its fix is reverted Then it fails (mutation)

## Boundaries & Constraints

**Always:** Prove each test can fail with a mutant; keep the flag's behaviour unchanged.

**Never:** Never change the flag key, its defaults or its overlays.

</intent-contract>

## Binding

Parent: Story 84.4 (`spec-pyforge-steward` CAP-60).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-03 (night) entry.
Ledger key: `84-5-the-github-only-marker-tests-can-fail-and-config-refuses-half-declarations`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
