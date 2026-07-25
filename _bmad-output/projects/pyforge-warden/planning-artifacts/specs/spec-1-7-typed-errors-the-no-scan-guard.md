<!-- RECOVERED 2026-07-25 from a surviving bmad-loop run worktree (.bmad-loop/runs/20260718-101504-2c07/worktrees/6-2-license-axis-producer-gate-flags/_bmad-output/implementation-artifacts/spec-1-7-typed-errors-the-no-scan-guard.md); this is the ORIGINAL spec, not an epics.md regeneration. Promoted to tracked planning-artifacts/specs/ for durability. -->
---
title: 'Story 1.7: Typed errors & the no-scan guard (the fail-closed net)'
type: 'feature'
created: '2026-07-17'
status: 'done'
baseline_revision: '478738ac25d9120da359a53584d9716da4312a78'
final_revision: 'f27591f2d2'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Both epics.md ACs are already shipped and tested (Stories 1.2/1.3/1.5/1.6/2.4): `models.py` has a closed `ErrorKind`/`ErrorRecord`; `engines.py`'s `_engine_env()` types every subprocess failure incl. bounded timeouts; `cli.py`'s CLI boundary catches every seam, never a bare traceback to stdout; `verdict.compose(())` already returns `not-applicable`, never `clean`. What's undone is the "error-grammar" work three modules explicitly flag by name as Story 1.7's: every error rung hardcodes `axis=AXIS_VULNERABILITY` regardless of which engine/stage actually failed (deferred-work.md:37; forward-refs in `interfaces.py`:48/224/318, `cli.py`:63/543); the error-driver `finding_id`-vs-`findings[]` referential-integrity question was left open (deferred-work.md:13); `architecture.md`:236/261/296 still calls the shipped `errors.py`-in-`models.py` design "PLANNED"; `DeptryEngine` over-reports `deps_assessed` for purity-guard-excluded components, disagreeing with `OsvEngine`'s honest accounting for the identical exclusion (deferred-work.md:24/60); and `routing.py`:16's "arrives with Story 1.7" comment is stale (already caught by `cli.py`'s extract seam).

**Approach:** Ratify the shipped value-based `ErrorRecord` design as FR21's permanent implementation (doc-only `architecture.md` update — no raised-exception rewrite of already-tested code). Give every error rung its true axis (`AXIS_HYGIENE`/`AXIS_VULNERABILITY` per engine, new `AXIS_INGESTION` for pre-engine discovery/extract failures). Formally document + regression-test the two-namespace `finding_id` contract. Fix `DeptryEngine.deps_assessed` to subtract purity-guard exclusions, matching `OsvEngine`.

## Boundaries & Constraints

**Always:** Every error rung's `StatusDriver.axis` reflects the actual failing stage/engine — `AXIS_HYGIENE` (deptry), `AXIS_VULNERABILITY` (osv), `AXIS_INGESTION` (discovery/extract/routing failures before any engine exists) — never a blanket default. `axis` stays an open string constant (matching `models.py`'s existing "OPEN string mechanism" comment) — `AXIS_INGESTION` is added the same way, not a `StrEnum` member. `Status.ERROR`'s `error:<kind>:<subject>` driver grammar stays deliberately exempt from `findings[]`-referential-integrity — document this, don't add new runtime validation (1.1 already declared blanket enforcement "not safely expressible"; a regression test pins the contract instead). `DeptryEngine`'s `deps_assessed` fix mirrors `OsvEngine`'s existing `deps_assessed=len(synthesized.lines)` shape (subtract `len(synthesized.excluded)` from `inventory.count`). No change to `ErrorKind`'s 9-member closed set, `Status`, the verdict lattice, or any exit-code literal (`verdict.py` sole ownership untouched).

**Block If:** Nothing here — every decision resolves from evidence already in the codebase (deferred-work.md, architecture.md, named forward-reference comments), not a human judgment call.

