# python-deptry-osv-scanner — Phase-0 Deep Review: Findings, Corrections, Enhancements & Action Plan

**Date:** 2026-07-12 (Rev 2 — adds X11 workstation-mode finding; **Tier 1 APPLIED** in `local-recipes@33010ac0af` on branch `claude/python-deptry-osv-scanner`)
**Scope:** full-corpus review of the intake spec + all BMAD planning artifacts + the implementation scaffold, extended with the surrounding ecosystem (CycloneDX Universe Inventory, cfe-atlas Kedro migration, the conda-forge-expert skill's atlas layer) to ground the tool's mission across all repositories in multiple organizations.
**Status of the effort at review time:** PRD + Architecture + Epics/Stories COMPLETE (20 stories / 5 epics, committed `fd37aa9745`); implementation not started (Story 1.1a next).

---

## 0. Documents reviewed

**Effort artifacts:**

| # | Document | Role |
|---|---|---|
| 1 | `docs/specs/python-deptry-osv-scanner.md` | Tier-1 intake spec (source of truth per repo convention) |
| 2 | `_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/prd.md` | PRD — FR1–FR31 + 22 NFRs + post-architecture reconciliation callout |
| 3 | `…/planning-artifacts/architecture.md` | Architecture — false-green triad, Gaps A/B/C, module tree, patterns |
| 4 | `…/planning-artifacts/implementation-readiness-report-2026-07-11.md` | Readiness gate (PRD READY, 0 defects) |
| 5 | `…/planning-artifacts/epics.md` | 20 stories / 5 vertical-slice epics |
| 6 | `src/shared/packages/python-deptry-osv-scanner/` | Scaffold (pyproject.toml, pixi.toml, cli.py stub, smoke tests) |

**Ecosystem context (the mission grounding):**

| # | Document | Why it matters here |
|---|---|---|
| 7 | `docs/specs/cyclonedx-universe-inventory.md` (SHIPPED, CFE v8.71–8.73) | The org-intelligence layer: `inventory-match --policy` CI gate, `universe-sbom` (856k components), the conda↔pypi mapping exports, `recommend-2027` |
| 8 | `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (ready) | The pipeline end-state: FR-13 SBOM intake, **FR-16 deptry hygiene node**, FR-17 transitive resolver + universe BOM, **FR-18 unified CI policy gate** — both FR-16/FR-18 consume *this tool's* `ComplianceReport` schema |
| 9 | `.claude/skills/conda-forge-expert/reference/dependency-input-formats.md` | The shipped `scan_project` intake matrix — already parses all six of this tool's formats |
| 10 | `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` § Consumer persona | The shipped consumer-facing scanning/gating surfaces this tool must be positioned against |

---

## 1. Executive verdict

The planning chain is unusually strong. The false-green triad (`indeterminate` verdict state + 7-rung lattice + Gap-C ecosystem-identity withhold), the honest-coverage contract, the security-NFRs-as-enforced-mechanisms discipline, and the adversarially-stress-tested 20-story breakdown are genuinely well-engineered — several defects that would normally surface in implementation (green-by-default on a bare recipe, the pytorch→torch silent false-green) were caught and fixed in planning.

The review nonetheless found:

- **1 process-level failure** — the Tier-1 spec was never reconciled to the architecture and now contradicts it in ≥9 places (§ 3, A1).
- **2 contract-critical ecosystem findings** — an **exit-code semantic inversion** between the two gates that the Kedro FR-18 convergence must merge (§ 5, X1), and a **two-producer schema-freeze risk** (§ 5, X2). These are the two places where a wrong v1 freeze forces breaking changes at an already-specced convergence point.
- **4 design-level gaps** — the undecided `indeterminate` exit code, the unowned `pixi.lock`/`conda-lock` extraction (the vuln hero path), two hidden implementation cliffs in the vuln axis (CVSS-vector normalization; the name-level tier requiring direct OSV-DB reads), and the unspecified stable finding-ID scheme that waivers depend on.
- **~12 cross-document contradictions** (spec↔PRD↔architecture↔epics) plus a set of smaller nits.
- **1 scoping correction** — the **workstation / local-terminal use case** is real, already load-bearing (waiver authoring is local-only by design — CI cannot commit the stanza), and unnamed in the PRD (§ 5, X11).
- A body of **enhancements and post-v1 feature candidates**, several of which are directly liftable from shipped ecosystem designs rather than speculative.

**The mission, restated with full ecosystem context (§ 2), is the most important framing produced by this review:** python-deptry-osv-scanner is not a standalone product — it is the **fleet-edge node of a three-layer supply-chain architecture**, and the third producer/consumer of contracts that already exist. Its v1 freeze decisions are therefore ecosystem-wide freeze decisions.

---

## 2. The mission: what this tool is, across all repositories in multiple organizations

### 2.1 The three-layer architecture (two layers already exist)

| Layer | Surface | Data estate | Runs where | Status |
|---|---|---|---|---|
| **1 — Fleet edge (per-repo gate)** | `python-deptry-osv-scanner` | **None** — bundled conda→pypi map + offline OSV DB + two conda-provisioned engines; zero atlas | *Any* org's CI — including orgs with no atlas, no vdb, no internet (JFrog / air-gapped) | planned (this effort) |
| **2 — Org intelligence** | `scan-project` (~40 formats incl. containers/K8s/live envs), `inventory-match --policy` (six-bucket gap/version-lag matching, freshness-percentile policy, vuln/license thresholds), `recommend-2027` (2027–2030 futures), `universe-sbom` | `cf_atlas.db` — 33,624 conda-forge pkgs, 843k PyPI universe, AppThreat vdb, CISA KEV, EPSS | The atlas host / this repo | **shipped** (CFE v8.71–8.76) |
| **3 — Pipeline end-state** | Kedro Universal SBOM pipeline: deptry hygiene node (FR-16) + inventory-match matching node + transitive resolver (FR-17) + **FR-18 unified terminal policy gate** | DuckDB / Parquet, Dagster-orchestrated | The migrated atlas | spec `ready` |

**The connective tissue is this tool's `ComplianceReport` schema.** Kedro FR-16 populates *python-deptry-osv-scanner's* `hygiene` section from its own deptry node; FR-18 assembles the full report with `security` sourced from `inventory-match`/`cve` (the atlas does **not** re-invoke osv-scanner — standalone v1 does); the assembled artifact is schema-validated against this tool's contract. The planned promotion of the tool into the atlas surface is asserted by the Kedro spec to be "a wiring change, not a redesign" *precisely because* the schema is shared. Every v1 freeze decision in Story 1.1a is therefore a **three-layer contract decision**.

### 2.2 The fleet is concrete and bimodal

The PRD's "20,000+ repo fleet" is the generic story. The concrete fleet, visible from the ecosystem docs:

- **Mode A — source-less manifest repos (the majority mode):** conda feedstocks. The operator maintains 769 feedstocks (537 sole / 232 co) across the conda-forge org + their own; this repo alone carries ~1,950 recipes. These repos have a `recipe.yaml`/`meta.yaml` and **no Python source tree** — deptry's AST/import analysis has nothing to analyze. The hygiene axis is structurally inapplicable in the fleet's *dominant* repo shape (see X4/A-h).
- **Mode B — source+manifest repos:** pixi/pyproject projects (apps, libraries, analytics repos) where both axes fire and `pixi.lock` is the vuln hero path.
- **Both modes inside enterprise/air-gapped organizations:** the repo's enterprise discipline (`docs/enterprise-deployment.md`, `_http.py` JFrog/mirror routing, the `pypi.org/packages` URL convention) applies to every artifact this tool needs at runtime or provision time — engines, offline OSV DB, map refreshes. Layer 3's FR-17 makes mirror-routing a *hard requirement* on the tool's pipeline twin; the standalone edge tool cannot be the one component in the estate that ignores it.

### 2.3 What is genuinely unique about the edge tool (vs the shipped incumbents)

With `inventory-match --policy` already shipped as a CI gate, the edge tool's differentiation must be stated precisely (the PRD currently doesn't — see X9):

1. **Zero data estate.** `inventory-match`/`scan-project` require the atlas (`cf_atlas.db`, gitignored, heavy env). The edge tool runs in any org's CI with only conda-provisioned engines + bundled assets.
2. **Pinned-version vulnerability truth.** `inventory-match`'s vuln thresholds read atlas Phase-G rollups — `vuln_*_affecting_current`, i.e. the **current conda-forge version's** posture. The edge tool scans **your pinned/locked versions** via osv-scanner. These are complementary, not redundant: "are MY pins vulnerable" vs "is the ecosystem current version vulnerable / am I behind."
3. **Dependency hygiene.** deptry-based unused/missing/transitive/misplaced analysis — no shipped in-house surface does this (until Kedro FR-16, which will *reuse this tool's schema*).
4. **The honest-verdict contract.** The `indeterminate` state, split coverage, fail-closed guards — a trust posture none of the incumbents (in-house or external) formalize.

---

## 3. 🔴 A-series: Corrections (contradictions & gaps to fix before implementation)

### A1. The Tier-1 spec was never reconciled — it now contradicts the architecture in ≥9 places
**Severity: highest (process failure).**

**What happened:** the `bmad-correct-course` reconciliation pass landed the 7 architecture-driven deltas into the **PRD only**. But this repo's own convention (CLAUDE.md / AGENTS.md) makes `docs/specs/*.md` the *framework-neutral source of truth* — the one document any future agent/tool/human reads first. It is now the most stale artifact in the set.

**The stale points (spec line references):**

| # | Spec location | Spec says | Superseded by |
|---|---|---|---|
| 1 | `NFR2` (:238) | "no `pyyaml` or other heavy parsers" | Lean lib policy: PyYAML(safe_load/safe_dump), packaging, cyclonedx-python-lib, jsonschema |
| 2 | `OD3` (:532) | stdlib `re`/`tomllib` only; YAML lib deferred | E1 = non-rendering neutralize + `safe_load`; v1 recipes `safe_load` directly |
| 3 | `OD6` (:547) + data flow (:378) | "Execution (**sequential** in v1)" | NFR-P-concurrency: engines run **in parallel** |
| 4 | `FR5` (:173) | default blocks on "critical CVE **or KEV**" | KEV deferred post-v1, annotation-only (PRD § Domain) |
| 5 | `FR4` (:164) | status enum lacks `indeterminate`; uses `warnings` | 7-rung lattice; canonical token is `warn` |
| 6 | Data flow step 1 (:371) | **priority-order** discovery, one winner | Architecture: **union coverage** — scan all discovered manifests |
| 7 | Data flow step 2 (:377) | writes `.scanner-temp-reqs.txt` | osv temp input must be named `requirements.txt` (parser inference) — see also B1 |
| 8 | Story 1.1 AC (:473) + report arch (:412, :504) | "no pyyaml imported"; `jsonschema` **test-only** | jsonschema is a **runtime** dep (FR14 report self-validation) |
| 9 | Header (:17) + § Story sharding | "~4 epics / ~12–16 stories"; old story stubs | 5 epics / 20 stories in `epics.md` |

Plus minor: exit enum `{0,1,2}` (no 130); `report-schema.json` at package root vs `src/…/data/`; the "installed env" osv-input fallback (:389) that the architecture correctly dropped (conflicts with the pre-build posture) but the spec still lists.

**Why it matters:** any future session, agent, or human that starts from the spec (the documented entry point) will re-derive decisions the architecture already reversed — e.g. re-imposing stdlib-only extraction or sequential engines. The spec-first convention only works if reconciliation reaches the spec.

**Recommendation:** one spec-sync pass — add a "Post-architecture reconciliation (2026-07-11)" callout mirroring the PRD's, apply surgical edits to OD3/OD6/FR4/FR5 and the data-flow section, point § Story sharding at `epics.md` as the superseding artifact, and add a **§ Cross-spec impact & sync** section (the cyclonedx spec is the exemplar) carrying the X1 exit-code obligation (§ 5).

---

### A2. `indeterminate`'s exit code is undecided — the projection is not actually total
**Severity: high (blocks Story 1.1a).**

**What:** the architecture (:115) and FR20 (prd:511) both say `indeterminate → non-zero / never a silent 0` — but never pick **1 or 2**, and the exit enum is the frozen closed set `{0,1,2,130}`. Story 1.1a's acceptance criterion says the projection must be "total over all 7 rungs"; as documented, it isn't — a dev agent must guess, and the two guesses produce different fleet behavior.

**Recommendation: `indeterminate → exit 1`.** Rationale:
- **Exit 2 means "the run is untrustworthy"** (operational failure — engine crash, unparsable manifest, config error). Fleet routing treats rc==2 as "page the platform/CLI owner."
- **`indeterminate` means the run is trustworthy** and honestly reports *unproven cleanliness* — a policy-family outcome ("not provably clean"), analogous to a policy violation, not an infrastructure failure.
- Keeping 2 pure preserves Sam's (J3) typed-error routing semantics: `rc==2` → infra problem; `rc==1` → the repo has a real finding or an unproven dep set to fix (lock, waive, or `--warn-only`).
- Also rename the "6→3 exit projection" — it's now 7 rungs → 4 codes.

---

### A3. `pixi.lock` / `conda-lock.yml` extraction is unowned — and it's the vuln hero path
**Severity: high (structural gap).**

**What:** the PRD's own positioning (reconciliation delta 5) is that **pixi.lock = the vuln hero path** — the artifact that turns a conda/pixi project's vuln coverage from "risk surface + lock-nudge" into real version-pinned scanning. Yet:
- The architecture module tree (arch:254–258) has `extract/{recipe_v1,meta_v0,environment_yml,pixi,pyproject,requirements}.py` — **no lockfile extractor module**.
- No story AC owns "parse pixi.lock → locked-closure inventory with `==` versions." It appears only as a subordinate clause in Story 2.1 (`pypi_identity` taken "from pixi.lock `pypi:` entries") and 2.3's `direct-only`/`locked-closure` marking.

The single highest-value input the tool can consume has no module, no fixtures, and no acceptance criteria.

**Recommendation:** add `extract/lockfiles.py` (pixi.lock + conda-lock.yml) to the module tree, and give Story 2.1 (or 2.3) explicit ACs: *Given a `pixi.lock` with conda + pypi packages across environments, the locked closure lands in the inventory with exact versions; `vuln_matchable=true` where `pypi_identity` resolves; coverage marked `locked-closure`; conda-lock's manager-aware rows (conda vs pip) route to the correct ecosystem.* Inherit the shipped parser's documented pitfall as a fixture (see X8): pixi.lock URL-form entries must extract the basename *before* name/version regexing (the atlas parser once mis-captured `linux` as a package name from the subdir segment).

---

### A4. Two hidden implementation cliffs in the vulnerability axis
**Severity: high (schedule risk hiding in "small" stories).**

**Cliff 1 — CVSS severity normalization.** OSV's `severity` field carries **CVSS vector strings** (`CVSS:3.1/AV:N/…`), not tier labels. Gating on "critical" (FR18) therefore requires either (a) trusting `database_specific.severity` (GHSA-only; not guaranteed present), or (b) **computing the CVSS base score from the vector** — a real pure-function implementation (v3.1 + v4.0 differ). No FR, module, or story owns vector→tier normalization. osv-scanner's own table output embeds a Go CVSS library to do exactly this; our JSON-reading path gets the raw vectors.

**Cliff 2 — the name-level CVE tier requires reading the OSV DB directly.** Story 2.4's "does package X carry *any* critical CVE across any version?" is **not an osv-scanner invocation** — osv-scanner scans lockfiles. Answering it means our own code iterates the offline `{ecosystem}/all.zip` advisories, taking on OSV-schema parsing plus the same severity computation as Cliff 1.

**Recommendation:** fold both into Story 1.3a's spike scope as decision-record items (severity-normalization strategy: `database_specific.severity` when present → computed base score fallback; name-level-tier mechanism: direct all.zip iteration with a minimal matcher). Add a `severity.py`-shaped responsibility to the module tree. Note the in-repo prior art (X6): the CFE `update-cve-db` surface already maintains an offline OSV store — its download/parse mechanics are reusable.

---

### A5. Direct epics↔architecture contradiction: the `Ecosystem` enum
**Severity: medium (one-line fix, but it's in the frozen contract).**

**What:** architecture (arch:215): `Ecosystem {pypi, conda}`. Epics Story 1.1a froze `{pypi, conda, pixi}` (a party-mode roundtable artifact that was baked in unexamined).

**Why the architecture is right:** pixi is a **manifest format, not a package ecosystem** — there is no `pkg:pixi` purl type; a pixi `[dependencies]` section resolves from conda channels and `[pypi-dependencies]` from PyPI. A third enum value would poison purl emission, identity keys, and the cross-ecosystem non-merge rule (FR7).

**Recommendation:** correct epics 1.1a to `{pypi, conda}`; the pixi-manifest fact lives in `provenance` (which already carries `(manifest, section)` tuples).

---

### A6. Stable finding-IDs + hygiene/indeterminate waiver semantics — unspecified, and waivers depend on them
**Severity: high (silently blocks Epic 3).**

**What:** waivers must match findings **across runs**, so finding IDs must be stable and deterministic — no document defines the ID scheme. Worse:
- NFR-S3 defines waiver keys as `(vuln-id, package, ecosystem)` — which has **no representation for hygiene findings** (FR24 says "a finding"; J4's premise is waiving; what does a DEP001 waiver key on — the missing module name? the manifest?).
- **Are `indeterminate` outcomes waivable?** Undecided anywhere. If not, a bare-recipe beachhead user can *never* reach exit 0 without a lockfile — probably intended as the lock-nudge, but it must be an explicit decision, because it defines the beachhead's day-one experience (see A7).

**Recommendation:** add to Story 1.1a's frozen contract: (a) the finding-ID scheme — e.g. `vuln:<advisory-id>:<pkg>@<ver>` / `hygiene:<DEP-code>:<module-or-pkg>` / `indeterminate:<reason>:<pkg>` — deterministic, documented, and part of the report schema; (b) the waiver-scope decision for all three families. **Recommended: yes, indeterminates are waivable-with-expiry** — an auditable, time-boxed acceptance of unscannable deps is exactly what waivers exist for, and it gives the beachhead a graduated path (waive-with-expiry → lock before expiry) rather than a wall.

---

### A7. Three PRD prose sites still contradict the false-green triad (missed by correct-course)
**Severity: medium-high (they describe product behavior that no longer exists).**

1. **J1** (prd:186): "empty-findings-at-partial-coverage is never clean — it is **warn at minimum**." Post-triad, name-only/unresolved components route to `indeterminate` — which sits **above** warn and exits **non-zero**. Priya's day-one scan of a bare recipe is *red by design*; the narrative still implies a soft yellow.
2. **FR16** (prd:505): the "qualified verdict (*clean at N%*)" phrasing. Post-triad, vuln-coverage < 100% ⟺ ≥1 indeterminate component ⟹ the run status is never `clean at N%` — the qualified-coverage text renders under an `indeterminate`/`warn` status, not a qualified `clean`.
3. **CLI state-machine table** (prd:418): "`--offline` + OSV DB unreachable → vuln dimension `coverage: skipped` … **default exit 0** (data, not failure)." This directly contradicts the triad — the architecture explicitly routes *withheld/**skipped**/unresolved* to `indeterminate → non-zero`. The architecture wins; this cell is dead text.

**Why it matters beyond hygiene:** these three sites collectively hide the single most important adoption fact of the product. **State it plainly, in the spec and the README:** *a bare `recipe.yaml` scan exits non-zero until you lock, waive, or run `--warn-only`.* That is the product working as designed (the lock-nudge), and the docs should sell it as such rather than let users discover it as a surprise red wall.

**Recommendation:** three surgical PRD edits + the honest adoption statement. Also re-examine FR19 in this light (A8).

---

### A8. FR19 (coverage-floor gate) is now nearly redundant — re-justify or repurpose
**Severity: medium (requirements hygiene).**

**What:** post-triad, *any* coverage gap already produces a non-zero exit via `indeterminate`. `--fail-under-coverage` (default off) gates almost nothing: by the time coverage < 100%, the run is already non-zero.

**Recommendation:** either (a) delete FR19, or (b) **repurpose it as the warn-only graduation dial**: under `--warn-only`, everything exits 0 — a coverage floor that *still fails* under warn-only ("report-only, but never let coverage regress below N%") gives the on-ramp a ratchet-like guardrail and a reason to exist. Option (b) also partially compensates for the deferred baseline-ratchet (C3).

---

### A9. Smaller but real corrections

| # | Item | Fix |
|---|---|---|
| a | **Epics 1.6 vs PRD D2 polarity:** D2 says Python-signals-present-but-nothing-parses = **exit 2** (fail-closed error); epics 1.6 routes ambiguous/empty discovery to `indeterminate`. | Sharpen 1.6's AC: *empty-with-Python-signals → `error` (exit 2, per D2); ambiguous/partial discovery → `indeterminate`.* Different failure classes, different owners. |
| b | **DEP005 unmapped in the hygiene policy table.** Gap A's table covers DEP001–004; epics 1.2 says "DEP001–005"; the pinned engine contract labels DEP005 "unused-dev" — verify the actual DEP005 semantics against the pinned deptry version at Story 1.2 (it may be "standard-library module declared as dependency" in current deptry). | Add DEP005 → `warn` to the ConfigLoader table + verify the label. |
| c | **PRD-internal "parallel execution" ambiguity:** listed as post-MVP Growth (prd:156, :456) while NFR-P-concurrency mandates parallel engines in v1. | Disambiguate: the Growth item means *multi-manifest / fleet-level* parallelism; the two engines are parallel in v1. |
| d | **`status.driver` missing from the epics freeze list** — the architecture makes it mandatory on every non-clean status (arch:118: "an exit-2 that can't say 'critical CVE' vs 'blocking DEP001' is an incoherent contract"); Story 1.1a doesn't freeze it. | Add to 1.1a's frozen-schema AC. |
| e | **Waiver in-file `version:` + unknown-version rejection** (PRD CLI :434) dropped from Story 3.2. | Add AC: waiver file carries `version:`; unknown/future version → typed rejection, never guessed. |
| f | **Architecture module-list drift:** § Implementation Patterns tree (arch:191) lacks `models.py`; § Project Structure (arch:250) has it. | One line: the § Project Structure tree is authoritative. |
| g | **Story 5.1's `--explain`** — the PRD reserved `explain` as a **post-v1 subcommand** (prd:381); epics 5.1 names it as a v1 capability. | Reword 5.1: remediation text in the report/diagnostics (NFR-U1), not a new subcommand surface. |
| h | **Hygiene on source-less repos** — see X4; this is the fleet's majority mode, not an edge case. | Define: no adjacent Python source → hygiene axis honestly `not-applicable`/skipped (matching Kedro FR-16's already-specced semantics), never 100%-DEP002 noise. AC in 2.2a/2.3. |
| i | **pixi ≥ 0.72.2 runtime role** (PRD open Q 8a) never answered. The tool never invokes pixi (the extractor may not subprocess; `pixi.lock` is `safe_load`-parsed) → it's a build/dev-env floor, not a runtime constraint. | One line in the architecture. |
| j | **Corpus is a biased distribution** — the ~1,950-file corpus is this repo's own (CFE-generated, curated, clean) recipes. | Story 5.2's harvest task adds a small adversarial out-of-repo recipe set (exotic selectors, `{% for %}`, unicode, giant files) so the ratchet isn't grading on a friendly distribution. |

