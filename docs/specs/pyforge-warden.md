---
status: in-progress
spec_updated: 2026-07-14
---
# Tech Spec: `pyforge.warden` (**Warden**) — Python dependency **compliance gate** (multi-axis)

> **Naming (recorded here as source of truth).** **Warden** = the product /
> brand (display name only — bare `warden` is taken on public PyPI, not
> claimed). **pyforge** = the internal team / namespace (also taken bare on
> PyPI — namespace only). **pyforge-warden** = the distribution name
> (PyPI/conda) and the BMAD project slug. **`pyforge.warden`** = the import
> package (PEP 420 namespace, `src/pyforge/warden/`). **`warden`** = the CLI
> entry point (`console_scripts: warden = pyforge.warden.cli:main`). Product
> name ≠ distribution name is **intentional** (internal-first per OD5; public
> names verified at closeout). The intake-note filename convention below is
> preserved as a historical note under the Warden brand.

> **BMAD intake document.** **Warden** is a **pluggable, multi-axis Python
> dependency compliance gate.** v1 orchestrates `deptry` (hygiene) and
> Google's `osv-scanner` (security) over Python / Conda / Pixi manifests;
> v1.x adds a **license** axis and a **currency / supportability** axis and
> **KEV/EPSS** enrichment on the security axis (see the Post-scope-change
> reconciliation callout below). Written to be self-contained: it folds
> the Analyst brief, PM PRD, Architect design, and story sharding into one
> file as the self-contained source of truth for the **full BMAD** chain.
>
> The full BMAD planning chain (PRD → architecture → epics/stories → dev)
> runs against this spec under the `pyforge-warden` BMAD project
> (`_bmad-output/projects/pyforge-warden/`).
>
> Scope: **5 epics / 20 stories** (see the reconciliation callout below —
> originally scoped ~4 epics / ~12–16; `epics.md` supersedes), driven through
> the **full BMAD** flow (not Quick Flow).
>
> **Conda-forge tie-in (Rules 1 & 2).** If the effort packages
> `pyforge.warden` (or any of its scanning engines) as a conda recipe, or
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

## ⚠️⚠️ Post-scope-change reconciliation (2026-07-14) — READ FIRST (WINS over the whole body)

The effort was **reframed from a two-engine scanner into a pluggable,
multi-axis compliance gate** and **renamed to Warden**. Where anything below
still says "two engines (deptry + osv-scanner)" or "hygiene + vulnerability
only," **this callout wins.** The PRD (`prd.md`), architecture, and epics
carry the same reframe.

**The axes and their exact tools / data sources:**

| Axis | Ships | Engine / source |
|---|---|---|
| **1 — Hygiene** | **v1** | `deptry` |
| **2 — Security** | **v1** | `osv-scanner` (Google OSV) — **+ v1.x enrichment:** CISA **KEV** catalog + FIRST **EPSS** score |
| **3 — License** | **v1.x (NEW)** | normalizer **`license-expression`** (nexB/AboutCode); sources = conda recipe `about: license:` (+ `license_family`) and PyPI package metadata via stdlib `importlib.metadata` (PEP 639 `License-Expression`, legacy `License`, `Classifier: License ::` trove). **No source scanning**; ScanCode Toolkit deep-scan is **deferred (post-v1.x)**. |
| **4 — Currency / Supportability** | **v1.x (NEW)** | **endoflife.date** + version-lag of the resolved set; covers each dependency **and** the Python runtime (LTS / N / N-1 / not-EOL). |
| **5 — Provenance** | vision (name only) | Sigstore / SLSA attestation. |
| **6 — Maintenance** | vision (name only) | OpenSSF Scorecard. |

**Release sequencing (stated in every artifact):**
- **v1** = Axis 1 (hygiene) + Axis 2 (security).
- **v1.x** = + Axis 3 (license via `license-expression`) + Axis 4 (currency via endoflife.date) + KEV/EPSS enrichment on Axis 2.
- **Provenance + Maintenance = future (vision)** — out of scope now.

