---
status: ready
spec_updated: 2026-07-11
---
# Tech Spec: `python_deptry_osv_scanner` — Python dependency-hygiene + vulnerability gate

> **BMAD intake document.** A unified dependency-hygiene + vulnerability
> scanner that orchestrates `deptry` and Google's `osv-scanner` over
> Python / Conda / Pixi manifests. Written to be self-contained: it folds
> the Analyst brief, PM PRD, Architect design, and story sharding into one
> file as the self-contained source of truth for the **full BMAD** chain.
>
> The full BMAD planning chain (PRD → architecture → epics/stories → dev)
> runs against this spec under the `python-deptry-osv-scanner` BMAD project
> (`_bmad-output/projects/python-deptry-osv-scanner/`).
>
> Scope is ~4 epics (E1–E4) / ~12–16 stories, driven through the **full
> BMAD** flow (not Quick Flow).
>
> **Conda-forge tie-in (Rules 1 & 2).** If the effort packages
> `python_deptry_osv_scanner` (or any of its scanning engines) as a conda recipe, or
> touches anything under `recipes/`, the executing agent **must** invoke the
> `conda-forge-expert` skill first (CLAUDE.md Rule 1) and close with a
> CFE-skill retrospective + CHANGELOG entry (Rule 2). Pure library/CLI work
> that never touches `recipes/` is exempt from those two rules.
>
> **Scope & naming (Python-only, by design).** This tool covers **Python
> dependency hygiene + vulnerability scanning only** — the six Python/conda
> manifest formats (`pyproject.toml`, `requirements.txt`, `environment.yml`,
> `meta.yaml`, `recipe.yaml`, `pixi.toml`). Non-Python ecosystems (npm, Go,
> Rust, Java, …) are **out of scope** and yield a `not-applicable` result
> (osv-scanner *could* cover many of them, but this tool deliberately does
> not). The filename encodes a deliberate **family convention** —
> `<language>-<hygiene-engine>-<vuln-engine>` — so sibling specs can adopt
> the same orchestration pattern per language, swapping `deptry` for that
> language's hygiene tool while typically keeping `osv-scanner` (which is
> multi-ecosystem) as the shared vuln engine — e.g. a future
> `js-depcheck-osv-scanner.md` or `go-<tool>-osv-scanner.md`.

---

## Status

| Field | Value |
|---|---|
| Status | **In progress** — full BMAD planning underway (PRD stage); all decisions resolved (§ Decisions) |
| Scope | **Python only** — PyPI + conda-forge, 6 Python/conda manifest formats; non-Python ecosystems out of scope (see § Scope & naming in the intake note) |
| Owner | rxm7706 |
| Track | **Full BMAD** (PRD → architecture → epics/stories → dev) — planning artifacts under `_bmad-output/projects/python-deptry-osv-scanner/` |
| Proposed project slug | `python-deptry-osv-scanner` (BMAD artifacts → `_bmad-output/projects/python-deptry-osv-scanner/`) |
| Python package | module `python_deptry_osv_scanner`; dist name `python-deptry-osv-scanner` |
| Source root | **In-repo pixi *build* workspace member** at `src/shared/packages/python-deptry-osv-scanner/` (Option B; unity-data-stack `src/shared/packages` convention) — see § Repository layout |
| Target users | Platform Engineers (CI/CD), DevSecOps Engineers (compliance / SBOM), and **Python developers shipping pip- + conda-sourced software of any shape** (scripts, applications, components, libraries) |
| Distribution | **Internal-first library** (v1); PyPI/conda-forge packaging decided at closeout (OD5) |
| Lifetime | Long-running CI/CD quality gate |

---

## Background and Context

### The problem (Analyst brief)

Managing dependency hygiene and security compliance across
enterprise-scale infrastructure requires disjointed tools. Developers and
security teams currently run separate pipelines for unused-dependency
detection (`deptry`) and vulnerability scanning (`osv-scanner`), which
creates friction — especially in complex environments heavily utilizing
Conda and Pixi, where — **as of 2026-07-11** — neither tool natively
understands those manifests (§ Engine-native support; time-bound, re-verify).

**Target users**

- Platform Engineers managing CI/CD pipelines.
- DevSecOps Engineers tracking organization-wide software compliance and SBOM data.
- **Python developers** who build and ship pip- *and* conda-sourced Python
  of any shape — scripts, applications, components, and libraries alike.

**MVP idea.** A unified Python CLI (`python_deptry_osv_scanner`) that orchestrates
both `deptry` and Google's `osv-scanner`. It resolves manifests across the
six formats (`pyproject.toml`, `requirements.txt`, `environment.yml`,
`meta.yaml` v0, `recipe.yaml` v1, `pixi.toml`), detects unused
dependencies in the codebase, and checks the resolved dependency tree for
known vulnerabilities against the OSV database.

