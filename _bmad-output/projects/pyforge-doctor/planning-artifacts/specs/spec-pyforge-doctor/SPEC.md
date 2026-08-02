---
surface:
  - src/shared/packages/pyforge-doctor/**   # the CLI this Spec builds
id: SPEC-doctor
owner-dream: docs/dreams/pyforge-doctor.md
companions:
  - ../../architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-doctor.md
  - ../../briefs/brief-pyforge-doctor-2026-07-25/brief.md
  - ../../prds/prd-pyforge-doctor-2026-07-25/prd.md
  - ../../epics.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Doctor (pyforge-doctor) — one bedside manner for the whole fleet

## Why

A pain already diagnosed, not a fresh idea: the factory's health signal already exists but is scattered across tools an operator or agent has to know about individually — pyforge-warden's engine-availability self-check, and cf_atlas's `feedstock-health`/`staleness-report`/`behind-upstream`/`cve-watcher`/`release-cadence`/`adoption-stage` CLIs — with no shared vocabulary for severity and no ranked prescription. Three concrete pains follow: no pre-flight gate (a missing engine or bad credential-scope config surfaces mid-build instead of in the first five seconds), no fleet pulse (an operator reconciles five separate CLI outputs by hand to answer "what got worse this week"), and no prescription (findings exist but nothing ranks them into "do this first"). Doctor (module `pyforge.doctor`, CLI `doctor`) is the pyforge Guild's health & diagnostics station: one bedside manner over instruments that already exist, wrapping them behind three verbs (`check`, `monitor`, `diagnose`) rather than adding a new detection engine. Its value is integration completeness and ranking quality, not new instrumentation — Marshal (the bmad-loop orchestrator) is the primary machine consumer, the repo maintainer the primary human one.

Four further capabilities (CAP-5..8) extend this v1 walking skeleton along a frontier the PRD's own non-goals already named as "a possible v1.x addition, not a v1 commitment" — health scoring, a persistent fleet-health surface, an adoption-tracking axis, and safe upgrade-path recommendation. None reopen the "no new scanning engine" or "no real dependency-graph resolver" boundaries; each is a synthesis or wiring layer over data Doctor already gathers or a source that already exists elsewhere in the factory.

## Capabilities

- **CAP-1**
  - **intent:** An operator or Marshal can run `doctor check --env --engines` for a fast, tri-state pre-flight that wraps warden's engine-availability self-check and adds a new credential/environment-hygiene detector.
  - **success:** Engine findings are identical to warden's own `--doctor` output for the same environment; every check reports `ok`/`warn`/`fail` (never a bare boolean) and is individually nameable/filterable, including via `doctor check --list`, which enumerates every named check without running them; a JFROG_API_KEY-shaped unconditional-credential-injection pattern is caught by `--env`, and a host-scoped credential attach is not (no false positive).
- **CAP-2**
  - **intent:** An operator can run `doctor monitor --fleet --watch <axis>[,<axis>...]` to get one normalized, source-tagged fleet-pulse view over cf_atlas's staleness/cve/abandonment signals instead of reconciling five separate CLIs by hand.
  - **success:** Findings are equivalent to the underlying atlas CLI/MCP call for the same scope, each tagged and filterable by its originating Source; omitting `--watch` runs a documented default axis set (`staleness`, `cve`) rather than every axis unconditionally.
- **CAP-3**
  - **intent:** An operator triaging a target can run `doctor diagnose --target <target> --prescribe` to get every gathered finding partitioned (`actionable`/`blocked`/`accepted-risk`, none silently dropped) and the actionable set ranked by severity × exploitability × blast-radius, each entry naming a root cause.
  - **success:** The total finding count across all three partitions equals the count gathered; a KEV-flagged finding outranks a non-KEV one of equal severity, a higher-EPSS finding outranks a lower one at equal severity, and a smaller upgrade-lag classification outranks a larger one as tiebreaker; every Prescription shows its `rank_factors` (never a bare priority number) and a `root_cause` templated from the finding's own structured evidence (no new inference layer).
- **CAP-4**
  - **intent:** An operator or agent can request `--json` on every verb (`check`, `monitor`, `diagnose`) and get one schema-validated `DoctorReport` document carrying the same information as the human-readable output.
  - **success:** `--json` output validates against a committed JSON Schema; no information present in the human-readable render is absent from `--json` (parity requirement).
- **CAP-5** *(v1.x, added 2026-08-02 — dream "frontier" item 1)*
  - **intent:** An operator can see a composite health grade (A–F) per dependency, synthesized from Doctor's own already-gathered Finding data across axes (age/staleness, CVE exposure, abandonment signal) — an aggregation layer over existing sources, not a new scanning engine.
  - **success:** The grade is a pure function over an already-gathered `list[Finding]` (no new subprocess/MCP call of its own, same discipline AD-4 already holds `prescribe` to); the same Finding set always produces the same grade (deterministic, no timestamp-in-logic-path); an incomplete axis gather degrades the grade to explicitly `incomplete`, never a false `A`.
- **CAP-6** *(v1.x, added 2026-08-02 — dream "frontier" item 2)*
  - **intent:** An operator can see the fleet's health condition as a tracked, at-a-glance surface instead of reconstructing it from a point-in-time `monitor --fleet` snapshot.
  - **success:** The surface is derived output written from a `monitor --fleet` run (the same Finding/Source shape CAP-2 already produces — never a second, independent gather); regenerating from the same underlying findings is idempotent; the surface's own schema is versioned the same way `DoctorReport` is (NFR-5 precedent) so a consumer can detect a format change.
- **CAP-7** *(v1.x, added 2026-08-02 — dream "frontier" item 3)*
  - **intent:** An operator can add `adoption` to `monitor --fleet`'s `--watch` set and get cf_atlas's `adoption-stage` and `version-downloads` signals normalized into the same Finding shape as the existing staleness/cve/abandonment axes.
  - **success:** Follows AD-6 exactly (MCP-first, CLI-fallback via `cli_bridge`, both paths normalize identically); `adoption` is **not** in the default `--watch` set (CAP-2's default stays `staleness`+`cve` unless explicitly widened); a new `Source` enum member is added for it (AD-3's closed-taxonomy pattern extended, never an open/stringly-typed source).
- **CAP-8** *(v1.x, added 2026-08-02 — dream "frontier" item 4)*
  - **intent:** A Prescription from `diagnose --prescribe` can name a specific next-safe-version target, not just rank and explain.
  - **success:** The recommendation is single-hop only — this package's own next safe version, sourced from atlas's existing `behind-upstream`/version data — never a transitive multi-package resolution; a Prescription with no confidently-known safe version states that plainly rather than guessing one; `prescribe` stays a pure function over already-gathered data (AD-4 preserved — no new subprocess/MCP call added to `prescribe` itself).

## Constraints

- **AD-1 (library, not subprocess):** `doctor check --engines` calls `pyforge.warden.engines.run_doctor_checks` as a library import, never a subprocess reimplementation; `pyforge-doctor` declares `pyforge-warden` as an optional `gate` extra (mirrors `pyforge-atlas`'s identical existing edge to warden). A meta-test asserts `doctor.sources.warden` contains no subprocess import or call.
- **AD-2 (closed, non-merging exit-code space):** Doctor owns its own exit-code domain `{0 = all ok, 2 = a fail present, 130 = SIGINT}`, permanently omitting warden's policy-gate rung `1` — Doctor reports operability, never policy. A `warn`-status finding never changes the exit code. Warden's own exit code is consumed only as data, folded into a `Finding.status`, never re-exposed as Doctor's process exit code.
- **AD-3 (own closed taxonomy):** Doctor defines its own closed `Finding`/`Source`/`DoctorStatus` taxonomy (`DoctorStatus{ok,warn,fail}`, a closed `Source` enum with one member per wrapped instrument, a `Finding` dataclass) — structurally mirrors warden's `models.py` pattern but never imports warden's `ErrorKind` directly. CAP-7's new `adoption` source extends this same closed enum; it does not open it.
- **AD-4 (`--prescribe` is a pure function):** `pyforge.doctor.prescribe` takes an already-gathered `list[Finding]` and returns partitioned, ranked `Prescription` objects — zero subprocess or MCP calls of its own; a meta-test asserts no subprocess/MCP-client import exists in the module. CAP-5 (scoring) and CAP-8 (upgrade-path) preserve this: both are pure functions over already-gathered data, never a new gather path.
- **AD-5 (one narrow, typed subprocess site):** `pyforge.doctor.cli_bridge` is the only module in the package permitted to spawn a subprocess (the CLI-fallback branch of AD-6) — argv as a list (never a shell string), `NO_COLOR`-equivalent + `stdin=DEVNULL` discipline, bounded timeout, typed `Finding(status=fail)` on failure, never a raw traceback. A meta-test asserts `cli_bridge` is the only module containing a subprocess call.
- **AD-6 (MCP-first, CLI-fallback):** `monitor --fleet` calls cf_atlas's MCP tools when an MCP client is available in-process (the expected Marshal/agent path); otherwise it falls back to the equivalent CLI subprocess via AD-5's `cli_bridge`. Both paths must normalize to the identical `Finding` shape. CAP-7's adoption axis follows this same path, not a new one.
- **NFR-1 (read-only):** v1 is read-only/non-mutating across all three verbs — no module under `pyforge.doctor` writes outside a `tempfile`-scoped path or mutates a scanned tree; no `--fix`/actuator exists. CAP-6's persistent surface is derived/regenerable output, not a mutation of scanned state — it does not reopen this boundary.
- **NFR-4 (speed budget):** `doctor check`'s default run must stay within a documented speed budget (the five-second pre-flight promise) — a benchmark test guards against future checks regressing this; check-suite runtime must not creep upward in pursuit of more findings.
- **NFR-5 (schema-versioned envelope):** The `DoctorReport` JSON envelope (`{schema_version, verb, generated_at, findings, prescriptions}`) carries a `schema_version` field starting at `1`; `prescriptions` is present only when `verb=diagnose`. CAP-6's persistent surface reuses this same versioning discipline.
- **Env-hygiene detection boundary:** the check fires on an env-var read (`os.environ.get`/`os.getenv`) feeding an HTTP-header/auth assignment with no accompanying host-scope conditional; a host-scoped credential attach must NOT produce a finding. The scanner uses `ast.parse` only — never `exec`/`eval`/dynamic-import of scanned code.
- **Default Watch-axis set:** omitting `--watch` runs `staleness`+`cve` as the two highest-signal defaults, not every axis unconditionally. Adding `adoption` (CAP-7) does not change this default.
- **`check --list` ships in v1:** it enumerates every named check without running them; running one named check in isolation matches that check's result within the full suite.

## Non-goals

- No auto-remediation actuator in v1 — `check`/`monitor`/`diagnose` are strictly read-only; no `--fix`, no PR-opening, no file mutation.
- **No new scanning engines or data sources beyond the one credential/env-hygiene check.** Doctor consolidates warden + atlas only. CAP-5 (health scoring) is aggregation over Doctor's own already-gathered findings, not a new instrument; CAP-7 (adoption-tracking) wires an *existing* atlas source into the axis set, it does not add a new one — neither reopens this boundary.
- **No real dependency-graph topological resolver for `--prescribe`.** Ranking + a lag-magnitude tiebreaker only. CAP-8's upgrade-path recommendation is explicitly bounded to single-hop, this-package-only — never multi-package transitive resolution.
- No waiver-authoring UI for the `accepted-risk` partition — the partition exists for forward-compatibility; authoring/managing waivers is out of v1.
- Not a general-purpose OSS health-check tool — scoped to this factory's own instruments (warden, atlas) and this repo's own fleet.
- **A persistent fleet-health surface is now in scope (CAP-6) — this is the graduation the original PRD named as "a possible v1.x addition," not a reopened non-goal.** What stays out: any surface requiring its own independent data-gathering path (CAP-6 is strictly derived from `monitor --fleet` output).

## Success signal

Zero mid-build failures attributable to an environment/engine condition `doctor check` could have caught (measured across factory runs after adoption), and `doctor diagnose --prescribe`'s ranking judged by the operator as at least as good as manually cross-referencing warden + atlas output for the same target. Secondarily, `doctor monitor --fleet` replaces the operator's manual multi-CLI weekly habit in observed practice, and the credential/env-hygiene check is live and catches the JFROG_API_KEY worked example by v1 ship. Counter-signals that must NOT be optimized away: check-suite runtime creeping upward in pursuit of more findings, and prescription ranking optimized for list length over correct partitioning.

For CAP-5..8: a health grade is trusted enough that the operator checks it before running `diagnose` on a target (not after); the fleet-health surface is consulted instead of a fresh `monitor --fleet` run in observed practice; the adoption axis catches at least one real abandoned-but-not-yet-CVE'd package the staleness/cve axes alone would have missed; an upgrade-path recommendation is accepted by the operator without independently re-checking it first.

## Assumptions

- Marshal (the bmad-loop orchestrator) is the primary machine consumer of `doctor check` as an unattended pre-flight gate; the repo maintainer is the primary human consumer running things by hand.
- The ranking/adoption success signals are qualitative and self-observed — no analytics/telemetry infrastructure is built to measure them in v1, consistent with a single-operator internal tool.
- Agent-consumers (Marshal, other BMAD skills) are read-only callers of Doctor's CLI + `--json` family; Doctor needs no agent-specific API surface beyond a well-behaved CLI, consistent with warden's own CLI-first design.
- CAP-5..8 assume Epic 1-3's v1 walking skeleton (CAP-1..4) ships and proves itself first — the PRD's own sequencing, not reordered by this update.

## Open Questions

- Exact severity default (`warn` vs `fail`) for the credential-hygiene check when a risky pattern like JFROG_API_KEY unconditional injection is detected — unresolved through the full planning chain (the epics stage itself defers this to a `warn_or_fail` placeholder).
- Exact schema-versioning *policy* for the `DoctorReport` envelope — `schema_version` starts at `1` (fixed), but no rule is specified for what triggers a version bump or how consumers should react to one.
- CAP-6's persistent surface format (a tracked file, a dashboard page, a GitHub issue à la Renovate?) is not yet decided — the capability commits to "derived, idempotent, versioned," not a specific medium; that's an architecture-phase call.
