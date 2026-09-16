---
spec: bmad-cursor-interactive-routing
status: ready   # 2026-09-15: CAP-1 probe PASS (Cursor Agent + Task). CAP-2 committed. CAP-3 residual for no-Task surfaces. CAP-4 verified. Leaves DEFERRED_SPECS; marshal Epic 45 is the dispatch home.
updated: "2026-09-15"
owner-dream: docs/dreams/bmad-cursor-interactive-routing.md
surface:
  - .cursor/rules/bmad-build.mdc
  - .cursor/rules/bmad-build-auto.mdc
  - scripts/bmad_cursor_mdc_check.py
  - tests/scripts/test_bmad_cursor_mdc_check.py
  - pixi.toml
companions: []
sources:
  - ../../../../../../docs/dreams/bmad-cursor-interactive-routing.md
open_questions: []
  # ALL FOUR ANSWERED 2026-09-09 (operator, fleet-readiness batch rows mars-A-B6..B9 / C10).
  # CAP-1 empirical result 2026-09-15: PASS on Agent+Task. Full text in § Open questions.
---

> **Canonical contract.** Derived 2026-09-15 from this folder's `.memlog.md`
> (CAP-1 probe dated that day). CAP-1 is closed. CAP-2 is committed work.
> CAP-3 is residual (no-Task surfaces). CAP-3a stays a later empty follow-on.
> CAP-4 is verified. Marshal Epic 45 is the dispatch home.

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

