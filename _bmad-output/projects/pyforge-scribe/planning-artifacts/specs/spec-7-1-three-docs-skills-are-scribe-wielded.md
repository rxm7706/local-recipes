<!-- RECOVERED 2026-09-18 Tier 3 (epics.md-derived Intent + ACs). No session
     transcript or bmad-loop worktree snapshot survived as a tracked story spec
     — regenerated from epics.md per CLAUDE.md's recovery priority order. -->
---
title: "Story 7-1: Three docs skills are scribe-wielded"
type: "docs"
created: "2026-09-07"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

## Intent

Three BMAD utility-skills for documentation structure, stale-reference sweeps,
and translated-prose review are wielded by scribe — routing lives on the
persona skill; the adoption register names scribe as sole wielder; CLAUDE.md
is not edited.

## Acceptance Criteria

- **Given** the three skills installed, **When** the scribe persona routes doc
  structure to `bmad-os-diataxis`, stale-reference sweeps to
  `bmad-os-audit-file-refs`, and translated prose review to
  `bmad-os-editorial-review-translation`, **Then** one `audit-file-refs` pass
  runs against `docs/reference/` and its findings land as a scribe capture, the
  register names scribe as sole wielder for all three, and CLAUDE.md is
  untouched.

## Delivery Record

Merged via PR #1079 (`bmad(all 8 stations): adoption/readiness batch -- 32
stories, Epic 44 cutover unblocked`), merge commit `1965e4189b`,
2026-09-07T20:33:05Z.
https://github.com/rxm7706/local-recipes/pull/1079

Implementation commit: `2df4fa7d46` (`scribe: Story 7.1 -- audit-file-refs pass
over docs/reference/, capture landed`). Routing lines on
`.claude/skills/bmad-agent-scribe/SKILL.md` and the
`adoption-register.md` § 2 row were already present from steward Story 46.2;
this story verified them and landed the remaining execution proof. Capture:
`.claude/memory/reference/pyforge-scribe-story-7-1-cap-3-bmad-os-audit-file-refs-adapt.md`
(13 files audited; 7 stale-reference violations across 5 files; 8 files clean).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass
  (this station's own verify suite; backfilled generically, no per-story claim).
