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

- **2026-10-25 (the PRD's FR arrows were mapped by section, not traced) — Found: eight of the herald PRD's
  `FR-n ← CAP-m` arrows name the wrong capability.** A fleet audit of every station PRD's arrows, run after marshal
  Story 105.1 found marshal's arrows counted rather than traced, read all 48 herald arrows against their capabilities.
  The 2026-09-17 fold (`4251c42229`) gave each feature group one capability. Three groups got the wrong one: the Moments
  CLI (FR-1.1..FR-1.3) reads CAP-1, the deck CLI; the web surface (FR-2.1, FR-2.3) reads only CAP-3, the visual
  identity; and evidence linking (FR-6.1..FR-6.3) reads CAP-11, whose success has no evidence clause. The 2026-10-10
  PRD section had already corrected FR-7.1..FR-7.4 for the same cause. Doctor's `fr-without-cap` only checks that a
  cited CAP exists, and 36 of herald's 48 dotted FR ids are never read, so nothing noticed. **What it looks like when
  fixed:** FR-1.1..FR-1.3 and FR-2.3 read CAP-11, CAP-12, CAP-13 (before the fold, the Spec's HER-11..HER-13
  constraints said all three Moments integrate with the Herald CLI and web surface); FR-2.1 reads CAP-3 and those
  three; FR-6.1..FR-6.3 read CAP-12 and CAP-13, whose successes require evidence links. **Constraints:** a chore under
  `spec-one-chain-per-station` CAP-5 (FRs derive from CAPs) and CAP-3 (the station fold procedure); no CAP, no flag, no
  `SPEC.md` change; no detector rule changes. Operator rulings, 2026-10-25: "Do rows 1-5 in one PR" and "CAP-11..13
  (Recommended)" for FR-1.x and FR-2.x. Owner `spec-pyforge-herald`. → Epic 46 / Story 46.1, specced 2026-10-25.
  **Amended the same day (the independent review; operator ruling "Apply all (Recommended)"):** FR-3.2, FR-4.2,
  FR-4.5 and FR-6.2 also cite the live-backend capabilities their automation clauses name (CAP-38, the webhook;
  CAP-39, the cron and the 7-day link re-validation), so eleven arrows change.
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
  session. Owner `spec-pyforge-herald`. → Epic 45 / Story 45.1, specced and fixed 2026-10-16. **Amended the same day
  (the independent review; the operator's ruling):** the SBOM laptop gate stays npm-free (fnd:CAP-13), so
  `pyforge-herald-test`, which `pyforge-station-tests` and the gate run, keeps no dependency. A separate
  `pyforge-herald-test-built` (the install, then the suite) is what CI's herald job runs, with
  `HERALD_DOCS_SITE_REQUIRED=1`. `pr-preflight-lanes` declares the install before the station suites, and a touched run
  keeps it beside any kept docs-site lane. Done 2026-10-16.

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
- **2026-10-26 (every requirement derives from a capability) — Found:** the 2026-09-17 fold left 20 of the Spec's capability titles as `from spec-<old>`, 12 intent/success bullets as 'See absorbed Spec memlog and git history.' and 8 cut at their first source line, so an arrow traced by Story 46.1 pointed at a block that said nothing. **Ruled** (2026-10-26, operator, fleet-wide: "yes forbid it" — a requirement cites one or more defined capabilities and nothing else; `spec-one-chain-per-station` CAP-5 as amended, CHAIN-STANDARD § 12). **For herald:** the text is restored by script from `4251c42229^` (9 titles from source lines, 11 authored from intent; 8 bullets from the source, 4 authored where the source carried none; 8 rejoined), every id stable, the authored lines recorded in the memlog for review. Epic 47 / Story 47.1, built in the one-PR effort with the other seven stations; no herald CAP minted, no requirement changes.

## 2026-10-26 — The deck family stays current — infographics re-derived from the ledgers, not remembered (folded from deck-family-currency)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/deck-family-currency.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/deck-family-currency.md`.*

## The deck family stays current — infographics re-derived from the ledgers, not remembered

### The Dream

Herald's infographics are the ecosystem's explainer surface and the input corpus for video
production. Today each one is frozen at the day it was authored: the Marshal poster still quotes
the tooling versions and fleet counts of 2026-07-31, and eleven of the fourteen posters never grew
past the six-section stub they were seeded as. The Dream is that every
`presentations/<slug>/project/<Name> Infographic standalone.html` reads as **true on the day you
open it** — its counts, versions, statuses and dates derived from the same ledgers the console
reads, its structure held to one codified standard (six-act arc, full-depth section set, inline
diagrams), and the whole family re-derivable on trigger the way code is re-built. Design stays the
visual editing surface; git stays the archive of record; **facts come from the ledger, never from
memory.**

> An infographic that quotes last month's ledger is a claim the estate can no longer stand behind.

### Why now — measured, not feared

| Finding | Where it is visible |
|---|---|
| Fourteen of fifteen deck folders carry a standalone poster; **eleven are July stubs** — 14–48 KB, zero inline SVGs, zero act bands | `presentations/*/project/*Infographic standalone.html`; `git log -1` per file: 2026-07-24/25 |
| Only three are at exemplar depth — warden 412 KB / 18 sections / 15 SVGs / no acts; marshal 91 KB / 19 / 3 / six acts; unifying-strategy 129 KB / 21 / 9 / six acts | same files, measured by `<section` / `<svg` / `ACT I..VI` counts |
| **The deep ones are stale too.** Marshal quotes `bmad-method 6.10.0`, `bmad-loop 0.9.0`, "128/333 fleet-wide", "Herald 4/27", "Mason 4/48", "Doctor 5/18", "Scribe 2/13", "Steward 3/26" | `presentations/pyforge-marshal/project/*.html`; live: BMAD core 6.12.0 (`_bmad/_config/manifest.yaml`); ledgers marshal 248/249, herald 67/68, mason 66/66, doctor 95/95, scribe 20/20, steward 206/222, atlas 94/95, warden 49/49; fleet 846/865 stories, 183/188 epics (`fleet-picture`) |
| Main has moved **4,414 commits** since the family-wide sync of 2026-07-24/25 | `git rev-list --count --since=2026-07-24 main` |
| The Design side holds nothing newer to pull: Unity Data Stack's Infographic head and standalone are the 2026-07-25 six-section stub, body-identical to disk; the Warden project's file set is unchanged since July | DesignSync `list_files` / `get_file`, 2026-09-13, projects `0494e2b0` and `100ca8cc` |
| `herald deck status` reports **all fifteen decks `linked: false`** — no `.herald/bridge-state.json` exists, and every README `## Design project` section predates the canonical two-line shape (DW-1-5-1) | `pixi run -e pyforge-herald herald deck status --repo-root .` |
| `pyforge-unifying-strategy` has **no Design project** — authored repo-side 2026-08-26, never seeded | its README carries no project id; no `design/p/` link anywhere in the tree |
| No fact in any poster cites its source, and nothing detects poster staleness: the chain-currency sweep covers planning spines, and the exemplar program names the deck/infographic family as a *purely manual* exemplar | [[chain-currency-sweep]]; [[fleet-hygiene-verification-exemplar-program]] § "narrower, purely-manual exemplars" |

### What it looks like when real

- **One standard, written once.** `docs/how-to/presentation-deck.md` carries the infographic
  standard as a checklist: the six-act arc with full-bleed act bands, the full-depth section set
  (problem · pipeline · cast · journey · flows · autonomy · phase×persona table · relay · shipped
  product · doctrine · stack · which-tool-when · escalation · per-leader value · enterprise ·
  seams · proof · seed · roadmap · creed, adapted per subject), at least three inline SVG diagrams,
  the 90 KB+ class, and a source line for every number. **Unifying Strategy is the structure,
  acts and length reference; Warden is the density and visual-form reference.**
- **A fact ledger per deck.** `presentations/<slug>/facts.yaml` lists every count, version,
  status and date the poster shows, each with the command or file it was derived from, its value,
  and the date derived. A derivation step re-emits it from live sources (`fleet-picture`, the
  tracked `sprint-status-ledger.yaml` files, each station's `pyproject.toml`, the BMAD manifest,
  `SPEC.md` capability tables, `bmad-groundtruth`); the deck README ledger summarizes it; a check
  reds when a rendered fact disagrees with its ledger row.
- **Every PyForge-branded poster rebuilt to the standard from its ledger** — the eight station
  decks, genesis and unifying-strategy — authored repo-side, pushed byte-exact to the deck's
  Design project with the DesignSync local-path pipeline, README sync ledger updated with the
  returned etags, and pulled back to prove the round trip.
- **The rendered page is looked at.** A headless full-page PNG of each standalone sits beside the
  report — the render gate proves it RUNS, the PNG proves it LOOKS right.
- **The bridge sees the family.** `herald deck status` reports every seeded deck linked, and
  unifying-strategy has a Design project bound to Modernist.
- **Later slices, named now.** The trio head, Infographic Deck and Executive Summary are
  re-derived from the same ledger so the family is back in lockstep; the four chain decks (unity,
  wasm, deckcraft, presenton) follow in their own wave; Design-side visual polish is its own act,
  always closed by a byte-exact pull.

### Constraints / Non-goals

- **Derive, never declare.** A number, version, status or date without a `facts.yaml` row does not
  ship. Story counts come from the tracked ledgers, versions from `pyproject.toml` and the BMAD
  manifest, capability counts from `SPEC.md`, fleet totals from `fleet-picture` — never from a
  prior poster or from memory.
- **Never restrict size at authoring time.** Lay everything out; cutting is a later, visual act.
- **Repo-side first.** This slice authors in the repo and pushes; no Design-chat authoring and
  no visual polish in Design. When polish happens later it ends with a byte-exact pull, per the
  deck spec's standing rule.
- **The standalone leads this slice — a dated, deliberate exception to trio lockstep.** The deck
  spec says the trio moves together; the operator chose the standalone first (2026-09-13). Each
  README ledger marks the head and Infographic Deck "standalone ahead" until the lockstep slice
  re-derives them.
- **Scope of this slice is the ten PyForge-branded decks.** The chain decks and `agentic-sdlc`
  (BMAD-branded, no standalone in `project/`) are out of this slice by decision, not omission.
- **Advisory, not a second gate.** The facts check reports; it does not become a PR verdict
  unless a later Spec promotes it.
- **One PR per deck; four worktree agents per wave; physical paths, never `bmad-switch` inside a
  parallel agent.** Non-recipe PRs carry the `maintenance` label.
- **Marp-derived renders stay derived.** `src/marp/*-infographic-standalone-*.html` remain
  `deck-export` outputs; this Dream does not redefine them.

### Kinships

[[pyforge-herald]] (the station — the bridge CLI, the deck family, the standard's home) ·
[[deck-visual-qa]] (the render-to-PNG discipline this extends to the standalone poster) ·
[[chain-currency-sweep]] (the same detector-plus-reconciler pattern, applied to presentation
surfaces instead of planning spines) · [[fleet-hygiene-verification-exemplar-program]] (names the
deck/infographic family as a purely manual exemplar — this is its graduation path) ·
[[pyforge-unifying-strategy]] (the structure, acts and length reference) · [[pyforge-warden]] (the
density and visual-form reference) · [[pyforge-charter]] (the Genesis deck this refreshes) ·
[[pptx-deck-generation]] (the export set the same ledger feeds in a later slice).

### Realization log

- **2026-09-13** — Seeded (operator direction: the Design-side infographics are outdated; every
  line is to be verified; plan first). Every row of § *Why now* was measured this date. Decisions
  of record from the operator, same date: (1) the ten PyForge-branded decks first, the four chain
  decks later; (2) a structure/acts/length reference plus Warden as the density/visual reference;
  (3) the standalone poster first, family lockstep as follow-up; (4) repo-side authoring from the
  fact ledger with a DesignSync push, no Design polish this session; (5) a tracked `facts.yaml`
  per deck summarized in the README ledger; (6) create the unifying-strategy Design project in its
  wave; (7) four worktree agents per wave, one PR per deck. **Reference ruling, confirmed by the operator the same date:** the operator had first named
  Unity Data Stack as the structure reference; verified this date that Unity's Design-side head
  and standalone are the 2026-07-25 six-section stub with no act bands, so the family's only
  six-act, exemplar-depth posters are Unifying Strategy and Marshal — the operator confirmed
  **Unifying Strategy as the structure, acts and length reference** and **Warden as the density
  and visual-form reference**. Next act: `bmad-spec` derives the Spec under `pyforge-herald`.
- **2026-09-13** — Specified. `bmad-spec` (headless, express) derived
  `spec-deck-family-currency` under `pyforge-herald`: CAP-1 the standard, CAP-2 the fact ledger,
  CAP-3 the rebuild, CAP-4 the mirror proof, CAP-5 the staleness check; companions
  `infographic-standard.md`, `facts-ledger.md`, `deck-inventory.md`; `status: ready`,
  `open_questions: []`, two assumptions (the claude-design MCP is reconnected before Wave B and
  before any >256 KiB read-back; Warden's Design-side standalone is unchanged since 2026-07-24).
  Dream `dreamt → specified` per README § status. Next act: Epic 20 and its ledger rows in
  `pyforge-herald`, then Story 20.1/20.2 before any file outside `docs/dreams/` or the Spec
  folder changes.
- **2026-09-13 (later the same day)** — Wave A landed. Story 20.2 shipped `deck-facts`
  (PR #1295; four-layer review, 45 findings, 32 patched); the eight station posters were rebuilt
  to the standard from their ledgers by worktree agents, reviewed against the floors, the facts
  check and a full-page render, pushed to their Design projects, merged (PRs #1297, #1298,
  #1300, #1301, #1303–#1306) and read back byte-identical once the claude-design MCP
  reconnected (etags in each README ledger). Two facts the wave corrected: the 411,764 B Warden
  "reference" was a Design bundle (192,472 B of content; the rebuild is 295,079 B), and
  `recipes_count` had read the working tree (now `git ls-files`). One capability the wave
  minted: **CAP-6, mechanical refresh** — the moment round 1 merged, the posters read `mismatch`
  on the fleet counts their own landings moved; CAP-5 detected it and nothing could repair it
  without hand edits, so `deck-facts --refresh` (Story 20.14) rewrites stale marked literals from
  the ledger. The Unifying Strategy Design project now exists (`1e4020bc`, seeded with the
  family). Wave B (20.11 genesis, 20.12 the Canopy) in flight; 20.13 and the closeout follow.
- **2026-09-13 (closeout)** — **Realized.** Epic 20 closed 14/14 in twelve PRs. The standard has one
  home and floors that can be checked; every PyForge poster meets them (112,847–295,083 B, six acts
  each, 21–33 sections, 4–26 inline diagrams); 833 facts across the ten carry a `data-fact` mark over
  a tracked `facts.yaml` row and every deck reports `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced`;
  each poster was pushed to its Design project and **read back byte-identical, 10 of 10**; and
  `herald deck status` reports the ten linked where it reported none this morning. The decay this
  Dream named turned out to be faster than expected — a poster goes stale on its own merge — so CAP-6
  was minted mid-epic and its first sweep refreshed 96 stale literals across nine posters in one
  pass. Deliberately left: the trio lockstep, the four chain decks, and Design-side polish. Retro:
  `_bmad-output/projects/pyforge-herald/planning-artifacts/retros/retro-epic-20-2026-09-13.md`.

## 2026-10-26 — The whole deck family moves together — every surface, every deck, one ledger (folded from deck-family-lockstep)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/deck-family-lockstep.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/deck-family-lockstep.md`.*

## The whole deck family moves together — every surface, every deck, one ledger

### The Dream

Epic 20 made one surface true. Ten PyForge posters read as of the day you open them, every number
traceable to a tracked row, the Design mirror byte-exact. But a deck is not one file. Beside each
rebuilt poster sits an **Infographic head**, an **Infographic Deck**, an **Executive Summary**, a
marp source and two PowerPoint exports — and all of them still carry July's facts. Four more decks
in `presentations/` never entered the wave at all. And nothing has yet been through the visual
editing surface the whole bridge exists to reach.

The Dream is that **the family moves as one**: every artifact of every deck derives from the same
`facts.yaml`, so a ledger that moves moves all of them; every deck in `presentations/` meets the
standard, not just the ten; and the Design side is a place the family is *improved*, not merely
mirrored — with git still the archive of record.

> A deck whose poster is current and whose slides are three months stale is not a current deck.

### Why now — measured, not feared

| Finding | Where it is visible |
|---|---|
| Every deck README says its head and Infographic Deck are **"standalone ahead"** — ten decks, three surfaces each, all still at their July content | the `## Ledger — 2026-09-13` section of each `presentations/pyforge-*/README.md` |
| The heads are 14–48 KB against posters of 112–295 KB; the Infographic Decks likewise | `presentations/pyforge-*/project/*- Infographic.dc.html` vs the standalone beside it |
| The marp sources and both PPTX per deck are dated 2026-07/08 and were never re-derived | `presentations/pyforge-*/src/marp/`, `src/pptx/` |
| Four decks never entered the wave: unity-data-stack, wasm-analytics-stack, deckcraft, presenton-pixi-image — 15–19 KB stubs, no act bands, no `facts.yaml` | `presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/project/` |
| Those four report `linked: false` and their `## Design project` sections are malformed for `registry.read` | `herald deck status --repo-root .` — 10 of 15 linked |
| No deck has been through a Design-side visual pass since the rebuild; the bridge's editing half is unexercised on current content | `spec-deck-family-currency` § Non-goals, and every README ledger's "Design etag" row |
| The mechanical path already exists and is unused for this: the standalone **is** the head's body, minus the `x-dc` wrapper, with styles moved into `<head>` | `docs/how-to/presentation-deck.md` § *Artifact dependency tree*; the trio's own definition |

### What it looks like when real

- **The trio derives, it is not re-authored.** A verb turns a current standalone into its
  Infographic head and Infographic Deck mechanically — the body is already identical by definition —
  so "standalone ahead" stops being a state a README can be in.
- **The exec summary and the exports follow the same ledger.** The one-page summary and the marp
  sources carry marked facts too, and `deck-export` regenerates the PPTX from them, so the Standard
  export set is current in every format at once.
- **Fourteen decks, not ten.** The four chain decks are rebuilt to the standard from their own fact
  ledgers, registered, and linked; `herald deck status` reports the whole of `presentations/`.
- **The Design side is used as a design surface.** At least one deck goes through a real visual pass
  in Claude Design and comes back through a byte-exact pull, proving the loop the bridge was built
  for — and the pull discipline holds: git stays the archive of record.
- **One sweep covers everything.** `deck-facts <slug> --refresh` walks every marked surface of a
  deck, not just its poster, and the standing sweep keeps fourteen decks current in one pass.

### Constraints / Non-goals

- **Derive, never re-author.** The head and Infographic Deck come from the standalone by transform;
  a hand-written divergence between them is the defect this Dream removes. The same rule that
  governs facts governs structure.
- **The marked-fact contract is unchanged.** Every number on every surface is a `data-fact` mark
  over a tracked `facts.yaml` row; the three hazards `--refresh` cannot cover (hand-counted prose,
  swept SVG labels, `inline-flex` fusing a token) stay in force.
- **Never restrict size at authoring time**; the floors in `infographic-standard.md` are a floor.
- **Design polish ends with a pull.** No visual act is complete until git holds the bytes.
- **Not a new engine.** The React deck, `deck_export.py`'s semantics and the `.pptx` pipeline are
  untouched; this Dream re-derives content, it does not rebuild machinery.
- **Not a second gate.** The checks stay advisory.
- **One PR per deck, worktrees, physical paths** — the parallel-agent discipline Epic 20 proved.

### Kinships

[[deck-family-currency]] (the realized parent — the standard, the fact ledger, CAP-6; this Dream
finishes the surfaces it deferred) · [[pyforge-herald]] (the station; the bridge and the deck family)
· [[deck-visual-qa]] (the render gate every rebuilt surface passes) · [[pptx-deck-generation]] and
[[pptx-custom-shapes]] (the export half the exec summary and marp sources feed) ·
[[chain-currency-sweep]] (the same detector-plus-reconciler shape, one tier up).

### Realization log

- **2026-09-13** — Seeded at Epic 20's closeout, from the three slices that epic deferred by operator
  ruling (trio lockstep, the four chain decks, Design-side polish). Every row of § *Why now* was
  measured on `main` that day, after all fourteen Epic 20 stories landed. Next act: `bmad-spec`
  derives the Spec under `pyforge-herald`.
- **2026-09-13 (same day)** — Specified. `spec-deck-family-lockstep` is `ready` with
  `open_questions: []` — the parent Spec and Epic 20's retro settled every decision this one would
  otherwise have had to ask, so it mints only CAP-1..5 and binds the rest. Epic 21 carries eleven
  stories with Given/When/Then and named surfaces, and eleven `backlog` rows sit in the tracked
  sprint ledger. Nothing else is owed before dispatch: the standard, the fact ledger, the refresh
  verb and the registry all shipped with Epic 20. Next act: drain Epic 21, starting with 21.1 —
  21.2 through 21.5 depend on it.
- **2026-09-16** — Dream-append: dispatching Story 21.4 (`bmad-build-auto`) surfaced a real,
  independently-reproduced blocker on the push+read-back leg — `herald deck push` raises
  `ImportError: cannot import name 'streamablehttp_client' from 'mcp.client.streamable_http'` on
  `main`, before any credential or network check. `mcp` 2.2.0 (what `pyforge-herald`'s pixi
  environment actually resolves) renamed the symbol to `streamable_http_client`;
  `pyforge.herald.transport.mcp_transport` (Story 1.2, 2026-08-07) never updated. Confined to
  herald's own transport — atlas's parallel `mcp` 2.x usage doesn't touch this symbol. A second
  claim from the same dispatch (missing Design credential) was re-checked directly and found stale
  — `resolve_design_credential()` succeeds live once `/design-login` had completed; not a standing
  gap. Minted `spec-deck-family-lockstep` CAP-6 for this (binds here rather than a new Dream/Spec
  file — governance ruling `spec-one-chain-per-station`, `chain-sprawl-check` enforces it live).
  Blocks 21.4, 21.6–21.9's push leg, and all of `spec-design-sync-loop`'s Epic 23. Next act: mint
  Story 21.12 in `epics.md` citing CAP-6, then implement via `bmad-build` (quick-dev — a single,
  low-external-blast-radius fix).
- **2026-09-16 (same day)** — Story 21.12 landed. The fix was two distinct `mcp` 2.2.0 symbol
  renames, not one — the second (`CallToolResult.isError` → `is_error`) only surfaced on a
  completed live call, after the first was fixed, which is exactly why the story's own AC
  insisted on a live push+read-back proof rather than an import-level check. Live-proved: `herald
  deck push pyforge-warden` succeeded for real against Design; `deck-facts pyforge-warden --check`
  reported 0 `mismatch` afterward. Found along the way, NOT fixed (orthogonal, deferred on the
  story spec): `herald deck pull` hits two separate pre-existing bugs on large/oddly-named decks
  (a 256 KiB `read_file` cap, and a `prototype_filename`-guessing mismatch) — both reach the fixed
  transport successfully before failing on unrelated causes. `pyforge-herald-test`: 1262 passed, 4
  skipped. Next act: Story 21.4 (the ten-deck sweep) and 21.6–21.9's push legs are now unblocked
  for real dispatch.

## 2026-10-26 — A deck is proven to look right, not merely to render without crashing (folded from deck-visual-qa)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/deck-visual-qa.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/deck-visual-qa.md`.*

## A deck is proven to look right, not merely to render without crashing

### The Dream

Every deck this repo produces — Herald's existing HTML/React pipeline today, and a possible
`.pptx` pipeline ([[pptx-deck-generation]]) tomorrow — passes some render check before being
called done, but "renders without a JS exception" and "looks right" are different claims, and
today's tooling only proves the first. This is not a hypothetical gap: it is a standing,
already-recorded piece of feedback in this repo's own memory — "Visual output needs a
screenshot — render gates prove the page RUNS, never that it LOOKS right." The source dream's
`visual_qa` concept (render every slide to PNG for review, opt-in native-app backends) is a direct
answer to a problem this repo has already been told it has, independent of whether a `.pptx`
pipeline ever exists.

### What it looks like when real

Splits cleanly into two pieces with different dependencies:

- **Visual rendering QA (PNG-per-slide, for review)** — applies to Herald's EXISTING HTML/React
  deck pipeline today, no `.pptx` pipeline required. This is the piece that actually closes the
  documented "render gates prove RUNS, never LOOKS right" gap — a headless-render-to-PNG step
  callable after any deck build, HTML or `.pptx` alike, giving a human or an LLM reviewer
  something to look at instead of trusting "the build didn't crash."
- **Structural/format-specific gates** (`check_xml`'s OOXML element-ordering validation,
  `check_typst_safety`'s Typst-PDF-renderer crash-pattern detection, `audit_overflow`'s
  text-capacity estimation) — these are `.pptx`/OOXML-specific and inherit
  [[pptx-deck-generation]]'s own open question about whether that pipeline is ever built at all.
- **`check_placeholders`** (regex scan for unedited "Click to add"/Lorem ipsum) — format-agnostic
  in principle; Herald's HTML pipeline already has its own `<image-slot>` placeholder convention
  (`presentation-deck.md`), so a similar unedited-placeholder scan could apply there too, though
  this repo's placeholder shape differs from the source's PowerPoint-specific one.

### What is real

Herald's existing deck pipeline (`docs/how-to/presentation-deck.md`) has NO dedicated
visual/structural QA gate today — checked directly, no `check_xml`/`overflow`/`visual_qa`-shaped
step exists anywhere in that spec. The gap this Dream's visual-QA half would close is real and
already named in this repo's own accumulated feedback, not speculative.

### Constraints

- **The visual-QA half does not require [[pptx-deck-generation]] to exist** — it should be scoped
  and potentially built against Herald's EXISTING HTML pipeline first, independent of that other
  Dream's own open question.
- **The structural/format-specific gates DO require a `.pptx` pipeline** — OOXML-element-ordering
  and Typst-crash-pattern checks have no meaning without `.pptx`/Typst artifacts to check.

### Non-goals

- **Not an automated fix-and-rebuild loop** — the QA pipeline reports; a human or agent fixes,
  carried from the source dream's own scope unchanged.
- **Not full WCAG 2.1 AA accessibility audit** — carried unchanged.
- **Not cross-platform rendering parity guarantees** — carried unchanged.

### Full feature audit against `deck-quality-assurance`

| Source feature | Disposition | Why |
|---|---|---|
| `visual_qa` (render every slide to PNG for review) | **Included, independent of `.pptx`** | The one piece with a real, already-documented local gap to close — applies to Herald's existing HTML pipeline today. |
| `check_xml` (OOXML element-ordering/choice-group validation) | **Contingent on [[pptx-deck-generation]]** | Meaningless without `.pptx`/OOXML artifacts. |
| `check_typst_safety` (Typst-PDF-renderer crash patterns) | **Contingent on [[pptx-deck-generation]]** | This repo's own pipeline doesn't use Typst for PDF export (see `presentation-deck.md`'s own export chain); relevant only if a future `.pptx`-adjacent pipeline introduces a Typst step. |
| `audit_overflow` (80%-capacity text estimation, autofit-aware) | **Contingent on [[pptx-custom-shapes]]** | Needs that Dream's own autofit engine to have an "AUTOFIT_OK/UNREADABLE" classification to audit against. |
| `check_placeholders` (unedited "Click to add"/Lorem ipsum scan) | **Reframed, format-agnostic in principle** | Herald's HTML pipeline has its own `<image-slot>` placeholder convention already; a similar unedited-content scan could apply there, though the exact regex/shape differs from PowerPoint's. |
| PowerPoint AppleScript/COM native-app render backends | **Omitted, platform-specific** | Opt-in native rendering is a nice-to-have this Dream doesn't need to commit to; a headless PDF/PNG path (PyMuPDF/`pdftoppm`, already the source's own default) is sufficient. |

### Kinships

[[pyforge-herald]] (the estate — the visual-QA half applies to Herald's EXISTING deck pipeline
directly) · [[pptx-deck-generation]] and [[pptx-custom-shapes]] (the two sibling Dreams whose
format-specific gates this one's structural half depends on)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit,
  alongside its two sibling deck dreams. Unlike those two, found this one splits into an
  independently-valuable half: `visual_qa`'s PNG-per-slide rendering directly answers an
  already-recorded piece of this repo's own feedback ("render gates prove RUNS, never LOOKS
  right"), applicable to Herald's existing HTML pipeline with no dependency on whether a `.pptx`
  pipeline is ever built — the strongest-evidenced of the three deck dreams in this batch as a
  result.
- **2026-08-14** — Spec authored (spec-deck-visual-qa, pyforge-herald) by the 2026-08-14 dream-backlog audit: the visual-QA half only (PNG-per-slide headless render + <image-slot> placeholder scan against the existing HTML pipeline); the three .pptx-contingent gates stay parked with their sibling dreams.
- **2026-09-09 (fleet readiness pass — built, not in effect)** — Epic 14 (14.1 gate-report
  interface, 14.2 headless-render gate, 14.3 image-slot scan) is `done` in the tracked
  ledger and real in code (`src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py`,
  665 lines; `herald deck qa <slug>` at `cli.py:331-341`, dispatched `:764-765`, handled
  `:982-995`). Both of the Spec's open questions are **answered by that code** and closed
  this date: the entrypoint is the Epic-6 CLI dispatcher (no per-deck `scripts/` step), and
  the serve mode is a throwaway loopback static server rather than `file://`
  (`deck_qa.py:143-152` — "Chromium needs a real HTTP origin, not `file://`"). **Status held
  at `specified`, not advanced to `realized`**: nothing in the repo calls the gate — no pixi
  task (`pixi.toml` names `deck_qa` only in the playwright dependency comment at line 2352),
  no CI job, and `docs/how-to/presentation-deck.md` still describes a purely run-shaped
  verify checklist. No run artifact exists — `render_gate` writes `.herald/deck-qa/<slug>/render/`
  (`deck_qa.py:117`, `:245-250`) and `.herald/` is not in the tree. The capability exists;
  the gap it was written to close is still open. Vessel: herald Epic 19 Story 19.3 (give
  the gate a caller), per the fleet-readiness decision batch 2026-09-09 row C6.

## 2026-10-26 — The Design sync loop — every Design project has a local twin, and one command keeps the whole family true (folded from design-sync-loop)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/design-sync-loop.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/design-sync-loop.md`.*

## The Design sync loop — every Design project has a local twin, and one command keeps the whole family true

### The Dream

The operator's ask, 2026-09-14, in their own words:

> We want the repeatable DesignSync to do 3 things — 1) Every design project should be available
> locally in `presentations/`. 2) Standalone HTML posters need to be synced (**Claude Design edits
> win over local copies**) and refreshed to the latest facts and state of the repo. 3) The remaining
> PowerPoint decks, Marp content (called *deck family*) in each Design project needs to be
> refreshed. 4) The synced posters and PowerPoints should be available on GitHub Pages for users to
> browse and download.

Today each of those is a hand-driven act, done by an agent in a session, one deck at a time, from
memory of a runbook. The second sweep (2026-09-14) took nine `finalize_plan` prompts, nine
`write_files`, nine `render_preview` read-backs and a hand-written ledger row per deck to move nine
posters — and it deliberately left the Infographic heads, the Infographic Decks, the executive
summaries, the Marp sources and the PowerPoints exactly as stale as they were, because no shipped
capability moves them. The Dream is that **the loop is one command**: it enumerates the Design
account, pulls what Design changed, refreshes every fact-bearing surface from the same ledger,
re-derives the family, pushes the result back, proves the mirror, and publishes — and that running
it twice in a row is a no-op.

> A deck family that is current only on the day an agent remembered the runbook is not current.

### What is real (measured 2026-09-14 on `main` at `168bbedb13`)

- **The Design account holds more projects than `presentations/` has twins.** `list_projects`
  returns 20+ (the tool pages at 20; `PyForge Scribe deck` and `PyForge Steward deck` exist and
  were not in the first page). Fourteen are deck projects with a local twin. Beside them:
  `Agentic AI SLDC deck` (twin: `presentations/agentic-sdlc/`, **unregistered** with herald's
  registry); `PyForge six-quarter roadmap` and `LLM Knowledge Bases` (**no local twin at all**);
  `REMOVED-PyForge Unifying Strategy` (the ad-hoc duplicate Story 21.11 found, renamed to mark it
  retired); `Local recipes repository connection` (the retired mirrored-app-tree project the deck
  spec names as the cautionary tale); and three **design systems** — `Modernist`, `Broadsheet`,
  `Nocturne` — which are libraries the decks bind to, not decks.
- **`herald deck status` reports 10 of 15 linked.** The registry (each README's machine-owned
  *Design project* section) and the gitignored `.herald/bridge-state.json` are the bridge's two
  halves; the four chain decks and `agentic-sdlc` have no registry section, so the bridge cannot
  see them (Story 21.10 is the backlog row for the fourteen).
- **Poster currency is solved repo-side-first, and only for the standalone.**
  `spec-deck-family-currency` CAP-6 is `deck-facts <slug> --refresh --check` → DesignSync push →
  read-back; git is the source and Design the mirror. The operator's rule for the loop inverts the
  direction — **Design edits win** — so the loop must *pull first*, then refresh, then push. The
  2026-09-14 sweep proved the push and read-back mechanics 9/9 byte-identical.
- **The rest of the family has no refresh path.** The `- Infographic.dc.html` head, the
  `- Infographic Deck.dc.html`, the `- Executive Summary.dc.html`, `src/marp/*.md` and
  `src/pptx/*.pptx` carry the literals of the day they were authored (July–September). Epic 21
  (`deck-family-lockstep`) owns deriving the trio from the standalone (21.1–21.4) and the exec
  summaries + export set (21.5); `deck-export` regenerates standalone HTML + PPTX from Marp via the
  marp CLI (PPTX needs Chrome); `herald deck push` (kernel CAP-5) pushes regenerated derived
  exports back into Design; `herald deck pptx-spec` / `pptx-fill` (Story 15.1) fill a template
  into a genuinely editable deck. The pieces exist; nothing sequences them.
- **Pages publishes the posters and nothing else.** `docsite/build.py` (`spec-pyforge-pages`,
  live at `/herald/infographics/` on Pages) renders the standalone infographics
  into a gallery from configured globs. No PPTX, Marp, executive summary or per-deck family page
  is published or downloadable; `dashboard.yml` is the one Pages deployment and must stay so
  (pgs:CAP-2).
- **The loop cannot run unattended today.** Every Design read and write goes through the
  operator's claude.ai login (the `claude-design` MCP server and `DesignSync` in a Claude Code
  session; herald's `McpTransport` needs a resolved credential). A GitHub Actions runner has none of
  that. `herald deck watch` polls for Design-side edits from a session.

### What it looks like when real

- `pixi run -e pyforge-herald herald deck sync-all` (name provisional) enumerates the account,
  reconciles the registry against it, and for every registered deck runs: **pull** (Design wins
  for every prototype and poster whose Design etag moved since the last pull) → **refresh**
  (`deck-facts --refresh` over every marked surface, so the human's visual edits survive and the
  numbers come from the ledger) → **derive** (trio, executive summary, Marp, PPTX from the
  refreshed standalone) → **push** (only what changed) → **prove** (read-back byte-identical, etag
  recorded) → **publish** (the Pages family page picks up the new artifacts). A second run reports
  every deck `unchanged` and writes nothing.
- Every Design project that is a presentation has a `presentations/<slug>/` twin with a registry
  section; projects that are not presentations are listed once in the registry as *excluded*, with
  the reason, so the loop never silently skips them.
- Pages has one page per deck: the poster (view), the Infographic Deck and Executive Summary
  (view), the PowerPoints and Marp sources (download), each with the etag/tree the artifact was
  derived at — and an index across the family.

### Open questions for the Spec — asked and answered 2026-09-14 (operator)

1. **Scope of "every Design project."** **Ruled: presentations *and* design systems.** Every
   presentation project gets a `presentations/<slug>/` twin with a registry section — the 14 decks,
   `agentic-sdlc` (registered at last), and new twins for `PyForge six-quarter roadmap` and
   `LLM Knowledge Bases`. The three design systems (`Modernist`, `Broadsheet`, `Nocturne`) are
   mirrored too, so the styling libraries the decks bind to are versioned alongside them (home to
   be chosen by the Spec — `presentations/_design-systems/<name>/` or a sibling dir; they are not
   decks and get no poster, ledger or Pages page). `REMOVED-PyForge Unifying Strategy` and `Local
   recipes repository connection` are **excluded by name** in the registry, with the reason, so the
   loop lists them as skipped rather than silently ignoring them.
2. **The conflict rule.** **Ruled: Design wins, then the ledger re-applies.** The loop pulls Design
   wholesale for every prototype and poster whose etag moved — the human's visual and prose edits
   survive — and then `deck-facts --refresh` rewrites every *marked* literal from the ledger. A
   human who changed a fleet count in Design is overridden by the tree, and the loop's report names
   every literal it overrode so the override is visible, never silent.
3. **Where PowerPoints come from.** **Ruled: both, per deck.** Marp-derived is the default — the
   Marp sources are refreshed from the ledger and `deck-export` regenerates the PPTX in-repo (marp
   CLI + Chrome on the machine running the loop); a deck that declares a `.potx` template is
   filled through `pptx-spec` / `pptx-fill` (Story 15.1) instead. The registry section records
   which path a deck takes; both push to Design and both publish.
4. **Pages shape and cadence.** **Ruled: extend the dossier site, on demand.** One Pages
   deployment (`dashboard.yml`, pgs:CAP-2); a family page per deck — poster, Infographic Deck and
   Executive Summary to view, PowerPoints and Marp sources to download, each stamped with the etag
   and tree it was derived at — plus an index across the family. The loop runs from an operator
   session (`herald deck sync-all`, or `herald deck watch` for the pull half); unattended runs are
   out of scope until a Design credential exists that a runner can hold.

### Constraints / Non-goals

- Git stays the archive of record and the *source* for facts; Design is the editing surface. "Design
  wins" is a rule about *prototype content*, not about `facts.yaml`, which is derived from the tree.
- One Pages deployment (`dashboard.yml`), per `spec-pyforge-pages` CAP-2.
- The loop binds to the shipped mechanics — `deck-facts`, `deck-export`, `herald deck
  seed/pull/push/status/watch`, DesignSync `finalize_plan` → `write_files`, the read-back recipe —
  and does not re-mint them. Epic 21's stories are its inputs, not its competitors: where 21.x
  builds a derivation the loop calls it.
- Not in scope: authoring new decks; the infographic standard itself; redesigning any poster.

### Kinships

- [[deck-family-currency]] — realized; CAP-1..6 are the refresh, mirror and check the loop calls.
- [[deck-family-lockstep]] — specified; Epic 21 derives the trio and export set the loop sequences,
  and 21.10 makes the registry see all fourteen.
- [[pyforge-pages]] — specified; the one Pages deployment the family page extends.
- [[pyforge-herald]] — the station; its kernel Spec owns the bridge verbs.
- [[vocabulary-one-name-one-job]] — `DW-VOCAB-2026-09-14-3` carries the agentic-sdlc deck's
  Design-side edits the loop's pull direction would make routine.

### Realization log

- **2026-09-14 (evening)** — **Re-scoped after the operator's duplicate-functionality review.** Read
  against the kernel code, four of Epic 23's eight stories re-described shipped verbs or Epic 21
  stories: `herald deck pull` *is* Design-wins (etag short-circuit, else Design's bytes overwrite
  local), `deck watch` is its continuous form, `deck push` already pushes the poster changed-only,
  and `deck-facts --refresh` over every surface is Story 21.3. 23.3 and 23.4 folded (reserved holes),
  23.5 narrowed to the `.potx` path + stamps, 23.6 to the binary PPTX push + read-back proof; the
  Spec's CAP-3..6 re-derived as deltas; 21.10's "`agentic-sdlc` stays unlinked by design" superseded
  by the scope ruling. Six stories remain. Dispatch order: 21.1 → 21.2 → 21.3, then 23.1 ∥ 23.2
  beside 21.5, then 23.5/23.6/23.7, then 23.8 — whose first run *is* 21.4.
- **2026-09-14 (later still)** — **Specified.** `bmad-spec` (headless, express) derived
  `spec-design-sync-loop` at `ready` from this file: CAP-1 enumerate + reconcile the account,
  CAP-2 every presentation has a twin (design systems mirrored as libraries), CAP-3 pull with Design
  winning, CAP-4 the ledger re-applies, CAP-5 the family derives and PPTX regenerates (both paths per
  deck), CAP-6 push-changed + prove, CAP-7 the Pages family page, CAP-8 one idempotent, reported
  command. Self-validate PASS on both passes. Decomposed the same day into herald Epic 23, Stories
  23.1–23.8, one per CAP, all `backlog`; 23.5 waits on Epic 21.1/21.2/21.5 for the derivations it
  calls.
- **2026-09-14 (later)** — The four questions answered by the operator: presentations *and* design
  systems in scope (two retired projects excluded by name); Design wins then the ledger re-applies;
  PowerPoints both ways per deck (Marp-derived default, template-filled where a `.potx` is declared);
  the dossier site extended with a family page per deck, run on demand from a session. `bmad-spec`
  derives the Spec from this file next.
- **2026-09-14** — Seeded from the operator's four-requirement ask, the afternoon PR #1361 landed
  the second manual sweep. Four open questions are the operator's; nothing downstream binds until
  they are answered and `bmad-spec` derives the Spec.

## 2026-10-26 — Herald Moments 2-4 run on a real live backend, not local-storage/CLI-triggered (folded from herald-moments-2-4-live-backend)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/herald-moments-2-4-live-backend.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/herald-moments-2-4-live-backend.md`.*

## Herald Moments 2-4 run on a real live backend, not local-storage/CLI-triggered

### The Dream

`_bmad-output/projects/pyforge-herald/planning-artifacts/epics-with-stories.md`'s Epics
8-10 (Progress/Success/Operations) spec a genuinely live service: a database (PostgreSQL
or SQLite via SQLAlchemy + Alembic migrations), a webhook HTTP endpoint receiving CI
callbacks (`on-ship`, `on-pr-close`), and scheduled jobs (a weekly cron aggregating
progress, an async job re-validating evidence links every 7 days). Records get created
automatically the moment a PR merges or closes, with zero operator action required to
produce the raw data -- an operator only reviews/publishes.

That is the vision this Dream preserves for later. It is explicitly **not** what
Epics 8-10 build first (see [[pyforge-herald]]'s own Epics tier + the 2026-08-08 scope
decision below) -- the first pass is scaled down to local storage (JSON/SQLite files, no
server) with every record created via a CLI command an operator runs by hand, because
nothing else in this repo's Herald architecture (a stateless CLI + a static web dashboard
talking to Claude Design) has ever hosted a persistent service, and inventing one
silently -- with no answer for where it deploys, what triggers CI to call it, or who
operates it -- would have been exactly the kind of scope invention the four behavioral
principles at the top of this repo's `CLAUDE.md` warn against.

### Why It Matters

The scaled-down first pass ships the operator-facing value (progress/claims/notices
records, the CLI, the web tabs) without inventing unrequested infrastructure. But it
trades away the whole point of "automatic": a factory lead currently has to remember to
run `herald progress warden --update` after a ship, rather than a webhook doing it the
moment CI reports success. The live-backend version is what actually delivers on Epic
8's own framing ("Progress records are created automatically when ships happen") and
Epic 9's ("auto-extract on PR-close") -- the scaled-down version is a real, useful
stepping stone, not the destination.

### What is Real

Nothing built yet toward the live-backend shape. What *is* real, as of 2026-08-08: the
scaled-down first pass of Epics 8-10 (local JSON/SQLite storage, CLI-triggered record
creation, the web tabs reading local data) -- tracked under the existing Epics 8/9/10
story numbers in `sprint-status-ledger.yaml`, which this Dream does not duplicate or
supersede.

### What it looks like when real

- A real webhook endpoint (`/api/herald/webhooks/on-ship`, `/api/herald/webhooks/on-pr-close`)
  that CI actually calls -- which first requires deciding where Herald's backend runs
  persistently (a question this Dream deliberately leaves open at `dreamt` stage; not
  Herald's call alone -- likely intersects Steward's estate/deployment ownership).
  a real database replacing the local JSON/SQLite files, with the same schema Epics
  8-10's specs already describe (Progress/Claims/Notice tables, indexes, migrations) --
  the CLI/web-tab surface built in the scaled-down pass should need minimal rework, since
  its data-access layer is the seam this Dream's eventual work slots behind.
- A weekly cron job and an async evidence-revalidation job actually running on a
  schedule, replacing the scaled-down pass's CLI-triggered equivalents
  (`herald progress --update`, a manual `herald success validate-evidence` or similar).
- Retry/backoff, webhook signature verification, and operator-alert delivery (email or
  in-app) -- all specced in Epics 8.2/9.2/9.5 but meaningless without a live endpoint to
  receive real traffic.

### Constraints

- **Do not silently invent server-hosting architecture.** The scaled-down pass exists
  precisely because Epics 8-10 assumed infrastructure this repo has never had an answer
  for. Realizing this Dream requires first answering: where does this run persistently,
  under whose operational ownership, and what actually triggers CI to call it -- likely
  a cross-station question (Herald's data model, Steward's deployment/estate ownership),
  not a unilateral Herald decision.
- **The scaled-down pass's CLI/web-tab contract should not need to change shape** when
  this Dream is realized -- only its data-access layer swaps from local files to a real
  database, and CLI-triggered updates become webhook/cron-triggered ones underneath the
  same commands. If realizing this Dream would require reshaping the CLI surface
  operators already learned, that is a signal the scaled-down pass's data-access seam
  was drawn in the wrong place.

### Non-goals

- Not re-litigating whether Epics 8-10 should exist at all -- they should; this Dream is
  about *how* they're powered, not *whether*.
- Not deciding the specific web framework (Flask/FastAPI), database (Postgres/SQLite), or
  scheduler (APScheduler/Celery Beat) named in the epics doc's Implementation Notes --
  those are illustrative, not committed, and remain open at Spec time.

### Kinships

[[pyforge-herald]] (the constitutive Dream Epics 8-10 belong to; this Dream is a
follow-up on top of it, not a replacement) · [[herald-moments-2-4-missing-surface]]
(archived/superseded predecessor covering the same Moments 2-4 gap at a coarser grain)

### Realization log

- **2026-08-08** — Dream captured. Surfaced mid-execution of Herald's "complete all
  epics and stories" campaign: Epics 8-10's specs assume a live database + webhook
  server + cron scheduler that exist nowhere else in this repo's Herald architecture.
  Flagged to the user rather than silently invented; user chose to build Epics 8-10's
  first pass scaled down to local-storage/CLI-triggered, and asked for this Dream to
  capture the full-spec live-backend version for later.

- **2026-08-10** — Specified: operator go in-session ("herald live-backend"); Spec at
  `ready`, decomposed as herald Epic 13 (6 stories) with the concurrency prerequisite as
  S-13.1 and the Spec's serverless-intermediates brake preserved as S-13.2.

- **2026-09-09 (fleet readiness pass — built, never run green)** — Epic 13 is 6/6 `done`
  and the code is real (`db.py` 667, `locking.py` 208, `webhook.py` 1350,
  `webhook_host.py` 246, `scheduler.py` 193), but under the realization gate the
  live-backend half is **not in effect**: `.github/workflows/herald-live-demo.yml` — the
  only thing in the estate that ever starts a listening process — is `disabled_manually`,
  its last 100 runs are 100 failures with zero successes, and its last run was 2026-08-24;
  its own header states it is "never a persistent, publicly-reachable deployment" and
  writes each job to a `${{ runner.temp }}` DB "discarded when the job ends". **A ship has
  never recorded itself.** Two corrections to the 2026-08-10 entry: the webhook path
  (`/api/herald/webhooks/on-ship`, `webhook.py:183-184`) violates the station route
  contract — `spec-pyforge-unifying-strategy` SPEC.md:497 is an Always, "station routes are
  `/stations/<name>/api/v<N>/`", and `config/asgi.py:149-150` sends every bare `/api/*`
  path to the platform FastAPI seam, so mounting the app today is a silent 404 — and
  "adopting Steward's pattern" bound only `webhook.py`'s *shape* (AD-8/AD-9), not its
  hosting: `pyforge-herald` imports nothing from `pyforge-steward` and mounts no Steward
  middleware (`webhook_host.py:77-89`), while `DW-13-6-1` records that `steward deploy
  perimeter` still cannot target an arbitrary ASGI callable (`deploy.py:484` hardcodes
  `myproject.asgi:application`). **Operator decision (fleet-readiness decision batch
  2026-09-09, row C11): there is no pull; the question re-opens as a *hosting* decision
  when the python-foundry cutover gives Herald a real perimeter.** LB-1 is closed; LB-2 and
  LB-3 are re-scoped `foundry-side`; the Spec moves `ready → in-progress`. **Status held at
  `specified`.** Vessel for the two now-actionable halves: herald Epic 19 (Stories 19.1 the
  route-contract move, 19.2 one real ship against a persistent store).

## 2026-10-26 — Herald — Moments 2–4 Missing Surface (folded from herald-moments-2-4-missing-surface)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/herald-moments-2-4-missing-surface.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/herald-moments-2-4-missing-surface.md`.*

## Herald — Moments 2–4 Missing Surface

### The Dream

Herald orchestrates **Four Moments of Proclamation** across the factory:

1. **Moment 1: Pitch** — A dream must be argued. The case made legible to non-dreamers. ✅ **READY** (Deck family spec complete)
2. **Moment 2: Progress** — A build in flight is not self-explaining. What changed, what it cost, what it unblocked. 📋 **SPECCED, UNBUILT**
3. **Moment 3: Success** — Shipping is not the same as being known to have shipped. The claim with evidence attached. 📋 **SPECCED, UNBUILT**
4. **Moment 4: Operations** — The long tail nobody announces. Fixes, updates, deprecations, end-of-life. ⚠️ **ZERO IMPLEMENTATION**

This dream addresses the **3 missing surfaces**: Moments 2, 3, and 4.

---

### Why It Matters

Herald Moment 1 (deck family) is a narrative tool for *launching* ideas. But proclamation doesn't end at launch:

- **Moment 2 (Progress)**: When we ship a new station, update a major component, or cross a milestone, who knows? A weekly/monthly artifact proving motion and explaining cost.
- **Moment 3 (Success)**: When a project ships, who knows it shipped? Success requires **claim + evidence** — not just a closed PR, but a public statement linking to proof (tests passing, metrics green, users adopting).
- **Moment 4 (Operations)**: Deprecations, security fixes, end-of-life notices — the unglamorous tail that protects users but nobody announces. Requires **proactive surfaces** (published notices, timeline archives, redirect rules).

---

### What is Real

- **Specs exist** for Moments 2 and 3 in `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/` (archived from prior work).
- **Moment 1 spec is complete** and production-ready (spec-herald-pitch/).
- **Moment 4 has zero implementation** — only a mention in the Herald Four Moments framework.

---

### Realization Log

- **2026-07** — Herald's Four Moments framework established (docs/dreams/pyforge-herald.md).
- **2026-08-01** — Moment 1 (Pitch) fleet-chain-completeness regeneration: Dream → Spec → PRD → Architecture → Epics → Stories fully grounded.
- **2026-08-02** — Identified 3 missing surfaces for Moments 2–4. Opening this dream to prioritize surface completion.

---

### Next Steps (Planning Phase)

1. **Audit existing Moment 2 & 3 specs** — retrieve from archive, assess completeness and currency.
2. **Author Moment 4 spec** — from first principles (deprecation & end-of-life proclamation workflow).
3. **Decide orchestration strategy** — separate specs/dreams per Moment, or unified Herald v2 spec?
4. **Scope surface delivery** — Moment 2 (dashboard widget?), Moment 3 (release page?), Moment 4 (archive + redirect rules?).

---

### Success Criteria

- [ ] All three Moment specs (2, 3, 4) drafted and reviewed
- [ ] Surface strategy decided (format, frequency, automation)
- [ ] Each Moment has a clear entry point in Herald CLI / web surface
- [ ] Automation identified (what triggers Moment 2 updates? Who authors Moment 3 claims?)

## 2026-10-26 — Herald's Pitch Deck — Moment 1 Orchestration (Consolidated) (folded from herald-pitch)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/herald-pitch.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/herald-pitch.md`.*

## Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)

This dream consolidates the Herald pitch-deck ecosystem: Tier 0 (Vision) + Tier 1 (Reusable Capabilities) + Tier 2 (Moment 1 Feature Orchestration). Single source of truth for Dream → Spec → Epic → Code chain.

---

### Tier 0: Vision — The Four Moments of Proclamation

Herald is the factory's *voice and visual surface*. Invisible engineering is failed engineering. Herald's work is continuous across **four moments of proclamation**:

| # | Moment | What Herald Owes | Lands As |
|---|---|---|---|
| **1** | **Pitch** — a Dream must be argued, not merely filed | the case made legible to humans who did not dream it | the deck family (THIS DREAM) |
| **2** | **Progress** — a build in flight is not self-explaining | what changed, what it cost, what it unblocked | release notables, run telemetry as imagery |
| **3** | **Success** — shipping is not the same as being known to have shipped | the claim, with the evidence attached | the release proclamation |
| **4** | **Operations** — the long tail nobody announces | fixes, updates, deprecations, decommissions | change + end-of-life notices |

Moment 1 is simply the **first** time Herald has something to do — it is not the extent of the job. This dream owns Moment 1's orchestration across 9 pyforge stations using the four Tier 1 capabilities below.

---

### Tier 1: Reusable Capabilities

#### Tier 1a: Design-Code-Bridge Framework

**Purpose:** Automate the round-trip between Design (claude.ai/design) and Code (this repo).

**The Core Problem:** Today, visual authoring and code are joined by hand. Designers manually mirror files into Design projects, work there, download, and copy back. Manual, error-prone, slow.

**The Solution:** **The prototype round-trips itself.** A persona deck starts as a seeded Design project; a human refines it visually in Claude Design; a single ask in Claude Code pulls the prototype straight into `presentations/<slug>/project/`, extracts, builds, and ships — zero downloads, zero copy-paste, conflicts caught by etags instead of overwrites.

**How It Works:**

1. **Seed (push):** Claude Code creates a Design project per deck, bound to the Modernist design system, pre-seeded with a contract-compliant starter prototype (1920×1080, Archivo, family palette).

2. **Design (human):** User iterates visually at claude.ai/design — their preferred surface, no repo mechanics.

3. **Pull (ship):** `herald deck pull <slug>` → read_file the prototype into `project/` → `npm run extract` → `npm run build` → `pixi run deck-export` → commit. The deck ships without a single manual transfer.

4. **Discipline:** Etags on every read/write so a mid-edit conflict surfaces instead of silently clobbering either side; only the **prototype** crosses the bridge (never a mirrored app tree).

**What Is Real:**
- The bridge is **realized** and proven on 7 decks in one day
- Herald CLI specced to 5 capabilities: seed / pull / watch / stale-mirror / export
- Etagged round-trip protocol established and working
- Zero manual file transfers between Design and Code

**Future:** Herald CLI full automation (v1: seed, pull, watch-mode sync, stale-mirror detection)

---

#### Tier 1b: Deckcraft Framework

**Purpose:** Generate editable PowerPoint, Markdown, infographics, and images from primitives — air-gapped, conda-forge-native.

**The Core Problem:** `marp --pptx` renders image-slides (fine for distribution, useless for editing). Decks need real, editable PowerPoint.

**The Solution:** Deckcraft is the **editable-PPTX engine** for the deck family. Markdown → PPTX generation using python-pptx + design tokens, delivering slides that are both programmatically generated and manually editable.

**How It Works:**

1. **Input:** Markdown source (`{station}.md`) + Modernist design tokens
2. **Transform:** `pixi run deck-export` → deckcraft pipeline → python-pptx
3. **Output:** `src/pptx/{station}.pptx` (editable PowerPoint with proper fonts, colors, layouts)

**What Is Real:**
- Deckcraft BMAD project registered and active
- Toolchain in place: python-pptx, pptxgenjs, marp-cli, markitdown
- Design-tokens pipeline found in Sentinel project: `tokens-to-potx.py`, `potx-to-tokens.py`, Figma-variable bridges

**Multi-Surface:** Claude Skill, MCP server for Copilot/MS365, CLI — same deck machinery serves interactive sessions, enterprise Office stacks, and headless factory runs.

---

#### Tier 1c: Video-Scripts Framework

**Purpose:** Extract narration scripts from decks and feed them into video production pipelines (bmad-manticore).

**The Core Problem:** Decks exist in isolation. Videos that could amplify them don't exist. Narration extraction is manual.

**The Solution:** **Mechanically extract narration scripts** from every deck prototype's speaker notes. Feed them to bmad-manticore, which orchestrates voice, graphics, screen recordings, and real footage into finished videos — no fabricated demos, ever.

**Three Content Classes (What Manticore Feeds On):**

1. **Raw Inputs** — Speaker notes from Design (extracted mechanically); real screen recordings of factory surfaces (console, marshal sessions, Guildhall board); real footage, never AI-generated UI.

2. **Taste & Identity** — Voice Bible (deconstructed from published transcripts: WPM, speech patterns); Production Bible (brand tokens, motion feel, CTA policy); Blacklist (LLM tells the script linter enforces); Format profiles (talking-head, screen-tutorial, voiceover-explainer, short).

3. **Orchestrated Media** — HyperFrames motion graphics (brand-themed overlays, kinetic captions); Kokoro-82M narration; MusicGen beds; AudioLDM2 SFX; approved b-roll only.

**Four Hard Gates:** Outline → Cut Plan → Graphics Beats → Final Render (no fabricated product demos, ever).

**How It Works:**

1. **Extract:** `narration-extract` task → pull speaker notes from Design proto → generate `{station}-narration-2026-08-01.md`
2. **Compose:** Herald feeds narration corpus to manticore (322 scenes extracted, first master script authored as exemplar)
3. **Render:** `mc-new` → script, edl.json cut plan, HyperFrames over real UI → incremental render → `.mp4`

**What Is Real:**
- Narration corpus: 27 files, 322 scenes, mechanically extracted from deck prototypes
- First master script: `presentations/pyforge-marshal/src/marp/pyforge-ecosystem-master-script-2026-07-31.md` (22 scene/visual/voiceover triples)
- bmad-manticore 2.0.0 installed and packaged (`recipes/bmad-manticore/`)
- Operator intake preserved verbatim in spec input

---

#### Tier 1d: Modernist-Identity Framework

**Purpose:** One visual language across all PyForge surfaces — decks, dashboards, docs, exports, videos.

**The Core Problem:** Consistency is hard. Without a shared language, artifacts diverge.

**The Solution:** **One design system binds everything:** Modernist. Flat, architectural, Archivo throughout; light `#f3f2f2`, ink `#201e1d`, one red accent `#ec3013`/`#c22a10`; visible grid, 2px rules, zero corner radius, flush-left labels, black-and-white photography.

**What It Is:**
- **The Modernist design system** project in Claude Design (tokenized stylesheet, component pages, templates)
- **Bound to all family decks** (9 pyforge stations + agentic-sdlc legacy)
- **Family grammar** codified in `presentation-deck.md` (design defaults, font-link gotchas, proven across 100+ slides)
- **Wordmark + banner assets** (agentic-sdlc Design project)

**How It Works:**
- Design tokens (Archivo, palette, grid) → drive Figma, deckcraft PPTX templates, deck engine, video production bibles
- Tokens round-trip: `tokens.json` + Figma-variable bridges + `tokens-to-potx.py` / `potx-to-tokens.py`
- Applied consistently: Decks, dashboards (`docs/dashboard/`), docs, videos (manticore uses Modernist tokens in Production Bible)

**What Is Real:**
- Modernist adopted as persona-family system; 7 decks bound; grammar codified
- Token-pipeline assets discovered in Sentinel project
- Ready for round-trip wiring (Figma ↔ PPTX ↔ deck engine ↔ video)

---

### Tier 2: Moment 1 Feature Orchestration

#### The Dream

Herald's **Four Moments of Proclamation** begins with **Moment 1: Pitch** — the case made legible to those who did not dream it. This dream **completes Moment 1** by authoring full six-act pitch decks for all **9 pyforge stations**, shipped in **multiple formats**: PPTX (editable), HTML (interactive), Markdown (version-controlled), Infographics (inline SVG), and narration scripts (companion video).

One source of truth (Design prototype). One delivery chain (Design → Code → Export). Multiple surfaces. Zero manual file transfers.

#### The Dream

Herald's **Four Moments of Proclamation** begins with **Moment 1: Pitch** — the case made legible to those who did not dream it. Today Herald has proven the deck bridge on all **9 pyforge stations**. This Dream completes Moment 1 by authoring full six-act pitch decks for each, shipped in **multiple formats**: PPTX (editable), HTML (interactive), Markdown (version-controlled), Infographics (inline SVG), and video scripts (companion narration).

One source of truth (Design prototype). One delivery chain (Design → Code → Export). Multiple surfaces. Zero manual file transfers.


### The Artifact Collection

Each of the 21 stations produces a **six-artifact export set** from one design source:

```
presentations/pyforge-{station}/
├── project/
│   └── {Station}.dc.html          ← Design prototype (SOURCE OF TRUTH, tracked ✓)
└── src/marp/
    ├── {station}.md               ← Markdown source (tracked ✓)
    ├── {station}-narration-2026-08-01.md  ← Narration script (tracked ✓)
    └── {station}-infographic.svg  ← Static infographic (tracked ✓)
└── src/pptx/
    └── {station}.pptx             ← Editable PowerPoint (tracked ✓)

Generated at build time (gitignored, regenerable):
├── src/slides/fragments/{station}-*.json  ← Marp-parsed fragments (regen)
├── dist/
│   ├── index.html                 ← Vite-built interactive deck (regen)
│   ├── assets/*.js                ← JS/CSS bundles (regen)
│   └── assets/*.css
└── {station}.mp4                  ← Companion video (regen via bmad-manticore)
```

**Optimization**: Only source artifacts (design proto, markdown, PPTX, narration, infographic) are tracked. Fragments and build outputs regenerate at build time, reducing per-deck tracked files from ~53 to ~20.

**The Six-Act Framework** (canonical structure for all 21):

1. **Cover: The Hook** — Thesis statement + hero graphic
2. **Act I: The Friction** — Problem framing (pain point)
3. **Act II: The Insight** — Solution introduction (aha moment)
4. **Act III: The Solution (Mechanics)** — 4-step delivery loop (chronological, L.A.T.C.H. Time)
5. **Act IV: Real-World Application** — Enterprise fit (L.A.T.C.H. Location)
6. **Act V: The Resolution (Future)** — Vision & scaling (L.A.T.C.H. Category)
7. **Act VI: The Action** — Payoff & CTA (command, docs link)
8. **Appendix: Personas** — Stakeholder context

**~28 slides per deck, 90KB+ class, inline SVGs, full depth.**

---

### File Locations, Workflow, and Dependency Chain

#### Physical File Structure

```
presentations/pyforge-{station}/
│
├─ project/                          ← DESIGN CLOUD (Design source of truth)
│  ├─ {station}.dc.html              [SOURCE: Design cloud, etagged]
│  ├─ {station}-cover.dc.html        [SOURCE: Design cloud, etagged]
│  └─ {station}-appendix.dc.html     [SOURCE: Design cloud, etagged]
│
├─ src/marp/                         ← MARKDOWN SOURCES (version-controlled content)
│  ├─ {station}.md                   [CREATED: npm run extract from .dc.html]
│  ├─ {station}-cover.md             [CREATED: npm run extract from .dc.html]
│  ├─ {station}-extended.md          [CREATED: npm run extract from .dc.html]
│  ├─ {station}-narration-2026-08-01.md    [CREATED: narration-extract task]
│  ├─ {station}-narration-cover-2026-08-01.md [CREATED: narration-extract task]
│  └─ {station}-infographic.svg      [CREATED: extraction/render from markdown]
│
├─ src/pptx/                         ← POWERPOINT EXPORTS (deckcraft output)
│  ├─ {station}.pptx                 [CREATED: deckcraft from {station}.md]
│  ├─ {station}-cover.pptx           [CREATED: deckcraft from {station}-cover.md]
│  ├─ {station}-extended.pptx        [CREATED: deckcraft from {station}-extended.md]
│  └─ {station}-appendix.pptx        [CREATED: deckcraft from appendix.md]
│
├─ src/slides/                       ← SLIDE FRAGMENTS (Marp parse tree)
│  └─ fragments.json                 [CREATED: npm run extract, intermediate]
│
├─ dist/                             ← BUILT OUTPUT (Vite bundle)
│  ├─ index.html                     [CREATED: npm run build (Vite)]
│  └─ assets/
│      ├─ main.[hash].js             [CREATED: npm run build (Vite)]
│      ├─ style.[hash].css           [CREATED: npm run build (Vite)]
│      └─ […more chunks…]
│
└─ {station}.mp4                     [CREATED: bmad-manticore (external)]
   (if tracked; otherwise regenerable on demand)
```

#### Seven-Step Workflow: Design → Extract → Build → Export → Ship

**STEP 1: SEED** (design-code-bridge: herald CLI)
- Input: None (first time only)
- Output: `project/{station}.dc.html` + variants (3–4 files)
- Action: `herald deck seed pyforge-marshal`
- Duration: ~30s (one-time, Design project creation)
- Tracking: ✓ **MUST TRACK** (source of truth)

**STEP 2: DESIGN** (human in Claude Design)
- Input: `{station}.dc.html` (Design project)
- Output: Updated `{station}.dc.html` (edits in Design cloud)
- Action: User refines visually; etagged changes tracked
- Duration: Hours (human authoring)
- Tracking: Synced via design-code-bridge "pull" command

**STEP 3: PULL** (design-code-bridge: herald CLI)
- Input: Updated `{station}.dc.html` from Design cloud
- Output: `project/{station}.dc.html` → `src/marp/{station}.md` (extracted)
- Action: `herald deck pull pyforge-marshal` or `npm run extract`
- Duration: <2s per deck
- Files Created: `.dc.html`, `.md` variants (5–8 files)
- Tracking: ✓ **MUST TRACK** (.dc.html design proof, .md content source)

**STEP 4a: BUILD — Fragments & HTML** (npm run build)
- Input: `src/marp/*.md` files
- Output: `src/slides/fragments.json` + `dist/index.html` + `dist/assets/*`
- Action: `npm run build` (Vite pipeline: marp parse → bundle → output)
- Duration: ~10–15s for full build
- Files Created: fragments.json, index.html, JS/CSS bundles (~50+ files)
- Regenerable: ✓ YES (deterministic, from .md alone)
- Tracking Decision:
  - ✗ GITIGNORE `fragments.json` → regenerates <1s
  - ✗ GITIGNORE `dist/` → regenerates <15s

**STEP 4b: EXTRACT NARRATION** (narration-extract task)
- Input: `project/{station}.dc.html` (Design speaker notes)
- Output: `src/marp/{station}-narration-2026-08-01.md`
- Action: `pixi run narration-extract pyforge-marshal`
- Duration: <1s per deck
- Files Created: narration `.md` files (1–2 files)
- Regenerable: ✓ YES (from Design speaker notes)
- Tracking Decision: **Decide** — needed for video pipeline

**STEP 5: EXPORT** (pixi run deck-export + deckcraft)
- Input: `src/marp/{station}.md` + Modernist design tokens
- Output: `src/pptx/{station}.pptx` + `{station}-infographic.svg`
- Action: `pixi run deck-export` → deckcraft → PowerPoint generation
- Duration: ~5–10s per deck
- Files Created: `.pptx` files + `.svg` infographics (8–12 files)
- Regenerable: ✓ YES (from .md + deckcraft engine)
- Tracking Decision: **Decide** — PPTX and SVG tracked or regenerated?

**STEP 6: VIDEO** (bmad-manticore, external pipeline)
- Input: `src/marp/{station}-narration-*.md` + screen recordings
- Output: `{station}.mp4` + optional `.edl` / `.fcpxml`
- Action: `mc-new` + render pipeline (outline → cut → graphics → render)
- Duration: ~30–60s per video (EXPENSIVE)
- Files Created: `.mp4` video file (1 file, ~100MB+)
- Regenerable: ✓ YES but EXPENSIVE (full render required)
- Tracking Decision: ✗ GITIGNORE (regenerate on demand)

**STEP 7: COMMIT & SHIP** (git → push → publish)
- Input: All staged files (tracked artifacts only)
- Output: Committed to git, pushed to origin
- Action: `git add` → `git commit` → `git push`
- Git Footprint: Only TRACKED files count; regenerable files are in `.gitignore`
- Decision Impact: Each track/ignore decision affects total repo size

#### Artifact Tracking: Tradeoff Spectrum

**AGGRESSIVE (144 tracked files for 9 stations) ← CHOSEN**
```
✓ TRACK:     Design protos (3-4), Markdown (5-8), PPTX (2-4), Narration (1-2), Infographics (0-1)
✗ GITIGNORE: Fragments (.json), dist/ (HTML), assets/ (JS/CSS), Video (.mp4)

Result:
  • Fast workflow (PPTX, HTML, narration ready immediately after git pull)
  • No rebuilds required for deliverables
  • Medium git footprint (~16 tracked files per station)
  • Video-ready (narration scripts staged for bmad-manticore)

Workflow:
  git pull → npm install → (all tracked artifacts available immediately)
  Optional: npm run build → for interactive HTML preview
  Optional: bmad-manticore → render videos from narration scripts
```

**BALANCED (120 tracked files for 9 stations)**
```
✓ Track:    Design protos, Markdown, Narration, Infographics
✗ Gitignore: Fragments, dist/, PPTX, Video
→ Result: Smaller git, PPTX regenerates (~5–10s), video-ready
→ Workflow: git pull → npm run build → pixi run deck-export → use
```

**CONSERVATIVE (100 tracked files for 9 stations)**
```
✓ Track:    Design protos, Markdown
✗ Gitignore: Fragments, dist/, PPTX, Narration, Infographics, Video
→ Result: Minimal git, everything regenerates, slower workflow
→ Workflow: git pull → npm run build → narration-extract → pixi run deck-export → use
```

---

### Dream Architecture: Layered (Option 4) ← CHOSEN

This expansion dream is **Tier 2 (Feature)** in a three-tier Herald architecture that separates **functionality** (how things work) from **features** (what gets delivered). This dream orchestrates Tier 1 capabilities to deliver Moment 1 (Pitch) across 9 pyforge stations.

#### Option 3: Capabilities-Driven

**Core Capability Dreams** (describe HOW things work):
- `design-code-bridge.md` → Framework: seed → design → pull automation
- `deckcraft.md` → Framework: markdown → PPTX generation engine
- `video-scripts.md` → Framework: narration extraction → script composition → video render
- `modernist-identity.md` → Framework: brand tokens → applied to all surfaces

**Feature/Orchestration Dreams** (describe WHAT gets delivered):
- `pyforge-herald.md` → Vision: Four Moments of Proclamation
- `herald-pitch-family-expansion.md` → Feature: Pitch Expansion using all capabilities

**Pros:** Clear separation (mechanics vs delivery)  
**Cons:** Requires mentioning capabilities in Pitch Expansion dream

#### Option 4: Layered (Tier Model) ← CHOSEN

**Tier 0 — Vision** (overarching framework):
- `pyforge-herald.md` → Four Moments of Proclamation (Pitch, Progress, Success, Operations)

**Tier 1 — Capabilities** (independent functionality, reusable across all Moments):
- `design-code-bridge.md` → Design ↔ Code round-trip (seed/pull/watch/stale-mirror)
- `deckcraft.md` → Markdown → PPTX generation engine
- `video-scripts.md` → Narration extraction → script composition → video pipeline
- `modernist-identity.md` → Brand tokens + application rules (Archivo, palette, grid)

**Tier 2 — Features** (orchestrations that compose Tier 1 into deliverables):
- `herald-pitch-family-expansion.md` (THIS DREAM) → **Moment 1 (Pitch) Feature**
  - **Orchestrates**: design-code-bridge + deckcraft + video-scripts + modernist-identity
  - **Produces**: 6 artifact types (Design protos, Markdown, PPTX, Narration, Infographics, Video)
  - **For**: 9 pyforge stations
  - **Tracked**: 144 files (Aggressive strategy)
  - **Future**: Moments 2–4 will be separate Tier 2 features using the same Tier 1 capabilities

**Pros:** Clear hierarchy; Capabilities are reusable; each Moment is independent; scales as new features arise  
**Advantage:** When Moment 2 (Progress) is specced, it can reuse all Tier 1 capabilities

#### Option 5: Domain-Separated (Process vs Artifact vs Tech vs Vision)

**Process Dreams** (how information flows):
- `design-code-bridge.md` → Design → Code round-trip workflow
- `video-scripts.md` → Narration → Video rendering workflow

**Artifact Dreams** (what gets produced and tracked):
- `herald-pitch-family-expansion.md` → Pitch decks: file locations, artifact types, tracking decisions

**Enabling Technology Dreams** (capabilities, tools, engines):
- `deckcraft.md` → PPTX generation engine
- `modernist-identity.md` → Brand token system

**Vision Dreams** (overarching purpose):
- `pyforge-herald.md` → Four Moments of Proclamation

**Pros:** Very clear domain boundaries, each dream has a single clear purpose  
**Cons:** 6 files, but each domain is atomic and understandable

#### Option 6: Factory Model (Input → Transform → Output)

**Input Source Dreams** (where data comes from):
- `design-code-bridge.md` → Input framework: Design prototypes from cloud (seed/pull)

**Transform Engine Dreams** (processing, generation):
- `deckcraft.md` → Transform: markdown → PPTX
- `video-scripts.md` → Transform: narration → video

**Output/Delivery Dreams** (what leaves the factory):
- `herald-pitch-family-expansion.md` → Output: 6 artifact formats for Pitch decks

**Governance/Constraint Dreams** (rules applied everywhere):
- `modernist-identity.md` → Constraints: brand tokens bound to all outputs
- `pyforge-herald.md` → Constraints: Four Moments framework governs all Herald work

**Pros:** Mimics factory mental model (inputs → processes → outputs)  
**Cons:** Governance dreams are meta-level, might be confusing

#### Comparison Table

| Model | Files | Functionality | Features | Clarity |
|-------|-------|---------------|----------|---------|
| **Option 3** (Capabilities-Driven) | 6 | ✓✓ Clear | ✓✓ Clear | Good |
| **Option 4** (Layered Tiers) | 6 | ✓✓ Tiered | ✓✓ Clear | **Best** |
| **Option 5** (Domain-Separated) | 6 | ✓✓✓ Crisp | ✓✓ Clear | **Excellent** |
| **Option 6** (Factory Model) | 6 | ✓✓ Clear | ✓✓ Clear | Good |

**Recommendation:** **Option 4 (Layered)** or **Option 5 (Domain-Separated)** are strongest:
- **Option 4:** Clear hierarchy; Tier 1 capabilities are reusable for Moments 2–4
- **Option 5:** Crispest separation of concerns; easiest to understand what each dream owns

---

### Artifact Optimization Strategy (Aggressive)

**Decision**: Aggressive strategy (144 tracked files for 9 stations).

Today's 14 decks produce **270 tracked files** across design-code-bridge (design protos, markdown, PPTX, narration). The 9 pyforge-station Pitch Expansion will follow the **Aggressive strategy**, tracking all source-of-truth and final deliverable artifacts while gitignoring intermediate build outputs:

| Category | Artifact | Count | **Aggressive** | Regenerable? | Why |
|----------|----------|-------|---|----------|-------|
| **Source of Truth** | `{Station}.dc.html` (design protos) | 3-4 | ✓ TRACK | No | Design prototypes are immutable, etagged authority; capture authoring decisions |
| **Source of Truth** | `{station}.md` + variants (marp) | 5-8 | ✓ TRACK | From `.dc.html` | Version-controlled content; represents narrative structure and structure |
| **Source of Truth** | `{station}.pptx` + variants (editable) | 2-4 | ✓ TRACK | From `.md` + deckcraft | Final deliverable; preserves formatting/layout choices |
| **Source of Truth** | `{station}-narration-*.md` (video scripts) | 1-2 | ✓ TRACK | From Design notes | Version-controlled content for video pipeline |
| **Source of Truth** | `{station}-infographic.svg` (inline) | 0-1 | ✓ TRACK | From `.md` extract | Final deliverable; preserves visual design choices |
| **Build Artifact** | `src/slides/fragments/*.json` (marp parse) | 1 | ✗ GITIGNORE | `npm run extract` | Intermediate parse tree; regenerates in <1s |
| **Build Artifact** | `dist/index.html` (vite bundle) | 1 | ✗ GITIGNORE | `npm run build` | Bundled HTML; regenerates in <5s |
| **Build Artifact** | `dist/assets/*.{js,css}` (bundles) | 3-6 | ✗ GITIGNORE | `npm run build` | JS/CSS bundles; regenerate in <5s |
| **Build Artifact** | `{station}.mp4` (video render) | 0 | ✗ GITIGNORE | `bmad-manticore` | Video; regenerate on demand (expensive) |

**Key design principle**: The **source of truth** (Design proto) is immutable and authored once; everything else either derives from it or is a deliberate export format. Gitignoring intermediate parsing/bundling cuts the footprint by 62% without losing auditability (all source traces back to one Design file per station).

---

#### Per-Station Customization

The framework stays constant. The content changes:

- **Copy/Content** — Thesis, pain point, solution pillars, ecosystem modules, personas (station-specific)
- **Visual Metaphors** — Domain-appropriate diagrams and symbols (warden: lattices/gates; marshal: policy composition; atlas: pipeline stages)
- **Color Accents** — Brand palette applied consistently (Modernist tokens)
- **Narration** — Station-specific speaker notes extracted for video production

### The Workflow (Four Stages)

#### Stage 1: Spec & Content Generation (this Dream → bmad-spec)

Input: This Dream + the six-act framework + per-station briefs.

Output: **Spec-Herald-Pitch-Expansion** (one SPEC kernel capturing):
- The framework (six acts, L.A.T.C.H. principles, visual strategy per act)
- 21 station entries (slug, thesis, domain, pain point, solution pillars, ecosystem vision, personas)
- Design seeding contract (Modernist-bound starter prototype)
- Export checklist (all formats, per-station)

#### Stage 2: Design Authoring (Human, Claude Design)

Input: Design projects seeded per-station (via `design-code-bridge` seed).

Process:
- Human refines prototype visually at claude.ai/design
- Edits are tracked by etag (conflicts caught, no overwrites)
- One prototype per station, 1920×1080, Archivo, brand palette

Output: 21 Design prototypes, each with speaker notes (fed to narration extraction).

#### Stage 3: Code & Export (Herald + deckcraft + video-scripts)

Input: 21 Design prototypes.

Process:
1. **Pull** via `design-code-bridge` (Claude Code: "pull {station}" → read_file + etagged safety)
   - Output: `{Station}.dc.html` → tracked in git ✓
2. **Extract** via `npm run extract` (markdown source from `.dc.html`)
   - Output: `{station}.md` → tracked in git ✓
3. **Export** via `pixi run deck-export` + deckcraft:
   - `.pptx` (editable, python-pptx + deckcraft) → tracked ✓
   - `.svg` infographic (inline, no raster) → tracked ✓
4. **Build** via `npm run build` (HTML5 deck)
   - Parses `.md` → `src/slides/fragments/*.json` (gitignored, regenerable)
   - Builds vite bundle → `dist/index.html` + `dist/assets/*` (gitignored, regenerable)
5. **Narration** via `narration-extract` task:
   - Pull speaker notes from Design
   - Generate `*-narration-2026-08-01.md` → tracked ✓
6. **Video** via `bmad-manticore`:
   - Take narration + screen recordings + bibles
   - Render `.mp4` (Kokoro voice, HyperFrames graphics, real UI) (gitignored, regenerable)

Output: 
- **Tracked (~144 files)**: Design protos (3-4 each), markdown sources (5-8 each), PPTX exports (2-4 each), narration scripts (1-2 each), infographics (0-1 each)
- **Regenerable (rebuilds on `npm install && npm run build`)**: Fragments (.json), dist/ (HTML), assets/ (JS/CSS)
- **Total footprint**: ~16 tracked files per station × 9 = **144 files** (vs. 178 today unoptimized)

#### Stage 4: Commit & Ship

Input: 126 artifacts.

Output: 21 decks across 6 formats, tracked in git, shipped to:
- `presentations/pyforge-{station}/dist/` (artifacts)
- Published to rxm7706.github.io (HTML + infographics)
- Slack notifications (via video-scripts moment 2: Progress)
- Release proclamations (via video-scripts moment 3: Success)

### What This Is Not

- Not new deck-authoring infrastructure (design-code-bridge already proven)
- Not a new export backend (deckcraft handles PPTX; `deck-export` handles others)
- Not a new video pipeline (manticore is upstream; this Dream feeds it)
- Not fabricated demos (all screen recordings are real)

It is the **orchestration of existing capabilities** to expand Moment 1 (Pitch) across the entire 21-station fleet in parallel, with automated round-trip and multi-format export.

### Kinships

[[pyforge-herald]] (the Four Moments framework) · [[pyforge-herald|design-code-bridge]] (round-trip automation) · [[pyforge-herald|modernist-identity]] (brand consistency) · [[pyforge-herald|deckcraft]] (PPTX backend) · [[pyforge-herald|video-scripts]] (narration + companion videos) · [presentation-deck](../how-to/presentation-deck.md) (export formats and artifact tree).

### Success Criteria

- [ ] 9 Design projects seeded (one per pyforge station), all using Modernist identity tokens
- [ ] 9 prototypes authored and refined per six-act framework (Design layer)
- [ ] 9 × 6 artifact sets exported and committed:
  - [ ] Design prototypes (.dc.html) tracked
  - [ ] Markdown sources (marp) tracked
  - [ ] PPTX exports (editable) tracked
  - [ ] Narration scripts (.md) tracked
  - [ ] Infographic SVGs tracked
  - [ ] Built outputs (fragments, dist/, assets/) gitignored (regenerable)
- [ ] All HTML decks render and pass `dashboard-check`
- [ ] All PPTX files editable in PowerPoint
- [ ] All infographics render as inline SVG (none are raster)
- [ ] All narration scripts extracted and available for video-scripts integration
- [ ] Zero manual file transfers between Design and Code (design-code-bridge automation end-to-end)
- [ ] Total tracked footprint: ~144 files (vs. 178 today unoptimized)

### Realization Log

- **2026-08-01 (this session)** — Dream seeded from user's vision of "Herald has moments, supporting capabilities, and a master dream that can create a collection of artifacts." Six-act framework (canonical reference) authored as the structural backbone. Architecture: one source (Design) → multiple outputs (PPTX, HTML, MD, SVG, MP4).

## 2026-10-26 — Programmatic OOXML shapes for information-dense slides, if the .pptx pipeline ever exists (folded from pptx-custom-shapes)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/pptx-custom-shapes.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pptx-custom-shapes.md`.*

## Programmatic OOXML shapes for information-dense slides, if the .pptx pipeline ever exists

### The Dream

Cards, metric boxes, tables, and section labels with no template placeholder to fill — plus a
real text-autofit engine using actual font measurement, not a guess — so an agent never
hand-writes OOXML fill/font XML for slide content a template didn't anticipate. This capability
is meaningless without [[pptx-deck-generation]]'s own template-parse-then-fill pipeline existing
first: there is no "open canvas layout" to place custom shapes on without a `.pptx` template
pipeline to place them inside. Strictly downstream of that Dream, not independent of it.

### What it looks like when real

Not scoped independently — see [[pptx-deck-generation]]'s own "What it looks like when real."
IF that Dream is ever built (contingent on Marp's existing `.pptx` export proving genuinely
inadequate, per its own open question), this capability would be its natural extension for
content a template placeholder can't express: `add_card`/`add_metric_box`/`add_table`/
`add_section_label`-shaped calls, an autofit engine using real font metrics (this repo already
depends on Pillow transitively in several environments, so `ImageFont`-based measurement is not a
new dependency class), and WF-brand-specific color/font mapping replaced with whatever this
repo's own `.pptx` template (if one is ever built) actually uses.

### What is real

Nothing — this Dream has no independent existence from [[pptx-deck-generation]], which itself has
no independent existence from a verified, named audience need for editable `.pptx` output beyond
what Herald's existing Marp export already produces.

### Constraints

- **Does not exist without [[pptx-deck-generation]] existing first.** This is not a standalone
  capability — building it before the base template-fill pipeline would have nothing to attach to.

### Non-goals

- **Not chart or SmartArt creation** — carried from the source's own v1 scope unchanged.
- **Not dynamic data binding** — static content only, carried unchanged.

### Full feature audit against `custom-branded-elements`

| Source feature | Disposition | Why |
|---|---|---|
| `add_card`/`add_metric_box`/`add_table`/`add_section_label` shape API | **Pattern retained, contingent** | Sound design; contingent entirely on [[pptx-deck-generation]] existing. |
| Text autofit engine (Pillow-based real font measurement) | **Pattern retained, contingent** | Same — genuinely useful IF the base pipeline exists; Pillow itself is not a new dependency class for this repo. |
| WF brand color-to-scheme-slot mapping | **Omitted, WF-specific** | No PyForge-branded template exists to map colors for. |
| Theme font refs (`+mj-lt`/`+mn-lt`) | **Implementation detail, deferred** | Not a scoping decision — carried forward as a "when built" concern. |

### Kinships

[[pptx-deck-generation]] (the base Dream this one is strictly downstream of — not a peer, a
dependent) · [[deck-visual-qa]] (the sibling Dream that would validate this one's output, same
source batch)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit,
  alongside its two sibling deck dreams. Deliberately framed as non-independent from
  [[pptx-deck-generation]] rather than duplicating that Dream's own "is a `.pptx` pipeline even
  needed" open question here — one open question, named once, inherited by both dependents.
- **2026-09-09 (fleet readiness pass — built, unexercised)** — § *What is real* ("Nothing —
  this Dream has no independent existence…") is superseded: Story 15.2 shipped
  `add_card` / `add_metric_box` / `add_table` / `add_section_label` plus `fit_text`'s Pillow
  `ImageFont` autofit inside `pptx_pipeline.py`, reached from `content_plan.json`'s optional
  `"shapes"` list. Unexercised — no dense slide has been run through it, because no
  `content_plan.json` exists anywhere in the tree, so the "densest six-act appendix slide"
  signal has never been executed. **Status held at `specified`.** Vessel: herald Epic 19
  Story 19.4 — the same real-deck render that exercises its parent
  [[pptx-deck-generation]] — per the fleet-readiness decision batch 2026-09-09 row C6.

## 2026-10-26 — A second, PowerPoint-native deck pipeline, if this repo ever needs editable .pptx output (folded from pptx-deck-generation)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/pptx-deck-generation.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pptx-deck-generation.md`.*

## A second, PowerPoint-native deck pipeline, if this repo ever needs editable .pptx output

### The Dream

The source dream's template-parse-then-fill pattern — parse a `.potx`/`.pptx` template once into
a machine-readable `spec.json` contract, let an agent write a `content_plan.json`, mechanically
fill placeholders without touching OOXML by hand — solves a real, well-documented problem for
audiences that need an EDITABLE PowerPoint file, not a browser deck. This repo already has a deck
pipeline, but it produces a genuinely different artifact: Herald's own bridge (`bridge.py`,
`deck_pipeline.py`) round-trips through Claude Design's MCP tools to a React+Vite HTML slide deck
(`docs/how-to/presentation-deck.md`'s own workflow), never a `.pptx` file. This Dream is not a port
of that pipeline — it shares no code with it — it is a SECOND, parallel capability for the one
thing the HTML pipeline structurally cannot produce: a file PowerPoint itself can open and edit.

### What it looks like when real

Left thin — no scoped feature, because no PyForge audience has been identified that needs an
editable `.pptx` specifically, as opposed to the browser deck the existing pipeline already
produces:

- IF a real audience need for editable `.pptx` output emerges (an external presentation to
  reviewers who expect PowerPoint, not a URL), the source dream's template-parse-then-fill
  discipline — `spec.json` as the machine-readable contract, `content_plan.json` as the agent's
  own content mapping, mechanical placeholder filling never touching raw OOXML by hand — is a
  sound, well-proven pattern to build against, given the source dream's own maturity (its own
  Realization log shows 5 of 6 epics complete, the most implementation-ready blueprint of any
  dream in this whole batch).
- This Dream and Herald's existing HTML deck pipeline would coexist, not compete — different
  output formats for different audiences, sharing only the top-level "generate a deck" concept,
  not any code.

### What is real

Herald's own deck pipeline already produces a real `.pptx` file, shipped, not merely planned:
`docs/how-to/presentation-deck.md`'s `deck-export` step writes a dated PowerPoint export to
`src/pptx/<slug>-YYYY-MM-DD.pptx`, derived from the deck's Marp narrative — confirmed by reading
the spec directly (§ the artifact dependency tree names the exact path and derivation). This
substantially narrows this Dream's actual premise: it is NOT "nothing produces `.pptx` here,"
it's "the existing `.pptx` is a Marp-markdown-to-slides conversion, not a template-positioned fill
the way the source dream's `python-pptx`-based approach guarantees." Whether that distinction
matters — whether Marp's own PPTX fidelity (shape/text positioning, WF-brand-equivalent layout
precision) is good enough for whatever audience would consume it — is unverified and is the real
open question this Dream should resolve before any code, not "build a second pipeline because
none exists."

### Constraints

- **Not a fork or reimplementation of Herald's existing deck pipeline.** Different artifact
  format's underlying mechanism (`python-pptx` template-fill vs. Marp markdown-conversion),
  deliberately separate code paths if both end up existing.
- **Verify Marp's existing `.pptx` output is actually insufficient before building this.** See
  "What is real" — a real `.pptx` already ships; this Dream is only justified if that export's
  fidelity is concretely inadequate for a named audience, not by default.

### Non-goals

- **Not a replacement for the HTML/React deck pipeline** — that pipeline's own strengths (live
  URL, keyboard nav, presenter view) are not this Dream's concern.
