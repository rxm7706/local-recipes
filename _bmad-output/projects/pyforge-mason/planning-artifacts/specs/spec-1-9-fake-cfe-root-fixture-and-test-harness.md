---
title: 'Fake CFE root fixture and test harness'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: 'e0ba45630db9924525500ade021833d8cf20d5e1'
final_revision: 'c51c596938ac4f0f1f59aca20c6d208a8997e17d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** No `tests/fixtures/` tree exists; every current test either mocks `subprocess.run`
inline (`test_cfe.py`) or builds a synthetic marker directory ad hoc (`test_resolve.py`). AD-16
requires a real on-disk fake CFE root the whole suite (minus one Epic-5 exception) can run against
with no real CFE install, network, or `recipes/` dir -- and no `slow` pytest marker exists yet to
later exclude that one exception from the default task.

**Approach:** Add `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/` -- a real
marker directory containing a shared `_stub_support.py` runtime plus two named stub scripts that
mirror real CFE script filenames (`validate_recipe.py`, `submit_pr.py`), each emitting a canned
JSON stdout body and exit code that a test can override via `MASON_FIXTURE_*` environment
variables, including a leading non-JSON progress line. Add a `conftest.py` exposing a
`fake_cfe_root` pytest fixture returning the tree's path, register the `slow` marker in
`pyproject.toml`, and split the `pyforge-mason-test` pixi task into a fast default (`-m "not
slow"`) plus a new `pyforge-mason-test-slow` task, mirroring `pyforge-warden`/`pyforge-marshal`.

## Boundaries & Constraints

**Always:** The fixture tree is static and read-only across tests -- all per-test variation goes
through `MASON_FIXTURE_STDOUT`/`MASON_FIXTURE_EXIT_CODE`/`MASON_FIXTURE_PROGRESS_LINE` environment
variables read at stub-script runtime, never by rewriting fixture files. Every stub script is
invocable as `[interpreter, script_path, *extra_argv]` (AD-4's shape) and ignores any extra argv
without error. The progress line, when set, is written to stdout before the JSON body -- FR-4's
tolerant-parsing target is stdout, not stderr. `_stub_support.py` and both named stub scripts stay
self-contained (stdlib only, `Path(__file__)`-relative imports), matching the real
`.claude/scripts/conda-forge-expert/*.py` wrapper convention. The `slow` marker text and the
fast/slow task split mirror `pyforge-warden`'s and `pyforge-marshal`'s existing pixi.toml pattern
verbatim in shape (description wording may adapt). `conftest.py` lives at
`src/shared/packages/pyforge-mason/tests/conftest.py` (suite-wide, not per-directory).

**Block If:** none identified -- AD-16, FR-4, and the existing `pyforge-warden`/`pyforge-marshal`
marker-split convention fully specify this work.

**Never:** Retrofit Stories 1.5-1.8's already-`done`, already-reviewed tests to consume this
fixture instead of their existing tmp_path-synthetic trees or mocks -- not named by this story's
acceptance criteria, and touching stable reviewed test files is out of scope here. Build the
Story 2.1 CFE script-invocation adapter, `CfeResult`, or JSON-stdout extraction logic -- this story
only supplies the fixture Epic 2 will invoke against, not the caller. Scaffold `tests/integration/`
-- Epic 2's first integration test (Story 2.4) creates that directory when it lands. Add a
placeholder `@pytest.mark.slow` test to make `pyforge-mason-test-slow` collect something --
Story 5.3's FR-46 delegation-fidelity test is the first real slow test; until then the task
legitimately collects zero tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Stub invoked with no env overrides | `python3 validate_recipe.py` | stdout is exactly the script's canned JSON body; exit code `0` | none |
| `MASON_FIXTURE_EXIT_CODE` set | env `MASON_FIXTURE_EXIT_CODE=3` | process exits `3`; stdout body unchanged | none |
| `MASON_FIXTURE_STDOUT` set | env `MASON_FIXTURE_STDOUT='{"x": 1}'` | stdout body is exactly that value instead of the canned default | none |
| `MASON_FIXTURE_PROGRESS_LINE` set | env `MASON_FIXTURE_PROGRESS_LINE="Resolving deps..."` | stdout's first line is that literal text, followed by the (canned or overridden) JSON body on the next line | none |
| Fixture tree used as a CFE root | `resolve_cfe_root(None, {}, fake_cfe_root)` | resolves with `step=STEP_CWD_WALK`, `root=fake_cfe_root` -- `.claude/scripts/conda-forge-expert` is a real directory | none |
| Second named stub invoked independently | `python3 submit_pr.py` with no env set | its own distinct canned JSON body; exit `0` -- proves the mechanism generalizes past one script | none |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/_stub_support.py` (new) --
  shared `emit(default_stdout, default_exit_code=0) -> int` runtime read by every stub script;
  resolves the three `MASON_FIXTURE_*` overrides.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/validate_recipe.py` (new) --
  stub mirroring the real CFE `validate_recipe.py` wrapper; canned default matches the real
  script's `--json` shape: `{"passed": true, "errors": [], "warnings": [], "info": [],
  "rattler_lint_ran": true}`.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/submit_pr.py` (new) -- stub
  mirroring the real CFE `submit_pr.py` wrapper; canned default matches the real script's
  success-path shape: `{"success": true, "recipe": "example-recipe", "branch":
  "add-example-recipe", "github_user": "example-user", "pr_url":
  "https://github.com/example/example/pull/1", "message": "PR created: ..."}`.
