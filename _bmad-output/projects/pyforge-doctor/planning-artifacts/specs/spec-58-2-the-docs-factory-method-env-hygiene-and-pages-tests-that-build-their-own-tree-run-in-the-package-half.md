---
title: '58.2: The docs, factory, method, env-hygiene and Pages tests that build their own tree run in the package half'
type: 'chore'
created: '2026-11-10'
status: 'done'
story: 58-2-the-docs-factory-method-env-hygiene-and-pages-tests-that-build-their-own-tree-run-in-the-package-half
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # test modules and a test-only split, no runtime path (spec-55-4's form; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_currency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_map_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_shelf.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_factory.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_bmad_method.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_checks_env_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_pages_liveness.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ci_pause_drift.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_live_proof_surfaces.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_general_docs_consistency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_flag_kill_switch.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Same defect as Story 58.1 for the other 11 module-marked files. Test-only; no source changes.

**Approach:** Per module: move each test, and the helpers only it uses, that reaches the repository through `parents[N]`, a `REPO_ROOT` name or a root hand-off into `tests/unit/test_live_<same name>.py` with `pytestmark = pytest.mark.live_tree`; delete the mark from the original; rewrite a fixture literal that names a tracked path as a path join or a made-up name (steward's scan_strings reads a bare literal of a tracked path as a read). In a test_live_ module a `pytest.skip` on an absent repository path becomes an assert with the same message. A shared helper goes to a private module under tests/unit/ only when both files need it. Record the final list of test_live_ modules in this spec: steward-station makes one re-key edit after Stories 56.2, 57.3, 58.1 and 58.2. No pixi.toml change: the two tasks select by marker.

Ledger key: `58-2-the-docs-factory-method-env-hygiene-and-pages-tests-that-build-their-own-tree-run-in-the-package-half`.
Type / Effort / Deps: chore / L / S-56.4.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-97** — the package-local half builds every tree it reads and is the rebuild oracle.

## Boundaries & Constraints

**Always:**
- Keep every test: the two halves together hold exactly the 514 functions grep-counted at `f614d6a9b8`.

**Never:**
- Never change a source; never delete or skip a test to meet the split.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — None of the 11 modules carries the live_tree mark any more.** Expected: exit 1 (no match).

  ```bash
  git grep -l live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py
  ```

- **AC2 — Every new test_live_ module is marked at module level.** Expected: exit 0, prints nothing.

  ```bash
  for f in $(ls src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_live_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_flag_kill_switch.py 2>/dev/null); do grep -qE '^pytestmark\s*=.*live_tree' "$f" || { echo "$f"; exit 1; }; done
  ```

- **AC3 — No test was lost, and the fixture tests stay in the package half.** Expected: the two counts sum to 514 (grep-counted at f614d6a9b8, the plan's base; 56.4 adds no test function to these modules); the second is at most 50.

  ```bash
  cat src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py | grep -cE '^\s*(async\s+)?def test_'; cat $(ls src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_live_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_flag_kill_switch.py 2>/dev/null) /dev/null | grep -cE '^\s*(async\s+)?def test_'
  ```

- **AC4 — The package-half modules skip on no repository condition.** Expected: prints 2 (the two environment skips that stay with fixture tests: test_sources_factory.py `_needs_unprivileged` and test_checks_env_hygiene.py's non-UTF-8 filesystem skip; today these 11 modules hold 10).

  ```bash
  cat src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py | grep -cE 'pytest\.skip\(|pytest\.mark\.skipif|pytest\.importorskip'
  ```

- **AC5 — A repository-absence skip moved to a live module became a failure.** Expected: prints nothing (exit 1).

  ```bash
  cat $(ls src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_live_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_flag_kill_switch.py 2>/dev/null) /dev/null | grep -nE 'not running inside|not resolvable from this checkout|parents\[6\] out of range|is not present|not present in this checkout|no _bmad-output|not in this checkout|monorepo'
  ```

- **AC6 — Steward's rule for the package half holds.** Expected: exit 0 (doctor's package half derives no outside read and no hand-off); test_root_handoffs_are_declared_exactly and test_the_handoff_floor are expected red until steward-station's re-key (shared request).

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -p no:cacheprovider -k package_half_reads_nothing
  ```

- **AC7 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-58-2-*.md)"
  ```

- **AC8 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-97 (realizes its oracle clause for the modules it splits; no text change); FR-28 ← CAP-97.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 58, minted with this story.
- Ledger key: `58-2-the-docs-factory-method-env-hygiene-and-pages-tests-that-build-their-own-tree-run-in-the-package-half` (`backlog`).
- Deps: S-56.4.
- Surface: `marshal-policy.toml` `[epic_surfaces]."58"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Readers: test_sources_ci_pause_drift.py's two tests that validate against steward's ci-status-schema.json, test_sources_pages_liveness.py's test that reads .github/workflows/pages.yml, test_flag_kill_switch.py's two tests that read django-pyforge's shipped config; test_sources_live_proof_surfaces.py's nine tracked-path literals are fixture data (rename them, or keep those cases live).
- test_sources_ci_pause_drift.py's `pytest.importorskip("jsonschema")` becomes a plain import: jsonschema is a hard dependency (pyproject.toml `dependencies`). The two environment skips that stay: test_sources_factory.py `_needs_unprivileged` and test_checks_env_hygiene.py's non-UTF-8 filesystem skip.
- The test_live_ files in the surface are created only where the module keeps a repository reader.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Final test_live_ modules (written at build)

Nine of the 11 modules keep a repository reader and gain a live twin under `src/shared/packages/pyforge-doctor/tests/unit/`; the twins hold 14 test functions and the package half keeps 500 (514 in all). Each twin carries `pytestmark = pytest.mark.live_tree` and derives the repository root inside a function or fixture, never at import.

| Live module | Tests moved | What it reads |
|---|---|---|
| `test_live_sources_docs_shelf.py` | `test_live_repo_gather_is_clean` | the repository root, handed to `docs_shelf.gather` |
| `test_live_sources_factory.py` | `test_env_count_reads_the_live_manifest_like_tomllib` | `pixi.toml`; the root, handed to `factory._env_count` |
| `test_live_sources_bmad_method.py` | `test_the_real_recipe_resolves_through_the_github_fallback` (6 cases) | `recipes/*/recipe.yaml`; the root, handed to the resolver |
| `test_live_checks_env_hygiene.py` | the CFE-scripts golden fixture, the whole-checkout discovery walk, `dependency-checker.py`'s guarded returns (3) | `.claude/skills/conda-forge-expert/scripts/`; the root, handed to the walk |
| `test_live_sources_pages_liveness.py` | the `pages.yml` filter pin and its named-exclusions mutation twin (2) | `.github/workflows/pages.yml` and the five excluded paths |
| `test_live_sources_ci_pause_drift.py` | `test_fixture_matches_ci_status_schema`, `test_partial_read_on_stdout` (2) | steward's `ci-status-schema.json` |
| `test_live_sources_live_proof_surfaces.py` | `test_zero_false_positives_against_the_live_tracked_tree` | `git ls-files` of the root and the tracked catalog |
| `test_live_sources_general_docs_consistency.py` | `test_live_repo_gather_no_longer_fires_after_story_22_1_landed` | the repository root, handed to `general_docs_consistency.gather` |
| `test_live_flag_kill_switch.py` | the CLI kill switch through `django_pyforge.flags`, the dated flag on the shipped tree (2) | `src/shared/packages/django-pyforge/src` on the import path; `src/platform/config` |

No twin for `test_sources_docs_currency.py` and `test_sources_docs_map_hygiene.py`: neither held a reader, only tracked-path fixture literals, now a made-up name (`scripts/docs_fixture_tasks.py`, `how-to/fixture-tasks.md`) and a path join (`docs/MAP.md`). `test_sources_pages_liveness.py` and `test_sources_live_proof_surfaces.py` spell their remaining real tracked paths as path joins.

Steward-station's one re-key (shared request): in `test_station_tests_trigger_map.py`'s `doctor_live` handoff declarations, the keys `test_checks_env_hygiene.py`, `test_sources_bmad_method.py`, `test_sources_docs_shelf.py`, `test_sources_factory.py`, `test_sources_general_docs_consistency.py` and `test_sources_live_proof_surfaces.py` become their `test_live_` twins, each with the same `_H` group.

Build decisions:
- The six repository-absence skips that moved became asserts. Their messages are reworded, not copied, because AC5 rejects the old phrases ("monorepo", "not present in this checkout", "not in this checkout").
- `pytest.importorskip("jsonschema")` is gone. The schema readers moved to the live twin, which imports jsonschema directly; the package module no longer uses it.
- No private helper module: the plan's files_owned names none. Each twin carries its own copy of what it needs: the per-module `_isolate_git_env` fixture (the existing convention, copied in many modules here), the one-flag `_sample_tree`, and the three false-positive paths. The pages exclusion set has a single definition, because its mutation twin moved with the pin.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
