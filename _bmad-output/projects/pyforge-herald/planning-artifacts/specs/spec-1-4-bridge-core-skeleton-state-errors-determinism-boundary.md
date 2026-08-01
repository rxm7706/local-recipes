<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Bridge-core skeleton — state, errors, determinism boundary'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: 'e868b607a10a8fbfba046a191d5ac637bde42f80'
final_revision: '3a0f55ae9d6dc8f7e33806e1046888554f2f840e'
---

<intent-contract>

## Intent

**Problem:** Herald's transport layer (Story 1.2) has no way to persist per-deck state, no
conflict-error types or exit-code map, and no proof its control flow stays free of inference —
so Story 1.6 (`seed`) and every later CAP story would each invent ad-hoc error handling instead
of sharing one structurally-enforced contract.

**Approach:** Add `state.py` (a `DeckState` record round-tripped against
`.herald/bridge-state.json`), extend `errors.py` with the three conflict error types plus a
fixed `exit_code_for` map, add a minimal `bridge.py` that is structurally the only module
allowed to call a `DesignTransport` port method, and add one CLI-boundary catch point in
`cli.py` every future subcommand will route through — all proven now via hand-written doubles
and a static import check, without implementing any real seed/pull/status/watch logic yet.

## Boundaries & Constraints

**Always:**
- `errors.py` gains three new direct `HeraldError` subclasses — `SeedConflictError`,
  `PullConflictError`, `ExportConflictError` — siblings of `TransportError`, not its subclasses
  (a conflict is bridge-core's own interpretation, never a transport failure).
- `errors.py` gains a sole-owned `exit_code_for(error: HeraldError) -> int`, mirroring
  `pyforge.warden.verdict.exit_code_for`'s shape (checked most-specific-first via `isinstance`,
  `TransportError`'s one entry covers every existing subclass — `AuthError`,
  `TransportUnreachableError`, `TransportCallError`, `UnconditionalWriteError` — with no entry
  of their own). Fixed values, documented beside the map: `1` = any other `HeraldError` (the
  safety net for a type this map is not yet extended to cover); `3` = the three conflict types;
  `4` = `TransportError` and everything under it. Argparse's own usage-error exit (`2`,
  `test_smoke.py`) is untouched by this map.