- `tests/conftest.py` (new) -- `fake_cfe_root` pytest fixture returning
  `Path(__file__).parent / "fixtures" / "fake_cfe_root"`.
- `tests/unit/test_fake_cfe_root_fixture.py` (new) -- exercises every I/O-matrix row above by
  invoking the stub scripts as real subprocesses (this is testing the fixture itself, not
  requiring a real CFE install -- consistent with AD-16).
- `pyproject.toml` (extend) -- add `[tool.pytest.ini_options]` with a `markers = ["slow: ..."]`
  entry, mirroring `pyforge-warden/pyproject.toml`'s existing block.
- `{project-root}/pixi.toml` (extend) -- `pyforge-mason-test` task gains `-m "not slow"`; new
  `pyforge-mason-test-slow` task added, mirroring `pyforge-marshal`'s split (lines ~230-236).

## Tasks & Acceptance

**Execution:**
- [x] `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/_stub_support.py` -- add
  `emit(default_stdout: str, default_exit_code: int = 0) -> int`: prints
  `MASON_FIXTURE_PROGRESS_LINE` (if set) first, then `MASON_FIXTURE_STDOUT` or `default_stdout`,
  then returns `int(MASON_FIXTURE_EXIT_CODE)` if set else `default_exit_code` -- AD-16.
- [x] `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/validate_recipe.py` --
  `sys.path.insert(0, str(Path(__file__).parent))`, import `_stub_support`, call `emit(...)` with
  the real script's `--json` shape under `sys.exit(...)` -- AD-16.
- [x] `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/submit_pr.py` -- same
  pattern, `emit('{"pr_url": "https://github.com/example/example/pull/1"}')` -- AD-16.
- [x] `tests/conftest.py` -- `fake_cfe_root` fixture (see Code Map) -- AD-16.
- [x] `tests/unit/test_fake_cfe_root_fixture.py` -- one test per I/O-matrix row: default canned
  output, exit-code override, stdout override, progress-line prefix, `resolve_cfe_root` resolves
  the tree, and the second stub script (`submit_pr.py`) works independently with its own canned
  body -- AD-16.
- [x] `pyproject.toml` -- add `[tool.pytest.ini_options]` `markers = ["slow: ..."]`, mirroring
  `pyforge-warden`'s existing entry -- NFR-13.
