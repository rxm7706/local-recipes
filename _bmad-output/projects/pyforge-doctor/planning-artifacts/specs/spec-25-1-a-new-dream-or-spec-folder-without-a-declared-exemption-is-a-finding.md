---
title: '25.1: A new Dream or Spec folder without a declared exemption is a finding'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 171 Dreams and 172 Spec folders for eight stations; the 2026-08-08 61-Dream fold regrew in five weeks because nothing refuses a new file. Dream-append-first is asserted, not enforced.

**Approach:** A repo-scope detector lists every Dream file and Spec folder, subtracts a dated baseline snapshot (the ruling SHA e630e43330), and requires `fold-exemption:` from the closed list on every remainder. The list is read from one declared source (guild-roster.json `fold_exemptions`). Baseline writes only remove entries. Registered in detectors-ci.

## Boundaries & Constraints

**Always:**
- Station Dreams, station Specs and story-spec files are structurally excluded — they are the chain.
- A baseline entry is never a finding; an exempt remainder is an info finding (visible, never silent).
- The exemption list comes from guild-roster.json; a hard-coded list in chain.py fails a meta-test.
- Scoped --write-baseline only removes entries (folds), never adds.
- Conformance test: zero FAIL on the live tree at the merge SHA.

**Never:**
- Do not grade pre-existing folders (eventual consistency — folded and unfolded stations both pass).
- Do not mint the exemption vocabulary's shape here (that is the declared source's owner).
- Do not fail on a station fold that archives a Dream or absorbs a Spec.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new Dream, no exemption | docs/dreams/new.md, no frontmatter key | chain-sprawl-unexempted FAIL naming the eight station Dreams | fail |
| new Spec folder, listed value | specs/spec-x/SPEC.md fold-exemption: cross-station-seam | chain-sprawl-exempt info | none |
| new folder, unlisted value | fold-exemption: because | chain-sprawl-unexempted FAIL | fail |
| baseline entry | any pre-ruling path | no finding | none |
| story spec file | specs/spec-25-1-….md | excluded, no finding | none |

</intent-contract>

## Binding

Parent Spec capability: `spec-one-chain-per-station CAP-2 (CAP-1 vocabulary)`.
Standard: `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`.
Surface: doctor sources/chain.py (gather_chain_sprawl), sources/__init__.py, sources/__main__.py, pixi.toml chain-sprawl-check, scripts/detectors.py, docs/governance/guild-roster.json fold_exemptions, docs/governance/chain-sprawl-baseline.json, doctor unit + conformance tests.
Ledger key: `25-1-a-new-dream-or-spec-folder-without-a-declared-exemption-is-a-finding`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-25-1-a-new-dream-or-spec-folder-without-a-declared-exemption-is-a-finding.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `065f73c9b5` (2026-09-16, "doctor: promote 25.1+25.2+25.3 to done (landed in #1385)"); also `7e42b536aa` (2026-09-16, "land doctor 25.1+25.2+25.3 (3 stories): one-chain mechanism — sprawl gate, FR<-CAP check, "); also `9e1c4758f5` (2026-09-10, "Merge latest main into Story 25.1 before landing"). Ledger row `25-1-a-new-dream-or-spec-folder-without-a-declared-exemption-is-a-finding: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `25-1-a-new-dream-or-spec-folder-without-a-declared-exemption-is-a-finding: done`).
- `## Auto Run Result` reconstructed from git (none survived).
