---
title: '93.2: The lint gate covers the repository''s own scripts in _bmad/scripts/'
type: 'feature'
created: '2026-11-27'
status: 'done'
story: 93-2-the-lint-gate-covers-the-repository-s-own-scripts-in-bmad-scripts
spec: spec-pyforge-steward
flag-exempt: detector-or-gate
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/lint_types.py'
  - '_bmad/scripts/bmad_tea_playwright.py'
  - '.github/workflows/lint-types.yml'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_lint_types_bmad_scripts.py'
  - 'pixi.toml'
  - 'AGENTS.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad/_config/files-manifest.csv
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `lint-types` checks the ten `pyforge-*` packages and the nine `django-*` packages, but nothing checks the
six scripts in `_bmad/scripts/`.

- Five of them belong to the BMAD installer. `_bmad/_config/files-manifest.csv` lists them with their hashes, and an
  upgrade rewrites them.
- The sixth is the repository's own: the TEA generator, `bmad_tea_playwright.py`. Its tests are in
  `pyforge-marshal`.

Under the rules every `pyforge-*` package shares (target py314; rules E, F, W and I; E501 ignored), the generator
passes `ruff check` and fails `ruff format --check`, on line wrapping only.

**Approach:** `lint_types.bmad_scripts()` lists every `_bmad/scripts/*.py` that the manifest does not list. The `ruff`
and `ruff-format` verbs check those files last, using `pyforge-marshal`'s `[tool.ruff]`, run from the repository root,
and report them as `_bmad/scripts`.

- If the manifest cannot be read, the verbs report could-not-run (exit 2). They never skip silently.
- `ruff-format --fix` rewrites the repository's own scripts. It never touches the installer's.
- The generator is formatted, and still writes the same eight documents.
- The Lint and types workflow fires on `_bmad/scripts/**` and on the manifest.
- The lines that describe the gate's scope are updated: the `ruff` and `ruff-format` task descriptions in `pixi.toml`,
  and `AGENTS.md`'s *Lint and types* line.

Ledger key: `93-2-the-lint-gate-covers-the-repository-s-own-scripts-in-bmad-scripts`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Leave the installer's scripts exactly as the installer wrote them.
- Keep every rule as strict as before.

**Never:**
- Never edit or lint a script the manifest lists.

## Acceptance Criteria

**Given** the tree on this story
**When** `lint-types` runs its ruff verbs
**Then** both report `_bmad/scripts ok`, and the generator writes the same documents as before.

- **AC1 — The gate covers the scripts.** Expected: both commands exit 0, and each prints a `_bmad/scripts ok` line.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/lint_types.py ruff
  pixi run --frozen -e pyforge-guild python scripts/lint_types.py ruff-format
  ```

- **AC2 — The set, the exclusion, the shared rules and the triggers.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_lint_types_bmad_scripts.py -q
  ```

- **AC3 — The formatted generator writes the same documents.** Running `origin/main`'s generator after this one leaves
  the eight documents unchanged.

</intent-contract>

## Result (2026-11-27)

- **AC1:** both verbs print `_bmad/scripts ok`. Before the format, `ruff-format` printed `exit 1`.
- **AC2:** 5 passed.
- **AC3:** `origin/main`'s generator, run after this one, wrote byte-identical documents.
- **Pre-existing staleness, fixed here:** regenerating every matrix also moved two stale fingerprints, in
  `pyforge-mason`'s and `pyforge-warden`'s `test-architecture.md`. Both generators write those fingerprints the same
  way.
