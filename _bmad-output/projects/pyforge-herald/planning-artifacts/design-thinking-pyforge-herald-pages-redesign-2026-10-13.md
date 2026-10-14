---
title: 'Design Thinking Session: the PyForge GitHub Pages deployment, redesigned'
chain: pyforge-herald
created: 2026-10-13
updated: 2026-10-13
status: input-for-dream-append
companion: _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/
---

# Design Thinking Session: local-recipes — the PyForge GitHub Pages deployment

**Date:** 2026-10-13
**Facilitator:** Rxm7706 (session run autonomously by the Claude Code harness; every number below was measured in this session, with its source named)
**Design Challenge:** Redesign and rework the whole GitHub Pages deployment of PyForge — what is published, how it is assembled, when it deploys, and who owns each part — so that the site is simpler to build, cheaper to run, honest about its own age, and cheap for the foundry (B) to rebuild from its Spec.

Companion artifacts: the brainstorm memlog (142 entries, nine techniques, convergence and synthesis) at `_bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/.memlog.md`, its intent doc `brainstorm-intent.md` and keepsake `brainstorm.html` in the same folder.

---

## 🎯 Design Challenge

The repository publishes one GitHub Pages site, `https://rxm7706.github.io/local-recipes/`. Four mechanisms, minted at four different times, feed it:

| Minted | Mechanism | Owner | Lines of bespoke code |
|---|---|---|---|
| 2026-08 | `docs/dashboard/kedro-viz/` — a Kedro-Viz export (11 MB, 215 files) committed to `main` by `kedro-viz-publish.yml` through `steward deploy dashboard` | atlas (export), steward (duct) | — (tracked build output) |
| 2026-09-13 | `docsite/` — Jinja2 + YAML renderer for the dossier, ten infographics, ten deck family pages, a Claude-artifact render and self-hosted fonts | herald | `build.py` 867, `verify_claims.py` 237, `import_artifact.py` 302 |
| 2026-10-05 | `docs-site/` — Astro + Starlight site over the `docs/` Diátaxis shelf, five files hash-pinned to BMAD-METHOD upstream | herald (site), doctor (`map.yaml` registry) | `sidebar_from_map.py` 297, loader 135, validators 1,086 (vendored) |
| 2026-10-05 | `docsite/tools/assemble_pages.py` — mounts herald under `/herald/`, copies the dashboard, writes 44 legacy redirect stubs, walks links, scans every HTML/CSS/JS for third-party origins | herald | 720, plus `pages_second_host.py` 101 |

They deploy through `.github/workflows/dashboard.yml` — named for the Guildhall console steward retired in Story 30.2 — which fires on **every** push to `main`, builds in about one minute from cache, and deploys in ten seconds. `docsite-check.yml` is its PR-time twin. The 2026-10-12 herald Dream entry records the operator's experience of the current root: *the site "is now docs", and everything else looked gone.*

**Challenge statement.** How might the eight-station factory publish one public site that a stranger understands in one screen, that a contributor can change with one workflow and one build, that costs minutes only when its inputs change, that tells on itself when stale, and that the foundry can regenerate from Astro, YAML and upstream validators alone?

---

## 👥 EMPATHIZE: Understanding Users

Methods used (from the design-methods catalog): **Journey Mapping** of the operator's landing and of a docs change through CI; **Shadowing** through the workflow run history and the live site's response headers; **Diary Study** through the dated realization log of `docs/dreams/pyforge-herald.md` (2026-09-13 → 2026-10-12); an **Empathy Map** per reader. No interviews were run; the operator's own words are quoted from the Dream.

### User Insights

**The operator (owner, pays the Actions bill).** Lands on the root and expects to see PyForge. On 2026-10-12 saw "docs" and nothing else; Story 40.1 added the Herald sidebar group and a shared top menu the same day. Learned on 2026-10-12 that the Pages deploy had sat in `waiting` from 2026-10-06 to 2026-10-12 — six days of a stale site, 199 cancelled runs, visible nowhere. Pays for Actions minutes on a paid plan (unifying strategy, 2026-09-04: "Actions minutes are a standing budget").

