<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Dual output format with stream discipline'
type: 'feature'
created: '2026-07-31'
status: done
baseline_revision: 'b9d28c704527c15c9cbdb259199f339e7ffa3dd9'
final_revision: '93d487134ee425d59348fb5bd896f4bebd4c1423'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `cli.py` accepts and resolves `--format` (Story 1.2) but nothing consumes it: `doctor`'s
stub writes its message straight to stderr via a raw `print()`, there is no JSON envelope, and no
module owns "how output looks" — violating AD-8 the moment a second output path is added.

**Approach:** Add `render.py` as the sole formatter (AD-8): a single `write()` entry point both the
text and JSON branches call, emitting a `schema_version`/`command`/`status`/`data`/`errors` envelope
under `--format json` (stdout: exactly one document; everything else: stderr) and an equivalent
human-readable line under `--format text` (the default). Wire it into the one existing command that
succeeds today — `doctor`'s stub — replacing its raw stderr `print()`.

## Boundaries & Constraints

**Always:** `render.py` is the only module that formats a command result. Its JSON envelope has
exactly these five keys: `schema_version`, `command`, `status`, `data`, `errors`. `render_json` calls
`json.dumps(doc, sort_keys=True, ensure_ascii=True, indent=2, separators=(",", ": "))` (the
`pyforge.warden.report.render_json` precedent) so identical inputs are byte-identical. One `write(fmt,
stream, command, status, data, errors)` function is the sole call site for both formats — `render_text`
is never invoked directly by `cli.py`. `doctor`'s stub message becomes `data`, rendered to stdout via
`write()`, not a stderr diagnostic — FR-34 frames `doctor` as a reporting command, and AD-8 requires its
result go through the one formatter. `--format` resolves via the existing `_resolve_str`/`_ENV_FORMAT`
helpers (Story 1.2), unchanged. `doctor` keeps exiting `EXIT_OK`.

**Block If:** none identified — epics.md's Story 1.4 AC plus AD-8 fully specify this work.

