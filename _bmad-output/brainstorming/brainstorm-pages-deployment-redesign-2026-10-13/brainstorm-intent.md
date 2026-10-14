# Intent — the PyForge GitHub Pages deployment, redesigned (2026-10-13)

Topic: redesign the PyForge GitHub Pages deployment (docsite/ + docs-site/ + dashboard, one Pages artifact); project pyforge-herald.
Goal: simpler, cheaper, one generator if possible, upstream parity, foundry-rebuildable, no bot commits, fewer deploys.
Mode: autonomous. Source: `_bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/.memlog.md` (status complete).

## The finding

The pain is not two sites. It is four separately minted mechanisms glued by 3,830 lines of bespoke code (assemble_pages.py 720, docsite/build.py 867, seven helper scripts):

1. a Jinja site, docsite/ (minted 2026-09-13);
2. a Starlight site, docs-site/ (minted 2026-10-05; Astro 7.2.8 / Starlight 0.42.1, YAML file() loader available);
3. a git-committed dashboard export, docs/dashboard/kedro-viz/ (2026-08; 11 MB, 215 files, frozen since 2026-08-15, kedro-viz-publish.yml paused manually);
4. a Python assembler with its own link, origin and redirect logic, deployed by dashboard.yml, a workflow named for a retired console, which fires on every push to main.

Measured (GitHub API total_count, not the gh run list cap of 200):

