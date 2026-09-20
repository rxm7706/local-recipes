---
surface:
  - src/shared/packages/pyforge-doctor/**
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
  - scripts/chain_currency_sweep_check.py
  - scripts/deferred_work_check.py
  - scripts/deferred_work_intake.py
  - docs/MAP.md
  - docs/how-to/**
  - docs/tutorials/**
  - docs/explanation/**
  - .claude/data/conda-forge-expert/
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/**
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py
  - docs/map.yaml
  - scripts/docs_map_render.py
surface-drift-exclude:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/flag_kill_switch.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/general_docs_consistency.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py
id: SPEC-pyforge-doctor
status: ready
owner-dream: docs/dreams/pyforge-doctor.md
companions:
  - ../../architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - live-proof-surfaces.md
sources:
  - ../../../../../../docs/dreams/pyforge-doctor.md
  - ../../briefs/brief-pyforge-doctor-2026-07-25/brief.md
  - ../../prds/prd-pyforge-doctor-2026-07-25/prd.md
  - ../../epics.md
spec: pyforge-doctor
updated: '2026-09-19'
covers-dreams:
  - docs/dreams/bmad-drift-new-artifact-shape.md
  - docs/dreams/bmad-method-version-drift.md
  - docs/dreams/capability-effect-check.md
  - docs/dreams/chain-currency-sweep.md
  - docs/dreams/deferred-work-audit-completeness.md
  - docs/dreams/deferred-work-resolution-sweep.md
  - docs/dreams/deferred-work-visibility.md
  - docs/dreams/docs-shelf-alignment.md
  - docs/dreams/fleet-hygiene-verification-exemplar-program.md
  - docs/dreams/general-docs-consistency.md
  - docs/dreams/pixi-candidate-currency.md
  - docs/dreams/pyforge-doctor-dependency-health.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/sibling-dreams-drift.md
  - docs/dreams/status-body-consistency.md
---

> **Canonical contract.** Derived from `.memlog.md` and the folded Specs on 2026-09-17 (one-chain-per-station CAP-3 / doctor fold). Companions of absorbed folders stay as record (CHAIN-STANDARD §7 item 3). Do not hand-edit — append the memlog and re-derive.

# Doctor (pyforge-doctor) — one bedside manner for the whole fleet

## Why

A pain already diagnosed, not a fresh idea: the factory's health signal already exists but is scattered across tools an operator or agent has to know about individually — pyforge-warden's engine-availability self-check, and cf_atlas's `feedstock-health`/`staleness-report`/`behind-upstream`/`cve-watcher`/`release-cadence`/`adoption-stage` CLIs — with no shared vocabulary for severity and no ranked prescription. Three concrete pains follow: no pre-flight gate (a missing engine or bad credential-scope config surfaces mid-build instead of in the first five seconds), no fleet pulse (an operator reconciles five separate CLI outputs by hand to answer "what got worse this week"), and no prescription (findings exist but nothing ranks them into "do this first"). Doctor (module `pyforge.doctor`, CLI `doctor`) is the pyforge Guild's health & diagnostics station: one bedside manner over instruments that already exist, wrapping them behind three verbs (`check`, `monitor`, `diagnose`) rather than adding a new detection engine. Its value is integration completeness and ranking quality, not new instrumentation — Marshal (the bmad-loop orchestrator) is the primary machine consumer, the repo maintainer the primary human one.

Four further capabilities (CAP-5..8) extend this v1 walking skeleton along a frontier the PRD's own non-goals already named as "a possible v1.x addition, not a v1 commitment" — health scoring, a persistent fleet-health surface, an adoption-tracking axis, and safe upgrade-path recommendation. None reopen the "no new scanning engine" or "no real dependency-graph resolver" boundaries; each is a synthesis or wiring layer over data Doctor already gathers or a source that already exists elsewhere in the factory.

## Capabilities
- **CAP-1 — An operator or Marshal can run `doctor check --env --engines` for a fast** ← spec-pyforge-doctor CAP-1 (shipped 2026-09-17)
  - **intent:** An operator or Marshal can run `doctor check --env --engines` for a fast, tri-state pre-flight that wraps warden's engine-availability self-check and adds a new credential/environment-hygiene detector.
  - **success:** Engine findings are identical to warden's own `--doctor` output for the same environment; every check reports `ok`/`warn`/`fail` (never a bare boolean) and is individually nameable/filterable, including via `doctor check --list`, which enumerates every named check without running them; a JFROG_API_KEY-shaped unconditional-credential-injection pattern is caught by `--env`, and a host-scoped credential attach is not (no false positive).
- **CAP-2 — An operator can run `doctor monitor --fleet --watch <axis>[,<axis>** ← spec-pyforge-doctor CAP-2 (shipped 2026-09-17)
  - **intent:** An operator can run `doctor monitor --fleet --watch <axis>[,<axis>...]` to get one normalized, source-tagged fleet-pulse view over cf_atlas's staleness/cve/abandonment signals instead of reconciling five separate CLIs by hand.
  - **success:** Findings are equivalent to the underlying atlas CLI/MCP call for the same scope, each tagged and filterable by its originating Source; omitting `--watch` runs a documented default axis set (`staleness`, `cve`) rather than every axis unconditionally.
- **CAP-3 — An operator triaging a target can run `doctor diagnose --target <target>** ← spec-pyforge-doctor CAP-3 (shipped 2026-09-17)
  - **intent:** An operator triaging a target can run `doctor diagnose --target <target> --prescribe` to get every gathered finding partitioned (`actionable`/`blocked`/`accepted-risk`, none silently dropped) and the actionable set ranked by severity × exploitability × blast-radius, each entry naming a root cause.
  - **success:** The total finding count across all three partitions equals the count gathered; a KEV-flagged finding outranks a non-KEV one of equal severity, a higher-EPSS finding outranks a lower one at equal severity, and a smaller upgrade-lag classification outranks a larger one as tiebreaker; every Prescription shows its `rank_factors` (never a bare priority number) and a `root_cause` templated from the finding's own structured evidence (no new inference layer).
- **CAP-4 — An operator or agent can request `--json` on every verb (`check`, `monit** ← spec-pyforge-doctor CAP-4 (shipped 2026-09-17)
  - **intent:** An operator or agent can request `--json` on every verb (`check`, `monitor`, `diagnose`) and get one schema-validated `DoctorReport` document carrying the same information as the human-readable output.
  - **success:** `--json` output validates against a committed JSON Schema; no information present in the human-readable render is absent from `--json` (parity requirement).
- **CAP-5 — An operator can see a composite health grade (A–F) per dependency, synth** ← spec-pyforge-doctor CAP-5 (shipped 2026-09-17)
  - **intent:** An operator can see a composite health grade (A–F) per dependency, synthesized from Doctor's own already-gathered Finding data across axes (age/staleness, CVE exposure, abandonment signal) — an aggregation layer over existing sources, not a new scanning engine.
  - **success:** The grade is a pure function over an already-gathered `list[Finding]` (no new subprocess/MCP call of its own, same discipline AD-4 already holds `prescribe` to); the same Finding set always produces the same grade (deterministic, no timestamp-in-logic-path); an incomplete axis gather degrades the grade to explicitly `incomplete`, never a false `A`.
- **CAP-6 — An operator can see the fleet's health condition as a tracked, at-a-glan** ← spec-pyforge-doctor CAP-6 (shipped 2026-09-17)
  - **intent:** An operator can see the fleet's health condition as a tracked, at-a-glance surface instead of reconstructing it from a point-in-time `monitor --fleet` snapshot.
  - **success:** The surface is derived output written from a `monitor --fleet` run (the same Finding/Source shape CAP-2 already produces — never a second, independent gather); regenerating from the same underlying findings is idempotent; the surface's own schema is versioned the same way `DoctorReport` is (NFR-5 precedent) so a consumer can detect a format change.
- **CAP-7 — An operator can add `adoption` to `monitor --fleet`'s `--watch` set and** ← spec-pyforge-doctor CAP-7 (shipped 2026-09-17)
  - **intent:** An operator can add `adoption` to `monitor --fleet`'s `--watch` set and get cf_atlas's `adoption-stage` and `version-downloads` signals normalized into the same Finding shape as the existing staleness/cve/abandonment axes.
  - **success:** Follows AD-6 exactly (MCP-first, CLI-fallback via `cli_bridge`, both paths normalize identically); `adoption` is **not** in the default `--watch` set (CAP-2's default stays `staleness`+`cve` unless explicitly widened); a new `Source` enum member is added for it (AD-3's closed-taxonomy pattern extended, never an open/stringly-typed source).
- **CAP-8 — A Prescription from `diagnose --prescribe` can name a specific next-safe** ← spec-pyforge-doctor CAP-8 (shipped 2026-09-17)
  - **intent:** A Prescription from `diagnose --prescribe` can name a specific next-safe-version target, not just rank and explain.
  - **success:** The recommendation is single-hop only — this package's own next safe version, sourced from atlas's existing `behind-upstream`/version data — never a transitive multi-package resolution; a Prescription with no confidently-known safe version states that plainly rather than guessing one; `prescribe` stays a pure function over already-gathered data (AD-4 preserved — no new subprocess/MCP call added to `prescribe` itself).
- **CAP-9 — the verdict on the Marshal's own row** ← spec-pyforge-doctor CAP-9 (shipped 2026-09-17)
  - **intent:** Doctor independently judges whether the Marshal's durability
  - **success:** a `marshal-durability` source reports FAIL naming every story key
- **CAP-10 — backlog-intake surfacing** ← spec-backlog-intake-check CAP-1 (shipped 2026-09-17)
  - **intent:** When a new story/spec is drafted for an epic, tracked deferred-work entries whose `owner:`/prose names that epic or a story within it are surfaced as candidate acceptance criteria, instead of staying inert prose only a human happens to notice by re-reading the ledger.
  - **success:** Given a story/spec draft naming epic E, tracked deferred-work entries across the fleet's ledgers whose `owner:`/prose names epic E or a story within it are surfaced to the drafting session as candidates.
- **CAP-11 — `classify()` recognizes the spike-report shape -- a file matching the** ← spec-bmad-drift-new-artifact-shape CAP-1 (shipped 2026-09-17)
  - **intent:** `classify()` recognizes the spike-report shape -- a file matching the
  - **success:** Re-running `check_coverage` against the live `pyforge-marshal` tree no longer
- **CAP-12 — The fix ships as one classification rule, added in the same place and th** ← spec-bmad-drift-new-artifact-shape CAP-2 (shipped 2026-09-17)
  - **intent:** The fix ships as one classification rule, added in the same place and the same
  - **success:** A file that still matches no rule at all -- including a spike-report look-alike
- **CAP-13 — declared-vs-installed drift** ← spec-bmad-method-version-drift CAP-1 (shipped 2026-09-17)
  - **intent:** An operator or agent sees when `pixi.toml`'s declared `bmad-method` floor and the actually-installed `_bmad/_config/manifest.yaml` version disagree, without checking by hand.
  - **success:** Given today's real state (`pixi.toml` `>=6.11.0`, `manifest.yaml` `6.10.0`), the new Source's Finding fires; given both agree, no Finding fires. Needs zero new infrastructure — both are already-tracked repo files.
- **CAP-14 — installed-vs-upstream-latest drift** ← spec-bmad-method-version-drift CAP-2 (shipped 2026-09-17)
  - **intent:** An operator or agent sees when the installed core is behind the latest published upstream `bmad-method` release, not just behind the repo's own declared floor. Data source: a live npm registry query (`https://registry.npmjs.org/bmad-method/latest` or equivalent) issued at check time — an operator-approved, deliberate exception to the fleet's general "no live query per home" discipline, scoped narrowly to this one ambient, non-gating, warn-only Finding (CAP-3).
  - **success:** Given the installed `manifest.yaml` version is older than the latest upstream release returned by the live query, a Finding fires naming both versions. Given the query fails or times out (offline, registry unreachable), no Finding fires and no error surfaces — CAP-2 degrades silently to CAP-1-only, never blocking or failing the check-suite (CAP-3's constraint applies here too).
- **CAP-15 — ambient, non-gating surface** ← spec-bmad-method-version-drift CAP-3 (shipped 2026-09-17)
  - **intent:** The drift Finding appears where operators already look — Doctor's own report/verdict shape and `fleet-picture`'s ATTENTION block — and never blocks or fails a check-suite run on its own.
  - **success:** `fleet-picture`'s ATTENTION block names the drift when CAP-1 or CAP-2 fire; the check-suite's exit code is unaffected by this Finding alone (a `warn`, never a `fail`).
- **CAP-16 — suite-vs-upstream drift** ← spec-bmad-method-version-drift CAP-4 (shipped 2026-09-17)
  - **intent:** The same ambient signal covers the installed bmad-suite, not just the core. Motivating evidence (2026-08-21, the live 6.10.0→6.11.0 upgrade session): `bmad-loop` sat at 0.9.0 against upstream 0.11.0 — 0.9.0 hardcodes `/bmad-dev-auto` and stalls every unattended session on BMAD ≥ 6.11, which upstream patched in an emergency 0.9.1 — while TEA lagged 1.19.1 vs 1.23.2 (1.19.1's `tea-test-review` bin was published empty), and three coordinated ecosystem waves rode the window. None of it produced any ambient signal until a human checked.
  - **success:** The watched set is DERIVED from `pixi.toml`'s `bmad-*` pins (never a hardcoded list — a hardcoded list omits exactly the newest tool); installed environment versions are compared against latest upstream releases through the same fail-open live-query exception CAP-2 already holds; warn-only per CAP-3. Pointed at the 2026-08-21 pre-update state, it names `bmad-loop 0.9.0 < 0.11.0` and `TEA 1.19.1 < 1.23.2`; offline it degrades silently.
- **CAP-17 — the caller-outside-its-own-tests check** ← spec-capability-effect-check CAP-1 (shipped 2026-09-17)
  - **intent:** For every declared capability whose citing story names Python surfaces, the
  - **success:** Run over every `pyforge-*` package in `src/shared/packages/`, it names
- **CAP-18 — the `verified:` line, rendered per CAP** ← spec-capability-effect-check CAP-2 (shipped 2026-09-17)
  - **intent:** A capability may carry `verified: <date> — <what was exercised, where>` on the
  - **success:** The "realized versus verified" column the Unifying Strategy's own 2026-09-09
- **CAP-19 — it renders where the operator already looks** ← spec-capability-effect-check CAP-3 (shipped 2026-09-17)
  - **intent:** The new Source appears in the doctor report and the `fleet-picture` ATTENTION
  - **success:** One `detectors` run answers both "did the story land" and "is the capability
- **CAP-20 — the sweep detector (SHIPPED)** ← spec-chain-currency-sweep CAP-1 (shipped 2026-09-17)
  - **intent:** Any agent can learn, in one command, whether the eight station planning spines are current — the per-project chain audit narrowed to the staleness + coherence checkpoints and looped across all eight station slugs.
  - **success:** `pixi run -e local-recipes chain-currency-sweep-check` (as-built: `scripts/chain_currency_sweep_check.py`, auto-discovered registry) exits 0 when all spines are current, 1 on any staleness/coherence finding, 2 when a station's audit could not run; supports `--json` and `--project <slug>`.
- **CAP-21 — the runbook is the procedure of record** ← spec-chain-currency-sweep CAP-2 (shipped 2026-09-17)
  - **intent:** A red detector is dispatched straight into remediation from the tracked runbook — the audit's real mechanics (feeds cascade order, 2-day grace window, strict `updated:` frontmatter precedence), the finding→remedy map, and the dispatch/land rules — never re-reverse-engineered per run.
  - **success:** An agent given only `CHAIN-CURRENCY-RUNBOOK.md` and a red detector clears the findings without reading detector internals; the detector's failure output names the runbook.
- **CAP-22 — triggered per-station cascades** ← spec-chain-currency-sweep CAP-3 (shipped 2026-09-17)
  - **intent:** The sweep runs on its trigger set — a fleet research wave, a spec re-stamp campaign, an epic close landing substantial code, or the detector going red — as eight independent per-station cascades (brief → PRD → arch → epics validation, plus a retro wherever code→retro fired), one commit per station, all inside one grace window.
  - **success:** After a sweep, `chain-currency-sweep-check` exits 0 across all 8 stations; each cascade was dispatched as single-story work.
- **CAP-23 — the grounding triple** ← spec-chain-currency-sweep CAP-4 (shipped 2026-09-17)
  - **intent:** Every artifact touched is reconciled against all three mandatory sources: (1) the upstream artifact that fired the edge, folded in rather than cited; (2) the Unifying Strategy pack (`spec-pyforge-unifying-strategy` + stack, console-parity inventory, architecture diagrams, resilience invariants) so the station's contract states its hub-and-spoke role; (3) the as-built `src/` code, with contract-vs-code divergence written down, never papered over.
  - **success:** Each reconciled artifact's dated addendum names all three grounding sources; when the strategy spec is itself `overtaken`, it is resolved before any station cascade grounds on it.
- **CAP-24 — no stamp without reconcile** ← spec-chain-currency-sweep CAP-5 (shipped 2026-09-17)
  - **intent:** Every `updated:` frontmatter bump is accompanied by a dated reconciliation addendum in the same file — an `updated:` bump without a genuine reconcile is lying to the board and is forbidden.
  - **success:** In any sweep PR, every diff hunk that bumps `updated:` pairs with a dated addendum in that same file; a stamp-only diff fails review.
- **CAP-25 — Worked-Example accumulation** ← spec-chain-currency-sweep CAP-6 (shipped 2026-09-17)
  - **intent:** Each sweep run leaves a record in the runbook, timeless-workflow style, so the procedure compounds — proportionate to the run, not a fixed narrative cost.
  - **success:** Run 1 — the 2026-08-26 clearance of 26 findings + 1 overtaken — lands as the runbook's validation Worked Example; every later run appends a one-line entry (date, findings cleared, deviations). A run that appends nothing has not completed its Land step.
- **CAP-26 — due-for-verification selection** ← spec-deferred-work-resolution-sweep CAP-1 (in-progress 2026-09-17)
  - **intent:** A sweep can select tracked entries needing verification — no `verified:` line at all, or a `verified:` date older than a staleness threshold — batched per project, without a human enumerating them by hand.
  - **success:** Given the fleet's current ~400+ tracked entries, running the selector returns exactly the entries with no `verified:` line or a stale one — demonstrated against the current ~150+ never-verified entries (mason/steward/scribe plus all promotions since the 2026-07-30 campaign).
- **CAP-27 — churn-based cost filtering** ← spec-deferred-work-resolution-sweep CAP-2 (in-progress 2026-09-17)
  - **intent:** Entries whose named file/path has had zero commits since their last verified date (or since authoring, if never verified) are deprioritized, since nothing could have changed.
  - **success:** Given an entry whose named path has zero commits since its last-verified date, the sweep does not select it for agent verification (or flags it `skip-reason: no-churn`); given commits since, it is selected.
- **CAP-28 — tiered verification, mechanical first** ← spec-deferred-work-resolution-sweep CAP-3 (in-progress 2026-09-17)
  - **intent:** A sweep attempts a cheap structural/grep-level check first for mechanically-checkable claims, escalating to an agent read only when the claim genuinely requires judgment.
  - **success:** Given an entry whose claim is grep-recomputable (e.g. "N call sites of X"), the mechanical check alone produces a verdict with no agent invocation; given a judgment-requiring claim, it escalates.
- **CAP-29 — evidence-grounded verdict recording, four verdicts** ← spec-deferred-work-resolution-sweep CAP-4 (in-progress 2026-09-17)
  - **intent:** For entries needing judgment, a verification agent reads the entry, locates the named code, and writes a `verified: <date> — <verdict>` line backed by cited evidence (a `file:line` or a reproduced/measured fact), never a restatement of the entry's own prose. The verdict is one of four: still-open, resolved, moot/superseded (cited), or pending-on-precondition — never a forced false confirm just to close the loop.
  - **success:** Every `verified:` line cites a `file:line` or a reproduced/measured fact; a scope correction (entry claims 2 packages, sweep finds 8) is written as the corrected number; an entry whose code no longer exists closes as moot/superseded citing what replaced or removed it.
- **CAP-30 — cross-project reach** ← spec-deferred-work-resolution-sweep CAP-5 (in-progress 2026-09-17)
  - **intent:** Whatever selects and verifies work for a batch can read any project's source tree, not just the owning project's.
  - **success:** Given an entry in project A whose defect was actually fixed by a commit in project B (the precedent's real `atlas DW-I5-1` case, resolved in marshal's `core/policy.py`), the sweep's verification step reads project B's tree and correctly closes the entry.
- **CAP-31 — cross-entry, cross-project correlation** ← spec-deferred-work-resolution-sweep CAP-6 (in-progress 2026-09-17)
  - **intent:** The sweep actively looks for near-duplicate entries (same file/symbol across different projects' ledgers, or near-identical summary text) and surfaces them as one defect-class group, not independent low-priority entries.
  - **success:** Given two or more tracked entries across different projects naming the same file/symbol or near-identical summary text, the sweep's report groups them as a single defect class.
- **CAP-32 — fleet-wide staleness signal** ← spec-deferred-work-resolution-sweep CAP-7 (in-progress 2026-09-17)
  - **intent:** `fleet_picture.py`'s ATTENTION block surfaces "% of tracked entries verified within N days, per project" as an ongoing signal.
  - **success:** After the sweep has run at least once, fleet-picture's ATTENTION block includes a per-project staleness percentage line, sourced from each project's tracked ledger's `verified:` dates.
- **CAP-33 — backlog-intake check. SPLIT OUT 2026-08-21 — no longer part of this Spec** ← spec-deferred-work-resolution-sweep CAP-8 (in-progress 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-34 — the intake guard** ← spec-deferred-work-resolution-sweep CAP-9 (in-progress 2026-09-17)
  - **intent:** Deferred-work intake refuses — or explicitly flags — an entry that cites no resolvable `location:`, so the ledger stops accumulating claims no sweep can ever check.
  - **success:** An entry with no extractable repo path is rejected at defer time (or emitted carrying an explicit unverifiable marker), and the fleet's never-verified population stops growing.
- **CAP-35 — a deferral carries identity from birth** ← spec-deferred-work-visibility CAP-1 (in-progress 2026-09-17)
  - **intent:** A review pass that defers something produces an entry bearing an id under the
  - **success:** a newly damped story leaves a Tier-3 entry whose id matches that station's
- **CAP-36 — the detector sees what it claims to check** ← spec-deferred-work-visibility CAP-2 (in-progress 2026-09-17)
  - **intent:** Anonymous Tier-3 entries are reported rather than silently skipped, so "every
  - **success:** deleting an id heading from a Tier-3 entry **reds** the detector — demonstrated
- **CAP-37 — the existing 470 do not red every landing pass on day one** ← spec-deferred-work-visibility CAP-3 (in-progress 2026-09-17)
  - **intent:** The backlog that accumulated while the detector was blind is baselined, and the
  - **success:** after the detector learns the anonymous shape, a landing pass is green on an
- **CAP-38 — a pre-CAP-1 anonymous entry is correctly parsed, whatever legacy shape it used** ← spec-deferred-work-visibility CAP-4 (in-progress 2026-09-17)
  - **intent:** CAP-1 only stops *new* anonymous entries. Legacy ones use at least two distinct
  - **success:** a parser fixture built from real excerpts of both legacy shapes, plus CAP-1's
- **CAP-39 — a legacy entry mints a collision-free id in CAP-1's own per-station convention** ← spec-deferred-work-visibility CAP-5 (in-progress 2026-09-17)
  - **intent:** Promoting old backlog entries must not invent a second id scheme alongside the
  - **success:** minting against a tracked ledger that already has entries for a story picks the
- **CAP-40 — a `--fix` mode promotes every genuine legacy-anonymous entry safely** ← spec-deferred-work-visibility CAP-6 (in-progress 2026-09-17)
  - **intent:** Mirrors `scripts/spec_surface_check.py`'s `--write-baseline` pattern: classify
  - **success:** running `--fix` against the live 72-entry backlog (marshal 30, steward 38,
- **CAP-41 — the grandfather baseline stays in lockstep with `--fix`** ← spec-deferred-work-visibility CAP-7 (in-progress 2026-09-17)
  - **intent:** After a `--fix` run, `scripts/.deferred-work-baseline.json` (CAP-3's own
  - **success:** running `--fix` twice in a row is a no-op the second time — 0 new writes, 0
- **CAP-42 — a fleet-wide hygiene sweep, generalizing the warden-only precedent** ← spec-deferred-work-visibility CAP-8 (in-progress 2026-09-17)
  - **intent:** The 2026-08-14/15 `bmad-output-hygiene` pass (dead test scaffolding archival,
  - **success:** running the sweep against all 8 projects reproduces warden's own 5 finding
- **CAP-43 — hygiene findings are reported, never auto-applied** ← spec-deferred-work-visibility CAP-9 (in-progress 2026-09-17)
  - **intent:** A dead-scaffolding or orphan-file finding names the path and the evidence for
  - **success:** the sweep's own invocation never mutates a file; every finding it reports is
- **CAP-44 — loop-home branch staleness is visible without a human asking** ← spec-deferred-work-visibility CAP-10 (in-progress 2026-09-17)
  - **intent:** `fleet_picture.py`'s ATTENTION block — already the ambient, always-run home for
  - **success:** fleet-picture's ATTENTION block names a synthetically-staled loop-home branch
- **CAP-45 — CAP-4** ← spec-deferred-work-visibility CAP-11 (in-progress 2026-09-17)
  - **intent:** CAP-4..7's id/position-based coverage check has a real gap: a Tier-3 entry can
  - **success:** Confirmed live: pyforge-atlas's own Tier-3 line 7 (summary byte-identical to its
- **CAP-46 — Two fixes needed together to actually run `--fix` for real against all 8** ← spec-deferred-work-visibility CAP-12 (in-progress 2026-09-17)
  - **intent:** Two fixes needed together to actually run `--fix` for real against all 8 live
  - **success:** `for p in atlas doctor herald marshal mason scribe steward warden; do python3
- **CAP-47 — `deferred_work_promote** ← spec-deferred-work-visibility CAP-13 (in-progress 2026-09-17)
  - **intent:** `deferred_work_promote.py` (Story 8.1-8.4) was scoped to orphans only
  - **success:** Confirmed live, all 8 projects, one clean `--fix` run, zero `ABORTED` outputs, zero
- **CAP-48 — A fact useful to an operator lives once under `docs/` (or** ← spec-docs-shelf-alignment CAP-1 (ready 2026-09-17)
  - **intent:** A fact useful to an operator lives once under `docs/` (or
  - **success:** No operational procedure is copied verbatim across an
- **CAP-49 — Unique operational steps from marshal** ← spec-docs-shelf-alignment CAP-2 (ready 2026-09-17)
  - **intent:** Unique operational steps from marshal
  - **success:** One tutorial path, one air-gap how-to, one air-gap
- **CAP-50 — Sunset `docs/specs/` by frontmatter `status:`** ← spec-docs-shelf-alignment CAP-3 (ready 2026-09-17)
  - **intent:** Sunset `docs/specs/` by frontmatter `status:`.
  - **success:** No shipped/superseded Tier-1 spec remains the live
- **CAP-51 — Route intake using `docs/intake/README** ← spec-docs-shelf-alignment CAP-4 (ready 2026-09-17)
  - **intent:** Route intake using `docs/intake/README.md` and
  - **success:** Nothing a specified/realized/archived Dream already
- **CAP-52 — Inbound links to the five files now under** ← spec-docs-shelf-alignment CAP-5 (ready 2026-09-17)
  - **intent:** Inbound links to the five files now under
  - **success:** `docs/intake/README.md` and station `specs/README.md`
- **CAP-53 — `docs/dashboard/kedro-viz/` stays the Kedro-Viz upload** ← spec-docs-shelf-alignment CAP-6 (ready 2026-09-17)
  - **intent:** `docs/dashboard/kedro-viz/` stays the Kedro-Viz upload
  - **success:** MAP lists publish roots as outside the four quadrants.
- **CAP-54 — A new Doctor source (not an extension of** ← spec-docs-shelf-alignment CAP-7 (ready 2026-09-17)
  - **intent:** A new Doctor source (not an extension of
  - **success:** Re-adding a dated campaign note at `_bmad-output/`
- **CAP-55 — the catalog stays a maintained, current artifact** ← spec-fleet-hygiene-verification-exemplar-program CAP-1 (shipped 2026-09-17)
  - **intent:** An operator or agent facing a "nothing actually checks for X" moment can check one document first and get one of three answers — already catalogued and specced, catalogued but not yet built, or genuinely new — rather than rediscovering it as a fresh, isolated finding.
  - **success:** Given a newly-discovered hygiene/verification/audit gap, checking the catalog against its six categories (`hygiene-gap-catalog.md`) returns a match or confirms genuine novelty; the catalog stays cross-referenced with which items have moved from cataloged to specced to shipped.
- **CAP-56 — `EXEMPLAR-STANDARD.md`'s conformance table is refreshed and re-verified** ← spec-fleet-hygiene-verification-exemplar-program CAP-2 (shipped 2026-09-17)
  - **intent:** The fleet's designated reference for what "done and clean" means stops reporting a stale, wrong table — flagged by the source Dream as the single most concrete, ready-now item.
  - **success:** Given the DW-ledger column currently shows only `pyforge-atlas` compliant while 7 other projects now carry real, git-tracked `deferred-work-ledger.md` files (warden 43, atlas 122, marshal 109, mason 48, steward 74, herald 45, doctor 20, scribe 7, as of this session), running the refresh corrects the table to the live state, and every other column is checked for the same staleness.
- **CAP-57 — `chain-completeness`'s INV-A parses capability ids, not a bare substring match** ← spec-fleet-hygiene-verification-exemplar-program CAP-3 (shipped 2026-09-17)
  - **intent:** "This open Spec is decomposed" is judged by whether the Spec's real `CAP-N` ids trace to actual stories, not by whether the Spec's slug merely appears somewhere in PRD/epics prose.
  - **success:** Given a Spec that grew from 3 capabilities to 10 with only 3 ever decomposed into stories, the detector reports the real 7-capability gap instead of `ok` — reproduces and fixes `DW-CHAIN-COMPLETENESS-1`, logged against `spec-deferred-work-visibility` this session.
- **CAP-58 — `dream-chain`'s gap count surfaces in `fleet-picture`'s ambient ATTENTION block** ← spec-fleet-hygiene-verification-exemplar-program CAP-4 (shipped 2026-09-17)
  - **intent:** An unspecced Dream nags quietly in the report an operator already checks every landing pass, instead of waiting for a separate `dream-chain` run.
  - **success:** Given N Dreams fleet-wide with no Spec, `fleet-picture`'s ATTENTION block names the count without a separate detector invocation.
- **CAP-59 — `spec_surface_check.py --write-baseline`'s read-modify-write race is closed** ← spec-fleet-hygiene-verification-exemplar-program CAP-5 (shipped 2026-09-17)
  - **intent:** Two concurrent `--write-baseline` invocations against `scripts/.spec-surface-baseline.json` do not silently clobber each other's write.
  - **success:** Given two concurrent `--write-baseline` calls, the race is closed such that neither write is silently lost — reproduces and fixes `DW-13-5-2`.
- **CAP-60 — Every authoritative source that describes what Doctor is and** ← spec-general-docs-consistency CAP-1 (shipped 2026-09-17)
  - **intent:** Every authoritative source that describes what Doctor is and
  - **success:** `pyforge-doctor/README.md` no longer uses gate language for
- **CAP-61 — The four confirmed decay findings in the repo's two** ← spec-general-docs-consistency CAP-2 (shipped 2026-09-17)
  - **intent:** The four confirmed decay findings in the repo's two
  - **success:** `README.md`'s workflow section accurately distinguishes the
- **CAP-62 — This class of drift gets a repeatable detector instead of** ← spec-general-docs-consistency CAP-3 (shipped 2026-09-17)
  - **intent:** This class of drift gets a repeatable detector instead of
  - **success:** The detector runs, is warn-only and fail-open (matches
- **CAP-63 — Design and adopt a Diátaxis-adapted information architecture** ← spec-general-docs-consistency CAP-4 (shipped 2026-09-17)
  - **intent:** Design and adopt a Diátaxis-adapted information architecture
  - **success:** A documented map exists naming four quadrants —
- **CAP-64 — Give the general-facing docs layer a discoverable** ← spec-general-docs-consistency CAP-5 (shipped 2026-09-17)
  - **intent:** Give the general-facing docs layer a discoverable
  - **success:** A newcomer with no prior context can find one place to get a
- **CAP-65 — `README** ← spec-general-docs-consistency CAP-6 (shipped 2026-09-17)
  - **intent:** `README.md`, `CLAUDE.md`, and `AGENTS.md` point cleanly into
  - **success:** No internal link into the reorganized structure is broken.
- **CAP-66 — SATISFIED by the Dream's ledgers, not by code** ← spec-pixi-candidate-currency CAP-1 (ready 2026-09-17)
  - **intent:** Every commented-out `pixi.toml` candidate carries exactly one of five
  - **success:** Every one of the Dream's 44 candidates already carries one; a newly
- **CAP-67 — SATISFIED by the Dream's ledgers, not by code** ← spec-pixi-candidate-currency CAP-2 (ready 2026-09-17)
  - **intent:** Every active dependency below its conda-forge latest, after a
  - **success:** A shared root cause blocking several packages at once (e.g. one feedstock
- **CAP-68 — SATISFIED by the Dream's ledgers, not by code** ← spec-pixi-candidate-currency CAP-3 (ready 2026-09-17)
  - **intent:** Every active dependency not resolved from conda-forge (SelfExplainML or
  - **success:** A recipe flagged `confirmed-on-conda-forge` whose package still locks from
- **CAP-69 — the one code capability; decomposed as a single doctor story** ← spec-pixi-candidate-currency CAP-4 (ready 2026-09-17)
  - **intent:** A `pyforge-doctor`-owned advisory check reads each ledger's own recorded
  - **success:** A ledger last verified beyond the threshold produces a named finding;
- **CAP-70 — SATISFIED by the Dream's ledgers, not by code** ← spec-pixi-candidate-currency CAP-5 (ready 2026-09-17)
  - **intent:** Every active dependency lacking a corresponding `[Conda-Forge Packaging]
  - **success:** Base conda/pixi ecosystem infra and this repo's own `pyforge-*` packages
- **CAP-71 — the drift check** ← spec-sibling-dreams-drift CAP-1 (in-progress 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-72 — progress-phrase-under-terminal-status** ← spec-status-body-consistency CAP-1 (draft 2026-09-17)
  - **intent:** Report a body matching an "N of M stories/capabilities" (or "N/M") phrase with
  - **success:** Fires on the scribe Dream (`:69`) and its Spec, stays silent across the rest
- **CAP-73 — `open_questions: []` over a live memlog question** ← spec-status-body-consistency CAP-2 (draft 2026-09-17)
  - **intent:** Report a Spec declaring no open questions while its companion `.memlog.md`'s
  - **success:** Fires on `docs/governance/spec-pyforge-charter` (`SPEC.md:16` vs
- **CAP-74 — promissory language under a terminal status** ← spec-status-body-consistency CAP-3 (draft 2026-09-17)
  - **intent:** Report a body whose section headings or lead sentences are still
  - **success:** Fires on the herald Dream+Spec pair *and* stays quiet elsewhere. This is the
- **CAP-75 — a status comment that contradicts the ledger it cites** ← spec-status-body-consistency CAP-4 (draft 2026-09-17)
  - **intent:** Report a frontmatter `status:` comment naming an epic/story whose live ledger
  - **success:** Fires on the `status: realized   # … → Epic 14 backlog` shape found live on
- **CAP-76 — it renders where the operator already looks** ← spec-status-body-consistency CAP-5 (draft 2026-09-17)
  - **intent:** A `report-schema.json` entry plus detectors membership, so the finding appears
  - **success:** The finding shows up in the doctor report and the `fleet-picture` ATTENTION
- **CAP-77 — the map of what no agent can verify without a live proof** ← spec-pyforge-doctor CAP-77 (ready 2026-09-18)
  - **intent:** A fleet-wide, doctor-owned inventory of surfaces a dev/review pass structurally cannot verify from inside the repo alone — station, surface, what a static pass cannot see, how to prove it live, roughly how expensive — catalogued in `live-proof-surfaces.md`, cited by name from a Finding when a touched surface matches.
  - **success:** A story/PR touching a catalogued surface gets an advisory Doctor finding naming it, never gating; the catalog is read from real, current mechanisms only (existing live-test scripts, opt-in env flags, service-up tasks), never invented. Motivating incident (2026-09-17/18): herald's mcp SDK transport broke across two 2.x changes — `streamablehttp_client` renamed to `streamable_http_client` with a different call signature, `CallToolResult.isError` renamed to `.is_error` — caught by neither review nor the test suite nor a dev pass's own self-report; only a real live push-then-read-back against Claude Design surfaced it.
- **CAP-78 — a PR is judged at its merge-base, and a merge subject is attributed to the station it names** ← spec-pyforge-doctor CAP-78 (ready 2026-09-18)
  - **intent:** Doctor's merge-history sources never report a regression that is an artifact of `main` having moved first: `ledger-regression` on a PR compares the tracked ledgers at `merge-base(base, head)` against `head` (a push to `main` keeps its first-parent fallback), and `ledger-direction` / `story-status` attribute a templated merge subject to a story only when the subject names that station's slug, reading each station's `merge_subject_template` from its own `marshal-policy.toml`.
  - **success:** Replaying herald PR #1465's shape (branch at `backlog`, `origin/main` already promoted to `done` after an unattended merge) reports `ok` instead of `done-key-regressed`, while a branch that genuinely moves a `done` key still fails; a fixture where `main` carries a sibling station's `Merge 13-5 into main` no longer reports `pyforge-atlas/13-5 landed-but-unpromoted`, while a station's own `Merge pyforge-atlas/13-5 into main` still counts *(corrected 2026-09-18: the three live atlas rows were a different cause — pre-rekey keys, CAP-79 — and are not this capability's evidence)*; the legacy un-scoped default is honoured only for a station whose policy still declares it, so no historical `done` row loses its evidence (fixture over the eight tracked ledgers); the `evidence` payload names the base actually used (`merge_base`, `base_requested`) so a `--json` consumer can tell the substitution happened.
- **CAP-79 — `ledger-direction` reads the station's rekey map** ← spec-pyforge-doctor CAP-79 (ready 2026-09-18)
  - **intent:** A merge subject that names a story by its *pre-rekey* key is attributed to the story's current key before `ledger-direction` judges it, exactly as `gather()` already does (Story 25.3), so a renumbered station never reads its own landed stories as `landed-but-unpromoted`.
  - **success:** `gather_direction` applies every `_bmad-output/projects/<slug>/planning-artifacts/rekey-*.md` map (via `pyforge.doctor.rekey.parse_rekey`, the same reader `gather()` uses) to the keys parsed from merge history before comparing against the tracked ledger; on today's `main` the three atlas rows (13-5 → 12-5, 14-4 → 13-4, 15-3 → 14-3) report nothing, a fixture with a rekey map and a merge naming the old key reports nothing, the same fixture with the map removed reports `landed-but-unpromoted` (mutation), and an unreadable map is a WARN naming the file, never a silent pass.
- **CAP-80 — a station's legacy-template history stays attributed after its template changes** ← spec-pyforge-doctor CAP-80 (ready 2026-09-18)
  - **intent:** When a station's `merge_subject_template` moves from the repo-default `Merge {key} into main` to a station-scoped form, the merges it landed under the old form are still its own: Doctor's merge-history sources attribute a bare legacy-form merge to a station by **the station paths its diff touches** (`_bmad-output/projects/<slug>/**` or `src/shared/packages/<slug>/**` against the merge's first parent — git as the sole authority for merged facts), never by which ledgers happen to know the number, so history is never orphaned and a sibling's bare subject still never attributes. *(Amended 2026-09-18: the first Approach — "the station's ledger knows the key", Story 27.3 — was found by its own review to reopen the cross-station collision whenever two stations know the same key, the common case; ruled and re-minted as Story 27.4.)*
  - **success:** On today's `main`, marshal `34-3` (landed 2026-09-12 as `Merge 34-3 into main`, whose first-parent diff touches only `pyforge-marshal` paths, harness run `deferred`) reads as merged again and `story-status` reports no finding for it; a fixture where a bare `Merge 34-3 into main` diff touches only *another* station's paths attributes nothing to the querying station even when its ledger knows 34-3; a merge whose diff touches no station path attributes nothing; a fixture with the scoped form still attributes; CAP-78's PR #1465 replay and CAP-79's rekey replay stay green.
- **CAP-81 — a frontmatter reader that stops at the fence, not at the first dashes** ← spec-pyforge-doctor CAP-81 (ready 2026-09-19)
  - **intent:** `sources/chain.py::_frontmatter_parse` — and every Doctor source that reads frontmatter through it (spec status, deferrals, surface, ownership) — bounds the YAML block by line-anchored `---` fences (opening fence on the first line, optionally after a `<!-- … -->` banner as marshal's post-CAP-248 readers allow; closing fence a line that is exactly `---`), so a quoted `---` inside a scalar or a `---` horizontal rule in prose never truncates or invents frontmatter, and a block that cannot be bounded is refused rather than degraded.
  - **success:** Marshal 50.5's tracked spec is the regression fixture: both deferrals parse, the first keeps its `location:` (fingerprint `fdd6bce25c09` for `3bc3d91bdf95`) and the second — severity high, `5434eca8c9e5` — is visible to `deferred-work` and to `deferred_work_intake.py` (which today reports "all 118 already in tracked ledger"); a prose file with a `---` rule and no leading fence is `({}, False)`, not unparseable; an unclosed fence is `({}, True)`; a banner-topped tracked spec parses its frontmatter; every existing caller's fixture set yields byte-identical verdicts; mutation-tested — restoring `split("---", 2)` re-truncates the fixture. *(Amended 2026-09-19: the realization sanctions exactly two verdict changes on existing shapes — the displaced-block Dream fixture (a complete `---`/YAML/`---` block below prose) is absent metadata, `dream-without-spec` with owner `(none)` rather than `unparseable-frontmatter`, per the Always clause's "no leading fence is `({}, False)`"; and the 34 archived Dreams with a glued `---title:` opener are refused as `unparseable-frontmatter` (attempted but unbounded) where the old reader parsed them leniently — unit fixtures are otherwise unchanged and byte-identical.)*
- **CAP-82 — the sibling drift check honours a per-Dream acknowledgement and follows the sibling's rename** (minted 2026-09-19 (evening); extends CAP-71)
  - **intent:** A local Dream may carry `sibling-acknowledged: <sibling content_hash>`; when the sibling's current hash equals it, CAP-71 reports nothing for that Dream, and any other hash re-fires with both hashes named, so a genuine later change on the sibling still surfaces. A locally `archived` Dream with no acknowledgement is reported with its archived status in the message. The sibling coordinates come from one place and read `openteams-ai/mgmt-wf-python-modernization` (the 301 target of the old `OpenTeams-WFT-CDO` path).
  - **success:** The six `DW-OPS-2026-09-19-6` Dreams, once acknowledged at their current sibling hashes, produce zero findings on a live run; changing one acknowledged hash in a fixture re-fires exactly that Dream; the unreachable and unauthenticated paths are unchanged (warn, fail-open); `tests/unit/test_sources_sibling_dreams.py` covers ack-match, ack-mismatch, archived-without-ack and the renamed owner.
- **CAP-83 — `docs/MAP.md` is enforced within its own scope** (minted 2026-09-19 (night); extends CAP-63/64; research: `planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md`)
  - **intent:** A Doctor source (`docs-map-hygiene`) reads `docs/MAP.md` and the four Diátaxis quadrant directories — exactly the scope MAP.md § *Outside this map* leaves inside — and reports a MAP link to a page that does not exist (fail) and a quadrant page MAP does not list (warn; a section index `README.md` directly inside a quadrant is exempt). Nothing outside the quadrants is scanned.
  - **success:** On `main` the source reports OK; an unmapped how-to reds a warn naming it; a removed mapped page reds a fail naming the dead link; a unit test covers each branch; the source runs in `detectors-ci`; CAP-62's warn-first posture holds for the unmapped class until Story 30.2 promotes it.
- **CAP-84 — documentation currency: every mapped page is generated, authored-and-verified, or a pointer, and the change that invalidates a page reds the PR that made it** (minted 2026-09-19 (night); Stories 30.2–30.3)
  - **intent:** `docs/map.yaml` (machine twin of `MAP.md`; `MAP.md` rendered from it) records for every page inside the map's scope its quadrant, owner station, `kind ∈ {generated, authored, pointer}`, `sources` and, for generated pages, a `derived_at` + `tree` stamp. Generated pages are never hand-edited — a `docs-<name>` pixi task regenerates each (pixi-task reference from `pixi.toml`, station CLI cheat sheet from each CLI's `--help`, detector table from `scripts/detectors.py` + `doctor.sources` registrations, skills catalog from `SKILL.md` frontmatter, environments table from `[environments]`). Authored pages carry `sources:` and `verified:` and are refreshed by the `bmad-os-docs-audit` → `bmad-os-diataxis` pass, triggered by a finding. One source `docs-currency` reds a stale generated page, a stale authored page (a named source moved past `verified:`, or a backticked path / pixi task / CLI grammar in it no longer resolves) and a stray file inside a managed skill dir.
  - **success:** `map.yaml` validates and `MAP.md` equals its render; each generator is idempotent on an unchanged tree; on `main` `docs-currency` reports OK; editing `pixi.toml`'s tasks without regenerating the task reference reds `detectors-ci`; the checks start warn and are promoted to fail individually once green; `llms-full-check` keeps its own lane.

## Constraints

- **CAP-81 keeps the refusal semantics of Story 17-1 / FR-144** *(2026-09-19)*: an unbounded or non-mapping block is still `({}, True)`, never a silent `{}` — the fix narrows what counts as a fence; it does not widen what counts as parseable.
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
- **CAP-77's catalog names only what already exists:** a live-proof mechanism cited in `live-proof-surfaces.md` must be a real, existing script/flag/task, never invented; a surface with no existing mechanism is recorded as a genuine gap. Extends AD-2's operability-not-policy posture — the finding is always advisory, never a second PR gate.
- **Docs detectors (CAP-83/84):** CAP-62's posture — warn first, fail-open when a source cannot be read; promotion to fail is per check, recorded on the memlog. Generated pages are derived, never hand-edited. No page under `docs/` is copied into a per-tool instruction file (scribe CAP-27). Skill directories hold only the Agent Skills layout.

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