**Never:** Do not create `errors.py` or a raised-exception hierarchy — ratify the value-based design instead; rebuilding working, tested catch sites for cosmetic reasons is out of scope. Do not attempt to detect deptry's own internal non-standard-layout resolution failures (deferred-work.md:24's other half) — deptry's JSON output carries no analyzed-count signal for this, and that entry itself assigns the full fix to a future coverage-floor gate (Story 3.1/FR19). Do not touch `hygiene.py`'s DEP001–005 table, `vuln.py`'s severity table, KEV/EPSS gating, or any config/`--fail-on` surface (Epic 3/6 scope). Do not change `ComplianceReport`/`Component`/the lattice (frozen, Story 1.1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Deptry crashes/unavailable/times out | `DeptryEngine.run` raises or binary missing | `ErrorRecord` + `Status.ERROR` rung, `driver.axis="hygiene"` | typed, exit 2 |
| Osv crashes/unavailable/times out | `OsvEngine.run` raises or times out | `ErrorRecord` + `Status.ERROR` rung, `driver.axis="vulnerability"` | typed, exit 2 |
| Discovery/extract-stage failure (malformed manifest, unreadable file, engine-factory crash pre-instantiation) | e.g. malformed `pyproject.toml` | `ErrorRecord` + `Status.ERROR` rung, `driver.axis="ingestion"` | typed, exit 2 |
| DeptryEngine's purity guard excludes ≥1 component | component(s) in `synthesized.excluded` | hygiene `AxisCoverage.deps_assessed = inventory.count - len(excluded)`, never `inventory.count` | No error — honest coverage count |
| `Status.ERROR` report driver | any error report | `driver.finding_id` uses `error:<kind>:<subject>`, NOT required to match any `findings[]` id | No error — sanctioned exception, regression-tested |
| Non-error status driver (`policy-violation`/`warn`/`indeterminate`) | any such report | `driver.finding_id` MUST equal an id present in `findings[]` | regression test enforces |

</intent-contract>

## Code Map

