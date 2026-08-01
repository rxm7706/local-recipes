<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Credential/environment-hygiene check (FR-3)'
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: 'bcb74547fcb11eae2036d880eb92d44250ed72d9'
final_revision: '7949053004e16c2187664b7d0abad971ea1c5662'
review_loop_iteration: 0
followup_review_recommended: true
context: [
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
  '{project-root}/src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py',
  '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/hygiene.py',
  '{project-root}/.claude/skills/conda-forge-expert/scripts/_http.py',
  '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md',
]
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Doctor has no way to catch the known `_http.py` class of bug — an env-var-sourced credential attached to every outbound request with no destination-host gate — short of a human remembering it. FR-3 requires a new `doctor check --env` category; unlike Stories 1.2/1.3, no existing instrument wraps this, so it is Doctor's first hand-written detector.

**Approach:** Add `doctor.checks.env_hygiene`, an `ast.parse`-only scanner walking `*.py` files under a target directory for a direct env-var-read (`os.environ.get`/`os.getenv`/`os.environ[...]`) feeding a header/auth-dict subscript assignment (`headers[...] = ...`, keyed on a variable whose name contains "header") with no enclosing `if`/`elif` test referencing a host-like name (`host`/`netloc`/`hostname`/`domain`). Register it in Story 1.3's `checks.registry` as category `"env"`, one `CheckSpec(name="unconditional-credential-injection")` — the tripwire tests `test_list_checks_unknown_category_returns_empty_tuple_no_exception` and `test_every_cataloged_category_is_dispatchable_by_gather_one` (both left by Story 1.3 for this exact moment) must be updated, not deleted.

## Boundaries & Constraints

