# Reviewer Gate — Version / Reality-Check Review

- **Artifact:** `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md`
- **Reviewer axis:** versions & reality-grounding (were committed decisions reality-checked, not asserted?)
- **Date:** 2026-07-16
- **Verdict:** **APPROVE WITH REQUIRED CORRECTIONS** — the design decisions are genuinely reality-grounded (engine contracts, exit codes, data feeds, and axis FRs all verify against the repo and upstream), but two frontmatter/status assertions are contradicted by the repo's own shipped, verified code and must be corrected before the doc is treated as ground truth.

## Severity counts

| Severity | Count |
|---|---|
| High | 2 |
| Medium | 2 |
| Low | 2 |

---

## High

### H1 — `pinnedEngineContracts.deptry.rules` glosses DEP005 as "unused-dev"; reality is "standard-library dependency" — and the shipped code already recorded the doc as wrong

Frontmatter (line 20): `DEP005 unused-dev`. Upstream (deptry.com/rules-violations, fetched 2026-07-16): **DEP005 = "Project should not contain dependencies that are in the standard library."** The shipped parser explicitly documents the correction:

> `src/shared/packages/pyforge-warden/src/pyforge/warden/hygiene.py` (Story 1.3): "**DEP005 = stdlib dependency** (verified against deptry 0.25.1, 2026-07-13 …). The architecture's pinned 'unused-dev' label was wrong; DEP005 → warn is still the correct ceiling."

The frontmatter was edited on 2026-07-15/16 (axisDataContracts added) but this known-wrong gloss was never fixed. The ceiling (warn) is unaffected, but a "pinned contract" block that the codebase has formally falsified is exactly the assertion-vs-reality failure this gate exists to catch. **Fix:** change the gloss to `DEP005 stdlib-dependency` and note the 2026-07-13 code-side verification.

### H2 — § GAP A status note claims Story 1.3 shipped "DEP001 blocks"; the shipped default is DEP001 → warn

Architecture line 145: *"(Status 2026-07-15: story 1.3 landed the default hygiene→status table as `hygiene.py:hygiene_rung` — **DEP001 blocks**, DEP002–005 warn … DEP001-blocks re-confirmed by owner 2026-07-15.)"*

Shipped reality (`hygiene.py`, `DEFAULT_HYGIENE_POLICY`): **DEP001–005 are ALL `Status.WARN`**, with an explicit ownership record: DEP001 is *deliberately* warn in 1.3 because Gap-A gates DEP001-blocking on the conda↔PyPI mapping-confidence signal, which needs Story 2.1's map (not yet built); Story 2.1 upgrades DEP001 to block-on-high-confidence. The doc's *decision* (block, gated on mapping confidence) is fine; the doc's *status claim about what landed* is false. **Fix:** reword the status note to "DEP001 defaults to warn until 2.1 lands the mapping-confidence gate; owner re-confirmed the eventual DEP001-blocks default 2026-07-15."

## Medium

### M1 — Module-structure lists vs the actual package tree: `interfaces.py` (the load-bearing Engine seam) exists but is unlisted; several listed modules are planned-only without marking

Actual tree at `src/shared/packages/pyforge-warden/src/pyforge/warden/`: `cli.py`(24 KB, real), `models.py`, `interfaces.py`(17 KB — the five Protocols + `EngineResult` + `DefaultPolicy`), `inventory.py`, `discovery.py`, `routing.py`, `extract/{__init__.py,pyproject.py}`, `mapping.py`, `engines.py`(deptry runner + registry; osv runner is Story 1.5), `hygiene.py`, `verdict.py`, `report.py`, `data/{report-schema.json,conda_pypi_map.json}`.

- **Exists but absent from BOTH the § Module structure list and the "Complete project tree": `interfaces.py`** — notable because § Multi-axis reconciliation pins the whole axis-registry decision on "the existing `Engine` seam" without ever naming the module that owns it, and the 6.1 coordinated-amendment set omits it.
- **Listed but not existing (planned, unmarked):** `config.py`, `vuln.py`, `sbom.py`, `waiver.py`, `errors.py`, `determinism.py`, `license.py`, `currency.py`, `feeds.py`, `baseline.py`, `actuator.py`, and `extract/{_jinja,recipe_v1,meta_v0,environment_yml,pixi,lockfiles,requirements}.py`. Target-state trees are legitimate architecture content, but the tree is captioned "Complete project tree (extends the existing scaffold)" with no shipped-vs-planned marking; §§ elsewhere date-stamp shipped stories, so an unmarked reader over-trusts the tree. Also `errors.py` is listed while `ErrorKind`/`ErrorRecord` actually live in the shipped `models.py`.
- **Frontmatter/tree self-inconsistency:** `axisDataContracts.lts-registry` pins `src/pyforge/warden/data/lts-registry.yaml`, but the doc's own project tree's `data/` omits it (and it does not exist on disk yet — story 6.3, fine as a plan; the tree should list it).