---

## 4. 🟡 B-series: Enhancements to the existing plan

### B1. osv-scanner's `--lockfile=<parser>:<path>` override may remove the temp-file-naming constraint
The architecture pins "osv's temp input file **must be named literally `requirements.txt`**" (basename-based parser inference). osv-scanner supports an explicit parser-override syntax (`-L requirements.txt:/tmp/xyz.txt`). If the pinned version supports it, the constraint disappears and the temp-file plumbing gets simpler and less fragile. **Verify in Story 1.3a against the pinned version range.**

### B2. Story 1.3a scope additions (all cheap decision-record items)
1. **Concrete engine version ranges.** NFR-C1 demands a "tested version range" with fail-loud out-of-range behavior — but no range exists anywhere (e.g. `osv-scanner >=2.0,<3`, `deptry >=0.23,<0.27`). Decide the ranges + the version-detection mechanism (`--version` parse) in the spike; Story 5.2's "out-of-range fails loud" AC needs them.
2. **Cold-start UX on a non-air-gap machine.** "Air-gap = fail-loud if DB absent" is decided; the default dev-laptop path is not. Recommendation: fail-loud **plus an actionable nudge** ("run `python-deptry-osv-scanner download-db` or set `--db-path`") — NFR-U1 applies to this failure too.
3. **DB packaging decision:** whether the offline OSV DB ships as a conda package (and becomes a run-dep) or a provisioning step — with X6's `update-cve-db` prior art evaluated first.

