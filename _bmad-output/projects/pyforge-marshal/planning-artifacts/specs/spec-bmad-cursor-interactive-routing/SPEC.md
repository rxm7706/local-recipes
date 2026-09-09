---
spec: bmad-cursor-interactive-routing
status: ready   # 2026-09-09: all four open questions answered by the operator batch -- the shape is chosen (probe first, plan for NO, CAP-3b as the fallback). Stays registered in doctor's DEFERRED_SPECS (a `ready` Spec IS in OPEN_SPEC_STATUSES) until the probe runs and decomposition begins.
updated: "2026-09-09"
owner-dream: docs/dreams/bmad-cursor-interactive-routing.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/bmad-cursor-interactive-routing.md
open_questions: []
  # ALL FOUR ANSWERED 2026-09-09 (operator, fleet-readiness batch rows mars-A-B6..B9 / C10).
  # Full text with answers in § Open questions -- closed 2026-09-09.
---

> **Canonical contract — in `draft`.** This SPEC is the chain link for
> `docs/dreams/bmad-cursor-interactive-routing.md`, not yet a contract downstream can bind to:
> CAP-1 (the live probe) has not run, so CAP-2..4 are candidate shapes contingent on its result,
> not committed work.

# SPEC — BMAD skills reachable from Cursor's own interactive chat

## Why

`marshal factory dispatch` / `bmad-loop` already drive Cursor headlessly (`cursor-agent -p --trust
--workspace <dir> --model <m>`, Story 22.8/FR-193/CAP-8, verified live 2026-08-27, and the fleet's
current active `harness_preference` for pyforge-marshal and pyforge-atlas) — that shape is solved
and out of scope here (see Constraints). Unsolved: a human sitting inside Cursor's own IDE chat
panel, invoking a BMAD skill the way `bmad-build`/`bmad-build-auto` run inside Claude Code's chat,
and getting the same disciplined workflow back — skill discovery, the `render_skill.py →
workflow.md` trigger, and (for `bmad-build-auto`) the mandatory context-free reviewer subagents
that `workflow.md` HALTs `blocked`/`no subagents` without. The choice of IDE should not be a choice
about workflow quality. Owner: **marshal** (owns Cursor portability generally, per CAP-6/Epic 6).

## Capabilities

*CAP-1 is the gate: nothing else here is committed work until it runs and answers the open
question. CAP-2..4 are candidate shapes contingent on its result.*

- **CAP-1 — The live subagent probe.**
  - **intent:** settle, empirically, whether Cursor's interactive IDE chat surface (not the
    headless CLI) can invoke a genuine context-free subagent and get a synchronous result back in
    the same turn. A cheap probe modeled on the Blind Hunter prompt shape (fixed diff in, "launch
    a context-free subagent that reviews CONTENT" instruction, real output back) is enough.
  - **success:** a dated, reproducible probe result recorded in this Spec's memlog — pass or fail,
    either answer closes CAP-1.
- **CAP-2 — `.mdc` routing layer** *(contingent on CAP-1 passing)*.
  - **intent:** a `.cursor/rules/*.mdc` file per BMAD skill (or one generated router), mechanically
    derived from `.claude/skills/bmad-*/SKILL.md`'s frontmatter (`name`, `description`) and its
    two-step trigger body, so an equivalent request typed into Cursor's chat runs the same
    `render_skill.py → workflow.md` path Claude Code runs.
  - **success:** a request typed into Cursor's interactive chat surfaces and runs the identical
    `workflow.md` a Claude Code session would, for at least the `bmad-build` / `bmad-build-auto`
    pilot pair; generation stays mechanical (never a hand-maintained fork of `SKILL.md`).
- **CAP-3 — The honest fallback** *(contingent on CAP-1 failing)*.
  - **intent:** `bmad-build-auto`'s workflow HALTs `blocked`/`no subagents` exactly as designed
    rather than silently skipping the review it depends on; document which of CAP-3a (route the
    review step through the already-verified headless `cursor-agent -p` dispatch) or CAP-3b
    (restrict Cursor-interactive-chat routing to skills without a subagent mandate) the operator
    picks.
  - **success:** the chosen fallback is documented and, if CAP-3a, wired; no skill silently
    degrades its review discipline inside Cursor chat.
- **CAP-4 — Team-memory reachability.**
  - **intent:** `.claude/memory/` content reachable from Cursor chat via whatever reference
    mechanism Cursor actually resolves at load time — verified, not assumed.
  - **success:** a live check confirms Cursor's chat surface can read (or is explicitly documented
    as unable to read) the team-memory content Claude Code's `@.claude/memory/MEMORY.md` inline
    import provides.

## Constraints

- **Dream-first.** No code from the seed; this Spec runs CAP-1 before committing to CAP-2/CAP-3.
- **Do not re-litigate or duplicate CAP-6/Epic 6** (`pyforge-marshal.md`) — that Dream already owns
  "portability proven, not claimed" for the headless/dispatch shape (Story 22.8 is done). This
  Spec is scoped to the *interactive-chat* shape only.
- **The probe must be live and empirical** — no assuming Cursor's interactive chat has the headless
  CLI's subagent support just because the CLI does.
