---
title: The operator stops re-pasting the status prompt — marshal watches its own runs
type: dream
owner: marshal
status: archived
                    # the implementable round, CAP-3/4/5 named follow-ons). No open questions —
                    # the Dream left none.
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `marshal-run-watch`).

# The operator stops re-pasting the status prompt — marshal watches its own runs

## The Dream

Watching a live `bmad-loop` run or a `bmad-build-auto` dispatch today means an operator
hand-driving a long, repeatable ritual through a chat session: run `bmad-loop status
<run_id> --json`, run `bmad-loop list --json`, run `marshal status --project <slug>`,
diff it against what was true five minutes ago, decide whether anything changed, and
decide how long to wait before checking again. Every property of that ritual — the
exact commands, the delta logic, the boundary-aligned polling, the "story completed,
check sooner" acceleration — was worked out once, live, against the pyforge-herald
Epic 21 run on 2026-09-15, and captured as a **Claude-only project skill**
(`.claude/skills/marshal-run-watch/`) that a `/loop` session re-invokes by hand.

That skill is real, tested against a live multi-hour run, and it works. But it lives
entirely outside marshal: it is prose a coding assistant follows, not code marshal
ships, so it exists only inside a chat session with that skill installed. Nothing on
marshal's own CLI, its MCP face, its persona, or its portal UI can produce this report.

The Dream is that **watching a run is a marshal capability**, not a Claude Code
convention. `marshal watch` — one run, one station's current run, or the whole
fleet — does what the skill does today: gather ground truth, diff it against the last
observation, report only when something changed or a caller-chosen cadence boundary is
due, and recommend how long to wait before checking again. It ships once, in
`pyforge-marshal`'s own CLI, and every other face — the unified `pyforge marshal watch`
grammar, the MCP tool, the persona menu, the portal view — either gets it for free or
costs one deliberate wrapper on top, per marshal's own layering.

> A ritual a human repeats by hand, that a program could repeat exactly, is a feature
> marshal hasn't shipped yet.

## Why now — measured, not feared

Live evidence from a single afternoon (2026-09-15, pyforge-herald run
`20260914-201759-bd47`, Epic 21 deck-trio derivation):

| Observation | Where it showed up |
|---|---|
| The same five-command sequence (`bmad-loop status`, `bmad-loop list`, `marshal status`, a git-branch-SHA check, a `gh pr list` filter) was re-run by hand roughly 20 times over 90 minutes | This conversation's own tool-call history |
| The delta logic (what counts as "changed": a story's phase, its `commit_sha`, the run's overall status, a new escalation, the loop branch's SHA, a PR's state) had to be re-derived from memory each time, not read from a single source of truth | Same |
| The "is it actually stalled or just quiet" liveness check (log mtime + size growth, not just the phase field) was reinvented ad hoc when story 21.3 ran ~75 minutes with zero token checkpoints | Same — nearly escalated a healthy run as stuck |
| `marshal status --project <slug>` surfaces a **stale, unrelated** one-shot dispatch record (`dispatch_*` fields) that must be manually filtered out on every single check when a `bmad-loop` run is what's actually live | Same, called out explicitly in every report this session produced |
| The eventual fix — a Claude Skill (`marshal-run-watch`) — had to reimplement marshal's own boundary/state logic in prose, in a project directory, invisible to `pyforge marshal watch`, `POST /stations/marshal/mcp`, the `bmad-agent-marshal` persona, and the `django-marshal` portal | `.claude/skills/marshal-run-watch/SKILL.md`, authored this session |

None of this is hypothetical scale — it is the exact ritual a fleet operator (human or
the `bmad-agent-marshal` persona) will repeat every time a bmad-loop run or dispatch is
in flight, which is most of the time this factory is running.

## What it looks like when real

