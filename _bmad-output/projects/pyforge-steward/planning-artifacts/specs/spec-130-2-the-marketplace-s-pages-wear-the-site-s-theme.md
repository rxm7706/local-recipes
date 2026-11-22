---
title: '130.2: The marketplace''s pages wear the site''s theme'
type: 'fix'
created: '2026-11-22'
status: 'ready-for-dev'
story: 130-2-the-marketplace-s-pages-wear-the-site-s-theme
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py'
  - 'docs/foundry/marketplace/site/**'
  - 'src/shared/packages/pyforge-steward/tests/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The marketplace's rendered pages are a serif light page whatever theme the reader chose, with no way back to the site, and print each listing as "skill · unverified · code-backed · never verified".

**Approach:** The renderer's stylesheet sets every colour and face as a site theme variable with a fallback, light and dark; each listing's kind, trust and verification print as short phrases an outside reader follows; the committed `docs/foundry/marketplace/site/` is re-rendered so it still byte-matches.

Ledger key: `130-2-the-marketplace-s-pages-wear-the-site-s-theme`.

### Living CAP citations

- spec-pyforge-steward CAP-171 (amended 2026-11-22); FR-44 ← CAP-171; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the pages readable opened alone from a file.
- Re-render the committed `site/` with the renderer, never by hand.

**Never:**
- Never copy the site's menu or header into the marketplace (herald Story 53.1 gives it at assembly).
- Never change a listing's data or the index schema.

## Acceptance Criteria

**Given** the marketplace's rendered pages are a serif light page whatever theme the reader chose, and print "skill · unverified · code-backed · never verified"
**When** `write_site` renders the tree
**Then** every colour a rendered page sets is a site theme variable with a fallback, in light and dark, each listing's kind, trust and verification read as words an outside reader follows, and the committed `site/` byte-matches the render
**And** steward's package half passes, with a test that fails by name on a colour outside the fallback block

- **AC1 — Steward's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-171 (amended 2026-11-22); FR-44 ← CAP-171; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-22 entry; operator, 2026-11-22: dark by default, one PR.
- Epic: Epic 130, minted with this story.
- Ledger key: `130-2-the-marketplace-s-pages-wear-the-site-s-theme` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."130"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.