- **`.mdc` generation, if built, stays a mechanical derivation** from the existing `SKILL.md` files
  (single source of truth), never a hand-maintained fork that can drift.
- **One PR verdict.** Warden stays the sole gate; this Spec adds no second verdict.

## Non-goals

- Rebuilding or replacing the already-verified headless `cursor-agent` dispatch path (Story 22.8).
- Day-one parity for all ~90 BMAD skills; the pilot only needs `bmad-build` (no subagent
  requirement) and `bmad-build-auto` (has the requirement) to answer the real question.
- Porting Claude Code's auto-memory harness feature itself; only confirming team-memory content is
  reachable in whatever form Cursor natively supports.

## Success signal

CAP-1's probe has run and its result is recorded (done either way). If it passed, CAP-2 has
shipped for the `bmad-build`/`bmad-build-auto` pilot pair and CAP-4 is verified. If it failed, the
operator's CAP-3 choice is documented and, if CAP-3a, wired. At that point this Spec leaves
doctor's `DEFERRED_SPECS` and decomposes into marshal epics.

## Open questions — closed 2026-09-09

All four answered by the operator, which is exactly the condition the `draft` status recorded.

- **OQ-1 — does Cursor's interactive IDE chat support genuine context-free subagent invocation?**
  **RUN THE PROBE, AND PLAN FOR A NO.** No in-repo evidence points either way and no probe
  artifact exists, but the two surfaces differ in the way that matters: the headless profile that
  works is `cursor-agent -p --trust --force` (`_bmad-output/harness-profiles/cursor.toml`), a
  non-interactive one-shot where the agent owns the whole turn, while Cursor interactive chat is a
  human-in-the-loop editor session whose parallel-agent features are session-level fan-out of the
  *same* prompt — not a model-invoked tool returning a synchronous result in-turn. Budget the probe
  at one session and treat CAP-3 as the likely branch. **Rejected:** skip the probe and adopt
  CAP-3b unconditionally — it forfeits this Dream's own stated discipline and would be the second
  time this estate declared a capability without exercising it.
- **OQ-2 — which fallback if the probe fails?** **Take CAP-3b NOW** (restrict
  Cursor-interactive-chat skill access to skills that do not mandate a subagent, e.g. plain
  `bmad-build`) and name **CAP-3a as a follow-on** — do not ship 3a as the first move. CAP-3a
  re-implements the review fan-out at a second seam, and this estate has been burned there twice
  (`bmad-build-auto`'s mandatory subagents break inside a fork; a fork ignoring declared scope). A
  shelled-out `cursor-agent -p` "subagent" is the same class of substitute reviewer with a process
  boundary instead of a fork boundary, and no proof it preserves context-freeness. CAP-3b costs one
  `.mdc` allowlist and keeps the HALT honest. If 3a is ever chosen it needs its own equivalence
  evidence before any story dispatches under it.
- **OQ-3 — one-time `.mdc` script or a maintained task?** **A maintained pixi task plus a drift
  detector** — never a one-time operator script. This Spec's own Constraint already forbids what a
  one-time run produces ("never a hand-maintained fork that can drift"), and a one-time script
  *becomes* that fork the first time a `SKILL.md` changes. The repo has both the pattern and the
  enforcement shape (`llms-full-check`, `bmad-drift-check`) and a documented three-place rule for a
  new CI script; hardcoded lists omit the newest thing. **Accepted narrowing:** a one-time script
  for a two-skill pilot is acceptable **only** if the generated `.mdc` files stay untracked, so
  they cannot silently rot in git.
- **OQ-4 — is there an analog to Claude Code's `@path` inline import?** **Assume NO.** Carry team
  memory by `alwaysApply` rule content plus explicit `@file` attachment, and **verify it in the
  same probe session as CAP-1** — same ten minutes, same chat panel; running it separately doubles
  the setup. The repo already proves the loaders differ and already worked around it once:
  `.cursor/rules/specs.mdc` uses `alwaysApply: true` plus a plain-prose instruction ("Read
  AGENTS.md at the repo root first") rather than an import, while `CLAUDE.md` uses a bare
  `@.claude/memory/MEMORY.md` line whose own comment warns it must stay un-backticked to remain an
  import. **Cost recorded honestly:** Claude Code inlines ~40 index lines at load; a Cursor rule
  that says "read this file" spends a tool call and can be skipped.

## Assumptions

- Owner `marshal` stands (matches the Dream's frontmatter and CAP-6/Epic 6 ownership of Cursor
  portability generally); the Spec moves with the owner (dream-chain INV-2) if it changes.
- The probe is cheap enough to run without a dedicated story — it is the Spec's own first action,
  not a separately-dispatched epic.
- `status: draft` → `ready` (2026-09-09): the shape is chosen — probe first, plan for NO, CAP-3b
  as the fallback, `.mdc` generation as a maintained task plus detector, no inline-import analog
  assumed. Doctor's `DEFERRED_SPECS` entry **stays live** (a `ready` Spec is in
  `OPEN_SPEC_STATUSES`) until the probe runs and decomposition begins.
  `docs/dreams/bmad-cursor-interactive-routing.md` flips `dreamt` → `specified` in the same pass.