- `src/pyforge/warden/models.py` -- MODIFY: add `AXIS_INGESTION = "ingestion"` beside `AXIS_HYGIENE`/`AXIS_VULNERABILITY` (:33-34); extend `StatusDriver`'s docstring (:208-214) with the two-namespace `finding_id` contract (non-error statuses reference `findings[]`; `error` status uses the reserved, exempt `error:<kind>:<subject>` grammar).
- `src/pyforge/warden/interfaces.py` -- MODIFY: `Engine` Protocol (:179-184) gains `axis: str`; `EngineResult` (:137-159) gains a required `axis: str` field (ordered before the defaulted `vuln_data`); `DefaultPolicy.evaluate`'s per-error loop (:315-329) uses `result.axis` instead of the hardcoded `AXIS_VULNERABILITY`; refresh the three stale "Story 1.7 owns" docstring notes (:48-49, :224-225, :318-319) to state the grammar is now landed.
- `src/pyforge/warden/engines.py` -- MODIFY: `DeptryEngine` gains `axis: str = AXIS_HYGIENE` (dataclass field, mirrors `name: str = "deptry"` at :406); `OsvEngine` gains `axis: str = AXIS_VULNERABILITY`; `NullEngine` gains `axis: str = AXIS_INGESTION` (inert — its result never carries errors/findings); every `EngineResult(...)` construction site (~15, across all three engines) gains `axis=self.axis`; `DeptryEngine.run`'s successful-parse `AxisCoverage` (:483-491) `deps_assessed` changes from `inventory.count` to `inventory.count - len(synthesized.excluded)`, matching `OsvEngine.run`'s own `deps_assessed=len(synthesized.lines)` (:759-761).
- `src/pyforge/warden/cli.py` -- MODIFY: `_record_error` (:531-557) gains a required `axis: str` parameter, replacing its hardcoded `AXIS_VULNERABILITY`; its 4 pipeline-stage call sites (discovery :292, extract ×3 :315/:334/:354) pass `axis=AXIS_INGESTION`; its 2 engine-scoped call sites (factory-instantiation crash :420, `engine.run()` crash :442) pass `axis=factory.axis` / `axis=engine.axis`; refresh the stale "Story 1.7 owns" docstring notes (:63, :543).
- `src/pyforge/warden/routing.py` -- MODIFY: reword the stale :16 comment ("the typed exception net arrives with Story 1.7") — it already arrived (caught by `cli.py`'s extract-seam `except (SystemExit, Exception)`); state that plainly.
- `tests/unit/test_engine_env_deptry.py` -- MODIFY: add coverage for the fixed `deps_assessed` accounting when the purity guard excludes ≥1 component.
- `tests/unit/test_interfaces_and_null_engine.py` -- MODIFY: extend the error-rung test(s) to assert `StatusDriver.axis` reflects the producing engine (hygiene/vulnerability/ingestion) instead of always vulnerability.
- `tests/conformance/test_scan_harness.py` -- MODIFY: `test_error_report_driver_is_a_dangling_error_grammar_id` gains a `driver["axis"] == "ingestion"` assertion (its malformed-`pyproject.toml` fixture is a pre-engine failure); add a new regression test asserting every non-error-status fixture's `driver.finding_id` is present in that report's `findings[]` ids.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` -- MODIFY: lines 236/261/296 — stop calling `errors.py` "PLANNED"; state the shipped design (typed `ErrorRecord` values in `models.py`, caught at the seam boundaries) is the ratified FR21/NFR-R5 implementation, decided at Story 1.7.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/prd.md` -- MODIFY: FR21's error-class list — replace "config-error" with "config-parse"/"config-validation" (matches the shipped `ErrorKind` split); remove the now-closed open item 10.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- MODIFY: mark the :13, :37, :60 entries `**RESOLVED (was deferred from ...)**` with a one-line note of what changed; narrow :24 to keep only the still-open "deptry's own internal resolution failure" half, noting the front-door-exclusion accounting half is now resolved and the remainder stays Story 3.1/FR19 scope.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add `AXIS_INGESTION` + `StatusDriver` docstring -- names the third pipeline-stage axis and ratifies the two-namespace grammar.
- [x] `interfaces.py` -- `axis` on `EngineResult`/`Engine` Protocol; `evaluate()` uses `result.axis` -- closes deferred-work:37.
- [x] `engines.py` -- `axis` attrs on the three engines + `deps_assessed` fix -- closes deferred-work:60 and the accounting half of :24.
- [x] `cli.py` -- `_record_error` axis param + 6 call sites -- completes axis-correctness for pipeline-stage + engine-crash errors.
- [x] `routing.py` -- reword the stale forward-reference comment.
- [x] `test_engine_env_deptry.py`, `test_interfaces_and_null_engine.py`, `test_scan_harness.py` -- regression coverage for axis correctness, the `deps_assessed` fix, and the referential-integrity contract.
- [x] `architecture.md` + `prd.md` -- ratify the design; close the FR21 prose gap.
- [x] `deferred-work.md` -- close 3 items, narrow 1.

**Acceptance Criteria** *(from epics.md, story 1.7, plus this story's own hardening scope):*
- Given a missing/incompatible engine or a bounded-timeout breach, when scanned, then a typed `error_kind` routed to its owner is emitted with the correct `driver.axis` (hygiene/vulnerability/ingestion) and exit is 2 — never a silent pass (FR21; already-shipped mechanics, now axis-correct).
- Given an engine timeout, then a typed `timeout` `ErrorKind` is emitted, never a hang (NFR-R5; already shipped, reconfirmed unchanged).
- Given a run that scanned nothing meaningful, when it completes, then the status is non-passing, never `clean` (FR22; already-shipped `compose(())` behavior, reconfirmed unchanged).
- Given a component the NFR-S6 purity guard excludes from `DeptryEngine`'s front-door input, when the scan completes, then the hygiene axis's `deps_assessed` excludes it too, matching `OsvEngine`'s convention — never over-claiming assessment.
- Given a `Status.ERROR` report, its driver's `finding_id` uses the `error:<kind>:<subject>` grammar and need not reference `findings[]`; given any non-error-status report, its driver's `finding_id` must reference a real `findings[]` entry (both regression-tested).

## Review Triage Log

### 2026-07-17 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 1, medium 1, low 3)
- defer: 2: (low 2)
- reject: 6: (low 6)
- addressed_findings:
  - `high` `patch` `_synthesize_deptry_frontdoor` silently `continue`s past a component with `hygiene_covered=False` or no resolved `pypi_identity` into NEITHER `synthesized.lines` NOR `synthesized.excluded` — the just-implemented `deps_assessed=inventory.count - len(synthesized.excluded)` formula over-counted this third bucket as assessed (reproduced live by the Edge Case Hunter: computed 1, true assessed count 0). Fixed: changed the formula to `deps_assessed=len(synthesized.lines)`, matching `OsvEngine.run`'s own formula byte-for-byte (which the spec's Design Notes always said to mirror "exactly" — the subtraction form was the actual deviation). Added `test_deptry_engine_deps_assessed_excludes_hygiene_uncovered_components` to `test_engine_env_deptry.py` pinning the fix; verified the pre-existing purity-guard-exclusion test still passes unchanged (both formulas agree on that scenario).
  - `medium` `patch` No test exercised two engines failing on different axes in one scan; `axis` is no longer a single hardcoded constant across every error rung (Story 1.7), so which failing engine's error becomes the report's `status.driver` is now determined by axis ordering rather than the prior constant tie-break — a real, if low-consequence, behavior shift (every error is still visible in `errors[]` regardless of which one is chosen as driver). Fixed: added `test_two_engines_failing_on_different_axes_both_surface` to `test_scan_harness.py` (registers `CrashingFactory` [hygiene] + `CrashingEngine` [vulnerability] simultaneously against `CLEAN`; asserts exit 2, both `ErrorRecord`s present in `errors[]`, driver non-null — without asserting which specific one wins, since that choice isn't semantically meaningful).
  - `low` `patch` `test_null_engine_run_returns_the_empty_result` wasn't updated to assert `result.axis == AXIS_INGESTION`, even though `NullEngine` gained this exact field. Fixed: added the assertion (+ the `AXIS_INGESTION` import).
  - `low` `patch` The new `test_non_error_status_driver_references_an_emitted_finding` parametrization covered indeterminate/vulnerability-axis cases but never a hygiene-axis `policy-violation` — a fourth (status, axis) combination the "two-namespace contract" claims to hold universally. Fixed: added the existing `DEPTRY_MISSING` fixture (DEP001-block) to the parametrize list.
  - `low` `patch` `StatusDriver`'s two-namespace docstring enumerated only `policy-violation`/`indeterminate`/`warn` as the non-error statuses requiring `findings[]`-referential-integrity, omitting `Status.BYPASSED` (also non-error, also requires a driver per the class's own pre-existing docstring). Fixed: reworded the parenthetical to include `bypassed`, with a one-clause rationale (a waiver suppresses a real finding, so its driver naturally references that same finding).
  - `reject`: six findings dropped as noise — (1) `cli.py`'s engine-crash handler reading `axis=engine.axis` with no `getattr` fallback (unlike the factory-crash site) is not actually inconsistent: `engine` is Protocol-typed as `Engine` there (which requires `axis: str` structurally), while `factory` is the looser `Callable[[], Engine]` — the asymmetry is correct, not an oversight; (2) the shared `EMPTY_RESULT` test constant being stamped `axis=AXIS_VULNERABILITY` is provably inert (verified: never paired with a non-empty `errors` tuple at any call site); (3) `epic-1-context.md` still describing the rejected `errors.py`-exception-hierarchy design is self-healing — `architecture.md` (now newer) invalidates the cached context per step-01's own freshness check, so the next Epic 1 story recompiles it automatically; (4) `StatusDriver`'s docstring asserting an unenforced contract is by-design, already reasoned through in this spec's own Design Notes (1.1 precedent: blanket construction-time enforcement isn't safely expressible; a regression test is the sanctioned substitute); (5) flagging the closed PRD open-item-10 as premature because no `ConfigLoader` yet raises `config-parse`/`config-validation` conflates two different questions — the closed item was narrowly about prose/naming reconciliation, which is genuinely done, not about wiring a not-yet-built component; (6) `NullEngine.axis = AXIS_INGESTION`'s conceptual tension (a registered engine carrying the "pre-engine" axis label) is a deliberate, reasoned, inert choice already justified in this spec's own Design Notes, not an oversight.
  - `defer`: two findings appended to `deferred-work.md` — (1) both `DeptryEngine` and `OsvEngine` now share the identical `deps_assessed=len(synthesized.lines)` formula, but both synthesizers' `set(lines)` dedup means two distinct components serializing to the same requirement line under-count `deps_assessed` symmetrically across both engines (pre-existing in `OsvEngine`, now also present in `DeptryEngine` since this story aligned the formulas) — a narrow future hardening target, not this story's AC scope; (2) `cli.py`'s `getattr(factory, "axis", AXIS_INGESTION)` silently misattributes axis for any future non-class-based engine factory — currently unreachable (all registered factories are the engine classes themselves) but worth a guard before Epic 6 registers more engines.

## Design Notes

**Why ratify, not rebuild:** `architecture.md` calls `errors.py` "PLANNED," but the shipped `ErrorRecord`-in-`models.py` design already satisfies FR21/NFR-R5 completely (typed kind + owner, caught at every seam, report still emitted, exit 2) — proven by ~570 passing tests across Stories 1.2–1.6. A raised-exception hierarchy would be a purely cosmetic rewrite of every catch site in `engines.py`/`cli.py` with zero behavioral change and real regression risk; Simplicity First says don't.

**Why `AXIS_INGESTION` (not reusing hygiene/vulnerability, not leaving axis unset):** discovery/extract/routing failures happen before any per-axis engine runs — tagging them `vulnerability` (today's default) actively misleads an operator reading the driver. `axis` is documented as an "OPEN string mechanism" in `models.py` specifically so a third token can land additively, exactly like this.

**Why `EngineResult` gains `axis` (not a parallel list threaded through `Policy.evaluate`):** `EngineResult`'s own docstring is "what one engine run contributes to the report" — the axis it contributed under belongs there, not bolted onto the `Policy` interface. Each engine already trivially knows its own axis (dataclass default, same shape as the existing `name` field), so every construction site states it explicitly — self-documenting, no default-driven mislabeling possible.

**Why the `deps_assessed` fix is `inventory.count - len(synthesized.excluded)`, not a deeper coverage-honesty rewrite:** `OsvEngine` already draws this exact distinction (`deps_assessed=len(synthesized.lines)`, i.e. what was actually fed to the subprocess after purity-guard exclusion). Matching that convention closes the concrete, provable half of deferred-work:24/:60. The other half — deptry silently resolving nothing due to its own config/layout — has no detectable signal in deptry's JSON output and is explicitly deferred-work:24's own Story 3.1/FR19 remainder; inventing a heuristic for it now would be speculative.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior suites unchanged + new axis/coverage/referential-integrity tests green; sole-ownership / no-execution / socket-deny meta-guards stay green.
- `pixi run --frozen -e local-recipes mypy src/shared/packages/pyforge-warden/src/pyforge/warden` -- expected: no new errors vs the story-1.6-recorded baseline.
- `pixi run --frozen -e local-recipes ruff check src/shared/packages/pyforge-warden/src/pyforge/warden` -- expected: no new issues vs baseline.
- Manual: `git diff --stat` shows zero changes to `verdict.py`, `hygiene.py`'s `DEFAULT_HYGIENE_POLICY`, `vuln.py`'s `DEFAULT_VULN_SEVERITY_POLICY`, `Status`/`ErrorKind` enum members, `pixi.toml`/`pixi.lock`/`pyproject.toml`.

## Auto Run Result

**Summary of implemented change:** Ratified the shipped value-based `ErrorRecord` design as FR21/NFR-R5's permanent implementation (no `errors.py` exception hierarchy). Added `AXIS_INGESTION = "ingestion"` beside `AXIS_HYGIENE`/`AXIS_VULNERABILITY` in `models.py` as a third OPEN-string axis token, and ratified `StatusDriver`'s two-namespace `finding_id` contract in its docstring (every non-error status that carries a driver — `policy-violation`/`indeterminate`/`warn`/`bypassed` — must reference `findings[]`; `Status.ERROR` uses the exempt `error:<kind>:<subject>` grammar). Gave `EngineResult` a required `axis: str` field (and `Engine` Protocol an `axis: str` member) so every engine states which axis it assesses; `DefaultPolicy.evaluate`'s per-error rung loop now uses `result.axis` instead of a hardcoded `AXIS_VULNERABILITY`. `DeptryEngine`/`OsvEngine`/`NullEngine` each declare their own `axis` class attribute (hygiene/vulnerability/ingestion respectively) and every one of the 15 `EngineResult(...)` construction sites in `engines.py` now passes `axis=self.axis`. `cli.py`'s `_record_error` helper gained a required `axis` keyword-only parameter, replacing its hardcoded `AXIS_VULNERABILITY`; its 4 pipeline-stage call sites pass `axis=AXIS_INGESTION`, its 2 engine-scoped call sites pass the crashing factory's/engine's own `axis`. Fixed `DeptryEngine.run`'s successful-parse `AxisCoverage` to report `deps_assessed = len(synthesized.lines)` — the review pass (below) caught that the implementation's first draft (`inventory.count - len(synthesized.excluded)`) over-counted a third, silently-`continue`d bucket (`hygiene_covered=False` / no resolved identity) as assessed; the corrected formula matches `OsvEngine.run`'s own formula byte-for-byte, exactly as originally intended. Reworded five stale "Story 1.7 owns/arrives with" forward-reference comments plus `routing.py`'s stale comment. Updated `architecture.md` (3 spots) and `prd.md` (FR21's error-class list + removed the now-closed open item 10). Closed 3 `deferred-work.md` entries as RESOLVED, narrowed 1, and appended 2 new entries from the review pass.

**Files changed:**
- `src/pyforge/warden/models.py` — added `AXIS_INGESTION`; extended `StatusDriver`'s docstring with the two-namespace `finding_id` contract (incl. `bypassed`, added during review).
- `src/pyforge/warden/interfaces.py` — `Engine` Protocol gains `axis: str`; `EngineResult` gains a required `axis: str` field (ordered before `vuln_data`); `DefaultPolicy.evaluate`'s per-error loop uses `result.axis`; reworded 3 stale "Story 1.7 owns" docstring/comment spots.
- `src/pyforge/warden/engines.py` — `NullEngine`/`DeptryEngine`/`OsvEngine` each gain an `axis` class attribute; all 15 `EngineResult(...)` construction sites pass `axis=self.axis`; `DeptryEngine.run`'s successful-parse coverage reports `deps_assessed=len(synthesized.lines)` (corrected during review — see Review Triage Log); updated `DeptryEngine`'s class docstring to describe the fix and name the still-open deptry-internal-layout remainder.
- `src/pyforge/warden/cli.py` — `_record_error` gains a required `axis` keyword-only param; 4 pipeline-stage call sites pass `axis=AXIS_INGESTION`, 2 engine-scoped call sites pass the crashing factory's/engine's own axis (`getattr(factory, "axis", AXIS_INGESTION)` at the factory site — a typing-only accommodation for `Callable[[], Engine]`, flagged as a forward-risk and deferred, not fixed, since it's unreachable today); reworded 2 stale "Story 1.7 owns" comments; dropped the now-unused `AXIS_VULNERABILITY` import.
- `src/pyforge/warden/routing.py` — reworded the stale "the typed exception net arrives with Story 1.7" comment.
- `tests/unit/test_engine_env_deptry.py` — `test_deptry_engine_deps_assessed_excludes_purity_guard_exclusions` (implementation) + `test_deptry_engine_deps_assessed_excludes_hygiene_uncovered_components` (review pass — pins the third-bucket fix).
- `tests/unit/test_interfaces_and_null_engine.py` — `axis=` on all 15 `EngineResult(...)` sites; rewrote 2 tests to assert the driver's axis matches the producing engine; `test_null_engine_run_returns_the_empty_result` gains an `axis == AXIS_INGESTION` assertion (review pass).
- `tests/conformance/test_scan_harness.py` — `axis` class attributes on the 6 fake-engine test classes; `test_error_report_driver_is_a_dangling_error_grammar_id` gains a `driver["axis"] == "ingestion"` assertion; `test_non_error_status_driver_references_an_emitted_finding` parametrized over `WARN_AND_INDETERMINATE`/`VULN_CRITICAL`/`VULN_HIGH` (implementation) + `DEPTRY_MISSING` (review pass — hygiene-axis policy-violation coverage); new `test_two_engines_failing_on_different_axes_both_surface` (review pass).
- `tests/unit/test_report.py` — `axis=AXIS_HYGIENE` on its one `EngineResult(...)` construction.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` — 3 spots stop calling `errors.py` "PLANNED"; ratify the shipped design.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/prd.md` — FR21's error-class list now says `config-parse`/`config-validation`; removed the now-closed open item 10.
- `_bmad-output/implementation-artifacts/deferred-work.md` — 3 entries marked `**RESOLVED**`, 1 narrowed (implementation), 2 new entries appended (review pass — dedup-collapse cross-engine parity gap; `factory_axis` fallback forward-risk).
- `_bmad-output/implementation-artifacts/spec-1-7-typed-errors-the-no-scan-guard.md` — this file: all 8 execution tasks checked off; `## Review Triage Log` added; this section.

**Review findings breakdown:** 0 intent_gap, 0 bad_spec, 5 patch (1 high, 1 medium, 3 low — all applied), 2 defer (appended to `deferred-work.md`: the now-symmetric dedup-collapse coverage imprecision, and the `factory_axis` fallback forward-risk), 6 reject (an Engine-Protocol-vs-Callable typing asymmetry that's actually correct rather than an oversight; an inert test-constant axis choice; a self-healing stale epic-context reference; an already-reasoned-through by-design docstring choice; a premature "unwired ErrorKind" complaint against a narrowly-scoped prose-reconciliation fix; an already-reasoned-through `NullEngine.axis` choice). Full detail: `## Review Triage Log` above.

**Verification performed:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 945 passed, 0 failed (938 baseline + 4 implementation + 3 review-pass tests). No prior test was weakened or skipped.
- `pixi run --frozen -e local-recipes mypy src/shared/packages/pyforge-warden/src/pyforge/warden` — 10 errors, confirmed identical to the pre-change baseline (missing `types-PyYAML`/`types-jsonschema` stubs, a `LineStr.source_line` attr-defined gap, a `report.py` list-vs-tuple coverage assignment, a `cli.py` stdout-`fileno`-on-`None` union-attr gap). Zero new errors.
- `pixi run --frozen -e local-recipes ruff check src/shared/packages/pyforge-warden/src/pyforge/warden` — all checks passed, zero issues.
- Manual `git diff --stat` — confirmed zero changes to `verdict.py`, `hygiene.py`, `vuln.py`, `pixi.toml`, `pixi.lock`, `pyproject.toml`, and zero changes to any `Status`/`ErrorKind` enum member, re-verified after the review-pass patches.

**Follow-up review recommendation:** `false` — the one high-severity patch (the `deps_assessed` third-bucket fix) is a narrow, well-verified arithmetic correction with a dedicated new regression test, not a design change; the medium patch adds test coverage for a pre-existing (not newly risky) axis-ordering tie-break with no exit-code/report-emission consequence; the remaining 3 patches are docstring/test-assertion additions. No API/behavior surface changed beyond what the spec's own Code Map already described, and the full suite (945 tests) plus mypy/ruff are green against the exact same baseline recorded at implementation.

**Residual risks:** The deptry-internal-layout coverage gap (deptry silently resolving nothing due to its own non-standard-layout detection or an over-broad `[tool.deptry] extend_exclude`) remains open by design — left to a future coverage-floor gate (Story 3.1/FR19). Two narrow, low-severity gaps were deferred rather than fixed (see `deferred-work.md`): a symmetric dedup-collapse coverage imprecision shared by both engines, and the `factory_axis` fallback's reliance on an unenforced "factory is always the engine class" convention (currently unreachable, worth a guard before Epic 6 registers more engines).
