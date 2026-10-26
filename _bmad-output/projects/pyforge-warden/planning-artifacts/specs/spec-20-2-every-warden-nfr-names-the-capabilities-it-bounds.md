---
title: "20.2: Every warden NFR names the capabilities it bounds"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/governance/fr-baseline.json
---

<intent-contract>

## Intent

**Problem:** CHAIN-STANDARD § 6 says every NFR cites a CAP; none of the 23 lettered NFR lines does, so they are baselined as the pre-rule arrowless population (ruling (c) of 2026-10-26).

**Approach:**
- Trace each NFR against the Spec's capability successes and write `← CAP-m` on its defining line; record the table in the station memlog before editing the PRD.
- Prune the baseline so the station's `projects` entry empties. Minted `backlog` by ruling (c); built in its own chain PR.
- Re-spell the eight ids outside CHAIN-STANDARD § 6's grammar in place, on the operator's ruling of 2026-10-26 (option A of the ruling sheet; the Spec memlog's decision entry of that date): `NFR-R3a` / `NFR-R3b` → `NFR-R3.1` / `NFR-R3.2`, `NFR-P-warm` / `NFR-P-cold` / `NFR-P-concurrency` → `NFR-P2` / `NFR-P3` / `NFR-P4`, `FR33` / `FR35` → `FR-33` / `FR-35`; the `FR30` traceability note names `FR-30` after its title and the six `FR-NEW-*` journey rows name their canonical FRs (the PRD's own 2026-07-12 crosswalk); the station's `findings` rows and `owners` entry leave the baseline with the `projects` rows.

Ledger key: `20-2-every-warden-nfr-names-the-capabilities-it-bounds`.
Type / Effort / Deps: chore / S / 20.1.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (amended): an NFR cites the CAP(s) it bounds.

## Acceptance Criteria

- **AC1 — 23 arrows.** Every NFR line carries `← CAP-m`; a diff against the pre-story PRD shows exactly 23 changed NFR lines.
- **AC2 — Defined cites.** Each cited CAP is a definition line in `spec-pyforge-warden/SPEC.md`; `fr-cap-unresolved` reports nothing for warden.
- **AC3 — The baseline.** `docs/governance/fr-baseline.json` `projects.pyforge-warden` carries no NFR id after `--prune`.
- **AC4 — The spellings (ruling of 2026-10-26).** No requirement id of this PRD is outside the grammar `N?FR-[A-Z]?\d+(\.\d+)*`: `findings.pyforge-warden` is empty after `--prune` and the station's `owners` entry is removed; the new spellings are carried by the PRD's live text, the spine's live text, `epics.md`'s live text and the 27 code comment, docstring and help-string lines of `src/shared/packages/pyforge-warden/`; dated records, memlogs, the Dream log and CHAIN-STANDARD's quoted examples keep the old spellings; the PRD's currency section carries the old → new table.

## Boundaries & Constraints

**Always:**
- Trace from the CAP's success text; keep the ids as spelled, except the eight the operator's ruling of 2026-10-26 re-spells (AC4), whose three P-family titles keep the word their old ids carried.

**Never:**
- Never count arrows; never change an NFR's text; never hand-edit `SPEC.md`.

## I/O & Edge-Case Matrix

| Line | Before | After |
|---|---|---|
| the 23 lettered NFR lines | no arrow (baselined) | `← CAP-m` traced |
| baseline `projects.pyforge-warden` | 30 ids (23 NFR lines, the `FR30` note, six `FR-NEW-*` rows) | pruned |
| baseline `findings.pyforge-warden`, `owners.pyforge-warden` | 14 structural findings; one owner row | pruned; removed |
| `NFR-R3a`, `NFR-R3b`, `NFR-P-warm`, `NFR-P-cold`, `NFR-P-concurrency`, `FR33`, `FR35` | outside the grammar | `NFR-R3.1`, `NFR-R3.2`, `NFR-P2`, `NFR-P3`, `NFR-P4`, `FR-33`, `FR-35`, in place |
| the `FR30` traceability note; the six `FR-NEW-*` journey rows | definition-shaped, unhyphenated / malformed | references to `FR-30` and to `FR-15`, `FR-22`, `FR-23`, `FR-26`, `FR-20`, `FR-21` |

</intent-contract>

## Binding

- Parent capability: `spec-one-chain-per-station` CAP-5 (amended 2026-10-26).
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 20, minted with Story 20.1.
- Ledger key: `20-2-every-warden-nfr-names-the-capabilities-it-bounds`.
- Deps: 20.1.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK (AC2).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run -e pyforge-guild python scripts/fr_baseline.py --prune` — expected: `pruned 0 entries` on the tip (AC3, AC4).
- `pixi run -e pyforge-warden pyforge-warden-test` — expected: green (the 27 code lines are comments, docstrings and help strings).

## Auto Run Result

Status: done (built 2026-10-26 in its own PR on the operator's ruling of the same date; minted 2026-10-26 `backlog` by operator ruling (c): the NFR backfill is its own story per station). `fr-without-cap` on the tip: zero FAIL, warden absent from the baseline; the advisory `fr-arrow-no-title-overlap` names ten of the 23 NFRs (`NFR-R2`, `NFR-R3.1`, `NFR-S4`, `NFR-S5`, `NFR-S7`, `NFR-S8`, `NFR-P4`, `NFR-I2`, `NFR-I3`, `NFR-U1`): their parenthetical titles share no word with the capability text; each arrow was read against the success text quoted in the memlog's trace table and stands.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).
- 2026-10-26 (build): AC4, the re-spell row of the I/O matrix and the two Verification commands added on the operator's ruling of 2026-10-26 (option A); the Always line amended for the eight re-spelled ids. The doctor Epic 50 retro's open question (re-spell in place, or sanction a suffix family) is closed by that ruling.

## Review Triage Log

- 2026-10-26, the ruling this story needed (doctor Epic 50 retro, open item): the ruling sheet read the story spec, the PRD's 44 baseline rows and every citation of the 14 ids across `_bmad-output/projects/pyforge-warden/`, `src/shared/packages/pyforge-warden/`, `docs/` and `.claude/`, and found nothing pinned in code or tests (27 code lines, all comments, docstrings or argparse help text; no test asserts on them; no generated page captures `--help`), that `FR-NEW-A..F` are the journeys' working labels already crosswalked to FR15/FR22/FR23/FR26/FR20/FR21 on 2026-07-12, and that the `FR30` row is the traceability note, not the `FR-30` definition. Two options: (A) re-spell in place; (B) widen CHAIN-STANDARD § 6 and the detector to a suffix family (a doctor story and a Guild-chain amendment, still leaving `FR30`/`FR33`/`FR35` and the `FR-NEW` rows to re-spell). Operator: *"A: re-spell in place to the grammar as the sheet proposes (NFR-R3.1/R3.2, NFR-P2/P3/P4, FR-33/FR-35, FR-30 after the title, FR-NEW rows name their canonical FR); rewrite the PRD, spine, epics.md and the 27 code lines; leave dated records, memlogs, Dream log and CHAIN-STANDARD examples."* Applied as AC4. One deviation from "leave dated records", recorded here and in the PRD section: the 2026-10-25 reconciliation record's bullet `- FR33 (the license gate flags) and FR35 …` was the only remaining definition-shaped `FR33` once the § I definition read `FR-33`, so the detector read it as a new unhyphenated id; the bullet gains the lead words "The bullets" so it reads as the reference it is, its words otherwise untouched.
