---
surface:
  - src/shared/packages/pyforge-doctor/**   # the CLI this Spec builds
id: SPEC-doctor
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

## Constraints

- **AD-1 (library, not subprocess):** `doctor check --engines` calls `pyforge.warden.engines.run_doctor_checks` as a library import, never a subprocess reimplementation; `pyforge-doctor` declares `pyforge-warden` as an optional `gate` extra (mirrors `pyforge-atlas`'s identical existing edge to warden). A meta-test asserts `doctor.sources.warden` contains no subprocess import or call.
- **AD-2 (closed, non-merging exit-code space):** Doctor owns its own exit-code domain `{0 = all ok, 2 = a fail present, 130 = SIGINT}`, permanently omitting warden's policy-gate rung `1` — Doctor reports operability, never policy. A `warn`-status finding never changes the exit code. Warden's own exit code is consumed only as data, folded into a `Finding.status`, never re-exposed as Doctor's process exit code.
- **AD-3 (own closed taxonomy):** Doctor defines its own closed `Finding`/`Source`/`DoctorStatus` taxonomy (`DoctorStatus{ok,warn,fail}`, a closed `Source` enum with one member per wrapped instrument, a `Finding` dataclass) — structurally mirrors warden's `models.py` pattern but never imports warden's `ErrorKind` directly.
- **AD-4 (`--prescribe` is a pure function):** `pyforge.doctor.prescribe` takes an already-gathered `list[Finding]` and returns partitioned, ranked `Prescription` objects — zero subprocess or MCP calls of its own; a meta-test asserts no subprocess/MCP-client import exists in the module.
- **AD-5 (one narrow, typed subprocess site):** `pyforge.doctor.cli_bridge` is the only module in the package permitted to spawn a subprocess (the CLI-fallback branch of AD-6) — argv as a list (never a shell string), `NO_COLOR`-equivalent + `stdin=DEVNULL` discipline, bounded timeout, typed `Finding(status=fail)` on failure, never a raw traceback. A meta-test asserts `cli_bridge` is the only module containing a subprocess call.
- **AD-6 (MCP-first, CLI-fallback):** `monitor --fleet` calls cf_atlas's MCP tools when an MCP client is available in-process (the expected Marshal/agent path); otherwise it falls back to the equivalent CLI subprocess via AD-5's `cli_bridge`. Both paths must normalize to the identical `Finding` shape.
- **NFR-1 (read-only):** v1 is read-only/non-mutating across all three verbs — no module under `pyforge.doctor` writes outside a `tempfile`-scoped path or mutates a scanned tree; no `--fix`/actuator exists.
- **NFR-4 (speed budget):** `doctor check`'s default run must stay within a documented speed budget (the five-second pre-flight promise) — a benchmark test guards against future checks regressing this; check-suite runtime must not creep upward in pursuit of more findings.
- **NFR-5 (schema-versioned envelope):** The `DoctorReport` JSON envelope (`{schema_version, verb, generated_at, findings, prescriptions}`) carries a `schema_version` field starting at `1`; `prescriptions` is present only when `verb=diagnose`.
- **Env-hygiene detection boundary:** the check fires on an env-var read (`os.environ.get`/`os.getenv`) feeding an HTTP-header/auth assignment with no accompanying host-scope conditional; a host-scoped credential attach must NOT produce a finding. The scanner uses `ast.parse` only — never `exec`/`eval`/dynamic-import of scanned code.
- **Default Watch-axis set:** omitting `--watch` runs `staleness`+`cve` as the two highest-signal defaults, not every axis unconditionally.
- **`check --list` ships in v1:** it enumerates every named check without running them; running one named check in isolation matches that check's result within the full suite.

## Non-goals

- No auto-remediation actuator in v1 — `check`/`monitor`/`diagnose` are strictly read-only; no `--fix`, no PR-opening, no file mutation.
- No persistent fleet-health surface (dashboard/tracked-issue/status file) in v1 — CLI + JSON output only; a possible v1.x addition, not a v1 commitment.
- No new scanning engines or data sources — Doctor consolidates warden + atlas only; the credential/env-hygiene check is the one new detection capability, not a precedent for adding others in v1.
- No real dependency-graph topological resolver for `--prescribe` — ranking + lag-magnitude tiebreaker only in v1.
- No waiver-authoring UI for the `accepted-risk` partition — the partition exists for forward-compatibility; authoring/managing waivers is out of v1.
- Not a general-purpose OSS health-check tool — scoped to this factory's own instruments (warden, atlas) and this repo's own fleet.

## Success signal

Zero mid-build failures attributable to an environment/engine condition `doctor check` could have caught (measured across factory runs after adoption), and `doctor diagnose --prescribe`'s ranking judged by the operator as at least as good as manually cross-referencing warden + atlas output for the same target. Secondarily, `doctor monitor --fleet` replaces the operator's manual multi-CLI weekly habit in observed practice, and the credential/env-hygiene check is live and catches the JFROG_API_KEY worked example by v1 ship. Counter-signals that must NOT be optimized away: check-suite runtime creeping upward in pursuit of more findings, and prescription ranking optimized for list length over correct partitioning.

## Assumptions

- Marshal (the bmad-loop orchestrator) is the primary machine consumer of `doctor check` as an unattended pre-flight gate; the repo maintainer is the primary human consumer running things by hand.
- The ranking/adoption success signals are qualitative and self-observed — no analytics/telemetry infrastructure is built to measure them in v1, consistent with a single-operator internal tool.
- Agent-consumers (Marshal, other BMAD skills) are read-only callers of Doctor's CLI + `--json` family; Doctor needs no agent-specific API surface beyond a well-behaved CLI, consistent with warden's own CLI-first design.

## Open Questions

- Exact severity default (`warn` vs `fail`) for the credential-hygiene check when a risky pattern like JFROG_API_KEY unconditional injection is detected — unresolved through the full planning chain (the epics stage itself defers this to a `warn_or_fail` placeholder).
- Exact schema-versioning *policy* for the `DoctorReport` envelope — `schema_version` starts at `1` (fixed), but no rule is specified for what triggers a version bump or how consumers should react to one.
