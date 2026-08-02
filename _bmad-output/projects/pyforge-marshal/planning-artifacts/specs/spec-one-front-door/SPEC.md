---
spec: one-front-door
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/one-front-door.md
surface: []          # archived — no live surface of its own; see § What carries forward
companions:
  - inventory.md      # kept live — the evidence base for Q2 (row-6 triage), still genuinely open
sources:
  - ../../../../../../docs/dreams/one-front-door.md
open_questions:
  - "Q2 — row-6 triage. Five installed packages (bmad-manticore, bmad-labs-skills, bmad-utility-skills, bmad-method-wds-expansion, bmad-module-template) are largely unexercised in this repo; keep, wrap, or remove is unresolved — not addressed anywhere in spec-pyforge-marshal's PRD."
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included. It states what was contracted, why it
> ended, and what survives — not a plan for work that will not happen. **`inventory.md` kept
> live** (not archived) — it is the evidence base for Q2 (row-6 triage), which is still
> genuinely open; a future decision on those five packages should read it, not rederive it.

# one-front-door — retirement record

## Why it was contracted

The Charter says execution has one owner, Marshal — true of accountability, false of
interface. Verified 2026-08-01: no composed `marshal` entry-point verbs existed; driving one
fleet run end-to-end required hand-invoking `bmad-loop run`/`status`, `tmux capture-pane`,
seven detectors individually, `dashboard-gen`/`watch`, `spec-surface-check`, `git push` across
nine homes, and `gh pr create/edit/merge` five times — none composed. Five capabilities:
`marshal run` (CAP-1), `marshal status` (CAP-2), `marshal check` (CAP-3), `marshal land`
(CAP-4, routing only — behavior specified by [[pr-lifecycle]]), and context resolved once and
threaded through every routed call (CAP-5, the Dream's actual value).

## Why it ended

**Retired 2026-08-02, as part of a dream-consolidation pass.** Checked each capability
individually against what's specified today, not assumed clean:

- **CAP-1** (`marshal run`) and **CAP-2** (`marshal status`) are **convergent, no gap** —
  already specified as `factory spin` (FR-9..11) and `marshal status` (FR-36); this Dream's
  candidate verb names did not need new FRs, per Q-15's resolution in the real PRD.
- **CAP-3** (`marshal check`) → **new FR-65** (added 2026-08-01) — the one genuinely new
  capability from this Dream: the detector registry reachable as a verb, not a separately
  remembered pixi task.
- **CAP-4** (`marshal land`, routing only) → **FR-59/FR-60**, per [[pr-lifecycle]]'s own
  retirement record — that Dream's Spec specified the landing behavior this capability
  deferred to.
- **CAP-5** (context resolved once, threaded through every routed call) → folded into
  **FR-65**'s own Consequences ("context ... resolves once per `marshal` invocation and
  threads to whichever verb is routed to — `run`, `status`, `check`, and `land` alike") rather
  than getting a separate FR — it is a cross-cutting property of the front door, not an
  independent feature.
- **Q1** (exact verb surface) and **Q3** (route-versus-contain boundary) carried forward
  verbatim into the PRD as **Q-15** and **Q-16** — both explicitly still open, not invented
  answers.
- **Q2** (row-6 triage) is **not addressed anywhere in the PRD** — grepped 2026-08-02, zero
  hits for `bmad-manticore` or "row-6"/"row 6". This is not a clean absorption; see § What
  carries forward.

## What carries forward

CAP-1/2/4/5 and Q1/Q3 all have a real, current home (a convergent FR, FR-65, or a named open
question in the PRD) — nothing to track for them here. **Q2 does not** — whether
`bmad-manticore`, `bmad-labs-skills`, `bmad-utility-skills`, `bmad-method-wds-expansion`, and
`bmad-module-template` should be kept, wrapped, or removed is a real, undismissed question
with no owner after this retirement. `inventory.md` is kept live specifically so a future
triage of those five packages starts from the 2026-07-31 evidence table, not a rederivation.

## Non-goals

- **Reviving this Dream as written.** CAP-1/2/4/5's intent already lives elsewhere; only Q2 is
  genuinely open, and reviving the whole Dream would re-litigate what's settled.
- **Treating this record as a backlog item in itself.** Archived Dreams are excluded from the
  Backlog board by design — but Q2's underlying triage is a real, undismissed gap; a future
  decision (by Marshal or whoever owns package hygiene) is the correct vehicle, not this
  record.
- **Assuming Marshal will triage row 6.** This retirement does not assign Q2 anywhere — it
  was never an FR to begin with, only ever an open question.

## Success signal

A reader arriving at this Dream learns in one page which four capabilities are settled and
where, and that Q2's five-package triage is still genuinely open with its evidence preserved
— without mistaking "archived" for "everything here is resolved."
