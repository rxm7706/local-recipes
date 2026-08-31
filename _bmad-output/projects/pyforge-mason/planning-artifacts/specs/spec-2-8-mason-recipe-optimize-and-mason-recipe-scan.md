---
title: 'mason recipe optimize and mason recipe scan'
type: 'feature'
created: '2026-08-12'
status: done
baseline_revision: '2eaf7927dd0db2bc0762ffe72ca7a07c13f4a96b'
review_loop_iteration: 0
followup_review_recommended: false # dev-verify repair pass: 3 low patches (count correction, docstring qualifier, 1 new test), 1 low defer, 6 rejects -- no structural/security/API change, below the follow-up threshold
final_revision: 'ff8d225ea4790442e255459c95bc816b97e38bdb'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** FR-11/FR-12's `recipe optimize` and `recipe scan` are unimplemented. A user preparing a
recipe for review has no way to get CFE's quality findings and vulnerability scan before a reviewer
flags them.

**Approach:** Reading the real scripts resolves both: `recipe_optimizer.py` (backing MCP's
`optimize_recipe`) and `vulnerability_scanner.py` (backing `scan_for_vulnerabilities`) are both
CAPTURE-mode, JSON-emitting scripts invoked exactly like Story 2.7's `failure_analyzer.py`. Add
`optimize()`/`scan()` to `recipe.py`, each composed on a new `cfe.py::optimize_recipe`/
`scan_for_vulnerabilities` adapter (mirrors `validate_recipe`'s shape: `args: Sequence[str]` in, bare
`CfeResult` out) and two new `recipe optimize`/`recipe scan` verbs on `cli.py`'s existing
`_noun_verbs["recipe"]` seam.

## Boundaries & Constraints

**Always:**
- `recipe_path` (positional, required) passed straight through as each script's own positional argv --
  no Mason-side existence check or interpretation (AD-1), mirroring `diagnose`; a missing/invalid path
  surfaces as CFE's own `{"success": false, "error": ...}` body, exit 1 -- data, never raised (AD-4).
- `optimize()`/`scan()` call `cfe.ensure_cfe_root` first (mirrors `diagnose`/`build`), THEN probe CFE's
  import floor via `cfe.probe_import_floor(resolved_interpreter.path)` and raise `CfeImportFloorError`
  themselves -- but ONLY when their own operation-relevant subset of `.missing` is non-empty, never the
  whole 6-entry floor (`cfe.ensure_import_floor` is NOT called by either) -- the one departure from
  `diagnose`/`build`'s stdlib-only exemption. Reading both scripts: `optimize()` checks only for
  `ruamel.yaml`; `scan()` checks only for `requests` and `pyyaml`. Scoping per operation matters because
  a working call must not be rejected for lacking a package the invoked operation never imports (e.g.
  `optimize()` must not fail over a missing `truststore`). Of the two, only a missing `pyyaml` produces a
  **false-clean** result: `vulnerability_scanner.py`'s `extract_dependencies` swallows the failure and
  returns `[]`, so `run_scan` reports `{"success": true, "mode": "skipped", "scanned": 0,
  "unpinned_skipped": [...]}` -- indistinguishable from a genuinely clean scan. A missing `requests`
  instead raises inside `scan_via_api`, which `run_scan` catches and reports honestly (`{"success":
  false, "error": ..., "hint": ...}`, exit 1) -- not false-clean, but still worth gating early rather
  than spawning the subprocess only to fail. A missing `ruamel.yaml` degrades `recipe_optimizer.py` to a
  lone `OPT-000` suggestion.