**Never:** Implement `doctor`'s real diagnosis (CFE root, interpreter, engines) — Story 1.8's job; the
payload stays the placeholder stub message. Add `errors.py`/`exit_codes.py` or route `MasonError`
through `render.py` — that machinery is Story 1.3's, developing in a parallel sibling worktree not yet
merged into this branch; `main()`'s existing exception handling is untouched here. Add JSON-Schema
self-validation (`pyforge.warden.report`'s heavier pattern) — no packaged schema file exists for Mason
yet and this story's AC doesn't ask for one. Change argparse's own `--help`/`--version`/bare-invocation/
bare-noun-usage-error output — those stay argparse-native per Story 1.2's settled contract; AD-8 governs
command-*result* formatting, not the CLI shell's own usage surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `doctor`, `--format json` | `argv=["doctor","--format","json"]` | stdout: one JSON doc — `schema_version`, `command="doctor"`, `status="ok"`, `data.message`, `errors=[]` | exit `EXIT_OK`; stderr empty |
| `doctor`, `--format text` (default) | `argv=["doctor"]` | stdout: a human-readable line built by the same `write()` call | exit `EXIT_OK`; stderr empty |
| `doctor`, env fallback | `MASON_FORMAT=json` env, no `--format` flag | resolved format is `"json"`; same JSON envelope as above | exit `EXIT_OK` |
| `render.write` with `errors` populated | `errors=[{"identifier": "x:y", "message": "z"}]` | JSON: `errors` preserved verbatim as a list; text: each error rendered on its own line | n/a |
| `render_json` called twice, identical args | same `(command, status, data, errors)` twice | the two returned strings are byte-identical | n/a |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/render.py` (new) -- the only formatter (AD-8): `SCHEMA_VERSION`, `render_json`,
  `render_text`, `write`.
- `src/pyforge/mason/cli.py` -- `doctor` branch resolves `--format` and calls `render.write(...)`
  instead of its raw stderr `print()`.
- `tests/unit/test_render.py` (new) -- envelope shape, determinism, text/json parity through `write`,
  errors rendering.
- `tests/unit/test_cli.py` -- rewrite `test_doctor_invocation_stubs_and_succeeds` for the new stdout
  contract; add a `--format json` doctor test asserting the parsed envelope; add a `MASON_FORMAT`
  env-var doctor test.
- `tests/meta/test_render_ownership.py` (new) -- AST scan mirroring `test_dependency_direction.py`/
  `test_exit_code_ownership.py`: no `.py` file under `src/pyforge/mason/` other than `cli.py`/
  `render.py` writes to stdout.

## Tasks & Acceptance

**Execution:**
- [x] `render.py` -- create the module: `SCHEMA_VERSION = "1"`; `render_json(command, status, data,
  errors) -> str`; `render_text(command, status, data, errors) -> str`; `write(fmt, stream, command,
  status, data, errors) -> None` dispatching to whichever renderer and writing+flushing to `stream` --
  FR-31, AD-8.
- [x] `cli.py` -- in the `doctor` branch, resolve `fmt = _resolve_str(getattr(ns, "format", None),
  _ENV_FORMAT, "text")` and call `render.write(fmt, sys.stdout, "doctor", "ok", {"message": "not
  implemented yet (Story 1.8 implements real diagnosis)"}, [])`; remove the old stderr `print()`;
  `EXIT_OK` unchanged -- FR-31, FR-34, AD-8.
- [x] `tests/unit/test_render.py` -- assert the five envelope keys under `--format json`; assert
  `render_json` is deterministic (two calls, identical args, byte-identical strings); assert
  `--format text` and `--format json` both flow through `write`; assert an `errors` list renders in
  both formats.
- [x] `tests/unit/test_cli.py` -- update `test_doctor_invocation_stubs_and_succeeds` (stdout now
  carries the summary, stderr is empty); add `test_doctor_json_format_emits_the_envelope` (parse
  stdout as JSON, assert the five keys and `command == "doctor"`); add a `MASON_FORMAT=json`
  env-var-only doctor test.
- [x] `tests/meta/test_render_ownership.py` -- AST scan asserting no `.py` file under
  `src/pyforge/mason/` other than `cli.py`/`render.py` contains a stdout-writing call (`print(...)`
  without `file=sys.stderr`, or `sys.stdout`/`sys.stdout.buffer` writes); `tmp_path` regression
  fixtures proving it fires on a violation and permits the two allowed files, mirroring
  `test_dependency_direction.py`'s rigor.

**Acceptance Criteria:**
- Given any command, when `--format json` is passed, then stdout carries exactly one JSON document
  (or nothing) and every diagnostic goes to stderr.
- Given the JSON document, when parsed, then it carries `schema_version`, `command`, `status`,
  `data`, and `errors`.
- Given `--format text` (the default), when a command succeeds, then a human-readable summary is
  written to stdout via the same writer the JSON branch uses.
- Given AD-8, when the module tree is inspected, then only `render.py` formats output and no other
  module (besides the argparse-native paths in `cli.py`) writes to stdout.
- Given identical inputs, when a command runs twice, then the JSON output is byte-identical.

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium: 2, low: 3)
- defer: 2
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` `test_render_ownership.py`'s `_is_stdout_write_target` recognized
    `sys.stdout`/`sys.stdout.buffer` but not a bare `stdout` name (e.g. `from sys import
    stdout`), asymmetric with the adjacent `_is_stderr_target`'s bare-`stderr` recognition —
    a real hole in the guard this story exists to build. Added the bare-name case; added a
    `tmp_path` regression fixture proving it now fires.
  - `[medium]` `[patch]` `render.write`'s fallback-to-text behavior for any `fmt` other than
    exactly `"json"` was undocumented and untested — Story 1.2's own review log explicitly
    punted `MASON_FORMAT` env-value validation to "Story 1.4's consumption site," and an
    out-of-choices env value (bypassing argparse's `choices=` validation entirely) silently
    fell through to text with no test proving that was intentional. Documented the behavior
    in `write`'s docstring (matches `_resolve_str`/`_resolve_bool`'s established
    invalid-value-falls-back-to-default philosophy — no `MasonError` taxonomy exists yet to
    raise a typed error instead) and added both a `render.py`-level test and a
    `MASON_FORMAT=bogus` CLI-level test.
  - `[low]` `[patch]` `_is_stdout_write_call` only recognized `.write(...)`, not
    `.writelines(...)`, on a stdout target — a structurally identical stdout-emitting call the
    guard silently missed. Extended the attribute check to both names; added a regression
    fixture.
  - `[low]` `[patch]` `test_doctor_invocation_stubs_and_succeeds` only substring-checked
    `"doctor"`/`"not implemented yet"` in stdout, which would still pass if the default format
    silently regressed to JSON. Added an explicit non-JSON-shape assertion (`json.JSONDecodeError`
    on the text output).
  - `[low]` `[patch]` Neither the `--format json` nor the `MASON_FORMAT=json` doctor test
    asserted the I/O matrix's documented `data.message` content, only the envelope's
    structural keys. Added `"not implemented yet" in doc["data"]["message"]` to both.

**Deferred findings (2 — logged to `{implementation_artifacts}/deferred-work.md`):**
`render.write`'s `stream.write()`/`stream.flush()` have no `BrokenPipeError`/`OSError` guard
(joins the existing Story 1.3 deferred entry for `cli.py`'s unguarded stderr writes — same
family, a unified fix isn't possible until Story 1.3 merges into this branch). `render_json`/
`render_text` have no defensive handling for a non-JSON-serializable `data` value (e.g. `Path`,
`datetime`) — not triggered by `doctor`'s current stub, will matter once later epics' use-cases
return richer data shapes.

**Rejected findings (6 — noise/speculative/matches established precedent/out-of-scope, dropped
silently per instructions, listed here only for this pass's audit trail):** the meta-test's
allowlist exempting the whole of `cli.py` rather than scoping to its specific legitimate stdout
call sites (matches `test_dependency_direction.py`'s established whole-file allowlist
precedent exactly). The claim that this new meta-test "mirrors `test_dependency_direction.py`'s
rigor exactly" being overstated for a structurally harder call-shape scan vs. a simpler
import scan (a documentation-framing critique, not a functional defect). `json.dumps`'s default
`allow_nan=True` permitting non-RFC-8259 `NaN`/`Infinity` tokens (speculative — no realistic
Mason data shape produces non-finite floats in the foreseeable future). No end-to-end `main()`
test exercising a non-`"ok"` status or non-empty `errors` (no such code branch exists in
`cli.py` today — `doctor`'s call site hardcodes `status="ok"`/`errors=[]`; a hypothetical
swapped-argument bug is already caught by the existing `command`/`status` assertions).
`schema_version = "1"` diverging from `pyforge.warden.report`'s stricter `"1.<minor>.<patch>"`
shape (no cross-station schema-version format contract exists; explicitly deferred by this
story's own Never clause, which omits schema-file validation entirely). `os.write(1, ...)`
(raw-fd write) not flagged by the AST scanner (exotic, no precedent anywhere in this codebase;
fd-number-based heuristics would be brittle over-engineering for a trigger with no realistic
path here).

### 2026-07-31 — Review pass 2 (fresh follow-up pass on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 1, low 1)
- defer: 2 (medium 1, low 1)
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` `test_doctor_invocation_stubs_and_succeeds` asserts the no-flag/no-env
    text default but never scrubbed `MASON_FORMAT` — no `conftest.py` exists anywhere in the
    package, so an ambient `MASON_FORMAT=json` on a runner legitimately selects JSON and falsely
    reds the test (the `_resolve_str` tests in the same file already `setenv`/`delenv` carefully;
    this test skipped that discipline). Added `monkeypatch.delenv("MASON_FORMAT", raising=False)`;
    verified the full suite green with `MASON_FORMAT=json` exported.
  - `[low]` `[patch]` `test_write_json_format_emits_one_parseable_document` promised "exactly one
    JSON document" but only parse-checked — `json.loads` tolerates surrounding whitespace, so a
    doubled/padded document would still pass. Replaced `endswith("\n")` with byte-equality against
    `render_json(...) + "\n"` (the text-fallback test in the same file already used exactly this
    pattern).

**Deferred findings (2 — both re-surfaced duplicates of the entries the first 2026-07-31 pass
already logged to `{implementation_artifacts}/deferred-work.md`; NOT re-appended, per the
orchestrator's append-NEW-entries-only instruction):** `render.write`'s unguarded
`stream.write()`/`stream.flush()` under a closed pipe (`mason doctor | head -1` →
`BrokenPipeError` → traceback + `EXIT_INTERNAL` via `main()`'s blanket handler). `render_json`/
`render_text`'s lack of defensive handling for non-JSON-serializable or non-`dict`-Mapping `data`
(`Path`/`datetime`/`ChainMap` → `TypeError` → same traceback path).

**Rejected findings (14 dedup'd — noise/speculative/spec-mandated/settled by the prior pass;
dropped silently per instructions, listed only for this pass's audit trail):** invalid or
case-variant `MASON_FORMAT` falling back silently without a stderr warning (settled last pass:
documented fallback matches `_resolve_str` philosophy; no error taxonomy until Story 1.3 merges).
`status: "ok"` for the unimplemented stub being a "semantic lie" (spec-mandated verbatim — the
task list and I/O matrix hardcode `status="ok"`; Story 1.8 replaces the payload, not the plumbing).
AST guard bypassable via aliasing (`out = sys.stdout`, `sys.__stdout__`, `getattr(sys, "stdout")`,
`os.write(1, ...)`, logging handlers) — documented literal-match scope in the test's own docstring;
the `os.write` variant was explicitly rejected last pass; it is a lint tripwire, not a sandbox.
Guard false-positives on `print(file=<non-stderr target>)` / bare `stdout`-named file handles /
`print(**kw)` (intentional documented conservatism — under AD-8 core modules return data rather
than printing anywhere; speculative future code). No doctor e2e for flag-beats-env or
flag-before-noun (composition-covered: Story 1.2's settled root+verb `--format` registration plus
`_resolve_str` precedence unit tests; the spec's test matrix doesn't call for it). `render_text`
newline-injection / nested-value repr in `data` values (explicitly NON-CONTRACT output; the crash
facet of richer data is already ledgered). Error-item shape unvalidated (`errors` as a bare str /
malformed dicts) — no caller exists beyond `cli.py`'s hardcoded `[]`; the analogous
no-such-branch finding was rejected last pass. Format validity defined in two places (argparse
`choices` vs `write`'s `== "json"`) — speculative third-format drift; adding a format necessarily
edits `write()` anyway. "Story 1.8" wording leaking into the user-facing payload (the spec
mandates that exact message verbatim). `SCHEMA_VERSION` bump policy unstated for future `data`
shape changes (schema governance is excluded by the Never clause; same family rejected last
pass). The `monkeypatch` mutual-exclusion tests pinning module-global lookup rather than behavior
(deliberate sole-call-site enforcement; nit). `json.dumps` `allow_nan` emitting non-RFC-8259
tokens (identical finding rejected last pass; facts unchanged). The symlink-based
unreadable-file fixture failing on Windows (copies `test_dependency_direction.py:156`'s exact
precedent, which the spec mandated mirroring; the suite runs via pixi on linux). The stderr→stdout
stub move breaking hypothetical out-of-tree stderr scrapers (that move IS the spec's intent;
the reviewer self-rated it low confidence).

## Design Notes

No other command exists yet to route through `render.py` — `doctor`'s stub is the first real caller,
mirroring the "vacuous but real" pattern Stories 1.2/1.3 already established (their meta-tests enforce
invariants before any real content exists to violate them). Once `recipe.py`/`package.py`/
`environment.py`/`doctor.py` land in later epics, they must call `render.write(...)`, never print
directly; `test_render_ownership.py`'s allowlist (`cli.py`, `render.py` only) already covers them
without needing a future edit. Story 1.3 (error taxonomy, `MasonError`, `exit_codes.py`) is developing
in a parallel sibling worktree (`bmad-loop/20260730-192241-976f/1-3-error-taxonomy-and-exit-code-contract`)
branched from the same base commit and has not merged into this branch; this story does not depend on
it, and `main()`'s existing `except Exception` handling is left untouched.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (existing + new tests).

## Auto Run Result

Status: done (fresh follow-up review pass, 2026-07-31)

- **Implemented change:** none beyond review patches — this run was a fresh review pass (Blind
  Hunter + Edge Case Hunter, per the done-spec route) over the already-committed Story 1.4 work
  (`b9d28c70` → `0ee5465e`).
- **Files changed this pass:**
  - `tests/unit/test_cli.py` — default-format doctor test made hermetic against an ambient
    `MASON_FORMAT` (`monkeypatch.delenv`).
  - `tests/unit/test_render.py` — json-write test now byte-asserts exactly one JSON document plus
    one trailing newline.
- **Review findings breakdown:** 23 raw findings from the two hunters, deduplicated → 2 patches
  applied (1 medium, 1 low), 2 deferred (both duplicates of the first pass's already-ledgered
  entries — not re-appended, per the orchestrator's append-NEW-entries-only instruction),
  14 rejected (see the Review Triage Log's pass-2 entry for the audit trail).
- **Follow-up review recommendation:** false — two localized, test-only, low-consequence fixes;
  no behavior, API, or security impact.
- **Verification:** `pixi run -e pyforge-mason pyforge-mason-test` → 68 passed; re-run with
  `MASON_FORMAT=json` exported → 68 passed (proves the hermeticity patch against the exact
  reported failure mode).
- **Residual risks:** the two ledgered deferrals — no `BrokenPipeError` guard on
  `render.write`'s stream I/O (unified fix waits on Story 1.3's merge), and no defensive handling
  for non-JSON-serializable `data` (latent until later epics return richer payloads).

