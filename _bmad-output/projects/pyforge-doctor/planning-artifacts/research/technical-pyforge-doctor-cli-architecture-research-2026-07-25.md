---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/ecosystem-crew.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py
  - .claude/skills/conda-forge-expert/reference/atlas-phases-overview.md
research_type: 'technical'
research_topic: 'CLI architecture for a diagnostics tool that consolidates existing subprocess-based scanners and read-side data sources (pyforge-doctor)'
research_goals: 'Ground the pyforge-doctor architecture stage in established technical patterns for (a) facading multiple subprocess/CLI tools behind one interface, (b) machine-readable diagnostics output interchange, and (c) ordering a remediation worklist — so the architecture reuses proven shapes rather than inventing them, and so it is explicit about what to reuse verbatim from pyforge-warden and cf_atlas vs. what is net-new.'
user_name: Rxm7706
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'LIGHT scope — internal tool, in-repo pixi workspace member. Focuses on architecture-relevant patterns (facade/wrapper design, output-schema interchange, remediation ordering algorithms), not a full technology-stack evaluation, since the stack (Python, pixi workspace member, warden-adjacent) is already fixed by repo convention.'
---

# Research Report: Technical Research — Doctor CLI Architecture

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Technical (light — internal tool, stack pre-fixed)

---

## Research Overview

Doctor's architecture question is narrower than a typical greenfield technical-research
scope: the stack is already fixed by repo convention (Python, `pyforge.*` namespace
package, in-repo pixi build-workspace member alongside `pyforge-warden` — see
`pixi.toml` `[feature.pyforge-warden.dependencies]` for the exact pattern Doctor should
mirror). What's open is the **internal architecture of a tool whose entire job is
wrapping other tools' output** — three verbs (`check`/`monitor`/`diagnose`), each
consolidating a different set of existing subprocess/data sources. This report surveys
three technical patterns that map directly onto that job, and cross-references them
against **pyforge-warden's already-implemented, in-repo precedent**, since warden already
solved an adjacent problem (wrapping `deptry`/`osv-scanner` subprocesses behind one exit
code and one report schema) and Doctor should reuse its seams rather than re-derive them.

## 1. Facading multiple subprocess/CLI tools behind one interface

The **Facade pattern** is the correct structural label for what Doctor does across all
three verbs: `check` coordinates warden's engine self-checks, `monitor` coordinates
cf_atlas's health/watch CLIs, `diagnose` coordinates both plus a ranking step. Research
into the pattern's own literature draws a distinction directly relevant to Doctor's
scope: a **true facade coordinates independently-usable subsystems with their own
lifecycles**, rather than reimplementing them — "the facade should coordinate, not
reimplement, the logic of each wrapped tool," with an explicit escape hatch to call the
underlying tool directly for advanced/tool-specific needs. This is precisely the
Dream's "consolidation, not invention" framing, now with an architectural label attached.

Concrete design takeaways, cross-checked against warden's existing implementation:

- **Normalize exit codes into one scheme, don't leak raw subprocess codes.** This is
  already warden's law: `verdict.exit_code_for` is described in `cli.py` as the "sole-owned
  knob" for exit codes — *nothing* inside a scan is allowed to `sys.exit()` directly, every
  path (including SIGINT → `EXIT_SIGINT`) funnels through it. Warden's `--doctor` flag
  further demonstrates a **second, narrower exit-code contract nested inside the same
  scheme**: `_run_doctor` returns only `0` (every check ok) or `exit_code_for(Status.ERROR)`
  — explicitly **never** `1`, because (warden's own comment) *"doctor reports operability,
  not policy."* This is a load-bearing distinction Doctor's architecture must adopt
  wholesale: `doctor check`'s exit code answers "is the machine sound," never "did a policy
  gate fail" — those are different questions with different consumers (a CI preflight step
  vs. a compliance gate), and conflating them was explicitly designed against in warden.
- **One subprocess-normalization seam, not N ad hoc `subprocess.run` call sites.** Warden's
  `engines.py` documents itself as "the package's ONLY subprocess-capable module — the sole
  subprocess site," with every engine call routed through one `_engine_env()` helper (argv
  as a list, forced tempfile output outside the scanned tree, `NO_COLOR=1`, `stdin=DEVNULL`,
  bounded timeout, typed `ErrorRecord` on failure). Doctor's `check --engines` step
  literally **calls into this existing seam** (via warden as a library dependency, not a
  reimplementation) rather than shelling out to `deptry`/`osv-scanner` a second time — this
  is the single clearest "reuse, don't invent" opportunity the codebase already offers.
