---
title: '21.2: `AGENTS.md` says what runs `governance-currency`'
type: 'docs'
created: '2026-09-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Story 21.1 wrote into `AGENTS.md` Pre-PR checklist item 10 that neither `detectors-ci` nor `pr-preflight` runs `governance-currency`. Both do: `scripts/detectors.py --scope repo` discovers `scripts/governance_currency_check.py` (`DETECTOR = {"scope": "repo"}`) by its `*_check.py` glob.

**Approach:** Restore a true line naming the lanes that run it, and append a dated correction to 21.1's triage log.

## Boundaries & Constraints

**Always:**
- Prove the claim with `python scripts/detectors.py --scope repo --list`, never a name grep (glob discovery is invisible to one).
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec; re-run the check and read its exit code.

**Never:**
- Do not edit the managed `bmad:context` block.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| detector discovery | `detectors.py --scope repo --list` | lists `governance_currency_check` with task `governance-currency` | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-27`.
Dream: `docs/dreams/pyforge-scribe.md` § *2026-09-26 — The instruction surface loads once, and says what runs it*.
Ledger key: `21-2-agents-md-says-what-runs-governance-currency`.
Ledger status at mint: `backlog`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** 21.1 • **FR/AD:** spec-pyforge-scribe CAP-27
**Surface:** `AGENTS.md` (Pre-PR checklist item 10, outside the managed block); this story's sibling `spec-21-1-agents-md-opens-with-what-this-repository-is.md` (a dated correction appended to its triage log).
**Given** 21.1 wrote that neither `detectors-ci` nor `pr-preflight` runs `governance-currency`, while `scripts/detectors.py --scope repo` discovers `scripts/governance_currency_check.py` by its `*_check.py` glob
**When** this story lands
**Then** checklist item 10 says `detectors-ci` (and so `pr-preflight`) runs `governance-currency` as a repo-scope detector, and 21.1's triage log carries a dated correction; the claim is proven against `python scripts/detectors.py --scope repo --list`, not a name grep
**And** `pixi run -e pyforge-guild governance-currency` exits 0; `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green; co-governor reconcile: a memlog entry on every Spec `spec-surface-check` names, then a scoped stamp per Spec

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).
- `python scripts/detectors.py --scope repo --list` — expected: lists `governance_currency_check`.

**Manual checks:**
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.

## Outcome

Done 2026-09-26, in an interactive session.

- `AGENTS.md` Pre-PR checklist item 10 now says `governance-currency` is a repo-scope detector that `detectors-ci` and `pr-preflight` run, and that `pixi run -e pyforge-guild governance-currency` runs it alone.
- The claim was proven against the tree:
  - `python scripts/detectors.py --scope repo --list` lists `governance_currency_check task=governance-currency`;
  - `pixi.toml`'s `pr-preflight` depends on `detectors-ci`.
- 21.1's story spec carries a dated correction; scribe memlog entry 115 records it.
- `pixi run -e pyforge-guild governance-currency`: exit 0. `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`: 398 passed, 11 skipped.