- `state.py` (new): a frozen `DeckState` dataclass — `project_id: str`, `etags: dict[str, str]`,
  `last_pull: str | None` (AD-5's three per-slug fields) — plus `read(state_path, slug) ->
  DeckState | None` and `write(state_path, slug, state) -> None`. One JSON file holds every
  slug's entry; `write` preserves every other slug already present. `state_path` is always an
  explicit `Path` argument — this module never assumes a cwd (mirrors `deck_pipeline.py`'s
  future explicit-`cwd` convention, AD-7). A `DEFAULT_STATE_PATH = Path(".herald/bridge-state.json")`
  constant documents the AD-5 default; resolving it against a real repo root is the caller's job
  (Story 1.6+), not this module's.
- `bridge.py` (new) — bridge-core's designated module. Contains exactly one typed seam, `run(transport:
  DesignTransport, operation: Callable[[DesignTransport], T]) -> T`, that simply calls
  `operation(transport)`: the point is that `operation`'s parameter is typed to the `DesignTransport`
  protocol only, so no future CAP function can close over a concrete adapter here. No
  seed/pull/status/watch/push_exports function body exists yet — each lands with its own story
  (1.6, 2.x, 3.x, 4.x, 5.x). Any `HeraldError` `operation` raises propagates unchanged; `bridge.py`
  never catches one.
- `cli.py` gains `dispatch(operation: Callable[[], None]) -> int` — the sole `HeraldError` catch
  point (AD-6: bridge-core raises, the CLI boundary catches). Catches `errors.HeraldError`,
  writes one structured line to stderr (tool name + error type name + message), returns
  `errors.exit_code_for(exc)`; returns `0` when `operation` completes without raising. Not wired
  to any subcommand yet (none exist) — exercised directly in tests.
- A static/import-level test (`ast`-parsing `bridge.py`'s own import statements, not a live
  import) proves bridge.py never names a concrete transport adapter (`mcp_transport`, a future
  `agent_sdk_transport`) or a recognized inference-SDK package (documented short list) — the
  epics AC's NFR-01/FR-23 proof, meaningful now and enforced as bridge.py grows.
- Add `.herald/` to the root `.gitignore` (AD-5: "repo-local, gitignored") — the first story to
  introduce the file this rule names.

**Block If:**
- A `DeckState` field a later story genuinely needs cannot be inferred from AD-5, the epics ACs,
  or `bridge-protocol.md` — HALT rather than invent an undocumented field.

**Never:**
- No `seed`/`pull`/`status`/`watch`/`push_exports` function bodies, no `registry.py`, no
  `deck_pipeline.py` — later stories (1.5, 1.6, 2.x, 3.x, 4.x, 5.x).
- No `models.py`. Story 1.2 already set the real precedent — value types live beside the module
  that owns them (`FileRead`/`ProjectRef`/etc. in `transport/base.py`, not a shared file) — so
  `DeckState` lives in `state.py`. `models.py` is deferred until a type is genuinely shared
  across multiple bridge-core modules; the architecture spine's Structural Seed diagram is
  illustrative, not binding, on this point (Story 1.2 diverged from it identically).
- No conflict-detection-from-transport-response logic. `deferred-work.md` records that a
  conflicted `write_files`/`copy_files` comes back as an ordinary success `Mapping` with no
  documented refusal shape — inventing an interpretation now would be unverified. The three new
  error types are raisable now; the story that adds real conflict interpretation (1.6 for seed,
  later for pull/export) defines how a response maps to one.
- No wiring of `dispatch`/`bridge.run` into `cli.py`'s `_build_parser()`/`main()` — no subcommand
  exists yet to call them.
- No `SIGINT`/`KeyboardInterrupt` handling in `cli.py` — out of this story's AC scope.
- Do not touch `transport/`, `README.md`'s registry section, or any planning-artifacts file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| State round-trip | `DeckState(project_id="p1", etags={"prototype":"E1"}, last_pull=None)` written for slug `"x"` to a fresh temp path, then read back | returned `DeckState` equals the written one field-for-field | No error expected |
| State read, unknown slug | file exists with an entry for `"a"` only; `read(path, "b")` | returns `None` | No error expected |
| State read, missing file | `state_path` does not exist | returns `None` | No error expected |
| State write, other slug preserved | write `"a"`, then write `"b"` to the same path | `read(path, "a")` after the second write still returns `"a"`'s original `DeckState` | No error expected |
| Dispatch, success | `operation` returns without raising | `dispatch` returns `0`, nothing written to stderr | No error expected |
| Dispatch, conflict error | `operation` raises `SeedConflictError("edits exist")` | returns `3`; stderr names `SeedConflictError` and the message | Caught by `dispatch` |
| Dispatch, transport error | `operation` raises `TransportUnreachableError(...)` / `AuthError(...)` | returns `4`; stderr names the concrete subclass | Caught by `dispatch` |
| Dispatch, unmapped HeraldError | `operation` raises a bare `HeraldError("x")` | returns `1` | Caught by `dispatch` |
| `bridge.run` propagation | `operation` (given a `DesignTransport` double) raises any of the above | the exception propagates out of `run` unchanged | Not caught by `bridge.py` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- edit -- add the three
  conflict error types + `exit_code_for`
- `src/shared/packages/pyforge-herald/src/pyforge/herald/state.py` -- create -- `DeckState` +
  `read`/`write`
- `src/shared/packages/pyforge-herald/src/pyforge/herald/bridge.py` -- create -- the `run` seam +
  the determinism-boundary contract
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- add `dispatch`
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py` -- reference
  (read-only) -- `DesignTransport` protocol `bridge.run`'s `operation` param is typed against
- `src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py:97-132` -- reference
  (read-only) -- `exit_code_for`'s sole-ownership shape to mirror
- `.gitignore` -- edit -- add `.herald/`
- `_bmad-output/implementation-artifacts/deferred-work.md` -- reference (read-only) -- the
  "conflicted write returns as an ordinary success Mapping" entry this story must not contradict

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- edit -- add
  `SeedConflictError`, `PullConflictError`, `ExportConflictError` (direct `HeraldError`
  subclasses) and `exit_code_for(error)` with the `1`/`3`/`4` map documented above
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/state.py` -- create -- `DeckState`
  dataclass + `read`/`write` against an explicit `state_path: Path`, creating parent dirs on
  write, preserving other slugs
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/bridge.py` -- create -- the `run`
  seam; module docstring records the determinism boundary and which future story adds each CAP
  function
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- add `dispatch`;
  import `errors`
- [x] `.gitignore` -- edit -- add `.herald/` near the other repo-local-state entries
- [x] `src/shared/packages/pyforge-herald/tests/test_errors.py` -- create -- `exit_code_for` for
  each error family + the fallback
- [x] `src/shared/packages/pyforge-herald/tests/test_state.py` -- create -- the I/O matrix rows
  for `state.py`, using `tmp_path`
- [x] `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- create -- `bridge.run`'s happy
  path and error-propagation rows against a hand-written `DesignTransport` double (no
  `unittest.mock`, matching the shipped suite's convention); the determinism-boundary static
  import check
- [x] `src/shared/packages/pyforge-herald/tests/test_cli_dispatch.py` -- create -- `dispatch`'s
  catching/mapping/stderr rows from the I/O matrix

**Acceptance Criteria:**
- Given the extended `errors.py` and new `state.py`/`bridge.py`, when `pyforge-herald-test`
  runs, then every test passes and no test opens a network socket (the existing egress-deny
  fixture stays active)
- Given `bridge.py` as it exists after this story, when the determinism-boundary check runs,
  then it proves zero imports of a concrete transport adapter or an LLM/inference client from
  `bridge.py` (NFR-01, FR-23)
- Given the full `HeraldError` hierarchy (Story 1.2's transport branch plus this story's conflict
  branch), when each is routed through `cli.dispatch`, then every one maps to exactly one fixed,
  documented exit code and one structured stderr line — never a silent no-op (NFR-02)
- Given `state.py`'s `write` then `read` for the same slug, then the returned `DeckState` is
  byte-for-byte equal to the one written — no data loss
- Given the new/edited files, when `pixi run -e local-recipes llms-full-check` runs, then it
  reports no new drift finding beyond the pre-existing `pyforge-herald` `undocumented-dep` entry

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 1, low 4)
- defer: 2: (low 2)
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` **The determinism-boundary static check had a blind spot large enough to
    let `from .transport import McpTransport` (the exact AD-3 violation it exists to catch)
    evade it entirely.** It only inspected `ast.ImportFrom.module` (the `X` in `from X import
    Y`), never the imported alias names (`Y`), and its forbidden-module set used snake_case
    module names, never the PascalCase class names the package's flat `transport/__init__.py`
    re-export actually makes importable. Verified live: a synthetic `from .transport import
    McpTransport` injected into `bridge.py` passed both original checks silently. Rewrote
    `test_bridge.py`'s check to (1) collect every imported alias name, not just `ImportFrom`
    module paths, (2) forbid the concrete adapter class names alongside their module names, and
    (3) assert `bridge.py` imports from `transport.base` only, never the package root (which
    re-exports adapters alongside the protocol). Re-verified: the same synthetic violation now
    fails on two independent assertions; restored `bridge.py` is byte-identical to before (no
    code change needed, only the test).
  - `[medium]` `[patch]` **`state.py` leaked raw `json.JSONDecodeError`/`KeyError`/`TypeError` on
    a corrupt or malformed `.herald/bridge-state.json`**, contradicting AD-6/NFR-02's "every
    bridge command fails structurally, never silently" — reproduced live (`read()` on an invalid-
    JSON file raised an uncaught `JSONDecodeError`). `_load_document` now raises
    `errors.HeraldError` on invalid JSON or a non-object top level (also guarding the
    exists-then-open TOCTOU race by treating a vanished file as "no state yet"); `read()` now
    raises `errors.HeraldError` when a slug's entry is missing `project_id`/`etags` or either has
    the wrong type. Four new tests cover invalid JSON, a non-object document, a missing field, and
    a wrong-typed field.
  - `[low]` `[patch]` `_FORBIDDEN_INFERENCE_PACKAGES`'s docstring claimed the list was "verified
    against `docs/reference/library-llms-full.md`," which does not hold for `openai` or
    `claude_agent_sdk` (confirmed absent from the catalog). Reworded to describe it as a
    hand-maintained denylist, not a derived/verified one.
  - `[low]` `[patch]` This spec's own Verification section claimed the whole-package `ruff
    check`/`llms-full-check` would report specific stale figures (a single pre-existing
    `undocumented-dep` finding; implicitly a clean whole-package lint). Re-run: `llms-full-check`
    is now fully clean (the referenced entry was already resolved before this story), and
    whole-package `ruff check` carries 4 pre-existing findings in `transport/`, confirmed present
    at this story's own baseline and out of this story's Boundaries (`Do not touch transport/`).
    Reworded the Verification section to match current, re-verified reality and scope the ruff
    expectation to this story's own files.
  - `[low]` `[patch]` No test pinned that the three conflict errors are direct `HeraldError`
    siblings, not `TransportError` subclasses — a distinction the module docstring calls
    load-bearing (re-parenting one would silently change its exit code from 3 to 4). Added
    `test_conflict_errors_are_not_transport_errors`.
  - `[low]` `[patch]` `test_dispatch_maps_every_transport_error_to_4_and_names_the_concrete_subclass`
    asserted only the error's class name appeared in stderr, unlike its conflict-error sibling
    test, which also checks the message text. Added the missing `str(error) in err` assertion.
- Deferred (2, both low): `state.py write()`'s unlocked read-modify-write of the whole
  slug-keyed document can lose a concurrent writer's update to a different slug (the atomic
  temp-file-plus-`os.replace` prevents corruption, not lost updates) — latent today (no caller
  writes concurrently yet), real risk lands with a future multi-process `watch` loop (Story 4.x);
  `write()`'s unguarded `parent.mkdir()` raises an unhandled `NotADirectoryError`/`FileExistsError`
  instead of a `HeraldError` if a path component already exists as a plain file — much rarer than
  the JSON-corruption cases already patched, nothing in this repo creates that shape today. Both
  appended to `deferred-work.md`.
- Rejected as noise (2, both by-design, not gaps): `cli.dispatch`'s zero-arg
  `Callable[[], None]` vs. `bridge.run`'s `Callable[[DesignTransport], T]) -> T` composition
  being "unowned" — the spec's own Never clause explicitly defers wiring them together to Story
  1.6, which is precisely this story's intended scope boundary, not a gap; Story 1.4 landing
  before Story 1.3 (fallback transport, still backlog) meaning AD-4 is only exercised against one
  real adapter plus a hand-written double — by design per the epic's own Cross-Story Dependencies
  (1.3 is explicitly not a prerequisite for 1.4).

### 2026-07-30 — Follow-up review pass

- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 3, low 5)
- defer: 0
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` **The rewritten determinism-boundary guard (last pass's own high fix) was
    still evadable by three ordinary import forms, each verified live:** `from . import
    transport` (AST gives `module=None`, which the `node.module`-only reading dropped, and the
    bound name `transport` was in no denylist), plain `import pyforge.herald.transport[.mcp_transport]
    as x` (the `ast.Import` branch kept only the first dotted segment, `pyforge`, and the module
    allowlist inspected `ImportFrom` nodes only), and `from anthropic import Anthropic` (only leaf
    alias names were collected, never the `ImportFrom` module, so the inference denylist never saw
    `anthropic`). Rewrote the checkers: `_import_statements` preserves full dotted paths and
    reconstructs relative dots from `ImportFrom.level`; `_all_identifiers` scans every `Name`,
    `Attribute`, `ImportFrom` module segment, and import alias (so `t.McpTransport` attribute
    traversal and a bare `__import__` are caught too); the transport rule now permits exactly the
    `from <...>.transport.base import <names>` form and nothing else. Dropped the dead
    `".transport.base"` allowlist entry and the redundant segment condition; added
    `_FORBIDDEN_DYNAMIC_IMPORT_NAMES` (`importlib`/`import_module`/`__import__`) with the static
    check's inherent runtime-import limit now documented instead of implied away. Added 17
    parameterized self-pinning tests feeding each known evasion form to the checkers — which
    immediately proved their worth: the first draft of `_all_identifiers` itself missed
    `ImportFrom.module` (the exact blind-spot class under repair) and the new tests caught it
    before it shipped.
  - `[medium]` `[patch]` `state.py`'s read path still leaked two raw exception families despite
    last pass's corrupt-file fix — `UnicodeDecodeError` on a binary-corrupt file
    (`JSONDecodeError`'s *sibling* under `ValueError`, not a subclass, so the
    `except json.JSONDecodeError` never fired) and non-`FileNotFoundError` `OSError`s
    (`PermissionError`, `IsADirectoryError` when `state_path` is a directory) — both reproduced
    live escaping `dispatch`. `_load_document` now catches `(ValueError, OSError)` (with
    `FileNotFoundError`'s "no state yet" branch deliberately first) and wraps them as
    `HeraldError`. Two new tests: binary-corrupt file, `state_path`-is-a-directory.
  - `[medium]` `[patch]` `read()`'s shape validation was half-done: non-string `etags` *values*
    and an any-typed `last_pull` passed silently (verified live: `etags={"a": 5}`,
    `last_pull=["not","a","ts"]` both returned a type-lying `DeckState`), deferring the failure
    to a far-away bare `TypeError` in Story 2.x+. `read()` now validates every field's declared
    type (`etags` values all `str`, `last_pull` `str | None`). Two new tests.
  - `[medium]` `[patch]` `write()`'s filesystem failures (`mkdir` over a plain `.herald` file,
    `mkstemp` in a read-only tree, `os.replace` onto a directory) all leaked raw `OSError`s
    through the AD-6 contract. All now wrapped as `HeraldError` naming the slug and path. This
    code-level fix also subsumes the prior pass's deferred mkdir-only ledger entry — the ledger
    entry itself is left untouched for the orchestrator to disposition.
  - `[low]` `[patch]` `write()`'s cleanup ran an unconditional `os.close(handle)` after the
    `with` had already closed the fd — a latent double-close that, under a future multi-threaded
    `watch` loop, could close an unrelated file that recycled the fd number. The raw fd is now
    closed only in the one branch where `os.fdopen` itself raised (before ownership transfer).
  - `[low]` `[patch]` `write()` over a corrupt existing file blocks forever (via
    `_load_document`) but the docstring never admitted `write` could raise at all, and no test
    covered the branch. Documented the contract (a corrupt file blocks writes deliberately —
    clobbering would destroy every other slug's entry; recovery is deleting the file) and added a
    test pinning that the corrupt file survives the failed write untouched.
  - `[low]` `[patch]` `dispatch`'s "one structured stderr line" contract broke on any
    newline-bearing message (verified live: two lines, the second prefix-less). Messages are now
    flattened with `" ".join(str(exc).splitlines())`; docstring updated; test added asserting
    exactly one terminating newline.
  - `[low]` `[patch]` The epics AC's literal scenario — a transport double raising each error
    type in turn, caught exactly once at the CLI boundary — was proven only as two disconnected
    halves (`bridge.run` propagates; `dispatch` catches), never composed. Added a parameterized
    `dispatch(lambda: bridge.run(transport, operation))` test asserting the mapped exit code and
    exactly one stderr line per family (conflict → 3, transport → 4, bare → 1). Distinct from the
    prior pass's correctly-rejected production-wiring concern: this needs no wiring.
  - `[low]` `[patch]` The `.gitignore` `.herald/` pattern was unanchored, so a future tracked
    fixture like `tests/fixtures/.herald/…` anywhere in the tree would be silently untrackable.
    Anchored to `/.herald/` (AD-5 puts the store at the repo root only) and verified both
    directions with `git check-ignore`.
- Deferred: none — every finding this pass anchors in code this story created, so all were fixed
  in place; nothing new was appended to `deferred-work.md` (and per the run instruction, no
  existing entry was modified).
- Rejected as noise (2): non-`HeraldError` exceptions escaping `dispatch` — catching only
  `HeraldError` is AD-6's own design (the spec scopes `dispatch` to exactly that), the in-diff
  sources of raw exceptions were the `state.py` leaks fixed above, and a last-resort net belongs
  to `main()` in a later story per the module's own docstring; `DeckState` being
  `frozen=True` yet unhashable (dict field) and shallowly mutable via `etags` — the field shape
  `etags: dict[str, str]` is spec-mandated (AD-5), unhashability is inherent Python semantics for
  a dict-bearing frozen dataclass, and no current or planned consumer hashes or mutates it.

### 2026-07-30 — Second follow-up review pass

- intent_gap: 0
- bad_spec: 0
- patch: 14: (medium 1, low 13)
- defer: 0
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` **`state.write` still leaked raw `TypeError` through the AD-6 contract
    and could manufacture its own "corruption"** — all live-verified: a non-serializable `etags`
    value escaped as a bare `json.dump` `TypeError` (the previous pass's wrap named `OSError`
    only), an `int` slug was silently laundered into the string `"5"`, and a type-lying
    `DeckState` (`etags={"a": 5}`) persisted fine only for `read()` to reject it as a malformed
    entry one process later. `write()` now refuses a non-string slug and validates every
    `DeckState` field up front via `_fields_problem` (shared with `read`, so both sides of the
    round-trip enforce one shape), and the final wrap covers `(OSError, TypeError, ValueError)`.
    Three new tests.
  - `[low]` `[patch]` Importing `bridge` executed `transport/__init__.py` and eagerly loaded the
    concrete `McpTransport` into `sys.modules` — the determinism boundary held in the file's AST
    but not at runtime (the external `mcp` SDK stays unloaded only because `mcp_transport`'s own
    SDK import is deliberately lazy). The `transport.base` import is now `TYPE_CHECKING`-only,
    and a new subprocess test pins that a fresh `import pyforge.herald.bridge` loads nothing
    from the transport package.
  - `[low]` `[patch]` `read()` conflated a hand-edited `"slug": null` entry with an absent one
    (returned `None` instead of failing structurally). `_MISSING` sentinel + test.
  - `[low]` `[patch]` `_load_document`'s `exists()` pre-check silently misread stat-failures
    (unsearchable parent, plain-file parent component, symlink loop) as "no state yet" —
    `Path.exists` returns `False` whenever the stat fails. Dropped the pre-check; `open()`'s
    `FileNotFoundError` is now the sole "no state yet" authority, which also removed the TOCTOU
    race outright. One existing test updated (a plain-file parent now fails the pre-write load
    with "could not be read") + one new read-path test.
  - `[low]` `[patch]` `json.load` raises `RecursionError` (not a `ValueError`) past its nesting
    limit — leaked raw. Added to the wrap tuple + test.
  - `[low]` `[patch]` The dynamic-machinery denylist omitted `eval`/`exec`/`getattr` —
    `exec("imp" + "ort anthropic")` and `getattr(h.transport, "Mcp" + "Transport")` passed every
    check (live-verified). All three added, with new evasion-pin cases.
  - `[low]` `[patch]` The inference denylist missed `fastmcp` (in this repo's own pixi envs),
    `litellm`, `genai`, `langchain`/`langchain_core`/`langgraph`, `groq`, `mistralai`, `cohere`.
    Added.
  - `[low]` `[patch]` The adapter denylists hardcoded names (the repo's derive-don't-declare
    rule): a Story-1.3 adapter under any other name would be silently uncovered. Both sets are
    now derived from the live package (`pkgutil` submodules except `base`; `transport.__all__`
    minus `base`'s exports — which also swept in the adapter's companions `DesignCredential` /
    `resolve_design_credential` / `DESIGN_MCP_URL`), unioned with the speculative Story-1.3
    names, plus a coverage-pin test that fails if the derivation ever goes blind.
  - `[low]` `[patch]` The guard swept `bridge.py` only while the claim is "bridge-core" —
    `state.py` could have gained `import anthropic` unnoticed. The adapter/inference/dynamic
    checks now parametrize over `bridge`/`state`/`errors`, and `state`/`errors` additionally
    must not name `transport` at all.
  - `[low]` `[patch]` `write()`'s docstring claimed "a crash mid-write can never leave a
    half-written file" — true for process crashes only (no fsync). Scoped the claim and named
    the shared limit with the mirrored warden writer.
  - `[low]` `[patch]` The docstring-claimed `state_path`-is-a-directory write refusal had no
    test. Added (the pre-write load trips first; the write-side wrap covers the racing variant).
  - `[low]` `[patch]` All four malformed-entry read failures shared one message naming no field.
    `_fields_problem` now names the offending field and its expected type; test added.
  - `[low]` `[patch]` `bridge.py`'s docstrings overclaimed "structurally impossible ... to close
    over a concrete adapter" — Python never enforces annotations, and a closure formed elsewhere
    is out of this module's reach. Reworded both docstrings to state what is actually enforced
    (the seam's protocol-typed handoff plus the AST guard on this file's source).
  - `[low]` `[patch]` `test_fake_transport_conforms_...` proves method *presence* only
    (`runtime_checkable` compares no signatures); its docstring now says so instead of implying
    full conformance.
- Deferred: none — the sole defer-shaped finding this pass surfaced (concurrent
  read-modify-write lost-update in `state.write`) was already appended to `deferred-work.md` by
  the first review pass; per the run instruction that existing entry was left untouched and
  nothing new needed appending.
- Rejected as noise (5): non-`HeraldError` exceptions escaping `dispatch` — AD-6 by design,
  re-rejected on the prior pass's grounds, and the in-diff raw-leak sources are now genuinely
  closed by the write-side fixes above; suppressing a broken-stderr `OSError` inside `dispatch`'s
  print — an environment failure whose suppression would mask diagnostics; the concurrent
  lost-update re-report — already ledgered, the orchestrator owns it; `write()` re-serializing
  another slug's malformed entry unvalidated — by design, write owns only its slug and
  validating others would block unrelated writes while destroying nothing; `os.replace` leaving
  `mkstemp`'s 0600 mode — a single-user, repo-local, gitignored operational file, owner-only is
  acceptable.

### 2026-07-30 — Third follow-up review pass

- intent_gap: 0
- bad_spec: 0
- patch: 10: (medium 3, low 7)
- defer: 0
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` **The dynamic-machinery denylist (grown eval/exec/getattr across two
    prior passes) was still evadable by the same machinery one name over** — all live-verified
    by the reviewers against the real guard functions: `sys.modules["…mcp_transport"]` fishes an
    already-loaded adapter out by string key without importing anything (so the runtime
    subprocess probe stays green too), `vars(mod)[…]`/`mod.__dict__[…]` substitute for the
    denied `getattr`, `pkgutil.resolve_name("…transport:McpTransport")` is a full dynamic
    import under another name, and `operator.attrgetter`/`globals()` are the same machinery
    again — and `bridge.py` specifically lacked the bare-`transport`-identifier ban that covers
    `state`/`errors`, so `vars(h.transport)` passed every check there. Extended
    `_FORBIDDEN_DYNAMIC_IMPORT_NAMES` with `__dict__`, `__getattribute__`, `attrgetter`,
    `globals`, `locals`, `modules`, `pkgutil`, `resolve_name`, `runpy`, `vars`; documented the
    sys.modules route in the denylist docstring; pinned all six new evasion forms in the
    parameterized evasion tests.
  - `[medium]` `[patch]` **`_BRIDGE_CORE_MODULES` was hand-declared while every denylist in the
    same file is derived** — Story 1.5's `registry.py` (named in `state.py`'s own docstring)
    would have landed unswept with nothing failing to force its inclusion: the repo's
    derive-don't-declare failure mode verbatim. Added
    `test_bridge_core_sweep_covers_every_non_excluded_package_module`, which derives the
    package's module list via `pkgutil` and fails until any new module is either swept or
    explicitly excluded with cause (`cli` = AD-2 CLI layer, `transport` = AD-3 adapter side).
  - `[medium]` `[patch]` **`read()` silently ignored entry fields outside the `DeckState`
    schema, and the natural read-modify-write path then dropped them permanently** (both
    live-verified: a `"future_field"` survived read and vanished after the write-back; a
    hand-edit typo like `"lastpull"` was silently ignored, its intended value lost while the
    entry still read as valid). Now a structural failure naming the unknown field(s), symmetric
    with the missing/mis-typed-field checks — an out-of-schema entry is exactly the "type-lying
    tolerance" the prior passes eliminated, and strict read-side rejection also makes the
    write-side data loss unreachable via the read-modify-write flow. `_DECK_STATE_FIELDS`
    documents the schema; test covers the typo case.
  - `[low]` `[patch]` A hand-edited duplicate slug key was silently last-wins-normalized by
    `json.load` (the earlier block discarded on read, erased permanently on the next write) —
    the one hand-edit shape that did not fail structurally. `_load_document` now loads with an
    `object_pairs_hook` refusing any duplicated key; the `ValueError` wraps into the existing
    `HeraldError` path; test added.
  - `[low]` `[patch]` Slug validation was asymmetric: `write(path, 5, …)` refused structurally
    while `read(path, 5)` returned `None` (JSON keys are strings, so `.get(5)` can never match)
    — a caller bug masked as "no state yet", which for Story 1.6 means silently driving a fresh
    seed instead of failing. `read` now mirrors `write`'s non-string-slug refusal; test added.
  - `[low]` `[patch]` `write()` with a non-`DeckState` `state` (plain dict, duck-typed
    stand-in) leaked a raw `AttributeError`/`TypeError` through the AD-6 contract
    (live-verified) while policing the equally-programmer-error slug type. Added an
    `isinstance(state, DeckState)` refusal; test added.
  - `[low]` `[patch]` The write-path wrap tuple omitted `RecursionError` while the load side
    deliberately catches it — a document parsed under the limit but encoded over it would leak
    raw. Added to the tuple with the asymmetry documented.
  - `[low]` `[patch]` The inference denylist omitted packages clearing its own
    foreseeable-reach bar: the legacy Google segment `generativeai` (a Gemini MCP server is in
    this repo's own tool config), `vertexai`, `boto3` (Bedrock), and the local-inference stack
    (`transformers`, `vllm`, `llama_cpp`, `huggingface_hub`). All added.
  - `[low]` `[patch]` `dispatch` flattened newlines but passed other control bytes through to
    the "one structured stderr line" — live-verified `\x1b[2K`/`\x08` sequences that can erase
    or spoof the structured prefix on a terminal. Every non-printable character is now
    flattened to a space; docstring updated; test added.
  - `[low]` `[patch]` `write()`'s docstring stated the crash-atomicity and fsync limits but not
    the concurrency one, inviting a later CAP story to assume atomic-replace means
    concurrency-safe. Added the explicit limitation sentence (lost-update under concurrent
    writers, pointing at the deferred-work ledger entry) — docstring only; the ledgered code
    fix stays the orchestrator's to disposition.
- Deferred: none — the only defer-shaped findings this pass re-surfaced (concurrent
  lost-update) were already appended to `deferred-work.md` by the first review pass; per the
  run instruction that entry was left untouched and nothing new needed appending.
- Rejected as noise (5): the concurrent lost-update *code* re-report — already ledgered, the
  orchestrator owns it (its docstring half was patched above); the state file's 0600
  `mkstemp`-inherited mode — re-adjudicated by-design on the prior pass's grounds (single-user,
  repo-local, gitignored operational file); `dispatch`'s stderr `print` itself raising on a
  closed/broken stderr — prior pass's adjudication stands (suppression would mask an
  environment failure; a last-resort net belongs to `main()` in a later story per its own
  docstring); `test_default_state_path_is_the_ad5_default` being a tautology — it still pins
  the constant against accidental edits, cosmetic at worst; the repo-level "maintenance label
  on the eventual PR" process note — not a code finding, recorded in the run result instead.

