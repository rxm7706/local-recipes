---
title: "33.2: The package's metadata and docs agree with the estate"
type: 'fix'
created: '2026-11-10'
status: 'backlog'
difficulty: 'medium'
story: 33-2-the-package-s-metadata-and-docs-agree-with-the-estate
spec: spec-pyforge-scribe
surface:
  - src/shared/packages/pyforge-scribe/pixi.toml
  - src/shared/packages/pyforge-scribe/pyproject.toml
  - src/shared/packages/pyforge-scribe/README.md
  - src/shared/packages/pyforge-scribe/docs/cli-runbooks.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_package_metadata_matches_estate.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_recall.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_capture.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_compile.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-33-2-the-package-s-metadata-and-docs-agree-with-the-estate.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - pixi.toml
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-05.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Scribe's own package disagrees with the estate (audit SHOULD S4, decision D6, and the broken windows N2,
N3 (code half), N4, N5): the postgres extra asks for a psycopg the estate forbids (`psycopg>=3.3`, past the
`<3.2.11` cap the PostgreSQL 17 rule holds); the conda manifest says `python >=3.12`; two docstrings
(`models.py`, `compile.py`) state the staleness rule against the node's own `valid_from` where the code compares
against the compile clock; four comments in `recall.py` cite archive-era capability ids; the README carries a hand
count of stories; the runbook routes guild tasks to `-e local-recipes`.

**Approach:** Metadata and prose fixes with one guard test; under `src/` only comments and docstrings change.

- `pyproject.toml` extras take the estate's pins, read from the root `pixi.toml` `[feature.pyforge-scribe.dependencies]`
  at build time (at plan time `psycopg>=3.2.10,<3.2.11`, `graphifyy>=0.9.89`, `cocoindex>=1.0.25`).
- The package `pixi.toml` python floor moves to `>=3.14` in both tables (decision D6), and its "staged-recipes"
  comment names the local-recipes workspace.
- `README.md` (the SKF compile source of the scribe skill) points its status line at the ledger instead of a count;
  the recompile is steward:S-29.5.
- The staleness docstrings say `compiled_at` and name the recall-time withhold (finding SCR-R-F3's code half, accepted
  2026-11-05).
- `recall.py`'s four comments take station ids (`token-economy:CAP-13` stays qualified as marshal's; CAP-4 → CAP-14;
  CAP-11 → CAP-25; CAP-1 → CAP-16).