- **`--version` preflight as a distinct, narrower call site.** Warden's `_check_engine_version`
  deliberately bypasses the main `_engine_env` seam (no `-o`/tempfile equivalent for
  `--version`) but still returns the same typed `ErrorRecord`/`ErrorKind` shape and the same
  timeout/no-shell discipline. This is the exact shape of a `doctor check --engines` probe:
  cheap, read-only, typed-failure, and explicitly justified as a narrower sibling seam
  rather than a bypass of the safety discipline.
- **Typed failure taxonomy over string matching.** Warden's `ErrorKind`/`ErrorRecord` pair
  (referenced throughout `engines.py`) is the generic version of what SARIF (below) and
  Dependabot's auto-triage rules both converge on independently: a structured, enumerable
  category for *why* something failed or what was found, not a free-text message an
  operator has to interpret. Doctor's `diagnose` output should adopt or directly reuse this
  taxonomy for consistency across the two tools' outputs — an operator seeing a Doctor
  finding and a Warden finding side by side should recognize the same vocabulary.

## 2. Machine-readable diagnostics output — SARIF as the interchange precedent

SARIF (Static Analysis Results Interchange Format, OASIS standard, currently v2.1.0) is
the industry-standard answer to exactly Doctor's aggregation problem stated generically:
*"developers use a variety of analysis tools... to form an overall picture... aggregation
is more difficult if each tool produces output in a different format."* Its relevant
structural ideas:

- **Multiple "runs" of different tools in one log**, each run tagged with which tool
  produced it — directly analogous to `doctor check` needing to report "deptry: ok,
  osv-scanner: missing, feedstock-health: stale" as one document with per-source
  provenance, not a flattened list that loses which instrument found what.
- **JSON-based, schema-validated, widely tool-supported** (GitHub code-scanning ingests
  SARIF natively; VS Code/Visual Studio have native viewers) — this is the same design
  choice warden already made independently (`ComplianceReport` is "one schema-validated"
  document per the repo's own PROJECTS.md description). Doctor does not need to adopt
  literal SARIF (it's scoped to static-analysis findings and would be a heavyweight,
  partially-mismatched fit for fleet-health/staleness signals), but the underlying
  discipline — one schema-validated envelope, multi-source runs tagged by origin,
  machine-parseable before human-readable — is directly reusable and matches the existing
  in-repo convention (warden's `ComplianceReport`, cf_atlas's `--json` output modes already
  used by `behind-upstream --json`, `cve-watcher --json` etc. per the atlas CLI reference).
- **A pragmatic middle path**: since Doctor's `check`/`monitor` sources already emit
  `--json` in their native shapes (warden's `ComplianceReport`, cf_atlas CLIs' JSON modes),
  the architecture-stage decision is not "adopt SARIF" but "define one thin Doctor-native
  envelope (source, check-name, status ∈ {ok,warn,fail}, message, evidence) that each
  wrapped source's JSON output is normalized into" — the SARIF precedent validates that
  this multi-run-tagged-by-source shape is the right generic answer, without requiring
  Doctor to take on SARIF's full spec surface.

## 3. Ordering the remediation worklist (`diagnose --prescribe`)

This is the most algorithmically substantive piece of Doctor's contract, and the
research area with the most directly transferable prior art:

- **Topological sort is the base primitive whenever prescriptions have a dependency
  order** (e.g., "upgrade A before B because B pins A"). Both DFS-based and Kahn's-algorithm
  (BFS, in-degree-zero queue) implementations are standard, well-understood, and trivial to
  implement in Python from the standard library — no new dependency needed. Doctor's
  architecture should reserve this only for cases with an actual edge (a real pin/version
  constraint dependency between two findings), not apply it universally — most Doctor
  findings (a stale feedstock, a missing engine, a CVE) are independent and don't need
  graph ordering, just *ranking*.
- **Ranking (not ordering) is the more common real need**, and the surveyed tools converge
  on a small, reusable set of ranking axes:
  - **Severity** (CVSS-equivalent) — already present via warden's KEV/CVSS gates and
    atlas's `vuln_max_epss_score`/severity columns.
  - **Exploitability** (EPSS) and **confirmed active exploitation** (KEV) — GitLab and
    GitHub's frameworks both treat these as the second/third pillar alongside severity;
    already wired into both warden (`--fail-on-kev`, `--min-epss`) and cf_atlas
    (`staleness-report --by-epss`, KEV overlay per the atlas reference doc).
  - **Magnitude of change / blast radius** — GitLab's own remediation-ordering proposal
    explicitly weighs "smaller change first" (patch < minor < major) as a tiebreaker
    alongside severity, on the reasoning that a closer upgrade target is less likely to
    regress; Endor Labs and OSV-Scanner's guided-remediation both add "how many
    transitive vulnerabilities does this one upgrade fix" as a multiplier. Doctor doesn't
    need a resolver of this depth for v1 — the transferable idea is a per-finding
    "distance to fix" and "blast radius" tiebreaker field, populated from atlas's existing
    `behind-upstream` lag classification (major/minor/patch) rather than a new dependency
    resolver.
  - **Incremental major-version sequencing** — Renovate's documented best practice
    (upgrade 1→2→3→4, never 1→4 directly, because changelogs must be read at each major
    boundary) is a useful *presentation* convention for `--prescribe`'s output even where
    no real dependency graph exists: an ordered worklist for a badly-lagging feedstock
    should present intermediate hops, not just "target: latest."
- **Partition before rank.** Every surveyed remediation tool separates "actionable now"
  from "blocked" (no fix available yet) before ranking within the actionable set —
  GitHub's "snooze until patch" auto-triage state and pip-audit/Safety's
  filter-by-fixability step are two independent implementations of the same idea. This maps
  directly onto Doctor's existing `indeterminate` vocabulary (already established in the
  warden spec for feed-absence-under-policy) — `diagnose --prescribe`'s output should be
  three buckets (actionable-ranked / blocked-tracked / accepted-risk), not one flat sorted
  list, so a blocked finding is never silently dropped nor mixed in as if it were
  actionable today.

