---
title: "11.3: The TEA advisory spawns through `engines.py`, like every other subprocess"
type: 'fix'
created: '2026-10-07'
status: 'ready-for-dev'
baseline_revision: '8ef4a6aa7950d8491852344209b60cdbc8765ac0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-11-2-tea-test-review-is-a-warden-advisory-finding.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-13-1-the-tea-advisory-diffs-from-the-remote-tracking-ref.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py
  - src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py
  - src/shared/packages/pyforge-warden/tests/meta/test_extract_no_execution.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the TEA advisory spawns its own subprocess, outside `engines.py`, and no test notices.

- **The rule.** The spine's security boundary names `engines.py` the only module that spawns subprocesses, always
  via `_engine_env()` (`ARCHITECTURE-SPINE.md` § Boundary contracts, and § Implementation Handoff: "route all
  subprocesses through `_engine_env()`"). `engines.py` records the same ownership decision in its own docstring
  (`engines.py:3-12`); its one other spawn, the Story 6.6 `--version` pre-flight `_check_engine_version`
  (`:393`), also lives there.
- **The breach.** Since Story 11.2 (2026-09-07, `9f2bfd9057`), `tea_advisory.py` imports `subprocess` (`:62`), types
  its runner seam with it (`TeaRunner`, `:93`), and its `_default_runner` calls `subprocess.run` itself
  (`:150-:174`, the call at `:160`). That one process skips `_engine_env()`'s normalized environment: it inherits
  stdin instead of `stdin=DEVNULL`, gets no `NO_COLOR=1`, and has no typed `ErrorRecord` for a missing binary, a
  timeout or an OS failure (it relies on `run_tea_test_review`'s blanket fail-open net instead).
- **Measured on `8ef4a6aa79`.** Across `src/shared/packages/pyforge-warden/src/pyforge/warden/` (38 modules) only
  `engines.py:91` and `tea_advisory.py:62` import `subprocess`; no module calls `os.system`, `os.popen` or
  `asyncio.create_subprocess_*` (every other hit of the word is a docstring).
- **Why nothing caught it.** `tests/meta/test_extract_no_execution.py` AST-scans `extract/` only (`EXTRACT_DIR`,
  `:64`); no test scans the rest of the package for a second spawn site. The 2026-10-07 chain-currency cascade
  recorded the breach in the spine and left it (§ Currency reconciliation — 2026-10-07, "One older divergence,
  recorded and not repaired").
- **What is NOT the problem.** The argv is a list and there is no shell, so this is not an injection risk, and the
  advisory's outputs (a note, never a finding) are correct today.

**Approach:** move the spawn into `engines.py`, and make the rule a test.

- `engines.py` gains one TEA entry point beside `run_pixi_lock` (`:368`), the precedent for a non-scan engine
  call: it runs the `tea-test-review` argv through `_engine_env(build_argv, owner="tea-test-review", cwd=target,
  timeout=<the advisory's 1800 s>)` and returns the decoded `--json` text, the `ErrorRecord` (or `None`) and the
  child's exit code. The `--json` flag points at `_engine_env()`'s own `output_path`; the `--output` markdown
  report goes to a scratch directory the call owns and removes, never `target` and never a fixed name in system
  temp. The argv is unchanged otherwise (`--base refs/remotes/origin/main`, `--agent claude`, CAP-23).
- `tea_advisory._default_runner` calls that entry point. On an `ErrorRecord` it raises inside
  `run_tea_test_review`'s existing fail-open net (so the result is `ran=False`, its `skipped_reason` naming the
  error); otherwise it writes the returned text to `json_path` and returns an object carrying the exit code, so
  `run_tea_test_review` keeps its `{0, 1}` check and its JSON read unchanged.
- `tea_advisory.py` drops `import subprocess`. `TeaRunner` names a structural return type (an object with an
  `int` `returncode`, or `None`), so the existing test fakes, which return a `subprocess.CompletedProcess` or
  `None`, stay valid. The module and `_default_runner` docstrings that name `subprocess.run` are corrected.
- No `--version` pre-flight is added: `engines.py` applies `_check_engine_version` only to an engine with a tested
  range mirrored from `pixi.toml` (`tests/meta/test_engine_version_range_sync.py`), and `pixi.toml` pins TEA
  `>=1.27.2`, open-ended (`tea-test-review --version` prints `1.27.2` in `pyforge-guild`). A tested TEA range is a
  separate decision.
- A new meta test, `tests/meta/test_subprocess_sole_site.py`, AST-scans every module of the installed
  `pyforge.warden` package (subpackages included) except the top-level `engines.py` and fails on: an import of
  `subprocess` in any form (`import subprocess`, `import subprocess as …`, `from subprocess import …`, inside
  `if TYPE_CHECKING:` too); `os.system` / `os.popen` called through any name bound to `os`, or imported with
  `from os import`; `asyncio.create_subprocess_exec` / `create_subprocess_shell` called bare, from-imported, or
  through any name bound to `asyncio`, and an import of `asyncio.subprocess`. It asserts it scanned more than one
  module, that `engines.py` (excluded) does import `subprocess` (the guard is alive), and that each detector fires
  on a synthetic source. Its stated bounds match `test_extract_no_execution.py`'s: a static check, so `getattr`,
  `importlib` and plain-assignment aliasing are out of scope.

Ledger key: `11-3-the-tea-advisory-spawns-through-engines-py-like-every-other-subprocess`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-bmad-suite-lifecycle` CAP-4 (TEA full adoption, the warden half; folded on
  2026-09-17 into `pyforge-steward:CAP-33`): Story 11.2 shipped `tea_advisory.py` under it, in Epic 11. A
  spawn site outside `engines.py` is a defect of that shipped behaviour against the spine's security boundary, so
  this story mints no CAP.
- **Constraints kept.** suite:AD-4 (an advisory contributes a note, never a verdict), suite:AD-10 (fail-closed
  when the suite:AD-9 roster lacks `tea`), `spec-pyforge-warden` CAP-23 (the base is the remote-tracking ref).
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** The warden chain-currency cascade of 2026-10-07 (spine § Currency reconciliation — 2026-10-07).

## Acceptance Criteria

- Given the fixed tree When `tea_advisory.py` is read Then it imports `subprocess` in no form, and its default
  runner reaches the binary only through the `engines.py` entry point.
- Given the `engines.py` entry point with `_engine_env()`'s spawn replaced by a recorder When the default runner
  runs Then the recorded call is one argv list with `--base refs/remotes/origin/main`, `--json` naming the seam's
  output path, `--output` naming a path outside `target`, `cwd` equal to `target`, `stdin=DEVNULL`, `NO_COLOR=1` in
  its environment and a timeout of 1800 s; the Story 13.1 argv test asserts the base through this seam.
- Given the entry point's spawn raising `FileNotFoundError`, `TimeoutExpired` or `OSError` When the advisory runs
  Then the result is `ran=False` with a `skipped_reason` naming the failure, and no exception leaves
  `TeaAdvisoryScanPlugin`.
- Given the child exiting 0 or 1 with a valid `--json` verdict When the advisory runs Then the score, the
  recommendation and the summary equal today's for the same verdict; given any other exit code Then the result is
  `ran=False` and the JSON is not read.
- Given a roster without `tea` When `run_tea_test_review` runs with no injected runner Then it raises
  `TeaRosterMissingError` before any spawn, as today; given the roster with `tea` and no binary on PATH Then
  `ran=False` with no spawn, as today.
- Given an injected `runner` that writes a verdict to `json_path` and returns a `subprocess.CompletedProcess` or
  `None` When `run_tea_test_review` runs Then it behaves as today (every existing `test_tea_advisory.py` and
  `test_cli_doctor.py` test passes unedited, except the Story 13.1 argv test's patch point).
- Given the new meta test When the station suite runs on the fixed tree Then it passes; given a synthetic module
  that imports `subprocess`, calls `os.system` or `os.popen`, or calls `asyncio.create_subprocess_exec` Then each
  detector fires; given `tea_advisory.py` restored to `8ef4a6aa79` (mutation) Then the meta test fails naming
  `tea_advisory.py`.
- Given the story lands When `pixi run --frozen -e pyforge-warden pyforge-warden-test` runs Then it passes.

## Boundaries & Constraints

**Always:**
- Spawn TEA through `_engine_env()` in `engines.py`; keep `_engine_env()`'s own contract and every existing caller
  (deptry, osv-scanner, native lockfiles, `run_pixi_lock`) unchanged.
- Keep the advisory's outcomes as today: `{0, 1}` trusted, everything else fail-open, the roster refusal
  fail-closed, no note ever a `Finding`, a rung or the exit code.
- Never run the real `tea-test-review` binary in the suite: every new test replaces the spawn.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped: `spec-pyforge-warden` governs
  `engines.py`, `tea_advisory.py` and the tests; `spec-pyforge-core` co-governs the two source files; run
  `spec-surface-check` for any co-governor it names (AGENTS.md pre-PR item 5).

**Never:**
- Never add a second subprocess helper outside `engines.py`, and never route TEA through `_check_engine_version`
  without a tested range mirrored from `pixi.toml` (out of scope here).
- Never widen the meta test's exclusion beyond the top-level `engines.py`, and never weaken or delete an existing
  test; the Story 13.1 argv test moves its patch point and keeps its assertion.
- Never change TEA's argv flags, the 1800 s timeout, `TeaAdvisoryResult`, `TeaRosterMissingError`, the doctor
  check `_doctor_check_tea`, `scanner_plugins.py`'s registration or the `WARDEN_OPTIONAL_SCANNERS` opt-in.
- Never touch `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Never edit the spine: its 2026-10-07 divergence paragraph is a dated record; a later chain-currency cascade
  records the repair.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| verdict pass | child exits 0, valid `--json` | `ran=True`, score and recommendation as today | — |
| verdict fail | child exits 1, valid `--json` | `ran=True`, the real score | — |
| untrusted exit | child exits 2 or 3 | `ran=False`, JSON not read | fail-open |
| binary vanishes after `which` | spawn raises `FileNotFoundError` | `ran=False`, reason names the missing engine | typed `ErrorRecord` → fail-open |
| timeout | spawn raises `TimeoutExpired` | `ran=False`, reason names the timeout | typed `ErrorRecord` → fail-open |
| garbled verdict | child exits 0, non-JSON or non-utf-8 output | `ran=False` | fail-open |
| roster lacks `tea` | no runner injected | `TeaRosterMissingError` before any spawn | fail-closed (suite:AD-10) |
| binary absent | roster has `tea`, not on PATH | `ran=False`, no spawn | fail-open |
| injected runner | test fake | as today | — |
| second spawn site | any module but `engines.py` imports `subprocess` | meta test fails, naming the module | — |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-10-07 (subprocess seam) entry.
- Epic: Epic 11 (Story 11.2 shipped `tea_advisory.py` there under `spec-bmad-suite-lifecycle` CAP-4); a fix joins the
  epic that shipped the behaviour, which reopens (doctor Story 41.5).
- Ledger key: `11-3-the-tea-advisory-spawns-through-engines-py-like-every-other-subprocess`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Spec: `spec-pyforge-warden/.memlog.md` records the mint; no contract change, `SPEC.md` untouched.
- Dispatch note: Epic 11's `[epic_surfaces]` entry in `planning-artifacts/marshal-policy.toml` gains every Spec memlog
  (the `spec-pyforge-core` co-governor reconcile) in the minting commit.
- Minted 2026-10-07 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `grep -rn "import subprocess\|from subprocess" src/shared/packages/pyforge-warden/src/pyforge/warden/` — expected:
  `engines.py` only.
- Mutation: restore `tea_advisory.py` from `8ef4a6aa79` (`git show 8ef4a6aa79:<path> > <path>`) and run
  `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_subprocess_sole_site.py`
  — expected: fail naming `tea_advisory.py`. Restore the fixed file.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped stamps.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