### Where this sits in THIS repo (prior art — read before building)

This spec is not authored in a vacuum. Three facts materially shape it:

1. **The scanning engines are already on conda-forge and mirrored locally.**
   `osv-scanner` (v2.4.0, Apache-2.0 Go binary — `conda-forge/osv-scanner-feedstock`,
   recipe.yaml) and `deptry` (`conda-forge/deptry-feedstock`, meta.yaml v0)
   both ship on conda-forge today. As of 2026-07-10 the tree also carries
   freshly-authored local recipes for the dep-hygiene family:
   `recipes/deptry/` (a v0→v1 migration of the feedstock, v0.25.1),
   `recipes/fawltydeps/` (v0.20.0), and `recipes/pip-check-reqs/` (v2.5.6).
   → **Provisioning `osv-scanner` should be a declared conda/pixi
   dependency, not a runtime `curl` fetch** (resolves the NFR3 tension the
   source design left open — see OD1).

2. **The repo already ships overlapping capability.** The
   `conda-forge-expert` skill exposes `scan-project` and
   `scan_for_vulnerabilities` (MCP + CLI), backed by
   `reference/dependency-input-formats.md` — the canonical "what does
   `scan_project` accept?" matrix (manifest / lock-file / SBOM / container
   inputs). `python_deptry_osv_scanner` partially re-implements that surface. Whether
   it should be a standalone external tool or reuse/extend the existing
   infra is an explicit decision (OD4), not a silent one.

3. **`fawltydeps` and `pip-check-reqs` are adjacent alternatives** to
   `deptry` for the unused-dependency job. The MVP picks `deptry` as the
   hygiene engine; the other two are candidate future backends (§ Future).

---

## Goals

- **G1.** One CLI (`python_deptry_osv_scanner`) that produces a single consolidated
  hygiene + security report from one invocation at a repo root.
- **G2.** Native, zero-heavy-parser manifest resolution across the six
  formats: `pyproject.toml`, `requirements.txt`, `environment.yml`,
  `meta.yaml` (v0), `recipe.yaml` (v1), and `pixi.toml`.
- **G3.** Act as a strict CI/CD quality gate: non-zero exit when unused
  deps **or** vulnerabilities are found.
- **G4.** Machine-readable JSON for programmatic consumption **and**
  human-readable stdout for CI logs.
- **G5.** Idempotent: never mutate host env or source; clean up all
  ephemeral files even on failure.
- **G6.** Lightweight enough to run concurrently across a 20,000+ repo
  fleet without excessive compute/memory overhead.

**Non-goals (v1).** Auto-fixing/removing unused deps; resolving/pinning
transitive version trees itself (the engines do that); replacing the repo's
existing `scan-project` intelligence layer; non-Python `osv-scanner`
ecosystems (npm / Go / Rust / …) and its container/artifact scanning
(Python across PyPI + conda-forge only). Note: PyPI lockfiles (`poetry.lock`
/ `pdm.lock` / `uv.lock` / `Pipfile.lock` / `pylock.toml`) ARE covered via
`osv-scanner`'s native delegation (§ Engine-native support), and **CycloneDX
SBOM emission is a v1 deliverable (FR8), not a non-goal** (owner-elevated
2026-07-11).

---

## Requirements (PM PRD)

### Functional Requirements

- **FR1.** Detect and parse `pyproject.toml`, `requirements.txt`,
  `environment.yml`, **`meta.yaml` (v0 conda recipe)**, `recipe.yaml`
  (v1 conda recipe), and `pixi.toml` automatically based on the execution
  directory. (`meta.yaml` is the *more common* conda recipe format —
  ~1,040 vs ~910 `recipe.yaml` in this repo as of 2026-07-11 — so it is
  prioritized in E1's fixtures; scope is Python across PyPI **and**
  conda-forge, not conda feedstocks only.)
- **FR2.** Execute `deptry` to identify declared-but-unused dependencies,
  parsing its output into a structured format.
- **FR3.** Execute `osv-scanner` against the resolved dependency set to
  identify known CVEs/advisories.
- **FR4.** Emit a **consolidated report in two parallel forms**: a
  machine-readable `ComplianceReport` JSON (for programmatic CI/CD
  consumption) **and** a human-readable summary (for CI logs), covering
  hygiene (unused) + security (vulnerable) findings. The JSON carries the
  gate contract: `status` (`clean` | `warnings` | `policy-violation` |
  `error` | `bypassed` | `not-applicable`), per-finding **severity** (CVSS
  + KEV for CVEs; hygiene defaults to `warning`), per-manifest **coverage**,
  `error_kind` (FR10), and `review_required` / `bypass` (FR9).
