---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
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
    - "FR5 (severity-tiered gate): exit 0/1/2; --fail-on=<severity> or max_critical/max_high/KEV; default block on critical CVE or KEV-affecting-current, warn on high/med/low + all hygiene. Retires coarse --no-fail-on-*. Gate decides on report CONTENT + severity, never subprocess returncode"
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
---

# Product Requirements Document - python-deptry-osv-scanner

**Author:** rxm7706
**Date:** 2026-07-11

## Executive Summary

**python-deptry-osv-scanner** is a non-interactive CI/CD quality-gate CLI that unifies **dependency hygiene** (unused / missing / transitive deps via `deptry`) and **known-vulnerability scanning** (CVEs via Google `osv-scanner`) into a single schema-validated pass behind **one exit code**, for **Python libraries sourced from either PyPI or conda-forge**. For PyPI-world projects both engines already work natively — deptry reads `pyproject.toml` (PEP 621 / Poetry / PDM / uv / setuptools) and `requirements.txt`; osv-scanner reads the lockfiles (`poetry.lock`, `pdm.lock`, `uv.lock`, `Pipfile.lock`, `pylock.toml`, `requirements.txt`) — so python-deptry-osv-scanner **orchestrates and unifies** them. Its differentiated wedge is **extending both engines to the conda/pixi formats neither parses natively** — `environment.yml`, v0 `meta.yaml`, v1 `recipe.yaml`, and `pixi.toml` — via a manifest-resolution bridge, making conda-forge-sourced Python projects first-class alongside PyPI ones. (See § Supported Dependency Managers & Lockfiles.)

The tool is **ecosystem-agnostic**: one gate whether a project's dependencies resolve from PyPI or conda-forge. The segment with the sharpest *unserved* gap is **conda-feedstock and pixi-project maintainers** — who today cannot run either engine without a lossy manual translation of their recipe/manifest into a `requirements.txt` fiction (the majority still on v0 `meta.yaml`) — but the product serves **any Python developer shipping pip- or conda-sourced software** (scripts, applications, components, libraries). Platform-engineering and DevSecOps teams are **distribution channels** (who deploy the gate across a 20,000+ repo fleet). The irreducible promise: **one exit code you can trust, with honest coverage.**

### What Makes This Special

**Core insight:** both jobs begin at the same manifest parse. python-deptry-osv-scanner builds **one conda/pixi-native manifest front-door feeding two independent extraction paths** — deptry's (source-tree AST + import→distribution mapping; versions ~irrelevant) and osv-scanner's (versioned lockfiles; name-only is last resort) — and emits one consolidated, schema-validated `ComplianceReport`.

Differentiators: (1) conda/pixi-native resolution across six manifest formats including both v0/v1 conda recipes — the wedge the individual tools lack (the hero; unification is the *byproduct* of parsing once); (2) one gate / both signals / one exit code; (3) fleet-scale and **lightweight at runtime** — stdlib-only extraction (`tomllib` + `re`), idempotent, cheap enough to be a default gate; (4) an **honest, actionable contract** — the report carries an explicit `status` (`error | findings | clean`) and per-manifest coverage, so "clean" never renders identically to "we only parsed what we could," and findings gate on **report content, never a subprocess exit code**.

