---
title: 'The Tutorials/Getting-Started and How-to-Guides quadrants are populated'
type: 'feature'
created: '2026-09-11'
status: 'backlog'
baseline_revision: 'a7752e7f91015b81d79a979bfca61a0dc8c8c8bb'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Depends on Story 22.4's map. The Tutorials/Getting-Started and How-to-Guides
quadrants have no discoverable home today — their would-be content is scattered across
`README.md`'s "Common Commands" section, `docs/reference/developer-guide.md` (a mixed-content
file per Story 22.4's own classification), and skill-scoped guides
(`.claude/skills/conda-forge-expert/guides/`, `.claude/skills/conda-forge-expert/quickref/`). A
newcomer has no single place to get a working environment running, and no single place to find
task-oriented "how do I do X" instructions.

**Approach:** Relocate and consolidate existing accurate content into the two new quadrant
homes Story 22.4's map names — this is population, not authoring from scratch. Tutorials/
Getting-Started gets the "get a working environment running" material (currently the opening
of `README.md`'s "Common Commands," any onboarding steps in `docs/reference/developer-guide.md`).
How-to Guides gets task-oriented operational instructions (the bulk of "Common Commands," the
operational parts of `developer-guide.md`, and — where genuinely general-purpose rather than
skill-scoped — material currently only discoverable inside `.claude/skills/conda-forge-expert/`'s
own guides). Content that is genuinely skill-scoped (specific to one skill's own workflow, not
general onboarding/operations) stays where it is; this story does not empty out skill-internal
docs, only pulls the general-purpose material that belongs at the repo level.

## Boundaries & Constraints

**Always:**
- Follow Story 22.4's map for the two quadrants' physical paths — do not invent new paths this
  story didn't already name.
- Content is relocated and corrected in place (fixing anything factually wrong while moving
  it), not rewritten from scratch — the same surgical discipline as Stories 22.1/22.2.
- Distinguish genuinely general-purpose operational content (belongs in the new How-to Guides
  home) from skill-internal workflow docs (stays in `.claude/skills/<skill>/guides/` — this
  story does not relocate skill-scoped documentation).

**Never:**
- Do not leave `README.md`'s "Common Commands" section and the new quadrant homes both carrying
  the full content — once relocated, `README.md` points to the new home (Story 22.6's job) or
  this story leaves a temporary pointer; the two must not silently diverge as duplicate copies.
- Do not touch the BMAD spec-driven tier.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Onboarding content in README's Common Commands | e.g. "get environment running" steps | Relocated to the Tutorials/Getting-Started home | n/a |
| Operational content in README's Common Commands | e.g. task-oriented CLI invocations | Relocated to the How-to Guides home | n/a |
| Mixed content in developer-guide.md | Both onboarding and operational material | Split per Story 22.4's classification, each half to its own quadrant | n/a |
| Skill-scoped guide content | e.g. `.claude/skills/conda-forge-expert/guides/*` | Stays in place — not relocated, this story only pulls general-purpose content | n/a |

</intent-contract>

## Code Map

- `README.md` — the "Common Commands" section, source content to relocate.
- `docs/reference/developer-guide.md` — mixed-content source, split per Story 22.4's
  classification.
- Story 22.4's map document — defines the two quadrants' physical target paths.
- `.claude/skills/conda-forge-expert/guides/`, `.claude/skills/conda-forge-expert/quickref/` —
  read-only reference; only genuinely general-purpose content gets pulled, skill-internal docs
  stay in place.

## Tasks & Acceptance

**Execution:**
- `feature` — relocate onboarding/"get running" content into the Tutorials/Getting-Started
  home.
- `feature` — relocate task-oriented operational content into the How-to Guides home.
- `feature` — split `developer-guide.md`'s mixed content across both, per Story 22.4's
  classification.

**Acceptance Criteria:**
- Given the Tutorials/Getting-Started and How-to-Guides roles have no discoverable home today,
  when their scattered content is relocated into the two new quadrant homes, then a newcomer
  with no prior context can find one place to get a working environment running and one place
  to find task-oriented operational instructions.
- Given the relocated content, when the move is done, then it is relocated/corrected existing
  material, not rewritten from scratch.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — expected: no new finding
  introduced.
- Manual verification: every fact relocated out of `README.md`'s Common Commands section and
  `developer-guide.md` is findable in exactly one new location, not duplicated in both the old
  and new spot.
