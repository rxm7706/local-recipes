---
title: BMAD from inside Cursor's own chat — interactive routing, not just headless dispatch
type: dream
owner: marshal
status: dreamt
---

# BMAD from inside Cursor's own chat — interactive routing, not just headless dispatch

## The Dream

"Portable to Cursor" is already solved for exactly one shape: headless, unattended dispatch.
`marshal factory dispatch` / `bmad-loop` already drive `cursor-agent -p --trust --workspace <dir>
--model <m> <prompt>` (Story 22.8, FR-193, CAP-8), verified live 2026-08-27, and it is the fleet's
*current active* `harness_preference` for both pyforge-marshal and pyforge-atlas today. Nobody has
proven the other shape: a human sitting inside Cursor's own IDE chat panel, invoking a BMAD skill
the way we invoke `bmad-build` inside Claude Code's chat right now, and getting the same
disciplined workflow back — skill discovery, the `render_skill.py` → `workflow.md` trigger, and
(for `bmad-build-auto`) the mandatory context-free reviewer subagents (Blind Hunter, Edge Case
Hunter, verification-gap, intent-alignment) that this repo's own `workflow.md` HALTs
`blocked`/`no subagents` without.

The dream: BMAD skills are reachable from Cursor's own interactive chat — not only its headless
CLI dispatch path — with the same review discipline, so a human working in Cursor gets the
identical guaranteed rigor a human working in Claude Code gets. The choice of IDE stops being a
choice about workflow quality.

## Grounding — verified state (2026-09-06)

- Every BMAD `SKILL.md` (`.claude/skills/bmad-*/SKILL.md`) is a two-line trigger: run
  `uv run _bmad/scripts/render_skill.py --project-root … --skill …`, then read and follow the
  printed `workflow.md`. The rendered workflow bodies themselves (grepped across
  `_bmad/render/bmad-build*/`) contain zero references to Claude-Code tool names (`Task tool`,
  `Agent tool`, `subagent_type`, `Skill tool`, `ScheduleWakeup`) — the prose is already
  agent-neutral ("Subagents, when the capability is available…").
- `bmad-build-auto`'s `workflow.md` / `step-04-review.md` are not neutral about the *capability*,
  only the *vendor*: "Using subagents when instructed is mandatory. If you cannot, HALT with status
  `blocked` and blocking condition `no subagents`." Each reviewer (Blind Hunter, Edge Case Hunter,
  verification-gap, intent-alignment) is launched as "a context-free subagent."
- The headless path already proves the capability works *through `cursor-agent`*:
  `harness_preference = ["cursor"]` is the live setting in both
  `pyforge-marshal/planning-artifacts/marshal-policy.toml` and pyforge-atlas's, with
  `model_tier_map` routing dev to `composer-2.5-fast` and review to `composer-2.5`
  (`data/harness_profiles/cursor.toml`, verified live 2026-08-27). That proves `cursor-agent -p
  --trust` headless mode's subagent tool works — it does **not** prove Cursor's own interactive IDE
  chat surface (the panel a human types into) exposes the same tool to the model running there. No
  evidence either way was found in-repo.
- `AGENTS.md` names Cursor as a sanctioned framework and `.cursor/rules/specs.mdc` exists as the
  cross-tool Tier pointer, but there is exactly one `.cursor/rules/*.mdc` file in the repo — none
  per-skill. Cursor's nearest analog to Claude Code's description-matched `Skill` tool is an "Agent
  Requested" rule (a `.mdc` carrying a `description` the agent can pull in on its own judgment) —
  mechanically derivable from the existing `SKILL.md` frontmatter + trigger body, but nothing
  generates it yet.
- Auto-memory (`~/.claude/projects/<encoded-path>/memory/`) and `CLAUDE.md`'s
  `@.claude/memory/MEMORY.md` inline-import are Claude-Code-loader-specific; Cursor rules do not
  resolve the same `@path` import syntax at load time.

## What it looks like when real

