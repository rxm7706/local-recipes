---
doc_type: retrospective
project: pyforge-atlas
epic: 3
wave: B
title: Wave B — Pipeline Node Porting & MCP Integration
stories: 10
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #76/#81/#82/#83)
---

# Epic 3 · Wave B — Pipeline Node Porting & MCP Integration

**Scope:** the keystone wave — B1…B10. The 12 conda-side backbone phases plus the
PyPI/vulnerability pipelines (14 nodes) become Kedro nodes; the read surface is
re-exposed as Kedro-API-native MCP tools; the parity harness is hardened into a
fail-closed retirement gate.

## What worked

- **The independent fresh-eyes reviewer earned its keep here, repeatedly.** Given
  only the spec and the files — no prior context — it caught what the two in-loop
  reviewers missed, and the misses were not cosmetic:
  - **B5 (HIGH)** — an `AD-13` `UnicodeDecodeError` guard hole
  - **B7 (HIGH)** — `_REQ_RE` mishandling extras and URL garbage-versions
  - **B8 (MED)** — an `AD-13` never-fail gap in `_persist`
  - **B1** — a `downloads_source='merged'` contract violation
  - **B2** — `_serial_moved` coercion
  Two of the three keystone stories shipped a contract violation past two
  adversarial reviewers. **Context is what made the in-loop reviewers miss them.**
- **Fail-closed by construction (B4).** The retirement gate could not pass by
  silence — it had to be *shown* parity before the legacy path could retire.
- **Honest deferral over faking.** B4's credentialed legacy-DB compare was
  recorded as attended work, not stubbed green.

## What did not

- **The keystone stories were too large to review well.** B1 (12 phases) and B2
  (14 nodes + a cost gate + a scheduler) each shipped a defect that survived two
  reviews. Story size, not reviewer quality, is the likeliest cause.
- **`AD-13` (keep-last-good) was violated twice in the same wave**, in different
  stories, in different ways. One shared helper — or one contract test applied to
  every `AD-13` site — would have caught both.
- **The MCP serialization defect (B3, Gemini HIGH on #76) reached PR.** The
  read-surface boundary had no round-trip test.

## Carry-forward

1. **Split keystone stories.** If a story ports a dozen phases, review coverage
   degrades faster than implementation quality does.
2. **A repeated architectural decision needs one shared implementation and one
   contract test**, not per-site re-implementation. `AD-13` is the case in point.
3. **Keep the independent reviewer.** It is the single practice with the clearest
   evidence of return in this whole effort.
