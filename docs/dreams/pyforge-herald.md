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

## One-chain fold (2026-09-17)

Herald rebases to one Dream, one Spec, one PRD, one spine, one epic chain. Folded topic Dreams are archived in place with `Consolidated into [[pyforge-herald]]` banners. Station Spec `spec-pyforge-herald` is `ready`; this Dream is `specified`.
