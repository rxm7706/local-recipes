---
title: '70.1: The flag scripts read each story spec once and each path without walking its parents'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 70-1-the-flag-scripts-read-each-story-spec-once-and-each-path-without-walking-its-parents
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/flag_rule.py'
  - 'scripts/flag_inventory.py'
  - 'tests/scripts/test_flag_rule.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Detectors job's library part is the longest job on a PR: 124 s, of which 24 s is the checkout, 31 s the pixi setup and 58 s `scripts-lib-test`. That suite's floor is two runs of `scripts/flag_inventory.py` over the live tree, 17.5 s each here. Profiled, a run spends most of its time in two readers of `scripts/flag_rule.py`:

- `read_frontmatter` YAML-parses each of the 1,983 story specs four times. The inventory and the flag gate's three readers (`judge_one`, `env_default_judge_targets`, `retirement_declarations`) each read every spec.
- `repo_relative` is asked of each of the 105,354 paths that the stories' `Surface:` lines name. It resolved both paths on every call, because the candidates were built as one tuple. It then tested the root against each of the path's parents, as `PurePath.relative_to` does. `_classify_surface`'s `is_relative_to` (47,079 calls) does the same.

**Approach:**
- `_frontmatter` keeps the YAML parse of a frontmatter block by the block's text (`_parse_frontmatter_block`, an `lru_cache`), and gives each caller its own deep copy. A changed file is read as it now is, since the key is the text, not the path.
- `repo_relative` resolves only when the lexical form is not under the root.
- `flag_rule.lexical_tail(path, base)` returns `path.relative_to(base).parts`, or None, comparing `base` once with the path made of `path`'s first `len(base.parts)` parts. `repo_relative` and `_classify_surface` use it.

Ledger key: `70-1-the-flag-scripts-read-each-story-spec-once-and-each-path-without-walking-its-parents`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized; no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every report, judgment, finding and frontmatter read stays exactly as before.

**Never:**
- Never let one caller's change to its mapping reach another caller.

## Acceptance Criteria

**Given** the live tree
**When** the inventory and the gate run
**Then** their outputs equal `origin/main`'s, in about half the time

- **AC1 — The flag tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_flag_rule.py tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_inventory.py -q
  ```

- **AC2 — The library tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild scripts-lib-test
  ```

</intent-contract>

## Result (2026-11-27)

**Equivalence with `origin/main`:**
- The inventory's eight reports, and the gate's text and `--json` output, are byte for byte the same.
- A dump of the gate's inputs, judgments and findings, every story spec's `read_frontmatter` result and `repo_relative` cases was taken with `PYTHONHASHSEED=0`, once with `origin/main`'s `flag_rule.py` in place and once with the new one. The two dumps are identical.
- `lexical_tail` agrees with `relative_to(...).parts` in 15,225 cases: 225 edge pairs, plus 3,000 real files against five bases.

**Speed:** the inventory takes 7.8 s, from 17.0 s; the gate 2.9 s, from 4.75 s. `scripts-lib-test` at four workers takes 20.4 s, from 28.5 s, with 147 more test cases.

**Mutation:** dropping the absolute/relative guard fails 8 of the new cases; dropping the defensive copy fails 1.

**Acceptance:** AC1: 512 passed. AC2: 1,235 passed, 3 skipped.
