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
updated: '2026-09-24'   # RE-STAMPED 2026-09-24: arch→epics cascade (doctor Story 30.3 landing, spec-pyforge-doctor CAP-84 realized in full); § Currency reconciliation — 2026-09-24 appended. Prior 2026-09-20
currency_review: 'Reviewed 2026-09-24 — arch→epics cascade (doctor Story 30.3 landing;
  the spine re-dated 2026-09-24 reconciling against the PRD''s same-day bump). No
  epic, story or AD content changed — Story 30.3''s own text already matches its
  as-implemented surface; only the story-status/ledger promotion (a separate,
  post-review landing step) remains open. Reviewed 2026-09-17 (one-chain doctor fold) — spec-pyforge-doctor
  reminted CAP-1..76; epics stay 1..25 sequential; story slugs reminted through sprint_plan._slug.
  No blocked keys flipped. Reviewed 2026-09-14, later the same day (Epic 24 added
  — numbered after the docs-shelf Epic 23 that PR #1358 minted the same day: the coverage
  gate ships outside every station it judges — the mechanism stories for docs/governance/spec-coverage-gate-independence,
  a guild-owned Spec by the Charter §5 amendment of this date; Stories 24.1-24.3 minted
  backlog, doctor as executing Smith under §5 outcome/mechanism; no pre-existing ledger
  row changed). Prior: Reviewed 2026-09-14 (chain-currency sweep cascade, arch->epics
  edge, fired by the spine''s 2026-09-14 re-count of the as-built sources/ inventory)
  — validation note appended at end of file (§ Currency validation — 2026-09-14):
  ledger re-measured with the real parser at 95/95 stories done across 22/22 epics;
  the eight sources/ modules the spine''s re-count added were traced to their story
  homes and two have none in THIS file — capability_ledger.py is decomposed on steward''s
  Epic 54 (cross-station relay, consistent with spec-pyforge-doctor''s own incoming-surface-claim
  Assumption) and platform_policy.py landed from a retro action item with no story
  anywhere. No epic or story restructured. Prior: Reviewed 2026-09-09 (Epic 21 added:
  Realization-gate hygiene — the doctor half of fleet-readiness-decision-batch-2026-09-09.md,
  operator-approved the same day. Stories 21.1-21.8 are the C8 / D2 / D3 / D5 code
  fixes that a Class-B status flip cannot carry (DEFERRED_SPECS hygiene, spec-status-missing,
  the sibling-dreams re-key on filename, CONSTITUTIVE derived from guild-roster.json,
  the deferred-work verifier project-root path bug, dreams-hygiene full coverage +
  README:71 + the Kinship wikilink validator, pixi-candidate-currency CAP-4, deferred-work
  intake CAP-9); Stories 21.9-21.16 decompose the two Specs minted this pass from
  new doctor Dreams (spec-capability-effect-check CAP-1..3 — the Story 49.2 relay;
  spec-status-body-consistency CAP-1..5). All 16 minted backlog via sprint_plan.py
  generate; no pre-existing ledger row changed. Prior: Reviewed 2026-09-06 (Epic 20
  added: spec-bmad-suite-lifecycle doctor relays — suite drift 7→13, render-HALT +
  frozen-path-changed detectors, RCA routing, version-drift write-back; Stories 20.1–20.5).
  Reviewed 2026-08-29 (chain-currency sweep cascade, arch->epics edge) — validation
  note appended at end of file (§ Currency validation — 2026-08-29): tracked ledger
  re-measured at 67/67 done across 18/18 epics (the 2026-08-26 note''s 82 figure was
  not re-verified before now), the four sources/ modules PRs #903/#904/#906/#907 touched
  map to already-decomposed Stories 8.5/8.6 or spec-pyforge-doctor''s already-described
  scope, no epic/story restructuring. Prior: Reviewed 2026-08-26 (chain-currency sweep)
  — validation note appended at end of file (§ Currency validation — 2026-08-26):
  tracked ledger 82/82 done across Epics 1-18, Epics 17/18 checked against the reconciled
  architecture spine, no epic/story restructuring. Prior: Reviewed 2026-08-15 (later
  same day) — Epics 10/11/12 appended, decomposing the 3 newly-authored doctor Specs
  (spec-bmad-method-version-drift, spec-deferred-work-resolution-sweep, spec-fleet-hygiene-verification-exemplar-program)
  directly, matching Epic 8/9''s own decompose-directly precedent (no new FR-N minted;
  CAP-N referenced directly per epic). Story 10.1/10.3/12.1-12.5 cleared to dispatch;
  Story 10.2 and 11.8 blocked pending open-question resolution named in their own
  Specs; Epic 11''s Stories 11.1-11.7 form a dependent pipeline, cleared to dispatch
  as a whole. Stories only — none dispatched this pass. Story 9.1 landed same day
  (PR #530), Epic 9''s own definition gate now cleared. Prior: Reviewed 2026-08-15
  — Epics 8 and 9 appended, decomposing spec-deferred-work-visibility''s CAP-4..10
  (added to that Spec the same day; operator answered its Q5 with decompose-directly).
  Epic 8 cleared to dispatch; Epic 9 queued behind its own Story 9.1 definition gate.
  Prior review 2026-08-10 (Phase 2 audit) — false Status lines corrected to done,
  rollup keys fixed via Tier-3+sync; see planning-artifacts/implementation-readiness-report-2026-08-10.md.'
epics_role: canonical
---

# pyforge-doctor - Epic Breakdown

## Fold provenance (2026-09-17)

Station Spec spec-pyforge-doctor reminted absorbed capabilities as CAP-1..76. Historical stories keep their sequential epic numbers (already 1..N with no gaps). This heading is the INV-A citation window: `spec-pyforge-doctor` CAP-1..76.


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

### Epic 13: Backlog-intake surfaces deferred entries during story drafting (added 2026-08-21)
Decomposes `spec-backlog-intake-check`, split from spec-deferred-work-resolution-sweep's former CAP-8 once Epic 11 shipped cleanly as its own self-contained pipeline. A tracked deferred-work entry naming an epic/story in its `owner:`/prose is surfaced as a candidate acceptance criterion when that epic/story is drafted, instead of staying inert prose only a human happens to notice by re-reading the ledger.
**CAP covered:** spec-backlog-intake-check CAP-1

### Epic 23: Leftover docs fold into Diátaxis (added 2026-09-14)
Decomposes `spec-docs-shelf-alignment` CAP-1..7. Residue of shipped Epic 22: indexes, fold cluster, sunset `docs/specs/` by status, intake route, archive citations, publish-root MAP rule, new leftover-shelf Doctor source.
**CAP covered:** spec-docs-shelf-alignment CAP-1..7

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
Marshal's marshal:AD-67. Splitting states the truth: the verdict is built and provably
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
2. `pyforge.doctor.sources.fleet_scan:650` does `from bmad_drift_check import …` for
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
**Surface:** `sources/factory.py`, `pyforge.doctor.sources.fleet_scan`, `tests/`

**Given** `pyforge.doctor.sources.fleet_scan` imports `GUILD_DREAMS`/`STATIONS` from
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
**Given** a `bmad-dev-auto` (the retired 6.x name of `bmad-build-auto`) review pass that defers work **When** the deferral is written
**Then** the entry carries an id under the station's own convention (`DW-FU-<story>` for
doctor/atlas/marshal/warden, `DW-<story>-<n>` for mason) from birth — an entry reaching
promotion without an id is already invisible to the promoter (CAP-1; edits
`.claude/skills/bmad-dev-auto/step-04-review.md` — the pre-6.11 path of the skill since renamed `bmad-build-auto` — allowlisted not governed).

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
`evidence:` bullet under a `bmad-dev-auto` step-04 marker comment (the retired 6.x name — a marker literal that parsers match, kept verbatim; atlas, 58 findings dating
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
the id-minting prose already living in `.claude/skills/bmad-dev-auto/step-04-review.md` (the pre-6.11 path; skill since renamed `bmad-build-auto`) into
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

**Epic 8 complete (7/7 stories, updated 2026-08-28).** The legacy deferred-work backlog now has a
real, mutation-tested tool (`classify_tier3_entries` + `mint_id_for_entry` +
`deferred_work_promote.py --fix` + baseline lockstep) replacing the error-prone by-hand process
that shipped two real bugs during the 2026-08-15 audit. Story 8.6 closed `DW-FU-8-4` and ran
`--fix` for real, fleet-wide: 373 orphans promoted across 5 projects (doctor/herald/marshal/
mason/steward), 3 clean no-ops (atlas/scribe/warden). Story 8.7 extended the same tool to
already-identified-but-untracked entries and ran it again: 65 more promoted across 5 projects
(atlas/doctor/marshal/mason/steward), 3 clean no-ops (herald/scribe/warden). `deferred-work-check`
dropped from 111 (session start) to **5** — atlas `DW-6`, scribe `DW-1..4`, traced to
spec-frontmatter fingerprint drift after the original Tier-3 harvest (see Story 8.7's own Outcome
and the spec's Non-goals), a fingerprint-algorithm/fuzzy-matching design question, not a
promotion-tool gap — named as future work, not carried forward silently.

### Story 8.5: The detector recognizes content that already reached the ledger by another path
**Type:** bug • **Effort:** S • **Deps:** S-8.1 • **FR/AD:** FR-15 (spec-deferred-work-visibility, CAP-11)
**Surface:** `pyforge-doctor` `sources/chain.py` (`_check_project_deferred_work` and two new
helpers), `tests/unit/test_sources_chain_deferred_work.py`
**Note:** found live 2026-08-28 during a fleet-wide hygiene sweep: `deferred-work-check` FAILed
117 `tier3-only-deferral`/`tier3-entry-unidentified` findings across doctor/marshal/mason/
scribe/steward/atlas. Investigating pyforge-atlas's own findings confirmed a real ID-vs-content
mismatch class DW-FU-8-4's own write-side collision guard (Story 8.3) already defends against on
the write side, but the read-side detector had no analogue: Tier-3 line 7's `summary:` text is
byte-identical to its own tracked `DW-A1-6`, and `DW-10` (no `summary:` field) carries an
`origin: spec-deferred 8b4c28559f93` marker already present in the tracked ledger via the
CAP-8 spec-frontmatter bridge — both under completely different, independently-minted ids.
**Given** a Tier-3 entry the id/position-based checks are about to flag **When** its normalized
summary or its harvest-damping fingerprint already appears in the tracked ledger **Then** it is
not flagged — mirroring `deferred_work_promote.py`'s own `_validate_batch` guard (summary) and
CAP-8's own `frontmatter_deferral_in_tracked` (fingerprint) exactly, no new mechanism invented.
**Explicitly bounded:** closes 6 of the 117 live findings (all pyforge-atlas), confirmed via
`git stash` A/B testing; the remaining ~111 are NOT claimed resolved — Epic 8's own "bounded and
shrinking, not an ongoing leak" framing already covers them as known, deliberately-deferred
backlog (the first real fleet-wide `--fix` run, blocked on `DW-FU-8-4`'s own redesign), not a new
gap this story leaves open.

### Story 8.6: DW-FU-8-4 closes — the collision-abort redesign, plus the parsing gap it surfaced
**Type:** bug • **Effort:** M • **Deps:** S-8.4, S-8.5 • **FR/AD:** FR-15 (spec-deferred-work-visibility, CAP-12)
**Surface:** `scripts/deferred_work_promote.py` (`_BatchValidation`, `_validate_batch`,
`_promote_project`), `pyforge-doctor` `sources/chain.py` (`_consume_bulleted_field_block`),
`tests/scripts/test_deferred_work_promote.py`, `tests/unit/test_sources_chain_deferred_work.py`
**Note:** completes the "real fleet-wide `--fix` run" Epic 8's own closing note left explicitly
out of scope, blocked on `DW-FU-8-4` (logged at Story 8.4's landing): once a project promotes
once, the whole-batch-abort guard fires forever on the OLD, already-promoted orphan's own
now-expected re-collision, permanently blocking any genuinely NEW orphan added later. Live-
confirmed against all 8 real fleet projects at Story 8.4's landing — every one would abort
outright if `--fix` were run unscoped.
**Given** a project's orphan batch where some entries' content already reached the tracked
ledger by another path (an old, already-promoted orphan re-colliding against its own tracked
twin) **When** `--fix` runs **Then** those entries are silently excluded from the write (never
re-promoted) while the REST of a clean batch — including a genuinely new orphan added since the
last run — still promotes; any OTHER collision (duplicate id, blank summary, a genuinely new
duplicate summary within the batch) still hard-aborts the whole batch, unchanged.
**Given** the fixed tool run for real **When** it processes doctor's/steward's live Tier-3 files
**Then** a second, independent parsing bug surfaces: `_consume_bulleted_field_block` truncates a
header-owned entry whose fields are EVERY ONE its own dashed bullet (no indented-continuation
lines) at the second bullet, because any `_BULLET_START_RE` match is treated as a block-ending
sibling — even one whose own key is a recognized field of the SAME entry (doctor's
`DW-FU-12-4/5/5-2`, steward's `DW-FU-11-4`, all real, live-confirmed truncations). Fixed:
`entry_id is not None` (header-owned) now checks `_KNOWN_FIELD_KEYS` first — a known-keyed
dashed bullet is a continuation, not a new sibling; headerless blocks (`entry_id is None`) are
untouched.
**Status:** done

**Outcome (2026-08-28).** Both fixes landed together (the parsing bug was found investigating
why 4 real entries misclassified after the collision-abort redesign already worked in isolation
on synthetic fixtures). Adversarial review (2 independent agents, mutation-tested against the
true pre-fix code on both files) found no HIGH/MEDIUM defects in either change; confirmed the
`already_minted` id-reservation set is populated before validation, so an excluded
already-tracked entry's id stays correctly reserved for the rest of the batch; confirmed
`to_write` empty short-circuits before the race-check/write/baseline-restamp block, so a
fully-already-tracked project has zero side effects. One LOW residual (not live, not exercised
anywhere in the fleet's 8 real files) documented in the review: a header-owned block ending in a
known-keyed bullet immediately followed (no blank line) by a genuinely separate headerless entry
whose own first bullet also uses a known key would be misabsorbed as a continuation — no such
shape exists live today. **Process note, not a code defect:** the two review agents ran real,
mutating `--fix` commands against the SAME shared (non-isolated) working tree concurrently,
producing a transient "unreproducible collision" and a duplicate write that looked like a race
in the script — actually two of my own agents stepping on each other's writes/reverts in shared
state. Resolved by re-running the fleet-wide `--fix` once, cleanly, myself, in this session, no
concurrent agents: doctor +72, herald +12, marshal +196, mason +21, steward +72 promoted
(zero duplicate ids, heading counts match promotion counts exactly); atlas/scribe/warden clean
no-ops (all orphans already tracked). **Explicitly bounded:** `deferred-work-check`'s combined
`tier3-only-deferral`/`tier3-entry-unidentified` count drops from 111 (post-Story-8.5) to 70 —
all 70 remaining are already-identified Tier-3 entries (real `DW-*` ids, real `status:`/
`severity:`/`source_spec:` fields) that were simply never copied to any tracked ledger, a
structurally different gap `deferred_work_promote.py`'s orphan-only scope does not cover (see
the spec's Non-goals) — not claimed resolved by this story, named as a future capability.

### Story 8.7: The promoter learns to copy already-identified-but-untracked entries too
**Type:** feature • **Effort:** M • **Deps:** S-8.6 • **FR/AD:** FR-15 (spec-deferred-work-visibility, CAP-13)
**Surface:** `scripts/deferred_work_promote.py` (`_promote_project`, `_format_promoted_entry`,
`_describe_counts`), `tests/scripts/test_deferred_work_promote.py`
**Note:** closes the gap Story 8.6's own closing note named as future work: an entry that
already carries a real `DW-*` id in Tier-3 but has no tracked twin was never touched by any
tool — `deferred_work_promote.py`'s `orphans = [e for e in entries if e.id is None]` filter
excluded it by design (Story 8.1-8.4's own stated scope).
**Given** an already-identified Tier-3 entry whose id is not yet a real `### DW-*:` header
anywhere in the tracked ledger **When** `--fix` runs **Then** it promotes verbatim under its own
id (no minting), folded into the SAME batch/validate/write pipeline orphans already use — one
combined message, one combined atomic write.
**Given** the fixed tool run for real **When** it processes the live fleet **Then** two real
bugs surface before the run ever touches real data, both caught by this story's own adversarial
review: (a) `Tier3Shape.IDENTIFIED_PLAIN` entries (bmad-loop's harvest-damping AND
follow-up-review-budget outputs, two independently-emitted shapes) carry no `summary:` field —
the pre-existing blank-summary guard hard-aborts the WHOLE project batch on just one, not merely
excludes it; live-confirmed this would have blocked 5 of 8 projects' entire batches (not just the
2 the first review pass found — a follow-up dry check across all 8 projects, run AFTER the first
review's fix landed, found the SAME bug under a second, independently-emitted origin value on 3
more projects). Fixed by generalizing the exclusion from "origin starts with spec-deferred" to
"blank/whitespace-only summary", regardless of origin. (b) the untracked-membership check used a
LOOSE `DW-`-shaped token harvest over the tracked ledger's raw text (matching a bare prose
mention, not just a real header) — reproduced live: an id merely referenced in someone else's
text was silently classified "already tracked" and permanently skipped, no warning, the exact
"silently never promoted" failure class this story exists to close. Fixed by checking real
`### DW-*:` headers instead.
**Status:** done

**Outcome (2026-08-28).** Two rounds of 2-agent adversarial review (round 1: general correctness
+ live fleet-safety, both isolated to `tmp_path` fixtures per explicit instruction, no repeat of
Story 8.6's own concurrent-writer incident; round 2: not re-reviewed, self-verified via a direct
read-only dry simulation against all 8 real projects after generalizing the blank-summary fix,
confirming zero remaining blank summaries and zero in-batch duplicate summaries anywhere before
running `--fix` for real) found and fixed one HIGH (independently reproduced by both round-1
reviewers) and one MEDIUM, both above, plus a real gap the round-1 reviews did not catch (the
`review-budget-followup` origin, found only by a broader post-fix fleet-wide dry check). Real
fleet-wide `--fix` run, all 8 projects, one clean pass, zero `ABORTED` outputs, zero duplicate
ids (heading-count-added matches promotion-count exactly per project): atlas +5, doctor +25,
marshal +12, mason +12, steward +11 already-identified entries promoted (65 total);
herald/scribe/warden clean no-ops (everything already tracked). Baseline correctly untouched
(0 orphans freshly promoted this run — the trigger stays scoped to "at least one orphan actually
landed in `to_write`", unchanged from Story 8.4's own intent, confirmed by a round-1 reviewer).
**Explicitly bounded:** `deferred-work-check`'s combined `tier3-only-deferral`/
`tier3-entry-unidentified` count drops from 70 to **5** (atlas `DW-6`, scribe `DW-1..4`) — traced
to spec-frontmatter fingerprint drift (the underlying finding was edited after the original
Tier-3 harvest, so the LIVE spec now derives a different fingerprint for the byte-identical
summary text than the one embedded in the stale Tier-3 bullet; `deferred_work_intake.py`
confirms it already promoted the current version under the new fingerprint). Reconciling a
stale-fingerprint Tier-3 reference against its own already-promoted twin is a fingerprint-
algorithm or fuzzy-matching design question — named as a future capability, not claimed resolved
by this story.

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
Finding names both versions (CAP-2). **Resolved and done** (2026-08-15, PR #554) — was blocked
on the Spec's Open Question of "how is the latest release sourced" (no npm-registry-lookup
infrastructure existed in this fleet; atlas's `behind-upstream`/`version-downloads` machinery is
conda-forge/PyPI-scoped only, and a live network query at check time cuts against Marshal's own
"no live query per home" discipline this fleet otherwise favors). Operator decision: a live npm
registry query at check time, scoped narrowly to this one warn-only, non-gating Finding — fails
open (no Finding, no error) if the query is unreachable. **Deps:** S-10.1.

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

**CAP-8 (backlog-intake surfaces deferred entries during story drafting) split out, 2026-08-21.**
Formerly Story 11.8 here. The Spec's own Open Question on CAP-8's scope boundary — same story
wave as CAP-1..7, or its own follow-on Spec, since it is write-adjacent to story-drafting, a
different subsystem than the read-only sweep CAP-1..7 are — is now resolved: **own follow-on
Spec**, decided once Epic 11 shipped cleanly as a self-contained read-only pipeline (11.1–11.7,
all done) and bundling a write-adjacent capability into it would have muddied that result. No
follow-on Spec/Dream exists yet — tracked in `deferred-work-ledger.md` (`DW-11-8-1`) rather than
silently dropped. `spec-deferred-work-resolution-sweep`'s own CAP-8 entry updated to match.

**Epic 11 clears to dispatch, and is now fully shipped, on Stories 11.1–11.7** (a natural
pipeline, each depending on the last) — CAP-8 was never part of that pipeline's own scope.

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

## Epic 13: Backlog-intake surfaces deferred entries during story drafting

**Spec binding.** Decomposes `spec-backlog-intake-check` (this station's `specs/` dir; split
2026-08-21 from `spec-deferred-work-resolution-sweep`'s former CAP-8, owner-dream
`docs/dreams/deferred-work-resolution-sweep.md`). Trigger mechanism resolved in that Spec's
Assumptions (not left as an Open Question): a `pyforge.doctor.sources` detector / `doctor` CLI
verb, invoked manually by a drafting session — matching every other Doctor capability's shape,
not a hook into `bmad-create-story` (retired in 6.11)/`bmad-create-epics-and-stories`'s own prompt instructions.

### Story 13.1: A drafting session surfaces matching deferred-work entries for an epic
**Given** an epic or story identifier named at invocation **When** the new detector/verb runs
**Then** it scans tracked `deferred-work-ledger.md` files fleet-wide for entries whose
`owner:`/prose precisely names that epic or story id — a parsed id token, never a bare
string-contains check, per the Spec's own constraint (avoids repeating `DW-CHAIN-COMPLETENESS-1`'s
substring-membership bug, Story 12.3's own fix target) — and surfaces each match as a candidate
acceptance criterion with its source ledger, entry id, and summary, for the drafting session to
accept, reject, or reword. Nothing is auto-written into the story/spec (CAP-1). **Deps:** —

**Epic 13 clears to dispatch** — one story, no dependencies, concrete.

## Epic 14: The bmad-suite's lag is as visible as the core's

Decomposes `spec-bmad-method-version-drift` **CAP-4** (added 2026-08-21, superseding the
former "core only" non-goal). Motivating evidence, from the live 6.10.0→6.11.0 upgrade
session: `bmad-loop` sat at 0.9.0 against upstream 0.11.0 — 0.9.0 hardcodes
`/bmad-dev-auto` and stalls every unattended session on BMAD ≥ 6.11 (upstream's 0.9.1 was
an emergency hotfix for exactly this) — while TEA lagged 1.19.1 vs 1.23.2 (1.19.1's
`tea-test-review` bin was published empty). None of it produced any ambient signal; Epic
10's detector watched only the core, and the suite's coordinated ecosystem waves (skill
rename, uv-run conversion, `persistent_facts`/AGENTS.md) went by invisibly until a human
checked. Steward's `spec-bmad-method-core-upgrade` (Epic 14 there, same day) owns acting on
the signal; this epic owns the signal.

### Story 14.1: The bmad-suite is compared against upstream, derived not declared
**Given** the `bmad-*` pins present in `pixi.toml` (the watched set is DERIVED from those
pins — a hardcoded list omits exactly the newest tool) and the versions actually installed
in the pixi environments **When** doctor's report or `fleet-picture` runs **Then** each
suite package behind its latest upstream release yields a warn-only Finding naming both
versions, through the same fail-open live-query exception Story 10.2's operator decision
already granted (unreachable ⇒ no Finding, no error, never gating) and the same ambient
surfaces as Story 10.3 — proven by a fixture of the 2026-08-21 pre-update state naming
`bmad-loop 0.9.0 < 0.11.0` and `TEA 1.19.1 < 1.23.2` (CAP-4). **Deps:** —

## Epic 15: The suite pipeline's drift is ambient at every stage

Decomposes `spec-bmad-suite-channel-product` **CAP-5** (steward-owned chain, detection
relayed here per the version-drift split — same day as steward Epic 15). Extends Epic 14's
suite check from installed-env-vs-npm to the full pipeline: the channel served a stale
bmad-method 6.3.0 for four months and 7 of 10 watched packages are npm-invisible.

### Story 15.1: GitHub releases unblind the npm-invisible packages
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-channel-product CAP-5 (closes doctor DW-14-1-1)
**Surface:** `sources/bmad_method.py` suite pass
**Given** the 6-7 GitHub-only suite packages (bmad-loop first — the package whose lag
motivated CAP-4) **Then** upstream latest falls back to GitHub releases/tags through the
same fail-open budget, `packages_checked` rises accordingly, and the DW-14-1-1 fixture
(bmad-loop named from GitHub) passes.

### Story 15.2: Channel and recipe staleness are ambient findings
**Type:** feature • **Effort:** S • **Deps:** S-15.1 • **FR/AD:** spec-bmad-suite-channel-product CAP-5
**Surface:** `sources/bmad_method.py` (new stages), fleet-picture ATTENTION
**Given** api.anaconda.org's SelfExplainML listing and `recipes/*/recipe.yaml` versions
**Then** channel-vs-recipe and recipe-vs-upstream drift are warn-only findings on the
same surfaces as Stories 10.3/14.1 — a fixture of the bmad-method 6.3.0 relic fires
channel-drift; offline degrades silently.


## Epic 16: Sibling dreams directories don't drift silently

Decomposes `spec-sibling-dreams-drift` CAP-1 (seeded 2026-08-22 from the seven-repo
analysis — the sibling PyForge instantiation shares 13/15 dream titles, independently
evolving, owners diverging).

### Story 16.1: The shared-title diff is an ambient finding
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-sibling-dreams-drift CAP-1
**Given** local `docs/dreams/` and the sibling's (operator token) **Then** a doctor source
reports shared titles with diverging status/owner/content-hash — warn-only, fail-open
unreachable, no sibling prose stored — on the doctor report + fleet-picture ATTENTION;
fixture reproduces the 2026-08-22 demonstrated drift; offline yields nothing.

## Canopy obligations (2026-08-24)

**Owner:** `pyforge-steward` owns the Canopy (`src/platform/` host). Doctor is spoke #5; the
Canopy is not a ninth station.

**Build surface:** Doctor's CLI chain ends at **Epic 16**. **Epic 17** is the CAP-18 gather/prescribe hook (not a Canopy remint). **Epic 18** (2026-08-25) is station-owned SKF skill, persona, and first portal job. Host MCP mounts and empty portal *shells* remain steward 19/21. Do **not** copy steward Epics 18–30.

**Five-tier symmetry (current → obligation):**

| Tier | Today | Canopy obligation | Steward epic |
|------|-------|-------------------|--------------|
| CLI | `doctor` console script (Epics 1–16) | Remains `doctor`; also reachable as `pyforge doctor …` | 22 |
| Web portal | absent | `/stations/doctor/`; triple `django-doctor` / `django_doctor_<app>` / `doctor_<app>` | 19 |
| Service/MCP | in-process MCP **client** (AD-6) | `POST /stations/doctor/mcp` on host ASGI; official `mcp` SDK; dual-era | 21 |
| Domain skill | absent | SKF skill from `pyforge-doctor/` — **doctor Epic 18** | 18 (not steward 29) |
| Agent persona | absent | BMAD persona consults doctor domain skill — **doctor Epic 18** | 18 |

**Constraints (binding on doctor participation):**

- No second chrome — portals use `django-pyforge` only.
- No extra public port — MCP is an in-host ASGI seam, not a standalone FastAPI process or
  `services/` tier.
- No `pyforge.*` import under `src/platform/` — portal reaches doctor only through
  `django-pyforge`'s HTTP client.
- If doctor publishes cross-station events, they ride `pyforge.events` on redis-broker (Epic 24)
  with a CloudEvents envelope — no ad-hoc bus.

**Shipped work stands:** Epics 1–16 and `spec-pyforge-doctor` CAP-1..9 remain the station
contract. Canopy tiers do not reopen CLI gather/prescribe semantics (AD-1..AD-6, NFR-1..5).
Pre-audit Dream prose (`doctor_portal`, `:8008`, `services/pyforge-doctor/`) is superseded by
Grounding (2026-08-24).

**Phase 5 scope:** This block records doctor's Canopy *shell* obligations (chrome, MCP mount).
Skill, persona, and the first portal job are **Epic 18**. Cite **parent AD-n** vs **canopy AD-n**.

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (canopy:AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Doctor-local:** Remedy and linter hooks are station plugins (Story **17.1**). Doctor findings are advisory or Warden inputs — they must not become a second PR gate. SLO burn for the deferred scorecard is consumed here later, not invented now.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`change-history/sprint-change-proposal-2026-08-24-hook-specs.md`;
steward `sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`.

## Epic 17: Gather/prescribe hook spec

**FR-45.** Deps: steward S-32.1. Not a PR-gate epic.

### Story 17.1: Extract gather/prescribe source plugins

As a doctor operator,
I want diagnosis sources and remedy actuators as plugins on the shared contract,
So that swapping a linter or gather source does not fork doctor.

**Type:** feature • **Effort:** M • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy:AD-21
**Given** today's gather/prescribe backends **When** the hook spec lands **Then** they are the default plugins
**And** findings remain advisory or Warden *inputs*, never a competing PR verdict

## Epic 18: Doctor owns its skill, persona, and one portal job

Does **not** copy Canopy 18–30. Empty `/stations/doctor/` shell stays steward 19.

### Story 18.1: SKF domain skill and BMAD persona for doctor

As an autonomous agent,
I want a doctor SKF skill from `pyforge-doctor/` and a `bmad-agent-doctor` persona,
So that Path B uses CAP-5 grammar and CAP-4 MCP only.

**Type:** feature • **Effort:** L • **Deps:** S-17.1 • **FR/AD:** canopy FR-37, FR-38 • canopy:AD-17
**Given** steward 29 proved the shape **When** this story completes **Then** SKF compiles from `src/shared/packages/pyforge-doctor/` if missing
**And** the persona uses only `pyforge doctor …` and `POST /stations/doctor/mcp`
**And** findings stay advisory — not a second PR gate

### Story 18.2: First portal slice — last fleet pulse

As a doctor operator,
I want `/stations/doctor/` to show the last `doctor monitor --fleet` summary,
So that one operator job works in HTMX on the host.

**Type:** feature • **Effort:** M • **Deps:** S-18.1 • **FR/AD:** canopy FR-10 • canopy:AD-7
**Given** an authenticated doctor-role session **When** the operator opens `/stations/doctor/` **Then** the pulse summary renders via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy

## Epic 19: Suite drift matches the channel catalog (registry-aware upstream)

**Spec binding.** Decomposes operator-authorized follow-on to Epic 15 Stories 15.1/15.2 and
steward `spec-bmad-suite-metapackage` CAP-1 (shared `recipes/bmad-suite/suite-members.yaml`).
Closes the npm-stale blind spot (builder/CIS/dashboard) and the `mybmad-dashboard` prefix gap.

### Story 19.1: The suite watched set matches the channel catalog and upstream follows recipe registry

As a factory operator,
I want doctor's ambient bmad-suite drift to watch every SelfExplainML channel product and resolve
upstream from each recipe's declared registry class,
So that GitHub-canonical packages warn when recipe or install lags upstream — not only TEA.

**Type:** feature • **Effort:** M • **Deps:** steward `spec-bmad-suite-metapackage` CAP-1 (manifest)
**Given** the 13-member suite manifest and live upstream **When** `doctor check --bmad-core` runs
**Then** builder/CIS/TEA recipe-upstream drift WARNs when behind GitHub/npm truth respectively
**And** `mybmad-dashboard` is in the watched set when manifest-present
**And** findings stay warn-only, never gating

## Epic 20: Doctor reads the whole suite and guards the estate's two blind spots

**Spec binding.** The doctor-side relays of `spec-bmad-suite-lifecycle` (Dream
`docs/dreams/bmad-suite-lifecycle.md`, 2026-09-06): CAP-9's two missing detectors (G7 render-HALT,
G11 `frozen-path-changed`), the suite-drift residual the core-upgrade Spec relayed as its open
question Q1 (7 of 13 members mapped), the `bmad-os-root-cause-analysis` routing (CAP-3), and the
version-drift Spec's open-question write-back. **HARD boundaries:** every finding stays advisory —
`warn` at most, never a second PR verdict (lifecycle spine AD-4; doctor Charter § 6); sources are
read-only gathers; the detectors join `detectors` only after their fixtures prove fail-open.

### Story 20.1: Suite drift maps every active member, derived from the roster
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-method-version-drift CAP-4 (residual) • spec-bmad-suite-lifecycle CAP-8 • `DW-FU-14-1-2` kin
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` (per-`recipe.yaml` `cfe-source-kind` derivation and its probe fetchers), `tests/unit/test_sources_bmad_method.py`, `recipes/bmad-suite/suite-members.yaml` (read for the member roster, never edited)
**Given** `bmad-suite-upstream-drift` checks 7 of 13 members because commit-pinned and npm-invisible members have no mapped upstream probe **When** the member set is derived from each member's own tracked `recipes/<name>/recipe.yaml` source kind (tag → GitHub releases/tags, commit-pinned → GitHub default-branch HEAD with the `X.Y.Z.dev0 @ sha` encoding, npm → npm) — `suite-members.yaml` carries the roster but no registry/probe-class field, so it cannot be the derivation source **Then** `packages_checked` reads 12 (`pyforge-core` is not a suite member and is excluded — see this story's spec Design Notes, "Why 12, not 13"), each member names its probe class in the finding evidence, the fail-open budget is unchanged, and a fixture of the 2026-08-21 bmad-loop lag (0.9.0 vs 0.11.0) fires `warn`

### Story 20.2: The render-HALT class has a detector
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-lifecycle CAP-9 (G7, P8) • customization-inventory C2
**Surface:** `sources/bmad_method.py` (or a sibling `bmad_config.py` source), `tests/unit/`, `pixi.toml` (`detectors` membership after fail-open proof; six blanket-glob specs → memlog + scoped stamps)
**Given** `render_skill.py` HALTs with "ambiguous config value" when the same key sits at two paths across the four `_bmad/config*.toml` + `_bmad/custom/config*.toml` layers (seen live 2026-09-06) **When** the detector merges the layers the way `load_central_config()` does and scans for a key present at two different paths **Then** it reports `warn` naming the key and both paths, `ok` on today's tree, a fixture with a planted `[core] user_skill_level` beside `[modules.bmm] user_skill_level` fires, and a missing layer file is fail-open

### Story 20.3: `frozen-path-changed` exists
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-suite-lifecycle CAP-9 (G11) • cutover spine `fnd:AD-11`, `fnd:AD-22`
**Surface:** a new source under `sources/` (reads `docs/foundry/manifest.*` capability ledger states when present; `ok` with "no ledger" otherwise), `tests/unit/`, `pixi.toml` (`detectors-ci` membership), cutover memlog relay note
**Given** `fnd:AD-22` freezes a capability's source paths once it enters `rebuilding` or `moving`, and the spine names a `frozen-path-changed` detector nothing built **When** the detector reads the capability ledger's frozen path sets and diffs `origin/main..HEAD` against them **Then** a change under a frozen path is a `fail` naming the capability and the path, an absent ledger is `ok` (pre-cutover), and the fixture plants one frozen-path edit; `cutover-readiness.md` G11 flips to landed by steward memlog relay

### Story 20.4: `bmad-os-root-cause-analysis` is doctor-wielded
**Type:** docs • **Effort:** XS • **Deps:** — (after steward 46.2 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-3 • lifecycle spine AD-2
**Surface:** `.claude/skills/bmad-agent-doctor/SKILL.md` (routing line), the register § 2 row (AGENTS.md carries one pointer line to the register, placed once by `bmad-project-context` — never per-skill lines, AD-2/AD-11), `adoption-register.md` § 2 row
**Given** the skill installed by steward 46.2 **When** the doctor persona gains "reach for `bmad-os-root-cause-analysis` when a detector finding needs a cause, never to change a verdict" **Then** the register names doctor as its sole wielder, the register row names it and the AD-2 meta-test passes, and CLAUDE.md is untouched

### Story 20.5: The version-drift Spec's open questions are written back
**Type:** docs • **Effort:** XS • **Deps:** — • **FR/AD:** spec-bmad-method-version-drift (body § Open Questions) • memlog entry of 2026-09-06
**Surface:** `specs/spec-bmad-method-version-drift/SPEC.md` (via `bmad-spec` update from the memlog), its `.memlog.md`
**Given** the two Open Questions (CAP-2's data source; registry placement) answered in practice by Epic 10 and recorded in the memlog on 2026-09-06 **When** `bmad-spec` update re-derives the SPEC **Then** § Open Questions is empty, the answers appear as constraints or assumptions, `status: shipped` survives the derive, and `dream-chain-check` / `spec-surface-check` stay ok


## Epic 21: Realization-gate hygiene (fleet readiness 2026-09-09)

**Spec binding.** The doctor half of the fleet-readiness decision batch
(`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`,
operator-approved 2026-09-09 — § 2.3 **C8**, § 2.4 **D1/D2/D3/D5**, and the Class B doctor rows).
Two things bind here that a Class-B status flip cannot: every `board.py` / `chain.py` /
`sibling_dreams.py` change in C8 is **code**, so it lands as a story, never as a Spec edit; and the
two Specs minted this pass from new doctor Dreams (`spec-capability-effect-check`,
`spec-status-body-consistency`) carry the batch's own realization gate into doctor's chain.
Covered Specs: `spec-fleet-hygiene-verification-exemplar-program` (CAP-3's defect class, reached by
a third route), `spec-sibling-dreams-drift` (CAP-1 re-keyed), `spec-pixi-candidate-currency` (CAP-4),
`spec-deferred-work-resolution-sweep` (CAP-9), `spec-capability-effect-check` (CAP-1..3),
`spec-status-body-consistency` (CAP-1..5), plus `spec-pyforge-doctor`'s own `sources/board.py`
registry scope. **HARD boundaries, unchanged:** every finding stays advisory — `warn` at most, never
a second PR verdict (`pyforge.doctor.verdict.exit_code_for` is the sole exit-code owner, pinned by
`tests/meta/test_verdict_sole_ownership.py`); every source is a read-only gather (NFR-1); a new
detector joins `detectors` only after its fixture proves it fails **open** and says so.

### Story 21.1: `DEFERRED_SPECS` stops reading as a live exemption when it is not one
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-doctor (owns `sources/board.py`) • batch § 2.3 C8 • doctor-B1 • guild-E2 • warden-E1 • mars-A-E2
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` (the `DEFERRED_SPECS` dict at `:87-135` and its exit-rule comment at `:84-86`), `tests/unit/test_sources_board.py`
**Given** the guard at `board.py:716` is `if status not in OPEN_SPEC_STATUSES or slug in DEFERRED_SPECS: continue`, so an entry naming a Spec outside `{draft,ready,in-progress}` suppresses nothing while still reading as a live exemption to every human and agent who greps it (audited 2026-09-09: **3 of 7** entries in that state) **When** the dict is reconciled against live Spec statuses and given a stated invariant **Then** `spec-agentic-sdlc-autonomy` and `spec-artifact-chain-reconciliation` are deleted; `spec-chain-currency-sweep` is deleted **iff** its Spec reads a terminal status at implementation time (it flips to `shipped` this same pass); the `spec-golden-path-conda-blind-spot` entry's open-question list is corrected to the Spec's actual five (**selector grammar, provisioning, coverage floor, warn-promotability, unscoped-union default** — `spec-golden-path-conda-blind-spot/SPEC.md:13-17`; only the first two of the four currently listed match), its de-registration criterion kept verbatim; the `spec-intelligence-hub` entry's rationale drops the factually wrong "only nebari-infrastructure-core is absent" clause (`recipes/nebari-infrastructure-core/recipe.yaml` landed 2026-09-07) and the entry is de-registered **iff** that Spec reads `ready` at implementation time; `spec-pyforge-charter` is **registered** with the reason "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties no story can pick up" (`in-progress`, eight capabilities, zero epics, zero ledger keys, registered nowhere today); the comment above the dict carries the invariant *every slug in this dict names a Spec whose `status:` is in `OPEN_SPEC_STATUSES`* plus the second exit condition the rule lacks (*or its Spec reaches a terminal status, at which point `:716` exempts it anyway*); and a unit test asserts every entry's named Spec resolves to an open status, so the next inert entry fails the suite instead of accumulating

### Story 21.2: A Spec with no `status:` line is a finding, not a silent exemption
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-fleet-hygiene-verification-exemplar-program CAP-3 (the same defect class, third route) • batch § 2.3 C8 • doctor-B5
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` (a new branch before `:716`), `tests/unit/test_sources_board.py`, doctor's `report-schema.json` if the check name is enumerated there
**Given** `board.py:715` reads `status = str(_frontmatter_from_text(spec_text).get("status", "")).strip()` and `:716` `continue`s when it is not in `OPEN_SPEC_STATUSES`, so a **missing** `status:` key fails the membership test and silently exempts the Spec — **8 fleet-wide, 4 of them doctor's own**, and one (`spec-pixi-candidate-currency`) has 5 of 5 declared CAPs uncovered by any epic or FR while `chain-completeness` reports `ok` **When** the absence of the key is separated from a declared-terminal status **Then** a `spec-status-missing` finding names the Spec with the remedy "add a `status:` line, or add the slug to `DEFERRED_SPECS` with the reason"; every declared-but-terminal status (`shipped`/`archived`/`absorbed`/`superseded`/`extension-point`) stays exempt exactly as today; **no implied status is guessed** (treating absence as `draft` would red `spec-pyforge-marshal` and `spec-pyforge-mason`, two effectively-shipped station flagships, for a bookkeeping omission); the branch mirrors the Dream-side check that already exists (`chain.py:993`, `Dream {slug!r} has no status: in frontmatter`); and a fixture carrying a status-less SPEC.md fires while today's tree — after the Class-B flips of this same pass — reports zero

### Story 21.3: `sibling-dreams-drift` joins on the key the two trees actually share
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-sibling-dreams-drift CAP-1 (re-keyed) • batch § 2.2 doctor-B4
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` (`:118`, `:155`, `:189`, `:194`, and the fail-open returns at `:45`/`:48`), `tests/unit/test_sources_sibling_dreams.py`
**Given** the detector keys both fingerprint maps on frontmatter `title:` while the sibling tree shares **0 titles and 8 filenames** (measured live 2026-09-09 with the operator's token: 131 local Dreams parsed, 15 sibling), so Story 16.1 is `done` and the capability is structurally incapable of a live finding **When** the join moves to the filename slug, with `title` demoted to a compared axis **Then** `_local_fingerprints` and `_fetch_sibling_fingerprints` key on the path stem, `_diff_shared_titles` intersects on slug, `title` joins `("status","owner","content_hash")` in the compared axes, and the eight shared filenames report their real divergence (at least `developer-machine-bootstrap`, local `specified` vs sibling `dreamt`); the token-absent and fetch-failed paths emit a warn-only `sibling-dreams-unreachable` finding naming the reason instead of `return ()`, so "could not look" never renders as "looked and agreed"; and the unit test is rebuilt on the **real** 8-shared-filename shape rather than today's single synthetic `_DECK_TITLE`, which by construction cannot reproduce the live failure

### Story 21.4: `CONSTITUTIVE` is derived from the roster, not hardcoded beside it
**Type:** feature • **Effort:** XS • **Deps:** — • **FR/AD:** spec-pyforge-charter CAP-3 (the constitutive-constant mirror) • batch § 2.3 C8 • guild-E1
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` (`:96` and its gate at `:634`), `tests/unit/test_sources_chain.py`
**Given** `chain.py:96` hardcodes `CONSTITUTIVE = frozenset({"pyforge-charter"})` while the same module already resolves statuses, types and stations from `docs/governance/guild-roster.json` through `_load_dream_roster` (`:838-852`), and the roster carries the authoritative `guild_dreams` list **When** `CONSTITUTIVE` is derived from that roster key the way the other three constants are **Then** the last unguarded mirror of a constitutional constant is gone (the "derive, don't declare" rule the roster consolidation was introduced to enforce), the gate at `:634` is unchanged in behaviour for today's single-entry roster, a roster carrying a second `guild_dreams` entry is honoured without a code edit, and an unreadable/absent roster degrades to today's value with a named warn rather than an empty set

### Story 21.5: The deferred-work verifier resolves a project-relative `source_spec` from the project root
**Type:** bug • **Effort:** S • **Deps:** — • **FR/AD:** spec-deferred-work-resolution-sweep CAP-3/CAP-4 • batch § 2.4 D5 (HIGH) • herald-E3
**Surface:** the `source_spec` resolution in doctor's deferred-work verification path (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/` sweep modules and their `scripts/` entrypoint), `tests/unit/`, a regression fixture built from herald's `DW-FU-15-1`
**Given** the 2026-09-02 mechanical re-verification stamped herald's `DW-FU-15-1` *"source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open"* while the file is present — `source_spec` is recorded **relative to the project** (`planning-artifacts/specs/spec-15-1-…md`) and resolves at `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`, but the verifier resolved it from the repo root **When** the resolver tries the project root before declaring a path absent **Then** every entry using the project-relative `source_spec` form resolves, an entry is never re-stamped `still-open` on the strength of a path the verifier failed to find, a regression test over `DW-FU-15-1` pins the behaviour, and the verdict text distinguishes "spec absent" from "spec not located by this resolver" — this is the false-stamp class that re-marks resolvable entries open **without reading them**

### Story 21.6: `dreams-hygiene` reconciles every Dream file, and README:71 is enforced
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** batch § 2.4 D2 + D3 • mars-B-E5 • mason-E8 • atlas-E2 • warden-E2 • stB-F2
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` (`_parse_readme_dream_statuses` at `:891` and the `dreams-hygiene` gather around it), `tests/unit/test_sources_chain.py`
**Given** `_parse_readme_dream_statuses` reconciles only Dreams that already carry a `docs/dreams/README.md` row, so **61 of 131** Dream files are invisible to the detector while it reports `ok` (`readme-table-orphan` is one-directional by design: it catches rows pointing at missing files, never files missing a row) **When** reconciliation is derived from the Dream files themselves and the README is treated as the incomplete map it is **Then** a Dream file with no README row is a named warn-only finding; `docs/dreams/README.md:71` is enforced — a Dream at `status: specified` whose Spec is not at `ready` or beyond is reported (today `django-accelerator-framework` violates it and passes both `dream-chain-check` and `dream-chain --dreams`); every `[[…]]` Kinship wikilink is resolved against `docs/dreams/` and an unresolvable target is a warn naming the source file and the dead link (D3 — the 2026-09-09 currency review found broken links and no detector validates them); and each of the three new classes ships with a fixture proving it fires **and** a measured count against the live tier, so a class that would flood the report is narrowed before it joins `detectors` rather than after

### Story 21.7: The pixi candidate ledgers get their staleness check
**Type:** feature • **Effort:** S • **Deps:** `spec-pixi-candidate-currency` carries `status: ready` (added by `bmad-spec` from its memlog this same pass) • **FR/AD:** spec-pixi-candidate-currency CAP-4 • batch § 2.2 doctor-B6
**Surface:** a new `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py`, its entry in `sources/__main__.py`'s `DISPATCH`, `pixi.toml` (one `detectors` row + the task), `tests/unit/`, `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` if a wrapper is added
**Given** all five of `spec-pixi-candidate-currency`'s CAPs are uncovered by any doctor epic or FR, and CAP-4 — the advisory ledger-staleness check, the Spec's own linchpin (*"that answer is demonstrably still current … because CAP-4's staleness check would have flagged it otherwise"*) — has no module in `sources/` and no dispatch entry, while the drift it exists to catch is already live (the Dream audited 44 candidates over 64 commented dependency lines; `pixi.toml` has moved, with **45 commits** to it since the last currency pass) **When** the check ships as one small source **Then** it reports how far each of the Dream's four ledgers has fallen behind `pixi.toml`'s own commit history, the staleness threshold is a **declared policy value** rather than a literal buried in the module, the finding is `warn` at most and never gates (the fleet's one fail-closed gate is not doctor's), it degrades to a named finding when a ledger or `pixi.toml` cannot be read, and CAP-1/2/3/5 are left alone — they are descriptions of ledgers the Dream already contains, satisfied by its own content, not by code

### Story 21.8: Deferred-work intake refuses an entry that cites nothing checkable
**Type:** feature • **Effort:** S • **Deps:** `spec-deferred-work-resolution-sweep` carries `status: in-progress` + CAP-9 (added by `bmad-spec` from its memlog this same pass) • **FR/AD:** spec-deferred-work-resolution-sweep CAP-9 • batch § 2.2 doctor-B7
**Surface:** `deferred_work_intake.py` and its doctor-side module, `tests/unit/`
**Given** Epic 11 is 7/7 `done` while the Spec's own companion `sweep-tooling-effectiveness-2026-09-08.md` measures CAP-3 matching **0 of 1,410** entries, CAP-2 skipping **0** of 183 due entries, and CAP-6 finding 1 near-duplicate pair where a hand sweep found 4 defect classes — with the binding constraint measured as **144 of 183** never-verified entries citing no extractable path **When** intake refuses (or explicitly flags) an entry citing no resolvable `location:` **Then** a new entry with no checkable claim cannot enter a ledger silently, an entry already in a ledger is never rewritten (the sweep is read-only and stays so), the refusal names the missing field and what a resolvable one looks like, and the never-verified population stops growing — the companion's own recommendation #1, and the reason CAP-2/CAP-3/CAP-6 are left as written rather than rewritten to describe their own inertness

### Story 21.9: A capability with no caller outside its own tests is a finding
**Type:** feature • **Effort:** M • **Deps:** `spec-capability-effect-check`'s SPEC.md is derived by `bmad-spec` from its `.memlog.md` (the memlog is seeded; the SPEC.md is not written yet) • **FR/AD:** spec-capability-effect-check CAP-1 • batch § 2.3 C8 (the Story 49.2 relay) • § 2.3 C6 • mars-B-E6
**Surface:** a new source module under `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/`, `tests/unit/`, `tests/fixtures/`
**Given** the 2026-09-09 pass found eighteen capabilities of one shape — a `done` epic whose named success criterion has never been exercised — and three of marshal's four were visible only by grepping for call sites **When** the check joins on `(spec-slug, CAP-N)` (the pair `board.py`'s own `_parse_declared_cap_ids` / `_cited_cap_ids_by_spec` already produce for INV-A), reaches code through the citing story's `Surface:` line in the owning station's `epics.md`, and asks whether any symbol those surfaces define is referenced outside its own module and outside tests **Then** it names `risk-tiered-review-depth`'s `classify_review_tier` / `resolve_review_cycles` (zero callers outside `core/gate.py` and `tests/unit/test_gate.py`) as a **live** finding — the join proven against the real fleet before this story closes, not against a fixture that constructs both sides from one synthetic value (the `sibling-dreams-drift` failure, Story 21.3); a capability whose surfaces are documents rather than modules reports "not applicable, document surface" rather than a false "no callers"; the reach is a bounded whole-word textual scan and says so in the finding text; and an unreadable `epics.md` or an absent surface path degrades to a named finding, never to silence

### Story 21.10: A `verified:` line on a capability is read and rendered
**Type:** feature • **Effort:** S • **Deps:** Story 21.9 • **FR/AD:** spec-capability-effect-check CAP-2 • batch § 2.3 C8 • steward Story 49.1 (the realized-versus-verified column)
**Surface:** the same new source module, `tests/unit/`
**Given** the Unifying Strategy's 2026-09-09 review asked for a "realized versus verified" column and nothing produces one, so a capability's evidence — if anyone ever looked — lives in prose no detector reads **When** a CAP may carry `verified: <date> — <what was exercised, where>` on the capability itself in `SPEC.md` **Then** the check renders that line beside the capability, reports a `shipped`/`realized` capability that carries none, stays silent for a capability with a current line, and **never authors one itself** (read-only, NFR-1) — the column is produced mechanically from `SPEC.md` rather than hand-maintained in a research file that goes stale between passes

### Story 21.11: The effect check renders beside `story-status-check`
**Type:** feature • **Effort:** S • **Deps:** Story 21.9 • **FR/AD:** spec-capability-effect-check CAP-3 • batch § 2.3 C8
**Surface:** the same new source module's registration in `sources/__init__.py`, doctor's `report-schema.json`, `pixi.toml` (`detectors` membership + task), `tests/unit/`, `tests/meta/`
**Given** an operator reading "story 33.4 landed" today learns "and nothing calls it" three weeks later in a readiness pass **When** the source is registered and joins the `detectors` set **Then** one `detectors` run answers both questions on adjacent lines — did the story land, is the capability reached — the finding reaches the doctor report and the fleet-picture ATTENTION block, the two checks stay **separate modules with separate check names** (this is not a re-implementation of `story-status-check`), and the meta-tests still pass: the verdict stays sole-owned by `verdict.exit_code_for` (`tests/meta/test_verdict_sole_ownership.py`) and the new source imports no station package it judges (`tests/meta/test_source_independence.py`)

### Story 21.12: A body that says "3 of 9" under `realized` is a finding
**Type:** feature • **Effort:** M • **Deps:** `spec-status-body-consistency`'s SPEC.md is derived by `bmad-spec` from its `.memlog.md` (the memlog is seeded; the SPEC.md is not written yet) • **FR/AD:** spec-status-body-consistency CAP-1 • batch § 2.4 D1 • guild-E5 • scribe-E3
**Surface:** a new source module under `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/`, `tests/unit/`, `tests/fixtures/`
**Given** `bmad-drift-check` polices frontmatter vocabulary and counts and `dreams-hygiene` polices presence, so nothing polices whether a document's prose still agrees with its own `status:` — six documents failed that test in one 2026-09-09 pass **When** a bounded pattern reads "N of M stories/capabilities" (and the `N/M` form) with N < M under `status: realized|shipped|done` **Then** it fires on `docs/dreams/pyforge-scribe.md:69` (*"3 of 9 stories complete overall"* under `status: realized`) and on `spec-pyforge-scribe`, which repeats the same stale figure under `shipped`; the finding **names the line it read** and never renders a verdict on the document; it stays silent across the rest of the live tier, with that count recorded; and it is warn-only, read-only and fail-open — an unparseable document is a named finding, never silence

### Story 21.13: `open_questions: []` over a live memlog question is a finding
**Type:** feature • **Effort:** S • **Deps:** Story 21.12 • **FR/AD:** spec-status-body-consistency CAP-2 • batch § 2.4 D1 • guild-B1/E-5
**Surface:** the same new source module, `tests/unit/`
**Given** `docs/governance/spec-pyforge-charter/SPEC.md:16` declares `open_questions: []` while its companion `.memlog.md:9` carries an `(open)` question from 2026-07-31 that no later `(decision)` entry closes — and for this document it is not hygiene, because Charter CAP-2 makes the Lexicon's own integrity constitutional **When** a Spec's declared `open_questions` are reconciled against its companion memlog's last unclosed question entry **Then** the Charter's Spec fires with both line numbers cited; a Spec whose memlog question is followed by a closing decision does not; a Spec with no memlog is `ok`, not an error; and the check reports the contradiction without proposing text — reconciliation belongs to the `chain-currency-sweep` loop, never to the detector

### Story 21.14: Promissory language under a terminal status is measured before it ships
**Type:** feature • **Effort:** S • **Deps:** Story 21.12 • **FR/AD:** spec-status-body-consistency CAP-3 • batch § 2.4 D1
**Surface:** the same new source module, `tests/unit/`, and — if the signal is rejected — the Spec's memlog carrying the measured number
**Given** the herald Dream and `spec-pyforge-herald` both describe a mid-build station under `realized`/`shipped`, which no count- or vocabulary-based signal can catch, and that a loose narrative signal that cries wolf gets muted — and a muted detector is worse than none **When** a bounded forward-looking-language pattern is measured over the whole live tier **Then** it must both fire on the herald pair **and** stay quiet elsewhere before it joins `detectors`; if it cannot do both, the honest outcome is to ship it **measured-and-rejected** with the precision number recorded in the Spec's memlog rather than to widen the threshold until it looks clean; and either way the signal's measured precision at ship time is recorded beside it

### Story 21.15: A status comment that contradicts its own ledger is a finding
**Type:** feature • **Effort:** XS • **Deps:** Story 21.12 • **FR/AD:** spec-status-body-consistency CAP-4 • batch § 2.4 D1
**Surface:** the same new source module, `tests/unit/`
**Given** the `status: realized   # … → Epic 14 backlog` shape found live on `docs/dreams/bmad-method-version-drift.md` while `epic-14` reads `done` in the tracked ledger — the cheapest and most mechanical of this Spec's signals **When** a frontmatter status comment naming an epic or story key is reconciled against that key's live ledger row **Then** the contradiction is a warn naming both the comment and the ledger row; a comment naming no key is ignored rather than guessed at; and a key absent from every ledger is reported as unresolvable, not as agreement

### Story 21.16: The status/body check renders where the operator already looks
**Type:** feature • **Effort:** S • **Deps:** Stories 21.12, 21.13, 21.15 • **FR/AD:** spec-status-body-consistency CAP-5 • batch § 2.4 D1
**Surface:** the new source module's registration in `sources/__init__.py`, doctor's `report-schema.json`, `pixi.toml` (`detectors` membership + task), `tests/unit/`, `tests/meta/`
**Given** the document tier drifts faster than any detector polices it, and a finding nobody sees is a finding nobody acts on **When** the source is registered and joins the `detectors` set **Then** its findings appear in the doctor report and the fleet-picture ATTENTION block beside `dream-vocab` and Story 21.2's `spec-status-missing`; each signal that joins carries its measured precision over the live tier; a signal rejected under Story 21.14 does **not** join; and the meta-tests still pass — verdict sole ownership, source independence, and read-only


## Currency validation — 2026-09-01

Story 19.1 landed: manifest-driven watched set + registry-aware
``_resolve_upstream_latest`` in ``sources/bmad_method.py``; ledger now
83 stories (Epics 1–19).

## Currency validation — 2026-08-26

Chain-currency sweep validation pass (arch→epics edge), against the architecture
spine as reconciled 2026-08-26 and the tracked ledger:

- **Ledger agreement:** every `### Story` heading above maps to a
  `sprint-status-ledger.yaml` key and all 82 story keys report `done` (Epics 1–18;
  the 18 `epic-N-retrospective` keys stay `optional`). No orphan headings, no
  orphan keys.
- **Epics 17/18 conform to the reconciled spine:** Story 17.1's hook extraction
  landed as `hooks.py` on the shared `pyforge.core.hooks` contract with today's
  gather/prescribe backends as default plugins (canopy:AD-21, spine § Currency
  reconciliation); Story 18.1's persona/skill and 18.2's portal slice
  (`/stations/doctor/` fleet pulse via PortalClient, landed 2026-08-26) respect the
  Canopy-obligations constraints recorded above — no second chrome, no `pyforge.*`
  under `src/platform/`, findings advisory only.
- **Known open at this stamp:** the `chain-currency-sweep` Dream (owner: doctor)
  reports `dream-without-spec` in the chain audit's orphans checkpoint; its Spec is
  being authored separately this same pass and is deliberately not an epic here yet.
- No epic or story content above was restructured; this note and the frontmatter
  `updated:` bump are the whole edit.

## Currency validation — 2026-08-29

Chain-currency sweep cascade continues (`arch→epics` edge, fired by the spine's
2026-08-29 re-dating, itself fired by the PRD's 2026-08-29 re-dating, itself fired by
`spec-pyforge-doctor`'s memlog moving):

- **Ledger agreement, re-measured (not copied forward):** the tracked ledger reports
  **67/67 stories done across 18/18 epics** as of this stamp. (The 2026-08-26 note
  above cited 82 — this pass measured directly rather than repeating that figure
  unchecked; every `### Story` heading still maps 1:1 to a `sprint-status-ledger.yaml`
  key with no orphan either direction.)
- **The four `sources/` modules PRs #903/#904/#906/#907 touched** (`chain.py`,
  `marshal.py`, `factory.py`, `board.py`): `chain.py`'s fixes back Stories 8.5/8.6
  above; `marshal.py` (PR #904, story-status's landing-evidence grammar) and
  `factory.py` (PR #903, a bmad-drift classifier rule) are bug fixes with no
  dedicated story or Spec of their own — hand-driven, not bmad-loop-dispatched — but
  within `spec-pyforge-doctor`'s own already-described scope (the source-registry
  CAPs above), same class as the umbrella catch-up entries this file already carries.
  Not a gap this pass needs to close; named here rather than silently folded in.
- No epic or story content above was restructured; this note and the frontmatter
  `updated:` bump are the whole edit.

## Epic 22: General documentation stops contradicting itself, and stays that way (spec-general-docs-consistency CAP-1..6)

Minted 2026-09-11 from `spec-general-docs-consistency` (owner Dream
`docs/dreams/general-docs-consistency.md`, `bmad-spec`-derived, self-validate PASS on both
passes). Two halves: content correctness (Stories 22.1-22.3, the original scope) and a
Diátaxis-adapted structural reorganization of the general-facing documentation layer only
(Stories 22.4-22.6, added when the Dream was widened 2026-09-11). **The BMAD spec-driven tier
(`docs/dreams/`, `docs/specs/` legacy Tier 1, `_bmad-output/*/planning-artifacts/`, gitignored
`implementation-artifacts/`) is out of scope for every story below** — it is a different layer
(the spec-and-build pipeline, already coherent) than the general-facing docs this Epic
reorganizes.

### Story 22.1: The 2 identity contradictions are fixed at their source

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-general-docs-consistency CAP-1
(`SPEC.md` success)
**Surface:** `src/shared/packages/pyforge-doctor/README.md`, `AGENTS.md`.
**Given** `pyforge-doctor/README.md` claims doctor consolidates warden + cf_atlas signals into
"its own exit-code gate," contradicting `skill-brief.yaml`/`CLAUDE.md`/`AGENTS.md`'s "advisory
— not a second PR gate," and `AGENTS.md` assigns Herald "keeping the Dream → spec handoff
portable across agents," contradicting Herald's own Dream (which assigns that to Marshal,
citing a dated ownership review) **When** both lines are corrected to match every other
authoritative source **Then** `pyforge-doctor/README.md` no longer uses gate language for
itself
**And** `AGENTS.md`'s cross-agent-portability claim names Marshal (or is reworded to make no
ownership claim at all), matching `docs/dreams/pyforge-herald.md`
**Status:** done

### Story 22.2: The 4 cross-cutting decay findings are corrected

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-general-docs-consistency CAP-2
(`SPEC.md` success)
**Surface:** `README.md`, `CLAUDE.md`.
**Given** `README.md`'s "GitHub Actions Workflows" section lists 4 of 19 real workflow files
and falsely claims CI is "manual trigger only"; `README.md`'s own project-structure tree cites
`docs/bmad-setup-plan.md`/`docs/developer-guide.md`, neither of which exists at those paths
(real paths: `archive/docs/bmad-setup-plan.md`, `docs/reference/developer-guide.md`) while the
same file's own prose elsewhere cites the correct paths; the active-project-resolution-priority
list is duplicated verbatim in `README.md` and `CLAUDE.md`, `CLAUDE.md`'s copy substantially
richer; `CLAUDE.md` names 8 PyForge Guild stations in one place and "7 skills" (silently
omitting Mason) in its own SKF Skills block **When** all four facts are corrected **Then**
`README.md`'s workflow section accurately distinguishes automatic PR-gate workflows from
on-demand/manual ones, against the real `.github/workflows/*.yml` trigger types
**And** `README.md`'s tree cites only paths that exist
**And** the priority list exists in exactly one place (`CLAUDE.md`), with `README.md` pointing
to it rather than duplicating it
**And** `CLAUDE.md`'s SKF block and its 8-station list agree, with Mason's deliberate
skill-omission noted rather than silent
**Status:** done

### Story 22.3: A repeatable Doctor detector catches this class of drift going forward

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-general-docs-consistency
CAP-3 (`SPEC.md` success)
**Note:** Fixture-based — replays the Story 22.1/22.2 contradictions as frozen before/after
fixtures rather than depending on those stories landing first.
**Surface:** a new or extended `pyforge.doctor.sources` module (mirrors
`capability_effect.py`/`status_body_consistency.py`'s own discipline), its pixi task, its test
file.
**Given** none of Doctor's existing hygiene detectors (`capability-effect-verified`,
`status-body-consistency`, `sibling-dreams-drift`, `dreams-hygiene`) reach the general,
human-facing documentation layer (`README.md`, `CLAUDE.md`, `AGENTS.md`, station `README.md`s,
`skill-brief.yaml`s, Dream identity claims) **When** a new detector cross-references what a
station's README/skill-brief/Dream/AGENTS.md say against each other **Then** it names a real
divergence — bounded, textual, explainable, matching `capability-effect-verified`'s own
evidence-based discipline (never an inferred or invented contradiction)
**And** it is warn-only and fail-open — never a second PR gate, matching Doctor's existing
hygiene-check contract
**And** it fires against at least the Doctor/Herald cases (Story 22.1's fixtures) that
motivated this Spec, plus a clean-station fixture proving it does not false-positive on
consistent sources
**Status:** done

### Story 22.4: A Diátaxis-adapted information architecture is designed for the general-facing docs layer

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-general-docs-consistency
CAP-4 (`SPEC.md` success)
**Note:** A design/decision story — produces the map, not the fully-populated content (Story
22.5 populates the two new quadrants; Story 22.6 wires the entry-point docs into it).
**Surface:** the general-facing documentation layer only (`README.md`, `docs/reference/`,
`docs/intake/`, scattered onboarding/operational content) — explicitly excludes the BMAD
spec-driven tier.
**Given** the general-facing docs layer has no recognizable information-architecture lens
applied to it, and `docs/reference/` mixes true reference material with architecture/rationale
("why") content **When** a Diátaxis-adapted map is designed, naming four quadrants
(Tutorials/Getting-Started, How-to Guides, Reference, Explanation) and which existing files
move where **Then** the map is documented and `docs/reference/`'s existing content is assigned
to a quadrant by kind — true reference material (config/CLI/schema specs) to Reference,
architecture-rationale content to the new Explanation quadrant — relocated/reorganized, not
discarded and rebuilt
**And** the BMAD spec-driven tier (`docs/dreams/`, `docs/specs/` legacy,
`_bmad-output/*/planning-artifacts/`, `implementation-artifacts/`) is named explicitly as
untouched by the map
**Status:** done

### Story 22.5: The Tutorials/Getting-Started and How-to-Guides quadrants are populated

**Type:** feature • **Effort:** M • **Deps:** S-22.4 (needs the map's quadrant boundaries
decided first) • **FR/AD:** spec-general-docs-consistency CAP-5 (`SPEC.md` success)
**Surface:** new quadrant homes per Story 22.4's map; source content currently in `README.md`'s
"Common Commands," `docs/reference/developer-guide.md`, and skill-scoped guides.
**Given** the Tutorials/Getting-Started and How-to-Guides roles have no discoverable home
today, and their content is scattered across `README.md`'s Common Commands section,
`docs/reference/developer-guide.md`, and skill-scoped guides **When** that content is relocated
into the two new quadrant homes Story 22.4 designed **Then** a newcomer with no prior context
can find one place to get a working environment running (Tutorials/Getting Started) and one
place to find task-oriented operational instructions (How-to Guides)
**And** the content populating both is relocated/corrected existing material, not rewritten
from scratch
**Status:** done

### Story 22.6: README.md, CLAUDE.md, and AGENTS.md point cleanly into the reorganized structure

**Type:** fix • **Effort:** S • **Deps:** S-22.4, S-22.5 (needs the final structure to exist
before pointing to it) • **FR/AD:** spec-general-docs-consistency CAP-6 (`SPEC.md` success)
**Surface:** `README.md`, `CLAUDE.md`, `AGENTS.md`.
**Given** the reorganized structure exists (Stories 22.4-22.5) but the three entry-point docs
still duplicate or predate it **When** their pointers are corrected **Then** no internal link
into the reorganized structure is broken
**And** no fact that lives in the new structure is also duplicated verbatim in
`README.md`/`CLAUDE.md`/`AGENTS.md` without one side pointing to the other — the same
discipline Story 22.2 already applies, now applied to the new structure
**Status:** done

## Epic 23: Leftover docs fold into Diátaxis (spec-docs-shelf-alignment CAP-1..7)

Minted 2026-09-14 from `spec-docs-shelf-alignment` (owner Dream
`docs/dreams/docs-shelf-alignment.md`, `ready`). Residue of realized
[[general-docs-consistency]] / shipped Epic 22 — not a reopen. Five design
questions settled the same day: workflow stubs, brownfield extract-then-stub,
a new Doctor source, this epic (not steward), no empty `vizro/` directory.

### Story 23.1: Entry points are indexes; one owner per fact

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-docs-shelf-alignment CAP-1
**Surface:** `docs/MAP.md`, `README.md`, `CLAUDE.md`, `AGENTS.md`.
**Given** operational procedures are still restated in entry-point files after Epic 22
**When** each duplicated procedure becomes a pointer into `docs/`
**Then** no operational procedure is copied verbatim across an entry point and a
quadrant file without one side being a pointer
**And** SKILL.md files keep wielding notes that name CLI grammar only
**Status:** backlog

### Story 23.2: Fold the getting-started and air-gap cluster; stub the binders

**Type:** feature • **Effort:** M • **Deps:** S-23.1 • **FR/AD:** spec-docs-shelf-alignment CAP-2
**Surface:** `docs/tutorials/getting-started.md`, `docs/how-to/`,
`docs/explanation/enterprise-deployment.md`, marshal
`planning-artifacts/development-guide.md` and `deployment-guide.md`,
`src/shared/packages/pyforge-marshal/docs/`, `docs/reference/` redirect stubs.
**Given** air-gap and getting-started facts live in three or more places and the
brownfield binders tell humans and agents to read different pages
**When** unique operational steps are extracted into the existing Diátaxis files
and the binders become stubs pointing at `docs/` plus `SYNC-RUNBOOK.md`
**Then** there is one tutorial path, one air-gap how-to, and one air-gap explanation
**And** `docs/reference/` redirect stubs are deleted after the pointer sweep
**And** the planning tree still exists — `epics.md` is not moved
**Status:** backlog

### Story 23.3: Sunset docs/specs/ by frontmatter status

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-docs-shelf-alignment CAP-3
**Surface:** `docs/specs/`, `docs/how-to/`, `archive/docs/specs/`, `CLAUDE.md`,
`scripts/bmad_drift_check.py` (`--specs` remains a glob of `docs/specs/*.md`).
**Given** 19 legacy intake specs still live in `docs/specs/` with YAML `status:`
**When** `shipped` and `superseded` files move to `archive/docs/specs/`,
`in-progress` files stay, and each `workflow` body moves to `docs/how-to/`
with a stub left at `docs/specs/<name>.md` (`status: workflow` + pointer)
**Then** no shipped/superseded Tier-1 spec remains the live home
**And** `python scripts/bmad_drift_check.py --specs` still lists the three
workflow stubs and CLAUDE.md still indexes those filenames
**Status:** done
**Outcome (2026-09-18, reconciled 2026-09-19):** landed as PR #1445 (`a8996d5abe`); the ledger row stayed `backlog` and the twin was never promoted — recovered from the session transcript when a 2026-09-19 re-dispatch found `story_merged_on_main`.

### Story 23.4: Empty the intake inbox per its own README

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-docs-shelf-alignment CAP-4
**Surface:** `docs/intake/`, `archive/docs/intake/`, owning Dream companions.
**Given** intake dumps have no per-file disposition and several already have a
specified or pitched Dream
**When** each folder is routed per `docs/intake/README.md` and `gists/INDEX.md`
**Then** nothing a specified/realized/archived Dream already absorbed remains
in intake
**And** no gist dump gains Dream YAML
**Status:** backlog

### Story 23.5: Archive citations for the five already-moved _bmad-output/ files

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-docs-shelf-alignment CAP-5
**Surface:** `docs/intake/README.md`, station `planning-artifacts/specs/README.md`
files that still cite `_bmad-output/DREAM-TRIAGE-2026-08-08.md` and siblings.
**Given** five files already live under `archive/_bmad-output/` and inbound
citations still use the old root path
**When** those citations are rewritten
**Then** no live doc cites the old `_bmad-output/` root path for those five files
**Status:** backlog

### Story 23.6: MAP names publish roots; do not mint an empty vizro/ tree

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-docs-shelf-alignment CAP-6
**Surface:** `docs/MAP.md`, `docs/dashboard/README.md`.
**Given** `docs/dashboard/kedro-viz/` is a generated Pages upload root and Vizro
is a different product
**When** MAP and the dashboard README state one subfolder per board
**Then** kedro-viz is not renamed
**And** `docs/dashboard/vizro/` does not exist unless a later publish story
created it
**Status:** backlog

### Story 23.7: A new Doctor source flags leftover-shelf occupancy

**Type:** feature • **Effort:** M • **Deps:** S-23.6 (needs the MAP exception list)
• **FR/AD:** spec-docs-shelf-alignment CAP-7
**Surface:** a new `pyforge.doctor.sources` module (not
`general_docs_consistency.py`), pixi task, unit fixtures.
**Given** `general_docs_consistency` is identity-only (README vs skill-brief vs
AGENTS vs Dream) with frozen 22.3 fixtures
**When** a new warn-only, fail-open source compares leftover-shelf paths to the
MAP allow-list
**Then** re-adding a dated campaign note at `_bmad-output/` root, or a second
air-gap how-to outside the cluster, is a finding with a quoted path
**And** a clean MAP fixture is silent
**And** the finding is never a second PR gate
**Status:** backlog

## Currency validation — 2026-09-14

Chain-currency sweep cascade (`arch→epics` edge, fired by the spine's 2026-09-14
re-stamp, itself fired by the PRD's, itself fired by `spec-pyforge-doctor`'s SPEC.md
moving to 2026-09-12 and its memlog to 2026-09-14):

- **Ledger agreement, re-measured with the real parser** (`fleet_scan.parse_sprint_status`,
  not a regex): **95/95 stories `done` across 22/22 epics**. Every `### Story` heading
  above maps 1:1 to a `sprint-status-ledger.yaml` key, no orphan either direction. The
  prior note's 67/18 figure is superseded by growth, not corrected.
- **The spine's re-counted `sources/` inventory was traced to story homes, module by
  module.** Six of the eight modules added since the 2026-08-29 count are decomposed
  here: `bmad_config` → Story 20.2 (render-config-ambiguity), `frozen_path` → Epic 20,
  `general_docs_consistency` → Epic 22, `capability_effect` → Stories 21.9–21.11,
  `status_body_consistency` → Stories 21.12–21.16, `pixi_currency` → Story 21.7.
- **Two have no story home in this file, and both are legitimate — but they are named
  here rather than left implicit.**
  1. `sources/capability_ledger.py` (landed `c48a65e8ad`, 2026-09-13) is decomposed on
     **steward's Epic 54**, not doctor's. That is the cross-station relay pattern
     `spec-pyforge-doctor`'s own Assumptions now record (steward writes the criterion,
     doctor's package carries the implementation). Not a gap; recorded so a future
     reader does not read the missing heading as an undecomposed source.
  2. `sources/platform_policy.py` (landed `4005c4ddbc`, 2026-09-05) came from a **retro
     action item**, with no story in this file and none found in any sibling station's
     `epics.md`. This is the one genuine bookkeeping residue this pass found. It is
     **not** repaired here — minting a retroactive story is a planning act, and this is
     a currency cascade; it is recorded for the next planning pass to decide whether it
     wants a retroactive heading (the precedent exists: marshal's Epics 37–41 and
     steward's Epic 57 were both minted retroactively for exactly this reason).
- No epic or story content above was restructured; this note and the frontmatter
  `updated:`/`currency_review:` bumps are the whole edit.

## Epic 23 mint — 2026-09-14 (later, same day)

`spec-docs-shelf-alignment` reached `ready`; Stories 23.1–23.7 and `## Epic 23`
appended above. Ledger keys minted via `sprint_plan.py generate` +
`sprint-ledger-sync -- --project pyforge-doctor`. Prior 95/95 / 22/22 figure
is superseded by this mint.

## Epic 24: The coverage gate ships outside every station it judges (spec-coverage-gate-independence CAP-1..3)

Minted 2026-09-14 from `docs/governance/spec-coverage-gate-independence/SPEC.md` (owner Dream
`docs/dreams/coverage-gate-independence.md`, **`owner: guild`** by the Charter §5 amendment of the
same day — the only Dream besides the Charter to carry it). The **outcome** is the Guild's; the
**mechanism** is Doctor's under §5's outcome/mechanism rule, because Doctor is the Smith §6 names as
Marshal's judge and `sources/marshal.py` is the independence exemplar CAP-1 copies — the same
relay shape as the C8 row on the Charter's own Spec. Every story below binds to a CAP id on a Spec
that lives in `docs/governance/`, not in this project's `specs/` tree; INV-A does not scan that
directory, so the citations here are the only place the Spec's stories are enumerated.
**Ruled and closed before minting** (do not re-open): the home is the Guild, not a `pyforge-gates`
package (a Smith-less ninth package is `owner: crew` again); the data-only split is **not**
sufficient (§6 names *weaken, re-threshold, disable* — moving only the data protects one of the
three), so Story 24.1 moves the evaluator and the thresholds together; all eight stations are
treated alike; the import-linter gains the rule. What is NOT in scope: any floor value (the 80/70
defaults are `spec-pyforge-testing-charter` CAP-4's), marshal's verdict lattice (cleared), and the
fleet-wide advisory posture of `detectors.yml` (its one-row carve-out, `ledger-regression`, was
ruled separately the same day).

### Story 24.1: The evaluator and the thresholds move out of marshal's package, together

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-coverage-gate-independence
CAP-1, CAP-2 (`SPEC.md` success; the two land together by ruling, never CAP-2 alone)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py` (removed),
`src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml` (removed), their
new homes under the governance Spec's surface (`docs/governance/coverage-thresholds.toml` beside
`guild-roster.json`, carrying the same "changing this file is a governance act" `$comment`; the
evaluator at a path outside every `pyforge.<station>` package — `scripts/` is the natural one, now
that the Spec governing it is guild-owned), `scripts/coverage_gates_ci.py`,
`scripts/run_station_coverage_gate.py`, `.github/workflows/coverage-gates.yml`, the eight
`pyforge-<station>-coverage-gate` pixi tasks,
`src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py` (the
AD-3/AD-4 contract that names `pyforge.marshal.coverage_gate`, amended with its reasoning), and
marshal's own tests for the module.
**Given** `pyforge/marshal/coverage_gate.py` and `coverage_thresholds.toml` ship inside the marshal
package and `coverage-gates.yml:90` runs that gate across all eight stations with no
`continue-on-error`, so a three-line `[stations.marshal]` edit to a file marshal owns lowers the
floor that reds marshal's own PRs with no Doctor verdict **When** the evaluator and the thresholds
are moved out of `pyforge.marshal` to homes governed by the guild-owned Spec, every caller is
re-pointed, and the AD-3/AD-4 import-linter contract is amended deliberately (its reasoning in the
same change) **Then** no `pyforge.<station>` module is the evaluator of any station's CI gate
**And** `coverage-gates.yml` and all eight `pyforge-<station>-coverage-gate` tasks call the new
home and are green at the same floors — no station's floor changes as a side effect (byte-compare
the effective thresholds before and after)
**And** `docs/governance/coverage-thresholds.toml` carries the governance-act `$comment` and
`spec-coverage-gate-independence/SPEC.md`'s `surface:` names both new paths
**And** `import-linter` passes with the amended contract; the old module path resolves nowhere
**Status:** done

**Outcome (2026-09-21).** Landed as PR #1559 (`78f5b33c56`, `Merge pyforge-doctor/24-1 into main`), autonomous end-to-end dispatch/land — no hand intervention needed. `coverage_gate.py` and `coverage_thresholds.toml` moved out of `pyforge.marshal` into guild-owned homes beside `guild-roster.json`; every caller (the eight `pyforge-<station>-coverage-gate` tasks, `coverage-gates.yml`, `scripts/coverage_gates_ci.py`) re-pointed. Ledger row promoted by hand afterward (Tier-3 feed + `sprint-ledger-sync`): `dispatch_land_finalize` didn't auto-promote it, same shape as marshal 53.2/53.3's own landings.

### Story 24.2: An import-linter contract catches the class structurally

**Type:** feature • **Effort:** S • **Deps:** S-24.1 • **FR/AD:** spec-coverage-gate-independence
CAP-3 (`SPEC.md` success)
**Surface:** `src/shared/packages/pyforge-marshal/pyproject.toml` `[tool.importlinter]` (marshal's
contracts, where AD-3/AD-4 live) and/or a fleet-level contract home the story chooses,
`src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py` or a sibling
meta-test, a fixture proving the contract fires.
**Given** the defect Story 24.1 removes survived for weeks because nothing could see it — no test
or contract asked whether a station's package evaluates that same station's CI gate **When** a
contract forbids any `pyforge.<station>` module from importing or defining the gate evaluator, and
a meta-test proves the contract fails on a planted reintroduction (a throwaway
`pyforge.<station>.coverage_gate` shim in a temp tree) and passes on the moved layout **Then**
reintroducing the shape fails a test rather than waiting for a future audit
**And** the contract's own docstring names Charter §5/§6 and this Spec as its reason, so a
future maintainer does not read it as an arbitrary layering rule
**Status:** backlog

### Story 24.3: The surfaces are reconciled so no file is governed twice or not at all

**Type:** fix • **Effort:** S • **Deps:** S-24.1 • **FR/AD:** spec-coverage-gate-independence
CAP-1 (`SPEC.md` `surface:`); spec-pyforge-testing-charter surface (the two `scripts/` drivers
leave it); spec-surface baseline
**Surface:** `docs/governance/spec-coverage-gate-independence/SPEC.md` (`surface:` declared,
`.memlog.md` moved), `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md`
(`scripts/coverage_gates_ci.py` and `scripts/run_station_coverage_gate.py` removed from its
`surface:`, `.memlog.md` moved), `scripts/.spec-surface-baseline.json` (scoped stamps only —
`--write-baseline --spec <key>` per key, never bare).
**Given** Story 24.1 moves files that `spec-pyforge-testing-charter` currently lists in its
`surface:` while the governance Spec's `surface:` is deliberately `[]` until the move **When** the
governance Spec declares its surface, testing-charter drops the two drivers, both memlogs record
the hand-over, and each key is stamped scoped **Then** `spec-surface` reports no `ungoverned`
and no `drift` for any moved path
**And** the governance Spec's `surface:` and testing-charter's are disjoint (no path appears in
both)
**And** `git ls-files` shows every new path tracked before the stamp (the baseline reads
`git ls-files`)
**Status:** backlog

## Epic 25: One chain per station — the sprawl gate, the FR check, and a ledger that survives a rebase (spec-one-chain-per-station CAP-2, CAP-5, CAP-3(g))

Minted 2026-09-16 from `docs/governance/spec-one-chain-per-station/SPEC.md` (owner Dream
`docs/dreams/one-chain-per-station.md`, **`owner: guild`** — the second instance of the Charter §5
shape amended 2026-09-14: a gate that judges all eight Smiths, registered in `guild_dreams` the
same day, PR #1384). The **outcome** is the Guild's; the **mechanism** is Doctor's under §5's
outcome/mechanism rule — the same relay as Epic 24. Every story below binds to a CAP id on a Spec
that lives in `docs/governance/`, not in this project's `specs/` tree; INV-A does not scan that
directory, so the citations here are the only place the Spec's stories are enumerated.
**Ruled and closed before minting** (do not re-open; Spec memlog 5–10, 26–43): Dream-**append**-
first with a closed `fold-exemption:` list `{different-owner, different-lifecycle,
cross-station-seam, governance}`; eventual consistency — a folded station and an unfolded one both
pass throughout, so the sprawl gate baselines from a dated snapshot and only *new* unexempted
folders are findings; a fold is a **rebase** — CAPs, epics and stories renumber sequentially and
every fold PR ships a re-key map, so `ledger-regression` must read that map or every fold reds on
its own renumbering; the standard every fold conforms to is
`docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` (§7 is the checklist). These three
stories land **before** the marshal pilot begins (Spec Constraint *Sequence*: "CAP-1/2 land before
marshal's fold so it does not refill while underway"). What is NOT in scope: any station's fold
(each is that Smith's own effort), the story-identity mint function (`vocabulary-one-name-one-job`
CAP-6, steward's), and the declared status-vocabulary source (vocabulary CAP-2, steward's) — Story
25.1 reads the exemption list from one declared source but does not mint that source's shape.

### Story 25.1: A new Dream or Spec folder without a declared exemption is a finding

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-one-chain-per-station CAP-1,
CAP-2 (`SPEC.md` success: "a Dream or Spec folder minted after the rule date without
`fold-exemption:` is a FAIL"; Constraint *Eventual consistency*: "baselines from a dated snapshot —
only new unexempted folders are findings")
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` (new
`gather_chain_sprawl`), `sources/__init__.py` (`Source.CHAIN_SPRAWL` registration, scope `repo`),
`sources/__main__.py` (dispatcher row), `pixi.toml` (`chain-sprawl-check` task),
`scripts/detectors.py` (row in the `detectors-ci` list), `docs/governance/guild-roster.json`
(`fold_exemptions` — the one declared source of the closed list, with a dated `$comment`),
`docs/governance/chain-sprawl-baseline.json` (the dated snapshot: every `docs/dreams/*.md` and every
`specs/spec-*/` folder present at the ruling SHA `e630e43330`, PR #1384's merge), doctor unit +
conformance tests.
**Given** the fleet holds 171 Dreams and 172 Spec folders for eight stations and the 2026-08-08
61-Dream fold regrew in five weeks because nothing refused a new file **When** the detector lists
every `docs/dreams/*.md` (excluding `README.md` and `archive/`) and every
`_bmad-output/projects/*/planning-artifacts/specs/spec-*/` and `docs/governance/spec-*/` folder,
subtracts the baseline, and for each remainder reads `fold-exemption:` from the Dream's or
`SPEC.md`'s frontmatter **Then** a remainder with no `fold-exemption:` or a value outside the
declared list is `check=chain-sprawl-unexempted` FAIL naming the path and the eight station Dreams
it could have been a section of; a remainder carrying a listed value is `check=chain-sprawl-exempt`
info (so the exemption is visible, never silent); a baseline entry is never a finding **and** the
station Dreams `pyforge-<s>.md`, the station Specs `spec-pyforge-<s>/`, and story-spec files
`spec-<E>-<S>-<slug>.md` are structurally excluded (they are the chain, not sprawl) **and** the
exemption list is read from `guild-roster.json` `fold_exemptions` — a value hard-coded in
`chain.py` is a meta-test failure — **and** `python scripts/spec_surface_check.py`-style scoped
`--write-baseline` for this detector only *removes* entries (a fold that archived a Dream or
absorbed a Spec), never adds one: adding is what the exemption is for **and** the task is in
`detectors-ci`, so the merge gate measures it as no-new-findings against `main` from the first PR
after this one **and** the doctor unit suite pins the finding codes and the exclusion set, and a
conformance test runs the detector on the live tree expecting zero FAIL at the merge SHA.

### Story 25.2: A product requirement minted after the rule date names its source capability

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-one-chain-per-station CAP-5
(`SPEC.md` success: "every FR minted after the rule date carries its source CAP; `fr-without-cap`
holds it"; CHAIN-STANDARD § 2 "an FR cites its source CAP (`FR-n ← CAP-m`)")
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` or a new
`sources/prd.py` (new `gather_fr_without_cap`), `sources/__init__.py`, `sources/__main__.py`,
`pixi.toml` (`fr-without-cap-check`), `scripts/detectors.py` (`detectors-ci` row),
`docs/governance/fr-baseline.json` (every `FR-n` / `NFR-n` id per station PRD at the ruling SHA —
the pre-rule population that is never a finding), doctor tests.
**Given** the fleet carries two requirement namespaces — 1,626 `FR-` citations and 3,161 `CAP-`
citations — with no rule joining them, so a PRD can grow a requirement no Spec ever contracted
**When** the detector parses each station's `prds/prd-pyforge-<s>-*/prd.md`, collects every
`FR-n` / `NFR-n` heading or list id, subtracts the baseline, and for each new id looks for a
`← CAP-m` (or `(CAP-m)`) citation on the same line or its first body line **Then** a new FR with
no CAP citation is `check=fr-without-cap` FAIL naming the PRD, the FR id and the station's Spec
folder; a new FR citing a `CAP-m` that does not exist in that station's `spec-pyforge-<s>/SPEC.md`
(or, before the station's fold, in *any* open Spec folder under that station — eventual
consistency) is `check=fr-cap-unresolved` FAIL; a baseline FR is never a finding **and** the
baseline is regenerated only by a scoped `--write-baseline --project <s>` at a station's fold PR,
when the PRD is re-derived FR ← CAP in full (CHAIN-STANDARD § 7 item 7) **and** the task is in
`detectors-ci` **and** a unit test pins both codes and the "same line or first body line" rule; a
conformance test runs on the live tree expecting zero FAIL at the merge SHA.

### Story 25.3: The ledger-regression verdict reads a re-key map, so a rebase moves done rows as done

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-one-chain-per-station CAP-3(g)
(`SPEC.md`: "the ledger regenerated from the Tier-3 feed through a re-key map … so a `done` row
moves as `done`, never as drop+add"); Constraint *Re-key, never regress*: "`ledger-regression-check`
and `story-status-check` must stay green through a renumbering; the re-key map is what makes that
true"; CHAIN-STANDARD § 7 item 1 (`planning-artifacts/rekey-<date>.md`, one line per old → new key)
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py`
(`gather` learns the map), a small `pyforge/doctor/rekey.py` parser (the map's one shape: one
`old-key -> new-key` per line, `#` comments, no other syntax), `scripts/promote_sprint_status.py`
(`--rekey <map>`: regenerate the tracked twin with keys translated, statuses carried; refuses if any
translated key collides or any `done` row would be dropped), `pixi.toml` (`sprint-ledger-sync`
passes the flag through), `story-status-check`'s heading↔key comparison (reads the same map for the
PR's diff), doctor tests with a fixture ledger + map.
**Given** `ledger-regression` compares the PR head's `sprint-status-ledger.yaml` to `main`'s by key
with one built-in continuity rule — a `done` story whose numeric prefix changed but whose kebab
tail survived is the same story (`_tail`) — so a *pure* renumber already passes, but a fold also
fixes the 53 slug divergences (the tail changes) and renumbers every `epic-N` row (no tail at
all), and `story-status` confirms a `done` story by merge subjects that name its *old* id; each
of those reads as a regression or a false green today *(corrected at implementation 2026-09-16:
the first draft of this story said every row would drop; only the slug-changed and epic rows do)*
**When** the fold PR ships
`planning-artifacts/rekey-<date>.md` and the detector, finding that file changed in the PR's diff,
applies the map to `main`'s ledger before comparing **Then** a `done` row whose key moves per the
map and stays `done` is not a finding; a `done` row whose key is absent from both the map and the
head ledger is `check=ledger-regression-dropped` FAIL (unchanged behaviour); a `done → backlog`
transition through the map is still `check=ledger-regression` FAIL (the map moves keys, never
statuses); a map line whose old key does not exist on `main` or whose new key is not in the head
ledger is `check=rekey-map-dangling` FAIL naming the line **and** `promote_sprint_status.py
--rekey` produces the head ledger the detector then accepts, byte-stable on a second run **and**
without a map in the diff, behaviour is byte-identical to today (the existing doctor unit tests
for `ledger.py` pass unchanged) **and** a fixture test rebases a 3-epic ledger to sequential
numbering and asserts zero findings, then flips one row's status through the same map and asserts
exactly one.

_Status (2026-09-16): all three `backlog`; they gate the marshal pilot (the first fold PR runs
CHAIN-STANDARD § 7 with these three green)._

## Epic 26: The map of what no agent can verify without a live proof (spec-pyforge-doctor CAP-77)

Minted 2026-09-18 from `spec-pyforge-doctor` CAP-77, seeded the same day in `docs/dreams/pyforge-doctor.md`'s
Realization log (Dream-append-first; no new Dream file, doctor's canonical chain). Motivating incident:
herald's mcp SDK transport broke across two silent 2.x renames (`streamablehttp_client` →
`streamable_http_client` with a different call signature; `CallToolResult.isError` → `.is_error`), caught
by neither review nor the test suite nor a dev pass's own self-report — only a real live
push-then-read-back against Claude Design surfaced it. `live-proof-surfaces.md` (the CAP-77 companion,
already landed) catalogs six known surfaces fleet-wide; this epic wires that catalog into a real,
advisory Doctor Finding.

### Story 26.1: A touched live-proof-only surface gets an advisory Doctor finding naming it

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-77 (companion refined 2026-09-20: `Surface globs` column; zero false positives on the live tree is a testable gate)
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/live_proof_surfaces.py` (new —
parses `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md`'s
table into a `(station, surface, surface_globs, how_to_prove, cost)` list — matching reads the companion's hand-authored `Surface globs` column and nothing else; amended 2026-09-20 after run `…8f2b958e` blocked on an intent gap: the keyword fallback for path-less rows produced three false positives against the live tree), `models.py` (`Source` enum gains
`LIVE_PROOF_SURFACE`, extending the closed taxonomy AD-3 already governs — one new member, never an open
string), `report-schema.json` (enum extended additively), `__main__.py` (DISPATCH + REGISTRY entry),
`scripts/detectors.py` (a `detectors-ci` row, matching CAP-77's own constraint that the finding is always
advisory, never gating), tests.
**Given** a PR's changed-paths set intersects one or more of the six catalogued surfaces in
`live-proof-surfaces.md` (herald's Claude Design MCP bridge, herald's live webhook host, herald's PPTX
Chrome/Chromium check, scribe's Postgres+pgvector cluster, atlas's Chromium/DuckDB/WASM pipeline, warden's
live OSV/CISA-KEV/EPSS feeds, guild-container docker/podman) **When** `doctor check`/`detectors` runs over
that PR **Then** a `Finding` fires naming the matched surface, quoting the catalog's own "how to prove it
live" cell verbatim (never a fabricated or re-derived proof step), and is tagged `status=warn` — never
`fail`, per CAP-77's own constraint (AD-2's operability-not-policy posture, matching CAP-14/CAP-15's
existing live-query-finding precedent in this same Spec)
**And** a surface catalogued with "no single documented live-proof mechanism as of this writing" (the
atlas Chromium/DuckDB/WASM row, the catalog's own named gap) fires a finding that says exactly that —
never invents a proof step to fill the gap, per CAP-77's own constraint against fabricating live-proof
mechanisms
**And** a PR touching no catalogued surface produces zero `LIVE_PROOF_SURFACE` findings — the check is
silent by default, matching every other advisory source's own baseline behavior

## Epic 27: A PR is judged at its merge-base, and a merge subject names its station (spec-pyforge-doctor CAP-78)

Minted 2026-09-18 from `spec-pyforge-doctor` CAP-78, seeded the same day in `docs/dreams/pyforge-doctor.md`'s
Realization log (Dream-append-first). Two false regressions in one day, both from Doctor's merge-history
sources asking the right question against the wrong base or the wrong station: herald PR #1465's blocking
`ledger-regression` step redded two minutes *after* `marshal factory dispatch` had merged it unattended and
promoted `23-6 → done` on `main` (the PR head, compared to the tip of `main`, "un-finished" a row it never
touched); and `ledger-direction` reported atlas 13-5/14-4/15-3 `landed-but-unpromoted` all day because
`sources/marshal.py:87` hardcodes `Merge {key} into main`, so a sibling station's merge reads as atlas's.
Marshal is closing its own side of the second finding as `spec-pyforge-marshal:CAP-247` (Story 50.4);
this epic makes Doctor read the station's own template rather than wait for it. **HARD boundaries:**
`ledger-regression` stays the one blocking Doctor step in CI (ruling 2026-09-14) — a branch that genuinely
moves a `done` key still FAILs; Doctor reads a station's `marshal-policy.toml` as TOML, never imports
`pyforge.marshal`; every other source stays advisory.

### Story 27.1: A PR is judged at its merge-base, and a merge subject names its station

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-78
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` (`gather`: when `base` and
`head` differ, compare against `merge-base(base, head)` and carry `merge_base` / `base_requested` in evidence; the
push-to-main first-parent fallback unchanged), `.../sources/marshal.py` (`_MERGE_SUBJECT_TEMPLATE` replaced by a
per-station read of `merge_subject_template` from `_bmad-output/projects/<slug>/planning-artifacts/marshal-policy.toml`,
falling back to the legacy default only when the policy declares none; a templated match counts only when the
rendered slug segment, if the template has one, is that station's), `scripts/ledger_regression_check.py` (the
mutation-only residual keeps parity), `.github/workflows/detectors.yml` (no change expected — the step's command is
unchanged), tests with two fixtures: herald PR #1465's shape and a repo whose `main` carries a sibling's
`Merge 13-5 into main`.
**Given** on 2026-09-18 `ledger-regression` on PR #1465's `detectors` lane ran at 18:17Z against an `origin/main`
that already carried `34f1df91d4 marshal: promote sprint-status ledger for 'pyforge-herald' (1 key(s) -> done)` and
reported `done-key-regressed: pyforge-herald: 1 story key(s) moved out of done` for a branch that never touched that
row, and `ledger-direction` reported `pyforge-atlas/13-5`, `14-4`, `15-3` `landed-but-unpromoted` because
`Merge 13-5 into main` / `Merge 14-4 into main` / `Merge 15-3 into main` on `main` belong to other stations
**When** a PR-shaped comparison (`base` ≠ `head`) reads the ledgers at `merge-base(base, head)` instead of at `base`'s
tip, and a templated merge subject is attributed to a station only when it renders from *that* station's own
`merge_subject_template` (slug included when the template carries one)
**Then** the PR #1465 fixture reports `ok` and a fixture branch that genuinely flips a `done` row to `backlog` still
FAILs; the sibling-merge fixture reports no `landed-but-unpromoted` row for atlas while `Merge pyforge-atlas/13-5 into
main` still counts; and the eight tracked ledgers' existing `done` rows keep their evidence under each station's
current template (regression fixture)
**And** the evidence payload of every `ledger-regression` finding names `merge_base` and `base_requested` when a
substitution happened, and the detector's exit-code domain (`{0, 2, 130}`) is untouched

### Story 27.2: `ledger-direction` reads the station's rekey map

**Type:** fix • **Effort:** S • **Deps:** S-27.1 • **FR/AD:** spec-pyforge-doctor CAP-79 • mirrors Story 25.3 (`gather()`'s rekey-awareness)
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` (`gather_direction` applies the station's `rekey-*.md` maps via `pyforge.doctor.rekey.parse_rekey` — the reader `gather()` already uses — to merge-history keys before the ledger comparison; an unreadable map is a WARN naming the file), `tests/unit/test_sources_ledger_direction.py` (fixture: a rekey map + a merge naming the old key; mutation: map removed), the three live atlas rows as the acceptance fixture.
**Given** Story 27.1's dispatched session traced atlas's 13-5 / 14-4 / 15-3 `landed-but-unpromoted` rows to their real cause — those merges are atlas's own `Merge bmad-loop/<run>/<key> into loop/pyforge-atlas (bmad-loop)` subjects naming keys that atlas's 2026-09-17 rekey renumbered (13-5 → 12-5-downstream-handoff-to-mason-fr-68, 14-4 → 13-4-air-gap-asset-rewriting-cap-4, 15-3 → 14-3-kedro-pipeline-surfacing-cap-4), and `gather_direction` has no rekey awareness while `gather()` has had it since Story 25.3 **When** every key parsed from merge history is passed through the station's rekey maps before it is compared against the tracked ledger **Then** `ledger-direction-check` on today's `main` reports no atlas `landed-but-unpromoted` row, the fixture with a map reports nothing and the same fixture without it reports the row (mutation test), and the exit-code domain `{0, 2, 130}` is untouched
**And** an unreadable or malformed rekey map is a WARN that names the file, never a silent pass or a crash — the same posture `gather()`'s `rekey-map-unreadable` already takes

### Story 27.3: A station's legacy-template history stays attributed after its template changes

**Type:** fix • **Effort:** S • **Deps:** S-27.1 • **FR/AD:** spec-pyforge-doctor CAP-80 • regression on `main` after PR #1471
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` and `.../sources/ledger.py` (the per-station template read from Story 27.1 gains a second accepted form: the repo-default `Merge {key} into main`, honoured for the querying station only for keys its own tracked ledger knows — Story 35.1's corroboration — and never otherwise), `tests/unit/test_sources_marshal_story_status.py`, `tests/unit/test_sources_ledger_direction.py`, marshal `34-3` on today's `main` as the acceptance fixture.
**Given** Story 27.1 made Doctor read each station's *current* `merge_subject_template`, and marshal landed `34-3` on 2026-09-12 as `Merge 34-3 into main` under the then-default template — so the moment marshal's policy moved to `Merge pyforge-marshal/{key} into main` (PR #1467), `story-status` on `main` reports `marshal/34-3: reads done in the sprint feed, but the harness says 'deferred' with no commit and no merge commit anywhere`, a `done` story orphaned by its own station's template move **When** a bare legacy-form subject is attributed to a station only when that station's tracked ledger knows the key **Then** marshal `34-3` reads as merged and `story-status` on `main` reports no finding for it, a fixture where the bare subject names a key the querying station's ledger does not know still attributes nothing, the scoped form still attributes, and CAP-78's PR #1465 replay stays `ok`
**And** the rule is one function used by both sources, never two readings of "legacy"; the exit-code domain `{0, 2, 130}` is untouched

**Story 27.4 — reserved hole (2026-09-18; do not reuse).** Its mint PR (#1477) was pushed from a branch named
`doctor/27-4-mint`, and `Merge pull request #1477 from rxm7706/doctor/27-4-mint` parses under the station-branch
landing grammar as *doctor 27.4 landed* — so the first dispatch of 27.4 (`pyforge-doctor-20260918T222825190Z`)
short-circuited `story_merged_on_main` in one second and detached. Same poison class as a `Story N.M:` commit
subject; the rule is renumber, never exclude. The story is 27.5 below, unchanged in content.

### Story 27.5: A bare-form merge is attributed by the paths its diff touches

**Type:** fix • **Effort:** S • **Deps:** S-27.3 • **FR/AD:** spec-pyforge-doctor CAP-80 (amended Approach) • supersedes Story 27.3 (landed empty on an intent gap)
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` and `.../sources/ledger.py` (one shared helper: for a bare legacy-form templated subject, `git diff --name-only <merge>^1 <merge>` classified into station slugs by `_bmad-output/projects/<slug>/` and `src/shared/packages/<slug>/` prefixes, cached per sha; a bare-form merge attributes to the querying station iff its paths appear AND the station's ledger knows the key; the scoped form and every other shape unchanged), `tests/unit/test_sources_marshal_story_status.py`, `tests/unit/test_sources_ledger_direction.py`; the reverted 27.3 patch in the 27.3 dispatch worktree (`spec-27-3-attempted-patch-2026-09-18.patch`) is prior art for the plumbing, not the rule.
**Given** Story 27.3's review found that "the querying station's ledger knows the key" reopens the cross-station collision whenever two stations know the same integer key (the common case under one shared grammar) and the story landed empty, while marshal `34-3` (`dcda31b8cb Merge 34-3 into main`, 2026-09-12, harness run `deferred`) still reads `done` with no merge commit anywhere — its first-parent diff touches `_bmad-output/projects/pyforge-marshal/**` and `src/shared/packages/pyforge-marshal/**` and nothing else **When** a bare-form merge is attributed by the station paths its diff touches, with ledger membership as a second necessary condition, never the sole one **Then** `story-status` on `main` reports no finding for marshal `34-3`; a fixture where a bare `Merge 34-3 into main` diff touches only another station's paths attributes nothing to the querying station even though its ledger knows 34-3; a merge touching no station path attributes nothing; the scoped form still attributes; CAP-78's PR #1465 replay and CAP-79's rekey replay stay green
**And** one helper serves both sources, the git call is cached per sha within a run, and the exit-code domain `{0, 2, 130}` is untouched

## Epic 28: A frontmatter reader that stops at the fence, not at the first dashes (spec-pyforge-doctor CAP-81)

Minted 2026-09-19 from `spec-pyforge-doctor` CAP-81, seeded 2026-09-18 (night) in `docs/dreams/pyforge-doctor.md`'s
Realization log (Dream-append-first). `sources/chain.py::_frontmatter_parse` splits a spec on the first `---`
*anywhere in the file* (`text.split("---", 2)`), not on a line-anchored fence. Marshal Story 50.5's tracked spec quotes
a `"---"` fence inside its first deferral's `evidence:`, so the YAML was cut mid-scalar, `yaml.safe_load` still returned
a mapping, and the detector saw one deferral where two exist: the first lost its `location:` (and so its fingerprint,
`fdd6bce25c09` for `3bc3d91bdf95`), the second — severity *high* — was invisible to `deferred-work` and to
`deferred_work_intake.py`, which reported "all 118 already in tracked ledger". Reconciled by hand that night
(DW-FU-50-5 rewritten in full-parse form, DW-FU-50-6 added). The same helper also marks any prose file containing a
`---` horizontal rule as unparseable frontmatter (`if "---" in text: return {}, True`). Every Doctor source that reads
frontmatter through this helper (spec status, deferrals, surface, ownership) inherits the fix. **HARD boundaries:** the
refusal semantics of Story 17-1 / FR-144 stay — an unbounded or non-mapping block is `({}, True)`, never a silent `{}`;
the exit-code domain is untouched; Story 27.4 remains a reserved hole (`rekey-2026-09-18.md`).

### Story 28.1: A frontmatter reader that stops at the fence, not at the first dashes

As every Doctor source that reads a spec's frontmatter,
I want `_frontmatter_parse` to bound the YAML block by line-anchored `---` fences — the opening fence on the first line
(optionally after a `<!-- … -->` banner, as marshal's post-CAP-248 readers allow), the closing fence a line that is
exactly `---`,
So that a quoted `---` inside a scalar or a `---` rule in prose never truncates or invents frontmatter, and a block
that cannot be bounded is refused rather than degraded.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-81
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_frontmatter_parse` (and
`_frontmatter_fields`), tests (`tests/` fixture = marshal 50.5's tracked spec as landed on `main`), no caller changes.
**Given** `_frontmatter_parse` on marshal's `spec-50-5-the-promoter-reads-a-spec-through-its-banner.md` returns one
deferral with no `location:` where the file declares two, and a prose file containing `---` returns `({}, True)`
**When** the block is bounded by line-anchored fences and a leading banner is skipped
**Then** the 50.5 fixture parses both deferrals — the first with `location:` (fingerprint `fdd6bce25c09`), the second
(`5434eca8c9e5`, severity high) visible to `deferred-work` and to `deferred_work_intake.py`; a prose file with a `---`
rule and no leading fence is `({}, False)`; an unclosed fence is `({}, True)`; a banner-topped tracked spec parses
**And** every existing caller's fixture set yields byte-identical verdicts, and restoring `split("---", 2)` re-truncates
the fixture (mutation test)

## Epic 29: The sibling drift check records a human acknowledgement and knows where the sibling went (spec-pyforge-doctor CAP-82)

Minted 2026-09-19 (evening) from `spec-pyforge-doctor` CAP-82, seeded the same evening in `docs/dreams/pyforge-doctor.md`'s
Realization log (Dream-append-first). The first live run with an operator token (`DW-OPS-2026-09-19-6`) found six locally
`archived` Dreams diverging from their pre-fold sibling copies — expected fold fallout the check cannot be told about, so
they re-fire forever and would drown a real change — and that the sibling repo has moved (`OpenTeams-WFT-CDO/…` →
`openteams-ai/mgmt-wf-python-modernization`, reachable only through a 301 the code does not know about).
**HARD boundaries:** read-only toward the sibling (never a sync engine, no content copied — only a hash recorded on the
LOCAL Dream); the unreachable / unauthenticated paths stay warn + fail-open; a new epic because Epic 16 (CAP-71) is `done`.

### Story 29.1: A per-Dream acknowledgement silences exactly one sibling hash, and the sibling coordinates are current

As the operator reading `fleet-picture`'s ATTENTION block,
I want a local Dream to carry `sibling-acknowledged: <sibling content_hash>` so that the drift check stays silent for
that Dream while the sibling's hash equals it and re-fires the moment it does not, and I want the check to name the
sibling's current repository,
So that the six fold-fallout divergences stop re-firing, a genuine later change on the sibling still surfaces, and the
check does not silently break the day GitHub stops redirecting the old owner.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-82
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` (`_SIBLING_OWNER` →
`openteams-ai`, old owner kept in the docstring as history; `sibling-acknowledged:` read from the local frontmatter and
compared to the sibling `content_hash`; `archived` status named in an unacknowledged finding), `tests/unit/test_sources_sibling_dreams.py`
(ack-match, ack-mismatch, archived-without-ack, renamed owner), the six local Dreams named in `DW-OPS-2026-09-19-6`
(one `sibling-acknowledged:` line each, at their sibling hashes as measured on the landing day), the DW row closed.
**Given** the six archived Dreams diverge on every live run and `_SIBLING_OWNER` names an org GitHub only redirects
**When** the acknowledgement is honoured and the coordinates are current
**Then** a live run (`GH_TOKEN` set) reports zero findings for the six; a fixture whose acknowledged hash differs from
the sibling's re-fires exactly that Dream naming both hashes; an archived Dream without an acknowledgement is reported
with `archived` in the message; the request goes to `openteams-ai/mgmt-wf-python-modernization` directly
**And** the unreachable and unauthenticated paths are unchanged (`sibling-dreams-unreachable`, warn, exit 0); no content
from the sibling is written anywhere
**Status:** backlog

## Epic 30: The documentation is right, and refreshing it is repeatable (spec-pyforge-doctor CAP-83, CAP-84)

Minted 2026-09-19 (night) from `spec-pyforge-doctor` CAP-83/84, seeded the same night in `docs/dreams/pyforge-doctor.md`'s
Realization log at the review of PR #1529 (a parallel session's documentation PR: 14 authored pages with day-one errors,
130 README stubs inside skill dirs, a map check that scanned everything `docs/MAP.md` excludes, ten laundering re-stamps,
a hand-written Spec whose CAP-82 / Epic 29 collided with #1526's). Research:
`planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md`. Extends Epics 22–23 (the
Diátaxis map, the docs shelf) with enforcement and currency. **HARD boundaries:** the map's own scope contract (four
quadrants) is the detector's scope; docs detectors start warn (CAP-62) and are promoted to fail per check; generated pages
are never hand-edited; skill directories hold only the Agent Skills layout; doctor owns the chain, a station owns the
generator for its own surface. **FRs covered:** FR-17 (minted 2026-09-19 on the PRD, citing CAP-83/CAP-84).

### Story 30.1: The map is enforced within its scope, the stubs are gone, and the new pages are true
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** FR-17, spec-pyforge-doctor CAP-83
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_map_hygiene.py` (rescoped to the four quadrants; missing = fail, unmapped = warn, index pages exempt), `sources/__init__.py`, `sources/__main__.py`, `models.py` (`Source.DOCS_MAP_HYGIENE`), `tests/unit/test_sources_docs_map_hygiene.py` (new), `scripts/detectors.py` + `pixi.toml` (`docs-map-hygiene-check` in `guild-tasks`), `docs/MAP.md` (the genuine gaps mapped; `docs/foundry/` listed outside the map), the 14 pages under `docs/{explanation,how-to,reference,tutorials}/` (errors corrected; `sources:` / `verified:` frontmatter), `.claude/skills/*/README.md` ×130 removed, nine station READMEs (plain-text pointer), `.steward/keys-inventory.yaml` (runbook pointer), `docs/dreams/pyforge-doctor.md`, `.claude/skills/bmad-os-docs-audit/SKILL.md` (kept).
**Given** the PR's check reds on 44 files on `main`, the pages cite paths and grammars that do not exist, and 130 stubs sit inside installer-managed skill directories
**When** this story lands
**Then** `python -m pyforge.doctor.sources docs-map-hygiene` reports OK on `main`, warns on an unmapped quadrant page and fails on a dead MAP link (each covered by a unit test); every backticked path, pixi task and CLI grammar in the 14 pages resolves; no `README.md` sits inside `.claude/skills/*/` except the three pre-existing conda-forge-expert subfolder READMEs; `pyforge-doctor-test` and the doctor coverage gate are green
**And** the chain carries the record: Dream entry, CAP-83/84, this epic, the tracked story spec with the review triage, capability-ledger rows, real memlog entries on every Spec the diff touches, scoped stamps for exactly those
**Status:** done
**Outcome (2026-09-19):** landed as PR #1529 after review + rebuild; tracked spec `specs/spec-30-1-the-map-is-enforced-within-its-scope-the-stubs-are-gone-and-the-new-pages-are-true.md`.

### Story 30.2: docs/map.yaml is the registry, MAP.md is its render, and `docs-currency` reds a stale page
**Type:** feature • **Effort:** M • **Deps:** S-30.1 • **FR/AD:** FR-17, spec-pyforge-doctor CAP-84
**difficulty:** medium
**Surface:** `docs/map.yaml` (new; quadrant / owner / kind / sources / stamp per page), a renderer task (`docs-map-render`) that writes `docs/MAP.md` from it, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py` (new; the four checks, warn), its unit tests, `scripts/detectors.py` + `pixi.toml` (`docs-currency-check`), frontmatter `sources:` / `verified:` on every authored page, `docs-map-hygiene` retired into `docs-currency` (or kept as its map-alignment check — the story decides and records it).
**Given** MAP.md is hand-maintained and no page declares what it derives from or explains
**When** this story lands
**Then** `map.yaml` validates against a schema shipped in the doctor package; `MAP.md` equals its render (a byte diff is a finding); `docs-currency` reports OK on `main` and reds (warn) an authored page whose named source moved past `verified:`, a page whose backticked path / pixi task / CLI grammar no longer resolves, and a stray file inside a managed skill dir; the unmapped-page class is promoted from warn to fail
**And** the promotion is recorded on the doctor memlog; `general-docs-consistency` and `governance-currency` keep their lanes
**Status:** backlog

### Story 30.3: The reference pages are generated — pixi tasks, station CLIs, detectors, skills — and stamped
**Type:** feature • **Effort:** M • **Deps:** S-30.2 • **FR/AD:** FR-17, spec-pyforge-doctor CAP-84
**difficulty:** medium
**Surface:** generator tasks `docs-pixi-tasks`, `docs-station-cli`, `docs-detectors`, `docs-skills-catalog`, `docs-environments` (each a script under `scripts/` or a station duty, registered in `docs/map.yaml` as the page's source), the generated pages `docs/how-to/pixi-tasks.md`, `docs/reference/station-cheat-sheet.md`, `docs/reference/detectors.md` (new), `docs/reference/skills-catalog.md` (new), `docs/reference/environments.md` (new) with `derived_at` + `tree` stamps, `docs-currency`'s generated-page check (source newer than stamp, or regeneration differs), `library-llms-full.md` unchanged (its own lane).
**Given** the task reference is hand-written and already stale, the cheat sheet was typed from memory, and no page lists the detectors or the skills
**When** this story lands
**Then** each generator is idempotent on an unchanged tree and rewrites its page + stamp on a changed one; editing `pixi.toml`'s tasks, a station CLI's grammar, a detector registration or a `SKILL.md` frontmatter without regenerating reds `detectors-ci`; a hand edit to a generated page is a finding
**And** the pages agents should read (reference) are exact by construction; authored explanation stays for humans
**Status:** backlog

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd→arch→epics` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this epics. `updated:` bumped to record that the
check ran.*