## Design Notes

**Exit-code map is fixed, not derived.** `1`/`3`/`4` are arbitrary but must never be
re-numbered once chosen (a later story extending the map only ever *adds* an isinstance entry
above the `TransportError` line, never renumbers an existing one, or every already-shipped
caller silently changes meaning).

**Why the CLI-boundary catch lives in `cli.py`, not `bridge.py`.** AD-6 splits raising
(bridge-core) from catching (the CLI boundary); AD-2 makes `cli.py` the CLI layer. `cli.py`'s own
Story 1.1 docstring already earmarks this landing point: "no `exit_code_for` projection... those
land once there is an actual bridge operation."

**Why `bridge.run` looks almost trivial.** `return operation(transport)` is the whole body. The
value isn't runtime logic — it's the type signature: `operation: Callable[[DesignTransport], T]`
makes it structurally impossible for a future CAP function to reach a concrete adapter through
this seam, which is exactly what AD-3 requires and what the determinism-boundary test verifies
by inspecting `bridge.py`'s imports.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: all tests pass (241 passed, 2
  pre-existing skips as of the third follow-up pass), no new skips, egress-deny fixture
  unbroken
- `pixi run -e pyforge-herald pyforge-herald-build` -- expected: unchanged build success (no
  manifest touched this story)