- **Not multi-brand support** — carried from the source's own v1 scope (WF-branding-only)
  unchanged; if built, this repo has no equivalent brand template to target yet either.

### Full feature audit against `deck-generation-pipeline`

| Source feature | Disposition | Why |
|---|---|---|
| Template parse → `spec.json` contract | **Pattern retained, no target template** | Sound design; no PyForge-branded `.potx` template exists to parse yet. |
| `content_plan.json` → mechanical fill | **Pattern retained** | Same reasoning — the mechanism is sound, no current trigger to build it. |
| Slide cloning between presentations (images/charts) | **Omitted, no target** | No current multi-deck rebranding need identified. |
| `[Content_Types].xml`/`docProps/app.xml` patching | **Implementation detail, deferred** | Not a scoping decision — carried forward as a "when built" concern. |
| 21 WF slide layouts (16:9, WF Sans) | **Omitted, WF-specific** | No PyForge-branded template exists; this repo's own template, if ever built, would need its own layout set. |

### Kinships

[[pyforge-herald]] (the actual owner — decks are Herald's domain in real PyForge, corrected from
the source's own `owner: scribe` label; scribe's real current scope is team-memory
capture/compile/promote/recall, unrelated) · [[pptx-custom-shapes]] and
[[deck-visual-qa]] (the two sibling dreams from the same source batch, extending and validating
this one respectively — captured together, same ownership correction applies to both)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Ownership corrected from the source's own `owner: scribe` label: checked directly and found
  decks are Herald's domain in this repo (`deck_pipeline.py`, `bridge.py` exist there), while
  scribe's actual current scope (`capture.py`/`compile.py`/`promote.py`/`recall.py`) is team-memory,
  unrelated to decks. First draft understated the overlap — re-checked `presentation-deck.md`
  directly and found Herald's `deck-export` step already ships a real, dated `.pptx` per deck
  (`src/pptx/<slug>-YYYY-MM-DD.pptx`, Marp-derived). Corrected the premise from "nothing produces
  `.pptx` here" to the narrower, real open question: whether Marp's conversion fidelity is
  actually inadequate for some named audience — unverified, and the thing to check before any
  code, not assumed.