### B3. Make the report's `axis` dimension open-by-design
Findings and coverage are keyed by axis (`hygiene`, `vulnerability`). Freeze the *mechanism* (axis-tagged findings, per-axis coverage) but declare the axis set **open** — a license axis (C7) or SAST sibling lands additively instead of schema-breaking. Near-mandatory given X2 (the schema already has a second producer with different sources).

### B4. Routing AC completeness for pixi manifests
Story 2.2a names `[dependencies]`/`[pypi-dependencies]`; real pixi manifests also carry `[feature.*.dependencies]`, `[feature.*.pypi-dependencies]`, `[target.*.dependencies]`, host/build tables. The provenance-now decision covers them conceptually — name them in the AC so fixtures exist. (The shipped `scan_project` pixi.toml parser reads feature tables — parity matters per X8.)

### B5. Own the dogfood gate
The spec's DoD requires the tool to run clean on this repo's own `pixi.toml`/`pyproject.toml`; no story AC owns it. Add to Story 5.2 + a `pixi run` task. It's also the architecture's stated supply-chain mitigation ("the tool dogfooding itself on its own deps").

### B6. Name the reference hardware for NFR-P-warm
"≤ ~2s p95 (engines stubbed)" is unfalsifiable without naming the box. One line in 5.2's calibration AC.