- `cfe.optimize_recipe` invokes with `args=[recipe_path]` (no `--json` -- the script always emits JSON);
  `cfe.scan_for_vulnerabilities` invokes with `args=["--json", recipe_path]` (defaults to human text
  without it) -- mirrors each real script's own MCP-server wrapper invocation exactly
  (`.claude/tools/conda_forge_server.py`'s `optimize_recipe`/`scan_for_vulnerabilities`).
- Both adapters default to a 120s timeout (mirrors the real MCP server's own `_run_script` default,
  which neither tool wrapper overrides), overridable via `--cfe-timeout`/`MASON_CFE_TIMEOUT`.
- Both results render through the existing path unchanged: `render.write(fmt, sys.stdout, "recipe
  optimize"/"recipe scan", "ok", dataclasses.asdict(result), [])` -- findings live in `json_body`,
  reaching `--format json`'s `data` field with CFE's own field/check-code identifiers untouched.
- A nonzero CFE returncode (findings/vulnerabilities present) is data on the returned `CfeResult`,
  never raised (AD-4) -- both scripts use "nonzero = found something" as their own CI convention,
  matching `validate_recipe`/`diagnose_failure`'s precedent; `mason recipe optimize`/`scan` exit
  `EXIT_OK` regardless of findings.

**Block If:** None identified -- both backing scripts' argv/import-floor shape are resolved above from
reading the real scripts and the real MCP wrapper.

**Never:**
- No `--offline` flag on `scan`: the MCP surface Mason mirrors (`scan_for_vulnerabilities(recipe_path:
  str)`) exposes none, and neither FR-12 nor test-architecture.md's row name one -- speculative surface,
  matching Story 2.7's identical `--first-only` rejection.
- No Mason-side severity/threshold policy on `scan`'s results, no check-code filtering on `optimize`'s
  (FR-11/FR-12's own wording) -- CFE's identifiers pass through untouched, like `validate`/`diagnose`.
- No new model: both adapters return the shared `CfeResult` (Story 2.1) -- a second CAPTURE-mode shape
  would contradict the established one-shape rule.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Optimize finds suggestions | `recipe optimize <path>`, checks fire | `CfeResult` with CFE's suggestions array rendered verbatim | No error (nonzero returncode is data) |
| Optimize clean recipe | no suggestions | `CfeResult`, empty suggestions array, returncode 0 | No error |
| Scan finds vulnerabilities | `recipe scan <path>`, a pinned dep has a CVE | `CfeResult` with CFE's vulnerable-package list verbatim, no Mason filtering | No error (nonzero returncode is data) |
| Scan clean dependency set | no vulnerabilities | `CfeResult`, `total_vulnerabilities: 0` | No error |
| CFE root unresolved | no root found | `CfeUnresolvedError` before any subprocess spawns | `EXIT_CFE_UNAVAILABLE` |
| Interpreter missing its operation's import floor | `optimize`: `ruamel.yaml` absent; `scan`: `requests` and/or `pyyaml` absent | `CfeImportFloorError` scoped to the operation's own subset, before that operation's own subprocess spawns; an interpreter missing only an unrelated floor entry (e.g. `truststore` for `optimize`) is NOT rejected | `EXIT_FAILED` |
| Operation exceeds timeout | `--cfe-timeout` fires | `CfeTimeoutError` | `EXIT_FAILED`, stderr |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/cfe.py` -- add `_CFE_SCRIPTS["optimize_recipe"] = "recipe_optimizer.py"`,
  `_CFE_SCRIPTS["scan_for_vulnerabilities"] = "vulnerability_scanner.py"`, two
  `_..._TIMEOUT_SECONDS = 120.0` constants, `optimize_recipe(args, *, root, interpreter, timeout=None)
  -> CfeResult` and `scan_for_vulnerabilities(args, *, root, interpreter, timeout=None) -> CfeResult`
  (both mirror `validate_recipe`'s shape via `_invoke_captured`).
- `src/pyforge/mason/recipe.py` -- add `optimize(recipe_path, *, cfe_root_arg, cfe_python_arg,
  cfe_timeout_arg, environ, start_directory) -> CfeResult` and `scan(recipe_path, *, ...) ->
  CfeResult`: each resolves root + interpreter, calls `cfe.ensure_cfe_root`, calls
  `cfe.probe_import_floor(resolved_interpreter.path)` and raises `CfeImportFloorError(missing=...,
  interpreter=...)` itself when its own operation-relevant subset of `.missing` is non-empty --
  `optimize()` checks only `{"ruamel.yaml"}`, `scan()` checks only `{"requests", "pyyaml"}` (new, scoped
  per operation -- see Boundaries; `cfe.ensure_import_floor`'s whole-floor check is used by neither),
  calls its own `cfe.*` adapter with the args shape documented above.
- `src/pyforge/mason/cli.py` -- add `_RECIPE_OPTIMIZE_HELP`/`_RECIPE_SCAN_HELP`; register `optimize`/
  `scan` verb subparsers on `_noun_verbs["recipe"]` (each a required `recipe_path` positional)
  alongside the existing `diagnose` registration -- the `.choices`-derived metavar update already
  covers additional verbs automatically; dispatch both in `main()` after the `recipe diagnose` branch.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/recipe_optimizer.py` (new) -- stub
  mirroring `failure_analyzer.py`'s shape, canned success JSON (`{"success": true, "suggestions_found":
  ..., "suggestions": [...]}`).
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/vulnerability_scanner.py` (new) --
  stub, canned clean-scan JSON (`{"success": true, "mode": "osv-api", ..., "total_vulnerabilities": 0,
  "results": []}`).
- `tests/unit/test_cfe.py` -- `optimize_recipe`/`scan_for_vulnerabilities` coverage mirroring
  `diagnose_failure`'s (mocked I/O matrix, per-operation-default timeout, table-entry identity,
  real-fixture round-trip with the import floor faked -- see Design Notes); extend `_CFE_SCRIPTS`
  table-shape assertion to 5 entries; extend the AD-14 sentinel test to both new call sites.
