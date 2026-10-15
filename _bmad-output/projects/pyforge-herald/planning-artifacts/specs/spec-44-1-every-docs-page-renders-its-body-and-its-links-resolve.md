---
title: '44.1: Every docs page renders its body and its links resolve'
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '22e5c19c285e722bcf7d58203689d57e9cc4dd55'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs-site/src/loaders/shelf-docs-loader.ts
  - docs-site/astro.config.mjs
  - docs-site/README.md
  - docsite/tools/assemble_pages.py
  - docs/index.md
  - docs/reference/developer-guide.md
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the docs shelf on Pages published every page with an empty body from 2026-10-08, when the unified artifact
(CAP-52, Story 27.2) first deployed it. Measured on the live site 2026-10-14:

- The Starlight markdown container (`sl-markdown-content`) of `/`, `/how-to/pixi-tasks/`,
  `/explanation/the-detector-framework/` and `/tutorials/getting-started/` holds 0 words. The first sentence of
  `docs/how-to/pixi-tasks.md` ("Task-oriented reference for the pixi tas…") appears nowhere in its page, which has no
  `<p>` element at all.
- **Cause.** `docs-site/src/loaders/shelf-docs-loader.ts` calls `store.set({ id, data, body, filePath })` and never sets
  `rendered`. Starlight renders an entry's `rendered` HTML, so every page shows its title, sidebar and table of contents
  and nothing else.
- **Why nobody saw it.** `pages-check` (`docsite/tools/assemble_pages.py` `check()`) walks links on herald pages only
  (`_check_href_resolution` iterates `_iter_herald_html`), and no check reads a shelf body. The upstream link validator
  checks the markdown sources, not the built pages.
- **What rendering exposes.** The 70 shelf pages (69 plus the 404 page) hold 678 links in their bodies. They point at `.md` paths (`/tutorials/README.md`,
  `../reference/x.md`), at `README.md` files the loader publishes as directory indexes, and at repo files the shelf does
  not publish (`docs/MAP.md`, `docs/governance/**`, `docs/governance/guild-roster.json`, a TOML example). Upstream
  BMAD-METHOD rewrites links with two rehype plugins, `src/rehype-markdown-links.js` and `src/rehype-base-paths.js`,
  which this repo never vendored. `docs/reference/developer-guide.md` also embeds four GitHub Actions badge images that
  would load from github.com, which herald:AD-21 forbids.