- **2026-09-09 (fleet readiness pass — built, unexercised)** — Epic 15 is `done` (15.1
  template-parse-then-fill, 15.2 shapes + autofit); `pptx_pipeline.py` (1057 lines) ships
  both CAPs, with `herald deck pptx-spec` / `herald deck pptx-fill` on the CLI
  (`cli.py:342-386`, dispatched `:766-769`), and the interim template is committed and
  git-tracked at `src/pyforge/herald/templates/pyforge-deck-template.pptx`. § *What is
  real* above is superseded: it still frames this as an unanswered "is Marp good enough"
  question, which 2026-08-22 answered (Marp's export is background-image slides with zero
  text runs). The Spec's one open question is **closed this date** — 15.1 answered it with
  a third option neither branch named, python-pptx's own bundled Office theme adopted
  verbatim and regenerated by `scripts/generate_default_template.py`, because a hand-derived
  `.potx` needs custom slide *layouts* python-pptx cannot author without forbidden raw-OOXML
  surgery and an operator-supplied `.potx` needs a human who was not present. A branded
  `.potx` remains owed and is a `--template` flag, not a code change. **Status held at
  `specified`**: no station deck has been rendered through the pipeline — no
  `content_plan.json` exists anywhere in the tree, and every `.pptx` under
  `presentations/*/src/pptx/` is a dated Marp export from 2026-07/08. Vessel: herald Epic 19
  Story 19.4 (render one real station deck), per the fleet-readiness decision batch
  2026-09-09 row C6.

