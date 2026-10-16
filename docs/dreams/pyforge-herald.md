---
title: Herald — capture the dream, illustrate the telemetry, proclaim the release
type: dream
owner: herald
status: specified
---

# Herald — the outward voice and design surface

## The Dream

Herald is the factory's **voice and visual surface**. Invisible engineering is
failed engineering; Herald exists so nothing the factory does stays invisible.
Not infrastructure — BMAD monorepo/multi-project machinery and cross-agent
portability belong to [[pyforge-marshal]] (the 2026-07-23 ownership review;
reaffirmed 2026-08-02 when [[fleet-chain-completeness]]'s orchestrated
regeneration machinery moved to Marshal for the same reason). Herald keeps
the communication face only.

Herald's work spans **four moments of proclamation**, and every product and
every Smith passes through all of them:

| # | Moment | What Herald owes | Lands as |
|---|---|---|---|
| **1** | **Pitch** — a Dream must be argued, not merely filed | the case made legible to humans who did not dream it | the deck family |
| **2** | **Progress** — a build in flight is not self-explaining | what changed, what it cost, what it unblocked | release notables, run telemetry as imagery |
| **3** | **Success** — shipping is not the same as being known to have shipped | the claim, with the evidence attached | the release proclamation |
| **4** | **Operations** — the long tail nobody announces | fixes, updates, deprecations, decommissions | change + end-of-life notices |

Moment 1 is the **first** thing Herald had to build, not the extent of the
job — the bookend framing ("first to touch a Dream, last to touch a release")
was retired 2026-07-25 because it reads as two touchpoints with silence
between them. Moment 4 needs no new lifecycle vocabulary: ending is one act,
scale-invariant across a Dream, a package, an application or a platform
(`archived`, with one of four reasons). What is missing is not the state —
it is anyone being **told**.

## What is real

- **The deck family (Moment 1 content)** — decks live on one shared engine
  under `presentations/`, bound to the Modernist design system, with the
  6-artifact export set proven repeatedly (`deck-export`). This is
  production-ready. Full orchestration detail (design-code-bridge +
  deckcraft + video-scripts + modernist-identity, the 9-station expansion,
  artifact tracking, 7 capabilities) lived in `spec-herald-pitch` —
  [[herald-pitch]] itself is archived (dream-level consolidation,
  2026-08-02). **Station-level consolidation, later the same day:** those 7
  capabilities are now folded inline into `spec-pyforge-herald/SPEC.md` as
  HER-4..HER-10 (`spec-herald-pitch` itself is archived, unmodified, at
  `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/`).
  Their PRD/Architecture decomposition had, in fact, already run — the same
  2026-08-01 commit that produced `spec-herald-pitch` also produced
  `prd-pyforge-herald-2026-08-01/prd.md` and
  `architecture-herald-pitch-2026-08-01/ARCHITECTURE-SPINE.md` — so the
  prior wording here ("ready for... that work has not run yet") was already
  stale before today's consolidation; both documents are now this station's
  single canonical PRD and Architecture. The Epics decomposition is a
  genuine gap, not a stale claim: `planning-artifacts/epics.md` /
  `epics-with-stories.md` are entirely Moments-2-4 content — Moment 1's own
  epic breakdown from the 2026-08-01 regeneration appears to have been
  overwritten by later Moments-2-4 epics work and was not found anywhere in
  the current tree during the 2026-08-02 consolidation; recoverable only via
  git history if needed.
- **The bridge, mechanized (`pyforge-herald` CLI)** — the Design↔Code seed/pull
  loop proven manually on 7 decks in one day is being packaged as a
  deterministic CLI (`herald deck seed/pull/status/watch`, `SPEC-design-code-bridge`
  CAP-1..5, FR-01–FR-26). **Shipped** — *corrected 2026-09-09 (fleet readiness
  pass); the superseded 2026-08-02 reading was "in progress, not finished… the
  foundation is 4 of 17 stories done… The CLI parser currently exposes only the
  empty `deck` subcommand group; `seed`, `pull`, `status` and `watch` are not
  wired up yet. The loop (`loop/pyforge-herald`) is paused mid-story on the
  next one, the fallback transport adapter (1.3)."* Epics 1–5 are `done` and
  `cli.py` (1764 lines) wires 26 subparsers across `deck`, `progress`,
  `success`, `notice` and `scheduler` (`cli.py:226-700`), including the
  `deck qa` and two `deck pptx-*` verbs added by Epics 14–15. Real code at
  `src/shared/packages/pyforge-herald/` (`bridge.py`, `cli.py`, `errors.py`,
  `registry.py`, `state.py`, `transport/`, `deck_qa.py`, `pptx_pipeline.py`),
  with tests, and a CI lane that runs them
  (`.github/workflows/pyforge-station-tests.yml:160-182`).
- **The stage** — the program console publishes the factory's state
  ([[factory-console]], Marshal's ledger; in the persona ideal Herald
  proclaims from it).

## Moments 2–4 (Progress, Success, Operations)

Moments 2, 3 and 4 were specced but had no implementation surface when this
section was first written. They are now shipped (see below), covering:

- **Moment 2 (Progress)** — `herald progress` / release notables composed
  from run telemetry and cost data, delivered where the audience lives.
- **Moment 3 (Success)** — `herald success` — a claim ("Project X shipped;
  here is the proof") backed by retrievable evidence (tests, metrics,
  adoption), gated on operator review before publish.
- **Moment 4 (Operations)** — `herald notice` — deprecation, fix and
  end-of-life notices with a permanent, indexed archive. A retired product
  currently just stops appearing; nobody is told it ended.

**Shipped 2026-08-08** — *corrected 2026-09-09 (fleet readiness pass); the
superseded 2026-08-02 reading was "the full planning chain for these three
surfaces exists… but **zero stories are implemented yet**. This is the
immediate next build target once the bridge foundation above clears its own
remaining stories."* Epics 8–10 landed 47 stories — `herald progress`,
`herald success`, `herald notice`, their three web tabs, and the local
JSON/SQLite stores behind them. What was deliberately scaled down is the
*triggering*: records are created by an operator running a CLI verb, not by a
webhook. The live-backend version is [[herald-moments-2-4-live-backend]],
whose Epic 13 is code-complete but has never run green in the estate — see
that Dream's 2026-09-09 entry.

## Kinships

