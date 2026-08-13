---
project: pyforge-steward
date: 2026-08-13
trigger: 2026-08-10 implementation-readiness audit, NEEDS-RESPEC on Stories 8.4 and 8.5
scope: Moderate — backlog reorganization (one new story inserted, two renumbered), no architecture change
---

# Sprint Change Proposal — Epic 8 (Two boards, one truth)

## 1. Issue Summary

The 2026-08-10 implementation-readiness audit (`implementation-readiness-report-20260810.md`)
flagged Epic 8's Stories 8.4 ("Fail loud, fail alone") and 8.5 ("Explicit status-vocabulary
translation") `NEEDS-RESPEC`, blocking dispatch (`sprint-status.yaml`: both `blocked`). This
proposal resolves both so they can be re-dispatched.

## 2. Root-Cause Analysis

### 8.4 — genuine gap, needs a producer story

The Spec's Q3 resolution and the landed architecture (`architecture-jira-github-projects-sync-
2026-08-09`, AD-2/AD-5) establish `trigger=schedule` batch cadence as Epic 8's **default**
operating mode — `epics.md:656-658`: "`updated_at` may only select candidates under
`trigger=schedule`, never decide [the zero-loop question]." That sentence presupposes a
candidate-*selection* mechanism exists. It does not: Story 8.1 built only the single-pair
`reconcile()` core — `cli.py:231-233` makes `--github-item`/`--jira-issue` **mutually
exclusive**, i.e. exactly one pair per invocation, always. No story anywhere builds the
`trigger=schedule` loop that would enumerate multiple candidates (by comparing each linked
item's current `updated_at` against its recorded baseline) and reconcile each in turn.

8.4's own AC — "a batch containing one unlinked item completes for all others" — presupposes
that batch loop. It is not 8.4's defect; it is a missing **producer story** for a capability
the architecture already decided but no story decomposition ever assigned. The frozen 8-1 spec
"defers nothing for CAP-4's batch premise" (audit finding AF-3) — it isn't the deferred half's
owner, and neither is any other landed or backlog story.

### 8.5 — not a genuine conflict; the audit's framing was a misreading

The audit describes 8.5 as colliding with a "frozen boundary" the landed code cites at
`sync.py:421-422`: *"Never build a general status-vocabulary translation table."* Read in
isolation this looks like a permanent architectural prohibition. Read in its own source —
Story 8.1's frozen spec, `spec-8-1-bidirectional-propagation.md:119-121` — it is not one:

> "Never build a general status-vocabulary translation table. This story propagates the
> configured field's raw value 1:1... **The reviewable translation table + explicit
> hard-fail-on-unmapped is Story 8.5.**"

8.1 explicitly *scopes itself out* of building the table because it explicitly *names 8.5* as
the story that builds it. There is no boundary to amend and no architecture-phase decision to
re-open. The only real gap is asymmetry already in the landed code: the Jira→GitHub direction
already hard-fails on an unmapped status (`sync.py:613-616`, tested), but the GitHub→Jira
direction is still 8.1's raw 1:1 passthrough (`sync.py:417-421`) — exactly what 8.5 exists to
replace. 8.5's own AC ("any status crossing the boundary") already covers both directions as
written; it does not need new text, only the audit's stale "collision" framing corrected and
its `blocked` status lifted.

## 3. Epic Impact

- **Epic 8 story count: 5 → 6.** One new producer story inserted ahead of the current 8.4/8.5,
  which shift down by one (8.4 → 8.5, 8.5 → 8.6). Neither existing story has been dispatched
  (`backlog`/`blocked`, no branch, no story spec) — renumbering carries no landed-work risk.
- **No FR change.** The new story decomposes FR-27 (bidirectional propagation) further, the
  same FR Story 8.1 already carries — it operationalizes the already-decided AD-2/AD-5
  `trigger=schedule` mechanism, not a new capability. No new FR, no PRD edit.
- **No architecture change.** AD-2 (trigger/transport decoupling) and AD-5 (per-field baseline
  comparison) already specify everything the new story needs; it is pure decomposition.
- **PRD MVP: unaffected.** FR-27..FR-31 stand exactly as written.

## 4. Path Forward: Option 1 (Direct Adjustment) — selected

| Option | Viable? | Rationale |
|---|---|---|
| **1. Direct Adjustment** | **Yes — selected** | Both fixes are pure backlog decomposition: insert one story (8.4) whose entire scope is already covered by landed architecture decisions; correct one mis-framed audit note. Effort: Low (8.4 insertion) + trivial (8.5 unblock). Risk: Low — no code exists yet for either shifted story. |
| 2. Rollback | Not viable | Nothing is built for 8.4 or 8.5 to roll back. |
| 3. PRD MVP review | Not viable | No FR, capability, or MVP scope is in question — this is pure decomposition-gap repair. |

## 5. Detailed Change Proposals

### 5.1 `epics.md` — insert new Story 8.4, renumber the following two

**NEW Story 8.4: The schedule trigger enumerates real candidates**
```
### Story 8.4: The schedule trigger enumerates real candidates
**FR/AD:** FR-27 (AD-2/AD-5) • **Effort:** M • **Deps:** S-8.1
**Given** `trigger=schedule` fires **Then** every linked item whose current `updated_at`
differs from its recorded per-field baseline is selected as a candidate and reconciled through
the existing single-pair `reconcile()` engine, in one run, with no `--github-item`/
`--jira-issue` pair required per invocation.
**Status:** backlog
```

**RENAME** `8-4-fail-loud-fail-alone` → `8-5-fail-loud-fail-alone` (story text unchanged; now
depends on the new 8.4 for its batch, per its own AC).

**RENAME** `8-5-explicit-status-vocabulary-translation` → `8-6-explicit-status-vocabulary-
translation` (story text unchanged). **Unblock**: clear `blocked`, set `backlog` — no boundary
amendment needed (§2 above).

**Audit-note correction** (`epics.md:665-670`, the "Audit note" paragraph): replace the 8.5
"collides with a frozen boundary" sentence with a corrected note pointing to this proposal and
`spec-8-1-bidirectional-propagation.md:119-121` as the resolution record, so a future reader
does not re-litigate a non-conflict.

### 5.2 `sprint-status.yaml` (both Tier-3 and tracked ledger)

- Add `8-4-the-schedule-trigger-enumerates-real-candidates: backlog`
- Rename `8-4-fail-loud-fail-alone` → `8-5-fail-loud-fail-alone: backlog` (unchanged status)
- Rename `8-5-explicit-status-vocabulary-translation` → `8-6-explicit-status-vocabulary-
  translation: backlog` (was `blocked`)

### 5.3 `spec-jira-github-projects-sync/SPEC.md`

No change — CAP-4 and CAP-5's `intent`/`success` text already describes exactly what the
renumbered 8-5 and 8-6 build; the new 8-4 is architecture-decomposition, not a new capability,
so it claims no new CAP.

### 5.4 Secondary artifacts

None. No deployment, IaC, monitoring, or CI/CD surface touches Epic 8 yet (greenfield, nothing
landed beyond 8.1's core module).

## 6. Handoff

**Scope classification: Moderate** — backlog reorganization (insert + renumber), no strategic
replan. Route to: **Developer agent** (direct implementation is safe here — no PM/Architect
re-scoping needed since architecture is unchanged) for `epics.md` + ledger edits, then this
Spec's normal dispatch flow picks up the three stories in order.

**Success criteria:** `epics.md` shows 6 stories in Epic 8 with the new 8-4 first; both
Tier-3 and tracked `sprint-status-ledger.yaml` show `8-4-the-schedule-trigger-...: backlog`,
`8-5-fail-loud-fail-alone: backlog`, `8-6-explicit-status-vocabulary-translation: backlog`
(no `blocked` remaining in Epic 8); `forward-dependency-check` and `chain-completeness-check`
both clean for pyforge-steward afterward.
