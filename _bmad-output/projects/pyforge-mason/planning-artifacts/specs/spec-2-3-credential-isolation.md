---
title: 'Credential isolation'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: '7d57873e4d4b47f3429d626970c6e309b6a86ffe'
review_loop_iteration: 0
followup_review_recommended: true
final_revision: '79c2c8c8cb'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Nothing mechanically enforces AD-14 (credential blindness): today no module reads a
`JFROG_*` variable or overrides a CFE subprocess's environment, but that is true by accident, not
by a guard — the exact gap Story 2.2's seam-guard precedent exists to close for AD-1/AD-3.

**Approach:** Add a meta-test mirroring `test_no_recipe_knowledge.py`/`test_adapter_sole_caller.py`'s
AST-scan-with-planted-fixture pattern, covering `JFROG_*` string literals, HTTP-client imports, and
non-`None` `env=` overrides on every subprocess/`run_streamed` call site; plus a real-subprocess
sentinel test proving a credential-shaped value never reaches Mason's own captured output.

## Boundaries & Constraints

**Always:** AST-based scanning only (never raw-text regex — matches every sibling meta-test's
documented rationale). Real-tree assertions run against `src/pyforge/mason/`, not a synthetic copy.
Every scanner has at least one planted-violation fixture proving it actually fires, plus one clean
fixture proving it does not false-positive.

**Block If:** N/A — no undecided design choice; the scope is fully determined by FR-6/NFR-2/AD-14
and the current, already-inspected codebase.

**Never:** No production code change is anticipated — investigation confirmed `resolve.py`,
`cli.py`, and `cfe.py` already satisfy AD-14 (only two named `MASON_*` env keys are ever read;
`os.environ` is never rendered or dumped whole). This story adds the mechanical guard, not a fix.
The HTTP-import ban is scoped to *today's* zero-HTTP-usage baseline — Epic 3's ship targets will
need their own (non-CFE) HTTP calls to PyPI/conda channels later and must loosen this guard
explicitly when that story lands; that is expected, not a violation of this one.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean real tree | scan `src/pyforge/mason/` | zero violations across all three guards | N/A |
| Planted `JFROG_*` literal | synthetic module: `os.environ.get("JFROG_API_KEY")` | flagged, naming file/line | N/A |
| Planted HTTP import | synthetic module: `import requests` | flagged, naming file/line | N/A |
| Planted `env=` override | synthetic module: `subprocess.run(x, env={"FOO": "bar"})` | flagged, naming file/line | N/A |
| Allowlisted `env=` site | `cfe.py`'s own `run_streamed`-internal `Popen(..., env=dict(env) if env is not None else None)` | not flagged | N/A |
| Sentinel credential present | `JFROG_API_KEY=<sentinel>` in env; `probe_import_floor`/`validate_recipe`/`submit_pr` run against `fake_cfe_root` | sentinel absent from every `CfeResult` field | N/A |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `tests/meta/test_credential_isolation.py` (new) -- AD-14 guard: three AST scanners (`JFROG_*`
  string literals, HTTP-client imports, non-`None` `env=` overrides) with real-tree assertions and
  planted/clean/allowlist-regression fixtures.
- `tests/unit/test_cfe.py` (edit) -- sentinel-credential test: a `JFROG_API_KEY` sentinel value set
  via `monkeypatch.setenv`, real-subprocess calls to `probe_import_floor`/`validate_recipe`/
  `submit_pr` against the `fake_cfe_root` fixture, asserting the sentinel never appears in any
  `CfeResult` field.
- `tests/unit/test_cli.py` (edit) -- sentinel-credential test at `mason doctor --verbose`, asserting
  the sentinel never appears in `capsys`-captured stdout/stderr.

## Tasks & Acceptance