- [x] `{project-root}/pixi.toml` -- `pyforge-mason-test` task: append `-m "not slow"` to its `cmd`;
  add `pyforge-mason-test-slow` task (`cmd = "pytest src/shared/packages/pyforge-mason/tests -q -m
  slow"`), mirroring `pyforge-marshal-test`/`pyforge-marshal-test-slow` -- NFR-13.

**Acceptance Criteria:**
- Given `tests/fixtures/fake_cfe_root/`, when the fixture is built, then it mirrors the real layout
  (`.claude/scripts/conda-forge-expert/<script>.py`) with stub scripts that emit canned stdout and
  configurable exit codes.
- Given the fixture, when a stub is asked to emit a leading progress line before its JSON body,
  then it does so, exercising the tolerant-parsing path.
- Given the whole test suite except the FR-46 fidelity test (which does not exist yet -- Story 5.3),
  when it runs on a machine with no real CFE installation, no network, and no `recipes/` directory,
  then every test passes.
- Given `pyproject.toml`, when pytest markers are declared, then a `slow` marker exists, mirroring
  the `pyforge-warden` convention, and the default `pyforge-mason-test` task excludes it.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium: 3, low: 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter's separate passes independently
    surfaced a real contract-fidelity gap; Blind Hunter found `validate_recipe.py`'s canned body
    (`{"valid": true, "errors": []}`) uses keys that don't exist anywhere in the real
    `.claude/skills/conda-forge-expert/scripts/validate_recipe.py --json` output, which is
    `{"passed", "errors", "warnings", "info", "rattler_lint_ran"}` -- verified live against the
    real script's `print_result`. Replaced the canned body with the real shape so Epic 2
    developers who build against this fixture inherit the correct contract, not an invented one.
  - `[medium]` `[patch]` Blind Hunter found `submit_pr.py`'s canned body omits `success`, the key
    the real script's own exit logic (`sys.exit(0 if result.get("success") else 1)`) depends on --
    verified live against the real script. Replaced the canned body with the real success-path
    shape (`success`/`recipe`/`branch`/`github_user`/`pr_url`/`message`).
  - `[medium]` `[patch]` Both reviewers independently flagged that two "default canned output"
    tests (`test_default_canned_stdout_and_exit_zero`, `test_second_stub_script_works_independently`)
    called `subprocess.run(..., env=None)`, inheriting the real ambient environment -- an
    accidental `MASON_FIXTURE_*` leak in the runner's shell would silently override the asserted
    default. Introduced a module-level `_CLEAN_ENV` (ambient environment with `MASON_FIXTURE_*`
    stripped) as `_run`'s default and applied it to every test in the file for consistency, not
    just the two named.
  - `[low]` `[patch]` Blind Hunter found the stub scripts' docstrings claimed to mirror "the real
    wrapper's file-relative-import convention," when the real `.claude/scripts/conda-forge-expert/`
    wrappers file-relatively locate and subprocess-*delegate* to the canonical skill script --
    they never import anything. Corrected the docstrings in `_stub_support.py`, `validate_recipe.py`,
    and `submit_pr.py` to describe the sibling-import pattern as this fixture's own convention.
  - `[low]` `[patch]` Edge Case Hunter found `test_fixture_tree_resolves_as_a_cfe_root` compares
    `resolve_cfe_root`'s result against the bare `fake_cfe_root` fixture path rather than its
    `.resolve()`d form, inconsistent with `test_resolve.py`'s own established defensive pattern
    for exactly this kind of walk-target equality check (relevant if `fake_cfe_root` ever
    traverses a symlink). Aligned the assertion with the sibling test's pattern.
