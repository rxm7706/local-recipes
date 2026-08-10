---
title: 'Configuration surface, logging, and child-output streaming'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: 'b1c885caf5305a1cebb8300eddca0de3562d79eb'
final_revision: 'f91b693a35'
review_loop_iteration: 0
followup_review_recommended: true
# true, fifth time. The self-inflicted-regression streak BROKE here -- this pass's most consequential
# finding is not something the fourth pass introduced, it is a defect present since `run_streamed`
# was first written and signed off by four passes: stderr was streamed per-newline, not as produced,
# so any terminator-free child output was held for the length of the pause. That changes what the
# recommendation is arguing. It is no longer "the last pass probably broke something"; it is "this
# pass rewrote the reader at the I/O core of a primitive with a three-for-four regression history,
# and prior passes have repeatedly proven that a guard here can look sound and be incapable of
# failing." Mitigations this time: all five behavioral fixes were mutation-verified against the
# pre-fix code, AND the two historic deadlock guards were re-mutated to prove the rewrite did not
# reopen either healed hole. Weigh that evidence; do not skip on the strength of it. If a sixth pass
# finds only cosmetics in `run_streamed`, that is the signal to stop.
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The v1 knob set is missing `--cfe-timeout`/`MASON_CFE_TIMEOUT` (deferred by Story
1.2's own Never boundary), `--verbose`/`--quiet` are parsed but never wired into real logging
(same boundary), and AD-25's STREAM invocation mode has no primitive yet -- a delegated operation
long enough to need live progress has nothing to call.

**Approach:** Add the sixth knob (flag → environment → `None`, no Mason-wide default per PRD
FR-4's "per-operation default"), wire `--verbose`/`--quiet` into stdlib `logging` configured to
stderr in `main()`, add an AD-13 meta-test banning config-file-parser imports, and add
`cfe.py::run_streamed` -- the STREAM-mode subprocess primitive Story 2.1's CFE adapter will call
and Epic 3's `engines/*` will mirror (Consistency Conventions forbid a shared helper module).

## Boundaries & Constraints

**Always:** Precedence for every knob, including the new `--cfe-timeout`, is flag → environment →
default, matching `_resolve_str`/`_resolve_bool`. `--cfe-timeout` has no Mason-wide default
(`None` when unset) -- the future call site supplies its own. `_configure_logging` runs once,
immediately after `parser.parse_args(argv)` in `main()`, before any noun dispatch, so every
command path is covered. `--quiet` wins when both `--verbose` and `--quiet` are given (documented
tie-break; ACs don't specify one). `run_streamed` never writes to Mason's own `sys.stdout` and
resolves `sys.stderr` at call time, not def time (so test-time monkeypatching applies). It is a
list-argv, mandatory-timeout subprocess call (AD-2/AD-4) living in `cfe.py`.

**Block If:** none identified -- epics.md's Story 1.10 AC, AD-13, and AD-25 fully specify this
work.

**Never:** Build Story 2.1's `CfeResult`, the CFE script-invocation adapter table, or a typed
timeout error -- this story ships only the low-level STREAM primitive; Story 2.1 wraps/consumes
it. Add a shared `utils`/`helpers` module for `engines/*` to import from -- forbidden by the
Consistency Conventions; Epic 3 mirrors this pattern independently. Wire `--cfe-timeout`'s
resolved value into any subprocess call -- nothing calls a CFE script yet; this story only adds
the flag/env/resolver, mirroring how `--cfe-root`/`--cfe-python` were accepted-but-unconsumed
until Stories 1.5/1.6/1.8. Add a runtime log-filtering mechanism against environment values --
nothing logs anything yet; the guarantee is proven with a regression test, not a speculative
filter.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--cfe-timeout` flag given | `--cfe-timeout 30` | resolves to `30.0` | non-numeric value is argparse usage error |
| `MASON_CFE_TIMEOUT` set, no flag | env `MASON_CFE_TIMEOUT=45` | resolves to `45.0` | malformed env value resolves to `None` |
| Neither given | no flag, no env | resolves to `None` | none -- per-operation default lives at the future call site |
| `--verbose` given | any command | root logger level `INFO`; stderr receives records | none |
| `--quiet` given | any command | root logger level `ERROR` | none |
| Both given | `--verbose --quiet` | `--quiet` wins (`ERROR`) | none |
| `run_streamed` on a script that writes stderr, sleeps, writes again | child process | each line reaches the sink before the child exits (proven via a sync event) | none |
| `run_streamed` on a script writing both streams | child process | returned `stdout` is only the child's stdout; Mason's real `sys.stdout` untouched | none |
| `run_streamed` exceeds `timeout` | slow child | child killed, `subprocess.TimeoutExpired` propagates | no orphaned process |
| Distinctive env-var value set, `--verbose` on | `MASON_CFE_ROOT=<marker>` | marker never appears in captured stderr | doctor's stdout report may still show it -- only log records are constrained |

</intent-contract>

## Code Map

- `src/pyforge/mason/cli.py` -- add `_ENV_CFE_TIMEOUT`, the `--cfe-timeout` flag,
  `_resolve_optional_float`, `_configure_logging`, call it in `main()` right after `parse_args`.
- `src/pyforge/mason/cfe.py` -- add `run_streamed` (STREAM-mode primitive): `subprocess.Popen` +
  a stderr-forwarding thread + a stdout-capturing thread, mandatory timeout, kill-on-timeout.
- `tests/meta/test_no_config_file.py` (new) -- AD-13 meta-test: no module under
  `src/pyforge/mason/` imports a config-file parser (`configparser`, `tomllib`, `tomli`, `yaml`,
  `ruamel.yaml`).
- `tests/unit/test_cli.py` (extend) -- `TestResolveOptionalFloat`, the six-knob flag+env
  enumeration test, `_configure_logging` level tests, the env-value-never-in-stderr test.
- `tests/unit/test_cfe.py` (extend) -- `run_streamed`'s streaming/isolation/timeout/default-sink
  tests against real `sys.executable` child processes (mirrors the existing real-subprocess
  precedent already in this file).

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/cli.py` -- add `_ENV_CFE_TIMEOUT = "MASON_CFE_TIMEOUT"` and `--cfe-timeout`
  (`type=float`, `default=argparse.SUPPRESS`) on the global-flags parser -- AD-13/FR-48.
- [x] `src/pyforge/mason/cli.py` -- add `_resolve_optional_float(flag_value: float | None,
  env_var_name: str) -> float | None`: flag → environment (parsed; malformed → absent) → `None`
  -- AD-13/FR-4.
- [x] `src/pyforge/mason/cli.py` -- add `_configure_logging(verbose: bool, quiet: bool) -> None`
  (`logging.basicConfig(stream=sys.stderr, level=..., force=True)`) and call it in `main()`
  immediately after `parser.parse_args(argv)` -- FR-49/NFR-2.
- [x] `src/pyforge/mason/cfe.py` -- add `run_streamed(argv, *, timeout, env=None,
  stderr_sink=None) -> tuple[int, str]` -- AD-25.
- [x] `tests/meta/test_no_config_file.py` -- AD-13 meta-test + a tmp_path positive/negative
  regression fixture pair, mirroring `test_dependency_direction.py`'s rigor.
- [x] `tests/unit/test_cli.py` -- cover the I/O matrix's config-knob and logging rows plus the
  env-value-leak regression test.
- [x] `tests/unit/test_cfe.py` -- cover the I/O matrix's `run_streamed` rows.

**Acceptance Criteria:**
- Given the v1 knob set, when each is exercised, then all six work in both flag and environment
  forms with flag→environment→default precedence, and one test asserts this for all six.
- Given AD-13, when the codebase is scanned, then no module imports a config-file parser.
- Given the logging subsystem, when any command runs at any verbosity, then all log records go to
  stderr via stdlib `logging`, and no record contains an environment-variable value.
- Given a delegated operation exceeding a few seconds, when it runs via `run_streamed`, then child
  stderr reaches the sink as produced, not buffered to completion.
- Given a streaming `run_streamed` call, when it completes, then Mason's own stdout is untouched.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10 (medium: 5, low: 5)
- defer: 0
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found `run_streamed`'s
    reader threads had no exception handling: a child emitting a byte sequence not valid under the
    platform's default text encoding crashes the reader thread silently, and `Thread.join()` never
    surfaces that -- the function returns normally with truncated/empty output and no signal
    anything was lost. Added `errors="replace"` to the `Popen(..., text=True, ...)` call so
    non-decodable bytes degrade to replacement characters instead of crashing the thread outright.
  - `[medium]` `[patch]` Both reviewers independently found the final `stderr_thread.join()`/
    `stdout_thread.join()` in `run_streamed`'s `finally` block had no timeout: if the child spawned
    a grandchild that inherited the pipe file descriptors (common for build tooling that shells out
    further), the pipes never see EOF after the direct child is killed, and the reader threads --
    thus `run_streamed` -- hang indefinitely. Added `_JOIN_GRACE_SECONDS = 5.0` and bounded both
    joins with it, degrading to "return what was captured so far" rather than an unbounded hang,
    matching this file's existing `probe_import_floor` precedent of returning a best-effort result
    over raising a new error type for a rare edge case.
  - `[medium]` `[patch]` Both reviewers independently found `_resolve_optional_float` and the
    `--cfe-timeout` flag accept `nan`/`inf`/`-inf` as well-formed (`float()` parses them), which
    would silently defeat a mandatory subprocess timeout downstream (`nan` never compares as
    expired; `inf` never expires at all) despite superficially "having a timeout." Added
    `_parse_finite_float` as the flag's `type=` callable (raises `argparse.ArgumentTypeError`,
    matching the existing non-numeric-value usage-error path) and an `math.isfinite` guard in
    `_resolve_optional_float`'s env-parsing branch (falls back to `None`, matching the existing
    malformed-value convention).
  - `[medium]` `[patch]` Edge Case Hunter found only `subprocess.TimeoutExpired` triggered
    `proc.kill()` in `run_streamed` -- any other exception escaping `proc.wait()` (notably a
    `KeyboardInterrupt` from a user's Ctrl-C) left the child orphaned, so the "no orphaned process"
    guarantee only actually held for the timeout path. Changed the `except subprocess.TimeoutExpired`
    clause to `except BaseException`, so the child is always killed and reaped before any exception
    propagates, not only a timeout.
  - `[low]` `[patch]` Edge Case Hunter found `run_streamed(argv: Sequence[str], ...)` accepts a bare
    `str` unguarded by the type system alone -- `list("mason build")` would explode into
    single-character argv elements, producing a confusing `FileNotFoundError` instead of a clear
    error. Added an `isinstance(argv, (str, bytes))` guard raising `TypeError` immediately.
  - `[low]` `[patch]` Blind Hunter found no test exercised `run_streamed` against a failing (non-zero
    exit) child -- every existing test's child exits 0, leaving half the declared return contract
    (`returncode`) unproven on the failure path. Added
    `test_run_streamed_propagates_a_nonzero_child_returncode`.
  - `[low]` `[patch]` Blind Hunter found `env=`'s replace-vs-merge semantics were untested and
    undocumented -- a future caller (Story 2.1's adapter) could plausibly expect it to merge with
    the inherited environment when `Popen` actually replaces it wholesale. Added
    `test_run_streamed_env_replaces_not_merges_the_inherited_environment` and a docstring note.
  - `[low]` `[patch]` Blind Hunter found `_configure_logging`'s docstring and its `main()` call-site
    comment overclaimed coverage of "a usage error" -- true only for the custom bare-noun usage
    error; an argparse-raised usage error (bad `--format` choice, non-numeric `--cfe-timeout`)
    raises `SystemExit` before `_configure_logging` is ever reached. Tightened both to name exactly
    which usage-error path is and isn't covered, and why today's gap is harmless.
  - `[low]` `[patch]` Blind Hunter found `test_cfe_timeout_flag_rejects_a_non_numeric_value` declared
    an unused `capsys` fixture parameter. Put it to use: asserts `--cfe-timeout` appears in the
    printed usage error.
  - `[low]` `[patch]` Blind Hunter found `run_streamed`'s docstring overstated parity with
    `subprocess.run(capture_output=True)`, which returns both streams, while `run_streamed` returns
    only stdout (stderr is forwarded live and gone, by STREAM-mode design -- see the first rejected
    finding below). Reworded the docstring to state precisely what is and isn't captured, and that a
    caller wanting STREAM-mode stderr content must supply a retaining `stderr_sink`.
- Rejected findings (3): Blind Hunter's request that `run_streamed` capture and return the child's
  stderr text (for a future `CfeResult`-style contract) -- AD-25 explicitly defines STREAM mode as
  forward-only, distinct from and never blended with CAPTURE mode ("streams or is captured, never
  both"), and this story's own Never boundary explicitly excludes building `CfeResult`; a future
  caller wanting retained stderr supplies a sink that itself retains what it's given. Blind Hunter's
  finding that carriage-return-only (`\r`) progress output won't stream live under the current
  newline-iterating reader -- out of scope: this story's ACs and I/O matrix only require `\n`-line
  streaming (matching every existing convention in this codebase, including the CFE fixture stubs'
  own newline-terminated output), no real caller exists yet to need `\r`-aware reading, and building
  it now would be speculative generality for a hypothetical future consumer rather than the actual
  next one (Story 2.1's CFE scripts, which emit `\n`-terminated JSON/progress lines). Blind Hunter's
  finding that the env-value-leak regression test is currently "vacuous" since nothing logs anything
  yet -- this is the spec's own explicit, documented choice (Never boundary: "the guarantee is
  proven with a regression test, not a speculative filter"), not a defect; the test provides real
  regression protection the moment a future story adds a `logging` call near an environment read.

### 2026-08-10 — Review pass (verification-repair resume)
- intent_gap: 0
- bad_spec: 0
- patch: 12 (medium: 4, low: 8)
- defer: 1
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` Both reviewers independently found `run_streamed`'s reader threads had no
    exception handling: a broken/closed `stderr_sink` (or similarly rare stream failure) crashed the
    daemon thread silently via Python's default excepthook, degrading nothing gracefully. Wrapped
    `_forward_stderr`'s loop and `_capture_stdout`'s read in `try/except Exception: pass`, matching
    this file's existing best-effort-degrade philosophy, and added
    `test_run_streamed_survives_a_broken_stderr_sink`.
  - `[medium]` `[patch]` Both reviewers independently found `--cfe-timeout`/`MASON_CFE_TIMEOUT`
    accepted zero and negative values as well-formed, which are exactly as unusable as `nan`/`inf`
    (rejected in the prior pass) via the opposite failure mode: they expire before the delegated
    operation has any chance to run. Extended `_parse_finite_float`'s and `_resolve_optional_float`'s
    guards to also reject `value <= 0`, and added parametrized coverage at both the flag and env
    layers.
  - `[medium]` `[patch]` Edge Case Hunter found `run_streamed`'s own `timeout` parameter was
    unvalidated -- a caller invoking it directly (bypassing `cli.py`'s argparse layer entirely, e.g.
    a future `engines/*` mirror) could pass `nan`/`inf`/zero/negative and silently defeat the
    "no orphaned process, never silently hung" guarantee the function exists to provide. Added the
    same finite-and-positive guard directly inside `run_streamed`, independent of the CLI layer, plus
    `test_run_streamed_rejects_a_non_finite_or_non_positive_timeout`.
  - `[medium]` `[patch]` Blind Hunter found `run_streamed` did not isolate the child's `stdin`, so it
    inherited Mason's own -- a delegated operation that unexpectedly prompts for input would hang
    indefinitely on a stream nothing feeds in a non-interactive context, reproducing the exact
    "silently hung" failure mode this primitive exists to prevent on stderr. Added
    `stdin=subprocess.DEVNULL` and `test_run_streamed_child_stdin_is_not_inherited`.
  - `[low]` `[patch]` Edge Case Hunter found `argv=[]` passed the bare-`str`/`bytes` guard but exploded
    `Popen([])` into an unhelpful `IndexError` rather than naming the mistake. Added an explicit
    empty-sequence check raising `ValueError`, plus `test_run_streamed_rejects_an_empty_argv`.
  - `[low]` `[patch]` Edge Case Hunter found a rare edge case (a child that spawns a grandchild
    inheriting the pipe file descriptors) where the bounded `_JOIN_GRACE_SECONDS` join expires while a
    reader thread's single blocking read call never returns -- `run_streamed` then returns silently
    with `stdout=""` (not a true partial capture) and the stderr-forwarding thread keeps running in
    the background past the function's own return, contradicting the docstring's "return with
    whatever was captured so far" claim. Reworded `_JOIN_GRACE_SECONDS`'s docstring to state this
    honestly rather than overclaim a full best-effort partial-capture guarantee; no behavior change
    (a proper fix needs a chunked/non-blocking read redesign, out of scope for this repair pass).
  - `[low]` `[patch]` Blind Hunter found `cfe.py` imported `Mapping`/`Sequence` from `typing` while the
    sibling `resolve.py` in the same package already imports `Mapping` from `collections.abc` (the
    modern/PEP 585 source) -- an inconsistency within the very file whose own docstring cites
    `resolve.py` as precedent. Moved both imports to `collections.abc`, keeping `TextIO` (not in
    `collections.abc`) under `typing`.
  - `[low]` `[patch]` Blind Hunter found `run_streamed`'s docstring never warned that `env=` *replaces*
    the child's environment wholesale rather than merging -- a partial `env={...}` dict silently strips
    `PATH`, producing a child that cannot itself shell out to anything, likely surfacing as a confusing
    `FileNotFoundError` rather than an obvious "you forgot PATH" signal. Added a docstring paragraph
    stating this explicitly (the existing test already proves the replace-not-merge behavior; only the
    docstring was missing the caveat).
  - `[low]` `[patch]` Blind Hunter found the reader-thread joins' documented rationale didn't state the
    compound wall-clock consequence: two sequential bounded joins mean `run_streamed`'s real worst-case
    bound is `timeout` (or however long `kill()`+`wait()` take) plus up to `2 * _JOIN_GRACE_SECONDS`,
    never stated as part of the function's contract. Added that bound explicitly to the docstring.
  - `[low]` `[patch]` Blind Hunter found the new AD-13 meta-test bans `tomllib`/`tomli` unconditionally,
    while AD-13's own text carves out one sanctioned exception ("Mason reads no key from
    `pyproject.toml` other than the packaging metadata it is asked to build") the guard does not yet
    encode. No current code path reads a target package's `pyproject.toml` (Story 1.10's Never
    boundary: nothing delegates to a build yet), so the unconditional ban is correct today; added a
    docstring note stating the carve-out is deliberately unencoded and that a future story needing it
    must extend this guard rather than rediscover the gap as a test failure.
  - `[low]` `[patch]` Edge Case Hunter found `_matches_banned`'s `ast.ImportFrom` branch didn't check
    `node.level`, so a relative import of a local module happening to share a banned name (e.g. a
    hypothetical `from .yaml import X` inside a future `mason/yaml.py`) would false-positive as the
    third-party `yaml` package. Added a `node.level == 0` guard (absolute imports only) plus
    `test_detector_permits_a_relative_import_of_a_local_module_with_the_same_name`.
  - `[low]` `[patch]` Edge Case Hunter found the existing `-inf`/`nan` parametrized `--cfe-timeout`
    test passed for the wrong reason for the `-inf` case: as a separate argv token, `-inf` looks like
    another option string to argparse's own parser, which raises its own "expected one argument"
    error *before* `_parse_finite_float` ever runs -- both paths exit 2 with `--cfe-timeout` in the
    message, so the test didn't actually prove the isfinite guard rejects `-inf`. Removed `-inf` from
    the two-token parametrize list and added a dedicated
    `test_cfe_timeout_flag_rejects_negative_infinity_via_equals_form` using the `--cfe-timeout=-inf`
    single-token form, which genuinely reaches the custom validator.
- Rejected findings (4): Blind Hunter's finding that `--cfe-timeout`'s resolved value is never
  consumed by any subprocess call -- explicitly scoped out by this story's own Never boundary
  ("nothing calls a CFE script yet; this story only adds the flag/env/resolver"), mirroring how
  `--cfe-root`/`--cfe-python` were accepted-but-unconsumed until later stories. Blind Hunter's
  re-finding that the env-value-leak regression test is "vacuous" since nothing logs anything yet --
  identical to a finding already rejected in the 2026-08-09 pass above, same reasoning (this review
  ran with no prior-pass context, so it independently rediscovered the same non-defect). Blind
  Hunter's finding that `--verbose`/`--quiet` given together is "silently" resolved rather than
  rejected -- this is the spec's own documented tie-break (Boundaries & Constraints: "`--quiet` wins
  when both `--verbose` and `--quiet` are given"), not a defect. Blind Hunter's finding that the
  memlog's "S-13.7's guard is gating for this Spec right now" claim is "unverifiable" from the diff
  alone -- independently confirmed true by the orchestrator during this same session (the baseline
  re-stamp that fixed the original verification failure is direct proof the guard is live and gating
  for this spec).

### 2026-08-10 — Review pass (third, fresh no-context reviewers)
- intent_gap: 0
- bad_spec: 0
- patch: 15 (high: 1, medium: 3, low: 11)
- defer: 4 (1 already on the ledger from the pass above, not re-appended)
- reject: 7
- addressed_findings:
  - `[high]` `[patch]` Both reviewers independently found — and Blind Hunter reproduced — that a
    failing `stderr_sink` **deadlocks the child**. The pass above wrapped `_forward_stderr`'s entire
    read loop in `except Exception: pass` to stop a broken sink crashing the daemon thread; that fix
    made the reader *abandon the pipe* on the first sink failure, so nothing drained the child's
    stderr, the ~64KB OS pipe buffer filled, the child blocked forever on its next write, and
    `timeout` eventually SIGKILLed a perfectly healthy process — the exact failure mode this
    primitive exists to prevent, reachable from something as ordinary as `mason ... 2>&1 | head -5`
    (`BrokenPipeError` on every sink write). Verified against the committed code: `TimeoutExpired`
    at exactly 5.00s on a child that finishes instantly. Fixed by keeping the reader draining to EOF
    and discarding what it can no longer deliver (one failed write marks the sink dead; the loop
    continues), with the same keep-draining discipline applied to `_capture_stdout`. Pinned by
    `test_run_streamed_broken_stderr_sink_does_not_deadlock_a_noisy_child` (20,000-line child),
    mutation-verified: it fails against the pre-fix reader at 20s while the existing single-line
    `test_run_streamed_survives_a_broken_stderr_sink` still passes — which is exactly why two prior
    passes certified this path as sound.
  - `[medium]` `[patch]` Blind Hunter found `run_streamed` never closes the child's pipes (`Popen`
    is not used as a context manager, because the reader threads outlive any `with` block), leaking
    two file descriptors per call until the GC runs: 18 `ResourceWarning: unclosed file` across the
    suite under `-W error::ResourceWarning`. Added an explicit close of both streams after the
    bounded joins; the suite now runs clean under `-W error::ResourceWarning` (329 passed, 0
    warnings).
  - `[medium]` `[patch]` Blind Hunter and Edge Case Hunter both found `_resolve_optional_float`
    validates its *environment* half but returns its *flag* half unchecked, so `nan`/`inf`/`0`/
    negative pass straight through — the resolver hands callers exactly the value
    `_parse_finite_float` and `run_streamed` both reject as unusable, and a test
    (`test_zero_flag_value_still_wins_over_env`) had locked in the stale "`0.0` is a valid timeout"
    premise the same diff contradicts twice over. Applied the identical finite-and-positive guard to
    the flag path, with fall-through to the environment rather than short-circuiting to `None` —
    matching `_resolve_str`'s documented "absent at whichever step supplied it" rule. Replaced the
    stale test with a valid-unusual-value case plus parametrized fall-through/`None` coverage.
  - `[medium]` `[patch]` Edge Case Hunter found a `Thread.start()` failure (thread exhaustion) after
    `Popen` succeeded orphans the child, since the kill-and-reap handler only wrapped `proc.wait()`.
    Moved both `.start()` calls inside the guarded block and made the join step skip a thread that
    never started, so the documented "no orphaned process for every exit from this function"
    guarantee is now true for the spawn path too.
  - `[low]` `[patch]` Blind Hunter found `argparse` leaks the private validator's name into
    user-facing output — `mason --cfe-timeout 30s` printed `invalid _parse_finite_float value:
    '30s'`, because the bare `ValueError` from `float()` escaped and argparse fell back to
    `type_func.__name__`. Wrapped the parse in `ArgumentTypeError`; the test now asserts
    `_parse_finite_float` does *not* appear and the real wording does.
  - `[low]` `[patch]` Edge Case Hunter found the AD-13 guard misses `from ruamel import yaml` — the
    banned dotted name split across the import's two halves, so matching `node.module` alone
    ("ruamel") waves through the single most natural way to import it. Added a recheck joining each
    bound name onto the module path, plus regression cases for both the catch and the innocent
    `from json import loads` shape.
  - `[low]` `[patch]` Blind Hunter found the AD-13 ban list omits the most probable offenders —
    `toml`, `tomlkit`, `configobj`, `dotenv` all sailed through the detector (verified against
    synthetic trees). Extended `_BANNED_MODULES` and the parametrized regression list.
  - `[low]` `[patch]` Blind Hunter found the guard's docstring claims package-wide coverage while
    the scanner is blind to dynamic imports (`importlib.import_module("yaml")` — this codebase's own
    idiom in `_build_probe_script`) and hand-rolled `open()`-based parsers. No behavior change
    (a static AST guard cannot honestly cover those); the docstring now states the gap outright so a
    future story does not mistake the guard's silence for proof.
  - `[low]` `[patch]` Edge Case Hunter found a UTF-8 BOM makes the guard fail a valid, importable
    module as "invalid Python syntax" (CPython strips the BOM; `ast.parse` on the decoded string does
    not). Switched to `utf-8-sig` and added a regression test proving both that a BOM'd clean file
    passes and that a BOM cannot hide a real violation.
  - `[low]` `[patch]` Edge Case Hunter found `run_streamed(timeout=None)` raises a bare "must be real
    number, not NoneType" from `math.isfinite`, naming neither the function nor the parameter —
    `None` being the likely mistake, since it means "wait forever" to subprocess's own API. Added an
    isinstance guard ahead of the finite check, plus parametrized coverage.
  - `[low]` `[patch]` Blind Hunter found `cli.py` is now the only module in the package still
    importing `Sequence` from `typing` — the pass above moved exactly this to `collections.abc` in
    `cfe.py` and left the sibling file the same story touched. Moved it.
  - `[low]` `[patch]` Blind Hunter found the orphan-kill test asserts only `elapsed < 10.0`, which
    the un-killed mutant clears by 0.3s and only because `2 * _JOIN_GRACE_SECONDS` caps it — so
    retuning that constant below 5.0 would let a genuinely orphaned 30-second child pass green.
    Tightened to `< 3.0` (a killed child releases its pipes at once; the real figure is ~0.4s).
  - `[low]` `[patch]` Both reviewers found the live-streaming test has a ~1s race: it reads the sink
    from the main thread after waiting on an Event, so any pause longer than the child's sleep
    between the Event firing and the assertion running fails a correct run. Replaced with an arrival
    timestamp captured inside the sink, so the proof no longer depends on main-thread scheduling.
  - `[low]` `[patch]` Blind Hunter and Edge Case Hunter both found `_configure_logging`'s
    spec-mandated `force=True` removes pytest's own `caplog` handler — verified: a test that calls
    `main()` then asserts on `caplog.text` fails on an empty string — and leaks the root logger's
    level plus a handler bound to a torn-down capture buffer into every later test. Added an autouse
    `_restore_root_logging` fixture to `tests/conftest.py` (fences the cross-test leak) and
    documented the intra-test `caplog` interaction in `_configure_logging`'s docstring, since
    `force=True` itself is the spec's Design Notes decision and stays.
  - `[low]` `[patch]` Edge Case Hunter found the `--quiet`-wins tie-break is applied to *resolved*
    values, so `MASON_QUIET=1` in a shell profile silently mutes an explicit `--verbose` on the
    command line. This follows from AD-13's per-knob precedence rather than contradicting it, so
    behavior is unchanged — documented in the docstring and pinned by a test, rather than left to be
    rediscovered.
- Deferred (4): unbounded in-memory stdout capture in a primitive whose docstring names multi-minute
  builds as its callers; `TimeoutExpired` discarding all stdout captured before the deadline (unlike
  `subprocess.run` and this file's own `probe_import_floor` precedent); a `Popen` spawn failure
  escaping raw to `main()`'s bare-`Exception` traceback boundary instead of an AD-7 anticipated
  failure. All three are unreachable today (no production caller) and all three resolve into Story
  2.1's `CfeResult`/error contract, which this story's Never boundary excludes. The fourth —
  `test-architecture.md`'s `--format json` streaming-integration row — was already appended to the
  ledger by the pass above and was left untouched rather than duplicated.
- Rejected findings (7): `--cfe-timeout` being parsed but consumed by no production code path —
  explicitly scoped out by the Never boundary, third independent rediscovery. The env-value-leak
  regression test being "vacuous" because nothing logs yet — the spec's own documented choice
  ("proven with a regression test, not a speculative filter"), third rediscovery. A malformed or
  non-positive `MASON_CFE_TIMEOUT` degrading silently to `None` while the flag form hard-errors —
  the I/O matrix specifies exactly this ("malformed env value resolves to `None`"), and it matches
  `_resolve_str`'s treatment of the environment as a best-effort source. Verbosity being applied to
  the root logger rather than a `pyforge.mason` logger (raising third-party INFO records under
  `--verbose`) — the I/O matrix says "root logger level `INFO`" verbatim, and no third-party logging
  dependency exists; revisit if Story 2.1 adds one. A test monkeypatching `cfe_module.subprocess`
  (which is the stdlib module object, so the patch is process-wide) — `monkeypatch` restores it at
  teardown and nothing else in this suite spawns concurrently. A non-`str` `argv` element producing
  a confusing error — `Popen`'s own "expected str, bytes or os.PathLike object, not int" already
  names the mistake adequately. Blind Hunter's request to bound stdout in memory was split: the
  claim is real and was deferred rather than rejected (see above), only its framing as a defect in
  this story's delivered scope was not accepted.

### 2026-08-10 — Review pass (fourth, fresh no-context reviewers)
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high: 1, medium: 2, low: 9)
- defer: 1 (plus 1 already on the ledger from an earlier pass, not re-appended)
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` Both reviewers independently reproduced — and both mutation-verified — that the
    pass above's fd-leak fix **reintroduced an unbounded hang**, for the second consecutive pass in
    which a fix for a real bug created a worse one. That pass closed both child pipes after the
    bounded reader joins; `close()` acquires the `BufferedReader` lock a still-blocked reader holds,
    so in exactly the grandchild-holds-the-pipe scenario `_JOIN_GRACE_SECONDS` exists for, the close
    waited for the same EOF the bounded join had just given up on. Measured at 45.02s and 40.03s
    against documented bounds of 10s and 12s; on the timeout path `subprocess.TimeoutExpired` never
    propagated at all, so a `mason recipe build` whose CFE script shells out to `rattler-build`
    would hang forever instead of timing out. Removing only the close loop returned at 10.03s,
    exactly as documented. Fixed by closing each pipe only once *its own* reader has joined, leaking
    the descriptor to the daemon reader in that rare already-degraded path — strictly better than
    never returning. Pinned by `test_run_streamed_returns_promptly_when_a_grandchild_holds_the_pipes`,
    mutation-verified to fail at 20s against the pre-fix code.
  - `[medium]` `[patch]` Both reviewers mutation-verified that `test_run_streamed_closes_both_child_pipes`
    — the sole guard on the change that introduced the deadlock above — **could not fail**: it passed
    with the entire close loop deleted. `ResourceWarning` is emitted by the GC when the
    `TextIOWrapper` is finalized, after `warnings.catch_warnings()` has exited and never while the
    `Popen` is still referenced, and arrives as an *unraisable* exception that pytest downgrades to a
    non-fatal `PytestUnraisableExceptionWarning`. Rewritten to assert `proc.stdout.closed` /
    `proc.stderr.closed` directly via a capturing `Popen`; now fails against the mutant.
  - `[medium]` `[patch]` Edge Case Hunter found the sink-dead latch added by the pass above is a
    one-way trip taken on *any* exception from write **or flush** — so a sink with no `flush` method
    (a hand-rolled tee, which the docstring explicitly invites) raised `AttributeError` on line 1 and
    silently dropped the other 4 of 5, and a single transient `BlockingIOError` on flush did the
    same. `flush` is now resolved once via `getattr` and never fatal; only a failed *write* latches,
    which still covers the `| head -5` `BrokenPipeError` case the latch exists for (its next write
    fails too). Two regression tests added.
  - `[low]` `[patch]` Both reviewers found a generator `argv` bypasses the non-empty guard entirely —
    `not argv` is always `False` for a non-`Sized` iterable, so an exhausted one reached `Popen([])`
    and raised the exact `IndexError` the guard was added to replace. `argv` is materialized once,
    before both guards; tests cover the empty generator and a valid one.
  - `[low]` `[patch]` Edge Case Hunter found `_resolve_optional_float` returns a `bool` verbatim:
    `bool` subclasses `int`, so `True` clears both `math.isfinite` and `> 0`. That is precisely the
    resolver-vs-consumer disagreement the pass above claimed to have closed — `run_streamed` rejects
    a bool `timeout` outright. Added the same `isinstance(..., bool)` rejection `run_streamed`
    already applies.
  - `[low]` `[patch]` Blind Hunter found the `--cfe-timeout` rejection tests assert only exit code 2
    plus the flag name — the identical weak pair the *previous* pass identified as unable to
    distinguish argparse's own "expected one argument" from the validator's rejection, fixed for
    `-inf` and left in place for `0`/`-1`/`-0.5`/`nan`/`inf`. All three tests now assert the
    validator's real wording.
  - `[low]` `[patch]` Blind Hunter found the "no orphaned process survives any exit from this
    function" guarantee overclaims: `proc.kill()` signals the direct child, not its process group, so
    a grandchild survives — which is not a footnote here, it is the mechanism of the high-severity
    finding above. Docstring now states what is actually guaranteed.
  - `[low]` `[patch]` Blind Hunter found the `bufsize=1` comment ("line-buffered: each child stderr
    line is readable as soon as it is written") is factually wrong for read pipes — `subprocess`
    applies line buffering only to *writable* text wrappers, and both of these come back
    `line_buffering=False`. Live streaming works via `readline()` regardless. Corrected, with a note
    not to reach for this parameter to tune streaming latency.
  - `[low]` `[patch]` Blind Hunter found `_capture_stdout`'s fallback drain claims to preserve the
    keep-draining anti-deadlock discipline but is a no-op in the only state that reaches it: if
    `read()` raised because the stream is closed or broken, the fallback iteration raises identically
    on its first step. Comment corrected to describe it as best-effort, not as anti-deadlock
    protection.
  - `[low]` `[patch]` Both reviewers found `basicConfig(force=True)` *closes* every root handler it
    removes rather than merely detaching it, which is not undoable. Two documented consequences: a
    write-mode `FileHandler` (what `pytest --log-file` installs) stays dead and silently drops every
    later record, and `main()` — importable, and the declared console-script entry point — destroys
    the root logging of any host that calls it in-process. `force=True` itself is the spec's Design
    Notes decision and stays (Mason's real consumer gets a fresh process per invocation); both
    consequences are now stated in `_configure_logging`'s docstring.
  - `[low]` `[patch]` Edge Case Hunter found the companion gap in `tests/conftest.py`'s
    `_restore_root_logging`: it re-adds handlers `basicConfig` has already closed, restoring
    membership but not function. Harmless for the handlers that actually appear (pytest's `caplog`
    wraps a `StringIO` whose `close()` is a no-op), real under `--log-file`. Documented in the
    fixture's docstring, which previously claimed to contain the side effects outright.
  - `[low]` `[patch]` Blind Hunter found the AD-13 guard's honestly-stated gap list omits its most
    plausible hole: `json` cannot be banned because `render.py` already imports it legitimately, so a
    `~/.mason.json` reader would pass the scan unremarked. Added to the documented gaps.
- Deferred (1 new): the grandchild-degraded path now deliberately leaves a pipe open and its daemon
  reader blocked past return — two leaked descriptors and a live thread per occurrence — because
  closing it deadlocks the caller. That, and the already-logged "no true partial capture" limitation,
  dissolve together only under a chunked/non-blocking reader redesign, which wants Story 2.1's real
  caller to size it against. The `test-architecture.md` `--format json` streaming-integration row was
  already on the ledger from an earlier pass and was left untouched rather than duplicated.
- Rejected findings (5): `--cfe-timeout` being parsed but consumed by no production code path —
  fourth independent rediscovery, explicitly scoped out by the frozen Never boundary. The
  env-value-leak regression test being "vacuous" because nothing logs yet, and the logging ACs being
  exercised only by synthetic loggers — same root, fourth rediscovery, and the spec's own documented
  choice ("proven with a regression test, not a speculative filter"). The live-streaming test's ~2s
  budget including interpreter cold-start — Edge Case Hunter's only unreproduced finding, and the
  docstring already states the framing is deliberately strict; the residual margin is ample. A
  non-`str` `argv` element producing a confusing error — `Popen`'s own message already names it.
- Verification: 336 passed (329 → 336), and still zero warnings under `-W error::ResourceWarning`.
  Every one of the five behavioral fixes was mutation-verified: reverting each in a scratch copy
  fails its guard (the deadlock guard at 20s), so no new test in this pass is one that cannot fail —
  which is the specific failure mode that let the last two passes ship regressions.

### 2026-08-10 — Review pass (fifth, fresh no-context reviewers)
- intent_gap: 0
- bad_spec: 0
- patch: 10 (medium: 4, low: 6)
- defer: 0
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` Both reviewers independently reproduced that `run_streamed` does not
    actually stream stderr *as produced* — it streamed it *per newline*. `_forward_stderr` iterated
    the text wrapper (`for line in proc.stderr`), which blocks until it sees `\n`, so a child that
    writes a status line **without** a terminator and then works silently — a spinner, a progress
    bar, `Building... ` before a long compile — delivered nothing at all for the whole pause.
    Measured: 200 bytes written at t=0 first reached the sink at t=3.01s, together with the
    terminator that finally released them. That is the "buffered to completion" behavior AD-25
    forbids and this primitive exists to prevent, and it is the story's own AC ("child stderr
    reaches the sink as produced, not buffered to completion") rather than a speculative extension
    of it. Structurally invisible to the suite because every existing streaming test's child uses
    `print(..., file=sys.stderr)`, which always terminates its line. Fixed by reading the raw pipe
    in chunks (`BufferedReader.read1`) with an incremental UTF-8 decoder — a strict latency
    improvement over `readline()` with identical blocking semantics, so neither historic deadlock
    path changes. Pinned by `test_run_streamed_forwards_stderr_without_waiting_for_a_line_terminator`,
    mutation-verified against the pre-fix line iterator.
    *Distinct from the `\r`-live-streaming finding rejected in the first pass:* that one asked for
    `\r`-aware **line splitting** as a new feature; this is any terminator-free output being held,
    which the AC already requires.
  - `[medium]` `[patch]` Blind Hunter reproduced that `Popen` pinned no `encoding`, so the child's
    output was decoded with the **caller's** locale encoding. Under `LC_ALL=C` — routine in CI
    containers, cron, and `docker run` without `LANG` — a valid UTF-8 JSON document came back with
    every non-ASCII byte replaced (`café` → `caf��`) and **still parsed as JSON**, so Story
    2.1's AD-4 extraction would return a quietly wrong answer rather than an error. `errors="replace"`
    (added in an earlier pass to stop a decode crash) is what makes the corruption silent. Pinned
    `encoding="utf-8"`; the same chunked reader above decodes stderr identically. Pinned by
    `test_run_streamed_decodes_utf8_regardless_of_the_ambient_locale`, which calls `run_streamed`
    from a grandparent interpreter launched under `LC_ALL=C` — setting the *child's* `env=` proves
    nothing, since the decode happens on this side of the pipe.
  - `[medium]` `[patch]` Both reviewers independently reproduced that a single **transient**
    `BlockingIOError` latches the sink permanently dead. `BlockingIOError` means "busy," not "gone" —
    it is what a non-blocking `sys.stderr` under tmux or some CI runners raises when the downstream
    pipe is momentarily full, and the very next write succeeds. Measured: of 5 child stderr lines,
    `write()` was attempted **once** and 0 lines were delivered, with `rc=0` and no diagnostic. The
    adjacent `flush` handler three lines away already reasons the opposite way about the identical
    exception and says so in its comment. `BlockingIOError` now skips that one chunk without
    latching; a genuinely broken sink still latches via its failing write, so the `| head -5`
    `BrokenPipeError` case the latch exists for is unaffected (still pinned by the noisy-child
    deadlock test).
  - `[medium]` `[patch]` Blind Hunter found the AC's own guard for the six-knob configuration
    surface is a `format_help()` **substring match**: it asserts only that six flag names and six
    variable names appear in help output, so it would pass unchanged with `_resolve_optional_float`
    deleted outright, and it proves nothing about the flag → environment → default precedence the AC
    explicitly names. Rewritten to exercise all three resolution steps for each of the six, with each
    knob's environment value chosen so no sub-assertion is vacuous (`--format`, `--verbose` and
    `--quiet` have defaults that are themselves one of only two possible values, so their flag-wins
    case uses an environment value that would produce a *different* answer if the flag were ignored).
    Mutation-verified: neutering `_resolve_optional_float` to `return None` now fails it.
  - `[low]` `[patch]` Both reviewers found `_resolve_optional_float` leaks a bare `TypeError: must be
    real number, not str` for a non-numeric flag value — reaching `math.isfinite` without an
    isinstance check, naming neither the function nor the parameter. This is the exact defect
    `run_streamed`'s own `timeout` guard was given an isinstance check for in an earlier pass; its
    sibling resolver was left without one. A non-number now falls *through* to the environment like
    every other unusable value, keeping the resolver's documented never-raises contract.
  - `[low]` `[patch]` Edge Case Hunter found `run_streamed(argv=None)` reports a bare `'NoneType'
    object is not iterable` from `list(argv)`, naming neither the function nor the parameter — the
    same gap `timeout=None` was already guarded against, and `None` is the likely mistake. Added the
    matching guard.
  - `[low]` `[patch]` Edge Case Hunter found a `stderr_sink` with no callable `write` — or a
    `sys.stderr` that is `None`, which a `pythonw`/detached host supplies — is swallowed silently by
    the forwarding thread's own degrade-don't-crash handling: every line the child produced vanished,
    indistinguishable to the caller from a quiet child. Reproduced. Now rejected up front with a
    `TypeError`, ahead of `Popen` so a caller's mistake costs no child process; `flush` stays
    optional.
  - `[low]` `[patch]` Blind Hunter reproduced that `_configure_logging`'s docstring prescribes a
    remedy that **does not work**: re-entering `caplog.at_level(...)` after a `main()` call cannot
    restore capture, because `at_level` only adjusts levels while `force=True` has *removed and
    closed* the handler. Verified — the assertion sees an empty `caplog.text` while the record is
    plainly on stderr. Story 2.1 adds the package's first real log call and would have followed it.
    Replaced with the remedy that does work (re-attaching `caplog.handler` by hand, verified), plus
    why it works only for handlers `close()` cannot kill.
  - `[low]` `[patch]` Blind Hunter found the AD-13 guard's failure message hand-lists 5 of its 9
    banned modules — the earlier pass that added `toml`/`tomlkit`/`configobj`/`dotenv` to
    `_BANNED_MODULES` left the assertion text behind, so a developer tripping the guard with `import
    dotenv` reads a message that does not mention dotenv and could reasonably conclude it misfired.
    Message now derived from `_BANNED_MODULES`, never re-typed.
  - `[low]` `[patch]` Blind Hunter found text-mode universal-newline translation rewrites every `\r`
    the child emits into `\n`, turning a build tool's single in-place progress line into hundreds of
    scrolling ones. Reproduced. Resolved by the chunked binary reader above (no separate change);
    pinned by `test_run_streamed_preserves_carriage_returns_in_child_stderr`. This is the *content
    corruption* half of the `\r` question, independent of the `\r`-aware-splitting feature request
    the first pass rejected.
- Deferred (0 new): three of this pass's rejections are findings already on the ledger from earlier
  passes — unbounded in-memory stdout capture, and the grandchild-degraded path (which Blind Hunter
  re-framed as `(0, "")` being indistinguishable from a quiet child; the existing entry already names
  the same redesign as its fix and says so). Left untouched rather than duplicated.
- Rejected findings (7): `--cfe-timeout` being parsed but consumed by no production code path —
  fifth independent rediscovery, explicitly scoped out by the frozen Never boundary. The
  env-value-leak regression test being "vacuous" because nothing logs yet — fifth rediscovery, and
  the spec's own documented choice. Unbounded stdout capture, and the grandchild path's silent empty
  return — both already on the ledger (see above). `--quiet` not silencing `run_streamed`'s forwarded
  child stderr — the primitive takes a `stderr_sink`, so a quiet caller supplies a discarding one;
  wiring that is Story 2.1's, excluded by the Never boundary. `run_streamed` having no `cwd`
  parameter — speculative; a keyword-only parameter is a non-breaking addition when Story 2.1's real
  caller needs it. `stderr_sink=sys.stdout` being unguarded against AD-8 — a primitive cannot police
  its caller's stream discipline, and the docstring already states it never writes Mason's stdout.
- Verification: 350 passed (336 → 350), still zero warnings under `-W error::ResourceWarning`, and
  `spec_surface_check` reports `OK: no drift` after the memlog reconciliation and scoped re-stamp.
  All five behavioral fixes were mutation-verified (9 mutations, 9 dead guards). Because the reader
  rewrite touched the code both prior regressions lived in, the two **historic** deadlock guards were
  re-mutated as well: abandon-the-pipe-on-sink-failure still fails the noisy-child test at 20s, and
  an unconditional pipe close still fails the grandchild test — neither healed hole was reopened.

## Design Notes

`_configure_logging` uses `force=True` so repeated `main()` calls within one process (as in the
test suite) reconfigure cleanly rather than no-op behind `logging.basicConfig`'s "only configures
once" default behavior.

`run_streamed` needs two concurrent reader threads, not sequential reads: the child may block on a
full stderr pipe while Mason is still reading stdout (or vice versa) if only one stream is drained
at a time, so both must be drained concurrently while the process is alive. On timeout, `proc.kill()`
+ `proc.wait()` before re-raising guarantees no orphan; the reader threads then hit EOF naturally as
the killed process's pipes close.

`stderr_sink: TextIO | None = None`, resolved to `sys.stderr` *inside* the function body -- a
`= sys.stderr` default parameter would bind the module-import-time stream object, which does not
track `capsys`'s per-test monkeypatching of `sys.stderr`.

`_forward_stderr` reads the *binary* pipe under the text wrapper in chunks and decodes
incrementally, rather than iterating the wrapper's lines (review pass, 2026-08-10, fifth). Line
iteration blocks until `\n`, so terminator-free output -- a spinner, a progress bar, a status line
before a long compile -- was held for as long as the child kept working, which is the very
"buffered to completion" behavior the AC forbids. Reading raw also stops universal-newline
translation from rewriting the child's `\r` into `\n`, and lets the decode encoding be pinned to
UTF-8 instead of inherited from the caller's locale (a `LC_ALL=C` caller silently mangled valid
UTF-8 JSON into replacement characters that still parsed). `read1` blocks exactly as `readline()`
did -- until at least one byte is available -- so the bounded-join and pipe-close lock ordering the
third and fourth passes established is unchanged.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (242 existing + new
  tests), still excludes `slow`.
- `python3 scripts/detectors.py --scope repo` -- expected: `spec_surface_check` passes; other
  detectors' pre-existing branch-staleness findings (if any) are out of scope.

## Auto Run Result

Status: `done` (fifth review pass; implementation was already complete and unchanged in intent).

**Summary.** A fresh no-context adversarial review pass over the whole story diff. No intent gaps
and no spec defects; 10 patch-class findings fixed in place, 0 new deferrals, 7 rejections. The
consequential half of the pass is that `run_streamed` did not deliver its central promise for a
whole class of real child output: stderr was forwarded *per newline*, so terminator-free progress
output (spinners, `\r` progress bars, `Building... ` before a long compile) was held for as long as
the child kept working -- reproduced at 3.01s of total silence for a 3s pause. Fixing the reader to
read raw chunks with an incremental UTF-8 decoder also fixed `\r` being rewritten into `\n` and let
the decode encoding be pinned, closing a silent data-corruption path where a `LC_ALL=C` caller
turned valid UTF-8 JSON into replacement characters that still parsed as JSON.

**Files changed.**
- `src/pyforge/mason/cfe.py` -- chunked, locale-independent stderr forwarding; `encoding="utf-8"`
  pinned on `Popen`; `BlockingIOError` no longer latches the sink dead; `argv=None` and an
  unwritable `stderr_sink` rejected up front; docstrings updated to match.
- `src/pyforge/mason/cli.py` -- `_resolve_optional_float` guards its flag half against non-numbers
  (falls through instead of raising a bare `TypeError`); `_configure_logging`'s docstring no longer
  prescribes a `caplog` remedy that does not work.
- `tests/meta/test_no_config_file.py` -- AD-13 failure message derived from `_BANNED_MODULES`
  instead of hand-listing 5 of 9.
- `tests/unit/test_cli.py` -- the six-knob AC guard rewritten from a `--help` substring match into
  real flag → environment → default coverage; non-numeric flag-value regression cases.
- `tests/unit/test_cfe.py` -- 7 new regression tests for the findings above.
- `planning-artifacts/specs/spec-pyforge-mason/.memlog.md` + `scripts/.spec-surface-baseline.json`
  -- S-13.7 reconciliation for the governed files this pass changed.

**Findings breakdown.** patch 10 (medium 4, low 6) -- all applied; defer 0 new (3 rejections were
findings already on the ledger, left untouched rather than duplicated); reject 7.

**Verification.** `pytest src/shared/packages/pyforge-mason/tests/ -q` → **350 passed** (up from
336); same suite under `-W error::ResourceWarning` → 350 passed, 0 warnings;
`python3 scripts/spec_surface_check.py` → `OK: every tracked file governed or allowlisted; no
drift`. `scripts/detectors.py --scope repo` leaves only `ledger_regression_check` findings for
pyforge-atlas and pyforge-marshal -- other projects' ledger files, untouched by this story and out
of scope per the Verification block above. Every one of the five behavioral fixes was
mutation-verified against the pre-fix code (9 mutations, 9 dead guards), and because the reader
rewrite touched the code both prior regressions lived in, the two historic deadlock guards were
re-mutated too: neither healed hole was reopened.

**Residual risks.**
- The chunked reader is a change to the I/O core of a primitive that regressed in three of the last
  four passes. Every guard is mutation-verified and both historic deadlock guards were re-checked
  against their own mutants, but the base rate is why `followup_review_recommended` stays `true`.
- The `BlockingIOError` path still *drops* the busy chunk rather than retrying (retrying would
  block or spin). Documented in the docstring; a caller needing lossless delivery must supply a
  buffering sink.
- The ledger's open entries against this primitive -- unbounded stdout capture, `TimeoutExpired`
  discarding partial stdout, a raw `Popen` spawn failure, and the grandchild-degraded path's leaked
  descriptor and blocked reader -- are all unchanged and all still resolve into Story 2.1's
  `CfeResult`/error contract, which this story's frozen Never boundary excludes.