**Approach:** render each body in the loader with the project's markdown pipeline
(`renderMarkdown(body, { fileURL })`), and give that pipeline three rehype plugins, in order: a local
`src/rehype-shelf-links.js` (a `README.md` link the shelf publishes becomes `index.md`; a link to a repo file the shelf
does not publish becomes that file's repository page), then upstream's `rehype-markdown-links.js` and
`rehype-base-paths.js`, vendored byte-identical at the commit `docs-site/README.md` records. The loader and the local
plugin share one publish rule, `src/lib/shelf.mjs`. The badge images become text links. `pages-check` gains a shelf
check: every shelf page's body is non-empty and every local link in it resolves inside the artifact under the base path.

### Living CAP citations

- **Parent.** A fix under `spec-pyforge-herald` CAP-52 (the docs site matches BMAD-METHOD's pattern), whose success
  clause already requires one page per `docs/map.yaml` entry; no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
- **Architecture.** herald:AD-21: one artifact; no third-party origin loads; "re-vendor, never fork" (rule 5) — the two
  plugins arrive byte-identical, and local behaviour lives in a local file.
- **Origin.** `docs/dreams/pyforge-herald.md` Realization log, 2026-10-14 (every docs page is empty); the operator's
  ask in session, "Fix the docs root rendering an empty body", raised during Story 41.1's review.

## Acceptance Criteria

- **AC1 — Bodies render.** In the built artifact, every shelf page's `sl-markdown-content` holds at least one word, and
  `how-to/pixi-tasks/index.html` contains the first sentence of `docs/how-to/pixi-tasks.md`. Measured on the fixed build:
  70 shelf pages, 0 empty. The body is the container alone, depth-tracked on `div`; Starlight's Previous/Next footer is
  never counted.
- **AC2 — Shelf links resolve.** Every local link in a shelf body resolves to a file inside the artifact under the base
  path: a `README.md` link to its directory index, a `.md` link to its page route, a directory link to its absolute
  route (a non-index page is served one level deeper than its file), a `docs/dashboard/**` link to its served path, and
  a link to a repo file or directory the site does not serve to `https://github.com/<repo>/blob|tree/main/<path>`.
  Percent-escapes are decoded on both sides. Measured: 678 body URLs, 0 dead, 19 sent to the repository.
- **AC3 — Vendored, not forked.** `docs-site/src/rehype-markdown-links.js` and `docs-site/src/rehype-base-paths.js`
  have the git blob ids of upstream's files at `561eeedf386bc7cb164c577c423dc4484056a759`, and `docs-site/README.md`
  lists their sha256 in the vendored table, so `tests/meta/test_docs_site.py` pins them. No previously vendored file
  changes.
- **AC4 — No third-party image.** `docs/reference/developer-guide.md` carries no badge image; its four CI workflows are
  plain links. `pages-check`'s cross-origin check reports 0 findings on shelf pages.
- **AC5 — The check guards it.** `pages-check` exits 1 naming the page on an empty shelf body, on a shelf link that does
  not resolve, on a shelf link missing the base path, on a link escaping the artifact, on a relative link on the 404
  page (it is served at any missing path), on a broken `img`/`source`/media `src`, and when the artifact has no shelf
  page at all; nested `div`s in a body (code blocks) do not end it early; `check()` calls the shelf check
  (`tests/meta/test_pages_shelf_check.py`, 12 cases).
- **AC6 — Gates.** `pixi run --frozen -e site pages-check`, `pixi run --frozen -e site docs-site-validate` and
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` exit 0.

## Boundaries & Constraints

- No page moves and no URL changes; the loader's publish rule is unchanged, only moved into `src/lib/shelf.mjs`.
- The five previously vendored files keep their hashes; the two new vendored files are never edited.
- `unist-util-visit` 5.1.0 was already in the lockfile (through `@astrojs/markdown-remark`); it is now declared, because
  the local plugin imports it.
- Links to repo files point at `blob/main/`, not at the build's commit, so a rebuild with unchanged inputs produces the
  same bytes (steward Story 102.2's no-op skip compares them).

## I/O & Edge-Case Matrix

| Input link in `docs/how-to/x.md` | Rendered href | Why |
|---|---|---|
| `../reference/README.md` | `/local-recipes/reference/` | README is the directory index |
| `./y.md#part` | `/local-recipes/how-to/y/#part` | upstream plugin, fragment kept |
| `../MAP.md` | `https://github.com/rxm7706/local-recipes/blob/main/docs/MAP.md` | not a shelf page |
| `../governance/guild-roster.json` | `https://github.com/rxm7706/local-recipes/blob/main/docs/governance/guild-roster.json` | not a shelf page |
| `../../AGENTS.md` | `https://github.com/rxm7706/local-recipes/blob/main/AGENTS.md` | outside `docs/` |
| `../` | `/local-recipes/` | a directory: its absolute route |
| `../governance/` | `https://github.com/rxm7706/local-recipes/tree/main/docs/governance` | a directory with no page |
| `../dashboard/kedro-viz/` | `/local-recipes/dashboard/kedro-viz/` | served as-is by the assembler |
| `../My%20Notes.md` (unpublished) | `https://github.com/rxm7706/local-recipes/blob/main/docs/My%20Notes.md` | decoded to find the file |
| `herald/` (from `index.md`) | `herald/` | not under `docs/`: left alone (an artifact route from the root page) |
| `./missing.md` | `/local-recipes/how-to/missing/` | missing target: left for the validator and `pages-check` |
| `https://example.org` | unchanged | external |

## Binding

- Parent Spec capability: a fix under `spec-pyforge-herald` CAP-52; no CAP minted.
- Architecture: herald:AD-21 (unamended).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-14 (every docs page is empty) entry.
- Epic: Epic 44, Story 44.1.
- Ledger key: `44-1-every-docs-page-renders-its-body-and-its-links-resolve`.
- Ledger status at mint: `done` (specced and fixed in the same change, as mason Story 24.1 was in PR #1669).
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."44"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1).

## Epic excerpt

Story 44.1 in `epics.md` § Epic 44: every docs page renders its body and its links resolve.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e site pages-check` — expected: exit 0 (AC1, AC2, AC4, AC5 on the real build).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e site docs-site-install` — expected: exit 0 (`npm ci` accepts the declared dependency).
- `git hash-object docs-site/src/rehype-markdown-links.js docs-site/src/rehype-base-paths.js` against
  `gh api repos/bmad-code-org/BMAD-METHOD/contents/docs-site/src/<file>?ref=561eeedf38… --jq .sha` — expected: equal (AC3).
- Mutation: replace the loader's `rendered: await renderMarkdown(...)` line with nothing — expected: `pages-check` exits 1
  with `empty shelf page body:` naming the first page. Also: empty one leaf page's container in a copy of the built
  artifact — expected: `_check_shelf_pages` exits 1 naming that page (run 2026-10-14 on `how-to/pixi-tasks/index.html`).
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and scoped stamp.

## Named, not fixed here

- The redirect stubs, herald pages and dashboard mount are judged by the checks that already cover them; this story adds
  shelf pages only.
- Epic 43 (one generator) replaces `assemble_pages.py`; `_check_shelf_pages` moves with it then.

## Spec Change Log

- 2026-10-14: specced and fixed in the same change, at the operator's ask in session. Measured on the live site and on
  the fixed build the same day.
- 2026-10-14 (independent review before commit): seven findings, all fixed in this change. High: the empty-body check
  matched from the container to `</main>`, so Starlight's Previous/Next footer counted as body and only `index.html` and
  `404.html` could fail (the first mutation passed only because `404.html` sorts first); the body is now parsed with
  `div` depth. Medium: relative directory links landed one level off on non-index pages; they now become absolute
  routes. Low: no test exercised `check()`'s call; `%`-escapes were not decoded; `docs/dashboard/**` links went to the
  repository instead of the served file; no containment check; relative links on the 404 page; `src` attributes
  unchecked. The first measurements (69 pages, 812 links, 13 to the repository) counted footer links; the exact
  numbers are 70 pages, 678 body URLs, 19 to the repository.

</intent-contract>

## Review Triage Log

### 2026-10-14 — Independent review pass

- verdicts: 7 findings — high 1, medium 1, low 5; all fixed in this change (see Spec Change Log)

## Auto Run Result

Status: done

**Files changed:**
- `docs-site/src/loaders/shelf-docs-loader.ts` — renders each body; the publish rule moves to `src/lib/shelf.mjs`
- `docs-site/src/lib/shelf.mjs` — new: the publish rule and the repository URL
- `docs-site/src/rehype-shelf-links.js` — new, local: README → index; unpublished repo file → repository page
- `docs-site/src/rehype-markdown-links.js`, `docs-site/src/rehype-base-paths.js` — new, vendored byte-identical
- `docs-site/astro.config.mjs` — the three rehype plugins
- `docs-site/README.md` — two vendored sha256 rows; the local files listed
- `docs-site/package.json`, `docs-site/package-lock.json` — `unist-util-visit` declared
- `docsite/tools/assemble_pages.py` — `_check_shelf_pages` in `check()`
- `docs/index.md` — the Kedro-Viz link points at `dashboard/kedro-viz/`
- `docs/reference/developer-guide.md` — badge images become text links
- `src/shared/packages/pyforge-herald/tests/meta/test_pages_shelf_check.py` — new; three fixtures gain a shelf body
