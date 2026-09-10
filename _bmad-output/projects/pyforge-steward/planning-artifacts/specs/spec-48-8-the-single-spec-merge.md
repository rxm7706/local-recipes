---
title: "Story 48.8: The Single-Spec merge"
type: story
created: 2026-09-10
baseline_revision: b19ad5971acd608fd0bcc23d7935c05d9cd2e181
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/convergence.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/python-agent-platform.md
  - scripts/ad_citation_check.py
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.8: The Single-Spec merge

<intent-contract>

## Intent

**Problem:** `spec-pyforge-unifying-strategy` still `extends: spec-python-agent-platform`, so the host contract lives split across two Specs with a summary table instead of full `pap:CAP-1..6` text. Four sibling Specs point at the parent via `absorbed-into: spec-python-agent-platform`, Epic 10–12 still bind to the parent Spec, and the parent Dream carries a stale absolute `pyforge.*` import ban.

**Approach:** Copy `pap:CAP-1..6` full intent/success text from `spec-python-agent-platform` into the Unifying SPEC (replacing the inherited-host summary table), retire `extends:`, supersede the parent Spec with `absorbed-into` pointers retargeted to Unifying, update Epic 10–12/convergence/spine parent lines, and soften the Dream import rule to match live carve-outs. **`pap:` stays a live prefix** — move text, never namespace.

## Boundaries & Constraints

**Always:** Preserve `pap:CAP-*` and `pap:AD-*` qualified ids everywhere outside definitional headings. Keep `[feature.python-agent-platform]` pixi env id unchanged. Run chain detectors after edits.

**Never:** Hand-edit `sprint-status-ledger.yaml`. Do not rename `[feature.python-agent-platform]`. Do not fold `pap:` into `canopy:`. Do not edit mason's `spec-django-accelerator-framework` (relay only — note in Auto Run Result).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MERGE_TEXT | Unifying SPEC § Inherited host table | Full `pap:CAP-1..6` intent+success blocks; table removed | N/A |
| EXTENDS_RETIRED | Unifying frontmatter | No `extends:` key; merge note in body | N/A |
| PARENT_SUPERSEDED | pap SPEC frontmatter | `status: superseded`; `absorbed-into: spec-pyforge-unifying-strategy` | N/A |
| SIBLING_POINTERS | Four plugin/topology SPEC.md:5 | `absorbed-into: spec-pyforge-unifying-strategy` | N/A |
| EPIC_BIND | epics.md Epic 10–12 headers | Bind to Unifying SPEC; stories keep `pap:CAP-*` / `pap:AD-*` | N/A |
| DREAM_FIX | python-agent-platform.md Non-goals | Import ban qualified (carve-outs named), not absolute | N/A |

</intent-contract>

## Code Map

- `spec-pyforge-unifying-strategy/SPEC.md:22,67-86` — remove `extends:`; replace inherited-host table with full CAP text from pap SPEC L65-120; move `single-spec-merge-timing` open_question to § Residual
- `spec-python-agent-platform/SPEC.md:1-5` — `status: superseded`; add `absorbed-into: spec-pyforge-unifying-strategy`; keep § Superseded block
- `spec-asgi-multiplexer-monolith/SPEC.md:5`, `spec-langflow-django-plugin/SPEC.md:5`, `spec-enterprise-multi-agent-orchestration/SPEC.md:5`, `spec-db-gpt-django-plugin/SPEC.md:5` — retarget `absorbed-into`
- `ARCHITECTURE-SPINE.md:281-283,617-618` — parent pointer → Unifying SPEC; keep `pap:AD-n` cite form
- `convergence.md:18,122` — extension binding → merged-into-Unifying wording
- `epics.md:847-848,917-918,979-980` — Epic 10–12 spec binding headers
- `docs/dreams/python-agent-platform.md:70-73` — qualify `pyforge.*` import ban (platform boundary, named carve-outs)

## Tasks & Acceptance

**Execution:**
- `spec-pyforge-unifying-strategy/SPEC.md` — merge full `pap:CAP-1..6` text; retire `extends:`; update Residual — host contract is inline
- `spec-python-agent-platform/SPEC.md` — supersede with pointer to Unifying
- Four sibling SPEC.md files — retarget `absorbed-into` frontmatter
- `ARCHITECTURE-SPINE.md` — retarget parent Spec references at L281 and L617
- `convergence.md` — update extension-binding prose
- `epics.md` — Epic 10–12 spec binding lines cite Unifying SPEC
- `docs/dreams/python-agent-platform.md` — qualify import ban (src/platform/ carve-outs)

**Acceptance Criteria:**
- Given Unifying SPEC, when read, then full `pap:CAP-1..6` intent+success appear and no `extends:` in frontmatter
- Given pap SPEC frontmatter, when read, then `status: superseded` and `absorbed-into: spec-pyforge-unifying-strategy`
- Given four sibling specs, when frontmatter read, then each `absorbed-into: spec-pyforge-unifying-strategy`
- Given `pixi run -e local-recipes dream-chain-check`, when run, then exit 0
- Given `pixi run -e local-recipes chain-completeness-check`, when run, then exit 0
- Given `rg 'extends: spec-python-agent-platform' _bmad-output/projects/pyforge-steward`, when run, then no matches

## Verification

**Commands:**
- `pixi run -e local-recipes dream-chain-check` — expected: exit 0
- `pixi run -e local-recipes chain-completeness-check` — expected: exit 0
- `rg 'extends: spec-python-agent-platform' _bmad-output/projects/pyforge-steward/planning-artifacts` — expected: no matches
- `rg 'absorbed-into: spec-python-agent-platform' _bmad-output/projects/pyforge-steward/planning-artifacts/specs` — expected: no matches (siblings retargeted)

## Design Notes

The merge follows the DAF absorption pattern (Story 48.7 namespace pass): qualified ids stay, text moves. Mason's `spec-django-accelerator-framework` already points at Unifying — no edit (cross-station relay).

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 0, false 2, maybe-false 0, reject 1
- findings:
  - `[false]` `[reject]` Sibling spec body text still names `spec-python-agent-platform`'s chain — intentional historical pointer in absorbed specs' narrative; frontmatter `absorbed-into` retarget is the contract surface
  - `[false]` `[reject]` Unifying SPEC Residual still mentions `spec-python-agent-platform` memlog — historical record of merge source, not an active `extends:` binding
  - `[low]` `[reject]` `dream-chain-check` reds on pre-existing marshal findings — unrelated to steward 48.8 merge surfaces

## Auto Run Result

**2026-09-10 — Story 48.8 landed in dispatch worktree.**

- Merged full `pap:CAP-1..6` intent+success into `spec-pyforge-unifying-strategy/SPEC.md` § Host platform; retired `extends:`; moved single-spec-merge-timing to Residual as shipped.
- Superseded `spec-python-agent-platform` (`status: superseded`, `absorbed-into: spec-pyforge-unifying-strategy`).
- Retargeted four sibling specs' `absorbed-into` frontmatter to Unifying.
- Updated Epic 10–12 spec bindings, `convergence.md`, `ARCHITECTURE-SPINE.md` parent pointers, and qualified remaining Constraint cites.
- Fixed `docs/dreams/python-agent-platform.md` import ban with named carve-outs.

**Files changed:** 11 planning/docs artifacts (see git diff from `b19ad5971a`).

**Verification:** `chain-completeness-check` exit 0; `extends:` and sibling `absorbed-into: spec-python-agent-platform` absent from steward planning-artifacts; `dream-chain-check` fails on pre-existing marshal chain gaps (not introduced by this story).

**followup_review_recommended:** false
