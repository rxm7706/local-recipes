---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
classification:
  projectType: cli_tool
  projectTypeNote: "Non-interactive CI/CD policy/quality-gate CLI; primary consumer is a pipeline, not a human terminal. report-schema.json is the data contract (an output_formats concern). developer_tool label dropped (no public SDK/IDE surface). Interactive/shell-completion UX deprioritized."
  domain: devsecops-supply-chain-security
  domainNote: "First-class DevSecOps / software supply-chain security (not 'general'). Special sections: OSV vuln-data source/currency, FR7 false-positive/actionability policy, SBOM-adjacency."
  complexity: medium
  complexityNote: "Medium engineering, HIGH stakes (missed CVE / fleet-wide build-block). Complexity hotspots: OD2 (osv-scanner input / version resolution) and OD3 (stdlib manifest parsing across 5 formats). Implies strong test/validation rigor."
  projectContext: greenfield
vision:
  irreduciblePromise: "One exit code you can trust, with honest coverage."
  problem: "Dependency hygiene and dependency security are two disjointed tools/pipelines; conda/pixi projects are second-class because neither deptry nor osv-scanner natively parses pixi.toml / environment.yml / v1 recipe.yaml."
  coreInsight: "Both jobs start from the same manifest parse; build ONE conda/pixi-native manifest front-door feeding two INDEPENDENT extraction paths (deptry: source-tree AST + import->distribution mapping; osv-scanner: versioned lockfiles), emit ONE schema-validated report behind ONE exit code."
  scope: "Python libraries across PyPI AND conda-forge (ecosystem-agnostic). PyPI path = delegate to engines' native parsers (deptry: pyproject PEP621/Poetry/PDM/uv/setuptools + requirements.txt; osv: requirements.txt/poetry.lock/pdm.lock/uv.lock/Pipfile.lock/pylock.toml). Conda/pixi path (the wedge) = E1 bridge for environment.yml/meta.yaml/recipe.yaml/pixi.toml (neither engine parses these). Grounded 2026-07-11, time-bound."
  hero: "extending deptry + osv-scanner to the conda/pixi formats neither parses natively (the differentiated wedge); one-gate unification across both ecosystems is the broad value"
  beachhead: "sharpest UNSERVED gap = serves ANY Python project (scripts/apps/components/libraries), pip- or conda-sourced. platform-eng + DevSecOps = distribution channels (fleet deployers)"
  valueProp: "One lightweight, conda/pixi-native CI gate that unifies dependency-hygiene and known-vulnerability scanning into a single honest, schema-validated pass."
prioritizedRefinements:
  v1_must:
    - "arch: shared manifest front-door + 2 independent extraction paths (deptry AST+import->dist; osv versioned lockfiles)"
    - "NFR4: manifest engine is load-bearing + must-be-observable; its coverage is the correctness root"
    - "FR8 schema: report status = error | findings | clean (crash != clean != findings)"
    - "FR9 schema/policy: per-manifest coverage/parse-confidence; fail-loud — 'incomplete' never renders as 'clean'"
    - "FR5 (severity-tiered gate): exit 0/1/2; --fail-on=<severity> or max_critical/max_high/KEV; default block on critical CVE (KEV tier deferred post-v1 — see § Domain-Specific Requirements), warn on high/med/low + all hygiene. Retires coarse --no-fail-on-*. Gate decides on report CONTENT + severity, never subprocess returncode"
    - "FR10 (typed errors, exit 2): error_kind = unparsable-manifest (owner=developer) | engine-unavailable (owner=platform) | engine-crash | internal-error (owner=CLI maintainers); not-applicable = benign exit 0 (non-Python repo, not an error). Non-relaxable except via audited bypass. Explicit missing-binary + unparsable-manifest tests"
    - "FR11 (E1): recipe.yaml two-pass eval (${{}} + compiler()/pin_subpackage() -> name-only+marked); environment.yml pip: = core case (3rd naming domain)"
    - "FR1/E1: v0 meta.yaml is a 6th supported format (MORE common than recipe.yaml here: ~1,040 vs ~910 as of 2026-07-11) — {% set %} + {{ x|filter }} + {{ compiler() }} + '# [sel]' line-selectors; extends OD3, degrade to name-only+marked. Scope = Python across PyPI AND conda-forge (not feedstocks-only)."
    - "NFR5: bounded parse-error budget"
    - "test-strategy: corpus-conformance over recipes/*/{recipe.yaml,meta.yaml} (~1,950 real files as of 2026-07-11, globbed at runtime) — 0 uncaught exceptions, bounded unparseable rate surfaced per-manifest, twice-run byte-identical/NFR3"
    - "FR8 (v1, owner-elevated 2026-07-11): emit a CycloneDX SBOM of the resolved inventory — correct purls (pkg:pypi vs pkg:conda?channel=), per-manifest coverage marking, stdlib-only, committed CycloneDX schema; aligns cyclonedx-universe-inventory + kedro FR-17. Reverses the old 'writing SBOMs' non-goal."
  v1_should:
    - "positioning: hero=conda/pixi-native resolution; beachhead=conda-feedstock maintainers; platform/DevSecOps=distribution wins"
    - "pre-work: dated competitive spike (osv-scanner supported lockfiles + Trivy catalogue) -> 'Competitive Moat — Time-Bound' subsection"
    - "FR-schema: include a schema_version field now (cheap insurance)"
    - "FR/arch-Q: v1 must NOT silently merge/dup cross-ecosystem names — mark uncertainty; full conda<->PyPI reconciliation = architecture-phase open question"
    - "NFR-note: 'lightweight = runtime-footprint, not total-cost' (fixture-maintenance tax on conda-build selectors + Jinja grammars)"
    - "FR9 (v1, owner-elevated 2026-07-11): auditable EXPIRING bypass (waivers-as-code) — --bypass --reason emits a committed .python-deptry-osv-scanner-waivers.yaml stanza (accepted_at/expires_at; default 14d, config + per-repo override) the tool READS (never writes repo; NFR3 intact); status: bypassed + review_required routed to the security queue at the fleet/atlas layer. Also respect [tool.deptry] ignores. REVERSES the earlier 'waiver out of v1' call."
  defer_post_v1:
    - "formal report-schema deprecation/migration process (ship the version field only)"
    - "perfect cross-ecosystem (conda<->PyPI) name reconciliation"
    - "org-wide bypass-review routing/queue (per-repo tool emits review_required; the atlas FR-16/FR-18 promotion does the org routing)"
inputDocuments:
  - docs/specs/python-deptry-osv-scanner.md
  - docs/specs/cfe-atlas-datapipeline-kedro-migration.md
workflowType: 'prd'
releaseMode: single-release
---

# Product Requirements Document - python-deptry-osv-scanner

**Author:** rxm7706
**Date:** 2026-07-11

