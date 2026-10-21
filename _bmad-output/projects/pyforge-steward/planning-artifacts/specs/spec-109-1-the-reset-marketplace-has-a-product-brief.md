---
title: '109.1: The reset marketplace has a product brief'
type: 'docs'
created: '2026-10-21'
status: 'in-review'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag-exempt: docs-only
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/self-hosted-bmad-marketplace.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/design-thinking-2026-10-20.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/bmad-marketplace-dream-reset.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-10-20 session re-decided the marketplace, and the archived seed plus Epic 60 do not say so. A teammate-facing product needs a brief in the station's brief format before the skeleton is the only statement of what the product is.

**Approach:** Write `briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md` with the brief template's sections (Executive Summary, The Problem, The Solution, What Makes This Different, Who This Serves, Success Criteria, Scope, Vision) plus `assumptions[]` and `open_questions[]`. Link the session folder. Do not un-archive the seed Dream.

## Acceptance criteria

1. The brief exists at the path above and contains each template section named in the approach.
2. It states the four jobs, the skill-folder install into `.agents/skills/` and `.claude/skills/`, the pilot audience (Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin (Cognition AI), and no AI tool yet), that Claude Code's documented skill path is `.claude/skills/` and Devin's is `.agents/skills/`, steward as owner, and Stories 109.4 and 109.5 as not built.
3. It records the session success signal (a teammate other than rxm7706 contributes a skill, and a different teammate installs and uses it), states that concepts A–F were all selected, and points at the verbatim session folder. It does not add a Dream under `docs/dreams/`.
4. The brief's memlog exists and was appended with `memlog.py`.

## Boundaries

- No code, no flag, no `SPEC.md` capability beyond the CAP-169 line this epic's chain commit adds.
- No new Dream file.

</intent-contract>

## Verification

**Commands:**

- `test -f _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md` — expected: exit 0.
- `test -f _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/.memlog.md` — expected: exit 0.

**Manual checks:**

- Read the brief against `design-thinking-2026-10-20.md`. The success signal and the selected concepts match that record.
