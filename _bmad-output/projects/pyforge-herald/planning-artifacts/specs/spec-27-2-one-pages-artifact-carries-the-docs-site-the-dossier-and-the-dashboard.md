---
title: '27.2: One Pages artifact carries the docs site, the dossier and the dashboard'
type: 'feature'
created: '2026-09-27'
status: 'ready'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/docs-site-bmad-method-pattern-2026-09-20.md
  - .github/workflows/dashboard.yml
  - .github/workflows/docsite-check.yml
  - docsite/README.md
  - docs/dashboard/README.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** GitHub Pages serves one artifact per repository. Today that artifact is `docs/dashboard/`: `dashboard.yml` builds the dossier (`docsite/build.py`) straight into it as the site root, next to the tracked Kedro-Viz export at `kedro-viz/` (CAP-44). Story 27.1's Starlight site builds to `docs-site/build/site/` and has nowhere to publish. A second workflow calling `deploy-pages` would race `dashboard.yml` and wipe the Kedro-Viz export, as that workflow's own header says, so a second deploy is not an option.

**Approach:** Assemble one artifact at `docs-site/build/site/`, with one owner per path prefix:

- Starlight at the root.
- docsite's whole output under `/dossier/`. Its links are relative (`build.py:132-134`, `339-341`), so it renders unchanged under a prefix.
- The tracked `docs/dashboard/` tree under `/dashboard/`, with a `/kedro-viz/` redirect so the old public URL still answers.

Reshape `dashboard.yml`, keeping its path, into upstream `docs.yaml`'s build and deploy jobs in the pixi `site` env. Point `docsite-check.yml` at the same `pages-check` task, so a PR predicts the deploy (CAP-52 D2, AD-21).

## Boundaries & Constraints

**Always:**
- `.github/workflows/dashboard.yml` stays the only file under `.github/workflows/` that uses `actions/deploy-pages`, and it keeps its path. Steward's `tests/meta/test_invariants.py:885`, `src/platform/tests/test_console_parity_homes.py:255` and `scripts/pixi_version_registry.py:61` read it. Its triggers (`push: main`, `workflow_dispatch`), permissions and `concurrency: pages` stay as they are, and its header keeps the race note.
- `dashboard.yml` keeps exactly one `pixi-version:` pin, so registry site `dashboard.yml setup-pixi` stays valid. If a second pin appears, register it in `scripts/pixi_version_registry.py` in the same PR. `pixi run -e pyforge-guild pixi-version-check` must be green.
- The assembler refuses, with exit 1 and the path named, any mount point that already exists in Starlight's output. It never deletes outside `docs-site/build/site/`.
- `verify_claims.py` (`site-verify`) stays advisory in the deploy (`continue-on-error`), as CAP-46 requires.
- `pr-preflight`'s `site` leg becomes `pages-check`, so the local run predicts `docsite-check.yml`. `pixi.toml` changed: run `pixi run -e pyforge-guild pyforge-station-tests` first, and regenerate `environment.yaml` (expected byte-identical).
- Before landing, reconcile each co-governor: add a memlog entry on every Spec that `spec-surface-check` names (`spec-pyforge-herald` governs `docsite/**`, `.github/workflows/dashboard.yml` and `docs/dashboard/index.html`), `git add`, run one scoped stamp per named Spec, re-check, and read the exit code.
- The PR carries the `maintenance` label.

**Never:**
- Do not rename `dashboard.yml` to `docs.yaml`, and do not edit steward's or platform's tests.
- Do not add a second `deploy-pages` caller, and do not have `kedro-viz-publish.yml` deploy.
- Do not change what `docsite/build.py` renders, apart from the Kedro-Viz nav `href` in `docsite/content/site.yml`. The dossier's pages, family pages and artifact build stay as they are (CAP-35, CAP-43, CAP-47).
- Do not commit anything under `docs-site/build/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| full build | `pixi run -e site pages-check` | exit 0; `index.html`, `404.html`, `dossier/index.html`, `dossier/dossier/index.html`, `dashboard/kedro-viz/index.html`, `kedro-viz/` redirect | non-zero names the failing step |
| collision | Starlight output already contains `dossier/` | the assembler exits 1 naming `dossier/` | fail loud; nothing overwritten |
| missing mount | `dashboard/kedro-viz/index.html` absent | `pages-check` exits 1 naming it | fail loud |
| broken dossier link | a relative `href` in `dossier/` resolving outside the artifact | `pages-check` exits 1 naming the page and link | fail loud |
| old URL | `/kedro-viz/` | a redirect page to `/dashboard/kedro-viz/` | none |
| deploy lane | push to `main` | the build job uploads `docs-site/build/site`; the deploy job runs `deploy-pages` | `site-verify` failure only annotates |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-52` (FR-8.2; decision D2 in the Spec's `.memlog.md`). Supersedes CAP-44's root and path clauses and keeps CAP-44/CAP-49's single-deployment rule.
Architecture: AD-21 (one Pages artifact, one owner per path prefix, one deploy caller).
Ledger key: `27-2-one-pages-artifact-carries-the-docs-site-the-dossier-and-the-dashboard`.
Ledger status at mint: `backlog`.
Deps: S-27.1 (the Starlight build it mounts beside).
Minted 2026-09-27 from `epics.md` so `marshal factory dispatch` can resolve this spec.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-27.1 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.2; D2); AD-21; supersedes CAP-44's root and path clauses, keeps CAP-44/CAP-49's single-deployment rule

