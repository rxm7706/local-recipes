---
spec: bmad-cursor-interactive-routing
status: draft   # 2026-09-07 seeded so the Dream's chain link is durable (dream-chain INV-1). Nothing chosen yet: CAP-1 (the live subagent probe) gates every other CAP. Registered in doctor's DEFERRED_SPECS until the probe runs and the operator picks a shape.
owner-dream: docs/dreams/bmad-cursor-interactive-routing.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/bmad-cursor-interactive-routing.md
open_questions:
  - "Does Cursor's interactive IDE chat surface (not the headless `cursor-agent -p` CLI, already verified via Story 22.8/CAP-8) support genuine context-free subagent invocation? CAP-1's live probe answers this empirically before anything else here is built."
  - "If the probe fails: which fallback does the operator want — route `bmad-build-auto`'s review step through the already-verified headless `cursor-agent -p` dispatch as the 'subagent' (CAP-3a), or restrict Cursor-interactive-chat skill access to skills that don't mandate one, like plain `bmad-build` (CAP-3b)? Shapes CAP-3."
  - "If the probe succeeds: is `.mdc` generation a one-time script run by an operator, or a maintained pixi task that regenerates on every `SKILL.md` change? Shapes CAP-2's build-vs-maintain cost."
  - "What reference/import mechanism does Cursor actually resolve for `.mdc` rules at load time, and is there any analog to Claude Code's `@path` inline import so team-memory (`.claude/memory/MEMORY.md`) stays reachable from Cursor chat? Shapes CAP-4."
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

## Assumptions

- Owner `marshal` stands (matches the Dream's frontmatter and CAP-6/Epic 6 ownership of Cursor
  portability generally); the Spec moves with the owner (dream-chain INV-2) if it changes.
- The probe is cheap enough to run without a dedicated story — it is the Spec's own first action,
  not a separately-dispatched epic.