> **⚠️ Post-Architecture Reconciliation (2026-07-11) — authoritative.** The architecture phase (`planning-artifacts/architecture.md`, status: complete) revised **7 decisions** after adversarial roundtable review (the sharpest catch: the pre-architecture design shipped a *green-by-default on a bare `recipe.yaml`* — the beachhead's most common artifact). Where inline PRD text below predates these, **the reconciliation wins**; `architecture.md` § Core Architectural Decisions carries the full detail.
> 1. **New verdict state `indeterminate`** in the J9 lattice **above `warn`** (`error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`). Gap-C withheld/skipped/unresolved outcomes route **here, never to `not-applicable`** (so a clean sibling axis can't mask "we couldn't scan what existed"); `indeterminate` → **non-zero exit, never a silent 0**. (Revises the status vocabulary + FR20 + the exit projection.)
> 2. **Name-level CVE tier** — for a mapped-but-unversioned dep, flag "carries known critical CVEs across any version" (a risk surface + lock-nudge, not a dead coverage number). **Guardrail:** coverage improves **only** by resolving (read the lock) or name-level flagging — **never** by assuming a version. (Extends FR13.)
> 3. **DEP001 (missing dependency) blocks by default**, gated on conda↔pypi name-mapping confidence (high-confidence → block, ambiguous → `warn`); DEP002/3/4 → `warn`. Hygiene is a **separate axis** from the CVSS gate; the hygiene→status + CVSS-threshold tables live in the FR30 `ConfigLoader`. (Refines FR18/FR8, Gap A.)
> 4. **Bundled static conda→pypi map** — a v1 asset (the offline CLI can't call the MCP `get_conda_name` mapper), generated from the atlas `export-purls` TSVs. It powers the Gap-C ecosystem-identity predicate (`pypi_identity`) that prevents the silent `pytorch`→`torch` false-green.
> 5. **Coverage is a function of artifact resolvability** — kill the symmetric "hygiene AND vuln for conda" claim: **pixi.lock = the vuln hero path**; a **bare `recipe.yaml` = hygiene + a vuln risk-surface + a lock-nudge**. The coverage block states **`direct-only` vs `locked-closure`** (a loose manifest lists direct deps only; transitive vulns are invisible without a lockfile).
> 6. **Library policy** — NFR-P1 "stdlib-only" → **"lean, targeted conda-provisioned deps"** (PyYAML, packaging, cyclonedx-python-lib, jsonschema); NFR-S1 reframed to **"no *execution* of untrusted input"** (AST-denylist: no `eval`/`exec`/`subprocess`-in-extractor/**Jinja render**, `yaml.safe_load` only). The scaffold's `dependencies = []` becomes a targeted list. Every "stdlib-only extraction" phrasing below is superseded by "stdlib-lean + targeted safe libs."
> 7. **E1 supported-construct matrix** is now an **owned deliverable** (grounded in the conda-forge-expert recipe-format refs): `compiler()`/`stdlib()` → build-tool-exclude; `pin_subpackage()` → internal-subpackage-exclude; `# [sel]`/`if-then-else` → union both branches + mark; expression logic → degrade to name-only+marked. *(D1/FR9 does **not** change — the waiver stays `.yaml` via `yaml.safe_dump`; the earlier TOML-reversal is withdrawn.)*

> **⚠️ Phase-0 review corrections (2026-07-12) — second reconciliation pass.** A full-corpus review (findings: gist `326be5f25e702e0fcce343046c70a6b2`) landed these corrections: **(a)** the exit projection is pinned — **`indeterminate` → exit 1** (exit 2 stays reserved for operational error; FR20); **(b)** J1's "warn at minimum," FR16's "clean at N%," and the offline-DB state-machine cell predated the `indeterminate` state and are corrected inline; **(c)** **FR19 is repurposed** as the warn-only coverage guardrail (post-triad, any coverage gap already exits non-zero via `indeterminate`); **(d)** persona **P8 (local developer / workstation mode)** + Journey 10 added — the `--bypass`→commit flow is local-only by design; the primary consumer remains the pipeline; **(e)** "parallel execution" in Growth means *fleet/multi-manifest* parallelism — the two engines are parallel in v1 (NFR-P-concurrency).

## Executive Summary

**python-deptry-osv-scanner** is a non-interactive CI/CD quality-gate CLI that unifies **dependency hygiene** (unused / missing / transitive deps via `deptry`) and **known-vulnerability scanning** (CVEs via Google `osv-scanner`) into a single schema-validated pass behind **one exit code**, for **Python libraries sourced from either PyPI or conda-forge**. For PyPI-world projects both engines already work natively — deptry reads `pyproject.toml` (PEP 621 / Poetry / PDM / uv / setuptools) and `requirements.txt`; osv-scanner reads the lockfiles (`poetry.lock`, `pdm.lock`, `uv.lock`, `Pipfile.lock`, `pylock.toml`, `requirements.txt`) — so python-deptry-osv-scanner **orchestrates and unifies** them. Its differentiated wedge is **extending both engines to the conda/pixi formats neither parses natively** — `environment.yml`, v0 `meta.yaml`, v1 `recipe.yaml`, and `pixi.toml` — via a manifest-resolution bridge, making conda-forge-sourced Python projects first-class alongside PyPI ones. (See § Supported Dependency Managers & Lockfiles.)

The tool is **ecosystem-agnostic**: one gate whether a project's dependencies resolve from PyPI or conda-forge. The segment with the sharpest *unserved* gap is **conda-feedstock and pixi-project maintainers** — who today cannot run either engine on their **source** recipe/manifest without a lossy manual translation into a `requirements.txt` fiction (the majority still on v0 `meta.yaml`). *(Precisely: incumbents like Trivy/Syft do scan an already-**installed** conda environment via `conda-meta/`; what nobody serves is **pre-build source-manifest** scanning, and no tool brings dependency-**hygiene** to conda at all — see § Innovation.)* The product serves **any Python developer shipping pip- or conda-sourced software** (scripts, applications, components, libraries). Platform-engineering and DevSecOps teams are **distribution channels** (who deploy the gate across a 20,000+ repo fleet). The irreducible promise: **one exit code you can trust, with honest coverage.**

### What Makes This Special

**Core insight:** both jobs begin at the same manifest parse. python-deptry-osv-scanner builds **one conda/pixi-native manifest front-door feeding two independent extraction paths** — deptry's (source-tree AST + import→distribution mapping; versions ~irrelevant) and osv-scanner's (versioned lockfiles; name-only is last resort) — and emits one consolidated, schema-validated `ComplianceReport`.

Differentiators: (1) **pre-build source-manifest resolution** across six formats including both v0/v1 conda recipes — incumbents (deptry, osv-scanner, Trivy, Syft) all require a *resolved/installed* environment, so scanning the *source* recipe/manifest pre-build, plus dependency-**hygiene** for conda (zero incumbents), is the wedge (the hero; unification is the *byproduct* of parsing once); (2) one gate / both signals / one exit code; (3) fleet-scale and **lean at runtime** — stdlib-lean extraction (`tomllib` + `re` + `yaml.safe_load` for clean-YAML; targeted conda-provisioned libs, no heavy frameworks), idempotent, cheap enough to be a default gate; (4) an **honest, actionable contract** — the report carries an explicit `status` and per-manifest coverage, so "clean" never renders identically to "we only parsed what we could," and findings gate on **report content, never a subprocess exit code**.

*Competitive note (time-bound):* the wedge rests on a snapshot of fast-moving upstream tools (osv-scanner's lockfile list grows per release; Trivy/Syft scan *installed* `conda-meta/`, not source manifests; Trivy owns the "one CLI / one gate" shape) — to be validated by a dated competitive spike (done 2026-07-11, § Innovation), not asserted as an evergreen gap.

## Project Classification

- **Type:** `cli_tool` — a non-interactive CI/CD policy/quality-gate CLI (primary consumer = pipeline). `report-schema.json` is the data contract (an output_formats concern); no public SDK/IDE surface. *(Corrected 2026-07-12: supported **secondary** consumer = a developer at a terminal — P8, workstation mode: pre-push testing, waiver authoring, environment debugging. Interactivity remains zero; local mode softens nothing.)*
- **Domain:** DevSecOps / software supply-chain security.
- **Complexity:** Medium engineering, **high stakes** (a missed CVE or a false-positive blocking builds propagates fleet-wide). Hotspots: **OD2** (osv-scanner input / version resolution) and **OD3** (stdlib parsing of v0 `meta.yaml` Jinja `{% set %}` / `{{ x|filter }}` / `{{ compiler() }}` / `# [sel]` selectors + v1 `recipe.yaml` `${{ }}` + `environment.yml`).
- **Context:** Greenfield (complete intake spec + committed build scaffold at `src/shared/packages/python-deptry-osv-scanner/`; no running system).

## Supported Dependency Managers & Lockfiles

*Grounded 2026-07-11 against upstream docs — a **time-bound snapshot** (both engines move fast; re-verify before any external release). Sources: osv-scanner "supported-languages-and-lockfiles"; deptry "supported-dependency-managers".*

Two coverage paths, by where the dependencies are sourced:

**PyPI path — delegate to the engines' native parsers, then unify** (python-deptry-osv-scanner adds no bespoke parsing here):

- **deptry** natively reads `pyproject.toml` — PEP 621 (`[project.dependencies]`, `[project.optional-dependencies]`, `[dependency-groups]`), Poetry (`[tool.poetry.*]`), PDM (`[tool.pdm.dev-dependencies]`), uv (`[tool.uv]`), setuptools (`[tool.setuptools.dynamic]`) — and `requirements.txt` / `requirements.in` / `*-dev.txt` (pip / pip-tools).
- **osv-scanner** natively reads (Python) `requirements.txt`, `poetry.lock`, `pdm.lock`, `uv.lock`, `Pipfile.lock`, `pylock.toml`.
- → python-deptry-osv-scanner runs each engine on its native input and consolidates the result.

**Conda/Pixi path — the differentiated bridge (E1):** **neither** engine parses `environment.yml`, `meta.yaml` (v0), `recipe.yaml` (v1), `pixi.toml`, `pixi.lock`, or `conda-lock.yml`. python-deptry-osv-scanner's manifest engine extracts the dependency set and bridges it — a synthesized `requirements.txt` for deptry, and version-pinned requirements (from `pixi.lock` / conda where present, else **name-only + marked** per OD2) for osv-scanner, since osv has **no** conda/pixi-native format.

**Stated precisely:** python-deptry-osv-scanner is *not* re-implementing PyPI dependency parsing — it **extends two mature engines to the conda/pixi ecosystem they don't cover**, behind one unified gate. Non-Python osv-scanner ecosystems (npm, Go, Rust, …) and its container/artifact scanning are **out of v1 scope** (Python-first: PyPI + conda-forge).

## Success Criteria

### User Success

- A **Python developer shipping pip- or conda-sourced software (scripts, applications, components, libraries)** — whether deps come from PyPI or conda-forge — runs `python-deptry-osv-scanner` once and gets a unified hygiene + vulnerability verdict. PyPI projects: deptry + osv consolidated (no more two CI steps + `jq`). Conda/pixi projects: **source-manifest** hygiene+vuln coverage they had none of before (no manual `requirements.txt` translation; incumbents scan only a *built* environment).
- Every finding is **actionable** (package + manifest location; or advisory ID + affected/fixed version); no theoretical noise.
- A **platform engineer** wires it into a CI template once — deterministic exit 0 / non-zero across the fleet.
- **Trust:** a green check never hides a crash or an unparsed manifest.

### Business Success

- **3-month:** gate on local-recipes CI + N pilot Python projects (PyPI- and conda-sourced). Metric: ≥ 98% of the repo's own conda recipes scan without an `error` status.
- **12-month:** promoted into cf_atlas (FR-16/FR-18); default fleet gate. False-positive rate low enough teams don't disable it.
- **Anti-metric:** gate-disabled events (false-green / false-red storm) → **target 0**. *(Not in-tool-measurable — telemetry is out of scope; tracked via measurable **proxies**: false-green = 0 (C0/Measurable Outcomes), a warn-only on-ramp exists (FR23), and an auditable expiring bypass exists (FR24). The chain prevents disablement; the proxies are how we evidence it.)*

### Technical Success

- **PyPI path:** correct **delegation** — deptry consumes `pyproject.toml`/`requirements.txt`, osv-scanner consumes the native lockfile (`poetry.lock`/`uv.lock`/`pdm.lock`/`Pipfile.lock`/`pylock.toml`/`requirements.txt`); no bespoke parsing; results unified.
- **Conda/pixi path (E1 bridge):** corpus-conformance — **0 uncaught exceptions** across all `recipes/*/{recipe.yaml,meta.yaml}` (~1,950 real files as of 2026-07-11; globbed at runtime) + sampled `environment.yml`/`pixi.toml`; unparseable rate **< 2%**, surfaced per-manifest.
- **Honest contract + severity gate:** schema-validated; `status ∈ {clean, warnings, policy-violation, error, bypassed, not-applicable}`; **severity-tiered exit 0/1/2** (default block on **critical CVE**; the KEV tier is **deferred post-v1**, KEV surfaced as an annotation only — see § Domain-Specific Requirements); typed `error_kind` (unparsable-manifest → developer, engine-unavailable → platform, internal-error → CLI maintainers); the gate decides on report **content + severity**, never a subprocess returncode.
- **Auditable bypass:** `--bypass` emits a committed, **expiring** waiver (default 14d; config + per-repo override); exits 0 with `status: bypassed` + `review_required: true`; the tool never writes the repo (NFR3). An **expired** waiver re-blocks.
- **SBOM:** a **CycloneDX BOM** is emitted and validates against the committed CycloneDX schema; components carry correct purls (`pkg:pypi/…` vs `pkg:conda/…?channel=`); a **partial** BOM when coverage < 100%.
- **Determinism + no mutation (NFR-R3):** **decision-deterministic** by default (same inputs + DB snapshot → same exit code + findings set); **byte-identical** output in `--deterministic` mode; no host/source mutation; cleanup on success + failure.
- **Lightweight (NFR-P):** stdlib-only bridge; cheap concurrent 20k-repo runs (per-invocation cost independent of fleet size). Conda + wheel + sdist build green.

### Measurable Outcomes

- PyPI path: 100% correct delegation on fixtures (both engines consume native inputs; report unifies).
- Conda/pixi path: parse coverage ≥ 98% on the recipe corpus (~1,950 files, 2026-07-11; globbed at runtime); 0 uncaught exceptions; decision-deterministic (byte-identical in `--deterministic` mode).
- Exit-code matrix 100% correct across severity tiers (clean/warn → 0, policy-violation → 1, error → 2) + each typed `error_kind`; **false-green = 0** on seeded fixtures; a **non-expired waiver → exit 0** (`bypassed`, `review_required`) and an **expired waiver → re-block (exit 1)**; report schema-valid in CI (100%).
- Emitted **CycloneDX BOM validates against schema** in CI (100%); purls correct on the fixture set; **BOM component count == resolved-inventory count** (no silent drops).
- **Split coverage asserted independently:** `coverage.hygiene` and `coverage.vulnerability` are validated as **distinct fields** on the fixture set (a manifest may be 100% hygiene-covered yet 0% vuln-covered) — the measurable form of the "honest coverage" promise.

## Product Scope

### MVP - Minimum Viable Product (v1)

**PyPI path:** orchestrate deptry (native pyproject/requirements) + osv-scanner (native lockfile) → unified `ComplianceReport` + gate. **Conda/pixi path (E1 bridge):** extract deps from `environment.yml`/`meta.yaml` (v0)/`recipe.yaml` (v1)/`pixi.toml` (stdlib-only, two-pass eval, name-only+marked, per-manifest coverage); synthesize `requirements.txt` for deptry + version-pinned reqs for osv (from `pixi.lock`/conda else name-only). **E4:** schema-validated `ComplianceReport` (`status` + severity + `schema_version` + coverage + `error_kind`) + human summary + **severity-tiered exit-gate** (FR5: 0/1/2; `--fail-on` / `max_critical`/`max_high`/KEV; default critical+KEV blocks) + typed errors (FR10) + an **auditable expiring bypass** (FR9: `--bypass` → committed waiver, default 14d / config / per-repo, `review_required`); **emit a schema-validated CycloneDX SBOM (FR8 — correct purls, coverage-marked)**. Corpus + fixture tests; conda/wheel/sdist build; respect `[tool.deptry]` ignores.

### Growth Features (Post-MVP)

cf_atlas promotion (FR-16/FR-18 MCP tool + pixi CLI) · vuln-side waiver · surface more osv-native lockfiles · better conda↔PyPI name reconciliation · alternate hygiene backends (`fawltydeps`, `pip-check-reqs`) via `--engine` · fleet/multi-manifest parallelism *(the two engines already run in parallel in v1 — NFR-P-concurrency; disambiguated 2026-07-12)*.

### Vision (Future)

Non-Python osv ecosystems + container/artifact scanning · default fleet supply-chain gate / the atlas's authoritative signal · optional external distribution (PyPI/conda-forge, OD5).

## User Journeys

*Refined via an advanced-elicitation pass (pre-mortem + red-team + stakeholder round-table) and a party-mode roundtable (PM / Architect / Analyst / Dev). The consensus that shaped this set: **"honest coverage" and its false-green guards are the product, not enhancements** — so the journeys below make the coverage contract and the "no-meaningful-scan" guard first-class, and each surfaces the requirements it implies (see Journey Requirements Summary).*

### Persona roster

| ID | Persona | Scope | Distinct need |
|---|---|---|---|
| **P1** | Conda-feedstock / pixi maintainer (*Priya*) | **Beachhead** | A hygiene + CVE gate on manifests neither engine parses natively |
| **P2** | PyPI-world Python developer (*Devon*) | Market-expansion | Collapse two CI steps + `jq` glue into one trustworthy gate |
| **P3** | Platform engineer (*Sam*) | Distribution (fleet) | Deterministic exit matrix + self-routing failures across 20k repos |
| **P4** | DevSecOps / security triage (*Alex*) | Distribution (fleet) | Triage a finding; decide accept-risk vs fix |
| **P6** | Durable-evidence consumer / auditor | **Enterprise / post-v1** | Historical SBOM+report as audit evidence (sole human justification for the durability property; v1 *emits* the artifacts, retention is the CI system's job) |
| **P7** | Schema / release owner (the CFE-skill owner here) | Maintainer | Owns report `schema_version`, severity mapping, pinned engine versions; the person "one exit code you can trust" actually depends on |
| **P8** | Local developer at a terminal (workstation mode) | **Secondary consumer (v1, added 2026-07-12)** | Pre-push testing, waiver authoring (the `--bypass`→commit flow is local-only by design), environment debugging — same gate, zero prompts |
| **M1** | The CI pipeline / cf_atlas | Machine consumer | A stable, self-describing data contract (schema report + SBOM) |

*Cut from the roster (this is the gap where a "P5" would sit):* a standalone **risk-approver/EM** persona — in the beachhead a solo maintainer triages, authorizes, and audits one waiver in a single motion; the authorization *moment* is captured as a **waiver-schema field (`authorized_by` / `signed`)**, not a distinct person. The J4 authorization beat still proves the tool works whether those roles collapse to one human (beachhead) or split across three (enterprise). *Logged as a dependency risk, not a persona:* the upstream deptry/osv maintainers, whose output formats the tool's parsing contract is hostage to (absorbed by J3's engine-drift handling + FR10).

### Journey 1 — Priya (P1), the conda-feedstock maintainer: the wedge, proven by honest coverage *(primary success path)*

**Opening scene.** Priya maintains ~30 conda-forge feedstocks and a pixi analytics library. Her deps live in `recipe.yaml`, legacy `meta.yaml`, and `pixi.toml`. She wants the hygiene + CVE gate her PyPI-shipping colleagues have, but every time she reaches for `deptry` or `osv-scanner` she hits the same wall: neither parses her manifests. Her only option is to hand-translate the recipe into a fictional `requirements.txt` — lossy, stale the instant she edits the recipe, quietly wrong.

**Rising action.** She adds one step: `python-deptry-osv-scanner scan .`. The manifest engine walks the repo, two-pass-evaluates the `recipe.yaml` `${{ }}` and the `meta.yaml` `{% set %}` / `{{ compiler() }}` / `# [sel]` selectors stdlib-only, and extracts the dependency set — feeding deptry a synthesized requirements front-door and osv the version-pinned set from `pixi.lock` (name-only + marked where no version resolves).

**Climax — the payoff is the *honest* verdict, not the clean one.** Her mixed repo can't be fully resolved: some deps come through with versions, some degrade to name-only, one `meta.yaml` uses a Jinja construct the extractor can't evaluate. The report doesn't paper over it — it renders **`clean at 60% coverage`**, with the coverage split into **hygiene-coverage vs vulnerability-coverage** (a manifest can be 100% hygiene-covered yet 0% vuln-covered when every dep is name-only), and it names the 40% it *couldn't* see. Critically: **the unresolved 40% routes to `indeterminate` (above `warn`) — the run exits non-zero by design** until Priya locks (`pixi.lock`), files a time-boxed waiver, or opts into `--warn-only`; empty-findings-at-partial-coverage is never `clean`. *(Corrected 2026-07-12 — the original "warn at minimum" predated the `indeterminate` state.)* Anyone can scan a clean `pixi.toml`; the wedge is trustworthy coverage on formats neither engine parses, and *this* is the demo that sells it.

**Resolution.** Priya has the same one-command gate as her PyPI peers, first-class on conda/pixi — and a green that never hides what it didn't look at.

*Reveals:* E1 6-format bridge + two-pass eval; **coverage as a first-class, split (hygiene/vuln) report field**; the `warn`-not-`clean` invariant on partial coverage; name-only+marked degrade. *Implies FR-NEW-A (coverage-as-requirement).*

### Journey 2 — Devon (P2), the PyPI developer: unification *(market-expansion happy path)*

**Opening.** Devon ships a Poetry library; his CI runs deptry in one step, osv-scanner in another, stitched with a brittle `jq` snippet that decides whether to fail the build.

**Rising action → climax.** He replaces all of it with `python-deptry-osv-scanner scan .`. The tool **delegates** — deptry reads his `pyproject.toml`, osv reads his `poetry.lock`, native inputs, no bespoke parsing — and emits one consolidated `ComplianceReport`. The exit code is driven by report **content + severity** (FR5), never by whichever subprocess happened to return non-zero.

**Resolution.** Two steps and a fragile script collapse into one honest gate. The value here isn't new coverage — it's unification behind one exit code you can trust. (This persona validates the two-path design and the "any Python dev" claim without inflating MVP scope.)

*Reveals:* PyPI delegation path, report consolidation, FR5 content-based gate, `[tool.deptry]` ignore respect.

### Journey 3 — Sam (P3), the platform engineer: fleet ops + typed-failure routing

**Opening.** Sam owns the CI template pushed to 20,000+ repos — some PyPI-sourced, many conda/pixi. He needs one gate that behaves deterministically and never flaps.

**Rising action.** He wires the tool in with `--fail-on=critical` and relies on the typed exit matrix. A path with **zero Python anything** exits 0 (`not-applicable`) benignly — **but a path with Python signals yet no parseable manifest fails closed (exit 2) by default** (the misconfiguration guard — wrong working dir, glob miss), and `--allow-empty` downgrades that to exit-0 + `coverage: none` for a deliberate monorepo sweep. *(Reconciled in Step 7: the default polarity is fail-closed-when-Python-present, superseding the earlier `--require-manifest` opt-in framing; the exact "expected-a-manifest" heuristic is an Architecture open Q.)*

**Climax — failures route themselves.** A rollout wave hits problems, and instead of a false-green *or* a fleet-wide red storm, each failure carries a typed `error_kind` with an owner:
- `unparsable-manifest` → **developer**
- `engine-unavailable` → **platform** (Sam)
- `engine-output-unrecognized` (valid JSON, expected keys absent — silent upstream schema drift) / `engine-output-unparseable` (truncated/log-polluted output) / `engine-execution-failed` (crash/OOM, no usable output) / `engine-timeout` → **CLI maintainers** (P7)
- `internal-error` → **CLI maintainers**

Every one of these is **exit 2, explicitly not clean** — the absence of an expected field is treated as an *error, not a zero*, so a working-but-drifted engine can never report false-green.

**Resolution.** One template, deterministic across the fleet, self-routing failures. Sam's anti-metric — gate-disabled events — stays at zero because the gate never lies and never storms.

*Reveals:* FR10 **expanded error taxonomy** + ownership routing; `--allow-empty` (the fail-closed default's downgrade, D2); the "absence-is-error-not-zero" invariant. *Implies FR-NEW-F (engine-output shape validation).*

### Journey 4 — Priya + Alex (P1 / P4): the auditable bypass loop *(primary edge case)*

**Opening.** Priya has a release to ship, but osv flags a `high` CVE with no upstream fix. A hard block strands the release; silently ignoring it is dishonest.

**Rising action.** She runs `... --bypass --reason "no upstream fix; tracking GHSA-xxxx"`. The tool emits a committed `.python-deptry-osv-scanner-waivers.yaml` stanza (`accepted_at` / `expires_at`, default 14d, + an `authorized_by` field) that it **reads but never writes** (NFR3). It exits 0 with `status: bypassed`, `review_required: true` — **and the run still carries `bypassed` in the audit record even though the residual exit is 0**, so the trail is never blind to a suppression. Only the *covered* finding is suppressed; a residual un-waived violation still surfaces `policy-violation`.

**The trust boundary (explicit).** The waiver file is **untrusted input**. The tool's *only* runtime obligations are: parse it, enforce `expires_at` against wall-clock, and emit an auditable record (id, matched finding, `authorized_by`-as-claimed, expiry, days-remaining). *Was the approver real? Was the date hand-edited forward?* — **out of the tool's process boundary, delegated to code review + CODEOWNERS on the waiver file.** The tool can't verify a GitHub control at runtime, and the PRD says so rather than pretending otherwise.

**Climax — the other side.** Two weeks later Alex (P4) sees the waiver surface via `review_required`; meanwhile Priya's next CI run finds it **expired** → the finding **re-blocks** (exit 1). The bypass was a time-boxed loan, not a permanent mute. *(Waiver-at-scale / expiry-storm renewal is deferred post-v1.)*

*Reveals:* FR9 waivers-as-code (expiring, `authorized_by`); `review_required` routing; expiry re-block; **waiver-as-untrusted-input trust boundary**; NFR3. *Implies FR-NEW-D (waiver integrity + authorizer identity, extending FR9 beyond expiry).*

### Journey 5 — M1, the machine consumer: the data contract + false-green guards

**Opening.** The consumer is the pipeline, not a person. It needs a stable contract, not prose.

**Rising action.** Each run emits a schema-validated `ComplianceReport` (`status` + `severity` + `schema_version` + split `coverage` + `error_kind`) and a **CycloneDX SBOM** of the resolved inventory.

**Climax — the guards that make "clean" honest:**
- **Empty-extraction trap.** A manifest that parses but yields zero deps must distinguish *legitimately empty* from *extractor dropped them all*. The parser emits per manifest `{deps_section_present, raw_token_count, extracted_count}`; `deps_section_present && raw_token_count>0 && extracted_count==0` ⇒ an **`extraction-anomaly`**, degrade to name-only+marked — **never `clean` at 100%**.
- **Self-declaring partial SBOM.** A partial BOM carries a BOM-level `extraction:complete=false`; an SBOM that can't tell you it's incomplete is worse than none for a downstream consumer.
- **Source-registry purls.** A component's purl reflects the **source registry of the manifest it came from** — `pkg:pypi/…` vs `pkg:conda/…?channel=` — never a guess (conda name ≠ PyPI name; the mapping is unreliable). An unresolved registry-of-truth is **marked, not guessed** into a purl.

**Resolution.** The exit code gates the build today; the schema'd report + honest SBOM make the tool a first-class data source for cf_atlas (FR-16/FR-18, post-v1) tomorrow — `schema_version` lets old and new reports coexist without a breaking rewrite.

*Reveals:* E4 schema + `schema_version`; FR8 CycloneDX SBOM; empty-extraction guard; partial-SBOM self-declaration; source-registry purls. *Implies FR-NEW-B (no-meaningful-scan guard).*

### Journey 6 — First-run adoption on a dirty legacy repo *(the anti-metric on-ramp)*

**Opening.** A maintainer turns the gate on over a legacy feedstock with accumulated debt. First run: 40 findings. If CI hard-fails immediately, they rip the gate out — and `gate-disabled events → 0` is blown.

**Rising action → resolution.** A **warn-only** first-run mode reports everything but exits 0 (findings surface as `warn`, loud in the report), letting the team adopt without a day-one red wall and burn the backlog down deliberately. This is the pressure-release valve, distinct from the severity gate — it *is* the on-ramp. *("baseline" is reserved for the deferred new-findings-only ratchet; the v1 on-ramp is warn-only.)*

*Reveals:* baseline/warn-only mode. *Implies FR-NEW-C.*

### Journey 7 — Compliance / audit evidence retrieval *(enterprise / post-v1)*

**Opening.** Months after a release, an auditor (P6) needs to prove it was scanned. v1 already **emits** the durable evidence: the schema report + CycloneDX SBOM + waiver audit trail, each deterministic and self-describing.

**Boundary (explicit).** **Retention and retrieval are the CI system's job, not the tool's** — NFR3 forbids the tool writing the repo. The tool's contribution is a self-describing artifact; storage, indexing, and query-over-time are out of v1 scope. This journey exists to justify the *durability property* of FR8, not to smuggle in a retention requirement the tool can't own.

*Reveals:* FR8 SBOM + report as durable evidence (durability property owned); retention explicitly out-of-scope.

### Journey 8 — P7, the schema/release owner: the corpus regression gate

**Opening.** P7 owns the extractor's correctness — the evidence behind "coverage you can trust." Every skill/tool bump risks a parsing regression across the conda recipe universe.

**Rising action → climax.** A **corpus-conformance suite** runs the extractor over ~1,950 real `recipes/*/{recipe.yaml,meta.yaml}` (globbed at runtime) asserting **0 uncaught exceptions**, a **ratcheted `unparseable_rate` baseline** (committed golden number; `current <= baseline` or CI fails — a bump that degrades more manifests is caught), plus **NFR-R3a zero repo writes + NFR-R3b byte-identical output (run in `--deterministic` mode)**. Because the extractor is lossy-by-design (stdlib `re` can't fully evaluate `pin_subpackage` / conditional deps), P7 also owns a **per-format supported-construct matrix** — what's in-scope vs. degrades — without which "coverage" is undefined per format.

*Reveals:* corpus-conformance as an owned regression gate; ratcheted baseline; supported-construct matrix. *(Test-strategy made a journey because a promise with no owner has no teeth.)*

### Journey 9 — Verdict composition: N findings → one status, one exit *(the state-machine contract)*

**Opening.** Real runs produce mixed outcomes: one manifest clean-but-vulnerable (`policy-violation`), another fails to parse (`error`), a third has a valid waiver (`bypassed`). What single `status` and single exit code does the run carry?

**The contract.** The report is a **reduce** over per-finding outcomes, and status severity and exit code are **deliberately different orderings**:
- **Status severity:** `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable` (bypassed sits above clean because a suppression is an audit-relevant event; **`indeterminate` sits above `warn`** so a clean sibling axis can never mask "existed-but-couldn't-scan" — it routes here, *not* to `not-applicable`).
- **Exit derived separately:** any `error` → **2**; else any un-waived `policy-violation` → **1**; else **0**.
- **`error` dominates the exit** because an errored run means the verdict is *untrustworthy* — you cannot assert "no violation" over a manifest you failed to scan. The report still records the violation that *was* detected; the exit collapses to one number, the report does not.
- **"Content wins" (FR5) holds only when content exists and validates.** Absence of content on a non-zero engine exit (crash/OOM) is a **hard failure, not empty-clean** — the single most dangerous case, nailed here.

*Reveals:* verdict-composition precedence lattice; status-vs-exit separation; the crash-is-not-clean invariant. *Implies FR-NEW-E.*

### Journey 10 — P8, the developer at a terminal: workstation mode *(secondary consumer; added 2026-07-12)*

**Opening.** Before wiring CI, a developer trials the gate locally: install to the workstation (`pixi global install` / the local channel — Story 5.1 docs), then `python-deptry-osv-scanner scan . --warn-only` — the recommended first contact with the tool.

**Rising action.** Cold start bites first: no offline DB on the laptop → a typed error with an **actionable nudge** (provision the DB / point `--db-path` / use the explicit online mode if Story 1.3a ships one — never a silent fetch, NFR-S2). A `doctor`-style self-check (FR21's detection logic re-exposed; v1-if-cheap) answers "is this machine even scan-capable?"

**Climax.** They fix a finding, re-run, watch it clear — then hit the un-fixable one and author a waiver: `--bypass --reason …` emits the stanza **they commit** (the tool never writes the repo, NFR-S4). This loop *cannot run in CI* — waiver authoring is local-only by design, which is why P8 is a supported consumer, not an afterthought.

**Resolution.** Same lattice, same exit codes, same zero prompts as CI — local mode softens nothing. The developer wires CI already knowing exactly what it will say.

*Reveals:* the workstation install story (5.1); cold-start provisioning UX + the online-opt-in decision (1.3a); `doctor` re-ranked v1-if-cheap; the waiver-authoring loop as a local-first flow.

### Journey Requirements Summary

The journeys resolve into these capability clusters, mapped to epics + the requirements they surface:

- **Manifest resolution front-door (E1)** — 6 formats, two-pass eval, stdlib-only, split coverage, name-only+marked degrade, supported-construct matrix *(J1, J8)*
- **Dual extraction + delegation (E2/E3)** — PyPI native delegation; conda/pixi bridge to deptry + osv *(J1, J2)*
- **Honest report + severity gate (E4)** — schema'd `ComplianceReport`, split coverage, verdict-composition, typed error taxonomy + ownership routing, CycloneDX SBOM *(J2, J3, J5, J9)*
- **Auditable expiring bypass (FR9)** — waivers-as-code, `authorized_by`, `review_required`, expiry re-block, untrusted-input trust boundary *(J4)*
- **Adoption + fleet + machine contract** — warn-only on-ramp, deterministic exit matrix, `--allow-empty`, `schema_version` forward-compat, corpus regression gate, atlas seam, workstation on-ramp (install story, cold-start UX) *(J3, J6, J8, J10, M1)*

**Requirements these journeys surface for Step 9 (Functional Requirements):**

| Flag | Requirement | Origin |
|---|---|---|
| **FR-NEW-A** | Coverage measurement + reporting as first-class (split **hygiene** vs **vulnerability**) — *the "honest coverage" promise's missing FR* | J1, J5 |
| **FR-NEW-B** | "No-meaningful-scan" guarded exit state (empty-extraction ∪ not-applicable ∪ crashed-engine → **never `clean`/0**) — the false-green guard | J3, J5, J9 |
| **FR-NEW-C** | Warn-only / baseline first-run mode (adoption on-ramp) | J6 |
| **FR-NEW-D** | Waiver integrity + authorizer identity (extends FR9 beyond expiry) | J4 |
| **FR-NEW-E** | Verdict-composition / precedence (status-severity lattice + separately-derived exit) | J9 |
| **FR-NEW-F** | Engine-output shape validation + expanded error taxonomy (`engine-output-unrecognized` / `-unparseable` / `engine-execution-failed` / `engine-timeout`) | J3 |

**Open questions carried to the Architecture phase (4):**

1. **Coverage-floor policy** — default for `--fail-under-coverage` (assume `0` = off in v1 to protect first-run adoption; the *floor gate* is opt-in, the *coverage field* is always emitted).
2. **Waiver integrity trust boundary** — v1 assumes *git + CODEOWNERS is the boundary*; the tool treats the waiver as untrusted and only enforces expiry + emits the audit record.
3. **Multi-environment dep selection & per-section severity** — v1 assumes **provenance-now, policy-later**: extract all resolvable sections, tag each dep with its source environment in the report/SBOM, apply one uniform policy; per-section severity deferred.
4. **deptry has no severity concept** — how do hygiene findings (unused/missing/transitive/misplaced) map onto FR5's 0/1/2 gate — a separate boolean axis, or mapped onto severity? *(+ minor: `pkg:conda?channel=` identity/dedup semantics.)*

## Domain-Specific Requirements

*Domain: DevSecOps / software supply-chain security (medium complexity, high stakes). No row in `domain-complexity.csv`, so grounded from the domain itself. Two high-risk decisions (KEV data source, air-gapped/offline operation) were stress-tested (debate + red-team, grounded against osv-scanner's actual offline + KEV behavior) and resolved below.*

### Standards & Conformance
- **CycloneDX** (FR8 output) — target spec **1.6**; components aim at the **NTIA minimum SBOM elements** (supplier, component name, version, unique identifier, dependency relationship, author, timestamp) so the BOM is audit-usable.
- **Package-URL (purl) spec** — emitted purls conform to the purl spec; `pkg:pypi/…` vs `pkg:conda/…?channel=` reflects source registry (ties to the Step-4 purl-correctness invariant). *Channel-qualifier identity/dedup semantics = Architecture open Q.*
- **OSV schema** — the vuln data model consumed via osv-scanner; findings surface OSV / GHSA / CVE advisory IDs.
- **Severity taxonomy** — **CVSS** (v3.1 / v4.0) is the **v1 gate signal**; **CVE** identifiers; **CISA KEV** is *annotation-only in v1* (see Integration Requirements).
- **Context frameworks (positioning, not v1 outputs):** NIST **SSDF** (SP 800-218), **SLSA**, EO 14028. SPDX output is **out of v1** (CycloneDX only, locked).

### Technical Constraints (domain-driven)
- **Offline-first vuln data (resolved).** Offline is the **fleet-recommended, determinism-preserving path** — a provisioned/cached OSV database (`--offline`, `{ecosystem}/all.zip`), not live osv.dev querying. Online querying remains supported but **opt-in and never silent** (no covert egress of the dependency list to a third-party API). For a true air-gap use **full `--offline`**, not `--offline-vulnerabilities` (the latter can still egress during transitive resolution — flagged for Architecture). Consistent with `docs/enterprise-deployment.md` (JFrog / offline mirrors).
- **Vuln-DB provenance & currency (mandatory).** Every report **records the vuln-DB source + snapshot timestamp**; a **staleness warning is mandatory in offline mode** (warn if the DB is older than a configurable N days). This is what converts a stale-DB false-green into a loud `warn`.
- **Determinism for forensics.** NFR3 twice-run byte-identical is an **audit / reproducibility** requirement in this domain (a scan cited in an incident must reproduce) — an offline, pinned DB is what makes it hold; a live DB cannot.

### Integration Requirements
- **KEV gate tier — deferred to post-v1 (resolved).** osv-scanner does **not** natively supply CISA KEV; a KEV gate tier would add a second data source, a second staleness axis, and a fragile OSV-advisory→CVE→KEV alias join. **v1 default gates on CVSS-critical only.** If osv output already carries an exploited/KEV hint in `database_specific`, surface it as a **report annotation, never a gate input**. Revisit as a **bundled CISA KEV snapshot** (US-gov public domain, refreshed per tool release) in v1.1. *(EPSS: out of scope — separate FIRST.org feed.)*
- **cf_atlas ingestion** (FR-16 / FR-18, post-v1) — schema report + SBOM as an atlas signal.
- **Downstream SBOM consumers** — the CycloneDX BOM is consumable by Dependency-Track-class tooling.

### Risk Mitigations (domain risk posture)
- **Cardinal rule — asymmetric failure cost.** A missed CVE (false-negative) is catastrophic; a blocked build (false-positive) is costly but recoverable. Bias = **fail-loud, never false-green** (enforced by the Step-4 guards + the mandatory offline staleness warning). *This is precisely why deferring KEV is acceptable — it under-prioritizes, it does not create a false-green.*
- **Advisory churn** — advisories get withdrawn / disputed; a waiver keyed to a now-withdrawn advisory should not silently outlive it (FR9 expiry bounds this).
- **Actionability (FR7)** — every finding carries advisory ID + affected/fixed version + severity + manifest location; no theoretical noise. *(Out of scope: install-time typosquat / name-confusion — the tool scans **declared** deps, not resolver substitution.)*

### 🚩 Cross-step decision to carry into Step 9 (Functional Requirements)
> **FR5 default REVISED for v1:** the v1 default gate blocks on **CVSS-critical** (warn on high/med/low + all hygiene). The **"KEV-affecting-current" tier is deferred to post-v1** (bundled KEV snapshot). KEV/exploited is surfaced as a report annotation only, never a v1 gate input. *(Supersedes FR5's original "block on critical CVE or KEV-affecting-current" wording for v1.)*

### Architecture open questions (from this step)
1. `--offline` vs `--offline-vulnerabilities` for the air-gapped path (the transitive-resolution egress leak).
2. Configurable DB-staleness threshold (default N days) + the source of the DB snapshot timestamp.
3. osv-scanner feedstock version to pin (verify offline-mode flags against the pinned version; offline mode stable since ~v1.4).

## Innovation & Novel Patterns

*Innovation type: **novel-combination / underserved-gap**, not a breakthrough paradigm. Grounded against the live competitive landscape (2026-07-11 spike) — which sharpened the claim and caught a potential over-reach: vuln scanning of **installed** conda environments already exists (Trivy/Syft/Grype parse `conda-meta/`), so the defensible novelty is narrower and stronger than "conda is unserved."*

### Detected Innovation Areas
1. **Source-manifest-native scanning (the real wedge).** Dep-hygiene + vulnerability scanning on the **declarative** conda/pixi formats — `recipe.yaml`, `meta.yaml`, `environment.yml`, `pixi.toml` — **pre-build, without a resolved environment.** Every incumbent scanner requires an *installed* `conda-meta/`; a feedstock maintainer editing a recipe that was never built locally is unserved today.
2. **Dependency-hygiene for conda — zero incumbents.** deptry (unused / missing / transitive / misplaced) is PyPI-only; no tool brings hygiene to conda recipes. This niche has *no* competitor, built or unbuilt.
3. **Honest-coverage contract as a correctness posture.** Split hygiene/vuln coverage, coverage-qualified verdict, "never false-green," source-registry-correct purls — a differentiated *trust* property, not just a feature.
4. **Assumption challenged:** "you must build / resolve the environment before you can scan it." The wedge scans the *intent* (the manifest), degrading honestly where it can't resolve versions.

### Market Context & Competitive Landscape

| Tool | Covers | The gap it leaves |
|---|---|---|
| **Trivy** | `conda-meta/` (installed), Python egg/wheel, SBOM, one-gate shape | No source manifests; no hygiene |
| **Syft / Grype** | `conda-meta/` parsing, SBOM, vuln match | No source manifests; no hygiene |
| **pip-audit** | PyPI installed env, PyPA advisory DB | PyPI-only; installed-only; no hygiene |
| **deptry** | PyPI hygiene (pyproject / requirements) | No conda; no vuln |
| **QuantCo tooling / conda-deny / conda-meta-mcp** | Post-build conda audit; license checks; agent CVE triage | Not a unified pre-build hygiene+vuln gate |

**Owned by incumbents (not our novelty):** the one-CLI / one-gate / SBOM *shape* (Trivy). **Genuinely unserved:** pre-build source-manifest scanning + conda dependency-hygiene + the honest-coverage contract.

### Validation Approach
- **The bridge works:** corpus-conformance over ~1,950 real `recipes/*/{recipe.yaml,meta.yaml}` — 0 uncaught exceptions, ratcheted unparseable rate (Journey 8).
- **The honest-coverage claim holds:** false-green = 0 on seeded fixtures; the split coverage fields are asserted independently of pass/fail (Journeys 1, 5).
- **The gap is real (dated spike):** the 2026-07-11 competitive check *is* the spike — re-run before any external release, since Trivy/Syft could extend to source manifests.

### Risk Mitigation (innovation-specific)
- **Time-bound wedge (primary risk).** If Trivy/Syft add source-manifest parsing, or osv-scanner adds conda-native input, the bridge value erodes. **Fallback:** the hygiene+vuln unification + honest-coverage contract remain valuable independent of the bridge, and **conda dependency-hygiene has no incumbent at all** — that niche survives even if vuln-bridge parity arrives.
- **Don't over-claim.** Position as "source-manifest-native, pre-build, hygiene+vuln unified," never "the only conda vuln scanner." *(Applied in the Executive Summary: the defensible claim is the pre-build source-manifest + hygiene niche; incumbents scan only a built environment.)*

## CLI Tool Specific Requirements

*Project type: `cli_tool` — a **single-command, strictly non-interactive CI/CD gate**. CSV-guided (`command_structure` / `output_formats` / `config_schema` / `scripting_support`; `visual_design` / `ux_principles` / `touch_interactions` skipped — N/A). Hardened via advanced-elicitation (ADR + red-team + interface-consistency) and a party-mode roundtable (Architect / Dev / PM); the consensus reframe: the CLI surface is **a public contract consumed by a 20k-repo fleet + cf_atlas**, so it is **under-taxonomized, not over-built** — inputs, outputs, and the exit-code enum evolve by different rules.*

### Project-Type Overview
`python-deptry-osv-scanner scan <path>` (default `.`) + global `--version` / `--help` (part of the frozen contract — CI provenance + M1 discovery). One verb; no interactive subcommands; **no prompts ever** (even `--bypass` takes `--reason` inline). Room for `report` / `explain` subcommands post-v1.

### Command Structure
- **Verb:** `scan <path>`.
- **Gate/policy:** `--fail-on=<severity>` (default `critical`, per revised FR5), `--warn-only` (report + exit 0 — the sanctioned J6 adoption on-ramp), `--fail-under-coverage=<pct>` (default off), `--require-full-coverage` (promotes any `skipped` dimension to a failing verdict), `--allow-empty` (downgrades the no-manifest guard for monorepo sweeps).
- **Data source:** `--offline` / `--offline-vulnerabilities`, (contradictory combos like `--offline` + an online-only feature → typed exit-2 error, never silent last-wins).
- **Bypass:** `--bypass --reason "<text>"` (inline, never prompts).
- **Output control:** `--format text|json` (default `text`), `--output <file>` (report), `--sbom-output <file>` (SBOM — **orthogonal** to `--output`; `--format` governs the report only; the SBOM is always CycloneDX; file extension is not a contract), `--no-color` (auto-off when stdout isn't a TTY), `--quiet` (lowers **our** diagnostics only).

### Output Formats
- **Human (default, stdout):** findings by severity, per-manifest split coverage (hygiene/vuln), waiver notices, verdict line, **and a self-selling on-ramp nudge** when non-enforcing — e.g. `23 findings (18 waivable). Currently --warn-only — set --fail-on=high to enforce.` (adoption is a UX problem, tied to the `gate-disabled=0` anti-metric).
- **Machine (`--format json`):** **stdout is a valid `ComplianceReport` document OR empty — never partial/non-JSON.** On an early fatal error (bad flag, config-parse, nonexistent path) stdout is empty and the error is on stderr. Tested via chatty-engine + pseudo-TTY (`pty`) fixtures.
- **SBOM (`--sbom-output`):** CycloneDX **1.6**, self-declaring partiality, emitted **`experimental`** (schema not frozen) until cf_atlas actually ingests it.
- **Streams discipline:** report → **stdout**; all progress/diagnostics/warnings → **stderr**; text output + stderr are **explicitly unstable** (may change any release — declaring non-contract is itself a stability statement).
- **Engine invocation environment normalization (load-bearing — a single `_engine_env()` helper every engine call goes through):** force each engine's machine output to a **temp file** (deptry `--json-output`, osv `--format json --output`) and read the file (sidesteps "warning prepended to JSON"); `NO_COLOR=1` in the child env unconditionally; `stdin=DEVNULL` (no engine can block on a prompt); capture engine stdout/stderr to a system-temp diagnostics sink (never the scanned tree, NFR3); explicit `encoding="utf-8"` decode → undecodable engine output maps to a typed `error_kind` (FR10/FR-NEW-F), never a raw traceback. *Built in the first engine-integration slice — cheap now, ruinous to retrofit.*

### Config Schema
- **Precedence:** CLI flags > per-repo config file > built-in defaults.
- **Config file (decided — D3):** `[tool.python-deptry-osv-scanner]` in **both** `pyproject.toml` (PyPI-world home, beside `[tool.deptry]`) **and** `pixi.toml` (the conda/pixi bridge's natural home — P1/beachhead *is* the pixi user). *A dedicated `.python-deptry-osv-scanner.toml` may be added post-v1 if the TOML-section approach proves limiting.*
- **Per-key precedence rule:** effective config = union of the two tables. A key set in **both with unequal values** → `pyproject.toml` wins + a `config-conflict` warning to **stderr** (naming the key, both values, the winner). A key in one file only, or the same key with equal values, is **not** a conflict; both files present is **not** a conflict; conflicts never change the exit code; a CLI flag overriding the key suppresses the warning.
- **Parsing ACs:** `tomllib` binary mode (`rb`); a missing file is **normal → skip that source** (not an error); malformed TOML → typed `config-parse` error_kind (a malformed *primary* → exit 2; a malformed *optional secondary* with no relevant table → warn, don't hard-fail); wrong value types → `config-validation` error_kind; keys are hyphenated (`fail-on`), the underscore variant is rejected/ignored explicitly (no silent dual-accept).
- **Respect existing config:** `[tool.deptry]` ignores honored; the waiver file `.python-deptry-osv-scanner-waivers.yaml` is read (never written into the repo tree by a scan, NFR3).

### Scripting Support
- **Frozen exit-code enum `{0, 1, 2, 130}`** (0 clean/warn, 1 policy-violation, 2 error, 130 interrupted): a **closed set** — adding a code is a **MAJOR** change (a new code silently breaks every `elif rc == 2:` consumer), the *opposite* of the additive flag rule.
- **"No abnormal exit returns 0"** — any signal / interrupt / uncaught internal error → non-zero (SIGINT → 130), and **never** a `status: pass` report. (Handler unit-tested deterministically; a tolerant `pty` integration test is post-v1.)
- **Deterministic + composable:** decision-deterministic by default, **byte-identical in `--deterministic` mode** (NFR-R3b); JSON on stdout pipes to `jq`; the exit code drives the gate directly (no `jq` needed, unlike the pre-tool status quo).

### CLI Contract Stability (taxonomized — supersedes a single "additive-only" rule)
The tool is a stable fleet gate as a **behavioral** commitment, not a governance document. Three contract families:
- **OUTPUT** (evolve by *add fields + bump version*): `ComplianceReport` JSON (`schema_version`); CycloneDX SBOM (its **own** version = spec 1.6 + our profile, decoupled from the report; `experimental` until consumed); text stdout + stderr = **unstable**.
- **INPUT** (evolve by *accept-old-forever + deprecate→warn→remove*): config-key schema (renames deprecate, never silent-break — keys live in 20k repos); waiver-file schema (an in-file `version:` key; an unknown/future version → **reject with a typed error, never guess**).
- **Exit codes:** the frozen closed enum above.
- **v1 ships the behavior, not the paperwork:** no deprecation *lifecycle machinery* (registry / warn-emitter / removal schedule) — internal consumers are coordinated by a same-PR `grep`; the formal semver/deprecation *policy doc* is post-v1 (OD5, when external consumers exist).

### State-Machine Behaviors (defined cells)
- **No recognized manifest at the path (D2 — reconciles J3):** **fail-closed (exit 2) by default when Python signals are present but nothing parses** (the misconfiguration guard); exit-0 `not-applicable` only when the path has zero Python anything; `--allow-empty` downgrades the former.
- **`--offline` + OSV DB unreachable:** the vuln dimension reports `coverage: skipped (offline, no local db)` — **never "0 vulns"**; per the triad, skipped routes to **`indeterminate` → exit 1** (never a silent 0; `--warn-only` downgrades). *(Corrected 2026-07-12 — "default exit 0 (data, not failure)" predated the `indeterminate` state; `--require-full-coverage` is subsumed on this path.)*
- **One engine crashes, other succeeds:** verdict exit 2, **but the `ComplianceReport` is still emitted** with per-dimension status (clean / violation / error / skipped) — exit code ⊥ report emission.
- **Stale/expired waiver matrix:** valid+matches → suppress; valid+matches-nothing → `stale-waiver` warn (no verdict change); expired+matches → finding **un-waived** (counts toward exit 1) + `waiver-expired` warn; expired+matches-nothing → `stale-waiver` warn.

### Decisions resolved this step
- **D1 — Waiver I/O dependency:** the waiver read/write path uses a proper **YAML emitter (`safe_dump`), never string-concatenation** (`--reason` YAML-injection is real — the waiver is P4's audit trail); a small YAML lib scoped to waiver I/O is acceptable, while **extraction stays regex/stdlib** (`recipe.yaml`/`meta.yaml` carry Jinja a YAML parser chokes on). Round-trip AC: `safe_load(written)["reason"] == original` across quotes / `: ` / leading YAML indicators / newlines / whitespace / unicode / empty / a length bound.
- **D2 — no-manifest default:** fail-closed-when-Python-present (above).
- **D3 — dual-config at v1:** keep both `pyproject.toml` + `pixi.toml` config.

### Deferred to post-v1
- **SARIF output** (GitHub code-scanning / P3 fleet integration) — **reserve the `--format` value space now** so `--format sarif` is additive, not a breaking widening.
- Deprecation lifecycle machinery; SBOM schema freeze (emit `experimental` until cf_atlas consumes).

### Architecture open questions (from this step)
1. The exact **"expected-a-manifest" heuristic** for the fail-closed no-manifest guard (D2).
2. Confirm the **YAML-lib runtime dependency** scope for waiver I/O (D1) against the "lightweight" positioning.
3. Waiver-file **in-file `version:`** field + unknown-version rejection behavior.

## Project Scoping

*Release mode: **single-release** (one committed v1 = epics E1–E4; Growth/Vision are a documented backlog, not committed phases). Every deferral below was approved in Steps 4–7 — nothing user-specified is silently de-scoped.*

### Strategy & Philosophy
**Approach:** **problem-solving MVP** — the minimum that makes the beachhead (P1 conda/pixi maintainer) say "this is useful": a working hygiene + vulnerability gate on the source manifests neither engine parses, behind one honest exit code. **Resource requirements:** small — a stdlib-heavy CLI wrapping two existing engines; the cost center is the E1 extractor + the corpus-conformance rig, not infrastructure.

### Complete Feature Set (v1)

**Core journeys supported in v1:** J1 (conda/pixi wedge), J2 (PyPI unification), J3 (fleet ops), J4 (bypass loop), J5 (machine contract), J6 (adoption on-ramp), J8 (corpus gate), J9 (verdict composition). **Personas served:** P1, P2, P3, P4, M1, P7.

**Must-Have Capabilities (v1):**
- **E1 — manifest bridge:** `recipe.yaml` / `meta.yaml` / `environment.yml` / `pixi.toml` (stdlib-only, two-pass eval, split hygiene/vuln coverage, name-only+marked degrade) + PyPI delegation to the engines' native parsers.
- **E2 / E3 — dual extraction:** deptry (hygiene) + osv-scanner (vuln), via the `_engine_env()` normalization helper (temp-file output, `NO_COLOR`, `stdin=DEVNULL`, utf-8 decode).
- **E4 — honest report + gate:** schema `ComplianceReport` (status / severity / `schema_version` / split coverage / `error_kind`); **verdict-composition** (J9 precedence lattice); **severity gate** (FR5 revised — CVSS-critical default, KEV deferred); **typed errors** (FR10 + FR-NEW-F expanded engine taxonomy); **CycloneDX 1.6 SBOM** (FR8, emitted `experimental`); **false-green guards** (empty-extraction, no-manifest fail-closed, offline-DB-skipped, crashed-engine).
- **FR9** expiring waivers (+ `authorized_by`, untrusted-input trust boundary, D1 YAML-emitter I/O). **FR7** actionability.
- **Cross-cutting NEW FRs:** FR-NEW-A (split coverage), -B (no-meaningful-scan guard), -C (warn-only on-ramp), -D (waiver integrity/authorizer), -E (verdict composition), -F (engine-output shape validation).
- **CLI contract:** single `scan` verb; frozen exit enum `{0,1,2,130}`; dual-TOML config (`pyproject.toml` + `pixi.toml`, per-key precedence); stability-as-behavior (3 contract families); `--version` / `--help`.
- **Offline-first vuln data** + mandatory DB provenance/staleness; **corpus-conformance test** (J8, ratcheted unparseable-rate, NFR3 twice-run).

**Nice-to-Have / Deferred to post-v1** *(all previously approved — re-stated, not newly cut):* KEV gate tier (bundled snapshot) · SARIF output (`--format` value-space reserved) · cf_atlas promotion (FR-16/18) · P6 + J7 compliance-audit retrieval (enterprise) · waiver-at-scale / renewal · per-section (dev/test) severity policy · coverage-floor *default* policy (the `--fail-under-coverage` knob ships v1, default off) · deprecation lifecycle machinery · SBOM schema freeze · alternate hygiene backends (fawltydeps) · fleet/multi-manifest parallelism (engines are parallel in v1) · better conda↔PyPI reconciliation · EPSS.

**Vision (future):** non-Python osv ecosystems · container/artifact scanning · default fleet supply-chain gate · optional external distribution (OD5).

### Risk Mitigation Strategy
- **Technical risk (highest):** the E1 lossy stdlib extractor across six Jinja/selector-laden formats (the "hard 80%" hiding in J1's happy path). *Mitigation:* a per-format supported-construct matrix + the corpus-conformance ratchet (J8); degrade-to-name-only+marked never raises.
- **Market risk:** the wedge is **time-bound** — Trivy/Syft could extend to source manifests. *Mitigation:* the dated competitive spike (re-run pre-release); the **conda dependency-hygiene niche has zero incumbents** and survives even if vuln-bridge parity arrives.
- **Resource / correctness risk:** false-green is catastrophic and asymmetric with false-positive cost. *Mitigation:* the fail-loud posture + the guard suite + a `false-green = 0` fixture gate + the `--warn-only` adoption on-ramp defending the `gate-disabled = 0` anti-metric.

## Functional Requirements

*THE binding v1 capability contract — any capability not listed here will not exist unless explicitly added. Synthesized from the exec summary, success criteria, 9 journeys, domain + innovation + CLI-tool sections, then completeness-stress-tested via advanced-elicitation + a party-mode roundtable (Analyst traceability / Architect connective-tissue / PM scope). The roundtable's decisive finding: the promise is "honest coverage," and coverage is a claim about a **scope** — so the contract now owns the **discovery / routing / reconciliation** capabilities between "a directory exists" and "extract from a manifest," giving coverage a defined denominator.*

> **⚠️ Requirement-ID conventions (read first).** **FR1–FR31 in this section are canonical and binding.** Any `FRn` cited *earlier* in this document (frontmatter `prioritizedRefinements`, journeys, domain, CLI, scoping) is an **intake-spec working label** from an earlier drafting step and is **superseded** by this block. Crosswalk of the colliding labels:
>
> | Working label (narrative) | means | Canonical FR |
> |---|---|---|
> | FR5 | severity/content gate | **FR18** |
> | FR7 | actionability | **FR17** |
> | FR8 | CycloneDX SBOM | **FR27** |
> | FR9 | expiring waiver | **FR24** |
> | FR10 | typed errors | **FR21** |
> | FR11 | recipe two-pass eval | **FR1 / FR3 / FR5 (E1 cluster)** |
> | FR-NEW-A / -B / -C / -D / -E / -F | coverage split / no-scan guard / warn-only / waiver-integrity / verdict-composition / engine-taxonomy | **FR15 / FR22 / FR23 / FR26 / FR20 / FR21** |
>
> **NFR IDs:** the intake-spec `NFR3` = **NFR-R3a** (no-mutation) + **NFR-R3b** (determinism); `NFR5` = **NFR-R2**; `NFR1/NFR2` = **NFR-P\***; `NFR4` = **C0 / NFR-R1**. **`cf_atlas FR-16/FR-18`** (post-v1 atlas promotion) refer to the **atlas's own** requirements — **not** this PRD's FR16 (qualified verdict) / FR18 (severity gate).

### A. Manifest Discovery, Ingestion & Extraction
- **FR1:** Given a target path, the tool can **discover and classify** candidate manifests (`recipe.yaml` / `meta.yaml` / `environment.yml` / `pixi.toml` / `pyproject.toml`), apply a **deterministic selection/precedence policy** across coexisting manifests, and report the **resolved scan set** (the coverage denominator).
- **FR2:** The tool can classify each **dependency source section** (e.g. `pixi.toml` `[dependencies]` vs `[pypi-dependencies]`; `environment.yml` conda deps vs a `- pip:` block) as conda-ecosystem or PyPI-ecosystem and dispatch it to the correct extraction path.
- **FR3:** The tool can extract the declared dependency set from conda/pixi **source** manifests **without a resolved/installed environment**.
- **FR4:** The tool can delegate to each engine's native parser for PyPI-world inputs (`pyproject.toml` PEP621/Poetry/PDM/uv/setuptools, `requirements.txt`, osv-supported lockfiles) rather than re-implementing that parsing.
- **FR5:** The tool can evaluate recipe templating/selector constructs on a **best-effort** basis, producing a partial/degraded extraction (name-only-and-marked) rather than failing.
- **FR6:** The tool can, per manifest, distinguish "**no dependencies present**" from "**dependencies present but not fully resolved**."
- **FR7:** The tool can keep **per-ecosystem attribution** for a dependency appearing in multiple ecosystems and **does not silently merge or dedup** cross-ecosystem names *(full reconciliation deferred post-v1)*.

### B. Dependency-Hygiene Analysis
- **FR8:** A user can obtain dependency-hygiene findings (unused / missing / transitive / misplaced) for a project sourced from PyPI **or** conda-forge.
- **FR9:** The tool can honor a project's existing hygiene-ignore configuration (`[tool.deptry]`).

### C. Vulnerability Analysis
- **FR10:** A user can obtain known-vulnerability findings — advisory ID, affected/fixed version, severity — that are individually actionable.
- **FR11:** The tool can operate against an **offline/air-gapped** vulnerability database, **offline-by-default with no silent network egress**, and record the vuln-data **source + snapshot timestamp**.
- **FR12:** The tool can detect a **stale** vulnerability database (past a threshold) and **degrade the verdict / emit a typed staleness signal** rather than reporting a confident "clean."
- **FR13:** The tool can classify a dependency whose version cannot be resolved as **vulnerability-indeterminate** — distinguishing a **queryable range** from a **genuinely unresolved** spec — never as scanned-clean; and for a **mapped-but-unversioned** dep it can **flag whether the package carries any known critical CVE across any version** (a risk surface + lock-nudge, not a dead coverage number). **Guardrail: coverage improves only by resolving or name-level flagging — never by assuming a version.** *(The `pypi_identity` predicate + bundled conda→pypi map that gate `vuln_matchable` prevent the silent `pytorch`→`torch` false-green — architecture Gap C.)*

### D. Honest Coverage & Reporting
- **FR14:** The tool can produce a **schema-validated** compliance report carrying explicit status, severity, **schema version**, per-manifest coverage, and typed error kind.
- **FR15:** The tool can report coverage as **two distinct dimensions** — hygiene coverage and vulnerability coverage.
- **FR16:** The tool can render a partial-coverage result as a **qualified verdict** — the coverage qualifier is always stated, and the governing status follows the FR20 lattice (partial vuln coverage ⇒ ≥1 `indeterminate` component ⇒ status `indeterminate`, non-zero) — never an unqualified "clean." *(The earlier "clean at N%" phrasing predated `indeterminate` — corrected 2026-07-12.)*
- **FR17:** A user can obtain a human-readable summary and, on request, a machine-readable report, in which **every blocking finding is individually actionable** (package + manifest location + severity-that-tripped + remediation pointer).

### E. Policy Gate & Verdict
- **FR18:** A user can gate a build on report **content + severity**, choosing the failing threshold. The **vuln axis** defaults to block on **critical** CVEs; the **hygiene axis is separate** — **DEP001 (missing dependency) blocks by default** (gated on conda↔pypi name-mapping confidence: high-confidence → block, ambiguous → `warn`), DEP002/3/4 → `warn`. Both policy tables (hygiene→status + CVSS thresholds) live in the FR30 `ConfigLoader`.
- **FR19:** A user can gate on a **minimum coverage floor** (**default OFF**). *(Repurposed 2026-07-12: post-triad, any coverage gap already exits non-zero via `indeterminate`, so the floor's remaining roles are (a) a guardrail **under `--warn-only`** — report-only, but never let coverage regress below N% — and (b) a ceiling on waived-away `indeterminate` surface once waivers apply.)*
- **FR20:** The tool can compose many per-finding outcomes into **one status + one exit code** by a defined precedence in which an **error dominates**, a **waiver suppresses a finding unless expired or error-dominated**, and an **`indeterminate` outcome (withheld/skipped/unresolved) can never be masked by a clean sibling axis**, ingesting coverage-floor, engine-unavailable, and discovery-found-nothing as inputs. *(Precedence lattice `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable` + the separately-derived exit — any error→2, else un-waived policy-violation→1, **else `indeterminate`→exit 1 (pinned 2026-07-12; never a silent 0 — exit 2 stays reserved for operational error)**, else 0 — defined in Journey 9 / architecture.)*
- **FR21:** The tool can **detect required-engine presence + version-compatibility** and distinguish, via **typed error kinds routed to an owner**, the failure classes (unparsable-manifest, engine-unavailable/incompatible, engine-output-unrecognized/-unparseable, engine-execution-failed, engine-timeout, config-error, internal-error) — a missing/incompatible engine **never yields a silent PASS**.
- **FR22:** The tool can treat any run that did **not meaningfully scan** (empty extraction, expected-but-missing manifest, crashed engine, or skipped coverage) as **non-passing, never clean**.
- **FR23:** A user can adopt the gate in a **non-blocking warn-only** mode.

### F. Waivers & Bypass
- **FR24:** A user can record an **auditable, expiring** waiver for a finding (reason, authorizer, expiry) which the tool **reads but never writes into the repository**.
- **FR25:** The tool can **re-block** a finding whose waiver has expired, and flag applied/expired waivers for downstream review.
- **FR26:** The tool can **validate the waiver file against its schema and reject a malformed/malicious one**.

### G. SBOM & Machine Contract
- **FR27:** The tool can emit a **CycloneDX SBOM** with source-registry-correct package URLs and explicit **self-declared partiality** when coverage is incomplete.
- **FR28:** The tool can provide a **stable exit-code contract** (the single, consolidated exit-code semantics for the whole tool).

### H. CLI Operation & Configuration
- **FR29:** A user can run the entire hygiene + vulnerability check as **one non-interactive command** producing one exit code.
- **FR30:** A user can configure per-repo defaults via a `[tool.python-deptry-osv-scanner]` table in `pyproject.toml` **and/or** `pixi.toml`, with CLI flags overriding and **deterministic per-key precedence** (conflicts surfaced, never failing the build).
- **FR31:** A user can discover the tool's version and usage as part of a stable contract.

### Traceability & boundary notes
- **J3 (fleet ops) is satisfied by composition** — N invocations of FR29, with cross-repo aggregation delegated to the CI system — a by-design non-capability, **not** a fleet-aggregation FR.
- **FR9-was-KEV — CUT from v1:** a KEV annotation with no gate delivers no decision value while pulling in the deferred CISA-KEV data source. *Only* if osv-scanner emits a KEV flag **natively at zero new data source** is it passed through as a display-only field under FR10/FR17 — no commitment to sourcing KEV.
- **Requirements deferred to post-v1 (not v1 FRs):** KEV gate tier · **new-findings-only baseline ratchet** (adoption on-ramp — deferred to Growth; FR17 actionability hardening taken now instead) · SARIF output · cf_atlas promotion (FR-16/18) · compliance-audit retrieval (P6/J7) · waiver-at-scale renewal · per-section severity policy · coverage-floor *default* tuning (the `--fail-under-coverage` / `--require-full-coverage` flags ship v1, off) · alternate hygiene backends · EPSS.

### → NFR handoffs (Step 10 will formalize these as non-functional requirements)
Offline-operation *property* (mechanism behind FR11) · noise-free machine-output stream · interface stability / forward-compatibility of the report + SBOM schemas · the "code-review-is-the-integrity-boundary" waiver security assumption (rationale behind FR26) · corpus robustness (**0 uncaught exceptions across ~1,950 recipe files**, ratcheted unparseable rate — proves the E1-cluster / typed-error / no-meaningful-scan FRs across the real distribution, J8) · no-mutation (NFR-R3a) + two-tier determinism (NFR-R3b) · lightweight fleet-scale footprint.

### Architecture open questions (added this step)
1. **Multi-manifest selection precedence** heuristic (FR1) — union-coverage vs a precedence winner when `recipe.yaml` + `pixi.toml` + `pyproject.toml` coexist.
2. **conda range-native version model vs FR13** — deps on the conda path are inherently ranges; define "range-but-queryable" vs "genuinely unresolved" so FR13 doesn't over-fire on every recipe.
3. **Cross-ecosystem dedup key** (FR7/FR27) — the `(ecosystem, name, version)` identity for gating vs SBOM component identity.

## Non-Functional Requirements

*Selective — only categories that matter for a non-interactive CI security gate. **Accessibility is skipped** (no human-UI surface). Completeness/measurability stress-tested via advanced-elicitation + a party-mode threat-model roundtable (security-architecture / testability / adoption). Two guiding reframes landed: **(1)** every security NFR is worded as an **enforced mechanism** (AST denylist, socket guard, line-bound, injected-timeout) rather than an unprovable negative, so each is deterministically assertable; **(2)** the ingress (`re` over untrusted manifests) was already defended — the roundtable closed the two undefended flanks, **egress (output neutralization)** and the **trusted-provisioning path (stale/empty DB)**, both of which sit on the one promise that can't break: never false-green.*

### C0 — Gate-Integrity invariant *(cross-cutting acceptance property)*
**The gate never emits a false-green.** This is not one reliability item among many — it is *the* acceptance property that R1/R2/R5/S8 and exit-code disambiguation all serve. **Metric:** an enumerated adversarial-fixture corpus → **0 fixtures emit exit-0**, covering: stale/empty/swapped DB · engine crash / timeout / missing / version-incompatible · unparseable-but-nonempty manifest · injection attempt · wildcard/over-broad waiver.

### Reliability & Robustness
- **NFR-R1 (corpus robustness):** **0 uncaught exceptions** across the full recipe corpus (~1,950 `recipes/*/{recipe.yaml,meta.yaml}`, globbed at runtime); any unparseable manifest degrades to name-only+marked.
- **NFR-R2 (bounded parse-error budget):** unparseable rate is ratcheted — a **committed baseline number** + corpus; CI enforces **monotonic non-increase** across releases.
- **NFR-R3a (no mutation):** a scan never mutates the scanned tree or host state; cleanup on success *and* failure.
- **NFR-R3b (determinism, two-tier):** **default** = *decision-determinism* — identical inputs + identical DB snapshot ⇒ identical exit code + findings set. **Opt-in** `--deterministic` / `SOURCE_DATE_EPOCH` ⇒ **byte-identical** output, achieved by pinning a **documented volatile-field set** (report/SBOM timestamps, CycloneDX `serialNumber`/`bom-ref`, set-iteration order → sorted, absolute paths → repo-relative, DB-version). *(The opt-in mode is also what makes the SBOM reproducible for downstream/forensics.)*
- **NFR-R5 (engine timeout):** every engine invocation sets a **bounded, configurable subprocess timeout**; `TimeoutExpired` maps to a typed error (FR21) + frozen exit code — never an indefinite hang, never scored as pass. *(Tested via injected fake, not a real sleep.)*

### Security *(each stated as an enforced, testable mechanism)*
- **NFR-S1 (no *execution* of untrusted input — the constraint is no-execution, NOT stdlib-only):** the extraction module **imports no execution primitive** (`eval`/`exec`/`compile`/`__import__`/`os.system`/`subprocess.*`, AST-asserted denylist; subprocess confined to a separate whitelisted engine-runner) and **never renders templates** (`re`-scrape for Jinja recipes, **no `jinja2` import**); **safe parsers are permitted** — `yaml.safe_load` (clean-YAML lockfiles), `tomllib`, `packaging`, `cyclonedx-python-lib` are allowed because they don't execute input. Asserted against a malicious-manifest fixture corpus.
- **NFR-S2 (no silent egress):** the **orchestrator's own process opens no socket** (socket-guard test); all network is confined to the named engine subprocesses; air-gapped mode passes explicit `--offline`/local-DB flags (osv-scanner defaults *online* — an assertion, not a hope).
- **NFR-S3 (waiver untrusted + least-privilege):** the waiver file is schema-validated, expiry enforced against wall-clock, **never executed**; waivers are **least-privilege** (specific vuln-id + package + ecosystem, **no wildcards**) and **every applied waiver is echoed in output** so a broad suppression is review-visible; authorship/integrity delegated to code review + CODEOWNERS.
- **NFR-S4 (no repo writes + secure temp):** no writes into the repository tree; temp artifacts via `mkstemp`/`mkdtemp` (`0600`/`0700`) under the system temp dir (`mkstemp` *is* the symlink/TOCTOU defense).
- **NFR-S5 (ReDoS / resource bound):** extraction is **line-bounded with a per-line byte cap** and a total manifest-size cap `M`; **no compiled pattern contains nested unbounded quantifiers** (static assertion); offline-DB extraction carries a **decompression bound** (zip-bomb). A pathological manifest can never hang or OOM the tool.
- **NFR-S6 (engine-input purity):** the synthesized engine input (requirements projection) is a **pure data projection** — any line starting with `-`, or containing a URL / VCS ref / path / environment-marker we did not author, is rejected or neutralized; manifest-derived values are **never** passed as CLI flags; `shell=True` is banned; DB-extract paths are **zip-slip confined**.
- **NFR-S7 (output neutralization):** every input-derived string (package name / version / description) is emitted **only through a schema-aware JSON/XML encoder** (never string concatenation); purls are canonically percent-encoded per the purl spec; control/escape chars are stripped — so a malicious component string cannot make the tool a confused-deputy injection vector against a downstream SBOM/dashboard consumer. Property-tested over an adversarial name/version corpus (`</script>`, JSON/XML metachars, ANSI, 10 KB names).
- **NFR-S8 (trusted-input integrity):** engines + vuln DB must be **present, fresh (bounded max-age), and authentic (checksum / known-good)** before a verdict is trusted; a stale/empty/swapped/unverifiable DB → **fail-loud, never green** (the security twin of FR12).

### Performance & Footprint *(measurable = named corpus + reference hardware + percentile)*
- **NFR-P-warm (our overhead):** the extraction + orchestration + report overhead the tool adds *on top of the engines* is **≤ ~2s p95** on a median repo over the pinned reference corpus, **measured with engines stubbed** (engine scan time scales with dep count and is not ours to promise). Gated on p95/median over N runs, never a single run.
- **NFR-P-cold (first-run DB):** the first-run vuln-DB provisioning is a **one-time, cacheable** cost with a **documented DB size + cache-key contract** so runs #2..N are warm; air-gapped mode = **pre-provisioned DB, zero network, fail-loud if absent**. Cold-start is amortizable, not per-run.
- **NFR-P-concurrency:** the two engines run **in parallel** (independent); the tool holds **no shared mutable state / no global lock**; per-invocation cost is **O(project), independent of fleet size** *(absorbs the deleted standalone "fleet-scale" NFR — fleet orchestration is the CI platform's job)*.

### Interoperability & Contract
- **NFR-I1 (schema conformance):** the report validates against its committed JSON schema; the SBOM validates against **CycloneDX 1.6**; purls conform to the purl spec.
- **NFR-I2 (minimal contract stability):** the report + SBOM carry a **schema-version field** and the exit-code enum is a **frozen closed set `{0,1,2,130}`**. *(Full forward-compat/migration machinery is deferred — no external consumers in single-release v1.)*
- **NFR-I3 (machine-output purity):** in machine mode, stdout is a **single valid document or empty** — never contaminated by diagnostics (→ stderr).

### Usability & Adoption *(the anti-metric lens — a disabled gate scans nothing)*
- **NFR-U1 (actionable diagnostics):** every non-zero exit emits a deterministic, human-readable explanation naming the **offending package(s)**, the **finding** (advisory id + severity + fixed-version, or the hygiene rule), the **source manifest + location**, and a **remediation path** (upgrade-to / how-to-file-a-time-boxed-waiver) — actionable without reading engine internals. *("Fail with a fix, not just a red X.")*
- **NFR-U2 (safe-by-default + on-ramp):** the zero-config default is the **secure** one (fail on critical, expiring waivers, unknown/incompatible engine → fail-loud, air-gap explicit), **paired** with the documented warn-only adoption on-ramp (FR23) so a repo's pre-existing debt doesn't trigger a day-one mass-disable. *(The fuller baseline-bootstrap = the deferred Growth ratchet.)*

### Portability / Compatibility
- **NFR-C1:** runs on **Python ≥ 3.12**; requires deptry + osv-scanner on PATH within a **tested version range** and **fails loud when an engine is out-of-range** (guarding against silent output-schema drift — the engine comes from the feedstock, so a range, not an exact pin); requires **pixi ≥ 0.72.2** for the pixi path; conda + wheel + sdist build green.

*Cut/deferred this step: standalone "fleet-scale" NFR (folded into NFR-P-concurrency) · broad observability/telemetry (kernel → NFR-U1) · forward-compat migration machinery (trimmed to NFR-I2). Accessibility skipped.*

## Architecture Open Questions (consolidated)

*Single source of truth for the next phase — consolidates the open-question fragments that were scattered across the Domain, CLI-Tool, and Functional-Requirements sections. Split into **resolved v1 assumptions** (recorded — do not relitigate) and **genuinely-open** decisions the architect must make. Ordered by how much of the v1 build sits on top of them.*

### Resolved v1 assumptions (recorded — do not relitigate)
- **Coverage-floor default = OFF** — `--fail-under-coverage` / `--require-full-coverage` ship v1 but default off (protects first-run adoption).
- **Waiver integrity boundary = git + CODEOWNERS** — the tool treats the waiver file as untrusted input, enforces expiry, and emits an audit record; it does not verify authorship (NFR-S3).
- **Multi-environment deps = provenance-now, policy-later** — v1 extracts all resolvable sections, tags each dep with its source environment, and applies one uniform severity policy; per-section severity is deferred.
- **No-manifest polarity = fail-closed-when-Python-present**; `--allow-empty` downgrades for monorepo sweeps (D2).
- **KEV = deferred post-v1, annotation-only** in v1 (no CISA-KEV data source committed).

### Open — architect must decide (blocking items first)
1. **[Gap A — sharpest] deptry-severity → verdict-lattice mapping.** deptry hygiene findings carry no CVSS; decide whether a hygiene finding can reach `policy-violation`/exit-1 or is capped at `warn`. The two models yield **different exit-code state machines**, and FR20 / E4 (the report engine) sit directly on top of this. *Recommended default for the architect to confirm: hygiene is a **separate `warn`-axis**, not an input to the severity gate.*
2. **[Gap B] ComplianceReport ↔ CycloneDX shared-inventory model.** One artifact or two (CLI implies two: `--output` + `--sbom-output`); embedded / referenced / independent; do findings **and** SBOM components key off one **resolved-inventory** object? ("BOM component count == resolved-inventory count" implies a shared object that is never named as a first-class model.) Define it — it is the spine of E4.
3. **[Gap C] osv input contract + offline-DB provisioning.** What osv-scanner does with a **name-only / range** dependency (fed-and-dropped vs withheld-and-marked `vulnerability-indeterminate`, FR13); where the offline OSV DB lives; how it is provisioned; the snapshot-timestamp source; and the checksum / trust anchor (NFR-S8). *(OD2 — the #1 complexity hotspot; fully deferred today.)*
4. **Multi-manifest selection precedence** (FR1) — union-coverage vs a precedence winner when `recipe.yaml` + `pixi.toml` + `pyproject.toml` coexist (distinct from FR30's config-key precedence).
5. **conda range-native version vs FR13** — define "range-but-queryable" vs "genuinely unresolved" so FR13 does not over-fire on every recipe.
6. **Cross-ecosystem dedup key** (FR7 / FR27) — the `(ecosystem, name, version)` identity for gating vs SBOM component identity; `pkg:conda?channel=` channel-qualifier semantics.
7. **`--offline` vs `--offline-vulnerabilities`** for the air-gapped path (the transitive-resolution egress leak); DB-staleness threshold + timestamp source; osv-scanner feedstock **version range** to pin (NFR-C1).
8. **Fuzzy constraints to pin.** (a) **pixi ≥ 0.72.2 runtime role** — does the tool ever *invoke* pixi (e.g. to read `pixi.lock`), or is 0.72.2 a build/dev-env floor mislabeled as a runtime constraint? NFR-S1 forbids subprocess in the extractor, so state which. (b) **Offline cold-start default** on a non-air-gap machine — fetch / warn / fail? (air-gap is "fail-loud if absent"; the default path is unstated). (c) **Waiver write-target** — the `--bypass` stanza is emitted to **stdout for the human to commit**, *not* written into the repo tree by the tool (reconciles FR24 / NFR-S4 "never writes the repo" with D1's read/write path).
9. **Waiver-file in-file `version:`** + unknown-version rejection; **`--reason` YAML-lib runtime-dep** scope vs the "lightweight" positioning (D1).
10. **FR21 error-kind granularity** — reconcile the FR's `config-error` with the CLI section's `config-parse` vs `config-validation`.

### Owners still to assign (from traceability review)
- **Per-format supported-construct matrix** (J8) — declared as the thing "without which coverage is undefined per format," currently lives only in Risk-Mitigation prose; give it an owning FR/NFR or an explicit architecture deliverable.
- **`environment.yml` / `pixi.toml` corpus ratchet** — the six-formats claim is corpus-ratcheted (NFR-R1/R2) only for `recipe.yaml` + `meta.yaml`; these two are "sampled" with no baseline.
- **FR30 dual-config robustness** — config-key precedence-determinism / conflict-surfacing / forward-compat live only as CLI-section prose ACs; NFR-I2 scopes stability to report + SBOM + exit-enum, not the config-key input contract.