**Surface:**
- `docsite/tools/assemble_pages.py` (new; a pure `assemble(...)` and a `--check` mode):
  - mounts docsite's output under `docs-site/build/site/dossier/` (`docsite/build.py --out … --check`)
  - copies the tracked `docs/dashboard/` tree, minus its `README.md`, under `docs-site/build/site/dashboard/`
  - refuses, with exit 1 and the path named, when a mount point already exists in Starlight's output
  - `--check` asserts `index.html`, `404.html`, `dossier/index.html`, `dashboard/kedro-viz/index.html` and the `kedro-viz/` redirect, and that every relative `href`/`src` in the `dossier/` tree resolves inside the artifact
- `pixi.toml`:
  - `[feature.site.tasks]` gains `pages-build` (`docs-site-build`, then the dossier and dashboard mounts) and `pages-check` (the assembler's `--check`, depending on `pages-build`)
  - `pr-preflight`'s `{ task = "site-check", environment = "site" }` leg becomes `pages-check`, with its description saying why
- `docs-site/astro.config.mjs`: `redirects`, `/kedro-viz/` → `/dashboard/kedro-viz/`.
- `docsite/content/site.yml`: the Kedro-Viz nav `href` becomes `../dashboard/kedro-viz/`, and its comment is updated.
- `docsite/README.md` and `docs/dashboard/README.md`: the new mount points.
- `.github/workflows/dashboard.yml`, reshaped into upstream `docs.yaml`'s two jobs with its path kept:
  - build job: checkout; setup-pixi `environments: site` (one `pixi-version:` pin, registry site `dashboard.yml setup-pixi`); `configure-pages`, whose `base_url` feeds `SITE_URL`; `pixi run --frozen -e site pages-check`; the advisory `site-verify` step, kept `continue-on-error`; `upload-pages-artifact` of `docs-site/build/site`
  - deploy job: `needs: build`, `environment: github-pages`, `deploy-pages`
  - its triggers, permissions and `concurrency: pages` stay as they are, and its header keeps the race note
- `.github/workflows/docsite-check.yml`: its pip-installed `build.py --check` leg is replaced by `pixi run --frozen -e site pages-check`, so the PR lane predicts the reshaped deploy.
- `.gitignore`: drops the `docs/dashboard/{index.html,.nojekyll,assets/,dossier/,infographics/,decks/,artifact/}` block once nothing writes there.
- `src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py` (new), asserting:
  - `dashboard.yml` is the only file under `.github/workflows/` that uses `actions/deploy-pages`
  - it uploads `docs-site/build/site`, its concurrency group is `pages`, and it triggers on `push: main` and `workflow_dispatch`
  - `pr-preflight` carries `pages-check` in `site`, and `docsite-check.yml` runs `pages-check`
  - unit tests over a temp tree cover the happy path, a refused collision and a missing mount

**Given** the Pages root is the dossier landing page that `dashboard.yml` builds into `docs/dashboard/` (CAP-44), with Kedro-Viz at `/kedro-viz/`, and Story 27.1's site builds to `docs-site/build/site/`
**When** `pixi run -e site pages-build` and then `pixi run -e site pages-check` run
**Then** both exit 0, and the artifact holds `index.html` (Starlight), `dossier/index.html`, `dossier/dossier/index.html`, `dashboard/kedro-viz/index.html` and a `kedro-viz/` page that redirects to `/dashboard/kedro-viz/`; a planted collision or a removed mount makes `pages-check` exit 1 and name the path
**And** `dashboard.yml` is the only workflow using `actions/deploy-pages` and it uploads `docs-site/build/site`; steward's `tests/meta/test_invariants.py` and `src/platform/tests/test_console_parity_homes.py` pass unedited; `pixi run -e pyforge-guild pixi-version-check` is green; `test_pages_artifact.py` passes in `pyforge-herald-test`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/meta/test_pages_artifact.py` runs inside it).

**Manual checks:**
- `pixi run -e site pages-check` — expected: exit 0; list `docs-site/build/site/` and confirm `index.html`, `dossier/index.html`, `dashboard/kedro-viz/index.html` and `kedro-viz/index.html` (the redirect).
- `pixi run -e pyforge-guild pixi-version-check` — expected: exit 0.
- `pixi run -e pyforge-steward pyforge-steward-test` and `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: the `dashboard.yml` readers stay green.
- After merge: the first `dashboard.yml` run on `main` deploys, and the Pages URL serves the docs landing at `/`, the dossier at `/dossier/` and Kedro-Viz at `/dashboard/kedro-viz/`.
