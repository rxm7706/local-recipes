---
title: '127.1: The TEA generator links a story to a test file by whole name parts'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 127-1-the-tea-generator-links-a-story-to-a-test-file-by-whole-name-parts
spec: spec-pyforge-testing-charter
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '_bmad/scripts/bmad_tea_playwright.py'
  - 'src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marshal's two slowest live tests render test-architecture documents: `test_fleet_smoke_all_eight_paths_exist_without_tbd` (37.9 s on CI, 27.8 s here) and `test_herald_marshal_dry_run_regenerable_without_tbd[pyforge-marshal]` (24 s on CI). A profile puts 95% of the render in `_stories_linked_to_test`. It builds one bounded regex per story and test file and calls `re.search` 342,612 times for marshal (558 stories, 307 test files), which overflows `re`'s 512-entry cache, so nearly every call compiles. Rendering all eight stations takes 12.5 s.

**Approach:** A story's token (`1.2` becomes `1_2`) matches when its `_`-separated parts appear contiguously in the stem's parts. That is the rule the regex `(?:^|_)(?:story_)?<token>(?:_|$)` held: a token bounded by `_` or an end of the stem, so `1_1` never matches `11_1`. The stem's windows are built once per token width.

Ledger key: `127-1-the-tea-generator-links-a-story-to-a-test-file-by-whole-name-parts`.

### Living CAP citations

- spec-pyforge-testing-charter:CAP-2 (one automation path; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every station's generated document is byte-identical to the regex version's.

**Never:**
- Never change a test's assertion, or the generator's version (its output does not change).

## Acceptance Criteria

**Given** the eight stations' epics and tests
**When** the generator renders each document
**Then** each document is byte-identical to the old renderer's, and the eight take under a second

- **AC1 — The matcher keeps the bounded-token rule.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py -q
  ```

- **AC2 — Every generated matrix is current.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python _bmad/scripts/bmad_tea_playwright.py --all --check
  ```

</intent-contract>

## Result (2026-11-27)

- Rendering the eight stations took 12.49 s before (marshal 7.96 s, steward 4.28 s) and 0.27 s after (marshal 0.09 s, steward 0.06 s); the eight documents are byte-identical (`diff -r` of both renders is empty).
- `test_fleet_smoke_all_eight_paths_exist_without_tbd` takes 0.54 s (from 27.8 s here), and the marshal case of `test_herald_marshal_dry_run_regenerable_without_tbd` 0.18 s (from 18 s).
- `test_story_links_keep_the_bounded_token_rule` compares the matcher with the old regex over 13 stems and 7 story ids: boundaries, the `story_` prefix, hyphens, a double underscore, a lettered id and a stem with no match.
- AC1: 18 passed. AC2: every station's matrix is current.