### B7. Declare the OS matrix
NFR-C1 pins Python/pixi/engines but not platforms. linux-64 is the fleet; state whether osx-arm64/win-64 are supported, best-effort, or unsupported. ("Unstated" reads as "supported" to an adopter.)

### B8. Adopt the ecosystem's `resolution:` vocabulary
The shipped `inventory-match` stamps rows `locked / resolved / direct`. The tool's `locked-closure` vs `direct-only` coverage marking should adopt the same tokens (or map 1:1) so layer-2/3 reports compose without translation.

---

## 5. 🔴 X-series: Cross-ecosystem findings (from the extended context)

### X1. Exit-code semantics are **inverted** between the two gates FR-18 must converge — nobody owns the flip
**Severity: highest of the ecosystem findings.**

- **This tool (frozen enum, MAJOR-change to alter):** `0` pass · **`1` policy-violation** · **`2` error** · `130` SIGINT.
- **Shipped `inventory-match --policy`** (cyclonedx spec :637; confirmed atlas-phases-overview :178): `0` pass · **`2` policy violations** · **`1` error**.
- **Kedro FR-18** (kedro:633) declares the converged gate as "exit 0 pass / **1 policy-fail / 2 error**" — the *python-deptry-osv-scanner* convention — while naming `inventory-match --policy` as its co-source.

