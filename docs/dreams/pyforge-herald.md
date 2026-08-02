---
title: Herald — capture the dream, illustrate the telemetry, proclaim the release
type: dream
owner: herald
status: specified
---

# Herald — the outward voice and design surface

## The Dream

Herald is the factory's **voice and visual surface**. Invisible engineering is
failed engineering; Herald exists so nothing the factory does stays invisible.
Not infrastructure — BMAD monorepo/multi-project machinery and cross-agent
portability belong to [[pyforge-marshal]] (the 2026-07-23 ownership review;
reaffirmed 2026-08-02 when [[fleet-chain-completeness]]'s orchestrated
regeneration machinery moved to Marshal for the same reason). Herald keeps
the communication face only.

Herald's work spans **four moments of proclamation**, and every product and
every Smith passes through all of them:

| # | Moment | What Herald owes | Lands as |
|---|---|---|---|
| **1** | **Pitch** — a Dream must be argued, not merely filed | the case made legible to humans who did not dream it | the deck family |
| **2** | **Progress** — a build in flight is not self-explaining | what changed, what it cost, what it unblocked | release notables, run telemetry as imagery |
| **3** | **Success** — shipping is not the same as being known to have shipped | the claim, with the evidence attached | the release proclamation |
| **4** | **Operations** — the long tail nobody announces | fixes, updates, deprecations, decommissions | change + end-of-life notices |

Moment 1 is the **first** thing Herald had to build, not the extent of the
job — the bookend framing ("first to touch a Dream, last to touch a release")
was retired 2026-07-25 because it reads as two touchpoints with silence
between them. Moment 4 needs no new lifecycle vocabulary: ending is one act,
scale-invariant across a Dream, a package, an application or a platform
(`archived`, with one of four reasons). What is missing is not the state —
it is anyone being **told**.

## What is real

- **The deck family (Moment 1 content)** — decks live on one shared engine
  under `presentations/`, bound to the Modernist design system, with the
  6-artifact export set proven repeatedly (`deck-export`). This is
  production-ready. Full orchestration detail (design-code-bridge +
  deckcraft + video-scripts + modernist-identity, the 9-station expansion,
  artifact tracking, 7 capabilities) lives in `spec-herald-pitch` —
  [[herald-pitch]] itself is archived (dream-level consolidation,
  2026-08-02) but its Spec is real, unbuilt, and ready for the
  PRD/Architecture/Epics decomposition its own "Next Steps" call for; that
  work has not run yet.
- **The bridge, mechanized (`pyforge-herald` CLI)** — the Design↔Code seed/pull
  loop proven manually on 7 decks in one day is being packaged as a
  deterministic CLI (`herald deck seed/pull/status/watch`, `SPEC-design-code-bridge`
  CAP-1..5, FR-01–FR-26). This is **in progress, not finished**: as of
  2026-08-02 the foundation is 4 of 17 stories done (package scaffold, the
  MCP-transport spike, the bridge-core skeleton, the registry module) —
  real code at `src/shared/packages/pyforge-herald/` (`bridge.py`, `cli.py`,
  `errors.py`, `registry.py`, `state.py`, `transport/`), with tests. The CLI
  parser currently exposes only the empty `deck` subcommand group; `seed`,
  `pull`, `status` and `watch` are not wired up yet. The loop
  (`loop/pyforge-herald`) is paused mid-story on the next one, the fallback
  transport adapter (1.3).
- **The stage** — the program console publishes the factory's state
  ([[factory-console]], Marshal's ledger; in the persona ideal Herald
  proclaims from it).

## The frontier — Moments 2–4, active now

Moments 2, 3 and 4 were specced but had no implementation surface. **This is
now Herald's active, in-progress work** — not aspirational, not shipped:

- **Moment 2 (Progress)** — `herald progress` / release notables composed
  from run telemetry and cost data, delivered where the audience lives.
- **Moment 3 (Success)** — `herald success` — a claim ("Project X shipped;
  here is the proof") backed by retrievable evidence (tests, metrics,
  adoption), gated on operator review before publish.
- **Moment 4 (Operations)** — `herald notice` — deprecation, fix and
  end-of-life notices with a permanent, indexed archive. A retired product
  currently just stops appearing; nobody is told it ended.

As of 2026-08-02 the full planning chain for these three surfaces exists —
Spec (`spec-herald-moments-2-4`), PRD, Architecture and Epics (7 epics,
~12–19 stories, unified CLI + web dashboard + automation triggers, all three
orchestration decisions locked) — but **zero stories are implemented yet**.
This is the immediate next build target once the bridge foundation above
clears its own remaining stories.

## Kinships

[[pyforge-charter]] (charter section) · [[pyforge-marshal]] (owns the
re-scoped infrastructure and the fleet-chain regeneration machinery) ·
[[pyforge-scribe]] (the inward voice to Herald's outward) ·
[[factory-console]] (the stage Herald proclaims from).

## Realization log

- **2026-08-02 (second pass)** — Folded [[herald-pitch]] (Moment 1 complete
  orchestration, 7 capabilities) into this Dream's narrative. Dream-level
  consolidation only — `spec-herald-pitch` and its 4 companions stay fully
  live and untouched; that Spec's own PRD/Architecture/Epics decomposition
  has not run yet, unlike Moments 2–4's chain (below), which already has.
- **2026-08-02** — Consolidated. Folded [[herald-moments-2-4-missing-surface]]'s
  vision into this Dream (single narrative for Herald's voice-and-visual
  scope); that Dream is now `archived` / `absorbed` — its own downstream
  chain (Spec, PRD, Architecture, Epics under
  `_bmad-output/projects/pyforge-herald/planning-artifacts/`) stays live and
  is the active execution reference for Moments 2–4, unchanged by this
  consolidation. [[fleet-chain-completeness]] (the orchestrated-regeneration
  workflow that had been filed here) was reassigned to `owner: marshal` the
  same day — it is machinery, not Herald's communication-surface scope.
