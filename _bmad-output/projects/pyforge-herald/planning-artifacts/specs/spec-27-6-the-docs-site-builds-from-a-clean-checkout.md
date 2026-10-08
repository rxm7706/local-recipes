---
title: '27.6: The docs site builds from a clean checkout'
type: 'fix'
created: '2026-10-08'
status: 'in-progress'
difficulty: 'easy'
baseline_revision: 'd576ac1f1d46693db4d0e0e43fbc2ff845a68ef3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-27-1-the-docs-shelf-builds-as-a-starlight-site-in-place.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md
  - docs-site/astro.config.mjs
  - docs-site/README.md
  - docs-site/src/content.config.ts
  - .gitignore
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py
  - .github/workflows/pyforge-station-tests.yml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Starlight docs site (Story 27.1, FR-8.1, AD-21) cannot build from a clean checkout, and no test notices.

- **The import.** `docs-site/astro.config.mjs:4` reads `import { getSiteUrl } from './src/lib/site-url.mjs';`, and
  `docs-site/README.md:26` lists `src/lib/site-url.mjs` as "copied from upstream at the recorded commit (URL
  resolution helper)".
- **The ignore.** The root `.gitignore` rule `lib/` (`:40`, in the Python-packaging block) matches any directory named
  `lib`, so it also matches `docs-site/src/lib/`. `git check-ignore -v docs-site/src/lib/site-url.mjs` prints
  `.gitignore:40:lib/`.
- **Never tracked.** `git log --all -- docs-site/src/lib/site-url.mjs` is empty. Story 27.1's dispatch built green
  (its Auto Run Result reports 64 pages) because the file sat untracked in its worktree. Its auto-checkpoint
  `773f656f03` and its landing `c47bbb99e4` (2026-10-05) never staged it, and no worktree of this repository holds it
  now.
- **Measured on `054bb4e795` (2026-10-08).** In a fresh `git clone`, `pixi run --frozen -e site docs-site-build`
  runs `npm ci`, then `astro build` exits 1 with `[astro] Unable to load your Astro config` and "Failed to load url
  ./src/lib/site-url.mjs ... Does the file exist?". With upstream's file copied into the same clone, the build exits 0
  and writes 64 HTML pages (`index.html`, `404.html`, the four quadrants), and that file is the only one missing.
- **Why nothing caught it.** `tests/meta/test_docs_site.py` checks the symlink, the Node pin, the two tasks, the
  `.nvmrc` major, the landing pages, the vendored sha256 rows and the three ignores. It never asks whether a file the
  config imports is tracked, and it runs in the working tree, where an untracked file passes. Herald's job in
  `pyforge-station-tests.yml` runs on `src/shared/packages/pyforge-herald/**` and `presentations/**`, not
  `docs-site/**`. No CI lane builds the site yet (Story 27.2 adds that). The PRD's and spine's § Currency
  reconciliation — 2026-10-07 and the 2026-10-07 retro recorded the gap and left it for a fix story.
- **What is NOT the problem.** The config and the loader are right. `docs-site/src/content.config.ts` imports
  `./loaders/shelf-docs-loader`, which is tracked. The helper's behaviour is upstream's and is not changed here.

**Approach:** track the upstream helper behind a narrow `.gitignore` exception, and make "every file the site loads is
tracked" a test.

- **The file.** `docs-site/src/lib/site-url.mjs` is upstream's file, byte-identical (AD-21 rule 5, D6: re-vendor,
  never fork). Source: `bmad-code-org/BMAD-METHOD`, path `docs-site/src/lib/site-url.mjs`, at the commit
  `docs-site/README.md` already records, `561eeedf386bc7cb164c577c423dc4484056a759` (2026-09-26). Git blob
  `7bc47ba8b85f88ae009d6b322c730440c745a9da`, 1032 bytes, sha256
  `734c233ba2d1e601771caf05b55a99d3db35576fe0305e8e341e5e18daeb3520` (fetched and hashed 2026-10-08 with `gh api
  repos/bmad-code-org/BMAD-METHOD/git/blobs/7bc47ba8b85f88ae009d6b322c730440c745a9da --jq .content | base64 -d`).
  Fetch it the same way, or from
  `https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/561eeedf386bc7cb164c577c423dc4484056a759/docs-site/src/lib/site-url.mjs`,
  and confirm `git hash-object` and `sha256sum` match before staging. If neither source answers, stop and report: do
  not write a local stand-in. The provenance is known, so a hand-written `getSiteUrl` would be a fork.
