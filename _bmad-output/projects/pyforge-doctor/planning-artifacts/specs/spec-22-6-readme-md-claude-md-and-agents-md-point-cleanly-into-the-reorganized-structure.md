---
title: 'README.md, CLAUDE.md, and AGENTS.md point cleanly into the reorganized structure'
type: 'fix'
created: '2026-09-11'
status: 'done'
baseline_revision: '395e66abd6aabdc5c630cff6e7b3c98b19c94dd3'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      README Quick start, Common Commands, and Pixi tasks sections still carry full
      operational text until Story 22.5 populates docs/tutorials/ and docs/how-to/.
    evidence: |-
      docs/MAP.md lists those README sections as Story 22.5 relocation targets; the
      quadrant scaffolds are empty README stubs only. Replacing with pointers now would
      send newcomers to unpopulated homes.
    location: >-
      README.md
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Depends on Stories 22.4 and 22.5. Once the Diátaxis-adapted structure exists,
`README.md`, `CLAUDE.md`, and `AGENTS.md` (the repo's three highest-visibility entry-point docs)
still either duplicate content that now lives in the new structure, or point at the old,
pre-reorganization locations Story 22.5 moved content out of.

**Approach:** Update every link and cross-reference in the three entry-point docs that targets
content Stories 22.4/22.5 relocated, and remove any content now duplicated in the new
structure in favor of a pointer. `CLAUDE.md` and `AGENTS.md` stay where they are (tool entry
points, not general docs, per the owning Dream's own framing) — this story corrects their
pointers, it does not relocate them into the new quadrant structure.

## Boundaries & Constraints

**Always:**
- Every internal link into the reorganized structure must resolve — verify each one, do not
  assume Story 22.4/22.5's relocations match what the old links expected.
- Where a fact now lives in the new structure, the entry-point doc gets a pointer to it, not a
  second copy — matching Story 22.2's same discipline (the duplicated priority list) applied to
  the new structure.

**Never:**
- Do not relocate `CLAUDE.md` or `AGENTS.md` themselves into the Diátaxis structure — they
  remain tool entry points at the repo root.
- Do not touch content in `README.md`/`CLAUDE.md`/`AGENTS.md` that is unrelated to Stories
  22.4/22.5's relocations (e.g. Story 22.1/22.2's own already-corrected content is out of this
  story's scope, already done).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Link into a relocated file | e.g. `README.md` linking to a `docs/reference/*.md` file Story 22.4 moved | Link updated to the new path | n/a |
| Content now duplicated in the new structure | e.g. onboarding steps Story 22.5 relocated but README still carries the full text | README's copy replaced with a pointer to the new home | n/a |
| Link that already resolves correctly | A link untouched by Stories 22.4/22.5 | Left unchanged — not this story's scope | n/a |

</intent-contract>

## Code Map

- `README.md:152-156` — project-structure tree lists pre-22.4 paths (`docs/enterprise-deployment.md`,
  `docs/mcp-server-architecture.md` at docs root); update to Diátaxis quadrants per `docs/MAP.md`.
- `README.md:281` — link `docs/reference/mcp-server-architecture.md` → canonical
  `docs/explanation/mcp-server-architecture.md` (22.4 relocation).
- `README.md:374` — inline ref `docs/reference/enterprise-deployment.md` →
  `docs/explanation/enterprise-deployment.md` (22.4 relocation).
- `CLAUDE.md:200-205` — Project Documentation Reference: same two explanation relocations;
  add `docs/MAP.md` as the general-docs index.
- `AGENTS.md:40,194` — `docs/reference/library-llms-full.md` unchanged (still Reference quadrant).
- `docs/MAP.md` — authoritative target map; Story 22.5 scaffolds only (`docs/tutorials/`,
  `docs/how-to/`) — README Common Commands / Quick start dedup deferred until 22.5 populates.
- Redirect stubs at `docs/reference/mcp-server-architecture.md` and
  `docs/reference/enterprise-deployment.md` — resolve but entry points should cite canonical paths.

## Tasks & Acceptance

**Execution:**
- `fix` — audit every link in `README.md`/`CLAUDE.md`/`AGENTS.md` against Stories 22.4/22.5's
  actual relocations; update any that now point at a moved or stale location.
- `fix` — replace any content now duplicated in the new structure with a pointer.

**Acceptance Criteria:**
- Given the reorganized structure exists (Stories 22.4-22.5), when the three entry-point docs'
  pointers are corrected, then no internal link into the reorganized structure is broken.
- Given a fact now lives in the new structure, when the entry-point docs are checked, then no
  such fact is also duplicated verbatim in `README.md`/`CLAUDE.md`/`AGENTS.md` without one side
  pointing to the other.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — expected: no new finding
  introduced.
- Manual verification: every internal markdown link in `README.md`/`CLAUDE.md`/`AGENTS.md`
  resolves to a real path (no 404s against the repo tree).

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 3 findings — high 0, medium 1, low 0, false 0, maybe-false 0, defer 2
- findings:
  - `[medium]` `[defer]` README operational sections not yet deduplicated to tutorials/how-to — Story 22.5 scaffolds empty; defer pointer swap until 22.5 lands
  - `[defer]` `[defer]` developer-guide.md split pending — file still correctly at docs/reference/ until Story 22.5 executes MAP split
  - `[false]` `[reject]` AGENTS.md docs/foundry/ reference — pre-existing foundry-cutover policy placeholder, not introduced by this change

## Auto Run Result

Status: done

**Summary:** Updated README.md, CLAUDE.md, and AGENTS.md so Story 22.4 explanation-quadrant relocations and the Diátaxis map are cited at canonical paths; README project-structure tree reflects the four quadrants.

**Files changed:**
- `README.md` — Diátaxis docs tree; mcp-server + enterprise-deployment → docs/explanation/; MAP.md pointer
- `CLAUDE.md` — Project Documentation Reference paths + docs/MAP.md index line
- `AGENTS.md` — docs/MAP.md pointer under Where things are
- Story spec — code map, review log, deferred 22.5 follow-up

**Review:** 0 patches; 2 deferred (22.5-dependent dedup); 1 rejected (pre-existing).

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — exit 0 (pre-existing warnings only)
- Manual: all concrete `docs/` links in the three entry-point files resolve; Story 22.4 explanation relocations cited canonically

**Residual risks:** README Common Commands / Quick start duplication remains until Story 22.5; re-run link sweep after 22.5 merges or dispatch 22.6 follow-up pass.
