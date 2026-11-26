---
title: '143.1: Steward''s source cites other spines'' decisions qualified'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 143-1-steward-s-source-cites-other-spines-decisions-qualified
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/apps.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/models.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/audit.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/migrations/0001_initial.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** steward's own spine defines `AD-1` to `AD-9`, and its source cites other spines' decisions bare: the jira spine's baseline and transport rules in `sync.py` (`jira:AD-10`, and `jira:AD-2` and `jira:AD-5`, numbers steward's own spine also defines), the platform-library spine's static-export, reusable-app and storage rules in `deploy.py`, `cli.py` and `dashboard/`, the canopy's interpreter rule, and marshal's loop-home and seam decisions.

**Approach:** Write each such tag with the prefix of the spine it means (`jira:`, `sld:`, `canopy:` and `pyforge-marshal:`). Each was judged from its context against the spines' own headings, not by number alone.

Ledger key: `143-1-steward-s-source-cites-other-spines-decisions-qualified`.

### Living CAP citations

- spec-one-chain-per-station:CAP-9 (the chain standard is one page, and that page holds the id grammar; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change behaviour, an exit code or a flag.
- Never qualify a tag that means this station's own spine.

## Acceptance Criteria

**Given** nine steward modules cite decisions of the jira, platform-library, canopy and marshal spines bare, two of them numbers steward's own spine also defines
**When** each is written with the prefix of the spine it means (`jira:`, `sld:`, `canopy:` and `pyforge-marshal:`)
**Then** `ad-citation-check` reports no undefined bare tag in steward's source
**And** steward's suites pass with no behaviour changed

- **AC1 — The detector is green on the tree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild ad-citation-check
  ```

- **AC2 — Steward's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```

</intent-contract>

## What the detector cannot see, and what was read instead

Steward's own spine defines the first nine numbers, so a bare tag in that range resolves whichever spine it means; `ad-citation-check` reports only a number the home spine lacks. The tags in that range were judged by reading: every bare tag in `dashboard/` is the platform-library spine's (that package realizes it); in `sync.py`, the first, third, fourth, ninth and, on the two authentication lines, eighth are the jira spine's; the shareability refusal in `deploy.py` and `cli.py` is the platform library's fifth; the studio root and the module roster in `suite.py` and `provision.py` are the suite spine's.

Left bare because the read did not settle them: `deploy.py` line 9 (the fifth decision's 2026-08-09 rule) and line 11 (the eighth, beside the shareability slice); `sync.py` lines 2036 and 2042 read as steward's own. `sprint_ledger_query.py` cites the canopy's thirteenth and twenty-third as the tracked story spec for Story 65.1 does; the review doubted that either heading fits the sentence, and it is unchanged from that spec.

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`. Its first finding was that the first sweep was partial: about ninety bare tags in steward's source still meant another spine and were invisible to the detector. The sweep was finished for the ones it named and the wording here, in the Dream and in the chain standard was narrowed to what the detector can hold.
