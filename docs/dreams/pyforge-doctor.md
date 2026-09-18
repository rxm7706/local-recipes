---
title: Doctor — one bedside manner for the whole fleet
type: dream
owner: doctor
status: specified
---

# Doctor — check the vitals, keep the ecosystem alive

## The Dream

The Physician's dream: **a factory is only as autonomous as its health checks.**
Before any run, verify the machinery is sound — a missing engine or broken
config fails fast, never mid-build. After anything ships, keep a finger on the
fleet's pulse: staleness, new advisories, upstream abandonment — surfaced as
signals, not surprises. And never stop at a finding: every diagnosis names its
root cause and ships an **ordered prescription** — what to patch, upgrade, or
retire, in what order. Over time, the fleet's overall condition should be
readable at a glance, not reconstructed by hand from five CLIs.

## What it looks like when real, today (v1)

- `doctor check --env --engines` — pre-flight before Marshal spins the factory.
- `doctor monitor --fleet --watch staleness,cve` — the continuous pulse (default
  two highest-signal axes; more addable per invocation).
- `doctor diagnose --target … --prescribe` — partitioned, ranked findings with a
  named root cause for each.
- `--json` on every verb, one schema-versioned `DoctorReport` envelope.

## Why this is a consolidation, not an invention

The instruments already beat inside the factory — Doctor is one bedside manner
over all of them, not a new detection engine:

- **warden · self-check**: the engine-availability doctor check, wrapped as a
  library import (never a subprocess reimplementation).
- **atlas · health & watch**: `feedstock-health`, `staleness-report`,
  `behind-upstream`, `cve-watcher`, `release-cadence` — MCP-first with CLI
  fallback.
- **The one genuinely new instrument**: a credential/environment-hygiene check
  (the `JFROG_API_KEY` unconditional-injection pattern is exactly a Doctor
  finding) — deliberately the *only* new detection capability v1 adds, not a
  precedent for adding others without a matching decision.

## The frontier — named, not yet built

Four capabilities sit outside v1's boundary on purpose — the PRD's own
non-goals name them as "a possible v1.x addition, not a v1 commitment" rather
than rejecting them outright. Real, wanted, deliberately sequenced after the
walking skeleton proves itself:

1. **Health scoring** — a composite grade (A–F) synthesizing Doctor's own
   already-gathered findings across axes (age, staleness, CVE exposure,
   abandonment signal). Not a new scanning engine — a new aggregation layer
   over data Doctor already collects, so it doesn't reopen the "no new
   instruments" boundary v1 draws.
2. **A persistent fleet-health surface** — today's `monitor --fleet` is a
   point-in-time CLI/JSON snapshot; a tracked, at-a-glance view of the whole
   fleet's condition is the natural next step once the snapshot format has
   proven itself in practice.
3. **An adoption-tracking axis** — cf_atlas's `adoption-stage` and
   `version-downloads` signals are named as candidate sources in this Dream's
   own original draft but never made it into `monitor --fleet`'s wired axis
   set. Real, cited, unbuilt.
4. **Safe upgrade-path recommendation** — `--prescribe` ranks and names a root
   cause today, but stops short of naming a target version. A narrow,
   single-hop "here is the next safe version" suggestion (not a full
   transitive dependency-graph resolver — that stays explicitly out of scope)
   is the natural extension once ranking is trusted.

## Why this is different from a fabricated dream

An earlier, separate dream (`pyforge-doctor-dependency-health.md`, created
2026-08-02) proposed most of this same frontier, but inside a bulk commit
later found to contain fabricated content elsewhere (a false migration note,
boilerplate test-architecture docs invented for six stations). Its four
genuinely new items — health scoring, the persistent dashboard, adoption
tracking, and upgrade-path recommendation — survived verification against
Doctor's real, already-authored PRD and are captured above, in Doctor's own
voice and grounded in Doctor's own existing constraints (never a new scanning
engine, never a real graph resolver). The other two-thirds of that dream —
"multi-axis A–F scoring... validated against 1000+ real packages," "95%+
obsolescence catch rate," "80%+ operator acceptance" — were invented precision
with no grounding anywhere in this project's real work, and do not carry
forward. That dream is archived; this one is the real record.

## Realization log

