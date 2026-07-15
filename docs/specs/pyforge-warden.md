---
status: in-progress
spec_updated: 2026-07-15
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
> dependency compliance gate.** v1 runs **four axes** over Python / Conda /
> Pixi manifests — hygiene (`deptry`), security (`osv-scanner` + the CISA
> **KEV** gate), license, and currency — and returns one consolidated
> `ComplianceReport`. Axes 3 (license) and 4 (currency) ship **v1 as
> enrichment** (`gating: false`): they report `allowed | denied | unknown`
> and `supported | eol | unknown` but do not block; their **gates** land
> v1.1. See the single Reconciliation note below for the exact axis-by-axis
> release split. Written to be self-contained: it folds the Analyst brief,
> PM PRD, Architect design, and story sharding into one file as the source of
> truth for the **full BMAD** chain.
>
> The full BMAD planning chain (PRD → architecture → epics/stories → dev)
> runs against this spec under the `pyforge-warden` BMAD project
> (`_bmad-output/projects/pyforge-warden/`).
>
> Scope: `epics.md` currently encodes **5 epics / 20 stories** (a
> hygiene+security shape). The v1 axis expansion (axes 3+4 enrichment + KEV
> gate) grows that set; the PRD/architecture/epics reconciliation is **story
> 0.1** (this spec's Reconciliation note describes the deltas; story 6.1
> executes the schema amendment). Driven through the **full BMAD** flow (not
> Quick Flow).
>
> **Conda-forge tie-in (Rules 1 & 2 — now ENGAGED).** The engines are already
> packaged as conda recipes in-tree (`recipes/deptry`, `recipes/osv-scanner`)
> and v1 distribution (D6) ships them, so the condition is met: the executing
> agent **must** invoke the `conda-forge-expert` skill first (CLAUDE.md Rule 1)
> and close the effort with a CFE-skill retrospective + CHANGELOG entry
> (Rule 2). Note `recipes/deptry` + `recipes/osv-scanner` currently have **no**
> CHANGELOG entries — that retro is **owed** (§ Definition of Done). *(This doc
> edit + the deck edits touch neither `recipes/` nor engine code, so they do
> not themselves trigger a recipe build; the obligation attaches to the
> implementation effort.)*
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

## ⚠️ Reconciliation (2026-07-15) — READ FIRST (WINS over the whole body)

This single note supersedes the two earlier stacked reconciliation callouts
(2026-07-14 scope-change + 2026-07-11/12 architecture pass). The effort is a
**pluggable, multi-axis compliance gate** named **Warden**. Where anything in
the body below still says "two engines (deptry + osv-scanner)" or "hygiene +
vulnerability only," or dates a decision to v1.x that this note re-sequences,
**this note wins.** The PRD/architecture/epics still encode the older
hygiene+security shape (see § Status) — reconciling them is **story 0.1**;
this note is the current contract for a dev agent.

**The axes, their tools, and the release each ships in:**

| Axis | Engine / source | v1 | v1.1 | v2 | vision |
|---|---|:--:|:--:|:--:|:--:|
| **1 — Hygiene** | `deptry` | **gate** | | | |
| **2 — Security** | `osv-scanner` (Google OSV) + **CISA KEV** gate | **gate** | +EPSS `--min-epss` | | |
| **3 — License** | `license-expression` (nexB/AboutCode) — SPDX from conda `about: license:` (pre-build) + PyPI `importlib.metadata`; **no source scanning** | **enrich (`gating: false`)** | gate (`--allow/--deny-licenses`) | | |
| **4 — Currency** | LTS registry → `endoflife.date` → N/N-1 from channel data → `unknown` (deps **and** `runtime_python`) | **enrich (`gating: false`)** | gate (`--max-lag`/`--require-lts`/`--fail-on-eol`) | | |
| **Registry perimeter** | JFrog/Artifactory allow-lists; engine-swappability; client provisioner | | | **✓** | |
| **5 — Provenance** | Sigstore / SLSA attestation | | | | ✓ |
| **6 — Maintenance** | OpenSSF Scorecard | | | | ✓ |

**Why axes 3+4 ship as enrichment, not gates, in v1 (`gating: false`).** A
gate on an axis that reports `unknown` for the common first-run input is the
false-green (or false-red) the tool exists to prevent: OD8 concedes a bare
uninstalled `pyproject.toml` yields `unknown` license for every PyPI
component. `gating: false` makes `unknown` a **reportable field, not a red
gate** — the axis is present and honest in v1, its blocking gate lands v1.1.
The conda beachhead is unaffected: `about: license:` resolves **pre-build**,
so conda components carry real license/currency verdicts in v1. (Decision D4,
conditional on D5 — see § Release map.)