**Runtime-dependency policy (lean; precise).** ADD **exactly one** runtime
dep: **`license-expression`**. endoflife.date + KEV + EPSS are
**fetched-and-cached data feeds** — **offline stays the default**; any online
query is **opt-in and never silent** (NFR-S2). Unchanged runtime deps: PyYAML
(`safe_load` only), `packaging`, `cyclonedx-python-lib`, `jsonschema`; stdlib
`tomllib`, `re`, `importlib.metadata`. Engines `deptry` + `osv-scanner` stay
declared conda/pixi run-deps (never pip, never runtime `curl`).

**New CLI flags** (specced in FR-L*/FR-C*/FR-K* below):
- License: `--allow-licenses <SPDX,…>` · `--deny-licenses <SPDX,…>`
- Currency: `--max-lag <n>` · `--require-lts` · `--fail-on-eol`
- Security: `--fail-on-kev` · `[--min-epss <0..1>]`

**`ComplianceReport` / `report-schema.json` — additive, VERSIONED** (bump
`schema_version`; `validate_report.py` + fixtures updated so the contract
can't silently drift):
- **security** findings gain `kev` (bool), `kev_date`, `epss {score, percentile}`.
- new **`license`** section: per-component `spdx_expression`, `license_family`, `source`, `allowed | denied | unknown`.
- new **`currency`** section: per-component `latest`, `lag`, `eol_date`, `supported | eol | unknown`; **+ `runtime_python`** currency.
- **coverage** + **provenance** (`{source, snapshot_at}`) for the new axes, same as security.

**PRESERVED (do not regress):** the verdict lattice `error > policy-violation
> indeterminate > warn > bypassed > clean > not-applicable`; exit enum
`{0,1,2,130}`. **Unproven license/currency → `indeterminate` (non-zero),
never a silent pass.** Honest-adoption posture (no false greens);
producer-agnostic report; "no execution of untrusted input." Do NOT touch
`recipes/` (CLAUDE.md Rules 1 & 2 stay disengaged).

---

## ⚠️ Post-architecture reconciliation (2026-07-11) + Phase-0 review pass (2026-07-12) — READ FIRST

The architecture phase (`_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md`, status: complete) and the 2026-07-12 Phase-0 deep review (full findings: gist `326be5f25e702e0fcce343046c70a6b2`) revised decisions this spec still states in their original form. **Where the body below conflicts, this list wins** — the PRD carries the same reconciliation callout; `architecture.md` § Core Architectural Decisions has the detail.

1. **Library policy (supersedes NFR2 + OD3 + Story 1.1's "no pyyaml" AC):** extraction is no longer stdlib-only — the constraint is **"no *execution* of untrusted input"** (no eval/exec/subprocess-in-extractor, no Jinja render, `yaml.safe_load` only). Lean targeted runtime deps: PyYAML (`safe_load`/`safe_dump`), packaging, cyclonedx-python-lib, **jsonschema (runtime, not test-only** — FR14 report self-validation). v1 `recipe.yaml` is `safe_load`-parsed directly; v0 `meta.yaml` is neutralized then `safe_load`-parsed.
2. **Execution model (supersedes OD6 + data-flow step 3):** the two engines run **in parallel** (NFR-P-concurrency), not sequentially.
3. **Verdict lattice + exit enum (supersedes FR4/FR5's status list + exit codes):** the status enum gains **`indeterminate`** (above `warn`): `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`; the canonical token is `warn` (not `warnings`). Frozen exit enum **`{0, 1, 2, 130}`**; the 7→4 projection maps **`indeterminate` → exit 1** (decided 2026-07-12: exit 2 stays reserved for operational errors — an indeterminate run is trustworthy and honestly reports unproven cleanliness). Withheld / skipped / unresolved outcomes route to `indeterminate` → non-zero, **never** a silent 0.
4. **Gate default (supersedes FR5's "critical CVE or KEV"):** v1 blocks on **CVSS-critical only**; the KEV tier is post-v1 (annotation-only if osv emits it natively at zero new data source).
5. **Discovery (supersedes data-flow step 1's priority order):** **union coverage** — all discovered manifests are scanned and reported per-manifest; there is no single-winner priority chain.
6. **osv input (supersedes step 2's `.scanner-temp-reqs.txt` + the "installed env" fallback):** the synthesized osv input is a temp file named **`requirements.txt`** (osv infers the parser from the basename; the `--lockfile=<parser>:<path>` override is to be verified in Story 1.4); the "installed env" fallback is **dropped** (conflicts with the pre-build posture — never assume a version).
7. **Story sharding (supersedes § Story sharding):** the breakdown is now **5 epics / 20 stories** in `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` (this header originally said ~4 epics / ~12–16 stories). § Story sharding below is historical intent only.
8. **Repo layout detail:** `report-schema.json` lives at `src/pyforge/warden/data/` (beside the bundled `conda_pypi_map.json`), not the package root.
9. **Honest-adoption statement (new, load-bearing):** a bare `recipe.yaml` scan **exits non-zero by design** until the project locks (`pixi.lock`), waives (expiring, auditable), or runs `--warn-only` — that is the lock-nudge working, not a bug. The recommended **first contact** with the tool is a local `--warn-only` run at a developer terminal (see § Local / workstation mode), not a CI wiring.
10. **Implementation execution model (2026-07-12, user decision "Option B"):** the 20 stories run **loop-driven** — `bmad-loop` orchestrating `bmad-dev-auto` sessions (`DEV → VERIFY → REVIEW → VERIFY → COMMIT`), per `docs/specs/bmad-loop-adoption.md`. Each story's Given/When/Then ACs are the contract the dev-auto spec conversion must preserve; the loop's deterministic `[verify]` command is the scanner's own pytest task (the 1.1/1.2 harness + C0 gates thereby police every later story); gates graduate: `per-story-spec-approval` (1.1/1.2, the contract freeze) → `per-epic` (Epic 2+) → revisit `none` for the tail. Escalations resolve interactively via `bmad-loop-resolve`.

---

## Status

| Field | Value |
|---|---|
| Status | **In progress** — planning COMPLETE (PRD + architecture + readiness + **epics/stories: 5 epics / 20 stories**, committed); implementation next (Story 1.1). All decisions resolved (§ Decisions + the reconciliation callout above) |
| Scope | **Python only** — PyPI + conda-forge, 6 Python/conda manifest formats; non-Python ecosystems out of scope (see § Scope & naming in the intake note) |
| Owner | rxm7706 |
| Track | **Full BMAD** (PRD → architecture → epics/stories → **loop-driven dev**) — planning artifacts under `_bmad-output/projects/pyforge-warden/`. Implementation runs via **bmad-loop v0.8.1 + bmad-dev-auto** (BMAD 6.10) per `docs/specs/bmad-loop-adoption.md` — graduated gates (per-story-spec-approval for 1.1/1.2 → per-epic from Epic 2), deterministic verify gate = the scanner's own test suite |
| Proposed project slug | `pyforge-warden` (BMAD artifacts → `_bmad-output/projects/pyforge-warden/`) |
| Python package | module `pyforge.warden`; dist name `pyforge-warden` |
| Source root | **In-repo pixi *build* workspace member** at `src/shared/packages/pyforge-warden/` (Option B; unity-data-stack `src/shared/packages` convention) — see § Repository layout |
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

**MVP idea.** A unified Python CLI (`pyforge.warden`) that orchestrates
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
   inputs). `pyforge.warden` partially re-implements that surface. Whether
   it should be a standalone external tool or reuse/extend the existing
   infra is an explicit decision (OD4), not a silent one.

3. **`fawltydeps` and `pip-check-reqs` are adjacent alternatives** to
   `deptry` for the unused-dependency job. The MVP picks `deptry` as the
   hygiene engine; the other two are candidate future backends (§ Future).

---

## Goals

*(Scope-change 2026-07-14: the goals below frame the v1 hygiene+security core;
the v1.x axes — license, currency, KEV/EPSS — extend G1's "single consolidated
report" and G3's "strict gate" to all axes. See the top callout.)*

- **G1.** One CLI (`warden`) that produces a single consolidated **multi-axis**
  compliance report (v1: hygiene + security; v1.x: + license + currency) from
  one invocation at a repo root.
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
  `error` | `bypassed` | `not-applicable`) *(status vocabulary superseded —
  callout #3: + `indeterminate` above `warn`; canonical token `warn`)*,
  per-finding **severity** (CVSS
  + KEV for CVEs; hygiene defaults to `warning`), per-manifest **coverage**,
  `error_kind` (FR10), and `review_required` / `bypass` (FR9). *(Scope-change
  2026-07-14: the report is additionally sectioned by axis — it gains a
  `license` section (FR-L1) and a `currency` section (FR-C1) with their own
  coverage + provenance, and security findings gain `kev`/`kev_date`/`epss`
  slots (FR-K1). The schema is **versioned** on this change. See the top
  callout for the exact field list.)*
- **FR5.** **Severity-tiered CI gate.** The exit code encodes the policy
  result, not a binary pass/fail: **0** = clean, or only findings *below*
  the fail-threshold (reported as **warnings**, non-blocking), or an audited
  `--bypass` (FR9); **1** = ≥1 finding *at/above* the threshold
  (**policy-violation** → blocks merge); **2** = operational **error**
  (FR10; non-relaxable except via the audited bypass). The **fail-threshold
  is configurable** — `--fail-on=<severity>`, or the atlas FR-18 knobs
  `max_critical` / `max_high` / KEV. **Default: block on any critical CVE or
  KEV-affecting-current; warn on high/medium/low + all hygiene.** *(Revised —
  callout #4: the v1 default blocks on CVSS-critical only; KEV deferred
  post-v1.)* This
  replaces a hard "any finding blocks" gate, which drives teams to disable
  the gate entirely (the NFR1 anti-goal). *(Scope-change 2026-07-14: the gate
  is **multi-axis**. Additional v1.x knobs — security `--fail-on-kev` /
  `--min-epss` (FR-K1); license `--allow-licenses` / `--deny-licenses`
  (FR-L2); currency `--max-lag` / `--require-lts` / `--fail-on-eol` (FR-C2).
  A **denied** license or an EOL/over-lag component → `policy-violation`
  (exit 1); an **unknown/unproven** license or currency → `indeterminate`
  (exit 1), never a silent clean.)*
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
  `.warden-waivers.yaml`; the tool **reads** it and never
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

*(New FRs for the multi-axis scope — 2026-07-14. FR1–FR10 above are the v1
hygiene+security core; the axes below ship v1.x. All feed the same
`ComplianceReport` + verdict lattice; unproven → `indeterminate`, never a
silent pass.)*

- **FR-K1 — KEV/EPSS enrichment (Axis 2, v1.x).** Enrich each security
  finding with the **CISA KEV** flag (`kev`, `kev_date`) and the **FIRST
  EPSS** score (`epss {score, percentile}`), from cached data feeds (offline
  default; opt-in online, never silent). New gate knobs: `--fail-on-kev`
  (block when a matched advisory is KEV-listed) and optional `--min-epss
  <0..1>` (block at/above an EPSS threshold). Absent enrichment data → the
  slots stay null and the finding gates on CVSS as before (never a false
  clean).
- **FR-L1 — License axis (Axis 3, v1.x).** For every resolved component,
  determine its license: normalize to an **SPDX expression** via
  `license-expression` from (a) the conda recipe `about: license:` (+
  `license_family`) and (b) PyPI metadata via stdlib `importlib.metadata`
  (PEP 639 `License-Expression`, legacy `License`, `Classifier: License ::`
  trove classifiers). **No source scanning** (ScanCode is deferred). Emit a
  per-component `license` finding: `spdx_expression`, `license_family`,
  `source`, and a verdict `allowed | denied | unknown`.
- **FR-L2 — License policy gate.** `--allow-licenses <SPDX,…>` /
  `--deny-licenses <SPDX,…>` set the allow/deny sets (SPDX ids/expressions).
  A **denied** license → `policy-violation` (exit 1). An **unknown /
  unresolvable** license → **`indeterminate`** (exit 1) — never a silent
  clean; copyleft & unknown-license exposure surface here, not by omission.
- **FR-C1 — Currency / supportability axis (Axis 4, v1.x).** For every
  resolved component **and the Python runtime**, compute
  currency from **endoflife.date** + version-lag of the resolved set: emit
  `latest`, `lag` (releases/versions behind), `eol_date`, and a verdict
  `supported | eol | unknown` (LTS / N / N-1 / not-EOL classification).
  `runtime_python` currency is a first-class field.
- **FR-C2 — Currency policy gate.** `--max-lag <n>` (block when a component's
  lag exceeds `n`), `--require-lts` (block on non-LTS runtimes/deps where an
  LTS exists), `--fail-on-eol` (block on an EOL component or runtime). An
  **unknown** currency (no endoflife.date coverage / no resolved version) →
  **`indeterminate`**, never a silent pass.

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
- **NFR4 — Fleet observability.** Errors and axis coverage are reportable
  across a 20k-repo fleet by `error_kind` + per-axis `coverage` (referenced
  by FR10), so a partial-coverage run never masquerades as a complete clean.
- **NFR5 — Lean runtime dependencies + no-execution (scope-change
  2026-07-14).** The multi-axis expansion adds **exactly one** runtime dep:
  **`license-expression`**. The currency (endoflife.date) + security-KEV/EPSS
  data are **fetched-and-cached feeds**, not runtime libraries — **offline is
  the default; any online query is opt-in and never silent** (NFR-S2). The
  unchanged runtime set stays PyYAML (`safe_load` only) / `packaging` /
  `cyclonedx-python-lib` / `jsonschema` + stdlib `tomllib` / `re` /
  `importlib.metadata`; engines `deptry` + `osv-scanner` remain declared
  conda/pixi run-deps. The binding constraint is **no execution of untrusted
  input** (supersedes NFR2's "stdlib-only" per callout #1).

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
| conda package (`.conda`) | `pixi-build-python` (wraps the hatchling wheel) | `pyforge-warden-build-conda` |
| pypi wheel (`.whl`) | `python -m build` (hatchling) | `pyforge-warden-build-dist` |
| sdist (`.tar.gz`) | `python -m build` (hatchling) | `pyforge-warden-build-dist` |

`pyforge-warden-build` runs all three; the path dependency also builds+installs
the conda package into the dev env on `pixi install`.

```
local-recipes/
├─ pixi.toml                          # root [workspace]; preview = ["pixi-build"];
│                                     #   [feature.pyforge-warden.*] + lean env + build tasks
├─ src/
│  ├─ sentinel/                       # existing in-repo app (wiki/knowledge)
│  └─ shared/packages/pyforge-warden/ # the workspace MEMBER (no [workspace] table)
│     ├─ pixi.toml                    #   [package] + [package.build.backend]=pixi-build-python
│     ├─ pyproject.toml               #   hatchling; entry point pyforge.warden.cli:main
│     ├─ src/pyforge/warden/          #   E1 extractor.py · E2/E3 runners · E4 report.py + cli.py
│     ├─ report-schema.json           #   FR6 (E4)
│     └─ tests/
└─ docs/specs/pyforge-warden.md
```

- **Runtime engines** (`deptry`, `osv-scanner`) are the member's conda
  `[package.run-dependencies]` (OD1) — never pip, never runtime `curl`.
- **Dedicated lean env**: `[environments] pyforge-warden` uses
  `no-default-feature = true`, so it excludes the repo's fat default toolchain
  (python 3.14 + pixi + conda + pip + uv) and carries only the built package +
  its run-deps + build/test tooling (NFR1/NFR2). Tasks: `warden-scan`,
  `pyforge-warden-test`, `pyforge-warden-build{,-conda,-dist}`.
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
/ `conda-lock.yml` — pyforge-warden's manifest engine bridges them. Non-Python
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
  `security` (advisory findings from E3 — **v1.x:** each with `kev`/`kev_date`/
  `epss`), and a `summary` (counts + overall pass/fail). *(Scope-change
  2026-07-14: the report is axis-sectioned — **v1.x adds** a `license` section
  (per-component `spdx_expression` / `license_family` / `source` /
  `allowed|denied|unknown`) and a `currency` section (per-component `latest` /
  `lag` / `eol_date` / `supported|eol|unknown`, plus `runtime_python`), each
  with its own `coverage` + `provenance {source, snapshot_at}`. The schema
  carries a **`schema_version`** bumped on this additive change; the additions
  are backward-compatible — `additionalProperties` stays open and the frozen
  keys are unchanged.)*
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
  itself; `pyforge.warden` adds no additional network side effects beyond
  the two engines.

---

## Story sharding (Product Owner) — SUPERSEDED (historical)

> **Superseded 2026-07-11** by the full breakdown in
> `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md`
> (5 epics / 20 stories, roundtable-validated). Retained as historical intent;
> Story 1.1's "no heavy external parser" AC is void per callout #1.

Story 1.1 was specified in full; the rest were seeded stubs for
`bmad-create-story` expansion.

### Story 1.1 — Core Manifest Extractor (E1)

> **Context.** Before scanning with Deptry or OSV, we need a unified
> interface to read dependencies without external parsers, keeping the
> runner lightweight.
>
> **Implementation guidance.**
> - Create `pyforge/warden/extractor.py`.
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
  osv-native), so pyforge-warden synthesizes a **version-pinned
  `requirements.txt`** from `pixi.lock` / `conda-lock` / the installed env
  where available; name-only is the last-resort fallback, its weaker
  coverage flagged in the report. See § Engine-native support.
- **OD3 — stdlib-only YAML → RESOLVED (a).** Hold the line on stdlib
  `re`/`tomllib` for v1, backed by an explicit fixture suite
  (Jinja-bearing `recipe.yaml`, nested `pip:` in `environment.yml`). An
  optional light YAML dep is deferred to § Future, taken up only if
  fragility surfaces. **[SUPERSEDED 2026-07-11 — callout #1: lean-lib policy;
  `safe_load` is in; the constraint is no-execution, not stdlib-only.]**
- **OD4 — relationship to `scan-project` → RESOLVED (standalone for v1,
  integrate after).** `pyforge.warden` is a standalone tool for v1, not
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
  exit-2, non-relaxable except via the recorded bypass. **[PARTIALLY
  SUPERSEDED — callout #2/#3/#4: the engines now run in PARALLEL; the status
  lattice gains `indeterminate` (→ exit 1); the v1 default blocks on
  CVSS-critical only (KEV deferred).]**

**New Core Architectural Decisions (2026-07-14 scope change — multi-axis gate):**

- **OD7 — Axis-plugin model.** Warden is one report + one verdict lattice
  fed by **pluggable axis strategies** (a small `Axis` interface: `assess()
  → findings + coverage + provenance`), each independently enable/disable-able
  and each composing into the same `ComplianceReport` and the same exit
  projection. v1 registers **hygiene** (deptry) + **security** (osv-scanner);
  v1.x registers **license** + **currency**; provenance/maintenance are
  reserved axis slots (vision). This keeps the never-false-green invariant
  central (verdict owns projection; axes only feed rungs) and makes each new
  axis additive to the frozen contract, never an editor.
- **OD8 — License source strategy (metadata, not source scan).** Resolve
  licenses from **package/recipe metadata only** — conda recipe `about:
  license:` (+ `license_family`) and PyPI metadata via stdlib
  `importlib.metadata` (PEP 639 `License-Expression`, legacy `License`,
  `Classifier: License ::` trove) — and normalize to SPDX via the one new
  runtime dep **`license-expression`** (nexB/AboutCode). **No source
  scanning**: ScanCode Toolkit deep-scan is deferred (post-v1.x) as it would
  break the lean-deps + fast-fleet posture (NFR1/NFR5). Unresolvable →
  `unknown` → `indeterminate` (never a silent allow).
- **OD9 — Currency source strategy (endoflife.date + lag).** Compute
  supportability from **endoflife.date** (cached offline; opt-in online,
  never silent) plus **version-lag** of the resolved set, for each dependency
  **and the Python runtime** (LTS / N / N-1 / not-EOL). No endoflife.date
  coverage or no resolved version → `unknown` → `indeterminate`.
- **OD10 — KEV/EPSS enrichment (cached feeds, annotate + optionally gate).**
  Enrich osv findings with **CISA KEV** + **FIRST EPSS** from cached data
  feeds (offline default). v1.x annotates every security finding and adds
  `--fail-on-kev` / `--min-epss` gate knobs; absent feed data leaves the
  slots null and gates on CVSS (never a false clean). This is the producer
  populating the KEV/EPSS slots Story 1.1 froze into the schema empty.

---

## Local / workstation mode (P8 — added 2026-07-12)

The primary consumer is a CI pipeline, but the tool has a **supported
secondary mode: a developer at a terminal** (persona P8). Three local use
cases are real and one is load-bearing:

1. **Pre-push testing** — verify a fix clears a finding / trial the gate
   before wiring CI (adoption realistically starts here — J6's warn-only
   on-ramp begins at a terminal).
2. **Waiver authoring — already local-only by design:** `--bypass` emits the
   stanza *for the human to commit* (the tool never writes the repo, NFR-S4),
   which CI cannot do.
3. **Environment debugging** — reproducing an `engine-unavailable` exit 2
   outside the runner image.

Mechanically nothing changes (same argparse CLI, `--format text` default, TTY
color auto-detection, zero prompts). **Local mode must not soften the gate** —
same lattice, same exit codes, same fail-loud. The workstation-only deltas are
story-owned: cold-start provisioning UX + the explicit online-vuln-query
decision (Story 1.4 — offline stays the fleet default; any online mode is
opt-in and never silent, per NFR-S2), and the workstation install story
(Story 5.1 docs; `pixi global install` / the local channel now, conda-forge
per OD5 later). A `doctor` self-check subcommand is re-ranked **v1-if-cheap**
(it is FR21's engine/DB detection logic re-exposed).

**nebi + prefix-ecosystem notes (2026-07-12 survey).** A
[nebi](https://github.com/nebari-dev/nebi)-managed team environment **is a
pixi workspace** (`pixi.toml` + `pixi.lock`) — so `nebi pull <ws>:<tag>` →
`scan .` works with **zero new code**; and because nebi versions environments
while the scanner is decision-deterministic (NFR-R3b), scanning two pulled
versions yields **meaningfully diffable `ComplianceReport`s** ("did our env
upgrade introduce CVEs?"). Distribution channels for the scanner env itself
(named in Story 1.4's decision record): `pixi global install` (online) ·
**pixi-pack/unpack** (air-gapped single-archive bundles) · **nebi push/pull**
for nebi-adopted teams (OCI registries; alpha — a candidate, not the
recommended primary path for a security gate yet). The scanner stays
**nebi-agnostic but nebi-compatible**.

## Positioning vs the in-house gates (which tool when)

This repo fields three (going on four) scanning/gating surfaces. The
differentiation, stated once:

| You have | Use |
|---|---|
| Any repo, any org, **no atlas**; need a CI/terminal gate on **your pinned deps** (hygiene + CVEs) | **pyforge-warden** (this tool — the fleet edge; zero data estate) |
| The atlas host; need gap/version-lag buckets (ADD/UPDATE/CURRENT), freshness-percentile policy, packaging worklists | `inventory-match --policy` (+ `add-handoff`) — CFE v8.71+ |
| Anything exotic — containers, K8s, live envs, third-party SBOMs, non-Python ecosystems | `scan-project` (CFE) |
| The migrated Kedro pipeline (future) | the FR-18 terminal gate — assembles **this tool's** `ComplianceReport` schema |

Key non-overlap: `inventory-match`'s vuln signal reads atlas rollups for the
**current conda-forge version** (`vuln_*_affecting_current`); this tool scans
**your pinned/locked versions** via osv-scanner. Complementary, not redundant.

## Cross-spec impact & sync (obligations owned by this effort)

Per the repo's cross-spec sync discipline, the shared-contract facts this
effort touches and the obligations they create:

1. **Exit-code convergence (the sharpest).** This tool's frozen enum
   `{0 pass, 1 policy-violation, 2 error, 130 SIGINT}` and the shipped
   `inventory-match --policy` gate (`0 pass, 2 policy-violations, 1 error` —
   cyclonedx-universe-inventory S5) are **inverted**. The Kedro FR-18 unified
   gate is specced to the **this-tool convention** — so `inventory-match`
   must flip its exit semantics at (or before) convergence, a breaking change
   for its CI consumers needing a deprecation window. Recorded as an
   amendment in `cyclonedx-universe-inventory.md` § Cross-spec impact & sync;
   owned at the FR-18 implementation.
2. **Two producers of `ComplianceReport`.** Kedro FR-16/FR-18 assemble this
   schema with a different security source (atlas vdb + CISA-KEV + EPSS —
   not osv-scanner). Story 1.1 freezes the schema **producer-agnostically**:
   generic vuln-data provenance (`{source, snapshot_at, max_age_ok}`),
   optional KEV/EPSS slots (v1 never populates them), severity carrying tier
   + raw evidence.
3. **Source-less hygiene semantics are shared.** Kedro FR-16 already specs
   "deptry runs when project source accompanies the manifest; source-less
   inputs skip gracefully, reduced scope recorded." This tool adopts the
   identical semantic (hygiene axis `not-applicable`, honestly scoped) — the
   fleet's majority repo shape (feedstocks) is source-less.
4. **SBOM conventions.** The `cfe:*` property namespace (`cfe:pypi_purl`,
   `cfe:match_source`, `cfe:match_confidence`) + G98 purl normalization
   (lowercase, `_`→`-`, dots preserved, `?channel=` qualifier) are
   estate-pinned; Story 4.1 adopts them (round-trip AC: `scan-project
   --sbom-in` ingests our BOM).
5. **The bundled conda→pypi map** is generated from the atlas `export-purls`
   TSVs **preserving `match_source`/`match_confidence`** — the DEP001-block
   confidence rule reads those tiers (parselmouth / recipe_source_url →
   block-eligible; name_coincidence → warn; none → withheld).
   `prefix-dev/purl-associator` is a second corroborator, and the generator
   supports a **parselmouth-direct refresh mode** (consume
   `prefix-dev/parselmouth`'s published mapping artifacts — the same source
   pixi's default `conda-pypi-map` uses) so the map is regenerable by orgs
   **without** this repo's atlas (added 2026-07-12).
6. **Parse-parity matrix (promotion prerequisite).** The Kedro "promotion is
   wiring, not redesign" claim assumes E1 ↔ `scan_project` parser parity;
   known deltas (selector-union vs skip; `run_constraints` handling) are
   recorded, and a parity matrix is a retro obligation.

---

## Definition of Done

- [x] All decisions (OD1–OD6) resolved (§ Decisions); `status: ready`.
      Next transition: `in-progress` when a dev agent picks it up.
- [ ] E1–E4 stories implemented with passing unit tests (all six manifest types).
- [ ] `pyforge.warden` runs clean on this repo's own `pixi.toml` /
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

**v1.x DoD (multi-axis scope, 2026-07-14):**
- [ ] **KEV/EPSS enrichment (FR-K1):** security findings carry `kev`/`kev_date`/
      `epss`; `--fail-on-kev` / `--min-epss` gate; cached feeds, offline default.
- [ ] **License axis (FR-L1/L2):** SPDX via `license-expression` (the one new
      runtime dep) from conda `about:` + PyPI `importlib.metadata`; `license`
      report section; `--allow-licenses` / `--deny-licenses`; denied →
      policy-violation, unknown → indeterminate. No source scanning.
- [ ] **Currency axis (FR-C1/C2):** endoflife.date + lag for deps **and**
      `runtime_python`; `currency` report section; `--max-lag` / `--require-lts`
      / `--fail-on-eol`; EOL → policy-violation, unknown → indeterminate.
- [ ] **Schema versioned:** `schema_version` bumped; `validate_report.py` +
      fixtures updated for the new sections; the frozen v1 keys unchanged.
- [ ] Release sequencing honored: v1 shipped hygiene+security; v1.x adds the
      above; provenance + maintenance remain vision (unbuilt).

---

## Future / backlog (out of MVP scope)

- **Promote into the conda-forge-atlas / `conda-forge-expert` scope
  (planned follow-on — the intended end state once v1 ships).** Expose
  `pyforge.warden` inside the atlas intelligence layer as an MCP tool +
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
- **Complementary SAST layer.** `pyforge.warden` is SCA (dependency
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