**Execution:**
- [x] `tests/meta/test_credential_isolation.py` (new) -- **Guard 1 (env-var name):** AST walk over
  every `.py` file under `src/pyforge/mason/` collecting string constants (excluding docstrings,
  mirroring `test_no_recipe_knowledge.py`'s exemption) and flagging any matching
  `\bJFROG_[A-Z0-9_]*\b`; a test asserting zero matches against the real tree, naming file/line;
  planted-violation and clean-module fixtures -- FR-6.
- [x] Same file -- **Guard 2 (HTTP client import):** AST walk flagging any `import`/`from ... import`
  of `requests`, `httpx`, `urllib.request`, or `http.client` anywhere under `src/pyforge/mason/`; a
  test asserting zero matches against the real tree; planted-violation and clean-module fixtures --
  FR-6.
- [x] Same file -- **Guard 3 (env inheritance):** AST walk over every `Call` node under
  `src/pyforge/mason/` whose callee resolves to `subprocess.run`, `subprocess.Popen`, or
  `run_streamed`, flagging any `env=` keyword argument whose value is not the bare literal `None`,
  except one rationale-commented allowlist entry for `cfe.py::run_streamed`'s own internal `Popen`
  call (the sanctioned pass-through primitive itself, Story 1.10); a test asserting zero
  unallowlisted matches against the real tree, naming file/line; fixtures: a planted
  `subprocess.run(x, env={...})` (flagged), a planted `run_streamed(argv, timeout=5,
  env={"FOO": "bar"})` caller (flagged), the real allowlisted `run_streamed` internals (not
  flagged) -- FR-6, AD-14.
- [x] `tests/unit/test_cfe.py` -- add a test that sets `JFROG_API_KEY` to a sentinel value
  (`monkeypatch.setenv`), then calls `cfe.probe_import_floor(sys.executable)`,
  `cfe.validate_recipe([], root=fake_cfe_root, interpreter=sys.executable)`, and
  `cfe.submit_pr([], root=fake_cfe_root, interpreter=sys.executable)`, asserting the sentinel string
  appears in none of the returned `stdout`/`stderr`/`json_body` fields -- FR-6, NFR-2.
- [x] `tests/unit/test_cli.py` -- add a test running `main(["doctor", "--verbose"])` with the same
  sentinel set, asserting via `capsys` that the sentinel never appears in captured stdout or stderr
  -- FR-6, NFR-2.

**Acceptance Criteria:**
- Given the Mason codebase, when it is scanned, then no module reads any `JFROG_*` environment
  variable and no module imports an HTTP client library.
- Given a CFE subprocess invocation anywhere in the codebase, when it is spawned, then no call
  overrides its environment except the one allowlisted `run_streamed` primitive, so credentials
  reach CFE only through the inherited process environment.
- Given any verbosity level including `--verbose`, when `mason doctor` runs with a sentinel
  credential set, then the sentinel value is absent from stdout and stderr.
- Given a sentinel credential set in the environment, when `probe_import_floor`/`validate_recipe`/
  `submit_pr` run, then the sentinel is absent from every field of the returned `CfeResult`.
- Given this story completes, when a subsequent Epic 2-5 story adds code, then all three guards run
  against it automatically in the default (non-`slow`) test task, with no per-story registration
  step.

## Spec Change Log

## Review Triage Log

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high: 1, medium: 2, low: 4)
- defer: 1 (low: 1)
- reject: 6
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter found (and reproduced) that Guard 3's `cfe.py` allowlist
    exempted **every** `Popen` call found anywhere inside `run_streamed`'s body, not just the one
    sanctioned pass-through call -- a second, hostile `Popen(..., env={...})` planted in the same
    function body was silently allowlisted alongside the real one, defeating the guard's core
    purpose. Fixed `_allowlisted_popen_call_ids` to fail CLOSED: it now allowlists only when
    `run_streamed`'s body contains exactly one `Popen` call; more than one revokes the allowlist
    entirely, so both are flagged. Added a regression fixture planting a second call and asserting
    both are caught.
  - `[medium]` `[patch]` Edge Case Hunter found Guard 1's `\bJFROG_...` pattern never fires when
    preceded by `_` (the same underscore-adjacency bug `test_no_recipe_knowledge.py` already
    documents fixing for its own entries, reintroduced here despite this file's docstring claiming
    to mirror that guard) -- `STAGING_JFROG_API_KEY` evaded detection. Replaced with the sibling
    file's own established lookaround (`(?<![0-9A-Za-z])JFROG_[A-Z0-9_]*`, alnum-excluding but
    underscore-permitting). Added a regression fixture for the prefixed form.
  - `[medium]` `[patch]` Edge Case Hunter found the `test_cli.py` sentinel test only exercised
    `--verbose`, while both its own docstring and the spec's AC claim coverage of "any verbosity
    level." Parametrized the test over default/`--quiet`/`--verbose`.
  - `[low]` `[patch]` Blind Hunter found Guard 1 never scans `bytes` string constants, unlike
    `test_no_recipe_knowledge.py`'s precedent (`KEY = b"JFROG_API_KEY"` evaded detection). Added the
    same bytes-decode handling (`errors="replace"`) plus a regression fixture.
  - `[low]` `[patch]` Blind Hunter found Guard 1 case-sensitive (`jfrog_api_key` evaded detection).
    Added `re.IGNORECASE` plus a regression fixture.
  - `[low]` `[patch]` Blind Hunter found Guard 1's docstring-exemption only covered a scope's first
    statement, narrower than `test_no_recipe_knowledge.py`'s own exemption (which also covers a
    trailing "attribute docstring" immediately after an assignment) despite this file's docstring
    claiming to mirror it -- confirmed by direct reproduction (a trailing docstring mentioning
    `JFROG_API_KEY`, in this very file's own `_JFROG_ENV_VAR_PATTERN`-adjacent style, would have
    false-positived on itself). Added `_trailing_attribute_docstring_ids`, wired into
    `_docstring_string_ids`, plus two regression fixtures (exemption applies; a bare string with no
    preceding assignment still flags).
  - `[low]` `[patch]` Edge Case Hunter found Guard 3's docstring disclosed the `**kwargs` residual
    but not the equally-real positional-`env=`-argument residual. Extended the existing disclosure
    sentence to name both (doc-only; no detection-logic change -- out of proportion for this guard,
    matching the already-accepted `**kwargs` precedent).
  - `[low]` `[defer]` Both reviewers independently found `_parse_source`'s `except SyntaxError`
    clause doesn't catch the `ValueError` `ast.parse` raises for null-byte source. Confirmed
    pre-existing and identical in both sibling meta-test files this guard mirrors (not introduced by
    this story) -- logged to `deferred-work.md` for a unified three-file fix rather than a
    unilateral deviation in only the newest file.
  - `[reject]` Edge Case Hunter's "dynamic `importlib.import_module("requests")` bypasses Guard 2" --
    moot: `test_dependency_direction.py`'s existing AD-4 guard already bans
    `importlib.import_module`/`import_module`/`exec`/`__import__` anywhere in `pyforge.mason`,
    unconditionally, with no allowlist (confirmed by reading that file) -- any such call is already
    caught regardless of which module name it targets.
  - `[reject]` Blind Hunter's "`probe_import_floor`'s sentinel assertion is weak (isinstance only)"
    -- `ImportFloorResult` holds only `interpreter: str` (the input path, not derived from
    environment) and `missing: tuple[str, ...]` (a fixed subset of `CFE_IMPORT_FLOOR` keys);
    neither field can structurally carry an observed environment value, so there is nothing more to
    assert -- the test's own docstring already discloses this honestly.
  - `[reject]` Blind Hunter's "no test proves the positive half of AD-14 (credentials DO reach CFE)"
    -- already covered by design: Guard 3 structurally proves `env=` is never overridden at any
    call site, which (given Python's own subprocess semantics) is what guarantees inheritance;
    extending the fixture stub scripts to echo env vars back was considered and rejected during
    implementation as out of scope (spec Never boundary).
  - `[reject]` Blind Hunter's "both sentinel tests hardcode the identical literal independently
    rather than sharing one constant" -- a two-occurrence local constant in two independent test
    files is normal, not a defect; centralizing it is speculative abstraction for a trivial nit.
  - `[reject]` Blind Hunter's "`_run_streamed_function_def` only matches `ast.FunctionDef`, not
    `ast.AsyncFunctionDef`" -- speculative; `run_streamed` is shipped, reviewed, synchronous
    Story-1.10 API with no async-conversion plan anywhere in this project's artifacts.
  - `[reject]` Blind Hunter's "Guard 2's HTTP-ban scope isn't force-enforced against future drift"
    -- already explicitly disclosed in this spec's own Design Notes and Never boundary; not an
    actionable code change for this story.

### 2026-08-11 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 2, medium 3, low 6)
- defer: 0
- reject: 3
- addressed_findings:
  - `[high]` `[patch]` Both reviewers independently found (and reproduced against the real
    `cfe.py`) that Guard 3's allowlist blessed the sanctioned `Popen` **call's identity** and never
    inspected its `env=` expression. Rewriting that one call to `env={}`, to a hostile dict, or to a
    targeted `JFROG_*`-stripping comprehension defeated AD-14 at the single site that can defeat it,
    with all 34 guard tests green. Added `_SANCTIONED_PASS_THROUGH_ENV_EXPR` and an `ast.unparse`
    equality check, so the allowlist pins the expression, not the call. Mutation-verified: all three
    rewrites now red `test_no_unallowlisted_env_override_in_the_real_tree`; the genuine expression
    still passes. Added a 3-way parametrized regression fixture.
  - `[high]` `[patch]` Both reviewers found the new `test_cli.py` sentinel test mocked
    `doctor.build_report` — the only function on the `doctor` path that receives `os.environ` — so
    its own docstring claim that "the report itself" cannot echo the environment was structurally
    unreachable. Reproduced: a `build_report` folding `environ` into the report printed the sentinel
    verbatim to stdout while all three parametrized cases passed. Dropped the mock and made the test
    hermetic via `test_doctor.py`'s established empty-`PATH` + `tmp_path` pattern (AD-16).
    Mutation-verified: all three cases now fail on that exact mutation.
  - `[medium]` `[patch]` Both reviewers found `os.environ` mutation is an unguarded — and more
    idiomatic — route around Guard 3: `os.environ['TOKEN']=x; subprocess.run(argv)` scanned clean,
    though it overrides what the child inherits exactly as `env=` does. Added Guard 3b
    (`_find_env_mutation_violations`: subscript assign/delete, `update`/`setdefault`/`pop`/
    `popitem`/`clear`, `os.putenv`/`unsetenv`) with a real-tree assertion, an 8-way parametrized
    planted fixture, and two clean fixtures proving reads and unrelated mappings are not flagged.
  - `[medium]` `[patch]` Edge Case Hunter found Guard 2's per-name fixtures parametrize over
    `_BANNED_HTTP_IMPORTS` itself, so deleting an entry deleted its own coverage — reproduced by
    dropping `requests`/`httpx` and adding real imports to `resolve.py`: 262/262 meta-tests green.
    Added an independently-spelled `_REQUIRED_HTTP_IMPORTS` floor + assertion, mirroring
    `test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`.
  - `[medium]` `[patch]` Edge Case Hunter found Guard 3a recognized only `run`/`Popen`/
    `run_streamed`, so `subprocess.check_output(..., env={...})` — a plain override — passed
    unflagged (reproduced). Widened `_ENV_OVERRIDE_CALL_NAMES` to every spawn API in reach that
    takes `env` as a *keyword* (`call`/`check_call`/`check_output`/`create_subprocess_exec`/
    `_shell`), added a `_REQUIRED_ENV_OVERRIDE_CALL_NAMES` floor + per-name parametrized fixture.
  - `[low]` `[patch]` Both reviewers found Guard 2 ignores `ImportFrom.level`, so a *relative*
    import of a local module (`from .requests import helper`) was reported as the third-party
    client — a false positive whose cheapest repair is to weaken the guard. Added `node.level == 0`
    plus fixtures for both the relative (clean) and absolute (flagged) forms.
  - `[low]` `[patch]` Both reviewers found Guard 1 defeated by `+`-concatenation
    (`os.environ.get("JFROG" + "_API_KEY")` scanned clean). Added `_folded_concatenations`, which
    folds outermost `+`-chains of string/bytes constants and suppresses their consumed leaves so one
    expression is counted once (a self-written fixture caught a double-count in the first cut).
    Disclosed the remaining `%`/`.format`/`join`/`getattr` residuals in the module docstring.
  - `[low]` `[patch]` Blind Hunter found this was the only AST-scanning meta-test in the suite
    without the dangling-symlink `test_unreadable_file_...` fixture its six siblings all carry,
    leaving `_read_source`'s `except OSError` branch untested. Added it.
  - `[low]` `[patch]` Blind Hunter found no fixture pinned Guard 3's allowlist to a *path* rather
    than a bare filename, so a regression to `path.name == "cfe.py"` would ship green. Added
    `test_allowlist_is_matched_by_path_not_bare_filename` (a nested `cfe.py` must still be scanned),
    mirroring the identically-named sibling fixture.
  - `[low]` `[patch]` Blind Hunter found `probe_import_floor`'s sentinel assertion
    (`isinstance(...)`) cannot fail — both return paths construct an `ImportFloorResult` — so it
    paid for a real subprocess to assert nothing. Replaced with assertions over its actual fields,
    and narrowed `test_cfe.py`'s module-docstring claim that `subprocess.run` is "mocked throughout"
    to the Story 1.6 tests it was written for (Story 2.3's probe is deliberately real).
  - `[low]` `[patch]` Edge Case Hunter found the three-verbosity parametrization could silently
    collapse to one path when the runner's shell has `MASON_QUIET`/`MASON_VERBOSE` set. Added
    `monkeypatch.delenv` hygiene for the `MASON_*` surface.
  - `[reject]` Blind Hunter's "the `test_cfe.py` sentinel test passes with the child's environment
    scrubbed, so it proves neither direction of AD-14" — the `env={}`-at-`_invoke_captured` mutation
    it cites is caught by Guard 3a (Blind Hunter's own net assessment confirms this), and the prior
    pass already rejected extending the fixture stubs to echo env vars as outside the spec's Never
    boundary. The premise that made that rejection shaky (identity-only allowlisting) is fixed above.
  - `[reject]` Edge Case Hunter's "`os.execve`/`os.posix_spawn` env overrides pass unflagged" —
    those take env positionally-only in CPython, so no keyword-name scan can reach them, and
    `test_adapter_sole_caller.py`'s AD-3 guard already bans them outside `cfe.py`. Disclosed as a
    named residual in the module docstring instead.
  - `[reject]` Blind Hunter's "the story's deferred residual was never promoted to the tracked
    `planning-artifacts/deferred-work-ledger.md`" — premature, not missing: the ledger's own
    entries show the orchestrator's landing pass performing exactly this promotion (`promoted:
    2026-08-11 (landing pass, mason 2-2 / marshal 7-4)`), and 2-3 has not landed yet. Per the
    invocation's standing instruction, the orchestrator owns ledger entry status and resolution.

### 2026-08-11 — Review pass (third)
- intent_gap: 0
- bad_spec: 0
- patch: 17 (high 4, medium 6, low 7)
- defer: 1 (low 1)
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` Both reviewers found (and reproduced) that Guard 2 tested exact set
    membership, so any SUBMODULE of a banned client scanned clean while binding the full client:
    `import requests.sessions` leaves `requests.get` callable, and `from requests.sessions import
    Session` hands back a complete session object. One dotted suffix was the cheapest possible
    defeat of the guard, covered by no declared residual, and `test_dependency_direction.py`'s AD-4
    guard does not backstop it (it bans dynamic imports, not `import` statements). Added
    `_is_banned_http_module` (dotted-boundary prefix match) applied to all three import shapes, with
    a 4-way parametrized fixture, a report-once fixture, and a `requestsx`/`httpxray` fixture
    proving the match is on a dotted boundary and not a bare string prefix.
  - `[high]` `[patch]` Both reviewers found `os.environ |= {...}` — the operator that IS `update`
    (`MutableMapping.__ior__` → `os._Environ.__setitem__` → `putenv`, verified present at runtime) —
    fell through every Guard 3b branch, because its target is the bare `os.environ` attribute rather
    than a subscript. A complete one-line AD-14 break scanning clean. Added an explicit `AugAssign`
    branch plus a parametrized fixture.
  - `[high]` `[patch]` Both reviewers found the module docstring's positional-`env` residual rested
    on two claims that are both FALSE, and reproduced the consequence. Verified independently:
    `inspect.signature(os.execve)` is `(path, argv, env)` — positional-OR-keyword, so
    `os.execve(p, argv, env={...})` is accepted, not "positional-only" as claimed — and
    `test_adapter_sole_caller.py`'s AD-3 guard flags a spawn only when an argument names a CFE path
    or `_CFE_SCRIPTS` filename, so a spawn carrying a credential dict but no CFE path is invisible
    to it. `os.posix_spawn(path, argv, {"JFROG_API_KEY": tok})` was an unguarded AD-14 break. Added
    `_BANNED_EXPLICIT_ENV_SPAWN_FUNCTIONS` (the ten `os.exec*e`/`spawn*e`/`posix_spawn[p]` variants
    that take an explicit environment), banned outright rather than keyword-scanned since the
    argument is positional-only for `posix_spawn`; plus a floor, a per-name fixture, and a fixture
    proving the inheriting variants (`os.execv`) stay unflagged. A residual accepted on the strength
    of protection that was not there is worse than no disclosure, so the docstring now states the
    correction explicitly. (This supersedes the prior pass's `[reject]` of the same finding, whose
    premise these reproductions disproved.)
  - `[high]` `[patch]` Both reviewers found the `test_cfe.py` sentinel test was incapable of
    failing: the `fake_cfe_root` stubs emit a canned constant that never reads the ambient
    environment, so no `CfeResult` field could carry the sentinel regardless of Mason's behavior.
    Blind Hunter reproduced it by making `_invoke_captured` pass `env={}` to `subprocess.run` —
    Mason scrubbing the child's environment wholesale, the exact inverse of AD-14 — with the test
    still green. Added a POSITIVE control: `MASON_FIXTURE_STDOUT` (which the stub reads from its own
    inherited environment) is set to a marker asserted back out of `json_body`, so the "credentials
    DO reach CFE" half of AD-14 is now proved at runtime rather than only structurally.
    Mutation-verified: that same `env={}` mutation now reds the test.
  - `[medium]` `[patch]` Both reviewers found Guard 1's `+`-folding marked every `+`-operand as
    "nested" BEFORE knowing whether its parent folded, so `"JFROG" + "_API_KEY" + suffix` (an
    unfoldable outer node over a perfectly foldable inner one) folded nothing and scanned clean —
    one extra operand defeated the whole prior-pass fix. Rewrote `_folded_concatenations` to derive
    nesting only from chains that actually fold.
  - `[medium]` `[patch]` Blind Hunter found the folding pass could SUPPRESS a match the constant
    pass would otherwise have made — a net weakening introduced by the prior pass: `"staging" +
    "JFROG_API_KEY"` folds to text the alnum lookbehind correctly rejects, while the leaf
    `"JFROG_API_KEY"` was skipped as "consumed". Leaves are now re-scanned when their fold does not
    match, so folding can only ever add detections; the "one expression, one violation" property the
    existing fixture pins still holds.
  - `[medium]` `[patch]` Both reviewers found Guard 3b's `_is_os_environ` matched `attr ==
    "environ"` exactly, so `os.environb` — the bytes view of the identical POSIX environment, which
    `putenv`s through — scanned clean (both verified a real child inheriting the value). Widened to
    `_ENV_MAPPING_NAMES`.
  - `[medium]` `[patch]` Both reviewers found Guard 3b inspected only top-level assignment targets,
    so `os.environ['JFROG_API_KEY'], ok = token, True` scanned clean;
    `test_no_recipe_knowledge.py::_bound_names_in_target` already recurses for exactly this reason.
    Added `_mutated_env_targets` (tuple/list/starred recursion) plus `for`/`with ... as` targets.
    Writing the `with`-target fixture exposed a genuine crash — `ast.withitem` carries no `lineno`,
    so that path raised `AttributeError` out of the scanner instead of reporting the violation; the
    violation is now anchored on the matched target, which is the more precise anchor anyway.
  - `[medium]` `[patch]` Edge Case Hunter found `_JFROG_ENV_VAR_PATTERN` required a trailing `_`, so
    `{k: v for k, v in os.environ.items() if k.startswith("JFROG")}` — the idiomatic way to read a
    whole credential FAMILY at once, reading every `JFROG_*` variable while naming none — scanned
    clean. Made the suffix optional with a matching alnum lookahead, plus a `JFROGGY` fixture
    proving the bare form still does not match inside an unrelated word.
  - `[medium]` `[patch]` Blind Hunter found the allowlist had no liveness check and reproduced it:
    deleting the `env=` line from the real `cfe.py` entirely — so `run_streamed`'s `env` parameter is
    accepted and silently ignored and the pinned expression matches nothing — left all 65 guard tests
    green. A carve-out nobody exercises quietly comes to cover whatever that file grows next. Added
    `test_the_real_cfe_py_allowlist_entry_is_still_live`, mirroring
    `test_adapter_sole_caller.py::test_cfe_path_allowlist_is_exactly_ad3s_two_live_carve_outs`.
  - `[low]` `[patch]` Blind Hunter found Guard 3a omitted `subprocess_exec`/`subprocess_shell`,
    contradicting its own "every spawn API that takes `env` as a KEYWORD" claim — `asyncio`'s
    low-level loop methods forward `**kwargs` straight to `Popen`, and both names are already in the
    sibling floor this set says it mirrors. Added to both the live set and the floor.
  - `[low]` `[patch]` Blind Hunter found Guard 3a's failure message was a raw `ast.dump`, so its
    most likely real-world red — a benign reformat of `cfe.py`'s pass-through — printed
    `IfExp(test=Name(id='env', ...))` with no mention that an expression pin exists or what it
    expects. Switched to `ast.unparse` and made the assertion name the sanctioned expression.
  - `[low]` `[patch]` Blind Hunter found Guard 3b was the only guard in the file without an
    independently-spelled anti-shrink floor, protected today only incidentally because its fixture
    hardcodes its mutation strings. Added `_REQUIRED_ENV_MUTATING_METHODS`/`_FUNCTIONS` + a floor
    test, and a floor test for the new explicit-env spawn set.
  - `[low]` `[patch]` Blind Hunter found `_ENV_MUTATING_FUNCTIONS` matches a bare call name with no
    receiver check (unlike the adjacent `os.environ` method branch) yet reported every hit as
    `os.putenv()`, naming a module it never confirmed was involved. The conservative matching is
    deliberate and kept; the message now reports the call's own source text.
  - `[low]` `[patch]` Edge Case Hunter found `_run_streamed_function_def` matched only
    `ast.FunctionDef`, so an `async def run_streamed` voids the allowlist and reds the guard on the
    sanctioned call itself. Fails closed, but a false positive whose cheapest repair is to weaken the
    guard is the failure mode this file designs against, and `_docstring_string_ids` in the same file
    already handles both node types. Added `AsyncFunctionDef` + a fixture. (Supersedes the prior
    pass's `[reject]`, which called it speculative; it is reproducible in one line.)
  - `[low]` `[patch]` Blind Hunter found the CLI sentinel test covered the verbosity axis but not
    the format axis, despite `--format json` being the documented machine-consumed contract surface
    — latent only because `render_text` happens to print the same `data` keys today. Added `json`
    and `verbose-json` cases.
  - `[low]` `[patch]` Edge Case Hunter found `_REQUIRED_HTTP_IMPORTS`'s docstring cited ledger entry
    `DW-1-10` for its duplication rationale; verified against the ledger, `DW-1-10-1` is about an
    owed follow-up review of Story 1.10 and says nothing about set duplication. Repointed to the
    real precedent (`test_adapter_sole_caller.py`, which carries the rationale inline).
  - `[low]` `[defer]` Both reviewers found the attribute-docstring exemption misses prose following
    an `AugAssign` or appearing inside a function body, so a module's own AD-14 explanatory text can
    false-positive the guard. Reproduced, but identical in `test_no_recipe_knowledge.py:425-483`,
    which this file faithfully mirrors — logged to `deferred-work.md` for a unified two-file fix
    alongside the existing `_parse_source`/null-byte entry, rather than a unilateral deviation.
  - `[reject]` Edge Case Hunter's "dynamic `importlib.import_module('requests')`/`__import__('httpx')`
    bypasses Guard 2" — re-verified rather than inherited: `test_dependency_direction.py` bans
    `importlib.import_module`, `exec`, and `__import__` anywhere in `pyforge.mason`, unconditionally
    and with no allowlist (read directly, lines 228-299, including alias-tracking for
    `import importlib as il`). The prior pass's rejection premise holds.
  - `[reject]` Blind Hunter's "`_SANCTIONED_PASS_THROUGH_ENV_EXPR` is hand-duplicated from `cfe.py`
    rather than parsed out of it" — parsing the expected value out of the file under test would make
    the pin self-fulfilling (any rewrite would redefine what "sanctioned" means). The actual risk it
    names — a stale, dead carve-out — is closed by the liveness test added above.

### 2026-08-11 — Review pass (fourth)
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 3, medium 3, low 5)
- defer: 0
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Both reviewers found (and I re-reproduced against the real scanners) that
    Guard 3b never walks an `ast.comprehension`'s own `for` target, so `[None for
    os.environ['ARTIFACTORY_TOKEN'] in ['scrubbed']]` — which binds and mutates the real
    environment exactly as the statement `for` the third pass guarded — scanned clean. Added the
    `ast.comprehension` branch plus a 3-way fixture (listcomp/genexp/dictcomp).
    Mutation-verified against the live `resolve.py`.
  - `[high]` `[patch]` Both reviewers found ONE binding line defeated the whole of Guard 3b:
    `_is_os_environ` matched only the two literal spellings, so `_env = os.environ` followed by a
    targeted `del` of the `ARTIFACTORY*` family — Mason scrubbing what the CFE child inherits, the
    exact inverse of AD-14 at the seam this story protects — passed every guard and both sentinel
    tests. `from os import environ as e` was the same hole one keyword shorter (the unaliased form
    was already caught, which is what made the gap specific to rebinding). Added
    `_env_alias_names`: `as`-aliases plus direct assignment chains resolved to a fixed point,
    flow-insensitive so it fails closed, threaded through every 3b branch. Attribute matching
    stays pinned to the two literal names so one `data = os.environ` line cannot false-positive
    every `foo.data[...]` in the file. 4-way fixture + a clean fixture proving `dict(os.environ)`
    and unrelated mappings stay unflagged. Mutation-verified against the live `cfe.py`.
  - `[high]` `[patch]` Blind Hunter found Guard 2 bypassed by an indirect rebinding of the import
    primitive: `_dyn = importlib.import_module; _dyn("requests")` gave `resolve.py` a live HTTP
    client posting a bearer token with all 664 tests green. The two prior passes `[reject]`ed this
    family twice on the premise that `test_dependency_direction.py`'s AD-4 guard bans it
    unconditionally — true of the direct spellings those passes tested, but that guard's own
    docstring declares the exception verbatim ("It does not trace indirect rebinding"), verified
    by reading it. Added a scan for banned module names spelled as string constants passed as
    call ARGUMENTS, which closes every dynamic route (`import_module`, `__import__`,
    `globals()[...]`, any rebinding) without tracing a callable. Scoped to arguments after the
    first cut — a blanket constant scan — red the real tree on `cfe.py`'s legitimate
    `CFE_IMPORT_FLOOR` data entry; that false positive is now its own regression fixture.
    Mutation-verified.
  - `[medium]` `[patch]` Blind Hunter found Guard 1's declared residual list factually wrong in 3
    of 4 claims: `%`/`.format()`/`str.join`/f-strings are all FLAGGED (each re-reproduced against
    the real detector), and have been since the third pass made the `_` suffix optional — every
    one leaves a literal `"JFROG…"` fragment the bare-prefix form matches. Only `getattr`/a
    never-constant name genuinely evades. Same stale-disclosure class the third pass corrected for
    `os.execve`, and that `test_adapter_sole_caller.py` corrected for its own f-string note.
    Corrected the disclosure.
  - `[medium]` `[patch]` Both reviewers found the CLI sentinel test's absence assertions could not
    distinguish "no leak" from "no output", and that its docstring's claim that the `MASON_*`
    deletes "keep the three verbosity cases from collapsing into one" is false in both directions
    — `render.py` has no verbosity branch at all, so default/`--quiet`/`--verbose` are byte-
    identical regardless of the environment. Added a positive control (`mason_version`, a field
    both renderers emit) and rewrote the docstring to state honestly that the three verbosity ids
    exercise one render path today and are kept as forward coverage for the AC, that the format
    axis is the one that differs, and that the `MASON_*` deletes are hermeticity. Mutation-
    verified: dropping the report body from `render.write` now reds all five cases.
  - `[medium]` `[patch]` Both reviewers found `os.environ.__ior__({...})` — the explicit-dunder
    spelling of the `|=` operator the third pass closed as a HIGH — scanned clean, even though
    `__setitem__`/`__delitem__` were already in the method set for exactly that reason. Added
    `__ior__` to the live set and the floor, plus a fixture. Mutation-verified.
  - `[low]` `[patch]` Blind Hunter found three of Guard 3b's seven floor names (`popitem`,
    `__setitem__`, `__delitem__`) had no detection fixture — "membership in the frozenset is not
    detection" being this file's own repeatedly-stated standard, enforced with a per-name fixture
    for every other set. Added per-name fixtures parametrized over the independently-spelled
    floors (never the live sets, per `_REQUIRED_ENV_MUTATING_METHODS`' own docstring).
  - `[low]` `[patch]` Blind Hunter found Guard 2's two per-name fixtures parametrize over
    `_BANNED_HTTP_IMPORTS` itself — the self-deleting-fixture shape the floors exist to prevent,
    left in the one guard whose write-up narrates that bug at greatest length (backstopped by the
    floor test, so not a live hole). Repointed both to `_REQUIRED_HTTP_IMPORTS`.
  - `[low]` `[patch]` Edge Case Hunter found `_BANNED_EXPLICIT_ENV_SPAWN_FUNCTIONS`' docstring
    justified omitting the non-`e` spawn variants with "AD-3's own guard owns them" — the same
    false-backstop claim the paragraph directly above it had just corrected for `os.execve` (AD-3
    fires only when a spawn's arguments name a CFE path, so a bare `os.execv` is invisible to it
    too). Corrected: they are omitted because they inherit, which is what AD-14 requires, so they
    are outside this guard's rule rather than delegated to another one. No logic change — an
    inheriting spawn cannot break credential isolation.
  - `[low]` `[patch]` Edge Case Hunter found `test_cfe.py`'s `assert sentinel not in
    result.stderr` structurally incapable of failing: `_stub_support.emit` has no stderr channel,
    so `result.stderr` is always `""`. Disclosed as a tripwire rather than expanding Story 1.9's
    shared fixture with a `MASON_FIXTURE_STDERR` knob to re-prove, on a second stream, the
    inheritance the `MASON_FIXTURE_STDOUT` positive control already establishes.
  - `[low]` `[patch]` Blind Hunter found two false cross-references introduced by this story:
    `test_cli.py` cited `test_doctor.py::test_build_report_against_the_real_resolve_and_probe_chain`
    (no such test — the real name is `test_build_report_never_raises_against_a_real_unresolved_
    environment`), and `test_cfe.py`'s new paragraph claimed to be "the one place
    `probe_import_floor` runs against a real interpreter" when `test_doctor.py` and this story's
    own `test_cli.py` test both do too. Both corrected.
  - `[reject]` Edge Case Hunter's "a `+` chain of ~1000 string literals raises `RecursionError`
    out of `_folded_concatenations`" — fails LOUD (a red, erroring test), not silently, and a
    thousand-operand concatenation in a 2,129-line package is not a shape this guard needs to
    survive. The fail-cleanly handlers it cites are about unreadable/unparseable files.
  - `[reject]` Edge Case Hunter's "a `+`-assembled docstring naming a JFROG_* variable
    false-positives" — a `+` concatenation in the first statement position is not a docstring at
    all (CPython requires a single `ast.Constant`), so the premise misstates the shape, and the
    trigger requires someone to write `"…" + "JFROG_…"` as prose in production source.
  - `[reject]` Blind Hunter's "`probe_import_floor`'s half of the sentinel test still cannot fail;
    the honest move is to drop the call" — the spec's AC names `probe_import_floor` explicitly
    alongside `validate_recipe`/`submit_pr`, so dropping it deviates from the contract; the
    third pass already disclosed the limitation honestly in the test's own docstring.
  - `[reject]` Blind Hunter's proportionality finding (1,773 lines of guard; the module docstring
    duplicates the Review Triage Log) — the size is the accumulated product of four adversarial
    passes against a security invariant, the spec's frontmatter already carries `warnings:
    ['oversized']`, and a wholesale docstring rewrite is churn with its own regression risk. The
    one concrete drift it names (the stale residual list) is patched above.

## Design Notes

The HTTP-import guard is deliberately narrow (four known client libraries, not "no `socket` use" or
similar) because FR-6's rationale is specifically CFE's `_http.py` unconditionally attaching
`JFROG_API_KEY` to outbound requests -- Mason holding zero HTTP-client capability today structurally
forecloses that inheritance path. It is not a general network-access ban and Epic 3 is expected to
add scoped HTTP capability for its own (non-CFE) credentials later.

Guard 3 targets call sites, not function signatures: `run_streamed`'s own parameter
(`env: Mapping[str, str] | None = None`) is legitimate, shipped, reviewed Story-1.10 API surface --
the property this guard protects is "nobody currently exercises the override," which only a call-site
scan (not a signature scan) can prove.

**Implementation note (2026-08-11):** all three guards were built as a single, proportionally-simpler
scanner per rule in `tests/meta/test_credential_isolation.py` (one compiled pattern / name set each),
not a `DenyListEntry`-style table -- matching the spec's instruction not to over-engineer a
generalized deny-list abstraction for a single-category-per-scanner guard. Guard 1 is scoped to
string CONSTANT VALUES only (not identifier positions, unlike AD-1's guard), since FR-6's rule
concerns env-var *reads*, which always name the variable as a string. Investigation re-confirmed the
spec's Never boundary before writing any test: `resolve.py`/`cli.py`/`cfe.py` read only two
`MASON_*` keys via `.get()`, `os.environ` as a whole mapping is never rendered or logged anywhere in
the package, and `cfe.py`'s only `env=` call site is `run_streamed`'s own internal `Popen` call --
no production-code change was made or needed.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green, all new tests
  included, none marked `slow`.

**Result (fourth review pass, 2026-08-11):** **`691 passed in 7.93s`** (+27 collected items over the
third pass's 664). `git diff HEAD -- src/shared/packages/pyforge-mason/src/` is empty — zero
production-code change; the three modified files are all under `tests/`.

**Mutation verification (fourth review pass, 2026-08-11)** — every patch was proved non-vacuous by
planting the defect the reviewers reproduced and confirming the guard now reds. Each mutation was
appended to a tracked, unmodified file (`resolve.py`, `cfe.py`, `render.py`) and reverted with
`git checkout --` immediately after, so restoration is byte-exact; `git status --porcelain`
re-confirmed only the three intended test files modified, and `git diff HEAD -- .../src/` is empty.
The scanner-level reproductions were additionally run through a standalone harness that imports the
guard module and scans synthetic trees, before and after each patch.

| Re-planted defect | Before | After |
|---|---|---|
| `_env = os.environ` + `del _env[k]` credential scrub in `cfe.py` | green | reds real-tree Guard 3b |
| `_dyn = importlib.import_module; _dyn("requests")` in `resolve.py` | green | reds real-tree Guard 2 |
| `[None for os.environ["ARTIFACTORY_TOKEN"] in [...]]` in `resolve.py` | green | reds real-tree Guard 3b |
| `os.environ.__ior__({"JFROG_API_KEY": ...})` in `resolve.py` | green | reds real-tree Guard 3b |
| `from os import environ as e; e[...] = ...` (harness) | clean | flagged |
| `os.environ.popitem()` / `__setitem__` / `__delitem__` (harness) | flagged, untested | flagged, per-name fixture |
| `render.write` drops the report body | green | reds all 5 CLI sentinel cases |
| Blanket constant scan for Guard 2 (first cut of the fix) | — | red the real tree on `cfe.py`'s `CFE_IMPORT_FLOOR`; narrowed to call arguments |

**Result (third review pass, 2026-08-11):** **`664 passed in 7.93s`** (+36 collected items over the
follow-up pass's 628). `git diff --stat HEAD -- src/` confirms zero production-code change: the
three modified files are all under `tests/`.

**Mutation verification (third review pass, 2026-08-11)** — every patch was proved non-vacuous by
planting the defect the reviewers reproduced and confirming the guard now reds. The seven real-tree
mutations were applied to the live `resolve.py` and reverted with `git checkout --` after each (the
file is tracked and was unmodified, so restoration is byte-exact); the two `cfe.py` mutations the
same way. `git status --porcelain` re-confirmed only the three intended test files modified, and
`git diff HEAD -- src/shared/packages/pyforge-mason/src/` is empty.

| Re-planted defect | Before | After |
|---|---|---|
| `os.posix_spawn(path, argv, {"JFROG_API_KEY": ...})` in `resolve.py` | green | reds real-tree Guard 3a |
| `os.environ \|= {"JFROG_API_KEY": ...}` | green | reds real-tree Guard 3b |
| `os.environb[b"JFROG_API_KEY"] = ...` | green | reds real-tree Guard 3b |
| `os.environ["A"], _ok = "b", True` (tuple target) | green | reds real-tree Guard 3b |
| `{k: v for k, v in os.environ.items() if k.startswith("JFROG")}` | green | reds real-tree Guard 1 |
| `import requests.sessions` | green | reds real-tree Guard 2 |
| `os.environ.get("JFROG" + "_API_KEY" + _S)` (unfoldable outer chain) | green | reds real-tree Guard 1 |
| Delete the sanctioned `env=` line from `cfe.py` | green (65 guard tests) | reds the allowlist-liveness test |
| `_invoke_captured` passes `env={}` (scrubs the child) | green | reds the `test_cfe.py` sentinel test |

**Result (2026-08-11):** `589 passed in 8.10s` (baseline before this story, confirmed via
`git stash`: 559 collected; +30 new collected items: 22 functions in
`tests/meta/test_credential_isolation.py` expanding to 28 collected items via
`@pytest.mark.parametrize`, +1 in `tests/unit/test_cfe.py`, +1 in `tests/unit/test_cli.py`).
After the review pass's patches: `597 passed in 7.83s`.
After the follow-up review pass's patches: **`628 passed in 7.84s`** (+31 collected items).

**Mutation verification (follow-up review, 2026-08-11)** — each patch was proved non-vacuous by
re-planting the defect the reviewers reproduced and confirming the guard now reds. Run against a
scratch copy of the package (`cp -r` to the session scratchpad) so the worktree stayed clean; the
one live-tree mutation (`doctor.py`, untouched by this story) was backed up and restored, and
`git status` re-confirmed only the three intended test files modified.

| Re-planted defect | Before | After |
|---|---|---|
| Sanctioned `Popen` `env=` → `JFROG_*`-stripping comprehension | green | reds real-tree Guard 3a |
| Sanctioned `Popen` `env=` → `{}` | green | reds real-tree Guard 3a |
| Sanctioned `Popen` `env=` unchanged (control) | green | still green |
| `os.environ['ARTIFACTORY_TOKEN']=...` in `resolve.py` | green | reds real-tree Guard 3b |
| `build_report` folds `environ` into the report | green | reds all 3 `doctor` sentinel cases |
| Drop `requests`/`httpx` from banned set + real imports | green | reds the `_REQUIRED_HTTP_IMPORTS` floor |
| `subprocess.check_output(..., env={...})` in `cfe.py` | green | reds real-tree Guard 3a |




## Auto Run Result

**Status:** done (fourth review pass — follow-up review of a previously-`done` spec).

**Implemented change.** No new feature work; this pass hardened the AD-14 credential-isolation
guard against eleven review findings, three of them complete AD-14 breaks that scanned clean.
Guard 3b now walks comprehension binding targets and resolves aliases of the environment mapping
(`from os import environ as e`, `_env = os.environ`, and assignment chains, to a fixed point) and
recognizes the `__ior__` dunder; Guard 2 now flags a banned client named as a string constant in a
call argument, closing every dynamic-import route including the indirect rebinding
`test_dependency_direction.py`'s AD-4 guard explicitly declares it does not trace. Two factually
wrong residual disclosures were corrected, and the CLI sentinel test gained a positive control so
its absence assertions cannot pass against empty output.

**Files changed** (all under `src/shared/packages/pyforge-mason/`, zero production-code change):
- `tests/meta/test_credential_isolation.py` — the three guard fixes above, corrected residual
  disclosures for Guards 1/2/3b/3c, per-name fixtures over the independently-spelled floors, and
  fixtures for every newly closed hole plus the `CFE_IMPORT_FLOOR` false positive the first cut of
  the Guard 2 fix produced.
- `tests/unit/test_cfe.py` — disclosed the structurally-empty `stderr` assertion as a tripwire;
  corrected the false "the one place `probe_import_floor` runs for real" claim.
- `tests/unit/test_cli.py` — added the `mason_version` positive control; corrected the false
  `MASON_*`-collapse claim and the dangling `test_doctor.py` cross-reference.

**Review findings:** 11 patched (high 3, medium 3, low 5), 0 deferred, 4 rejected, 0 intent gaps,
0 spec defects. Full detail in the fourth-pass Review Triage Log above.

**Verification.** `pixi run -e pyforge-mason pyforge-mason-test` → `691 passed in 7.93s` (+27
collected items over 664). `git diff HEAD -- src/shared/packages/pyforge-mason/src/` empty.
Seven mutations planted and reverted (table above); all red the intended assertion, control green.

**Residual risks.**
- Alias tracking is flow-insensitive by design (fails closed), so a name rebound away from
  `os.environ` after being bound to it stays flagged. No such shape exists in the package; the
  trade is disclosed at `_env_alias_names`.
- Binding the environment through a container, a call, or an instance attribute
  (`self._env = os.environ`) is untracked open-ended dataflow, as is a module name assembled at
  runtime or reached via `getattr`. Both disclosed in the module docstring.
- Guard 2's HTTP ban remains scoped to today's zero-HTTP baseline; Epic 3 must loosen it
  explicitly (spec Never boundary).
