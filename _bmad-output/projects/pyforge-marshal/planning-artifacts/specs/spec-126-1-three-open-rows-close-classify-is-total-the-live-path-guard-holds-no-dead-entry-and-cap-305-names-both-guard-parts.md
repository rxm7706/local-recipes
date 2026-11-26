---
title: '126.1: Three open rows close: classify is total, the live-path guard holds no dead entry, and CAP-305 names both guard parts'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 126-1-three-open-rows-close-classify-is-total-the-live-path-guard-holds-no-dead-entry-and-cap-305-names-both-guard-parts
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py'
  - 'src/shared/packages/pyforge-marshal/tests/meta/test_spec_names_live_paths.py'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `classify` raised `ValueError` for `MRS-CHAIN-005`, `MRS-PREFLIGHT-016` and `MRS-REFRESH-008`, though each is emitted; two `ALLOW` entries of the live-path guard excuse files Story 116.4 wrote; CAP-305's guard clause names the audit hook but not the off-tree start that arms it.

**Approach:** Add `_CLASSIFY_TABLE` members matching each code's emitted severity (`MRS-CHAIN-005` error; the other two warn) and a test that `classify` is total over `REGISTERED_CODES`, proven to fail by code with a row removed; set the contract's three verdict cells; drop the two entries; amend CAP-305 by a memlog decision and a render.

Ledger key: `126-1-three-open-rows-close-classify-is-total-the-live-path-guard-holds-no-dead-entry-and-cap-305-names-both-guard-parts`.

### Living CAP citations

- spec-pyforge-marshal CAP-13 (no text change).
- spec-pyforge-marshal CAP-305 (guard clause amended 2026-11-26).
- pyforge-marshal:AD-31 (no text change).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Match each member to the severity the code emits.

**Never:**
- Never change a finding's severity.

## Acceptance Criteria

**Given** three codes raise in `classify`
**When** they get members and a totality test
**Then** `classify` answers every registered code
**And** the guard passes with the two entries gone

- **AC1 — Marshal's verdict tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py -q
  ```

- **AC2 — Marshal's contract and live-path guard pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py src/shared/packages/pyforge-marshal/tests/meta/test_spec_names_live_paths.py -q -m "live_tree or not live_tree"
  ```

</intent-contract>

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only (the skill files excluded, being regenerated). It found nothing blocking; it confirmed each new member matches its emitted severity (`MRS-CHAIN-005` ERROR at `cli/planning.py`, `MRS-REFRESH-008` and `MRS-PREFLIGHT-016` WARN) and named the behaviour this fixes: `compute_verdict` raised for these codes, so `marshal init` with a stale Tier-3 feed and a planning chain blocked mid-run crashed instead of projecting an exit code. The contract cells and the three closed rows agree with the code.