- `pixi run -e local-recipes llms-full-check` -- expected: clean (as of this story's landing the
  repo carries no drift at all; do not assume a specific pre-existing finding count, re-run and
  compare)
- `ruff format --check .` (from the package root) -- expected: clean
- `ruff check .` on this story's new/edited files specifically -- expected: clean. The
  whole-package `ruff check .` carries 4 pre-existing findings in `transport/` (2x `FURB188` in
  `base.py`, 1x `SIM117` each in `mcp_transport.py` and `tests/test_transport_base.py`),
  confirmed present at this story's own baseline commit and out of this story's Boundaries (`Do
  not touch transport/`) -- do not expect the whole-package command to report clean

## Auto Run Result

**Run type:** follow-up review pass (third) on a `done` spec — review-only iteration, no new
feature scope.

**Summary of implemented change:** two independent reviewers (adversarial + edge-case) swept
the full story diff (baseline `e868b607` → `e28ef42d`); 10 deduplicated findings were patched
in place, 5 rejected as noise, 0 deferred (nothing new appended to `deferred-work.md`; the
pre-existing concurrent lost-update entry was left untouched per the run instruction). The
patches harden three surfaces: (1) `state.py` now enforces the full `DeckState` schema on both
sides of the round-trip — unknown/typoed entry fields, duplicate JSON keys, a non-string slug
on `read`, and a non-`DeckState` state on `write` all fail structurally as `HeraldError`, and
the write-path wrap gains `RecursionError`; (2) the determinism guard closes the
`sys.modules`/`vars`/`__dict__`/`pkgutil.resolve_name`/`attrgetter`/`globals` evasion class,
gains 7 more inference-SDK names, and derives a coverage pin so Story 1.5's `registry.py`
cannot land unswept; (3) `cli.dispatch` flattens all non-printable characters (not just
newlines) out of its one structured stderr line.

