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
> gates, flag-activated (D12)**: unconfigured they report
> `allowed | denied | unknown` and `supported | eol | unknown` via the
> visible `warn` rung; configuring an axis's policy flags activates its v1
> gate. See the single Reconciliation note below for the exact axis-by-axis
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
vulnerability only," or dates a decision to a release this note re-sequences,
**this note wins.**

**Intent-coverage pass (2026-07-15, evening — spec-first replan).** Per owner
direction, this spec is now the **sole source of truth**: it must capture the
full intent and feature surface of the Warden infographic/deck (Parts I–IV),
tiered into exactly three release buckets — **v1 / v1.x / vision** (the former
v1.1 and v2 buckets fold into **v1.x**; D12 (2026-07-16) then moved the former v1.1 content INTO v1).
The current PRD/architecture/epics are **superseded, not authorities**: story
0.1 is upgraded from "reconcile" to **"replan — rebuild PRD + epics from this
spec"** (see § Status and § Release map). The absorbed feature catalog lives
in § Release map + § Vision catalog; the adversarial-review evidence behind
the semantics fixes below is
`_bmad-output/projects/pyforge-warden/planning-artifacts/adversarial-review-pyforge-warden-spec-2026-07-15.md`.

**The axes, their tools, and the release each ships in:**

| Axis | Engine / source | v1 | v1.x | vision |
|---|---|:--:|:--:|:--:|
| **1 — Hygiene** | `deptry` | **gate** | alternate engines (`--engine`) | |
| **2 — Security** | `osv-scanner` (Google OSV) + **CISA KEV** gate + **EPSS `--min-epss`** | **gate** | pluggable vuln backends | |
| **3 — License** | `license-expression` (nexB/AboutCode) — SPDX from conda `about: license:` (pre-build) + PyPI `importlib.metadata`; **no source scanning** | **gate (flag-activated: `--allow/--deny-licenses`; unconfigured → visible `warn`)** | | |
| **4 — Currency** | LTS registry → `endoflife.date` → N/N-1 from channel data → `unknown` (deps **and** `runtime_python`) | **gate (flag-activated: `--max-lag`/`--require-lts`/`--fail-on-eol`; unconfigured → visible `warn`)** | | |
| **Registry perimeter** | JFrog/Artifactory block/allow lists · quarantine · client provisioner | | **✓ (later 1.x)** | |
| **5 — Provenance** | Sigstore / SLSA attestation | | | ✓ |
| **6 — Maintenance** | OpenSSF Scorecard | | | ✓ |

**Why the axis gates are flag-activated in v1 (D12, 2026-07-16 — supersedes
the earlier enrichment-only split).** v1 ships the **full gate mechanism** for
all four axes; what varies per axis is activation. A license/currency axis
with **no policy flags configured** reports its verdicts visibly — `unknown`
/ `denied` / `eol` feed a **`warn`** rung (status `warn`, driver names the
axis, exit 0) — never a silent clean (adversarial review T2). **Setting any
axis policy flag flips that axis to gating**: denied/eol → `policy-violation`
(exit 1), unknown → `indeterminate` (exit 1). The OD8 first-run problem (a
bare uninstalled `pyproject.toml` is all-`unknown` on the license axis) is
resolved by the **v1 adoption on-ramp**, not by deferring gates: **baseline &
grandfathering** (FR-B1 — accept existing debt in a committed baseline, gate
only NEW findings) plus `--warn-only`; `--warn-as-error` remains the
strict-shop escalator for unconfigured axes. The conda beachhead:
`about: license:` resolves **pre-build**, so conda components carry real
*license* verdicts in v1 (currency coverage per mode — see the OD9 tier
matrix). (D12 subsumes D4/D5's split; the `gating` bool remains per-axis
report state, now flag-driven.)

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

