---
title: '30.2: docs/map.yaml is the registry, MAP.md is its render, and `docs-currency` reds a stale page'
type: 'feature'
created: '2026-09-20'
status: 'in-review'
baseline_revision: 'fa54e525cbf28e49e6975799390866e996ca0e59'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md']
warnings: ['oversized']
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `docs/MAP.md` is hand-maintained and no page declares what it derives from or explains, so nothing can say a page is stale — the 14 pages PR #1529 added shipped with dead paths and a non-existent CLI grammar and nothing noticed.

**Approach:** a machine registry `docs/map.yaml` (quadrant, owner, `kind ∈ {generated, authored, pointer}`, `sources`, stamp) from which `docs/MAP.md` is rendered; `sources:` / `verified:` frontmatter on every authored page; a Doctor source `docs-currency` with four warn-first checks (map alignment, stale generated page, stale authored page, stray file in a managed skill dir); the unmapped-page class promoted from warn to fail.

## Boundaries & Constraints

**Always:** CAP-62's posture (warn first, fail-open on unreadable input); `MAP.md` is a render — a byte diff between it and its render is a finding; schema for `map.yaml` ships in the doctor package.
**Never:** copy a docs page into a per-tool instruction file; make `docs-currency` write anything.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `map.yaml` page with `sources:` newer (git last-touch) than `verified:` | warn naming the page and the source |
| authored page with a backticked path / `pixi run … task` / CLI grammar that no longer resolves | warn naming the token |
| `MAP.md` hand-edited so it differs from the render | warn (fail after promotion) |
| quadrant page absent from `map.yaml` | fail (promoted from CAP-83's warn in this story) |
| a `README.md` or other non-layout file inside a managed skill dir | warn naming it |
| `map.yaml` missing or invalid | fail-open: one `could-not-evaluate` warn, never a false green |

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-84`.
Surface: `docs/map.yaml` (new), a `docs-map-render` task, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py` (new) + unit tests, `scripts/detectors.py`, `pixi.toml`, the authored pages' frontmatter, `docs_map_hygiene.py` (retired into or kept beside `docs-currency` — decided and recorded in the story).
Ledger key: `30-2-docs-map-yaml-is-the-registry-map-md-is-its-render-and-docs-currency-reds-a-stale-page`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-19 (night) from `epics.md` so `marshal factory dispatch` can resolve this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:** `pixi run -e pyforge-guild detectors-ci` green on the branch; hand-edit `docs/MAP.md` → `docs-currency` warns; revert → OK.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_map_hygiene.py` -- KEEP as its own `Source`/dispatch entry ("kept beside", per the Binding's own discretion clause -- recorded in Design Notes below). One-line change: the `unmapped` `Finding` now uses `DoctorStatus.FAIL` instead of `WARN`. Its comparison target (MAP.md's own markdown links vs the four quadrant dirs) does **not** need to change: once `docs/MAP.md` carries the generated `## Page registry` section this story adds (which links every `docs/map.yaml` page), MAP.md's links already equal map.yaml's page set transitively -- promoting `unmapped` to FAIL is therefore safe on `main` today (zero violations after this story lands).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py` -- update `test_unmapped_quadrant_page_emits_one_warn_naming_it` to assert `DoctorStatus.FAIL` (rename to `..._emits_one_fail_naming_it`); update the module docstring's "unmapped is WARN" line to FAIL; note Story 30.2/CAP-84 promotion.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py` (NEW) -- the three genuinely-new checks. Read-only (NFR-1); never writes `docs/MAP.md`. Reuses `..cli_bridge.run_git`/`CliBridgeError` (see `sources/pixi_currency.py` for the exact import + wrapper pattern) and `. import degrade_on_exception` (see `sources/docs_map_hygiene.py::gather` for the exact wrap pattern).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/docs-map-schema.json` (NEW) -- JSON Schema for `docs/map.yaml`, mirroring `data/report-schema.json`'s header style (`$schema` draft 2020-12, `$id: urn:local-recipes:pyforge-doctor:docs-map-schema`, `additionalProperties: false` on the page shape).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py` (NEW) -- unit coverage for all six I/O matrix rows, against temp fixture trees only (mirror `test_sources_docs_map_hygiene.py`'s fixture-helper style: `tmp_path`, never the live `docs/` tree).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- append `Source.DOCS_CURRENCY = "docs-currency"` after `LIVE_PROOF_SURFACE` (the enum is append-only; do not reorder or remove `DOCS_MAP_HYGIENE`), with a comment block matching the style of the `DOCS_MAP_HYGIENE` / `LIVE_PROOF_SURFACE` comments immediately above it.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- append one `SourceRegistration(source=Source.DOCS_CURRENCY, scope="repo", subject_station="fleet", owning_station="doctor")` to `REGISTRY`, after the `LIVE_PROOF_SURFACE` entry, with an explanatory comment in the same style.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` -- import `docs_currency` in the `from . import (...)` block (alphabetical, beside `docs_map_hygiene`/`docs_shelf`); add `Source.DOCS_CURRENCY.value: docs_currency.gather,` to `DISPATCH`, after the `LIVE_PROOF_SURFACE` entry, with a one-line comment like the sibling entries.
- `scripts/detectors.py` -- append `("docs-currency", "docs-currency-check"),` to the tuple ending at `("live-proof-surface", "live-proof-surface-check"),` (around line 265), with a one-line comment matching the sibling entries' style.
- `pixi.toml` -- two new `[feature.guild-tasks.tasks.*]` entries, placed directly after the existing `[feature.guild-tasks.tasks.docs-map-hygiene-check]` block (around line 1133):
  - `docs-currency-check`: `cmd = "python -m pyforge.doctor.sources docs-currency"` (mirror `docs-map-hygiene-check`'s `description` style: what it checks, warn-only/read-only/fail-open, contract citation `spec-30-2-...`).
  - `docs-map-render`: `cmd = "python scripts/docs_map_render.py"` (description: regenerates `docs/MAP.md`'s generated `## Page registry` section from `docs/map.yaml`; the only sanctioned way to edit that section).
- `docs/map.yaml` (NEW) -- the registry. Top-level `schema_version: 1` + `pages:` (54 entries, one per file currently under the four quadrant directories -- see "The 54 pages" below for the exact list + per-page `kind`/`owner`). Each entry: `path` (docs-relative, e.g. `how-to/pixi-tasks.md`), `quadrant` (`tutorials`|`how-to`|`reference`|`explanation`, derived from the path), `owner` (station slug or `fleet`), `kind` (`authored`|`generated`|`pointer` -- no `generated` pages exist yet, that is Story 30.3's job). `sources`/`stamp` are schema-legal but **omitted for every page in this story** (reserved for `kind: generated` pages Story 30.3 adds) -- an `authored` page's own staleness signal comes from **that page's own frontmatter** `sources:`/`verified:` (the convention Story 30.1 already seeded on 14 pages), never duplicated into map.yaml. Do not add `sources:`/`verified:` frontmatter to the 40 authored pages that lack it today -- out of scope for this story (the checks that use it simply find nothing to check on those pages, which is correct, honest, incremental behavior, not a gap).
- `docs/MAP.md` -- append ONE new section at the very end (after "## Downstream stories"), nothing else in the file changes:
  ```
  ## Page registry (generated)

  <!-- docs-map:registry:begin -- generated by `pixi run -e pyforge-guild docs-map-render` from docs/map.yaml. Do not hand-edit between the markers; docs-currency (Story 30.2) treats a mismatch as a finding. -->
  ...
  <!-- docs-map:registry:end -->
  ```
  Between the markers: one `### <Quadrant title>` subsection per quadrant (`Tutorials`, `How-to`, `Reference`, `Explanation`, in that order), each with a `| Page | Owner | Kind |` table, one row per that quadrant's `docs/map.yaml` pages sorted by `path`, `Page` cell a markdown link `` [`<path>`](<path>) `` (this exact form is what `docs_map_hygiene.py`'s existing `_MD_LINK_RE` already recognizes -- no change needed there). The render function that produces this block is the single source for both the pixi task's write and the doctor check's read (see Design Notes).
- `scripts/docs_map_render.py` (NEW) -- thin write-side script (repo-level, deliberately **outside** `pyforge.doctor` -- that package is read-only, NFR-1). Reads `docs/map.yaml`, imports the pure render function from `pyforge.doctor.sources.docs_currency`, replaces the text between the `docs-map:registry:begin`/`docs-map:registry:end` markers in `docs/MAP.md` in place (everything outside the markers untouched byte-for-byte), writes the file. Mirror `scripts/governance_currency_check.py`'s module style (docstring, `ROOT = Path(__file__).resolve().parents[1]`, `argparse`, `main()` returning an int) but this script is a plain mutator with no `DETECTOR` marker and no exit-code contract beyond 0/1 (success/failure writing) -- it is invoked directly by the pixi task, never through `scripts/detectors.py`'s AST scan.

### The 54 pages (`docs/map.yaml` `pages:` contents)

Default `kind: authored`, `owner: fleet` for every page **except** the two override lists below. `quadrant` is always derivable from the path's first segment.

**`kind: pointer`** (7 -- the four quadrant-root `README.md` index pages, plus the three redirect stubs `docs/MAP.md` § *Redirect stubs* already documents):
`tutorials/README.md`, `how-to/README.md`, `reference/README.md`, `explanation/README.md`, `reference/antigravity-developer-startup.md`, `reference/manticore-studio.md`, `reference/mcp-server-architecture.md`.

**`owner: doctor`** (6 -- pages that document Doctor's own detector/one-chain mechanism; everything else, including the two `-py`-suffixed conda-forge-inventory pages and the Jira/GitHub sync README, is `owner: fleet`):
`how-to/one-chain-station-ops.md`, `how-to/reconcile-spec-surface.md`, `how-to/run-and-understand-detectors.md`, `explanation/one-chain-lock-and-mop.md`, `explanation/the-detector-framework.md`, `reference/judgement-vocabulary.md`.

**Full path list** (54; quadrant = first path segment):

`tutorials/`: `getting-started.md`, `local-platform-development.md`, `README.md`

`how-to/`: `ai-engine-operations.md`, `air-gapped-mirror-setup.md`, `antigravity-developer-startup.md`, `detect-concurrent-agent-activity.md`, `disaster-recovery.md`, `driving-a-pyforge-station-backlog.md`, `feedstock-failure-remediation.md`, `feedstock-platform-expansion.md`, `github-actions-recipe-ci.md`, `manage-worktrees-with-bmad.md`, `manticore-studio.md`, `monitor-the-fleet.md`, `ocp-cluster-bringup.md`, `one-chain-station-ops.md`, `pixi-tasks.md`, `presentation-deck.md`, `README.md`, `recipe-testing-and-builds.md`, `reconcile-spec-surface.md`, `restore-operations.md`, `run-and-understand-detectors.md`, `station-cli-operations.md`, `troubleshoot-bmad-agent-loops.md`, `troubleshooting-recipe-builds.md`

`reference/`: `agent-memory-lifecycle.md`, `antigravity-developer-startup.md`, `conda-forge-packaging-inventory-operations_prompt.md`, `conda-forge-packaging-inventory-operations_replay.md`, `container-base-layer-convention.md`, `developer-guide.md`, `github-workflows.md`, `judgement-vocabulary.md`, `library-llms-full.md`, `manticore-studio.md`, `mcp-server-architecture.md`, `README.md`, `station-cheat-sheet.md`, `station-verify-commands.md`, `sync-jira-github-workflow-templates/README.md`, `test-charter.md`

`explanation/`: `airgap-distribution-contract.md`, `enterprise-deployment.md`, `mcp-server-architecture.md`, `one-chain-lock-and-mop.md`, `platform-deployment-architecture.md`, `platform-requirements.md`, `pyforge-ecosystem-architecture.md`, `pyforge-estate-overview.md`, `README.md`, `the-detector-framework.md`, `the-tier-model-and-data-flow.md`

Count check: 3 + 24 + 16 + 11 = 54, matching `find docs/{tutorials,how-to,reference,explanation} -name '*.md' | wc -l` on `main` today. If that count has changed since this spec was written (a page added/removed by another PR), reconcile `docs/map.yaml`'s page list against the live tree rather than this list -- the live tree is authoritative, this enumeration is a snapshot.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/docs-map-schema.json` -- create the JSON Schema -- `docs/map.yaml` needs something to validate against; ships in the doctor package per the Binding.
  - Shape: `{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:local-recipes:pyforge-doctor:docs-map-schema", "type": "object", "required": ["schema_version", "pages"], "properties": {"schema_version": {"type": "integer", "minimum": 1}, "pages": {"type": "array", "items": {"$ref": "#/$defs/page"}}}, "$defs": {"page": {"type": "object", "required": ["path", "quadrant", "owner", "kind"], "properties": {"path": {"type": "string"}, "quadrant": {"enum": ["tutorials", "how-to", "reference", "explanation"]}, "owner": {"type": "string"}, "kind": {"enum": ["generated", "authored", "pointer"]}, "sources": {"type": "array", "items": {"type": "string"}}, "stamp": {"type": "object", "properties": {"derived_at": {"type": "string"}, "tree": {"type": "string"}}, "additionalProperties": false}}, "additionalProperties": false}}, "additionalProperties": false}`.
- `docs/map.yaml` -- create the registry with all 54 pages from the Code Map's list above -- this is the new source of truth the story's title names.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py` -- implement, exporting at least `gather(target: Path) -> tuple[Finding, ...]`, `render_map_registry(pages: list[dict]) -> str` (pure), and `load_map_yaml(target: Path) -> dict` (raises `ValueError`/`yaml.YAMLError`/`jsonschema.ValidationError` on missing/invalid -- caller wraps with `degrade_on_exception`) -- these three checks, one Finding per triggered class (else one OK):
  - **map-render** (`docs-currency-map-render`): render `docs/map.yaml`'s pages via `render_map_registry`; extract the text between `docs-map:registry:begin`/`docs-map:registry:end` in `docs/MAP.md`; byte-compare. Markers absent from MAP.md counts as a mismatch too. WARN on mismatch, naming that the registry section is stale.
  - **authored-page-stale** (`docs-currency-authored-stale`): for each `kind: authored` page, (a) parse *that page's own* frontmatter for `sources:`/`verified:` (reuse the block-fence parse pattern other sources already use for page frontmatter, e.g. `sources/chain.py`'s frontmatter split, or a minimal local one -- PyYAML `safe_load` on the fenced block is sufficient here); for each source path, `run_git(target, ["log", "-1", "--format=%cs", "--", source])` and compare the returned `YYYY-MM-DD` against `verified:` -- WARN naming the page + stale source(s) if newer. (b) scan the page body for backticked `bmad-*`/`skf-*` skill names, `scripts/`/`_bmad/`-rooted `.py` paths, and repo-relative paths under a real top-level dir (mirror `scripts/governance_currency_check.py`'s three regexes and `_resolves_as_identifier`/existence-check logic -- duplicated here deliberately, `pyforge.doctor` cannot import from the top-level `scripts/` tree) that do not resolve -- WARN naming the token + page. One Finding per page with either/both evidence kinds (`evidence={"kind": "source-stale"|"dead-reference", ...}`); pages without `sources:`/`verified:` frontmatter are only checked for (b).
  - **skill-dir-hygiene** (`docs-currency-skill-dir-hygiene`): for each `.claude/skills/<name>/` directory whose name starts with `bmad-`, `pyforge-`, or `skf-`, list top-level entries; allowed = `SKILL.md` (file) and `scripts/`, `references/`, `assets/` (dirs). Anything else -- WARN naming the stray path(s), one Finding aggregating all of them (mirror `docs_map_hygiene.py`'s aggregate-evidence-list style).
  - Fail-open: `docs/map.yaml` missing or schema-invalid -- let `load_map_yaml` raise; `gather()` wraps the whole thing in `degrade_on_exception(Source.DOCS_CURRENCY, "docs-currency", ...)`, producing exactly one WARN naming the problem (never a false green; never FAIL).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_map_hygiene.py` -- change the `unmapped` `Finding`'s `status=DoctorStatus.WARN` to `status=DoctorStatus.FAIL`; update its module docstring and the `unmapped` bullet in `gather()`'s docstring to say FAIL, citing Story 30.2/CAP-84 as the promotion.
- `scripts/docs_map_render.py` -- create the write-side script per the Code Map.
- `docs/MAP.md` -- append the generated `## Page registry` section per the Code Map, then run `pixi run -e pyforge-guild docs-map-render` (once the script exists) rather than hand-typing the table, so the committed content is provably the script's own output.
- Wiring: `models.py`, `sources/__init__.py`, `sources/__main__.py`, `scripts/detectors.py`, `pixi.toml` -- the five registration edits from the Code Map.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py` -- one test per I/O matrix row (6), plus `render_map_registry` round-trips against a small fixture `pages` list, plus the schema-validation-rejects-a-malformed-file case. Use `tmp_path` fixtures throughout (never read the live `docs/` tree from a unit test -- mirror `test_sources_docs_map_hygiene.py`).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py` -- update the one test per the Code Map.
- Doctor memlog: append one entry recording the promotion + the "kept beside" decision -- `uv run _bmad/scripts/memlog.py append --workspace _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor --type event --text "Story 30.2: docs/map.yaml + docs-currency landed; docs-map-hygiene's unmapped class promoted warn->fail (kept beside docs-currency, not retired -- MAP.md's generated Page registry section keeps its MAP.md-link scan equivalent to a map.yaml-membership scan)."` -- satisfies the epics.md Then-clause "the promotion is recorded on the doctor memlog".

**Acceptance Criteria:**
- Given `docs/map.yaml` and `data/docs-map-schema.json` exist, when `jsonschema.validate` runs the former against the latter, then it succeeds with no `ValidationError`.
- Given `docs/MAP.md`'s generated section and `docs/map.yaml`, when `docs-currency` runs on `main` after this story lands, then it reports OK (no map-render, authored-stale, or skill-dir-hygiene findings).
- Given `docs/MAP.md` is hand-edited so its `## Page registry` section content no longer matches a fresh render of `docs/map.yaml`, when `docs-currency` runs, then it reports exactly one WARN naming the mismatch; reverting the edit restores OK.
- Given a page listed as `kind: authored` with its own `sources:`/`verified:` frontmatter where a listed source's git last-touch postdates `verified:`, when `docs-currency` runs, then it WARNs naming that page and that source.
- Given an authored page's body contains a backticked path that does not resolve, when `docs-currency` runs, then it WARNs naming that token and that page.
- Given a stray non-layout file inside a `bmad-*`/`pyforge-*`/`skf-*` skill directory, when `docs-currency` runs, then it WARNs naming that path.
- Given every quadrant page is present in `docs/map.yaml` (the 54-page list), when `docs-map-hygiene` runs on `main` after this story lands, then it reports OK -- the promoted `unmapped` FAIL does not regress `detectors-ci`.
- Given `docs/map.yaml` is deleted or made schema-invalid, when `docs-currency` runs, then it emits exactly one WARN (never FAIL, never a crash, never a silent OK).

## Design Notes

**"Kept beside," not "retired into"** (the Binding's own discretion clause, recorded here as required). `docs_map_hygiene.py` keeps its own `Source.DOCS_MAP_HYGIENE`, its own CLI dispatch entry, its own pixi task, its own detectors.py registration, and its own test file -- unchanged in identity, one status flip (`unmapped` WARN -> FAIL). This is deliberately the lower-risk path versus deleting an enum member from Doctor's closed, historically append-only `Source` taxonomy (every prior story's comment reads "the closed taxonomy EXTENDED once more" -- never "retired"), rewiring `sources/__init__.py`/`__main__.py`/`scripts/detectors.py`/`pixi.toml` to remove entries, and deleting a test file with live coverage. It is correct, not just convenient: `docs_map_hygiene.py` already compares MAP.md's *rendered markdown links* against the four quadrant directories; once this story's `## Page registry` section links every `docs/map.yaml` page (by construction -- the render function emits one link per page), MAP.md's link set and map.yaml's page set are the same set. Promoting `unmapped` to FAIL is therefore equivalent to "a quadrant page absent from map.yaml is FAIL" (the story's own I/O matrix row 4) without touching `docs_map_hygiene.py`'s comparison logic at all.

**Why the render is a marked *section*, not a byte-for-byte reproduction of the whole file.** `docs/MAP.md` today is ~170 lines of hand-authored narrative: an intro, a four-quadrant summary table with rich multi-link prose cells, an "Outside this map" exclusion table, several historical "Relocated in Story N" / "Per-file classification" / "Archived reference" / "Downstream stories" tables that record *migration history*, not current per-page facts. `docs/map.yaml`'s own declared schema (Binding: "quadrant / owner / kind / sources / stamp per page") is a minimal, 4-5-field-per-page registry -- it has no field for the rich per-table prose those historical sections carry, and inventing one to force a full-file byte-for-byte reproduction would mean either duplicating narrative content into YAML (a second, driftable copy of prose that belongs in exactly one place) or silently discarding institutional memory neither this story nor its research doc asked to delete. The marked-section design instead adds ONE new, wholly-generated section that is byte-verifiable by construction (`## Page registry`, all 54 pages, `Page | Owner | Kind` per quadrant) and leaves every existing hand-authored table untouched. This satisfies "MAP.md is a render -- a byte diff between it and its render is a finding" for the part that is genuinely a render, without inventing scope (a full historical-content data model) the story never asked for. Story 30.3, which introduces real `kind: generated` pages with `derived_at`/`tree` stamps, is a natural place to extend this section-marker pattern to more of MAP.md if wanted -- not required here.

**Why `sources:`/`verified:` live on each authored page's own frontmatter, never duplicated into `docs/map.yaml`.** The Binding lists both "`docs/map.yaml` (new; quadrant / owner / kind / sources / stamp per page)" and "frontmatter `sources:` / `verified:` on every authored page" as surface. Duplicating the same two facts in two files is itself a drift risk this story's whole point is to eliminate. Resolution: `sources`/`stamp` in `docs/map.yaml`'s schema exist for `kind: generated` pages (Story 30.3, where a generator's inputs are genuinely registry-level facts, not something the generated page's own body could sensibly declare); for `kind: authored` pages, the per-page frontmatter Story 30.1 already seeded on 14 pages *is* the `sources:`/`verified:` record, and `docs-currency`'s authored-page-stale check reads it from there. This story does not add `sources:`/`verified:` frontmatter to the other 40 authored pages -- the check honestly finds nothing to verify on a page that declares nothing, which is correct incremental behavior (the same warn-first, coverage-grows-over-time posture CAP-62 already establishes for this whole class of check), not a gap this story leaves open.

**Why the skill-dir-hygiene check scopes to `bmad-*`/`pyforge-*`/`skf-*` directories only.** These are the externally-regenerated directories (the BMAD installer rewrites/deletes `bmad-*` on every upgrade; the SKF exporter regenerates `pyforge-*` and owns `skf-*`'s own tooling) -- the exact failure class the research doc's finding #1 documents (130 dead README stubs, none read by any harness, silently overwritten or orphaned on the next regeneration). `conda-forge-expert/` and the other hand-curated `.claude/skills/*` directories are not externally regenerated and are deliberately out of this check's scope -- flagging their non-minimal layout would be false-positive noise against directories nothing is going to silently delete out from under.

## Spec Change Log

_Empty -- no review loopback yet._

## Review Triage Log

_Empty -- no review pass yet._