- **FR5.** **Severity-tiered CI gate.** The exit code encodes the policy
  result, not a binary pass/fail: **0** = clean, or only findings *below*
  the fail-threshold (reported as **warnings**, non-blocking), or an audited
  `--bypass` (FR9); **1** = ≥1 finding *at/above* the threshold
  (**policy-violation** → blocks merge); **2** = operational **error**
  (FR10; non-relaxable except via the audited bypass). The **fail-threshold
  is configurable** — `--fail-on=<severity>`, or the atlas FR-18 knobs
  `max_critical` / `max_high` / KEV. **Default: block on any critical CVE or
  KEV-affecting-current; warn on high/medium/low + all hygiene.** This
  replaces a hard "any finding blocks" gate, which drives teams to disable
  the gate entirely (the NFR1 anti-goal).
- **FR6.** The JSON report is **validated against a committed
  `report-schema.json`** (JSON Schema); a `validate_report.py` validator
  ships alongside it (the analogue of Cloudflare's `validate-findings.cjs`
  — § References). A report that fails schema validation is itself a hard
  error, so the output contract can't silently drift.
- **FR7.** **Actionable findings only.** Every emitted finding carries
  concrete, attributable context — the offending package + manifest
  location for hygiene; the advisory ID + affected version + fixed version
  for security. Non-applicable / purely theoretical noise is suppressed —
  the "only report what you can act on" discipline borrowed from the
  Cloudflare harness (§ References), which keeps the gate's false-positive
  rate low at fleet scale (NFR1).
- **FR8.** **Emit a CycloneDX SBOM (v1).** The resolved dependency inventory
  is emitted as a valid CycloneDX BOM (JSON) — components carry correct purls
  (`pkg:pypi/<name>@<version>`, `pkg:conda/<name>@<version>?channel=<ch>`) and
  the same per-manifest coverage marking as the report (a *partial* BOM when
  coverage < 100%, never a silently-complete-looking one). Emission is
  stdlib-only (NFR2), validated against a committed CycloneDX schema, and
  follows the repo's `cyclonedx-universe-inventory` purl conventions + the
  kedro migration's CycloneDX normalization (FR-17). Optional synergy: the
  emitted BOM can feed `osv-scanner`'s SBOM-scan path.
- **FR9.** **Auditable, expiring bypass (waivers-as-code).** A break-glass
  risk-acceptance path so application teams can merge and proceed without a
  silent `--force`. `--bypass --reason "<why>" [--owner --ticket --expires
  <days>]` emits a **waiver stanza** (scope/selector, reason, owner, ticket,
  `accepted_at`, `expires_at`) the team commits to a tracked
  `.python-deptry-osv-scanner-waivers.yaml`; the tool **reads** it and never
  writes the repo (NFR3 intact). While a matching waiver is non-expired the
  gate exits **0** with `status: bypassed`, the bypassed findings listed, and
  **`review_required: true`** — routed to the security-engineer queue at the
  fleet/atlas layer (the per-repo tool only *emits* the flag). A bypass is
  **loud and recorded** (the opposite of a false green), which is why it may
  also override an `error` (FR10). **Expiry: default 14 days**, overridable
  at acceptance (`--expires`), by a global config default (set
  independently), and **per-repository**; on `expires_at` the waiver stops
  suppressing and the finding **re-blocks** until reviewed / fixed /
  re-accepted.
- **FR10.** **Typed error states (exit 2), each with an owner.** When the
  scan cannot complete reliably, `status: error` carries an `error_kind` so
  the failure is actionable by the right audience:
  - `unparsable-manifest` — a manifest is present but can't be parsed
    (malformed TOML/YAML, non-degradable Jinja); the report names the file +
    location. **Owner: the developer** (clean up the manifest / repository).
  - `engine-unavailable` — `deptry`/`osv-scanner` not on `$PATH`; names the
    missing binary. **Owner: platform / CI** (fix the runner image).
  - `engine-crash` — an engine ran but failed unexpectedly (not a findings
    exit); surfaces the engine's stderr.
  - `internal-error` — an uncaught exception in this tool itself; emits a
    diagnostic (traceback + bug-report pointer). **Owner: the CLI
    maintainers** (a tool bug).

  Distinct from **`not-applicable`** (no supported/Python manifest found) —
  **benign, exit 0**, never an error — so non-Python repos in a fleet don't
  masquerade as failures. Errors are observable across the fleet by
  `error_kind` (NFR4).

### Non-Functional Requirements

- **NFR1 — Scalability.** Lightweight enough to run concurrently across a
  20,000+ repository CI/CD fleet without excessive compute or memory
  overhead.
- **NFR2 — Zero-heavy-parser extraction.** Manifest parsing for Conda and
  Pixi relies on the Python standard library (`tomllib`, `re`) — no
  `pyyaml` or other heavy parsers added to the runner. (See OD3: this is
  in tension with robust `environment.yml` / Jinja-bearing `recipe.yaml`
  parsing; the tension is called out, not hand-waved.)
