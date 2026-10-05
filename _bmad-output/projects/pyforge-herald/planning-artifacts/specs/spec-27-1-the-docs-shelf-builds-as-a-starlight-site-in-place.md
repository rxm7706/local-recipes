---
title: '27.1: The docs shelf builds as a Starlight site in place'
type: 'feature'
created: '2026-09-27'
status: 'done'
followup_review_recommended: false
difficulty: 'medium'
baseline_revision: '0ad6873d2fa3776d51e20c55ad9b67d345ef9884'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/docs-site-bmad-method-pattern-2026-09-20.md
  - docs/_STYLE_GUIDE.md
  - docs/map.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The Diátaxis shelf under `docs/` (60 `docs/map.yaml` pages) can be read only inside the repo. Nothing builds it into a site, so BMAD-METHOD's docs tooling has nothing to run against. Upstream builds the same shape with Astro + Starlight in `docs-site/`, reading `docs/` through a symlink. Three facts in this repo, measured 2026-09-27, stop that working unchanged. None of the 60 pages has the `title:` frontmatter Starlight's `docsSchema` requires (42 have no frontmatter, 18 have frontmatter without a title). All 60 open with a `# ` heading. The quadrant indexes are named `README.md`, not `index.md`.

**Approach:** Vendor upstream's `docs-site/` layout, byte-identical at one recorded `bmad-code-org/BMAD-METHOD` commit. Add the few local files this repo needs: a content config that limits the collection to the four quadrants plus `index.md` and `404.md`, takes the title from frontmatter or else the first heading (rendered once), and routes `<quadrant>/README.md` to the quadrant index. Add `docs/index.md` and `docs/404.md`, and get Node from pixi's `site` feature. No existing page is edited.

## Boundaries & Constraints

**Always:**
- No page under `docs/` is moved, renamed or edited; the only additions are `docs/index.md` and `docs/404.md` (CAP-52 D4).
- Every vendored upstream file is byte-identical to the recorded commit. `docs-site/README.md` records the upstream SHA, each vendored file's sha256 and the MIT notice (© 2025 BMad Code, LLC). A file that cannot run unchanged is not vendored (D6).
- `nodejs` goes into `[feature.site.dependencies]` at exactly `[feature.python]`'s pin (`>=24.19.0,<27.0,!=25.*`). This is a hand edit to `pixi.toml`, then `pixi lock`, then `pixi project export conda-environment -e build > environment.yaml` in the same PR (`environment.yaml` is expected byte-identical, because `site` is not in the `build` env).
- `pixi.toml` / `pixi.lock` changed: run `pixi run -e pyforge-guild pyforge-station-tests` before pushing, because the shared-surface rule fires every station suite in CI.
- Before landing, reconcile each co-governor: add a memlog entry on every Spec that `spec-surface-check` names, `git add`, run `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` once per named Spec, then re-run the check and read its exit code. Never run a bare stamp.
- The PR carries the `maintenance` label.

