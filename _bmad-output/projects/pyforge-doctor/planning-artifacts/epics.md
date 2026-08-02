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
updated: '2026-08-02'
currency_review: "Reviewed 2026-08-02 — added Epic 4 (Stories 4.1-4.4, FR-10..13) decomposing the fresh docs/dreams/pyforge-doctor.md's frontier section. Mechanically verified: all 13 PRD FRs trace to epics.md both directions, 16/16 unique story ids, zero orphans."

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