**Files changed (commit `3a0f55ae`):**
- `src/pyforge/herald/state.py` — schema-strict read/write validation, duplicate-key-refusing
  loader, concurrency-limit docstring
- `src/pyforge/herald/cli.py` — control-char-safe `dispatch` stderr line
- `tests/test_bridge.py` — extended dynamic-machinery + inference denylists, sweep coverage
  pin, 6 new pinned evasion forms
- `tests/test_state.py` — 4 new tests (unknown field, duplicate keys, non-string slug read,
  non-`DeckState` write)
- `tests/test_cli_dispatch.py` — 1 new test (control-char flattening)

**Review findings breakdown:** patch 10 (medium 3, low 7) — all fixed; defer 0; reject 5.

**Verification performed:** `pyforge-herald-test` 241 passed / 2 pre-existing skips;
`pyforge-herald-build` builds sdist+wheel clean; `llms-full-check` clean (231 deps covered);
`ruff format --check .` clean; `ruff check` clean on all story files (whole-package carries
only the 4 documented pre-existing `transport/` findings).

**Follow-up review recommendation:** true — 10 patched findings including 3 medium, with real
behavior changes on data-handling paths (`state.read`/`state.write` now reject shapes they
previously tolerated) and another determinism-guard extension; volume and behavior impact
clear the significance bar even though each fix is individually small.

**Residual risks:** the static determinism denylist is inherently open-ended (documented as
deliberate — a denylist of machinery names can always be extended; string-smuggling past
`eval`-class machinery is invisible to AST by design); the concurrent lost-update in
`state.write` remains open in `deferred-work.md` (orchestrator-owned); when this branch
reaches a PR to `rxm7706/local-recipes` it touches files outside `recipes/` (`.gitignore`,
`src/`), so the `maintenance` label is required at PR-open time per the repo's always-on CI
gate.

