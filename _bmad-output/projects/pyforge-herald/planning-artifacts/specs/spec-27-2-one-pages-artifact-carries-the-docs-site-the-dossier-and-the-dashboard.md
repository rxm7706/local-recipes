---
title: '27.2: One Pages artifact carries the docs site, the dossier and the dashboard'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: '3fe8584eac77aec67e1a8df4e64b243e99eb6891'
followup_review_recommended: false
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/docs-site-bmad-method-pattern-2026-09-20.md
  - .github/workflows/dashboard.yml
  - .github/workflows/docsite-check.yml
  - docsite/build.py
  - docsite/README.md
  - docs/dashboard/README.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** GitHub Pages serves one artifact per repository. Today that artifact is `docs/dashboard/`: `dashboard.yml` builds the dossier site (`docsite/build.py`) straight into it as the site root, next to the tracked Kedro-Viz export at `kedro-viz/` (CAP-44). Story 27.1's Starlight site builds to `docs-site/build/site/` and has nowhere to publish. A second workflow calling `deploy-pages` would race `dashboard.yml` and wipe the Kedro-Viz export, as that workflow's own header says, so a second deploy is not an option. Moving the dossier site off the root also changes 45 public HTML URLs it serves there today, and none of them may silently change meaning.

**Approach:** Assemble one artifact at `docs-site/build/site/`, with one owner per path prefix (AD-21):

- Starlight at the root.
- docsite's whole output under `/herald/`. Its links are relative (`build.py:132-134`, `339-341`, and every template's `rel` prefix), so it renders unchanged there.
- The tracked `docs/dashboard/` tree under `/dashboard/`.

Then write a redirect page at every HTML path docsite served at the root before, derived from the `herald/` tree, with `/` as the one named exception. Keep `/kedro-viz/` → `/dashboard/kedro-viz/`. Reshape `dashboard.yml`, keeping its path, into upstream `docs.yaml`'s build and deploy jobs in the pixi `site` env. Point `docsite-check.yml` at the same `pages-check` task and path-filter it on the docs, so a PR predicts the deploy. `pr-preflight` is left alone: Story 27.5 owns that lane (CAP-52 D2, D7, D8).

## Boundaries & Constraints

**Always:**
- `.github/workflows/dashboard.yml` stays the only file under `.github/workflows/` that uses `actions/deploy-pages`, and it keeps its path. Steward's `tests/meta/test_invariants.py:885`, `src/platform/tests/test_console_parity_homes.py:255` and `scripts/pixi_version_registry.py:61` read it. Its triggers (`push: main`, `workflow_dispatch`), permissions and `concurrency: pages` stay as they are, and its header keeps the race note.
- `dashboard.yml` keeps exactly one `pixi-version:` pin, so registry site `dashboard.yml setup-pixi` stays valid. If a second pin appears, register it in `scripts/pixi_version_registry.py` in the same PR. `pixi run -e pyforge-guild pixi-version-check` must be green.
- Redirects are derived, never listed by hand. The assembler writes one redirect page for every `.html` file docsite wrote under `herald/`, except `herald/index.html`, at the same path with the `herald/` prefix removed (45 HTML files on 2026-09-27, so 44 redirects). Each redirect's target is relative, so it works under any Pages `base`.
- One owner per path prefix: the assembler refuses, with exit 1 and the path named, any mount point or redirect path that already exists in Starlight's output. It never deletes outside `docs-site/build/site/`.
- The root `index.html` is the single named exception, a constant in the assembler rather than a silent skip: Starlight's landing (`docs/index.md`, Story 27.1) owns `/` and links to `/herald/`.
- Non-HTML files docsite wrote at the root cannot carry an HTML redirect on static Pages: `assets/site.css`, `.nojekyll`, and the 69 deck downloads under `decks/<slug>/downloads/` on 2026-09-27. They move under `herald/` with no redirect, so an old path returns 404 and never serves different content.
- `verify_claims.py` (`site-verify`) stays advisory in the deploy (`continue-on-error`), as CAP-46 requires.
- `pixi.toml` changed: run `pixi run -e pyforge-guild pyforge-station-tests` first, and regenerate `environment.yaml` (expected byte-identical).
- Before landing, reconcile each co-governor: add a memlog entry on every Spec that `spec-surface-check` names (`spec-pyforge-herald` governs `docsite/**`, `.github/workflows/dashboard.yml` and `docs/dashboard/index.html`), `git add`, run one scoped stamp per named Spec, re-check, and read the exit code.
- The PR carries the `maintenance` label.