`rc==2` means "page the platform team" in one tool and "block the merge" in the other — and the convergence spec silently assumes inventory-match flips (a breaking change for its existing CI consumers) without any spec owning the flip. A fleet CI template with `elif rc == 2:` routing misroutes one of the two tools today.

**Recommendation:** this tool's frozen enum wins (it's declared a closed set; FR-18 already matches it). Record the inventory-match exit-code migration as an explicit **cross-spec sync obligation**: (a) in this tool's spec (the new § Cross-spec impact & sync from A1), (b) as an amendment note on the shipped cyclonedx spec, (c) leave Kedro FR-18 as-is (it already states the target). Sequence the inventory-match flip with a deprecation window (accept an `INVENTORY_MATCH_LEGACY_EXIT=1` env for one release) since it has live consumers.

### X2. The ComplianceReport schema has **two producers** — Story 1.1a must freeze it producer-agnostically
Kedro FR-16/FR-18 assemble the same schema with a different security source (atlas vdb + `cisa_kev` + EPSS — not osv-scanner). If 1.1a freezes osv-flavored fields, the first atlas-assembled report forces a schema bump at the convergence point. Concretely:

1. **Vuln-data provenance must be generic** — `{source: <string>, snapshot_at, max_age_ok}`, not `osv_db_*`-named fields.
2. **Optional KEV/EPSS slots now.** v1 never populates them (the KEV deferral stands — and is *strengthened*: the atlas producer gets KEV free from its `cisa_kev` table), but the schema must have the fields so the atlas-assembled report can carry them without a version bump.
3. **Severity carries both** a normalized tier and the raw evidence (CVSS vector string or database label) — the two producers derive tiers differently (A4 Cliff 1 vs the atlas's `_coerce_cvss_score` path).
4. **Source-less hygiene semantics identical across producers** (X4).

### X3. `run_constrained` / `run_constraints` — E1's walk list contradicts the shipped parser's deliberate exclusion
The architecture (arch:144) walks `requirements.{build,host,run,run_constrained|run_constraints}`. The shipped S5a `meta.yaml` parser **deliberately does NOT harvest `run_constrained:`** (dependency-input-formats.md:66 — "correctly NOT harvested") — because constrained entries are *not dependencies*: they are version pins applied only **if** the package happens to be installed. Ingesting them as deps over-reports the inventory (components that may exist in no resolved environment), pollutes the SBOM component count, and skews coverage denominators.

**Recommendation:** exclude `run_constraints` from the dependency set — or ingest with `provenance: constraint`, excluded from vuln matching and the SBOM invariant count. Align the differential oracle accordingly (renderers treat them separately too).

### X4. Kedro FR-16 already decided the source-less-hygiene semantics — this tool never inherited them
FR-16 (kedro:625): the deptry node runs "**when project source code accompanies the manifest** — for source-less inputs the node **skips gracefully and the report records the reduced scope** instead of failing." That is finding A9-h — except it's not a suggestion: it's the shared schema's *other producer* already specced to behave that way, and the source-less case is the **majority mode** of the concrete fleet (§ 2.2). v1 must define the identical semantic or the same report field means different things per producer.

### X5. The name-mapping confidence threshold (first-story open item) is **already answered by existing data**
The atlas mapping export — the exact TSV the bundled map generates from — carries per-pair **`match_source` + `match_confidence`** columns (21,403 pairs; provenance tiers `parselmouth / recipe_source_url / name_coincidence / none`). The DEP001-block gate's "high-confidence vs ambiguous" rule falls out directly:

| Map provenance | DEP001 treatment | vuln `pypi_identity` |
|---|---|---|
| `parselmouth` / `recipe_source_url` / verified | block-eligible | trusted |
| `name_coincidence` | `warn` | *withheld* or trusted-with-flag (decide in 2.1) |
| `none` / unmapped | `warn` | withheld (`unmapped-ecosystem`) |

**Recommendations:** (a) Story 2.1's generator **preserves these columns** into `data/conda_pypi_map.json` — do not flatten to name→name; (b) the threshold open-item closes with the table above; (c) cross-check the generated map against **`prefix-dev/purl-associator`** (externally-maintained canonical conda-forge→purl mappings, published `mappings.json` — already adopted as an atlas corroboration source) as a second independent corroborator; (d) note pixi ≥0.71's custom `conda-pypi-map` support — the same asset is emittable in pixi's format later (a cheap post-v1 deliverable).

### X6. The offline-OSV-DB spike has in-repo prior art: `update-cve-db`
The CFE skill already ships `update-cve-db` — an offline OSV store provisioning surface (wrapped by Kedro Story B5 alongside `vdb-refresh` and `update-mapping-cache`), under `.claude/data/conda-forge-expert/cve/`. Story 1.3a should **evaluate reuse first** (or at minimum its download + integrity mechanics) instead of writing a second OSV-DB downloader in the same repo. And the provisioning fetch must be **env-var mirror-overridable** (JFrog) — mirroring the `PYPI_BASE_URL`-style contract Kedro FR-17 mandates for its resolver twin. The standalone edge tool is stdlib-lean, but its *provisioning step* is not exempt from the estate's air-gap discipline.

### X7. SBOM conventions are already standardized estate-wide — Story 4.1 must adopt, not invent
Three SBOM producers will coexist (`universe-sbom`, `scan-project`, this tool). Two conventions are pinned:
1. **The `cfe:*` property namespace** (cyclonedx design decision 1): mapped conda↔pypi identity is expressed as properties on the conda component — `cfe:pypi_purl`, `cfe:match_source`, `cfe:match_confidence`. The Kedro normalizer explicitly preserves this namespace. When this tool resolves a conda component's `pypi_identity`, emit the same keys.
2. **G98 purl normalization** — lowercase, `_`→`-`, **dots preserved** (PEP 503 over-normalizes dotted names) + the `?channel=conda-forge` qualifier on conda purls.

**Recommendation:** add both as explicit Story 4.1 ACs, plus a round-trip AC: `scan-project --sbom-in <our-BOM>` ingests cleanly (its purl-prefix classifier is already qualifier-safe — verified in the cyclonedx spec's seventh amendment).

### X8. A second, cheaper differential oracle exists — and parse-parity is a promotion prerequisite
The shipped S5a parsers already parse **all six** of this tool's formats (recipe.yaml/meta.yaml-as-manifests landed CFE v8.71.0; battle-tested in a 2,039-test suite), with documented construct decisions that mostly mirror E1's matrix. Two implications:

1. **Story 2.2a's differential oracle can cross-check against `scan_project`'s parsers** as a fast second oracle beside the rattler-build/conda-build render — pure-Python, already fixture-covered, and any divergence is signal for *both* codebases.
2. **The "promotion is wiring, not redesign" claim (Kedro FR-16) silently assumes parse-parity** between E1 and `scan_project`. Known deltas already exist: E1 unions selector branches (S5a skips templated names); X3 run_constrained; S5a's `=1.2` fuzzy-pin range semantics. Divergence is acceptable for v1 (different tools, different risk postures) — but record a **parity matrix** as a Wave-E/retro obligation so the promotion claim stays true when the time comes.

Also inherit the shipped parser's documented **pixi.lock URL-basename pitfall** as a fixture (see A3).

### X9. The competitive landscape omits the in-house incumbents — operators need a "which gate when" table
The PRD's landscape table (Trivy/Syft/Grype/pip-audit/deptry/QuantCo) never mentions that **this repo already ships two scanning gates** — and with this tool that's three, and with Kedro FR-18 four. The differentiation is real (§ 2.3) but implicit. Also, "no tool brings dependency-hygiene to conda at all — zero incumbents" needs an in-house footnote: `env-inspect --audit` ships adjacent manifest-hygiene (pure-intent / transitively-covered / drifted-explicits buckets), and Kedro FR-16 makes deptry-on-conda a planned atlas node (consuming this tool's schema).

**Recommendation:** add an in-house row to the landscape table, and a one-screen decision table in the spec:

| You have | Use |
|---|---|
| Any repo, any org, no atlas, need a CI gate on pinned deps + hygiene | **python-deptry-osv-scanner** (edge) |
| The atlas host; need gap/version-lag buckets, freshness policy, packaging worklists | `inventory-match --policy` (+ `add-handoff`) |
| Anything exotic — containers, K8s, live envs, third-party SBOMs, non-Python ecosystems | `scan-project` |
| The migrated pipeline (future) | the FR-18 terminal gate (assembles this tool's report schema) |

### X10. Post-v1 feature imports from the shipped S5 design (proven, not speculative)
- **`--weights` criticality sidecar** (cyclonedx:640): "conda-forge blast radius is not the user's blast radius" — per-package criticality multipliers on gate thresholds. Directly adoptable.
- **The 14-day staleness-refusal pattern** (`--allow-stale` override) validates the `--db-max-age` fail-loud posture — keep flag symmetry (`--allow-stale-db`).

### X11. The workstation / local-terminal use case is real, already load-bearing, and unnamed
**Severity: medium (scoping correction, not new scope).**

**What:** the PRD classifies the tool as "non-interactive CI/CD gate; primary consumer is a pipeline, not a human terminal" and dropped the `developer_tool` label. But the design already **depends** on local execution: the `--bypass` flow emits a waiver stanza *for the human to commit* (NFR-S4 — the tool never writes the repo). **CI cannot commit waivers** — J4 (the bypass loop, a headline v1 feature) only works if the developer runs the tool at a terminal. Three genuine local use cases:
1. **Pre-push testing** — verify a fix clears the finding; trial the gate before CI wiring. Realistically, every adoption *starts* here (J6's warn-only on-ramp begins at a terminal).
2. **Waiver authoring** — already local-only by design (above).
3. **Environment debugging** — reproducing an `engine-unavailable` exit 2 outside the runner image (the actual justification for `doctor`, C2).

**What already works** (mechanically, terminal use was designed in without being named): argparse CLI; `--format text` is the *default* (human summary); `--no-color` auto-detects TTY (i.e. color **on** at a real terminal); NFR-U1 "fail with a fix" diagnostics; non-interactive stays fine locally (`--bypass` takes `--reason` inline — no prompts, ever).

**The gaps bite only outside CI** — where the user *is* the platform team:
1. **Cold-start = every run fails.** Offline-by-default + no DB on the laptop → typed error, exit 2, forever. In CI the runner image is pre-provisioned; locally nobody did it. The B2.2 nudge becomes load-bearing, and a provisioning command is needed.
2. **The online opt-in vuln path has no owner.** The PRD's domain section says online osv.dev querying "remains supported but opt-in and never silent" — but **no FR, AC, or story implements it**. It is the natural *laptop* path (no DB provisioning needed). Decide in Story 1.3a: ship an explicit `--online` mode (the *engine* egresses, explicitly — NFR-S2-consistent) **or** declare v1 offline-only-everywhere and make provisioning trivial.
3. **No workstation install story** (`pixi global install` / the local channel now; conda-forge per OD5 later).
4. **`doctor` (C2) jumps the queue** — re-rank to v1-if-cheap; it is FR21's detection logic re-exposed.

**Recommendations:** add persona **P8 (local developer / workstation mode)** + a compact Journey 10 to the PRD; correct the classification note (*primary = pipeline; supported secondary = a developer at a terminal; interactivity stays zero*); fold the deltas into Story 1.3a (cold-start UX + online-opt-in decision), 1.3b (chosen mode AC), and 5.1 (install story); state the recommended first contact = a local `--warn-only` run. **Guardrail: local mode must not soften the gate** — same lattice, same exit codes, same no-prompts, same fail-loud; only the provisioning UX and (possibly) the explicit online path differ.

---

## 6. 🟢 C-series: New feature suggestions (ranked; post-v1 unless noted)

| # | Feature | Why | Cost |
|---|---|---|---|
| **C1** | **Waiver → CycloneDX VEX emission** | The tool already computes vulnerabilities + waivers; a CycloneDX VEX document (analysis state `accepted`/`false_positive`, justification from `--reason`, expiry) is nearly free via cyclonedx-python-lib and turns the bespoke waiver file into the **standards-native** exchange format Dependency-Track-class consumers already ingest. Elegant FR24×FR27 synergy; also closes the loop with `scan-project`'s shipped VEX ingestion. | S–M |
| **C2** | **`doctor` subcommand** — **re-ranked v1-if-cheap per X11** | Environment self-check without scanning: engines present + in version range, DB present/fresh/authentic, config parses. It's FR21's detection logic re-exposed; serves the platform engineer debugging runner images fleet-wide **and is the first thing a workstation user (P8) needs** ("is this machine scan-capable?"). | S |
| **C3** | **Baseline ratchet as the #1 v1.1 item** | `--warn-only` currently has **no graduation mechanism** — the deferred new-findings-only ratchet *is* the exit path from the on-ramp. Without it, warn-only repos stay warn-only forever and the `gate-disabled = 0` anti-metric quietly loses. (A8's FR19 repurposing is a partial stopgap.) | M |
| **C4** | **`upgrade-plan` report block** | Aggregate min-fixed-versions per package from data FR10 already collects ("bump `cryptography` to ≥42.0.4 to clear 3 findings"). Machine-readable remediation, trivially derived. | S |
| **C5** | **Packaged CI surfaces: composite GitHub Action + `pre-commit` hook** | The beachhead (feedstock maintainers) lives in pre-commit; platform teams distribute via Actions templates. Pure packaging, no engine code. | S |
| **C6** | **SARIF output** (already value-space-reserved) | Rises in value once C5 exists (GitHub code-scanning annotations). | M |
| **C7** | **License-compliance third axis** | conda-deny-style license gating over the same `ResolvedInventory`; enabled cheaply if B3 (open axis enum) lands in v1. Aligns with the family convention (`<language>-<hygiene>-<vuln>` siblings sharing the report schema). | M |
| **C8** | **Waiver ops (`waivers list / prune / renew`)** | The deferred expiry-storm story; becomes real the first time a fleet hits 100 simultaneous expiries. | S–M |
| **C9** | **`--pixi-map` export of the bundled map** (from X5d) | Emit `data/conda_pypi_map.json` in pixi ≥0.71's `conda-pypi-map` format so any pixi user can consume the atlas-derived mapping. | XS–S |
| **C10** | **`--weights` criticality sidecar** (from X10) | Estate-specific criticality multipliers on gate thresholds — proven design from the shipped `inventory-match`. | S–M |

---

## 7. Consolidated action plan

### Tier 1 — Now (planning hygiene; one session, one commit) — ✅ APPLIED 2026-07-12, commit `33010ac0af`

| Item | Action |
|---|---|
| A1 + X1 + X9 | **Spec-sync pass**: post-architecture reconciliation callout + surgical edits (OD3/OD6/FR4/FR5/data-flow/story-sharding pointer) + new **§ Cross-spec impact & sync** (X1 exit-code obligation; X4 shared source-less semantics; X8 parity-matrix obligation) + the "which gate when" table + landscape row |
| A2 | Decide + record `indeterminate → exit 1` (architecture + PRD FR20 + epics 1.1a) |
| A5 | Epics 1.1a: `Ecosystem {pypi, conda}` |
| A7 | Three PRD prose edits (J1, FR16, the offline-DB state-machine cell) + the honest adoption statement |
| A8 | FR19 decision (delete or repurpose as the warn-only coverage guardrail) |
| A9 a/c/d/e/f/g/i | Small epics/PRD/architecture touch-ups |
| X1 | Amendment note on the shipped cyclonedx spec recording the inventory-match exit-code migration obligation |
| X11 | PRD gains persona **P8** + Journey 10 (workstation mode) + the classification correction; spec gains **§ Local / workstation mode** + the honest-adoption statement; epics 1.3a/5.1 gain the workstation ACs (cold-start UX + online-opt-in decision scope; install story); C2 `doctor` re-ranked v1-if-cheap |

### Tier 2 — Fold into Story 1.1a (the schema freeze)

- A6: finding-ID scheme + waiver-scope decision (hygiene + indeterminate families; recommended: waivable-with-expiry)
- A9-d: `status.driver` in the frozen schema
- X2: producer-agnostic security section (generic vuln provenance; optional KEV/EPSS slots; tier + raw severity evidence)
- B3: open `axis` mechanism

### Tier 3 — Fold into Story 1.3a (the OSV-DB spike)

- A4: severity-normalization strategy + name-level-tier query mechanism (decision records)
- X6: evaluate `update-cve-db` reuse; env-var mirror override for provisioning
- B1: verify `--lockfile=<parser>:<path>` against the pinned range
- B2: concrete engine version ranges; cold-start UX; DB packaging decision
- X11: the **online opt-in vuln-query decision** — explicit `--online` mode vs offline-only-everywhere (the workstation path's key fork)

### Tier 4 — Fold into E2/E4/E5 stories

- A3: `extract/lockfiles.py` + locked-closure ACs + the pixi.lock basename fixture (2.1/2.3)
- X3: run_constraints excluded / flagged-as-constraint (2.2a/2.2b + oracle)
- X4/A9-h: source-less hygiene `not-applicable` semantics (2.2a/2.3)
- X5: map generator preserves `match_source`/`match_confidence`; provenance-tier threshold rule; purl-associator corroboration (2.1)
- X7: `cfe:*` property namespace + G98 purl normalization + scan-project round-trip (4.1)
- X8: scan_project as second differential oracle (2.2a)
- B4: pixi feature/target-table routing ACs (2.2a)
- B5/B6/B7/A9-j: dogfood gate, reference hardware, OS matrix, adversarial corpus additions (5.2)

### Tier 5 — Wave-E / retro obligations

- X8: the E1 ↔ scan_project parse-parity matrix (the promotion prerequisite)
- Re-run the dated competitive spike before any external release (already specced; reaffirmed)

### Tier 6 — Backlog (spec § Future)

- C1–C10 (VEX, doctor, baseline ratchet, upgrade-plan, CI packaging, SARIF, license axis, waiver ops, pixi-map export, criticality weights)
- B8: `resolution:` vocabulary alignment
- X10: `--allow-stale-db` flag symmetry

---

## 8. Closing assessment

The design's spine — never-false-green, one shared inventory model, verdict.py sole ownership, non-rendering extraction, honest split coverage — survived a full-corpus adversarial re-read *and* an ecosystem-wide consistency check. The corrections above are almost all **freeze-order problems** (deciding things before the contract hardens) rather than design flaws, and the two most consequential (X1 exit-code inversion, X2 producer-agnostic schema) exist precisely because the tool's contracts are already load-bearing for two other specced systems.

That is the strongest possible validation of the mission framing in § 2: **python-deptry-osv-scanner is the fleet-edge node of an architecture that already exists in two of its three layers.** Freeze the contracts with the ecosystem in view, and the promotion path (edge tool → atlas surface → Kedro terminal gate) stays what the Kedro spec says it is — wiring, not redesign.
