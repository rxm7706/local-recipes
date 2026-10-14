---
title: '41.1: The Pages hygiene before the rework'
type: 'fix'
created: '2026-10-14'
status: 'in-progress'
baseline_revision: '4ea6f365af657b8bbe92149891859cdc1e198d7b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - docsite/build.py
  - docsite/content/dossier.yml
  - docsite/README.md
  - docsite/tools/import_artifact.py
  - docsite/tools/assemble_pages.py
  - docs/index.md
  - docs/reference/github-workflows.md
  - docs/explanation/enterprise-deployment.md
  - docs/dreams/design-sync-loop.md
  - src/prototype/packages/pyforge-atlas-kedro-viz/README.md
  - src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The operator ruled on 2026-10-13 that the whole GitHub Pages deployment is redesigned in three stages
(the station Dream, *the Pages deployment, redesigned*; M1, M2, M3). The analysis that led there found defects on the
live site and in the repository's own prose that no stage should inherit:

- `md_inline` in `docsite/build.py` lifts escapes, arrows and code spans into NUL-delimited slots
  (`\x00<n>\x00`) and restores them in one pass. An escape inside a code span is lifted first, so the code span's
  slot contains the escape's sentinel, and the single restore leaves it in the output. The one such span in
  `docsite/content/dossier.yml` (`` `/stations/\*/mcp` ``, the line `epics.md` names as 1151; 1152 on the tree this
  spec was written against) renders two NUL bytes on `/herald/dossier/` and in the artifact render
  (`herald/artifact/dossier.html`), measured 2026-10-13.
- `docsite/tools/import_artifact.py` (302 lines) is the 2026-09-13 one-time migration from the published artifact. It
  ran once and is dead; `docsite/README.md` still lists it as a tool.
- `docs/index.md` links `dreams/pyforge-herald.md`, a path the shelf loader excludes (`dreams/` is not a quadrant), so
  the published link is dead on arrival.
- `docs/reference/github-workflows.md` says `dashboard.yml` "regenerates `data.js` from git history + live detectors",
  and `docs/explanation/enterprise-deployment.md` says the Guildhall dashboard is "the only thing CI deploys": both
  describe the retired Guildhall deploy, not the unified Pages artifact (CAP-52, AD-21, landed 2026-10-08).
- Two tracked files point at pre-2026-10-08 root URLs: `docs/dreams/design-sync-loop.md` at
  `rxm7706.github.io/local-recipes/infographics/` and `src/prototype/packages/pyforge-atlas-kedro-viz/README.md` at
  `rxm7706.github.io/local-recipes/kedro-viz/`.
- The Claude-artifact render (`herald/artifact/dossier.html`, republishing "The PyForge Dossier") was last refreshed
  2026-09-13 until the 2026-10-13 session republished it; nothing writes down that it is refreshed at session close.

**Approach:** one fix story, no CAP, no FR, no flag (`spec-feature-flag-governance` Q1). No page moves and no URL
changes. The trigger and cost half of M1 is steward's (`pyforge-steward:CAP-168`, Story 102.1).

- **The slot restore.** `md_inline` restores slots until none remains: the `_SLOT.sub` pass repeats while the text
  still matches `\x00(\d+)\x00`, so a sentinel nested in another slot's content is restored on the next pass. A
  regression test in `src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py` renders an escape inside a
  code span and asserts the literal character inside `<code>` with no `\x00` in the output. The one needless escape
  goes from `dossier.yml`: inside a code span `*` is literal, so the span reads `` `/stations/*/mcp` ``.
- **The dead tool.** `docsite/tools/import_artifact.py` is deleted. Its mention in `docsite/README.md` is replaced by
  the refresh ritual the operator ruled in (Dream, *The Claude-artifact render stays and is refreshed*): rebuild
  `dist/artifact/dossier.html`, then republish "The PyForge Dossier" at session close. The README's step 5 under
  *How a refresh actually happens* already says "Republish the artifact"; the ritual names the two acts in one place.