**The contributor and the harness (Claude Code, Cursor, a marshal dispatch).** Edits a how-to, waits for `docsite-check`, lands; then watches three Pages deploys fire for one landing (merge, then two ledger-promote commits) with two of them cancelled. Reads `AGENTS.md`, which cites `docsite/content/dossier.yml` as the cutover's control plane. Needs an agent-readable surface (`llms.txt`) that does not exist yet; the repo hand-maintains `*-llms-full.md` files instead.

**The outside reader (a collaborator, a peer in conda-forge, a hiring manager).** Wants "what is PyForge" in one screen, then the dossier and the decks. Gets a Starlight landing page with four quadrant links and a Herald group; the dossier is one click away under `/herald/dossier/`. The dossier's section stats were last hand-refreshed 2026-09-13; today's run reports 17 drifted claims as an advisory annotation nobody reads.

**The air-gapped reader (the enterprise GitHub Pages host, CAP-56).** Needs the same artifact with zero third-party origins. Got Google Fonts on 45 pages until Story 31.3 vendored 25 `woff2` files with a hand-written sha256 table. Needs a flag (`pyforge.herald.pages_second_host`) flipped in the enterprise copy and a conda mirror reachable from the runner just to build a static site.

**The foundry rebuilder (B, `rxm7706/python-foundry`).** Must re-derive this surface from the Spec (`pgs:CAP-1..5` and herald's CAP-44/49/52/56/58 are all `mode: rebuild` in `docs/foundry/capability-ledger.yaml`). Every bespoke line is rebuild cost; every upstream tool is free.

**The station owners.** AD-21 gives each path prefix one owner: herald `/herald/`, doctor the shelf registry, atlas `/dashboard/kedro-viz/`, steward the deploy duct. The tooling does not follow the ownership: herald's `assemble_pages.py` copies atlas's export and reads doctor's `map.yaml`; steward's duty commits atlas's bytes to `main`.

### Key Observations

All measured 2026-10-13 against `origin/main` and the GitHub API (`gh api rate_limit` 5000/5000 before trusting any green).

| Observation | Measurement | Source |
|---|---|---|
| Deploys per month | **1,342 runs** of `dashboard.yml` since 2026-09-13: **720 deployed**, **621 cancelled**, 1 failed (about 24 deploys a day) | `actions/workflows/dashboard.yml/runs?created=>=2026-09-13` `total_count` |
| Pushes to `main` | ~1,330 first-parent commits in 30 days; up to 176 in one day (2026-10-08) | `git rev-list --first-parent` |
| Would-be deploys under the current `docsite-check` path filter | **385** of 1,330 — driven by `docs/dreams` (515 file touches) and `docs/governance` (143), neither of which Starlight publishes | `git log --first-parent -- docs/** …` |
| Would-be deploys under a published-inputs filter (four quadrants, `index.md`, `404.md`, `map.yaml`, `docs/dashboard/`, `docs-site/`, `docsite/`, `presentations/`, the workflow) | **132** of 1,330 — a 5.5× cut with no loss of freshness | same, narrower pathspec |
| Build and deploy time | build job 58 s (checkout 15 s, pixi 5 s, host-env resolve 19 s, pages-check 9 s), deploy 10 s | run 38485633989 step timings |
| Checkout shape | `fetch-depth: 0` on a repository whose `presentations/` tree is 658 MB (870 tracked files); nothing in the build reads history (`build.py` reads `GITHUB_SHA`) | `dashboard.yml`, `du`, `build.py:545` |
| Dossier honesty | 17 of the marked stat claims drifted; the step is `continue-on-error` | run 38485633989, "Verify the dossier's numbers" |
| Kedro-Viz freshness | export committed 2026-08-15; `kedro-viz-publish.yml` listed `paused-manually` in the CI-pause plan | `git log -- docs/dashboard/kedro-viz`, `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` |
| Bespoke code | 3,830 lines across `docsite/`, `docs-site/scripts`, `docs-site/src` (1,086 of them vendored validators) | `wc -l` |
| Names | `docsite/` and `docs-site/` side by side; no record weighs the clash | `git log --diff-filter=A` |
| Stale prose | `docs/MAP.md:34` still says the dossier publishes at the root (Story 27.2 moved it under `/herald/`); `docs/index.md` links `dreams/pyforge-herald.md`, a path the Starlight loader excludes — the live root hides the link | file reads; live `curl` returns 404 for `/dreams/pyforge-herald/` |
| Live site | root and every mount return 200; `last-modified` 2026-10-13T23:42:30Z | `curl -sI` |
| Incident | deploy parked in `waiting` 2026-10-06 → 2026-10-12 (environment `github-pages`: branch policy only, zero reviewers); `timeout-minutes` cannot cover a job in `waiting` | CI-pause plan § G10, environment API |

### Empathy Map Summary

| | Says | Thinks | Does | Feels |
|---|---|---|---|---|
| Operator | "The site is now docs; everything else looked gone." "Actions minutes are a standing budget." | The public face should explain the factory, not hide it. A stale site should tell me. | Rules on layout, mints Dream entries, pays the bill | Surprised by invisibility; wary of a second 6-day gap |
| Contributor / harness | "Which workflow do I wait for?" | One docs change should mean one build and one deploy | Edits `docs/`, lands, watches three deploys | Noise fatigue (two of three runs cancelled) |
| Outside reader | "What is PyForge?" | The dossier is the pitch; numbers should be current | Clicks Dossier, Decks | Trusts the page less when a figure is off |
| Air-gapped reader | "Nothing may leave the host." | Same bytes, different base URL | Flips a flag, mirrors conda, rebuilds | Over-tooled for a static site |
| Foundry rebuilder | "Which of this is contract, which is accident?" | Astro + YAML is rebuildable; 3,830 lines of glue is not | Reads the Spec, re-derives | Dreads the assembler |

---

## 🎨 DEFINE: Frame the Problem

### Point of View Statement

- **The operator** needs the Pages deploy to run only when a published input changes and to announce when it is stale, because 720 deploys a month that nobody watches let a six-day outage pass unseen while costing paid minutes.
- **The contributor** needs one workflow, one build and one output tree, because today a docs change passes through a PR twin and a deployer that must be kept in step by hand, and two generators plus an assembler to reason about.
- **The outside reader** needs the dossier's figures measured at build time, because an advisory drift report (17 today) that never blocks is a number that is false on the public page.
- **The foundry rebuilder** needs the site expressed in Astro, YAML and upstream validators, because every bespoke line in `docsite/` is a line B must rewrite from a five-field Spec.
- **The station owners** need the tooling to follow AD-21's ownership, because a herald script that copies atlas bytes which a steward duty committed to `main` is three owners in one code path.

### How Might We Questions

1. How might we deploy only when the published inputs change, and skip even then when the built tree is byte-identical?
2. How might we hand generated boards (Kedro-Viz, a future sprint board) to the Pages build without committing them to `main`?
3. How might one workflow in BMAD-METHOD's own `docs.yaml` shape serve as PR check and deployer, and fold `docsite-check.yml` into it?
4. How might one generator render the dossier, the gallery, the family pages and the shelf, so that the assembler, the Jinja templates and the `docsite/` directory — and with it the name clash — disappear?
5. How might the dossier's numbers come from the measurer instead of being checked against it?
6. How might every page say which commit and run built it, so a stale site tells on itself?
7. How might the site serve agents (`llms.txt`, `llms-full.txt`, `facts.json`) as well as humans?
8. How might one rule decide, for every future surface, whether it belongs on Pages or on Lane 1 — including MyBMAD?
9. How might the enterprise host get the reviewed bytes without a flag, a mirror, or a rebuild?

### Key Insights

1. **Four mechanisms, not two sites.** The visible symptom is the `docsite/` vs `docs-site/` clash. The structural problem is four separately minted mechanisms glued by 3,830 lines, deployed by a workflow named for something retired.
2. **One root cause behind two incidents.** The Kedro-Viz bot-commit pattern and the six-day `waiting` outage share it: a deploy decoupled from the change that should cause it. Path filters and artifact handoffs fix both.
3. **Checks nobody reads are not properties.** The Google-Fonts incident (2026-10-08) and today's 17 drifted claims are the same class. Make the property structural: fonts via `@fontsource` imports, stats computed at build.
4. **Upstream parity is the deciding value** because B must rebuild this. The 2026-09-20 operator ask ("match what BMAD-METHOD itself does") already chose it; the redesign finishes that thought.
5. **The name clash dissolves for free under the one-generator shape** (the dossier becomes `docs-site/src/content/dossier/`, the herald pages `docs-site/src/pages/herald/`). A rename story is only needed if the one-generator step is *not* committed to.
6. **MyBMAD answers itself.** `bmad-method-ui/web` is Next.js with `output: "standalone"`, PostgreSQL + Prisma, Better Auth sessions, Server Actions, API routes and middleware — a server, not a static site. GitHub Pages serves files only, and an `<iframe>` to the hosted instance is a cross-origin load AD-21 forbids. The placement rule: **dynamic, authenticated, per-user → Lane 1 (`/console/`); static, public, build-time → Pages.** MyBMAD can run as a Lane 1 sidecar (Dockerfile and compose exist; PostgreSQL 17 is already in the stack). Its Pages-side twin is a build-time **board snapshot** rendered from the eight stations' ledgers — the same read-only epic/story view, zero origins, refreshed per deploy. Its MIT parser (`web/src/lib/bmad/`) is reusable for that renderer.

---

## 💡 IDEATE: Generate Solutions

### Selected Methods

Run in the companion brainstorm (autonomous mode), each logged to the memlog: **Constraint Mapping** (18 constraints sorted real vs imagined), **Assumption Reversal** (18), **SCAMPER** (24), **Morphological Analysis** (11 parameters, 6 configurations), **Kill the Crown Jewel** (8), **Failure Analysis** (9 incidents), **Ecosystem Thinking** (9), **Backcasting** (3), **Wild/Speculative** (7), plus 5 MyBMAD placements. 118 ideas; 9 clusters; Impact–Effort convergence.

### Generated Ideas

The nine clusters, with the ideas that define them (full list in the memlog):

1. **Trigger & cost** — publish-inputs path filter (720 → ~132 deploys/month), `fetch-depth: 1`, sparse checkout of `presentations/*/project/*.html`, no-op deploy skip on tree hash, a weekly scheduled run so dossier stats stay within a week of the tree, a daily liveness probe (live `last-modified` vs latest publish-input commit) as a doctor advisory.
2. **Handoffs, not commits** — Kedro-Viz arrives as a workflow artifact (`upload-artifact` in `kedro-viz-publish`, cross-run `download-artifact` in the Pages build; mount skipped and tile hidden when none exists); build once per PR, promote that artifact on merge.
3. **One workflow, upstream shape** — `pages.yml` with `build` (pull_request and push) and `deploy` (push to `main`) jobs, BMAD-METHOD `docs.yaml` shape, `docsite-check.yml` deleted; steward owns the duct (`steward pages build|deploy|status`), herald owns `/herald/`.
4. **One generator** — Astro content collection over `dossier.yml` (14 block macros → 14 components), gallery and family pages as Astro pages over `presentations/` globs and `facts.yaml`, design twins and the dashboard mounted through `publicDir`, redirects as an `astro.config` map, fonts via `@fontsource`, Starlight theme tokens on herald pages; `build.py`, `assemble_pages.py`, the Jinja templates and `docsite/` retired.
5. **One registry, one search, one status** — herald rows join doctor's `map.yaml`; Pagefind indexes the whole artifact (`data-pagefind-body` on herald pages); one build-time `status.json` (from `steward ci status --json`) and the stations' `facts.yaml` feed the dossier.
6. **Honest numbers** — stats with `check:` take their value from the measurer; each section carries a "measured on" stamp; every page footer says *built from `<sha>` at `<time>` by run `<id>`*; a site-health tile (last deploy, runs this month, cancelled streak, export age).
7. **Agent and proclamation surfaces** — `llms.txt` / `llms-full.txt` (starlight-llms-txt), `facts.json`, a *Changes* page from merge subjects since the last CalVer tag with RSS (Herald's Moments 3–4 finally get a surface), the board snapshot (Pages-side MyBMAD).
8. **Simplify hosts** — `actions/configure-pages` is authoritative on every host; the `pages_second_host` flag and `export_pages_host_env.py` retire; the artifact is also zipped as a release asset so the enterprise host pulls reviewed bytes instead of rebuilding behind a mirror.
9. **Retire and sunset** — the 44 legacy root redirects on a dated sunset; `import_artifact.py` (one-time migration, done); the `dist/` second output tree; a decision on Kedro-Viz on Pages (atlas's call: rebuild via artifact, or retire to Lane 1); fix `docs/MAP.md:34` and the dead `docs/index.md` dream link.

Configurations considered: **M1** minimal fix (cluster 1 + 9), **M2** upstream-shape workflow (clusters 2, 3, 8), **M3** one generator (clusters 4, 5, 6), **M4** split surfaces (Pages = docs only; dossier to Lane 1) — *rejected*, it removes the public dossier that `fnd:CAP-14` makes the cutover's control plane, **M5** hub root with Starlight under `/docs/` — *rejected*, it moves every docs URL and mints a second generation of redirects.

### Top Concepts

| Rank | Concept | Impact | Effort | Shape |
|---|---|---|---|---|
| 1 | **M1 — trigger, cost, hygiene.** Publish-inputs path filter; `fetch-depth: 1`; sparse checkout; no-op deploy skip; delete `import_artifact.py`; fix `MAP.md:34` and the dead dream link; sunset list for redirects | High (5.5× fewer deploys; the outage class shrinks) | Low | 1 story, or one small fix epic |
| 2 | **M2 — one `pages.yml` in upstream shape, artifact handoffs, flag retired.** `docsite-check.yml` folds in; Kedro-Viz via artifact, zero bot commits; `configure-pages` always; release-asset zip; steward owns the duct | High | Medium | 1 epic (3–4 stories) |
| 3 | **M3 — one Astro generator.** Dossier from YAML, gallery and family pages as Astro pages, `publicDir` mounts, redirects map, `@fontsource`, Pagefind over all, `llms.txt`, computed stats, built-from footer; `docsite/` dissolves into `docs-site/`; bespoke Python under 300 lines | High (the foundry-rebuildable shape; name clash gone) | High | 1 epic (5–7 stories), after M2 |
| 4 | **Y3 — the placement rule** for every future surface (MyBMAD → Lane 1 sidecar; a static board snapshot → Pages under `/herald/board/`) | Medium | Low (a rule) then Medium (the snapshot) | A Dream line now; a later story |

---

### Target information architecture — the holistic site

The operator's third ask in this session: one Pages site that combines Docs, Overview, Dossier, Infographics, Decks, Kedro-Viz (Pipelines) and Vizro (Dashboards) with the fleet view marshal's watcher and `fleet-picture` already compute — a holistic view into PyForge, the BMAD layer, the stations and the guild, for operators, users and developers. Every section below is a **build-time snapshot of an existing CLI's JSON** (the Y3 rule); nothing on Pages is live or authenticated, and each page prints its own freshness.

| Section | URL | Feed (already exists unless marked new) | Owner (data → render) | Refresh | Stage |
|---|---|---|---|---|---|
| Home | `/` | generated from `map.yaml` + `site.yml`: four doors (Docs, Overview, Status, Decks), built-from footer | doctor → herald | per deploy | M3 |
| Docs | `/tutorials/ /how-to/ /reference/ /explanation/` | the shelf, `docs/map.yaml` order | doctor | per merge | today |
| Overview + Dossier | `/herald/`, `/herald/dossier/` | `dossier.yml` prose + computed stats + `presentations/*/facts.yaml` + `status.json` tiles | herald | per deploy; prose carries "measured on" | today → M3 |
| Infographics, Decks | `/herald/infographics/`, `/herald/decks/<slug>/` | design twins + `facts.yaml` (CAP-35/53/55) | herald | per deploy | today |
| **Fleet board** (static MyBMAD twin) | `/status/` | `sprint-ledger-query --format json` (8 ledgers + `epics.md`) and `scripts/fleet_picture.py` (done / in-progress / blocked + ATTENTION) | steward (engine) → herald (render) | per deploy + scheduled every 6 h with the no-op skip | **new, M2-era** |
| **Guild status** | `/status/ci/` | `steward ci status --json` (paused / stuck / overdue surfaces, Epic 99), `steward estate status`, bmad-estate catalog versions | steward → herald | same | **new, M2-era** |
| **Runs & progress** | `/status/runs/` | `marshal status --format json`, `herald progress --json` (Moment 2: shipped, cost, unblocked) | marshal/herald → herald | same | **new, M3** |
| Pipelines | `/pipelines/` (today `/dashboard/kedro-viz/`) | Kedro-Viz export via workflow artifact | atlas | on export change | M2 |
| Dashboards | `/dashboards/` | Vizro boards exported offline from the BSL-driven dashboard object (34 pages exist; `dashboard-dryrun` already builds the object without a server); **plotly.js must be vendored** — the intake workaround's `include_plotlyjs='cdn'` violates AD-21 | atlas | on data change, scheduled | **new, atlas story** |
| Changes | `/changes/` + RSS | merge subjects since the last CalVer tag (Moments 3–4) | herald | per deploy | M3 |
| Agents | `/llms.txt`, `/llms-full.txt`, `/facts.json` | starlight-llms-txt; `facts.yaml` union | herald | per deploy | M3 |

One nav from one registry (`map.yaml` gains the non-docs sections), one Pagefind index, one footer, one theme. The live fleet watcher (`marshal watch`), the live Vizro server and MyBMAD itself remain Lane 1 `/console/`; every status page links there with "live view".

**Freshness versus deploy count.** A fleet board refreshed hourly would reintroduce 24 deploys a day. The resolution is the no-op skip: a scheduled build that finds the fleet unchanged uploads nothing, so the schedule costs about one minute of build and zero deploys when nothing moved.

---

## 🛠️ PROTOTYPE: Make Ideas Tangible

### Prototype Approach

Paper prototypes and one Wizard-of-Oz replay, because the riskiest assumptions are about *behaviour of the pipeline*, not about pixels. Rough on purpose: the point is to learn whether each configuration holds before any file moves.

### Prototype Description

**P-A. Target workflow skeleton (`pages.yml`, upstream `docs.yaml` shape).**

```yaml
on:
  pull_request:
    paths: [docs/tutorials/**, docs/how-to/**, docs/reference/**, docs/explanation/**,
            docs/index.md, docs/404.md, docs/map.yaml, docs/dashboard/**,
            docs-site/**, presentations/**, .github/workflows/pages.yml]
  push:
    branches: [main]
    paths: [same list]
  schedule: [{cron: '17 6 * * 1'}]     # weekly: dossier stats within a week of the tree
  workflow_dispatch:
jobs:
  build:   # checkout fetch-depth 1 + sparse; download kedro-viz-export artifact if any;
           # pixi -e site pages-check; upload pages artifact; upload zip as PR artifact
  deploy:  # if: github.event_name != 'pull_request' && needs.build.outputs.changed == 'true'
           # environment github-pages; deploy-pages
```

**P-B. Target tree (M3).** `docs-site/src/content/dossier/*.yml` (sections), `docs-site/src/components/dossier/*.astro` (14 block components), `docs-site/src/pages/herald/{index,dossier,infographics,decks/[slug]}.astro`, `docs-site/public/herald/twins/` (copied design twins), `docs-site/public/dashboard/` (downloaded export), `astro.config.mjs` `redirects` from `docs-site/redirects.json`. `docsite/` gone. Published URLs unchanged: `/`, `/herald/…`, `/dashboard/kedro-viz/`.

**P-C. Wizard-of-Oz replay of the path filter (run in this session).** The last 30 days of `main` were replayed against the current broad filter and the proposed narrow one: 1,330 pushes → 385 would-be deploys (broad) → 132 (narrow). The narrow filter loses nothing Starlight publishes, because the churn it drops is `docs/dreams` and `docs/governance`, which the shelf loader excludes.

**P-D. Placement rule card (Y3).** One sentence on the herald Dream: *dynamic, authenticated or per-user → Lane 1; static, public and build-time → Pages.* Applied: MyBMAD → Lane 1 sidecar; board snapshot → Pages; Kedro-Viz → Pages only as a build-time artifact or retired.

### Key Features to Test

1. The narrow path filter catches every change that alters the published artifact (false negatives would mean a stale site).
2. Cross-run `download-artifact` of the Kedro-Viz export works within retention and with `actions: read` permissions; the build degrades gracefully when the artifact is absent.
3. Astro renders the 14 dossier block types with visual parity to the Jinja output (golden-HTML diff).
4. `publicDir` HTML is indexed by Pagefind when tagged `data-pagefind-body`.
5. `actions/configure-pages` yields the right `base_url`/`base_path` on github.com without the flag (it already does; the GHE case is documented, not testable here).
6. The no-op deploy skip compares a stable tree hash (the built-from footer must be excluded from the hash or injected after hashing).

---

## ✅ TEST: Validate with Users

### Testing Plan

No external readers were available in this session; the operator's 2026-10-12 rulings and Dream entries stand in for user feedback. The plan for the build-out:

- **Assumption tests (riskiest first):** (1) filter replay — done, see P-C; (2) artifact handoff — a spike story that uploads one export and downloads it in a `workflow_dispatch` run of the new workflow; (3) block parity — a spike that renders one dossier section both ways and diffs the DOM; (4) Pagefind over `publicDir` — part of the same spike; (6) tree-hash skip — unit test on the hashing step.
- **Usability test with the operator (5–7 tasks, think-aloud):** find the dossier from the root; find a deck's PPTX; tell how old the site is; find the Kedro-Viz graph; find the docs for `pixi-tasks`; find the sprint board; locate `llms.txt`.
- **Pipeline test:** after M1 lands, count deploys for 14 days; expect ≤ 70 (≈ 5/day) and zero cancelled streaks ≥ 5.
- **Feedback capture grid** in the Story specs: liked / questions / ideas / changes, per task.

### User Feedback

Collected so far (operator, from the Dream's realization log and the 2026-10-12 rulings): the root must lead to the herald pages (ruled, shipped as Story 40.1); the dossier must show paused or stuck CI surfaces (ruled, planned as a CI-surfaces tile); a Pages fix lands before the second-host story (ruled 2026-10-08); the docs must match BMAD-METHOD's pattern so upstream skills apply unchanged (asked 2026-09-20). This session's mid-run asks: whether MyBMAD can be shown on Pages (answered by Y3: not as-is; Lane 1 sidecar plus a Pages board snapshot), and that the CIS module be used to generate ideas and requirements (this session: `bmad-brainstorming` + `bmad-cis-design-thinking`; requirements themselves are `bmad-spec`'s to mint).

### Key Learnings

- **Validated:** the trigger is the cheapest, largest win (P-C); the four-mechanism diagnosis (the churn is in glue, not in content); upstream parity as the deciding value (operator ask 2026-09-20 plus `mode: rebuild` on every Pages capability).
- **Invalidated:** "two docs sites" as the problem statement — there is one site; "the clash needs a rename" — only if M3 is not committed to; "MyBMAD could be on Pages" — it is a server.
- **Open:** whether Kedro-Viz stays on Pages at all (atlas's call); whether the Claude-artifact dossier render (`herald/artifact/dossier.html`) still has a reader; how long the legacy redirects must live (no access logs on Pages — pick a date).

---

## 🚀 Next Steps

### Refinements Needed

- Narrow the published-inputs filter to exactly what the Starlight loader and the herald renderer read, and keep it in one place (the workflow) that a meta test reads back (steward 71.2 already derives `pr-preflight`'s lane selection from the workflow file).
- Decide the Kedro-Viz question with atlas before M2 (artifact handoff vs retire).
- Fix the `md_inline` NUL-sentinel leak in `docsite/build.py` (an escape inside a code span, `dossier.yml:1151`, renders as `\x000\x00` on the live dossier and in the artifact render) as part of M1.
- Decide the redirect sunset date in the Spec (proposal: 90 days after M3 lands).
- Write the Y3 placement rule into the herald Dream and cite it from AD-21.

### Action Items

Under the repo's Dream-first workflow, in order:

1. **Dream append** — a dated 2026-10-13 entry on `docs/dreams/pyforge-herald.md`: the four-mechanism finding, the measured numbers, the M6 staged direction, the target site map above as "what it looks like when real", the Y3 placement rule, the MyBMAD ruling; Kinships to steward (deploy duct, budgets, CI-surfaces, `ledger-query`), doctor (`map.yaml`, liveness probe), atlas (Kedro-Viz export, Vizro static boards), marshal (`status --format json`), the cutover (`fnd:CAP-14`, rebuild mode).
2. **`bmad-spec`** mints the CAPs on `spec-pyforge-herald` (one per stage, plus the placement rule as a constraint on AD-21), with decisions D-n on its memlog.
3. **Epics and stories** in herald's `epics.md` + ledger: M1 as one fix story (or a two-story epic: trigger/cost; hygiene), M2 as one epic, M3 as one epic; a steward story for the `pages` duty and the registry row; an atlas story for the artifact handoff or the retire.
4. **Spikes first** in M2/M3: artifact handoff; block-parity render; Pagefind over `publicDir`.
5. **Retire** at the end of M3: `docsite/`, `docsite-check.yml`, `import_artifact.py`, `export_pages_host_env.py`, the `pages_second_host` flag, the `dist/` path — each with its memlog reconcile and scoped spec-surface stamp.

### Success Metrics

| Metric | Today (2026-10-13) | M1 done | M2 done | M3 done |
|---|---|---|---|---|
| Pages deploys per 30 days | 720 (+621 cancelled) | ≤ 150, cancelled streak never ≥ 5 | same | same |
| Commits on `main` by `github-actions[bot]` for Pages | yes (`steward deploy dashboard`) | yes | **0** | 0 |
| Workflows touching Pages | 3 (`dashboard.yml`, `docsite-check.yml`, `kedro-viz-publish.yml`) | 3 | **1** (`pages.yml`) + atlas's producer | 1 |
| Bespoke lines under `docsite/` + `docs-site/` (excluding vendored validators) | ~2,740 | ~2,440 | ~2,300 | **< 300** |
| Top-level site dirs | 2 (`docsite/`, `docs-site/`) | 2 | 2 | **1** |
| Live `last-modified` within 24 h of the last publish-input commit | unmeasured; once 6 days stale | measured daily (doctor advisory) | same | same |
| Dossier stat claims drifted | 17 (advisory) | 17 | 17 | **0 computed at build**; prose carries "measured on" |
| Third-party origins in the artifact | 0 (scanner) | 0 | 0 | 0 (structural: `@fontsource`, CSP meta) |
| Agent surface | none | none | none | `/llms.txt`, `/llms-full.txt`, `facts.json` |

---

_Generated using BMAD Creative Intelligence Suite - Design Thinking Workflow_
