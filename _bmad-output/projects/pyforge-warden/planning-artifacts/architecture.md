---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
inputDocuments:
  - planning-artifacts/prd.md
  - planning-artifacts/implementation-readiness-report-2026-07-11.md
  - docs/specs/pyforge-warden.md
  - docs/specs/cfe-atlas-datapipeline-kedro-migration.md
referenceImplementation: src/shared/packages/pyforge-warden/  # pixi build member; stdlib-only lib, deptry+osv-scanner conda run-deps; cli.py stub
pinnedEngineContracts:  # grounded 2026-07-11 — the wrapped-engine contracts the design pins against
  deptry:
    docs: https://deptry.com/usage/
    rules: "DEP001 missing / DEP002 unused / DEP003 transitive / DEP004 misplaced-dev / DEP005 unused-dev"
    severity: "NONE — uniform violations, no CVSS (confirms Gap A: hygiene = separate warn-axis)"
    json: "--json-output / -o → array of {error:{code,message}, module, location:{file,line,column}}"
    config: "[tool.deptry] ignore / per_rule_ignores / exclude / extend_exclude (FR9)"
  osv-scanner:
    docs: https://google.github.io/osv-scanner/output/
    json: "--format json → JSON to stdout, all else to stderr; results[].packages[].{package{name,version,ecosystem}, vulnerabilities[]{id,aliases,...Full OSV}, groups[]{ids}}"
    severity: "CVSS inside Full-OSV severity field; NO CISA-KEV flag (confirms KEV-deferral — must join ourselves)"
    exitCodes: "0 no-vulns / 1 vulns-found (EXPECTED, not error) / 127 DB-load/coverage error (MULTIPLEXED: DB-absent|corrupt-zip|missing -L file|unknown parser) / 128 no-packages-found. Reconciled by the Story-1.4 spike: a DB-absent/empty 127 and 128 are COVERAGE GAPS -> indeterminate, not exit-2; any OTHER 127 -> error"
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-07-11'
project_name: 'pyforge-warden'
user_name: 'rxm7706'
date: '2026-07-11'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (31, 8 areas) — architecturally, a 7-stage pipeline over one shared object:**

```
Discover(FR1) → Route-per-section(FR2) → Extract(FR3–7) → ┬─ Hygiene: deptry (FR8–9)
                                                          └─ Vuln: osv-scanner (FR10–13)
   → Coverage+Report assembly(FR14–17) → Verdict/Gate(FR18–23) → Waivers(FR24–26)
   → SBOM + machine contract(FR27–28)  ⟂  CLI + config wrapper(FR29–31)
```

The **resolved-inventory object** is the spine (this *is* Gap B): discovery + extraction produce it; both engine paths annotate it; report, SBOM, verdict, and coverage all read it. "BOM component count == resolved-inventory count" is meaningful only because they share it.

**Non-Functional Requirements — the dominant architectural drivers:**
- **C0 (never false-green)** is the shaping force → fail-loud everywhere; verdict on report **content**, never an engine exit code; typed errors; no-meaningful-scan guards. Every module inherits it.
- **Security S1–S8** split the design into a **stdlib-only, execution-free extractor** (AST-denylist, ReDoS line-bound, no template render) vs. a **hardened engine-runner** (input purity, secure temp, `_engine_env` normalization) vs. a **schema-aware serializer** (S7 output neutralization).
- **NFR-R3b determinism** → report assembly canonicalizes (sort, pin volatile fields, `--deterministic` mode).
- **NFR-P** → the two engines run **in parallel**; stdlib-only; offline DB. **NFR-I1/I3** → schema-validated report + CycloneDX 1.6 + pure-JSON stdout.

### Scale & Complexity
- **Medium engineering, high stakes.** Single-process CLI — no service, database, network server, or UI. Domain: DevSecOps supply-chain tooling.
- **Estimated architectural components: ~7** — discovery/router · extractor · engine-runner · resolved-inventory model · verdict-composer · report/SBOM serializer · CLI/config — plus cross-cutting security & determinism layers.
- Complexity concentrates in exactly the three blocking gaps: the lossy E1 extractor, the resolved-inventory model (Gap B), and the osv/deptry output-orchestration + verdict math (Gaps A & C).

### Technical Constraints & Dependencies
- **stdlib-only library** (argparse / tomllib / re) — confirmed by the scaffold's empty `dependencies`; `jsonschema` test-only; engines (`deptry`, `osv-scanner`) as **conda run-deps** (provisioned, not fetched — OD1).
- **Pinned engine contracts (2026-07-11):** deptry = no-severity + `--json-output`; osv = `--format json` (JSON→stdout, else→stderr) + exit `{0 clean, 1 vulns-found=EXPECTED, 127 DB-load/coverage error, 128 no-packages}` — Story-1.4-reconciled: 127 is multiplexed and a DB-absent/empty 127 → `indeterminate` (coverage gap, gated by the content pre-flight below), other 127 → `error`; 128 → `indeterminate`.
- python ≥ 3.12; pixi ≥ 0.72.2 (**a build/dev-env floor — the tool never invokes pixi at runtime**; `pixi.lock` is `safe_load`-parsed; clarified 2026-07-12); `pixi-build-python` packaging; never-writes-repo (NFR-R3a/S4); offline-first vuln data.
- **Open dependency question (D1):** the waiver YAML writer may pull one small YAML lib *or* emit-for-human-to-commit — resolved in Architectural Decisions.