- The runbook routes guild tasks through `-e pyforge-guild`.
- `tests/meta/test_package_metadata_matches_estate.py` (with `pytestmark = pytest.mark.live_tree`) holds each
  optional-dependency floor equal to the estate's pin, cap included, and fires on a planted drift. The python-floor
  half belongs in `scripts/target_version_check.py` (steward-station's; a shared request), since eight package
  manifests carry the same defect.

The `src/` edits put `models.py`, `compile.py` and `recall.py` under the touched-module 80 percent floor; if one falls
under it, the story adds the missing unit tests (`test_capture.py`, `test_recall.py`, `test_compile.py`) rather than
dropping the fix.

Ledger key: `33-2-the-package-s-metadata-and-docs-agree-with-the-estate`. Type / Effort / Deps: fix / M / 33.1.

### Living CAP citations

- `spec-pyforge-scribe` CAP-28, as amended at the 2026-11-10 mint: the extras match the estate, held by
  `test_package_metadata_matches_estate.py`.
- `spec-pyforge-scribe` CAP-11 and CAP-26: the staleness clock the docstrings now state.

## Boundaries & Constraints

**Always:**
- Every pixi command is `--frozen`: the manifest edit changes the run-dependency string of a conda path dependency of
  two environments, so a non-frozen command would re-solve and rewrite `pixi.lock`, which is steward-station's
  (steward:S-124.3 regenerates it once for every package manifest).

**Never:**
- Do not change runtime behaviour; under `src/` only comments and docstrings move.
- Do not raise a PostgreSQL, libpq or psycopg cap to clear a solve (`fnd:CAP-12`).

</intent-contract>

## Acceptance Criteria

- **AC1 — Python floor is 3.14 in the conda manifest.** `git grep -n '>=3.12' -- src/shared/packages/pyforge-scribe/pixi.toml` exits 1 (no match).
- **AC2 — The postgres extra no longer asks past the estate cap.** `git grep -nE 'psycopg>=3\.3' -- src/shared/packages/pyforge-scribe/pyproject.toml` exits 1 (no match).
- **AC3 — The extras guard passes and fires on a planted drift** (an extra's floor below the estate pin; a missing cap):
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_package_metadata_matches_estate.py -q` exits 0.
- **AC4 — The runbook routes guild tasks through the session environment.** `git grep -n -e '-e local-recipes' -- src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` exits 1 (no match).
- **AC5 — The README carries no hand count of stories.** `git grep -n 'all 9 stories' -- src/shared/packages/pyforge-scribe/README.md` exits 1 (no match).
- **AC6 — The staleness docstrings name the compile clock.** `git grep -n "own .valid_from." -- src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` exits 1 (no match).
- **AC7 — recall.py cites station capability ids.** `git grep -nE 'Story (6\.3, CAP-13|8\.5 / CAP-4|16\.1 / CAP-11|9\.1 / CAP-1)\b' -- src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` exits 1 (no match).
- **AC8 — The docs that teach capture and recall still route correctly.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py -q` exits 0.
- **AC9 — Touched modules hold the coverage floor.** `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up && pixi run --frozen -e pyforge-scribe pyforge-scribe-coverage-gate` exits 0.
- **AC10 — Lint and types.** `pixi run --frozen -e pyforge-guild lint-types` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-28 (amended 2026-11-10); CAP-11 and CAP-26 (docstrings only).
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 33. Ledger key `33-2-the-package-s-metadata-and-docs-agree-with-the-estate`, minted `backlog`.
- Deps: 33.1 (it shares `pyproject.toml` and `test_compile.py`). Wave BUILD-2.

## Notes

- Closes audit SHOULD S4 and NICE N2, N3, N4, N5.
- Shared requests: steward-station regenerates `pixi.lock` once after this edit and before Story 31.4's gates
  (steward:S-124.3) and carries the python-floor guard in `scripts/target_version_check.py`; the co-governor
  reconciles for `spec-pyforge-core` (src) and `spec-pyforge-unifying-strategy` (the package) are written by their
  own closers.

## Spec Change Log

- 2026-11-10: minted with Epic 33 at the cutover-readiness mint.
- 2026-11-11: built (wave BUILD-2).
  - The estate pins read from the root `pixi.toml` at build time match the plan's: `psycopg>=3.2.10,<3.2.11`,
    `graphifyy>=0.9.89`, `cocoindex>=1.0.25`.
  - Run against the pre-fix `pyproject.toml` (HEAD), `test_package_metadata_matches_estate.py` names all three
    extras. Its planted cases are a floor below the pin, a missing cap, a floor past the cap, a package the estate
    does not pin, and a drifted manifest pair on disk. It carries `live_tree`, resolves the root inside a function,
    and passes `test_live_tree_split.py`.
  - The README status paragraph keeps its four lines, so the compiled skill's `[SRC:README.md:L19-L33]` anchors
    stay put until steward:S-29.5 recompiles.
  - The runbook had three `-e local-recipes` sites. One was wrapped across a line break, which AC4's line grep
    cannot see. All three now read `-e pyforge-guild`, which carries `guild-tasks`.
  - In the two staleness paragraphs this story rewrites (`models.py`, `compile.py`) and in `compile.py`'s staleness
    section comment, Story 6.3's id is qualified `token-economy:CAP-13`, and the clock cites CAP-11 and CAP-26.
  - Coverage: the gate diffs `origin/main...HEAD`, so before the wave commit it judges no scribe module. Run with
    `--paths-file` naming the three modules against the same report, it passes: `compile.py` 90.35, `models.py` 98.1,
    `recall.py` 95.56. No unit test was added.