**Always:**
- `ast.parse` only — never `exec`/`eval`/dynamic `import`/`importlib` of scanned source (mirrors warden's own extraction discipline); a meta-test (mirroring `test_sources_warden_no_subprocess.py`'s style) AST-scans `env_hygiene.py`'s own source for such call sites and positively proves it fires on a synthetic violation.
- Every emitted `Finding` uses `source=Source.ENV_HYGIENE`, `check="unconditional-credential-injection"`, `status=DoctorStatus.WARN` (Design Decision below), `evidence={"file": str, "line": int, "var_name": str | None}` — no new `Source`/`DoctorStatus` member (Story 1.1's closed taxonomy).
- Detection matches ONLY a **direct** expression: the env-read call/subscript must appear within the assigned value's own expression subtree — no intermediate-variable or dict-literal-construction tracking. Deliberate v1 boundary (see Design Decisions), not a bug.
- `"env"` is registered in `registry._CATALOG` with exactly one `CheckSpec`, and `gather_one` gets an `"env"` dispatch branch calling `env_hygiene.gather(target)` and filtering by `check`, mirroring the `"engines"` branch's exact shape — no redesign of `gather_one`'s filter semantics.

**Block If:** `.claude/skills/conda-forge-expert/scripts/_http.py`'s `auth_headers_for` no longer contains the unconditional `if os.environ.get("JFROG_API_KEY"): headers["X-JFrog-Art-Api"] = os.environ["JFROG_API_KEY"]` shape (~lines 213–215) — re-verify against the live file before implementing; if the pattern is gone, HALT and name the mismatch.

**Never:**
- Never modify `doctor.models`, `doctor.verdict`, the `DoctorReport` schema, or `sources/warden.py`'s OK/FAIL mapping (frozen, Stories 1.1/1.2/1.3).
- Never add multi-hop variable tracking, dict-literal-construction detection, or any pattern beyond the direct-expression match — explicitly deferred (see Design Decisions).
- Never execute, import, or otherwise run scanned source code.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Direct unconditional injection | `if os.environ.get("X"):\n    headers["Y"] = os.environ["X"]` | One `Finding(status=WARN, evidence={file, line, var_name="X"})` | No error |
| Golden fixture | target dir containing the real `_http.py` | Findings include one for `JFROG_API_KEY` at its live line | No error |
| Host-scoped credential attach | `if host == "internal.example.com":\n    headers["Authorization"] = os.environ.get("T")` | No Finding — enclosing `if` test references `host` | No error |
| No matching pattern | A `.py` file with no env-read/header shape | Empty tuple | No error, no exception |
| `gather_one("env", "unconditional-credential-injection", target)` | Same target as a direct positive case | Equals the `check`-matching `Finding` filtered from `env_hygiene.gather(target)` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py` (NEW) -- `gather(target: Path) -> tuple[Finding, ...]`; an `ast.NodeVisitor` tracking a stack of enclosing `ast.If.test` nodes to implement the host-scope check (no precedent for this in the repo — first NodeVisitor-based scanner; every existing AST guard uses a flat `ast.walk`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` -- add `"env"` to `_CATALOG` (one `CheckSpec`) and a `gather_one` dispatch branch calling `env_hygiene.gather`; the module's existing dispatch-coherence comment (line ~112-117) already anticipates this edit.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/hygiene.py` (`has_adjacent_python_source`, ~line 172) -- the bounded, `.git`-pruning `os.walk` idiom (entry cap, `onerror` handling) to mirror for `env_hygiene`'s file-discovery walk.
- `src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py` -- the AST-scan-the-module-itself + synthetic-positive-proof meta-test idiom to mirror for the no-execution guard.
- `src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py` -- already scans every module under `pyforge.doctor` (`PACKAGE_DIR.rglob("*.py")`); `env_hygiene.py` is automatically covered, no edit needed there.
- `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py` -- `test_list_checks_unknown_category_returns_empty_tuple_no_exception` (line ~60) asserts `list_checks(category="env") == ()`; this line must change now that `"env"` is registered — Story 1.3's own comment names this test as the deliberate tripwire for this moment.
- `.claude/skills/conda-forge-expert/scripts/_http.py` (`auth_headers_for`, ~lines 186-235) -- the golden fixture, read-only reference; scanned as real, unmodified source, never copied into a synthetic string for the golden-fixture test.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- append one NEW entry (never edit existing) noting the v1 scope limits below.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py` -- new module: `gather(target: Path) -> tuple[Finding, ...]` walks `*.py` files under `target` (bounded `os.walk`, pruning `.git`/`__pycache__`/`.venv`/`venv`/`node_modules`/`.pixi`), AST-parses each, and runs the `_CredentialInjectionVisitor` (tracks an `if`-test guard stack; on an `Assign` whose target is `headers[...]`-shaped and whose value directly contains an env-read, checks whether any guard references a host-like name) to emit `Finding`s.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` -- register `CheckSpec(category="env", name="unconditional-credential-injection")` in `_CATALOG`; add the `"env"` branch to `gather_one` (imports `env_hygiene`, dispatches, filters by `check`).
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` (NEW) -- covers the I/O matrix: direct positive case, golden-fixture case (real `_http.py`, target scoped to `.claude/skills/conda-forge-expert/scripts/`), host-scoped negative case, no-match empty tuple, and `gather_one("env", ...)` filter-equivalence.
- [x] `src/shared/packages/pyforge-doctor/tests/meta/test_env_hygiene_no_execution.py` (NEW) -- AST-scans `env_hygiene.py`'s own source for `exec`/`eval`/`importlib`/dynamic-`__import__` call sites (zero expected) plus a synthetic-violation positive-proof test, mirroring `test_sources_warden_no_subprocess.py`'s structure.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py` -- update `test_list_checks_unknown_category_returns_empty_tuple_no_exception` to drop the now-false `list_checks(category="env") == ()` assertion (keep the `"bogus-category"` one) and add a positive assertion that `list_checks(category="env")` returns the one registered `CheckSpec`; `test_every_cataloged_category_is_dispatchable_by_gather_one` needs no edit (it already iterates `_CATALOG` generically) but must be re-verified green. (Additional fallout from registering "env" also fixed: `test_list_checks_returns_the_six_known_engine_specs`, the former `test_list_checks_filtered_by_engines_matches_unfiltered` (renamed `test_list_checks_unfiltered_returns_every_category_concatenated`), `test_list_checks_never_invokes_run_doctor_checks`, and `test_live_catalog_matches_real_warden_gather_check_names` all called unfiltered `list_checks()` and assumed only "engines" existed -- each now filters to `category="engines"` or compares against the concatenated `_EXPECTED_ALL_SPECS`, not called out individually in this spec's Code Map but required for the full suite to stay green per the Verification section.)
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- append one NEW entry: (a) direct-expression-only detection (no multi-hop/dict-literal tracking) may miss shapes like `headers = {"k": os.environ.get(...)}` or `return {"k": token}`; (b) if a future `"env"` check ever emits >1 `Finding` sharing one `check` name for the same `target`, `gather_one`'s `next(...)`-based filter (Story 1.3's established contract) silently returns only the first — noted for Story 1.5's CLI-wiring pass to weigh.

**Acceptance Criteria:**
- Given a Python file where an env-var read directly feeds a `headers[...]`-shaped assignment with no enclosing host-referencing `if`/`elif` test, when `env_hygiene.gather` scans it, then it returns a `Finding(source=ENV_HYGIENE, check="unconditional-credential-injection", status=WARN, evidence={file, line, var_name})`.
- Given the real `.claude/skills/conda-forge-expert/scripts/_http.py` as a golden fixture, when `gather` scans a target directory containing it, then the `JFROG_API_KEY` finding is present among the results.
- Given `env_hygiene.py`'s own source, when the no-execution meta-test runs, then it contains zero `exec`/`eval`/dynamic-import call sites, and the guard positively fires on a synthetic violation.
- Given a file with a host-scoped credential attach (an enclosing `if`/`elif` test referencing a host-like name), when scanned, then no `Finding` is produced for that assignment.
- Given `"env"` registered in `_CATALOG`, when `list_checks(category="env")` and `gather_one("env", "unconditional-credential-injection", target)` run, then both behave per the `"engines"` category's established registry contract (Story 1.3), and `test_every_cataloged_category_is_dispatchable_by_gather_one` / the updated `test_list_checks_unknown_category_returns_empty_tuple_no_exception` both pass.

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 1, medium 7, low 2)
- defer: 1: (medium 1)
- reject: 3: (low 3)
- addressed_findings:
  - `high` `patch` The guard stack applied a host-referencing `if`/`elif` test to BOTH branches (`node.body` and `node.orelse`), so `if host==safe: ... else: headers[...] = os.environ.get(...)` — the exact inverse-condition leak the check exists to catch — was silently invisible. Fixed `visit_If` to only extend the guard stack while visiting `node.body`; `node.orelse` runs under the prior (unextended) stack. Elif chains verified unaffected (each elif's own test is pushed while visiting its own body, per Python's nested-`If`-in-`orelse` AST shape).
  - `medium` `patch` Host-name matching used substring containment (`"host" in "ghost_mode"`), letting an unrelated variable name accidentally suppress a real finding. Changed `_references_host_like` to whole-token matching (split on `_`, exact membership).
  - `medium` `patch` An env-read used only as a ternary's `test` (deciding between two unrelated values, e.g. `"a" if os.environ.get("X") else "b"`) was flagged as if it fed the header, with a message asserting something untrue. Replaced the blind `ast.walk` in `_direct_env_read` with `_walk_value_positions`, which skips `ast.IfExp.test` but still walks `.body`/`.orelse` (so an env-read that IS a ternary's value branch is still correctly flagged).
  - `medium` `patch` `import os as o` and `from os import environ`/`getenv` evaded the detector entirely (hard-coded literal names `"os"`/`"environ"`/`"getenv"`). Added `_resolve_os_aliases` (mirrors `test_sources_warden_no_subprocess.py`'s `os_aliases` idiom), threaded the resolved name sets through the matcher functions and the visitor.
  - `medium` `patch` `headers["X"] += os.environ.get(...)` (AugAssign) was invisible — only `visit_Assign` existed. Added `visit_AugAssign`, sharing the same `_check` helper as `visit_Assign`.
  - `medium` `patch` `headers["X"] = other["Y"] = os.environ.get(...)` (chained/multi-target assignment) was invisible — `_header_subscript_target` required exactly one target. Changed it to check every target in `assign.targets`.
  - `medium` `patch` `_discover_python_files`'s `os.walk` omitted the `onerror` handling the spec's own Code Map named as part of the exemplar pattern to mirror (`hygiene.has_adjacent_python_source`) — an unreadable subdirectory silently vanished from the scan. Added an `onerror` callback and an `incomplete` return flag.
  - `medium` `patch` Hitting the 50k-entry discovery cap silently truncated the scan with zero signal in the result — a large/padded tree could hide a real leak while reporting a clean pass. `gather()` now appends one `Finding(status=WARN)` naming the scan as incomplete when either the cap or an `onerror` was hit.
  - `low` `patch` The `deferred-work.md` entry appended during implementation stated the `gather_one` first-match-only limitation as a hypothetical "future" risk; the edge-case reviewer confirmed it is live TODAY (two files, each with one match, same target). Reworded the entry to state this as confirmed, not speculative.
  - `low` `patch` Ternary-as-host-guard (`headers["X"] = os.environ.get("Y") if host==... else None`) and `match`/`case`-as-host-guard are not recognized as suppressing (guard tracking is statement-level `if`/`elif` only) — scoped out rather than chased (expression-level guard tracking is materially more complex than the fixes above, and the shape is narrower/less common than the branch-blindness and ternary-false-positive bugs). Made this boundary explicit in the module docstring so it reads as a deliberate v1 scope decision, not a silent gap.
- deferred: `medium` — `checks.registry.gather_one`'s `next(...)`-based first-match filter (Story 1.3's established, frozen contract — this story's own Boundaries forbid redesigning it) silently drops all but the first `Finding` when 2+ files each independently match under the same `check` name; confirmed reproducible by construction, not hypothetical. Logged in `deferred-work.md` for Story 1.5's CLI-wiring pass.
- rejected: `low` (x3) — `gather(target)` on a single-file (not directory) `target` silently returns `()`: matches the established `gather(target: Path)` convention across the registry (sibling `sources/warden.py` makes the same assumption, untested for file-vs-dir either), and adding dual-mode handling is unrequested scope beyond any AC. `_scan_file`'s broad `except (SyntaxError, UnicodeDecodeError, OSError): return []` silently skips one unparseable file: consistent, proportionate "degrade never crash" precedent from `sources/warden.py`, and far narrower blast radius than the whole-subtree gaps that WERE patched above. "Test coverage only exercises the documented I/O-matrix pair" is moot now that this pass added 12 new regression tests covering every patched gap.

### 2026-07-31 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 1, medium 3, low 8)
- defer: 0
- reject: 7: (low 7)
- addressed_findings:
  - `high` `patch` A parseable file with a pathologically deep expression tree (e.g. a machine-generated multi-thousand-term concatenation assigned to `headers[...]`) raised `RecursionError` out of the (recursive) visitor walk, escaping `gather()` and crashing the whole doctor run — verified live by both reviewers; violated the module's own degrade-never-crash discipline. Moved `_resolve_os_aliases` + the visitor walk inside `_scan_file`'s try and added `RecursionError` to the caught tuple; the file is skipped, the rest of the scan proceeds (regression test with a 5000-term chain plus a normal file whose finding must still surface).
  - `medium` `patch` Guard matching was polarity-blind: `if host != "internal.example.com": headers["Auth"] = os.environ.get("TOKEN")` — the exact inverse-condition leak, TRUE-branch form — was silently suppressed because the test merely *references* a host-like name. `visit_If` now swaps guarded/unguarded branches for a PURE-NEGATION test (an `ast.Compare` whose every op is `!=`/`not in`/`is not`): its body is unguarded, its else branch (which runs precisely when host == safe) is guarded. Deliberately narrow — `not host_ok(h)` / `BoolOp` negations stay conservatively suppressing (allowlist-vs-denylist is statically undecidable; boundary in the docstring + deferred-work ledger). Matches are now sorted by line in `_scan_file` since the swap changes visit order. Tests cover both branches plus `not in`.
  - `medium` `patch` The incomplete-scan sentinel reused `check=CHECK_NAME`, so `gather_one("env", CHECK_NAME, target)` either returned the sentinel *as if it were a real injection match* (no real finding present) or silently dropped the incompleteness signal (real finding sorted first) — breaking the engines precedent of a distinct, never-cataloged degradation-sentinel name (`"pyforge-warden"`). The sentinel now carries `SCAN_INCOMPLETE_CHECK_NAME = "env-hygiene"` with `evidence={"target": ...}` (the typed `{file, line: int, var_name}` contract stays exclusive to real `CHECK_NAME` findings, resolving the sentinel's contract-violating `line: None` too); registry docstring updated; addressability pinned by a new gather_one test.
  - `medium` `patch` The early-return guard idiom (`if host != safe: return` then an unguarded attach) — the dominant Python guard-clause style and the most plausible shape of a *remediated* `_http.py` — is flagged as a false positive; recognizing it needs statement-flow analysis beyond v1's enclosing-guard model. Not code-fixed (materially complex, same treatment as pass 1's ternary-as-guard scope-out): boundary made explicit in the module docstring and recorded in the deferred-work ledger as a NEW entry (with the polarity residuals and the sentinel/CLI-validation question).
  - `low` `patch` A non-directory `target` (single file, nonexistent/typo'd path) fed `os.walk`'s top-level scandir error into the pass-1 `onerror` callback, emitting a misleading "could not read some subdirectory" INCOMPLETE sentinel — a regression of pass 1's own onerror patch against the pass-1-rejected-and-affirmed silent-`()` convention. Added an `is_dir` guard returning the documented empty result; tests for both shapes.
  - `low` `patch` An env-read used only in a comprehension's `if` filter (`headers["Accept"] = ",".join(v for v in values if os.environ.get("DEBUG"))`) was flagged — the same non-value-carrying rationale as pass 1's ternary-test fix, inconsistently unapplied. `_walk_value_positions` now skips `comprehension.ifs` (iter/target still walked; env-read in the iterated source still flags — tested both ways).
  - `low` `patch` `headers["X"]: str = os.environ.get(...)` (AnnAssign) was invisible — only Assign/AugAssign were visited. Added `visit_AnnAssign` (bare annotations without a value assign nothing and are ignored).
  - `low` `patch` Tuple/list-unpacking targets (`headers["A"], x = os.environ.get("T"), 1`) were invisible — only top-level targets were inspected. `_iter_assign_checks` now pairs unpacking elements POSITIONALLY when the value is a same-length tuple/list literal (so `headers["A"], x = "static", os.environ.get("D")` does not false-positive on the element feeding `x`), else checks the whole value; one level of unpacking only, chained top-level targets keep first-match-wins.
  - `low` `patch` A walrus inside a skipped ternary test (`headers["X"] = t if (t := os.environ.get("K")) else "d"`) was invisible — the binding IS value-carrying even though the rest of the test is not. `_skipped_test_walrus_values` rescues `NamedExpr.value` subtrees from skipped `IfExp.test`/`comprehension.ifs` positions.
  - `low` `patch` `from os import *` evaded the scanner entirely (no alias branch matched `*`). Star-import now seeds both `environ` and `getenv` into the resolved name sets.
  - `low` `patch` camelCase host guards (`serverHost`, `APIHost`) were not recognized — tokens split on `_` only. `_NAME_TOKEN_SPLIT` now also splits camelCase and acronym boundaries (`ghost_mode` still correctly non-suppressing).
  - `low` `patch` Zero test coverage existed for the whole `os.getenv` detection path, `elif`-test guard accumulation, and the nested-`def` guard-stack reset despite all three being documented contract. Added dedicated tests for each (getenv call, `from os import getenv`, elif suppression, outer-guard-does-not-leak-into-nested-def).
- rejected: `low` (x7) — Golden-fixture test "hard-depends on the live `_http.py` bug remaining unfixed": that is AC2's designed tripwire (the spec's Block-If clause exists for exactly this), not a defect. `parents[6]` repo-root resolution fragility/IndexError-at-shallow-checkout: mirrors the established sibling idiom (`pyforge-warden`'s `test_currency.py`) with a deliberate skip for non-monorepo contexts. Entry cap bounds directory entries, not bytes-per-file: mirrors the spec-named exemplar (`hygiene._ADJACENT_PYTHON_SOURCE_ENTRY_CAP`); per-file size bounds are new scope. No-execution meta-guard is literal-name-only (`builtins.exec` etc. evade): matches the spec-mandated mirror of `test_sources_warden_no_subprocess.py`, whose best-effort-static bounds are already ledgered under spec-1-2. Exact-cap boundary marks a fully-scanned tree INCOMPLETE / current directory's listed files dropped on dir-count cap-hit: conservative-direction imprecision at a 50k boundary, cosmetic. `_resolve_os_aliases` unconditionally seeds `"os"` so a rebound local named `os` could false-positive: exotic beyond proportion. Incomplete-sentinel evidence doesn't distinguish cap-hit vs unreadable-subdir cause: cosmetic; the missing-root third cause is now excluded by the `is_dir` patch.

## Design Notes

**Design Decision — severity default is `WARN`, not `FAIL`.** PRD §8 Open Question 1 and epics.md's own AC (`status=warn_or_fail`) both punt this to the implementing story. Resolved here as `WARN`: AD-2 frames Doctor's exit code as an *operability* signal, reserving `FAIL` for the machine being unsound (Story 1.2's engine checks); a hand-written heuristic pattern-match — Doctor's first, with no wrap-a-proven-instrument precedent — has an unproven false-positive rate on arbitrary scanned trees, so it should surface without blocking `doctor check`'s exit code by itself in v1. `WARN` still guarantees the finding is reported (AC1/AC2), just doesn't gate.

**Design Decision — generalization boundary is the epics AC's own wording, not broader.** PRD §8 Open Question 2 asks how far past `JFROG_API_KEY` to generalize. epics.md's ACs already fix the boundary concretely: "env-var read feeds an HTTP-header/auth assignment with no accompanying host-scope conditional" — implemented as the direct-expression, `headers[...]`-keyed, if-guard-stack check below. Two other real repo shapes surfaced during investigation (`dependency-checker.py`'s `return {"X-JFrog-Art-Api": api_key}`, `gemini_server.py`'s `headers = {"x-goog-api-key": ...}` single-endpoint tool) use dict-literal construction, not subscript assignment, and are NOT required by any AC — deliberately out of v1 scope (see deferred-work.md task above), not chased speculatively.

**Sketch (illustrative, not literal code to paste):**

```python
class _CredentialInjectionVisitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path, self.findings, self._guards = path, [], []

    def visit_If(self, node):
        self._guards.append(node.test)
        self.generic_visit(node)
        self._guards.pop()

    def visit_Assign(self, node):
        if (var := _header_subscript_target(node.targets)) is not None:
            if (env_name := _direct_env_read_name(node.value)) is not None:
                if not any(_references_host(g) for g in self._guards):
                    self.findings.append((node.lineno, env_name))
        self.generic_visit(node)
```

`_header_subscript_target`: target is `ast.Subscript` on an `ast.Name` whose `.id.lower()` contains `"header"`. `_direct_env_read_name`: `ast.walk` the value subtree for `os.environ.get(...)`/`os.getenv(...)`/`os.environ[...]`, return the literal string arg if present. `_references_host`: `ast.walk` a test subtree for any `ast.Name.id`/`ast.Attribute.attr` (case-insensitive) containing `host`/`netloc`/`hostname`/`domain`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full unit + meta suite passes, including the updated registry tripwire tests and the new `env_hygiene` unit + meta tests.
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src:src/shared/packages/pyforge-warden/src python3 -m pytest src/shared/packages/pyforge-doctor/tests -q` -- substitute verification if the pixi task cannot run.

**Actual results (2026-07-30):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **135 passed** (implementation pass), **147 passed** (post-review, 12 new regression tests added for the review pass's 10 patches). No `pixi-build-python` panic in this worktree.

**Actual results (2026-07-31, follow-up review pass):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **166 passed** in 1.59s (19 new regression tests for this pass's 12 patches: recursion containment, guard polarity both branches + `not in`, sentinel split/addressability, non-directory targets, comprehension filter both ways, AnnAssign, tuple-unpacking both ways, walrus, star-import, camelCase guard, getenv x2, elif, nested-def). First run green; no `pixi-build-python` panic.


## Auto Run Result

**Status:** done (follow-up review pass, 2026-07-31; commit `7949053004e16c2187664b7d0abad971ea1c5662` on `bmad-loop/20260730-192238-c553/1-4-credential-environment-hygiene-check`).

**Summary:** Second independent review pass (Blind Hunter + Edge Case Hunter, parallel, no prior context) over the full Story 1.4 diff since `bcb74547fc`. 25 raw findings deduplicated to 19; triaged 12 patch (1 high, 3 medium, 8 low), 0 intent_gap, 0 bad_spec, 0 defer, 7 reject. All 12 patches applied and individually regression-tested; one NEW deferred-work ledger entry appended (guard-recognition v1 residuals + the now-two-category sentinel/CLI-validation question).

**Files changed this pass:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py` — RecursionError containment in `_scan_file`; pure-negation guard-polarity branch swap in `visit_If` (+ line-sorted output); incomplete-scan sentinel split onto `SCAN_INCOMPLETE_CHECK_NAME="env-hygiene"`; non-directory-target guard; comprehension-filter skip + walrus rescue in `_walk_value_positions`; `visit_AnnAssign`; tuple-unpacking targets with positional pairing (`_iter_assign_checks`); star-import alias seeding; camelCase host-token splitting; docstring boundaries (early-return idiom, negation-form limits, non-directory targets).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` — `gather_one` docstring: the never-cataloged degradation-sentinel contract now names both categories' sentinels.
- `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` — sentinel-name assertions updated; 19 new regression tests (one per patched gap, positive and negative directions).

**Review findings breakdown:** 12 patched (see the 2026-07-31 Review Triage Log entry for each finding and action), 0 deferred via triage (the ledger entry accompanies the early-return/polarity boundary patch, appended as a NEW entry per the invocation constraint — no existing entries modified), 7 rejected (spec-mandated golden-fixture tripwire, established sibling idioms, cosmetic cap-boundary imprecision, exotic shapes — reasons in the triage log).

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` → **166 passed** in 1.59s, first run, no pixi-build-python panic in this worktree. The spec's Block-If precondition re-verified live before patching (`_http.py:214-215` still carries the unconditional `JFROG_API_KEY` shape).

**Follow-up review recommendation:** `true`. This pass's changes are behavior-affecting in a security detector — the polarity swap changes which branch inherits a host guard, the sentinel split renames an emitted check name and reshapes its evidence, and six new match shapes were added — and the patched-finding volume (12, incl. 1 high crash fix) is comparable to pass 1's. Every change is pinned by a dedicated test, but the severity trend (pass 1: core semantics; pass 2: periphery) suggests one more independent pass should confirm convergence cheaply.

**Residual risks:** the early-return guard-clause idiom still WARNs on correctly host-gated code (documented boundary, ledgered — will fire on any remediated `_http.py` until a statement-flow-aware v2); negation forms beyond pure-negation Compares conservatively suppress (ledgered); `gather_one`'s first-match filter semantics for multi-file matches remain Story 1.5's decision (ledgered pass 1); the golden-fixture test reds by design the day `_http.py` is actually fixed — update the fixture expectation in the same change that fixes it.