**Runtime-dependency policy (lean; precise).** ADD **exactly one** runtime
dep: **`license-expression`**. The **LTS registry ships as bundled static data
in the package** (`src/pyforge/warden/data/lts-registry.yaml`, loaded via
`importlib.resources` — never the dev-workspace `.claude/` copy, which is not
distributed) — this is the "**bundled tiers, zero data estate**" of D11's edge
mode. endoflife.date + KEV + EPSS are **fetched-and-cached data feeds** —
**offline stays the default**; any online query is **opt-in and never silent**
(NFR-S2), and respects a configured mirror / base-URL override (the `_http.py`
JFrog/`.netrc`/truststore chain).
Unchanged runtime deps: PyYAML (`safe_load` only), `packaging`,
`cyclonedx-python-lib`, `jsonschema`; stdlib `tomllib`, `re`,
`importlib.metadata`. Engines `deptry` + `osv-scanner` stay declared
conda/pixi run-deps (never pip, never runtime `curl`).

**New CLI (specced in FR-L*/FR-C*/FR-K* below).** v1 adds **`--warn-only`**
(the first-contact on-ramp — already specced) and **`warden scan --doctor`**
(D8 — a *flag*, not a verb, so the frozen "one verb; no interactive
subcommands" contract holds). Axis gate flags land v1.1: license
`--allow-licenses`/`--deny-licenses`; currency
`--max-lag`/`--require-lts`/`--fail-on-eol`; security `--min-epss`. The
security `--fail-on-kev` gate ships **v1**.

**`ComplianceReport` / `report-schema.json` — additive, VERSIONED, executed in
story 6.1.** The producer is **closed** (`Component` is exact-tested
`len(declared) == 13` at `tests/unit/test_models.py:212`; `ComplianceReport`
has `inventory_count: int` and **no** `components` array), so axes 3+4 force
one deliberate, versioned schema amendment — paid **once**, not four times by
accident. The `Finding` fields for KEV/EPSS already exist (subset-tested,
`{"kev","epss"} <= field_names` at `test_models.py:224`) — the **KEV gate
needs no schema amendment**. The amendment (bump `schema_version`; add
per-axis `gating` bool + `license`/`currency` sections + coverage/provenance;
update `validate_report.py` + fixtures) is **described here and executed in
story 6.1** — not by this doc edit. Note `_SCHEMA_VERSION_RE =
re.compile(r"1\.\d+\.\d+")` (`models.py:38`, matched with `fullmatch`) cannot
express `2.0.0`; the story-6.1 amendment must decide whether the additive
change stays `1.x` (it should) or widens the pattern.

**Load-bearing decisions carried forward (2026-07-11/12) — still authoritative:**

1. **Library policy (supersedes NFR2 + OD3 + Story 1.1's "no pyyaml" AC):** the constraint is **"no *execution* of untrusted input"** (no eval/exec/subprocess-in-extractor, no Jinja render, `yaml.safe_load` only), **not** stdlib-only. Lean targeted runtime deps per the policy above; `jsonschema` is a **runtime** dep (FR14 self-validation). v1 `recipe.yaml` is `safe_load`-parsed; v0 `meta.yaml` is neutralized then `safe_load`-parsed.
2. **Execution model (supersedes OD6 + data-flow step 3):** the axes run **in parallel** (NFR-P-concurrency), not sequentially.
3. **Verdict lattice + exit enum (FROZEN — do not regress):** `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable` (canonical token `warn`, not `warnings`); exit enum **`{0, 1, 2, 130}`**; **`indeterminate` → exit 1** (exit 2 reserved for operational errors). Unproven license/currency, withheld/skipped/unresolved outcomes route to `indeterminate` → non-zero, **never** a silent 0.
4. **Gate default (updated by D3 — KEV now v1):** v1 blocks on **CVSS-critical** CVEs **and** any **CISA-KEV**-listed advisory on a pinned version; high/med/low + all hygiene warn; axes 3+4 do not gate in v1 (`gating: false`). EPSS + the axis-3/4 gates land v1.1.
5. **Discovery (supersedes data-flow step 1's priority order):** **union coverage** — all discovered manifests are scanned and reported per-manifest; no single-winner priority chain.
6. **osv input (supersedes step 2's `.scanner-temp-reqs.txt` + "installed env" fallback):** the synthesized osv input is a temp file named **`requirements.txt`** (osv infers the parser from the basename); the "installed env" fallback is **dropped** (never assume a version).
7. **Repo layout detail:** `report-schema.json` lives at `src/pyforge/warden/data/` (beside the bundled `conda_pypi_map.json`), not the package root.
8. **Honest-adoption statement (load-bearing):** a bare `recipe.yaml` scan **exits non-zero by design** until the project locks (`pixi.lock`), waives (expiring, auditable), or runs `--warn-only` — the lock-nudge working, not a bug. Recommended **first contact** is a local `--warn-only` run at a terminal (§ Local / workstation mode), not CI wiring.
9. **Implementation execution model ("Option B"):** the stories run **loop-driven** — `bmad-loop` orchestrating `bmad-dev-auto` (`DEV → VERIFY → REVIEW → VERIFY → COMMIT`), per `docs/specs/bmad-loop-adoption.md`. Each story's Given/When/Then ACs are the contract; the deterministic `[verify]` command is the scanner's own pytest task; gates graduate `per-story-spec-approval` (1.1/1.2) → `per-epic` (Epic 2+) → `none` for the tail. Escalations resolve via `bmad-loop-resolve`.

**PRESERVED (do not regress):** honest-adoption posture (no false greens);
producer-agnostic report; "no execution of untrusted input." Distribution is
**no longer deferred** (D6/OD5 reversed — internal JFrog ships v1 behind story
1.7's engine pins; public PyPI/conda-forge is v1.1). Because v1 now packages
the engines as conda recipes (`recipes/deptry`, `recipes/osv-scanner`),
**CLAUDE.md Rules 1 & 2 are engaged** — the closeout owes a `conda-forge-expert`
retro + CHANGELOG entry (see § Definition of Done).

---

## Status

| Field | Value |
|---|---|
| Status | **In progress** — planning artifacts (PRD + architecture + readiness + **epics/stories: 5 epics / 20 stories**) encode the older **hygiene+security** shape; the v1 axis expansion (axes 3+4 enrichment + KEV gate) is captured in the § Reconciliation note and **awaits reconciliation into PRD/architecture/epics (story 0.1)** before implementation resumes. Decisions resolved through D11 (§ Decisions + § Reconciliation) |
| Scope | **Python only** — PyPI + conda-forge, 6 Python/conda manifest formats; non-Python ecosystems out of scope (see § Scope & naming in the intake note) |
| Owner | rxm7706 |
| Track | **Full BMAD** (PRD → architecture → epics/stories → **loop-driven dev**) — planning artifacts under `_bmad-output/projects/pyforge-warden/`. Implementation runs via **bmad-loop v0.8.1 + bmad-dev-auto** (BMAD 6.10) per `docs/specs/bmad-loop-adoption.md` — graduated gates (per-story-spec-approval for 1.1/1.2 → per-epic from Epic 2), deterministic verify gate = the scanner's own test suite |
| Proposed project slug | `pyforge-warden` (BMAD artifacts → `_bmad-output/projects/pyforge-warden/`) |
| Python package | module `pyforge.warden`; dist name `pyforge-warden` |
| Source root | **In-repo pixi *build* workspace member** at `src/shared/packages/pyforge-warden/` (Option B; unity-data-stack `src/shared/packages` convention) — see § Repository layout |
| Target users | Platform Engineers (CI/CD), DevSecOps Engineers (compliance / SBOM), and **Python developers shipping pip- + conda-sourced software of any shape** (scripts, applications, components, libraries) |
| Distribution | **Internal JFrog** (PyPI + conda) ships **v1**, behind story 1.7's engine pins (D6/OD5 reversed — no longer deferred); public PyPI/conda-forge is **v1.1** |
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

*(The goals below were authored for the hygiene+security core; per
§ Reconciliation, v1 now spans all four axes — license + currency ship as
enrichment (`gating: false`) and KEV as a gate. G1's "single consolidated
report" and G3's "strict gate" apply across all four; the axis-3/4 *gates* are
v1.1.)*

- **G1.** One CLI (`warden`) that produces a single consolidated **multi-axis**
  compliance report (v1: hygiene + security gates, license + currency
  enrichment; v1.1: the license + currency gates) from one invocation at a
  repo root.
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

> **⚠️ Requirement-ID conventions (read first) — three FR spaces are in play.**
> The `FRn` labels **in this section are intake-spec working labels**, not the
> binding contract. The canonical, binding space is **`FR1`–`FR31` in
> `_bmad-output/projects/pyforge-warden/planning-artifacts/prd.md`** § Functional
> Requirements, which states the rule itself (`prd.md:484`: *"FR1–FR31 in this
> section are canonical and binding"*). **The two spaces collide — same IDs,
> different requirements** — so an unqualified "FR9" is ambiguous:
>
> | Label | In **this spec** it means | In the **PRD** (canonical) it means |
> |---|---|---|
> | `FR2` | execute `deptry` + parse its output | classify each dependency *source section* (conda vs PyPI) and dispatch it |
> | `FR9` | the auditable, expiring **bypass** (waivers-as-code) | honor a project's existing `[tool.deptry]` hygiene-ignore config |
>
> (Waivers are **FR24–FR26** in the canonical space.) Two labels are
> unambiguous and safe to cite bare: the **scope-change FRs**
> (`FR-K1`/`FR-L1`/`FR-L2`/`FR-C1`/`FR-C2` — suffixed, colliding with neither
> space), and **`FR-15`–`FR-18`**, which belong to
> `docs/specs/cfe-atlas-datapipeline-kedro-migration.md`, **not** to Warden —
> § Cross-spec impact cites them as that spec's IDs.
>
> **When editing:** keep this section as narrative intent; land contract changes
> in the PRD's canonical space. Reconciling the two is **story 0.1**.

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
  KEV-affecting-current; warn on high/medium/low + all hygiene.** *(Per
  § Reconciliation D3: the **v1** default blocks on CVSS-critical **and** any
  CISA-KEV-listed advisory on a pinned version; EPSS (`--min-epss`) is
  v1.1.)* This
  replaces a hard "any finding blocks" gate, which drives teams to disable
  the gate entirely (the NFR1 anti-goal). *(Per § Reconciliation: the gate is
  **multi-axis but staged**. **v1** gates: hygiene, security CVSS-critical,
  and `--fail-on-kev` (FR-K1). Axes 3+4 ship v1 **enrichment-only**
  (`gating: false`) — a denied license or EOL/over-lag component is
  **reported** (`denied` / `eol` verdict in the report) but does **not** block
  in v1; an unknown license/currency is a reported `unknown`, not
  `indeterminate`, in v1. The blocking gates — license `--allow-licenses` /
  `--deny-licenses` (FR-L2), currency `--max-lag` / `--require-lts` /
  `--fail-on-eol` (FR-C2), security `--min-epss` — land **v1.1**, at which
  point denied → `policy-violation` and unknown → `indeterminate`.)*
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

*(FRs for the multi-axis scope. FR1–FR10 above are the hygiene+security core.
Per § Reconciliation: KEV enrichment **and** its gate (FR-K1) ship **v1**; the
license (FR-L1) and currency (FR-C1) axes ship **v1 as enrichment**
(`gating: false`) — present and reported, not blocking; their gates (FR-L2 /
FR-C2) and EPSS gating land **v1.1**. All feed the same `ComplianceReport`;
in v1 an unknown license/currency is a reported `unknown`, and from v1.1 an
unproven-yet-gated axis routes to `indeterminate`, never a silent pass.)*

- **FR-K1 — KEV/EPSS enrichment (Axis 2).** Enrich each security finding with
  the **CISA KEV** flag (`kev`, `kev_date`) and the **FIRST EPSS** score
  (`epss {score, percentile}`), from cached data feeds (offline default;
  opt-in online, never silent). **v1:** KEV enrichment + the `--fail-on-kev`
  gate (block when a matched advisory is KEV-listed). **v1.1:** the optional
  `--min-epss <0..1>` gate (block at/above an EPSS threshold). Absent
  enrichment data → the slots stay null and the finding gates on CVSS as
  before (never a false clean). The `kev`/`epss` `Finding` fields already
  exist (subset-tested) — KEV needs **no** schema amendment.
- **FR-L1 — License axis (Axis 3, v1 enrichment / `gating: false`).** For every resolved component,
  determine its license: normalize to an **SPDX expression** via
  `license-expression` from (a) the conda recipe `about: license:` (+
  `license_family`) and (b) PyPI metadata via stdlib `importlib.metadata`
  (PEP 639 `License-Expression`, legacy `License`, `Classifier: License ::`
  trove classifiers). **No source scanning** (ScanCode is deferred). Emit a
  per-component `license` finding: `spdx_expression`, `license_family`,
  `source`, and a verdict `allowed | denied | unknown`. In **v1** the axis is
  `gating: false` — these verdicts are **reported**, not blocking.
- **FR-L2 — License policy gate (v1.1).** `--allow-licenses <SPDX,…>` /
  `--deny-licenses <SPDX,…>` set the allow/deny sets (SPDX ids/expressions).
  From v1.1, a **denied** license → `policy-violation` (exit 1); an **unknown
  / unresolvable** license → **`indeterminate`** (exit 1) — never a silent
  clean; copyleft & unknown-license exposure surface here, not by omission.
- **FR-C1 — Currency / supportability axis (Axis 4, v1 enrichment /
  `gating: false`).** For every resolved component **and the Python runtime**,
  compute currency tiered: **LTS registry** (a **bundled**
  `src/pyforge/warden/data/lts-registry.yaml`, loaded via
  `importlib.resources` — the same in-package bundle-and-regenerate pattern as
  `conda_pypi_map.json` / `report-schema.json`; regenerated from the CFE
  `.claude/skills/conda-forge-expert/data/lts-registry.yaml`, which is the
  **source**, not the runtime path — `.claude/` never ships in the wheel/conda
  package nor exists on a scanned repo) → **endoflife.date** (the same
  URL-resolution + mirror-override pattern as `_http.py`'s
  `resolve_endoflife_urls()`; a fetched-and-cached feed, offline default) →
  **N/N-1 from conda channel data** → `unknown`. Emit `latest`, `lag` (releases/versions
  behind), `eol_date`, and a verdict `supported | eol | unknown`;
  `runtime_python` currency is a first-class field. Additionally emit an
  **availability-at-N/N-1 finding** — whether a newer supported release
  exists at the estate's N/N-1 policy tier — the ADD/UPDATE signal that feeds
  the `inventory-match --policy` → `add-handoff` → `feedstock-refresh.md`
  loop (§ Reconciliation D9/D10; this is edge-detector **wiring**, not new
  construction). In **v1** the axis is `gating: false` — reported, not blocking.
- **FR-C2 — Currency policy gate (v1.1).** `--max-lag <n>` (block when a
  component's lag exceeds `n`), `--require-lts` (block on non-LTS
  runtimes/deps where an LTS exists), `--fail-on-eol` (block on an EOL
  component or runtime). From v1.1, an **unknown** currency (no coverage / no
  resolved version) → **`indeterminate`**, never a silent pass.

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
  the default; any online query is opt-in and never silent** (NFR-S2). When
  online provisioning IS opted into (or for pre-provisioning), the feed fetch
  MUST respect a **configured mirror / base-URL override** (the same air-gap
  discipline as the OSV DB's `OSV_VULNS_BUCKET_URL` + the `_http.py`
  JFrog/`.netrc`/truststore auth chain) — never a hardcoded public endpoint
  only, so enterprise/air-gapped fleets provision endoflife.date + KEV + EPSS
  from an internal mirror (Gemini PR #58). The unchanged runtime set stays
  PyYAML (`safe_load` only) / `packaging` /
  `cyclonedx-python-lib` / `jsonschema` + stdlib `tomllib` / `re` /
  `importlib.metadata`; engines `deptry` + `osv-scanner` remain declared
  conda/pixi run-deps. The binding constraint is **no execution of untrusted
  input** (supersedes NFR2's "stdlib-only" per callout #1).

---

## Epics

> The four-epic table that stood here (E1 Manifest Resolution / E2 Deptry /
> E3 OSV / E4 Reporting) was the original ~4-epic seed. The live breakdown is
> **`_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md`**
> (5 epics / 20 stories, hygiene+security shape). That set does **not** yet
> encode axes 3+4 or the KEV gate — reconciling it to the § Reconciliation
> scope is **story 0.1**. See § Release map below for the current v1/v1.1/v2
> shape and the story map.

---

## Release map (v1 / v1.1 / v2 / vision)

The confirmed release split (decisions D1–D11 in § Decisions). **v1 is the
gate**; everything below v1 is roadmap and does not dilute the contract.

| Release | Ships | Gates |
|---|---|---|
| **v1** | Axes 1–4 (hygiene, security, license, currency) + KEV gate + full conda/pixi source-manifest resolution (the wedge) + policy/waivers/`--warn-only` + CycloneDX SBOM + polished local client (`scan --doctor`) + **internal JFrog** distribution (behind story 1.7 pins) | hygiene · security CVSS-critical · `--fail-on-kev`. Axes 3+4 are **enrichment (`gating: false`)** — reported, not blocking |
| **v1.1** | Axis 3/4 **gates** (`--allow-licenses` / `--fail-on-eol` etc.) · EPSS `--min-epss` · public PyPI + conda-forge publish · corpus ratchet · channel/index-provenance axis | the axis-3/4 gates activate; denied → `policy-violation`, unknown → `indeterminate` |
| **v2** | Registry perimeter + JFrog allow-lists (D2 — the strongest enforcement point) · engine-swappability · client provisioner | perimeter block/allow lists |
| **vision** | Axis 5 provenance (Sigstore/SLSA attestation) · Axis 6 maintenance (OpenSSF Scorecard) · malicious-package detection · reachability · TUI · IDE | — |

**Two modes, one identity (D11).** **Edge mode** (v1, no atlas, bundled
LTS/endoflife tiers) is the differentiator — "the fleet edge, zero data
estate." **Fleet mode** (v1.x → v2) is estate-backed via `inventory-match`.
FR-18 already converges the two; the deck's "three rings" is this picture.

**Story map (indicative — the authoritative breakdown is reconciled in story 0.1):**

- **0.1** — reconcile PRD/architecture/epics to the § Reconciliation scope (the hard gate; re-run both readiness reports).
- **6.1** — the versioned `ComplianceReport` schema amendment (per-axis `gating` bool + `license`/`currency` sections + KEV/EPSS slots already present); the single deliberate producer change.
- Epic 1 (Spine + PyPI engine), Epic 2 (conda/pixi wedge), Epic 3 (policy + waivers + warn-only), Epic 4 (machine contract + CycloneDX), Epic 5 (fleet-readiness + adoption) carry forward from `epics.md`; the license, currency, and KEV work threads through them under 0.1's reconciliation.

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

1. **Discovery (union coverage per § Reconciliation #5 — superseding the
   priority-order chain below).** Invoked at the repo root; **all** discovered
   manifests are scanned and reported per-manifest (no single winner). The
   original priority list (`pixi.toml` → `environment.yml` → `recipe.yaml` →
   `meta.yaml` → `pyproject.toml`, `requirements.txt` fallback) is retained
   only as the report's display ordering.
2. **Extraction.** The Manifest Engine flattens dependencies and writes an
   ephemeral temp file named **`requirements.txt`** (per § Reconciliation #6 —
   osv infers the parser from the basename; the "installed env" fallback is
   dropped).
3. **Execution (axes run in PARALLEL per § Reconciliation #2, superseding the
   original OD6 "sequential"; all v1 axes feed the report — hygiene + security
   gate, license + currency enrich):**
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
  `security` (advisory findings from E3 — **v1:** each with `kev`/`kev_date`;
  `epss` surfaced v1.1), and a `summary` (counts + overall pass/fail). *(Per
  § Reconciliation: **v1** adds a `license` section (per-component
  `spdx_expression` / `license_family` / `source` / `allowed|denied|unknown`)
  and a `currency` section (per-component `latest` / `lag` / `eol_date` /
  `supported|eol|unknown`, plus `runtime_python`), each with a per-axis
  `gating` bool (`false` in v1 — enrichment) and its own `coverage` +
  `provenance {source, snapshot_at}`. Story 6.1 bumps `schema_version` on this
  additive change; the additions are backward-compatible —
  `additionalProperties` stays open and the frozen
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

## Decisions (resolved 2026-07-10; OD2 refined 2026-07-11; D1–D11 2026-07-15)

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
- **OD5 — distribution → RE-DECIDED 2026-07-15 (D6; no longer deferred).**
  The internal-first build stands, but distribution is now **scheduled, not
  deferred to an unspecified closeout**: **internal JFrog** (PyPI + conda)
  ships **v1**, gated on story 1.7 pinning the engine run-deps (`deptry` /
  `osv-scanner` are `"*"` today — publishing before the pins go live would
  ship the fleet-wide false-error the pins exist to prevent). **Public PyPI +
  conda-forge publish is v1.1.** Because v1 packages the engines as conda
  recipes (`recipes/deptry`, `recipes/osv-scanner` already exist), **Rules 1
  & 2 are engaged now** (conda-forge-expert skill + closeout retro +
  CHANGELOG) — see § Definition of Done.
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

**Core Architectural Decisions (multi-axis gate):**

- **OD7 — Axis-plugin model → RETIRED as a new abstraction 2026-07-15.** The
  spec proposed a small `Axis` interface (`assess() → findings + coverage +
  provenance`) as new work. **It is a phantom:** the shipped code is already
  axis-generic — `AxisCoverage.axis` is a plain string and engines pass
  `axis=AXIS_HYGIENE` / `axis=finding.axis` (`engines.py`, `hygiene.py`), with
  no `Axis` protocol class. License and currency register by **reusing the
  existing `Engine` shape with a new axis string** — **no new protocol, no new
  interface work.** What survives is the *invariant*, not the abstraction: one
  report + one verdict lattice, the verdict owns exit projection, axes only
  feed rungs (never-false-green stays central); the new per-axis `gating`
  bool (v1 enrichment vs gate) is the one additive field. Retiring OD7's
  interface **deletes work**.
- **OD8 — License source strategy (metadata, not source scan).** Resolve
  licenses from **package/recipe metadata only** and normalize to SPDX via the
  one new runtime dep **`license-expression`** (nexB/AboutCode). **No source
  scanning**: ScanCode Toolkit deep-scan is deferred (post-v1.x) as it would
  break the lean-deps + fast-fleet posture (NFR1/NFR5). Two sources, with
  **different availability** — this is the same "coverage improves only by
  resolving, never by assuming" guardrail the security/currency axes use, and
  it keeps the pre-build posture honest (Gemini PR #58):
  - **conda** — `about: license:` (+ `license_family`) is carried **in the
    recipe manifest itself**, so it resolves **pre-build**, no install needed.
  - **PyPI** — resolved from **installed distribution metadata** via
    `importlib.metadata` (PEP 639 `License-Expression`, legacy `License`,
    `Classifier: License ::` trove). This requires the component to be
    **present in an environment Warden can inspect** — a resolved/installed
    tree, a `pixi.lock`/lockfile-provisioned env, or Warden run inside the
    target env. **A bare, uninstalled PyPI manifest** (`pyproject.toml` /
    `requirements.txt` whose deps are not installed) cannot yield license
    metadata offline, so those components are **`unknown` → `indeterminate`**
    (honest coverage gap + lock-nudge, exactly like an unversioned dep on the
    vuln axis) — **never a silent `allowed`**. Filling that gap by resolving
    (install / lock) or via an **optional bundled/cached license map** (same
    provisioning pattern as the conda→pypi map, offline; a PyPI JSON-metadata
    fetch is opt-in-online-only, per OD9/OD10 mirror policy) is a documented
    coverage lever, never an assumption.
- **OD9 — Currency source strategy → REFINED 2026-07-15 (D9/D10; tiered +
  availability).** Compute supportability **tiered**: **LTS registry**
  (a **bundled** `src/pyforge/warden/data/lts-registry.yaml` loaded via
  `importlib.resources`, regenerated from the CFE
  `.claude/…/lts-registry.yaml` source — never `.claude/` at runtime) →
  **endoflife.date** (the `_http.py` `resolve_endoflife_urls()` pattern; cached
  offline; opt-in online, never silent) → **N/N-1 from conda channel data** →
  `unknown`, for each dependency **and the Python runtime**. Emit the currency verdict **plus a distinct
  availability-at-N/N-1 finding** (is a newer supported release available at
  the estate's policy tier) — the **ADD/UPDATE** signal. This is **wiring, not
  new construction**: `inventory-match --policy` already emits
  ADD/UPDATE/CURRENT, `add-handoff` builds worklists, and `feedstock-refresh.md`
  executes them across 769 feedstocks; Warden's currency finding is the **edge
  detector feeding that loop**. In v1 the axis is `gating: false` (reported);
  from v1.1 a gated `unknown` → `indeterminate`.
- **OD10 — KEV/EPSS enrichment → SPLIT 2026-07-15 (D3).** Enrich osv findings
  with **CISA KEV** + **FIRST EPSS** from cached data feeds (offline default).
  **v1:** KEV enrichment on every security finding **and** the `--fail-on-kev`
  gate — cheap, and no schema amendment (the `kev`/`epss` `Finding` fields are
  already present, subset-tested). **v1.1:** EPSS enrichment surfacing +
  `--min-epss` gate. Absent feed data leaves the slots null and gates on CVSS
  (never a false clean).

**Confirmation decisions (D1–D11, 2026-07-15 — the reshape):**

- **D1** — full reshape around the deck's Parts I–IV, vision tiered after the contract. **D2** — registry perimeter → **v2** (the strongest enforcement point, not the weakest). **D3** — KEV gate → **v1** (cheap; no schema amendment). **D4** — axes 1–4 in **v1**, conditional on the `gating: false` mechanism. **D5** — axis 3/4 **gates** → **v1.1** (what makes D4 survivable). **D6** — packaging in v1 (internal JFrog) + public v1.1 behind story 1.7 pins. **D7** — TUI/IDE → vision. **D8** — local client = install + output + **`scan --doctor`** (a flag, not a verb — `prd.md:396` freezes "one verb; no interactive subcommands"). **D9** — currency tiered LTS → endoflife → N/N-1 → unknown. **D10** — availability-at-N/N-1 as a distinct ADD/UPDATE finding. **D11** — Warden owns edge **and** fleet as **two modes, one identity** (edge = v1 no-atlas; fleet = v1.x→v2 estate-backed; FR-18 converges them).

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
(Story 5.1 docs; `pixi global install` / the local channel + internal JFrog
now, public conda-forge v1.1 per OD5/D6). The self-check ships **v1 as
`warden scan --doctor`** (D8) — a **flag on the one frozen verb, not a
`doctor` subcommand** (`prd.md:396` freezes "one verb; no interactive
subcommands"; `doctor` isn't even on the post-v1 subcommand list). It
re-exposes FR21's engine/DB detection logic.

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
differentiation, stated once. **Warden is two modes, one identity (D11):**
**edge mode** (v1, no atlas, bundled LTS/endoflife tiers — "the fleet edge,
zero data estate") and **fleet mode** (v1.x→v2, estate-backed via
`inventory-match`); FR-18 converges them. The row below is edge mode:

| You have | Use |
|---|---|
| Any repo, any org, **no atlas**; need a CI/terminal gate on **your pinned deps** (hygiene + CVEs + license/currency enrichment) | **pyforge-warden edge mode** (this tool — the fleet edge; zero data estate) |
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
   KEV/EPSS slots (**v1 populates KEV** and gates on it; EPSS surfacing is
   v1.1), severity carrying tier + raw evidence.
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
7. **Currency axis feeds the refresh loop (D9/D10).** Warden's
   availability-at-N/N-1 (ADD/UPDATE) finding is the edge detector for the
   loop `feedstock-refresh.md` already runs (`inventory-match --policy` →
   `add-handoff` → per-feedstock refresh). Obligation: a reciprocal note in
   **`docs/specs/feedstock-refresh.md`** that Warden's currency finding is an
   additional worklist source — recorded here, **owned at the currency-axis
   implementation** (not this doc edit), mirroring item 1's pattern.
8. **Env scaffolding is nebi's, not Warden's (why no provisioner).** "Ensure
   envs source from approved channels" is a **verification** property, not a
   provisioning one; a provisioner governs only what it creates and is bypassed
   by `pixi add --channel`, and pixi mirrors are transparent by design (a
   fully-mirrored JFrog estate's `pixi.lock` still records
   `conda.anaconda.org/conda-forge/…`, so a lock-reading axis would misreport).
   pixi 0.72.2 already ships `pixi import --format {conda-env,pypi-txt}`, `uv`
   covers the venv case, and `cfe-atlas-datapipeline-kedro-migration.md`
   already assigns env scaffolding to **nebi**. Warden builds **no
   provisioner**; the read-only channel-provenance axis is **v1.1**, and
   `doctor --fix` is foreclosed by the one-verb contract (accepted risk — v2's
   first job, behind the registry perimeter). Obligation: a reciprocal note in
   the kedro spec that Warden defers env scaffolding to nebi — recorded here,
   owned at that convergence.

---

## Definition of Done

- [x] All decisions resolved through **D11** (§ Decisions + § Reconciliation).
- [ ] **Story 0.1** — PRD/architecture/epics reconciled to the § Reconciliation
      scope (axes 3+4 enrichment + KEV gate); both readiness reports re-run.
- [ ] E1–E4 stories implemented with passing unit tests (all six manifest types).
- [ ] `pyforge.warden` runs clean on this repo's own `pixi.toml` /
      `pyproject.toml` and exits 0 on a known-clean fixture, non-zero on a
      seeded-violation fixture.
- [ ] Committed `report-schema.json` + `validate_report.py`; emitted JSON
      validates against the schema in the test suite; human stdout view
      verified in a CI log (FR4/FR6).
- [ ] NFR3 verified: no host/source mutation; ephemeral files removed on
      both success and failure paths.
- [ ] **CFE Rules 1 & 2 (engaged, not conditional — D6):** the engine recipes
      (`recipes/deptry`, `recipes/osv-scanner`) are maintained via
      `conda-forge-expert`, and the effort closes with a CFE-skill retro +
      CHANGELOG entry. Both recipes currently lack CHANGELOG entries — that
      retro is owed at closeout.
- [ ] `status: shipped` with `implemented_by:` + `shipped_ref:` set.

**v1 multi-axis DoD (§ Reconciliation scope):**
- [ ] **KEV gate (FR-K1, v1):** security findings carry `kev`/`kev_date`;
      `--fail-on-kev` blocks; cached feeds, offline default. No schema
      amendment (the `Finding` fields already exist).
- [ ] **License axis enrichment (FR-L1, v1, `gating: false`):** SPDX via
      `license-expression` (the one new runtime dep) from conda `about:` +
      PyPI `importlib.metadata`; `license` report section with
      `allowed | denied | unknown` **reported, not blocking**. No source scanning.
- [ ] **Currency axis enrichment (FR-C1, v1, `gating: false`):** tiered LTS →
      endoflife.date → N/N-1 for deps **and** `runtime_python`; `currency`
      report section + the availability-at-N/N-1 (ADD/UPDATE) finding;
      reported, not blocking.
- [ ] **Schema versioned (story 6.1):** `schema_version` bumped; per-axis
      `gating` bool + `license`/`currency` sections added; `validate_report.py`
      + fixtures updated; the frozen v1 keys + `Component` (13 fields) unchanged.

**v1.1 DoD (the axis gates):**
- [ ] License gate (FR-L2): `--allow-licenses` / `--deny-licenses`; denied →
      policy-violation, unknown → indeterminate.
- [ ] Currency gate (FR-C2): `--max-lag` / `--require-lts` / `--fail-on-eol`;
      EOL → policy-violation, unknown → indeterminate.
- [ ] EPSS: `epss {score, percentile}` surfaced + `--min-epss` gate.
- [ ] Public PyPI + conda-forge publish (behind story 1.7 engine pins).
- [ ] Release sequencing honored: v2 = registry perimeter; provenance +
      maintenance remain vision (unbuilt).

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
