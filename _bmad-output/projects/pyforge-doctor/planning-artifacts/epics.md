---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/briefs/brief-pyforge-doctor-2026-07-25/brief.md
updated: '2026-08-15'
currency_review: "Reviewed 2026-08-15 (later same day) — Epics 10/11/12 appended, decomposing the 3 newly-authored doctor Specs (spec-bmad-method-version-drift, spec-deferred-work-resolution-sweep, spec-fleet-hygiene-verification-exemplar-program) directly, matching Epic 8/9's own decompose-directly precedent (no new FR-N minted; CAP-N referenced directly per epic). Story 10.1/10.3/12.1-12.5 cleared to dispatch; Story 10.2 and 11.8 blocked pending open-question resolution named in their own Specs; Epic 11's Stories 11.1-11.7 form a dependent pipeline, cleared to dispatch as a whole. Stories only — none dispatched this pass. Story 9.1 landed same day (PR #530), Epic 9's own definition gate now cleared. Prior: Reviewed 2026-08-15 — Epics 8 and 9 appended, decomposing spec-deferred-work-visibility's CAP-4..10 (added to that Spec the same day; operator answered its Q5 with decompose-directly). Epic 8 cleared to dispatch; Epic 9 queued behind its own Story 9.1 definition gate. Prior review 2026-08-10 (Phase 2 audit) — false Status lines corrected to done, rollup keys fixed via Tier-3+sync; see planning-artifacts/implementation-readiness-report-2026-08-10.md."
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (AD-72).
epics_role: canonical
---

# pyforge-doctor - Epic Breakdown

## Overview

Complete epic and story breakdown for **pyforge-doctor** (Doctor) — the pyforge
PyForge Guild's health & diagnostics CLI. Decomposed from the completed PRD
(FR-1–FR-9) and the completed architecture spine (6 ADs, Capability → Architecture
Map covering all 9 FRs). No UX design contract exists — Doctor is a non-interactive
CLI, same as its nearest sibling `pyforge-warden`. Epics are **vertical slices, one
per verb** (`check` / `monitor` / `diagnose`) — each ships end-to-end, independently
valuable, and JSON-capable on its own; no epic requires a later one to function.

## Requirements Inventory

### Functional Requirements

FR-1: Wrap pyforge-warden's engine-availability self-check as a library call (`doctor check --engines`), not a subprocess reimplementation.
FR-2: Every check `doctor check` runs reports tri-state `ok`/`warn`/`fail` and is individually nameable/filterable.
FR-3: `doctor check --env` includes a new credential/environment-hygiene check category (unconditional-credential-injection pattern; `JFROG_API_KEY` is the worked example).
FR-4: `doctor monitor --fleet --watch <axis>[,<axis>...]` queries cf_atlas's health/watch surfaces per named Watch axis (`staleness`, `cve`, `abandonment`), normalized into one tagged envelope.
FR-5: `monitor --fleet` prefers cf_atlas's MCP tool surface when an MCP client is available in-process, falling back to the equivalent CLI subprocess otherwise — both paths normalize to the same Finding shape.
FR-6: `diagnose --target <target>` partitions every gathered Finding into `actionable` / `blocked` / `accepted-risk` — no Finding silently dropped.
FR-7: Within the `actionable` partition, Prescriptions are ranked by severity × exploitability × blast-radius, with the ranking factors shown (never an opaque priority number).
FR-8: Every Prescription names a root cause, not just a symptom.
FR-9: `doctor check`, `doctor monitor`, and `doctor diagnose` each accept a `--json` flag producing a schema-validated `DoctorReport` document with the same information as the human-readable output.

**Added 2026-08-02 (v1.x, Epic 4 — the frontier, decomposed for real):**

FR-10: A composite health grade (A–F) per dependency, synthesized from Doctor's own already-gathered Finding data — an aggregation layer, not a new scanning instrument.
FR-11: A persistent, tracked fleet-health surface, strictly derived from `monitor --fleet` output — the graduation the original PRD §6.2 named as a candidate v1.x addition.
FR-12: An `adoption` watch axis wiring cf_atlas's existing `adoption-stage`/`version-downloads` sources into `monitor --fleet`, following the same MCP-first/CLI-fallback rule as FR-5.
FR-13: A single-hop safe-upgrade-version recommendation on `--prescribe`'s Prescription output — explicitly not a transitive dependency-graph resolver.

### NonFunctional Requirements

NFR-1: **Read-only, non-mutating (all verbs).** No module under `pyforge.doctor` writes outside a `tempfile`-scoped path or mutates a scanned tree; v1 has no `--fix`/actuator (PRD §5 Non-Goals).
NFR-2: **Operability exit-code contract.** `doctor check`/`doctor monitor` exit codes answer "is the machine/fleet sound," never a policy-gate question — closed domain `{0, 2, 130}`, permanently omitting warden's policy-gate `1` (Architecture AD-2; PRD §3 Glossary "Operability exit code").
NFR-3: **Bounded, typed subprocess safety.** The one narrow subprocess site Doctor owns (`doctor.cli_bridge`, the CLI-fallback path of FR-5) uses argv-as-list (never a shell string), a bounded timeout, and a typed `Finding(status=fail)` on failure — never a raw traceback (Architecture AD-5).
NFR-4: **Pre-flight speed budget.** `doctor check`'s default run stays fast enough to be a habitual first step (PRD SM-C1 counter-metric: check-suite runtime must not creep upward in pursuit of more findings).
NFR-5: **Schema-versioned machine contract.** The `DoctorReport` JSON envelope carries a `schema_version` field, starting at `1` (Architecture Consistency Conventions).

### Additional Requirements

*From the architecture spine (Design Paradigm / Invariants & Rules / Structural Seed) — these shape the epic/story design:*

