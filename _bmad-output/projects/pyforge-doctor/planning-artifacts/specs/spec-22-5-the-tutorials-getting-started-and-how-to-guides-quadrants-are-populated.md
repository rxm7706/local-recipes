---
title: 'The Tutorials/Getting-Started and How-to-Guides quadrants are populated'
type: 'feature'
created: '2026-09-11'
status: 'done'
baseline_revision: '85cfb7d7e4bc743c2d636f18d2eb761e423d3eea'
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

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 4 findings — high 0, medium 1, low 2, false 1, maybe-false 0
- findings:
  - `[medium]` `[patch]` `enterprise-deployment.md` §1 retained duplicate procedural steps after creating `air-gapped-mirror-setup.md` — trimmed Setup Steps/Mirror Management/Offline build blocks; pointer to how-to remains
  - `[low]` `[defer]` Inbound links to old `docs/reference/antigravity-developer-startup.md` / `manticore-studio.md` paths remain repo-wide — Story 22.6 entry-point sweep
  - `[low]` `[defer]` `CLAUDE.md` still cites pre-relocation doc paths — Story 22.6 explicit scope
  - `[false]` `[reject]` README project-structure tree stale doc paths — updated in this pass to Diátaxis layout

## Auto Run Result

Status: done

**Summary:** Populated `docs/tutorials/getting-started.md` and seven how-to guides by relocating existing content from `README.md`, `developer-guide.md`, and `enterprise-deployment.md` §1; moved antigravity/manticore to `docs/how-to/` with redirect stubs; split `developer-guide.md` to reference-only; updated MAP and quadrant indexes.

**Files changed:**
- `docs/tutorials/getting-started.md` — onboarding path (new)
- `docs/how-to/*.md` — recipe testing, pixi tasks, GitHub Actions CI, troubleshooting, air-gap mirror, antigravity, manticore (new + relocated)
- `docs/reference/developer-guide.md` — reference-only split with quadrant pointers
- `docs/reference/antigravity-developer-startup.md`, `manticore-studio.md` — redirect stubs
- `README.md` — temporary pointers to new homes (no duplicate full content)
- `docs/MAP.md`, quadrant README indexes — population status updated
- `docs/explanation/enterprise-deployment.md` — procedural split to how-to
- Story spec + sprint ledger — status promoted

**Review:** 1 patch applied (enterprise-deployment dedupe); 2 items deferred to Story 22.6; 1 rejected as already fixed.

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — exit 0
- Manual: relocated README Quick start / Pixi / GitHub Actions content lives only under `docs/tutorials/` and `docs/how-to/`; `developer-guide.md` retains formats + config reference only

**Residual risks:** Inbound links to old paths (including § anchors) remain until Story 22.6; README pointers are temporary per spec until 22.6 full entry-point sweep.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 1, false 1, maybe-false 0, reject 2
- findings:
  - `[low]` `[patch]` Mason-backed `recipe build` route dropped during `developer-guide.md` split — re-added to `docs/how-to/recipe-testing-and-builds.md`
  - `[false]` `[reject]` Duplicate README/Pixi task tables remain — README now holds pointers only; full tables live in `docs/how-to/pixi-tasks.md`
  - `[defer]` `CLAUDE.md` / agent entry points still cite pre-relocation paths — Story 22.6 explicit scope
  - `[defer]` Section-anchor inbound links to relocated docs hit redirect stubs — Story 22.6 link sweep

## Auto Run Result

Status: done

**Summary:** Populated `docs/tutorials/getting-started.md` and seven how-to guides by relocating scattered onboarding and operational content from `README.md` and `docs/reference/developer-guide.md`. Split `developer-guide.md` to reference-only (formats, platform matrix, config). Moved `antigravity-developer-startup.md` and `manticore-studio.md` to `docs/how-to/` with redirect stubs. Updated quadrant READMEs and `docs/MAP.md`.

**Files changed:**
- `docs/tutorials/getting-started.md` — onboarding path (new)
- `docs/tutorials/README.md` — index
- `docs/how-to/*.md` — recipe testing, CI, pixi tasks, troubleshooting, air-gap, antigravity, manticore (new/relocated)
- `docs/how-to/README.md` — index
- `docs/reference/developer-guide.md` — split to reference-only with quadrant pointers
- `docs/reference/antigravity-developer-startup.md`, `manticore-studio.md` — redirect stubs
- `docs/reference/README.md`, `docs/MAP.md` — population status updated
- `README.md` — duplicate sections replaced with pointers to new homes

**Review:** 1 patch applied (low); 2 items deferred to Story 22.6; 2 rejected/false.

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — exit 0 (pre-existing warnings only)
- Manual: README and developer-guide no longer duplicate relocated tutorial/how-to content; new quadrant homes indexed in READMEs and MAP

**Residual risks:** Inbound links from `CLAUDE.md`, `AGENTS.md`, and §-anchored references remain until Story 22.6.
