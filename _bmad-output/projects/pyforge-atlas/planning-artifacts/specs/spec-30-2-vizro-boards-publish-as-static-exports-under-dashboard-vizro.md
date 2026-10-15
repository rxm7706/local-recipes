---
title: '30.2: Vizro boards publish as static exports under /dashboard/vizro/'
type: 'feature'
created: '2026-10-14'
status: 'in-progress'
baseline_revision: 'e134549afcbdcc5b55b35f291464ac60d6685243'
flag:
  key: pyforge.atlas.vizro_static_boards          # new; minted by this story
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                   # v1 is global only
  fallback: 'vizro-static-export refuses with the flag-off message and writes nothing; no vizro-static-export artifact is produced'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-30-1-the-dag-export-reaches-pages-as-a-workflow-artifact.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/DESIGN.md
  - docs/dreams/pyforge-atlas.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - archive/docs/intake/secure-live-dashboards/vizro-static-github-pages-workaround.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/scan_submit.py
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_dryrun.py
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_provenance.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
  - docsite/tools/assemble_pages.py
  - .github/workflows/kedro-viz-publish.yml
  - src/platform/config/flags.json
  - pixi.toml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the 34-page BSL-driven Vizro dashboard (`pyforge.atlas.dashboard.app.build_dashboard`; CAP-8, CAP-40,
CAP-42, CAP-50) runs only as a live server on Lane 1. The Pages redesign (herald Dream 2026-10-13, the target site map
row *Dashboards*) wants the boards beside the pipeline graph under `/dashboard/`, and the placement rule allows it only
as a static, public, build-time export: no server, no live data, zero third-party origins (herald AD-21). The one
documented way to do it, the archived intake `vizro-static-github-pages-workaround.md`, renders each figure with
`include_plotlyjs='cdn'` — a load from `cdn.plot.ly` the artifact may not make — and its section 4 embeds every state's
rows in the page, which `sld:AD-10` (steward spine) forbids as access control. Story 30.1 gives atlas the artifact
handoff this export rides.

**Approach:** export the same object the live server runs, vendor plotly.js once, refuse what cannot be static.

