---
title: '62.1: Herald''s two-builds test names what differs'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 62-1-herald-s-two-builds-test-names-what-differs
spec: spec-pyforge-herald
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-herald/tests/meta/pages_astro.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_pages_astro_differences_report.py'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test_43_5_two_builds_two_days_runs_and_commits_apart_differ_only_in_the_built_from_line` builds the site
twice and asserts the two builds are byte-identical apart from the built-from line. On PR #2431's CI run (job
140707620970) it failed. Its message named one path, `pagefind/pagefind-entry.json`, and said nothing about how the
file differed. Every other file was byte-identical, including Pagefind's index, fragment and meta files, whose names
carry content hashes. The re-run passed.

The entry file holds four fields: Pagefind's version, the language's index hash (also in the meta file's name, which
matched), its page count and its fixed character list. So something other than the hash moved.

Locally the failure did not recur in 23 builds:
- the test alone, three times;
- its whole module, in one process;
- herald's live shard 2, three times, as CI runs it;
- eight two-build pairs in one process, some after a build with the exports mounted.

All of them wrote the same entry file.

**Approach:** `pages_astro.differences_report(one, two)` names every path whose bytes differ between two built trees.
For the first three it shows a unified diff of up to 40 lines when both sides decode as UTF-8, and otherwise each
side's size and sha256. The two-builds test passes the report as its assertion's message. The assertion is unchanged,
and the report is built only when the assertion fails.

Ledger key: `62-1-herald-s-two-builds-test-names-what-differs`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The assertion holds exactly what it held.

**Never:**
- Never skip or re-mark a test.

## Acceptance Criteria

**Given** two built trees that differ
**When** the report is made
**Then** it names every differing path and shows how the first few differ.

- **AC1 — The report.** Expected: exit 0. The tests cover a text diff, a binary file's size and hash, every path
  named with only the first few shown, a long diff cut with its remainder counted, and identical trees.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_pages_astro_differences_report.py -q
  ```

- **AC2 — The two-builds test still passes and carries the report.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pytest "src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py::test_43_5_two_builds_two_days_runs_and_commits_apart_differ_only_in_the_built_from_line" -q
  ```

</intent-contract>

## Result (2026-11-27)

- **AC1:** 5 passed.
- **AC2:** 1 passed.
- **Cause:** not found. It did not recur in 23 local builds. The next failure will show the difference.
