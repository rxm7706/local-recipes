---
title: 'The CFE port'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: 'd409cdca9c23511a4c9a10cbcfc120760e10ec6b'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '2db2d58f1bb3073b420a53495560027993f9414c'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `cfe.py` today only probes the import floor and streams long-running child output
(`run_streamed`) — nothing declares which CFE scripts Mason calls, invokes one as a short
JSON-returning CAPTURE-mode subprocess, or turns the result into a typed shape, so no future
`mason recipe` verb has anywhere to delegate to. `models.py`, the architecture's designated home
for cross-layer data shapes, does not exist yet either.

**Approach:** Extend `cfe.py` with a module-level `_CFE_SCRIPTS` table, a private CAPTURE-mode
invocation helper, and two public named adapter functions (`validate_recipe`, `submit_pr` — the
two scripts Story 1.9's fixture already stubs) that return a new `CfeResult`. Add tolerant
JSON-from-stdout extraction and a new `CfeTimeoutError`. Create `models.py`, holding `CfeResult`
and the relocated `DoctorReport` (the architecture's one sanctioned pre-existing-shape move).

## Boundaries & Constraints

**Always:** only `cfe.py` may hold a CFE script name/path or spawn a CFE process (AD-3's existing
two-entry carve-out — `resolve.py`'s `_CFE_MARKER`, `errors.py`'s guidance echo — is unaffected);
every CFE script `cfe.py` invokes is declared exactly once in the module-level `_CFE_SCRIPTS`
table, and each public adapter function looks up its own key — it never accepts a script name/path
as a parameter; CAPTURE-mode invocation always runs `[interpreter, str(script_path), *args]` as
list argv, `shell=True` never used (AD-2/AD-4); `subprocess.run(..., encoding="utf-8",
errors="replace")` is pinned explicitly, never bare `text=True` — mirrors `run_streamed`'s own
documented rationale that a locale-derived default silently mangles a valid UTF-8 JSON body under
`LC_ALL=C`; `stdin=subprocess.DEVNULL` on every CAPTURE-mode call, mirroring `run_streamed`'s
"never hang on an unexpectedly-interactive child" rule; a non-zero return code is data on
`CfeResult`, never an exception; timeout expiry raises the new `CfeTimeoutError` (identifier
`cfe:timeout`) and relies on `subprocess.run`'s own kill-and-reap-before-raising behavior for "no
orphaned process"; JSON extraction tries the whole stdout first, then — on failure — finds the
first `{`/`[` at the start of a line and parses from there (ports `_extract_json_from_stdout()`,
`.claude/tools/conda_forge_server.py` — not imported, FR-4's own rationale: that shim lives in a
governed surface); unlike that precedent, finding no JSON at all sets `CfeResult.json_body` to
`None` rather than raising — FR-4 says a parsed body is present "when one is present," so its
absence is a normal outcome, not an error; `CfeResult` is `@dataclass(frozen=True)` and lives in
the new `models.py`; `models.py` is a dependency-direction leaf — it may import from `.engines` (a
still-more-leaf sibling) but nothing besides this story's `DoctorReport` relocation moves into it;
`doctor.py` re-exports `DoctorReport` via `from .models import DoctorReport` so the existing `from
pyforge.mason.doctor import DoctorReport` (used by `tests/unit/test_cli.py`) keeps working
unchanged.

**Block If:** none identified — the epics.md ACs, AD-3/AD-4, and Story 1.9's fixture fully specify
this work.

**Never:** wire any `mason recipe` verb into `cli.py`, or create `recipe.py` — no verb exists yet
(Epic 2's later stories own that, mirroring Stories 1.5-1.7's identical "not wired in yet"
precedent); build `tests/meta/test_no_recipe_knowledge.py` or `test_adapter_sole_caller.py` —
Story 2.2's "seam guard" scope; add a `_CFE_SCRIPTS` entry or named adapter for any script beyond
`validate_recipe.py`/`submit_pr.py` — the fixture built for this story only stubs these two, and
which script backs each of Stories 2.4-2.10 is explicitly still open (epic context); those stories
add their own table entry and adapter as thin use-cases on top of this one; implement `submit`'s
two-phase (`prepare_pr --prepare-only` then `submit_pr`) composition or the `CFE_RECIPES_ROOT`
out-of-tree mechanism — Story 2.9's scope; add credential-specific handling (env filtering,
injection) — Story 2.3's scope; today's CAPTURE helper passes `env=None` to `subprocess.run`
(inherits the parent environment unmodified), which already satisfies "credentials reach CFE only
through the inherited process environment"; modify `run_streamed`, `probe_import_floor`,
`ensure_cfe_root`, or `ensure_import_floor` — shipped, tested code; `run_streamed`'s own raw
`subprocess.TimeoutExpired` stays uncaught — translating STREAM-mode's timeout into
`CfeTimeoutError` is whichever future story builds a named STREAM adapter (e.g. 2.6 `recipe
build`); touch `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`, or
`.claude/tools/conda_forge_server.py` (FR-45); move `EngineStatus`, `ImportFloorResult`,
`ResolvedCfeRoot`, or `ResolvedCfeInterpreter` into `models.py` — the architecture names
`DoctorReport` as "the one landed divergence"; the others stay where they are.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Whole stdout is valid JSON, exit 0 | `validate_recipe(args, root=..., interpreter=...)` against a mocked/fixture process | `CfeResult(returncode=0, stdout=..., stderr=..., json_body=<parsed dict>)` | none |
| Stdout carries a leading non-JSON progress line before the JSON body | `submit_pr` fixture with `MASON_FIXTURE_PROGRESS_LINE` set | `json_body` parsed correctly from the JSON-starting line onward | none |
| Stdout has no parseable JSON anywhere (plain text only) | mocked stdout of plain text | `CfeResult` returned with `json_body=None`; `returncode`/`stdout`/`stderr` still populated | none (not an exception) |
| Non-zero return code with a JSON error body present | `MASON_FIXTURE_EXIT_CODE=1` against the fixture | `CfeResult(returncode=1, ..., json_body=<parsed dict>)` returned normally | not raised — data, per AD-4 |
| Subprocess exceeds its timeout | mocked `subprocess.run` raising `subprocess.TimeoutExpired` | `CfeTimeoutError` raised, naming the script key and timeout | typed error, no traceback |
| Real end-to-end call against Story 1.9's `fake_cfe_root` fixture | `cfe.validate_recipe(...)` / `cfe.submit_pr(...)`, real subprocess, no mocking | Result matches each script's canned JSON body exactly | none |
| AD-4 static check | `pyforge/mason/` source tree | no `import`, `importlib.import_module`, or `exec` targeting CFE code anywhere | meta-test failure names the file |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/models.py` (new) -- `CfeResult` (new); `DoctorReport` (moved verbatim from `doctor.py`), importing `EngineStatus` from `.engines`.
- `src/pyforge/mason/doctor.py` (edit) -- remove the local `DoctorReport` definition and its now-unused `dataclass`/`EngineStatus` imports; add `from .models import DoctorReport`.
- `src/pyforge/mason/cfe.py` (edit) -- `_CFE_SCRIPTS` table, `_extract_json`, `_invoke_captured`, `validate_recipe`, `submit_pr`.
- `src/pyforge/mason/errors.py` (edit) -- add `CfeTimeoutError(MasonError)`.
- `tests/meta/test_dependency_direction.py` (edit) -- add the AD-4 import/importlib/exec guard.
- `tests/unit/test_cfe.py` (edit) -- mocked coverage of the new functions plus fixture-backed, real-subprocess coverage of the two adapters.
- `tests/unit/test_models.py` (new) -- `CfeResult` construction/immutability; `DoctorReport` relocation sanity.
- `tests/unit/test_errors.py` (edit) -- `CfeTimeoutError` coverage.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/models.py` (new) -- `CfeResult` frozen dataclass: `returncode: int`,
  `stdout: str`, `stderr: str`, `json_body: object | None`. Move `DoctorReport` here verbatim
  (unchanged fields, importing `EngineStatus` from `.engines`) -- FR-4, AD-3 Consistency
  Conventions ("Data shapes... in `models.py`").
- [x] `src/pyforge/mason/doctor.py` -- remove the local `DoctorReport` class and its now-unused
  `from dataclasses import dataclass` / `from .engines import EngineStatus` imports; add `from
  .models import DoctorReport` so the existing `from pyforge.mason.doctor import DoctorReport`
  import keeps working with zero test churn.
- [x] `src/pyforge/mason/errors.py` -- add `CfeTimeoutError(MasonError)`: constructor
  `(script: str, timeout: float)`, identifier `cfe:timeout`, message naming the script key and the
  timeout value in seconds -- FR-4, AD-4, NFR-14.
- [x] `src/pyforge/mason/cfe.py` -- add `_CFE_SCRIPTS: dict[str, str] = {"validate_recipe":
  "validate_recipe.py", "submit_pr": "submit_pr.py"}` (relative to the CFE root's
  `.claude/scripts/conda-forge-expert/`, a local re-declaration of that subpath mirroring the
  sanctioned `_ENV_CFE_ROOT`/`_ENV_CFE_PYTHON` duplication pattern -- `cfe.py` is the one module
  unrestricted by AD-3's carve-out).
- [x] `src/pyforge/mason/cfe.py` -- add `_extract_json(stdout: str) -> object | None`: try
  `json.loads(stdout)` whole; on `JSONDecodeError`, regex-search (`re.MULTILINE`) for the first
  `{`/`[` at the start of a line and parse from there; return `None` if neither succeeds -- FR-4.
- [x] `src/pyforge/mason/cfe.py` -- add `_invoke_captured(script_key: str, args: Sequence[str], *,
  root: Path, interpreter: str, timeout: float) -> CfeResult` (private): builds `script_path = root
  / ".claude" / "scripts" / "conda-forge-expert" / _CFE_SCRIPTS[script_key]`; validates `timeout`
  is finite and positive (mirrors `run_streamed`'s own guard -- a direct caller may bypass
  argparse); runs `subprocess.run([interpreter, str(script_path), *args], capture_output=True,
  text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=timeout,
  check=False)`; on `subprocess.TimeoutExpired`, raises `CfeTimeoutError(script=script_key,
  timeout=timeout)`; otherwise returns `CfeResult(returncode=completed.returncode,
  stdout=completed.stdout, stderr=completed.stderr, json_body=_extract_json(completed.stdout))` --
  FR-1, FR-4, AD-2, AD-3, AD-4.
- [x] `src/pyforge/mason/cfe.py` -- add `validate_recipe(args: Sequence[str], *, root: Path,
  interpreter: str, timeout: float | None = None) -> CfeResult` and `submit_pr(args: Sequence[str],
  *, root: Path, interpreter: str, timeout: float | None = None) -> CfeResult`: each calls
  `_invoke_captured` with its own table key and a per-operation default timeout when `timeout` is
  `None` (`validate_recipe` 120.0s, `submit_pr` 300.0s -- both mirroring the real MCP server's own
  existing per-operation defaults, `.claude/tools/conda_forge_server.py`) -- FR-1, FR-7, FR-8.
- [x] `tests/meta/test_dependency_direction.py` -- add an AST-based test asserting no `.py` file
  under `pyforge/mason/` contains a call to `importlib.import_module` or the `exec` builtin
  anywhere in the tree (no allowlist -- this ban is unconditional, unlike the `subprocess`
  allowlist above it); include synthetic-tree regression fixtures proving the detector fires on
  each form -- AD-4.
- [x] `tests/unit/test_cfe.py` -- mocked (`subprocess.run` patched) coverage of every I/O-matrix
  row: whole-JSON stdout, leading-progress-line stdout, no-JSON stdout (`json_body=None`),
  non-zero-returncode-is-data, `TimeoutExpired` -> `CfeTimeoutError`; plus real-subprocess coverage
  of `validate_recipe`/`submit_pr` against the `fake_cfe_root` fixture (mirroring
  `test_fake_cfe_root_fixture.py`'s style), proving each adapter's result matches the fixture's
  canned JSON exactly.
- [x] `tests/unit/test_models.py` (new) -- `CfeResult` construction and `FrozenInstanceError` on
  mutation; `DoctorReport` imported via `pyforge.mason.models` and via `pyforge.mason.doctor` are
  the identical class object.
- [x] `tests/unit/test_errors.py` -- `CfeTimeoutError`'s identifier, and that its message names
  both the script key and the timeout value.

**Acceptance Criteria:**
- Given `cfe.py`, when it is authored, then it declares every CFE script Mason uses (today:
  `validate_recipe`, `submit_pr`) in one module-level table, and exposes a named adapter function
  per entry; no caller passes a script name.
- Given an adapter call, when CFE is invoked, then it runs as `[interpreter, script_path, *args]`
  via subprocess with a mandatory timeout, using a list argv and never `shell=True`.
- Given any invocation, when it completes, then a `CfeResult` is returned carrying return code,
  stdout, stderr, and a parsed JSON body when one is present, and a non-zero return code is data,
  not an exception.
- Given stdout with a leading non-JSON progress line before the JSON body, when the result is
  parsed, then the JSON body is extracted successfully.
- Given a script that exceeds its timeout, when the timeout fires, then `CfeTimeoutError` is
  raised and no orphaned child process remains.
- Given AD-4, when the codebase is inspected, then no `import`, `importlib.import_module`, or
  `exec` call targeting CFE code exists anywhere in `pyforge.mason`.
- Given the architecture's re-affirmed shapes-in-`models.py` convention, when `models.py` is
  inspected, then it holds `CfeResult` and the relocated `DoctorReport`, and every pre-existing
  import of `DoctorReport` from `pyforge.mason.doctor` still resolves unchanged.

## Spec Change Log

## Review Triage Log

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium: 2, low: 4)
- defer: 0
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found the AD-4
    meta-test (`test_dependency_direction.py`) bypassable: it recognized only the literal names
    `importlib.import_module`/`import_module`/`exec`, missing the `__import__` builtin (Python's
    own low-level import primitive) and aliased forms (`import importlib as il;
    il.import_module(...)`, `from importlib import import_module as im; im(...)`). Both were
    confirmed by direct reproduction against the detector. Added `_is_dunder_import_call` and
    `_collect_import_module_aliases` (tree-wide alias resolution feeding `_is_import_module_call`);
    added 3 regression tests covering each new bypass form. Scope boundary stated explicitly in the
    updated docstring: indirect rebinding and reflective lookups (`globals()["__import__"]`) are
    out of scope for this incidental guard — that level of rigor is Story 2.2's dedicated
    seam-guard job.
  - `[medium]` `[patch]` Blind Hunter found `_invoke_captured`'s `args` parameter has no bare-
    `str`/`bytes`/`None` guard, unlike `run_streamed`'s documented and tested guard for the
    identical footgun in the same file — confirmed by reproduction (`args="--json recipe.yaml"`
    silently explodes via `*args` into one-character argv elements). Added the same guard
    `run_streamed` already carries, plus a parametrized regression test.
  - `[medium]` `[patch]` Blind Hunter found `models.py`'s "leaf" property — explicitly reaffirmed
    in the architecture as load-bearing — has no meta-test enforcing it, unlike every other
    architectural invariant this story's siblings guard (AD-2, AD-4, AD-6). Added
    `test_models_module_imports_only_the_sanctioned_engines_sibling` (AST-based, `.engines` is the
    only permitted relative import) plus 3 regression tests, in `test_dependency_direction.py`.
  - `[low]` `[patch]` Blind Hunter found no test pins `_invoke_captured` omitting `env=` from its
    `subprocess.run` call, despite the spec's own Never boundary explicitly relying on this
    (`env=None` inherits the parent environment unmodified, which is what makes "credentials reach
    CFE only through the inherited process environment" already true today). Added an assertion to
    the existing invocation-shape test.
  - `[low]` `[patch]` Blind Hunter found the `_JSON_LINE_START_PATTERN` docstring cites AD-15 (which
    governs *writes* to the CFE surface) as the reason `_extract_json_from_stdout()` isn't imported,
    when the real reason is AD-3 (CFE path/invocation knowledge stays in `cfe.py` alone) plus that
    surface not being part of the installed package. Corrected the comment.
  - `[low]` `[patch]` Edge Case Hunter found `CfeTimeoutError` missing the `__reduce__` override
    `CfeUnresolvedError` already carries a few classes above for the same defect class:
    `Exception.__reduce__` reconstructs via `cls(*self.args)`, and `CfeTimeoutError`'s two-argument
    constructor happens to match `self.args`'s length, so a deepcopy/pickle round-trip would not
    raise but would silently corrupt `.script`/`.timeout` (bound to the identifier string and the
    built message instead). Added the override plus deepcopy/pickle regression tests, mirroring
    `CfeUnresolvedError`'s existing pair.

**Rejected findings (6):** `_extract_json` returning `None` for both "no JSON found" and a
legitimate bare JSON `null` body (Edge Case Hunter) — no CFE script investigated for this story
(`validate_recipe.py`, `submit_pr.py`) ever emits a bare `null`; both always emit a JSON object, and
FR-4's own text only promises a body "when one is present," which a content-free `null` arguably
isn't in any actionable sense — speculative, not grounded in a real script. The tolerant-parsing
fallback only recovering a *leading* progress line, never a *trailing* one (Blind Hunter) — FR-4's
text explicitly scopes tolerance to "a leading non-JSON progress line," and investigation found no
CFE script that prints anything after its JSON body; this is a documented non-goal, not a gap.
`_invoke_captured`'s unguarded `_CFE_SCRIPTS[script_key]` lookup raising a bare `KeyError` for an
unregistered key (both reviewers) — `_invoke_captured` is private with exactly two, both-correct
call sites in this same file; this is the identical class of speculative internal-misuse guard
Story 1.7's own Rejected findings already ruled out (`ensure_cfe_root(None)`) for lacking a
realistic caller. A bad `interpreter`/`root` path raising a raw, untyped `OSError`/`FileNotFoundError`
at `_invoke_captured`'s `subprocess.run` call (both reviewers) — verified against `run_streamed`'s
own `subprocess.Popen(...)` call in this same file (line 442): it is likewise unwrapped by any
try/except for `OSError`, an already-shipped, already-reviewed precedent for the identical failure
mode on the more heavily-scrutinized STREAM-mode sibling; AD-7's own rule text explicitly sanctions
this ("An unanticipated exception exits 1 with the traceback on stderr — never the interpreter's
default") for anything not named as an "anticipated" failure, and AD-4's Rule text names only
timeout expiry as requiring a distinct typed error. `CfeTimeoutError`'s message rendering `timeout`
via bare f-string interpolation without normalizing `int` vs. `float` (`"5s"` vs. `"120.0s"`) (Blind
Hunter) — cosmetic only; both forms remain fully actionable per NFR-14, and normalizing precision
is a nice-to-have, not a defect. `CfeResult` being unhashable when `json_body` holds a `dict`/`list`
(Edge Case Hunter) — standard Python behavior for any dataclass carrying a mutable field; nothing in
the spec, the architecture, or the test suite ever needs to hash, cache-key, or set-deduplicate a
`CfeResult`, and forcing hashability (`eq=False` or similar) would be speculative complexity with no
real caller.

## Design Notes

`models.py`'s "leaf" property is about import direction, not import count: it may import
`EngineStatus` from `.engines` (itself a leaf with zero internal-package imports) without
compromising the guarantee that `cli.py`/`render.py`/a future presentation layer can import
`models.py` without ever risking a cycle back through it. Only `DoctorReport` moves out of its
owning module -- the spec-pyforge-mason memlog's 2026-08-10 re-decision names it "the one landed
divergence"; `EngineStatus`, `ImportFloorResult`, `ResolvedCfeRoot`, and `ResolvedCfeInterpreter`
are deliberately left where they are.

CAPTURE mode (this story) and STREAM mode (`run_streamed`, Story 1.10) are AD-25's two invocation
modes, not one generalized over the other: CAPTURE buffers stdout whole and parses it; STREAM
forwards stderr live and never parses stdout at all. `_invoke_captured` therefore duplicates a
small amount of validation logic (`run_streamed`'s timeout/argv-shape guards) rather than sharing a
helper with it -- the Consistency Conventions forbid a shared `utils`/`helpers` module, and
`run_streamed` is shipped, reviewed, tested code this story does not touch.

Two scripts, not eight: Story 1.9 built exactly two fixture stubs (`validate_recipe.py`,
`submit_pr.py`) anticipating this story, and the epic context marks "which specific wrapped script
backs each of Stories 2.4-2.10" as still open. Declaring an adapter for a script whose exact
identity is not yet decided (e.g. `build`'s native-vs-Docker choice) would be unfalsifiable against
this story's own test fixtures.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

- **Implemented change:** extended `cfe.py` with a module-level `_CFE_SCRIPTS` table
  (`validate_recipe`, `submit_pr`), tolerant JSON-from-stdout extraction (`_extract_json`), a
  private CAPTURE-mode invocation helper (`_invoke_captured`), and two public named adapters
  (`validate_recipe`, `submit_pr`) returning the new `CfeResult`; added `CfeTimeoutError` to
  `errors.py`; created `models.py` (new dependency-direction leaf) holding `CfeResult` and the
  relocated `DoctorReport` (re-exported from `doctor.py`, zero import churn) -- FR-1, FR-4, FR-7,
  FR-8, AD-2, AD-3, AD-4, AD-25.
- **Files changed:**
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/models.py` (new) -- `CfeResult`;
    `DoctorReport` moved here verbatim.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/doctor.py` -- removed the local
    `DoctorReport` definition and its now-unused imports; re-exports it from `.models`.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` -- `_CFE_SCRIPTS`,
    `_extract_json`, `_invoke_captured` (hardened during review with a bare-str/bytes/None `args`
    guard mirroring `run_streamed`'s established pattern), `validate_recipe`, `submit_pr`.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- `CfeTimeoutError`
    (hardened during review with a `__reduce__` override for pickle/deepcopy safety, mirroring
    `CfeUnresolvedError`'s existing pattern).
  - `tests/meta/test_dependency_direction.py` -- the AD-4 import/importlib/exec guard (hardened
    during review to also catch the `__import__` builtin and aliased `importlib`/`import_module`
    forms), plus a new `models.py` leaf-import-direction guard.
  - `tests/unit/test_cfe.py`, `test_errors.py`, `test_models.py` (new) -- full coverage of the
    above, including the review-driven regression tests (args guard, `env` pinning, pickle/deepcopy
    round-trip).
- **Review findings breakdown:** 2 independent reviewers (Blind Hunter, Edge Case Hunter, no shared
  context) surfaced 12 distinct findings after dedup -- 6 patches applied (2 medium: the AD-4
  meta-test was bypassable via `__import__`/aliased imports, now closed with 3 regression tests;
  `_invoke_captured`'s `args` had no bare-str/None guard unlike its sibling `run_streamed`, now
  matched; 4 low: `models.py`'s reaffirmed "leaf" property had no enforcing test, now added; no test
  pinned `env` omission from the `subprocess.run` call, now added; a docstring cited the wrong
  architectural decision (AD-15 instead of AD-3), now corrected; `CfeTimeoutError` lacked the same
  `__reduce__` pickle/deepcopy safety `CfeUnresolvedError` already carries, now added), 0 deferred,
  6 rejected (two out-of-scope-per-FR-4 edge cases — bare JSON `null`, trailing progress lines; one
  speculative internal-misuse guard with no realistic caller, mirroring Story 1.7's own precedent;
  one OSError-handling gap verified consistent with `run_streamed`'s own already-shipped, unguarded
  `Popen()` call for the identical failure mode, and explicitly sanctioned by AD-7's text for
  "unanticipated" exceptions; one cosmetic message-formatting nit; one speculative hashability
  concern with no real caller). See the Review Triage Log for the full audit trail.
- **Follow-up review recommendation:** false -- both medium findings were test-and-validation
  hardening confined to patterns already proven elsewhere in the same file (`run_streamed`'s argv
  guard, `test_capability_tiers.py`'s alias-resolution precedent), the four low findings were
  localized (a missing regression test, a missing pin, a comment citation, a pickle edge case), and
  every patched behavior now has dedicated regression coverage (415 passing tests, up from 403
  before this review pass).
- **Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -> 415 passed (331 before this
  story; 403 after initial implementation; 415 after the review pass's 12 net new tests).
- **Residual risks:** none rated medium or higher. `_invoke_captured`/`run_streamed` both leave a
  bad `interpreter`/`root` path (spawn failure) as a raw, untyped exception by deliberate,
  now-explicitly-verified design consistency (AD-7's sanctioned "unanticipated exception" fallback)
  rather than a `MasonError` subclass -- a future story could still choose to harden this
  consistently across both functions, but nothing about this story's own scope requires it. Only two
  of the eventual eight-or-so CFE scripts have a named adapter today (`validate_recipe`, `submit_pr`)
  -- by design (spec Never boundary); Stories 2.4-2.10 each add their own table entry and adapter as
  a thin use-case on top of this port.