[[pyforge-charter]] (charter section) · [[pyforge-marshal]] (owns the
re-scoped infrastructure and the fleet-chain regeneration machinery) ·
[[pyforge-scribe]] (the inward voice to Herald's outward) ·
[[factory-console]] (the stage Herald proclaims from).

## Realization log

- **2026-10-16 (the built-site tests skip silently) — Found: herald's 25 built-site tests run only where
  `docs-site/node_modules` already happens to exist.** Steward Story 105.1 named it as residual risk. A diff that
  touches only herald does not fire `pages.yml`, so `pr-preflight` never selects `docs-site-install`. CI's herald job
  (`pyforge-station-tests.yml` `herald-test`, `pixi run --frozen -e pyforge-herald pyforge-herald-test`) sets up only
  herald's environment and never installs docs-site either. Measured 2026-10-16 at `d21af06fbc` through
  `run_preflight`'s own selection, with an untracked herald probe and no `docs-site/node_modules`: herald's lane ran
  alone and reported 2033 passed and 30 skipped, 25 of the skips naming the docs-site install (17 through
  `pages_astro.needs_astro`, 8 through `test_agent_surface_and_changes.py`'s copy of it). CAP-61's success says
  `pyforge-herald-test` is green, and that green said nothing about the built site. **What it looks like when
  fixed:** herald's suite tasks depend on `docs-site-install` in the `site` environment, so `pixi run` installs first
  wherever the task runs. That covers CI's herald job, which sets up `site` beside herald, and the preflight, whose
  reader selects the install with herald's lane because the job's step runs that task. Under the task a missing
  install fails the built-site tests (`HERALD_DOCS_SITE_REQUIRED`) and never skips them, and one `needs_astro` serves
  every built-site test. **Constraints:** a fix under CAP-61 (no CAP, no FR, no flag); `pixi.lock` and
  `environment.yaml` do not change; the coverage gate takes no install dependency, because CI's coverage leg runs its
  driver and a preflight lane whose dependency the reader does not select never starts. Asked by the orchestrating
  session. Owner `spec-pyforge-herald`. → Epic 45 / Story 45.1, specced and fixed 2026-10-16.

- **2026-10-14 (every docs page is empty) — Found: the docs shelf on Pages has published 70 pages (69 and the 404 page) with no body since
  2026-10-08.** Measured on the live site the same day: the Starlight markdown container of `/`, `/how-to/pixi-tasks/`,
  `/explanation/the-detector-framework/` and `/tutorials/getting-started/` holds 0 words, and the first sentence of
  `docs/how-to/pixi-tasks.md` appears nowhere in its page. Cause: `docs-site/src/loaders/shelf-docs-loader.ts` stores each
  page's markdown as `body` but never renders it, and Starlight shows only an entry's `rendered` HTML. Nothing noticed:
  `pages-check` walks links on herald pages only, and no check reads a shelf page's body. Rendering the bodies also
  exposes their links: 678 in the 70 page bodies, which point at `.md` paths, `README.md` (published as a directory index),
  and repo files the shelf does not publish (`docs/MAP.md`, `docs/governance/**`); upstream BMAD-METHOD rewrites links
  with two rehype plugins this repo never vendored. Four GitHub Actions badge images in
  `docs/reference/developer-guide.md` would also load from github.com, which herald:AD-21 forbids. **What it looks like
  when fixed:** the loader renders each body with the project's rehype plugins; `rehype-markdown-links.js` and
  `rehype-base-paths.js` are vendored byte-identical from upstream at the recorded commit and pinned in
  `docs-site/README.md`; one local plugin points `README.md` links at the directory index and sends links to repo files
  the shelf does not publish to their repository page; the badge images become text links; `pages-check` fails an empty
  shelf body, a shelf link that does not resolve inside the artifact, and a shelf link missing the base path. Measured
  on the fixed build: 70 pages, 678 body links, 0 dead, 0 empty, 19 sent to their repository page; an
  independent review before commit found the first body check counted Starlight's footer, and it now parses the
  container alone. **Constraints:** a `fix`
  under CAP-52 (no CAP, no FR, no flag); the five files already vendored stay byte-identical (Story 41.1's review);
  no page moves. Asked by the operator in session ("Fix the docs root rendering an empty body"). Owner
  `spec-pyforge-herald`. → Epic 44 / Story 44.1, specced and fixed 2026-10-14.

- **2026-10-13 (the Pages deployment, redesigned) — Ruled: one holistic Pages site, built by one generator, deployed by
  one steward-owned workflow only when its inputs change.** Operator ask 2026-10-13: "redesign and rework the entire
  deployment at github pages", analysed through the CIS module (`bmad-brainstorming`, `bmad-cis-design-thinking`).
  Measured that day (API `total_count`, `git log --first-parent`, live `curl`): `dashboard.yml` ran 1,342 times since
  2026-09-13 (720 deploys, 621 cancelled, 1 failure, about 24 deploys a day) because it fires on every push to `main`
  (about 1,330 pushes in 30 days, up to 176 a day); a published-inputs path filter would have deployed 132 times; the
  site is four separately minted mechanisms glued by 3,830 bespoke lines (Jinja `docsite/` 2026-09-13, Starlight
  `docs-site/` 2026-10-05, the Kedro-Viz export committed to `docs/dashboard/kedro-viz/` since 2026-08-15 with its
  producer disabled since 2026-08-24, and `assemble_pages.py` with its own link, origin and redirect logic);
  `verify_claims.py` reports 17 drifted dossier claims as an advisory nobody reads; the deploy sat in `waiting` from
  2026-10-06 to 2026-10-12 unseen. The "two docs sites" the operator first named is the symptom; the four mechanisms
  are the problem. The analysis, 118 ideas, convergence and the target site map are in
  `_bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md`
  and `_bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md`.
  **What it looks like when real** (operator rulings 2026-10-13; staged, each stage shippable alone):
  - **M1, trigger, cost and hygiene (one fix story, herald).** The deploy workflow fires only on the published inputs
    (`docs/{tutorials,how-to,reference,explanation}/**`, `docs/index.md`, `docs/404.md`, `docs/map.yaml`,
    `docs/dashboard/**`, `docs-site/**`, `docsite/**`, `presentations/**`, the workflow itself), on `workflow_dispatch`
    and on a weekly schedule; `fetch-depth: 1` and a sparse checkout; the deploy job skips when the built tree hash
    equals the last deployed one; `docsite/tools/import_artifact.py` (a one-time migration, done) is deleted; the dead
    `dreams/pyforge-herald.md` link in `docs/index.md`, the stale deploy prose in `docs/reference/github-workflows.md`
    and `docs/explanation/enterprise-deployment.md`, and the two old-root URL references
    (`docs/dreams/design-sync-loop.md`, `src/prototype/packages/pyforge-atlas-kedro-viz/README.md`) are corrected, and
    doctor's `docs/MAP.md` names `docsite/` and `docs-site/` side by side (the clash is accepted until M3 ends it).
    Found while republishing the artifact: `md_inline` in `docsite/build.py` lifts escapes into NUL-delimited slots
    before code spans, so an escape inside a code span (`dossier.yml:1151`, `` `/stations/\*/mcp` ``) leaves a
    literal `\x000\x00` in `/herald/dossier/` and the artifact render today; the slot restore becomes iterative and
    the one needless escape goes.
    Done when deploys per 30 days fall under 150 and no cancelled streak reaches five.
  - **M2, one workflow in upstream shape (one epic; steward leads the duct, herald the content).** `dashboard.yml`
    becomes `pages.yml` in BMAD-METHOD `docs.yaml`'s shape (build on `pull_request` and `push`, deploy on `main` only),
    superseding the 2026-09-27 ruling that the file keeps its `dashboard.yml` path; `docsite-check.yml` folds in; the
    Kedro-Viz export arrives as a workflow artifact from atlas's producer and the mount is skipped, never failed, when
    none exists; the `pyforge.herald.pages_second_host` flag retires and `actions/configure-pages` is authoritative on
    every host; the same artifact is zipped as a release asset for the air-gapped host; the fleet board (`/status/`)
    and guild status (`/status/ci/`) render at build from `sprint-ledger-query --format json`,
    `scripts/fleet_picture.py` and `steward ci status --json`, refreshed per deploy and by a six-hourly schedule that
    deploys only when the fleet moved. Done when no commit by `github-actions[bot]` lands on `main` for Pages and one
    workflow touches Pages.
  - **M3, one generator (one epic, herald).** Astro renders the dossier from `dossier.yml` through a content
    collection (the 14 block macros become 14 components), the gallery and the deck family pages as Astro pages over
    `presentations/` and `facts.yaml`, the design twins and the dashboard through `publicDir`, the 44 legacy redirects
    as an `astro.config` map (kept; no sunset), fonts through `@fontsource`; Pagefind indexes the whole artifact;
    `/llms.txt`, `/llms-full.txt` and `/facts.json` exist; every dossier stat with `check:` is computed at build and
    every page carries a built-from footer; `/status/runs/` (`marshal status --format json`, `herald progress --json`)
    and `/changes/` (a 30-day merge-subject window with RSS until a CalVer tag exists) land; `build.py`,
    `assemble_pages.py`, the Jinja templates and `docsite/` retire, the dossier content moving to
    `docs-site/src/content/dossier/` and the herald pages to `docs-site/src/pages/herald/`, so the `docsite` /
    `docs-site` name clash ends without a rename story. Done when `docsite/` is gone and the bespoke Python under
    `docs-site/` is under 300 lines.
  - **The Claude-artifact render stays and is refreshed.** `herald/artifact/dossier.html` republishes "The PyForge
    Dossier" (`claude.ai/artifact/RcpHNycoHqxv98YCmV8Zmt`), last refreshed 2026-09-13 until this session republished it
    on 2026-10-13; the refresh is a session-close ritual line in `docsite/README.md` now and a scheduled routine once
    the stats are computed.

  **Placement rule (binds every future surface; amends AD-21):** dynamic, authenticated or per-user → Lane 1
  `/console/`; static, public and build-time → Pages. Pages renders only tracked files and public API JSON, never
  Tier-3, Lane 1 data or warden findings. Applied the same day: MyBMAD (`bmad-code-org/bmad-method-ui` `web/`: Next.js
  `output: "standalone"`, PostgreSQL + Prisma, Better Auth sessions, Server Actions, API routes) cannot run on Pages,
  and an iframe to its hosted instance is a cross-origin load AD-21 forbids; it may run as a Lane 1 sidecar; its Pages
  twin is the fleet board. New sections take new prefixes (`/status/`, `/changes/`); `/dashboard/kedro-viz/` keeps its
  URL and Vizro boards go beside it under `/dashboard/vizro/`.
  **Constraints:** one `deploy-pages` caller; zero third-party origins (AD-21); `docs/` never moves; the five vendored
  files under `docs-site/` stay hash-pinned to upstream; every Pages capability stays `mode: rebuild` for the foundry;
  Actions minutes are budget; no bot commits on `main`.
  **Kinships:** [[pyforge-steward]] (the duct: `pages.yml`, the budget, the CI-surfaces registry row, `ledger-query`),
  [[pyforge-atlas]] (the Kedro-Viz producer artifact, Vizro static boards), [[pyforge-doctor]] (`map.yaml` orders the
  whole site, a liveness probe), [[pyforge-marshal]] (`status --format json`), [[pyforge-unifying-strategy]]
  (`fnd:CAP-14`: the dossier stays the cutover's control plane; the Actions budget). Owner `spec-pyforge-herald`
  (CAP-44, CAP-49, CAP-52, CAP-56 and CAP-58 amended; new CAPs for M2 and M3; M1 a fix). → CAP-60 / CAP-61, FR-12.1–12.5,
  AD-21 amended and AD-23 added; Epic 41 (fix) / 42 / 43, Stories 41.1, 42.1–42.3, 43.1–43.7, specced 2026-10-14; steward
  CAP-168 / Epic 102, atlas CAP-62–63 / Epic 30 and doctor CAP-90–91 / Epic 48 minted the same day on their own Dreams.
  Herald Epic 41 lands first, the steward surface move (102.1) opens M2.

- **2026-10-12 (the docs home leads to the herald pages) — Wanted: a reader who lands on the Pages root can reach the
  dossier, the infographics, the decks and the Kedro-Viz pipelines without knowing their URLs.** Since the unified
  Pages artifact (CAP-52, AD-21, 2026-10-08) the root is the Starlight docs shelf, and docsite's whole output moved
  under `/herald/`.
  - **The docs side.** The docs home's left menu has four groups (Tutorials, How-to, Reference, Explanation), and
    its top bar holds only the title, search and the theme toggle. Measured on the live site 2026-10-12, the root
    links only two how-to pages that mention herald. Nothing links `/herald/`, `/herald/dossier/`,
    `/herald/infographics/`, `/herald/decks/` or `/dashboard/kedro-viz/`.
  - **The herald side.** Herald's own top menu (Overview, Dossier, Infographics, Decks, Kedro-Viz, from
    `docsite/content/site.yml`) has no way back to the docs.
  - **What the operator saw.** The site "is now docs", and everything else looked gone.

  **What it looks like when real:** the docs left menu gains a fifth first-level group, **Herald**, linking
  Overview, Dossier, Infographics, Decks and Kedro-Viz. Every docs page and every herald page carries the same top
  menu: Docs, Overview, Dossier, Infographics, Decks, Kedro-Viz. Both menus come from one list in
  `docsite/content/site.yml`, so a new herald page appears in both places at once. Every link resolves under the base
  path of whichever host built the artifact (CAP-56's second host included). **Constraints:** a feature under the
  docs-site capability. The quadrant order still comes from `docs/map.yaml`, and the Herald group follows it.
  `pages-check` and the docs validators stay the gates. No page moves, and nothing under `/herald/` changes path.
  Operator rulings 2026-10-12: layout "Sidebar group + top menu (Recommended)", group name "Herald (Recommended)", the
  chain shape "Seed on herald Dream (Recommended)" ("this should be its own dream seeds, dream to code chain"), and
  the SPEC.md render route "Yes, script-render (Recommended)". Owner `spec-pyforge-herald`. → CAP-58 / Epic 40 /
  Story 40.1, specced 2026-10-12.
- **2026-10-12 (ci surfaces on the dossier) — Wanted: the dossier says which CI surfaces are paused or stuck, from the
  same JSON the steward CLI prints.** Today the dossier (`docsite/content/dossier.yml`) shows the A→B cutover and
  nothing about the pipeline that lands it: two container-build pauses live since 2026-10-04 and 2026-10-09, six
  workflows disabled by hand since 2026-08-24, and this station's own `dashboard.yml` deploy stuck in `waiting` from
  2026-10-06 to 2026-10-12 (199 cancelled runs, a six-day-old Pages build) were visible nowhere a reader looks.
  Steward's same-day append mints the registry (`docs/governance/ci-surfaces.yaml`) and `pyforge steward ci status
  --json`; doctor's mints the drift source; the plan is `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md`.
  **What it looks like when fixed:** one dossier tile, "CI surfaces", rendered from `steward ci status --json` at
  build time: one line per surface whose verdict is not `live` — switch, `paused_since`, `review_by`, owner, verdict —
  and a single "all live" line otherwise; the tile is data-driven (a fixture JSON renders it in the docsite check),
  never hand-edited; and `dashboard.deploy` carries its registry row with the `stuck_rules` that would have caught
  2026-10-06. **Constraints:** a feature under CAP-11 (the progress visibility surface); behind a flag
  (`pyforge.herald.ci_surfaces_tile` proposed); reads steward through the CLI's JSON, never by import; depends on
  steward's `ci status` landing first; `docsite-check.yml` stays the gate. Operator ruling 2026-10-12: the plan's
  recommended answers Q1–Q8 stand. Owner `spec-pyforge-herald`. → CAP-59 / FR-11.1 / Epic 39 / Story 39.1,
  specced 2026-10-14 (entry of that date below).
- **2026-10-11 (django-herald lint clean) — Ruled: the django-herald portal passes the lint gate and is the first
  package off its not-yet-clean list.** Story 37.1's review found that no gate lints the `django-*` portal packages:
  `lint-types` globs only `pyforge-*`, and `platform-ci-local` lints only `src/platform`. django-herald's
  `pyproject.toml` has no `[tool.ruff]` table, so a hand run of the guild ruff (0.16.9) falls back to its own default
  rule set and reports 17 findings on `2b5e0d649b`: eight unused `noqa` directives (RUF100), four unsorted import
  blocks (I001), one unused import (F401, `deck_twin_routes.py:8`), one TRY004 and one DTZ007
  (`deck_export_sync.py:18`, `:34`) and two RUF012 in the generated migration. The operator's request, verbatim: "Do
  this task here: Lint django-herald package and add it to a gate". Asked how wide to go, the operator chose, verbatim
  label "Gate all, clean herald (Recommended)": "Two stories. Steward's story extends lint-types to every django-*
  package and adds an explicit 'not yet clean' list that can only shrink. Herald's story clears django-herald's 17
  findings and takes it off that list. The other stations follow later as their own fix stories." **What it looks like
  when real:** once steward Story 93.1 has put the nine portal packages under `lint-types`, each with its own
  `[tool.ruff]` table, django-herald checks and format-checks clean under that table and leaves the not-yet-clean
  list, so any new finding in it fails the gate. Under that table its inventory is five check findings (the four I001
  and the F401) and three files to reformat (`deck_viewer.py`, `herald_guard.py`,
  `management/commands/refresh_deck_exports.py`). The other twelve of the 17 are each cleared or recorded with a
  reason. With herald installed the portal behaves exactly as before. **Constraints:** lint-only edits inside
  django-herald and the one list entry; no blanket ignore; the route files Story 37.1 kept unedited may now change for
  lint only; the generated migration is never hand-edited. One `fix` story, no CAP, no flag. Its ledger key is
  minted `blocked` on steward 93.1 (a cross-station gate, which marshal's station-local `Deps:` parser cannot see);
  the operator flips it once 93.1 is `done` on `main`. Owner `spec-pyforge-herald` (CAP-55, the capability that names
  the django-herald portal, with CAP-54 for the deck-export files). → Epic 38 / Story 38.1, specced 2026-10-11.
- **2026-10-11 (portal without herald) — Ruled: the herald portal stops taking the host's Django pages down when
  herald is absent.** Story 19.2's landing review found a high defect outside its scope (`DW-herald-19-2-1`, recorded
  when 19.2 landed as PR #2123, merge `ba613abab3`). The django-herald portal imports `pyforge.herald` at module load:
  `src/platform/config/urls.py:40` includes `django_pyforge.urls`, whose AppConfig discovery (`:14`-`:17`) includes
  `django_herald_portal/urls.py`. Its `:3` imports `views.py`, whose `:10` imports `deck_viewer.py`, whose `:9` reads
  `from pyforge.herald.deck_twins import NotFound, iframe_twin_path` (Story 30.2, `7cde96b702`). Its `:11` reaches a
  second module-level herald import through `deck_twin_routes.py:8`-`:9`. `platform-dev`, where 19.2's host runs,
  carries no herald, so the URLconf cannot load there:
  - `manage.py check` exits 1 with `ModuleNotFoundError: No module named 'pyforge.herald'` (reproduced 2026-10-11 on
    `origin/main` `2a725c113f` and again on `baf4779b6d`). `manage.py migrate` stops in the same system check; 19.2's
    how-to works around it with `--skip-checks`.
  - Every page Django serves (`/`, `/stations/`, `/stations/herald/`, `/cms/`) answers 500. The webhook forward is
    unaffected, because `config/asgi.py:135` routes it before Django resolves a URL.
  - Steward Story 87.1's contract, "the host boots without herald", holds for the station API only. Its test imports
    `config.asgi` and drives the API, and Django resolves the URLconf only at a system check or a page request, so
    the test never reached the portal.

  The operator was asked: "Herald 19.2's review confirmed a high defect outside its scope (now DW-herald-19-2-1). The
  django-herald portal imports `pyforge.herald` at module load (deck_viewer.py:9, from Story 30.2). So on the
  `platform-dev` host (no herald), `manage.py migrate` fails its URL check, and `/`, `/stations/`, `/stations/herald/`
  and `/cms/` answer 500. That breaks steward 87.1's "host boots without herald" contract for Django pages; the webhook
  forward is unaffected. How should I handle it?" The operator chose on 2026-10-11, verbatim label "Mint a herald fix
  story (Recommended)": "Herald chain: Dream entry, a fix story in a new herald epic. It guards the portal import or
  skips mounting the herald portal when herald is absent, mirroring 87.1. The test: under an env without herald,
  `manage.py check` passes and `/stations/` answers 200. Then dispatch it." **What it looks like when real:**
  - **The host checks clean without herald.** Under `platform-dev`, `manage.py check` exits 0 and `manage.py migrate`
    needs no `--skip-checks`. The how-to's workaround note goes.
  - **The host's Django pages answer as they do with herald installed.** Measured 2026-10-11 on a fresh test database
    with herald present (`platform-ci-test`, anonymous client): `/` 200, `/stations/` 404 (the Wagtail catch-all; no
    page has that slug), `/stations/herald/` 403, `/cms/` 302 to the login. The ruling's test names `/stations/`
    answering 200, but no env answers that today. The story pins `/` at 200 and `/stations/` at its with-herald status,
    never a 5xx. A 200 at `/stations/` would need a stations index page, which is a separate decision.
  - **The portal says why, once.** As in 87.1, the herald portal's pages are skipped with one logged reason. The
    decision is taken once, when the URLconf loads, and every `/stations/herald/` path answers 404 with that reason.
    The app stays installed, so its models, migrations and MCP mount do not move.
  - **With herald installed, nothing changes.** The deck list and viewer pass their Story 30.2 tests unedited.
  - **Constraints.** Herald's code only: the django-herald portal, a herald meta-test that pins the import boundary,
    one platform test, the how-to's note and the `DW-herald-19-2-1` row. `src/platform/` never imports `pyforge.*`
    (pap:AD-2). `config/`, the settings and `django-pyforge`'s discovery are untouched. One `fix` story, no CAP, no
    flag. `Deps: S-19.2` (done on main 2026-10-11): the story closes 19.2's deferral row and drops its how-to note.

  Owner `spec-pyforge-herald` (CAP-55: Story 30.2 added the import). → Epic 37 / Story 37.1, specced 2026-10-11,
  `Deps: S-19.2`.
- **2026-10-10 (live backend, via the sidecar) — Ruled: the ship lands on the platform host, and herald's webhook runs
  in steward's mcp-host sidecar.** The local-host ruling (two entries down) put the host on
  `pyforge-foundry-full-stack`, which cannot import it (`config/celery_app.py:4`, no `celery`), and steward's Story
  87.2 that would have fixed that is retired. The image env cannot hold herald either: herald's run-dep
  `mcp >=2.2.0` meets langflow-base and lfx 1.12.x's `mcp <2.0.0`. The operator chose, verbatim label "Via the sidecar
  (Recommended)": "Mint a steward story: mcp-host env gains pyforge-herald; the sidecar mounts herald's webhook ASGI;
  the host forwards /stations/herald/api/v1/webhooks/* to MCP_HOST_SIDECAR_BASE_URL like MCP. 19.2's proof runs host +
  sidecar locally (loopback). 87.1 stays (host never imports herald); 87.2's full-stack composition can be dropped."
  **What it looks like when real:** the platform host runs from `platform-dev`, rendered by `steward deploy perimeter`
  and bound to loopback; herald's webhook, its HMAC check and its SQLite store run in the mcp-host sidecar
  (`mcp-host-serve`, `127.0.0.1:8090`); the local caller posts to the host, which forwards; a restart of both keeps the
  record. **Constraints:** herald's code changes only by the caller; the sidecar is steward's process, not a herald
  one, and no port is public; AD-14 and AD-13/AD-17 as built hold. Owner `spec-pyforge-herald` (CAP-38, CAP-39). →
  Story 19.2, re-scoped again 2026-10-10 and `blocked` on steward Story 87.3
  (`87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar`); it flips `blocked -> backlog` once 87.3 is
  `done` on main.
- **2026-10-10 (live demo archive) — Ruled: `herald-live-demo.yml` moves to the archive once Story 19.2 closes.**
  The workflow reads `disabled_manually` (Actions API, 2026-10-10), and its last run was on 2026-08-24. Two of its
  three jobs start a standalone `pyforge.herald.webhook_host:application` under daphne
  (`.github/workflows/herald-live-demo.yml:162`, `:267`), the per-station process 19.2 rejects. All three use a
  `runner.temp` store (`:157`, `:262`, `:385`), and the webhook jobs need a repository secret (`:41`). Once 19.2 proves a ship on the local host, the workflow proves nothing the estate still needs, yet live files
  keep it in place:
  - the pixi version registry (`scripts/pixi_version_registry.py:82`, its three pins), which `bump-pixi-version`
    rewrites;
  - doctor's live-proof catalog row (`spec-pyforge-doctor/live-proof-surfaces.md:28`) and its test exception
    (`test_sources_live_proof_surfaces.py:459`);
  - the two workflow inventories;
  - herald's own docs and docstrings;
  - the `bump-pixi-version` description in `pixi.toml` (`:1244`), which lists sites by name.

  The operator chose on 2026-10-10 ("Archive after 19.2"): "Mint a herald fix story now (Deps: S-19.2): git mv to
  archive/.github/workflows/, repoint doctor's catalog row and test exceptions, drop the pixi_version_registry entry,
  update inventories/docs, generalise the bump-pixi-version description; reconcile doctor/herald/core specs." **What it
  looks like when real:**
  - **The file** sits at `archive/.github/workflows/herald-live-demo.yml`, moved by `git mv` and byte-identical.
    CHAIN-STANDARD §11 says "Nothing is deleted; every move is a `git mv`". GitHub reads only `.github/workflows/`, so
    the workflow is gone from Actions.
  - **Its readers follow the move.** Doctor's *Live webhook host* row proves the host through 19.2's how-to, the
    `herald-ship-local` task and the opt-in `HERALD_LIVE_WEBHOOK=1` smoke test, with no workflow in its globs or in
    the test's exceptions. The registry has no site for it, and `pixi-version-check` passes. The inventories and
    herald's docs name the archive path or nothing. The `bump-pixi-version` description says "every site in the
    registry" and stops listing sites, so it cannot go stale again.
  - **Constraints.** This supersedes the 2026-10-10 (live backend, local host) entry's "stays disabled and unchanged",
    but only from 19.2's close; until then that constraint, Epic 19's HARD boundary and 19.2's Never list hold. One
    `fix` story, no CAP, no flag. Epic 19 closes when 19.2 lands, so the story opens a new epic. Historical planning
    files and `pixi.toml`'s dated 2026-08-21 `requires-pixi` comment keep their mentions. The `pixi.toml` edit brings
    the reconcile of every Spec that governs it, plus every station suite.

  Owner `spec-pyforge-herald` (CAP-38 ← LB-2: Story 13.6 shipped the workflow). → Epic 36 / Story 36.1, specced
  2026-10-10, `Deps: S-19.2`.
- **2026-10-10 (live backend, local host) — Ruled: a ship records itself on this machine's local stack, not
  foundry-side.** Epic 13 is `done` and a ship has never recorded itself. Story 19.2 sat `blocked` on DW-13-6-1:
  `steward deploy perimeter` renders a hardcoded `myproject.asgi:application` (`steward/deploy.py:539`) and has no
  `--asgi-application` flag. The 2026-09-09 readiness pass (batch row C11) parked the hosting half `foundry-side`,
  waiting for the cutover to give Herald a perimeter. The operator chose option 1 on 2026-10-10 ("go with option 1,
  local host"): "Mint a small steward fix that adds `--asgi-application` to `deploy perimeter`. Then re-scope herald
  19.2 so its host and store are this machine's local stack: `pyforge-foundry-full-stack` with PostgreSQL 17. No
  public endpoint, nothing outside the repo. Herald Epic 19 then closes, and 49.11 flips to done." **What it looks like
  when real:**
  - **Host.** The platform's one ASGI host (`config.asgi:application`) runs under daphne from
    `pyforge-foundry-full-stack`, bound to `127.0.0.1`, on its local PostgreSQL 17. It is started from the line
    `steward deploy perimeter --asgi-application` renders, and herald's routes reach it through Story 19.1's seam.
    There is no standalone herald process: AGENTS.md says no `:800x` process tree, and AD-14 as built says no bespoke
    Herald perimeter.
  - **Store.** Herald's records stay in SQLite at the primary checkout's ignored `.herald/herald.db`. `db.py` has no
    PostgreSQL backend, and the spine closed that choice. PostgreSQL 17 is the host's database, not herald's store.
  - **Proof.** One real landing on `origin/main` is delivered by a local caller as signed `on-ship` and `on-pr-close`.
    Its Progress record and draft claim survive a restart of the host, and the run is transcribed into a tracked proof
    file.
  - **Constraints.** The secret stays local. `herald-live-demo.yml` stays disabled and unchanged: three other
    surfaces govern it, and its `runner.temp` store can never be the proof. No CAP, no flag (the spec is pre-rule). One
    residual is recorded: FR-7.1's "CI notifies Herald" stays open, because a loopback host has no public endpoint for
    CI to call.

  Owner `spec-pyforge-herald` (CAP-38, CAP-39; AD-14, AD-13/AD-17 as built). → Story 19.2, re-scoped 2026-10-10; it
  stays `blocked` on the steward story that closes DW-13-6-1 (key `86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`), and the ruling
  pre-authorises the one flip, "flip 19.2 blocked -> backlog when the steward story that closes DW-13-6-1 is done on
  main".
- **2026-10-08 (native pptx tokens) — Found: the native `.pptx` export reads no design token.** The spine's AD-5 and
  its PPTX Generation invariant say every PPTX takes its fonts, colours and spacing from the design tokens, never
  hardcoded. Story 32.1's driver, `node/pptx_native.mjs`, sets `LAYOUT_16x9` (`:22`), hardcodes every offset and box,
  and hardcodes its font sizes, 32 pt for the title (`:33`), 18 pt for bullets (`:40`) and 14 pt for tables (`:45`). It
  names no face and no colour, so pptxgenjs-plus's defaults apply. `pptx_native.py` passes it no token. The spine's
  § Currency reconciliation — 2026-10-08 recorded this gap and left it for a fix story. One more finding: the file the
  spine names, `design-tokens.json`, does not exist, and no commit has ever held one (`git log --all` is empty). The
  Modernist tokens herald binds every deck to (`MODERNIST_DESIGN_SYSTEM_ID`, `transport/base.py:113`,
  `deck_pipeline.py:256`) are tracked under `presentations/_design-systems/modernist/`. `theme.json` holds the palette
  and the font families. The deck template's custom properties (`templates/deck/index.html:16-26`) hold the type scale
  and the slide padding, on a 1920×1080 canvas. **What it looks like when fixed:** the driver takes every font face,
  font size, colour, offset and padding from those Modernist tokens, scaled to the slide. A changed token value
  changes the export, and a missing token file stops the export with a named error. **Constraints:** a `fix`
  story, no CAP, no flag. No second token file, the Marp and pptx-fill exports do not change, and no file under
  `presentations/` changes. Owner `spec-pyforge-herald` (CAP-57, FR-10.6; AD-5; AD-3 as amended). → Epic 32 /
  Story 32.3, specced 2026-10-08.
- **2026-10-08 (native pptx notes) — Found: the native `.pptx` export drops multi-line speaker notes and most body
  text.** In Story 32.1's parser (`pyforge.herald.pptx_native`), a comment is a note only when it opens and closes on
  one line (`:101`). The lines of a `<!--` block fall to the body loop, which keeps images, the first heading, the last
  table and `-`/`*` bullets (`:121-143`) and drops every other line. The slide model has no field for body text
  (`:35-41`), and the driver draws only the title, bullets, a table, images and notes (`node/pptx_native.mjs:24-57`).
  Measured on `8a2da2c010` with the parser itself over the 15 current Marp decks (263 slides): 101 note comments, 50 of
  them multi-line, all 50 in `agentic-sdlc`, and none of those 50 reaches the export. 410 paragraph lines, 26
  numbered-list lines, 109 headings after a slide's first, 12 fenced code blocks and 10 inline-HTML lines are dropped.
  FR-10.6 says the export carries a deck's notes; the PRD's § Currency reconciliation — 2026-10-08 recorded the gap and
  left it for a fix story. **What it looks like when fixed:** every note, single- or multi-line, lands in its slide's
  notes, and every text block on a slide becomes text on the native slide, in source order. A fixture deck proves both
  through python-pptx, and a measure over the 15 decks finds nothing dropped. **Constraints:** a `fix` story, no CAP,
  no flag (the verb stays behind `pyforge.herald.deck_export_native`). The Marp and pptx-fill exports do not change.
  Owner `spec-pyforge-herald` (CAP-57, FR-10.6; AD-3 as amended). → Epic 32 / Story 32.2, specced 2026-10-08.
- **2026-10-08 (Pages fonts) — Found: every herald page on the public Pages site loads Google Fonts.** Story 31.1's
  cross-origin check (on its dispatch branch, not on `main`) finds 135 references on the real artifact, all under
  `/herald/`, in 45 pages. Each page has one stylesheet from `fonts.googleapis.com` and two `rel="preconnect"` hints, to
  `fonts.googleapis.com` and `fonts.gstatic.com`. Herald's own scanner, `pyforge.herald.twins.scan_tree`, finds the same
  135 in a `docsite/build.py` build of `8a2da2c010`. Two kinds of source emit them. The docsite shells
  (`templates/shell_page.html.j2:13-15`, `templates/shell_artifact.html.j2:6-8`) load Big Shoulders Display, IBM Plex
  Sans and IBM Plex Mono in 15 pages. The 30 Design-twin pages that `build.py` publishes as copies (the ten posters and
  each deck's Infographic Deck and Executive Summary, from `presentations/<slug>/project/`) carry their own Archivo and
  Archivo Expanded links. AD-21's 2026-09-28 amendment says no stylesheet or font in the artifact names another origin,
  so FR-10.5 cannot hold on any host while these remain. **What it looks like when fixed:** the faces are self-hosted
  under the docsite's assets, each recorded with its source, version, licence and sha256. The shells and the published
  copies point at them, both preconnect hints are gone, and a check fails the build when a herald page names another
  origin. **Constraints:** a `fix` story, no CAP, no flag. The Design twins under `presentations/` are not edited; only
  their published copies are. The vendored Kedro-Viz bundle under `/dashboard/` is out of scope. Operator decision
  2026-10-08: this lands before Story 31.1. Owner `spec-pyforge-herald` (CAP-56, FR-10.5; AD-21 as amended).
  → Epic 31 / Story 31.3, specced 2026-10-08.
- **2026-10-08 (docs-site helper) — Found: the docs site cannot build from a clean checkout, because its URL helper
  was never tracked.** `docs-site/astro.config.mjs:4` imports `./src/lib/site-url.mjs`, and `docs-site/README.md:26`
  lists that file as copied from upstream. The root `.gitignore` rule `lib/` (`:40`, a Python-packaging ignore) also
  matches `docs-site/src/lib/`: `git check-ignore -v` prints `.gitignore:40:lib/`, and `git log --all` finds no commit
  that ever held the file. Story 27.1's dispatch built green because the file sat untracked in its worktree; its
  auto-checkpoint (`773f656f03`) and its landing (`c47bbb99e4`, 2026-10-05) left it behind, and no worktree of this
  repository holds it now. Measured on `054bb4e795`: in a fresh clone, `pixi run -e site docs-site-build` exits 1 at `[astro] Unable to
  load your Astro config` ("Failed to load url ./src/lib/site-url.mjs"). With upstream's `docs-site/src/lib/site-url.mjs`
  in place (`bmad-code-org/BMAD-METHOD` at the recorded commit `561eeedf38`, 1032 bytes), the same build exits 0 and
  writes 64 pages. So FR-8.1 and AD-21 hold on no checkout, and Stories 27.2–27.4 build on a site that does not build.
  Nothing catches it: `tests/meta/test_docs_site.py` checks the symlink, the Node pin and the vendored hashes, never
  whether the config's imports are tracked; herald's CI job does not run on `docs-site/**`; and no lane builds the
  site yet. The 2026-10-07 retro, PRD and spine recorded the gap and left it for a fix story. **What it looks like when
  fixed:** the helper is tracked, byte-identical to upstream, with its sha256 in `docs-site/README.md`'s vendored
  table; a narrow `.gitignore` exception admits `docs-site/src/lib/` and the general `lib/` rule stays; a herald meta
  test fails when any relative import in the docs-site sources resolves to a path git does not track; herald's CI job
  runs on `docs-site/**`; and a fresh clone builds. **Constraints:** a `fix` story, no CAP, no flag. Re-vendor, never
  fork (AD-21 rule 5, D6). No page under `docs/` changes, and the only workflow edit is herald's trigger. Owner
  `spec-pyforge-herald` (CAP-52, FR-8.1, AD-21; Story 27.1 shipped the site). → Epic 27 / Story 27.6, specced
  2026-10-08.
- **2026-10-03 (night) — Found: Story 35.1 landed with two rows closed on thin evidence.** It auto-landed after
  its send-back pass, before a landing review. The docs-site check has tests for 4 of its 15 problems, the sync-proof
  row closed on a speculative normaliser and a tautological hash branch, and the act vocabulary, a README sentence and
  one row's closure record were left wrong. **What it looks like when fixed:** each check fails a test when broken, the
  sync-proof row stays open until a live proof exists, and the records read true. Fix story, no CAP, no flag. Owner
  `spec-pyforge-herald`. → Story 35.2, specced 2026-10-03.
- **2026-10-03 (Phase 4+5) — Ruled: herald's open medium and low deferrals close in one fix story.** The
  operator ruled on 2026-10-03 that the deferral burn-down's Phase 4 (open medium rows) and Phase 5 (open
  low rows) run together on the idle station lanes, then, the same day, that each station takes exactly
  one story. Herald carries 6 open medium and 15 open low rows (measured with a parser over its
  `deferred-work-ledger.md`). **What it looks like when fixed:** `list_files` reads the live server's
  answer; `deck sync-all` proves a standalone poster push instead of refusing it; `deck-trio` derives all
  ten PyForge posters; `docsite/build.py` has unit tests; an ambiguous layout name is refused; the eleven
  recommended follow-up reviews of ten landed stories have run and their findings are fixed; three rows
  whose fix already landed are closed citing the line that holds it. **Constraints:** a `fix` story, no
  CAP, no flag; a row closes only with a `resolution:` and a cited `verified:` line; the one open high row
  (DW-21-7-1, the corrupted standalone poster on the live Design project) is outside these phases.
  Owner `spec-pyforge-herald`. → Epic 35 / Story 35.1, specced 2026-10-03.
- **2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from
  an internal Pages site, and each current export is also kept in object storage.**
  Source: the intake `archive/docs/intake/airgapped_pptx_architecture_specification.md`, triaged
  2026-09-28 under operator rulings. The intake describes an implementation: python-pptx writes
  into a PostgreSQL `BYTEA` column, a Django view streams it with a hard-coded CORS origin, and
  PPTXjs renders it in a Wagtail template and on a GitHub Enterprise Pages page. The need behind it
  is smaller. People inside the enterprise airgap read a deck in the browser without PowerPoint,
  from the django-herald portal and from an internal GHE Pages site, and git stops being the only
  place the exports live.
  **Measured 2026-09-28** on `306d7563fd`:
  - 57 tracked `.pptx` hold 121,976,204 bytes.
  - Every standard `.pptx` export comes from `marp --pptx` (`scripts/deck_export.py`), which
    writes image-only slides, needs Chrome, and runs in `-e local-recipes`.
  - 14 decks carry React/JSX sources. Their `dist/` bundle is gitignored.
  - `src/platform/config/object_storage.py` says "No existing feature is wired to consume this
    seam yet".
  - No in-browser `.pptx` viewer exists. Deck visual QA screenshots the React bundle, not the
    `.pptx`.
  - `pptxgenjs-plus >=4.2.1` is packaged (`recipes/pptxgenjs-plus`) but sits only in the
    `local-recipes` environment. `django-cors-headers` is in no environment.
  **Operator rulings 2026-09-28:**
  1. Decks stay tracked. CAP-53 still prunes superseded exports, and AD-4 does not change. Each
     current export is *also* published to the object store with a metadata row.
  2. The viewer shows Herald's own decks through their HTML twins, meaning the Marp HTML and the
     React bundle. No browser-side `.pptx` parser.
  3. `pptxgenjs-plus` becomes an *additional* export kind, native and editable `.pptx`, beside
     `marp --pptx` and the python-pptx fill. Neither of those retires.
  **Rejected, with reasons:**
  - Bytes in PostgreSQL: the platform's blobs go to consumed S3 (the dated 2026-09-10 exception
    in `spec-pyforge-unifying-strategy` AD-1; `spec-pyforge-steward` CAP-94..97), and the
    database belongs to the enterprise DB team.
  - PPTXjs: its last release was 2022-03-26, it bundles jQuery 1.11.3, and it needs JSZip v2.
  - `pptxgenjs-plus` as the viewer: it generates decks and does not render them.
  - An unauthenticated stream with a fixed CORS origin: the portals require OIDC and a station
    role, and station routes live under `/stations/herald/api/v1/`.
  - A second Pages *artifact*: AD-21 keeps one.
  **What it looks like when real:**
  - `herald deck publish <slug>` puts each current export's bytes in the object store under a
    sha256 key. It records topic, kind, date, size, content type and source commit.
  - The django-herald portal lists a deck and shows it in the browser from its HTML twin. The twin
    is served from the store with vendored assets and zero CDN references.
  - The same docsite artifact deploys to a second host, an internal GHE Pages site. It is built
    statically, so no browser calls the platform cross-origin.
  - A `pptxgenjs-plus` export kind writes a native `.pptx` from the Guild environment.
  **Constraints:**
  - Git stays the archive of record ([[design-sync-loop]]), and CAP-35's downloads still build
    from tracked files.
  - `src/platform/` never imports `pyforge.*`.
  - There is no new package path.
  - Every new capability here carries a flag block, under the Guild Dream
    [[feature-flag-governance]] seeded the same day.
  **Kinships:**
  - steward: the object-storage seam's first consumer ([[pyforge-steward]], same day).
  - This station: CAP-35, CAP-52 (the docsite and its `/herald/` mount), CAP-53 (Epic 28), AD-4
    and AD-21.
  - mason: the `pptxgenjs-plus-jsx` recipe ([[pyforge-mason]], same day).
  - warden: vendored JavaScript is scanned like any other dependency.
  Owner: herald. → CAP-54 / Epic 29 / Stories 29.1–29.2 (FR-10.1–FR-10.2); CAP-55 / Epic 30 /
  Stories 30.1–30.2 (FR-10.3–FR-10.4); CAP-56 / Epic 31 / Stories 31.1–31.2 (FR-10.5); CAP-57 /
  Epic 32 / Story 32.1 (FR-10.6), specced 2026-09-28. Stories 29.1 and 29.2 are minted `blocked`
  until steward Story 74.1 (the seam's first-consumer contract) lands.
- **2026-09-28 — Each deck keeps one current version of each export; git keeps the rest.**
  Source: the steward Dream's 2026-09-25 seed, [[pyforge-unifying-strategy]] § Realization log,
  "`local-recipes` repo-size measurement". It proposed "latest deck per topic" and deferred the
  idea to the cutover's parked Story 44.5. Operator ruling 2026-09-28: spec it now, independent
  of the cutover. Keep the latest deck per topic in `presentations/`, and prune or move the older
  dated versions, because git history keeps them.
  **Measured 2026-09-28** on `c660efec81`:
  - `presentations/` holds 944 tracked files, 134.69 MB, which is 47.0% of the 286.5 MB tracked
    tree.
  - Dated exports live under `presentations/<topic>/src/{pptx,marp}/` and are named
    `<stem>-YYYY-MM-DD.<ext>`. They form 118 kinds, where a kind is a directory plus a stem plus
    an extension. 62 kinds carry more than one date.
  - That leaves 74 superseded files (26 `.pptx`, 36 `.md`, 12 `.html`), 54.14 MB in all, across 11
    topics:
    - `agentic-sdlc`: 2 files, 12.74 MB
    - `pyforge-atlas`: 12 files, 11.36 MB
    - `pyforge-unifying-strategy`: 6 files, 10.46 MB
    - `pyforge-marshal`: 11 files, 5.18 MB
    - `pyforge-genesis`: 6 files, 3.87 MB
    - `steward`, `mason`, `scribe`, `herald` and `doctor`: 6 files each, 1.75–1.83 MB each
    - `pyforge-warden`: 7 files, 1.56 MB
  - Pruning them leaves 870 files and 80.55 MB, and the tracked tree drops to about 232 MB.
  - Command: `python3 -c "import re,pathlib,collections as c;g=c.defaultdict(list);[g[(p.parent,m[1],m[3])].append((m[2],p.stat().st_size)) for p in pathlib.Path('presentations').rglob('*') if p.is_file() and (m:=re.match(r'(.+)-(\d{4}-\d{2}-\d{2})(\.\w+)$',p.name))];o=[s for v in g.values() for d,s in sorted(v)[:-1]];print(len(g),sum(len(v)>1 for v in g.values()),len(o),sum(o)/2**20)"`.
  - "Latest" already has one meaning in the repo: `docsite/build.py` `_listed_files`,
    `deck_pipeline._newest_dated_match`, `deck_export.find_source` and `deck_facts._marp_source`
    each pick the newest date per kind. So the 69 family-page downloads and every Design push
    are already the files that would be kept.
  - Every writer adds a new dated file and none removes the old one (`pull_marp_source`,
    `pull_standalone_bundle`, `PptxTemplateExporter.export`, `deck_export.stamp_marp_kinds`). A
    one-time prune would therefore regrow.
  - The prune shrinks the working tree and anything that copies it. It does not shrink `.git`.

  **Kinships:**
  - steward: `spec-python-foundry-cutover` Story 44.5 (parked) inherits a minimal deck tree.
    Story 59.4's `deck-drift` duty fingerprints the one pulled Design artifact passed as `--path`,
    and so far that is only ever a `project/*.dc.html`. Its baseline is gitignored and exists on
    neither checkout, so it has nothing to re-stamp.
  - core: `spec-pyforge-core:CAP-8`, the station-tests lane. Herald's suite starts running on
    `presentations/**` changes.
  - doctor: `docs/how-to/presentation-deck.md`, which holds the naming convention.
  - This station's docsite: CAP-35's family pages. Their downloads do not change.
  - Story 19.4's pptx-fill exemplar. Its tests regenerate the deck instead of reading the
    superseded file.

  Status: **specified** (2026-09-28). → CAP-53 / Epic 28 / Stories 28.1–28.2. Epic 28 is new,
  because Epic 27 belongs to CAP-52.
- **2026-09-20 (later) — Herald's deck pipeline runs from the Guild env, not the recipe factory.**
  `deck_pipeline.py` and `sync_all.py` shell `pixi run -e local-recipes deck-export | deck-facts |
  deck-trio`; only `pyforge-guild` exists at runtime (operator ruling, steward Dream 2026-09-20
  later). The three tasks move into `guild-tasks` with their deps in `pyforge-guild` (steward
  63.6 owns the env side) and herald's shell-outs name `-e pyforge-guild`. → CAP-51 / Story 25.1
  (Epic 25, new — 24 is `done`).
- **2026-09-20 — Proposed: the docs site matches BMAD-METHOD's pattern, so their skills and
  workflows apply unchanged.** Operator ask 09:55Z: *"design our docs and docs deployment to
  GitHub Pages to match what BMAD-METHOD itself does, so that we can reuse their patterns,
  skills and workflows."* What upstream does (verified, MIT): content stays in `docs/` (Diátaxis
  quadrants + `index.md`), `docs-site/` is Astro + Starlight reading `docs/` through a symlink,
  `sidebar.order` frontmatter with `validate-links` / `validate-sidebar` / `fix-links` scripts,
  hand-authored inlined SVG diagrams, and one `.github/workflows/docs.yaml` that builds with
  `npm ci` + `npm run build` and ships `build/site` through `upload-pages-artifact` →
  `deploy-pages`. What we have: this station's `docsite/` (dossier + infographics, Jinja2) and
  the Kedro-Viz dashboard sharing one Pages artifact via `dashboard.yml`; doctor's `docs/MAP.md`
  and, since 30.2, `docs/map.yaml`; no site for the shelf itself. Done ahead, because the
  `bmad-os-diataxis` skill reads it: `docs/_STYLE_GUIDE.md` vendored verbatim with provenance.
  Research: `planning-artifacts/research/docs-site-bmad-method-pattern-2026-09-20.md` — six
  decisions for `bmad-spec` (owner: herald for site + deploy, doctor's `map.yaml` as the sidebar
  source; one Pages artifact with the dossier and dashboard mounted beneath the Starlight site;
  Node via pixi; content moves nothing; validators become detectors; re-vendor never fork).
  **Kinships:** doctor 30.x (`map.yaml` ↔ `sidebar.order`), scribe 19.3 (instruction docs),
  `dashboard.yml`'s deploy-pages race note. Status: **specified** (2026-09-27) — `bmad-spec`
  adopted all six decisions as D1–D6 on the Spec memlog. Four were refined against the repo: the
  sidebar is generated from `map.yaml` at build time, not written into pages; the deploy workflow
  keeps its `dashboard.yml` path, reshaped to upstream's build and deploy jobs; `nodejs` joins the
  existing `site` feature; titles and quadrant indexes are resolved at build time. The operator's
  2026-09-27 rulings added two more. D7: the dossier site mounts under `/herald/`, and every old
  root HTML URL redirects there. D8: `pr-preflight` builds the site only when the docs change,
  selected from the workflow file itself. → CAP-52 / Epic 27 / Stories 27.1–27.5 (Epic 27, new —
  26 is `done`; 27.5 is `blocked` until steward Story 71.2 lands).
- **2026-09-18** — **Epic 23 drained to zero; what its four landings deferred.**
  The Design sync loop is real: 23.1 (`deck status` enumerates the whole account,
  PR #1459), 23.2 (every presentation twinned, three design systems mirrored
  byte-exact, #1461), 23.5 (family pages on Pages, #1463) and 23.6
  (`herald deck sync-all`, #1465) all landed today by `marshal factory dispatch`
  on the Claude harness — verified, merged and ledger-flipped without a human in
  the loop, 46–66 min each. Each dispatched session deferred exactly one thing it
  could not settle from inside its worktree, now twinned in the tracked ledger:
  **DW-FU-23-2** — `deck_pipeline._windowed_read` has no guard against a server
  that returns a non-advancing `last_line` (a real pagination-loop hazard; every
  live call paged forward, so reachability is unproven); **DW-FU-23-5** — no
  PR-gating CI lane runs `docsite/build.py` or `site-check`, and the station's
  verify command covers none of `docsite/`, so the family-page code (and the
  dossier/gallery/artifact code before it) can regress with every gate green;
  **DW-FU-23-6** — `sync-all`'s idempotency AC is proven over fakes and one live
  smoke of the skipped path only, never a seeded deck's unchanged path, because
  no dispatch environment has live Claude Design credentials. Those three are the
  residue of the Dream, not new dreams — a loop that can hang, a site that can
  regress unseen, and a "second run writes nothing" promise proven only on paper.
  Seeded as CAP-48..50 and decomposed the same day as Epic 24 (24.1..24.3);
  Epic 23 flips `done`. DW-FU-23-6's live half is an operator-run proof (it needs
  the credentials only a person has), so 24.3 is minted to make that proof a
  one-command, recorded act rather than a memory.
- **2026-08-02 (second pass)** — Folded [[herald-pitch]] (Moment 1 complete
  orchestration, 7 capabilities) into this Dream's narrative. Dream-level
  consolidation only — `spec-herald-pitch` and its 4 companions stay fully
  live and untouched; that Spec's own PRD/Architecture/Epics decomposition
  has not run yet, unlike Moments 2–4's chain (below), which already has.
- **2026-08-02** — Consolidated. Folded [[herald-moments-2-4-missing-surface]]'s
  vision into this Dream (single narrative for Herald's voice-and-visual
  scope); that Dream is now `archived` / `absorbed` — its own downstream
  chain (Spec, PRD, Architecture, Epics under
  `_bmad-output/projects/pyforge-herald/planning-artifacts/`) stays live and
  is the active execution reference for Moments 2–4, unchanged by this
  consolidation. [[fleet-chain-completeness]] (the orchestrated-regeneration
  workflow that had been filed here) was reassigned to `owner: marshal` the
  same day — it is machinery, not Herald's communication-surface scope.
- **2026-08-02 (station-level consolidation, later the same day, corrects the
  two entries above)** — Per an explicit user override of this repo's own
  same-day keep-chains-separate convention, both "stays fully live and
  untouched" / "unchanged by this consolidation" claims above are now
  **false**. The station's multiple Brief/PRD/Architecture/Spec chains were
  merged into one of each: `brief-herald-pitch-2026-08-01/brief.md`,
  `prd-pyforge-herald-2026-08-01/prd.md` (now also carrying the Moments 2–4
  PRD as a Satellite section), `architecture-herald-pitch-2026-08-01/ARCHITECTURE-SPINE.md`
  (now also carrying the Moments 2–4 architecture as AD-11..AD-20), and
  `spec-pyforge-herald/SPEC.md` (now also carrying `spec-herald-pitch`'s
  CAP-1..7 as HER-4..10 and `spec-herald-moments-2-4`'s CAP-1..3 as
  HER-11..13). Every folded-in source document is preserved, unmodified, at
  the mirrored path under `archive/_bmad-output/projects/pyforge-herald/…`
  (a rename, not a deletion — see git history for provenance if the
  `archive/` copy is ever removed). `product-brief-deckcraft.md` (+
  distillate, project-context, sprint-status, 3 research files) was
  investigated separately and found to be orphaned debris from an
  *already-completed* 2026-08-01 consolidation (`spec-deckcraft` folded into
  `spec-herald-pitch` CAP-2, now HER-5) whose own PRD/Architecture/Spec were
  archived at that time; it has been moved to the same `archive/` location
  as its siblings, not folded in as live station scope. Epics were
  deliberately left untouched by this pass (still Moments-2-4-only; see the
  note in "What is real" above).

- **2026-09-09 (fleet readiness pass — body re-grounded, status held)** — § *What is real*
  and § *The frontier* were both frozen at 2026-08-02 and understated the station by roughly
  sixty stories; both are corrected above with their superseded wording quoted. Herald now
  carries 18 epics and 64 story keys in `sprint-status-ledger.yaml`, all `done` except the
  `epic-18` roll-up row, which reads `backlog` while 18-1/18-2/18-3 are each `done` — a
  ledger roll-up defect, not outstanding work (folded into steward 48.1). **Status held at
  `realized`** for Moment 1 and the bridge. Three satellite Dreams do *not* clear the
  realization gate and say so in their own logs this date: [[herald-moments-2-4-live-backend]]
  (never run green), [[deck-visual-qa]] (gate has no caller) and [[pptx-deck-generation]] /
  [[pptx-custom-shapes]] (no real deck rendered). Herald **Epic 19 — "Herald in effect"** is
  minted as their single vessel (fleet-readiness decision batch 2026-09-09, row C6); steward
  Epic 49 carries the index row. One boundary claim is now pending elsewhere: this Dream's
  and the Spec's "the Guildhall is Marshal's ([[factory-console]])" cites a `superseded` Spec
  and a retired console — the referent is a Charter amendment (batch row C12), raised on
  `docs/governance/spec-pyforge-charter/.memlog.md` this date.
- **2026-10-14 (ci surfaces on the dossier, specced) — Ruled: the tile shows the steward's answer as it was
  captured, and says when it was captured.** Steward's status command landed on 2026-10-13 (steward Story 99.3,
  `pyforge-steward:CAP-166`), so the operator's order of that day holds: the doctor, herald and marshal readers are
  minted now, one chain each (`docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 5 and § 6).
  - **What changed since the seed.** The command reads GitHub live, and only for a signed-in reader with the
    steward's own switch on. The site's build is neither, and should not become one just to draw a tile. So the
    dossier cannot ask the command while it builds.
  - **What it looks like when real.** The operator captures the command's answer into the repository when a pause
    starts or ends. The dossier draws its "CI surfaces" tile from that captured copy: one line per surface that is
    not live, with its verdict, switch, since and review-by dates, and owner, or one "all live" line. The tile
    names the capture time, so an old copy reads as old, and a copy with the wrong shape fails the site check
    instead of drawing a quiet, empty tile. Herald shows the steward's verdict and never judges a surface itself;
    the doctor's drift source does the judging.
  - **Constraints.** Behind the proposed flag; off, the dossier is unchanged. Herald reads the steward only through
    the command's output, never its code. Whether the capture should one day refresh itself is the operator's call
    (it would need a token and an automated pull request).
  Kinships: [[pyforge-steward]] (`spec-pyforge-steward`, `pyforge-steward:CAP-166`: the status command and its
  frozen output), [[pyforge-doctor]] (the drift source that judges), the plan. Owner `spec-pyforge-herald`. →
  CAP-59 / FR-11.1 / Epic 39 / Story 39.1, specced 2026-10-14.
- **2026-10-14 (archivo-expanded) — Found: no React deck installs or builds from its lock, because Story 30.1 named a
  font package npm does not publish.** Story 30.1 (`697c985d25`, 2026-10-08) vendored the fonts of the 14 React decks
  under `presentations/` by adding `@fontsource/archivo` and `@fontsource/archivo-expanded` to 13 decks' `package.json`
  and nine `@fontsource/…` imports to each `src/main.jsx`, and regenerated no `package-lock.json`. Measured at
  `846d8383f5`: every one of the 14 locks has zero `@fontsource` entries, agentic-sdlc's included, whose three font
  packages are real. `@fontsource/archivo-expanded` is not on the registry: `npm view` and `npm install` answer E404,
  while `@fontsource/archivo` and `@fontsource-variable/archivo` are at 5.3.0. On HEAD's manifests, in scratch copies,
  `npm ci` exits 1 in pyforge-atlas (E404) and in agentic-sdlc (EUSAGE, lock out of sync with its manifest); a build in
  a `node_modules` that predates 30.1 fails with `Rollup failed to resolve import "@fontsource/archivo/400.css"`. So
  herald's `deck pull` prover (`deck_pipeline.NpmLocalProver`: `npm run extract`, then `npm run build`) could not pass
  for any deck, and no deck could record a bridge etag until the operator unblocked it that day with a local, untracked
  `node_modules` shim. Story 30.1's zero-origin meta-test never saw it: it scans each deck's source `index.html`, never
  a built bundle. **What it looks like when fixed:** Archivo Expanded is the 125% width of the variable Archivo, which
  `docsite/assets/fonts/fonts.css` already declares that way from `@fontsource-variable/archivo`. Each Archivo deck
  depends on that package in place of the phantom one, drops the three `archivo-expanded` imports, and declares the one
  `@font-face` for `'Archivo Expanded'` (`font-stretch: 125%`) in its `src/index.css`. Every lock is regenerated from
  the registry with no shim present, and `npm ci` and `npm run build` exit 0 in all 14 decks; the built bundle carries
  the `wdth` face and names no other origin. A meta-test reads every deck's `package.json` against its lock, offline,
  so a declared dependency with no lock entry fails the suite before a prover does. **Constraints:** a fix under CAP-55
  (Story 30.1), with no CAP and no flag; no deck's content, design, weights or `index.html` changes; `dist/`,
  `node_modules/` and every font binary stay untracked (AD-4). Owner `spec-pyforge-herald`. → Epic 30 / Story 30.3,
  specced 2026-10-14.

## One-chain fold (2026-09-17)

Herald rebases to one Dream, one Spec, one PRD, one spine, one epic chain. Folded topic Dreams are archived in place with `Consolidated into [[pyforge-herald]]` banners. Station Spec `spec-pyforge-herald` is `ready`; this Dream is `specified`.