- A `.cursor/rules/*.mdc` file per BMAD skill (or one generated router), mechanically derived from
  `.claude/skills/bmad-*/SKILL.md`'s frontmatter (`name`, `description`) and its two-step trigger
  body, so an equivalent request typed into Cursor's chat surfaces and runs the same
  `render_skill.py → workflow.md` path Claude Code runs.
- A live probe, run once, that settles the open question directly: from inside Cursor's
  interactive IDE chat (not `cursor-agent -p` headless), can the running model invoke a genuine
  context-free subagent and get a synchronous result back in the same turn? A cheap probe modeled
  on the Blind Hunter prompt shape (fixed diff in, "launch a context-free subagent that reviews
  CONTENT" instruction, real output back) is enough to answer it either way.
- If the probe succeeds: `.mdc` routing is the whole gap, and `bmad-build`/`bmad-build-auto` run
  inside Cursor's chat with full parity to Claude Code — no quality degradation.
- If the probe fails: the workflow HALTs `blocked`/`no subagents` exactly as designed rather than
  silently skipping the review it depends on, and the honest fallback gets documented (e.g., route
  `bmad-build-auto`'s review step through the already-verified headless `cursor-agent -p` dispatch
  as the "subagent," or restrict Cursor's interactive chat to skills that don't mandate one).
- Team-memory (`.claude/memory/`) reachable from Cursor chat via whatever reference mechanism
  Cursor actually resolves at load time — verified, not assumed.

## What is real

Nothing built yet for the interactive path. This Dream is the seed; the finding that triggered it
is the 2026-09-06 conversation establishing that headless dispatch (CAP-6 / Story 22.8) is already
solved and live, and that the interactive-chat shape is a distinct, unverified surface.

## Constraints

- Do not re-litigate or duplicate CAP-6 / Epic 6 ([`pyforge-marshal.md`](pyforge-marshal.md)) — that
  Dream already owns "portability proven, not claimed" for the headless/dispatch shape (Story 22.8
  is done). This Dream is scoped to the *interactive-chat* shape only.
- The probe must be live and empirical — no assuming Cursor's interactive chat has the headless
  CLI's subagent support just because the CLI does.
- `.mdc` generation, if built, stays a mechanical derivation from the existing `SKILL.md` files
  (single source of truth), never a hand-maintained fork that can drift.

## Non-goals

- Rebuilding or replacing the already-verified headless `cursor-agent` dispatch path (Story 22.8) —
  this Dream is additive to it, not a redo.
- Day-one parity for all ~90 BMAD skills; the pilot only needs `bmad-build` (no subagent
  requirement) and `bmad-build-auto` (has the requirement) to answer the real question.
- Porting Claude Code's auto-memory harness feature itself; only confirming team-memory content is
  reachable in whatever form Cursor natively supports.

## Kinships

- [`pyforge-marshal.md`](pyforge-marshal.md) — CAP-6 / Epic 6, the realized headless-dispatch
  portability capability this Dream extends into the interactive surface.
- [`agent-portability.md`](agent-portability.md) — archived/absorbed into pyforge-marshal; this
  Dream is a fresh satellite for the one gap that absorption didn't cover.

## Realization log

- **2026-09-06** — Seeded from a conversation auditing what "portable to Cursor" would require.
  Finding: the unattended/headless path (`marshal factory dispatch` / `bmad-loop` via
  `cursor-agent -p`, Story 22.8, CAP-6) is already built, verified live 2026-08-27, and is the
  fleet's *current active* `harness_preference` for pyforge-marshal and pyforge-atlas. The gap is
  narrower than first assumed: (1) a mechanical `.mdc` routing layer so Cursor's own interactive
  chat can trigger BMAD skills the way Claude Code's `Skill` tool does, and (2) an unverified
  empirical question — whether Cursor's interactive IDE chat surface (not the headless CLI) can
  spawn a context-free subagent, which `bmad-build-auto`'s review step mandates. Next: run the live
  subagent probe from inside Cursor's chat before building any `.mdc` routing.