## 2026-10-26 — The public Pages root is one dossier, not two copies (folded from pyforge-pages)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 48.1). The body below is `docs/dreams/pyforge-pages.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pyforge-pages.md`.*

## The public Pages root is one dossier, not two copies

### The Dream

The factory already has a public GitHub Pages tree (`docs/dashboard/`) and a
Kedro-Viz export that lives under it. What it does **not** have is a single
checked-in source for the **PyForge dossier** — the narrative, figures, and
standalone infographics that explain the estate. Those have lived in a published
artifact. Updating the dossier and updating the site were two acts of copying,
and they drifted.

The Dream is **one YAML, many renders**. `docsite/content/dossier.yml` is the
source of truth. The Pages landing page, the dossier HTML, the infographic
gallery, and the Claude Artifact build are all renders of that file. Kedro-Viz
stays at `/kedro-viz/` and is linked from the new landing page. There is still
exactly one Pages deployment.

> A number that is true in the repo and false on the public page is not a
> published number.

### Why now

A complete site already exists as a git bundle (`pyforge-pages.bundle`, tip
`5b6a540477`, based on `50504e52e` when `main` was that commit). Landing it
without a Dream and Spec would skip the contract this repo requires, and would
leave foundry with no five-field to rebuild from — the exact failure
`foundry-regenerate-not-fold` exists to prevent.