*Competitive note (time-bound):* the wedge rests on a snapshot of two fast-moving upstream tools (osv-scanner's lockfile list grows per release; Trivy owns the "one CLI / one gate" shape) — to be validated by a dated competitive spike, not asserted as an evergreen gap.

## Project Classification

- **Type:** `cli_tool` — a non-interactive CI/CD policy/quality-gate CLI (primary consumer = pipeline). `report-schema.json` is the data contract (an output_formats concern); no public SDK/IDE surface.
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

- A **Python developer shipping pip- or conda-sourced software (scripts, applications, components, libraries)** — whether deps come from PyPI or conda-forge — runs `python-deptry-osv-scanner` once and gets a unified hygiene + vulnerability verdict. PyPI projects: deptry + osv consolidated (no more two CI steps + `jq`). Conda/pixi projects: coverage they had **none** of before (no manual `requirements.txt` translation).
- Every finding is **actionable** (package + manifest location; or advisory ID + affected/fixed version); no theoretical noise.
- A **platform engineer** wires it into a CI template once — deterministic exit 0 / non-zero across the fleet.
- **Trust:** a green check never hides a crash or an unparsed manifest.

### Business Success

- **3-month:** gate on local-recipes CI + N pilot Python projects (PyPI- and conda-sourced). Metric: ≥ 98% of the repo's own conda recipes scan without an `error` status.
- **12-month:** promoted into cf_atlas (FR-16/FR-18); default fleet gate. False-positive rate low enough teams don't disable it.
- **Anti-metric:** gate-disabled events (false-green / false-red storm) → **target 0**.

### Technical Success

- **PyPI path:** correct **delegation** — deptry consumes `pyproject.toml`/`requirements.txt`, osv-scanner consumes the native lockfile (`poetry.lock`/`uv.lock`/`pdm.lock`/`Pipfile.lock`/`pylock.toml`/`requirements.txt`); no bespoke parsing; results unified.
- **Conda/pixi path (E1 bridge):** corpus-conformance — **0 uncaught exceptions** across all `recipes/*/{recipe.yaml,meta.yaml}` (~1,950 real files as of 2026-07-11; globbed at runtime) + sampled `environment.yml`/`pixi.toml`; unparseable rate **< 2%**, surfaced per-manifest.
- **Honest contract + severity gate:** schema-validated; `status ∈ {clean, warnings, policy-violation, error, bypassed, not-applicable}`; **severity-tiered exit 0/1/2** (default block on critical CVE / KEV, warn on the rest); typed `error_kind` (unparsable-manifest → developer, engine-unavailable → platform, internal-error → CLI maintainers); the gate decides on report **content + severity**, never a subprocess returncode.
- **Auditable bypass:** `--bypass` emits a committed, **expiring** waiver (default 14d; config + per-repo override); exits 0 with `status: bypassed` + `review_required: true`; the tool never writes the repo (NFR3). An **expired** waiver re-blocks.
- **SBOM:** a **CycloneDX BOM** is emitted and validates against the committed CycloneDX schema; components carry correct purls (`pkg:pypi/…` vs `pkg:conda/…?channel=`); a **partial** BOM when coverage < 100%.
- **Idempotency (NFR3):** twice-run byte-identical; no host/source mutation; cleanup on success + failure.
- **Lightweight (NFR1/NFR2):** stdlib-only bridge; cheap concurrent 20k-repo runs. Conda + wheel + sdist build green.

### Measurable Outcomes

- PyPI path: 100% correct delegation on fixtures (both engines consume native inputs; report unifies).
- Conda/pixi path: parse coverage ≥ 98% on the recipe corpus (~1,950 files, 2026-07-11; globbed at runtime); 0 uncaught exceptions; twice-run byte-identical.
- Exit-code matrix 100% correct across severity tiers (clean/warn → 0, policy-violation → 1, error → 2) + each typed `error_kind`; **false-green = 0** on seeded fixtures; a **non-expired waiver → exit 0** (`bypassed`, `review_required`) and an **expired waiver → re-block (exit 1)**; report schema-valid in CI (100%).
- Emitted **CycloneDX BOM validates against schema** in CI (100%); purls correct on the fixture set; **BOM component count == resolved-inventory count** (no silent drops).

## Product Scope

### MVP - Minimum Viable Product (v1)

**PyPI path:** orchestrate deptry (native pyproject/requirements) + osv-scanner (native lockfile) → unified `ComplianceReport` + gate. **Conda/pixi path (E1 bridge):** extract deps from `environment.yml`/`meta.yaml` (v0)/`recipe.yaml` (v1)/`pixi.toml` (stdlib-only, two-pass eval, name-only+marked, per-manifest coverage); synthesize `requirements.txt` for deptry + version-pinned reqs for osv (from `pixi.lock`/conda else name-only). **E4:** schema-validated `ComplianceReport` (`status` + severity + `schema_version` + coverage + `error_kind`) + human summary + **severity-tiered exit-gate** (FR5: 0/1/2; `--fail-on` / `max_critical`/`max_high`/KEV; default critical+KEV blocks) + typed errors (FR10) + an **auditable expiring bypass** (FR9: `--bypass` → committed waiver, default 14d / config / per-repo, `review_required`); **emit a schema-validated CycloneDX SBOM (FR8 — correct purls, coverage-marked)**. Corpus + fixture tests; conda/wheel/sdist build; respect `[tool.deptry]` ignores.

### Growth Features (Post-MVP)

cf_atlas promotion (FR-16/FR-18 MCP tool + pixi CLI) · vuln-side waiver · surface more osv-native lockfiles · better conda↔PyPI name reconciliation · alternate hygiene backends (`fawltydeps`, `pip-check-reqs`) via `--engine` · parallel execution.

### Vision (Future)

Non-Python osv ecosystems + container/artifact scanning · default fleet supply-chain gate / the atlas's authoritative signal · optional external distribution (PyPI/conda-forge, OD5).
