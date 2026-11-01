---
title: "113.7: the first fleet audit runs and lands its residue"
type: 'docs'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
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
- **Amended 2026-11-01 (the run).** The audit ran by hand on 2026-11-01, before the verb existed in a form that could review whole files; its Tier-3 reports are under `_bmad-output/projects/pyforge-marshal/implementation-artifacts/egm/audit-2026-11-01/`, with the triage in `triage-2026-11-01.md`. The operator ruled (2026-11-01) that this hand run counts as AC1, not journaled through the verb; the first automated `marshal factory challenge --audit` runs after Story 113.14 (EGM audit MAR-D-R2).
- **Amended 2026-11-01 (scope, operator ruling).** The landing PR also carries the fix stories the audit produced, implemented in this PR: marshal 113.8–113.13, atlas 34.14 and 35.5, doctor 45.4, 48.3 and 50.2, herald 42.4, mason 4.5 and 19.6, scribe 19.4, 22.2, 23.2 and 25.2, steward 118.6 and 29.4, warden 13.2, 14.4, 15.2 and 16.6–16.10; parked at backlog: marshal 113.14, mason 25.17 and 25.18, steward 118.7 and 118.8. Each fix story moves by its own implementation and independent review, never by 113.7; a fix story that fails its review twice drops to `backlog` and the PR proceeds.

Ledger key: `113-7-the-first-fleet-audit-runs-and-lands-its-residue`.
Type / Effort / Deps: docs / M / 113.5.

### Living CAP citations

- **CAP-302** — the sweep whose residue this story lands.
- **CAP-303** — the bridge the accepted findings travel (Story 113.6), when on.

## Acceptance Criteria

- **AC1 — The run.** One `--audit` sweep over the eight stations and the rules targets, journaled; the Tier-3 reports exist. (Amended 2026-11-01: met by the hand run of 2026-11-01, which the operator ruled counts as AC1 without a verb journal; its reports are under `_bmad-output/projects/pyforge-marshal/implementation-artifacts/egm/audit-2026-11-01/`, the triage in `triage-2026-11-01.md`; the first automated `--audit` runs after Story 113.14.)
- **AC2 — The residue.** Eight `research/egm-audit-2026-11.md` files, one per station, each with every finding, its accept/reject and reason, and the headline counts. (Amended 2026-11-01: the file name is `research/egm-audit-2026-11-01.md`, a full date per AGENTS.md § Dates; the rules stage and the fleet totals live in marshal's file.)
- **AC3 — The memlogs.** One memlog event per accepted finding on its owning Spec, through `memlog.py`; a re-derive where the contract changed. (Amended 2026-11-01: 226 findings accepted, 41 rejected, 2 deferred; the events and the operator's decisions are already on the owning memlogs; the re-derives ride the fix stories that change each contract.)
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
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`. Amended 2026-11-01: the residue files `_bmad-output/projects/pyforge-<station>/planning-artifacts/research/egm-audit-2026-11-01.md` × 8, each station Spec's `.memlog.md`, `docs/dreams/pyforge-marshal.md` § Realization log, and the fix stories this PR carries: marshal 113.8–113.13, atlas 34.14 and 35.5, doctor 45.4, 48.3 and 50.2, herald 42.4, mason 4.5 and 19.6, scribe 19.4, 22.2, 23.2 and 25.2, steward 118.6 and 29.4, warden 13.2, 14.4, 15.2 and 16.6–16.10; parked at backlog: marshal 113.14, mason 25.17 and 25.18, steward 118.7 and 118.8.
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
- 2026-11-01: amended, status unchanged (EGM audit MAR-D-R2; operator rulings 2026-11-01): `declared_low_risk` set to false; Approach gains the hand-run bullet (the 2026-11-01 hand run counts as AC1, reports under `implementation-artifacts/egm/audit-2026-11-01/`, triage in `triage-2026-11-01.md`, first automated `--audit` after Story 113.14) and the scope bullet (the landing PR carries the fix stories the audit produced; five parked at backlog); AC1, AC2 (`research/egm-audit-2026-11-01.md`, rules stage and fleet totals in marshal's file) and AC3 (226 accepted, 41 rejected, 2 deferred; events and decisions already on the memlogs) carry dated amendments; the Binding Surface lists the residue files and the fix-story keys; `epics.md` Story 113.7's Surface and Given carry the same dated notes.

## Review Triage Log

- (none yet)
