---
title: '117.39: The image builds delete the runner''s toolchains only when the disk is short'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-39-the-image-builds-delete-the-runner-s-toolchains-only-when-the-disk-is-short
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - '.github/workflows/platform-ci.yml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** the guild image build (`guild-container`, on a push to `main`) and the platform image build (Platform CI's `container`) each start by deleting the runner's preinstalled toolchains. They were written for runners with about 14 GB free, where deleting left about 39 to 45 GB. On 2026-11-27 the runner had 87 GB free before the step, which deleted 31 GB more in 136 to 163 s.

**Approach:** read the free space first (`df --output=avail -BG /`) and delete only when less than 50 GB is free. 50 GB is more than the step ever left on the short runners, so a build never has less room than before.

Ledger key: `117-39-the-image-builds-delete-the-runner-s-toolchains-only-when-the-disk-is-short`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change); works with CAP-131 (the image proves itself at build time).
- No AD moves.

## Boundaries & Constraints

**Always:**
- A runner with less than 50 GB free deletes exactly what it deleted before.

**Never:**
- Never drop the step or change what it deletes.

## Acceptance Criteria

**Given** a runner with 50 GB or more free
**When** an image build runs
**Then** the step deletes nothing and the build passes
**And** a runner with less deletes as before

- **AC1 — A dispatched run.** Expected: both `guild-container` jobs pass, and the disk step prints that nothing was deleted.

</intent-contract>
