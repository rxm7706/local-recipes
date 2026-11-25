---
title: '61.1: The shelf, the front doors and the dossier say what the tree does'
type: 'fix'
created: '2026-11-24'
status: 'done'
story: 61-1-the-shelf-the-front-doors-and-the-dossier-say-what-the-tree-does
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # documentation and planning text; no code path to gate (roster list)
surface:
  - 'docs/tutorials/**'
  - 'docs/how-to/**'
  - 'docs/reference/**'
  - 'docs/explanation/**'
  - 'docs/_STYLE_GUIDE.md'
  - 'docs/dreams/README.md'
  - 'docs/governance/**'
  - 'docs/foundry/**'
  - 'docs-site/src/content/dossier/dossier.yml'
  - 'AGENTS.md'
  - 'CHANGELOG.md'
  - '.github/pull_request_template.md'
  - '.claude/memory/README.md'
  - '.claude/skills/bmad-agent-*/SKILL.md'
  - 'src/platform/**/README.md'
  - 'src/shared/packages/*/README.md'
  - 'src/shared/packages/pyforge-atlas/**/*.md'
  - 'src/shared/packages/pyforge-herald/web/README.md'
  - 'src/shared/packages/pyforge-marshal/tests/integration/README.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Every documentation detector and generator reads green at main `7da08791f3`, yet a read of each page against the tree found about 48 pages and files that state something the tree contradicts: commands that fail or do nothing as written, environments described as carrying what they do not, paths that are gone, and published measurements the tree no longer supports.

**Approach:** Re-verify each finding of the 2026-11-24 review against the tree, correct the page with the smallest edit that makes it true, and move its `verified:` date. Leave a page alone when the tree does not support the finding. Record the four governance Specs with stale text, and the code defects this change does not fix, as deferred-work rows on the owning stations' ledgers.

Ledger key: `61-1-the-shelf-the-front-doors-and-the-dossier-say-what-the-tree-does`.

### Living CAP citations

- spec-pyforge-doctor CAP-84 (realized, no text change); FR-17 ← CAP-84; no AD moves.

## Boundaries & Constraints

**Always:**
- Re-verify a finding against the tree before its page moves.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change a detector, a generator, station code or a CLI in this story.
- Never hand-edit a `SPEC.md`, a generated page or a `bmad:context` block.

## Acceptance Criteria

**Given** pages that give a command that fails or does nothing as written, describe an environment as carrying what it does not, cite a path that is gone, or publish a measurement the tree no longer supports, while every documentation detector reads green
**When** each finding of the 2026-11-24 review is re-verified against the tree and its page corrected, with the page's `verified:` date moved
**Then** the documentation detectors and the seven generators' `--check` exit 0, and the Pages site's `pages-check` exits 0 with the dossier's section numbers intact
**And** the four governance Specs with stale present-tense text, and every code defect the review found that this change does not fix, are open rows in the owning stations' deferred-work ledgers

- **AC1 — The documentation detectors read green.** Expected: exit 0 for each.

  ```bash
  pixi run -e pyforge-guild docs-currency-check
  pixi run -e pyforge-guild docs-map-hygiene-check
  pixi run -e pyforge-guild governance-currency
  pixi run -e pyforge-guild dreams-hygiene-check
  ```

- **AC2 — The site builds with the dossier intact.** Expected: exit 0.

  ```bash
  pixi run -e site pages-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (realized, no text change); FR-17 ← CAP-84; no AD moves.
- Dream: `docs/dreams/pyforge-doctor.md`, the 2026-11-24 entry (the documentation says what the tree does); operator rulings of 2026-11-24.
- Epic: Epic 61, minted with this story.
- Ledger key: `61-1-the-shelf-the-front-doors-and-the-dossier-say-what-the-tree-does`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."61"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-24: minted from the station Dream's 2026-11-24 entry and the operator's rulings of the same date; implemented the same day and left `in-review`: implementation and review do not share a session.
- 2026-11-24: closed. PR #2383 merged as b5019058e3 (`Merge pyforge-doctor/61-1 into main`) after its 43 CI checks passed and the full local `pr-preflight` exited 0; independent reviewers read the diff against this spec before the merge and their findings were applied.