- **NFR3 — Idempotency.** The scanner must not modify the host environment
  or source code. All intermediate ephemeral files are cleaned up
  post-execution (enforced via `try/finally`).

---

## Epics

| Epic | Title | Description |
|---|---|---|
| **E1** | Manifest Resolution Engine | Dynamically detect and extract dependencies from standard, Conda, and Pixi manifests natively (stdlib-only). |
| **E2** | Deptry Integration | Wrapper logic to drive `deptry` over the project and capture structured violations. |
| **E3** | OSV-Scanner Integration | Feed each project's native lockfile (PyPI) or a synthesized version-pinned requirements file (conda/pixi) into `osv-scanner` and parse vulnerability data (OD2). |
| **E4** | Unified Reporting & CLI | `argparse` CLI + schema-validated `ComplianceReport` JSON **and** human report consolidating E2 and E3, with the CI exit-code gate. |

---

## Architecture (Architect design)

### Technology stack

- **Language:** Python 3.12+ (built-in `tomllib` for `pyproject.toml` /
  `pixi.toml` parsing). A deliberate **3.12** baseline — one minor above the
  repo's conda-forge `python_min` floor (G40/G41 — 3.11).
- **CLI framework:** `argparse` (stdlib) — chosen over Typer/Click to keep
  third-party deps limited strictly to the scanning engines.
- **Core dependencies:** `deptry` (Python package) and `osv-scanner` (Go
  binary invoked via `subprocess`). **Both are provisioned as declared
  conda/pixi dependencies** (both live on conda-forge) — see OD1.
- **Data format:** a `ComplianceReport` JSON validated against a committed
  `report-schema.json` for CI/CD consumption, plus a structured
  human-readable summary on stdout. See § Report architecture below.

### Repository layout (Option B — pixi build workspace member)

The library lives **in-repo** as a first-class member of the root
`staged-recipes` pixi workspace, under `src/shared/packages/` — the
`unity-data-stack` monorepo convention for shared, cross-cutting libraries
(sibling of its `src/shared/packages/common`; ADR-005). All deployable source
lives under `src/`; `recipes/`, `docs/`, `scripts/` stay outside it. This
aligns with the kedro migration's pixi-first / conda-forge-only end-state
(FR-15).

**Three artifacts from one source (Option B).** A single hatchling
`pyproject.toml` is the only Python build backend; `pixi` produces all three
distribution artifacts from it:

| Artifact | Tool | pixi task |
|---|---|---|
| conda package (`.conda`) | `pixi-build-python` (wraps the hatchling wheel) | `python-deptry-osv-scanner-build-conda` |
| pypi wheel (`.whl`) | `python -m build` (hatchling) | `python-deptry-osv-scanner-build-dist` |
| sdist (`.tar.gz`) | `python -m build` (hatchling) | `python-deptry-osv-scanner-build-dist` |

`python-deptry-osv-scanner-build` runs all three; the path dependency also builds+installs
the conda package into the dev env on `pixi install`.

```
local-recipes/
├─ pixi.toml                          # root [workspace]; preview = ["pixi-build"];
│                                     #   [feature.python-deptry-osv-scanner.*] + lean env + build tasks
├─ src/
│  ├─ sentinel/                       # existing in-repo app (wiki/knowledge)
│  └─ shared/packages/python-deptry-osv-scanner/ # the workspace MEMBER (no [workspace] table)
│     ├─ pixi.toml                    #   [package] + [package.build.backend]=pixi-build-python
│     ├─ pyproject.toml               #   hatchling; entry point python_deptry_osv_scanner.cli:main
│     ├─ src/python_deptry_osv_scanner/          #   E1 extractor.py · E2/E3 runners · E4 report.py + cli.py
│     ├─ report-schema.json           #   FR6 (E4)
│     └─ tests/
└─ docs/specs/python-deptry-osv-scanner.md
```

- **Runtime engines** (`deptry`, `osv-scanner`) are the member's conda
  `[package.run-dependencies]` (OD1) — never pip, never runtime `curl`.
- **Dedicated lean env**: `[environments] python-deptry-osv-scanner` uses
  `no-default-feature = true`, so it excludes the repo's fat default toolchain
  (python 3.14 + pixi + conda + pip + uv) and carries only the built package +
  its run-deps + build/test tooling (NFR1/NFR2). Tasks: `python-deptry-osv-scan`,
  `python-deptry-osv-scanner-test`, `python-deptry-osv-scanner-build{,-conda,-dist}`.
- **Preview flag**: the workspace opts into `preview = ["pixi-build"]` (still
  experimental in pixi); it only unlocks the `[package]`/build tables and does
  not affect the rattler-build recipe workflow.
