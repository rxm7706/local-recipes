---
title: '42.2: The Kedro-Viz mount is an artifact handoff that tolerates absence'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
flag-exempt: docs-only   # the documentation site's own build assembly; no CLI verb, portal or runtime path (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-27-2-one-pages-artifact-carries-the-docs-site-the-dossier-and-the-dashboard.md
  - docsite/tools/assemble_pages.py
  - docsite/content/site.yml
  - docsite/templates/shell_page.html.j2
  - docsite/templates/page_index.html.j2
  - docsite/build.py
  - docs-site/astro.config.mjs
  - docs/dashboard/README.md
  - .github/workflows/kedro-viz-publish.yml
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The Kedro-Viz export lives in git at `docs/dashboard/kedro-viz/` (11 MB, 215 files, from 2026-08-15, its
producer `kedro-viz-publish.yml` paused since 2026-08-24). `docsite/tools/assemble_pages.py` copies `docs/dashboard/`
into `/dashboard/` and `pages-check` exits 1 when `dashboard/kedro-viz/index.html` is missing (`_required_paths`), so a
paused producer means either a frozen export committed by a bot or a broken site. The export carries no commit or date
a reader can see, so its age hides. The operator ruled on 2026-10-13 that the export arrives as a workflow artifact
(atlas's `kedro-viz-export`, atlas Story 30.1) that steward's deploy workflow downloads (steward Story 102.4), and that
the mount is skipped, never failed, when none exists.

**Approach:** the mount becomes an artifact handoff with a manifest, and absence is a normal build.

- **The input.** A downloaded export tree with a `manifest.json` naming its commit, date and kedro-viz version, placed
  in the build input directory (`docsite/content/kedro-viz-export/`, gitignored, beside Story 42.1's
  `fleet-status.json`) by steward's Guild step. Herald reads `commit` and `date` from the manifest (the two keys the
  acceptance names) and shows the version under the key atlas gives it. A fixture export with a manifest lives under
  herald's tests.
- **With the export.** `_copy_dashboard` mounts the tree under `/dashboard/kedro-viz/`, `_ensure_kedro_viz_redirect`
  writes `/kedro-viz/` → `/dashboard/kedro-viz/` as today, and two places name the manifest's commit and date: the
  overview's Kedro-Viz tile (the `neighbours` entry in `site.yml`, whose blurb today says the export is "republished on
  every push") and the pipelines page, the one page under `/dashboard/` that herald renders in front of the mount
  (`dashboard/index.html`), since the export's own `index.html` is a vendored bundle no template edits.
- **Without the export.** The build exits 0; no `dashboard/kedro-viz/` path and no `kedro-viz/` redirect are written;
  the Kedro-Viz neighbour is hidden from the overview tiles and from CAP-58's shared menu (the `neighbours` entry
  becomes conditional, so both menus follow with no other edit); `_required_paths` no longer lists the two paths
  unconditionally. The `/kedro-viz/` redirect `docs-site/astro.config.mjs` declares becomes conditional on the export's
  presence too, so the artifact holds no redirect to a path that does not exist.
- **The shape check.** `pages-check` exits 1 naming the file when an export is present but its `manifest.json` is
  missing, not JSON, or lacks `commit` or `date`.
- **What stays.** The URL `/dashboard/kedro-viz/` and the `/kedro-viz/` redirect (AD-21 amended 2026-10-14: kept
  URLs); the vendored-root exemption of `/dashboard/kedro-viz/` from the cross-origin check, by name (AD-21 rule 5);
  the tracked `docs/dashboard/README.md` (the tree itself leaves git under atlas Story 30.1, not here).

Ledger key: `42-2-the-kedro-viz-mount-is-an-artifact-handoff-that-tolerates-absence`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / steward 102.4 (downloads `kedro-viz-export` into the build input), atlas 30.1
(produces it with a `manifest.json`).

### Living CAP citations

- **`spec-pyforge-herald` CAP-60** (FR-12.2): the handoff, the manifest on the page, the tolerated absence. On AD-21
  (one artifact, one owner per prefix, kept URLs) and AD-23 (a downloaded artifact is data the generator mounts).
