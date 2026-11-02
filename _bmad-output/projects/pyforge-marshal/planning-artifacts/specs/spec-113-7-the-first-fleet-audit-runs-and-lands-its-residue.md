---
title: "113.7: the first fleet audit runs and lands its residue"
type: 'docs'
created: '2026-11-01'
status: 'done'
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
- **Amended 2026-11-01 (scope, operator ruling).** The landing PR also carries the fix stories the audit produced, implemented in this PR: marshal 113.8–113.13, atlas 34.14, 34.15 (minted 2026-11-01 from 34.14's network-refused AC, session-owner ruling) and 35.5, doctor 45.4, 48.3 and 50.2, herald 42.4, mason 4.5 and 19.6, scribe 19.4, 22.2, 23.2 and 25.2, steward 118.6 and 29.4, warden 13.2, 14.4, 15.2 and 16.6–16.10; parked at backlog: marshal 113.14, mason 25.17 and 25.18, steward 118.7 and 118.8. Each fix story moves by its own implementation and independent review, never by 113.7; a fix story that fails its review twice drops to `backlog` and the PR proceeds.

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
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`. Amended 2026-11-01: the residue files `_bmad-output/projects/pyforge-<station>/planning-artifacts/research/egm-audit-2026-11-01.md` × 8, each station Spec's `.memlog.md`, `docs/dreams/pyforge-marshal.md` § Realization log, and the fix stories this PR carries: marshal 113.8–113.13, atlas 34.14, 34.15 (minted 2026-11-01 from 34.14's network-refused AC, session-owner ruling) and 35.5, doctor 45.4, 48.3 and 50.2, herald 42.4, mason 4.5 and 19.6, scribe 19.4, 22.2, 23.2 and 25.2, steward 118.6 and 29.4, warden 13.2, 14.4, 15.2 and 16.6–16.10; parked at backlog: marshal 113.14, mason 25.17 and 25.18, steward 118.7 and 118.8.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0.

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check` and `dream-chain-check` — expected: exit 0.

## Auto Run Result

Status: done (built by hand in the landing PR at the operator's direction, 2026-11-01; independent review passed on its second pass, see Review Triage Log)

Summary:
- AC1: the audit ran by hand on 2026-11-01 (Tier-3 reports under `implementation-artifacts/egm/audit-2026-11-01/`); the operator ruled that run counts. Every finding was re-verified against `main` at `03a7aff5d9` and adversarially checked; triage file `triage-2026-11-01.md`.
- AC2: eight `research/egm-audit-2026-11-01.md` files, one per station, with every finding, its decision and reason, and headline counts per stage; marshal's carries the rules stage and the fleet totals (269 findings: 226 accepted, 41 rejected, 2 deferred).
- AC3: one memlog event per accepted finding on its owning Spec (226), the operator's decisions on the Specs they bind, and all eight station Specs re-derived from memlog capability entries (script-rendered, both self-validate passes logged); six pointer glossaries added.
- AC4: `docs/dreams/pyforge-marshal.md` § Realization log names the run, its counts and the fix stories; each station Dream names its own.
- AC5: the planning detectors and `detectors-ci` exit 0 on the branch; no status moved from the audit alone — every status move belongs to a fix story with its own independent review.
- Carried in the same PR (operator ruling 2026-11-01): fix stories marshal 113.8–113.13, atlas 34.14, 34.15 and 35.5, doctor 45.4, 48.3 and 50.2, herald 42.4, mason 4.5 and 19.6, scribe 19.4, 22.2, 23.2 and 25.2, steward 29.4 and 118.6, warden 13.2, 14.4, 15.2 and 16.6–16.10, all done; parked at backlog: marshal 113.14, mason 25.17 and 25.18, steward 118.7 and 118.8.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger); the operator's audit condition and session default 5 (one research file per station) bind here.
- 2026-11-01: amended, status unchanged (EGM audit MAR-D-R2; operator rulings 2026-11-01): `declared_low_risk` set to false; Approach gains the hand-run bullet (the 2026-11-01 hand run counts as AC1, reports under `implementation-artifacts/egm/audit-2026-11-01/`, triage in `triage-2026-11-01.md`, first automated `--audit` after Story 113.14) and the scope bullet (the landing PR carries the fix stories the audit produced; five parked at backlog); AC1, AC2 (`research/egm-audit-2026-11-01.md`, rules stage and fleet totals in marshal's file) and AC3 (226 accepted, 41 rejected, 2 deferred; events and decisions already on the memlogs) carry dated amendments; the Binding Surface lists the residue files and the fix-story keys; `epics.md` Story 113.7's Surface and Given carry the same dated notes.
- 2026-11-01 (review 1 failure fixed): the Approach scope bullet, the Binding Surface and `epics.md` Story 113.7's Surface line name atlas Story 34.15 beside 34.14 and 35.5 (minted the same day from 34.14's network-refused AC by session-owner ruling, done after two independent reviews); the marshal Dream's Realization line counts 23 fix stories on the other stations, not 22.

## Review Triage Log

- 2026-11-01 (independent reviewer; did not write this work; judged HEAD `5c8bfc3877` of `egm-audit-2026-11`, clean
  tree, against this spec's ACs as amended 2026-11-01, its Boundaries and its Change Log): **fail**, one failure (a
  record-accuracy fix, below); every AC check otherwise passes. Status left at `backlog` for the session owner.
  - **AC1 — pass.** The nine Tier-3 files (eight station reports and the fleet summary) and `triage-2026-11-01.md` exist
    under `implementation-artifacts/egm/audit-2026-11-01/`; the amended AC1 and the Approach record the hand run as
    ruled; marshal's memlog carries the operator's decision that the hand run counts as AC1.
  - **AC2 — pass.** All eight `research/egm-audit-2026-11-01.md` files exist and are tracked. Finding ids per station
    match the Tier-3 report ids exactly (atlas, doctor, herald, mason, steward, warden 30 each; scribe 31; marshal 34,
    the four `MAR-E` method rows included); marshal's file adds the 24 rules rows (matching the fleet summary's 24
    `RUL-*` ids) and the fleet totals (269: 226 / 41 / 2). Every row's decision equals `final_rows.json`; each file's
    Result line and per-stage Headline counts equal the counts computed from `final_rows.json`. Spot check of 10 rows
    (SCR-M-Z2, MAR-M-C2, MAS-D-C5, WAR-D-C1, MAR-D-R5, SCR-M-C4, ATL-D-C4, DOC-D-R1, ATL-M-D5, MAR-M-D3): decision,
    severity, status on main, reason, fix and carrier all match. Of all 269 rows only 14 reasons differ in text, each
    only by a cross-Spec CAP qualification (`spec-x:CAP-n`) or an appended cluster/gap-check note.
  - **AC3 — pass.** 226 `EGM audit 2026-11-01 finding <ID> accepted` events, one per accepted id, no duplicates, none
    on a rejected or deferred id: scribe 38, marshal 35, warden 28, mason 26, steward 26, atlas 24, doctor 24, herald 21,
    `spec-one-chain-per-station` 4 — each equal to `final_rows.json`'s accepted count for that Spec. RUL-C3's co-record
    is on `spec-pyforge-unifying-strategy`. The operator's triage decisions are on marshal's memlog (accept 226 / reject
    41 / defer 2; single PR; hand run is AC1; rules residue in marshal's file; resolve; catalog; audit scope) and each
    station's own rulings on its memlog. Every memlog change is append-only against `origin/main` (one `updated:` key
    each). All eight station `SPEC.md` files differ from `origin/main`; every changed CAP block has a 2026-11-01
    capability entry (or herald's `capability by claude` entries) behind it, each Spec has its two 2026-11-01
    Self-validate events, frontmatter `status` and every CAP `(ready <date>)` marker are unchanged. Every
    `spec-rederive` fix in the triage sits on one of these eight Specs; `spec-one-chain-per-station`'s four are `doc`
    fixes (CHAIN-STANDARD.md, surface-reconciled), so no other Spec needed a re-derive.
  - **AC4 — pass on the AC's terms.** The 2026-11-01 entry's `### Realization log` in `docs/dreams/pyforge-marshal.md`
    has *2026-11-01 (the audit lands)*: the run date, 269 findings (42 / 205 / 22 as audited, 1 Blocker after
    verification, matching `final_rows.json`) and 226 / 41 / 2. Its fix-story count is wrong: see the failure.
  - **AC5 — pass.** Exit codes, read from `$?`: `chain-currency-sweep-check` 0, `chain-completeness-check` 0,
    `dream-chain-check` 0, `spec-surface-check` 0, `story-status-check` 0, `ledger-regression-check` 0,
    `deferred-work-check` 0, `ad-citation-check` 0, `governance-currency` 0, `detectors-ci` 0 (49 of 49 pass, re-run on
    the clean HEAD). No status moved from the audit alone: every ledger change is a new fix-story key (29 at `done`,
    5 at `backlog`) or mason `epic-25` reopening for its two backlog stories (doctor 41.5's sanctioned roll-up); every
    pre-existing story spec keeps its status (their edits are append-only notes, plus 118.3's dated Deps amendment);
    every new `done` story spec has an independent review whose last verdict is pass (113.8–113.13, 48.3, 50.2, 19.4,
    23.2 and 118.6 failed once and passed a second review; none failed twice).
  - **Boundaries — pass.** No hand edit of a `SPEC.md` is visible: each diff is backed by memlog entries and the
    Self-validate events record the script render (the operator-approved route). Ledgers: each station's Tier-3 feed
    equals its tracked ledger on every story key (the only differences are three epic roll-up rows unchanged from
    `main`), so the ledgers moved by feed and `sprint-ledger-sync`. No `egm-bootstrap` run: no README or other
    bootstrap output among the branch's added files, and no mention in the diff.
  - **Failure 1 (record accuracy; fix before promotion).** The PR lands atlas Story 34.15 (`done`, minted 2026-11-01
    by the session owner from 34.14's AC3, independently reviewed twice, pass), but this spec's amended Approach scope
    bullet, its Binding Surface and `epics.md` Story 113.7's Surface list only atlas 34.14 and 35.5. The marshal Dream
    line says "22 fix stories on the other stations" where 23 land (atlas 3, doctor 3, herald 1, mason 2, scribe 4,
    steward 2, warden 8). The atlas Dream (line 795) already names 34.15. Fix: a dated amendment adding 34.15, with its
    minting basis, to the three lists, and correct the Dream count to 23.
  - Nits (not failures): 12 reasons across seven research files read "gap check: gap check: …" (a doubled prefix
    inherited from the triage notes), and a few end "… contested; settled in cluster" with no separator. Auto Run Result
    still reads "not yet dispatched"; update it when promoting. Seen while checking, not this story's:
    `docs-currency` warns that `docs/reference/station-cheat-sheet.md` is stale (`scripts/docs_station_cli.py --check`
    exit 1). The only content drift is steward's `nic:` help line, from `8ecec302e8` (2026-10-31) on `main`.
- 2026-11-01 (independent reviewer, second review; judged the working tree on HEAD `5c8bfc3877`, fixes uncommitted):
  **pass**, no failures. Status left at `backlog` for the session owner.
  - **Failure 1 — fixed.** The Approach scope bullet (line 28), the Binding Surface (line 66) and `epics.md` Story
    113.7's Surface line (11107) each name "atlas 34.14, 34.15 (minted 2026-11-01 from 34.14's network-refused AC,
    session-owner ruling) and 35.5". A dated Spec Change Log line records the fix. The marshal Dream's Realization line
    reads "23 fix stories on the other stations", which matches the 23 non-marshal `done` fix keys in the ledgers. Only
    those lines changed in the three files, apart from this log.
  - **Nits — fixed.** The research files no longer carry "gap check: gap check:". A word diff shows exactly 12 rows,
    each losing one duplicated "gap check:" and nothing else. Re-running review 1's AC2 checks gives the same result:
    ids, decisions and per-stage headline counts all match `final_rows.json`. `docs/reference/station-cheat-sheet.md` is
    regenerated, and its only content change is steward's `nic:` help line. `docs/map.yaml` changes only that page's
    `derived_at` / `tree` stamp. `scripts/docs_station_cli.py --check` exits 0. The "contested; settled in cluster"
    run-on and the stale Auto Run Result remain as review 1 noted (not failures).
  - Exit codes, read from `$?` (`pixi run --frozen -e pyforge-guild …`): `chain-completeness-check` 0,
    `dream-chain-check` 0, `dreams-hygiene-check` 0, `story-status-check` 0, `spec-surface-check` 0,
    `ad-citation-check` 0.
