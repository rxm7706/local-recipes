---
status: in-progress
spec_updated: 2026-07-05
---

# Tech Spec: CycloneDX Universe Inventory — full PyPI + full conda-forge, purl mapping, gap/version-lag matching, and 2027–2030 library recommendations

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/cyclonedx-universe-inventory.md
> ```
>
> **Rule-1 reminder:** every atlas-touching / recipe-touching sub-task here MUST go
> through the `conda-forge-expert` skill (CLAUDE.md BMAD↔CFE Rule 1). The skill's
> Operating Principles (esp. "pair quantitative claims with a verifiable source"),
> Critical Constraints, and the atlas-phase-engineering rule book
> (`reference/atlas-phase-engineering.md`) are authoritative over any story text below.
> **Rule-2 reminder:** the effort closes with a CFE-skill retrospective (Wave E, S-retro).

---

## Status

- **ready** — authored 2026-07-05, grounded against the live `cf_atlas.db` and the
  2026-07-04 ad-hoc purl exports; hardened same day by a 3-lens adversarial review
  (17 findings applied). **Scope amendment (same day, per user):** the universe is
  **full PyPI + full conda-forge** (not the mapped/actionable slice), and — because the
  users are conda-forge **consumers** — **non-Python conda-forge packages (Go, Rust,
  npm-origin, R, C libs) are first-class** in the matcher and the 2027+ recommendation
  layer: they don't map to PyPI, but freshness/quality/recommendation apply via their
  own upstream-of-record. **Second amendment (same day, per user):** the recommendation
  window is **2027–2030**, with two first-class horizon signals — **Python 3.14
  readiness** (tiered, from wheel tags / classifiers / requires_python + conda py314
  build evidence) and an **LTS-policy flag** (curated registry + labeled heuristic;
  e.g. Python, Django). **Third amendment (same day): Wave A is
  implementation-READY** — plan-mode exploration (3 agents) + a design pass pinned
  the S1/S2 file surfaces, artifact contracts, decisions D1–D4, and live verification
  gates directly into § Wave A; a second-pass Ultraplan refinement on Claude Code web
  may further revise this spec before implementation. **Fourth amendment (same day,
  per user): schema changes are permitted when the atlas owns them** — D3 upgraded
  from a code-side guard to a **v28→v29 migration** (`v_pypi_intelligence_valid`
  view); `trendshift-conda-forge.md` Phase T renumbered v29→v30 in the same pass
  (schema numbers allocate in implementation order). **Fifth amendment (same day,
  per user): endoflife.date API v1 is the authoritative LTS/EOL source**
  (live-verified: 460 products; django 4.2 LTS → EOL 2026-04-07) — registry demoted
  to slug-map + overrides, `eol-before-window` check added; the Phase P downloads
  refresh became an operator-gated S8 option (data verified fresh 2026-07-04); and
  **cross-spec sync is an explicit implementation + retro obligation** — the
  2026-07-05 all-specs impact analysis (2 impacted / 9 none / 1 historical) is
  encoded in § Cross-spec impact & sync. **Sixth amendment (same day, per user):
  aligned with the Python Dependency Policy write-up**
  (`gist.github.com/rxm7706/6dfaa127f4b86c8d4717522ff0107e6c`) — S5 gains the
  freshness policy check (top-20th-percentile / last-eligible−1, configurable
  defaults), built-in transitive resolution for bare manifests (+ depth/fan-out →
  S7), a CI policy-gate mode with exit codes, and policy-tiered input formats
  (+`meta.yaml`/`recipe.yaml` as manifests, +`pdm.lock`); exception lists +
  `--verify-against` BOM drift explicitly deferred. **Seventh amendment
  (2026-07-05, the anticipated second-pass refinement on Claude Code web):
  spec re-verified against the live repo — zero claim drift found.** Confirmed
  live: both `_sbom.py` defects (`_purl` at `scripts/_sbom.py:48-50` emits no
  channel qualifier; license emission at `:86` is always `{"license": {"id": …}}`);
  `SCHEMA_VERSION = 28` (`conda_forge_atlas.py:138` — v29 still free); the
  trendshift v30 + kedro-migration cross-spec sync lines are in place;
  endoflife.date API v1 re-verified live (django 4.2 `isMaintained: false`,
  EOL 2026-04-07; 5.2 EOL 2028-04-30); 84 recipes currently carry
  `pending-`/`blocked-` cfe status (consistent with the 84-line ad-hoc
  exceptions baseline → 82 expected post-D1); all `recipes/*/recipe.yaml`
  parse clean (G92/G98 gate green). Two refinements: (a) **S4's
  `?channel=` qualifier risk is nil by construction** —
  `scan_project.parse_sbom_cyclonedx` classifies by purl *prefix* only and
  reads name/version from the component's own fields, so the qualifier cannot
  break ingestion; keep the pinned test as a regression formality. (b) **Path
  clarification**: every `tests/…` path in this spec is relative to
  `.claude/skills/conda-forge-expert/` (e.g.
  `.claude/skills/conda-forge-expert/tests/unit/test_export_purls.py`), not a
  repo-root `tests/` tree. See also § Execution-environment split (web pass)
  below. Zero implementation. Resume at **Wave A / S1**.

### Execution-environment split (web pass)

Wave A work splits cleanly between Claude Code web and a local machine — the
web container clones the repo fresh, so the gitignored
`.claude/data/conda-forge-expert/` (cf_atlas.db, `purl-export/` baseline,
grayskull cache) does **not** exist there, and `pixi` is not installed:

- **Web-executable**: all code (S1/S2 six-file surfaces), all fixture-DB unit
  tests (the `open_db()` + `init_schema()` + raw-INSERT pattern needs no live
  DB), the v28→v29 migration + its idempotency test, the three-place
  meta-tests, and spec/docs edits. Tests run via a scratch venv
  (`pip install pytest pyyaml`) invoking pytest directly.
- **Local-only**: the entire § Verification Wave A live-gate block (baseline
  copy, `export-purls` count assertions, sort checks, exceptions diff,
  `mapping-gap` dry-run → human spot-check → `--write` → idempotency re-run,
  D3 view count, re-export growth check, `pixi run -e local-recipes test`),
  and every dated Dev-Notes count. A web pass must NOT fabricate these
  numbers — they come from the local run (CFE live-verification principle).
  **Wave B local-only additions (recorded 2026-07-05, with the web slice):**
  the S4 validator run against the REAL full BOM; the measured full-universe
  size/emit-time numbers that decide single-file-vs-split (S3 Dev Notes);
  and the CLI-level `scan-project --sbom-in` invocation of the ~50-component
  round-trip (the web tests cover the same parser in-process with a
  60-component slice — the CLI surface needs the full pixi env).

### Adjacent prefix.dev / nebari tooling (survey 2026-07-05, per user — the eighth amendment)

Live survey of nebi, recent pixi releases, prefix-dev org repos, and wolfv's
repos, asking "can any of their tooling be used here?" Verdicts:

| Tool | Verdict for this effort |
|---|---|
| **`prefix-dev/purl-associator`** (pushed 2026-06-24) | **ADOPT as an optional S2 corroboration source + a standing cross-check.** Canonical conda-forge→PURL mappings (primary + alternative purls, optional CPE 2.3 prefixes) maintained via auto-inference + edit-via-PR; published artifacts: `web/public/mappings.json` (full bundle), `mappings-index.json` (compact), sharded per-package JSONs; repo-side `mappings/{auto,manual}.json`. S2 (D2-ext): a TTL-cached fetch of the bundle may serve as a SECOND independent corroborator alongside the reverse grayskull cache — agreement from either ⇒ `verified`; cache absent → warn + continue (same discipline as the grayskull cache; keeps S2's offline-only rule). S3/S1 follow-up: cross-check our conda purls + `cfe:upstream_purl` values against its alternative-purls; its externally-maintained CPE prefixes also vindicate the 2026-06-19 decision NOT to cache `cfe-cpe` in recipes (consume, don't cache). |
| **pixi 0.71.0+ configurable conda↔PyPI mappings** (2026-06-24) | **Follow-up, not scope**: pixi now accepts custom per-channel `conda-pypi-map` files (default source: the parselmouth-hosted mapping — the same provenance tier the atlas already ingests). Emitting our `purls_conda-pypi_mapped.tsv` additionally in pixi's mapping format (an `--pixi-map` flag on `export-purls`) would let any pixi user point at the atlas-derived mapping. Deferred — record as a Wave E candidate, do not widen S1's pinned artifact contract. |
| **py-rattler / rattler** | **USE for decision 3's conda-side comparison** (upgraded from "evaluate": `py-rattler >=0.22.0` is already pinned in `pixi.toml` `[feature.local-recipes.dependencies]` (verified 2026-07-05) — as are `py-rattler-build`, `pixi-inspect`, `pixi-diff`). `rattler.Version` implements conda version ordering natively; fall back to conda's `VersionOrder` only if the import fails at runtime. No change to Wave A. |
| **nebi** (`nebari-dev/nebi`, Go/TS, alpha) | **No new intake needed — and `nebi-cli >=0.13` is already pinned in `pixi.toml` `[feature.local-recipes.dependencies]`** (verified 2026-07-05). nebi is a pixi-lockfile-based team environment manager (push/pull/diff envs via OCI registries); a nebi workspace IS a pixi workspace, so S5's `pixi.toml`/`pixi.lock` intake covers nebi-managed inventories (`nebi pull` → lockfile → `inventory-match`). S9 runbook line cites the env-resident CLI. |
| **Env-resident pixi extensions** — `pixi-to-conda-lock >=0.4.3`, `pixi-inspect >=2.0.2`, `pixi-diff >=0.1.6`, `pixi-pack`/`pixi-unpack`, `conda-lock >=4.0.1`, `conda-pypi >=0.10.1` (all pinned in `[feature.local-recipes.dependencies]`) | **S5a implementation option**: `pixi-to-conda-lock` converts `pixi.lock` → `conda-lock.yml`, so the S5a pixi.lock intake (the DW17 discharge) may EITHER parse pixi.lock natively OR shell out to the converter and reuse `scan_project`'s existing conda-lock parser — decide in S5a by which is simpler + testable offline (fixture-driven either way). `pixi-inspect` (conda-artifact metadata) and `pixi-diff` (lock-diffs) are candidate corroborators for S5's three-way version comparison at Wave C; not Wave A scope. |
| pixi releases 0.68–0.72, rattler-build, resolvo, rip, pixi-build-backends | **Nothing to adopt**: no SBOM/CycloneDX/purl-export surface found in recent pixi releases or the full prefix-dev + wolfv repo sweeps — S3's `_sbom.py` extension remains the right implementation path (no existing wheel to reuse). |
| prefix.dev attestation cluster — `siglog` (Merkle transparency log, Jul 2026), `sigstore-example` (signing conda pkgs), `vouched`; wolfv's `sigstore-rust`/`tough` (TUF)/`ceps` fork | **Watch only**: this is the ecosystem's SBOM-*signing*/provenance direction (CEP #127 territory — SBOM's home is `conda-meta/`, attestation in external Sigstore bundles). Orthogonal to this effort's inventory/matcher scope; revisit at the S-retro if a signed-BOM ask appears. |

## Intent (the user's ask, decomposed)

The users are **consumers of conda-forge**: Python libraries may come from PyPI-mapped
conda packages, and non-Python tools (Go/Rust CLIs, npm-origin tools, C libs) are
consumed from conda-forge directly. Build a **CycloneDX inventory of the FULL PyPI and
FULL conda-forge universes**, with an explicit **purl-level mapping** where one exists
(which `pkg:pypi/<name>` corresponds to which `pkg:conda/<name>?channel=conda-forge`;
non-Python conda packages instead carry their upstream-of-record identity), then use it to:

1. **Match a user inventory** (a CycloneDX SBOM or any `scan-project` input) against the
   combined universe to classify each library as:
   - **ADD** — on PyPI, not on conda-forge → candidate for packaging (feeds the CFE
     10-step recipe loop, ranked by the existing Phase S `conda_forge_readiness` score);
     non-Python dependencies absent from conda-forge surface as **ADD-NONPYPI**
     (reported with upstream identity, unscored — packaging them is trendshift-style
     manual triage, out of scope here);
   - **UPDATE** — a version-lag exists → reported as a **three-way comparison**
     (inventory-pinned version vs conda-forge latest vs upstream-of-record latest —
     PyPI for Python packages, GitHub/npm/crates/… for the rest), so "the feedstock is
     behind upstream" and "my pin is behind conda-forge" are distinct, actionable rows;
   - **CURRENT** — present and version-aligned on all three axes.
2. **Run data-quality analysis** over source-code / pypi.org / conda-forge metadata
   (already harvested into the atlas) to produce a per-library **"continue using in
   2027–2030?" recommendation** (keep / watch / plan-migration / replace) — **for every
   conda-forge package in the user's inventory regardless of ecosystem** — with
   `find-alternative` suggestions for the bottom tier. Two horizon signals are
   first-class (per user): **Python 3.14 readiness** and whether the library is
   **LTS-supported** (publishes a long-term-support policy, like Python or Django).

## Grounding: what ALREADY exists (do not rebuild)

All facts verified **2026-07-05** against the live DB / repo (per the CFE
quantitative-claims discipline — re-verify at implementation time, the atlas moves):

| Asset | Where | State |
|---|---|---|
| purl exports (ad-hoc, 2026-07-04) | `.claude/data/conda-forge-expert/purl-export/` | `purls_conda-forge.txt` 33,392 · `purls_conda-forge_versioned.txt` · `purls_pypi.txt` 843,641 (live universe 843,764 on 2026-07-05 — +123 Phase-D drift since the export) · `purls_conda-pypi_mapped.tsv` 21,403 pairs (`conda_purl · pypi_purl · match_source · match_confidence`) · `recipe-purl-exceptions.txt` 82. **No committed generator script.** The exceptions file derives from `recipes/*/recipe.yaml` cfe metadata (NOT the DB) — see S1. |
| conda↔pypi mapping (source of truth) | `cf_atlas.db packages.pypi_name` **+ per-row provenance columns `match_source` / `match_confidence`** | 21,490 rows with `pypi_name` set (of 33,624 total / 32,655 in `v_actionable_packages`). Provenance tiers (the LITERAL `packages.match_source` enum): parselmouth / recipe_source_url / name_coincidence / **`none`** (= the 3,527 "unattributed" rows; use `'none'` in SQL — it is the real stored value); plus the grayskull cache (`pypi_conda_map.json`, `update_mapping_cache`). |
| **Non-Python upstream-of-record** | `upstream_versions` (+ `upstream_versions_history`) | **47,143 rows across sources: github 25,154 · pypi 21,217 · gitlab 381 · npm 198 · rubygems 165 · codeberg 16 · crates 10 · maven 2.** This is the freshness backbone for non-Python packages. Registry-name columns on `packages` are sparse (`npm_name` 198; `cran_name`/`cpan_name`/`luarocks_name` 0) — GitHub tracking is the dominant non-Python upstream identity. `behind-upstream` CLI already consumes this. |
| **Conda-side downloads (ecosystem-agnostic)** | `package_version_downloads` (417,850 rows, **32,636 distinct packages**) + `package_platform_downloads` + `package_channel_downloads` | Phase F; covers non-Python packages equally — adoption signal for the 2027+ scoring. |
| PyPI universe | `pypi_universe` (843,764 rows: name + last_serial + fetched_at) + `pypi_universe_serial_snapshots` | Phase D populates; serial history for activity bands. |
| PyPI per-package intelligence | `pypi_intelligence` (48 cols, 937,154 rows) | **Coverage is uneven — load-bearing for Waves C/D:** `json_fetched_at`/`conda_forge_readiness` on **43,717** rows; `license_spdx` on **22,450**; `downloads_90d` on **851,359** (Phase P/BQ ran at scale on this DB). **93,390 rows have no `pypi_universe` counterpart** (deleted/renamed projects — never version-truth; see S2). |
| Version-lag signals (Python) | `packages.pypi_current_version` / `pypi_last_serial` (Phase H, serial-gated) | conda-vs-PyPI lag already computable per package. |
| Vulnerability overlays | `package_version_vulns`, `cisa_kev`, `epss_scores`, `cwe_categories` + `vuln_*` rollups on `packages` | Phase G/G′; **32,687 packages carry rollups, of which 11,588 have NO `pypi_name`** — non-Python vuln posture is covered. Read-side offline. |
| Lifecycle / health classifiers | `adoption-stage`, `release-cadence`, `feedstock-health`, `package_health`, `find-alternative`, `whodepends` CLIs | shipped, offline; cadence/stage run off `upstream_versions_history` (multi-source, not Python-only). `gh_default_branch_status` on `packages` adds repo-liveness. |
| **Python 3.14 readiness raw signals** | `pypi_intelligence.python_tags` (43,306 rows; **1,099 already carry cp314/py314**), `classifiers` (`:: 3.14` on 6,488), `requires_python` (40,690) + conda-side `package_python_downloads.pkg_python` (35,961 rows — direct evidence a feedstock ships AND users run py3.14 builds; `pyver-breakdown` CLI reads it) | all present; S7 composes them into a tiered readiness signal. |
| **LTS detection — negative finding** | `upstream_versions_history` (499,654 rows: `snapshot_at · conda_name · source · version`) | **latest-version snapshots only — parallel maintenance branches (the LTS signature, e.g. Django 4.2.x patches landing after 6.0) are NOT detectable from the atlas.** Hence the S7 LTS design: endoflife.date (authoritative) → registry slug-map/overrides → bounded releases-fetch heuristic. |
| **LTS/EOL authoritative source (external)** | **endoflife.date API v1** (`https://endoflife.date/docs/api/v1/`) | **Live-verified 2026-07-05**: 460 products (python, django, numpy, wagtail, …); per release line: `isLts`/`ltsFrom`, `isEol`/`eolFrom`, `isMaintained`, `releaseDate`; product `aliases` + `identifiers` aid name→slug mapping. Decision-grade for the window: python 3.12→EOL 2028-10-31, 3.14→2030-10-31; django LTS 5.2→2028-04-30, **4.2→2026-04-07 (EOL before 2027)**. Free, no auth. |
| CycloneDX emitter | `.claude/skills/conda-forge-expert/scripts/_sbom.py` | `emit_cyclonedx()` — CycloneDX **1.6** JSON. **Two known defects to fix in S3 before universe-scale use:** (a) licenses always emitted as `{"license": {"id": ...}}`, schema-invalid for SPDX *expressions* (live data: `0BSD AND LGPL-2.1-or-later`) and for non-SPDX junk (`(FTL or GPLv2+) and BSD and ...`); (b) `_purl()` emits no `?channel=conda-forge` qualifier, contradicting the G98 purl convention. |
| CycloneDX ingester | `scan_project.py` (`--sbom-in`, 8+ formats) | user-inventory input side is already solved. **Verify it parses purls carrying the `?channel=` qualifier (S4).** |
| "PyPI-not-on-cf" channel-wide | `pypi-only-candidates` CLI + `v_pypi_candidates` view | the universe-level ADD list exists; this spec adds the *per-user-inventory* variant. |

**Consequence:** this effort is composition + productization, not new harvesting. No new
atlas phase is required (no new HTTP fanout); Waves B–D **read** existing tables. Three
bounded exceptions: S2 **writes** mapping recoveries back to `packages` (write-path
discipline applies — idempotent SQL + incremental commits per
`atlas-phase-engineering.md`; any recipes/ writeback follows G98 parse-gates), S2 ships
the **v28→v29 schema migration** (the D3 `v_pypi_intelligence_valid` view — schema
changes are permitted when the atlas owns them, per user 2026-07-05; cross-spec
renumbering applied to trendshift), and S5/S6 may perform a **bounded live fetch**
(PyPI JSON / channeldata) limited to the user-inventory slice.

## Not Doing

- No full npm / CRAN / CPAN / crates universe inventories (the two universes are PyPI +
  conda-forge, per the ask). **But non-Python conda-forge packages are first-class**
  in the BOM, the matcher, and the 2027+ scoring — they carry their upstream-of-record
  identity (`cfe:upstream_purl` from `upstream_versions` / registry-name columns) instead
  of a PyPI mapping, and their freshness compares against that upstream.
- No mandatory BigQuery. `downloads_30d/90d` (PyPI side) are broadly populated on THIS
  DB (851k rows) but the signal is **non-portable** — a fresh atlas rebuild without BQ
  credentials loses it — so S7 weights must not make PyPI downloads load-bearing, and
  every use is freshness-stamped from `downloads_fetched_at`. (Conda-side Phase F
  downloads are credential-free and portable.)
- No recipe generation / PR submission inside this effort — the ADD bucket *feeds* the
  existing CFE loop (`generate_recipe_from_pypi` → … → `submit_pr`), it does not run it.
- No re-derivation of the mapping from scratch — `packages.pypi_name` +
  `match_source`/`match_confidence` are the source of truth; Wave A only closes *gaps*
  and productizes the export.
- **Exception-list handling and deploy-time `--verify-against` BOM drift verification
  are DEFERRED** (user decision 2026-07-05) — the Python Dependency Policy write-up
  names both (approved exception lists; build-BOM vs deployed-graph verification with
  ticketing), but only the policy gate mode ships now. The gate's JSON output and
  exit-code contract are designed so both can be added by amendment without breaking
  consumers.

## Design decisions (pre-resolved)

1. **Identity representation in CycloneDX** — a mapped conda↔pypi pair is **ONE
   component** (the conda one), carrying namespaced properties mirroring the recipe
   `cfe-purls` convention — never two sibling components (SBOM consumers would
   double-count):
   ```json
   { "purl": "pkg:conda/dvc@3.63.0?channel=conda-forge",
     "properties": [
       {"name": "cfe:pypi_purl", "value": "pkg:pypi/dvc"},
       {"name": "cfe:match_source", "value": "parselmouth"},
       {"name": "cfe:match_confidence", "value": "verified"} ] }
   ```
   **Non-Python conda components carry `cfe:upstream_purl` instead** where the atlas
   knows the upstream (`pkg:npm/<name>`, `pkg:cargo/<name>`, `pkg:gem/<name>`,
   `pkg:github/<org>/<repo>` from `upstream_versions.source` + repo URL), plus
   `cfe:upstream_source`. Standalone `pkg:pypi/` components appear only for **unmapped**
   PyPI names. PyPI purl names use **purl-spec normalization: lowercase + `_`→`-`, dots
   PRESERVED** (G98 — PEP 503 over-normalizes dotted names).
2. **BOM scope — FULL universes by default (per user).** The default deliverable is the
   complete inventory: **all 33,624 conda-forge packages** (archived/inactive included,
   flagged via `cfe:latest_status` / `cfe:feedstock_archived` properties — a consumer
   may be running one) **+ all 843,764 PyPI projects**. Physical layout (one combined
   file vs a conda BOM + a PyPI BOM pair sharing the mapping on the conda side) is
   decided in S3 from **measured** sizes/emit times — both full either way; convenience
   flags (`--actionable-only`, `--mapped-only`, `--conda-only`, `--pypi-only`) produce
   smaller slices for tooling that can't ingest the full set. No napkin size numbers —
   record real ones in Dev Notes.
3. **Version truth + comparison authority** — conda side: atlas `packages` (Phase B),
   compared with conda's `VersionOrder`. Upstream side: Python → `pypi_intelligence.
   latest_version` read via the D3 `v_pypi_intelligence_valid` view (orphan-guarded;
   only where `json_fetched_at` set) → `packages.pypi_current_version`
   (Phase H) → bounded live `pypi.org/pypi/<name>/json` via `_http.py` (Wave C only,
   inventory slice), compared with PEP 440; **non-Python → `upstream_versions`**
   (github/gitlab/npm/rubygems/crates/maven/codeberg). Comparisons that fail either
   parser (date tags, epochs, `v`-prefixed or scheme-shifted tags — live realities)
   degrade to string-inequality **flagged `version_comparison: unreliable`** — never a
   silent guess.
4. **"Missing from conda-forge" is only declared after** the G10 five-spelling check +
   the grayskull mapping cache + (for destructive/report-final decisions) a live
   `channeldata.json` cross-check (G74 — the atlas can lag freshly-created feedstocks).
5. **2027+ recommendation = a transparent, weighted composite** (not ML), **computed for
   every conda-forge package in the inventory regardless of ecosystem**: each signal
   contributes a named, documented sub-score; weights live in one dict; the report
   always shows the per-signal breakdown so a human can audit any verdict. Missing
   signals shrink the denominator (no silent zeros) AND are listed in the output as
   `signals_absent` (for non-Python packages the `pypi_intelligence`-only signals are
   legitimately absent; the conda-side backbone — upstream freshness, Phase F downloads,
   vuln rollups, feedstock health, license quality — carries the score). Operator
   overrides via the existing `pypi_intelligence.notes` column (Python) / a small
   `futures_overrides` sidecar file (non-Python). **The horizon is the 2027–2030
   window, and it is defined, not vibes:**
   (a) **Python 3.14 readiness (key factor, per user)** — tiered per Python package:
   `py314-ready` (cp314/py314 wheel tags, or `:: 3.14` classifier, or conda py3.14
   builds shipping per `package_python_downloads`), `py314-likely` (pure-Python +
   `requires_python` does not exclude 3.14 + released within the 3.14 cycle),
   `py314-not-ready` (caps `<3.14`, or compiled with no cp314 wheels/builds),
   `unknown`. By 2030, 3.14 is a mid-life floor — `py314-not-ready` caps the tier at
   `watch` and is flagged in every report row;
   (b) **LTS + EOL flags (key factor, per user)** — source hierarchy: (1)
   **endoflife.date API v1** — authoritative LTS lines + per-line EOL dates
   (live-verified 2026-07-05: 460 products), matched by product
   `identifiers`/`aliases` then the registry slug-map; (2) the curated registry —
   now a thin name→slug map + entries only for LTS-policy projects endoflife.date
   lacks; (3) `lts-like` heuristic last (patch releases observed on an older line
   after a newer line exists — labeled heuristic, never presented as policy).
   Flags: `lts-supported` (pin on an active LTS line), `lts-available` (LTS lines
   exist; the recommendation includes "move to the LTS line"), `lts-like`,
   `none/unknown`. **EOL-line check:** the pinned line's `eolFrom` vs the window —
   line EOL **< 2027** → `eol-before-window` (upgrade lines or replace; live
   example: django 4.2 LTS → EOL 2026-04-07); product fully EOL/unmaintained →
   floor `plan-migration`. LTS standing with in-window EOL dates is a positive
   keep-tier signal: dated, predictable support through the window;
   (c) all ecosystems: silence window — no release AND no upstream movement
   > 18 months caps the tier at `watch`;
   (d) archived feedstock or yanked/broken latest → floor at `plan-migration`.
   Thresholds are dated constants in the weights dict, revisited at each retro.
6. **Freshness contract** — every emitted BOM/report stamps the atlas `built_at` (from
   `cf_atlas_meta.json`) and per-signal `*_fetched_at` ages as metadata properties
   (`cfe:atlas_built_at`, …). Reports refuse to run (override: `--allow-stale`) when the
   atlas is older than 14 days — this repo's G74/G78 lessons are precisely "cached
   records decay."

## Waves & stories

### Wave A — Productize the purl + mapping export (close the ad-hoc gap)

Wave A is **implementation-ready** (plan-mode exploration + design pass, 2026-07-05):
file surfaces, artifact contracts, and the write-path SQL are pinned below. Model
files: `scripts/pypi_only_candidates.py` (canonical CLI shape),
`tests/unit/test_pypi_only_candidates.py` (fixture-DB pattern via
`conda_forge_atlas.open_db()` + `init_schema()` + raw INSERTs, in-process helper
calls), the 19-line wrapper template in `.claude/scripts/conda-forge-expert/`.

- **S1 — `export-purls` CLI** (read-only exporter; two declared inputs: `cf_atlas.db`
  + the `recipes/` tree).
  **File surface (6, per the three-place rule + tests + MCP):** canonical
  `.claude/skills/conda-forge-expert/scripts/export_purls.py` (stdlib + `yaml`,
  conn-taking pure helpers, `main() -> int`); wrapper
  `.claude/scripts/conda-forge-expert/export_purls.py`; `pixi.toml` task
  `export-purls`; `"export_purls.py"` in `tests/meta/test_all_scripts_runnable.py`
  SCRIPTS; MCP tool `export_purls` in `conda_forge_server.py` (`ATLAS_EXPORT_PURLS`
  const, always-`--json` wrap via `_run_script`); unit tests
  `tests/unit/test_export_purls.py`. Flags: `--out-dir` (default the data-dir
  `purl-export/`), `--json` (per-artifact `{lines, previous_lines}` +
  `recipes_scanned`/`recipes_parse_errors`/`unparseable_upstream`).

  **Artifact contract (the regression surface — live-verified 2026-07-05):**

  | # | File | Population | Line format | Order |
  |---|---|---|---|---|
  | 1 | `purls_conda-forge.txt` | `packages WHERE latest_status='active'` (33,392) — deliberately broader than `v_actionable_packages` (archived-but-active INCLUDED: a consumer may run one); selector carries a `# scope:` comment for the meta-test | `pkg:conda/{name}?channel=conda-forge` | **by `conda_name`, C-locale — NEVER full-line sort** (`-` 0x2D < `?` 0x3F flips name-prefix pairs) |
  | 2 | `purls_conda-forge_versioned.txt` | same rows, same order | `…@{latest_conda_version}?channel=conda-forge`; NULL version → unversioned line (count parity with #1 asserted) | same |
  | 3 | `purls_pypi.txt` | all `pypi_universe` | `pkg:pypi/{name}` — G98: lowercase + `_`→`-`, **dots preserved** | full-line C-sort |
  | 4 | `purls_conda-pypi_mapped.tsv` | #1 rows AND `pypi_name <> ''` (21,403) — **includes** the 3,527 `match_source='none'`/`match_confidence='n/a'` rows (straight provenance passthrough from `packages.match_source`/`match_confidence`, no filtering) | header `conda_purl\tpypi_purl\tmatch_source\tmatch_confidence` verbatim | by `conda_name` |
  | 5 | `recipe-purl-exceptions.txt` | `recipes/*/recipe.yaml` whose `extra.cfe-on-conda-forge-status` starts `pending-`/`blocked-` (`yaml.safe_load`; parse failure → warn + skip + count) | `{dir}: conda:{name} not-on-cf (status={s})` when the conda name is absent from #1; else, for pypi-registry recipes, `{dir}: pypi:{name} not-in-pypi-export` when absent from #3 | by recipe dir |
  | 6 | `purls_conda-upstream_mapped.tsv` (NEW) | active, PyPI-unmapped, having a non-pypi `upstream_versions` row (one row per conda_name × source) | header `conda_purl\tupstream_purl\tupstream_source`; purl by source: github→`pkg:github/{owner}/{repo}`, npm→`pkg:npm/{n}`, crates→`pkg:cargo/{n}`, rubygems→`pkg:gem/{n}`, maven→`pkg:maven/{g}/{a}`, gitlab/codeberg→`pkg:generic/{repo}?vcs_url=git+{url}`; unparseable URL → skip + count | by (conda_name, source) |

  **Decision D1 — the exceptions dots-bug is FIXED, not reproduced.** The 2026-07-04
  ad-hoc run PEP-503-folded the recipe-side pypi name but not the export side,
  manufacturing 2 false `not-in-pypi-export` lines (`fs.googledrivefs`,
  `pymilvus.model` — both ARE in #3 under their dotted names). Rule: fold **both**
  sides for membership lookup ONLY (`re.sub(r"[-_.]+","-",n.lower())` — how PyPI
  itself resolves names); always emit G98-style. Expected baseline divergence:
  84 → 82 lines. The exporter reports `previous_lines` vs `lines` per artifact on
  overwrite instead of hardcoding baselines. Pinned tests: sort-by-name regression
  (`foo` before `foo-bar`, and `lines != sorted(lines)`), G98 dots-preserved, the D1
  bug pin (dotted name present in universe → zero `pypi:` lines; genuinely absent →
  line emitted, keeping the branch alive), determinism (double-run byte-identical),
  TSV headers + `none`-row passthrough, missing-DB → rc 1.

- **S2 — `mapping-gap` CLI** (the effort's ONE DB write path; **dry-run by default**).
  **File surface (6):** canonical `scripts/mapping_gap.py`, wrapper, `pixi.toml` task
  `mapping-gap`, SCRIPTS entry, unit tests `tests/unit/test_mapping_gap.py`, and
  `conda_forge_atlas.py` (the D3 v28→v29 migration + schema-version test). **No MCP
  tool** (S9's +4 list is unchanged). Flags: `--write` (default = dry-run: full
  classification + report, zero UPDATEs), `--json`, `--limit N`, `--report PATH`.

  **Classification** (working set = `v_actionable_packages WHERE pypi_name IS NULL OR
  pypi_name = ''`, ~11k): Python-track iff a `python` run-dep exists in
  `dependencies` (`target_conda_name='python' AND requirement_type='run'`) OR
  `upstream_versions` has a `source='pypi'` row; else non-Python, subdivided by
  whether ANY upstream identity exists (none → the "freshness unknowable until Phase
  L/K covers them" bucket — reported, not fixed here).

  **Recovery — offline only (no live probing; decision-4 live checks gate "missing
  from conda-forge" declarations, which S2 never makes):** inverse-G10 candidates
  from the conda name — folding subsumes the `-`/`_` swap, so ≤4 distinct: bare,
  strip `-py`, strip `-python`, strip `python-` — validated against a fold-keyed
  index of `pypi_universe` plus a one-time REVERSE index of the grayskull cache
  (`pypi_conda_map.json` is `{pypi_lower: conda_name}`-keyed). The written value is
  the universe's **stored spelling** (folding is lookup-only, G98-safe). Grayskull
  cache absent → warn + continue in `likely`-only mode (refreshing it remains
  `update_mapping_cache`'s job).

  **Decision D2 — two confidence tiers under `match_source='g10_spelling'`:**
  `verified` only when the reverse grayskull cache independently agrees; `likely` on
  universe membership alone (mirrors `name_coincidence` semantics). **Ambiguous**
  (2+ distinct candidates hit, no grayskull tiebreak) → NO write; `ambiguous` triage
  bucket with the candidate list. **Collision** (candidate pypi name already set on
  a different conda package) → skip; `collisions` bucket — the
  `wasmtime`-vs-`wasmtime-py` trap; never a "bare name wins" heuristic.
  (**D2-ext, eighth amendment:** the `prefix-dev/purl-associator` mapping
  bundle may serve as a second independent corroborator — agreement from
  EITHER the reverse grayskull cache OR purl-associator ⇒ `verified`; both
  caches absent → `likely`-only mode. Optional; see § Adjacent prefix.dev
  tooling.)

  **Writeback (pinned SQL — idempotent, no-clobber, `commit_every=500` per the
  Phase C pattern):**
  ```sql
  UPDATE packages
     SET pypi_name = ?, match_source = 'g10_spelling', match_confidence = ?
   WHERE conda_name = ?
     AND (pypi_name IS NULL OR pypi_name = '')
     AND match_source NOT IN ('parselmouth', 'recipe_source_url')
  ```
  A second `--write` run reporting 0 rows written IS the idempotency proof.

  **Decision D3 (REVISED 2026-07-05 — schema changes are permitted when the atlas
  owns them, per user): orphan rule as a SCHEMA-LEVEL view.** S2 ships an idempotent
  **v28→v29 migration** in `conda_forge_atlas.py` (`SCHEMA_VERSION` bump +
  `init_schema` self-healing, modeled on the v21 `v_actionable_packages` precedent)
  adding:
  ```sql
  CREATE VIEW IF NOT EXISTS v_pypi_intelligence_valid AS
    SELECT pi.* FROM pypi_intelligence pi
    JOIN pypi_universe pu ON pu.pypi_name = pi.pypi_name;
  ```
  Wave C/D consumers read the VIEW, never the raw table for version truth — enforced
  the `test_actionable_scope.py` way (any `FROM pypi_intelligence` outside the view
  needs a `# scope:` justification comment; meta-test added in the same story). The
  `ORPHAN_RULE` docstring, the `orphan_intelligence_stats()` report section (93,390
  orphans at 2026-07-05), and the unit test (seeded orphan excluded by the view;
  migration idempotent on a v28 fixture DB) all stay. `conda_forge_atlas.py` (the
  migration) + the schema-version test update are part of S2's 6-file surface.
  **Cross-spec consequence (applied 2026-07-05):** v29 is CLAIMED by this effort;
  `docs/specs/trendshift-conda-forge.md` Phase T renumbered v29→**v30**. Schema
  numbers are allocated in implementation order — whichever effort lands first takes
  the next free version, and the other spec renumbers again if needed.

  **Report** — `mapping-gap-report.md` is **runtime output into the gitignored data
  dir** (`.claude/data/conda-forge-expert/`), NOT a repo doc. Sections: (1) header
  (generated_at, atlas `built_at`, DRY-RUN/WRITE mode, grayskull-cache presence +
  mtime); (2) summary (actionable · mapped before/after · recovered · remaining);
  (3) per-class counts incl. non-Python-no-identity and recovered by confidence ×
  transform; (4) ambiguous + collision listings (the human-triage queue); (5) orphan
  section (rule verbatim + count + sample); (6) recovered-pairs appendix.

  **Decision D4 — sequencing:** S1 → S2 dry-run → human review of the report
  (spot-check ≥5 recovered pairs against pypi.org/the feedstock) → S2 `--write` →
  idempotency re-run (0 rows) → **re-run S1**: the mapped TSV must grow by exactly
  `rows_written` (the wave's success metric).

### Wave B — CycloneDX universe inventory

- **S3 — `universe-sbom` CLI.** Extends `_sbom.py` (shared code, no fork) with two
  **prerequisite fixes** (both defects verified live, see Grounding):
  (i) license normalization — single SPDX id → `{"license":{"id":...}}`, SPDX expression
  → `{"license":{"expression":...}}` (validated against the SPDX expression grammar),
  anything else → `{"license":{"name":...}}` fallback; (ii) purl qualifiers — `_purl()`
  gains channel-qualifier support so conda purls emit `?channel=conda-forge` (G98).
  Then emits the **full-universe inventory** per design decisions 1–2: all conda
  components (version, normalized license, `cfe:pypi_purl`/`cfe:match_*` for mapped
  Python, `cfe:upstream_purl`/`cfe:upstream_source` for non-Python,
  `cfe:latest_status`/`cfe:feedstock_archived` flags) + all PyPI projects (standalone
  components for unmapped names; name + last_serial always, version/license where
  `pypi_intelligence` is enriched); `cfe:atlas_built_at` stamped in BOM metadata
  (decision 6). Flags: `--actionable-only`, `--mapped-only`, `--conda-only`,
  `--pypi-only`, `--with-vulns` (joins `v_current_version_vulns`; off by default at
  universe scale), `--format cyclonedx|spdx`, `--out`. Offline-safe. Record measured
  output size + wall time for the full inventory and each slice in Dev Notes (verified
  numbers, dated); the single-file-vs-split layout decision is made HERE from those
  numbers. MCP: expose as `universe_sbom`.
- **S4 — BOM validity gate.** Validate emitted BOMs against the CycloneDX 1.6 schema
  (`cyclonedx-python-lib` if already in the env, else JSON-schema check) as a unit test
  with a small fixture DB **whose fixtures include an SPDX-expression license, a
  non-SPDX junk license, and a non-Python package with a `cfe:upstream_purl`** (the live
  variance). Meta-test asserts purl forms follow G98 normalization. Round-trip gate is
  **slice-based**: a bounded (~50-component) BOM slice through `scan-project --sbom-in`,
  plus an explicit test that `scan_project`'s purl parser accepts the
  `?channel=conda-forge` qualifier. Success: schema-valid on live data, not just
  fixtures (run the validator once against the real full BOM and record the result).

### Wave C — Inventory gap / version-lag matcher

- **S5 — `inventory-match` CLI.** **Input contract (pinned per user 2026-07-05;
  policy-TIERED 2026-07-05 per the Python Dependency Policy write-up —
  `gist.github.com/rxm7706/6dfaa127f4b86c8d4717522ff0107e6c`):**
  - **policy-supported** (the write-up's CI formats): pyproject.toml (PEP 621;
    517/518/639/735), requirements.txt (+ frozen), environment.yaml, conda-lock.yml,
    pixi.toml, pixi.lock (S5a — **discharges the DW17 follow-up** filed in
    `cfe-shipped-releases.md`), and **`meta.yaml` (v0) + `recipe.yaml` (v1) as
    dependency manifests** (S5a, NEW per the policy: parse `requirements.host/run`
    from recipes, reusing the repo's existing recipe parsers);
  - **tool-supported beyond policy** (the tool runs ahead of the policy):
    CycloneDX/SPDX SBOM (`--sbom-in`), live conda env (`--conda-env`), venv
    (`--venv`), container image (`--image`/`--oci-archive`), plus S5a text intake:
    `pip list`/`pip freeze` output and `conda list` output (incl. `--export`);
  - **future-tier** (S5a builds the parsers; rows flagged `policy: future`):
    `pylock.toml` (PEP 751), `poetry.lock`, `uv.lock`, **`pdm.lock`**.
  **S5a extends `scan_project`'s intake parsers** (shared with the plain
  `scan-project` surface — not an inventory-match-only fork); all formats feed the
  same `Dep` dataclass; each gets a fixture-driven unit test and a row (with policy
  tier) in `reference/dependency-input-formats.md` (Wave E docs).
  **Transitive resolution (per policy § 3, decision 2026-07-05):** bare manifests
  (direct-pinned, no lock) are RESOLVED to the full graph before matching — PyPI
  manifests via pip's resolver (resolvelib / `pip install --dry-run --report`),
  conda/pixi manifests via a conda/pixi solve; lockfiles, SBOMs, and live envs are
  used as-given (already complete). Resolver-derived rows are flagged
  `resolution: resolved` (vs `locked`); per-package graph **depth + fan-out** are
  computed from the resolved graph (feeds S7).
  **Freshness policy check (defaults from the Dependency Policy, dated + configurable
  in the weights dict):** per dep, compute the ELIGIBLE version set
  (runtime-Python-compatible, non-yanked); dense history (≥ N eligible versions,
  default N=10) → the pinned version must sit in the **top 20th percentile** of
  eligible versions; sparse history → **last-eligible −1** or newer suffices.
  Output pass/warn/fail + the percentile on every row.
  **Policy gate mode (CI):** `--policy <file>` (thresholds: freshness,
  metadata-completeness, vuln severity, license) + deterministic **exit codes**
  (0 = pass, 2 = policy violations, 1 = error) so CI can block; when enabled,
  incomplete/ambiguous metadata blocks per the policy. (Exception lists and
  deploy-time `--verify-against` BOM drift are deliberately deferred — see Not
  Doing.) Plus an **optional criticality/weight sidecar** (`--weights <csv|json>`:
  per-package multiplicity or criticality the user's estate assigns — conda-forge
  blast radius is not the user's blast radius). For **every** dep (any ecosystem): resolve to conda name (mapping →
  G10 → live channeldata per decision 4), then bucket on the **three-way version
  comparison** (decision 3: inventory-pinned vs cf-latest vs upstream-of-record):
  **ADD** (Python, not on cf; attach `conda_forge_readiness`, `recommended_template`,
  `staged_recipes_pr_url` if a PR exists, and local `recipes/<name>/` presence),
  **ADD-NONPYPI** (non-Python, not on cf; upstream identity reported, unscored),
  **UPDATE-FEEDSTOCK** (cf behind upstream — report both versions + lag in
  releases/days where `upstream_versions_history` allows), **UPDATE-PIN** (inventory
  behind cf), **CURRENT**, **UNKNOWN** (no data — including non-Python conda packages
  with no `upstream_versions` row, flagged `signals_absent: upstream_freshness`).
  Every row carries `match_confidence` (never present `unattributed`/`name_coincidence`
  mappings as verified) and the `version_comparison` reliability flag. Output: markdown
  report + `--json` + `--sbom-out` (input BOM annotated with `cfe:gap_status` /
  `cfe:conda_purl` properties). MCP: `inventory_match`.
- **S6 — ADD-bucket handoff artifact (with on-demand enrichment).** Readiness/license
  coverage is sparse (43,717 / 22,450 rows — see Grounding), so for ADD-bucket names
  lacking `json_fetched_at`, run a **bounded Phase-R-style single-package enrichment**
  (one `pypi.org/pypi/<name>/json` fetch each, capped at the inventory slice, written
  back to `pypi_intelligence` idempotently) BEFORE scoring — a NULL `license_spdx` must
  never silently pass the OSI-eligibility blocker check. Then emit the ready-to-consume
  packaging worklist (name, readiness score, template, blockers e.g. non-OSI license)
  sorted readiness-desc, with `signals_absent` listed per row; ADD-NONPYPI entries
  appended unscored with their upstream identity. No recipes generated in this story.

### Wave D — Data-quality analysis + 2027+ recommendation

- **S7 — `library-futures` scoring.** New module computing, per matched conda-forge
  package **in any ecosystem**, a composite from **existing** signals (offline;
  Python-side enrichment gaps already closed by S6 for the inventory slice).
  **Ecosystem-agnostic backbone** (available for ~all cf packages): upstream freshness
  (`upstream_versions` + `behind-upstream` lag, `gh_default_branch_status`),
  release-cadence class, adoption-stage class, conda-side downloads (Phase F: version /
  platform / channel), vuln posture (Critical/High counts, KEV, max EPSS, CWE
  categories — verified present for 11,588 non-PyPI packages), feedstock health +
  archived flag, license quality (`conda_license` present? SPDX-parseable? OSI?),
  cf-graph blast radius (`whodepends --reverse`), the user-estate weight from the
  S5 sidecar, plus two S5-computed signals (per the Dependency Policy write-up):
  the **freshness percentile / policy verdict** and the resolved-graph
  **depth + fan-out** of each package within the user's own inventory. **Python-only enrichment layer** (adds precision where present):
  activity_band + serial deltas, PyPI downloads, bus_factor_proxy, packaging health
  (has_wheel/has_sdist/packaging_shape/yanked), metadata completeness
  (repo_url/docs_url/classifiers/requires_python currency), cross-channel `in_*`
  redundancy, `dependency_blast_radius`. **Horizon signals (decision 5, both key
  factors per user):**
  - **Python 3.14 readiness** — composed offline from `python_tags` + `classifiers` +
    `requires_python` (PyPI side) corroborated by `package_python_downloads.pkg_python`
    (conda side); tiering per decision 5(a). N/A → `signals_absent` for non-Python.
  - **LTS + EOL flags** — primary source: **endoflife.date API v1** (see Grounding;
    460 products), fetched via `_http.py` with an `ENDOFLIFE_BASE_URL` env override
    (the `<HOST>_BASE_URL` enterprise-routing convention) into a TTL'd
    `eol_cache.json` in the data dir (default TTL 7 d; offline → stale cache + age
    warning in the report, never a hard fail). Slug resolution: product
    `identifiers`/`aliases` first, then the git-tracked registry
    `.claude/skills/conda-forge-expert/data/lts-registry.yaml` — now a thin
    name→slug map + manual entries ONLY for LTS-policy projects endoflife.date
    doesn't cover (schema + seed entries unit-tested; every entry dated). Heuristic
    corroboration unchanged: a bounded per-package PyPI **releases** fetch (shares
    S6's live-fetch budget; the atlas cannot detect parallel maintenance branches —
    see Grounding) marks `lts-like`. Tiering + the EOL-line check per decision 5(b);
    endoflife.date beats registry beats heuristic. Report rows carry `lts_status`
    AND `eol_date` (of the pinned line).
  Output tier: **keep / watch / plan-migration / replace**, with per-signal
  breakdown + `signals_absent`; `py314_readiness` and `lts_status` appear as explicit
  columns in every report row (and as `cfe:py314_readiness` / `cfe:lts_status`
  properties in annotated BOMs); `replace` tier auto-attaches `find-alternative`
  suggestions. Weights + dated thresholds in one auditable dict.
- **S8 — `recommend-2027` report.** Runs S5 then S7 over a user inventory → a single
  scorecard report (markdown + JSON + optional annotated CycloneDX with
  `cfe:futures_tier` / `cfe:futures_score` properties, `cfe:atlas_built_at` stamped).
  Calibrate on a fixture set of known-good (e.g. numpy, pydantic, **and one healthy
  non-Python package, e.g. a maintained Go/Rust CLI**) and known-bad (archived /
  KEV-listed / >18-months-silent, **including one non-Python case**) packages as unit
  tests — plus horizon-signal calibration cases: **django** (endoflife-driven: a
  5.2 pin → `lts-supported`, EOL 2028-04-30; a **4.2 pin → `eol-before-window`**,
  EOL 2026-04-07, and must NOT tier `keep`), one `py314-not-ready` package (must
  cap at `watch`), and one `py314-ready` compiled package. The tiers must rank all
  of these correctly before weights are accepted. The CLI name stays
  `recommend-2027`; the report header states the **2027–2030 window** explicitly.
  **Optional pre-run downloads refresh (operator-gated, per user 2026-07-05):**
  when `downloads_fetched_at` age exceeds ~90 d (the window the signal measures),
  the report offers a Phase P refresh (BigQuery; the user has cost-optimized it) —
  ALWAYS run the § 13 dry-run cost preflight first and present the measured
  estimate for approval; never run implicitly. Verified 2026-07-05: data is fresh
  (max fetched 2026-07-04; 818,868 `bigquery-public` + 32,491 `clickhouse-clickpy`
  rows) — no refresh needed at authoring time. MCP: `recommend_2027`.

### Wave E — Closeout

- **S9 — Docs + surfaces.** `reference/mcp-tools.md` (**+4 tools**: `export_purls`,
  `universe_sbom`, `inventory_match`, `recommend_2027`),
  `reference/atlas-phases-overview.md` Part A persona rows (consumer/architect:
  "which of my libraries — Python or not — should survive 2027–2030?"),
  `quickref/commands-cheatsheet.md`, SKILL.md Atlas CLI table (+4 rows). Regeneration
  cadence documented: `export-purls` + `universe-sbom` run after every atlas rebuild
  (noted in `guides/atlas-operations.md` next to the bootstrap-data runbook — wiring an
  automatic hook is optional follow-up, the freshness gate in decision 6 is the
  enforcement). **Cross-spec re-sync** per § Cross-spec impact & sync (extend the
  kedro-migration note with the `g10_spelling` writeback + `cfe:*`/`?channel=` purl
  conventions; BMAD planning artifacts re-grounded via the documented sync loop).
  CHANGELOG entry; **MINOR** skill version bump.
- **S-retro — CFE retrospective (Rule 2, mandatory).** `bmad-retrospective` over the
  effort; land corrections/refinements/additions in skill files; re-stamp the BMAD sync
  baseline (`bmad-drift-check -- --write-baseline`) since counts/tool-lists change.
  The retro also runs the **closing all-specs sync sweep** (§ Cross-spec impact &
  sync, retro tasks): re-verify the impacted specs against what actually shipped.

## Verification (per-wave gates)

- Every new CLI: unit tests on a fixture DB + the three-place meta-tests green
  (`pixi run -e local-recipes` test suite).
- **Wave A live gates** (run in order; record dated counts in Dev Notes):
  ```bash
  cp -r .claude/data/conda-forge-expert/purl-export <scratch>/purl-export.baseline-20260704
  pixi run -e local-recipes export-purls -- --json   # conda≈33,392±drift · versioned==conda · pypi≥843,764 · mapped≥21,403 · exceptions≈82
  LC_ALL=C sort -c .claude/data/conda-forge-expert/purl-export/purls_pypi.txt
  sed 's|^pkg:conda/||; s|[@?].*$||' .claude/data/conda-forge-expert/purl-export/purls_conda-forge.txt | LC_ALL=C sort -c
  diff <baseline>/recipe-purl-exceptions.txt <live>  # expected: ONLY the 2 dots-bug lines removed + status drift
  pixi run -e local-recipes mapping-gap -- --json    # dry-run: rows_written==0; review report; spot-check 5 pairs
  pixi run -e local-recipes mapping-gap -- --write --json
  # then assert: g10_spelling row count == rows_written; parselmouth/recipe_source_url rows byte-unchanged
  pixi run -e local-recipes mapping-gap -- --write --json   # idempotency: rows_written==0
  sqlite3 "file:.claude/data/conda-forge-expert/cf_atlas.db?mode=ro" \
    "SELECT COUNT(*) FROM v_pypi_intelligence_valid;"   # D3 view live post-migration (< pypi_intelligence count by ~93k)
  pixi run -e local-recipes export-purls -- --json   # mapped TSV lines == previous_lines + rows_written
  pixi run -e local-recipes test
  ```
- S3/S8 quantitative claims (BOM size, emit time, score distributions) recorded from
  actual runs with dates — never estimated (CFE live-verification principle). S4's
  schema validation runs once against the REAL full BOM, not only fixtures.
- S5 end-to-end smoke: run against this repo's own `pixi.toml` env and one real CycloneDX
  SBOM; hand-verify 3 members of each bucket (incl. one G10 rename, one
  atlas-stale/channeldata-fresh case, one `version_comparison: unreliable` case, **and
  one non-Python conda package with GitHub upstream** — e.g. a Go/Rust CLI from the env).
- After Wave E: `pixi run -e local-recipes bmad-drift-check` clean.

## Risks / open items

- **Full-universe BOM size is unmeasured** — ~844k PyPI components as CycloneDX JSON
  will be large; S3 measures before the single-file-vs-split layout is fixed. Slices
  exist for consumers that can't ingest the full set.
- **Non-Python upstream identity coverage is partial**: `upstream_versions` tracks
  47,143 packages (GitHub-dominant); registry-name columns are near-empty (npm 198,
  cran/cpan/luarocks 0). Non-Python packages with no upstream row get
  `signals_absent: upstream_freshness` and a UNKNOWN-leaning match — S2 reports the
  count; expanding Phase L/K coverage is deliberately out of scope here.
- **Signal portability**: PyPI `downloads_*` (851k rows) exists only because Phase P/BQ
  ran on this DB; a credential-less rebuild loses it. S7 treats PyPI downloads as
  optional (denominator-shrinking), never load-bearing. Conda-side Phase F downloads
  are the portable adoption signal.
- **93,390 orphan `pypi_intelligence` rows** (no universe counterpart) — S2 owns the
  reconciliation rule; until then they are excluded from version truth.
- Mapping tiers `none` (3,527 unattributed rows, `match_confidence='n/a'`) and
  `name_coincidence` (40, `likely`) are lower-confidence; S5 surfaces
  `match_confidence` per row rather than presenting all mappings as equally verified.
- S6's bounded live enrichment writes to `pypi_intelligence` — same write-path
  discipline as S2 (idempotent upsert, respects `_http.py` enterprise routing).

## Cross-spec impact & sync (implementation + retro tasks, per user 2026-07-05)

`docs/specs/` stays mutually consistent: changes this spec makes to shared atlas
facts propagate to affected siblings **as part of implementation** and are
re-verified **at the retro**. Full-tree impact analysis (all 13 specs, 2026-07-05):

| Spec | Verdict |
|---|---|
| `trendshift-conda-forge.md` | **IMPACTED — synced 2026-07-05**: Phase T renumbered v29→v30 (incl. the A1 acceptance line), v29 fixture-base conditional, `v_pypi_intelligence_valid` read note |
| `cfe-atlas-datapipeline-kedro-migration.md` | **IMPACTED — synced 2026-07-05**: re-enumerate-at-intake note (+5 CLIs / +4 MCP tools / +1 view / endoflife.date cache / trendshift v30) |
| `cfe-shipped-releases.md` | INFORMATIONAL — dated archive, no update (retro cross-ref: its DW17 `scan_project --pixi-lock` follow-up is **discharged by S5a**'s lockfile-intake work — note it at the retro) |
| the other 9 (conda-forge-tracker, claude-team-memory, copilot-bridge, db-gpt, flyte, langflow, feedstock-refresh / -platform-expansion / -failure-remediation) | NONE — recipe-authoring / process docs; no atlas read-surface touched (their `python_min` / `schema_version: 1` / parselmouth mentions are recipe-level, verified line-by-line) |

**Implementation-time tasks (owned by the wave that ships the change):**
- **Wave A/S2** — extend the kedro-migration cross-spec note with the
  `packages.pypi_name`/`match_source='g10_spelling'` writeback + the `cfe:*`
  property namespace + `?channel=conda-forge` purl qualifier (its FR-13 CycloneDX
  normalizer must preserve both); re-confirm trendshift's base-version conditional.
- **Every wave** — after shipping: repo-wide grep for the changed fact (e.g. `v29`,
  tool counts) + `pixi run -e local-recipes bmad-drift-check --specs`. BMAD planning
  artifacts (`index.md`, `implementation-readiness-report.md`,
  `architecture-cf-atlas.md`, `architecture-mcp-server.md` — all pin schema v28 /
  42 MCP tools / 22 phases) are re-grounded via the documented sync loop
  (`bmad-groundtruth` → reconciler skills → `-- --write-baseline`), never hand-edited.

**Retro-time tasks (S-retro):** the closing all-specs sync sweep — re-verify both
impacted specs against what actually shipped, add the optional cfe-shipped-releases
DW17 cross-ref, re-stamp the BMAD baseline.
- **endoflife.date is an external dependency** (availability; v1 schema stability;
  460-product coverage ≪ the universe). Mitigations: TTL'd cache with
  stale-plus-age-warning (never a hard fail); uncovered products fall through to
  the registry slug-map/overrides then the labeled `lts-like` heuristic; registry
  entries stay dated and the S-retro revisits them (expired → `unknown`, never a
  silent support assertion). A project back-porting patches is not the same as a
  published LTS policy.
