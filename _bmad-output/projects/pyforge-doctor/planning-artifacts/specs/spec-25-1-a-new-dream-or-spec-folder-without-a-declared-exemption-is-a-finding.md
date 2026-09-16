---
title: '25.1: A new Dream or Spec folder without a declared exemption is a finding'
type: 'feature'
created: '2026-09-16'
status: 'ready'
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
