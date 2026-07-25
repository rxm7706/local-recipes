---
title: 'Product Brief: Doctor (pyforge-doctor)'
status: complete
created: 2026-07-25
updated: 2026-07-25
inputs:
  - 'docs/dreams/pyforge-doctor.md'
  - 'docs/dreams/ecosystem-crew.md § 6 Doctor'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/research/domain-preflight-health-diagnostics-tooling-research-2026-07-25.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/research/technical-pyforge-doctor-cli-architecture-research-2026-07-25.md'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/{cli,engines}.py (--doctor exit-code + subprocess-seam precedent)'
---

# Product Brief: Doctor (pyforge-doctor)

## Executive Summary

Doctor is the pyforge Ecosystem Crew's health and diagnostics station: a single CLI
(`doctor`, package `pyforge-doctor`, module `pyforge.doctor`) that gives the factory one
bedside manner over instruments that already exist. Today, verifying the factory is
sound before a run means separately remembering to check pyforge-warden's engine
self-check; watching fleet health means separately remembering `feedstock-health`,
`staleness-report`, `behind-upstream`, `cve-watcher`, and `release-cadence` each have
their own invocation, their own output shape, and no shared vocabulary for severity.
Doctor does not replace any of these — it wraps them behind three verbs (`check`,
`monitor`, `diagnose`) so a missing engine fails fast before a build starts, fleet
drift surfaces as one pulse instead of five separate reports, and every finding ends
in an ordered, explainable prescription rather than a pile of unranked warnings.
**[ASSUMPTION]** "Why now": Doctor is the next crew station to formalize (per
`docs/dreams/ecosystem-crew.md`, alongside Scribe/Steward/Marshal/Mason), and its
consolidation targets (warden's self-check, atlas's health/watch CLIs) are already
shipped and stable — the cost of building Doctor now is almost entirely integration,
not new instrumentation.

## The Problem

The factory already produces excellent health signal — pyforge-warden's engine
self-check, cf_atlas's staleness/behind-upstream/CVE/cadence CLIs — but that signal is
scattered across tools an operator (or an agent like Marshal orchestrating a bmad-loop
run) has to know about, invoke individually, and manually reconcile. Three concrete
pains follow directly from the Dream and the domain research:

- **No pre-flight gate.** Nothing today stops a factory run from starting with a
  missing `osv-scanner` binary or a misconfigured environment — the failure surfaces
  mid-build instead of in the first five seconds, wasting the run and obscuring the
  real cause behind a downstream error. (Domain research: every comparable tool —
  `brew doctor`, `flutter doctor`, `npm doctor` — treats this exact failure mode as
  the reason the pattern exists.)
  **[ASSUMPTION]** Marshal (the bmad-loop orchestrator) is the primary machine
  consumer of this gate; the repo maintainer is the primary human consumer when
  running things by hand.
- **No fleet pulse.** An operator who wants to know "which of my feedstocks got worse
  this week" has to run `staleness-report`, `cve-watcher --since-days 7`, and an
  abandonment-signal query separately, in three different output shapes, with no
  single "here's what changed" view. (Domain research: this is exactly the gap
  Renovate's Dependency Dashboard exists to close for its own ecosystem, and exactly
  the gap cf_atlas is architecturally positioned to close natively — no third-party
  aggregator needed, unlike Renovate's own users.)
- **No prescription.** Findings across warden (KEV/EPSS-gated CVEs) and atlas
  (staleness lag, abandonment, CWE category) exist but nothing ranks them into "do
  this first, this second, this can wait" — an operator has to build that judgment
  call from scratch every time, and there's no shared, explainable ordering logic
  (technical research: Dependabot's own documented failure mode is exactly this —
  signal buried, no default ranking, operators re-deriving priority by hand).

## The Solution

Doctor wraps three existing signal sources behind one CLI and three verbs, doing
ranking and normalization work, not new scanning:

- **`doctor check --env --engines`** — pre-flight. Wraps pyforge-warden's existing
  `--doctor` self-check (engine availability/version) as a library call, and adds one
  genuinely new check category: environment/credential hygiene (first target: the
  known `JFROG_API_KEY` unconditional-injection pattern in `_http.py`, where the
  header attaches to every outbound request once the env var is set, regardless of
  host — exactly the shape of finding this check category exists to catch). Read-only,
  non-mutating, tri-state (ok/warn/fail) result per check — never a binary pass/fail,
  matching the domain convention every surveyed pre-flight tool converged on
  independently.
- **`doctor monitor --fleet --watch staleness,cve,abandonment`** — continuous pulse.
  Queries cf_atlas's existing `feedstock-health`/`staleness-report`/`behind-upstream`/
  `cve-watcher`/`release-cadence`/`adoption-stage` surfaces (CLI or MCP tool, decided at
  architecture stage) and normalizes their output into one envelope tagged by which
  instrument produced each finding — SARIF's aggregation discipline (multi-run,
  tool-tagged, schema-validated) without adopting SARIF's static-analysis-specific
  spec surface.
