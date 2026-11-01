---
title: "113.7: the first fleet audit runs and lands its residue"
type: 'docs'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
---

<intent-contract>

## Intent

**Problem:** the operator wants to know where the fleet stands — which existing Specs do not cover their Dream entries, which stories do not cover their CAPs, which repo rules a fresh agent cannot act on — once, written down in the chain and not in a chat.

**Approach:**
- With Story 113.5 done and `pyforge.marshal.egm_audit` on in `dev`, run `marshal factory challenge --audit` once over the fleet (Tier-3 reports only).
- Triage every finding with the operator: accept or reject, with a reason. Accepted findings become memlog events on their owning Spec through Story 113.6's bridge (or `memlog.py` by hand when 113.6 is not yet on), each followed by its Spec's `bmad-spec` re-derive in the same change where the finding changes the contract.
- Write one `_bmad-output/projects/pyforge-<station>/planning-artifacts/research/egm-audit-2026-11.md` per station: the findings, the accept/reject per finding with the reason, and the headline counts (findings, accepted, rejected, per stage). Record the run's date and headline counts in the marshal Dream's Realization log.
- The research file and the memlog lines land in one PR so `chain-currency` reads them together; no `SPEC.md`, ledger or story spec `status` moves from the audit alone.

Ledger key: `113-7-the-first-fleet-audit-runs-and-lands-its-residue`.
Type / Effort / Deps: docs / M / 113.5.

### Living CAP citations

- **CAP-302** — the sweep whose residue this story lands.
- **CAP-303** — the bridge the accepted findings travel (Story 113.6), when on.

## Acceptance Criteria

- **AC1 — The run.** One `--audit` sweep over the eight stations and the rules targets, journaled; the Tier-3 reports exist.
- **AC2 — The residue.** Eight `research/egm-audit-2026-11.md` files, one per station, each with every finding, its accept/reject and reason, and the headline counts.
- **AC3 — The memlogs.** One memlog event per accepted finding on its owning Spec, through `memlog.py`; a re-derive where the contract changed.
- **AC4 — The Dream.** `docs/dreams/pyforge-marshal.md` § Realization log names the run's date and headline counts.
- **AC5 — Green.** `chain-currency-sweep-check`, `chain-completeness-check`, `dream-chain-check`, `spec-surface-check` and `detectors-ci` are green on the PR; no `SPEC.md`, ledger or story spec `status` moved from the audit alone.

## Boundaries & Constraints

**Always:**
- Land the research files and the memlog lines in one PR; re-derive a Spec whose contract a finding changes.

**Never:**
- Never hand-edit a `SPEC.md`; never write a ledger; never accept a finding without the operator's word; never run `egm-bootstrap`.

</intent-contract>

## Binding

- Parent capability: CAP-302.

Parent: CAP-302

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-7-the-first-fleet-audit-runs-and-lands-its-residue`.
- Deps: 113.5.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0.

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check` and `dream-chain-check` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger); the operator's audit condition and session default 5 (one research file per station) bind here.

## Review Triage Log

- (none yet)