- `tests/unit/test_recipe.py` -- `optimize()`/`scan()` composition against mocks + `fake_cfe_root`:
  happy path, CFE-unresolved propagation, import-floor-missing propagation (a REAL, unmocked
  assertion -- see Design Notes), a positive "`probe_import_floor` is called, scoped to the operation's
  own subset" test (inverse of Story 2.7's `test_diagnose_never_calls_ensure_import_floor`).
- `tests/unit/test_cli.py` -- `recipe optimize`/`recipe scan` verb registration + dispatch (text/JSON,
  `CfeUnresolvedError` -> `EXIT_CFE_UNAVAILABLE`, `CfeImportFloorError` -> `EXIT_FAILED`, real-fixture
  end-to-end).
- `tests/meta/test_adapter_sole_caller.py` -- update
  `test_parse_cfe_script_filenames_reads_the_real_cfe_py`'s literal to the new 5-entry frozenset.

## Tasks & Acceptance

**Execution:**
- [x] `cfe.py` -- add both table entries, timeout constants, adapter functions -- FR-11, FR-12.
- [x] `recipe.py` -- `optimize()`/`scan()` use-cases, each gated on `probe_import_floor` scoped to its
  own operation-relevant subset -- FR-11, FR-12.
- [x] `cli.py` -- register + dispatch `recipe optimize`/`recipe scan` -- FR-11, FR-12.
- [x] `tests/fixtures/.../recipe_optimizer.py`, `vulnerability_scanner.py` (new stubs) -- FR-11, FR-12.
- [x] `test_cfe.py`, `test_recipe.py`, `test_cli.py` -- coverage per the I/O matrix -- FR-11, FR-12.
- [x] `test_adapter_sole_caller.py` -- update the table-shape assertion -- FR-11, FR-12.

**Acceptance Criteria:**
- Given `mason recipe optimize <path>`, when it runs, then CFE's check codes are preserved verbatim in
  the rendered output.
- Given `mason recipe scan <path>`, when it runs, then CFE's scanner is invoked and its findings are
  rendered with no Mason-side severity policy, threshold, or filtering.
- Given `--format json` on either verb, when it runs, then findings appear in the envelope's `data`
  field.
- Given an interpreter missing its operation's own import-floor subset (`optimize`: `ruamel.yaml`;
  `scan`: `requests` and/or `pyyaml`), when that verb runs, then it fails with
  `CfeImportFloorError`/`EXIT_FAILED` before the wrapped script's own subprocess spawns -- unlike
  `diagnose`/`build`, neither `recipe_optimizer.py` nor `vulnerability_scanner.py` is stdlib-only.
- Given an interpreter missing only a floor entry unrelated to the verb being run (e.g. `truststore`
  for `optimize`), when that verb runs, then it is NOT rejected on that account.
- Given no CFE root is resolvable, when either verb runs, then it fails with `EXIT_CFE_UNAVAILABLE`
  before any subprocess spawns (mirrors `diagnose`/`build`).

## Spec Change Log