- **CAP-1 — The live subagent probe.** **Closed 2026-09-15 (PASS).**
  - **intent:** settle, empirically, whether Cursor's interactive IDE chat surface (not the
    headless CLI) can invoke a genuine context-free subagent and get a synchronous result back in
    the same turn. A cheap probe modeled on the Blind Hunter prompt shape (fixed diff in, "launch
    a context-free subagent that reviews CONTENT" instruction, real output back) is enough.
  - **success:** a dated, reproducible probe result recorded in this Spec's memlog — pass or fail,
    either answer closes CAP-1.
  - **result:** Cursor Agent chat invoked the Task tool (`subagent_type` generalPurpose) twice.
    First: agent `56105fa3-c052-429d-9061-d852e0640e2b`, CONTENT `add`/`return a-b`, token
    `HUNT7K2Q` returned in-turn with the subtraction defect named. Second (clean leak): agent
    `e74b7cd1-149c-4d18-b21f-06dcfd7adf6b`, `PARENT_USER_QUERY=UNKNOWN`. Not `cursor-agent -p`.
    Not a tool-less Ask panel. Not BMAD `workflow.md` Blind Hunter by name — the capability the
    workflow needs is present.

- **CAP-2 — `.mdc` routing layer** *(committed — CAP-1 passed)*.
  - **intent:** a `.cursor/rules/*.mdc` file per BMAD skill (or one generated router), mechanically
    derived from `.claude/skills/bmad-*/SKILL.md`'s frontmatter (`name`, `description`) and its
    two-step trigger body, so an equivalent request typed into Cursor's chat runs the same
    `render_skill.py → workflow.md` path Claude Code runs.
  - **success:** a request typed into Cursor's interactive chat surfaces and runs the identical
    `workflow.md` a Claude Code session would, for at least the `bmad-build` / `bmad-build-auto`
    pilot pair; generation stays mechanical (never a hand-maintained fork of `SKILL.md`).
    Maintained pixi task plus a drift detector (OQ-3). Reviewer steps use the Task tool when it
    is available.

- **CAP-3 — The honest fallback** *(residual — CAP-1 passed on Agent+Task; still binds
  surfaces without Task)*.
  - **intent:** `bmad-build-auto`'s workflow HALTs `blocked`/`no subagents` exactly as designed
    rather than silently skipping the review it depends on. CAP-3b (restrict Cursor-interactive
    routing / keep the HALT) applies when the running surface has no model-invoked Task tool.
    CAP-3a (route the review step through headless `cursor-agent -p`) stays a later empty
    follow-on — no story in Epic 45.
  - **success:** no skill silently degrades its review discipline inside Cursor chat.

- **CAP-4 — Team-memory reachability.** **Verified 2026-09-15.**
  - **intent:** `.claude/memory/` content reachable from Cursor chat via whatever reference
    mechanism Cursor actually resolves at load time — verified, not assumed.
  - **success:** `Read` of `.claude/memory/MEMORY.md` works. There is no Claude Code `@path`
    inline-import analog. `.cursor/rules/specs.mdc` is `alwaysApply: true` and points at
    `AGENTS.md`; it does not inline `MEMORY.md`. Carry team memory by `alwaysApply` pointer plus
    explicit `@file` / Read (a tool call, skippable).

## Constraints

- **Dream-first.** No code from the seed; this Spec ran CAP-1 before committing to CAP-2/CAP-3.
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
- Shipping CAP-3a (headless `cursor-agent -p` as a substitute reviewer) without its own
  equivalence evidence.

## Success signal

CAP-1's probe has run and its result is recorded (PASS, 2026-09-15, Agent+Task). CAP-2 ships for
the `bmad-build`/`bmad-build-auto` pilot pair (mechanical `.mdc` + pixi task + drift detector;
Task-backed review when available). CAP-4 is verified. CAP-3b remains the honest HALT on a
no-Task surface. This Spec has left doctor's `DEFERRED_SPECS` and decomposes as marshal Epic 45.

## Open questions — closed 2026-09-09; probe result 2026-09-15

All four answered by the operator, which is exactly the condition the `draft` status recorded.

- **OQ-1 — does Cursor's interactive IDE chat support genuine context-free subagent invocation?**
  **RUN THE PROBE, AND PLAN FOR A NO.** No in-repo evidence pointed either way and no probe
  artifact existed, but the two surfaces differ in the way that matters: the headless profile that
  works is `cursor-agent -p --trust --force` (`_bmad-output/harness-profiles/cursor.toml`), a
  non-interactive one-shot where the agent owns the whole turn, while Cursor interactive chat is a
  human-in-the-loop editor session whose parallel-agent features were predicted as session-level
  fan-out of the *same* prompt — not a model-invoked tool returning a synchronous result in-turn.
  Budget the probe at one session and treat CAP-3 as the likely branch. **Rejected:** skip the
  probe and adopt CAP-3b unconditionally — it forfeits this Dream's own stated discipline and
  would be the second time this estate declared a capability without exercising it.
  **Probe 2026-09-15: PASS on Cursor Agent + Task.** The 2026-09-09 prediction (same-prompt
  fan-out only) did not hold for Agent chat: the running model invoked Task and got a
  context-free in-turn result. CAP-3 is not the primary branch.

- **OQ-2 — which fallback if the probe fails?** **Take CAP-3b NOW** (restrict
  Cursor-interactive-chat skill access to skills that do not mandate a subagent, e.g. plain
  `bmad-build`) and name **CAP-3a as a follow-on** — do not ship 3a as the first move. CAP-3a
  re-implements the review fan-out at a second seam, and this estate has been burned there twice
  (`bmad-build-auto`'s mandatory subagents break inside a fork; a fork ignoring declared scope). A
  shelled-out `cursor-agent -p` "subagent" is the same class of substitute reviewer with a process
  boundary instead of a fork boundary, and no proof it preserves context-freeness. CAP-3b costs one
  `.mdc` allowlist and keeps the HALT honest. If 3a is ever chosen it needs its own equivalence
  evidence before any story dispatches under it.
  **After PASS:** CAP-3b remains the residual for surfaces without Task. CAP-3a stays empty.

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
  **Verified 2026-09-15:** assumption holds.

## Assumptions

- Owner `marshal` stands (matches the Dream's frontmatter and CAP-6/Epic 6 ownership of Cursor
  portability generally); the Spec moves with the owner (dream-chain INV-2) if it changes.
- The probe is cheap enough to run without a dedicated story — it is the Spec's own first action,
  not a separately-dispatched epic. Closed 2026-09-15; Epic 45 starts at CAP-2.
- `status: draft` → `ready` (2026-09-09): the shape is chosen — probe first, plan for NO, CAP-3b
  as the fallback, `.mdc` generation as a maintained task plus detector, no inline-import analog
  assumed. `docs/dreams/bmad-cursor-interactive-routing.md` flipped `dreamt` → `specified` then.
- 2026-09-15: CAP-1 PASS commits CAP-2. Doctor's `DEFERRED_SPECS` entry is removed. Dream stays
  `specified` until Epic 45 ships.