- **Right-sizing**: local-recipes adopts only `src/shared/packages/` now
  (`src/apps/`, `src/platform/` as needed); it does **not** import unity's
  `tech-domains/` apparatus (`DOMAIN.md`, `data_product.yaml`, 15 domains) —
  that targets a multi-team data platform, not a recipe factory.

### Manifest extraction targets (E1 detail)

The extractor returns a de-duplicated, base-package-filtered `List[str]`
of dependency names (v1) — filtering out `python`, `pip`, and other
base/virtual packages. Per-format targets:

| File | Extract from | Parser |
|---|---|---|
| `pyproject.toml` | `[project].dependencies` (PEP 621) and/or `[tool.poetry.dependencies]` | `tomllib` |
| `pixi.toml` | `[dependencies]`, `[pypi-dependencies]`, `[feature.*.dependencies]` | `tomllib` |
| `requirements.txt` | one requirement per non-comment line | `re` / line-parse |
| `environment.yml` | the `dependencies:` block (incl. a nested `pip:` list) | `re` (see OD3) |
| `meta.yaml` (v0) | `requirements: run:` (+ `outputs:`); `{% set … %}` vars + `{{ … }}` (incl. `\|filter`s + `compiler()`/`stdlib()` calls → name-only) + `# [selector]` line-selectors | `re` (see OD3) |
| `recipe.yaml` (v1) | `requirements: run:` (Jinja `${{ … }}` tokens stripped) | `re` (see OD3) |

> **Two-path note (see § Engine-native support).** The `environment.yml` /
> `meta.yaml` / `recipe.yaml` / `pixi.toml` rows are the **primary bridge**
> (neither engine parses them). The `pyproject.toml` / `requirements.txt`
> rows are used **only to synthesize `osv-scanner` input when a PyPI project
> ships no native lockfile** (OD2) — they do not replace deptry/osv native
> parsing of those files.

### Engine-native support (grounded 2026-07-11 — time-bound)

Scope is **Python libraries across PyPI *and* conda-forge** (not conda
feedstocks only). Verified against upstream docs (re-verify before any
external release; both engines move fast):

- **deptry** natively reads `pyproject.toml` (PEP 621, Poetry, PDM, uv,
  setuptools-dynamic) + `requirements.txt`/`.in`/`*-dev.txt`. **No** conda/pixi.
- **osv-scanner** natively reads (Python) `requirements.txt`, `poetry.lock`,
  `pdm.lock`, `uv.lock`, `Pipfile.lock`, `pylock.toml`. **No** conda/pixi.

→ **PyPI path:** delegate to each engine's native parser, then unify — E1
only synthesizes `osv-scanner` input when a PyPI project has no native
lockfile (OD2). **Conda/pixi path (the E1 wedge):** neither engine parses
`environment.yml` / `meta.yaml` / `recipe.yaml` / `pixi.toml` / `pixi.lock`
/ `conda-lock.yml` — python-deptry-osv-scanner's manifest engine bridges them. Non-Python
osv ecosystems + container/artifact scanning are out of v1 scope.

### System data flow

1. **Discovery.** Invoked at the repo root; scans for manifests in priority
   order (`pixi.toml` → `environment.yml` → `recipe.yaml` → `meta.yaml` →
   `pyproject.toml`, with `requirements.txt` as a fallback). `recipe.yaml`
   (v1) is preferred over `meta.yaml` (v0) when a feedstock has both
   mid-migration.
2. **Extraction.** The Manifest Engine flattens dependencies and writes an
   ephemeral `.scanner-temp-reqs.txt`.
3. **Execution (sequential in v1 — OD6; both signals gate):**
   - **Branch A (Hygiene).** `deptry` is run against the project source to
     detect unused declared dependencies. (Note: `deptry` performs AST
     import analysis on the *source tree* and reads declared deps itself;
     the synthesized reqs file is used only where `deptry` cannot read the
     native manifest — the extractor is the value-add for conda/pixi.)
   - **Branch B (Security).** `osv-scanner` is run over the dependency set.
     **Input (OD2, resolved):** for **PyPI** projects, point `osv-scanner`
     at a lockfile it reads *natively* (`requirements.txt`, `poetry.lock`,
     `pdm.lock`, `uv.lock`, `Pipfile.lock`, `pylock.toml`); for **conda/pixi**
     projects (no osv-native format) synthesize a version-pinned
     `requirements.txt` from `pixi.lock` / `conda-lock` / the installed env.
     A bare name-only list is the last-resort fallback, its weaker coverage
     recorded in the report.
4. **Aggregation.** Both branches parse into a single `ComplianceReport`,
   emitted as schema-validated JSON plus the human summary (see § Report
   architecture).
5. **Teardown.** Ephemeral files deleted via `try/finally` (NFR3).

### Report architecture (E4 detail) — borrowed from the Cloudflare harness

The reporting design deliberately mirrors the proven pattern in
`cloudflare/security-audit-skill` (§ References), adapted from SAST to SCA:

