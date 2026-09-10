---
title: 'The structure-graph reference is wired for spin, unblocking the already-built loop-home index'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Story 28.3 has deployed a real `.codegraph/codegraph.db` index for any loop home with `[context."structure-graph"]` enabled since it shipped — confirmed live 2026-09-10 (`marshal preflight pyforge-marshal` built a real 229MB index in ~21s). But `bmad-build-auto`'s own skill files had zero reference to codegraph, exactly the gap `output` had before Story 28.30 closed it. The already-paid-for index has been providing zero benefit.

**Approach:** Add one bullet to `step-01-clarify-and-route.md`'s existing "1. Load context" item, telling the agent to check for `.codegraph/codegraph.db` and prefer `codegraph context`/`codegraph explore` over unbounded file reads when it exists. Self-gating on the index's own presence (never on which engine launched the session), so a dispatch worktree — which has no index until Story 28.31 resolves its own cost question — reads nothing new.

## Boundaries & Constraints

**Always:** Condition the reference on the index file's own presence, not on a layer flag or an engine check — the file existing IS the signal that provisioning already happened and paid its cost. Keep this as an additional navigation aid, never a replacement for the epic-context/planning-graph/derived-context sources.

**Never:** Pre-commit to building a dispatch-side index in this story — that is 28.31's own, still-unresolved scope. Move this bullet into a numbered sub-step that existing story references (elsewhere in this file, or in other files) count by number — inserted as a `-` bullet, not a renumbered item.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| INDEX_PRESENT | `.codegraph/codegraph.db` exists (a preflighted loop home with the layer on) | Agent is told to prefer `codegraph context`/`codegraph explore` for locating/understanding code | N/A |
| INDEX_ABSENT | No index (dispatch worktree today, or layer off) | Nothing new happens — same navigation as before this story | N/A |

</intent-contract>

## Code Map

- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` — new bullet inside item 1 "Load context"

## Tasks & Acceptance

**Execution:**
- `step-01-clarify-and-route.md` — one new bullet — feature

**Acceptance Criteria:**
- Given a spin session in a loop home with `[context."structure-graph"].enabled = true` and a present `.codegraph/codegraph.db`, when step-01's "Load context" item runs, then the agent is told to query the index instead of unbounded file reads
- Given a loop home with the layer off, or no index present, when step-01 runs, then nothing new happens
- Given the existing context sources, when this bullet is added, then they are unchanged — this is additive only

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** Closed the mirror-image gap to Story 28.30's `output` finding: the loop-home codegraph index has existed since Story 28.3 and just needed the reference. No cost question needed answering for this half (unlike 28.31's dispatch-side spike) — the index already exists and was already paid for.

**Files changed:**
- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` — new bullet in item 1
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — 28-33 → done

**Review:** A one-bullet documentation addition to an already-reviewed skill file section; verified by reading the rendered instruction against the acceptance criteria. No separate review-loop pass.

**Verification:** Read the edited file and confirmed the bullet reads correctly, is self-gating on the index's presence, sits inside item 1 rather than renumbering anything, and does not alter any existing bullet. `codegraph context --help`/`codegraph explore --help` checked live to confirm the cited CLI grammar is real and current.

**Residual risks:** Same honest residual as 28.30's own record — no automated test proves an agent actually queries the index when told to; only that the instruction is present, correctly worded, and correctly gated.

## Verification

**Commands:**
- Read `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` and confirm the new bullet under item 1
- `codegraph context --help` / `codegraph explore --help` — expected: both verbs exist as documented
