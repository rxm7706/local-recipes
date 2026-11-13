---
title: "52.2: Herald's landing record names this checkout's forge, and its package names Python 3.14"
type: 'fix'
created: '2026-11-10'
status: 'done'
difficulty: easy
story: '52.2'
spec: pyforge-herald
surface:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/local_ship.py
  - src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py
  - src/shared/packages/pyforge-herald/pixi.toml
  - src/shared/packages/pyforge-herald/README.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/guild-roster.json
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/local_ship.py
  - src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `local_ship.py:31` hard-codes `rxm7706/local-recipes` as the forge slug of every landing record
`herald-ship-local` posts, so a second root's landings would name A's forge. The package `pixi.toml` states
`python >=3.12` twice against a 3.14 `pyproject.toml`. The README counts "47 stories" by hand (audit SHOULD:
portability, Python floor; NICE: README).

**Approach:** A fix under spec-pyforge-herald CAP-38 (the landing record `herald-ship-local` posts). It consumes
core's forge slug table, which marshal:S-117.2 adds as a constant in `pyforge.core.cutover_root`. There is no herald
CAP and no FR.

- **The slug.** `_DEFAULT_REPO` goes. `build_on_pr_close_body(landing, *, repo=None)` resolves the slug at call time
  from this checkout's identity: `roots.this` in `docs/governance/guild-roster.json` (added by steward:S-121.4),
  through `pyforge.core.cutover_root.forge_slug_for()`. It never resolves at import, and never through
  `root_of_record()`. Herald's landing record is not one of the three consumers ruling 2 names, so it does not follow
  the root of record (second addendum, ruling 5). Herald reads no flag key.
