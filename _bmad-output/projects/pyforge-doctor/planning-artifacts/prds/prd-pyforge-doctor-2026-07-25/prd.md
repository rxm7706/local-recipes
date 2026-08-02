---
title: Doctor (pyforge-doctor)
created: 2026-07-25
updated: 2026-08-01
status: final
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
inputs:
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/briefs/brief-pyforge-doctor-2026-07-25/brief.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/research/domain-preflight-health-diagnostics-tooling-research-2026-07-25.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/research/technical-pyforge-doctor-cli-architecture-research-2026-07-25.md'
  - 'docs/dreams/pyforge-doctor.md'
  - 'docs/dreams/ecosystem-crew.md § 6 Doctor'
---

# PRD: Doctor (pyforge-doctor)
*Working title — confirmed by the Dream and PROJECTS.md registry entry; not provisional.*

## 0. Document Purpose

This PRD is for the architecture and epics/stories stages that follow it, and for
anyone (human or agent) implementing `pyforge-doctor`. It builds on
`briefs/brief-pyforge-doctor-2026-07-25/brief.md` (problem framing, audience, scope
boundary) and the two research reports under `planning-artifacts/research/` (domain
conventions for pre-flight/health/prescribe tooling; technical patterns for facading
existing subprocess tools) — it does not re-derive those, it operationalizes them into
functional requirements. Vocabulary is Glossary-anchored (§3); FRs are globally
numbered and grouped under their feature (§4); every inferred decision is tagged
`[ASSUMPTION]` inline and indexed in §9.

## 1. Vision

Doctor gives the pyforge factory one bedside manner over health signal that already
exists but is scattered: pyforge-warden's engine-availability self-check, and
cf_atlas's feedstock-health/staleness/behind-upstream/CVE/cadence/adoption CLIs. A
single CLI (`doctor`) with three verbs replaces "remember to run five different tools
and reconcile their output by hand" with one habit: `doctor check` before anything
starts, `doctor monitor` for the weekly pulse, `doctor diagnose --prescribe` when
something specific needs triage. Doctor adds almost no new detection capability in
v1 — one new check category (credential/environment hygiene) — its value is
integration completeness and ranking quality: turning scattered, unranked signal into
one trusted, explainable worklist. If it succeeds, "run `doctor check` first" becomes
as automatic here as `brew doctor` is for a broken Homebrew install, and Marshal
(the bmad-loop orchestrator) runs it unprompted before every factory spin-up.

## 2. Target User

### 2.1 Jobs To Be Done

- **As the factory operator**, I need a five-second answer to "is my environment sound
  enough to start a run" so I don't waste a build discovering a missing engine
  mid-way.
- **As the factory operator**, I need a weekly "what changed across my feedstocks"
  glance without manually running and reconciling five separate atlas CLIs.
- **As the factory operator**, when I'm triaging a specific feedstock or CVE, I need an
  ordered "do this first" worklist instead of a pile of unranked findings I have to
  prioritize myself.
- **As Marshal (bmad-loop orchestrator, machine actor)**, I need a scriptable,
  stable-exit-code pre-flight gate I can run unattended before spinning the factory,
  and a JSON contract I can parse without a human in the loop.

### 2.2 Non-Users (v1)

- General conda-forge/staged-recipes contributors outside this repo — Doctor is
  scoped to this factory's own instruments (warden + atlas), not a general-purpose
  OSS health-check tool. `[ASSUMPTION]`
- Anyone needing auto-remediation (a `--fix` actuator) — v1 is diagnostic only,
  matching every domain precedent surveyed (`brew doctor`, `flutter doctor`, warden's
  own `--doctor`). Explicit non-goal, see §5.

### 2.3 Key User Journeys

*Lighter scope dial (single-operator internal tool, per template guidance) — one line
per journey rather than full UJ narratives.*

- **UJ-1.** The operator, about to kick off a feedstock-platform-expansion run, types
  `doctor check --env --engines`; it reports one engine missing (osv-scanner not on
  PATH) in under a second, exit code non-zero, before any build subprocess spawns.
- **UJ-2.** Marshal, orchestrating an unattended bmad-loop run, invokes
  `doctor check --json` as its first step; a clean exit 0 lets the loop proceed, a
  non-zero exit halts it with the JSON findings attached to the loop's own log.
- **UJ-3.** The operator runs `doctor monitor --fleet --watch staleness,cve,abandonment`
  on a Monday, sees one table combining what atlas's five separate CLIs would have
  shown separately, tagged by source instrument.