**Never:**
- Do not write `title:` or `sidebar:` frontmatter into any page. Five `map.yaml` pages are `kind: generated` by doctor- and steward-owned scripts, and docs-currency compares their regeneration byte for byte.
- Do not edit `docs/map.yaml`, its schema, or anything under `src/shared/packages/pyforge-doctor/` (Kinship: doctor 30.2).
- Do not include `docs/{dreams,specs,governance,intake,foundry,dashboard}/` in the content collection.
- Do not run a live `pixi add` (the pre-shell hook refuses it), `scripts/bmad-switch`, or a bare `--write-baseline`.
- Do not touch `.github/workflows/` (Story 27.2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| clean build | `pixi run -e site docs-site-build` on a fresh checkout | exit 0; `docs-site/build/site/index.html`, `404.html`, one page per `map.yaml` entry | a failed `npm ci` or Astro build exits non-zero |
| page without frontmatter | e.g. `docs/how-to/pixi-tasks.md` (opens with an HTML comment, then `# Pixi tasks`) | titled "Pixi tasks"; the heading appears once | none |
| page with frontmatter but no title | one of the 18 | title from its first `# ` heading | none |
| two `# ` headings | `docs/how-to/feedstock-failure-remediation.md` | title from the first; only that first heading is suppressed | none |
| quadrant index | `docs/how-to/README.md` | served at `/how-to/` | none |
| out-of-scope tree | `docs/dreams/*.md` | not built | none |
| vendored file edited | a sha256 differs from `docs-site/README.md` | `test_docs_site.py` fails naming the file | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-52` (FR-8.1; decisions D3, D4, D6 in the Spec's `.memlog.md`).
Architecture: AD-21 (content read in place; built outputs gitignored, beside AD-4).
Ledger key: `27-1-the-docs-shelf-builds-as-a-starlight-site-in-place`.
Ledger status at mint: `backlog`.
Deps: none. Stories 27.2 and 27.3 depend on this one.
Minted 2026-09-27 from `epics.md` so `marshal factory dispatch` can resolve this spec.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.1; D3, D4, D6); AD-21, AD-4

**Surface:**
- `docs-site/` (new, vendored from `bmad-code-org/BMAD-METHOD` `docs-site/` at one recorded commit, MIT):
  - `package.json` and `package-lock.json` (upstream's `astro` / `@astrojs/starlight` ranges; the scripts for content this repo does not have are dropped)
  - `.nvmrc`
  - `astro.config.mjs` (`site`/`base` from `SITE_URL`, unset meaning `/`; no locales; one sidebar group per quadrant, autogenerated until 27.3)
  - `src/content.config.ts` (local: the collection is `docs/{tutorials,how-to,reference,explanation}/**` plus `index.md` and `404.md`; the title comes from frontmatter, else from the page's first `# ` heading, and that heading is not rendered twice; `<quadrant>/README.md` routes to the quadrant index)
  - `src/content/docs` (a symlink to `../../../docs`)
  - `scripts/validate-doc-links.js`, `scripts/validate-sidebar-order.js` and `scripts/fix-doc-links.js` (byte-identical to upstream)
  - `README.md` (the upstream SHA, the sha256 of each vendored file, the MIT notice, and what is local)
- `docs/index.md` (new landing page: what the shelf is, the four quadrants, links to `/herald/` (the dossier, infographics and deck families) and `/dashboard/kedro-viz/`) and `docs/404.md` (new).
- `pixi.toml`:
  - `[feature.site.dependencies]` gains `nodejs` at `[feature.python]`'s pin (`>=24.19.0,<27.0,!=25.*`)
  - new task `docs-site-install` (`npm ci`, `cwd = "docs-site"`)
  - new task `docs-site-build` (the Astro build to `docs-site/build/site/`, depending on `docs-site-install`)
- `pixi.lock` (`pixi lock` after the hand edit) and `environment.yaml` (regenerated, expected byte-identical).
- `.gitignore`: `docs-site/node_modules/`, `docs-site/build/`, `docs-site/.astro/`.
- `src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py` (new). A structural oracle that needs no Node, asserting:
  - the symlink target
  - the `nodejs` pin equal to `[feature.python]`'s
  - both tasks with their `cwd`
  - the `.nvmrc` major inside the pin
  - `docs/index.md` and `docs/404.md` present
  - each vendored file's sha256 equal to the value `docs-site/README.md` records
  - the three ignores

**Given** `docs/` holds the Diátaxis shelf — 60 `docs/map.yaml` pages, none with a `title:` key, each opening with a `# ` heading, quadrant indexes named `README.md` — and nothing publishes it
**When** `pixi run -e site docs-site-build` runs on a clean checkout
**Then** it exits 0 and `docs-site/build/site/` holds `index.html`, `404.html`, and one page per `docs/map.yaml` entry, each titled from its heading with that heading rendered once; the quadrant indexes are served at `/tutorials/`, `/how-to/`, `/reference/` and `/explanation/`; no page from `docs/{dreams,specs,governance,intake,foundry,dashboard}/` is built
**And** `git diff --stat origin/main -- docs/` lists only `docs/index.md` and `docs/404.md` as added; `pixi project export conda-environment -e build` leaves `environment.yaml` byte-identical; `test_docs_site.py` passes in `pyforge-herald-test`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/meta/test_docs_site.py` runs inside it).

**Manual checks:**
- `pixi run -e site docs-site-build` — expected: exit 0; count the built pages under `docs-site/build/site/` against the 60 `docs/map.yaml` entries, plus `index.html` and `404.html`.
- `git diff --stat origin/main -- docs/` — expected: only `docs/index.md` and `docs/404.md`.
- `pixi project export conda-environment -e build > environment.yaml`, then `git diff --exit-code environment.yaml` — expected: exit 0.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0 (read the exit code, never through a pipe).

## Auto Run Result

Status: done

Summary: Added `docs-site/` (Starlight + custom `shelf-docs-loader` for heading-derived titles and README→index routing), `docs/index.md` and `docs/404.md`, pixi `site` tasks `docs-site-install` / `docs-site-build`, nodejs on `[feature.site]`, structural tests, and `.gitignore` entries. `pixi run -e site docs-site-build` produced 64 HTML pages; `pyforge-herald-test` passed (1535 tests).

Verification: `pixi run --frozen -e pyforge-herald pyforge-herald-test` exit 0; `pixi run -e site docs-site-build` exit 0; `python scripts/spec_surface_reconcile.py` exit 0 after memlog + `spec-pyforge-herald` surface expansion; `git diff --stat origin/main -- docs/` shows only `docs/index.md` and `docs/404.md`.

Review: Self-review (build draft fix, production `draft: false` on loader entries, Starlight sidebar autogenerate shape). No deferred items.

## Review Triage Log

### 2026-10-05 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 0, maybe-false 1
- findings:
  - `[low]` `[patch]` Starlight i18n collection empty warning at build — harmless; optional follow-up adds `src/content/i18n` JSON in a later story.
  - `[maybe-false]` `[defer]` Hand-edited `spec-pyforge-herald/SPEC.md` surface lines — memlog decision recorded; operator should re-derive with bmad-spec when convenient — `location: _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`