- Rejected findings (8): both reviewers' request that the stubs replicate the real scripts'
  `--json`-flag-gated JSON output and required-positional-argument enforcement -- AD-16's own text
  scopes this fixture to "stub scripts emitting canned stdout," not a faithful CLI-argparse
  reimplementation, and Story 2.1 (this story's explicit Never boundary) owns constructing and
  testing the real invocation argv. Blind Hunter's note that `pyforge-mason-test-slow` exits 5
  ("no tests ran") -- already documented in this spec's own Design Notes/Verification as
  intentional pending Story 5.3, and confirmed live that nothing in the repo (e.g.
  `marshal-policy.toml`'s readiness gate) currently invokes that task automatically. Blind
  Hunter's ask for a test proving the stub tree runs under a non-suite interpreter -- the "stdlib
  only" property is already true by static inspection (no third-party imports exist), so a
  bespoke-interpreter test would prove nothing a code read doesn't already. Blind Hunter's ask for
  a combined exit-code+stdout-override test -- `emit()`'s three env reads are fully independent
  with no coupling logic, so no combination test could catch anything the isolated tests miss.
  Edge Case Hunter's and Blind Hunter's shared ask to guard `int(MASON_FIXTURE_EXIT_CODE)` against
  a malformed value -- this env var is set exclusively by trusted, co-located test code, never an
  external boundary; failing loudly on a test-authoring typo is correct, not a gap, per this
  repo's "don't validate scenarios that can't happen" convention. Blind Hunter's ask for the
  `fake_cfe_root` fixture to pre-assert the marker directory exists -- it is version-controlled
  and always present; a hypothetical deletion already produces an immediately diagnosable
  `FileNotFoundError`. Blind Hunter's note that only 2 of ~60 real CFE scripts have stubs with no
  documented recipe for more -- already addressed by this spec's own Design Notes plus
  `_stub_support.py`'s docstring, which both name the extension pattern explicitly.

### 2026-08-09 — Review pass (verification repair)
- intent_gap: 0
- bad_spec: 0
- patch: 2 (low: 2)
- defer: 1 (low: 1)
- reject: 9
- addressed_findings:
  - `[low]` `[patch]` This pass's own diff is not code but a `spec-surface-check` reconciliation:
    the prior session's story commit changed root `pixi.toml` (the fast/slow `pyforge-mason-test`
    split), which two OTHER specs' surfaces also govern
    (`pyforge-marshal/spec-pyforge-core`, `pyforge-steward/spec-unified-container`); their memlogs
    hadn't named the change, so `python scripts/spec_surface_check.py` gated red with 2
    `[drift]` findings -- the verification failure this pass exists to repair. Reconciled by
    adding a `(change)` entry naming `pixi.toml` to each spec's `.memlog.md`, then re-stamping
    `scripts/.spec-surface-baseline.json` scoped to just those two specs
    (`--write-baseline --spec pyforge-marshal/spec-pyforge-core --spec
    pyforge-steward/spec-unified-container`). No change to this story's `<intent-contract>` or any
    file its Code Map governs. Blind Hunter, independently verifying against
    `spec-pyforge-doctor/SPEC.md`'s surface and `pixi.toml`'s task list, found the new
    `spec-pyforge-core` entry sat next to a pre-existing (already-wrong-when-written) claim that
    `pixi.toml` is "governed by three surfaces at once (also spec-pyforge-doctor and
    spec-unified-container)" -- `spec-pyforge-doctor` has never included `pixi.toml` in its surface
    (confirmed against its full git history). Added a `(correction)` bullet to
    `spec-pyforge-core/.memlog.md` naming the error rather than silently rewriting the historical
    entry, and cross-referenced it from `spec-unified-container/.memlog.md`.
  - `[low]` `[patch]` Blind Hunter found my new memlog text ("mirroring the
    pyforge-warden/pyforge-marshal marker-split convention") overstated naming uniformity: `pixi.toml`
    shows marshal's equivalent task is literally named `pyforge-marshal-test-slow` (which the real
    `pyforge-mason-test-slow` task's own description cites), but warden's is `pyforge-warden-test-corpus-oracle`,
    not `*-test-slow` -- confirmed by reading `pixi.toml` directly. Reworded both new memlog entries
    to cite `pyforge-marshal-test-slow` by name and note warden's differently-named equivalent,
    rather than implying a uniform `*-test-slow` naming convention across both stations.
  - `[low]` `[defer]` Edge Case Hunter and Blind Hunter (independently) surfaced that
    `pyforge-mason/spec-pyforge-mason`'s own surface still shows 23 governed files
    (this story's new fixture/test/pixi files among them) as `[drift-presumed]` -- its memlog moved
    since the last baseline stamp but doesn't name them individually. Confirmed non-gating by the
    detector's own design (`spec_surface_check.py`'s docstring: informational, "unproven rather than
    wrong") and confirmed via `--json specs` output that this story's diff didn't cause it -- it
    predates this pass. Reconciling it means authoring content in mason's own spec memlog, which is
    a mason-spec-ownership decision, not a mechanical verification repair; logged to
    `deferred-work.md` instead of actioned here.
- Rejected findings (9): Edge Case Hunter's claim that a third surface (mason's own spec) might
  also govern `pixi.toml` and go unreconciled -- verified false via `spec_surface_check.py --json`'s
  `specs` mapping and `spec-pyforge-mason/SPEC.md`'s frontmatter directly: its surface is
  `src/shared/packages/pyforge-mason/**` only, never `pixi.toml`. Edge Case Hunter's ordering-risk
  concern (the baseline write running before the memlog edits were saved) -- verified non-issue: the
  edits were saved first, `--write-baseline` ran after, and the post-hoc `spec_surface_check.py` run
  confirms both files' recorded hashes match their on-disk content with exit 0. Blind Hunter's and
  Edge Case Hunter's shared note that both memlog entries carry the identical hand-set timestamp
  `2026-08-09T11:40` -- this file's own history already carries the same batch-timestamp pattern
  (8 existing entries across other memlogs share one timestamp from an earlier reconciliation), so
  this matches established convention rather than deviating from it. Blind Hunter's note that the
  new entries don't name the `feature.pyforge-ci`-style pixi feature namespace the way the prior
  doctor-authored entry does -- cosmetic precision-of-detail mismatch, not a factual error. Blind
  Hunter's note that the entries duplicate prose across both memlog files with no single source of
  truth -- matches the pre-existing pattern already used by every other cross-spec pixi.toml
  reconciliation in these same two files. Blind Hunter's note that the entries don't cite the
  originating commit SHA -- matches pre-existing convention in this file (identifies work by
  epic/story, not SHA). Blind Hunter's note that this diff includes no evidence the maintenance-label
  PR gate was applied -- out of scope for this pass: `step-04-review.md`'s Finalize instructions
  commit but explicitly do not push or open a PR in this session. Blind Hunter's note that the
  baseline's "deterministic script output, not hand-edited" claim can't be verified from the diff
  alone -- the reviewer's own independent hash recomputation confirmed the claim holds; noise once
  verified. Blind Hunter's meta-observation that "named" in the detector's per-file rule is a proxy
  for "verified true," not truth itself -- restates the same already-corrected stale claim (see the
  addressed `(correction)` bullet above) rather than raising a new, distinct defect.

## Design Notes

The three `MASON_FIXTURE_*` environment variables are process-global, not per-script-name-scoped
-- a test configuring one stub's behavior does not affect a second stub invoked in the same test
unless both are invoked under the same overridden environment. This is sufficient for the current
one-stub-per-test-case usage pattern; if a future Epic 2 test needs two differently-configured
stubs live in the same process, it invokes them as separate subprocess calls with different
`env=` dicts (each subprocess call already takes its own `env` mapping under AD-4's
`[interpreter, script, *args]` invocation shape), not a design change to this fixture.

`validate_recipe.py` and `submit_pr.py` are real filenames from the actual
`.claude/scripts/conda-forge-expert/` wrapper directory (verified to exist), chosen so the fixture
literally mirrors the real layout rather than inventing speculative future Epic 2 script names.
Epic 2 stories are free to add more stub scripts under this same tree using `_stub_support.emit`
when they need one this story didn't anticipate.

`pyforge-mason-test-slow` legitimately collects zero tests (pytest exit code 5) until Story 5.3
lands FR-46's delegation-fidelity test -- this mirrors the documented Story-1.9-then-5.3 sequencing
in `test-architecture.md` and is not a defect to work around here.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (236 existing +
  new fixture-self-tests), still excludes `slow` (none exist yet, so behavior is unchanged from
  today's unfiltered run).
- `pixi run -e pyforge-mason pyforge-mason-test-slow` -- expected: `no tests ran` (exit code 5) --
  documented in Design Notes, not a failure of this story.
- `python3 src/shared/packages/pyforge-mason/tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/validate_recipe.py`
  -- expected: prints the real script's `--json` shape (`{"passed": true, "errors": [], ...}`) and
  exits `0`, run directly with no pytest involved, proving the stub is a genuine standalone script.

## Auto Run Result

Status: done

Summary: Resumed session to repair a deterministic-verification failure from the prior session's
landed work. `python scripts/spec_surface_check.py` gated red with 2 `[drift]` findings: root
`pixi.toml`'s Story-1.9 edit (the `pyforge-mason-test` fast/slow split) is also governed by
`pyforge-marshal/spec-pyforge-core` and `pyforge-steward/spec-unified-container`'s surfaces, and
neither spec's memlog had named the change. No code, test, or fixture file changed -- the story's
own implementation (all Tasks & Acceptance already `[x]`, 242/242 tests green, including the 6
fixture-self-tests covering every I/O-matrix row) was already correct and untouched.

Files changed (this pass, commit `c51c596938ac4f0f1f59aca20c6d208a8997e17d`):
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` --
  added a `(change)` entry naming `pixi.toml`'s Story 1.9 edit, plus a `(correction)` entry fixing a
  pre-existing wrong "governed by three surfaces" claim found during review.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/.memlog.md`
  -- same `(change)` entry, cross-referencing the correction above.
- `scripts/.spec-surface-baseline.json` -- re-stamped via `spec_surface_check.py --write-baseline
  --spec pyforge-marshal/spec-pyforge-core --spec pyforge-steward/spec-unified-container` (scoped,
  not a blanket stamp).

Review findings breakdown (this pass): 2 patch (both low severity, applied -- the "three surfaces"
correction and a wording fix removing an overstated pyforge-warden naming-convention claim), 1 defer
(low severity -- `pyforge-mason/spec-pyforge-mason`'s own memlog has 23 unnamed governed files,
`[drift-presumed]`/non-gating, logged to `deferred-work.md`), 9 reject (see Review Triage Log for
detail -- includes a verified-false Edge Case Hunter claim that a third surface also needed
reconciling).

Verification performed:
- `python scripts/spec_surface_check.py` -- exit 0, "OK: every tracked file governed or
  allowlisted; no drift." (previously exit 1 with the 2 `[drift]` findings above).
- `pixi run -e pyforge-mason pyforge-mason-test` -- 242 passed.
- `pixi run -e pyforge-mason pyforge-mason-test-slow` -- exit 5 ("242 deselected"), matching the
  spec's documented expectation.
- `python3 .../fake_cfe_root/.claude/scripts/conda-forge-expert/validate_recipe.py` (standalone) --
  prints the real `--json` shape, exits 0.
- `pixi project export conda-environment -e build` vs. committed `environment.yaml` -- in sync (no
  dependency change in this story's pixi.toml edit).
- `python3 scripts/detectors.py --scope repo` -- `spec_surface_check` now passes; two unrelated
  detectors (`ledger_regression_check`, `llms_full_check`) still report findings, but both compare
  this branch against `origin/main`, which has advanced past this branch's merge-base with unrelated
  merges since this worktree was created -- pre-existing branch staleness, not caused by or in scope
  for this story or this repair pass.

Residual risks: none identified for this story's own surface. The deferred `[drift-presumed]` item
on `spec-pyforge-mason` is informational/non-gating by design and does not block this story.

