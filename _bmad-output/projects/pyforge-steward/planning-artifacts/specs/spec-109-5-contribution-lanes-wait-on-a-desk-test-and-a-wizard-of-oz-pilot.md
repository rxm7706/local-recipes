---
title: '109.5: Contribution lanes wait on a desk test and a Wizard-of-Oz pilot'
type: 'docs'
created: '2026-10-21'
status: 'ready-for-dev'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag-exempt: docs-only
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/catalog/marketplace/MANUAL-CHECKLIST.md
  - src/shared/packages/pyforge-steward/catalog/marketplace/.github/PULL_REQUEST_TEMPLATE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/decision-record.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two contribution lanes were decided (instructions-only and code-backed). Automating either lane before a person has run the desk test and the Wizard-of-Oz pilot would publish a path that has not been tried. `DW-FU-60-1`, `DW-FU-60-1-4`, and `DW-FRR-60-1` are still open and are not this story's closures.

**Approach:** The manual checklist and the PR template are the pilot's tools (landed with Story 109.3). This story records one Round 0 result and one Wizard-of-Oz result against that checklist, then either leaves both lanes manual or specs the smallest automation the notes justify. It does not close the three Epic 60 deferrals. `carried:` on those rows points here.

## Acceptance criteria

1. `MANUAL-CHECKLIST.md` Round 0 and Wizard-of-Oz sections each have a dated note of what a person did and what failed. The note lives with the checklist or in this story's spec, not only in chat.
2. Any automation that follows is a separate change inside this story's spec, and it refuses to upload (`twine`, `pixi upload`, feedstock, upstream PR).
3. Instructions-only remains a markdown-and-index pull request. Code-backed names the package the skill calls and whether `published` is false.
4. The three deferred rows named above are still `status: open` after this story.

## Boundaries

- Do not mark the deferred rows resolved.
- Do not create the internal GitHub repository.
- Do not treat a green unit test as the desk test.

</intent-contract>

## Verification

**Commands:**

- `test -f src/shared/packages/pyforge-steward/catalog/marketplace/MANUAL-CHECKLIST.md` — expected: exit 0. This only proves the checklist is present. The desk test itself is the manual check.

**Manual checks:**

- The Round 0 and Wizard-of-Oz notes exist and name a repository that is not local-recipes.