- **UJ-4.** The operator, staring at a feedstock with three open CVEs and a stale
  upstream version, runs `doctor diagnose --target <feedstock> --prescribe` and gets
  a three-item ordered worklist (KEV-flagged CVE first, EPSS-ranked second CVE next,
  version bump last) instead of three unranked findings.

## 3. Glossary

- **Check** — one atomic, named, individually addressable diagnostic probe (e.g. "is
  osv-scanner on PATH and version-compatible"). Result is tri-state: `ok` / `warn` /
  `fail`. Mirrors the domain convention (`brew doctor --list-checks`) and warden's own
  per-engine self-check granularity.
- **Finding** — one reported unit of Doctor output: which check/source produced it,
  its status, a human message, and structured evidence. The generalization of a
  `Check`'s result plus `monitor`/`diagnose`'s atlas-sourced signals into one shape.
- **Source** — the upstream instrument a Finding traces to (warden's `--doctor`,
  cf_atlas's `feedstock-health`, etc.). Every Finding is tagged with exactly one
  Source — the SARIF-inspired "multi-run, tool-tagged" discipline from the technical
  research.
- **Watch axis** — one of the named signal categories `monitor --fleet` can select
  independently (`staleness`, `cve`, `abandonment`, ... — extensible list). Selected
  via `--watch <axis>[,<axis>...]`.
- **Prescription** — one entry in `diagnose --prescribe`'s ordered output: a Finding
  plus a remediation action (patch/upgrade/retire/wait), a rank, and the ranking
  factors that produced that rank (never an opaque priority number — direct carry-over
  from the domain research's Dependabot-critique finding).
- **Partition** — the three-way split `diagnose --prescribe` applies before ranking:
  `actionable` (a fix exists now), `blocked` (no fix available yet — tracked, not
  dropped), `accepted-risk` (explicitly waived, out of scope for v1's waiver mechanism
  — see §5).
- **Operability exit code** — Doctor's `check`/`monitor` exit-code contract: answers
  "is the machine/fleet sound," never "did a policy gate fail." Carried directly from
  warden's `--doctor` precedent (`{0, ERROR}`, never the policy-gate `1`).

## 4. Features

### 4.1 `doctor check` — Pre-flight

**Description:** A read-only, non-mutating pre-flight scan an operator or Marshal
runs before a factory run starts. Wraps pyforge-warden's existing `--doctor`
engine-availability self-check (library call — see FR-1) and adds one new check
category, environment/credential hygiene (FR-3). Every check reports tri-state
`ok`/`warn`/`fail`, individually nameable and filterable (`--engines`, `--env`, or
both — the default with neither flag given). Realizes UJ-1, UJ-2.

**Functional Requirements:**

#### FR-1: Wrap warden's engine-availability self-check

The operator or an agent can run `doctor check --engines` and receive the same
engine-availability/version findings warden's own `--doctor` flag produces (deptry,
osv-scanner presence + minimum version), sourced via a library import of
`pyforge.warden`'s doctor-check machinery — not a second subprocess reimplementation.

**Consequences (testable):**
- `doctor check --engines` reports the identical set of engine findings `warden scan
  --doctor` would report for the same environment, byte-for-byte equivalent Finding
  content (allowing for envelope/Source-tag differences).
- No new subprocess call site is added for engine-version probing; the call routes
  through warden's existing `_check_engine_version`/`run_doctor_checks` surface.
- `[ASSUMPTION]` `pyforge-doctor` declares `pyforge-warden` as a direct dependency
  (both pixi workspace members in the same monorepo; no circular dependency since
  warden does not depend on Doctor).

**Out of Scope:** Doctor does not vendor or fork warden's engine-probe logic; if
warden's self-check surface changes shape, Doctor's FR-1 output changes with it
(single source of truth, not a second copy to drift).

#### FR-2: Individually addressable, tri-state checks

Every check `doctor check` runs (engine or env/credential) reports one of `ok` /
`warn` / `fail` — never a binary pass/fail — and is independently nameable/filterable,
mirroring `brew doctor --list-checks`' modular-check convention.

**Consequences (testable):**
- `doctor check --list` (or equivalent introspection flag) enumerates every named
  check without running them. `[ASSUMPTION]` flag name/shape deferred to architecture;
  the capability itself is not optional per the domain research's convergent finding.
- Running one named check in isolation (e.g. `doctor check --engines osv-scanner`)
  produces the same result as running the full suite and filtering to that check.
- A `warn`-status check does not, by itself, produce a non-zero exit code (only
  `fail` does) — consistent with the tri-state-not-binary model and warden's own
  "informational warnings are not proof of brokenness" convention.

#### FR-3: Environment / credential-hygiene check category (new)

`doctor check --env` includes a check for unconditional-credential-injection-shaped
configuration issues — the worked example being `JFROG_API_KEY`'s unconditional
attachment to every outbound request once set, regardless of destination host (the
known finding in `_http.py`). This is Doctor's first genuinely new (non-wrapped)
detection capability.

**Consequences (testable):**
- Given an environment where `JFROG_API_KEY` is set, `doctor check --env` reports a
  `warn` (or `fail` — architecture stage to confirm severity default) finding
  identifying the unconditional-injection risk, with evidence naming the affected
  code path.
- The check category is designed to generalize beyond the one worked example (any
  credential env var attached without host-scoping), not hard-coded to
  `JFROG_API_KEY` alone — `[ASSUMPTION]`, exact generalization boundary deferred to
  architecture (§8 open question).

**Notes:** `[NOTE FOR PM]` — this is the one FR in the PRD with no existing instrument
to wrap; it deserves the most architecture/epics scrutiny since it's genuinely new
surface, not a ranking/normalization layer over shipped code.

### 4.2 `doctor monitor` — Continuous fleet pulse

**Description:** Queries cf_atlas's existing health/watch surfaces and normalizes
their output into one envelope tagged by originating Source, selectable by named
Watch axis. Read-only. Realizes UJ-3.

**Functional Requirements:**

#### FR-4: Fleet-wide watch-axis query

The operator can run `doctor monitor --fleet --watch <axis>[,<axis>...]` where axes
include at minimum `staleness` (→ `staleness-report`), `cve` (→ `cve-watcher`), and
`abandonment` (→ composite of `feedstock-health --filter stuck/bad` +
`release-cadence`'s decelerating/silent classification), each normalized into one
tagged, schema-validated output document.

**Consequences (testable):**
- `doctor monitor --fleet --watch cve` and manually running `cve-watcher` against the
  same maintainer/scope produce the same underlying findings, re-shaped into Doctor's
  envelope with a `source: cve-watcher` tag per Finding.
- Omitting `--watch` runs a documented default axis set (not "all axes always" —
  `[ASSUMPTION]` default set deferred to architecture; likely staleness+cve as the
  two highest-signal defaults per the domain research's Dependabot-severity-first
  convention).
- Each Finding's Source tag is queryable/filterable in output — an operator can ask
  "show me only what came from `behind-upstream`."

#### FR-5: MCP-tool-first data access, CLI fallback

`monitor --fleet` queries cf_atlas via its existing MCP tool surface
(`feedstock_health`, `staleness_report`, `behind_upstream`, `cve_watcher`,
`release_cadence`, `adoption_stage`) when running in an agent/in-process context, and
falls back to the equivalent CLI subprocess when run as a standalone terminal command.
`[ASSUMPTION — resolves the brief's open question]`: MCP-first because Marshal and
other agent-consumers are expected to be Doctor's most frequent `monitor` callers, and
the MCP surface avoids a subprocess spawn in-process; the CLI fallback preserves
human-terminal usability without requiring an MCP client.

**Consequences (testable):**
- Running `doctor monitor` inside an MCP-tool-capable session and via bare CLI both
  produce the same Finding content for the same fleet scope.
- No new atlas data pipeline or direct DB connection is introduced — FR-5 is
  exclusively a consumer of already-shipped read surfaces.

**Notes:** No persistent fleet-health surface (dashboard, tracked issue, committed
status file) in v1 — CLI/JSON output only. See §5 Non-Goals.

### 4.3 `doctor diagnose --prescribe` — Root cause + ordered remediation

**Description:** Given a target (a feedstock, a CVE, or a broader scope), Doctor
gathers the relevant Findings from warden + atlas, partitions them by actionability,
and ranks the actionable partition into an ordered, explainable Prescription list.
This is Doctor's synthesis feature — no new scanning, a ranking/explanation layer over
FR-1 through FR-5's existing signal. Realizes UJ-4.

**Functional Requirements:**

#### FR-6: Partition findings by actionability

`diagnose --target <target>` partitions every gathered Finding into exactly one of
`actionable` (a fix/upgrade path exists now), `blocked` (no fix available yet — e.g.
an unfixed CVE), or `accepted-risk` (explicitly waived — v1 has no waiver-authoring
UI; this bucket exists for forward-compatibility with a future waiver mechanism and
starts empty in v1). No Finding is silently dropped.

**Consequences (testable):**
- Every Finding gathered for a target appears in exactly one partition in
  `diagnose --prescribe` output; the total Finding count across all three partitions
  equals the count gathered.
- A `blocked` Finding is visibly listed (with why it's blocked), not omitted —
  directly testable by constructing a target with a known unfixed CVE.

#### FR-7: Rank the actionable partition

Within the `actionable` partition, Prescriptions are ranked by severity × exploitability
(reusing warden's KEV/EPSS gate signals and atlas's `vuln_max_epss_score`/CWE-category
overlays) with blast-radius/lag-magnitude (reusing `behind-upstream`'s major/minor/patch
lag classification) as a tiebreaker. Each Prescription's rank is shown with the
factors that produced it — never an opaque priority number.

**Consequences (testable):**
- Given a target with one KEV-flagged CVE and one non-KEV CVE, the KEV-flagged one
  ranks first.
- Given two CVEs of equal severity where one has a higher EPSS score, the
  higher-EPSS one ranks first.
- Every Prescription's output includes a human-readable rationale line naming which
  signals fired (e.g. "KEV: yes, EPSS: 0.62, blast-radius: patch-level").
- `[ASSUMPTION]` no real dependency-graph topological ordering in v1 (only
  ranking + a lag-magnitude tiebreaker) — deferred to v1.x per the brief's scope
  boundary; flagged if a real multi-hop remediation case surfaces during
  implementation.

#### FR-8: Root-cause naming

Every Prescription names a root cause (not just a symptom) — e.g. "upstream released
a security patch you haven't picked up" rather than just "CVE-2026-XXXXX present."

**Consequences (testable):**
- A Prescription for a stale-dependency CVE finding names the staleness lag as the
  root cause, not only the CVE ID.
- `[ASSUMPTION]` root-cause naming is templated from the Source Finding's own
  structured evidence (no new NLP/inference layer) — deferred to architecture for
  the exact template mechanism.

### 4.4 Machine-Consumer Contract (cross-cutting)

**Description:** Every verb has a JSON output mode, since Marshal and other
agent-consumers are as important an audience as the human operator (per the brief's
explicit dual-audience framing). This is not a fourth verb — it is a required output
mode on FR-1 through FR-8.

**Functional Requirements:**

#### FR-9: `--json` on every verb

`doctor check`, `doctor monitor`, and `doctor diagnose` each accept a `--json` flag
producing the same information as the human-readable default, structured as one
schema-validated document (Finding/Prescription shape from §3 Glossary), suitable for
an agent to parse without scraping text output.

**Consequences (testable):**
- `--json` output validates against a committed JSON Schema for the Finding/Prescription
  envelope.
- No information present in the human-readable output is absent from `--json` output
  (parity requirement).

## 5. Non-Goals (Explicit)

- **No auto-remediation actuator in v1.** Doctor never opens PRs, patches files, or
  mutates any state — `check`/`monitor`/`diagnose` are strictly read-only, matching
  every domain precedent surveyed and warden's own `--doctor` design. A future
  `--fix`/actuator (if ever built) is explicitly out of this PRD's scope.
- **No persistent fleet-health surface (dashboard/tracked-issue/status file) in v1.**
  CLI + JSON output only; Renovate-Dashboard-style persistence is a possible v1.x
  addition, not a v1 commitment.
- **No new scanning engines or data sources.** Doctor consolidates warden + atlas; it
  does not add a third detection instrument in v1 beyond the one credential-hygiene
  check category (FR-3).
- **No real dependency-graph resolver for `--prescribe`.** Ranking + a lag-magnitude
  tiebreaker only; true topological multi-hop ordering is deferred.
- **No waiver-authoring UI for `accepted-risk`.** The partition (FR-6) exists for
  forward-compatibility; authoring/managing waivers is out of v1.
- **Not a general-purpose OSS health-check tool.** Scoped to this factory's own
  instruments and this repo's own fleet.

## 6. MVP Scope

### 6.1 In Scope

- `doctor check --env --engines` (FR-1, FR-2, FR-3) — pre-flight, tri-state, wraps
  warden's self-check, adds credential-hygiene.
- `doctor monitor --fleet --watch <axes>` (FR-4, FR-5) — fleet pulse over cf_atlas,
  MCP-first with CLI fallback.
- `doctor diagnose --target … --prescribe` (FR-6, FR-7, FR-8) — partition + rank +
  root-cause naming over existing warden/atlas signal.
- `--json` on all three verbs (FR-9).
- In-repo pixi build-workspace member at `src/shared/packages/pyforge-doctor/`,
  mirroring `pyforge-warden`'s `pixi.toml` `[feature.pyforge-warden.*]` pattern (conda
  + wheel/sdist build, dedicated pixi env, test task).

### 6.2 Out of Scope for MVP

- Auto-remediation / `--fix` actuator — see §5.
- Persistent fleet-health surface — see §5. `[NOTE FOR PM]`: revisit if operator
  adoption of `monitor --fleet` in v1 shows the CLI-only glance isn't sticky.
- Real dependency-graph topological resolver — see §5.
- Waiver-authoring UI — see §5.
- New scanning engines beyond credential/env hygiene — see §5.
- Cross-crew integration (Steward for credentials/ops, Scribe for knowledge) —
  Vision-level only, not v1 scope; Doctor stays narrow to warden+atlas until the
  consolidation thesis is proven.

## 7. Success Metrics

**Primary**
- **SM-1**: Zero mid-build failures attributable to an environment/engine condition
  `doctor check` could have caught, measured across factory runs after adoption.
  Validates FR-1, FR-2, FR-3.
- **SM-2**: `doctor diagnose --prescribe`'s ranking is judged by the operator as at
  least as good as manually cross-referencing warden + atlas output for the same
  target (qualitative, self-assessed — no analytics infrastructure for an internal
  single-operator tool). Validates FR-6, FR-7, FR-8.

**Secondary**
- **SM-3**: `doctor monitor --fleet` replaces the operator's manual multi-CLI weekly
  habit in observed practice (used, not just built). Validates FR-4, FR-5.
- **SM-4**: The credential/env-hygiene check (FR-3) is live and catches at least the
  one named worked example (`JFROG_API_KEY` unconditional injection) by v1 ship —
  the Dream names it as a concrete deliverable, not an aspiration.

**Counter-metrics (do not optimize)**
- **SM-C1**: Check-suite runtime does not creep upward in pursuit of more findings —
  `doctor check`'s five-second pre-flight promise (UJ-1) is load-bearing; a
  comprehensive-but-slow check suite defeats the "fails fast" purpose. Counterbalances
  SM-1 and FR-3 (don't over-scope the credential-hygiene check category at the cost
  of pre-flight speed).
- **SM-C2**: Prescription ranking is not optimized for "produces the longest list" —
  a shorter, correctly-partitioned worklist (few actionable items, rest correctly
  bucketed blocked/accepted-risk) is the goal, not exhaustiveness. Counterbalances
  SM-2.

## 8. Open Questions

1. Exact severity default (`warn` vs `fail`) for the credential-hygiene check (FR-3)
   when a risky pattern like `JFROG_API_KEY` unconditional injection is detected.
2. Exact generalization boundary for the credential-hygiene check category beyond the
   one worked example — is it host-scoping-of-secrets in general, or narrower?
3. Default Watch-axis set when `--watch` is omitted from `doctor monitor --fleet`
   (leaning staleness+cve per Dependabot's severity-first convention, not confirmed).
4. Exact `--json` schema versioning policy — does Doctor's JSON envelope need its own
   schema-version field from day one (matching warden's `ComplianceReport` precedent)?
5. Does Doctor need its own typed Finding taxonomy module structurally mirroring
   warden's `ErrorKind`, or can architecture find a lighter-weight shared shape?
6. Whether `doctor check --list` (check introspection) ships in v1 or is a fast-follow
   — the domain research treats it as a near-universal convention but it's not named
   in the Dream's CLI cadence examples.

## 9. Assumptions Index

- §1/Brief carry-over — Doctor adds no new detection capability beyond credential
  hygiene in v1; value is integration + ranking quality.
- §4.1 FR-1 — `pyforge-doctor` depends directly on `pyforge-warden` (both pixi
  workspace members, no circular dependency).
- §4.1 FR-2 — check-introspection flag shape (`--list` or equivalent) deferred to
  architecture; capability itself not optional.
- §4.1 FR-3 — credential-hygiene check generalizes beyond the one worked example;
  exact boundary deferred (Open Question 2).
- §4.2 FR-4 — default Watch-axis set when `--watch` omitted (Open Question 3).
- §4.2 FR-5 — MCP-tool-first / CLI-fallback data-access resolution for `monitor
  --fleet` (resolves the brief's open question).
- §4.3 FR-7 — no real dependency-graph resolver in v1; ranking + lag-magnitude
  tiebreaker only.
- §4.3 FR-8 — root-cause naming is templated from existing Source Finding evidence,
  no new NLP/inference layer.
- §7 SM-2/SM-3 — qualitative/observed-adoption success signals only; no analytics
  infrastructure in scope for a single-operator internal tool.
