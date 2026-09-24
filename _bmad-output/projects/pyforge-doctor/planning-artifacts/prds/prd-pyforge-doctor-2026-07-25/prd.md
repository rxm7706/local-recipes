---
title: Doctor (pyforge-doctor)
created: 2026-07-25
updated: '2026-09-24'   # RE-STAMPED 2026-09-24: chain-currency sweep (doctor Story 30.3 landing, spec-pyforge-doctor CAP-84 realized in full — the .memlog''s 2026-09-24 entry moved spec ahead of this PRD past the 2-day feeds grace window); § Currency reconciliation — 2026-09-24 appended. Prior 2026-09-20
status: final
currency_review: 'Reviewed 2026-09-24 — chain-currency sweep (doctor Story 30.3 landing).
  Story 30.2 (docs/map.yaml + the three docs-currency checks, hand-landed ''Merge
  pyforge-doctor/30-2 into main'', e2105fec02d, 2026-09-20) and now Story 30.3 (the
  five reference-page generators — docs-pixi-tasks, docs-environments, docs-detectors,
  docs-skills-catalog, docs-station-cli — plus docs_currency.py''s generated-page-stale
  check) complete CAP-84 in full; FR-17''s two capabilities (CAP-83, CAP-84) are both
  delivered. spec-pyforge-doctor''s .memlog moved to 2026-09-24T06:55 (Story 30.3''s
  surface gains) while this PRD sat at 2026-09-20, tripping the spec→prd feeds check;
  reconciled in the appended § Currency reconciliation — 2026-09-24. No FR/content
  change required beyond marking FR-17''s decomposition current. Prior: Reviewed
  2026-09-19 — chain-currency sweep after PR #1529 (doctor Story
  30.1). research/documentation-currency-and-repeatable-refresh-2026-09-19.md post-dated the
  brief; spec-pyforge-doctor minted CAP-83/CAP-84 (docs currency, Epic 30). FR-17 minted
  below to cite them; reconciled in the appended § Currency reconciliation — 2026-09-19.
  Prior: Reviewed 2026-09-17 — one-chain doctor fold reminted spec-pyforge-doctor
  CAP-1..76. Kernel FR-1..13 cite CAP-1..13 (original station CAPs, same numbers).
  Absorbed CAPs were already decomposed as Epics 5–25 on their own Specs — remint
  is provenance, not a new FR set. FR delta: citations only. Reviewed 2026-09-14 —
  chain-currency sweep. spec-pyforge-doctor''s SPEC.md moved to 2026-09-12 (surface-drift-exclude
  block; eight dated `verified:` CAP lines from the 2026-09-11 mechanical sweep, all
  PASS; three new Assumptions bullets) and its .memlog to 2026-09-14T05:18 (six surface-reconcile
  entries: the new capability_ledger.py source, the PR #1354 snapshot-test re-measure,
  board.py''s INV-A delivered-Spec branch and INV-B epic arm, and marshal Epic 42''s
  incoming surface claim) while this PRD sat at 2026-09-07; reconciled in the appended
  § Currency reconciliation — 2026-09-14. No FR/content change required. Prior: Reviewed
  2026-09-07 — chain-currency sweep (marshal Story 31.1). Three specs'' .memlog moved
  to 2026-09-07 (cross-station surface-reconcile for factory.py/hygiene_definitions.py''s
  new TEA test-design classification rules) after this PRD sat at 2026-09-04; reconciled
  in the appended § Currency reconciliation — 2026-09-07. No FR/content change required.
  Prior: Reviewed 2026-09-04 — chain-currency sweep (PR #1043). spec-pyforge-doctor''s
  .memlog moved to 2026-09-03T20:35 (fleet-hygiene surface restamp, no new product
  work) after four 2026-08-30..09-01 detector bug-fix / classifier-rule entries against
  already-described FR-14/FR-15 infrastructure and the Story 19.1 entry (Epic 19,
  above this PRD''s FR ceiling; bound to steward spec-bmad-suite-metapackage CAP-1);
  reconciled in the appended § Currency reconciliation — 2026-09-04. No FR/content
  change required. Prior: Reviewed 2026-08-29 — chain-currency sweep. spec-pyforge-doctor''s
  .memlog moved to 2026-08-29T02:15 (five bookkeeping RECONCILES entries: two detector
  bug-fixes, one classifier-rule addition, one DEFERRED_SPECS registration note, all
  against already-described FR-14/FR-15 detector infrastructure — no new capability)
  while this PRD sat at 2026-08-26; reconciled in the appended § Currency reconciliation
  — 2026-08-29 (detector bug-fix attribution, spec-chain-currency-sweep''s own DEFERRED_SPECS
  registration). No FR/content change required. Prior: Reviewed 2026-08-26 — chain-currency
  sweep. SPEC-doctor (status shipped, CAP-1..9) and its .memlog had moved through
  2026-08-22 while this PRD sat at 2026-08-02; reconciled in the appended § Currency
  reconciliation — 2026-08-26 (open-questions dispositions, FR inventory boundary
  vs. the decompose-directly Spec convention, Canopy/operating-model obligations,
  Unifying Strategy roles). FR-14/FR-15 sections below were added 2026-08-08 without
  a frontmatter bump at the time — this stamp also covers them. Prior: Reviewed 2026-08-02
  — dream-consolidation pass added §4.5 (FR-10..13, the frontier decomposed from the
  fresh docs/dreams/pyforge-doctor.md, replacing the retired pyforge-doctor-dependency-health.md).
  §5/§6.2 updated to mark the persistent-fleet-health-surface non-goal as graduated
  (FR-11), not reopened wholesale.'
inputs:
- _bmad-output/projects/pyforge-doctor/planning-artifacts/briefs/brief-pyforge-doctor-2026-07-25/brief.md
- _bmad-output/projects/pyforge-doctor/planning-artifacts/research/domain-preflight-health-diagnostics-tooling-research-2026-07-25.md
- _bmad-output/projects/pyforge-doctor/planning-artifacts/research/technical-pyforge-doctor-cli-architecture-research-2026-07-25.md
- docs/dreams/pyforge-doctor.md
- docs/dreams/ecosystem-crew.md § 6 Doctor
fr-derivation-from: '2026-09-19'
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

#### FR-1: Wrap warden's engine-availability self-check ← CAP-1

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

#### FR-2: Individually addressable, tri-state checks ← CAP-1

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

#### FR-3: Environment / credential-hygiene check category (new) ← CAP-1

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

#### FR-4: Fleet-wide watch-axis query ← CAP-2

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

#### FR-5: MCP-tool-first data access, CLI fallback ← CAP-2

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

#### FR-6: Partition findings by actionability ← CAP-3

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

#### FR-7: Rank the actionable partition ← CAP-3

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

#### FR-8: Root-cause naming ← CAP-3

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

#### FR-9: `--json` on every verb ← CAP-4

`doctor check`, `doctor monitor`, and `doctor diagnose` each accept a `--json` flag
producing the same information as the human-readable default, structured as one
schema-validated document (Finding/Prescription shape from §3 Glossary), suitable for
an agent to parse without scraping text output.

**Consequences (testable):**
- `--json` output validates against a committed JSON Schema for the Finding/Prescription
  envelope.
- No information present in the human-readable output is absent from `--json` output
  (parity requirement).

### 4.5 The frontier, decomposed (v1.x — added 2026-08-02)

**Description:** Four capabilities this PRD's own §5/§6.2 already named as candidate
v1.x additions ("a possible v1.x addition, not a v1 commitment"), decomposed for real
following the dream-consolidation pass. None reopen the "no new scanning engine" or
"no real dependency-graph resolver" boundaries §5 draws — each is a synthesis or
wiring layer over data Doctor already gathers, or a source that already exists
elsewhere in the factory. Sequenced after Epics 1-3 (v1's walking skeleton) ship and
prove themselves, not concurrent with them.

**Functional Requirements:**

#### FR-10: Health scoring ← CAP-5

An operator can see a composite health grade (A–F) per dependency, synthesized from
Doctor's own already-gathered Finding data across axes (age/staleness, CVE exposure,
abandonment signal) — an aggregation layer over CAP-1..3's existing output, not a
fourth scanning instrument.

**Consequences (testable):**
- The grade is a pure function over an already-gathered `list[Finding]` — no new
  subprocess/MCP call of its own (same discipline FR-7's `--prescribe` already holds).
- The same Finding set always produces the same grade (deterministic, no
  timestamp-in-logic-path, mirroring NFR-1's read-only/pure-function precedent).
- An incomplete axis gather degrades the grade to explicitly `incomplete`, never a
  false `A` — a grade must never overstate confidence it does not have.

#### FR-11: Persistent fleet-health surface ← CAP-6

An operator can see the fleet's health condition as a tracked, at-a-glance surface
instead of reconstructing it from a point-in-time `monitor --fleet` snapshot — the
graduation §6.2's `[NOTE FOR PM]` already flagged as worth revisiting.

**Consequences (testable):**
- The surface is strictly derived output written from a `monitor --fleet` run (FR-4's
  existing Finding/Source shape) — never a second, independent gather path.
- Regenerating the surface from the same underlying findings is idempotent.
- The surface's own schema is versioned the same way `DoctorReport` is (FR-9's
  `schema_version` precedent) so a consumer can detect a format change.

#### FR-12: Adoption-tracking watch axis ← CAP-7

An operator can add `adoption` to `monitor --fleet`'s `--watch` set and get
cf_atlas's `adoption-stage` and `version-downloads` signals — named as candidate
sources in Doctor's own original Dream but never wired in — normalized into the same
Finding shape as the existing staleness/cve/abandonment axes.

**Consequences (testable):**
- Follows FR-5's MCP-first/CLI-fallback pattern exactly; both paths normalize to the
  identical Finding shape.
- `adoption` is **not** added to the default `--watch` set (FR-4's default stays
  `staleness`+`cve` unless explicitly widened) — additive, not a default-behavior
  change.
- A new `Source` enum member is added for it (FR-2's closed-taxonomy convention
  extended, never an open/stringly-typed source).

#### FR-13: Safe upgrade-path recommendation ← CAP-8

A Prescription from `diagnose --prescribe` can name a specific next-safe-version
target, not just rank and explain — the narrow slice of "Version Intelligence" that
survives verification, explicitly not the real dependency-graph resolver §5 excludes.

**Consequences (testable):**
- The recommendation is single-hop only — this package's own next safe version,
  sourced from atlas's existing `behind-upstream`/version data — never a transitive
  multi-package resolution.
- A Prescription with no confidently-known safe version states that plainly rather
  than guessing one.
- `--prescribe` stays a pure function over already-gathered data (FR-7's existing
  discipline preserved — no new subprocess/MCP call added to `prescribe` itself).

## 5. Non-Goals (Explicit)

- **No auto-remediation actuator in v1.** Doctor never opens PRs, patches files, or
  mutates any state — `check`/`monitor`/`diagnose` are strictly read-only, matching
  every domain precedent surveyed and warden's own `--doctor` design. A future
  `--fix`/actuator (if ever built) is explicitly out of this PRD's scope.
- **No persistent fleet-health surface (dashboard/tracked-issue/status file) in v1.**
  CLI + JSON output only. *(Graduated 2026-08-02: this is now FR-11, decomposed as a
  v1.x addition strictly derived from `monitor --fleet`'s existing output — not a
  reopening of "v1 is CLI+JSON only," a scheduled extension of it.)*
- **No new scanning engines or data sources beyond the one credential-hygiene check
  category (FR-3).** Doctor consolidates warden + atlas; it does not add a third
  detection *instrument*. FR-10 (health scoring) and FR-12 (adoption-tracking) do not
  cross this line — FR-10 aggregates Doctor's own already-gathered findings, and
  FR-12 wires an *existing* atlas source into the axis set, not a new one.
- **No real dependency-graph resolver for `--prescribe`.** Ranking + a lag-magnitude
  tiebreaker only; true topological multi-hop ordering is deferred. FR-13's
  upgrade-path recommendation is explicitly bounded to single-hop, this-package-only
  — it does not cross into resolver territory.
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
- Real dependency-graph topological resolver — see §5. (FR-13's single-hop
  recommendation does not cross this line.)
- Waiver-authoring UI — see §5.
- New scanning engines/instruments beyond credential/env hygiene — see §5. (FR-10 and
  FR-12 do not cross this line — see §5's updated non-goal text.)
- Cross-crew integration (Steward for credentials/ops, Scribe for knowledge) —
  Vision-level only, not v1 scope; Doctor stays narrow to warden+atlas until the
  consolidation thesis is proven.

### 6.3 In Scope for v1.x (added 2026-08-02, sequenced after §6.1 ships)

- Health scoring (FR-10) — composite A–F grade over already-gathered findings.
- Persistent fleet-health surface (FR-11) — the `[NOTE FOR PM]` graduation from the
  original §6.2, now decomposed for real.
- Adoption-tracking watch axis (FR-12) — wires cf_atlas's existing `adoption-stage`/
  `version-downloads` sources into `monitor --fleet`.
- Safe upgrade-path recommendation (FR-13) — single-hop only, bounded per §5.

Not concurrent with §6.1 — sequenced after Epic 1-3's walking skeleton ships and
proves itself, per the Spec's own Assumptions.

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

## FR-14 — Verdict on the Marshal's durability (Charter §6)

Doctor reports whether every tracked sprint ledger still holds the completions it
held at HEAD.

**Consequences (testable):**
- A ledger whose working state un-finishes a story yields a `FAIL` Finding naming the
  project, the count and the keys, plus a `git checkout HEAD -- <path>` remedy.
- No regression yields one `OK` Finding stating how many ledgers were checked.
- Missing ledgers, absent git, or an unreadable file yield `WARN` — never `OK`, never
  an exception.
- **`sources/marshal.py` imports no `pyforge.<station>` package.** Enforced by
  `test_sources_marshal_independence.py`, so the judged station cannot alter the
  judgement. This is the FR's load-bearing half: the finding is worth nothing if
  Marshal can change what counts as passing.

*Grounding: on 2026-08-08 one `sprint-ledger-sync` run destroyed 96 `done` markers
across four stations and reported success. All three guards written in response live
in Marshal's own surface, which §6 forbids as sufficient.*

## FR-15 — Doctor holds the verdict for every conformance detector (Charter §6, generalized)

Added 2026-08-08 (operator decision). FR-14 applied §6 to exactly one artifact — the
sprint ledger. A detector-ownership audit the same day found the clause is violated
fleet-wide: of **13** repo-level detectors, **10 judge an artifact another station
produces**, and none of those 10 belongs to Doctor.

Doctor becomes the home for every detector whose subject is another station's artifact.
The producing station keeps its **pre-write operational guards**; it loses only the
authority to be the final word on itself.

**Consequences (testable):**
- The 10 judging detectors resolve as Doctor sources: `ledger_regression`,
  `story_status`, `chain_completeness`, `dashboard_drift`, `check_layout`,
  `dream_chain`, `spec_surface`, `forward_dependency`, `deferred_work`, `bmad_drift`.
- `loop_stall` and `unpushed_work` stay Marshal's — operational watchdogs over live
  runs, not conformance verdicts on an artifact. `llms_full` stays Steward's (its own
  platform catalog; no §6 conflict).
- **No Doctor source imports the station it judges** — the `sources/marshal.py` rule,
  generalized and meta-tested across every source. `sources/warden.py` remains the
  deliberate exception: it relays an instrument's self-report about its own
  environment, which is a different act from judging an artifact.
- Every detector resolves to exactly one owning station, and a newly added detector
  with no owner is a finding rather than a silent exemption.
- `doctor check` remains inside **SM-C1 (5.0s)** after the additions — measured, not
  assumed.

**Non-goals:** Marshal's pre-write guards are not removed. `promote_sprint_status.py`
keeps refusing regressions; `--project` scoping stays. Two layers, not a transfer.

*Grounding: measured 2026-08-08. `scripts/spec_surface_allowlist.txt` carried a blanket
`scripts/**` exemption whose stated reason named 2 detectors; the directory had grown to
12, and the glob silently absorbed 20 tracked files including 6 detectors and the
registry itself, emitting no finding. Doctor's `sources/marshal.py` — the fleet's only
§6-compliant verdict — is not wired to any verb (Story 5.2, backlog), so an operator
cannot currently reach it.*

## FR-17 — The documentation is right, and refreshing it is repeatable (spec-pyforge-doctor CAP-83, CAP-84)

Added 2026-09-19 (operator rulings recorded in
`research/documentation-currency-and-repeatable-refresh-2026-09-19.md` §4). The repository's
human documentation — the Diátaxis shelf under `docs/{tutorials,how-to,reference,explanation}`
mapped by `docs/MAP.md` — is an artifact every station writes into and none owns, so under
FR-15 its currency verdict is Doctor's. Two capabilities:

- **CAP-83 — the map is enforced within its scope.** A `docs-map-hygiene` source judges the
  four quadrants only: a page the MAP links but the tree lacks is a `fail`; a quadrant page the
  MAP does not link is a `warn` (warn-first, the CAP-62 posture); quadrant `README.md` indexes
  are exempt; everything the MAP's § *Outside this map* names (governance files, intake
  specs, dashboards, `docs/foundry/`, station READMEs, skill directories) is out of scope by
  construction. Nothing is authored under `.claude/skills/` — the BMAD installer owns that tree.
- **CAP-84 — refresh is repeatable.** `docs/map.yaml` is the machine twin of `docs/MAP.md`
  (every page: `kind` generated|authored|pointer, owner, `sources`, `derived_at` + tree
  stamps); `docs/MAP.md` renders from it; generated reference pages (pixi tasks, station CLIs,
  detector catalog, skills catalog, environments) are produced by generators from the code and
  manifests — never hand-edited — and a `docs-currency` source flags a generated page whose
  stamp is older than its sources, and an authored page whose `sources:` moved since
  `verified:`. Authored pages are re-verified through `bmad-os-docs-audit → bmad-os-diataxis`.

**Consequences (testable):** `docs-map-hygiene` is in the `detectors` and `detectors-ci`
registry with the `warn`/`fail` split above and reports OK on `main` after Story 30.1;
`docs/map.yaml` round-trips to the committed `docs/MAP.md` byte-for-byte once Story 30.2
lands; every generated page carries a stamp a generator can compare; `doctor check` stays
inside SM-C1 (5.0s) — measured.

**Non-goals:** no docs PR gate (findings stay advisory or Warden inputs, Charter §6); no
prose-quality judgement — currency is about facts the code can refute, not style; the
legacy `docs/specs/` intake tier, `docs/dreams/`, and `_bmad-output/` are not on the shelf.

*Decomposed as Epic 30 — Stories 30.1 (done, PR #1529), 30.2 (done, hand-landed
`Merge pyforge-doctor/30-2 into main`, e2105fec02d), 30.3 (done). Epic 30 complete.*

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

## Currency reconciliation — 2026-08-26

*Chain-currency sweep (CHAIN-CURRENCY-RUNBOOK.md): `specs/spec-pyforge-doctor/`
(SPEC status `shipped`, CAP-1..9; its `.memlog` last moved 2026-08-22) had out-dated
this PRD's 2026-08-02 stamp. Reconciled against the SPEC, the 2026-08-08 research
refresh wave, the as-built package, and the Unifying Strategy. The body above is the
contract of record for FR-1..15; this section records what reality did to it.*

**Delivery state.** All of §6.1 (FR-1..9) and §6.3 (FR-10..13) shipped — 16 stories,
Epics 1–4, merged via PRs #156/#162/#167/#290/#299/#303, retro'd 2026-08-08. FR-14 and
FR-15 (added 2026-08-08, below §8) shipped as Epics 5–6: the marshal-durability source,
the source registry, and the re-homing of the 10 judging detectors as Doctor sources
behind the `python -m pyforge.doctor.sources` dispatcher (14 addressable sources as of
2026-08-26), each structurally barred from importing the station it judges. The
`sources/marshal.py` gap FR-15's grounding named ("not wired to any verb") closed via
Story 5.2. The tracked ledger reports **82/82 stories done across Epics 1–18** as of
this stamp.

**FR-inventory boundary — the decompose-directly convention.** FR-1..15 (plus FR-16,
the spike-report classifier, minted 2026-08-11 at epics level, and FR-17, docs
currency, minted 2026-09-19) is the complete FR set
this PRD owns, but it is deliberately **not** the complete story universe: Epics 7–16
decompose sibling doctor Specs directly (spec-deferred-work-visibility,
spec-deferred-work-resolution-sweep, spec-fleet-hygiene-verification-exemplar-program,
spec-bmad-method-version-drift, spec-backlog-intake-check, spec-sibling-dreams-drift),
referencing their CAP-Ns without minting new PRD FR-Ns — the precedent `epics.md`'s own
currency_review records. Read this PRD's FR list as the v1 + Charter-§6 contract, not
as an index of everything Doctor now does.

**§8 Open Questions — dispositions (per the 2026-08-08 research refresh + shipped code):**

1. *Severity default for credential-hygiene findings* — resolved in practice by
   per-finding tri-state semantics inside `checks/env_hygiene.py` rather than a
   category-wide default; the SPEC still carries the residual `warn_or_fail` wording.
2. *Generalization boundary for env hygiene* — shipped as the general
   unconditional-credential-injection scanner; host-scoped attaches produce no finding.
3. *Default watch-axis set* — **`staleness`+`cve`**, as leaned; `adoption` stayed
   opt-in (FR-12's own consequence held).
4. *JSON schema versioning* — `schema_version: 1` shipped on `DoctorReport` (NFR-5);
   the bump *policy* (what triggers a version bump, how consumers react) remains open —
   also still open in the SPEC's Open Questions.
5. *Own taxonomy vs. warden's `ErrorKind`* — own closed taxonomy (AD-3); zero
   cross-package vocabulary drift over the whole build.
6. *`check --list` in v1?* — shipped in v1 (registry-addressable checks; public
   `VALID_WATCH_AXES` on the monitor side).

**Success metrics status.** SM-4 met (env-hygiene live, JFROG_API_KEY worked example
caught). SM-1/SM-2/SM-3 are qualitative by design; the 2026-08-08 domain refresh flagged
that SM-1's premise (Marshal invoking `doctor check` unprompted pre-spin) is wiring
outside Doctor's own stories and was not yet institutional habit at that date.
Counter-metrics held: SM-C1's 5-second budget survived Epic 6's source additions
(re-profiled in Story 6.1; the benchmark asserts a minimum findings count so
broken-and-therefore-fast cannot pass).

**Estate obligations post-dating this PRD (owned by `epics.md`, recorded here for
traceability).** The 2026-08-24 Canopy and operating-model passes bound Doctor as spoke
#5 of the `src/platform/` host: portal `/stations/doctor/` (first slice — last fleet
pulse — landed 2026-08-26 via `PortalClient` only), service face `POST
/stations/doctor/mcp` on the host ASGI, SKF domain skill + `bmad-agent-doctor` persona
(Epic 18), and gather/prescribe hook specs with default plugins on the shared
`pyforge.core.hooks` contract (Epic 17 / FR-45, canopy:AD-21). Per the Unifying
Strategy (`spec-pyforge-unifying-strategy`), Doctor's role is fleet vitals and
prescriptions; the §2.1 "Operability exit code" framing above is now a fleet-wide
constraint: **findings stay advisory or Warden inputs — never a second PR-gate
verdict.** None of these reopen §5's non-goals; the read-only boundary (NFR-1) holds
with the sole sanctioned widening AD-12 records (a `run_git` leg inside `cli_bridge`).

## Currency reconciliation — 2026-08-29

*Chain-currency sweep re-fired: `specs/spec-pyforge-doctor/`'s `.memlog` moved to
2026-08-29T02:15 while this PRD sat at 2026-08-26, past the runbook's 2-day grace
window. Reconciled against the spec's own memlog entries, `spec-chain-currency-sweep`
(the sibling Spec this sweep runs from), and the as-built package.*

**What moved, and why none of it is a new FR.** `sources/chain.py` (deferred-work-check
content-comparison fix + fleet-wide promotion unblock, doctor Stories 8.5/8.6, PRs
#906/#907) and `sources/marshal.py` (story-status's landing-evidence grammar fix, PR
#904) are bug fixes to detector infrastructure this PRD's FR-14/FR-15 already describes
(the source registry; the ten re-homed detectors, each barred from importing the
station it judges) — a detector getting more accurate is not a new capability.
`sources/factory.py` gained one classifier rule for marshal's own dispatch-run records
inside `bmad-drift` (PR #903), same class. The `DEFERRED_SPECS` registration itself
(`sources/board.py`) is `chain-completeness` bookkeeping, not a Doctor capability.

**`spec-chain-currency-sweep`** declared its real surface
(`scripts/chain_currency_sweep_check.py`, previously `surface: []`) and was itself
registered in `DEFERRED_SPECS` as workflow-shaped — its companion
`CHAIN-CURRENCY-RUNBOOK.md` is the procedure of record, not an epic backlog. Already
inside this PRD's own "decompose-directly" FR-inventory boundary (above): sibling
doctor Specs (this one included) are referenced by CAP-N, never minted as a new PRD FR.

**No FR/content change required.** `updated:` bumped to record that the check ran.

## Currency reconciliation — 2026-09-04

*Chain-currency sweep re-fired: `specs/spec-pyforge-doctor/`'s `.memlog` moved to
2026-09-03T20:35 while this PRD sat at 2026-08-29, past the runbook's 2-day grace
window. Reconciled against every memlog entry since 2026-08-29, `epics.md`, and the
as-built package (PR #1043).*

**What moved, and why none of it is a new FR.** Four `(change)` entries, all detector
infrastructure this PRD's FR-14/FR-15 already describe: `sources/factory.py`'s classifier
gained the `fleet-drain-runs/*` coverage rule (PR #936) and the `fleet-drain-queue.yaml →
tracked:marshal-queue` rule (atlas course correction, 2026-08-30); `sources/chain.py::
_call_site_count` stopped walking `.pixi/` (the 32 GB tree that hard-timed-out
`fleet-picture`'s due-for-verification pass); `checks/env_hygiene.py` regained its sub-5 s
budget by pruning `output/`, `archive/`, `_skf-learn/` and prefiltering before `ast.parse`
(2026-09-01). A detector getting more accurate or faster is not a new capability. The
2026-09-03 entry is the fleet-hygiene surface restamp (post-#1038 `pixi lock`; "no new
product work").

**Epic 19 (Story 19.1, 2026-09-01) landed above this PRD's FR ceiling** — the
manifest-driven suite watched set (`recipes/bmad-suite/suite-members.yaml` ∪ pixi pins)
with registry-aware upstream resolution. It extends Epic 15's suite-drift work and binds
steward `spec-bmad-suite-metapackage` CAP-1 (its `epics.md` heading carries the Spec
binding); per this PRD's decompose-directly boundary it is referenced by that binding, not
minted as an FR here.

**No FR/content change required.** `updated:` bumped to record that the check ran.

## Currency reconciliation — 2026-09-07

*Chain-currency sweep re-fired: three specs' `.memlog`s (`spec-bmad-drift-new-artifact-shape`,
`spec-pixi-candidate-currency`, `spec-pyforge-doctor`) moved to 2026-09-07 (marshal Story 31.1
cross-station surface-reconcile, below) while this PRD sat at 2026-09-04, past the runbook's
2-day grace window.*

**What moved, and why none of it is a new FR.** Marshal's Story 31.1 (TEA equivalence run
against all 8 stations) added five new file shapes under each station's `planning-artifacts/`
(`test-design-architecture.md`, `test-design-qa.md`, `test-design-progress-system.md`,
`test-design/<slug>-handoff.md`, `reviews/*.md`) — a new artifact class this PRD's FR-14/FR-15
detector-infrastructure sections already cover in kind (Doctor recognizes new planning-artifact
shapes as they appear; it does not enumerate every shape in the PRD itself). The new shapes
tripped two existing detectors for the first time — `factory.py::classify()`
(`test_bmad_artifacts_integrity`, HARD `uncovered`) and `hygiene_definitions.py::is_orphan_file`
(`test_live_repo_gather_reports_no_finding_naming_warden`, orphan-file WARN) — both fixed with
one dated classification rule set each, same shape and convention as every prior new-artifact-
shape incident recorded above. A classifier recognizing one more conventional shape is not a new
capability.

**No FR/content change required.** `updated:` bumped to record that the check ran.

## Currency reconciliation — 2026-09-14

*Chain-currency sweep re-fired: `spec-pyforge-doctor`'s SPEC.md moved to 2026-09-12 and its
`.memlog` to 2026-09-14T05:18 while this PRD sat at 2026-09-07 — seven days, past the runbook's
2-day grace window.*

**What moved in the Spec, and why none of it is a new FR.**

1. **A `surface-drift-exclude:` frontmatter block (7 paths, 2026-09-12).** Pure detector
   bookkeeping for `spec-surface-check`: seven files this kernel Spec still *covers* under
   `surface:` but no longer *drift-tracks*, because a narrower Spec
   (`spec-sibling-dreams-drift`, `pyforge-marshal/spec-pyforge-core`) already reconciles each
   one. Coverage is unchanged. No FR describes drift-tracking bookkeeping, and none should.
2. **Eight dated `verified:` lines on CAP-1..CAP-8 plus the Charter §6 CAP (2026-09-11
   operator-directed mechanical sweep).** All PASS, all evidence *about* the shipped contract
   rather than changes *to* it. One is worth recording here because it reads like a defect and
   is not: CAP-3's sweep found 6 of 12 prescriptions carrying `rank_factors: null`, traced to
   `prescribe.rank()`'s deliberate exclusion of `DoctorStatus.OK` findings from ranking —
   covered by `test_prescribe_rank.py::test_clean_ok_finding_is_excluded_from_ranking_even_though_actionable`.
   FR-4's "never a bare priority number" stands as written.
3. **Three new Assumptions bullets.** (a) Two *incoming* surface claims recorded before the
   code lands — steward Story 49.2's new `sources/` module (criterion stays on
   `spec-pyforge-unifying-strategy`; implementation relayed to a new doctor Dream + Spec,
   `spec-capability-effect-check`) and steward Story 49.8's named `sources/marshal.py:544`
   read. (b) `spec-pyforge-charter`'s registration in `DEFERRED_SPECS`. (c) The explicit
   statement that `bmad-drift`'s 17 live warns against marshal's artifacts are **not doctor's
   to fix** — doctor is the detector, marshal's `SYNC-RUNBOOK.md` is the reconciler. All three
   are ownership/boundary statements about work this PRD already scopes; none widens the FR set.
4. **Six `.memlog` surface-reconcile entries (2026-09-12 → 2026-09-14).** A new detector source
   (`sources/capability_ledger.py` + its tests), a PR #1354 re-measure of three live-repo
   snapshot tests against the GitHub Actions billing-outage content drift, `board.py`'s INV-A
   gaining a delivered-Spec branch (ten `shipped` Specs delivered with no epic and no ledger row
   were structurally invisible), the four-test replacement that followed it, `board.py`'s INV-B
   gaining an EPIC arm (`DW-CHAIN-COMPLETENESS-7`, closed), and marshal Epic 42's incoming claim
   on `sources/chain.py::_drift_findings`.

**Why (4) is still inside FR-14/FR-15 and not a new FR.** This PRD's established boundary —
recorded in the 2026-08-26 reconciliation and reapplied at every sweep since — is that FR-14
(verdict on the Marshal's durability) and FR-15 (doctor holds the verdict for every conformance
detector) scope detector *infrastructure*, and that new sources, new invariant arms and new
classifier rules land inside them rather than each minting an FR. `capability_ledger.py` is one
more source behind the same dispatcher; INV-A's delivered-Spec branch and INV-B's epic arm are
two invariants correcting their own blind spots (each had a structural exemption that made a real
gap invisible) inside `chain-completeness`, which FR-15 already names. Nothing moved a module
boundary and nothing reopened AD-1..AD-6.

**One thing worth naming rather than absorbing.** Both INV-A and INV-B changes fixed the same
*class* of defect: an invariant that discarded a whole key class up front (`if status not in
OPEN_SPEC_STATUSES: continue`; `if not k.startswith("epic-")`) and therefore could never fire on
it. That is a detector-design lesson, not an FR — it belongs in the doctor Spec's own guidance,
where the memlog already records it, and it is repeated here only so the PRD's reader knows the
two entries are one story, not two.

**No FR/content change required.** `updated:` bumped to record that the check ran.

## Currency reconciliation — 2026-09-17

One-chain fold. `fr-derivation-from` set. Every kernel FR heading cites its source CAP. No new FR minted. Absorbed Spec CAPs stay epic-decomposed.

## Currency reconciliation — 2026-09-19

*Chain-currency sweep after PR #1529 (doctor Story 30.1): the brief absorbed
`research/documentation-currency-and-repeatable-refresh-2026-09-19.md`, and
`spec-pyforge-doctor` minted CAP-83/CAP-84 (Epic 30) the same day.*

**One new FR.** FR-17 cites CAP-83/CAP-84 — the first kernel-Spec CAPs since the one-chain fold
that describe product scope this PRD had not framed (documentation currency as a fleet vital
sign). It is minted here, not decomposed directly, because the capability is Doctor's own
(FR-15's "home for every detector judging another station's artifact" applied to the docs
shelf), not a sibling Spec's. Epic 30 is its decomposition; the FR-inventory boundary paragraph
in § Currency reconciliation — 2026-08-26 is amended to name it.

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this PRD. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-24

*Chain-currency sweep (CHAIN-CURRENCY-RUNBOOK.md): `specs/spec-pyforge-doctor/.memlog.md` moved
to 2026-09-24T06:55 (Story 30.3 landing: the five reference-page generators —
`docs-pixi-tasks`, `docs-environments`, `docs-detectors`, `docs-skills-catalog`,
`docs-station-cli` — plus `docs_currency.py`'s `generated-page-stale` check) while this PRD sat
at 2026-09-20, tripping a `feeds` finding (`spec` dated after `prd` past the 2-day grace
window). Story 30.2 (`docs/map.yaml` and the three `docs-currency` checks) had already landed
2026-09-20 (hand-landed merge `Merge pyforge-doctor/30-2 into main`, e2105fec02d) without a PRD
bump of its own; both stories are folded into this one pass. FR-17's two capabilities — CAP-83
(map-scope enforcement) and CAP-84 (repeatable regeneration) — are now both fully delivered;
Epic 30 is 30.1/30.2/30.3 all `done`. No new requirement, decision, or AD; the "Decomposed as
Epic 30" line above is updated to match. `updated:`/`currency_review:` bumped to record that
this sweep ran.*