- **Machine-readable `ComplianceReport` JSON** — the canonical artifact.
  Top-level shape: `run` metadata (tool version, timestamp, resolved
  manifest, target path), `hygiene` (unused-dependency findings from E2),
  `security` (advisory findings from E3), and a `summary` (counts +
  overall pass/fail).
- **Committed `report-schema.json`** (JSON Schema 2020-12) — the report is
  validated against it, and a standalone `validate_report.py` ships as the
  validator (the analogue of Cloudflare's `validate-findings.cjs`). The
  schema is the contract: it is exercised in the test suite so the JSON
  shape can't drift unnoticed, and is optionally re-checked at runtime via
  `--validate`. Test-time validation may use `jsonschema` as a
  **test-only** dependency; the runtime hot path stays limited to the two
  scanning engines (NFR1/NFR2).
- **Parallel human-readable summary** on stdout — the CI-log view (the
  analogue of the harness's `REPORT.md`): a compact, scannable rollup of
  the same data, never the source of truth.
- **Actionable findings only (FR7).** Each finding is concrete and
  attributable (package + manifest location, or advisory ID + affected /
  fixed version). Theoretical or non-applicable entries are suppressed —
  the harness's "only report what you can act on / no 'theoretically'"
  discipline, which keeps the gate's false-positive rate low at fleet
  scale (NFR1).

### Security & CI/CD considerations

- **Binary provisioning.** `osv-scanner` is a standalone Go binary.
  **Recommendation: declare it as a conda/pixi dependency** (it is on
  conda-forge). A `$PATH` presence check with a clear, actionable error
  is the fallback; runtime `curl` fetch is **rejected** as it violates
  NFR3 and introduces a supply-chain vector (OD1).
- **Ignore configuration.** The wrapper must respect existing
  `[tool.deptry]` configuration in `pyproject.toml` so teams keep their
  current ignore lists (e.g. ignoring `pytest`).
- **No network mutation of host.** OSV data is fetched by `osv-scanner`
  itself; `python_deptry_osv_scanner` adds no additional network side effects beyond
  the two engines.

---

## Story sharding (Product Owner)

Story 1.1 is specified in full; the rest are seeded stubs the executing
agent expands via `bmad-create-story` in the full BMAD flow.

### Story 1.1 — Core Manifest Extractor (E1)

> **Context.** Before scanning with Deptry or OSV, we need a unified
> interface to read dependencies without external parsers, keeping the
> runner lightweight.
>
> **Implementation guidance.**
> - Create `python_deptry_osv_scanner/extractor.py`.
> - `extract_pixi(filepath)` and `extract_pyproject(filepath)` using `tomllib`.
> - `extract_conda_env(filepath)`, `extract_meta_yaml(filepath)`, and
>   `extract_recipe_yaml(filepath)` using `re` — the `dependencies:` block
>   (`environment.yml`); the `requirements: run:` (+ `outputs:`) block of v0
>   `meta.yaml` (`{% set %}` vars + `{{ … }}` incl. `|filter`s +
>   `compiler()`/`stdlib()` → name-only, `# [selector]` lines); the
>   `requirements: run:` block of v1 `recipe.yaml` (`${{ … }}` tokens).
> - Return a standardized, de-duplicated `List[str]` of package names,
>   explicitly filtering base packages (`python`, `pip`, and virtual/`__*` packages).
> - **Two-path role:** `extract_pyproject`/requirements-text parsing exists to
>   synthesize the **osv-scanner input when a PyPI project has no native
>   lockfile** — it does NOT replace the engines' native parsing (deptry reads
>   `pyproject.toml`/`requirements.txt` natively; osv reads native lockfiles).
>   The conda/pixi extractors are the primary bridge (§ Engine-native support).
>
> **Acceptance criteria.**
> - Unit tests pass for all six target file types (`pixi.toml`,
>   `environment.yml`, `meta.yaml`, `recipe.yaml`, `pyproject.toml`,
>   `requirements.txt`).
> - No heavy external parser (e.g. `pyyaml`) is imported in this module.
> - Output is de-duplicated and base-package-filtered; unresolvable Jinja
>   (`compiler()`, cross-ref vars) degrades to name-only + marked.
> - Fixtures include a `{% set %}`/`|filter`/`# [selector]`-bearing v0
>   `meta.yaml`, a Jinja-bearing v1 `recipe.yaml`, and an `environment.yml`
>   with a nested `pip:` list.

### Story 1.2 — Discovery & priority resolution (E1)
Detect which manifest(s) exist at the root; apply the documented priority
order; expose the chosen manifest in the report. AC: deterministic
selection; multi-manifest repos resolve predictably.

### Story 2.1 — Deptry runner + output parser (E2)
Invoke `deptry` via `subprocess`, honor `[tool.deptry]` config, parse its
JSON output into structured violations. AC: unused-dep violations captured;
non-zero deptry exit handled without crashing the wrapper.

### Story 3.1 — OSV-scanner runner + parser (E3)
Provision-check `osv-scanner` on `$PATH`; run it over the resolved input
(per OD2 resolution); parse advisories into structured findings. AC:
clear, actionable error when the binary is absent; CVE list parsed.

### Story 4.1 — `ComplianceReport` + schema + CLI + exit gate (E4)
`argparse` CLI; merge E2+E3 into a `ComplianceReport`; emit
schema-validated JSON **and** a human-readable stdout summary; implement
the FR5 exit-code gate with `--no-fail-on-unused` / `--no-fail-on-vulns`.
AC:
- Exit 0 on a clean tree / non-zero when findings exist.
- A committed `report-schema.json` (JSON Schema 2020-12) plus a
  `validate_report.py` validator; the emitted JSON validates against it in
  the test suite, and `--validate` re-checks at runtime. `jsonschema` is
  allowed as a **test-only** dependency (runtime stays limited to the two
  engines).
- Findings are actionable (FR7): package + manifest location for hygiene;
  advisory ID + affected/fixed version for security.
- Ephemeral files cleaned via `try/finally` on both success and failure
  (NFR3).

---

## Decisions (resolved 2026-07-10; OD2 refined 2026-07-11)

The forks the source design left implicit, now decided. Recorded here so
the rationale survives; each drove a concrete change above.

- **OD1 — osv-scanner provisioning → RESOLVED.** Declared conda/pixi
  dependency + `$PATH` check fallback; runtime `curl` rejected (NFR3 +
  supply-chain). Consumed from the existing `osv-scanner-feedstock`
  (v2.4.0) — no new recipe (owner-confirmed).
- **OD2 — osv-scanner input → RESOLVED (a, else b) [refined 2026-07-11 vs
  upstream docs].** For **PyPI projects**, point `osv-scanner` at a lockfile
  it reads *natively* — `requirements.txt`, `poetry.lock`, `pdm.lock`,
  `uv.lock`, `Pipfile.lock`, `pylock.toml`. For **conda/pixi projects**
  there is **no osv-native format** (`pixi.lock` / `conda-lock.yml` are NOT
  supported by osv-scanner — an earlier draft wrongly called `pixi.lock`
  osv-native), so python-deptry-osv-scanner synthesizes a **version-pinned
  `requirements.txt`** from `pixi.lock` / `conda-lock` / the installed env
  where available; name-only is the last-resort fallback, its weaker
  coverage flagged in the report. See § Engine-native support.
- **OD3 — stdlib-only YAML → RESOLVED (a).** Hold the line on stdlib
  `re`/`tomllib` for v1, backed by an explicit fixture suite
  (Jinja-bearing `recipe.yaml`, nested `pip:` in `environment.yml`). An
  optional light YAML dep is deferred to § Future, taken up only if
  fragility surfaces.
- **OD4 — relationship to `scan-project` → RESOLVED (standalone for v1,
  integrate after).** `python_deptry_osv_scanner` is a standalone tool for v1, not
  folded into the repo's `scan-project` infra; it cross-links
  `reference/dependency-input-formats.md` so manifest-input behavior stays
  consistent. **Post-v1, promotion into the conda-forge-atlas / CFE scope
  is a planned follow-on (§ Future).**
- **OD5 — distribution → RESOLVED (internal-first).** Build the library
  internal-first; decide PyPI / conda-forge packaging at closeout. If
  conda-forge is chosen, Rules 1 & 2 (conda-forge-expert skill + retro)
  engage then.
- **OD6 — execution model + gate → RESOLVED (sequential; severity-tiered
  gate + audited bypass) [refined 2026-07-11].** Sequential branches in v1
  (simpler, still lightweight for NFR1). The gate is **severity-tiered**
  (FR5: exit 0/1/2; `--fail-on=<severity>` / `max_critical` / `max_high` /
  KEV; default block-on-critical-or-KEV) — **not** the original hard "any
  finding blocks" gate (which drives teams to disable it). The coarse
  `--no-fail-on-*` flags are retired in favour of the threshold plus the
  auditable, expiring **bypass** (FR9). Typed `error` states (FR10) stay
  exit-2, non-relaxable except via the recorded bypass.

---

## Definition of Done

- [x] All decisions (OD1–OD6) resolved (§ Decisions); `status: ready`.
      Next transition: `in-progress` when a dev agent picks it up.
- [ ] E1–E4 stories implemented with passing unit tests (all six manifest types).
- [ ] `python_deptry_osv_scanner` runs clean on this repo's own `pixi.toml` /
      `pyproject.toml` and exits 0 on a known-clean fixture, non-zero on a
      seeded-violation fixture.
- [ ] Committed `report-schema.json` + `validate_report.py`; emitted JSON
      validates against the schema in the test suite; human stdout view
      verified in a CI log (FR4/FR6).
- [ ] NFR3 verified: no host/source mutation; ephemeral files removed on
      both success and failure paths.
- [ ] If packaged for conda-forge (OD5): recipe authored via
      `conda-forge-expert`, and the effort closes with a CFE-skill retro +
      CHANGELOG entry (CLAUDE.md Rules 1 & 2).
- [ ] `status: shipped` with `implemented_by:` + `shipped_ref:` set.

---

## Future / backlog (out of MVP scope)

- **Promote into the conda-forge-atlas / `conda-forge-expert` scope
  (planned follow-on — the intended end state once v1 ships).** Expose
  `python_deptry_osv_scanner` inside the atlas intelligence layer as an MCP tool +
  `pixi run` CLI wrapper, consolidating with the existing `scan-project` /
  `scan_for_vulnerabilities` surfaces (dedupe overlap; share
  `reference/dependency-input-formats.md`). This is conda-forge work:
  adding a CFE script touches the three canonical places (pixi.toml task +
  the `SCRIPTS` test list + a wrapper/allowlist entry), and CLAUDE.md
  Rules 1 & 2 engage — invoke the `conda-forge-expert` skill, and close
  with a CFE-skill retro + CHANGELOG entry. The atlas-migration spec
  (`cfe-atlas-datapipeline-kedro-migration.md`, FR-16 / FR-18, Story F4)
  already models this promotion: the `hygiene` half becomes the `deptry`
  scan node (FR-16); the `security` half converges with
  `inventory-match --policy` at the unified CI gate (FR-18) — both emitting
  this spec's `ComplianceReport` schema, so consolidation is wiring, not a
  redesign. Note the security-source difference: standalone v1 runs
  `osv-scanner` (E3), whereas the promoted atlas node sources the
  `security` section from `inventory-match`/`cve` rather than re-invoking
  it.
- Alternate hygiene backends (`fawltydeps`, `pip-check-reqs` — both now in
  `recipes/`) behind a `--engine` flag.
- **Optional light YAML dependency (OD3 contingency).** If stdlib `re`
  parsing of `environment.yml` / `meta.yaml` / `recipe.yaml` proves too
  fragile against the fleet's long tail, adopt an optional light YAML parser
  behind a feature flag (keeping the default runtime stdlib-only per NFR2).
- Non-Python `osv-scanner` ecosystems (npm / Go / Rust / …) + its
  container/artifact scanning. (CycloneDX SBOM emission was promoted to v1 —
  FR8; PyPI lockfiles are already covered via `osv-scanner` delegation.)
- Auto-fix mode (remove unused declared deps) — deliberately excluded from
  v1 per NFR3.
- **Complementary SAST layer.** `python_deptry_osv_scanner` is SCA (dependency
  inventory + known-CVE). A code-vulnerability (SAST) layer such as
  Cloudflare's vulnerability harness / `security-audit-skill` is an
  orthogonal stage a mature pipeline runs *alongside* it — not a backend
  of this tool (its LLM-agent model conflicts with NFR1/NFR2). See
  § References.

---

## References

Adjacent SAST / LLM-harness work — complementary to this SCA tool, and the
source of two transferable design lessons (schema-enforced findings; and
fleet-scale run persistence + minimizing *unconfirmed* findings shown to
humans, which reinforces NFR1's 20k-repo target):

- **Cloudflare — "Build your own vulnerability harness"** (Dan Jones,
  Alexandra Godoi, Grant Bourzikas; 2026-06-18) —
  <https://blog.cloudflare.com/build-your-own-vulnerability-harness/>.
  Model-agnostic multi-agent VDH/VVS pipeline; **schema-enforced findings
  (threat model + working PoC required)**, SQLite persistence keyed by
  run-id/repo/stage for resumability, cross-repo dependency tracing;
  20,799 raw → 7,245 actionable findings across a 128-repo fleet. Informs
  our E4 report schema and NFR1 fleet-scale posture.
- **Cloudflare — "Project Glasswing: what Mythos showed us"** (Grant
  Bourzikas; 2026-05-18) —
  <https://blog.cloudflare.com/cyber-frontier-models/>. Frontier
  security-LLM (Anthropic Mythos Preview) evaluation; argues engineered
  *harnesses* beat generic agents pointed at a repo. "A finding that
  arrives with a PoC is a finding you can act on" — the actionability /
  false-positive discipline that maps onto OD2 (avoid noisy name-only OSV
  results).
- **`cloudflare/security-audit-skill`** (MIT) —
  <https://github.com/cloudflare/security-audit-skill>. The open-source
  foundation for the harness above; a coding-agent *skill*, not a CLI —
  reference for the dual human/`findings.json` + `report-schema.json`
  validated-report pattern to mirror in E4, **not** a build dependency.