### Cross-Cutting Concerns Identified
1. **Resolved-inventory model** (Gap B) — spans discovery → extraction → both engines → report/SBOM/verdict/coverage.
2. **Verdict-composition state machine** (FR20/J9) — the C0 acceptance property; ingests every finding source + the pinned osv exit codes.
3. **Typed-error taxonomy + ownership routing** (FR21) — every failure path; must map osv `127`/`128` and deptry non-zero.
4. **Determinism** (NFR-R3b) — every emit path.
5. **Security invariants** (S1–S8) — extractor + engine-runner + serializer boundaries.
6. **Split coverage accounting** (hygiene vs vuln) — discovery denominator → per-engine coverage → report.

## Starter Template Evaluation

### Primary Technology Domain
CLI tool — a **non-interactive, single-process, stdlib-only Python CLI**. No web/mobile/desktop/API-server dimension; no UX/starter concerns (database, styling, real-time, PWA all N/A).

### Starter Options Considered
| Candidate | Verdict |
|---|---|
| Click / Typer / Rich CLI starters | ❌ Ruled out by the stdlib-only NFR (no third-party runtime deps; the S1 AST-denylist forbids importing execution primitives) |
| cookiecutter-pypackage / hatch `new` | ❌ Redundant — the scaffold already provides hatchling packaging |
| oclif / framework generators | ❌ JS ecosystem; N/A |

### Selected Starter: NONE — use the existing scaffold

**Rationale:** the stdlib-only constraint is load-bearing (lightweight fleet gate + S1 security), so no third-party CLI framework is permissible. The existing scaffold at `src/shared/packages/pyforge-warden/` already establishes the entire foundation.

**Technical stack (locked — versions fixed by PRD + scaffold, nothing to verify):**
- Language/runtime: Python ≥ 3.12
- CLI: `argparse` (stdlib) — *not* Click/Typer
- Config parse: `tomllib` (stdlib); manifest extraction: `re` (stdlib)
- Packaging: `hatchling` + `pixi-build-python` (conda build member)
- Engines: `deptry`, `osv-scanner` as conda run-deps (provisioned)
- Test: `pytest`; lint: `ruff`; schema validation: `jsonschema` (test-only)

**Note:** the first implementation story is **complete-the-scaffold** (wire E1–E4 into the existing `cli.py` stub), not create-from-template.

## Core Architectural Decisions

*Resolves the PRD's blocking Architecture Open Questions (Gaps A/B/C) + the connective-tissue open questions, hardened through an advanced-elicitation + party-mode roundtable (PM/Architect/Dev) whose decisive finding was that the first-draft resolutions shipped a **false-green on the beachhead's most common artifact** — corrected below. The E1 extraction strategy is grounded in the `conda-forge-expert` skill's recipe-format references (v0/v1 Jinja + selector semantics; gotchas G20/G3/G43/G93). The generic web-app decision categories (Data/DB, Auth, API-server, Frontend, Cloud-hosting) are **N/A** for a stdlib-lean single-process CLI.*

