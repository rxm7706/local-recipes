---
title: The pointers lint and the drift gates
type: feature
created: '2026-08-22'
status: done
review_loop_iteration: 0
baseline_revision: 585d1799199bb7e29c9a3134bc373f13ce5632db
followup_review_recommended: true
context: []
warnings:
- oversized
deferred:
- summary: '_code_present()''s narrow `code="X"`/`code=''X''` literal-substring match could miss a check
    code defined a different way (spaced `code = "X"`, a dict-literal `"code": "X"`, ...), producing a
    false unresolved-pointer.'
  evidence: This mirrors failure_catalog_generator.py's own _REGISTRY_CODE_RE = re.compile(r'code=["\']([A-Z]+-[0-9]+)["\']')
    narrow-match convention verbatim -- the spec's own Code Map explicitly directs reusing this exact
    pattern, and Story 7.1's review already accepted the same narrowness for the generator. Not new to
    this story; a future widening (if a differently-styled check-code definition is ever added to recipe_optimizer.py)
    is a legitimate backlog item, not a defect here.
  location: scripts/failure_catalog_check.py:_code_present
  severity: low
- summary: check_drift() decides ordinary drift vs. generator-broke by testing for the literal string
    "DRIFT DETECTED" in the generator's stderr -- a real but self-detecting coupling to Story 7.1's exact
    wording.
  evidence: If failure_catalog_generator.py's message text ever changes, test_check_drift_detects_drifted_catalog
    reds immediately (the test asserts on the finding kind, not the string), so the coupling break surfaces
    at test time rather than as a silent misclassification in production.
  location: scripts/failure_catalog_check.py:check_drift
  severity: low