- **The exporter.** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/static_export.py` (new, inside
  `dashboard/`, the one place vizro is imported) calls `build_dashboard` exactly as `dashboard-dryrun` does — offline, no
  `.run()` — and walks its pages. For each page it renders the page's declared chart (the one `PageDef` chart DESIGN.md
  § 3–5 specifies, through `dashboard.data`'s loader, so AD-8 holds) and its table as HTML fragments with plotly's
  `Figure.to_html(full_html=False, include_plotlyjs="../assets/plotly.min.js")`, and wraps them in one page template
  (title, the page's `note`, its AD-17 stamp line, a link back to the board index). Output:
  `docs/dashboard/vizro/index.html` (the board index: one row per exported page with title, path and stamp),
  `docs/dashboard/vizro/<page-id>/index.html` per page, and `docs/dashboard/vizro/assets/plotly.min.js` — ONE copy, read
  from the env's `plotly/package_data/plotly.min.js` (`importlib.resources`), never fetched. `include_plotlyjs` is a
  relative path string, never `'cdn'`, never `True` (which inlines ~4 MB into every page) and never `'directory'`
  (which writes a copy per output directory).
- **What is not exported.** Controls that submit work — the path input and Run button of `scan-project` and
  `env-inspect`, which go through `dashboard.scan_submit` — are not rendered; those two pages show the latest cached
  result and carry one line saying so. Filters are not emulated client-side; a page renders the frame its loader returns
  with no filter applied, the same frame `dashboard-dryrun` proves against an independent BSL query. Pages that render
  only a Card today (the `behind-upstream` and `whodepends` shells, the honest-empty states) export that Card's text.
- **The manifest.** `docs/dashboard/vizro/manifest.json`: `exported_at` (ISO 8601 UTC, the export's wall clock),
  `export_commit` (40-hex; `GITHUB_SHA` when set, else `git rev-parse HEAD`, through the same helper 30.1 added), and
  `boards[]` — one entry per exported page with `id` (the page id), `title`, `path` (relative, `<page-id>/index.html`)
  and `data_build_timestamp`: the page's own AD-17 stamp, the ISO value `test_dashboard_provenance.py` already reads
  back from each page's legibility Card (`unavailable` when its constant has no file, exactly as the live page shows).
- **The refusal.** Before any file is written, the exporter asks each page whether it declares an access column (the
  hook is a `PageDef` field, default `None`; today no page sets it, and the exporter accepts an injected declaration so
  a fixture can). One declared column refuses the whole export: exit 1, the board named, nothing written — the rule
  `steward deploy static --access-column` already applies (`deploy.py` `_run_static`; `sld:AD-10`: "refuses rather
  than warns"). The exporter does not import `pyforge.steward`.
- **The task and the job.** `vizro-static-export` lands under `[feature.local-recipes.tasks]` in `pixi.toml` beside
  `dashboard-dryrun` (the vizro closure is in `local-recipes`, not `pyforge-guild`), with the same `PYTHONPATH` shape
  `dashboard-serve` uses. The producer is a second job on `.github/workflows/kedro-viz-publish.yml` — path-filtered on
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/**`, `.../semantic/**` and
  `.../conf/base/catalog.yml`, `setup-pixi` with `environments: local-recipes`, the task, then one
  `actions/upload-artifact` step `name: vizro-static-export`, `retention-days: 90`, `path: docs/dashboard/vizro` — gated
  on the same `PAUSE_KEDRO_VIZ_PUBLISH` fragment and the flag's resolved value, with no commit or push step. If the
  operator rules for its own workflow instead (the Spec's open question), the job moves file with its own registry row
  (steward's), and the shape above holds unchanged.
- **The consumer is not this story.** The Pages build consumes `vizro-static-export` the way steward 102.4 consumes
  `kedro-viz-export`, and herald Story 43.3 (CAP-61, M3) mounts it through `publicDir`. `pages-check` judges the mount as a
  first-party tree: no `VENDORED_ROOTS` entry is added for `dashboard/vizro/`, so a `cdn.plot.ly` reference would red
  it — the structural proof the Dream asks for.
- **The flag.** `pyforge.atlas.vizro_static_boards` in `flags.json` (`defaultVariant` off, owner `atlas`, story this
  key), `flag-overlays.json` (dev on, staging and production off) and `docs/governance/flag-inventory/pyforge-atlas.md`;
  read through `pyforge.core.flags.read_boolean` at the top of the exporter. Off: the task prints the flag-off message,
  exits with the station's usage code, writes nothing (`spec-feature-flag-governance` Q3's shape for a verb, applied to
  the task).

Ledger key: `30-2-vizro-boards-publish-as-static-exports-under-dashboard-vizro`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / S-30.1 (cross-station, prose: herald Story 43.3 (CAP-61, M3) `publicDir` mounts; steward 102.4's
consumer step generalized; no blocked row).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-63** (FR-71): the static export, the vendored plotly.js, the manifest, the refusal, the
  producer artifact, the flag. Extends CAP-8 / CAP-40 / CAP-42 / CAP-50 (the Vizro pages) and CAP-62 (the artifact
  handoff); AD-21 as amended 2026-10-14, AD-17 (the per-page stamp), AD-8 (every figure through the BSL seam), AD-1
  (vizro and the exporter stay under `dashboard/`; `pipelines/`, `datasets/`, `hooks.py` untouched).
- **`sld:AD-10`** (steward spine; `spec-secure-live-dashboards` folded into `spec-pyforge-steward`): static export and
  role isolation are mutually exclusive; a declared access column refuses, never warns. Applied by `steward deploy
  static`; re-applied here by the same rule, not by import.
- **herald AD-21** (one Pages artifact, one deploy caller, zero third-party origins; `pages-check` is the gate).
- **`pyforge-steward:CAP-166`** (the CI-pause fragment the job carries; the registry row, steward's).
- **canopy:AD-11** (one flag tree); `feature-flag-governance:CAP-1`, `CAP-4`.
- **Origin.** Dream `docs/dreams/pyforge-atlas.md`, the 2026-10-13 entry (its last sentences: "A later story publishes
  Vizro boards under `/dashboard/vizro/` as offline exports of the BSL-driven dashboard object"); herald Dream
  2026-10-13 (the site map's *Dashboards* row; the placement rule); the intake's *Vizro constraint* line; operator
  ruling 2026-10-13.

## Acceptance Criteria

- **AC1 — The export.** With the flag on and the fixture data root the dryrun gate uses,
  `pixi run -e local-recipes vizro-static-export` exits 0 and `docs/dashboard/vizro/` holds `index.html`, exactly one
  `assets/plotly.min.js` (byte-identical to the env's `plotly/package_data/plotly.min.js`), `manifest.json`, and one
  `<page-id>/index.html` for every page `build_dashboard` returns (34 today; the test reads the count from the object,
  never a literal).
- **AC2 — No third-party origin.** `grep -rl "cdn.plot.ly" docs/dashboard/vizro` prints nothing; every `<script src=`
  and `<link href=` in the export resolves to a file inside `docs/dashboard/vizro/`; no `https://` resource reference
  appears in any page (navigation `<a href>` to `/dashboard/kedro-viz/` and `/` is allowed, as herald's check allows).
- **AC3 — The manifest.** `manifest.json` parses with the keys `exported_at` (ISO 8601 UTC), `export_commit`
  (`^[0-9a-f]{40}$`, equal to `git rev-parse HEAD` or `GITHUB_SHA`) and `boards[]`; `boards` has one entry per exported
  page, each with exactly `id`, `title`, `path`, `data_build_timestamp`; every `path` exists; every
  `data_build_timestamp` equals the stamp the page's own legibility Card shows (`test_dashboard_provenance.py`'s
  read-back, reused), including `unavailable` where no constant file exists.
- **AC4 — What is not exported.** The `scan-project` and `env-inspect` pages contain no `<input`, no `<button` and no
  reference to `scan_submit`, and each carries the latest-cached-result line; no page contains a `<select` or any
  client-side filter script.
- **AC5 — The refusal.** A fixture board with a declared access column (injected through the `PageDef` hook) makes the
  task exit 1 with the board's id in the message, and `docs/dashboard/vizro/` does not exist afterwards (nothing
  written, not a partial tree). The exporter's module imports no `pyforge.steward`.
- **AC6 — Flag off.** With the flag off the task prints the flag-off message, exits with the station's usage code, and
  writes nothing.
- **AC7 — The mount holds the Pages gate.** With the export present under `docs/dashboard/vizro/` and
  `docsite/tools/assemble_pages.py`'s `VENDORED_ROOTS` unchanged, `pixi run --frozen -e site pages-check` exits 0 and
  reports no cross-origin finding under `dashboard/vizro/`.
- **AC8 — The producer job.** A test reads `.github/workflows/kedro-viz-publish.yml` as YAML and asserts the Vizro job:
  `setup-pixi` `environments` naming `local-recipes`; one `actions/upload-artifact` step with `name:
  vizro-static-export`, `retention-days: 90`, `path: docs/dashboard/vizro`; no `run` containing `git push`,
  `git commit` or `steward deploy`; `permissions.contents` still `read`; the job `if:` carrying
  `PAUSE_KEDRO_VIZ_PUBLISH`; the upload step gated on the flag's resolved value. (If the operator rules for a separate
  workflow, the same assertions run against that file and the test names it.)
- **AC9 — Two states.** A test runs the exporter with
  `pyforge.testing_kit.flags.flag_states("pyforge.atlas.vizro_static_boards")`: on, AC1–AC4 on the fixture root; off,
  AC6.
- **AC10 — The gates.** `pixi run -e pyforge-atlas kedro-test`, `pixi run -e pyforge-atlas kedro-catalog-check` and
  `pixi run --frozen -e local-recipes dashboard-dryrun` exit 0; `flag-gate-check` exits 0; `spec-surface-check` exits 0
  after the memlog reconciles and scoped stamps of every Spec it names.

## Boundaries & Constraints

**Always:**
- The export is the same `Dashboard` object the live server runs: `build_dashboard`, `dashboard.data`'s loaders, the D1
  models. Nothing is re-derived for the export (the intake's drift risk, closed by construction).
- One vendored `plotly.min.js`, referenced by relative path from every page; its bytes come from the env, never from a
  URL and never from a checked-in copy.
- The refusal runs first and writes nothing; `sld:AD-10` is applied as a rule, not by importing steward.
- Every page prints its AD-17 stamp; the manifest repeats it as `data_build_timestamp`.
- Runs in `-e local-recipes` (the vizro closure, about 257 packages, is not in `pyforge-guild`); the task uses the
  `PYTHONPATH` shape `dashboard-serve` already uses.
- Every Spec `spec-surface-check` names is reconciled through its memlog and stamped scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not use `include_plotlyjs='cdn'`, `True` or `'directory'`; do not reference any origin but the artifact's own.
- Do not embed data for filter states, emulate filters in JavaScript, or export a Run control — no server means no
  submission and no per-user view.
- Do not export a board that declares an access column, and do not downgrade the refusal to a warning or a skip.
- Do not commit the export, call `deploy-pages`, edit `pages.yml` / `dashboard.yml` / `docsite/` / `docs-site/`, or add a
  `VENDORED_ROOTS` entry for `dashboard/vizro/` (the mount must pass the cross-origin check on its own).
- Do not import Dagster, `kedro-mcp`, `pyforge.steward` or `subprocess` under `src/pyforge/atlas`; do not import vizro or
  plotly outside `dashboard/`.
- Do not change the 34-page inventory, DESIGN.md's controls, or `dashboard-dryrun`'s assertions; do not hand-edit
  `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on, fixture root | 34 pages, no access column | index + 34 pages + one plotly.min.js + manifest | exit 0 |
| honest-empty page | a BSL-wired page whose Parquet is absent | the page renders its honest-empty state and `unavailable` stamp; manifest row present | exit 0 |
| shell page | `behind-upstream`, `whodepends` | the Card's text, no figure, no script tag beyond plotly's | exit 0 |
| live-scan page | `scan-project`, `env-inspect` | latest cached result, the one-line notice, no input/button | exit 0 |
| access column declared | a fixture board with `access_column="org"` | nothing written; message names the board | exit 1 |
| flag off | any | flag-off message; nothing written | the station's usage exit code |
| plotly.min.js not found | env without plotly's package_data | nothing written; message names the resource | exit 1 |
| `export_commit` unknown | no git, no `GITHUB_SHA` | nothing written; message names the field | exit 1 |
| a `cdn.plot.ly` string in any page | regression in `include_plotlyjs` | AC2 test reds; `pages-check` reds the mount | test / check failure names the file |
| output dir exists | a previous export under `docs/dashboard/vizro/` | replaced wholesale, as `viz-publish-stage` replaces its tree | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-63 (FR-71), minted 2026-10-14; extends CAP-8, CAP-40, CAP-42, CAP-50
  and CAP-62; binds `sld:AD-10` (steward spine).
- Architecture: AD-21 (amended 2026-10-14), AD-17, AD-8, AD-1; herald AD-21; `sld:AD-10`. See the spine's § Currency
  reconciliation — 2026-10-14.
- Dream: `docs/dreams/pyforge-atlas.md` § Realization log, the 2026-10-13 entry (the DAG export reaches Pages as an
  artifact; its Vizro sentences); herald Dream 2026-10-13 (the Pages deployment, redesigned).
- Epic: Epic 30, Story 30.2.
- Ledger key: `30-2-vizro-boards-publish-as-static-exports-under-dashboard-vizro`.
- Ledger status at mint: `backlog`.
- Deps: S-30.1 (the artifact handoff and the `export_commit` helper). Cross-station, prose: herald Story 43.3 (CAP-61, M3)
  `publicDir` mounts; steward 102.4's consumer step, generalized to this artifact; neither is a blocked row.
  `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."30"`.
- Flag: `pyforge.atlas.vizro_static_boards` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** L • **Deps:** S-30.1 • **FR/AD:** spec-pyforge-atlas CAP-63 (FR-71), extending CAP-8,
CAP-40, CAP-42, CAP-50 and CAP-62; AD-21 (amended 2026-10-14), AD-17, AD-8, AD-1; `sld:AD-10` • flag:
`pyforge.atlas.vizro_static_boards`

**Given** the 34-page BSL-driven `Dashboard` object `dashboard-dryrun` builds offline in `-e local-recipes`, each page
carrying its own AD-17 stamp, and the archived intake workaround whose `include_plotlyjs='cdn'` herald AD-21 forbids
**When** `pixi run -e local-recipes vizro-static-export` runs with the flag on against the fixture data root
**Then** it exits 0 and writes the board index, one page per board, exactly one `assets/plotly.min.js` and
`manifest.json` (`exported_at`, `export_commit`, `boards[]` with `id`, `title`, `path`, `data_build_timestamp`); no
`cdn.plot.ly` reference exists and every script resolves to the vendored file; the Run controls are absent
**And** a declared access column refuses and writes nothing; flag off refuses and writes nothing; `pages-check` exits 0
with the export mounted and `VENDORED_ROOTS` unchanged; the producer job uploads `vizro-static-export` (90 days) with no
commit step; `dashboard-dryrun`, `kedro-test` and `kedro-catalog-check` are green and the flag test runs the key in both
states

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; import smoke and scaffold
  layout — the exporter must import without vizro present only where `dashboard/__init__.py` already guards it).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; the AD-1
  import-direction and no-inline-IO meta-tests, which must stay green with the exporter under `dashboard/`).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e local-recipes dashboard-dryrun` — expected: pass (the object still builds; the exporter's tests
  live beside it under `tests/integration/dashboard/` and run in this env: AC1–AC6, AC9).
- `pixi run --frozen -e local-recipes vizro-static-export` on a checkout with the flag on, then
  `grep -rl "cdn.plot.ly" docs/dashboard/vizro; echo $?` — expected: no output, then `1` (AC2); `find docs/dashboard/vizro
  -name plotly.min.js | wc -l` — expected: `1`.
- `pixi run --frozen -e site pages-check` with the export present — expected: exit 0 (AC7).
- `pixi run -e pyforge-atlas pyforge-atlas-test -k "kedro_viz_publish or vizro_static"` — expected: pass (AC8 and the
  unit-level tests).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped
  stamps (`spec-pyforge-atlas`; `spec-pyforge-unifying-strategy` co-governs `test_dashboard_dryrun.py` and
  `dashboard/__init__.py` if either moves; `spec-pyforge-steward` if the workflow's registry row changes).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (outward acts a session never performs):**
- Decide the producer's home (the Spec's open question: a second job on `kedro-viz-publish.yml`, or its own workflow
  with its own registry row). Then `gh workflow run kedro-viz-publish.yml` once and confirm `vizro-static-export` is
  listed on the run.
- Turn `pyforge.atlas.vizro_static_boards` on where the boards should publish; the consumer (steward 102.4, herald
  CAP-61) mounts them at `/dashboard/vizro/`.

## Named, not fixed here

- **The consumer and the mount.** Steward 102.4's download step, generalized to `vizro-static-export`; herald CAP-61
  (M3) `publicDir` mounts; the nav tile for `/dashboard/vizro/` (herald's `site.yml`, CAP-58's one navigation list).
- **The producer's home.** Second job or own workflow — the operator's call; the registry row is steward's either way.
- **A `pyforge atlas` verb for the export** is a later CAP if wanted; this story ships a pixi task.
- **Scheduled refresh** of the boards (the intake's "on data change, scheduled") is the Pages schedule's business
  (steward's `pages.yml`), not this producer's.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 30's Story 30.2 text, `spec-pyforge-atlas` CAP-63, the landed dashboard
  (`app.py` at `e134549afc`: `build_dashboard`, the 34-page inventory, `scan_submit`), `test_dashboard_provenance.py`'s
  per-page stamp read-back, steward's `deploy.py` `_run_static` refusal and `docsite/tools/assemble_pages.py`'s
  `VENDORED_ROOTS`. Where the landed code differs from the shape quoted here, the landed code wins and the deviation is
  recorded in this log.
- 2026-10-15 (atlas side built; the mount follows herald 43.3 / steward 102.4): `dashboard/static_export.py`,
  `vizro_static_boards.py` (the flag, read without vizro), `PageDef.access_column`, `tools/vizro_static_export.py`
  behind the `vizro-static-export` task, the `vizro` and `changes` jobs, the flag in the tree, overlays and inventory.
  Where the landed code differs from the shape quoted above:
  - **The bundle trips AC2's grep and AC7's check.** plotly 7.1.0's `package_data/plotly.min.js`, copied byte for
    byte (AC1, an Always), carries `cdn.plot.ly/un/` (its default topojson URL, fetched only by geo traces) and a
    maplibre ``.src = `https://cdn.jsdelivr.net/npm/@mapbox/maki@8.2.0/icons/${p}.svg` `` template that
    `assemble_pages.cross_origin_findings` reports as a cross-origin dynamic src. The pages reference no origin at
    all, so AC2 is tested on the pages; AC7 with `VENDORED_ROOTS` unchanged reds on `dashboard/vizro/assets/plotly.min.js`
    alone. Open for the operator: a `VENDORED_ROOTS` entry for `dashboard/vizro/assets/` only (AD-21 rule 5, the
    pages stay judged), a partial plotly.js bundle (a new dependency), or an amended AC.
  - **Path filter.** GitHub filters paths per workflow, so `on.push.paths` gains `dashboard/**` and `semantic/**`
    (30.1's AC4 pinned it unchanged; its test now pins the publish job to the 30.1 paths through the `changes` job,
    which tells each producer whether the push touched its own paths).
  - **Tables** render as plain HTML tables (every row, no script); only the declared chart goes through
    `Figure.to_html`. Card text renders through a small Markdown subset (headings, paragraphs, `code`, **bold**,
    pipe tables) rather than a new dependency. The data root's absolute path is shown as `<data-root>` on the
    static pages. Flag off exits 2, atlas's usage code.
  - **Fixed on the way (red on base):** `dashboard-dryrun` and `vizro-ai-dryrun` died loading `tests/conftest.py`
    (`pyforge.testing_kit` is not in `-e local-recipes`; their `PYTHONPATH` now carries the kit's `src`), and five
    `test_dashboard_e2e.py` tests then failed on `KeyError: 'nav-control-panel'` under vizro 0.1.62
    (`LandmarkDashboard` now finds the nav container in 0.1.60 and 0.1.62). AC9's two-state test needs
    `openfeature`, so it runs in `-e pyforge-atlas` and skips in `-e local-recipes`. The pixi-version registry counts
    two `setup-pixi` pins in `kedro-viz-publish.yml`.
