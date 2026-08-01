---
spec: one-front-door
status: draft
owner-dream: docs/dreams/one-front-door.md
surface: []          # composes spec-pyforge-marshal's existing surface; claims no files of its own — see Why
companions:
  - inventory.md
sources:
  - ../../../../../../docs/dreams/one-front-door.md
open_questions:
  - "Q1 — exact verb surface. The Dream lists run/status/check/land/switch(shipped)/homes(shipped)/doctor(delegate) as candidates it explicitly says to argue with, not a decided list."
  - "Q2 — row-6 triage. Five installed packages (bmad-manticore, bmad-labs-skills, bmad-utility-skills, bmad-method-wds-expansion, bmad-module-template) are largely unexercised in this repo; keep, wrap, or remove is unresolved."
  - "Q3 — the route-versus-contain boundary, per skill. Where supplying context once (CAP-5) becomes containing a skill's logic is undecided across the 51 bmad-* skills."
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. `docs/dreams/one-front-door.md` is listed in `sources:` for narrative rationale this contract intentionally omits.

# SPEC — one front door

## Why

The Charter says execution has one owner, Marshal — true of accountability,
false of interface. What is installed is a toolbox (11 conda packages, 51
`bmad-*` skills, 16 `skf-*` skills, 10 detectors, an engine, a dashboard, a
multi-project switch — see `inventory.md`), used today by remembering which
piece is needed, in what order, with which project active. Verified
2026-08-01: no composed `marshal` entry-point verbs exist yet —
`cli/init.py` and `cli/config.py` cover only the four already-shipped Epic-1
verbs (`init`, `homes`, `preflight`, `teardown`, `config`), all governed by
`spec-pyforge-marshal`. The Dream's own evidence: driving one fleet run
end-to-end required hand-invoking `bmad-loop run`/`status`, `tmux
capture-pane`, seven detectors individually, `dashboard-gen`,
`dashboard-watch`, `spec-surface-check --write-baseline`, `git push` across
nine homes, and `gh pr create/edit/merge` five times — none composed. The
failure modes observed were seams: `dashboard-watch` never started because
nobody thought of it, the push window reopened because nothing owned it
([[durable-runs]]), PR #170 merged broken because the landing path asked
nothing ([[pr-lifecycle]]).

**Surface note.** `spec-pyforge-marshal` already claims
`src/shared/packages/pyforge-marshal/**` in full; `spec-factory-console`
claims `docs/dashboard/**`; `spec-bmad-loop-governance` claims
`.bmad-loop/**`; `spec-multi-loop-isolation` claims `scripts/bmad-switch` +
`scripts/bmad-loop-worktree`. This Spec claims no surface of its own — its
verbs land inside `spec-pyforge-marshal`'s existing package when built. It
is the composition contract, not a second claim on the same files.

## Capabilities

- **CAP-1 — `marshal run`.**
  - **intent:** One verb drives a story or epic through `bmad-loop`
    internally (wraps, never absorbs the engine), supplying active
    project + loop home + policy layer + story key from context.
  - **success:** driving one story from the Dream's evidence scenario
    collapses `bmad-loop run` + `status` + `tmux capture-pane` into one
    `marshal run` call with no loss of context `bmad-loop` itself needs.

- **CAP-2 — `marshal status`.**
  - **intent:** One verb answers "is Marshal's work saved, and how is it
    going" across fleet state, the dashboard board, the detector registry,
    and unpushed-work-check ([[durable-runs]] CAP-5's reported property) —
    today that answer requires four separate commands.
  - **success:** `marshal status` reports fleet health, unpushed-work
    findings, and detector state in one call.

- **CAP-3 — `marshal check`.**
  - **intent:** `scripts/detectors.py`'s derived registry becomes reachable
    as `marshal check` rather than a separate pixi task the operator must
    remember exists.
  - **success:** `marshal check` produces the same output as
    `pixi run -e local-recipes detectors`, invoked through the front door.

- **CAP-4 — `marshal land`.**
  - **intent:** Once [[pr-lifecycle]]'s Spec exists and specifies what
    landing requires, `marshal land` is the one verb behind that door. This
    Spec records the routing contract only; landing behavior is
    pr-lifecycle's to specify.
  - **success:** `marshal land` invokes pr-lifecycle's specified behavior
    rather than this Spec re-specifying it.

- **CAP-5 — context supplied once.**
  - **intent:** The active project, loop home, policy layer, and story key
    are resolved once by the front door and threaded through every routed
    call, rather than each composed tool independently requiring them. This
    is the Dream's actual value — not shorter commands, context held once.
  - **success:** a single `marshal` invocation carries project/home/policy/
    story context to every tool it routes to, with no mid-sequence
    re-specification.

## Constraints

- **Wrap, never absorb.** The moment `marshal` contains a skill's logic
  instead of invoking it, this rule is broken one level up — CAP-1..4 route
  to `bmad-loop`, the detector registry, and pr-lifecycle; none reimplement
  them.
- **Each craft stays with its owning station.** `conda-forge-expert` is
  Mason's craft; Marshal routing to it is fine, Marshal knowing conda
  internals is not (a named boundary test in the source Dream).
- **Install-time and run-time stay two Dreams.** [[genesis-installer]] owns
  greenfield `init` / brownfield `adopt` / the write guard / managed
  regions; this Spec is scoped to the runtime half only.
- New verbs land inside `spec-pyforge-marshal`'s existing package surface —
  this Spec introduces no new package and claims no surface of its own.

## Non-goals

- Not a replacement for `bmad-loop`'s engine, any of the 51 `bmad-*`
  skills, or the 16 `skf-*` Skill Forge skills.
- Not the install/init surface — that is [[genesis-installer]]'s Spec.
- Not a decision on row 6's triage (see Open Questions Q2) — the Dream
  poses keep/wrap/remove as genuinely open, and this Spec does not invent
  an answer.

## Success signal

Driving one fleet run end-to-end — the Dream's own evidence scenario — no
longer requires hand-invoking `bmad-loop`, `tmux`, seven detectors,
`dashboard-gen`/`watch`, `spec-surface-check`, `git push` across nine homes,
and `gh pr` five times as separate command classes. It runs through
`marshal run`/`status`/`check`/`land`, with project/home/policy/story
context supplied once.

## Open Questions

- Q1 — exact verb surface. The Dream lists run/status/check/land/switch
  (shipped)/homes (shipped)/doctor (delegate) as candidates it explicitly
  says to argue with, not a decided list.
- Q2 — row-6 triage. Five installed packages (`bmad-manticore`,
  `bmad-labs-skills`, `bmad-utility-skills`, `bmad-method-wds-expansion`,
  `bmad-module-template`) are largely unexercised in this repo; keep, wrap,
  or remove is unresolved.
- Q3 — the route-versus-contain boundary, per skill. Where supplying
  context once (CAP-5) becomes containing a skill's logic is undecided
  across the 51 `bmad-*` skills.