- summary: Nothing in this repo currently makes a detector finding (this one included) or a tests/scripts/
    failure literally block a PR -- .github/workflows/detectors.yml is advisory-only by a pre-existing
    2026-07-31 operator decision, and tests/scripts/ (including this story's new test file) is not invoked
    by any GitHub Actions workflow at all.
  evidence: 'Confirmed via the Intent Alignment Auditor''s independent read of every workflow file plus
    this dispatch''s own earlier research: detectors.yml''s own header comment states findings surface
    as warning annotations and "the job itself always succeeds, so a detector finding never blocks a merge";
    no workflow references tests/scripts or the pyforge-doctor-scripts-test pixi task. Pre-existing, repo-wide,
    and explicitly out of scope per this story''s own spec ("Never flip .github/workflows/detectors.yml
    from advisory to a hard gate"). Worth a future dedicated decision, not a defect of this diff.'
  location: .github/workflows/detectors.yml
  severity: medium
---

<intent-contract>

## Intent

**Problem:** Story 7.1's `failure-catalog.yaml` generator can detect catalog↔SKILL.md drift and
validate `enforced_by` pointers, but only when explicitly run with `--check` — nothing wires this
into the repo's detector suite, nothing independently re-resolves a *committed* pointer against
the live check registry, and nothing reports the null-rows backlog.

**Approach:** Add `scripts/failure_catalog_check.py`, a new repo-scope detector matching this
repo's existing `*_check.py` convention (`pixi_version_check.py`, `mason_cfe_surface_check.py`):
it resolves every non-null `enforced_by` pointer against the live check surface, delegates
catalog↔SKILL.md drift detection to `failure_catalog_generator.py --check`, and reports the
null-rows count as a visibility-only backlog. Wire it into `scripts/detectors.py`'s
auto-discovery via a new pixi task.

## Boundaries & Constraints

**Always:**
- `scripts/failure_catalog_check.py` declares `DETECTOR = {"scope": "repo"}` and follows the
  `run() -> (findings, stats)` / `main()` (`--json`, exit 0 clean / 1 findings / 2 could-not-run)
  shape used by `scripts/pixi_version_check.py` and `scripts/mason_cfe_surface_check.py`.
- Pointer-resolution lint: for each committed catalog row with non-null `enforced_by`
  (`<repo-relative-path>:<CODE>`), confirm the path exists and `code="<CODE>"`/`code='<CODE>'`
  appears in that file's live source. Missing file or absent code -> finding `unresolved-pointer`.
- Drift check: invoke `.claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py
  --check` (subprocess or in-process import); non-zero -> finding `catalog-drift`.
- This story reads/invokes files under `.claude/skills/conda-forge-expert/` — invoke the
  `conda-forge-expert` skill per CLAUDE.md's BMAD↔CFE Rule 1 before implementing.
- Add a pixi task whose `cmd` contains the script filename with no `--json`, so
  `scripts/detectors.py discover()` picks it up automatically; confirm via
  `python scripts/detectors.py --list`.
- Null-rows report: count of `enforced_by: null` rows / total, surfaced in text and `--json`
  output (`null_rows`, `coverage`) — informational only, never a finding, never affects exit code.
- New tests `tests/scripts/test_failure_catalog_check.py` (mirrors
  `tests/scripts/test_mason_cfe_surface_check.py`'s fixture style, tmp-dir based, never touching
  the real committed catalog/SKILL.md) proving red-first: a bogus/unresolvable pointer and a
  drifted catalog each independently produce a finding and exit 1; a clean fixture exits 0.
- Run `pixi run -e local-recipes test` (full CFE suite, incl. 7.1's freshness meta-test) and the
  new test file locally before considering this done.

**Block If:** none identified — shape, location, and integration point are pinned by the epic
context's explicit convention pointer and the `*_check.py` exemplars already in `scripts/`.

**Never:**
- Never modify `failure_catalog_generator.py`'s existing CLI/output behavior (7.1's contract) —
  call it as-is.
- Never auto-generate/auto-fix/auto-actuate a new `recipe_optimizer.py` check code from a null
  row — the backlog is a report only.
- Never treat the null-rows count itself as a finding, or fail the detector's exit code purely
  because null rows exist (108/110 null today is the expected honest starting state).
- Never flip `.github/workflows/detectors.yml` from advisory to a hard gate — that is a separate,
  already-flagged repo-wide open decision, out of scope here.
- Never hand-edit `failure-catalog.yaml` or `SKILL.md`.
- Never bump `skill-config.yaml`'s version or add a CHANGELOG entry in this story — the Rule-2
  retro lands at the effort's closeout, as a separate step after this spec is implemented.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean fixture | fixture catalog: all pointers resolve, matches fresh `--check` regen | 0 findings, exit 0 | No error expected |
| Bogus pointer | fixture catalog row's `enforced_by` code absent from its pointed-at file | `unresolved-pointer` finding, exit 1 | None (this IS the expected failure) |
| Missing pointer target file | `enforced_by` path itself doesn't exist | `unresolved-pointer` finding, exit 1 | None (expected failure) |
| Drift (gotcha edited w/o regen) | fixture catalog no longer matches `--check` regen of a fixture SKILL.md | `catalog-drift` finding, exit 1 | None (expected failure) |
| Generator itself can't run | `--check` exits with an unrecoverable/unexpected error | surfaced as could-not-run, exit 2 — never silently clean | Non-zero exit, message names cause |
| Real committed catalog (smoke) | actual `failure-catalog.yaml` + SKILL.md + `recipe_optimizer.py` | exit 0 today, `null_rows: 108` reported, 0 findings | No error expected |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py` -- existing generator;
  `--check` mode (`build_catalog`/`render_catalog`/`main`) is the drift-check primitive to reuse.
- `.claude/skills/conda-forge-expert/config/failure-catalog.yaml` -- the committed catalog under
  lint (110 rows; today only G2->ABT-002 and G3->SEL-003 are non-null).
- `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` -- live check registry;
  `code=["\']([A-Z]+-[0-9]+)["\']` regex (already in the generator) is reusable for resolution.
- `.claude/skills/conda-forge-expert/tests/meta/test_failure_catalog_freshness.py` -- 7.1's
  freshness meta-test; its own docstring says it is deliberately narrower than this story's gate
  — add alongside, do not replace.
- `scripts/pixi_version_check.py`, `scripts/mason_cfe_surface_check.py` -- exemplar detector shape.
- `scripts/detectors.py` -- discovery: `SEARCH` (`scripts/*_check.py` + `docs/dashboard/check_*.py`),
  `_declared_scope`, `discover()` (requires a pixi task whose `cmd` contains the script filename
  and no `--json`).
- `tests/scripts/test_mason_cfe_surface_check.py` -- exemplar test/fixture shape to mirror.
- `pixi.toml` -- add the new task near the existing `generate-failure-catalog` task (~line 841) and
  `pixi-version-check` task (~line 634) for pattern reference.

## Tasks & Acceptance

**Execution:**
- `scripts/failure_catalog_check.py` -- new detector: pointer lint + drift delegation + null-rows
  report -- the story's core deliverable.
- `pixi.toml` -- add `[feature.local-recipes.tasks.failure-catalog-check]` -- makes the detector
  discoverable by `scripts/detectors.py` and runnable by name.
- `tests/scripts/test_failure_catalog_check.py` -- new fixture-based tests covering the I/O matrix,
  including red-first proof for `unresolved-pointer` and `catalog-drift`.
- Invoke the `conda-forge-expert` skill during implementation (CLAUDE.md Rule 1 — this story reads
  files under `.claude/skills/conda-forge-expert/`).

**Acceptance Criteria:**
- Given the real committed `failure-catalog.yaml`, when `pixi run -e local-recipes
  failure-catalog-check` runs, then it exits 0 and reports the honest null-rows count without
  treating null rows as findings.
- Given a fixture catalog with a bogus `enforced_by` pointer, when the detector runs against it,
  then it reports `unresolved-pointer` and exits 1.
- Given a fixture catalog that drifted from its source SKILL.md, when the detector runs, then it
  reports `catalog-drift` and exits 1.
- Given the new script, when `python scripts/detectors.py --list` runs, then it appears as a
  registered `scope=repo` detector with a resolved pixi task and no new registry-gap finding.

## Spec Change Log

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 0, medium 3, low 1)
- defer: 3 (high 0, medium 1, low 2)
- reject: 9 (high 0, medium 0, low 9)
- addressed_findings:
  - `[medium]` `[patch]` `run()` silently discarded already-found `unresolved-pointer` findings when `check_drift()` raised `CouldNotRunError` afterward -- fixed so pointer findings surface alongside a could-not-run report instead of vanishing.
  - `[medium]` `[patch]` Malformed-catalog / row-shape inputs were under-validated: `rows: null` (or another falsy-but-wrong-type value) silently read as "0 rows, clean" (exit 0); a non-dict row crashed uncaught, defaulting to Python's exit 1 -- identical to the documented "findings present" exit code, defeating the exit-code contract. Strengthened `_load_catalog` to validate `rows` is a list of mappings (raising `CouldNotRunError` otherwise), added a generic exception fallback in `main()` so an unexpected error still returns 2, and added the two malformed-catalog tests (invalid YAML; valid YAML missing the `rows` key) the Verification Gap reviewer specified.
  - `[medium]` `[patch]` `main()`'s plain-text findings-report branch -- the exact code path `scripts/detectors.py`'s `run_one()` and the bare `pixi run -e local-recipes failure-catalog-check` invoke (no `--json`) -- was never exercised by any test; only the `--json` findings path and the no-findings plain-text path were covered. Added a covering test asserting exit 1 and that stdout contains the finding kind/id/detail and the `FAIL:` summary line.
  - `[low]` `[patch]` The new pixi.toml task description hardcoded a point-in-time "(108/110 today)" null-rows count in a static string -- reworded to drop the specific numbers (this repo's own "derive, don't declare" convention: a hardcoded count goes stale the moment coverage improves).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary of implemented change:** Added `scripts/failure_catalog_check.py`, a new
repo-scope detector (`DETECTOR = {"scope": "repo"}`, matching the `pixi_version_check.py`
/ `mason_cfe_surface_check.py` shape) that (1) independently re-resolves every non-null
`enforced_by` pointer in the committed `failure-catalog.yaml` against the live check
registry (`unresolved-pointer` findings), (2) delegates catalog<->SKILL.md drift
detection to Story 7.1's `failure_catalog_generator.py --check` (`catalog-drift`
findings), and (3) reports the null-rows count as an informational `null_rows`/
`coverage` stat that never gates the exit code. Wired into `scripts/detectors.py`'s
auto-discovery via a new pixi task, `failure-catalog-check`. The `conda-forge-expert`
skill was invoked before implementation per CLAUDE.md Rule 1 (this story reads files
under `.claude/skills/conda-forge-expert/`).

**Files changed:**
- `scripts/failure_catalog_check.py` (new) -- the detector: `check_pointers()`,
  `check_drift()`, `run()`, `main()`.
- `tests/scripts/test_failure_catalog_check.py` (new, 23 tests) -- fixture-based unit
  tests covering every I/O-matrix row, incl. red-first proofs for a bogus pointer and a
  drifted catalog, plus two smoke tests against the real committed catalog.
- `pixi.toml` -- added `[feature.local-recipes.tasks.failure-catalog-check]`.

**Review findings breakdown:**
- patch: 4 (medium 3, low 1) -- all applied and re-verified: (1) `run()` no longer
  silently drops `unresolved-pointer` findings when `check_drift()` raises
  `CouldNotRunError` afterward, (2) `_load_catalog()` now validates `rows` is a list of
  mappings (raises `CouldNotRunError` otherwise) and `main()` gained a broad exception
  fallback that still returns 2, both backed by new tests, (3) added a test covering
  `main()`'s plain-text findings-report branch (the exact path `scripts/detectors.py`
  and the bare pixi task invoke), (4) removed a hardcoded "108/110 today" count from the
  pixi.toml task description.
- defer: 3 (medium 1, low 2) -- recorded in frontmatter `deferred`: `_code_present()`'s
  narrow string-match convention (mirrors Story 7.1's own established pattern);
  `check_drift()`'s coupling to the generator's literal "DRIFT DETECTED" stderr text
  (self-detecting via `test_check_drift_detects_drifted_catalog`); the repo-wide,
  pre-existing fact that no CI workflow currently makes any detector or `tests/scripts/`
  failure literally block a PR (`.github/workflows/detectors.yml` is advisory-only by a
  documented 2026-07-31 decision) -- explicitly out of scope per this story's own spec.
- reject: 9 (all low) -- noise / non-applicable-threat-model / already-independently-
  verified-working items: `DETECTOR`-dict placement (matches the exemplar files'
  established layout), no visible detectors.py registration in the diff (independently
  confirmed live via `python scripts/detectors.py --list`), the "live repo" smoke tests'
  coupling to unrelated tracked-file drift (required by this story's own spec and by
  Story 7.1's precedent), an absolute-path/path-traversal guard on `enforced_by` (no
  real threat model -- the pointer is fully generator-controlled, never external input),
  duplicate-id detection, an argparse-unrecognized-flag exit-code collision, hardcoded
  subprocess timeout / decode-error robustness (speculative, not required), and
  `coverage: 0.0` on an empty catalog (never occurs with the real 110-row catalog).

**Follow-up review recommendation:** `true`. Score = 3×medium(3) + 1×low(1) = 10 (>= 5);
no high-severity patch. Patched-finding counts by severity: high 0, medium 3, low 1.

**Verification performed:**
- `pixi run -e local-recipes failure-catalog-check` -- exit 0, `null_rows=108`,
  `coverage=1.8%`, 0 findings against the real committed catalog (110 rows). Verified
  independently by the reviewing session, not just self-reported.
- `python scripts/detectors.py --list` -- `failure_catalog_check` listed, `scope=repo`,
  resolved task `failure-catalog-check`, zero new registry findings. Verified
  independently.
- `python -m pytest tests/scripts/test_failure_catalog_check.py -q` -- 23 passed (17
  original + 6 added during the patch pass). Verified independently.
- `python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_failure_catalog_freshness.py tests/scripts/test_failure_catalog_check.py -q`
  -- 24 passed together. Verified independently.
- `pixi run -e local-recipes test` (full CFE suite) -- run twice independently by the
  reviewing session (before and after the patch pass): both times `3 failed, 8970
  passed, 30 skipped, 16 deselected, 1 xpassed`, the identical 3 failures each time
  (`test_no_redundant_python_min`, `test_recipe_yaml_parse_audit`,
  `test_spec_surface_check_green`) -- confirmed pre-existing and unrelated (they scan
  the `recipes/*/recipe.yaml` corpus and a `pyforge-marshal` spec-surface baseline,
  neither touched by this story). Zero new failures from the patch pass.

**Residual risks:** None blocking. The 3 deferred findings are real but explicitly
out-of-scope or self-detecting per the reasoning above. `_code_present()`'s narrow
match convention and `check_drift()`'s string-coupling to the generator's exact output
are both inherited, pre-existing design choices from Story 7.1, not new fragility. The
detectors.yml-is-advisory-only fact is a repo-wide, already-known, already-decided gap
(2026-07-31) that this story's own spec explicitly forbids touching.
