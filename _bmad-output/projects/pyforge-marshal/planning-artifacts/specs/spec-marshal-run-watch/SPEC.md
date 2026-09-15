---
id: SPEC-marshal-run-watch
spec: marshal-run-watch
status: ready
owner-dream: docs/dreams/marshal-run-watch.md
companions: []
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/tests/**/*watch*
sources:
  - ../../../../../../docs/dreams/marshal-run-watch.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to
> build, test, and validate. `docs/dreams/marshal-run-watch.md` is listed in `sources:` for
> narrative rationale this contract intentionally omits.
>
> **Round one is CAP-1+CAP-2.** CAP-3/4/5 are named so a later story can pick them up without a
> new Spec, but this Spec's implementable slice — the one a first dispatch should build — is the
> `marshal watch` CLI verb alone.

# The operator stops re-pasting the status prompt — marshal watches its own runs

## Why

A pain to solve. Watching a live `bmad-loop` run or `bmad-build-auto` dispatch today means an
operator hand-driving a repeatable ritual through a chat session: run `bmad-loop status <run_id>
--json`, run `bmad-loop list --json`, run `marshal status --project <slug>`, diff it against what
was true minutes ago, and decide whether to check again. That exact ritual was worked out live
against a real multi-hour run (pyforge-herald `20260914-201759-bd47`, Epic 21, 2026-09-15) and
captured as a Claude-only project skill (`.claude/skills/marshal-run-watch/`) — proven correct,
but invisible to marshal's own CLI, its unified `pyforge marshal` grammar, its MCP face, its
persona, and its portal. The skill also had to learn, ad hoc, that `marshal status`'s `dispatch_*`
fields can be a stale, unrelated prior dispatch record when a `bmad-loop` run is what's actually
live — a trap any future caller of `marshal status` alone will hit again. This Spec ports that
proven ritual into marshal itself so watching a run is a CLI capability, not a chat convention.

## Capabilities

- **CAP-1**
  - **intent:** An operator (or any caller of marshal's CLI) can run `marshal watch` against one
    pinned run, one station's current run, or the whole fleet, and receive a report that gathers
    ground truth, diffs it against the immediately-prior observation, and states only what
    changed (or that nothing did) plus a recommended delay before checking again — for both the
    `bmad-loop` orchestrator pattern and the `bmad-build-auto` single-dispatch pattern.
  - **success:** `marshal watch --project <slug> --run <run_id>` (bmad-loop pattern) and `marshal
    watch --project <slug>` with no run pinned (auto-detects the station's current run,
    bmad-build-auto or bmad-loop) each produce a report matching the five-section shape
    (completions / delta / currently-running / up-next / user-action-required) the hand-driven
    skill produced against the live pyforge-herald run; `marshal watch --fleet` produces the
    compact per-project snapshot the skill's fleet mode produces, escalated/paused projects
    sorted first. A second invocation with no intervening change reports "nothing changed," not a
    repeated full report. Every code path is covered by a test that does not require a live
    bmad-loop process (fixture journals/state fed to the same diff+report logic).
- **CAP-2**
  - **intent:** `marshal watch` never conflates a live `bmad-loop` run's per-story ground truth
    with an unrelated, stale `bmad-build-auto` dispatch record that `marshal status` may also be
    holding for the same project slug.
  - **success:** A test fixture where `marshal status --project <slug>`'s `dispatch_*` fields
    describe a DIFFERENT, older run than the live `bmad-loop status <run_id>` result proves
    `marshal watch`'s report uses only the `bmad-loop` result for that pattern's per-story detail,
    and states plainly (as the hand-driven reports did) that a stale unrelated dispatch record was
    present and ignored.
- **CAP-3** *(follow-on — not this Spec's implementable round)*
  - **intent:** `marshal watch`'s report is reachable over `POST /stations/marshal/mcp` as a
    named tool, the way `django-marshal`'s existing `publish_loop_run` /
    `heartbeat_loop_run` / `complete_loop_run` / `list_loop_story_tasks` tools are registered in
    `mcp_asgi.py`.
  - **success:** A new `@server.tool(...)`-registered tool in `django_marshal_portal/mcp_asgi.py`
    returns the same report shape CAP-1 produces, callable by the `bmad-agent-marshal` persona's
    `mcp` action kind.
- **CAP-4** *(follow-on — not this Spec's implementable round)*
  - **intent:** The `bmad-agent-marshal` persona can offer "watch a run" as a named menu action
    that dispatches `pyforge marshal watch ...` grammar.
  - **success:** A menu entry exists in the persona's resolved `agent.menu` that, when selected,
    issues a `grammar` action kind starting `pyforge marshal watch` — no forbidden-action
    violation (no direct filesystem, no ad-hoc HTTP) in the transcript.
- **CAP-5** *(follow-on — not this Spec's implementable round)*
  - **intent:** The report CAP-1 produces is viewable in the `django-marshal` browser portal,
    alongside its existing `chrome_home` view.
  - **success:** A new view + URL route in `django_marshal_portal` renders CAP-1's report for a
    project/run selected in the portal, without requiring a terminal.

## Constraints

- Ports the skill's validated logic — the delta predicate (story phase/`commit_sha`, run status,
  escalation, loop-branch SHA, PR state) and the boundary/backoff pacing
  (`min(300s, seconds-to-next-:00/:30-boundary)` while active, boundary-only while
  paused/escalated) — faithfully; this Spec does not invent a new status model or a different
  delta definition than what was proven live.
- Read-only. `marshal watch` never resolves escalations, resumes runs, dispatches new work, or
  writes to any sprint ledger. Those remain `bmad-loop resolve`, `marshal factory resume`, and
  `marshal factory dispatch`.
- No second status engine. `marshal watch` is a report *shape* over the same ground truth
  `marshal status` and `bmad-loop status`/`list` already read (journals and run state, never a
  hand-maintained feed); it does not compete with `marshal status` as a second verdict.
- Persisted last-observation state is a local, regenerable cache (mirroring the skill's
  `.claude/data/marshal-run-watch/*.json`), never a new durable ledger. A missing or stale cache
  degrades to a first-observation report, never a wrong delta.
- CLI first. This Spec's implementable round is CAP-1+CAP-2 alone. CAP-3/4/5 are named so a
  later story can take them up without a new Spec, but are not required for this round to be
  complete.

## Non-goals

- No MCP tool, persona menu entry, or portal view in this round (CAP-3/4/5, explicitly deferred).
- No event-driven wake mechanism (no Monitor-equivalent) — polling only, on the caller's own
  cadence; `marshal watch` recommends a delay, it does not schedule anything itself.
- Does not replace `marshal status` as the fleet-summary command, and does not write to any
  sprint ledger or resolve any escalation.

## Success signal

An operator (or the `bmad-agent-marshal` persona, once CAP-4 lands) runs `marshal watch --project
<slug> [--run <run_id>]` or `marshal watch --fleet` from a fresh terminal with no prior state and
gets the same report shape and correctness the hand-driven Claude skill produced against the live
pyforge-herald run on 2026-09-15 — including correctly ignoring a stale, unrelated `dispatch_*`
record — with no `.claude/skills/marshal-run-watch/` file consulted anywhere in the process.