**Fix:** add `interfaces.py` to both lists (naming it as the Engine seam), mark planned-only entries, reconcile `errors.py`↔`models.py`, add `data/lts-registry.yaml` to the tree.

### M2 — `referenceImplementation` frontmatter gloss is stale: "stdlib-only lib …; cli.py stub"

Line 16 still describes the scaffold as a stdlib-only lib with a `cli.py` stub. Reality: `pyproject.toml` now declares 4 runtime deps (`PyYAML`, `packaging`, `cyclonedx-python-lib`, `jsonschema` — matching the doc's own revised Library policy), and `cli.py` is a 24 KB real implementation; 14 modules shipped (stories 1.1–1.4). The body even says "wire E1–E4 into the existing `cli.py` stub". **Fix:** refresh the gloss to the post-1.4 state.

## Low

### L1 — Stale "6→3 exit projection" comments contradict the locked "7→4" projection

Module-structure and project-tree comments for `verdict.py` (lines ~232, ~292) still say "J9 lattice + **6→3** exit projection" — a pre-`indeterminate` remnant. The triad decision (line 124) locks a **7→4** projection (`{0,1,2,130}`), and shipped `verdict.py` says "TOTAL over all 7 rungs" with exits `{0,1,2,130}`. Cosmetic but confusing in the two places dev-agents copy from.

### L2 — Engine version pins: current and consistent; one inconclusive web datum

`recipes/deptry/recipe.yaml` pins **0.25.1** (upstream latest, released 2026-03; 0.25.0 was yanked — pin is correct and current; note upstream repo appears to have moved to the `osprey-oss` org, still actively maintained). `recipes/osv-scanner/recipe.yaml` pins **2.4.0**; a web search surfaced v2.3.5 (2026-03) as "latest" but search summaries lag — the v2 line and its output contract are unchanged either way; not actionable. `pixi.toml` run-deps are still `"*"`, consistent with the doc's own 6.6 distribution gate ("move from `*` to tested ranges" — pending).

---

## Reality-checks that PASSED (verified, not asserted)

- **osv-scanner contract** — upstream docs (google.github.io/osv-scanner/output) confirm exactly the frontmatter: `--format json` → JSON to stdout / all else stderr; `results[].packages[].{package{name,version,ecosystem}, vulnerabilities[], groups[]}`; exit codes **0 / 1 (vulns-found) / 127 (general error) / 128 (no packages)**. The doc's 127-multiplexing/1.4-spike refinement is a legitimate tightening on top.
- **deptry `--json-output` shape** — shipped `hygiene.py` parses exactly the frontmatter's `array of {error:{code,message}, module, location}` with C0-grade malformed-record handling; rule codes DEP001–004 glosses match upstream (only DEP005 wrong — H1).
- **Spec axis FRs exist and match** — `docs/specs/pyforge-warden.md` defines **FR-K1** (KEV/EPSS enrichment + `--fail-on-kev`/`--min-epss`, feed-absence → indeterminate), **FR-L1** (license axis, flag-activated gate per D12), **FR-C1** (currency axis, data-age provenance); the `axisDataContracts` entries restate them faithfully.
- **CFE data layout** — `.claude/skills/conda-forge-expert/data/lts-registry.yaml` **exists** (alongside `cwe_categories_seed.json`, `spdx.schema.json`), so the bundle-from-CFE plan is grounded; `_http.py:653 resolve_endoflife_urls()` exists as claimed for the endoflife-date mirror pattern.
- **license-expression** — nexB/AboutCode is the current maintainer; latest 30.4.4 (2025-07-22), ships SPDX list 3.26; parse/normalize purpose matches the FR32 pin.
- **FIRST EPSS** — real and fetchable: `https://api.first.org/data/v1/epss` + a daily downloadable scores CSV (`epss_scores-YYYY-MM-DD.csv.gz`), suitable for the cached-feed posture described.
- **Verdict lattice / exit projection / enums** — shipped `models.py` + `verdict.py` match the doc: `Status` includes `INDETERMINATE`, indeterminate → exit 1, projection total over 7 rungs, exits `{0,1,2,130}`, sole-ownership guard real.

## Network caveat

All web checks succeeded through the proxy (deptry.com, google.github.io, pypi.org, first.org, web search). No item had to be answered blind.