### 2026-08-12 — Escalation resolved (human decision via `/bmad-loop-resolve`)
Boundaries & Constraints rewritten: `optimize()`/`scan()` now probe CFE's import floor themselves via
`cfe.probe_import_floor` and raise `CfeImportFloorError` only for their own operation-relevant subset of
`.missing` (`optimize`: `{"ruamel.yaml"}`; `scan`: `{"requests", "pyyaml"}`) -- `cfe.ensure_import_floor`'s
whole-floor check is used by neither verb. Also corrected the false-clean claim: only a missing `pyyaml`
is genuinely false-clean (`scan`'s `mode: "skipped"` path); a missing `requests` raises an honest error.
Code Map and the I/O & Edge-Case Matrix updated to match. Chosen from 3 options presented (scope per
operation / drop the gate entirely / keep the whole-floor gate as spec'd) -- the preserved attempt-1 diff
(`{implementation_artifacts}/preserved/spec-2-8-attempt-1-tracked.patch`) should apply close to as-is
once its two `ensure_import_floor` call sites are rescoped per this change.

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 1 (high: 1)
- bad_spec: 0
- patch: 4 (low: 4)
- defer: 2 (medium: 2)
- reject: 1
- addressed_findings:
  - none

**Intent-gap finding (blocking, root cause inside `<intent-contract>`):** Both Blind Hunter and
Edge Case Hunter independently found that this spec's own Boundaries & Constraints "Always" bullet
-- "THEN call `cfe.ensure_import_floor(resolved_interpreter.path)` before invoking their own
adapter" -- mandates the existing, unscoped `ensure_import_floor`, which raises whenever ANY of
`CFE_IMPORT_FLOOR`'s 6 entries (`pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`,
`conda-forge-metadata`) is missing from the interpreter, not just the 1-2 entries the specific
wrapped script actually imports (`ruamel.yaml` for `optimize`; `requests`+`pyyaml` for `scan`). A
faithful implementation of that literal instruction therefore rejects a working call whenever an
interpreter has (say) `ruamel.yaml` but lacks the unrelated `truststore`/`packaging`/
`conda-forge-metadata` -- reintroducing, at a coarser grain, exactly the "reject a call that would
have succeeded" failure `diagnose()`'s own docstring says was deliberately avoided by skipping the
floor gate entirely. The same over-broad claim is baked into this spec's own "false-clean" framing
(Boundaries + Design Notes): tracing the real `vulnerability_scanner.py`, a missing `requests`
actually produces an HONEST `{"success": false, "error": "...", "hint": ...}`, not a silent
false-clean result; only a missing `pyyaml` produces a misleadingly-clean-shaped response, and even
then with a different JSON shape (`mode: "skipped"`, no `results` key) than the literal this spec
quotes three times. The fix -- scope the floor check to only the operation-relevant subset of
`probe_import_floor(...).missing` per verb, rather than delegating to the whole-floor
`ensure_import_floor` -- is a Boundaries & Constraints-level design change, i.e. inside
`<intent-contract>`, which this workflow's own rules forbid an autonomous pass from rewriting
unilaterally. Per protocol: code changes reverted to `baseline_revision`
(`2eaf7927dd0db2bc0762ffe72ca7a07c13f4a96b`) and this run HALTs for human resolution via
`/bmad-loop-resolve`. **The full first-attempt implementation is preserved, not discarded** --
`{implementation_artifacts}/preserved/spec-2-8-attempt-1-tracked.patch` (tracked-file diff) plus the
two new untracked fixture stubs under `{implementation_artifacts}/preserved/src/...` -- it was
783-tests-green and, aside from the floor-scoping question, matched every other Boundary faithfully;
once the floor-check is rescoped, most of this diff should still apply close to as-is.

**Other findings this pass -- addressed in the attempt-2 reimplementation below (2026-08-12):**
- `[low]` `[patch]` `recipe.py`'s docstrings describe `recipe_optimizer.py`'s `ruamel.yaml`-missing
  degrade output as "a lone low-confidence suggestion" -- the real script emits it at confidence
  `1.0` (the schema's max), the opposite of low-confidence. **Fixed**: both `recipe.py` and `cfe.py`
  docstrings now say "maximum confidence (1.0)".
- `[low]` `[patch]` The two new REAL, unmocked `CfeImportFloorError`-propagation tests in
  `test_recipe.py` depend on the undocumented, unpinned fact that the `pyforge-mason` pixi env
  currently lacks `ruamel.yaml`/`requests`/`pyyaml` -- if a future story adds any of these as a
  dependency, the tests will fail with "DID NOT RAISE," reading as a regression rather than a drifted
  environmental assumption. Should assert/document the precondition explicitly. **Fixed**: both tests
  now assert the precondition directly against the real `cfe.probe_import_floor(sys.executable)`
  result before the `pytest.raises` block.
- `[low]` `[patch]` `cfe.py`'s new adapter docstrings claim skipping the floor gate at the adapter
  layer "matches every other adapter here, which never re-derives a precondition its own use-case has
  already checked" -- no other existing adapter actually has such a precondition to skip; the framing
  implies a precedent that doesn't exist. **Fixed**: reworded to drop the false-precedent claim.
- `[low-medium]` `[patch]` `_RECIPE_SCAN_HELP` doesn't disclose that, unlike its sibling `optimize`
  (purely local), `scan` makes outbound network calls to `api.osv.dev` by default -- a surprising
  asymmetry between two verbs with parallel single-positional signatures under the same noun. **Fixed**:
  help text now names the `api.osv.dev` network call.

**Still deliberately not actioned (deferred/rejected, unchanged from the original triage):**
- `[medium]` `[defer]` No `--offline` escape hatch is reachable from `mason recipe scan` for
  air-gapped/enterprise deployments -- real, but pre-existing in the MCP surface this story mirrors
  (`scan_for_vulnerabilities(recipe_path: str)` itself takes no such parameter) and explicitly,
  deliberately scoped out by this spec's own Never boundary (mirrors Story 2.7's identical
  `--first-only` precedent). Not this story's defect to fix.
- `[medium]` `[defer]` `_invoke_captured`'s `subprocess.run(timeout=...)` only kills the direct CFE
  wrapper-script child, not the grandchild subprocess that wrapper itself spawns for the real skill
  script -- pre-existing since Story 2.1, shared by every CAPTURE-mode adapter (`validate_recipe`,
  `submit_pr`, `diagnose_failure` too), but newly more likely to matter now that
  `scan_for_vulnerabilities` is the first adapter to perform live network I/O.
- `[reject]` `CfeImportFloorError` has no dedicated exit code, falling through to the generic
  `EXIT_FAILED` `MasonError` branch like an ordinary finding -- this is the existing, established
  5-code exit taxonomy (AD-7), unchanged by and not specific to this story; `CfeImportFloorError` was
  already a `MasonError` subclass before this story (Story 1.6/1.7).

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 2, low 3)
- defer: 1 (high 0, medium 0, low 1)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` `recipe.py`'s module docstring claimed both verbs surface a missing/invalid
    `recipe_path` identically as a `CfeResult.json_body` -- verified against the real
    `vulnerability_scanner.py`/`recipe_optimizer.py` that this is false: the wrapped scanner writes that
    same `{"success": false, "error": ...}` shape to **stderr** (not stdout) on `FileNotFoundError`, so
    `scan()`'s `json_body` is `None` in that case while `optimize()`'s is not. Corrected the module and
    `scan()` docstrings to describe the asymmetry accurately; no code behavior changed (spec Never
    boundary forbids Mason-side reinterpretation, and the divergence lives in the wrapped script, not in
    Mason).
  - `[medium]` `[patch]` `_RECIPE_SCAN_HELP` didn't disclose that the wrapped scanner only scans
    exactly-pinned (`==`) dependencies -- confirmed by reading `extract_dependencies`'s own docstring and
    filter logic; range-pinned/unpinned deps are silently excluded, and a scan of this repo's own
    `recipes/` tree found only ~12% carry an exact pin, so `mason recipe scan` commonly reports "clean"
    having queried nothing. Help text now names this scope limit.
  - `[low]` `[patch]` No test isolated a single missing package (`pyyaml` XOR `requests`) for `scan()`'s
    import-floor gate -- every existing test had either neither or both relevant packages missing, never
    pinning the gate's OR-semantics in between. Added a parametrized test covering each in isolation.
  - `[low]` `[patch]` `cfe.py`'s `scan_for_vulnerabilities` docstring overclaimed a missing `requests` is
    "reported honestly" unconditionally -- the real script only does so when no local CVE database file
    exists yet; if one does, it silently falls back to a (possibly stale) local-db scan instead.
    Docstring now states the condition and notes the distinction is moot in practice, since Mason's own
    gate always intercepts before either path is reached.
  - `[low]` `[patch]` `_SCAN_RELEVANT_FLOOR`'s tuple literal was declared in the reverse of
    `cfe.CFE_IMPORT_FLOOR`'s own declared order (`requests` before `pyyaml`) -- purely cosmetic
    (membership-test order doesn't affect `CfeImportFloorError.missing`'s reported order, which inherits
    from `probe.missing`), but needlessly inconsistent with the stated convention. Reordered to
    `("pyyaml", "requests")`.

**Deferred (not this pass's fix):**
- `[low]` `[defer]` `render_text`'s one-line-per-key format double-prints `scan`'s findings -- both the
  raw `stdout` string and the already-parsed `json_body` render as separate keys, so any real result
  appears twice. Pre-existing since Story 2.1 (shared by every CAPTURE-mode adapter), newly more visible
  now that `scan`'s payloads (vulnerability lists, aliases, summaries) are likely the largest/noisiest
  `json_body`s Mason renders yet. Logged as `DW-2-8-1` in `{implementation_artifacts}/deferred-work.md`
  -- a proper fix belongs to `render.py` itself, not a `recipe scan`-local workaround.

**Rejected (noise, dropped):**
- `[reject]` A speculative note that `optimize()`/`scan()` lack the same `-` stdin-sentinel usage-error
  check `diagnose`'s dispatch branch has -- verified directly: neither wrapped script treats `-`
  specially, so there is no actual behavior gap, only an undocumented (and unnecessary) parallel.
- `[reject]` A refactor suggestion to extract the near-identical root/floor-gate sequence duplicated
  between `optimize()`/`scan()` into a shared private helper -- two call sites is not the threshold this
  codebase's stated conventions treat as warranting a new abstraction (Simplicity First: "three similar
  lines is better than a premature abstraction").
- `[reject]` A refactor suggestion to replace `cli.py`'s three copy-pasted `recipe`-verb dispatch blocks
  with a verb-to-handler table ahead of future verbs (`recipe build`/`recipe new`) that don't exist yet
  -- speculative, forward-looking design work outside this story's scope.

Verified green after these patches: `pixi run -e pyforge-mason pyforge-mason-test` -- 787 passed (785
before this pass's 2 new parametrized-test cases).

### 2026-08-12 — Review pass (dev-verify repair)
- intent_gap: 0
- bad_spec: 0
- patch: 3 (low: 3)
- defer: 1 (low: 1)
- reject: 6
- addressed_findings:
  - `[low]` `[patch]` `spec-pyforge-mason/.memlog.md`'s own reconciliation entry (added earlier in
    this repair pass) claimed "mason suite 723 -> 785," but the committed implementation actually
    collects 787 tests at that point (independently verified: baseline `2eaf7927dd` collects 723 via
    `pixi run -e pyforge-mason pyforge-mason-test` in a scratch checkout, HEAD `7b02785f60` collects
    787 both with and without this pass's own uncommitted changes). Fixed the memlog's own count.
  - `[low]` `[patch]` `recipe.py`'s module docstring and `scan()`'s own docstring both stated a
    missing `requests` "is reported honestly" unconditionally, dropping the qualifier `cfe.py`'s
    parallel docstring for the identical fact correctly carries ("when no local CVE database exists
    yet at the path `pixi run update-cve-db` populates"). Two docstrings written in the same commit
    disagreed about the same underlying script behavior. Fixed both to match `cfe.py`'s wording.
  - `[low]` `[patch]` No test exercised `scan_for_vulnerabilities`'s documented stdout/stderr
    asymmetry on a missing path -- the existing `test_scan_for_vulnerabilities_reports_a_scan_error_body_as_data_not_raised`
    puts its error JSON on stdout, not stderr, so it cannot exercise the real wrapped scanner's actual
    behavior (confirmed by reading the real script: it prints its `FileNotFoundError` body to `stderr`
    via `print(..., file=sys.stderr)`, unlike the optimizer's stdout `print`). Added
    `test_scan_for_vulnerabilities_reports_a_missing_path_body_on_stderr_with_no_json_body`, pinning
    `json_body is None` / `stderr` carries the raw text, matching `_invoke_captured`'s
    stdout-only `_extract_json` behavior.

**Deferred (not this pass's fix):**
- `[low]` `[defer]` `_OPTIMIZE_RELEVANT_FLOOR`/`_SCAN_RELEVANT_FLOOR` are hand-declared tuples, never
  derived from or cross-checked against the real wrapped scripts' own `try/except ImportError`
  blocks -- a future CFE skill change to either script's import set would silently desync Mason's
  per-operation floor gate with no test to catch it. Logged as `DW-2-8-2` in
  `{implementation_artifacts}/deferred-work.md` -- a proper fix mirrors
  `test_adapter_sole_caller.py`'s existing AST-based style, benefiting whichever future story next
  touches either script's import list, not a fix scoped to this pass.

**Rejected (noise, dropped):**
- `[reject]` `scan()`'s import-floor gate rejects a call that a local CVE database's own fallback
  path (`scan_via_local_db`) could have completed successfully -- real, but restates a tradeoff the
  frozen `<intent-contract>` already made explicitly (Boundaries: "gating it early is a courtesy...
  not a false-clean fix") and the second review pass already surfaced and left unchanged ("the
  distinction is moot in practice, since Mason's own gate always intercepts before either path is
  reached"). Fixing it would require Mason to know CFE's own local-CVE-db-file state to decide
  whether to gate -- exactly the CFE-specific policy knowledge AD-1's knowledge-free core forbids.
- `[reject]` `optimize()`/`scan()`'s scoped `CfeImportFloorError` (naming only the operation-relevant
  missing subset) is less diagnosable than `doctor`'s full-floor report for a genuinely bogus
  `--cfe-python` path -- not a like-for-like comparison (doctor answers "what is this interpreter's
  overall floor status," `optimize`/`scan` answer "why did THIS operation fail"), no concrete harm
  named, and the scoped-subset error shape is the frozen intent-contract's own explicit design
  (Boundaries: "raise `CfeImportFloorError` themselves... scoped to their own operation-relevant
  subset").
- `[reject]` `mason recipe scan`'s help text doesn't document the missing `--offline` flag as a
  deliberate scope cut -- exact re-discovery of this story's own first review pass's `[medium]`
  `[defer]` finding on the identical gap, itself citing the frozen intent-contract's Never boundary
  ("No `--offline` flag on `scan`... speculative surface, matching Story 2.7's identical
  `--first-only` rejection").
- `[reject]` `mypy` flags `Path | None` passed where `Path` is expected at `optimize()`/`scan()`'s
  two new `cfe.*` call sites -- confirmed pre-existing: the identical pattern already exists,
  unaddressed, at `diagnose()`'s call site (Story 2.7), and no pixi task wires `mypy` into
  `pyforge-mason`'s gate, so this is not newly introduced or newly visible.
- `[reject]` `optimize`/`scan` lack the same stdin-sentinel (`-`) usage-error guard `diagnose`'s
  dispatch branch has -- exact re-discovery of this story's own first review pass's rejection of the
  identical claim, which verified directly that neither `recipe_optimizer.py` nor
  `vulnerability_scanner.py` treats `-` specially.
- `[reject]` `mason recipe scan` on a script-reported "path not found" can render `status: "ok"` with
  `data.json_body: null` at the CLI/render layer -- the render-unchanged behavior is the frozen
  intent-contract's own explicit Always boundary ("Both results render through the existing path
  unchanged... no Mason-side reinterpretation"), and the underlying stdout/stderr asymmetry it stems
  from was already surfaced and fixed as a docs-only correction in this story's own second review
  pass, which explicitly noted "no code behavior changed... [the] spec Never boundary forbids
  Mason-side reinterpretation."

Verified green after these patches: `pixi run -e pyforge-mason pyforge-mason-test` -- 788 passed (787
before this pass's 1 new test), and `python scripts/spec_surface_reconcile.py` -- `OK: every tracked
file governed or allowlisted; no drift.`

## Design Notes

**Why `optimize`/`scan` probe the import floor themselves, scoped per operation, instead of calling
`ensure_import_floor`:** both wrapped scripts guard their third-party imports with `try/except
ImportError` and degrade rather than crash, but each depends on a different, small subset of CFE's
6-entry floor (`recipe_optimizer.py`: `ruamel.yaml`; `vulnerability_scanner.py`: `requests`+`pyyaml`) --
`ensure_import_floor`'s whole-floor check would reject a working call over an entry the invoked
operation never imports (e.g. reject `optimize()` for a missing `truststore`), reintroducing at a
coarser grain exactly the "reject a call that would have succeeded" failure `diagnose()`'s own docstring
says was deliberately avoided by skipping the floor gate entirely. Only one of the two degrade paths is
actually false-clean: a missing `pyyaml` makes `extract_dependencies` return `[]` silently, so
`run_scan` reports `{"success": true, "mode": "skipped", "scanned": 0, "unpinned_skipped": [...]}` --
indistinguishable from a genuinely clean scan. A missing `requests` instead raises inside
`scan_via_api`, which `run_scan` catches and reports honestly (`{"success": false, "error": ...,
"hint": ...}`); gating it early is a courtesy (fail before spawning the subprocess), not a false-clean
fix. A missing `ruamel.yaml` degrades `optimize` to a lone `OPT-000` suggestion -- not false-clean, but
also gated early for the same reason. Confirmed by reading both scripts directly, not inferred.

**Why the real-fixture round-trip test must fake the floor via `probe_import_floor`, not
`subprocess.run`:** patching `pyforge.mason.cfe.subprocess.run` wholesale would also intercept
`_invoke_captured`'s own real call against the fixture stub. Patching `cfe.probe_import_floor`'s return
value fakes only the floor-satisfied verdict, leaving the actual invocation's subprocess call genuinely
real -- mirrors `test_diagnose_never_calls_ensure_import_floor`'s call-site-level patching style rather
than a blanket subprocess mock.

**Empirical note:** `pixi run -e pyforge-mason python -c "import yaml"` (and `requests`/`truststore`/
`ruamel.yaml`/`conda_forge_metadata`) confirms the lean `pyforge-mason` pixi env genuinely lacks 5 of
`CFE_IMPORT_FLOOR`'s 6 entries -- only `packaging` is present. A test that does NOT fake the floor and
calls `optimize()`/`scan()` with `cfe_python_arg=sys.executable` exercises a REAL, unmocked
`CfeImportFloorError` raise, not a synthetic one -- no mocking needed for that negative-path test.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** This run was a dev-verify repair pass, resumed after the previous session's committed
implementation (commit `7b02785f60`, unchanged by this pass) failed bmad-loop's own deterministic
`python scripts/spec_surface_reconcile.py` verify gate. Root cause: the story's 9 changed/added
`pyforge-mason` files are governed by a *different*, higher-level Spec
(`pyforge-mason/spec-pyforge-mason`, the product Spec), whose `.memlog.md` was never updated to name
them and whose drift baseline was never re-stamped -- the identical shape Story 2.7 hit one story
earlier, repaired the same way.

**Files changed this pass (two commits):**
- `2ae6c66499` -- reconciliation: `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/
  spec-pyforge-mason/.memlog.md` (appended a `(change)` entry naming all 9 files this story touched,
  plus an `(event)` entry noting the baseline re-stamp) and `scripts/.spec-surface-baseline.json`
  (re-stamped via `spec_surface_check.py --write-baseline --spec pyforge-mason/spec-pyforge-mason`,
  scoped to this one spec only -- verified no other spec's entry was touched).
- `ff8d225ea4` -- fresh review pass over the diff since `baseline_revision`, covering both the
  original story diff and the reconciliation commit: corrected the reconciliation commit's own
  test-count claim (723 -> 785 was wrong; actual 723 -> 788), added a missing qualifier to two
  `recipe.py` docstrings (a missing `requests` is reported honestly only when no local CVE database
  exists yet, matching `cfe.py`'s own docstring), and added one real test pinning
  `scan_for_vulnerabilities`'s documented stdout/stderr asymmetry on a missing recipe path. Re-stamped
  the baseline once more (`--write-baseline --spec pyforge-mason/spec-pyforge-mason`) after these
  code/test edits, since they changed governed-file hashes again.
- No file inside `<intent-contract>` was touched; no functional/behavioral change beyond the two
  docstring corrections and the added test.

**Review findings breakdown (fresh Blind Hunter + Edge Case Hunter pass over the diff since
`baseline_revision`, covering the original story diff, the reconciliation commit, and this pass's own
fixes):**
- patch: 3 (low) -- a stale test-count claim in the reconciliation memlog entry; a dropped docstring
  qualifier about a missing `requests`'s honest-error path being conditional on no local CVE database
  existing yet; a missing test for `scan_for_vulnerabilities`'s documented stdout/stderr asymmetry on
  a missing path.
- defer: 1 (low) -- logged `DW-2-8-2`: `_OPTIMIZE_RELEVANT_FLOOR`/`_SCAN_RELEVANT_FLOOR` are
  hand-declared, never derived from or cross-checked against the real wrapped scripts' own import
  sets -- a future CFE skill import-set change would silently desync Mason's floor gate.
- reject: 6 -- including three re-discoveries of points this story's own two prior review passes
  already surfaced and explicitly left as-is (the stdin-sentinel `-` guard gap, the missing
  `--offline` flag, and the missing-path `status: "ok"`/`json_body: null` render-layer quirk), one
  restatement of a tradeoff already explicit in the frozen `<intent-contract>` whose "fix" would
  require Mason to hold CFE-specific policy knowledge AD-1 forbids (the local-CVE-db-fallback gating
  question), one comparison against `doctor`'s full-floor report that isn't like-for-like (the scoped
  error shape is itself the frozen intent-contract's own design), and one pre-existing, non-CI-gated
  `mypy` narrowing gap already present at `diagnose()`'s identical call site.
- intent_gap: 0, bad_spec: 0.

**Follow-up review recommendation:** `false` -- three low-severity localized fixes (a count
correction, a docstring wording fix, one new test), no structural/security/API/behavior change.

**Verification performed:** `pixi run --frozen -e pyforge-mason pyforge-mason-test` (788 passed, 0
failed) and `python scripts/spec_surface_reconcile.py` (`OK: every tracked file governed or
allowlisted; no drift.`) both re-run and confirmed green against the final committed HEAD
(`ff8d225ea4`) -- the exact two verify commands `bmad-loop`'s own policy runs for this story.

**Residual risks:** None blocking. `DW-2-8-1` (the `render_text` double-print of `scan`'s findings)
and the new `DW-2-8-2` (hand-declared floor-subset tuples) remain open in Tier-3 `deferred-work.md`
for later, unrelated attention -- neither blocks this story.


