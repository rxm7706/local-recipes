---
title: '123.2: One steward module names this root''s layout and repository, and prove-landed reads doctor through its command'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate
difficulty: medium
story: 123.2
spec: pyforge-steward
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/measures.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py
  - src/shared/packages/pyforge-steward/tests/meta/test_portability.py
  - src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Real defects the audit found: hard-coded roots and an in-process import of another station, where the grammar is the only contract between stations.

**Approach:** A refactor with a gate. Steward's four identity sites (`steward ci`'s default repository, `bootstrap --url`'s default, the marketplace URL, the owner) are this checkout's identity, not the root of record: one constant each in `root_layout.py`, listed in contract.md as estate-bound, and none follows a flip (operator ruling 2026-11-10 on question 5). No module starts reading `pyforge.cutover_root`.

Ledger key: `123-2-one-steward-module-names-this-root-s-layout-and-repository-and-prove-landed-reads-doctor-through-its-command`. Type / Effort / Deps: feature / M / S-121.2, S-123.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-182** — one module names this root's layout and repository, and a test holds the rest of steward's source to it; minted 2026-11-10 `(ready 2026-11-10)` and rendered at mint. Works with `spec-pyforge-core:CAP-13` (`root_of_record()`, `LOCAL_DEV_RELATIVE`).

## Boundaries & Constraints

**Always:**
- Keep every value identical on A.
- Keep `root_layout.py` to assignments: no function and no import of a steward module.

**Never:**
- Never edit `src/platform/ingest/github_projects/pipeline.py` (the src/platform import guard; DW-steward-74-1 holds the private import).
- Never edit session.py or test_session.py (Story 123.3's).
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the portability test passes.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q
  ```
- **AC2 — the test can fire.** Expected: exit 0 with at least 4 tests selected (a planted path constant, a planted slug, a planted cross-station import, an exception entry that no longer applies).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q -k fires
  ```
- **AC3 — no path constant outside the one module.** Expected: exit 1 (no match); docstrings and comments use backticks and are not matched, which is what CAP-182 says.
  ```bash
  git grep -nE "[\"']src/shared/packages" -- src/shared/packages/pyforge-steward/src/pyforge/steward ':(exclude)src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py'
  ```
- **AC4 — no slug outside the one module.** Expected: exit 1 (no match).
  ```bash
  git grep -n 'rxm7706' -- src/shared/packages/pyforge-steward/src/pyforge/steward ':(exclude)src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py'
  ```
- **AC5 — no cross-station import remains (session.py's left with Story 123.3, operator ruling 2026-11-10).** Expected: exit 1 (no match).
  ```bash
  git grep -nE 'from pyforge\.(doctor|marshal|herald|scribe|mason|atlas|warden)|import pyforge\.(doctor|marshal|herald|scribe|mason|atlas|warden)' -- src/shared/packages/pyforge-steward/src/pyforge/steward
  ```
- **AC6 — the values are unchanged.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src python -c "from pyforge.steward import catalog,corridor,measures,ci,workspace,root_layout as r;from pyforge.core.cutover_root import LOCAL_DEV_RELATIVE as L;assert str(catalog.CATALOG_RELATIVE)=='src/shared/packages/pyforge-steward/catalog';assert str(corridor.CORRIDOR_RELATIVE).endswith('pyforge-steward/corridor');assert str(measures.MEASURES_RELATIVE).endswith('pyforge-steward/measures');assert ci.DEFAULT_REPO=='rxm7706/local-recipes';assert catalog.PUBLIC_MARKETPLACE_GIT_URL=='https://github.com/rxm7706/local-recipes.git';assert workspace.default_flags_path()==workspace.repo_root()/L"
  ```
- **AC7 — prove-landed keeps its verdict.** Expected: exit 0: `run_bmad_drift_integrity` takes exit 0 as pass, 1 as findings and 2 as could-not-run from `pixi run --frozen -e pyforge-guild bmad-drift-check` through the stubbed command runner; test_session.py is not edited by this story (Story 123.3 owns it).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py src/shared/packages/pyforge-steward/tests/unit/test_session.py -q
  ```
- **AC8 — no new subprocess call site and no builtin-rooted exception.** Expected: prints 0 (BASE is the `baseline_revision` in this story's spec frontmatter; core-kit Story 117.1 pins both counts).
  ```bash
  git diff "$BASE"..HEAD -- src/shared/packages/pyforge-steward/src/pyforge/steward | grep -cE '^\+.*(subprocess\.(run|Popen|check_)|class [A-Za-z]+\((Exception|ValueError|RuntimeError|OSError|TypeError|KeyError|LookupError)\))'
  ```
- **AC9 — src/platform is not touched.** Expected: prints 0.
  ```bash
  git diff --name-only "$BASE"..HEAD -- src/platform | wc -l
  ```
- **AC10 — coverage floor on touched modules.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-coverage-gate
  ```
- **AC11 — package half.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC12 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC13 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-182

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 123.
- Ledger key: `123-2-one-steward-module-names-this-root-s-layout-and-repository-and-prove-landed-reads-doctor-through-its-command` (`backlog` at mint).
- Deps: S-121.2, S-123.3.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py` (new), `src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py, measures.py, catalog.py, preflight_ci.py, upgrade.py, workspace.py, ci.py, bootstrap.py, marketplace_pages.py and sync.py`, `src/shared/packages/pyforge-steward/tests/meta/test_portability.py` (new), `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py`.
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q` — expected: exit 0.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q -k fires` — expected: exit 0 with at least 4 tests selected (a planted path constant, a planted slug, a planted cross-station import, an exception entry that no longer applies).

## Notes

- Cross-station: marshal:S-117.2 (core-kit) publishes `root_of_record()` and `LOCAL_DEV_RELATIVE` first; steward does not consume `root_of_record()` (its identity sites are this checkout's).
- Operator ruling 2026-11-10 (Story 123.3): `steward session check` finding (2) takes `bmad-drift-check`'s verdict everywhere, so session.py's `pyforge.doctor` import leaves with Story 123.3 and this story's exception list is empty; the plan's session.py exception is superseded. Hence the dependency on 123.3.
- control-plane 121.2 drops cutover.py's path literals with the apply code; if any remains, this story moves it.
- `$BASE` in the acceptance criteria is the `baseline_revision` the build writes into this spec's frontmatter when it starts (the commit it starts from); it is not set at mint.
- Until Story 124.2 lands, steward's trigger-map test may red on other units' new reads (a planned red window); this story is judged by its own test modules and by steward's package half without that module.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