## Cross-Domain Synthesis: Direct Reuse vs. Net-New Build

| Component | Existing precedent in-repo | Architecture-stage decision this implies |
|---|---|---|
| Exit-code contract for `check` | Warden's `--doctor` flag: `{0, exit_code_for(ERROR)}`, never the policy-gate `1` | Doctor's `check`/`monitor` verbs should adopt the SAME "operability, not policy" exit-code split; only a future policy-gate use of Doctor (if any) would use the fuller warden-style enum. |
| Subprocess execution | Warden's `_engine_env()` seam (`engines.py`) — the ONLY subprocess site in that package | Doctor's `check --engines` should call warden's self-check as a library, not reimplement subprocess handling for deptry/osv-scanner a second time. |
| Output schema | Warden's `ComplianceReport` (schema-validated, one document); atlas CLIs' existing `--json` modes | Define one thin Doctor-native envelope normalizing multi-source JSON into (source, check, status, message, evidence) tuples — SARIF-inspired discipline, not SARIF itself. |
| Fleet data source | cf_atlas `cf_atlas.db` + its `feedstock-health`/`staleness-report`/`behind-upstream`/`cve-watcher`/`release-cadence` CLIs and MCP tools | `monitor --fleet` queries these directly (CLI subprocess or, preferably, the existing MCP tool surface / direct atlas query) — no new data pipeline. |
| Prescription ranking | Warden's KEV+EPSS gates; atlas's `--by-epss`/`--by-risk`/CWE overlays; `behind-upstream`'s major/minor/patch lag classification | `diagnose --prescribe` is a ranking+partition layer over these existing signals (severity × exploitability × blast-radius, partitioned actionable/blocked/accepted), not a new scanner. |
| Credential/privilege hygiene (candidate check) | Known `JFROG_API_KEY` unconditional-injection finding in `_http.py` | A concrete worked example for a NEW check category `check --env` should cover (env/credential-scope hygiene) that neither warden nor atlas currently owns — likely Doctor's first genuinely net-new check, not a wrap of an existing one. |

## Assumptions

- Doctor is a Python package in the `pyforge.*` namespace, built as an in-repo pixi
  build-workspace member the same way `pyforge-warden` is (`pixi.toml`
  `[feature.pyforge-warden.dependencies]` block is the template) — this was treated as
  already decided by repo convention (per `_bmad-output/PROJECTS.md`'s pyforge-doctor
  entry: "dist `pyforge-doctor` / module `pyforge.doctor` / CLI `doctor`"), not re-litigated
  here.
- Doctor depends on `pyforge-warden` as a library for `check --engines` (reusing its
  `--doctor` self-check machinery) rather than vendoring or reimplementing engine-probe
  logic — flagged as the intended default; architecture stage should confirm the dependency
  is legitimate for a pixi workspace member (no circular-dependency risk, since warden does
  not depend on Doctor).