- **The docs.** `docs/index.md` links `/herald/` (the herald overview, under the configured base path) in place of the
  excluded Dream path. `docs/reference/github-workflows.md`'s `dashboard.yml` row and
  `docs/explanation/enterprise-deployment.md`'s "Deploys?" row describe the deploy as it is: one artifact,
  `docs-site/build/site/` (the Starlight shelf at the root, docsite's output under `/herald/`, the dashboard under
  `/dashboard/`), built in the `site` env and deployed by the one `deploy-pages` caller, `.github/workflows/dashboard.yml`
  (named as the tree names it on the story's day; steward Story 102.1 renames the file, and the row follows then).
- **The old roots.** `docs/dreams/design-sync-loop.md` points at `/herald/infographics/` and the prototype README at
  `/dashboard/kedro-viz/`.
- **Not touched.** `docs/MAP.md` is doctor's (`pyforge-doctor:CAP-90`, Story 48.1). The 44 redirect pages stay
  (operator ruling 2026-10-13). Nothing under `/herald/` changes path.

Ledger key: `41-1-the-pages-hygiene-before-the-rework`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **`spec-pyforge-herald` CAP-52** (the docs site matches BMAD-METHOD's pattern) and **CAP-44** (the dossier is the
  source): a fix under both; the docs pages this story corrects are shelf pages governed by `docs/map.yaml`, named in
  the memlog reconcile. On AD-21 (one Pages artifact, one deploy caller).
- **`pyforge-steward:CAP-168`** (Story 102.1): the path filter, `fetch-depth: 1`, the sparse checkout and the schedule
  are steward's half of M1 and are not in this story.
- **`pyforge-doctor:CAP-90`** (Story 48.1): `docs/MAP.md` names `docsite/` and `docs-site/` side by side; doctor's
  edit, not this story's.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 (the Pages deployment, redesigned) entry, M1 and
  *The Claude-artifact render stays and is refreshed*; `brainstorm-intent.md` § *Hygiene to fold into M1*; the
  2026-10-14 decisions on the Spec's memlog (Epic 41 is a fix under CAP-52 and CAP-44).

## Acceptance Criteria

- **AC1 — No sentinel leaks.** `test_docsite_build.py` gains a test that renders `` `/stations/\*/mcp` `` through
  `md_inline` and asserts the output contains `<code>/stations/*/mcp</code>` and no `\x00`; a second case nests an
  arrow inside a code span and asserts no `\x00`. After `pixi run --frozen -e site pages-build`,
  `grep -c $'\x00' docs-site/build/site/herald/dossier/index.html` and
  `grep -c $'\x00' docs-site/build/site/herald/artifact/dossier.html` both print 0.
- **AC2 — The needless escape is gone.** `grep -c 'stations/\\\*/mcp' docsite/content/dossier.yml` prints 0 and
  `grep -c 'stations/\*/mcp' docsite/content/dossier.yml` prints 1. No other line of `dossier.yml` changes.
- **AC3 — The dead tool is gone and the ritual is written.** `docsite/tools/import_artifact.py` does not exist;
  `grep -c import_artifact docsite/README.md` prints 0; `docsite/README.md` names, in one place, the rebuild of
  `dist/artifact/dossier.html` and the republish of "The PyForge Dossier" at session close.
- **AC4 — The docs home links the herald pages.** `grep -c 'dreams/pyforge-herald.md' docs/index.md` prints 0 and
  `docs/index.md` carries a link to `/herald/` that resolves to `herald/index.html` in the built artifact
  (`pages-check` already fails a non-resolving link).
- **AC5 — The deploy prose is true.** `grep -c 'only thing CI deploys' docs/explanation/enterprise-deployment.md` and
  `grep -c 'data.js' docs/reference/github-workflows.md` print 0; the two pages name `docs-site/build/site/` as the
  one artifact, `/herald/` and `/dashboard/` as its mounts and `dashboard.yml` as its one `deploy-pages` caller.
- **AC6 — No old root.** `grep -c 'local-recipes/infographics/' docs/dreams/design-sync-loop.md` and
  `grep -c 'local-recipes/kedro-viz/' src/prototype/packages/pyforge-atlas-kedro-viz/README.md` print 0; the two files
  name `/herald/infographics/` and `/dashboard/kedro-viz/`.
- **AC7 — Nothing moves.** The built artifact holds every path it held before the story: `herald/index.html`,
  `herald/dossier/index.html`, `herald/infographics/index.html`, `herald/decks/index.html`, the 44 redirect pages,
  `kedro-viz/index.html` and `dashboard/kedro-viz/index.html`; `git diff --stat origin/main...HEAD -- docs/MAP.md` is
  empty.
- **AC8 — The gates.** `pixi run --frozen -e site pages-check`, `pixi run --frozen -e site docs-site-validate` and
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` exit 0; `pixi run --frozen -e pyforge-guild
  spec-surface-check` exits 0 after the memlog reconcile names each path.

## Boundaries & Constraints

**Always:**
- Keep `md_inline`'s vocabulary (`` `code` ``, bold, em, link, `<<arrow>>`, backslash escapes) and its output for
  every input that has no nested slot byte-identical; the change is the restore loop only.
- Treat each corrected docs page as a shelf page: `docs/map.yaml` governs it, and the memlog reconcile names the path.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped (AGENTS.md pre-PR item 5); the
  PR carries the `maintenance` label.

**Never:**
- Do not edit `docs/MAP.md`, `.github/workflows/dashboard.yml`, `docsite-check.yml` or any job's `if:` line.
- Do not move a page, change a URL, drop a redirect or add a deploy caller (AD-21; operator ruling 2026-10-13).
- Do not change what `docsite/build.py` renders apart from the restore loop; the dossier's blocks, family pages and
  artifact build stay as they are (CAP-35, CAP-43, CAP-47).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| escape in a code span | `` `/stations/\*/mcp` `` | `<code>/stations/*/mcp</code>` | no `\x00` |
| arrow in a code span | `` `a <<b>> c` `` | one `<code>` holding the arrow span's text | no `\x00` |
| escape outside a code span | `exit: 0\*` (dossier.yml:965) | `0*`, unchanged from today | — |
| no slot | plain prose | byte-identical to today | — |
| built dossier | `pages-build` | `herald/dossier/index.html` and `herald/artifact/dossier.html` with no NUL byte | `grep -c` prints 0 |
| the migration tool | `docsite/tools/import_artifact.py` | absent; README names the refresh ritual instead | — |
| docs home | `docs/index.md` | links `/herald/`; no `dreams/` link | `pages-check` exit 1 on a dead link |

</intent-contract>

## Binding

- Parent Spec capability: a fix under `spec-pyforge-herald` CAP-52 and CAP-44; no CAP minted (memlog decision
  2026-10-14, "Epic 41 is a fix under CAP-52/CAP-44 (no CAP, no flag)").
- Architecture: AD-21 (unamended by this story; see the spine's § Currency reconciliation — 2026-10-14 (later)).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M1.
- Epic: Epic 41, Story 41.1.
- Ledger key: `41-1-the-pages-hygiene-before-the-rework`.
- Ledger status at mint: `backlog`.
- Deps: none. Steward Story 102.1 is the other half of M1 and neither waits on the other. `marshal factory dispatch`
  stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."41"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1).

## Epic excerpt

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** fix under spec-pyforge-herald CAP-52 (the docs site) and CAP-44 (the dossier is the source), on AD-21 • Dream 2026-10-13 (the Pages deployment, redesigned)
**Flag:** none — a fix (`spec-feature-flag-governance` Q1)

**Given** `md_inline` lifts escapes into NUL-delimited slots before code spans, so `` `/stations/\*/mcp` `` at
`dossier.yml:1151` renders two NUL bytes on `/herald/dossier/` and in the artifact render (measured 2026-10-13);
`import_artifact.py` (302 lines, the 2026-09-13 one-time migration) is dead; `docs/index.md` links
`dreams/pyforge-herald.md`, a path the shelf loader excludes; `docs/reference/github-workflows.md` and
`docs/explanation/enterprise-deployment.md` describe the retired Guildhall deploy; two tracked files reference
pre-2026-10-08 root URLs
**When** the story lands
**Then** `md_inline` restores slots until none remains, a regression test renders an escape inside a code span to its
literal text with no `\x00`, and `grep -c $'\x00'` over the built `herald/dossier/index.html` and
`herald/artifact/dossier.html` is 0; the needless escape is gone from `dossier.yml`; `import_artifact.py` is deleted
and `docsite/README.md` names the refresh ritual (rebuild `dist/artifact/dossier.html`, republish "The PyForge
Dossier" at session close) in place of the migration; `docs/index.md` links `/herald/`; the two docs pages describe the
unified artifact and its one deploy caller; the two old-root references point at `/herald/infographics/` and
`/dashboard/kedro-viz/`
**And** `pixi run -e site pages-check`, `pixi run -e site docs-site-validate` and `pyforge-herald-test` are green;
`spec-surface-check` exits 0 after the memlog reconcile names each path

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py -q` — expected: pass (AC1's regression tests).
- `pixi run --frozen -e site pages-build`, then `grep -c $'\x00' docs-site/build/site/herald/dossier/index.html; echo $?` and the same over `herald/artifact/dossier.html` — expected: `0` printed by `grep -c` (AC1).
- `pixi run --frozen -e site pages-check` — expected: exit 0 (AC4, AC7).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0 (the upstream link and sidebar validators over the corrected docs pages).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and the scoped stamps (`spec-pyforge-herald` for `docsite/**`; every co-governor the detector names for the docs pages, the Dream and the prototype README).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Revert the restore loop to one pass — expected: AC1's test fails naming the `\x00`.
- Re-add the `\*` escape to the span — expected: the built dossier carries a NUL byte and the `grep -c` line prints a non-zero count.

**Operator, at session close (the ritual this story writes down):**
- Rebuild `dist/artifact/dossier.html` and republish "The PyForge Dossier"; the README names the two acts.

## Named, not fixed here

- **The trigger and the cost** (the published-inputs path filter, `fetch-depth: 1`, the sparse checkout, the schedule,
  the no-op deploy skip): steward Story 102.1 (`pyforge-steward:CAP-168`).
- **`docs/MAP.md`** naming `docsite/` and `docs-site/` side by side, and the "outside this map" row for a new
  top-level directory: doctor Story 48.1 (`pyforge-doctor:CAP-90`).
- **`validate-doc-links.js` resolving against the published set** rather than the repo tree (the brainstorm intent's
  ask): the vendored validator stays byte-identical (AD-21 rule 5); this story only makes the link true.
- **The `docsite` / `docs-site` name clash**: accepted until Epic 43 dissolves `docsite/` (Story 43.7); no rename story.
- **A scheduled refresh** of the artifact render once the dossier stats are computed (Story 43.5): the ritual is a
  README line here.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 41's Story 41.1 text, the Dream's 2026-10-13 entry (M1 and the refresh
  ritual) and `brainstorm-intent.md` § *Hygiene to fold into M1*. The NUL leak was measured on the live
  `/herald/dossier/` and the artifact render on 2026-10-13; the implementing session re-reads `md_inline` on its own
  tree and follows it where the line numbers quoted here have moved.
