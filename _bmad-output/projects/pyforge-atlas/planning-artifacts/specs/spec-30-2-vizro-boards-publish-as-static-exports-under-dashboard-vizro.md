---
title: '30.2: Vizro boards publish as static exports under /dashboard/vizro/'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
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
  (steward's), and the shape above holds unchanged. *(Amended 2026-10-15, orchestrator ruling; operator may override:
  the task lands under `[feature.pyforge-atlas.tasks]` and runs in `-e pyforge-atlas`, which carries vizro and
  plotly 7.1.0, with no `PYTHONPATH`, as its sibling atlas tasks; the job's `setup-pixi` names `pyforge-atlas`. AC1,
  AC8 and Always say the same.)*
- **The consumer is not this story.** The Pages build consumes `vizro-static-export` the way steward 102.4 consumes
  `kedro-viz-export`, and herald Story 43.3 (CAP-61, M3) mounts it through `publicDir`. `pages-check` judges the mount as a
  first-party tree: no `VENDORED_ROOTS` entry is added for `dashboard/vizro/`, so a `cdn.plot.ly` reference would red
  it — the structural proof the Dream asks for. *(Amended 2026-10-15, orchestrator ruling; operator may override: the
  pages stay judged, but the vendored bundle `dashboard/vizro/assets/plotly.min.js` is byte-identical upstream code
  that names third-party origins, so herald Story 43.3 adds that one exact file, never the tree, to `VENDORED_ROOTS`
  (herald:AD-21 rule 5), and the export refuses any chart drawing a third-party trace; the Pages download step is
  steward 102.4's. AC2 and AC7 say the same.)*
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
  `pixi run -e pyforge-atlas vizro-static-export` (amended 2026-10-15, orchestrator ruling; operator may override) exits 0 and `docs/dashboard/vizro/` holds `index.html`, exactly one
  `assets/plotly.min.js` (byte-identical to the env's `plotly/package_data/plotly.min.js`), `manifest.json`, and one
  `<page-id>/index.html` for every page `build_dashboard` returns (34 today; the test reads the count from the object,
  never a literal).
- **AC2 — No third-party origin.** (amended 2026-10-15, orchestrator ruling; operator may override) The pages: `grep -rl --include='*.html' "cdn.plot.ly" docs/dashboard/vizro`
  prints nothing; every `<script src=` and `<link href=` in the export resolves to a file inside
  `docs/dashboard/vizro/`; no `https://` resource reference appears in any page (navigation `<a href>` to
  `/dashboard/kedro-viz/` and `/` is allowed, as herald's check allows). The vendored `assets/plotly.min.js` is
  plotly's own bytes (AC1) and carries map and geo provider URLs; it is reachable at runtime only through geo or map
  traces or Chart Studio links, so the export refuses a chart that draws one of those traces, writes
  `showLink` / `showEditInChartStudio` off, and `assets/` holds that one file only.
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
- **AC7 — The mount holds the Pages gate.** (amended 2026-10-15, orchestrator ruling; operator may override) Verified when herald Story 43.3 runs
  `pixi run --frozen -e site pages-check` with an export present: 43.3 lands the `/dashboard/vizro/` mount and adds to
  `docsite/tools/assemble_pages.py`'s `VENDORED_ROOTS` the exact file `dashboard/vizro/assets/plotly.min.js`
  (herald:AD-21 rule 5, a vendored upstream bundle), never the `dashboard/vizro/` tree, so every page stays judged and
  `pages-check` reports no cross-origin finding under `dashboard/vizro/`. The `pages.yml` download of the
  `vizro-static-export` artifact is steward 102.4's (its review fix, `5993910a33`).
- **AC8 — The producer job.** A test reads `.github/workflows/kedro-viz-publish.yml` as YAML and asserts the Vizro job:
  `setup-pixi` `environments` naming `pyforge-atlas` (amended 2026-10-15, orchestrator ruling; operator may override); one `actions/upload-artifact` step with `name:
  vizro-static-export`, `retention-days: 90`, `path: docs/dashboard/vizro`; no `run` containing `git push`,
  `git commit` or `steward deploy`; `permissions.contents` still `read`; the job `if:` carrying
  `PAUSE_KEDRO_VIZ_PUBLISH`; the upload step gated on the flag's resolved value. (If the operator rules for a separate
  workflow, the same assertions run against that file and the test names it.)
- **AC9 — Two states.** A test runs the exporter with
  `pyforge.testing_kit.flags.flag_states("pyforge.atlas.vizro_static_boards")`: on, AC1–AC4 on the fixture root; off,
  AC6.
- **AC10 — The gates.** `pixi run -e pyforge-atlas kedro-test`, `pixi run -e pyforge-atlas kedro-catalog-check` and
  `pixi run --frozen -e local-recipes dashboard-dryrun` exit 0 (the live dashboard's own gate, unchanged); `flag-gate-check` exits 0; `spec-surface-check` exits 0
  after the memlog reconciles and scoped stamps of every Spec it names.

## Boundaries & Constraints

**Always:**
- The export is the same `Dashboard` object the live server runs: `build_dashboard`, `dashboard.data`'s loaders, the D1
  models. Nothing is re-derived for the export (the intake's drift risk, closed by construction).
- One vendored `plotly.min.js`, referenced by relative path from every page; its bytes come from the env, never from a
  URL and never from a checked-in copy.
- The refusal runs first and writes nothing; `sld:AD-10` is applied as a rule, not by importing steward.
- Every page prints its AD-17 stamp; the manifest repeats it as `data_build_timestamp`.
- Runs in `-e pyforge-atlas` (amended 2026-10-15, orchestrator ruling; operator may override): that env carries vizro and plotly 7.1.0, and `-e local-recipes` (over 10 GB) is the
  recipe factory's env, which no station job assumes (AGENTS.md). The task is
  `[feature.pyforge-atlas.tasks.vizro-static-export]`.
- Every Spec `spec-surface-check` names is reconciled through its memlog and stamped scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not use `include_plotlyjs='cdn'`, `True` or `'directory'`; do not reference any origin but the artifact's own.
- Do not embed data for filter states, emulate filters in JavaScript, or export a Run control — no server means no
  submission and no per-user view.
- Do not export a board that declares an access column, and do not downgrade the refusal to a warning or a skip.
- Do not commit the export, call `deploy-pages`, or edit `pages.yml` / `docsite/` / `docs-site/` in this story (amended 2026-10-15, orchestrator ruling; operator may override): the
  `pages.yml` consumer step is steward 102.4's, and the `/dashboard/vizro/` mount and the `VENDORED_ROOTS` entry for
  the exact file `dashboard/vizro/assets/plotly.min.js` are herald 43.3's. No `VENDORED_ROOTS` entry ever covers the
  `dashboard/vizro/` tree or its pages.
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
**When** `pixi run -e pyforge-atlas vizro-static-export` runs with the flag on against the fixture data root *(amended 2026-10-15, orchestrator ruling; operator may override)*
**Then** it exits 0 and writes the board index, one page per board, exactly one `assets/plotly.min.js` and
`manifest.json` (`exported_at`, `export_commit`, `boards[]` with `id`, `title`, `path`, `data_build_timestamp`); no
`cdn.plot.ly` reference exists and every script resolves to the vendored file; the Run controls are absent
**And** a declared access column refuses and writes nothing; flag off refuses and writes nothing; `pages-check` exits 0
with the export mounted and the exact file `dashboard/vizro/assets/plotly.min.js` the one `VENDORED_ROOTS` entry
under it (herald:AD-21 rule 5; amended 2026-10-15, was "`VENDORED_ROOTS` unchanged"); the producer job uploads `vizro-static-export` (90 days) with no
commit step; `dashboard-dryrun`, `kedro-test` and `kedro-catalog-check` are green and the flag test runs the key in both
states

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; import smoke and scaffold
  layout — the exporter must import without vizro present only where `dashboard/__init__.py` already guards it).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; the AD-1
  import-direction and no-inline-IO meta-tests, which must stay green with the exporter under `dashboard/`).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e local-recipes dashboard-dryrun` — expected: pass (the object still builds;
  `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_dryrun.py` and the exporter's tests run
  there: AC1–AC6; the two-state test skips, `-e local-recipes` carries no openfeature).
- `pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_vizro_static_export.py src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_vizro_static_export_flag.py -q`
  — expected: pass (AC1–AC6 and AC9: the second file runs `pyforge.atlas.vizro_static_boards` in both states with
  `flag_states`).
- `pixi run --frozen -e pyforge-atlas vizro-static-export` on a checkout with the flag on, then
  `grep -rl --include='*.html' "cdn.plot.ly" docs/dashboard/vizro; echo $?` — expected: no output, then `1` (AC2);
  `find docs/dashboard/vizro -name plotly.min.js | wc -l` — expected: `1`.
- `pixi run --frozen -e site pages-check` with the export present — expected: exit 0 (AC7; run by herald Story 43.3).
  *Verified 2026-10-15 by herald 43.3 (its Verification run; copied here at the lane-B → lane-A merge):* a real export
  from this story's `vizro_static_export.py` (34 boards, 37 files, `export_commit` `cbc34a5800`) copied to
  `docs/dashboard/vizro/` — `pixi run --frozen -e site pages-check` exit 0 with `pyforge.herald.pages_one_generator`
  on (mounted from `docs-site/public/`, judged by 43.3's origin check) and off (mounted by `_copy_dashboard`, judged by
  the old scanner); no cross-origin finding under `dashboard/vizro/`; the one exempt file,
  `dashboard/vizro/assets/plotly.min.js` (herald:AD-21 rule 5), holds one reference, `https://cdn.jsdelivr.net`
  (maplibre's icon template), and all 34 pages pass judged. The export was removed afterwards. AC7 is met; this
  story's status stays `in-review` until the chain's endgame flips it.
  *Re-verified 2026-10-15 by herald 43.3's second review fix, on the rewritten origin check (`html.parser`, code read
  only from scripts, styles and .css/.js files):* a fresh real export (34 boards, 37 files, `export_commit`
  `ee4d754fd437`) in `docs/dashboard/vizro/` -- `pages-check` exit 0 with `pyforge.herald.pages_one_generator` and
  `pyforge.herald.status_pages` on and the 42.1 and 43.6 fixtures present; the artifact held all 37 files under
  `dashboard/vizro/`, `plotly.min.js` exempt by name and every page judged. The export was removed afterwards.
- `pixi run -e pyforge-atlas pyforge-atlas-test -k "kedro_viz_publish or vizro_static"` — expected: pass (AC8 and the
  unit-level tests).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped
  stamps (`spec-pyforge-atlas`; `spec-pyforge-unifying-strategy` co-governs the dryrun test and
  `dashboard/__init__.py` if either moves; `spec-pyforge-steward` if the workflow's registry row changes).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (outward acts a session never performs):**
- Decide the producer's home (the Spec's open question: a second job on `kedro-viz-publish.yml`, or its own workflow
  with its own registry row). Then `gh workflow run kedro-viz-publish.yml` once and confirm `vizro-static-export` is
  listed on the run.
- Turn `pyforge.atlas.vizro_static_boards` on where the boards should publish; the consumer (steward 102.4, herald
  CAP-61) mounts them at `/dashboard/vizro/`.
- Know what CI exports: the workflow sets no `PYFORGE_ENVIRONMENT`, so the flag resolves as `dev` (on) in CI, and the
  runner materializes no data (`data/` is gitignored), so the uploaded boards are honest-empty until a producer step
  materializes their datasets.

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
- 2026-10-15 (fixed while building herald 42.3 + steward 102.5; this story's spec status unchanged):
  - `StaticExportError` gains `PyforgeError` as a base, as `pyforge-core`'s exception-root meta-test requires.
    *(42.3 + 102.5's review, 2026-10-15: the second base `Exception` was redundant, since `PyforgeError` subclasses
    it; the class is now `StaticExportError(PyforgeError)`, as `pyforge-core`'s own errors are.)*
  - The flag key is registered in the core and platform tree-wide flag tests, which list every key the tree holds;
    both were red at `73ae4f1180`.
  - `test_vizro_static_export.py` no longer computes a repository root. `MEMBER_DIR.parents[2]` was `src/`, and steward's
    station-tests trigger map read that as a read of all of `src/`. The HEAD check runs from the member directory.
- 2026-10-15 (independent review, iteration 1; orchestrator rulings 2026-10-15, operator may override):
  - **Rulings.** The Vizro export runs in `-e pyforge-atlas`, not `-e local-recipes`. That env carries vizro and
    plotly 7.1.0; `-e local-recipes` is over 10 GB, has no disk-free step on a stock runner, and is not a station job's
    env (AGENTS.md). The task moves to `[feature.pyforge-atlas.tasks]`, and the job's `setup-pixi` names `pyforge-atlas`.
    The Pages-side items leave this story, per its own cross-station prose:
    - the `pages.yml` consumer step landed in steward 102.4's review fix (`5993910a33`);
    - the `/dashboard/vizro/` mount, and the herald exemption of the exact file `dashboard/vizro/assets/plotly.min.js`
      (herald:AD-21 rule 5), land in herald 43.3.

    AC1, AC2, AC7, AC8, Always and Never are amended in place to say so.
  - **Should-fix.**
    - The data-root scrub replaces only the absolute root as a whole path: a relative `--data-root data` no longer
      rewrites `"data"` in a figure's JSON, and `/data` no longer rewrites `/database`. Tests cover the relative root
      and the path boundary.
    - Verification names `test_vizro_static_export_flag.py` and the dryrun test by repo path.
    - Guards: a chart drawing a geo or map trace (`THIRD_PARTY_TRACE_TYPES`) refuses the export.
      `PLOTLY_CONFIG` writes `showLink` and `showEditInChartStudio` off. A test asserts every exported chart's trace
      types avoid that set. `assets/` holds `plotly.min.js` alone.
  - **Nits.**
    - `exported_at` is the export commit's committer time, so one commit's export is byte-identical on every run (a
      test proves it) and the Pages tree hash does not move on a producer run with unchanged data. An unreadable
      committer time refuses (exit 1).
    - The `changes` job reads `git diff --quiet`'s exit code, so a diff error runs the producer instead of skipping it.
    - The `publish` job's marker is `kedro-viz-publish.publish`: rendered as if its row were live, the workflow does
      not change. Its three jobs still need `ci-job` rows when that row leaves `paused-manually` (steward's follow-up).
    - A fresh-interpreter test shows a flag-off run imports neither `pyforge.atlas.dashboard` nor vizro.
    - A hostile-input escaping test covers cells, columns, ids and Card text.
    - `docs/dashboard/.vizro-*/` is gitignored.
    - The swap renames the old tree aside and puts it back if the new tree's rename fails.
    - 30.1's spec points here for its AC4 widening.
  - **Not done here.** The `pyforge-atlas/tools/vizro_static_export.py` and `pixi.lock` paths are not in the job's
    filter, so a plotly bump does not re-export (review N3); that belongs to the schedule/consumer story.
- 2026-10-15 (the lane-B re-review, `rereview-laneb`: 30.2 RESOLVED with four nits; done here):
  - **The Approach is annotated in place (nit a)** with the 2026-10-15 rulings the ACs already carry: the task and
    the job run in `-e pyforge-atlas`, and the pages stay judged while herald 43.3 exempts the one vendored bundle
    file.
  - **The staleness clock is the export's moment (nit b).** `export_boards` passed no `now`, so the BSL staleness
    models read `time.time()`, and "one commit's export is byte-identical on every run" held only for honest-empty
    data. `now` now defaults to the export moment (`exported_at`, the export commit's committer time when the task
    runs), so the claim holds with materialized data too. Test:
    `test_the_staleness_clock_is_the_export_moment_not_the_wall_clock`.
  - **A failed aside-rename no longer leaks the staging directory (nit c).** Both renames sit inside the cleanup
    `try`: either failure puts the previous tree back if it was moved and removes the staging directory. Test:
    `test_a_failed_swap_keeps_the_previous_export_and_leaks_no_staging` (the aside rename and the swap-in rename).
  - **The scrub boundary is any non-path character (nit d).** The lookahead is `(?![\w-]|\.[\w-])`: a root followed
    by `)`, `,`, `:` or a sentence's `.` is replaced, and `/data.bak`, `/data-old`, `/data_2` are not. Test:
    `test_the_scrub_boundary_is_any_non_path_character`.
  - **The surface.** Atlas's Epic 30 surface (`marshal-policy.toml`) lists the two tree-wide flag pins that carry
    `pyforge.atlas.vizro_static_boards` (`src/platform/tests/test_openfeature_file_flags.py`,
    `src/shared/packages/pyforge-core/tests/unit/test_flags.py`).
- 2026-10-15 (the lane-B → lane-A merge): AC7's evidence, recorded by herald 43.3 with a real 34-board export, is copied
  into the Verification section beside AC7's command. Status stays `in-review`.
- 2026-10-15 (the Pages one-PR endgame, pass 1b): the Epic excerpt above still read `pixi run -e local-recipes
  vizro-static-export` and "`VENDORED_ROOTS` unchanged", against AC1, AC7, AC8 and Always as amended. It is amended in
  place, as Story 30.2's text in `epics.md` is, and `spec-pyforge-atlas` CAP-63 and FR-71 are re-derived to the same two
  rulings (the Spec memlog's decision of 2026-10-15). `docs/dashboard/README.md` names `-e pyforge-atlas` too. No AC
  changes; status stays `in-review`.