- **Its provenance record.** In `docs-site/README.md`, the helper gets a row in the vendored sha256 table (`|
  \`src/lib/site-url.mjs\` | \`734c233b…\` |`, the full digest), so the existing
  `test_vendored_files_match_readme_sha256` pins it. Its bullet leaves "Local-only files", which lists files that are
  "**not** byte-identical to upstream". Upstream's `docs-site/test/test-site-url.mjs` is not vendored: this repo runs
  no Node test lane, and the clean-clone build exercises the helper.
- **The ignore.** One negation, `!docs-site/src/lib/`, goes in the Story 27.1 docs-site block of `.gitignore` (after
  `docs-site/.astro/`), with a comment naming the `lib/` rule it overrides and why. The general `lib/` rule at `:40`
  stays, and no wider negation (`!lib/`, `!**/lib/`, `!src/lib/`) is written. A negation after `lib/` re-includes the
  directory, because none of its parents is excluded. This was measured in a scratch repository with this
  `.gitignore` plus the line: `docs-site/src/lib/site-url.mjs` is no longer ignored, and `src/x/lib/y.py` is still
  ignored by `.gitignore:40:lib/`.
- **The test.** `src/shared/packages/pyforge-herald/tests/meta/test_docs_site_imports_tracked.py` (new). Its helper,
  local to the test module, takes a repo root and returns findings:
  - **Modules scanned:** every tracked `*.mjs`, `*.js`, `*.ts` and `*.mts` file under `docs-site/` (from `git
    ls-files -z -- docs-site`), outside `node_modules/`, `build/` and `.astro/`. This includes `astro.config.mjs` and
    `src/content.config.ts`, which Astro loads itself.
  - **Specifiers:** the string-literal specifier of each static `import … from`, side-effect `import '…'`, `export …
    from`, dynamic `import('…')` and `require('…')` that starts with `./` or `../`, read after `//` and `/* */`
    comments are stripped. Bare, `node:` and `astro:` specifiers resolve through npm or Astro and are out of scope.
  - **Resolution, relative to the importing file:** the path as written if it exists. Otherwise, for an extensionless
    specifier, the first existing path with one of Vite's default `resolve.extensions`, in its order (`.mjs`, `.js`,
    `.mts`, `.ts`, `.jsx`, `.tsx`, `.json`), then `index` plus the same extensions under it. A specifier that
    resolves to no file is a finding (`unresolved`), and so is one that resolves to a path missing from `git
    ls-files` (`untracked`). Each finding names the importing file, the specifier and the resolved path.
  - **Git:** the helper runs `git ls-files` with an argv list and no shell. When git is missing, or the root is not a
    work tree, the test fails with that reason and never skips, because a skip would be a false green on the one
    check that exists for this.

  The test asserts, on the live tree:
  - no finding;
  - at least two relative imports were checked, so the guard is alive: `./src/lib/site-url.mjs` from
    `astro.config.mjs`, and `./loaders/shelf-docs-loader` from `src/content.config.ts`, which resolves to `.ts`;
  - `.gitignore` still has the exact line `lib/`, and its only negation under `docs-site/` is `!docs-site/src/lib/`;
  - `git check-ignore -q docs-site/src/lib/site-url.mjs` exits 1, and `git check-ignore --no-index -q` exits 0 for
    both `lib/probe.py` and `docs-site/lib/probe.mjs`, so the general rule still holds, even beside the exception.
    (Not a path under `src/**/packages/`: `.gitignore:490` re-includes those, so a probe there proves nothing.)

  On a synthetic `git init` tree under `tmp_path`, it asserts each case:
  - an imported file that exists but was never added is an `untracked` finding naming its path;
  - an imported file that does not exist is an `unresolved` finding naming the specifier;
  - after `git add` of the first file, it is no longer a finding;
  - a commented-out import of a missing file is not a finding;
  - a bare `astro/config` import is not checked;
  - an extensionless specifier resolves to its tracked `.ts` file, with no finding.