Today on `main` (measured 2026-09-13, `origin/main` `08613ac92f`):

| Finding | Where it is visible |
|---|---|
| Pages publishes `docs/dashboard/` as the site root | `.github/workflows/dashboard.yml` uploads that path |
| The live content of that tree is Atlas Kedro-Viz | workflow comment; `kedro-viz-publish.yml` stages `docs/dashboard/kedro-viz/` |
| There is no `docsite/`, no `feature.site`, no `site-check` | `pixi.toml` / repo root |
| The Guildhall generator is retired; Lane 1 `/console/` is the operator console | `dashboard.yml` header; steward 30.2 |
| The dossier is not a tracked source | nothing named `dossier.yml` on `main` |

### What it looks like when real

- **Edit the YAML, rebuild, publish.** A sentence change is a line in
  `docsite/content/dossier.yml`. `pixi run -e site site-check` proves the
  render. Push to `main` rebuilds Pages.
- **The landing page is the site.** `https://rxm7706.github.io/local-recipes/`
  is the dossier landing page. Kedro-Viz remains at `/kedro-viz/` and is linked
  from it.
- **One Pages deploy.** `dashboard.yml` builds the site *into* `docs/dashboard/`
  and is still the only workflow that calls `deploy-pages`. A second deploy
  would race and wipe Kedro-Viz.