- **No existing scaffold** — unlike `pyforge-warden` (which had a pre-existing stub), `src/shared/packages/pyforge-doctor/` does not exist yet. Epic 1 Story 1 creates the package from scratch, **mirroring** `pyforge-warden`'s own layout conventions (`pyproject.toml`, `src/pyforge/doctor/`, `tests/{unit,meta,fixtures}`, `scripts/`) rather than inventing new ones (Architecture Structural Seed).
- **AD-1 (library import, not subprocess):** `doctor.sources.warden` imports `pyforge.warden.engines.run_doctor_checks` directly. `pyforge-doctor`'s `pyproject.toml` declares `pyforge-warden` as an optional extra (`gate = ["pyforge-warden"]`), mirroring `pyforge-atlas`'s identical existing edge to warden — default-installed in-repo, external installs may omit it with an install-hint failure on the engines check only.
- **AD-2 (Doctor's own exit-code module):** `pyforge.doctor.verdict` is a new, sole-owned exit-code knob — structurally mirrors warden's `verdict.py` pattern but is not imported from it.
- **AD-3 (Doctor's own taxonomy):** `pyforge.doctor.models` defines a closed `DoctorStatus` (`ok`/`warn`/`fail`), a closed `Source` enum (one member per wrapped instrument), and a `Finding` dataclass — structurally mirrors warden's `models.py` pattern (`StrEnum` + frozen validation set) without importing warden's `ErrorKind`.
- **AD-4 (`--prescribe` is a pure function):** `pyforge.doctor.prescribe` takes an already-gathered `list[Finding]` and returns partitioned, ranked `Prescription` objects — zero subprocess or MCP calls of its own.
- **AD-5 (one narrow subprocess site):** `pyforge.doctor.cli_bridge` is the only module in `pyforge-doctor` permitted to spawn a subprocess (the CLI-fallback branch of AD-6), reusing warden's `_engine_env()` discipline as a convention.
- **AD-6 (MCP-first, CLI-fallback):** `doctor.sources.atlas` calls the MCP tool for a Watch axis when an MCP client is available in-process; otherwise falls back to the equivalent CLI subprocess via AD-5's `cli_bridge`. Both paths normalize to the same `Finding` shape.
- **`pixi.toml` `[feature.pyforge-doctor.*]` block** — documented in the architecture spine's Deferred section as mirroring `[feature.pyforge-warden.*]` verbatim; the actual edit is Epic 1 Story 1's job, not a prerequisite of this planning chain.
- **Cross-cutting acceptance gates applied to relevant stories** (not a separate epic): the read-only guard (NFR-1) as a meta-test on every gather/check module; the sole-subprocess-site guard (NFR-3/AD-5) as a static meta-test mirroring warden's own `tests/meta/test_verdict_sole_ownership.py`; the AD-1 no-reimplementation guard (a meta-test asserting `doctor.sources.warden` never calls `subprocess`).

### UX Design Requirements

**N/A** — non-interactive CLI, same as `pyforge-warden`; no UI surface. Human-facing affordances (tri-state check display, explainable prescription ranking) are owned as FR-2/FR-7, not UX artifacts.

### FR Coverage Map

FR-1: Epic 1 — wraps warden's self-check as a library call.
FR-2: Epic 1 — tri-state, individually addressable checks.
FR-3: Epic 1 — credential/env-hygiene check (new detection capability).
FR-4: Epic 2 — fleet-wide watch-axis query (staleness/cve/abandonment).
FR-5: Epic 2 — MCP-first, CLI-fallback data access.
FR-6: Epic 3 — partition findings by actionability.
FR-7: Epic 3 — rank the actionable partition.
FR-8: Epic 3 — root-cause naming.
FR-9: Epic 1 (`check --json`) + Epic 2 (`monitor --json`) + Epic 3 (`diagnose --json`) — delivered per-verb, as each verb's last story, not a separate epic (no epic exists that is JSON-output-only with no other user value).
FR-10: Epic 4 — health scoring.
FR-11: Epic 4 — persistent fleet-health surface.
FR-12: Epic 4 — adoption-tracking watch axis.
FR-13: Epic 4 — safe upgrade-path recommendation.

All 13 FRs covered; dependencies flow forward only (Epic 1 establishes the frozen `Finding`/`DoctorReport` contract every later epic produces against, never edits; Epic 2 and Epic 3 are independently valuable and do not require each other; Epic 4 consumes Epic 1's frozen contract, Epic 2's `atlas` gather filter (Story 2.1's MCP-first/CLI-fallback pattern, extended) and Epic 3's `prescribe` pipeline (Story 3.1's partition, Story 3.2's ranking) as already-shipped inputs — Epic 4 cannot start before Epics 1-3 ship, per the PRD's own sequencing).

## Epic List

### Epic 1: Pre-flight Check (walking skeleton)
An operator or Marshal (bmad-loop) runs `doctor check --env --engines` and gets a fast, tri-state, JSON-capable answer to "is the machine sound" before a factory run starts — wrapping warden's existing self-check and adding Doctor's one genuinely new detection capability (credential/env hygiene). This epic also stands up the package itself and freezes the `Finding`/`DoctorReport` contract every later epic builds on.
**FRs covered:** FR-1, FR-2, FR-3, FR-9 (check verb)

### Epic 2: Fleet Pulse (doctor monitor --fleet)
An operator runs `doctor monitor --fleet --watch staleness,cve,abandonment` and gets one normalized, source-tagged view of what cf_atlas's separate CLIs would otherwise require running and reconciling by hand — the weekly habit the brief names as a success signal (SM-3).
**FRs covered:** FR-4, FR-5, FR-9 (monitor verb)

### Epic 3: Diagnose & Prescribe (doctor diagnose --prescribe)
An operator triaging a specific feedstock or finding runs `doctor diagnose --target <target> --prescribe` and gets an ordered, explainable remediation worklist — partitioned by actionability, ranked by severity × exploitability × blast-radius, each entry naming its root cause — instead of unranked findings they have to prioritize themselves.
**FRs covered:** FR-6, FR-7, FR-8, FR-9 (diagnose verb)

### Epic 4: The frontier, decomposed (v1.x — added 2026-08-02)
An operator gets four extensions to the walking skeleton, each strictly derived from Epics 1-3's already-shipped output rather than a new gather path: a composite health grade, a persistent fleet-health surface, an adoption-tracking watch axis, and a single-hop safe-upgrade recommendation. Sequenced after Epics 1-3 ship and prove themselves — this epic requires all three, uniquely among Doctor's epics.
**FRs covered:** FR-10, FR-11, FR-12, FR-13

### Epic 5: The verdict on the Marshal's own row
The station that owns the sprint ledger stops being the station that grades it. Charter §6 has required this since 2026-07-28; nothing implemented it until a real loss made the gap concrete.
**FRs covered:** FR-14

### Epic 6: Every verdict comes home (Charter §6, generalized — added 2026-08-08)
Epic 5 applied §6 to one artifact. An ownership audit found the clause violated fleet-wide: 10 of 13 repo-level detectors judge an artifact another station produces, and none belongs to Doctor. This epic re-homes those 10 as Doctor sources, each structurally barred from importing the station it judges — and does it behind a profile, because the verb they land on is already over its budget.
**FRs covered:** FR-15, FR-16 (added 2026-08-11, queued via the Dream/Spec chain — Story 6.11)

---

## Epic 1: Pre-flight Check (walking skeleton)

Stand up the `pyforge-doctor` package, freeze its `Finding`/`Source`/`DoctorReport` contract and exit-code module, then deliver `doctor check` end-to-end: warden's wrapped self-check, tri-state individually addressable checks, the new credential-hygiene detector, and JSON output. Every later epic's gather filters are producers against this story's frozen contract.

### Story 1.1: Package scaffold, frozen Finding/DoctorReport contract & exit-code module

As a **tool maintainer**,
I want the `pyforge-doctor` package created (mirroring `pyforge-warden`'s layout), with the `DoctorStatus`/`Source`/`Finding`/`DoctorReport` shapes and Doctor's own exit-code module frozen and unit-proven,
So that every later gather filter, check, and verb is a producer against a stable contract that never needs a schema-breaking retrofit.

**Acceptance Criteria:**

**Given** no `src/shared/packages/pyforge-doctor/` directory exists, **When** the scaffold is created, **Then** it mirrors `pyforge-warden`'s structure — `pyproject.toml` (with `optional-dependencies.gate = ["pyforge-warden"]` per AD-1), `src/pyforge/doctor/` (empty `__init__.py`, `__main__.py` stub), `tests/{unit,meta,fixtures}/`, `scripts/` — and a `pyforge-doctor --version`/`--help` stub runs.

**Given** `pyforge.doctor.models`, **When** it is defined, **Then** it declares a closed `DoctorStatus` (`StrEnum`: `ok`, `warn`, `fail`), a closed `Source` enum with one member per wrapped instrument (`warden-doctor`, `staleness-report`, `cve-watcher`, `behind-upstream`, `feedstock-health`, `release-cadence`, `env-hygiene`), and a `Finding` dataclass (`source`, `check`, `status`, `message`, `evidence: dict`) with `__post_init__` validation rejecting an unknown `status`/`source` — structurally mirroring warden's `models.py` pattern (AD-3) without importing warden's `ErrorKind`.

**Given** the `DoctorReport` envelope, **When** it is frozen, **Then** it is `{schema_version, verb, generated_at, findings: [Finding], prescriptions: [Prescription]}` with `schema_version` starting at `1` (NFR-5), `prescriptions` present (possibly empty) only when `verb == "diagnose"`, and a committed JSON Schema document validates a minimal example report.

**Given** `pyforge.doctor.verdict`, **When** it is tested against every `DoctorStatus` combination, **Then** it is Doctor's sole-owned exit-code knob (AD-2) and its exit-code domain is exactly `{0 = every check ok, 2 = a fail present, 130 = SIGINT}` — a `warn`-status Finding never changes the exit code, and no path outside `verdict.py` invokes an exit primitive with a guarded exit value (a static meta-test enforces this, mirroring warden's own `tests/meta/test_verdict_sole_ownership.py`).

**Given** the repo, **When** a meta-test runs, **Then** it asserts no module under `pyforge.doctor` writes outside a `tempfile`-scoped path (NFR-1's read-only guard, proven now even though nothing gathers real Findings yet).

### Story 1.2: Wrap warden's engine-availability self-check (FR-1)

As an **operator or Marshal**,
I want `doctor check --engines` to report the same engine-availability findings warden's own `--doctor` flag produces,
So that I get warden's proven engine self-check through Doctor's one interface, without a second, drift-prone reimplementation.

**Acceptance Criteria:**

**Given** an environment where a required engine (e.g. `osv-scanner`) is missing, **When** `doctor check --engines` runs, **Then** `doctor.sources.warden` calls `pyforge.warden.engines.run_doctor_checks` as a **library import** (AD-1) and the missing-engine result is normalized into a `Finding(source=Source.WARDEN_DOCTOR, status=DoctorStatus.FAIL, ...)`.

**Given** the same environment, **When** `warden scan --doctor` is run directly, **Then** its finding content (which engines, what versions, pass/fail) is equivalent to what `doctor check --engines` reports for the same engine — the two never diverge because Doctor calls the same underlying function, not a copy of its logic.

**Given** the repo, **When** a meta-test runs, **Then** it asserts `doctor.sources.warden` contains no `subprocess` import or call (AD-1's no-reimplementation guard — the module may only import and call `pyforge.warden.engines`).

**Given** `pyforge-warden` is not installed (the `gate` extra omitted), **When** `doctor check --engines` runs, **Then** it reports a single `Finding(status=fail)` naming the missing extra and the install hint — never a raw `ImportError` traceback.

### Story 1.3: Tri-state, individually addressable checks (FR-2)

As an **operator**,
I want every check `doctor check` runs to report `ok`/`warn`/`fail` and be individually nameable,
So that a `warn`-level finding doesn't get treated as a build-blocking failure, and I can re-run one check in isolation while debugging.

**Acceptance Criteria:**

**Given** `doctor check` with no flags, **When** it runs, **Then** every check it performs reports exactly one of `DoctorStatus.OK`/`WARN`/`FAIL` (never a bare boolean), and only a `FAIL`-status Finding contributes to a non-zero exit code (per Story 1.1's `verdict` rule).

**Given** `doctor check --list`, **When** it runs, **Then** it enumerates every named check (`--engines`'s per-engine checks plus `--env`'s checks once Story 1.4 lands) without running any of them.

**Given** `doctor check --engines osv-scanner` (one named check), **When** it runs, **Then** its result is identical to running the full `--engines` suite and filtering to that one check's Finding.

### Story 1.4: Credential/environment-hygiene check (FR-3)

As an **operator**,
I want `doctor check --env` to detect unconditional-credential-injection-shaped configuration (the `JFROG_API_KEY` pattern in `_http.py` as the worked example),
So that Doctor catches this class of finding automatically instead of relying on someone remembering the known issue.

**Acceptance Criteria:**

**Given** a Python file where an env-var read (`os.environ.get`/`os.getenv`) feeds an HTTP-header/auth assignment with no accompanying host-scope conditional, **When** `doctor check --env` scans it, **Then** it reports a `Finding(source=Source.ENV_HYGIENE, status=warn_or_fail, evidence={file, line, var_name})` — evidence names the affected code path (not just "a problem exists somewhere").

**Given** `.claude/skills/conda-forge-expert/scripts/_http.py` as a golden fixture, **When** `doctor check --env` scans the repo's default target path, **Then** it reports the known `JFROG_API_KEY` unconditional-injection finding — the concrete worked example the Dream names.

**Given** the scanner, **When** it runs, **Then** it uses `ast.parse` only — it never `exec`s, `import`s, or otherwise executes the scanned code (mirrors warden's own extraction "no execution" discipline; a meta-test asserts no `exec`/`eval`/dynamic-import call exists in `doctor.checks.env_hygiene`).

**Given** a file with a host-scoped credential attach (a conditional gating the header assignment on destination host), **When** scanned, **Then** it does **not** produce a Finding — the check generalizes past the one worked example without false-positiving on already-correct code.

### Story 1.5: `doctor check` CLI wiring, `--json`, and the speed budget (FR-9, NFR-4)

As an **operator or Marshal**,
I want `doctor check --env --engines` to run as one command with both human-readable and `--json` output, fast,
So that it's a viable pre-flight gate in both an interactive terminal and an unattended bmad-loop run.

**Acceptance Criteria:**

**Given** `doctor check` (no verb flags), **When** it runs, **Then** it runs both `--engines` (Story 1.2) and `--env` (Story 1.4) checks by default, renders a human-readable summary, and exits per Story 1.1's `verdict` rule.

**Given** `doctor check --json`, **When** it runs, **Then** stdout is exactly one valid `DoctorReport` document (Story 1.1's schema) containing every Finding — no information present in the human-readable output is absent from the JSON output.

**Given** a normal repository state (no engine installs pending), **When** `doctor check` runs, **Then** it completes within a documented speed budget (NFR-4) — a benchmark test in `tests/unit` asserts this, guarding against a future check regressing the "five-second pre-flight" property.

**Given** `doctor check --version`/`--help`, **When** run, **Then** they behave as a stable contract, matching the convention warden's own CLI already established.

---

## Epic 2: Fleet Pulse (doctor monitor --fleet)

Deliver `doctor monitor --fleet` end-to-end: an atlas gather filter with the MCP-first/CLI-fallback rule proven on one axis, then extended to all three named Watch axes, then wired into the verb with `--json`. Builds on Epic 1's `Finding`/`DoctorReport` contract as a producer; does not require Epic 3.

### Story 2.1: Atlas gather filter — staleness axis, MCP-first with CLI fallback (FR-5, AD-6)

As an **operator or an MCP-capable agent (Marshal)**,
I want `doctor monitor --fleet --watch staleness` to query cf_atlas's `staleness_report` signal via whichever access path is available,
So that the same command works identically whether I'm a human at a terminal or an agent with an MCP client.

**Acceptance Criteria:**

**Given** an MCP client is available in-process, **When** `doctor monitor --fleet --watch staleness` runs, **Then** `doctor.sources.atlas` calls the `staleness_report` MCP tool and normalizes its output into `Finding(source=Source.STALENESS_REPORT, ...)` objects.

**Given** no MCP client is available (bare terminal invocation), **When** the same command runs, **Then** `doctor.sources.atlas` falls back to the `staleness-report` CLI via `doctor.cli_bridge` (AD-5) — argv as a list, bounded timeout, `NO_COLOR`-equivalent discipline, typed `Finding(status=fail)` on subprocess failure — and produces the **same** `Finding` shape as the MCP path for equivalent underlying data.

**Given** the repo, **When** a meta-test runs, **Then** it asserts `doctor.cli_bridge` is the only module in `pyforge-doctor` containing a `subprocess` call (AD-5's sole-subprocess-site guard, mirroring Story 1.2's AD-1 guard).

### Story 2.2: cve and abandonment watch axes (FR-4)

As an **operator**,
I want `--watch cve` and `--watch abandonment` to work the same way `--watch staleness` does,
So that I get the full named Watch-axis set the Dream promises (`staleness,cve,abandonment`), not just one.

**Acceptance Criteria:**

**Given** `doctor monitor --fleet --watch cve`, **When** it runs, **Then** it follows Story 2.1's MCP-first/CLI-fallback pattern against `cve_watcher`/`cve-watcher`, tagging Findings `Source.CVE_WATCHER`.

**Given** `doctor monitor --fleet --watch abandonment`, **When** it runs, **Then** it composes `feedstock_health` (filtered to `stuck`/`bad`) and `release_cadence` (`decelerating`/`silent` labels) into `Finding`s tagged with their respective originating Source — an "abandonment" Finding is never presented as if it came from a single instrument when it's actually a composite.

**Given** `--watch staleness,cve` (multiple axes in one invocation), **When** it runs, **Then** every requested axis's Findings appear in one `DoctorReport`, each still individually Source-tagged and filterable.

### Story 2.3: `doctor monitor --fleet` CLI wiring, default axis set, `--json` (FR-9)

As an **operator**,
I want `doctor monitor --fleet` (no `--watch` flag) to run a sensible default axis set, and `--json` to work the same way it does for `check`,
So that the weekly-glance habit doesn't require remembering the full axis list every time, and agent-consumers get the same machine contract across verbs.

**Acceptance Criteria:**

**Given** `doctor monitor --fleet` with no `--watch` flag, **When** it runs, **Then** it runs the documented default axis set (`staleness`, `cve` — the two highest-signal defaults per Story 2.1/2.2's Sources) rather than every axis unconditionally.

**Given** `doctor monitor --fleet --json`, **When** it runs, **Then** stdout is exactly one valid `DoctorReport` (`verb: "monitor"`) — same schema Story 1.5 established for `check`, same parity guarantee (no information in human output absent from JSON).

**Given** an operator filtering by Source in the human-readable output, **When** they ask "show me only what came from `behind-upstream`," **Then** the rendered output supports filtering by the `Finding.source` tag.

---

## Epic 3: Diagnose & Prescribe (doctor diagnose --prescribe)

Deliver `diagnose --target … --prescribe` end-to-end: partition, then rank, then root-cause naming, then CLI wiring with `--json`. Consumes Epic 1's `check` gather filter and Epic 2's `atlas` gather filter as already-shipped inputs — adds zero new subprocess/MCP calls of its own (AD-4).

### Story 3.1: Partition findings by actionability (FR-6, AD-4)

As an **operator triaging a target**,
I want every Finding gathered for that target sorted into `actionable`/`blocked`/`accepted-risk`,
So that a finding with no available fix is visibly tracked instead of either silently dropped or presented as if I should act on it today.

**Acceptance Criteria:**

**Given** a target with a mix of Findings (some with a known fix, one unfixed CVE, none yet waived), **When** `doctor.prescribe.partition` runs, **Then** every Finding appears in exactly one of `actionable`/`blocked`/`accepted-risk`, and the total count across all three partitions equals the count of Findings gathered.

**Given** a Finding for a CVE with no available fix version, **When** partitioned, **Then** it lands in `blocked` with a human-readable reason ("no fix version published") — visible in output, never omitted.

**Given** `pyforge.doctor.prescribe`, **When** it runs, **Then** it is a pure function over an already-gathered `list[Finding]` (AD-4) — it makes zero subprocess or MCP calls; a meta-test asserts no `subprocess`/MCP-client import exists in `doctor.prescribe`.

### Story 3.2: Rank the actionable partition (FR-7, AD-4)

As an **operator**,
I want the `actionable` partition ordered by severity × exploitability × blast-radius, with the ranking factors shown,
So that I know what to fix first and *why*, without re-deriving priority by hand.

**Acceptance Criteria:**

**Given** two actionable Findings where one is KEV-flagged and the other is not (equal severity otherwise), **When** ranked, **Then** the KEV-flagged one ranks first.

**Given** two actionable CVE Findings of equal severity where one has a higher EPSS score, **When** ranked, **Then** the higher-EPSS one ranks first.

**Given** two actionable Findings tied on severity and exploitability, **When** ranked, **Then** the one with the smaller upgrade-lag classification (patch < minor < major, reusing `behind-upstream`'s existing lag classification as the blast-radius tiebreaker) ranks first.

**Given** any ranked `Prescription`, **When** rendered, **Then** it includes a `rank_factors` object naming which signals fired (e.g. `{kev: true, epss: 0.62, blast_radius: "patch"}`) — never a bare integer with no explanation.

### Story 3.3: Root-cause naming (FR-8)

As an **operator**,
I want every Prescription to name a root cause, not just repeat the symptom,
So that I understand *why* the finding exists, not only that it exists.

**Acceptance Criteria:**

**Given** a Prescription for a CVE Finding that traces to a staleness lag (the fix already shipped upstream, just not adopted), **When** rendered, **Then** its `root_cause` field names the staleness lag ("upstream released a fix N versions ago you haven't picked up"), not only the CVE ID.

**Given** a Prescription for an engine-missing Finding (from Epic 1's `check` gather filter, when `diagnose --target` implies an environment check), **When** rendered, **Then** its `root_cause` is templated from that Finding's own `evidence` field (no new NLP/inference layer — the template reads structured evidence Epic 1/2 already produced).

### Story 3.4: `doctor diagnose --target … --prescribe` CLI wiring, `--json` (FR-9)

As an **operator or Marshal**,
I want `doctor diagnose --target <target> --prescribe` to run as one command with both human-readable and `--json` output,
So that the full partition-and-rank pipeline is reachable through Doctor's one interface, consistent with `check` and `monitor`.

**Acceptance Criteria:**

**Given** `doctor diagnose --target <feedstock>` (no `--prescribe`), **When** it runs, **Then** it gathers Findings for that target (composing Epic 1's `check` filter when the target implies an environment check, and Epic 2's `atlas` filter for the target's fleet signal) and reports them without partitioning/ranking — `--prescribe` is what triggers Story 3.1/3.2/3.3's pipeline.

**Given** `doctor diagnose --target <feedstock> --prescribe --json`, **When** it runs, **Then** stdout is exactly one valid `DoctorReport` (`verb: "diagnose"`) with `prescriptions` populated per Story 3.1/3.2's partition+rank output — same schema and parity guarantee as `check`/`monitor`.

**Given** a target with only `blocked` and `accepted-risk` Findings (nothing actionable today), **When** `--prescribe` runs, **Then** the output still lists them (Story 3.1's no-silent-drop rule) rather than reporting an empty/misleadingly-clean result.

---

## Epic 4: The frontier, decomposed (v1.x — added 2026-08-02)

Four extensions to the walking skeleton, each a pure synthesis/wiring layer over Epics 1-3's already-shipped output — zero new gather paths, zero new scanning instruments. Sequenced strictly after Epics 1-3 ship; this is the one epic in this project that genuinely requires its predecessors to function, not just to be more valuable.

### Story 4.1: Health scoring (FR-10)

As an **operator**,
I want a composite health grade (A–F) per dependency, synthesized from Doctor's own already-gathered Finding data,
So that I can tell at a glance whether a package is healthy without re-reading every individual Finding.

**Acceptance Criteria:**

**Given** a `list[Finding]` already gathered for a target (Epic 1's `check` filter and Epic 2's `atlas` filter as inputs), **When** `pyforge.doctor.score.grade` runs, **Then** it returns a grade in `{A, B, C, D, F}` computed as a pure function over that list — zero new subprocess or MCP calls (a meta-test asserts no such import exists in `doctor.score`, mirroring Story 3.1's AD-4 guard on `prescribe`).

**Given** the same `list[Finding]` passed twice, **When** graded both times, **Then** the grade is byte-identical (deterministic — no timestamp or wall-clock read in the scoring path).

**Given** a target whose gather only partially completed (e.g. the `cve` axis timed out but `staleness` succeeded), **When** graded, **Then** the result is explicitly `incomplete`, never a computed letter grade standing in for missing data.

**Given** `--json` on any verb that includes a grade, **When** rendered, **Then** the grade and its constituent axis scores both appear in the `DoctorReport` (parity with FR-9's existing rule).

### Story 4.2: Persistent fleet-health surface (FR-11)

As an **operator**,
I want the fleet's health condition written to a tracked, at-a-glance surface after a `monitor --fleet` run,
So that I don't have to re-run and manually compare snapshots to see what changed.

**Acceptance Criteria:**

**Given** a completed `doctor monitor --fleet` run, **When** the surface is written, **Then** its content is derived solely from that run's `Finding`/`Source` output (Epic 2's existing shape) — no independent second gather is triggered to produce it.

**Given** the same underlying findings, **When** the surface is regenerated, **Then** the output is idempotent (same findings in, same surface out, no spurious diff).

**Given** the surface's own schema, **When** written, **Then** it carries a `schema_version` field starting at `1` (NFR-5's existing precedent extended to this new artifact), so a future format change is detectable by a consumer.

**Given** a `monitor --fleet` run that includes the `adoption` axis (Story 4.3), **When** the surface is written, **Then** it reflects that axis too — the surface tracks whatever axes the triggering run covered, never a hardcoded subset.

### Story 4.3: Adoption-tracking watch axis (FR-12)

As an **operator**,
I want `--watch adoption` to normalize cf_atlas's `adoption-stage` and `version-downloads` signals into the same Finding shape as the existing axes,
So that I catch abandonment signals the staleness/cve axes alone would miss (a package can be un-abandoned-looking by commit history but genuinely losing adoption).

**Acceptance Criteria:**

**Given** an MCP client is available in-process, **When** `doctor monitor --fleet --watch adoption` runs, **Then** `doctor.sources.atlas` calls the `adoption_stage`/`version_downloads` MCP tools and normalizes their output into `Finding(source=Source.ADOPTION, ...)` objects — following Story 2.1's exact MCP-first pattern.

**Given** no MCP client is available, **When** the same command runs, **Then** it falls back to the equivalent CLI subprocess via the existing `cli_bridge` (AD-5) — same sole-subprocess-site guard as Story 2.1, no new subprocess site added.

**Given** `doctor monitor --fleet` with no `--watch` flag, **When** it runs, **Then** the default axis set stays `staleness`+`cve` (Story 2.3's existing default) — `adoption` is opt-in only, never silently added to the default.

**Given** the `Source` enum (Story 1.1's closed taxonomy), **When** `ADOPTION` is added as a new member, **Then** the enum stays closed (AD-3) — the addition is a deliberate extension, not an open/stringly-typed escape hatch.

### Story 4.4: Safe upgrade-path recommendation (FR-13)

As an **operator**,
I want a Prescription to name a specific next-safe-version target when one is confidently known,
So that "update to X.Y.Z" replaces "here's a ranked problem" as the last mile of the worklist.

**Acceptance Criteria:**

**Given** an actionable Prescription (Story 3.2's ranked output) for a package where atlas's `behind-upstream` data names a next release with no known breaking-change signal, **When** rendered, **Then** the Prescription includes a `safe_upgrade_target` field naming that version.

**Given** the same case but atlas's data spans multiple major-version jumps with no clear single "next safe" version, **When** rendered, **Then** `safe_upgrade_target` is explicitly `null`/absent with a stated reason — never a guessed version standing in for missing confidence.

**Given** `pyforge.doctor.score` (or wherever this recommendation is computed), **When** it runs, **Then** it is single-hop only — this package's own next version, never a transitive resolution across multiple packages (a meta-test or code-review-gated invariant asserts no multi-package graph traversal exists in this module, keeping the PRD §5 "no real dependency-graph resolver" non-goal intact).

**Given** `pyforge.doctor.prescribe`, **When** the upgrade-path recommendation is added, **Then** `prescribe` remains a pure function over already-gathered data (AD-4 preserved) — the recommendation is computed from data Epic 2's gather filters already produced, not a new fetch triggered inside `prescribe` itself.

---

## Epic 5: The verdict on the Marshal's own row

**Value delivered.** The station that owns the sprint ledger stops being the station
that grades it. Charter §6 has required this since 2026-07-28; nothing implemented it
until a real loss made the gap concrete.

### Story 5.1: Marshal-durability source, independent by construction

As the operator,
I want Doctor to tell me when a tracked ledger has lost a completion,
So that a durability failure in Marshal's own machinery is caught by something Marshal
does not control.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** FR-14; AD-11, AD-12
**Surface:** `sources/marshal.py`, `cli_bridge.py` (`run_git`), `models.py`
(`Source.MARSHAL_DURABILITY`), `tests/unit/test_sources_marshal_independence.py`

**Acceptance Criteria:**

**Given** a tracked sprint ledger whose working state un-finishes a story
**When** the `marshal-durability` source gathers
**Then** a `FAIL` Finding names the project, the count and the keys, with a
`git checkout HEAD -- <path>` remedy
**And** an aggregate `FAIL` states the total across all ledgers

**Given** no ledger has regressed
**Then** exactly one `OK` Finding states how many ledgers were checked

**Given** git is unavailable, the target is not a repository, or no ledger exists
**Then** the result is `WARN` — never `OK`, and never an exception

**Given** any state at all
**Then** `sources/marshal.py` imports no `pyforge.<station>` package — asserted by
`test_sources_marshal_independence.py`, including lazy imports and string constants
that could be fed to `import_module`
**And** every subprocess call routes through `cli_bridge` (AD-5/AD-12), asserted by
`test_cli_bridge_sole_subprocess.py`

**Status:** done — verified against the real 2026-08-08 incident (restoring the damaged
herald ledger yields FAIL/55; a clean tree yields OK/8 ledgers). Scope is the SOURCE
only; rendering it is Story 5.2, deliberately split rather than folded in (see below).

### Story 5.2: Render the verdict through a `doctor` verb

As the operator,
I want `doctor` to actually show me the Marshal-durability verdict,
So that the check is something I see, not something that merely exists.

**Type:** feature • **Effort:** XS • **Deps:** S-5.1, S-6.1 (the profile this is sequenced behind) • **FR/AD:** FR-14; AD-11
**Surface:** `__main__.py`

**Why this is its own story, not part of 5.1.** `sources/marshal.py` shipped with **no
caller** — `__main__.py:47` imports `atlas` and `warden`, not `marshal`. Marking 5.1
done while the source is unreachable would be the "merged, marked done, never became the
runtime" shape this repo already carries as the Atlas Kedro precedent and forbids in
Marshal's AD-67. Splitting states the truth: the verdict is built and provably
independent, and it is not yet rendered.

**Sequenced behind a profile, not blocked on nothing.** `doctor check` is measured at
**7.04s against its documented 5.0s budget** (SM-C1, `DW-DOCTOR-2026-08-08-1`). Adding a
gather filter to that verb before profiling would knowingly worsen a live NFR breach.

**Acceptance Criteria:**

**Given** a repo with tracked sprint ledgers
**When** the operator runs the verb this story wires
**Then** the `marshal-durability` Findings appear in both human and `--json` output
**And** a FAIL Finding participates in the exit-code lattice like any other
**And** `doctor check` is inside its documented budget after the addition — measured,
not assumed

**Status:** done

**Outcome (2026-08-09).** Wired as a third `doctor check` category (`--durability`),
whole-category only — per-check addressability is a `checks.registry` concern and this
story's surface is `__main__.py`; a NAME argument would hand-roll a second filter path
beside `gather_one`, the exact drift that function's "filter, not a second code path"
rule prevents. Default run is all three categories; an explicit `--engines`/`--env`
narrows, so durability is excluded — the existing semantics extended, not special-cased.

**The split paid for itself immediately.** `--json` crashed with
`jsonschema.ValidationError` and exit 2 on the first run: 5.1 added
`Source.MARSHAL_DURABILITY` to the Python enum but **not** to `data/report-schema.json`,
and nothing caught it because 5.1 shipped the source with no caller — its findings had
never been rendered, so they had never been validated. Exactly the "merged, marked done,
never became the runtime" shape this split was written to expose. Schema extended, plus
`test_schema_source_enum_matches_the_source_taxonomy_exactly` asserting **set equality in
both directions** (a one-way `schema ⊆ enum` check would have passed while the member was
missing — the direction that broke); mutation-tested by removing the member.

Measured, not assumed: `doctor check` **2.95 / 2.99 / 3.03s** against the 5.0s budget,
with the durability gather itself **~0.04s** — the headroom S-6.1 created, spent as
intended. FAIL drives exit 0 → 2. Suite 418 → 422.


---

## Epic 6: Every verdict comes home (Charter §6, generalized)

**Value delivered.** Epic 5 moved one verdict. This moves the rest. A detector-ownership
audit on 2026-08-08 measured the clause Charter §6 has asserted since 2026-07-28 and found
it violated fleet-wide: of **13** repo-level detectors, **10 judge an artifact another
station produces**, and not one of those 10 is Doctor's. Marshal owns the ledger, the board,
the Dream→Spec chain and the spec surface — and owns the detectors that grade all four.

**The rule, stated once.** *Marshal may own the operational guard; Doctor must own the
verdict.* Two layers, not a transfer. `promote_sprint_status.py` keeps refusing bad writes
and `--project` scoping stays; what moves is the authority to be the final word.

**Why this epic is sequenced, not parallel.** Every story lands a gather on `doctor check`,
measured at **7.04s against its documented 5.0s budget** (SM-C1, `DW-DOCTOR-2026-08-08-1`).
Adding 10 gathers to a verb already 40% over is not a detail to discover at the end — so
S-6.1 is the profile, and nothing else starts until it passes.

**Blockers found during the audit, recorded here so they are not rediscovered:**
1. `scripts/detectors.py` discovers detectors by AST-scanning `scripts/*.py`. Moving them
   into `pyforge.doctor.sources.*` returns an empty registry — the registry must be
   rewritten (S-6.2), and it is itself currently ungoverned.
2. `docs/dashboard/generate.py:650` does `from bmad_drift_check import …` for
   `GUILD_DREAMS`/`STATIONS`. PR #317 created that import deliberately to kill a
   hand-mirrored copy that had already caused a false positive. Moving `bmad_drift_check`
   breaks board generation unless the shared constants move first (S-6.8).
3. The `pyforge-doctor` env carries no `yaml` (needed by `chain_completeness`,
   `dream_chain`) and no `bmad_loop` (needed by `forward_dependency`). `yaml` is a plain
   library add; `bmad_loop` is a real coupling decision — the import is deliberate
   (`ACTIONABLE_STATUSES` is *derived, never restated*, so the check stays tied to real
   engine behaviour), and restating it breaks that invariant.
4. Three detectors are `runtime` scope (`dashboard_drift`, `loop_stall`, `unpushed_work`)
   and read host state (tmux, `~/.bmad-loops`); they cannot run in CI. Doctor must preserve
   the repo/runtime split internally or lose CI-ability (S-6.3).

### Story 6.1: Profile `doctor check` and bring it inside its budget

As the operator,
I want `doctor check` measured and inside SM-C1 before anything is added to it,
So that §6 compliance is not bought by breaking Doctor's own performance contract.

**Type:** change • **Effort:** M • **Deps:** — • **FR/AD:** FR-15; SM-C1
**Surface:** `sources/*.py`, `cli/check.py`, `tests/`

**Why first.** `DW-DOCTOR-2026-08-08-1` records three timed iterations — 6.92s / 7.04s /
6.73s against 5.0s — and states the cost is unattributed: warden's `--version`
subprocesses, the atlas MCP/CLI fallbacks, and the env-hygiene walk are all candidates.
Charter §6 forbids the judged station relaxing its own threshold, so the budget is fixed
and the work must meet it.

**Acceptance Criteria:**

**Given** the monorepo root
**When** `doctor check` is profiled per-source
**Then** the cost of each gather is attributed and recorded, not estimated
**And** `test_doctor_check_completes_within_the_five_second_budget` passes on `main`
**And** the budget itself is unchanged — no re-thresholding

**Status:** done

**Outcome (2026-08-08).** The profile cleared two of this entry's three suspects: warden's
engines gather is **0.18s**, and the atlas fallbacks are not on `check`'s path at all (they
belong to `monitor`). env-hygiene was **97%** — 7.73s of parse across 3,721 files, of which
**6.43s / 3,216 files was the gitignored 590MB `build_artifacts/`** (third-party conda
sources and test envs). That directory sorts before `docs`/`recipes`/`scripts`/`src`, so the
walk spent its entire entry cap inside it and reached **zero** first-party files — all 609
under `src/` and `scripts/` were unscanned, including the scanner's own module. Pruning
build-output/tool-cache dir names cut the gather to ~3.2s **and raised** first-party coverage
0 → 602 files, surfacing a third real finding that had been invisible. The 5.0s budget is
untouched. Residual: the walk is still `incomplete` (`SDKs/` is 39,379 of 52,968 entries and
holds no Python) — split out as `DW-DOCTOR-2026-08-08-2`, since it needs a design decision,
not a bigger constant. Epic 6's remaining stories are unblocked.

### Story 6.2: A source registry Doctor owns

**Type:** feature • **Effort:** M • **Deps:** S-6.1 • **FR/AD:** FR-15
**Surface:** `sources/__init__.py`, `models.py` (`Source`), `scripts/detectors.py`

**Given** detectors resolve as Doctor sources rather than `scripts/*.py` files
**Then** discovery no longer depends on AST-scanning a directory, and every source is
enumerable with its scope, subject station and owning station
**And** a source with no declared subject is a startup error, not a default

**Status:** done

**Outcome (2026-08-08).** `sources/__init__.py` (was empty) now holds a validated
`SourceRegistration` registry (scope + subject station + owning station per current
`Source` member, `__post_init__` raising loud on an empty subject/owner or an invalid
scope — including a whitespace-only value) covering all 9 sources that existed before
this story; a coherence test enforces exact set-equality between `Source` and the
registry in both directions. `scripts/detectors.py` gained a `_doctor_sources()` helper
that reads this registry directly (never AST-scanning Doctor's package) and reports a
`doctor_sources_available` flag alongside the rows, so "zero sources" is never confused
with "the package isn't importable here" — verified true in both the dedicated
`pyforge-doctor` env (9 rows) and the default `local-recipes` env / `detectors.yml` CI
workflow (neither installs `pyforge-doctor`; the flag reads `false` there, not a silent
empty list). This story is the registry MECHANISM only: no `scripts/*_check.py` logic
moved, and none of the 10 not-yet-implemented detector identities (`ledger_regression`
etc.) were added — those land with their own `gather()` in Stories 6.4-6.9, each
registering its own entry against the coherence test built here. One pre-existing gap
surfaced incidentally: `Source.BEHIND_UPSTREAM` has no backing `gather()` anywhere in
`pyforge.doctor` (only 4 of the 5 named atlas axes were ever wired) — logged as deferred
work, not fixed here (outside this story's surface). 435 doctor tests pass
(`pyforge-doctor-test`), plus 4 new stdlib-only tests under the lean `pyforge-ci` env
(`pyforge-doctor-scripts-test`, new task).

### Story 6.3: The repo/runtime split survives the move

**Type:** feature • **Effort:** S • **Deps:** S-6.2 • **FR/AD:** FR-15
**Surface:** `sources/__init__.py`, `cli/check.py`

**Given** three sources read host state and cannot run in CI
**When** Doctor runs where that state is absent
**Then** those sources report `WARN`/unknown — never `OK`, never an exception
**And** a CI-only invocation can select the repo-scope set explicitly

**Status:** done

**Outcome (2026-08-09).** Mechanism-only, like Story 6.2: no real `scope="runtime"`
source exists yet (Story 6.5's `dashboard_drift` is still the first), so this story
built the two pieces every later story needs. `sources.scope_for(source)` is the one
canonical per-source scope lookup, and `sources.degrade_on_exception(source, check,
gather)` is the reusable "cannot evaluate here" wrapper a future `scope="runtime"`
gather calls around its own host-state reads — deliberately NOT wired into today's
three existing (`scope="repo"`) dispatch calls, whose own gather functions already
promise never to raise. `doctor check` gained `--scope {repo,runtime,all}` (default
`all`, unchanged behavior), filtering `run_engines`/`run_env`/`run_durability` by
each category's `sources.REGISTRY`-declared scope — proving the CI-selection half of
the AC today (`--scope runtime` yields 0 findings/exit 0, since all 9 registered
sources are still `scope="repo"`). Adversarial review (Blind Hunter + Edge Case
Hunter, independently, both) caught one real gap: an EXPLICIT category flag
(`--engines`/`--env`/`--durability`) contradicting `--scope` used to silently drop to
a zero-finding, exit-0 report indistinguishable from "ran clean" for an automated
`--json` consumer — fixed with a usage-error guard (`_validate_scope_against_
explicit_categories`) before dispatch, so only the implicit default-run's "narrow to
zero" stays silent (the documented, intentional CI-selection behavior). 449 doctor
tests pass (10 new this story). One pre-existing `__all__`-sort lint finding
(ruff RUF022, confirmed via `git show <baseline> | ruff check`) logged to
`deferred-work.md`, not fixed here.

### Story 6.4: The ledger verdicts come home

**Type:** change • **Effort:** M • **Deps:** S-6.2, S-6.3 • **FR/AD:** FR-15
**Surface:** `sources/marshal.py`, `sources/ledger.py`, `tests/`

**Given** `ledger_regression_check` and `story_status_check` both judge Marshal's ledger
**When** they resolve as Doctor sources beside the existing `marshal-durability`
**Then** each reports through Doctor's Finding contract and exit-code lattice
**And** neither imports `pyforge.marshal`
**And** Marshal's pre-write guards remain in place, unmodified

**Status:** done

### Story 6.5: The board verdicts come home

**Type:** change • **Effort:** M • **Deps:** S-6.2, S-6.3 • **FR/AD:** FR-15
**Surface:** `sources/board.py`, `tests/`

**Given** `chain_completeness`, `dashboard_drift` and `check_layout` judge Marshal's board
**Then** all three resolve as Doctor sources, `dashboard_drift` declared `runtime` scope
**And** `chain_completeness`'s INV-A..D findings survive the move verbatim — same
invariants, same messages, proven by a mutation test per invariant

**Status:** done

### Story 6.6: The chain verdicts come home

**Type:** change • **Effort:** M • **Deps:** S-6.2, S-6.3 • **FR/AD:** FR-15
**Surface:** `sources/chain.py`, `tests/`, `pixi.toml`

**Given** `dream_chain`, `spec_surface` and `deferred_work` judge the artifact chain every
station shares
**Then** all three resolve as Doctor sources
**And** `yaml` is added to the `pyforge-doctor` env for the two that need it — a library
add, never a feature union (the isolation rule that broke `main` twice, PRs #113/#115)

**Status:** done

### Story 6.7: `forward_dependency` comes home, and the harness coupling is decided

**Type:** change • **Effort:** M • **Deps:** S-6.6 • **FR/AD:** FR-15
**Surface:** `sources/deps.py`, `pixi.toml`, `tests/`

**Why it is its own story.** This is the only detector whose move requires a decision
rather than a port. It imports `bmad_loop.sprintstatus.ACTIONABLE_STATUSES` deliberately —
*derived, never restated*, so the check cannot drift from real engine behaviour. Adding the
harness to Doctor's lean env couples Doctor to Marshal's toolchain; restating the enum
breaks the invariant that makes the check trustworthy. Neither is free.

**Acceptance Criteria:**

**Given** the two options are stated with their costs
**When** one is chosen
**Then** the decision is recorded as an AD with its rejected alternative
**And** if the enum is restated, a conformance test fails when it diverges from the
installed library — the invariant is preserved by a different mechanism, not dropped

**Status:** done

### Story 6.8: `bmad_drift` comes home without breaking the board

**Type:** change • **Effort:** M • **Deps:** S-6.6 • **FR/AD:** FR-15
**Surface:** `sources/factory.py`, `docs/dashboard/generate.py`, `tests/`

**Given** `docs/dashboard/generate.py` imports `GUILD_DREAMS`/`STATIONS` from
`scripts/bmad_drift_check.py`
**When** that detector moves
**Then** the shared constants have exactly one home and both consumers derive from it
**And** no hand-mirrored copy is reintroduced — the 2026-07-28 false positive is the reason
that import exists

**Status:** done

### Story 6.9: The `scripts/` shims retire

**Type:** change • **Effort:** S • **Deps:** S-6.4, S-6.5, S-6.7, S-6.8 • **FR/AD:** FR-15
**Surface:** `scripts/`, `pixi.toml`, `scripts/spec_surface_allowlist.txt`, meta-tests

**Given** all 10 verdicts resolve as Doctor sources
**Then** the `scripts/` detector files are removed, their pixi tasks re-point at Doctor
**And** each retired file's allowlist entry is deleted — the allowlist shrinks, per
`spec-regenerable-factory` CAP-2
**And** the two meta-tests that invoke the old paths
(`test_bmad_artifacts_in_sync.py`, `test_spec_surface_check.py`) are updated, not deleted
**And** the four detectors that are **governed rather than allowlisted** transfer their
surface claim: `spec-regenerable-factory`'s `surface:` globs for `spec_surface_check.py`,
`bmad_drift_check.py`, `dream_chain_check.py` and `deferred_work_check.py` are **deleted**,
as is `spec-surface-drift-reconciliation`'s claim on `spec_surface_check.py` — the moved
files are governed by `spec-pyforge-doctor`'s own `src/shared/packages/pyforge-doctor/**`
glob the moment they land there, so the transfer needs no new Doctor surface entry, only
retirement of the stale ones
**And** those retirements are **verified**, not assumed: a `surface:` glob that matches
nothing is **not** a finding today (only allowlist entries produce `stale-allowlist`), so a
stale claim rots silently — the same "a too-broad or stale glob is invisible by
construction" asymmetry `spec-regenerable-factory`'s own memlog records. Confirm each
retired glob by diffing the governed-file count before and after
**And** `spec-regenerable-factory`'s surface reaching **zero** ends its governance role —
recorded in its memlog rather than left implicit, since that Spec is `shipped` and nothing
else would mark the hand-off

**Status:** done

### Story 6.10: Independence is structural, for every source

**Type:** feature • **Effort:** S • **Deps:** S-6.9 • **FR/AD:** FR-15; AD-11, AD-12
**Surface:** `tests/meta/test_source_independence.py`

**Given** every Doctor source declares the station it judges
**When** the meta-test runs
**Then** no source imports the package of the station it judges — including lazy imports
and string constants that could reach `import_module`
**And** `sources/warden.py` is an explicitly allowlisted exception with its reason recorded
(it relays an instrument's self-report about its own environment, which is not judging an
artifact)
**And** a newly added source with no declared subject fails the test

**Status:** done

### Story 6.11: The classifier recognizes a spike report *(added 2026-08-11 — FR-16)*

As the operator,
I want `pyforge.doctor.sources.factory::classify()` to recognize a design-spike's PASS/FAIL
report written to a project's `planning-artifacts/` root,
So that a legitimate, story-mandated artifact shape stops HARD-failing `detectors-ci` as
`uncovered` the way every unrecognized shape already has, twice before this one.

**Type:** change • **Effort:** XS • **Deps:** S-6.8 • **FR/AD:** FR-16

**Why now.** On 2026-08-11 (PR #427, Marshal Story 7.6) Marshal's own landing agent
confirmed `_bmad-output/projects/pyforge-marshal/planning-artifacts/spike-0-copier-api-fit-report.md`
trips `check_coverage`'s `uncovered` HARD finding, and that the fix belongs in this
classifier, out of scope for a marshal-package landing. `classify()`'s own history already
covers this exact class of gap twice — fourteen shapes added 2026-07-28, eleven more
2026-08-08 — each closed by one small, dated, git-reviewed rule in the same function. This
is the third occurrence, not a new kind of problem.

**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py`
(`classify()`)

**Acceptance Criteria:**

**Given** a file under `_bmad-output/projects/pyforge-marshal/` matching the design-spike
report convention (`planning-artifacts/spike-0-copier-api-fit-report.md` today; the exact
rule scope — literally `spike-*-report.md` at `planning-artifacts/` root, or a pattern that
also anticipates a future `Spike-1`/`Spike-2` — is this story's own design decision, per
`spec-bmad-drift-new-artifact-shape`'s open question)
**When** `classify()` runs
**Then** it returns a named classification instead of `UNKNOWN`, with a dated comment
recording this story and the 2026-08-11 incident, matching the file's own established
convention for every prior carve-out
**And** `check_coverage` no longer reports that file as `uncovered`
**And** `check_coverage`'s fail-closed default is otherwise unchanged — a file that still
matches no rule, including a spike-report look-alike outside the agreed pattern, still HARD
fails
**And** re-running `check_coverage` against the live `pyforge-marshal` tree returns zero
`uncovered` findings, and `pixi run -e local-recipes detectors-ci` reports clean for
`bmad-drift`

## Epic 7: Deferred-work visibility

> **CONFIRMED by the operator, 2026-08-10 (in-session)** — the Phase-3 hold is lifted:
> `spec-deferred-work-visibility` is de-registered from `DEFERRED_SPECS` (its landed
> decomposition is this epic; 6-9's sequencing dependency landed as PR #394; the four
> questions closed at PR #396). Stories dispatch in order 7.1 → 7.2 → 7.3 → 7.4 on the
> next `marshal factory spin pyforge-doctor`.

**Value delivered.** `deferred_work_check`'s guarantee becomes real: every deferral carries
identity from birth, anonymous Tier-3 entries are seen, and the 470-entry blind backlog is
grandfathered rather than exploding a landing pass. Decomposes
`spec-deferred-work-visibility` (ready, PR #396; open_questions closed — Doctor owns BOTH
halves, the emitter mints ids at defer time, grandfather wholesale at a dated cut-off,
same severity both sides). Sequenced behind 6-9, which landed (PRs #394/#395). Added by
the fleet audit's Phase 3 (2026-08-10) per the operator-approved decomposition queue.

### Story 7.1: The emitter mints identity at defer time
**Given** a bmad-dev-auto review pass that defers work **When** the deferral is written
**Then** the entry carries an id under the station's own convention (`DW-FU-<story>` for
doctor/atlas/marshal/warden, `DW-<story>-<n>` for mason) from birth — an entry reaching
promotion without an id is already invisible to the promoter (CAP-1; edits
`.claude/skills/bmad-dev-auto/step-04-review.md`, allowlisted not governed).

### Story 7.2: Grandfather the 470 at a dated cut-off
**Given** the pre-existing anonymous backlog **When** this story lands **Then** the dated
cut-off baseline exists covering all 470 wholesale (warden's precedent); CAP-3's full
success — green on unchanged repo, red on one new anonymous entry — is demonstrable only
once S-7.3 arms the gate against it. Triage is explicitly a separate, later effort.
**Deps:** S-7.1.

### Story 7.3: The detector sees anonymous Tier-3 entries
**Given** `pyforge.doctor.sources`' deferred-work source **When** it audits **Then**
`_anonymous()` runs on the Tier-3 file too, new anonymous entries are findings, the
grandfathered set is exempt by the baseline, and **the CAP-2 mutation proof is met:
deleting an id heading from a Tier-3 entry reds the detector, demonstrated by mutation**
— the vacuity class `_anonymous()`'s own docstring records catching once before (CAP-2).
**Deps:** S-7.2.

### Story 7.4: One severity, both sides
**Given** anonymous entries on either side of the tracked/Tier-3 pair **When** reported
**Then** both carry the same severity, asserted by a test that plants one on each side
(CAP-2 closing AC). **Deps:** S-7.3.

## Epic 8: The legacy deferred-work backlog comes home

> **CONFIRMED by the operator, 2026-08-15 (in-session)** — decomposes CAP-4..7 of
> `spec-deferred-work-visibility`, added to that Spec the same day. Operator answered the
> Spec's Q5 (re-validate vs. decompose directly) with **decompose directly**: CAP-1..3 are
> shipped and untouched, `ready` is already the status that means "decompose me", and
> flipping the whole Spec back to `draft` would assert the shipped half is unbuilt. Stories
> dispatch in order 8.1 → 8.2 → 8.3 → 8.4 on the next `marshal factory spin pyforge-doctor`.

**Value delivered.** Epic 7 stopped the bleeding — the emitter mints ids at defer time, the
detector sees anonymous entries, the pre-existing backlog is grandfathered. It did not clear
the backlog, and its own Story 7.2 said so ("Triage is explicitly a separate, later effort").
That backlog is still gitignored Tier-3, still one worktree teardown from gone. A 2026-08-15
by-hand fleet audit promoted 144 `tier3-only-deferral` findings plus ~72 more previously
invisible ones across 6 of 8 projects, shipped two real bugs doing it, and still left **72
entries** (`tier3-entry-unidentified`: marshal 30, steward 38, mason 2, herald 2). This epic
replaces that by-hand process with a tool that cannot ship those two bugs. Bounded and
shrinking, not an ongoing leak — everything still anonymous predates PR #396.

### Story 8.1: The parser reads every legacy Tier-3 shape
**Given** a Tier-3 `deferred-work.md` carrying entries from before the CAP-1 emitter fix
**When** the deferred-work source parses it **Then** every entry is classified correctly
across all four shapes proven to exist live — a headerless flat `- source_spec:`/`summary:`/
`evidence:` bullet under a `bmad-dev-auto` step-04 marker comment (atlas, 58 findings dating
to July); the older `## Deferred from: code review of <spec> (<date>)` section-header
convention predating any `DW-` id (warden); CAP-1's current headed shape; and a headed entry
with **more than one** `- source_spec:` bullet stacked under it (marshal/steward) — with zero
false-orphan and zero false-owned misclassifications, pinned by a fixture built from real
excerpts of each. These are the exact two shapes that broke two different hand-rolled
attempts on 2026-08-15: a false-orphan duplication of already-headed content, and a 10x
overcount that read a header's second bullet as a new orphan (231 spurious mints against a
true count of 30 for marshal alone) (CAP-4). **Deps:** —

**Status:** done

**Outcome (2026-08-15).** `classify_tier3_entries` (new, additive, `pyforge/doctor/sources/
chain.py`) distinguishes the four live shapes; `_anonymous()`/`_entries()`/`_ids()` and
`gather_deferred_work`'s findings are untouched (verified byte-identical detector output).
Live verification found the real shape-4 mechanics narrower than this AC's paraphrase — the
header itself carries zero bulleted fields, and the bug is `_anonymous()`'s state machine
attributing the next unrelated headerless bullet to it, not "one header owning multiple
related bullets" — grounded in real excerpts, not the paraphrase (see the story spec's Design
Notes). Adversarial review caught and fixed two live-data-confirmed HIGH bugs before landing:
a continuation-line joiner misreading prose colons as field boundaries (corrupted 5 real
entries across 4 projects), and a false-orphan misclassification when non-field content (an
HTML comment) sits between a header and its field block (confirmed in marshal's committed
ledger). The `_anonymous()` swallow-bug itself is logged as `DW-FU-8-1` (25/38 headers
fleet-wide, corrected from this story's own 21/29 estimate), not fixed — out of scope per the
Spec's "do not rewrite `_anonymous()`" constraint.

### Story 8.2: Minting picks the next free suffix per station convention
**Given** an orphan entry Story 8.1 classified **When** an id is minted for it **Then** the
id follows the owning station's own convention that CAP-1 already standardized
(`DW-FU-<story>` for doctor/atlas/marshal/warden, `DW-<story>-<n>` for mason) and takes the
next free numeric suffix **for that story** by querying the tracked ledger's existing maximum
— never restarting at 1. Pinned against three real 2026-08-15 near-misses that each attempted
a duplicate mint before being caught and renumbered by hand: `DW-10-5-1` against an existing
`DW-10-5-1..8`, `DW-10-6-1`, and `DW-13-3-1` (CAP-5). **Deps:** S-8.1.

**Status:** done

**Outcome (2026-08-15).** `mint_id_for_entry` (new, `pyforge/doctor/sources/chain.py`) ports
the id-minting prose already living in `.claude/skills/bmad-dev-auto/step-04-review.md` into
real, tested code — pure computation, no file writes. Adversarial review, executed live
against real fleet data, caught and fixed three HIGH bugs before landing: a silent-swallow of
unreadable ledger files as "zero tokens"; a batch-minting collision (calling the function
repeatedly for entries sharing a derived story key without an in-batch accumulator produced 24
identical duplicate ids against real data — the exact volume Story 8.3's bulk `--fix` mode will
need, fixed by adding an `already_minted` accumulator parameter); and a brittle unnormalized
`station` comparison with no validation. The spec's own anecdotal near-miss ids
(`DW-10-5-1`/`DW-10-6-1`/`DW-13-3-1`) had since moved in the live ledgers (same-day churn); the
identical edge-case shapes were re-verified against real, currently-live entries instead
(steward's `DW-FU-9-3-*` series, mason's `DW-1-10-1`).

### Story 8.3: The fix mode promotes the backlog and refuses on collision
**Given** the live 72-entry legacy backlog **When** `--fix` runs (mirroring
`scripts/spec_surface_check.py --write-baseline`'s established pattern) **Then** every entry
Story 8.1 classifies as a genuine orphan is minted via Story 8.2 and appended to the tracked
ledger with a `status: open` line and a `promoted: <date>` provenance note, `tier3-entry-
unidentified` clears for marshal/steward/mason/herald with **zero content duplication**, and
a manufactured collision fixture (duplicate id **or** duplicate summary-text) aborts the write
with **no partial output** — mutation-tested, because a partial write is how the by-hand pass
corrupted content twice (CAP-6). **Deps:** S-8.2.

**Status:** done

**Outcome (2026-08-15).** `scripts/deferred_work_promote.py --fix` (new, standalone -- Doctor's
own package stays read-only) promotes Story 8.1's classified orphans via Story 8.2's minting,
writing once in memory after full validation, mirroring `spec_surface_check.py`'s pattern.
Adversarial review found real risks before this ever touched live data: a reproduced
concurrent-write data-loss race (now a loud abort, via a re-read-and-compare check
immediately before the write); a content-fidelity bug, live-confirmed on 13 real orphans, that
dropped a `resolution:` field and force-overwrote an orphan's own `status:` (now preserved
verbatim); a crash-safety gap (`write_text` truncation, now `tempfile`+`os.replace`, matching
`seed_claude_consent.py`'s in-repo precedent); and an uncaught-exception path that crashed the
whole multi-project run instead of isolating one project's failure. **Correction to this
story's own AC:** `tier3-entry-unidentified` does not fully clear from `--fix` alone -- that
finding is baseline-count-driven and needs Story 8.4's re-stamp too (see the spec's Design
Notes); `tier3-only-deferral` is what clears per newly-promoted id. Live backlog counts were
also stale in the epics.md text (72 total quoted vs. 300+ found live via `classify_tier3_entries`
today) -- noted, not corrected here, since re-measuring the fleet-wide count is not this
story's job. The script has not yet been run for real against the live fleet backlog (only
tmp copies during development) -- that first real run is deliberately out of this story's own
scope.

### Story 8.4: The baseline re-stamps so a second run is a no-op
**Given** a completed `--fix` run **When** the grandfather baseline
(`scripts/.deferred-work-baseline.json`, CAP-3's own mechanism) is re-stamped **Then**
newly-promoted entries are never re-flagged, and running `--fix` immediately again is a
no-op: 0 new writes, 0 findings delta — the same lockstep discipline
`spec_surface_check.py --write-baseline` already keeps for its own baseline (CAP-7).
**Deps:** S-8.3.

**Status:** done

**Outcome (2026-08-15).** `scripts/deferred_work_promote.py --fix` now re-stamps a project's
grandfather baseline (via `scripts/deferred_work_baseline.py`'s reusable `stamp_projects()`)
immediately after that project's ledger write succeeds, so a second immediate `--fix` run is a
true no-op -- 0 writes to either file, verified live. Adversarial review found three real HIGH
bugs before this touched live data: the baseline write itself was non-atomic (now
`tempfile`+`os.replace`); a failed restamp never affected the process exit code, hiding the
need for a manual fallback from any automated caller (now fixed); and a hard sibling-module
import could crash even `--help` if it were missing (now degrades gracefully). **A real,
live-confirmed design flaw was found in Story 8.3's own already-merged collision guard, not
this story's code**: once a project is promoted once, any genuinely new orphan added later is
permanently blocked, because the whole-batch-abort fires on the old, already-promoted entry's
own now-expected collision. Confirmed live against all 8 real fleet projects. Logged as
`DW-FU-8-4`, not fixed here -- needs a per-entry skip/promote redesign as its own future story.

**Epic 8 complete (4/4 stories).** The legacy deferred-work backlog now has a real,
mutation-tested tool (`classify_tier3_entries` + `mint_id_for_entry` + `deferred_work_promote.py
--fix` + baseline lockstep) replacing the error-prone by-hand process that shipped two real
bugs during the 2026-08-15 audit. It has not yet been run for real against the live,
300+-entry fleet-wide backlog (only tmp copies during development) -- and per `DW-FU-8-4`,
running it for real today would abort on every one of the 8 real projects until that
follow-on redesign lands. That first real run, and `DW-FU-8-4`'s redesign, are both explicitly
out of this epic's own scope -- future work, not carried forward silently.

## Epic 9: The hygiene sweep generalizes, and staleness surfaces itself

> **QUEUED, NOT CLEARED TO DISPATCH, 2026-08-15 (operator, in-session).** Decomposes
> CAP-8..10. Unlike Epic 8, these capabilities are **less grounded**: CAP-8/9 generalize a
> one-off `bmad-output-hygiene` sweep run by hand for `pyforge-warden` only (2026-08-14/15)
> whose finding classes were never formally defined. Testable as stated, under-specified for
> implementation. **Story 9.1 is the definition gate — it must land and be read before 9.2/9.3
> dispatch unattended.** Story 9.4 (CAP-10) is independent, concrete, and may run at any time.

**Value delivered.** The same class of finding gets looked for on every station instead of
whichever one a human happened to audit that night, and the fleet stops needing a human to
notice that a loop-home branch went stale. Both gaps are real and both were found by accident:
warden's hygiene sweep was never generalized to the other seven, and on 2026-08-15 all four
active stations' `loop/pyforge-<slug>` branches were found 55–60 commits behind `origin/main`
— which is how three separate stations independently rediscovered the *same* already-fixed
spec-surface bug before their branches caught up.

### Story 9.1: The five hygiene finding classes get testable definitions
**Given** the `bmad-output-hygiene` sweep exists only as a warden-shaped precedent in commit
history (`bfa9fd68`, `1567a478`, `5c5e3727`, `22da995c`, `f7654a4c`) **When** this story lands
**Then** each of its five classes — dead test scaffolding, hollow `sprint-status.yaml`, orphan
files, README placeholders, stale Dream statuses — carries a written, mechanically-checkable
definition stating what makes an artifact an instance and what explicitly does not, derived
from what that sweep actually fixed rather than invented. This is a **definition gate**: the
sweep's own success criterion (CAP-8) is stated against warden's classes as a fixture, so
those classes must be pinned before any sweep can be written against them. **Deps:** —

**Status:** done

**Outcome (2026-08-15).** `pyforge/doctor/hygiene_definitions.py` (new, dependency-free, sibling
to `models.py`/`verdict.py`/`prescribe.py`, deliberately outside `sources/`) adds
`HygieneFindingKind` (the closed 5-member enum) and five pure predicates —
`is_dead_test_scaffolding`, `is_hollow_sprint_status`, `is_readme_placeholder`,
`is_stale_dream_status`, `is_orphan_file` — each taking only caller-supplied evidence and each
docstring-cited against the real commit that first fixed a live instance of its class. All five
cited SHAs verified to exist and match the spec's own summary before any code was written.
Adversarial review (Blind Hunter + Edge Case Hunter) found and fixed 5 real issues before this
landed (0 high / 4 medium / 1 low; 10 further findings rejected with recorded rationale, 0
deferred) — most notably two crash guards (`is_hollow_sprint_status` on `None`/non-dict input
and a `None`-valued `summary:` key) and an explicit station-relative-path precondition added to
`is_orphan_file`'s docstring so Story 9.2's gather cannot misuse it. `is_orphan_file` — the one
class flagged last session as needing extra definitional care — deliberately does **not**
require a "closed" banner: both real fixtures (`RESUME-EPIC-10.md`'s self-marked banner and a
bannerless herald intake draft) classify `True` under the same mechanical rule
(non-conventional name + zero inbound references), an evidence-driven narrowing verified
against both, not an oversight. 20 new tests, 929 passed / 2 skipped (pre-existing, unrelated)
in the full suite. No production callers yet — Story 9.2 is this module's first consumer.

### Story 9.2: The sweep runs against all eight stations
**Given** the definitions from Story 9.1 **When** the hygiene sweep runs across
atlas/doctor/herald/marshal/mason/scribe/steward/warden **Then** it reproduces warden's own
five finding classes as a fixture, reports **zero false positives against warden itself**
(already swept clean, so any finding there is a false positive by construction), and surfaces
**at least one true positive** on a station never audited this way (CAP-8).
**Deps:** S-9.1.

### Story 9.3: Hygiene findings report and never mutate
**Given** any hygiene finding from Story 9.2 **When** it is emitted **Then** it names the path
and the evidence for why the artifact is judged dead/orphaned/hollow/stale, and the sweep's own
invocation **mutates no file** — asserted by a test that runs the sweep against a fixture tree
and diffs it byte-for-byte afterward. The archive/delete action stays a separate, reviewable
commit, matching this repo's archive-don't-delete convention and the same separation Story 8.3
keeps between detection and `--fix` (CAP-9). **Deps:** S-9.2.

### Story 9.4: Loop-home staleness surfaces in the ATTENTION block
**Given** a `loop/pyforge-<slug>` branch N or more commits behind `origin/main` **When**
`fleet-picture` runs **Then** its ATTENTION block names that branch and its commit distance,
without a separate manual check — proven against a synthetically-staled branch. `fleet_picture.py`
is already the ambient home for cross-cutting fleet signals and grew a baseline-drift line the
same 2026-08-15 session; this is one more line in the same block, and it stays a **report**,
never a gate (CAP-10). **Deps:** —

## Epic 10: Doctor notices when BMAD-METHOD's own installed core falls behind upstream

Decomposes `spec-bmad-method-version-drift` CAP-1..3. Split off `bmad-method-core-upgrade`
(now steward's — the apply/reconcile half) the same 2026-08-15 session; this epic is the
ambient, read-only detection half only. Live, present-tense proof the gap is real: `pixi.toml`
already requires `bmad-method >=6.11.0` while the installed `_bmad/_config/manifest.yaml`
still reports `6.10.0`, undetected until an operator happened to ask.

**Value delivered.** Doctor already reports staleness for feedstocks and CVE-affected floors;
this closes the one blind spot in an otherwise-consistent story — its own installed
BMAD-METHOD core, a governance-layer dependency with local customizations to protect, not an
ordinary pinned one.

### Story 10.1: The declared floor and the installed core are compared and reported
**Given** `pixi.toml`'s declared `bmad-method` floor and `_bmad/_config/manifest.yaml`'s
installed version **When** doctor's report/monitor runs **Then** a new read-only Source
(fitting the existing closed `Source` enum, FR-12's `adoption-stage` precedent) reports a
Finding whenever the two disagree — proven against today's real drift (`>=6.11.0` declared,
`6.10.0` installed) (CAP-1). **Deps:** —

### Story 10.2: The installed core is compared against the latest upstream release
**Given** Story 10.1's Source and a resolved data-source decision for "latest published
`bmad-method` release" **When** the installed version is older than that release **Then** a
Finding names both versions (CAP-2). **Blocked:** the Spec's own Open Questions leave "how is
the latest release sourced" unresolved — no npm-registry-lookup infrastructure exists anywhere
in this fleet (atlas's `behind-upstream`/`version-downloads` machinery is conda-forge/PyPI-scoped
only), and a live network query at check time cuts against Marshal's own "no live query per
home" discipline this fleet otherwise favors. Needs an operator/architecture decision (live
query vs. a periodically-refreshed cached feed) before this can be scoped further — tracked
openly, not silently dropped, the same way marshal's own 1 blocked story already is in this
fleet's status reporting. **Deps:** S-10.1.

### Story 10.3: The drift surfaces ambiently, never gates
**Given** a Finding from Story 10.1 (and Story 10.2, once unblocked) **When** doctor's report
runs or `fleet-picture` runs **Then** the Finding appears in both places as a `warn`, never
failing the check-suite on its own (CAP-3). **Deps:** S-10.1.

**Epic 10 clears to dispatch on Stories 10.1/10.3 alone** — Story 10.2 stays blocked pending
the operator decision above; 10.3 surfaces whatever Findings exist (10.1's today, 10.2's once
unblocked) rather than waiting on the blocked story.

## Epic 11: Tracked deferred-work entries get periodically re-verified against live code

Decomposes `spec-deferred-work-resolution-sweep` CAP-1..8. A tracked ledger entry is a claim
about code truth *at authoring time* — nobody re-checks it once it lands. Proven valuable to
fix, exactly once, by hand, never made repeatable: PR #147 (2026-07-30) individually
re-verified 145 entries and found 12 already-resolved-but-still-open, 2 that got *worse*, 5
that understated scope, and 1 only verifiable by reading a different project's code. That gap
has since grown, not shrunk — three stations have never been verified once, and every entry
promoted since (including this session's) is unverified from day one. Full precedent evidence
in the Spec's own `precedent-2026-07-30-campaign.md` companion.

**Value delivered.** The fleet stops carrying stale `status: open` lines that actively hide
drift (in either direction) and cross-project fixes a per-project sweep structurally cannot
see, without requiring a human to re-run a six-week-old manual campaign by hand again.

### Story 11.1: Due-for-verification entries are selected, per project
**Given** the fleet's tracked deferred-work ledgers **When** a sweep selector runs **Then** it
returns exactly the entries with no `verified:` line or a `verified:` date past a staleness
threshold, batched per project (CAP-1). **Deps:** —

### Story 11.2: Churn-based cost filtering skips entries whose code has not moved
**Given** an entry selected by Story 11.1 **When** its named path has zero commits since its
last-verified date (or since authoring) **Then** it is skipped (`skip-reason: no-churn`)
rather than re-read — the structural cost bound this sweep needs at ~400+ entries and growing
(CAP-2). **Deps:** S-11.1.

### Story 11.3: Mechanically-checkable claims are verified without an agent
**Given** an entry that survives Story 11.2's filter **When** its claim is grep-recomputable
(a raised exception, an absent `try/except`, an unused function, a call-site count) **Then**
the mechanical check alone produces a verdict, reusing `spec_surface_check.py`'s own two-tier
mechanical/agent-escalation shape rather than inventing a new one (CAP-3). **Deps:** S-11.2.

### Story 11.4: Judgment-requiring entries get an evidence-grounded verdict
**Given** an entry Story 11.3 escalates **When** a verification agent reads it and locates the
named code **Then** it writes a `verified: <date> — <verdict>` line citing a `file:line` or a
reproduced/measured fact — one of four verdicts (still-open, resolved, moot/superseded, or
pending-on-precondition), never a forced false confirm, and a scope correction (2 packages
claimed, 8 found) is written as the corrected number, never left stale (CAP-4). **Deps:** S-11.3.

### Story 11.5: Verification reaches across project boundaries
**Given** an entry in project A whose defect was actually fixed by a commit in project B (the
precedent's real `atlas DW-I5-1` case) **When** Story 11.4's verification runs **Then** it can
read project B's tree and correctly close the entry — a per-project-only sweep structurally
cannot catch this class at all (CAP-5). **Deps:** S-11.4.

### Story 11.6: Near-duplicate entries surface as one defect class
**Given** two or more tracked entries across different projects naming the same file/symbol
or near-identical summary text **When** the sweep reports **Then** they are grouped as a
single defect class, not independent low-priority entries nobody connects — the shape of the
precedent's sharpest finding (one root cause hit 3x across 3 projects) (CAP-6). **Deps:** S-11.4.

### Story 11.7: Verification staleness surfaces in the ambient fleet report
**Given** Story 11.1's selector data **When** `fleet-picture` runs **Then** its ATTENTION block
shows a "% of tracked entries verified within N days, per project" line, so the next
six-week staleness gap is visible incrementally instead of requiring another pointed
challenge to notice it (CAP-7). **Deps:** S-11.1.

### Story 11.8: Backlog-intake surfaces deferred entries during story drafting
**Given** a new story/spec drafted for an epic **When** tracked deferred-work entries name
that epic or story in their `owner:`/prose **Then** they surface as candidate acceptance
criteria (CAP-8). **Blocked:** the Spec's own Open Questions leave this capability's scope
boundary unresolved — it is write-adjacent to story-drafting, a different subsystem than the
read-only sweep Stories 11.1–11.7, and may belong in its own follow-on Spec rather than this
epic. Tracked openly rather than silently dropped. **Deps:** —

**Epic 11 clears to dispatch on Stories 11.1–11.7** (a natural pipeline, each depending on the
last); **Story 11.8 stays blocked** pending the scope-boundary decision above, same treatment
as Epic 10's Story 10.2.

## Epic 12: The fleet's own hygiene/verification tooling gets its documented sharp edges fixed

Decomposes `spec-fleet-hygiene-verification-exemplar-program` CAP-1..5 — deliberately narrow,
since the source Dream is an explicit catalog ("Not a commitment to build all of this...
none of these categories are sized, prioritized, or scoped for implementation here"). These
5 are the leftover items the catalog flags as concrete and not already claimed by Epic 9
(CAP-8/9/10) or Epic 11 (CAP-7). Full catalog in the Spec's own `hygiene-gap-catalog.md`
companion.

**Value delivered.** Five independent, self-contained fixes to tooling this fleet already
depends on and already found broken this session — none blocks the others, none has an open
question, all clear to dispatch immediately.

### Story 12.1: The hygiene/verification catalog stays a maintained, current artifact
**Given** a newly-discovered "nothing actually checks for X" gap **When** it is checked
against the catalog's six categories **Then** it returns a match or confirms genuine novelty,
and the catalog stays cross-referenced with which items moved from cataloged to specced to
shipped (CAP-1). **Deps:** —

### Story 12.2: The exemplar standard conformance table is refreshed and re-verified
**Given** the DW-ledger column currently shows only `pyforge-atlas` compliant while 7 other
projects now carry real, git-tracked `deferred-work-ledger.md` files **When** the refresh
runs **Then** the table is corrected to the live state, and every other column (companions,
story specs, delivery records, README) is checked for the same staleness (CAP-2). **Deps:** —

### Story 12.3: Chain completeness parses capability ids, not a bare substring match
**Given** a Spec that grew from 3 capabilities to 10 with only 3 ever decomposed into stories
**When** `chain-completeness` runs **Then** it reports the real 7-capability gap instead of
`ok` — reproduces and fixes `DW-CHAIN-COMPLETENESS-1`, found this session against
`spec-deferred-work-visibility` itself (CAP-3). **Deps:** —

### Story 12.4: Dream chain gap count surfaces in the ambient ATTENTION block
**Given** N Dreams fleet-wide with no Spec **When** `fleet-picture` runs **Then** its
ATTENTION block names the count without a separate `dream-chain` invocation being remembered
(CAP-4). **Deps:** —

### Story 12.5: The spec surface baseline write race is closed
**Given** two concurrent `--write-baseline` invocations against
`scripts/.spec-surface-baseline.json` **When** both run **Then** the race is closed (locked,
atomic, or serialized) such that neither write is silently lost — reproduces and fixes
`DW-13-5-2` (CAP-5). **Deps:** —

**Epic 12 clears to dispatch in full** — all 5 stories are independent and concrete.
