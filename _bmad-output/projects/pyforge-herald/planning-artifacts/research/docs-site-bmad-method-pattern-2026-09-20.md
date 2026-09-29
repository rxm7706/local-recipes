---
title: 'Research: the docs site matches BMAD-METHOD's pattern'
chain: pyforge-herald
created: 2026-09-20
updated: 2026-09-20
status: input-for-bmad-spec
---

# Research — the docs site matches BMAD-METHOD's pattern (2026-09-20)

Operator ask 09:55Z: *"lets design our docs and docs deployment to github pages to match what
BMAD-METHOD itself does, so that we can reuse their patterns, skills and workflows."* This note
records what upstream does (verified 2026-09-20 against `bmad-code-org/BMAD-METHOD@main` via the
GitHub API and raw files), what this repo has, and the decisions `bmad-spec` needs.

## 1. What BMAD-METHOD does (verified)

| Piece | Upstream (MIT, © 2025 BMad Code, LLC) |
|---|---|
| Content | `docs/` at the repo root: `index.md`, `404.md`, `_STYLE_GUIDE.md`, `start/`, `plan/`, `build/`, `customize/`, `existing-codebases/`, `reference/`, `images/`, plus locale trees (`cs`, `fr`, `ko-kr`, `vi-vn`, `zh-cn`). The style guide names the Diátaxis quadrants (`tutorials/`, `how-to/`, `explanation/`, `reference/`) as the content shape. |
| Site | `docs-site/`: Astro + `@astrojs/starlight`; `src/content/docs -> ../../../docs` (a symlink, so content never moves); `astro.config.mjs` sets `site`/`base` from `SITE_URL`, rehype plugins `rehypeInlineDiagrams` (hand-authored SVGs in `docs-site/src/diagrams/`, inlined, `data-i18n` labels), `rehypeMarkdownLinks`, `rehypeBasePaths`; `defaultLocale: 'root'` + `locales` from `src/lib/locales.mjs`; an explicit `sidebar` with `autogenerate` for `reference`. |
| Scripts | `build` (`scripts/build-docs.mjs`, validates links first), `validate-links`, `validate-sidebar` (`sidebar.order` frontmatter), `fix-links` (relative → repo-relative, `--write`), `locale-coverage`, `export-readme-diagrams`, `lint`/`format` (eslint + prettier over `scripts/`, `test/`), `test` (site URL, rehype plugins, redirects, locale coverage). |
| Deploy | `.github/workflows/docs.yaml`: on push to `dev` for `docs/**`, `docs-site/**`, the workflow itself, or `workflow_dispatch`; `permissions: contents: read, pages: write, id-token: write`; `concurrency: group: pages`; `build` job (`working-directory: docs-site`, `setup-node` from `docs-site/.nvmrc` with npm cache, `npm ci`, `npm run build` with `SITE_URL: ${{ vars.SITE_URL }}`, `upload-pages-artifact@v3` of `build/site`); `deploy` job (`environment: github-pages`, `deploy-pages@v4`). |
| Style | `docs/_STYLE_GUIDE.md`: Google developer style + Diátaxis; Starlight admonitions (`:::tip|note|caution|danger[Title]`); no `---` rules, no `####`, 8–12 `##` per doc; typed page structures (tutorial / how-to / explanation / reference sub-types / glossary). Vendored into this repo 2026-09-20 as `docs/_STYLE_GUIDE.md` (the `bmad-os-diataxis` skill reads it). |

## 2. What this repo has

- `docs/` already holds the four Diátaxis quadrants mapped by `docs/MAP.md` (doctor Epic 22/23) and, since doctor 30.2, the machine twin `docs/map.yaml` from which `MAP.md` renders; authored pages carry `sources:` / `verified:` (doctor 30.1). Outside the quadrants: `dreams/`, `specs/` (legacy), `governance/`, `intake/`, `foundry/`, `dashboard/`.
- The published Pages site is **herald's `docsite/`** (Jinja2 + YAML: `content/dossier.yml`, `content/site.yml`, `tools/verify_claims.py`, `build.py --out docs/dashboard --check`), deployed by `.github/workflows/dashboard.yml` (`upload-pages-artifact@v5`) together with the Kedro-Viz dashboard; `docsite-check.yml` gates PRs. It publishes the dossier + infographics, **not** the Diátaxis shelf — the shelf is readable only in the repo.
- No Node toolchain, no Starlight, no sidebar ordering, no link validator for `docs/`; `docs-map-hygiene` (doctor) is the closest thing to `validate-links`.

## 3. The gap, and the decisions `bmad-spec` must take

1. **Owner.** The site is herald's (docsite, Pages deploy); the shelf's registry is doctor's (`map.yaml`). Proposal: herald owns the site + deploy (this chain); doctor's `map.yaml` becomes the sidebar's source (`sidebar.order` ↔ `map.yaml` order, one generator), so the two registries never diverge — Kinship to doctor 30.x.
2. **One Pages site or two.** Pages serves one artifact per repo. Upstream serves the docs at the site root. Here the dossier/infographics and the Kedro-Viz dashboard already share the artifact under `docs/dashboard/`. Proposal: Starlight builds to `build/site/`, the existing `docsite/build.py` and dashboard outputs are copied under it (`/dossier/`, `/dashboard/`), one `upload-pages-artifact`; `dashboard.yml` merges into a single `docs.yaml` shaped like upstream's. The `deploy-pages` race note in `dashboard.yml` is the reason a second workflow is not acceptable.
3. **Toolchain.** Node via pixi (`nodejs` in a `docs-site` feature) so `npm ci` runs inside `pixi run`; `.nvmrc` kept for parity with upstream's workflow; `docs-site/` vendored from upstream's layout (config, scripts, tests) with our `SITE_URL`/`base`, no locales at first.
4. **Content moves nothing.** The symlink architecture is the point: `docs/` stays where doctor's detectors read it; only `docs/index.md` (the landing page) and `docs/404.md` are new, and `_STYLE_GUIDE.md` is already in place.
5. **Validators become detectors.** `validate-links` / `validate-sidebar` run in `docsite-check.yml` for PRs and are mirrored as `pixi` tasks; `docs-map-hygiene` stays the repo-side twin.
6. **Skills and workflows reuse.** With the same layout and style guide, upstream's `bmad-os-diataxis` / docs-audit skills, its link fixers and sidebar validator apply unchanged; re-vendor, never fork.

## 4. Sources

- https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/_STYLE_GUIDE.md (raw fetched 2026-09-20, 411 lines)
- https://github.com/bmad-code-org/BMAD-METHOD/tree/main/docs-site (`README.md`, `astro.config.mjs`, `package.json`, `scripts/`, `test/`)
- https://github.com/bmad-code-org/BMAD-METHOD/blob/main/.github/workflows/docs.yaml
- https://github.com/bmad-code-org/BMAD-METHOD/blob/main/LICENSE (MIT)
- This repo: `docsite/README.md`, `.github/workflows/dashboard.yml`, `.github/workflows/docsite-check.yml`, `docs/MAP.md`, doctor Stories 30.1–30.3.