### Cross-cutting: the false-green triad (the acceptance invariant, non-negotiable)
Three decisions are **only sound together** — fix one without the others and the cardinal-rule (never false-green) reopens:
1. **New verdict state `indeterminate`** — added to the J9 lattice **above `warn`**: `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`. Gap-C's *withheld / skipped / unresolved* outcomes route here — **never** to `not-applicable`. A clean sibling axis can therefore never mask "we couldn't scan what existed." (`not-applicable` = *nothing existed to scan*; `indeterminate` = *something existed we could not/would not scan*.)
2. **7→4 exit projection (locked; `indeterminate` pinned 2026-07-12):** exit **0** only when the vuln axis is `clean` **or** truly `not-applicable`. Mapping: `{clean, not-applicable, bypassed} → 0`; `warn → 0` (configurable); `policy-violation → 1`; **`indeterminate` → 1** (a trustworthy run honestly reporting unproven cleanliness is a policy-family outcome — never a silent 0); `error → 2` (**exit 2 stays reserved for operational failure** — the run itself is untrustworthy — preserving J3's fleet routing `rc==2 → infra owner`); SIGINT → 130. Status-severity and exit are deliberately different orderings.
3. **Gap-C withhold** — honest, but load-bearing on #1+#2.

Every non-`clean` status carries **`status.driver`** (axis + finding id) — an exit-2 that can't say "critical CVE" vs "blocking DEP001" is an incoherent contract.

### GAP A — deptry-severity → verdict → **two-axis, per-rule ceiling**
deptry emits *no severity* (uniform DEP001–005, confirmed from upstream docs). Both axes compute a status in the **same** lattice; "separate axis" = a separate **default ceiling** + `status.driver`:
- **DEP001 (missing dependency) blocks by default** — but **gated on conda↔PyPI name-mapping confidence**: block on a high-confidence mapping, `warn` on an ambiguous one (a mapping miss must not become a false-red disable-driver, per this repo's known name-unreliability).
- **DEP002 (unused) / DEP003 / DEP004 (misplaced) → `warn`** by default (false-positive-prone on conda recipes that legitimately carry deps deptry can't see).
- The **hygiene→status table** and the **CVSS severity thresholds** are *our* policy artifacts (deptry has no severity, osv has no gate) → both live in the **FR30 `ConfigLoader`** (overridable via the config tables). The CVSS gate (FR18) reads only the vuln axis.

### GAP B — ComplianceReport ↔ CycloneDX → **one `ResolvedInventory`, two artifacts**
One internal model, projected into two independent emitted artifacts:
- **`Component{ name, version|None, ecosystem, pypi_identity:(name,version)|None, purl, provenance:[(manifest,section)], hygiene_covered, vuln_matchable, indeterminate_reason|None }`**.
- **Identity = `(ecosystem, name, concrete_version)`**; purl is *derived*, its non-identity qualifiers **stripped before any comparison**. Merge rules: same identity across manifests/sections → **one** component with a **provenance list** (not scalar — a dep in `host:` *and* `run:` is one component); `(name,None)` merges into `(name,version)` **only when exactly one concrete version** exists (zero → stays one `indeterminate`; ≥2 → the bare entry stays a distinct `indeterminate` — never guess-attribute a version); different version, same `(eco,name)` → **distinct components, both scanned** (honest count inflation, stated).
- **Two artifacts:** `ComplianceReport` (JSON, `report-schema.json`) → stdout/`--output`; **CycloneDX 1.6 SBOM** → `--sbom-output` only. **Invariant `len(SBOM.components) == len(inventory) == report.inventory_count`**, evaluated **post-merge** with the **root project excluded** (it is CycloneDX `metadata.component`, not a dependency). The report *references* the SBOM (path/ref), never embeds it; schema versions decoupled (NFR-I2).
- **deptry↔inventory join is per-code** (not uniform — `importlib.metadata.packages_distributions()` reflects the CLI's env, not the target, so a uniform module→dist join is unbuildable offline): **DEP001** (module axis) → `component_ref = None` by construction; **DEP002/3/4** (declared-dep-name axis) → join to a component by name. Hygiene findings are **not** required 1:1 with inventory (the invariant holds because SBOM/inventory = the manifest-declared set). Import→distribution enrichment for DEP001 → **out of v1 scope**.

### GAP C — osv input contract + offline DB → **ecosystem-identity predicate + name-level tier + provisioned DB**
- **osv has no conda ecosystem** — it keys advisories by `(ecosystem, name, version)` over PyPI/npm/Go/… so a conda dep is parsed as **PyPI**. A pinned-but-differently-named conda pkg (`pytorch`→`torch`, native `openssl`) fed to osv matches the *wrong* PyPI identity → **silent false-green**. So `vuln_matchable = (pypi_identity ≠ None) AND (version resolved to ==X.Y.Z)`. `pypi_identity` is resolved **only** from trustworthy provenance: pixi.lock `pypi:` entries · explicit PyPI sections (`[pypi-dependencies]`, `environment.yml` `- pip:`) · a **bundled static conda→pypi map** (the CLI is offline — it cannot call the MCP `get_conda_name` mapper; regenerable from the atlas `export-purls` TSVs **or parselmouth-direct** — prefix-dev's published mapping, for non-atlas orgs; added 2026-07-12). Unmapped → `None`. Conda `=1.2` is a *prefix* (`1.2.*`), **not** an exact match → withheld as `range-only`.
- **Withhold reason enum:** `no-version | unmapped-ecosystem | native-nonpypi | range-only`. ~~osv's temp input file must be named literally `requirements.txt`~~ — **REMOVED (Story 1.4):** the `-L <parser>:<path>` override forces the parser, so osv's temp input may use any secure name (parser id is `requirements.txt`).
- **Name-level CVE tier (rescues beachhead value):** for a mapped-but-unversioned dep, query the DB "does this package carry *any* critical CVE across any version?" → `indeterminate: carries known critical CVEs — pin/lock to prove immunity` (a ranked worry-list + lock-nudge, not a dead "12%"). **Guardrail: coverage improves ONLY by resolving (read the lock) or name-level flagging — NEVER by assuming a version.**
- **osv exit codes read as content, never as the gate** (Story-1.4-reconciled): `0` no-vulns, `1` vulns-found=EXPECTED, `127` **multiplexed** — a DB-absent/empty/corrupt `127` is a *coverage gap* → `indeterminate` (gated by the DB content pre-flight, not the exit code alone), any **other** `127` (osv crashing with a valid DB) → `error`; `128` no-packages → `coverage: skipped` → `indeterminate`; any exit code **outside {0,1,127,128}** → `error`. Absence of an expected field is an error, not a zero.
- **Offline DB:** pre-provisioned as a conda package (`{ecosystem}/all.zip`), run **full `--offline`** (not `--offline-vulnerabilities` — that egresses on transitive resolution); **trust-anchor = conda package integrity** (the DB ships integrity-checked); **staleness from the DB package build-date** (`--db-max-age`, default 7d → stale ⇒ degrade/fail-loud, never confident-clean). **DB content pre-flight (INVARIANT, Story 1.4):** a present-but-EMPTY or content-corrupt `all.zip` makes osv exit **0** with an empty body — a false-green that neither the exit code nor a namelist count catches. The loader MUST run a **content** pre-flight (parse + validate the OSV advisory shape, advisory-count ≥ 1, at osv's case-sensitive `PyPI` dir segment) before trusting a clean; a **provenance-less** DB (`snapshot_at=None`) routes to `indeterminate`, never `clean`.
- **Resolution-depth honesty:** the coverage block states **`direct-only` vs `locked-closure`** (a loose manifest lists direct deps only; transitive vulns are invisible without a lockfile) — prefer a lockfile input, downgrade the coverage claim for a loose manifest.

### E1 extraction strategy — **non-rendering parse-as-data + a supported-construct matrix**
NFR-S1 forbids rendering untrusted Jinja, which rules out `conda-build MetaData`/grayskull/rattler-build on the runtime path (they *evaluate*), and rules out CRM/conda-souschef as the primary parser (G93: CRM crashes on odd comments → fails NFR-R1). E1 does a **bounded, non-rendering two-pass scrape**:
- **Pass 1 — capture context without executing:** v0 → regex-capture `{% set K=V %}`; v1 → `safe_load` the `context:` block.
- **Pass 2 — neutralize + `safe_load`:** v1 `recipe.yaml` is valid YAML → `safe_load` **directly**; v0 `meta.yaml` is not → capture `# [selector]` marks, strip `{% … %}` statement lines, substitute simple `{{ VAR|filter }}` via **our own safe-filter allowlist** (never a Jinja engine), then `safe_load`. Walk `requirements.{build,host,run}` + `test(s).requirements` + `outputs[].requirements`; `run_constrained`/`run_constraints` entries are **constraints, not dependencies** — excluded or flagged `provenance: constraint`, out of vuln matching + SBOM counts (corrected 2026-07-12; matches the shipped `scan_project` semantics).

**Supported-construct matrix (the FR-flagged unowned deliverable — owned here):**

| Construct | Handling |
|---|---|
| `numpy >=1.20` | ✅ name + spec |
| `{{ name }}` / `${{ version }}` (VAR∈context) | ✅ resolve to literal |
| `${{ compiler("c") }}` / `stdlib("c")` | ⚠️ variant-expanded **build-tool** → mark + **exclude** from the scanned set |
| `${{ pin_subpackage('foo') }}` | ⚠️ **intra-recipe output** → mark `internal-subpackage`, **exclude** from external deps |
| `# [linux]` / `if: linux then/else` | ⚠️ **union both branches**, tag each with its condition |
| `{{ version.replace(...) }}` expr logic | ⚠️ version field → `version=None` (Gap-C `range-only`); name field → best-effort |
| `{% for %}`-generated deps | ❌ degrade block to name-only+marked |
| bare `{{ }}` in a v1 file (G20) | ⚠️ literal text → raw string + malformed-recipe flag |

**v0↔v1 differences the parser must encode:** prefix `{{ }}` vs `${{ }}` (G20); context via `{% set %}` vs `context:` block; selectors `# [sel]`/`py < N` vs `if/then/else`/`match(python,…)`; section rename `run_constrained` → `run_constraints`; v0 needs neutralizing, v1 `safe_load`s directly.

**Validation (feeds J8/NFR-R1):** a **differential-oracle corpus test** — for each real recipe, assert E1's dep set **⊇ the authoritative renderer's** (rattler-build v1 / conda-build v0, both already in-repo) modulo name-only-marked. Ground truth *without* executing untrusted input at runtime. Two 2026-07-12 additions: **py-rattler `LockFile`** serves as a *test-side* second oracle for `extract/lockfiles.py` (never a runtime dep — the lean policy holds), and `prefix-dev/rattler-build-parser-tests` supplies out-of-repo adversarial recipes for the corpus gate.

### Library policy (stdlib-first; targeted conda-provisioned deps)
Per the directive to relax pure-stdlib: **stdlib where it suffices, targeted libs where they materially improve fidelity/resilience, always via safe APIs.**

| Lib | Buys | Guardrail |
|---|---|---|
| **PyYAML** (`safe_load`/`safe_dump`) | clean-YAML parse (pixi.lock/environment.yml/conda-lock) + safe waiver I/O | `safe_load` only; recipe Jinja still **not** YAML-parsed |
| **packaging** | version/specifier logic (Gap-C `==` vs conda `=` prefix vs ranges) | — |
| **cyclonedx-python-lib** | spec-correct CycloneDX 1.6 → **NFR-S7 output-neutralization + NFR-I1** for free | the maintained encoder *is* the injection defense |
| **jsonschema** | runtime `ComplianceReport` self-validation | — |
| stdlib retained | `argparse`, `tomllib`, `re` (Jinja neutralize), `subprocess`, `hashlib`, `tempfile` | argparse (no Click) |

**NFR-S1 reframed:** the constraint was never "stdlib-only" — it is **"no *execution* of untrusted input"** (no `eval`/`exec`/`compile`, no `subprocess` in the extractor, **no Jinja rendering, no `jinja2` import**, `yaml.safe_load` only). The AST-denylist targets execution primitives, not third-party imports. Honest trade-off: more deps = more supply-chain surface for a supply-chain tool — mitigated by conda-provisioning (integrity-checked), pinning, safe-APIs-only, and the tool **dogfooding itself** on its own deps.

### Smaller resolutions
- **D1 waiver → keep `.yaml` (FR9 UNCHANGED)** — with `yaml.safe_dump` available the "stdlib can't write YAML safely" driver disappears; the tool emits the `--bypass` stanza for the human to commit and reads via `safe_load` (never writes the repo, NFR-S4). *(Removes a PRD delta.)*
- **FR30 → a `ConfigLoader` component** owns the dual `[tool.pyforge-warden]` schema (pyproject+pixi, per-key precedence, conflict-surfaced), the hygiene→status table, and the CVSS thresholds.
- **Multi-manifest selection (FR1) → union coverage** — scan all discovered manifests, report per-manifest; honest coverage means the denominator includes everything found.
- **Determinism (NFR-R3b) → `--deterministic` mode** pins the volatile-field set (timestamps, CycloneDX `serialNumber`/`bom-ref` from a content hash, set-ordering→sorted, abs-paths→repo-relative, DB-version); default is decision-deterministic.
- **Engine orchestration** runs deptry + osv **in parallel** through the `_engine_env()` normalization helper (temp-file output, `NO_COLOR=1`, `stdin=DEVNULL`, utf-8 decode → undecodable = typed error).

### 🚩 PRD deltas to land via `bmad-correct-course` (kept in sync)
New `indeterminate` verdict state (revises J9/FR20/status vocab) · name-level CVE tier (new FR) · bundled conda→pypi map (v1 asset) · DEP001-blocks-by-default with mapping-confidence (revises FR18/Gap-A) · kill symmetric positioning (coverage-by-artifact-resolvability: pixi.lock = vuln-hero, bare recipe = hygiene + risk-surface + lock-nudge) · no-version-assumption guardrail · direct-vs-locked coverage · **library-policy NFR revisions (P1 "lean not stdlib-only", S1 "no execution not no-imports")** · the E1 supported-construct matrix as an owned deliverable. *(FR9/D1 no longer changes — TOML reversal withdrawn.)*

## Implementation Patterns & Consistency Rules

*The generic web patterns (DB/API/REST/events/state/loading-UI) don't apply — this is a single-process, stdlib-lean Python CLI. These rules exist so parallel dev-agents/stories produce compatible code around the **one shared model, the canonical enums, and the security/determinism invariants**.*

### Module structure (by pipeline stage — one module per capability)
```
pyforge/warden/
  cli.py            # argparse surface, exit-code emission (FR29/31)
  config.py         # ConfigLoader — dual [tool.*] TOML, per-key precedence, policy tables (FR30)
  discovery.py      # FR1 — enumerate/classify manifests, resolved scan set
  routing.py        # FR2 — per-section ecosystem classification (conda vs pypi)
  extract/          # E1 — one submodule per format; NO execution primitives (S1)
    recipe_v1.py  meta_v0.py  environment_yml.py  pixi.py  pyproject.py  requirements.py
  inventory.py      # the ResolvedInventory + Component model (the spine)
  mapping.py        # bundled static conda→pypi map (v1 asset)
  engines.py        # _engine_env() + deptry/osv runners (parallel), output parse
  vuln.py           # osv input synthesis, name-level CVE tier, indeterminate classing
  hygiene.py        # deptry per-code join
  report.py         # ComplianceReport assembly + jsonschema validation
  sbom.py           # CycloneDX 1.6 via cyclonedx-python-lib
  verdict.py        # J9 lattice + 6→3 exit projection + status.driver
  waiver.py         # .yaml read (safe_load) + --bypass stanza emit (safe_dump)
  errors.py         # exception hierarchy → error_kind → exit code
  determinism.py    # canonicalization + --deterministic pinning
```
`tests/` mirrors it; fixtures in `tests/fixtures/{recipes,lockfiles,malicious}/`. *(Where this list and § Project Structure's tree differ — e.g. `models.py` — the § Project Structure tree is authoritative.)*

### The single-source-of-truth rules (highest-conflict)
- **ONE `Component` + `ResolvedInventory`** (frozen dataclasses in `inventory.py`) — every stage annotates the *same* objects; no stage re-defines a parallel shape. Identity + merge logic lives **only** here.
- **Canonical enums (StrEnum, never string literals):** `Status {clean, warn, policy-violation, error, bypassed, not-applicable, indeterminate}` · `ErrorKind {unparsable-manifest, engine-unavailable, engine-output-unrecognized, engine-output-unparseable, engine-execution-failed, engine-timeout, config-parse, config-validation, internal-error}` · `WithholdReason {no-version, unmapped-ecosystem, native-nonpypi, range-only}` · `Ecosystem {pypi, conda}`. Defined once; imported everywhere.
- **The verdict lattice + exit projection live only in `verdict.py`** — no other module maps a status to an exit code.

### Naming & typing
- `snake_case` functions/modules, `PascalCase` classes, `SCREAMING_SNAKE` constants; the helper is `_engine_env()`. Full type hints (py3.12 `X | None`, `list[...]`); `from __future__ import annotations`.

### Security invariants (enforced as code rules + meta-tests)
- **Extractor modules import no execution primitive** — no `eval`/`exec`/`compile`/`__import__`/`os.system`/`subprocess`/**`jinja2`**; `yaml.safe_load` only. Enforced by an AST-denylist meta-test over `extract/` (mirrors the CFE `test_actionable_scope` pattern).
- **Engine calls only via `_engine_env()`** — file-output to system-temp (never the scanned tree), `NO_COLOR=1`, `stdin=DEVNULL`, argv lists (**never `shell=True`**, never manifest-data as flags), explicit utf-8 decode → undecodable = typed error.
- **Temp files via `tempfile.mkstemp`/`mkdtemp`** (`0600`/`0700`); ~~the osv input file basename is literally `requirements.txt`~~ — the osv input may use any secure temp name via the `-L requirements.txt:<path>` parser override (Story 1.4).
- **Serialize only through a schema-aware encoder** (cyclonedx-python-lib for SBOM; `json.dumps` for the report) — never string-concatenate input-derived values (S7).

### Determinism discipline (NFR-R3b)
- **Never iterate a `set` for output** — `sorted()` every list before emit; JSON with `sort_keys=True`, fixed separators, `ensure_ascii`. No unguarded `datetime.now()`; the volatile-field set is pinned in `--deterministic` mode (timestamps, `serialNumber`/`bom-ref` from content hash, repo-relative paths, DB-version).

### Error & stream discipline
- **Content, never returncode:** the verdict reads report *content*; osv exit `1` is expected, `127`/`128` map to typed errors; a crash-with-no-output is a hard `error`, never empty-clean.
- **Streams:** report → **stdout**, all diagnostics → **stderr**; in `--format json`, stdout is one valid document **or empty** (pure-JSON invariant).
- **Errors:** one exception hierarchy in `errors.py`; each subtype carries its `ErrorKind` + owner; caught at the CLI boundary → typed report + exit code. No bare tracebacks reach stdout.

### Test conventions (the teeth)
- **pytest**; the **corpus-conformance gate** (0 uncaught exceptions across ~1,950 `recipes/*/{recipe.yaml,meta.yaml}`, ratcheted `unparseable_rate` baseline) + the **differential-oracle** test (E1 dep-set ⊇ rattler-build/conda-build render) + the **false-green=0** adversarial fixture gate + **twice-run byte-identical in `--deterministic`**. Security tests assert enforced *mechanisms* (AST-denylist, socket-guard, `mkstemp`, injected-timeout), not unprovable negatives.

## Project Structure & Boundaries

### Complete project tree (extends the existing scaffold)
```
src/shared/packages/pyforge-warden/
├── pyproject.toml              # deps: pyyaml, packaging, cyclonedx-python-lib, jsonschema (was [])
├── pixi.toml                   # run-deps: python, deptry, osv-scanner (+ the above libs)
├── README.md   .gitignore
├── src/pyforge/warden/
│   ├── __init__.py             # __version__
│   ├── cli.py                  # E4 — argparse, exit emission (FR29/31)  [replaces the stub]
│   ├── config.py               # ConfigLoader (FR30): dual [tool.*] TOML, precedence, policy tables
│   ├── models.py               # enums (Status/ErrorKind/WithholdReason/Ecosystem) + report/finding types
│   ├── inventory.py            # Component + ResolvedInventory (the spine; identity+merge)
│   ├── discovery.py            # FR1 — enumerate/classify manifests → resolved scan set
│   ├── routing.py              # FR2 — per-section ecosystem classification
│   ├── extract/                # E1 — non-execution zone (AST-denylist enforced)
│   │   ├── __init__.py         #   dispatch by format
│   │   ├── _jinja.py           #   context capture + safe-filter allowlist + selector marking
│   │   ├── recipe_v1.py  meta_v0.py  environment_yml.py  pixi.py
│   │   ├── lockfiles.py            #   pixi.lock + conda-lock.yml → locked-closure (the vuln hero path; ownership added 2026-07-12)
│   │   └── pyproject.py  requirements.py   # PyPI-delegate inputs
│   ├── mapping.py              # bundled static conda→pypi map loader (v1 asset)
│   ├── engines.py              # _engine_env() + deptry/osv runners (parallel) + output parse
│   ├── hygiene.py              # E2 — deptry per-code join → inventory
│   ├── vuln.py                 # E3 — osv input synth, name-level CVE tier, indeterminate classing
│   ├── report.py               # E4 — ComplianceReport assembly + jsonschema self-validate
│   ├── sbom.py                 # E4 — CycloneDX 1.6 via cyclonedx-python-lib
│   ├── verdict.py              # E4 — J9 lattice + 6→3 exit projection + status.driver
│   ├── waiver.py               # FR24-26 — .yaml read (safe_load) + --bypass stanza (safe_dump)
│   ├── errors.py               # exception hierarchy → ErrorKind → exit code
│   ├── determinism.py          # canonicalization + --deterministic pinning
│   └── data/
│       ├── report-schema.json  # the report data contract (schema_version)
│       └── conda_pypi_map.json # bundled conda→pypi identity map
└── tests/
    ├── conftest.py
    ├── fixtures/{recipes,lockfiles,malicious,engine-output}/
    ├── unit/            # per-module
    ├── meta/            # AST-denylist, no-jinja2-in-extract, SCRIPTS-runnable
    └── conformance/     # corpus (0-exceptions, ratcheted rate), differential-oracle, false-green=0, twice-run
```

### Boundary contracts
- **Internal spine (module boundary):** `ResolvedInventory` is the *only* cross-stage object. Discovery/routing/extract **produce** it; hygiene/vuln **annotate** it; report/sbom/verdict **read** it. No stage reaches around it.
- **Security boundary:** `extract/` is a **no-execution zone** — imports no execution primitive, no `jinja2`, `safe_load` only (AST-denylist meta-test). `engines.py` is the *only* module that spawns subprocesses, always via `_engine_env()`.
- **External contracts (versioned):** `report-schema.json` (`ComplianceReport`, `schema_version`) → stdout/`--output`; CycloneDX 1.6 SBOM → `--sbom-output`; the frozen exit-code enum `{0,1,2,130}`; the `[tool.pyforge-warden]` config-key schema. cf_atlas (FR-16/18, post-v1) consumes the report contract.
- **Trust boundary:** the waiver file + the offline OSV DB are **untrusted/verified inputs** — `waiver.py` validates schema + enforces expiry (integrity delegated to git/CODEOWNERS); the DB's trust-anchor is conda package integrity + build-date staleness.

### Epic → structure mapping
| Epic | Modules | FRs |
|---|---|---|
| **E1 — manifest bridge** | `discovery` · `routing` · `extract/*` · `mapping` · `inventory` | FR1–FR7 |
| **E2 — hygiene** | `engines`(deptry) · `hygiene` | FR8–FR9 |
| **E3 — vulnerability** | `engines`(osv) · `vuln` | FR10–FR13 |
| **E4 — report + gate** | `report` · `sbom` · `verdict` · `waiver` · `cli` · `config` · `determinism` · `errors` | FR14–FR31 + C0 |

### Data flow
`cli` → `config` → `discovery` → `routing` → `extract/*` → **`inventory`** → (`engines`: deptry ‖ osv in parallel) → `hygiene`/`vuln` annotate inventory → `report` + `sbom` (projections) + `verdict` (lattice → status + exit) → `cli` emits report (stdout) + exit code. Errors surface as typed `ErrorKind` at the CLI boundary; `--bypass` routes through `waiver`.

## Architecture Validation Results

### Coherence Validation ✅
Decisions cohere: the 7-stage pipeline, the single `ResolvedInventory` spine, the two-axis verdict, the false-green triad, the library policy, and the non-rendering E1 all fit without contradiction. The one live tension — `indeterminate` vs `not-applicable` masking a clean sibling axis — was resolved by the roundtable (the new state sits above `warn`). Patterns support the decisions (one model, canonical enums, security/determinism invariants as meta-tests); the structure realizes them (extract = no-execution zone; engines = sole subprocess site; verdict = sole exit-code owner).

### Requirements Coverage Validation ✅
- **FR1–FR31** each map to a module (Epic→structure table). No orphaned FR.
- **NFRs:** C0 → verdict + guard suite; S1–S8 → extract-no-exec / engine-runner / schema-aware serializer boundaries; NFR-R3b → `determinism.py` + `--deterministic`; NFR-P → parallel engines + offline DB; NFR-I1/I3 → `report-schema.json` + cyclonedx-python-lib + pure-JSON stdout; NFR-U1/U2 → actionable diagnostics + warn-only.
- **The 3 blocking Gaps (A/B/C) are resolved**; the connective-tissue open questions (discovery/routing/reconciliation/coverage-floor) are decided.

### Implementation Readiness Validation ✅
Decisions are documented with the pinned engine contracts + versions; patterns are enforceable (AST-denylist, sort-before-emit, `_engine_env()`); the project tree is complete and specific (extends the real scaffold); module boundaries + data flow are explicit. A parallel dev-agent has a single canonical model + enums + verdict owner to build against.

### Gap Analysis Results
**Critical (blocks implementation):** none.
**Important (first-story work, non-blocking):**
1. **Bundled conda→pypi map asset** (`data/conda_pypi_map.json`) doesn't exist yet — but the atlas already produces the mapping (`export-purls` → conda↔pypi TSVs), so it's a **generate-from-atlas** task, not new research.
2. **Name-mapping confidence threshold** for DEP001-blocks (what counts as "high-confidence" → block vs "ambiguous" → warn) — pick a concrete rule (e.g. exact-map hit vs. multi-spelling guess).
3. **Coverage denominator formula** (`manifests_parsed/found` vs `deps_with_version/total`) — Amelia's flag; emit both as fields, pick the gate default.
4. **Offline-DB provisioning mechanism** — confirm whether an osv-DB conda package exists to depend on, or the tool ships a `download-offline-databases` provisioning step.

**Minor:** the P-warm p95 threshold + `--db-max-age` default need calibration against the reference corpus.

### Validation Issues Addressed
The false-green triad + the Gap-C ecosystem-identity predicate + the E1 non-rendering strategy were the substantive issues, all resolved in § Core Architectural Decisions. One **cross-document caveat**: the architecture revised ~7 PRD-locked decisions (new `indeterminate` state, DEP001-blocks, name-level tier, library policy, kill-symmetric-positioning, etc.) — the **PRD is temporarily inconsistent until a `bmad-correct-course` pass lands those deltas** (the 🚩 list). This is scheduled next; it's why the status below is "with minor gaps," not fully turnkey.

### Architecture Completeness Checklist
**Requirements Analysis** — [x] context analyzed · [x] scale/complexity assessed · [x] constraints identified · [x] cross-cutting concerns mapped
**Architectural Decisions** — [x] critical decisions documented with versions · [x] tech stack fully specified · [x] integration patterns defined · [x] performance addressed (3 budgets; thresholds to calibrate)
**Implementation Patterns** — [x] naming conventions · [x] structure patterns · [x] communication (module/data-flow) · [x] process (error/determinism/security)
**Project Structure** — [x] complete tree · [x] component boundaries · [x] integration points · [x] requirements→structure mapping

### Architecture Readiness Assessment
**Overall Status: READY WITH MINOR GAPS** — all 16 checklist axes covered and no Critical Gaps; downgraded from fully-ready by the 4 bounded first-story items + the pending PRD reconciliation.
**Confidence: HIGH** — the design was adversarially stress-tested (two roundtable rounds) and the sharpest defect (beachhead false-green) was caught and fixed before ratification.
**Key strengths:** the never-false-green acceptance spine (C0 → triad → guards); the single-model + canonical-enum discipline; the non-rendering-by-construction security posture; the honest coverage contract grounded in real engine + recipe-format facts.
**Future enhancement:** KEV gate tier · SARIF · cf_atlas promotion · full conda↔PyPI reconciliation · the baseline ratchet (all deferred-Growth).

### Implementation Handoff
**AI agent guidelines:** follow § Core Architectural Decisions + § Implementation Patterns exactly; use the single `ResolvedInventory` + canonical enums; keep `extract/` execution-free; route all subprocesses through `_engine_env()`; sort before every emit.
**First implementation priority:** complete-the-scaffold — wire E1 (`discovery` → `routing` → `extract/*` → `inventory`) into the `cli.py` stub + stand up the corpus-conformance + differential-oracle harness, then generate `data/conda_pypi_map.json` from the atlas.
**Execution model (2026-07-12 — "Option B"):** stories are driven by **`bmad-dev-auto`** sessions orchestrated by **`bmad-loop`** (`DEV → VERIFY → REVIEW → VERIFY → COMMIT`; policy at `.bmad-loop/policy.toml`), per `docs/specs/bmad-loop-adoption.md`. The deterministic `[verify]` gate is `pixi run -e pyforge-warden pyforge-warden-test` — so the 1.1/1.2 contract tests + C0a/C0c gates mechanically police every later story. Gates graduate: `per-story-spec-approval` (1.1/1.2) → `per-epic` (E2+). The epics' Given/When/Then ACs are the contract dev-auto's spec conversion must preserve verbatim; CRITICAL escalations resolve via `bmad-loop-resolve`; the sprint feed is `sprint-status.yaml` from `bmad-sprint-planning`.