- **Refusal.** An explicit `repo=` wins and reads no roster. A roster with no `roots.this`, or no roster above the
  working directory, makes `build_on_pr_close_body(landing)` raise a named error, and `local_ship.main` prints it to
  stderr and returns 1 (the module's existing refusal code) before any POST. It never falls back to A's slug. The
  existing case at `test_local_ship.py:51`, which calls `build_on_pr_close_body(landing)` bare, gains `repo=` or a
  temporary roster.
- **The contract row.** `contract.md` gains one row naming the repository key herald reads
  (`docs/governance/guild-roster.json` `roots.this`, resolved through `pyforge.core.cutover_root.forge_slug_for`), in
  the same change as the import. Story 50.3's contract test agrees.
- **The floor.** The package `pixi.toml` floor becomes `python = ">=3.14"` in both places. This alters the path
  dependency's run-dependency string in `pixi.lock`; steward-station re-locks once for every station after this
  wave, and its fresh-clone check (steward:S-124.3) is the lock post-condition, not this story's.
- **README.** The status line states no story count and points at the ledger.
- **Reconcile.** The co-governor spec-pyforge-core takes its reconcile line for `local_ship.py` from its own closer
  (marshal:S-117.8). Herald's own line is Story 50.2's.

Ledger key: `52-2-herald-s-landing-record-names-this-checkout-s-forge-and-its-package-names-python-3-14`.
Type / Effort / Deps: fix / S / S-50.3 (and marshal:S-117.2, steward:S-121.4).

## Boundaries & Constraints

**Always:**
- Resolve the slug at call time from `roots.this` through `forge_slug_for`; an explicit `repo=` wins.
- Refuse by name before any POST when the roster or `roots.this` is missing.
- Keep `test_local_ship.py` a package-half module: every case passes `repo=` or writes its own roster under
  `tmp_path`, none walks up to the live roster, and it carries no `live_tree` marker.

**Never:**
- Never call `root_of_record()`, never read `src/platform/config/flags.json`, and never fall back to A's slug.
- Never add a flag or a kill switch (ruling 5).
- Never re-lock `pixi.lock` here.

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe. Every `pixi run` here is `--frozen`, so no AC can
re-solve or rewrite `pixi.lock` (AC10 proves it). `BASE` is this spec's `baseline_revision`.

- **AC1 — No forge slug is typed in herald's source.**
  `git grep -n 'rxm7706/local-recipes' -- src/shared/packages/pyforge-herald/src`. Expected: exit 1 (no match).
- **AC2 — The landing body names this checkout's forge, and a missing `roots.this` is a named refusal.**
  `pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py -q`. Expected:
  exit 0, with these new cases:
  - a temporary roster whose `roots.this` is `local-recipes` gives A's slug in the on-pr-close body's `event_id` and
    commit URL;
  - `foundry` gives core's foundry slug;
  - an explicit `repo=` argument wins and reads no roster;
  - a roster with no `roots.this`, or none above the working directory, makes `build_on_pr_close_body(landing)`
    raise a named error, and `local_ship.main` print it to stderr and return 1 before any POST;
  - no case reads `src/platform/config/flags.json`.
- **AC3 — `test_local_ship.py` is a package-half module.** It passes with no roster and no flag tree anywhere above
  it. Expected: exit 0.

```bash
T=$(mktemp -d) && git archive HEAD src/shared/packages/pyforge-herald src/shared/packages/pyforge-core src/shared/packages/pyforge-testing-kit | tar -x -C "$T" && PY=$(pixi run --frozen -q -e pyforge-herald python -c 'import sys;print(sys.executable)') && (cd "$T" && env -u PYFORGE_FLAGS_PATH PYTHONPATH=src/shared/packages/pyforge-herald/src:src/shared/packages/pyforge-core/src:src/shared/packages/pyforge-testing-kit/src "$PY" -m pytest src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py -q -p no:cacheprovider)
```

- **AC4 — The contract lists the repository key, and the contract test agrees.**
  `grep -c 'roots.this' _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md && pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py -q`.
  Expected: prints at least `1`, then exit 0.
- **AC5 — The package has one Python floor.**
  `grep -c 'python = ">=3.14"' src/shared/packages/pyforge-herald/pixi.toml; grep -c '3\.12' src/shared/packages/pyforge-herald/pixi.toml`.
  Expected: prints `2`, then `0`.
- **AC6 — The README counts nothing by hand.**
  `git grep -n '47 stories' -- src/shared/packages/pyforge-herald/README.md`. Expected: exit 1 (no match).
- **AC7 — Floors agree across the estate.** `pixi run --frozen -e pyforge-guild target-version-check`. Expected: exit 0.
- **AC8 — The suite and the touched-module coverage floor hold.**
  `pixi run --frozen -e pyforge-herald pyforge-herald-test && pixi run --frozen -e pyforge-herald pyforge-herald-coverage-gate`.
  Expected: exit 0.
- **AC9 — Herald is not a consumer of the root of record.**
  `git grep -n 'root_of_record' -- src/shared/packages/pyforge-herald/src`. Expected: exit 1 (no match).
- **AC10 — The story leaves `pixi.lock` alone.** `git diff --quiet "$BASE" -- pixi.lock`. Expected: exit 0. The
  package floor's new run-dependency string reaches the lock only through steward-station's one re-lock after this
  wave (steward:S-124.3 is its post-condition).

</intent-contract>

## Binding

- A fix under spec-pyforge-herald CAP-38. No herald CAP or FR is minted, and no AD moves.
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry. Rulings:
  `docs/dreams/pyforge-unifying-strategy.md`, second addendum, ruling 5 (only ruling 2's three consumers follow the
  root of record; the forge slug table is a constant in `pyforge.core.cutover_root`).
- Epic 52. Ledger key `52-2-herald-s-landing-record-names-this-checkout-s-forge-and-its-package-names-python-3-14`.
- Cross-station: marshal:S-117.2 (core's `forge_slug_for` and its slug table) and steward:S-121.4 (`roots.this` in the
  roster) are gates held by the single PR's integration order. Steward:S-124.3's fresh-clone check is the lock
  post-condition. Marshal:S-117.8 writes spec-pyforge-core's reconcile line.
- Findings closed: SHOULD: portability, would break on B; SHOULD: Python floor; ruling 2's three consumers (herald
  reads its checkout's identity, not the flag).

## Spec Change Log

- 2026-11-10: minted (backlog). The integration pass resolved the slug through `forge_slug_for(roots.this)`, never
  `root_of_record()`, and that wording supersedes the plan's earlier flag-tree wording.
- 2026-11-11: the mint's review found that the ACs ran `pixi run` without `--frozen`, which could re-solve and rewrite
  `pixi.lock` in this story's own diff after the package `pixi.toml` edit. Every `pixi run` is now `--frozen`, and
  AC10 proves `pixi.lock` unchanged against `BASE`.

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet. Story 50.2 writes it to
`planning-artifacts/deferred-work-ledger.md` and adds it to this spec's `deferred:` frontmatter in the same change,
because `deferred-work-check` refuses a frontmatter deferral with no tracked twin. Station deferred-work rows are
written at build, never at mint.

- **`DW-herald-52-2-1`** (low, open; location `src/shared/packages/pyforge-herald`): Herald names A's package layout or forge slug by literal outside this fix. `src/shared/packages` in docs-site/scripts/verify_claims.py:91 and scripts/deck_facts.py:302 and :616; `../../../../..` in web/package.json:8; PYTHONPATH in pixi.toml:3272; root pixi task shell-outs in deck_pipeline.py and sync_all.py; the forge slug in docs-site/scripts/pages.mts:50, docs-site/src/lib/shelf.mjs:54, docs-site/src/lib/marketplace.ts:24 and web/src/components/TabNav.jsx:4. None of them is a rebuild input: steward Stories 44.4 and 44.5 (the fold to src/packages/) retired on 2026-11-10, so A has one layout and B rebuilds from Spec. The two docs-site slugs are fallbacks behind GITHUB_REPOSITORY, marketplace.ts is steward's capability, and web/ is built by no workflow. Revisit only if A's own layout or forge moves.

## Gate findings (build, BUILD-4)

- 2026-11-11, found by Story 124.1's build (core's whole suite) after the BUILD-4 gate, which did not run
  pyforge-core's suite: `ForgeSlugError(ValueError)` in `src/pyforge/herald/local_ship.py` was an exception root
  without `PyforgeError`, so spec-pyforge-core:CAP-5's guard
  `test_exception_root_sole_ownership.py::test_no_unreparented_exception_root[pyforge-herald/src/pyforge/herald/local_ship.py]`
  went red. The integrator reparented it as `ForgeSlugError(PyforgeError, ValueError)`; it is still a
  `ValueError`, so every caller's `except ValueError` holds. Core's guard: 494 passed; herald's local_ship,
  bridge and public-contract tests: 209 passed. Later wave gates run core's and the kit's suites every wave.