- cf_atlas access from `monitor --fleet` is assumed to go through the existing MCP tool
  surface (`feedstock_health`, `staleness_report`, `behind_upstream`, `cve_watcher`,
  `release_cadence`, `adoption_stage`) or their CLI equivalents, not a new direct-DB
  connection — consistent with "consolidation, not invention."
- SARIF itself is NOT recommended for adoption (scope mismatch — it's static-analysis
  specific and heavyweight for fleet-health signals); only its aggregation *discipline*
  (multi-run, tool-tagged, schema-validated) is recommended for reuse.

## Open Questions

- Does `doctor check --engines` invoke warden's `--doctor` flag as a subprocess (simplest,
  matches existing CLI boundary) or import `pyforge.warden.engines.run_doctor_checks`
  directly as a library call (tighter coupling, avoids a second process spawn)? Deferred to
  architecture stage — leans library-import given both packages already share a pixi
  workspace and Python namespace family, but needs an explicit ADR given warden's own
  "sole subprocess site" ownership rule would need a documented exception or a clean
  library-level API boundary.
- What is Doctor's OWN top-level exit-code contract when it aggregates multiple
  sub-verdicts (e.g., `monitor --fleet` where atlas signals are healthy but a warden
  engine is missing)? Needs the same "sole-owned knob" discipline warden uses — deferred to
  architecture.
- Is there an existing typed error/finding taxonomy Doctor should import directly from
  warden's `ErrorKind`/`models.py`, or does Doctor need its own (structurally similar but
  semantically distinct, since Doctor's findings span "engine missing" / "feedstock stale" /
  "credential hygiene," not just scan-engine failures)? Deferred to architecture.

## Sources

- [The complete guide to SARIF: Standardizing static analysis results — Sonar](https://www.sonarsource.com/resources/library/sarif/)
- [Static Analysis Results Interchange Format (SARIF) Version 2.1.0 — OASIS](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [SARIF Home](https://sarifweb.azurewebsites.net/)
- [Integrating Static Code Analysis Toolchains (arXiv)](https://arxiv.org/pdf/2403.05986)
- [The Facade Design Pattern: Simplifying Complex Subsystems Through Unified Interfaces — Medium](https://tobiaslang.medium.com/the-facade-design-pattern-simplifying-complex-subsystems-through-unified-interfaces-a569d0589ac3)
- [Facade | LLD (algomaster.io)](https://algomaster.io/learn/lld/facade)
- [Using the Facade Pattern to Wrap Third-Party Integrations — Siv Scripts](https://alysivji.com/clean-architecture-with-the-facade-pattern.html)
- [The subprocess Module: Wrapping Programs With Python — Real Python](https://realpython.com/python-subprocess/)
- [GitHub - Tyrrrz/CliWrap](https://github.com/Tyrrrz/CliWrap)
- [Upgrade impact analysis — Endor Labs Documentation](https://docs.endorlabs.com/risk-remediation/upgrade-impact-analysis)
- [Upgrade best practices — Renovate Docs](https://docs.renovatebot.com/upgrade-best-practices/)
- [Guided Remediation — OSV-Scanner](https://google.github.io/osv-scanner/experimental/guided-remediation/)
- [Remediation Guidance — FOSSA Docs](https://docs.fossa.com/docs/reports/remediation-guidance)
- [Topological Sorting — Dependency Resolution — Medium](https://arvita-writes.medium.com/topological-sorting-dependency-resolution-40a605e6a605)
- [Optimize order of auto-remediations for Dependency Scanning — GitLab Issue #328794](https://gitlab.com/gitlab-org/gitlab/-/issues/328794)

## Local (in-repo) sources consulted

- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` — subprocess seam,
  `--doctor` self-check (`DoctorCheck`/`run_doctor_checks`), typed `ErrorKind`/`ErrorRecord`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — `verdict.exit_code_for`
  sole-ownership rule, `--doctor` flag's `{0, ERROR}` exit-code contract.
- `pixi.toml` `[feature.pyforge-warden.*]` — in-repo pixi build-workspace member pattern to
  mirror for `pyforge-doctor`.
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — cf_atlas CLI/MCP
  surface (`feedstock-health`, `staleness-report`, `behind-upstream`, `cve-watcher`,
  `release-cadence`, `adoption-stage`) and their existing `--json`/`--by-epss`/`--by-risk`
  modes.
- `.claude/skills/conda-forge-expert/scripts/_http.py` — the JFROG_API_KEY unconditional-
  injection finding, cited in the Dream as a candidate Doctor check.