- **The CI trigger.** In `.github/workflows/pyforge-station-tests.yml`, herald's job also runs on `docs-site/**`:
  `'docs-site/**'` joins both the `pull_request` and the `push` `paths:` lists, after `'presentations/**'` (steward's
  `test_workflow_path_filters_match.py` requires the two lists to be identical), and herald's `job_paths` becomes
  `("$station_path" presentations docs-site)`. This follows Story 28.1, which added `presentations/**` for its own meta
  test. `.gitignore` is not added: a later ignore rule cannot untrack a tracked file, so a new untracked import always
  arrives with a `docs-site/` change.

Ledger key: `27-6-the-docs-site-builds-from-a-clean-checkout`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-52 (FR-8.1: the shelf builds in place; D6: vendored files are
  byte-identical to one recorded upstream commit). Story 27.1 shipped `docs-site/` under it, in Epic 27. A config that
  imports an untracked file is a defect of that shipped behaviour, so this story mints no CAP and registers no FR.
- **Architecture.** AD-21 rule 5 (re-vendor, never fork: the helper is byte-identical, and local behaviour lives in
  separate local files) and rule 4 (`docs-site/build/`, `node_modules/` and `.astro/` stay ignored). The spine's
  § Currency reconciliation — 2026-10-07 ("One divergence, recorded and not repaired") names this repair as a fix
  story with AD-21 standing; no AD is amended.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** The herald chain-currency cascade and retro of 2026-10-07; the station Dream's 2026-10-08 (docs-site
  helper) entry.

## Acceptance Criteria

- Given the fixed tree When `git ls-files docs-site/src/lib/site-url.mjs` runs Then it prints the path, and the
  file's `git hash-object` is `7bc47ba8b85f88ae009d6b322c730440c745a9da` and its sha256 is
  `734c233ba2d1e601771caf05b55a99d3db35576fe0305e8e341e5e18daeb3520`.