- **`doctor diagnose --target … --prescribe`** — root cause + ordered worklist.
  Partitions findings into actionable-now / blocked-on-upstream-fix / accepted-risk
  (never silently dropping a blocked finding), then ranks the actionable set by
  severity × exploitability (reusing warden's KEV/EPSS gates and atlas's CWE/EPSS
  overlays) with blast-radius/lag-magnitude as a tiebreaker (reusing `behind-upstream`'s
  existing major/minor/patch lag classification) — a ranking layer over data the fleet
  already has, not a new resolver.

**Exit-code framing (carried from warden's own precedent):** `doctor check` and
`doctor monitor` report *operability*, not policy — their exit code answers "is the
machine/fleet sound," mirroring warden's `--doctor` flag, which deliberately returns
only `{0, ERROR}` and never the policy-gate `1` ("doctor reports operability, not
policy"). `doctor diagnose` is a read-only report; whether its output becomes a policy
gate anywhere is a decision left to whatever consumes it (e.g., a future CI step),
not baked into Doctor's own exit code. **[ASSUMPTION]** — flagged for the PRD/
architecture stage to confirm or refine.

## What Makes This Different

Doctor's only real "moat" is that it doesn't need one: cf_atlas already has the
fleet-scale data model that comparable open-source tools (Renovate) have to hand-roll
a workaround for (a custom JSON aggregator or a third-party operator layer), and
pyforge-warden already has the exact typed subprocess-safety and exit-code discipline
Doctor needs for its own `check` verb. Building Doctor is consolidation-and-ranking
work on top of two already-shipped, already-trusted subsystems — the honest
differentiator is *integration completeness and ranking quality*, not a new detection
capability. If Doctor's prescription ranking turns out to be no better than an
operator eyeballing warden's and atlas's outputs side by side, it has not earned its
keep; the bar is genuinely higher-quality triage, not just fewer keystrokes.

## Who This Serves

- **Factory operators (human)** — the repo maintainer running the factory day to day.
  Needs: a five-second pre-flight before kicking off a recipe/feedstock run, a weekly
  "what changed" fleet glance, and a punch list when triaging a specific
  feedstock/target instead of re-deriving priority from raw CVE/staleness data by hand.
- **Agents (machine)** — Marshal (bmad-loop orchestrator) and other BMAD skills that
  currently have no formalized pre-flight gate before spinning the factory, and no
  shared vocabulary for "is this environment healthy enough to proceed." Needs: a
  stable, scriptable exit-code contract and machine-parseable (JSON) output for
  `check`/`monitor`/`diagnose`, not a human-only text report.
  **[ASSUMPTION]** Agent-consumers are read-only callers (they invoke `doctor check`
  and act on its exit code / JSON output); Doctor does not need an agent-specific API
  surface beyond a well-behaved CLI + `--json` flag family, consistent with warden's
  own CLI-first design.

## Success Criteria

- `doctor check --env --engines` becomes the pre-flight step Marshal/bmad-loop runs
  before every factory spin-up, and a missing engine or bad credential-scope config is
  caught there — not surfaced later as a confusing mid-build failure.
  **[ASSUMPTION — measurable target for PRD]**: zero mid-build failures attributable to
  an environment/engine condition `doctor check` could have caught, measured over the
  first N factory runs after adoption.
- `doctor monitor --fleet` replaces the operator's manual multi-CLI weekly-glance
  habit — i.e., it gets used in practice, not just built. **[ASSUMPTION]** self-reported/
  observed adoption is the only feasible v1 success signal for an internal single-operator
  tool; no analytics infrastructure is in scope.
  **[ASSUMPTION]** the JFROG_API_KEY-style credential-hygiene check (or its category)
  is live in `doctor check --env` by v1, since it's the one genuinely new detection
  capability and the Dream names it as a concrete worked example, not an aspiration.
- `doctor diagnose --prescribe`'s ordering is judged by the operator as *at least as
  good as* manually cross-referencing warden + atlas output for the same target —
  the ranking has to earn trust, not just exist.

## Scope

**In (v1):**
- `doctor check --env --engines`: wraps warden's `--doctor` self-check (library call,
  not a second subprocess reimplementation) + a new credential/env-hygiene check
  category (JFROG_API_KEY-shaped findings as the worked example).
- `doctor monitor --fleet --watch staleness,cve,abandonment`: normalizes cf_atlas's
  existing health/watch CLI or MCP-tool output into one tagged, schema-validated
  envelope.
- `doctor diagnose --target … --prescribe`: partition (actionable/blocked/
  accepted-risk) + rank (severity × exploitability × blast-radius) over existing
  warden + atlas signals.
- In-repo pixi build-workspace member at `src/shared/packages/pyforge-doctor/`,
  mirroring `pyforge-warden`'s `pixi.toml` `[feature.pyforge-warden.*]` pattern
  (conda + wheel/sdist build, dedicated pixi env, test task).
- JSON output mode on every verb (agent-consumer requirement).

**Out (v1 — explicitly deferred, not rejected):**
- Any auto-remediation / actuator (`doctor --fix`, opening PRs, mutating files) — v1
  is strictly read-only across all three verbs, matching every surveyed domain
  precedent (`brew doctor`, `flutter doctor`, warden's own `--doctor`).
- A persistent fleet-health surface (dashboard, committed status file, tracked issue)
  — v1 is CLI-output-only; whether `monitor --fleet` needs a Renovate-Dashboard-style
  persistent view is deferred to the PRD.
- A real dependency-graph resolver for `--prescribe` ordering (topological sort over
  actual version-pin edges) — v1 uses ranking + lag-magnitude tiebreakers only; true
  graph-ordering is flagged as a possible v1.x addition if a real multi-hop
  remediation case shows up.
- New scanning engines of any kind — Doctor never adds a new source of truth, only
  consolidates existing ones (warden, atlas). Any future new check category (beyond
  credential/env hygiene) is out of v1 scope.

## Vision

If Doctor succeeds, "run `doctor check` first" becomes as automatic a habit for this
factory as `brew doctor` is for a broken Homebrew install — the default first move
when anything looks wrong, and a silent, trusted gate the rest of the crew (Marshal
especially) runs without being asked. `doctor monitor --fleet` becomes the weekly
pulse-check that replaces manually running five separate atlas CLIs, and
`doctor diagnose --prescribe` becomes trusted enough that its ordering is followed
by default rather than second-guessed. Longer-term, as the Ecosystem Crew's other
stations (Steward for credentials/ops, Scribe for knowledge) come online, Doctor is
the natural home for cross-crew health signal — but v1 stays deliberately narrow:
prove the consolidation-and-ranking thesis on warden + atlas before widening scope.

## Open Questions (carried to PRD)

- Does `doctor check --engines` call warden's self-check as a library import or as a
  subprocess? (Technical research flags this as needing an explicit ADR given
  warden's "sole subprocess site" ownership rule.)
- Does `monitor --fleet` go through cf_atlas's MCP tool surface or its CLI layer?
- Is a persistent fleet-health surface (vs. CLI-output-only) needed for v1, or is that
  legitimately v1.x?
- Exact scope of the credential/env-hygiene check category beyond the JFROG_API_KEY
  worked example — is this a narrow one-off check or a general pattern (any
  unconditional-injection-shaped credential leak)?
- Does Doctor need its own typed finding taxonomy, or does it import warden's
  `ErrorKind`/`models.py` directly?

## Assumptions

- No market-facing sections (TAM/pricing/GTM/competitive-share) — Doctor is an
  internal developer tool with a single operator and a small set of agent-consumers,
  per the task's explicit audience framing.
- Headless/express drafting: this brief was produced without an interactive
  discovery conversation. Every `[ASSUMPTION]`-tagged claim above is an inferred
  reasonable default from the Dream, the Ecosystem Crew charter, and the two research
  reports (`domain-preflight-health-diagnostics-tooling-research-2026-07-25.md`,
  `technical-pyforge-doctor-cli-architecture-research-2026-07-25.md`) — the PRD stage
  should treat them as a starting point to confirm or revise, not as settled fact.
