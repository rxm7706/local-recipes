---
status: ready
spec_updated: 2026-07-11
---
# Tech Spec: `deptry_scanner`

> **BMAD intake document.** A unified dependency-hygiene + vulnerability
> scanner that orchestrates `deptry` and Google's `osv-scanner` over
> Python / Conda / Pixi manifests. Written to be self-contained: it folds
> the Analyst brief, PM PRD, Architect design, and the first sharded
> story into one file so a single agent can drive it end to end.
>
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/deptry-scanner.md
> ```
>
> Scope is ~4 epics / ~12–16 stories. It is Quick-Flow-drivable as written,
> but the epic breakdown (§ Epics) also supports the full
> PRD → architecture → epics planning chain if the owner prefers.
>
> **Conda-forge tie-in (Rules 1 & 2).** If the effort packages
> `deptry_scanner` (or any of its scanning engines) as a conda recipe, or
> touches anything under `recipes/`, the executing agent **must** invoke the
> `conda-forge-expert` skill first (CLAUDE.md Rule 1) and close with a
> CFE-skill retrospective + CHANGELOG entry (Rule 2). Pure library/CLI work
> that never touches `recipes/` is exempt from those two rules.

---

## Status

| Field | Value |
|---|---|
| Status | **Ready v1** — all decisions resolved (§ Decisions); ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec self-contained; no separate PRD/architecture phase required) |
| Proposed project slug | `deptry-scanner` (BMAD artifacts → `_bmad-output/projects/deptry-scanner/`) |
| Python package | module `deptry_scanner`; dist name `deptry-scanner` |
| Source root | **In-repo pixi *build* workspace member** at `src/shared/packages/deptry-scanner/` (Option B; unity-data-stack `src/shared/packages` convention) — see § Repository layout |
| Target users | Platform Engineers (CI/CD), DevSecOps Engineers (compliance / SBOM), Python + conda-feedstock maintainers |
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
Conda and Pixi, where neither tool natively understands the manifests.

**Target users**

- Platform Engineers managing CI/CD pipelines.
- DevSecOps Engineers tracking organization-wide software compliance and SBOM data.
- Python Developers maintaining Conda feedstocks and standard packages.

**MVP idea.** A unified Python CLI (`deptry_scanner`) that orchestrates
both `deptry` and Google's `osv-scanner`. It dynamically resolves
manifests (`pyproject.toml`, `requirements.txt`, `environment.yml`,
`recipe.yaml` v1, `pixi.toml`), detects unused dependencies in the
codebase, and checks the resolved dependency tree for known
vulnerabilities against the OSV database.

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
   inputs). `deptry_scanner` partially re-implements that surface. Whether
   it should be a standalone external tool or reuse/extend the existing
   infra is an explicit decision (OD4), not a silent one.

3. **`fawltydeps` and `pip-check-reqs` are adjacent alternatives** to
   `deptry` for the unused-dependency job. The MVP picks `deptry` as the
   hygiene engine; the other two are candidate future backends (§ Future).

---

## Goals

- **G1.** One CLI (`deptry_scanner`) that produces a single consolidated
  hygiene + security report from one invocation at a repo root.
- **G2.** Native, zero-heavy-parser manifest resolution across
  `pyproject.toml`, `requirements.txt`, `environment.yml`, `recipe.yaml`
  (v1), and `pixi.toml`.
- **G3.** Act as a strict CI/CD quality gate: non-zero exit when unused
  deps **or** vulnerabilities are found.
- **G4.** Machine-readable JSON for programmatic consumption **and**
  human-readable stdout for CI logs.
- **G5.** Idempotent: never mutate host env or source; clean up all
  ephemeral files even on failure.
- **G6.** Lightweight enough to run concurrently across a 20,000+ repo
  fleet without excessive compute/memory overhead.

**Non-goals (v1).** Auto-fixing/removing unused deps; writing SBOMs;
resolving/pinning transitive version trees itself; replacing the repo's
existing `scan-project` intelligence layer; supporting `poetry.lock` /
`Pipfile.lock` / npm lockfiles (Python/conda/pixi manifests only in v1).

---

## Requirements (PM PRD)

### Functional Requirements

- **FR1.** Detect and parse `pyproject.toml`, `requirements.txt`,
  `environment.yml`, `recipe.yaml` (v1), and `pixi.toml` automatically
  based on the execution directory.
- **FR2.** Execute `deptry` to identify declared-but-unused dependencies,
  parsing its output into a structured format.
- **FR3.** Execute `osv-scanner` against the resolved dependency set to
  identify known CVEs/advisories.
- **FR4.** Emit a **consolidated report in two parallel forms**: a
  machine-readable `ComplianceReport` JSON (for programmatic CI/CD
  consumption) **and** a human-readable summary (for CI logs), both
  covering hygiene (unused) and security (vulnerable) metrics.
- **FR5.** Exit non-zero if either unused dependencies **or**
  vulnerabilities are found (strict CI/CD gate). `--no-fail-on-unused` /
  `--no-fail-on-vulns` relax each signal independently (OD6).
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
| **E3** | OSV-Scanner Integration | Feed resolved dependencies (or a native lockfile) into `osv-scanner` and parse vulnerability data. |
| **E4** | Unified Reporting & CLI | `argparse` CLI + schema-validated `ComplianceReport` JSON **and** human report consolidating E2 and E3, with the CI exit-code gate. |

---

## Architecture (Architect design)

### Technology stack

- **Language:** Python 3.11+ (built-in `tomllib` for `pyproject.toml` /
  `pixi.toml` parsing). Matches the conda-forge `python_min` floor policy
  in this repo (G40/G41 — 3.11).
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
| conda package (`.conda`) | `pixi-build-python` (wraps the hatchling wheel) | `deptry-scanner-build-conda` |
| pypi wheel (`.whl`) | `python -m build` (hatchling) | `deptry-scanner-build-dist` |
| sdist (`.tar.gz`) | `python -m build` (hatchling) | `deptry-scanner-build-dist` |

`deptry-scanner-build` runs all three; the path dependency also builds+installs
the conda package into the dev env on `pixi install`.

```
local-recipes/
├─ pixi.toml                          # root [workspace]; preview = ["pixi-build"];
│                                     #   [feature.deptry-scanner.*] + lean env + build tasks
├─ src/
│  ├─ sentinel/                       # existing in-repo app (wiki/knowledge)
│  └─ shared/packages/deptry-scanner/ # the workspace MEMBER (no [workspace] table)
│     ├─ pixi.toml                    #   [package] + [package.build.backend]=pixi-build-python
│     ├─ pyproject.toml               #   hatchling; entry point deptry_scanner.cli:main
│     ├─ src/deptry_scanner/          #   E1 extractor.py · E2/E3 runners · E4 report.py + cli.py
│     ├─ report-schema.json           #   FR6 (E4)
│     └─ tests/
└─ docs/specs/deptry-scanner.md
```

- **Runtime engines** (`deptry`, `osv-scanner`) are the member's conda
  `[package.run-dependencies]` (OD1) — never pip, never runtime `curl`.
- **Dedicated lean env**: `[environments] deptry-scanner` uses
  `no-default-feature = true`, so it excludes the repo's fat default toolchain
  (python 3.14 + pixi + conda + pip + uv) and carries only the built package +
  its run-deps + build/test tooling (NFR1/NFR2). Tasks: `deptry-scan`,
  `deptry-scanner-test`, `deptry-scanner-build{,-conda,-dist}`.
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
| `recipe.yaml` (v1) | `requirements: run:` (Jinja `${{ … }}` tokens stripped) | `re` (see OD3) |

### System data flow

1. **Discovery.** Invoked at the repo root; scans for manifests in
   priority order (`pixi.toml` → `environment.yml` → `recipe.yaml` →
   `pyproject.toml`, with `requirements.txt` as a fallback).
2. **Extraction.** The Manifest Engine flattens dependencies and writes an
   ephemeral `.scanner-temp-reqs.txt`.
3. **Execution (sequential in v1 — OD6; both signals gate):**
   - **Branch A (Hygiene).** `deptry` is run against the project source to
     detect unused declared dependencies. (Note: `deptry` performs AST
     import analysis on the *source tree* and reads declared deps itself;
     the synthesized reqs file is used only where `deptry` cannot read the
     native manifest — the extractor is the value-add for conda/pixi.)
   - **Branch B (Security).** `osv-scanner` is run over the resolved
     dependency set. **Input (OD2, resolved):** point `osv-scanner` at a
     native lockfile (`pixi.lock` / pinned `requirements.txt`) when one
     exists; otherwise extract versions into the temp file. A bare
     name-only list is a last-resort fallback only, with the weaker
     coverage recorded in the report.
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
  itself; `deptry_scanner` adds no additional network side effects beyond
  the two engines.

---

## Story sharding (Product Owner)

Story 1.1 is specified in full; the rest are seeded stubs the executing
agent expands via `bmad-create-story` (or inline for Quick Flow).

### Story 1.1 — Core Manifest Extractor (E1)

> **Context.** Before scanning with Deptry or OSV, we need a unified
> interface to read dependencies without external parsers, keeping the
> runner lightweight.
>
> **Implementation guidance.**
> - Create `deptry_scanner/extractor.py`.
> - `extract_pixi(filepath)` and `extract_pyproject(filepath)` using `tomllib`.
> - `extract_conda_env(filepath)` and `extract_recipe_yaml(filepath)`
>   using `re` to target the `dependencies:` block (`environment.yml`) and
>   the `requirements: run:` block (v1 `recipe.yaml`), stripping Jinja
>   `${{ … }}` tokens.
> - Return a standardized, de-duplicated `List[str]` of package names,
>   explicitly filtering base packages (`python`, `pip`, and virtual/`__*` packages).
>
> **Acceptance criteria.**
> - Unit tests pass for all target file types (`pixi.toml`,
>   `environment.yml`, `recipe.yaml`, `pyproject.toml`, `requirements.txt`).
> - No heavy external parser (e.g. `pyyaml`) is imported in this module.
> - Output is de-duplicated and base-package-filtered.
> - Fixtures include a Jinja-bearing `recipe.yaml` and an
>   `environment.yml` with a nested `pip:` list.

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

## Decisions (all resolved 2026-07-10)

The forks the source design left implicit, now decided. Recorded here so
the rationale survives; each drove a concrete change above.

- **OD1 — osv-scanner provisioning → RESOLVED.** Declared conda/pixi
  dependency + `$PATH` check fallback; runtime `curl` rejected (NFR3 +
  supply-chain). Consumed from the existing `osv-scanner-feedstock`
  (v2.4.0) — no new recipe (owner-confirmed).
- **OD2 — osv-scanner input → RESOLVED (a, else b).** Point `osv-scanner`
  at a native lockfile (`pixi.lock` / pinned `requirements.txt`) when one
  exists; otherwise extract versions into the temp file. Name-only is a
  last-resort fallback, its weaker coverage flagged in the report.
- **OD3 — stdlib-only YAML → RESOLVED (a).** Hold the line on stdlib
  `re`/`tomllib` for v1, backed by an explicit fixture suite
  (Jinja-bearing `recipe.yaml`, nested `pip:` in `environment.yml`). An
  optional light YAML dep is deferred to § Future, taken up only if
  fragility surfaces.
- **OD4 — relationship to `scan-project` → RESOLVED (standalone for v1,
  integrate after).** `deptry_scanner` is a standalone tool for v1, not
  folded into the repo's `scan-project` infra; it cross-links
  `reference/dependency-input-formats.md` so manifest-input behavior stays
  consistent. **Post-v1, promotion into the conda-forge-atlas / CFE scope
  is a planned follow-on (§ Future).**
- **OD5 — distribution → RESOLVED (internal-first).** Build the library
  internal-first; decide PyPI / conda-forge packaging at closeout. If
  conda-forge is chosen, Rules 1 & 2 (conda-forge-expert skill + retro)
  engage then.
- **OD6 — execution model + gate → RESOLVED (sequential; both gate).**
  Sequential branches in v1 (simpler, still lightweight for NFR1); both
  hygiene and security gate by default, relaxable via
  `--no-fail-on-unused` / `--no-fail-on-vulns`.

---

## Definition of Done

- [x] All decisions (OD1–OD6) resolved (§ Decisions); `status: ready`.
      Next transition: `in-progress` when a dev agent picks it up.
- [ ] E1–E4 stories implemented with passing unit tests (all five manifest types).
- [ ] `deptry_scanner` runs clean on this repo's own `pixi.toml` /
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
  `deptry_scanner` inside the atlas intelligence layer as an MCP tool +
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
- SBOM (CycloneDX) emission, aligning with the repo's
  `cyclonedx-universe-inventory` tooling.
- `poetry.lock` / `Pipfile.lock` / npm lockfile support.
- Auto-fix mode (remove unused declared deps) — deliberately excluded from
  v1 per NFR3.
- **Complementary SAST layer.** `deptry_scanner` is SCA (dependency
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
