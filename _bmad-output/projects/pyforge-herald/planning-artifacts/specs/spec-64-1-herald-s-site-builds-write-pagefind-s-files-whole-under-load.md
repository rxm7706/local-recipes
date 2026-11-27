---
title: '64.1: Herald''s site builds write Pagefind''s files whole under load'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 64-1-herald-s-site-builds-write-pagefind-s-files-whole-under-load
spec: spec-pyforge-herald
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'docs-site/package-lock.json'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test_43_5_two_builds_two_days_runs_and_commits_apart_differ_only_in_the_built_from_line` builds the site twice and holds the two builds byte-identical apart from the built-from line. It failed twice on 2026-11-27, each time on one Pagefind file:

- On PR #2431's CI, `pagefind/pagefind-entry.json` differed.
- In a full local preflight, `pages_astro.differences_report` showed `pagefind/wasm.unknown.pagefind` at 68,024 bytes in the first build and 0 bytes in the second.

Starlight's Pagefind step (`@astrojs/starlight/dist/integrations/pagefind.js`) calls Pagefind's Node API: `createIndex`, `addDirectory`, `writeFiles`, then `close()`, which kills the `pagefind --service` child. To test that sequence, a probe called it on a 300-page site, 32 at a time, with every core busy. On Pagefind 1.5.2 it left `pagefind-entry.json` empty in 4 of 192 runs and `wasm.unknown.pagefind` empty in 2. The files were still empty 1.5 s later, so the service answered before its writes were on disk, and the kill cut them short. Pagefind 1.6.0 (2026-11-01) lists "Fixed a way that output files could be truncated in service-mode (PR #1272)".

**Approach:** `docs-site/package-lock.json` moves Pagefind's nine packages from 1.5.2 to 1.6.0, inside the ranges Starlight declares (`pagefind ^1.5.2`, `@pagefind/default-ui ^1.3.0`), with `npm update pagefind @pagefind/default-ui`. The nine are `pagefind`, `@pagefind/default-ui` and the seven platform binaries. Nothing else in the lock moves.

Ledger key: `64-1-herald-s-site-builds-write-pagefind-s-files-whole-under-load`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The site builds and passes its checks as before.

**Never:**
- Never change, skip or retry a test to make it pass.

## Acceptance Criteria

**Given** the site installed from the lock
**When** herald's suite runs with the built-site tests required
**Then** both halves pass, and Pagefind's files are whole under load

- **AC1 — Herald's live half passes with the built-site tests required.** Expected: exit 0.

  ```bash
  HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

- **AC2 — Only Pagefind's packages move in the lock.** Expected: nine `"version"` lines change, each from 1.5.2 to 1.6.0, and no other package's version.

  ```bash
  git diff origin/main -- docs-site/package-lock.json | grep '^[+-] *"version"'
  ```

</intent-contract>

## Result (2026-11-27)

- With 1.6.0, the same probe wrote every file whole in 768 runs: 384 from a scratch install and 384 from the site's own.
- The two-builds test passed 16 times out of 16, run 8 at a time with every core busy.
- AC1: 839 passed. The package half: 1,560 passed and 5 skipped.
