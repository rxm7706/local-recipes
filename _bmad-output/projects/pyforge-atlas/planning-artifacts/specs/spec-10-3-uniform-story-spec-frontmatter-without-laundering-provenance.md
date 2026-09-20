---
title: "Story 10-3: Uniform story-spec frontmatter + recovery documentation"
type: "feature"
created: "2026-07-27"
status: done
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-04"
---

<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Promote to full spec after initial stories land. -->

## Intent
Standardize frontmatter across all recovered/promoted specs (origin source, recovery tier, date); update CLAUDE.md example.

## Acceptance Criteria

- All story specs carry consistent YAML frontmatter (title, type, created, status, recovery source)
- CLAUDE.md 'story-specs-are-durable' section documents all 3 tiers + provenance comment format
- Warden exemplar is current and documented

## Notes
This spec was recovered from epics.md after Epic 10 was added (2026-07-27) post-atlas's initial 2026-07-25 reconciliation. Promote to full narrative spec + ACs matrix once implementation begins.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `10-3-uniform-story-spec-frontmatter-without-laundering-provenance: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `10-3-uniform-story-spec-frontmatter-without-laundering-provenance: done`).
- `## Auto Run Result` reconstructed from git (none survived).