- dashboard.yml since 2026-09-13: 1342 runs, 720 successful deploys, 621 cancelled, 1 failure (about 24 deploys a day). docsite-check.yml ran 522 times.
- About 1330 first-parent pushes to main in 30 days, up to 176 in one day.
- Filter replay over those 30 days of first-parent commits: the broad docsite-check filter (docs/** etc.) would still deploy 385 times, driven by docs/dreams (515 touches) and docs/governance (143), neither of which Starlight publishes. A narrow published-inputs filter (four quadrants, index/404, map.yaml, docs/dashboard, docs-site, docsite, presentations, the workflow) would deploy 132 times: a 5.5x cut from 720 with zero loss of freshness. Quadrant docs alone 91, presentations alone 35.
- 2026-10-06: a deploy sat in waiting for six days with 199 cancelled runs behind it and nobody saw. timeout-minutes cannot cover a job stuck in waiting; stuck detection (steward 99.7 stuck_rules, doctor 43.1) is the fix.
- Today's run: 17 dossier claims drifted, advisory, step green. Nobody reads an advisory annotation on a workflow that runs seven times a day.
- 2026-10-08: Google Fonts on 45 pages, fixed by vendoring 25 woff2 files with a hand-recorded sha256 table; the same day docs-site failed to build from a clean checkout (untracked lib/ helper).
- build.py reads presentations/ (658 MB) so the runner clones it, with fetch-depth 0; nothing in the build needs history.

Non-obvious links the Spec should carry:

- The docsite/ vs docs-site/ name clash dissolves for free under M3 (docsite/ becomes docs-site/src/herald); no rename story if M3 is committed to.
- The Kedro-Viz bot-commit pattern and the stuck-in-waiting incident share one root: a deploy decoupled from the change that should cause it. Path filters and artifact handoffs fix both.
- The dossier-numbers drift and the Google Fonts incident are one class, a check nobody reads. The cure is structural: computed stats, @fontsource via npm, a CSP meta so a violation shows in the browser.
- MyBMAD answers itself through the Y3 placement rule; its Pages twin is a build-time board snapshot herald renders from the eight ledgers.
- Upstream parity (BMAD-METHOD docs.yaml shape + Starlight) is the deciding value because foundry B must rebuild this surface; every bespoke line is rebuild cost.

## Chosen direction: M6 staged

Each stage ships independently and each reduces bespoke lines. Placement rule for every surface, now and later (Y3): dynamic, authenticated or per-user belongs to Lane 1 (/console/, MyBMAD); static, public and build-time belongs to Pages (docs, dossier, decks, board snapshot). The same rule already retired Guildhall to Lane 1 and made Kedro-Viz a static export.

### M1: trigger, cost, hygiene (one story, or one small epic)

- Changes: dashboard.yml gets the narrow published-inputs path filter plus workflow_dispatch; fetch-depth 1 (verify deck_versions does not read git log); sparse checkout of presentations/*/project/*.html only; concurrency group pages-build with cancel-in-progress for the build job, group pages without cancel for deploy; timeout-minutes on build; the deploy job is skipped when the built tree hash equals the last deployed hash (hash kept in a repo variable or cache); a scheduled liveness probe (live root last-modified vs latest docs commit) as a doctor advisory.
- Retired: import_artifact.py (302 lines, one-time migration, done); legacy root redirect stubs on a dated sunset (open question 3); the hygiene items in the last section.
- Done when: cancelled runs per 30 days under 10.

### M2: one workflow in upstream shape, handoffs not commits (one epic)

- Changes: one pages.yml in BMAD-METHOD docs.yaml shape (build on pull_request and push, deploy on push to main only; SITE_URL repo variable; setup-node from .nvmrc; pixi only where Python is needed). docsite-check.yml folds in, one set of path filters, no twin drift. The PR build uploads the built site as an artifact and posts one comment with the link; merge promotes that reviewed artifact (build once, promote; deployed bytes are reviewed bytes). Kedro-Viz arrives as a workflow artifact: kedro-viz-publish uploads kedro-viz-export (retention 90d), the Pages build downloads the newest successful one, and none found means the mount is skipped and the nav hides the tile, no hard failure. actions/configure-pages is authoritative on github.com and GHE. The same artifact is zipped as a release asset so the airgap host pulls reviewed bytes instead of rebuilding behind a mirror. Steward owns the duct (pages.yml, budget, stuck detection; a steward pages build|deploy|status duty mirroring steward deploy dashboard); herald owns what is inside /herald/. The fleet board (IA4) and guild status (IA5) land here as small renderers over JSON that already exists.
- Retired: docsite-check.yml; docs/dashboard/kedro-viz/ bytes in git; pyforge.herald.pages_second_host and export_pages_host_env.py (the how-to shrinks to "Settings > Pages > GitHub Actions"). The assembler stays but shrinks.
- Done when: zero commits by github-actions[bot] on main and docsite-check.yml deleted.

### M3: one generator, docsite/ dissolved (one epic, after M2, when herald's deck pipeline work is quiet)

- Changes: Astro renders everything. Dossier = content collection over dossier.yml, one page per section; the 14 block macros become 14 .astro components; stats blocks with check: take their value from the measurer at build (verify_claims becomes a producer); prose carries a measured-on stamp. Gallery = Astro page over import.meta.glob of presentations/*/project/*Infographic standalone.html copied verbatim to public/. Family pages = src/pages/herald/decks/[slug].astro reading presentations/<slug>/facts.yaml. Fonts via @fontsource imports. publicDir mounts the kedro-viz export; mount collisions surface as duplicate-route build errors. Redirects = astro.config redirects map generated from the 44-row JSON. map.yaml (doctor) gains herald rows and orders the whole site: Starlight sidebar, herald menu and landing tiles from one registry. Pagefind indexes the whole artifact. starlight-llms-txt emits /llms.txt and /llms-full.txt. Link check = vendored validate-doc-links.js plus lychee --offline over the build; origin check = a 30-line allowlist (every absolute URL shares the configured origin) plus a CSP meta default-src 'self'. Astro runs last and consumes herald output as data. Starlight theme tokens on every page; a footer "built from <sha> at <UTC>, deployed by run <id>"; a site-health tile on the dossier (last deploy, run count this month, cancelled streak, export age).
- Retired: Jinja and docsite/build.py; assemble_pages.py; the dist/ second output tree (site-check becomes pages-check); the 300-line cross-origin scanner and the custom link walker; the 25 vendored woff2 files and their sha256 table; docsite/ as a top-level directory (content moves to docs-site/src/content/dossier/ and docs-site/src/pages/herald/).
- Done when: docsite/ deleted and bespoke Python under docs-site/ under 300 lines.

## Target site map (what it looks like when real)

| Section | URL | Feed (existing CLI or file) | Owner | Refresh | Stage |
|---|---|---|---|---|---|
| Home (IA1) | `/` | generated Starlight landing from map.yaml + site.yml: hero, four doors (Docs, Overview, Status, Decks), built-from footer; never hand-written | herald | per deploy | M3 |
| Docs shelf (IA2) | /docs quadrants, URLs unchanged | docs/ via doctor map.yaml (Starlight) | doctor (registry), herald (site) | per merge | today; M1 keeps |
| Overview + Dossier (IA3) | `/herald/` | dossier.yml with computed stats + presentations/<slug>/facts.yaml per station + status.json tiles | herald | per deploy; prose shows measured-on date | today (Jinja); Astro render in M3 |
| Infographics (IA3) | `/herald/infographics/` | presentations/*/project/*Infographic standalone.html served verbatim | herald | per deploy | today; publicDir in M3 |
| Decks (IA3) | `/herald/decks/<slug>/` | presentations/<slug>/facts.yaml (CAP-35/53/55); one dated export per kind, date shown, git history for the rest | herald | per deploy | today; dynamic routes in M3 |
| Fleet board (IA4) | `/status/` | sprint-ledger-query --format json + scripts/fleet_picture.py (per-station done, in-progress, blocked; ATTENTION block) | herald (render) over steward (data) | per deploy + every 6h schedule, no-op skip | M2 |
| Guild status (IA5) | `/status/ci/` | steward ci status --json (paused, stuck, overdue), steward estate status (pins, floors), bmad-estate catalog versions (scribe) | steward (data), herald (render) | per deploy + schedule | M2 |
| Marshal runs (IA6) | `/status/runs/` | marshal status --format json + herald progress --json, a Moment 2 Progress page | marshal (data), herald (render) | snapshot; live watching stays marshal watch / Lane 1 | unassigned; pairs with IA4 and IA5 |
| Pipelines (IA7) | `/pipelines/` | Kedro-Viz export via workflow artifact | atlas | export age shown | M2, pending open question 1 |
| Dashboards (IA7) | `/dashboards/` | Vizro static boards exported offline from the BSL-driven dashboard object | atlas | export age shown | own atlas story |
| Changes (IA8) | `/changes/` + RSS | merge subjects since the last CalVer tag (Moments 3 and 4) | herald | per deploy | M3 |
| Agent surface (IA8) | `/llms.txt`, `/llms-full.txt`, `/facts.json` | starlight-llms-txt over the shelf; facts.yaml; scribe catalogs already on the shelf as raw .md | herald | per deploy | M3 (llms.txt is low effort, may land earlier) |
| Cross-cutting (IA9, IA10) | all | one nav from map.yaml (sections docs, herald, status, pipelines, dashboards, changes); one Pagefind index; one footer; Starlight theme tokens; freshness contract printed per section | doctor (registry), herald (render) | n/a | M3 |

- Vizro constraint: the documented static-export workaround (docs/intake/secure-live-dashboards/vizro-static-github-pages-workaround.md) uses include_plotlyjs='cdn', which AD-21 forbids; plotly.js must be vendored. The live Vizro server (34-page BSL-driven dashboard, closure about 257 packages, -e local-recipes) and the full console stay Lane 1 /console/.
- Freshness vs deploy count: scheduled runs (board every 6h; dossier stats weekly) pass through the no-op deploy skip, so an unchanged fleet costs a build check, never a deploy.
- Freshness contract (IA10): docs per merge; dossier prose measured-on date; board and guild status show snapshot time plus a "live view on Lane 1" link; pipelines and dashboards show export age.

## Operator rulings and asks recorded this session

Three asks arrived mid-session (the first two in one entry, the third later).

1. Ask: can MyBMAD (bmad-code-org/bmad-method-ui web/, Next.js) be shown on GitHub Pages too?
   Answer: not as-is. next.config uses output standalone, not export; PostgreSQL + Prisma; Better Auth sessions; Server Actions (src/actions); API routes (api/auth, api/revalidate, api/health); middleware.ts. Pages serves static files only, and an iframe to mybmad.hichem.cloud is a cross-origin load AD-21 forbids. It is MIT, so its BMAD parser (web/src/lib/bmad) is reusable. Resolution: Y1, run web/ as a sidecar container beside src/platform at /console/mybmad/ for operators (Dockerfile and compose exist; Postgres 17 is already in pyforge-foundry-full-stack), importing local-recipes by GitHub repo or local folder; Y2, a static board snapshot on Pages rendered at build from the eight stations' sprint-status-ledger.yaml + epics.md (now IA4 /status/). Y5, a client-side parser bundle reading raw.githubusercontent.com with the viewer's token, is parked: a cross-origin fetch the airgap host forbids. The VS Code extension in src/ is editor-side, note only.
2. Ask: use the CIS module (bmad-module-creative-intelligence-suite) to generate ideas and requirements and decide what gets deployed.
   Answer: CIS generates and converges; it does not mint CAPs. bmad-brainstorming (core) and bmad-cis-design-thinking ran this session; innovation-strategy, problem-solving and storytelling are installed and available. Requirements come from bmad-spec (Dream to Spec); decomposition from bmad-create-epics-and-stories.
3. Ask: one very useful Pages site combining Docs, Overview, Dossier, Infographics, Decks, Kedro-Viz (Pipelines) and Vizro (Dashboards): a holistic view into PyForge, the BMAD layer, the stations and guild status, for operators, users and developers.
   Answer: accepted as the target for M3 with Y3 intact. Every new section is a build-time snapshot from an existing CLI's JSON: scripts/fleet_picture.py; steward ledger-query / sprint-ledger-query --format json, summary, herald-facts, static-dossier (the last behind pyforge.steward.ledger_query_dossier_export, so the board-to-dossier path is already designed); herald progress --json; marshal status --format json; steward ci status --json (Epic 99, landing); steward estate status; bmad-estate catalog. Nothing on Pages is live or authenticated; live and per-user views stay Lane 1. The site map above goes into the Dream append as "what it looks like when real".

## Rejected

- M4 split surfaces (Pages = docs shelf only; dossier, decks and kedro-viz behind Lane 1): kills the public dossier, which fnd:CAP-14 makes the cutover control plane.
- M5 hub root (hand-made root, Starlight under /docs/, herald under /herald/): moves every docs URL and mints a second redirect generation; revisit only if the audience demands a non-docs front door.
- Also set aside: A4 build locally and commit output (the Kedro-Viz hybrid is exactly this anti-pattern); A6 MkDocs Material for docs/ (loses BMAD upstream parity and its validators); A16 a separate site repo (foundry B's shape after cutover, not now); W3 versioned docs per CalVer tag (parked while docs track main); E5 a public warden compliance tile (default no).

## Constraints the Spec must keep

- One deploy-pages caller per repo: Pages is one environment and two callers race. If another lane needs it, pages.yml becomes a reusable workflow (workflow_call), never a copy.
- Zero third-party origins in the artifact (AD-21 amendment, airgap host), enforced by one allowlist-origin check over the build plus a CSP meta, not a 300-line HTML/CSS/JS scanner.
- docs/ never moves; doctor detectors read it. The symlink stays the architecture.
- docs-site/ vendored upstream files stay hash-pinned (only five files are pinned; everything else is local). Parity never forces renaming docs-site/.
- Foundry rebuild mode: B rebuilds this surface from the Spec; prefer Astro, Starlight plugins and upstream validators over local Python. Bespoke line count is the cost metric (B3).
- Actions minutes are a paid budget (unifying strategy 2026-09-04): path filters, shallow and sparse checkout and the no-op deploy skip are budget moves, not polish.
- Lane 1 /console/ is dynamic and is not Pages. Pages consumes build-time JSON snapshots (steward ci status --json, facts.yaml, status.json), never live calls.
- No bot commits on main: generated content arrives as a workflow artifact, a release asset or a build-time render.
- GitHub Pages has no per-PR preview environment; the PR artifact plus one comment is the review surface.
- One owner per prefix (AD-21), extended to one owner per workflow: steward the duct, herald /herald/, doctor map.yaml, atlas the DAG and dashboard exports.
- Acceptance criteria stay measurable through the B3 markers: cancelled runs per 30 days under 10; zero github-actions[bot] commits on main and docsite-check.yml gone; docsite/ gone and under 300 bespoke Python lines under docs-site/.

## Open questions for the operator

1. Kedro-Viz on Pages: atlas owns the call (AD-21). Artifact handoff into /pipelines/ as reference documentation of the DAG, or retire it from Pages (keep at Lane 1 or as a release asset) if nobody external reads it. The export has been frozen since 2026-08-15 and its publish workflow is paused.
2. Is dist/artifact/dossier.html (the Claude Artifact render) still used? If not, retire the shell_artifact template and its check.
3. Redirect sunset date: the legacy root redirect stubs exist since 2026-10-05; the proposal is a 90-day sunset list in the Spec. Pick the date.
4. Who owns pages.yml: the session proposes steward (deploy duct, budget, stuck detection) with herald owning the content under /herald/. Confirm, or keep it under herald.
5. Warden on Pages: a counts-only compliance tile is possible; default is no. Decide explicitly.

## Hygiene to fold into M1

- docs/MAP.md:34 says the dossier publishes at the root; stale since Story 27.2. Deploy-shape claims belong in one place (the workflow header or an AGENTS.md pointer), not restated in MAP.
- docs/index.md links dreams/pyforge-herald.md, a path the Starlight loader excludes (dreams/ is not a quadrant), so the published link is dead on arrival. Fix the link, and have validate-doc-links resolve against the published set, not the repo tree.
- Delete import_artifact.py (one-time migration, 302 lines, done).
- The docsite/ vs docs-site/ name clash: no rename if M3 is committed to (docsite/ dissolves into docs-site/src/herald). Rename docsite/ to herald-site/ only if M3 is not committed to. Never rename docs-site/.
- So it does not recur: a new top-level directory needs a row in docs/MAP.md's "outside this map" table at mint time; doctor's docs-map-hygiene could red an unlisted top-level directory.
- `docsite/build.py` `md_inline` leaks its NUL slot sentinel when an escape sits inside a code span (`dossier.yml:1151`); the live dossier and the artifact render carry two NUL bytes today. Make the slot restore iterative and drop the needless escape.