- **One CLI verb replaces the ritual.** `marshal watch --project <slug> [--run
  <run_id>]` (a pinned run or a station's current one) and `marshal watch --fleet`
  (every project) each do what the skill's ground-truth-gathering + delta + boundary
  logic does today, in real Python under `pyforge.marshal.cli`, next to `status`/
  `homes`/`check`.
- **The stale-dispatch trap is gone.** `marshal watch` never conflates a live
  `bmad-loop` run's per-story detail with an unrelated prior `bmad-build-auto`
  dispatch record — it reads the right ground truth for whichever pattern is actually
  live, the way the skill already learned to.
- **Delta and cadence are a library, not a memory.** The "what counts as changed"
  predicate and the boundary/backoff poll-delay recommendation are one tested module
  other marshal code (and doctor's story-status source, if it ever wants the same
  liveness signal) can import — not prose a coding assistant re-derives per session.
- **The grammar is free.** `pyforge marshal watch ...` works the day the CLI verb
  ships — `pyforge.core.dispatch`'s argv passthrough needs no changes.
- **The other three faces are named, not assumed.** An MCP tool
  (`POST /stations/marshal/mcp`), a `bmad-agent-marshal` menu entry, and a
  `django-marshal` portal view are each real, separate follow-on work — this Dream
  states plainly that shipping the CLI verb does not give you those three for free,
  and scopes them as later CAPs an operator can take up or defer.
- **The Claude skill either retires or thins to a caller.** Once `marshal watch`
  exists, `.claude/skills/marshal-run-watch/SKILL.md` either becomes a thin wrapper
  that shells out to it, or retires outright — it does not stay the only
  implementation of logic marshal itself now owns.

## Constraints / Non-goals

- **Ports the skill's logic; does not redesign it.** The skill's delta predicate
  (story phase/commit_sha, run status, escalation, loop-branch SHA, PR state) and its
  boundary/backoff pacing were validated live against a real multi-hour run this
  session. The Spec derived from this Dream should port that behavior faithfully, not
  invent a new status model.
- **CLI first; the other three faces are scoped, not bundled.** Round one is the
  `marshal watch` CLI verb alone (which the unified grammar inherits for free). The
  MCP tool, the persona menu entry, and the portal view are named as explicit
  follow-on CAPs in the Spec this Dream produces — they may land as later stories in
  the same epic, or be deferred; this Dream does not presume they ship together.
  Whether the portal view or the MCP tool comes first is itself an open question for
  the Spec to resolve, not this Dream.
- **Read-only.** `marshal watch` observes and reports; it does not resolve
  escalations, resume runs, dispatch new work, or write to any sprint ledger. Those
  remain `bmad-loop resolve`, `marshal factory resume`, and `marshal factory dispatch`.
- **No second status engine.** `marshal watch` is a caller-facing report *shape*
  (delta-aware, boundary-paced) over the SAME ground truth `marshal status` and
  `bmad-loop status`/`list` already read — journals and run state, never a
  hand-maintained feed. It does not compete with `marshal status` as a second verdict.
- **Persisted state is local and disposable.** Whatever this capability uses to
  remember "what was true last time" (mirroring the skill's own
  `.claude/data/marshal-run-watch/*.json` cache) is a local, regenerable cache, not a
  new durable ledger. A missing or stale cache degrades to "first observation," never
  to a wrong delta.
- **Consumes `run-state-one-publisher` if and when it lands, doesn't wait on it.**
  [[run-state-one-publisher]] (status: specified, not yet realized at this Dream's
  seeding) would eventually give `marshal watch` a published run-state plane instead
  of journal-scraping. This Dream does not block on that landing — `marshal watch`
  reads today's ground truth (journals, `bmad-loop status`/`list`, `marshal status`)
  the same way the skill already does, and can be re-pointed at the published plane
  later without changing its caller-facing shape.

## Kinships

[[pyforge-marshal]] (the station Dream; `marshal watch` joins `status`/`homes`/`check`
as a CLI verb under the same package) · [[fleet-status-supervisor-fallback]] (realized
— the sibling correctness fix for `marshal status`'s fleet view; `marshal watch`
reuses that same supervisor/engine liveness distinction rather than re-deriving it) ·
[[marshal-single-story-dispatch]] (realized — `marshal factory dispatch`, the
`bmad-build-auto` pattern this capability watches) · [[run-state-one-publisher]]
(specified, not realized — the future ground-truth source this capability can migrate
to without changing its report shape) · [[marshal-token-economy]] (loop-home policy
and budget fields `marshal watch` surfaces alongside phase/commit detail) ·
[[bmad-loop-liveness-footgun]] (the `UNSUPERVISED` fleet-picture trap this
capability's liveness check must not reproduce) · [[django-accelerator-framework]]
(host for the `django-marshal` portal-view follow-on CAP, if taken up).

## Realization log

- **2026-09-15** — Seeded. A live, hand-driven `/loop` monitoring session against
  pyforge-herald run `20260914-201759-bd47` (Epic 21) produced a working ritual —
  captured as the Claude-only skill `.claude/skills/marshal-run-watch/` — that
  reimplements, in prose, status/delta/pacing logic that belongs in marshal itself.
  Operator asked to promote it into marshal "across its planes" (CLI, unified
  grammar, MCP, persona, UI); per the always-on Dream-first rule this Dream is the
  entry point, not a direct edit to `pyforge-marshal`'s source. Next act: `bmad-spec`
  derives the Spec under `pyforge-marshal`.
- **2026-09-15** — Specified. `spec-marshal-run-watch` derived headless/express (the Dream was
  fully seeded; no open questions raised). Mints CAP-1 (the `marshal watch` CLI verb, pinned-run/
  station/fleet scope) and CAP-2 (the stale-`dispatch_*`-record trap closed) as the implementable
  round, plus CAP-3 (MCP tool), CAP-4 (persona menu entry) and CAP-5 (portal view) as named
  follow-ons for later stories in the same epic. Both self-validate passes (coherence,
  preservation) passed clean. `status: ready`. Next act: decompose CAP-1+CAP-2 into a Story under
  `pyforge-marshal/epics.md`.