- **2026-09-18 (later)** — **Proposed: a PR is judged at its merge-base, and a
  merge subject is attributed to the station it names.** Twice today Doctor's
  merge-history sources reported a regression that was not one. (1) `ledger-
  regression` ran on herald PR #1465's `detectors` lane at 18:17Z — two minutes
  *after* `marshal factory dispatch` had merged the PR unattended and promoted
  `23-6 → done` on `main` — and compared `origin/main..HEAD`: the PR head still
  said `backlog`, main now said `done`, so the blocking step reported
  `done-key-regressed: pyforge-herald: 1 story key(s) moved out of done` and
  redded the lane on a PR whose branch never touched that row. The question a
  PR check must answer is "what does this branch change?", which is the ledger
  at `merge-base(origin/main, HEAD)` vs `HEAD` — the tip of `main` is the wrong
  base whenever main moves first, and under unattended landing it always moves
  first. (2) `ledger-direction` has reported `pyforge-atlas/13-5`, `14-4` and
  `15-3` as *landed-but-unpromoted* all day: `sources/marshal.py:87` hardcodes
  `_MERGE_SUBJECT_TEMPLATE = "Merge {key} into main"`, so another station's
  `Merge 13-5 into main` reads as atlas's 13.5 landed — the same un-scoped
  templated shape marshal's own supervisor tripped on this morning (herald
  23.x via atlas's `Merge 23-N into main`; marshal is closing its side as
  `spec-pyforge-marshal:CAP-247` and station policies now render
  `Merge <slug>/{key} into main`). Doctor's sources must read each station's
  own `merge_subject_template` from its `marshal-policy.toml` — a TOML read,
  never a marshal import — and accept only a subject whose slug is that
  station's. Seeded as CAP-78, decomposed the same day as Epic 27 / Story 27.1;
  advisory posture unchanged, and `ledger-regression` stays the one blocking
  Doctor step in CI (ruling 2026-09-14) — this makes its verdict true, not softer.
- **2026-09-18** — **Proposed: the map of what no agent can verify without a
  live proof.** Bugs cluster where agents cannot see them — not because the
  code is hard, but because verifying it correct needs a real round-trip
  against something outside the repo (a third-party API, a live browser, a
  service with its own auth and its own drift), and a dev pass's own
  self-report is never evidence of that, only a live proof is. This fleet
  already has several such surfaces, each documented only in its own
  station's prose, nowhere aggregated: herald's Claude Design MCP bridge (a
  push isn't proven until read back through the live serve URL, harness
  stripped, byte-compared), herald's live webhook host (opt-in only,
  `HERALD_LIVE_WEBHOOK=1`, never in the default gate), scribe's
  Postgres+pgvector cluster (`scribe-pg-up` first), atlas's
  Chromium/DuckDB/WASM pipeline, warden's live OSV-scanner/CISA-KEV/EPSS
  feeds. Every one already has a real, working live-proof mechanism; what's
  missing is one place that says *these exist, here's how to actually prove
  them, and a dev pass's own confidence is not enough evidence on its own.*
  Motivating incident, same session: herald's mcp SDK transport broke across
  two separate 2.x changes (`streamablehttp_client` renamed with a different
  call signature; `CallToolResult.isError` renamed to `.is_error`), caught
  by neither review nor the test suite nor a dev pass's self-report — only a
  real live push-then-read-back against Claude Design surfaced it. Shape:
  one doctor-owned, fleet-wide inventory of these surfaces (station, surface,
  what a static pass cannot see, how to prove it live, roughly how
  expensive); a story/PR touching one gets an advisory finding naming it,
  never gating, matching Doctor's own posture. Not yet a CAP or an Epic —
  recorded here as the seed; decomposition follows if greenlit.

- **2026-08-08** — **Doctor took the verdict on the Marshal's own row.** Charter §6
  has said since 2026-07-28 that the Doctor holds it, *"the one station that would
  otherwise grade itself"* — but nothing implemented it. A single `sprint-ledger-sync`
  run then destroyed 96 `done` markers across four stations and printed success, and
  all three guards written in response lived in Marshal's own surface. Doctor gained a
  ninth Source (`marshal-durability`), CAP-9, FR-14, AD-11/AD-12 and Epic 5. The
  design point worth remembering: unlike the warden source, this one **imports no
  station package** — a durability verdict assembled from the judged station's own
  code would fail exactly when that station's machinery is what broke.

- **2026-07-23** — persona defined in [[pyforge-charter]]; chapter deck seeded
  (`presentations/pyforge-doctor/`).
- **2026-07-25** — full planning chain landed: Spec (CAP-1..CAP-4), PRD
  (FR-1..FR-9), Architecture (AD-1..AD-7), Epics (3 epics, 12 stories).
- **2026-08-02** — Epic 1 shipped (5/5 stories: package scaffold, warden
  engine-check wrap, tri-state checks, credential/env-hygiene check, CLI
  wiring). Epics 2 (Fleet Pulse) and 3 (Diagnose & Prescribe) remain pending,
  7 stories. Dream consolidated same day: the fabricated `dependency-health`
  dream retired, its real remainder (four frontier items above) captured here
  and decomposed into a genuine Epic 4 (CAP-5..CAP-8, FR-10..FR-13) rather
  than left as an unlinked aspiration.

## Fold — one chain (2026-09-17)

Doctor rebases to one Dream, one Spec, one PRD, one spine, one epic chain. Folded topic Dreams are archived in place with `Consolidated into [[pyforge-doctor]]` banners. Absorbed Spec folders keep pointer + memlog + companions.

Folded Dreams: [[bmad-drift-new-artifact-shape]], [[bmad-method-version-drift]], [[capability-effect-check]], [[chain-currency-sweep]], [[deferred-work-audit-completeness]], [[deferred-work-resolution-sweep]], [[deferred-work-visibility]], [[docs-shelf-alignment]], [[fleet-hygiene-verification-exemplar-program]], [[general-docs-consistency]], [[pixi-candidate-currency]], [[pyforge-doctor-dependency-health]], [[sibling-dreams-drift]], [[status-body-consistency]].