**New CLI (specced in FR-L*/FR-C*/FR-K*/FR-B1/FR-A1 below).** v1 adds
**`--warn-only`** (the first-contact on-ramp — already specced), **`warden
scan --doctor`** (D8 — a *flag*, not a verb, so the frozen "one verb; no
interactive subcommands" contract holds), and — per **D12 (2026-07-16)** —
the **axis gate flags in v1**: license `--allow-licenses`/`--deny-licenses`;
currency `--max-lag`/`--require-lts`/`--fail-on-eol`; security `--min-epss`
(joining the v1 `--fail-on-kev` gate); plus **`--baseline <file>`** (FR-B1
baseline & grandfathering) and the opt-in post-scan **`--open-fix-prs`**
actuator (FR-A1 — forge-API only, never writes the scanned tree).

**`ComplianceReport` / `report-schema.json` — additive, VERSIONED, executed in
story 6.1.** The producer is **closed** (`Component` is exact-tested
`len(declared) == 13` at `tests/unit/test_models.py:212`; `ComplianceReport`
has `inventory_count: int` and **no** `components` array), so axes 3+4 force
one deliberate, versioned schema amendment — paid **once**, not four times by
accident. The `Finding` fields for KEV/EPSS already exist (subset-tested,
`{"kev","epss"} <= field_names` at `test_models.py:224`) — the **KEV gate's
bare `kev` bool needs no schema amendment** (its `kev_date`/`epss`-object/
provenance completions ride the 6.1 amendment — see below). The amendment
(bump `schema_version`; add
per-axis `gating` bool + `license`/`currency` sections + coverage/provenance;
update the runtime self-validation in `report.py` + the schema + fixtures —
note there is **no** standalone `validate_report.py`; self-validation lives at
`report.py:130-143`) is **described here and executed in story 6.1** — not by
this doc edit. The amendment also carries the FR-K1 field completions: the
bare `kev` bool is free (subset-tested), but `kev_date` is a **new** `Finding`
field and `epss {score, percentile}` **replaces the scalar `epss` slot** —
both are part of this one versioned amendment, not free riders. Note `_SCHEMA_VERSION_RE =
re.compile(r"1\.\d+\.\d+")` (`models.py:38`, matched with `fullmatch`) cannot
express `2.0.0`; the story-6.1 amendment must decide whether the additive
change stays `1.x` (it should) or widens the pattern.

**Load-bearing decisions carried forward (2026-07-11/12) — still authoritative:**

1. **Library policy (supersedes NFR2 + OD3 + Story 1.1's "no pyyaml" AC):** the constraint is **"no *execution* of untrusted input"** (no eval/exec/subprocess-in-extractor, no Jinja render, `yaml.safe_load` only), **not** stdlib-only. Lean targeted runtime deps per the policy above; `jsonschema` is a **runtime** dep (FR14 self-validation). v1 `recipe.yaml` is `safe_load`-parsed; v0 `meta.yaml` is neutralized then `safe_load`-parsed.
2. **Execution model (supersedes OD6 + data-flow step 3):** the axes run **in parallel** (NFR-P-concurrency), not sequentially.
3. **Verdict lattice + exit enum (FROZEN — do not regress):** `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable` (canonical token `warn`, not `warnings`); exit enum **`{0, 1, 2, 130}`**; **`indeterminate` → exit 1** (exit 2 reserved for operational errors). On **gating** axes, withheld/skipped/unresolved outcomes route to `indeterminate` → non-zero, never a silent 0 (the shipped C0 property). On an axis whose **policy flags are unconfigured** (license/currency with no allow/deny/lag/EOL policy set), unproven outcomes route to **`warn`** — visible in the status channel, exit 0 — never to a silent `clean`; **configuring any policy flag for that axis activates its gate in v1 (D12)**, at which point denied/eol → `policy-violation` and unknown → `indeterminate`. *(Amended 2026-07-15 and re-baselined 2026-07-16 (D12) — supersedes both the "always `indeterminate`" wording and the v1.x gate deferral.)*
4. **Gate default (updated by D3 — KEV now v1):** v1 blocks on **CVSS-critical** CVEs **and** any **CISA-KEV**-listed advisory on a pinned version; high/med/low warn; hygiene per the DEP001 table (**DEP001 missing-dependency blocks by default** on a high-confidence mapping, DEP002–005 warn — owner-confirmed 2026-07-15, aligning this spec to epics story 1.6); axes 3+4 gate **when configured** (D12 flag-activation; unconfigured → visible `warn`). **Feed absence is never silent:** under a KEV-blocking policy (including this default) an absent or stale KEV snapshot feeds an `indeterminate` rung with a KEV-provenance driver, and the same rule applies to the **EPSS feed under an active `--min-epss` policy** — a gate cannot silently no-op offline. EPSS enrichment + `--min-epss` ship **v1** (D12).
5. **Discovery (supersedes data-flow step 1's priority order):** **union coverage** — all discovered manifests are scanned and reported per-manifest; no single-winner priority chain.
6. **osv input (supersedes step 2's `.scanner-temp-reqs.txt` + "installed env" fallback):** the synthesized osv input is a temp file named **`requirements.txt`** (osv infers the parser from the basename); the "installed env" fallback is **dropped** (never assume a version).
7. **Repo layout detail:** `report-schema.json` lives at `src/pyforge/warden/data/` (beside the bundled `conda_pypi_map.json`), not the package root.
8. **Honest-adoption statement (load-bearing):** a bare `recipe.yaml` scan **exits non-zero by design** until the project locks (`pixi.lock`), waives (expiring, auditable), or runs `--warn-only` — the lock-nudge working, not a bug. Recommended **first contact** is a local `--warn-only` run at a terminal (§ Local / workstation mode), not CI wiring.
9. **Implementation execution model ("Option B"):** the stories run **loop-driven** — `bmad-loop` orchestrating `bmad-dev-auto` (`DEV → VERIFY → REVIEW → VERIFY → COMMIT`), per `docs/specs/bmad-loop-adoption.md`. Each story's Given/When/Then ACs are the contract; the deterministic `[verify]` command is the scanner's own pytest task; gates graduate `per-story-spec-approval` (1.1/1.2) → `per-epic` (Epic 2+) → `none` for the tail. Escalations resolve via `bmad-loop-resolve`.

**PRESERVED (do not regress):** honest-adoption posture (no false greens);
producer-agnostic report; "no execution of untrusted input." Distribution is
**no longer deferred** (D6/OD5 reversed — internal JFrog ships v1 behind the
**engine version-range story** (a v1 story the replan must assign: replace
`pixi.toml`'s `deptry = "*"` / `osv-scanner = "*"` with tested **ranges** per
canonical NFR-C1 — a range, not an exact pin; the review found no existing
story owns this); public PyPI/conda-forge is v1.x. Because v1 now packages
the engines as conda recipes (`recipes/deptry`, `recipes/osv-scanner`),
**CLAUDE.md Rules 1 & 2 are engaged** — the closeout owes a `conda-forge-expert`
retro + CHANGELOG entry (see § Definition of Done).

---

## Status

| Field | Value |
|---|---|
| Status | **In progress — story-0.1 replan EXECUTED 2026-07-15; v1 RE-BASELINED 2026-07-16 (D12).** This spec is the sole source of truth; the PRD (FR1–**FR40** + NFR-S9), architecture (§ Multi-axis reconciliation), and epics (**6 epics / 30 stories** — Epic 6 = multi-axis expansion 6.1–6.10) were rebuilt from this spec's v1 / v1.x / vision tiering and are authoritative **downstream** of it; **D12 pulled the axis gates (flag-activated), EPSS, baseline & grandfathering, and the fix-PR actuator into v1**; readiness re-run 2026-07-16 → READY-WITH-CONDITIONS (re-run `bmad-sprint-planning` before loop execution). Decisions resolved through **D12** (§ Reconciliation + § Decisions) |
| Scope | **Python only** — PyPI + conda-forge, 6 Python/conda manifest formats; non-Python ecosystems out of scope (see § Scope & naming in the intake note) |
| Owner | rxm7706 |
| Track | **Full BMAD** (PRD → architecture → epics/stories → **loop-driven dev**) — planning artifacts under `_bmad-output/projects/pyforge-warden/`. Implementation runs via **bmad-loop v0.8.1 + bmad-dev-auto** (BMAD 6.10) per `docs/specs/bmad-loop-adoption.md` — graduated gates (per-story-spec-approval for 1.1/1.2 → per-epic from Epic 2), deterministic verify gate = the scanner's own test suite |
| Proposed project slug | `pyforge-warden` (BMAD artifacts → `_bmad-output/projects/pyforge-warden/`) |
| Python package | module `pyforge.warden`; dist name `pyforge-warden` |
| Source root | **In-repo pixi *build* workspace member** at `src/shared/packages/pyforge-warden/` (Option B; unity-data-stack `src/shared/packages` convention) — see § Repository layout |
| Target users | Platform Engineers (CI/CD), DevSecOps Engineers (compliance / SBOM), and **Python developers shipping pip- + conda-sourced software of any shape** (scripts, applications, components, libraries) |
| Distribution | **Internal JFrog** (PyPI + conda) ships **v1**, behind the engine version-range story (replan-assigned; NFR-C1: tested range, not exact pin) (D6/OD5 reversed — no longer deferred); public PyPI/conda-forge is **v1.x** |
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
v1.x.)*

- **G1.** One CLI (`warden`) that produces a single consolidated **multi-axis**
  compliance report (v1: hygiene + security gates, license + currency
  enrichment via the visible `warn` rung; v1.x: the license + currency gates) from one invocation at a
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
SBOM emission is a v1 deliverable (working-FR8 = canonical FR27), not a
non-goal** (owner-elevated 2026-07-11).

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
> **When editing (updated 2026-07-15 — spec-first):** this spec is now the
> sole source of truth; land contract changes **here**. The PRD's canonical
> FR1–FR31 space is superseded and will be **re-derived from this spec** by
> the story-0.1 replan (which owns minting the next canonical numbering).
> Until then, cite this section's working labels with the `working-FR`
> qualifier when ambiguity is possible; the full working-label → old-canonical
> map is at `prd.md:486`.

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
  KEV-affecting-current; warn on high/medium/low; hygiene per the DEP001 table — DEP001 blocks by default, DEP002–005 warn (owner-confirmed 2026-07-15).** *(Per
  § Reconciliation D3: the **v1** default blocks on CVSS-critical **and** any
  CISA-KEV-listed advisory on a pinned version; EPSS (`--min-epss`) is
  v1.x.)* This
  replaces a hard "any finding blocks" gate, which drives teams to disable
  the gate entirely (the NFR1 anti-goal). *(Per § Reconciliation: the gate is
  **multi-axis, flag-activated (D12, 2026-07-16)**. Default-on **v1** gates:
  hygiene, security CVSS-critical, and `--fail-on-kev` (FR-K1). Axes 3+4
  ship v1 with their **full gates, activated by configuration** — license
  `--allow-licenses` / `--deny-licenses` (FR-L2), currency `--max-lag` /
  `--require-lts` / `--fail-on-eol` (FR-C2), security `--min-epss` (FR-K1) —
  when set: denied/eol → `policy-violation`, unknown → `indeterminate`.
  Unconfigured, those axes still surface every `denied` / `eol` / `unknown`
  verdict via a **`warn` rung** — status `warn`, exit 0, driver naming the
  axis — never a silent `clean` (review T2). The v1 adoption on-ramp is
  **baseline & grandfathering (FR-B1)** + `--warn-only`.)*
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
  kedro migration's CycloneDX normalization (kedro **FR-13**; FR-17 extends
  it with transitive resolution). Optional synergy: the
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
Per § Reconciliation as re-baselined by **D12 (2026-07-16)**: KEV + EPSS
enrichment **and** their gates (FR-K1), the license axis + gate (FR-L1/FR-L2),
the currency axis + gate (FR-C1/FR-C2), baseline & grandfathering (FR-B1),
and the fix-PR actuator (FR-A1) ALL ship **v1**. The axis gates are
**flag-activated**: configured → denied/eol → `policy-violation`, unknown →
`indeterminate`, never a silent pass; unconfigured → every verdict still
surfaces via the `warn` rung (exit 0, never a silent `clean`).)*

- **FR-K1 — KEV/EPSS enrichment (Axis 2).** Enrich each security finding with
  the **CISA KEV** flag (`kev`, `kev_date`) and the **FIRST EPSS** score
  (`epss {score, percentile}`), from cached data feeds (offline default;
  opt-in online, never silent). **v1:** KEV enrichment + the `--fail-on-kev`
  gate (block when a matched advisory is KEV-listed) **and** the optional
  `--min-epss <0..1>` gate (block at/above an EPSS threshold — D12 pulled
  EPSS into v1). **Feed-absence
  semantics (2026-07-15 amendment; review T1):** when **no KEV policy** is in
  effect, absent enrichment data leaves the slots null and the finding gates
  on CVSS as before. When a **KEV-blocking policy is in effect** (including
  the v1 default), an absent or stale KEV snapshot → an **`indeterminate`**
  rung with a KEV-provenance driver — the gate never silently no-ops. The
  report carries **per-feed KEV provenance** (`{source, snapshot_at,
  max_age_ok}` — the `VulnData` pattern), so `kev: null` = "feed absent" is
  distinguishable from "assessed, not KEV-listed". **EPSS ships v1 too
  (D12):** `epss {score, percentile}` from the FIRST.org feed (a second
  cached feed under the identical posture + provenance) and the **`--min-epss
  <0..1>` gate** — with the mirrored absence rule: an active `--min-epss`
  policy + an absent/stale EPSS feed → `indeterminate`, never a silent
  no-op. KEV + EPSS feed provisioning, cache location/lifecycle, and max-age
  policy are named v1 stories (6.4 / 6.7 — the OSV-DB provisioning story is
  the template). Schema cost, stated exactly: the bare `kev` bool rides free
  (subset-tested); `kev_date` + the `epss` object + per-feed provenance are
  part of the **story-6.1 amendment** (see § Reconciliation).
- **FR-L1 — License axis (Axis 3, v1; gate flag-activated — D12).** For every resolved component,
  determine its license: normalize to an **SPDX expression** via
  `license-expression` from (a) the conda recipe `about: license:` (+
  `license_family`) and (b) PyPI metadata via stdlib `importlib.metadata`
  (PEP 639 `License-Expression`, legacy `License`, `Classifier: License ::`
  trove classifiers). **No source scanning** (ScanCode is deferred). Emit a
  per-component `license` finding: `spdx_expression`, `license_family`,
  `source`, and a verdict `allowed | denied | unknown`. **v1 activation
  (D12):** unconfigured, verdicts surface via `warn`; any FR-L2 flag
  activates the gate.
- **FR-L2 — License policy gate (v1, flag-activated — D12).**
  `--allow-licenses <SPDX,…>` / `--deny-licenses <SPDX,…>` set the allow/deny
  sets (SPDX ids/expressions). Setting either flag activates the license
  gate: a **denied** license → `policy-violation` (exit 1); an **unknown /
  unresolvable** license → **`indeterminate`** (exit 1) — never a silent
  clean; copyleft & unknown-license exposure surface here, not by omission.
  (Unconfigured, the same verdicts feed `warn` — see FR5/FR-L1.)
- **FR-C1 — Currency / supportability axis (Axis 4, v1; gate flag-activated
  — D12).** For every resolved component **and the Python runtime**,
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
  `runtime_python` currency is a first-class field. **Per-mode tier
  availability (2026-07-15 amendment; review T4/T6):** in **edge mode** (no
  atlas, offline default) the live tiers are the bundled LTS registry and any
  locally-cached endoflife.date snapshot; the N/N-1 tier requires channel
  data (cached repodata/channeldata or the estate) and **degrades to
  `unknown` — visibly, via the `warn` rung — when absent**. Every currency
  verdict carries **data-age provenance**: bundled data reports its
  build-time `snapshot_at` plus a `max_age_ok` verdict against a configurable
  max-age (default 180 days) — a stale bundled registry can never silently
  report `supported`, and the `--fail-on-eol`/`--require-lts` gates (v1,
  flag-activated) **require fresh registry data as a precondition** (stale →
  `indeterminate`, not pass). Additionally emit an **availability-at-N/N-1 finding** — whether
  a newer supported release exists at the estate's N/N-1 policy tier — the
  ADD/UPDATE signal that feeds the `inventory-match --policy` →
  `add-handoff` → `feedstock-refresh.md` loop (§ Reconciliation D9/D10;
  edge-detector **wiring**, not new construction). The ADD/UPDATE finding is
  **fleet-mode**: in edge mode it is omitted with a coverage note (no estate
  policy tier to compare against). **v1 activation (D12):** unconfigured,
  verdicts surface via `warn`; any FR-C2 flag activates the gate.
- **FR-C2 — Currency policy gate (v1, flag-activated — D12).** `--max-lag
  <n>` (block when a component's lag exceeds `n`), `--require-lts` (block on
  non-LTS runtimes/deps where an LTS exists), `--fail-on-eol` (block on an
  EOL component or runtime). Setting any flag activates the currency gate: an
  **unknown** currency (no coverage / no resolved version) →
  **`indeterminate`**, never a silent pass — and the gates precondition on
  registry freshness (see FR-C1 data-age provenance).
- **FR-B1 — Baseline & grandfathering (v1 — D12; the adoption on-ramp at
  fleet scale).** `--baseline <file>` reads a **committed, schema-validated**
  `.warden-baseline.yaml` that records existing (grandfathered) findings by
  their stable finding IDs (the same ID grammar waiver matching uses —
  `models.py`'s three families). A baselined finding does not block; the gate
  blocks **NEW findings only**. Baseline entries carry `accepted_at` /
  `expires_at` (expiry semantics identical to waivers: on expiry the finding
  re-blocks) and every applied baseline entry is **echoed in the report**
  (loud, like `bypassed` — the opposite of a false green). The tool **reads**
  the baseline and never writes the repository (a `--baseline-emit` helper
  prints a candidate stanza to stdout for the human to commit — NFR3 intact).
- **FR-A1 — Automated fix-PR actuator (v1, opt-in — D12).**
  `--open-fix-prs` runs a **post-scan actuator**: given forge credentials
  (env-provided, never flags), it opens remediation pull requests from the
  run's findings via the **forge API** — security findings → upgrade-to-fixed-
  version PRs; hygiene unused-dependency findings → removal PRs — **never
  writing the scanned working tree** (NFR3/NFR-R3a hold; the actuator is the
  only component permitted forge egress, post-verdict, and is inert without
  the flag). `--fix-prs-dry-run` prints the would-be PRs. The scan's verdict
  and exit code are computed **before** and independent of actuation — a
  failed PR-open never alters the verdict (it surfaces as a typed warning).

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
> scope is **story 0.1 (upgraded to a full replan — see § Status)**. See
> § Release map below for the current v1 / v1.x / vision shape and the story map.

---

## Release map (v1 / v1.x / vision)

The confirmed release split (decisions D1–D11 + the 2026-07-15 intent-coverage
pass). Exactly **three buckets** (owner-directed): **v1** is the gate;
**v1.x** is scheduled roadmap (the former v1.1 content moved INTO v1 per D12; the former v2
items are the v1.x tail); **vision** is direction. Everything below v1 is roadmap
and does not dilute the contract. This table is the **complete absorbed
feature surface** of the Warden infographic/deck — nothing ships that is not
on this map, and nothing on the infographic is missing from it (§ Vision
catalog holds the Part III–IV detail).

| Release | Ships | Gates |
|---|---|---|
| **v1** | Axes 1–4 **with their gates** (D12): license `--allow/--deny-licenses` (FR-L2) · currency `--max-lag`/`--require-lts`/`--fail-on-eol` (FR-C2, freshness-preconditioned) · security KEV `--fail-on-kev` **+ EPSS `--min-epss`** (FR-K1, both feeds with provenance + absent-feed `indeterminate` semantics) + **baseline & grandfathering** (FR-B1 — committed baseline, gate NEW findings only, expiring entries) + **fix-PR actuator** (FR-A1, opt-in `--open-fix-prs`, forge-API only) + full conda/pixi source-manifest resolution (the wedge) + policy/waivers/`--warn-only` + CycloneDX SBOM + polished local client (`scan --doctor`) + **internal JFrog** distribution (behind the engine version-range story, NFR-C1) | Default-on: hygiene · security CVSS-critical · `--fail-on-kev`. Axes 3+4 gate **when configured** (flag-activated); unconfigured → every denied/eol/unknown feeds **`warn`** (visible, exit 0), never a silent clean |
| **v1.x — early** | Public PyPI + conda-forge publish · channel/index-provenance axis (mechanism must read pixi config layers, not just the lock — mirror-mode locks record canonical URLs; see § Positioning) · **SARIF output** (code-scanning consumers) · **vendor-support backlog** (auto-generate tracked work items from findings) · PRD Growth carry-overs: vuln-side waiver · more osv-native lockfiles · better conda↔PyPI name reconciliation (cf_atlas promotion lives in § Future/backlog) | — (the axis gates ship v1 per D12) |
| **v1.x — later** | **Registry perimeter** (JFrog/Artifactory block/allow lists + quarantine — the strongest enforcement point) · engine-swappability (`--engine`: fawltydeps/pip-check-reqs; pluggable vuln backends) · client provisioner (perimeter-integrated env creation — re-opens the § nebi survey refusal *only* at perimeter scope, where provenance is decidable) · `vers` version-range standard in report/SBOM | perimeter block/allow lists |
| **vision** | Axis 5 provenance (Sigstore/SLSA attestation, PEP 740 trusted publishing, in-toto/GUAC) · Axis 6 maintenance (OpenSSF Scorecard, criticality_score, sustainability/give-back) · **malicious-package detection** incl. **typosquat & name-squat** (OpenSSF Package Analysis / GuardDog-class signals) · **public-upstream ring** (scan PyPI/conda-forge themselves → blocklists feeding the perimeter) · reachability analysis · **alternate-library suggestions** (cf_atlas `find-alternative` surfaced at the edge) · OpenVEX/CSAF exchange · TUI · IDE · fleet **control plane** + OSPO + leader scorecards + ~60-tool integration surface (§ Vision catalog) | — |

**Two modes, one identity (D11).** **Edge mode** (v1, no atlas at runtime,
bundled LTS/endoflife tiers — the bundle is an atlas *snapshot*, carrying
build-time `snapshot_at` + `max_age_ok`) is the differentiator — "the fleet
edge, zero data estate at runtime." **Fleet mode** (v1.x) is estate-backed via
`inventory-match`. FR-18 already converges the two; the deck's "three rings"
is this picture (edge = today; perimeter = v1.x-later; public upstream =
vision).

**Story map (indicative — the authoritative breakdown is produced by the
story-0.1 replan):**

- **0.1 — REPLAN: EXECUTED 2026-07-15; RE-BASELINED 2026-07-16 (D12).** The
  PRD (canonical FR32–**FR40** + NFR-S9), architecture (§ Multi-axis
  reconciliation), and epics (Epic 6, stories **6.1–6.9**) were rebuilt from
  this spec; readiness re-ran both days (READY-WITH-CONDITIONS). Ownership:
  engine version-range → story 6.6; KEV feed → 6.4; **EPSS feed + `--min-epss`
  → 6.7; baseline & grandfathering → 6.8; fix-PR actuator → 6.9** (all v1 per
  D12); the schema amendment → 6.1; gate-flag activation → 6.2/6.3/6.5.
  Remaining condition: re-run `bmad-sprint-planning` (30 stories) before any
  bmad-loop execution.
- **6.1** — the versioned `ComplianceReport` schema amendment, **one paid
  amendment** covering: per-axis `gating` bool · `license`/`currency`
  sections (+ per-section coverage/provenance incl. bundled-data
  `snapshot_at`/`max_age_ok`) · `kev_date` + `epss {score, percentile}` +
  per-feed KEV provenance · runtime self-validation update in `report.py`
  (there is no standalone `validate_report.py`) + fixtures + the exact-13
  `Component` test + `_REPORT_AXES` in `report.py:57`.
- Epic 1 (Spine + PyPI engine), Epic 2 (conda/pixi wedge), Epic 3 (policy +
  waivers + warn-only), Epic 4 (machine contract + CycloneDX), Epic 5
  (fleet-readiness + adoption) carry forward as **value groupings**; the
  license, currency, and KEV work is **Epic 6** (epics.md, added by the 0.1
  replan) — delivery order E1 → E2 → E3/E4 → E6 → E5.

---

## Vision catalog (Parts III–IV of the infographic/deck, absorbed 2026-07-15)

Everything here is **vision** (or the named v1.x item it points to) — recorded
so the full intent no longer lives only in the presentation artifacts. None of
it dilutes the v1 contract; the 0.1 replan tiers nothing out of this section
into v1 without an owner decision.

### The three rings (supply-chain depth)

1. **Consumption edge — v1 (today):** scan repos, desktops & CI — the axes on
   what applications actually pull. Precise per-project; sees only what you
   scan.
2. **Registry perimeter — v1.x (later):** block/allow lists + quarantine on
   Artifactory/JFrog; a census of everything that enters; "clean pulls."
3. **Public upstream — vision:** scan PyPI & conda-forge themselves —
   malicious packages, **typosquats, name-squatting**, stale/abandoned
   feedstocks — producing **blocklists** that feed the perimeter.

### The control plane (fleet & ecosystem — vision)

Warden's report contract is the feed for a fleet-wide control plane:

- **Fleet intelligence** — central estate dashboard · cross-repo dependency
  graph · risk-trend tracking · KEV/EPSS enrichment · peer benchmarking ·
  historical SBOM diff · fix-at-source ledger · license-mix dashboard ·
  sponsorship candidates.
- **Policy & governance** — policy-as-code · golden-path catalog · waiver
  governance · typosquat detection · GRC sync · EOL calendar · establish an
  OSPO · license allow/deny families · outbound-OSS policy.
- **Supply-chain integrity** — SBOM registry + VEX · provenance & signing ·
  private-index enforcement · registry/Artifactory gate · upstream intel →
  blocklists · maintainer-risk signals · auditor evidence packs · data
  residency · repackaging patch provenance · source-fix registry · patch
  attribution & upstreaming.
- **Scale & operations** — incremental PR-diff scans · fleet-wide
  auto-remediation · SIEM/ticketing (Jira, ServiceNow, Splunk, Slack) ·
  SSO/RBAC + evidence (SOC 2 / ISO, air-gapped DB) · API + webhooks +
  Terraform · notification routing · PyPI ↔ conda-forge tracking · auto
  NOTICE/attribution in CI · contribute-back PR automation.
- **Program management** — remediation SLAs & MTTR · ownership & chargeback ·
  campaign mode · auto-enrollment · conda-forge onboarding · Python 3.14
  support · stewardship ownership · sponsorship & funding budget ·
  contribution OKRs & burn-down.

### OSS policy, governance & sustainability (OSPO — vision)

Consuming OSS at scale is a stewardship responsibility, not just a risk to
gate. Warden feeds: **policy** (usage & contribution policy, license
allow/deny families, new-dependency intake review), **governance**
(license-obligation tracking, stewardship ownership, export-control &
provenance), **sustainability** (upstream funding — Tidelift / GitHub
Sponsors / Open Collective — maintainer & community health, contribute-back
tracking).

### Leader scorecards (vision)

One report feeding eight executive outcomes: **CISO** (fleet risk score &
heatmap, MTTR/SLA, audit evidence, zero-day readiness) · **CDXO**
(gate-friction, shift-left ergonomics, auto-fix throughput, time-to-green) ·
**CIO** (OSS portfolio inventory, modernization, cost & consolidation, policy
conformance) · **CDAO** (data/ML dependency governance, model & pipeline SBOM
lineage, diffable env reports) · **DevSecOps Lead** (runner provisioning,
rollout config-as-code, gate tuning, engine upkeep) · **General Counsel**
(license-obligation register, copyleft/unknown exposure, outbound clearance,
audit trail) · **CRO** (aggregated risk posture, third-party/acquired-code
risk, regulatory mapping, risk-acceptance governance) · **OSPO Lead**
(stewardship, funding & contribute-back, source-fix ledger, community
health).

### Integration surface (producer-agnostic contract — status per tool)

A purl + CycloneDX report contract lets tools slot in as **engine**,
**data/enrichment feed**, **actuator**, or **consumer**. Current: `deptry`
(hygiene engine) · `osv-scanner` (vuln engine) · OSV.dev (advisory DB) ·
CycloneDX (SBOM). Candidates/planned (all vision unless a v1.x row above
names them): hygiene engines `fawltydeps`/`pip-check-reqs`/`vulture`; resolver
`uv`; vuln engines `osv-scalibr`/`vdb`/Trivy/Grype/`pip-audit`/Capslock;
conda-native **Basilisk** (OSV-compatible advisory API) + **parselmouth**
(PyPI↔conda purl bridge) + `rattler-build`/`rattler` (prefix.dev); SBOM
`cdxgen`/Syft; vuln data VulnerableCode (AboutCode) · PyPA Advisory DB ·
NVD/CVE/GHSA/CWE · EUVD (ENISA) · FIRST EPSS · VulnCheck; license
`license-expression`+SPDX (v1) · ORT · ClearlyDefined · ScanCode (deep-scan,
deferred); currency `endoflife.date` (v1 tier) · Repology; health OpenSSF
Scorecard · criticality_score · Libraries.io · Tidelift; provenance
Sigstore/SLSA · in-toto/GUAC · PyPI Trusted Publishing (PEP 740) ·
model-transparency; vetted-base Google Assured OSS · Anaconda Defaults;
malware OpenSSF Package Analysis · GuardDog. Actuators: Renovate (fix-PR) ·
Allstar · OWASP Dependency-Track · DefectDojo · `cf_atlas` (shares CycloneDX
+ `cfe:*` purls). Consumers: Black Duck · Snyk · Nexus IQ · Mend · JFrog
Xray · Wiz · Prisma Cloud · GitHub Advanced Security/Dependabot · Endor
Labs · Semgrep Supply Chain. **Standards spoken** (tiered): v1 — purl ·
OSV schema · CycloneDX · SPDX · CVE 5.x · CVSS · PEP 639; v1.x — `vers` ·
SARIF · EPSS; vision — OpenVEX/CSAF · SLSA · in-toto · PEP 740.

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
│     ├─ report-schema.json           #   working-FR6 = canonical FR14 (E4)
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
  `epss` surfaced v1.x), and a `summary` (counts + overall pass/fail). *(Per
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
- **Actionable findings only (working-FR7 = canonical FR17).** Each finding is concrete and
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
  ships **v1**, gated on the replan-assigned engine version-range story
  (per canonical NFR-C1 a tested **range**, not an exact pin; the 2026-07-15
  review found no existing story owns this) constraining the engine run-deps (`deptry` /
  `osv-scanner` are `"*"` today — publishing before the pins go live would
  ship the fleet-wide false-error the pins exist to prevent). **Public PyPI +
  conda-forge publish is v1.x.** Because v1 packages the engines as conda
  recipes (`recipes/deptry`, `recipes/osv-scanner` already exist), **Rules 1
  & 2 are engaged now** (conda-forge-expert skill + closeout retro +
  CHANGELOG) — see § Definition of Done.
- **OD6 — execution model + gate → RESOLVED (sequential; severity-tiered
  gate + audited bypass) [refined 2026-07-11].** Sequential branches in v1
  (simpler, still lightweight for NFR1). The gate is **severity-tiered**
  (FR5: exit 0/1/2; `--fail-on=<severity>` / `max_critical` / `max_high` /
  KEV; default block-on-critical-or-KEV; canonical **FR18**) — **not** the original hard "any
  finding blocks" gate (which drives teams to disable it). The coarse
  `--no-fail-on-*` flags are retired in favour of the threshold plus the
  auditable, expiring **bypass** (working-FR9 = canonical **FR24**). Typed
  `error` states (working-FR10 = canonical **FR21**) stay exit-2,
  non-relaxable except via the recorded bypass. **[PARTIALLY SUPERSEDED —
  callout #2/#3/#4: the engines now run in PARALLEL; the status lattice gains
  `indeterminate` (→ exit 1); the v1 default blocks on CVSS-critical **and
  KEV** (D3 pulled the KEV gate into v1 — this bracket previously said "KEV
  deferred", a stale contradiction fixed 2026-07-15).]**

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
    metadata offline, so those components are **`unknown`** — feeding the
    **`warn`** rung in v1 (non-gating) and escalating to **`indeterminate`**
    once the FR-L2 gate activates (honest coverage gap + lock-nudge, exactly
    like an unversioned dep on the vuln axis) — **never a silent `allowed`**. Filling that gap by resolving
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
  detector feeding that loop** (ADD/UPDATE is fleet-mode; edge mode omits it
  with a coverage note — see FR-C1). In v1 the axis is `gating: false`
  (unknown/eol feed `warn` unconfigured; any FR-C2 flag activates the v1 gate — D12 — at which point `unknown` → `indeterminate`).
  Bundled tiers carry build-time `snapshot_at` + a `max_age_ok` verdict so
  registry staleness is always visible (FR-C1 data-age provenance).
- **OD10 — KEV/EPSS enrichment → SPLIT 2026-07-15 (D3).** Enrich osv findings
  with **CISA KEV** + **FIRST EPSS** from cached data feeds (offline default).
  **v1:** KEV enrichment on every security finding **and** the `--fail-on-kev`
  gate — cheap at the *bool* level (the `kev`/`epss` `Finding` fields are
  already present, subset-tested); `kev_date`, the `epss` object, and KEV
  provenance ride the story-6.1 amendment. **EPSS enrichment + the
  `--min-epss` gate ship v1 too (D12).** Feed-absence semantics per FR-K1:
  with no KEV/EPSS policy, null slots gate on CVSS; **under an active
  KEV-blocking or `--min-epss` policy an absent/stale snapshot →
  `indeterminate`, never a silent no-op** (review T1; D12).

**Confirmation decisions (D1–D11, 2026-07-15 — the reshape):**

- **D1** — full reshape around the deck's Parts I–IV, vision tiered after the contract (Parts III–IV absorbed into § Vision catalog, 2026-07-15). **D2** — registry perimeter → **v1.x (later)** (the strongest enforcement point, not the weakest; formerly "v2" — re-bucketed by the 2026-07-15 three-tier taxonomy). **D3** — KEV gate → **v1** (the bare `kev` bool is amendment-free; `kev_date`/EPSS-object/provenance ride 6.1; feed absence under a KEV policy → `indeterminate`, never a silent no-op). **D4** — axes 1–4 in **v1** (superseded by D12: the visible-`warn` mechanism survives as the unconfigured-axis default). **D5** — ~~axis 3/4 gates → v1.x~~ **superseded by D12** (gates ship v1, flag-activated). **D6** — packaging in v1 (internal JFrog) + public v1.x, both behind the replan-assigned engine version-range story (NFR-C1). **D7** — TUI/IDE → vision. **D8** — local client = install + output + **`scan --doctor`** (a flag, not a verb — `prd.md:396` freezes "one verb; no interactive subcommands"; the replan defines its exit-code/output contract against the frozen `{0,1,2,130}` enum). **D9** — currency tiered LTS → endoflife → N/N-1 → unknown, with per-mode tier availability + bundled-data age provenance. **D10** — availability-at-N/N-1 as a distinct ADD/UPDATE finding (fleet-mode; edge omits with a coverage note). **D11** — Warden owns edge **and** fleet as **two modes, one identity** (edge = v1 no-atlas-at-runtime; fleet = v1.x estate-backed; FR-18 converges them). **D12 (2026-07-16, owner-directed re-baseline)** — **v1 absorbs the former "v1.1 NOW" bucket**: the axis-3/4 gates (FR-L2/FR-C2, **flag-activated**: unconfigured → visible `warn`; configured → `policy-violation`/`indeterminate`), **EPSS** `--min-epss` joining the KEV gate (FR-K1), **baseline & grandfathering** (FR-B1 — the fleet-scale adoption on-ramp that makes gates-in-v1 survivable), and the **fix-PR actuator** (FR-A1, opt-in post-scan flag, forge-API only). Supersedes D4/D5's enrichment-only v1 split; v1.x retains publish/provenance-axis/SARIF/backlog/perimeter/swap/provisioner/`vers`.

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
now, public conda-forge v1.x per OD5/D6). The self-check ships **v1 as
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
**edge mode** (v1, no atlas at runtime, bundled LTS/endoflife tiers — "the
fleet edge, zero data estate at runtime"; the bundle is an atlas snapshot
with visible age) and **fleet mode** (v1.x, estate-backed via
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
   KEV/EPSS slots (**v1 populates KEV and EPSS** and gates on both — D12),
   severity carrying tier + raw evidence.
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
   provisioner**; the read-only channel-provenance axis is **v1.x** (its
   mechanism must read the pixi config layers, not just the lock — mirror-mode
   locks record canonical URLs), and `doctor --fix` is foreclosed by the
   one-verb contract (accepted risk — the registry perimeter's first job,
   v1.x-later). Obligation: a reciprocal note in
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
- [ ] Committed `report-schema.json` + runtime self-validation in `report.py`
      (no standalone `validate_report.py` exists); emitted JSON validates
      against the schema in the test suite; human stdout view verified in a
      CI log (working-FR4/FR6 = canonical FR14/FR17 territory).
- [ ] NFR3 verified: no host/source mutation; ephemeral files removed on
      both success and failure paths.
- [ ] **CFE Rules 1 & 2 (engaged, not conditional — D6):** the engine recipes
      (`recipes/deptry`, `recipes/osv-scanner`) are maintained via
      `conda-forge-expert`, and the effort closes with a CFE-skill retro +
      CHANGELOG entry. Both recipes currently lack CHANGELOG entries — that
      retro is owed at closeout.
- [ ] `status: shipped` with `implemented_by:` + `shipped_ref:` set.

**v1 multi-axis DoD (§ Reconciliation scope):**
- [ ] **KEV + EPSS gates (FR-K1, v1 — D12):** security findings carry
      `kev`/`kev_date` + `epss {score, percentile}`; `--fail-on-kev` and
      `--min-epss` block; cached feeds, offline default, per-feed provenance;
      absent/stale feed under an active policy → `indeterminate`.
- [ ] **License axis (FR-L1/FR-L2, v1 — D12):** SPDX via
      `license-expression` (the one new runtime dep) from conda `about:` +
      PyPI `importlib.metadata`; `license` report section with
      `allowed | denied | unknown`; unconfigured → `warn`; `--allow-licenses`
      / `--deny-licenses` activate the gate (denied → policy-violation,
      unknown → indeterminate). No source scanning.
- [ ] **Currency axis (FR-C1/FR-C2, v1 — D12):** tiered LTS →
      endoflife.date → N/N-1 for deps **and** `runtime_python`; `currency`
      report section + the availability-at-N/N-1 (ADD/UPDATE) finding
      (fleet-mode); unconfigured → `warn`; `--max-lag`/`--require-lts`/
      `--fail-on-eol` activate the gate (freshness-preconditioned).
- [ ] **Schema versioned (story 6.1):** `schema_version` bumped; per-axis
      `gating` bool + `license`/`currency` sections added; `validate_report.py`
      + fixtures updated; the frozen v1 keys + `Component` (13 fields) unchanged.

- [ ] **Baseline & grandfathering (FR-B1, v1 — D12):** `--baseline` reads the
      committed, schema-validated `.warden-baseline.yaml`; gate blocks NEW
      findings only; expired entries re-block; applied entries echoed loud.
- [ ] **Fix-PR actuator (FR-A1, v1 — D12):** `--open-fix-prs` (opt-in,
      env-credentialed, post-verdict) opens upgrade/removal PRs via the forge
      API; the scanned tree is never written; `--fix-prs-dry-run` covered.

**v1.x DoD:**
- [ ] Public PyPI + conda-forge publish (behind the engine version-range
      story, NFR-C1).
- [ ] Release sequencing honored: registry perimeter = v1.x (later);
      provenance + maintenance remain vision (unbuilt).

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