- **Figures have a check.** `site-verify` compares marked dossier stats to the
  source tree. CI annotates drift and never blocks a deploy — editorial
  judgment stays human.
- **The artifact is a render too.** `dist/artifact/dossier.html` is the Claude
  Artifact host shape (no wrapping `<html>`), from the same templates.
- **Foundry can rebuild it.** After Story 54.5, B authors the equivalent
  Dream/Frame/Spec and the `docsite/` + `feature.site` + Pages-build step from
  this contract. A is the pin. No `_bmad-output` rsync, no comment-copy.

### Constraints / Non-goals

- **One Pages deployment.** Never a second `deploy-pages` job.
- **`build.py` owns only its outputs.** Never a blanket `rmtree` of
  `docs/dashboard/` — Kedro-Viz is Atlas-owned and stays.
- **New pixi feature only.** `environment.yaml` (`-e build` export) stays
  byte-identical; the `site` feature is not on that export.
- **`maintenance` label** on the landing PR (nothing under `recipes/`).
- **Verify is advisory** in CI. Local `site-verify` may exit 1; the Action
  `continue-on-error`.
- **Not Lane 1.** `/console/` stays the operator console.
- **Not a fold.** This is not Story 44.4 / `src/shared/packages/` path-rename.
- **Infographic sources are not rewritten.** The build injects a back-link bar
  only.

### Kinships

[[pyforge-herald]] (proclamation — the public dossier is Herald's voice) ·
[[factory-console]] (the Pages tree this landing page now occupies; generator
retired, Kedro-Viz kept) · [[pyforge-steward]] (Pages deploy duct;
`dashboard.yml`) · [[pyforge-atlas]] (Kedro-Viz at `/kedro-viz/`) ·
[[deck-family-currency]] (infographics the gallery publishes; facts stay on
their own ledger) · [[foundry-regenerate-not-fold]] (B rebuilds this surface
from the Spec after 54.5; A pins) · [[pyforge-unifying-strategy]] (its
`spec-python-foundry-cutover`: cargo on the kernel move list, not a 44.4 fold;
since 2026-09-25 `fnd:CAP-14` makes this dossier the cutover's control plane —
herald Story 26.1).

### Realization log

- **2026-09-13** — Seeded from the operator-supplied git bundle and the
  accompanying Pages/CI gates. Next act: `bmad-spec` under `pyforge-herald`,
  then Story 22.1, then rebase the bundle onto `origin/main` in a steward
  worktree.
