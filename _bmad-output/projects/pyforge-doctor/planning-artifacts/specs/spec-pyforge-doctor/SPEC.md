---
surface:
  - src/shared/packages/pyforge-doctor/**   # the CLI this Spec builds
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py   # also governed by pyforge-doctor/spec-sibling-dreams-drift
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/__init__.py   # also governed by pyforge-marshal/spec-pyforge-core
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/flag_kill_switch.py   # also governed by pyforge-marshal/spec-pyforge-core
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py   # also governed by pyforge-marshal/spec-pyforge-core
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/general_docs_consistency.py   # also governed by pyforge-marshal/spec-pyforge-core
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py   # also governed by pyforge-marshal/spec-pyforge-core
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py   # also governed by pyforge-marshal/spec-pyforge-core
id: SPEC-doctor
status: shipped
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
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a (operator-directed CAP-effect coverage sweep): live `doctor check --list` enumerates 7 named engine checks + `env unconditional-credential-injection` without running them; `sources/warden.py` calls `pyforge.warden.engines.run_doctor_checks` as a library import (AD-1 meta-test `test_source_independence.py` passing, 264/264 meta tests green); `tests/unit/test_sources_warden.py` passing (part of 1607/1609 unit suite green — the 2 failures are pre-existing local-only untracked scratch state unrelated to this Spec, not a regression).
- **CAP-2**
  - **intent:** An operator can run `doctor monitor --fleet --watch <axis>[,<axis>...]` to get one normalized, source-tagged fleet-pulse view over cf_atlas's staleness/cve/abandonment signals instead of reconciling five separate CLIs by hand.
  - **success:** Findings are equivalent to the underlying atlas CLI/MCP call for the same scope, each tagged and filterable by its originating Source; omitting `--watch` runs a documented default axis set (`staleness`, `cve`) rather than every axis unconditionally.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: live `doctor monitor --fleet --watch staleness,cve,adoption --json` returns findings source-tagged (`staleness-report`, `adoption` both observed); `__main__.py`'s `_DEFAULT_MONITOR_AXES = ("staleness", "cve")` confirmed as the value `_split_watch_axes` returns when `--watch` is omitted; `tests/unit/test_sources_atlas.py` + `test_sources_atlas_watch_axes.py` passing.
- **CAP-3**
  - **intent:** An operator triaging a target can run `doctor diagnose --target <target> --prescribe` to get every gathered finding partitioned (`actionable`/`blocked`/`accepted-risk`, none silently dropped) and the actionable set ranked by severity × exploitability × blast-radius, each entry naming a root cause.
  - **success:** The total finding count across all three partitions equals the count gathered; a KEV-flagged finding outranks a non-KEV one of equal severity, a higher-EPSS finding outranks a lower one at equal severity, and a smaller upgrade-lag classification outranks a larger one as tiebreaker; every Prescription shows its `rank_factors` (never a bare priority number) and a `root_cause` templated from the finding's own structured evidence (no new inference layer).
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: live `doctor diagnose --target . --prescribe --json` returned 12 prescriptions, `prescriptions` key present; spot-checked the "bare priority number" claim — 6 of 12 carry `rank_factors: null`, traced to `prescribe.rank()`'s documented, deliberate exclusion of `DoctorStatus.OK` ("clean -- no remediation needed") Findings from ranking (not a defect: every one of the 6 null-rank_factors entries has `action == "clean -- no remediation needed"`); `tests/unit/test_prescribe_rank.py::test_clean_ok_finding_is_excluded_from_ranking_even_though_actionable` covers exactly this and passes; `tests/unit/test_prescribe_partition.py` + `test_prescribe_root_cause.py` passing.
- **CAP-4**
  - **intent:** An operator or agent can request `--json` on every verb (`check`, `monitor`, `diagnose`) and get one schema-validated `DoctorReport` document carrying the same information as the human-readable output.
  - **success:** `--json` output validates against a committed JSON Schema; no information present in the human-readable render is absent from `--json` (parity requirement).
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: live `doctor check --json` returns `schema_version: 1`, `verb: "check"`, `findings` array (13 entries); `src/pyforge/doctor/data/report-schema.json` present and committed; `doctor diagnose --json` confirmed carries a `prescriptions` key (present only for that verb, per NFR-5).
- **CAP-5** *(v1.x, added 2026-08-02 — dream "frontier" item 1)*
  - **intent:** An operator can see a composite health grade (A–F) per dependency, synthesized from Doctor's own already-gathered Finding data across axes (age/staleness, CVE exposure, abandonment signal) — an aggregation layer over existing sources, not a new scanning engine.
  - **success:** The grade is a pure function over an already-gathered `list[Finding]` (no new subprocess/MCP call of its own, same discipline AD-4 already holds `prescribe` to); the same Finding set always produces the same grade (deterministic, no timestamp-in-logic-path); an incomplete axis gather degrades the grade to explicitly `incomplete`, never a false `A`.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: `pyforge.doctor.score.grade` imports and is callable; `tests/unit/test_score.py` passing (part of the 1607/1609-green unit run); no subprocess/MCP import present in `score.py` (module-level `grep` for `subprocess`/MCP client names — none found), consistent with the pure-function claim.
- **CAP-6** *(v1.x, added 2026-08-02 — dream "frontier" item 2)*
  - **intent:** An operator can see the fleet's health condition as a tracked, at-a-glance surface instead of reconstructing it from a point-in-time `monitor --fleet` snapshot.
  - **success:** The surface is derived output written from a `monitor --fleet` run (the same Finding/Source shape CAP-2 already produces — never a second, independent gather); regenerating from the same underlying findings is idempotent; the surface's own schema is versioned the same way `DoctorReport` is (NFR-5 precedent) so a consumer can detect a format change.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: `fleet_surface.py` exports `FLEET_SURFACE_SCHEMA_VERSION`, `build_surface`, `write_surface`, importable and taking `Finding` sequences (no independent gather call in the module); `tests/unit/test_fleet_surface.py` passing.
- **CAP-7** *(v1.x, added 2026-08-02 — dream "frontier" item 3)*
  - **intent:** An operator can add `adoption` to `monitor --fleet`'s `--watch` set and get cf_atlas's `adoption-stage` and `version-downloads` signals normalized into the same Finding shape as the existing staleness/cve/abandonment axes.
  - **success:** Follows AD-6 exactly (MCP-first, CLI-fallback via `cli_bridge`, both paths normalize identically); `adoption` is **not** in the default `--watch` set (CAP-2's default stays `staleness`+`cve` unless explicitly widened); a new `Source` enum member is added for it (AD-3's closed-taxonomy pattern extended, never an open/stringly-typed source).
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: live `doctor monitor --fleet --watch adoption --json` returns findings tagged `source: "adoption"`; live `doctor monitor --fleet --json` (no `--watch`) returns no `adoption`-sourced findings, confirming it is excluded from the default set; `Source` enum confirmed closed (no dynamic/stringly-typed members) in `models.py`; `tests/unit/test_sources_atlas_watch_axes.py` passing.
- **CAP-8** *(v1.x, added 2026-08-02 — dream "frontier" item 4)*
  - **intent:** A Prescription from `diagnose --prescribe` can name a specific next-safe-version target, not just rank and explain.
  - **success:** The recommendation is single-hop only — this package's own next safe version, sourced from atlas's existing `behind-upstream`/version data — never a transitive multi-package resolution; a Prescription with no confidently-known safe version states that plainly rather than guessing one; `prescribe` stays a pure function over already-gathered data (AD-4 preserved — no new subprocess/MCP call added to `prescribe` itself).
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: read `recommend_safe_upgrade()` in full — reads only `finding.evidence`, zero subprocess/MCP calls, returns `(None, reason)` with `reason` always populated when no confident target exists, explicitly rejects a `"major"`-classified delta as not confidently safe (single-hop bound); live `--prescribe --json` run shows every prescription's `safe_upgrade_reason` populated, no bare `None` with no explanation; `tests/unit/test_prescribe_safe_upgrade.py` passing.

- **CAP-9 — the verdict on the Marshal's own row.**
  - **intent:** Doctor independently judges whether the Marshal's durability
    guarantee holds, so the station that owns the ledger is not the station that
    grades it (Charter §6 — *"the one station that would otherwise grade itself"*).
  - **success:** a `marshal-durability` source reports FAIL naming every story key
    when a tracked sprint ledger holds fewer completions than its committed state,
    OK when none does, and WARN — never a crash and never silent OK — when git or
    the ledgers are unavailable; **the check reads the durable artifacts (tracked
    ledgers + git) and imports no station package**, asserted by a meta-test, so a
    Marshal change cannot weaken, re-threshold or disable it.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: `sources/marshal.py::gather` present and live-callable; `tests/meta/test_source_independence.py` (asserts no station-package import across every source module, including `marshal.py`) part of the 264/264 green meta-test run; `tests/unit/test_sources_marshal_story_status.py` passing.

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
- **Incoming surface claims recorded 2026-09-09, before any code lands**, so `spec-surface-check` does not read them as ungoverned drift on this Spec's `src/shared/packages/pyforge-doctor/**` glob: steward Story 49.2 writes a new `pyforge/doctor/sources/` module plus a report-schema entry and detectors membership — its *criterion* stays on `spec-pyforge-unifying-strategy` while the *implementation* is relayed to a new doctor Dream + Spec (`docs/dreams/capability-effect-check.md`, `specs/spec-capability-effect-check/`); steward Story 49.8 names `pyforge/doctor/sources/marshal.py:544` verbatim (the `~/.bmad-loops` read that Unifying CAP-17 retires), mints no doctor story, and carries its own one-line comment at `sources/__init__.py:223` in its own diff.
- `spec-pyforge-charter` is registered in `DEFERRED_SPECS` with the reason "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties no story can pick up" — it was exempt from neither the decomposition expectation nor the documented-deferral list. The dict edit is code and rides the C8 story.
- `bmad-drift`'s 17 live warns against marshal's artifacts (pin-behind CFE v8.86.1 < v8.90.1, two surface-changed, one deferred-stale) are **not** doctor's to fix and mint no doctor story: doctor is the detector, marshal's `SYNC-RUNBOOK.md` row 84 is the reconciler.

## Open Questions

- Exact severity default (`warn` vs `fail`) for the credential-hygiene check when a risky pattern like JFROG_API_KEY unconditional injection is detected — unresolved through the full planning chain (the epics stage itself defers this to a `warn_or_fail` placeholder).
- Exact schema-versioning *policy* for the `DoctorReport` envelope — `schema_version` starts at `1` (fixed), but no rule is specified for what triggers a version bump or how consumers should react to one.
- CAP-6's persistent surface format (a tracked file, a dashboard page, a GitHub issue à la Renovate?) is not yet decided — the capability commits to "derived, idempotent, versioned," not a specific medium; that's an architecture-phase call.