- Given a fresh `git clone` of the story's branch, with `SITE_URL` and `GITHUB_REPOSITORY` unset, When `pixi run
  --frozen -e site docs-site-build` runs Then it exits 0, and `docs-site/build/site/` holds `index.html`, `404.html`
  and the quadrant indexes (`tutorials/`, `how-to/`, `reference/`, `explanation/`), 64 HTML pages on 2026-10-08.
- Given `.gitignore` When it is read Then the line `lib/` is unchanged at its place, the one added line under the Story
  27.1 block is `!docs-site/src/lib/` with its comment, `git check-ignore -q docs-site/src/lib/site-url.mjs` exits 1,
  and `git check-ignore --no-index -q` exits 0 for `lib/probe.py` and `docs-site/lib/probe.mjs`.
- Given `docs-site/README.md` When it is read Then the vendored sha256 table carries `src/lib/site-url.mjs` with its
  digest, "Local-only files" no longer lists it, and `test_vendored_files_match_readme_sha256` passes.
- Given the new meta test When the station suite runs on the fixed tree Then it passes and reports at least two
  relative imports checked. Given `git rm --cached docs-site/src/lib/site-url.mjs` with the file kept on disk (the
  mutation) Then it fails naming `docs-site/src/lib/site-url.mjs` as `untracked`; `git add` restores it. Given the
  synthetic trees Then each case in the Approach behaves as stated.
- Given `.github/workflows/pyforge-station-tests.yml` When it is read Then both `paths:` lists carry `'docs-site/**'`,
  herald's `job_paths` carries `docs-site`, and steward's `test_workflow_path_filters_match.py` passes.
- Given the story lands When `pixi run --frozen -e pyforge-herald pyforge-herald-test` runs Then it passes.

## Boundaries & Constraints

**Always:**
- Vendor the helper byte-identical from the recorded commit, and check its blob id and sha256 before staging.
- Keep the general `lib/` rule. The exception is the single `docs-site/src/lib/` directory.
- Stage the helper with `git add`, and confirm `git ls-files` lists it before the station suite runs. The new test
  reads the index, so an unstaged helper fails it. That is correct, and the test is not what should change.
- Reconcile every Spec `spec-surface-check` names, then stamp each scoped (AGENTS.md pre-PR item 5): expect
  `spec-pyforge-herald` for `docs-site/**` and the new test, and `spec-pyforge-pages` (absorbed into herald, still
  carrying `.gitignore` in its surface) for `.gitignore`. Add any co-governor the detector names, and never run a bare
  `--write-baseline`.
- The PR carries the `maintenance` label. A change to `pyforge-station-tests.yml` is shared surface, so every station
  suite runs in CI. Run `pixi run -e pyforge-guild pyforge-station-tests` before pushing.

**Never:**
- Never write a local `getSiteUrl` while the upstream file can be fetched, and never edit the vendored file. Its
  `GITHUB_REPOSITORY` fallback stays as upstream wrote it. Story 27.2 sets `SITE_URL` for the deploy.
- Never drop or narrow `lib/`, never add a wider negation, and never untrack-and-ignore anything else under `docs-site/`.
- Never edit `docs-site/astro.config.mjs`, `src/content.config.ts`, the loader, `package.json` or `package-lock.json`.
  The config is right; only its dependency was missing.
- Never touch `pixi.toml`, `pixi.lock`, `environment.yaml`, `docsite-check.yml`, `dashboard.yml` or any page under
  `docs/`.
- Never weaken or delete an existing `test_docs_site.py` test.
- Never edit the PRD or the spine. Their 2026-10-07 divergence paragraphs are dated records, and a later
  chain-currency cascade records the repair.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| clean clone, fixed | `git clone` + `pixi run --frozen -e site docs-site-build` | exit 0, 64 pages | a failed `npm ci` or build exits non-zero |
| clean clone, today | the same on `054bb4e795` | exit 1, "Unable to load your Astro config" | — |
| helper untracked | file on disk, not in the index | meta test fails: `untracked`, names the path | fail loud, never skip |
| helper missing | import, no file | meta test fails: `unresolved`, names the specifier | — |
| extensionless import | `./loaders/shelf-docs-loader` | resolves to `shelf-docs-loader.ts`, tracked, no finding | — |
| bare specifier | `astro/config`, `@astrojs/starlight`, `node:fs`, `astro:content` | not checked | out of scope |
| commented-out import | `// import x from './gone.mjs'` | not checked | — |
| git unavailable | no `git` on PATH, or not a work tree | test fails, naming the reason | never a skip |
| general rule | `src/x/lib/y.py` | still ignored by `.gitignore:40:lib/` | — |
| vendored hash drift | the helper edited | `test_vendored_files_match_readme_sha256` fails naming it | — |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-08 (docs-site helper) entry.
- Epic: Epic 27 (Story 27.1 shipped `docs-site/` under `spec-pyforge-herald` CAP-52). The fix joins the epic that
  shipped the behaviour, which is still `in-progress`.
- Ledger key: `27-6-the-docs-site-builds-from-a-clean-checkout`.
- Ledger status at mint: `backlog`.
- Deps: none. Stories 27.2 and 27.3 build the site (`pages-build`, `docs-site-build`), so dispatch this story before
  them. Their `Deps:` lines are unchanged here.
- Spec: `spec-pyforge-herald/.memlog.md` records the mint. No contract change; `SPEC.md` is untouched.
- Dispatch note: Epic 27's `[epic_surfaces]` entry in `planning-artifacts/marshal-policy.toml` gains
  `.github/workflows/pyforge-station-tests.yml` in the minting commit. `.gitignore`, `docs-site/**`, the herald tests,
  `scripts/.spec-surface-baseline.json` and every Spec memlog were already admitted.
- Minted 2026-10-08 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- Clean-clone build: `git clone <worktree> <scratch>`, then in `<scratch>` run `env -u SITE_URL -u GITHUB_REPOSITORY
  pixi run --frozen -e site docs-site-build` — expected: exit 0, and `find docs-site/build/site -name '*.html' | wc
  -l` prints 64. Read the build's exit code directly, never through a pipe.
- `git hash-object docs-site/src/lib/site-url.mjs` — expected: `7bc47ba8b85f88ae009d6b322c730440c745a9da`.
- `git check-ignore -v docs-site/src/lib/site-url.mjs` — expected: exit 1, no output.
- Mutation: `git rm --cached docs-site/src/lib/site-url.mjs`, then `pixi run --frozen -e pyforge-herald pytest
  src/shared/packages/pyforge-herald/tests/meta/test_docs_site_imports_tracked.py` — expected: fail naming the path.
  Then `git add docs-site/src/lib/site-url.mjs`.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py`
  — expected: pass.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped stamps.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