- **`pyforge-atlas:CAP-62`** (Story 30.1): the producer and its manifest. **`pyforge-steward:CAP-168`** (Story 102.4):
  the download into the build input. Both read as data, never imported.
- **`spec-feature-flag-governance` Q2**: `flag-exempt: docs-only` — the documentation site's own build assembly; no
  CLI verb, portal or runtime path, so a flag would gate only a copy step.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M2 ("the Kedro-Viz export arrives as a
  workflow artifact from atlas's producer and the mount is skipped, never failed, when none exists");
  `brainstorm-intent.md` § M2 and open question 1 (atlas owns the call); design-thinking § *Target information
  architecture*, row Pipelines.

## Acceptance Criteria

- **AC1 — With the export.** Given a fixture export (a tree with `index.html` and a `manifest.json` naming `commit`,
  `date` and the version) in the build input, When the site builds, Then `dashboard/kedro-viz/index.html` and
  `kedro-viz/index.html` exist in the artifact, `kedro-viz/index.html` redirects to `/dashboard/kedro-viz/`, and both
  `herald/index.html` (the Kedro-Viz tile) and `dashboard/index.html` (the pipelines page) carry the manifest's commit
  and date.
- **AC2 — Without the export.** Given no export in the build input, When the site builds, Then the build exits 0; no
  path under `dashboard/kedro-viz/` and no `kedro-viz/index.html` exist in the artifact; no page of the artifact links
  either path (the link walk finds no href to them); the shared menu and the overview tiles carry no Kedro-Viz entry.
- **AC3 — The menu follows.** Given the export present, Then every docs page and every herald shell page renders the
  shared menu with Kedro-Viz, as Story 40.1 states; given it absent, the same pages render the menu without it, and
  `pages-check`'s menu check passes in both cases.
- **AC4 — Shape refusals.** Given an export whose `manifest.json` is absent; one that is not JSON; one lacking
  `commit`; and one lacking `date`, When `pages-check` runs, Then each exits 1 naming the manifest path. Extra keys
  change nothing.
- **AC5 — The origin rule.** Given the fixture export carries a third-party reference inside its own bundle, Then the
  cross-origin check still exempts `/dashboard/kedro-viz/` by name and `pages-check` exits 0; given a planted
  third-party reference in `dashboard/index.html`, `pages-check` exits 1.
- **AC6 — The gates.** `pixi run --frozen -e site pages-check` exits 0 with the fixture export and with none;
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green.

## Boundaries & Constraints

**Always:**
- Read the export as data from the build input; copy it verbatim and never edit a file inside it.
- Keep `/dashboard/kedro-viz/` and `/kedro-viz/` as the URLs (AD-21 amended 2026-10-14); the `/pipelines/` URL of
  the design-thinking IA is not minted.
- Keep the vendored-root exemption of `/dashboard/kedro-viz/` named with its reason, as today.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not edit `kedro-viz-publish.yml`, `pages.yml` or `dashboard.yml`; do not call `gh` or download an artifact from
  herald code or the `site` env (steward's Guild step downloads).
- Do not delete `docs/dashboard/kedro-viz/` here (atlas Story 30.1 owns that removal) and do not keep copying it once
  the input exists: the build input is the one source of the mount.
- Do not hand-keep a list of redirects (AD-21 rule 1); the `/kedro-viz/` redirect is written from the mount's presence.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| export present | tree + manifest | mount, redirect, commit and date on the tile and the pipelines page | exit 0 |
| export absent | no input dir | no mount, no redirect, no link, no menu entry | exit 0 |
| manifest absent | tree without `manifest.json` | — | exit 1, names the path |
| manifest lacks `commit` | `{date: ...}` | — | exit 1, names the path |
| manifest lacks `date` | `{commit: ...}` | — | exit 1, names the path |
| manifest not JSON | malformed file | — | exit 1, names the path |
| extra manifest keys | a new key | ignored | exit 0 |
| third-party URL inside the bundle | vendored root | exempt by name | exit 0 |
| third-party URL on the pipelines page | planted | — | exit 1 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-60 (FR-12.2), minted 2026-10-14; works with
  `pyforge-steward:CAP-168` and `pyforge-atlas:CAP-62`.
- Architecture: AD-21 (amended 2026-10-14) and AD-23 (adopted 2026-10-14).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M2.
- Epic: Epic 42, Story 42.2.
- Ledger key: `42-2-the-kedro-viz-mount-is-an-artifact-handoff-that-tolerates-absence`.
- Ledger status at mint: `backlog`.
- Deps: steward Story 102.4 (the download) and atlas Story 30.1 (the producer and the manifest). The story builds and
  tests on a fixture export before either lands; until the Guild step downloads a real export the production build takes
  the absent path and shows no mount. Named here and in `epics.md`, never as a `blocked` row. `marshal factory dispatch`
  stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."42"`.
- Flag: none — `flag-exempt: docs-only` (`spec-feature-flag-governance` Q2).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** steward 102.4 (downloads `kedro-viz-export` into the build input), atlas 30.1 (produces it with a `manifest.json`) • **FR/AD:** spec-pyforge-herald CAP-60 (FR-12.2), on AD-21 and AD-23
**Flag:** none — `flag-exempt: docs-only` (`spec-feature-flag-governance` Q2): the documentation site's own build assembly; no CLI verb, portal or runtime path

**Given** `assemble_pages.py` copies `docs/dashboard/` into `/dashboard/` and exits 1 when
`dashboard/kedro-viz/index.html` is missing, and the committed export (11 MB, 215 files, 2026-08-15) leaves git under
atlas Story 30.1
**When** the site builds with a downloaded export (a tree plus `manifest.json` naming commit, date and kedro-viz
version) in the build input, and again with none
**Then** with the export the mount is written under `/dashboard/kedro-viz/`, the `/kedro-viz/` redirect exists, and
the pipelines page and the nav tile name the manifest's commit and date; with no export the build exits 0, no
`/dashboard/kedro-viz/` path and no `/kedro-viz/` redirect are written, and no page links them
**And** `pages-check` exits 1 on an export whose `manifest.json` is missing or lacks `commit` or `date`;
`pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py -q` — expected: pass (AC1–AC5 on the fixture export and on its absence).
- `pixi run --frozen -e site pages-check` with the fixture export in the build input, and again with the input directory absent — expected: exit 0 both times (AC6).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Delete `manifest.json` from the fixture export — expected: `pages-check` exits 1 naming the path.
- Drop `date` from the manifest — expected: exit 1 naming the path.
- Leave a hardcoded Kedro-Viz link in a template and build without the export — expected: the link walk fails naming the page.

## Named, not fixed here

- **The producer** (`kedro-viz-export` with its manifest, the export's version key, retention) and the removal of
  `docs/dashboard/kedro-viz/` from git: atlas Story 30.1 (`pyforge-atlas:CAP-62`).
- **The download step** and the newest-successful-artifact rule: steward Story 102.4 (`pyforge-steward:CAP-168`).
- **Vizro static boards** beside the mount under `/dashboard/vizro/` (plotly.js vendored, never `cdn`): atlas
  (`pyforge-atlas:CAP-63`), not this story.
- **The `publicDir` mount** of the same export under the one generator, and the `/kedro-viz/` entry in the Astro
  redirects map: Story 43.3.
- **A liveness probe** comparing the live site's age with the latest publish-input commit: doctor (`pyforge-doctor:CAP-91`).

## Spec Change Log

- 2026-10-14: specced at mint from Epic 42's Story 42.2 text, `spec-pyforge-herald` CAP-60, FR-12.2 and the Dream's
  2026-10-13 entry. The build-input location (`docsite/content/kedro-viz-export/`) follows Story 42.1's
  `docsite/content/fleet-status.json`; the implementing session reads atlas Story 30.1's landed manifest first and
  follows it where it differs from the two-key shape quoted here, recording the keys on the Spec memlog.