**Never:**
- Do not touch `pr-preflight`: its `{ task = "site-check", environment = "site" }` leg stays exactly as today (D8; Story 27.5 changes that lane once steward Story 71.2 has landed).
- Do not rename `dashboard.yml` to `docs.yaml`, and do not edit steward's or platform's tests.
- Do not add a second `deploy-pages` caller, and do not have `kedro-viz-publish.yml` deploy.
- Do not change what `docsite/build.py` renders, apart from the Kedro-Viz neighbour `href` in `docsite/content/site.yml`. The dossier's pages, family pages and artifact build stay as they are (CAP-35, CAP-43, CAP-47).
- Do not write a hand-kept list of redirect paths, and do not duplicate the non-HTML files at their old paths (that would break the one-owner rule).
- Do not commit anything under `docs-site/build/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| full build | `pixi run -e site pages-check` | exit 0; `index.html` (Starlight), `404.html`, `herald/index.html`, `herald/dossier/index.html`, `dashboard/kedro-viz/index.html`, `kedro-viz/` redirect | non-zero names the failing step |
| dossier redirect | old `/dossier/` | `dossier/index.html` is a redirect page to `/herald/dossier/` | none |
| infographic redirect | old `/infographics/<slug>.html` | redirect page to `/herald/infographics/<slug>.html` | none |
| deck family redirects | old `/decks/<slug>/`, `/decks/<slug>/infographic-deck.html`, `/decks/<slug>/executive-summary.html` | each is a redirect page to its `/herald/decks/…` home | none |
| artifact redirect | old `/artifact/dossier.html` | redirect page to `/herald/artifact/dossier.html` | none |
| root | old `/` (the dossier landing) | Starlight's landing, which links to `/herald/`; no redirect page | named exception, not a collision |
| collision | Starlight output already holds `herald/`, `dashboard/` or any redirect path | the assembler exits 1 naming the path | fail loud; nothing overwritten |
| missing redirect | a `herald/**/*.html` page with no redirect at its old path | `pages-check` exits 1 naming it | fail loud |
| missing mount | `herald/dossier/index.html` or `dashboard/kedro-viz/index.html` absent | `pages-check` exits 1 naming it | fail loud |
| non-HTML old path | old `/decks/<slug>/downloads/<file>.pptx`, `/assets/site.css` | not present at the root (404); served under `/herald/` | documented exception |
| broken dossier link | a relative `href` in `herald/` resolving outside the artifact | `pages-check` exits 1 naming the page and link | fail loud |
| old Kedro-Viz URL | `/kedro-viz/` | a redirect page to `/dashboard/kedro-viz/` | none |
| deploy lane | push to `main` | the build job uploads `docs-site/build/site`; the deploy job runs `deploy-pages` | a `site-verify` failure only annotates |
| PR lane | a PR touching `docs/**`, `docs-site/**` or `docsite/**` | `docsite-check.yml` runs `pages-check` | red on exit 1 |
| local preflight | `pixi run -e pyforge-guild pr-preflight` | unchanged: still runs `site-check` in `site` | exit code read, never through a pipe |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-52` (FR-8.2; decisions D2, D7 and D8 in the Spec's `.memlog.md`). Supersedes CAP-44's root and path clauses and keeps CAP-44/CAP-49's single-deployment rule.
Architecture: AD-21 (one Pages artifact, one owner per path prefix, one deploy caller).
Ledger key: `27-2-one-pages-artifact-carries-the-docs-site-the-dossier-and-the-dashboard`.
Ledger status at mint: `backlog`.
Deps: S-27.1 (the Starlight build it mounts beside). Story 27.4 and Story 27.5 depend on this story.
Minted 2026-09-27 from `epics.md`, and amended the same day for the operator's rulings (D7 Pages URLs, D8 `pr-preflight` cost), so `marshal factory dispatch` can resolve this spec.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-27.1 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.2; D2, D7, D8); AD-21; supersedes CAP-44's root and path clauses, keeps CAP-44/CAP-49's single-deployment rule

**Surface:**
- `docsite/tools/assemble_pages.py` (new; a pure `assemble(...)` and a `--check` mode). It:
  - mounts docsite's whole output under `docs-site/build/site/herald/` (`docsite/build.py --out … --check`)
  - copies the tracked `docs/dashboard/` tree, minus its `README.md`, under `docs-site/build/site/dashboard/`
  - writes one redirect page for every HTML file docsite wrote, except the root `index.html`, at that file's old root path. The set is derived from the `herald/` tree, never hand-kept (44 on 2026-09-27); each target is relative
  - refuses, with exit 1 and the path named, when a mount point or a redirect path already exists in Starlight's output; the root `index.html` is the single named exception
  - leaves non-HTML files (`assets/site.css`, `.nojekyll`, the deck downloads) without a redirect
  - `--check` asserts `index.html`, `404.html`, `herald/index.html`, `herald/dossier/index.html`, `dashboard/kedro-viz/index.html`, the `kedro-viz/` redirect, one redirect page per HTML file under `herald/` except its root index, and that every relative `href`/`src` in `herald/` resolves inside the artifact
- `pixi.toml`: `[feature.site.tasks]` gains `pages-build` (`docs-site-build`, then the herald and dashboard mounts and the redirects) and `pages-check` (the assembler's `--check`, depending on `pages-build`). `pr-preflight` is not changed.
- `docs-site/astro.config.mjs`: `redirects`, `/kedro-viz/` → `/dashboard/kedro-viz/`.
- `docsite/content/site.yml`: the Kedro-Viz neighbour `href` becomes `../dashboard/kedro-viz/`, `rel`-prefixed so it resolves at every depth under `/herald/`, and its comment is updated.
- `docsite/README.md` and `docs/dashboard/README.md`: the new mount points and the redirects.
- `.github/workflows/dashboard.yml`, reshaped into upstream `docs.yaml`'s two jobs with its path kept:
  - build job: checkout; setup-pixi `environments: site` (one `pixi-version:` pin, registry site `dashboard.yml setup-pixi`); `configure-pages`, whose `base_url` feeds `SITE_URL`; `pixi run --frozen -e site pages-check`; the advisory `site-verify` step, kept `continue-on-error`; `upload-pages-artifact` of `docs-site/build/site`
  - deploy job: `needs: build`, `environment: github-pages`, `deploy-pages`
  - its triggers, permissions and `concurrency: pages` stay as they are, and its header keeps the race note
- `.github/workflows/docsite-check.yml`:
  - its pip-installed `build.py --check` leg is replaced by `pixi run --frozen -e site pages-check`, so the PR lane predicts the reshaped deploy
  - its `pull_request` and `push` path filters gain `docs/**` and `docs-site/**`, because the lane now builds `docs/` (moved here from 27.4, D8; Story 27.5's selection keys on these paths)
- `.gitignore`: drops the `docs/dashboard/{index.html,.nojekyll,assets/,dossier/,infographics/,decks/,artifact/}` block once nothing writes there.
- `src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py` (new), asserting:
  - `dashboard.yml` is the only file under `.github/workflows/` that uses `actions/deploy-pages`
  - it uploads `docs-site/build/site`, its concurrency group is `pages`, and it triggers on `push: main` and `workflow_dispatch`
  - `docsite-check.yml` runs `pages-check` and carries both new path filters
  - `pr-preflight`'s `site-check` leg is unchanged
  - unit tests over a temp tree cover the happy path, one redirect written per HTML page, a refused collision (a mount or a redirect path already present in Starlight's output), the root exception, and a missing mount

**Given** the Pages root is the dossier landing page that `dashboard.yml` builds into `docs/dashboard/` (CAP-44), serving `/`, `/dossier/`, `/infographics/…`, `/decks/…` and `/artifact/dossier.html`, with Kedro-Viz at `/kedro-viz/`, and Story 27.1's site builds to `docs-site/build/site/`
**When** `pixi run -e site pages-build` and then `pixi run -e site pages-check` run
**Then** both exit 0, and the artifact holds `index.html` (Starlight), `herald/index.html`, `herald/dossier/index.html`, `dashboard/kedro-viz/index.html`, a `kedro-viz/` page that redirects to `/dashboard/kedro-viz/`, and a redirect page at each former root HTML path (`dossier/index.html` → `/herald/dossier/`, and so on for the infographics, deck family pages and `artifact/dossier.html`) except `/`. A planted collision (a Starlight page at a redirect path or a mount point) or a removed mount makes `pages-check` exit 1 and name the path
**And** `dashboard.yml` is the only workflow using `actions/deploy-pages` and it uploads `docs-site/build/site`; `pr-preflight`'s `site-check` leg is unchanged; steward's `tests/meta/test_invariants.py` and `src/platform/tests/test_console_parity_homes.py` pass unedited; `pixi run -e pyforge-guild pixi-version-check` is green; `test_pages_artifact.py` passes in `pyforge-herald-test`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/meta/test_pages_artifact.py` runs inside it).

**Manual checks:**
- `pixi run -e site pages-check` — expected: exit 0. List `docs-site/build/site/` and confirm `index.html`, `herald/index.html`, `herald/dossier/index.html`, `dashboard/kedro-viz/index.html`, `kedro-viz/index.html` (redirect), `dossier/index.html` (redirect to `/herald/dossier/`), and one redirect per HTML file under `herald/` except its root index.
- `pixi run -e pyforge-guild pixi-version-check` — expected: exit 0.
- `pixi run -e pyforge-steward pyforge-steward-test` and `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: the `dashboard.yml` readers stay green.
- After merge: the first `dashboard.yml` run on `main` deploys. The Pages URL then serves the docs landing at `/`, the dossier at `/herald/dossier/` (with `/dossier/` redirecting there), and Kedro-Viz at `/dashboard/kedro-viz/` (with `/kedro-viz/` redirecting there).

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (review layers condensed; diff verified against spec intent-contract)

## Auto Run Result

Status: done

Summary: One GitHub Pages artifact at `docs-site/build/site/`: Starlight at `/`, dossier under `/herald/` with derived legacy HTML redirects, Kedro-Viz under `/dashboard/kedro-viz/`, Astro `/kedro-viz/` redirect, reshaped `dashboard.yml` (build + deploy jobs) and `docsite-check.yml` on `pages-check`.

Files changed:
- `docsite/tools/assemble_pages.py` — assembler and `--check` verifier
- `pixi.toml` — `pages-build` / `pages-check` tasks
- `docs-site/astro.config.mjs` — kedro-viz redirect
- `docsite/content/site.yml` — Kedro-Viz neighbour href for `/herald/` depth
- `.github/workflows/dashboard.yml` / `docsite-check.yml` — unified artifact CI/deploy
- `.gitignore` — drop generated dossier paths under `docs/dashboard/`
- `docsite/README.md`, `docs/dashboard/README.md` — mount layout docs
- `tests/meta/test_pages_artifact.py` — workflow and assembler meta tests
- Co-governor memlogs: `spec-pyforge-herald/.memlog.md`, `spec-pyforge-marshal/.memlog.md`

Review: no patch/defer items.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — pass
- `pixi run --frozen -e site pages-check` — exit 0
- `pixi run --frozen -e pyforge-guild pixi-version-check` — exit 0
- `pytest …/test_invariants.py -k dashboard` — 8 passed
- `python scripts/spec_surface_reconcile.py` — exit 0 (memlog paths named below)

Residual risk: first production deploy on `main` should be watched; `site-verify` remains advisory in CI.
