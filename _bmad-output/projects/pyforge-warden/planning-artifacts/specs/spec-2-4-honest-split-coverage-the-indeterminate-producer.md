<!-- RECOVERED 2026-07-25 from Claude Code session transcript db3290ed-e363-4de4-92c1-d4ab7d5411de.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 2.4: Honest split coverage + the indeterminate producer (C0b)'
type: 'feature'
created: '2026-07-16'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-2-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** `DeptryEngine.run` always invokes `deptry` even when the scan target has no adjacent Python source (the fleet's majority feedstock shape — a bare `recipe.yaml`/`pixi.toml` with zero `.py` files) — a real, already-partially-acknowledged gap (`sentinel`'s own fixture comment: "this fixture has no source module, so deptry would flag both declared deps DEP002"). deptry then flags every conda-sourced dependency reaching the front-door as "unused," and the report's coverage has no way to say "hygiene wasn't applicable here" — only "0 of N assessed," which reads as a coverage failure, not an honest scope exclusion. Separately, the split-coverage/`indeterminate`-lattice/`resolution_depth` machinery that makes a partial-coverage conda/pixi scan honestly non-clean already exists (Stories 1.1–1.6, 2.1, 2.2, 2.6, confirmed by direct code read) but has only ever been proven synthetically (a hand-built `pyproject.toml` fixture, Story 1.6) — never end-to-end through a REAL conda/pixi extractor.

**Approach:** Add a bounded "adjacent Python source" predicate; when absent, `cli.py` excludes `DeptryEngine` from the engines it runs and tells `report.assemble_report` to report the hygiene axis honestly as not-applicable (zero total/assessed) — no frozen-model change, an orchestrator-supplied boolean overrides existing `AxisCoverage` fields. Then prove the pre-existing coverage-split/indeterminate/resolution-depth machinery end-to-end via real conda/pixi conformance tests (no new production code needed there).

## Boundaries & Constraints

**Always:**
- The "no adjacent Python source" check lives OUTSIDE `DeptryEngine.run`, in `cli.py`'s orchestration. `DeptryEngine.run(target, inventory)` is called directly, against bare `tmp_path` dirs with zero `.py` files, by ~20 existing tests in `tests/unit/test_engine_env_deptry.py`; embedding the skip inside the engine would break all of them. Instead, `cli.py` filters `DeptryEngine` out of `engines_to_run` when the predicate is False — mirroring the existing `engines_to_run = engine_factories() if manifests_parsed > 0 else ()` gate already there.
- The predicate (new `hygiene.has_adjacent_python_source(target: Path) -> bool`) is a bounded recursive walk for at least one `*.py` file anywhere under the target: early-exits on the first match, skips `.git` directories, and caps total directory entries visited (NFR-S5-style bound — never an unbounded walk on a pathological tree).
- `report.assemble_report` gains one new defaulted keyword parameter, `hygiene_applicable: bool = True` — the default preserves every existing caller/test byte-for-byte (mirrors the `has_locked_closure` parameter already on this exact function, same precedent). When `False`, the returned hygiene `AxisCoverage` reports `deps_total=0, deps_assessed=0, resolution_depth=None` regardless of any engine's own coverage claim (today `assemble_report` already ignores each engine's own `deps_total`/`resolution_depth` and recomputes them itself — only `deps_assessed` is pulled from `EngineResult.coverage`, per direct code read of `report.py`'s `assemble_report`). `manifests_found`/`manifests_parsed` and the vulnerability axis are untouched.
- `models.py`, `verdict.py`'s rung order, and `interfaces.py`'s Protocol shapes stay untouched (`git diff --stat` shows zero changes) — every primitive AC1/AC2 need (the `WithholdReason` vocabulary, the `indeterminate` rung, `AxisCoverage`'s existing fields, `ResolutionDepth`) already exists and already works there, confirmed by direct code read of `interfaces.DefaultPolicy.evaluate`, `verdict.compose`, and `Component.__post_init__`.
- New conformance tests exercise the REAL pipeline (`cli.main`, via `tests/conformance/test_scan_harness.py`'s established `run_scan`/`parse_report` harness) against real conda/pixi fixtures — never a hand-built `ComplianceReport`. AC1/AC2's job this story is proving the existing machinery holds for a REAL conda/pixi producer; Story 1.6 already proved it synthetically for pyproject.toml.
- Reuse the existing `tests/fixtures/projects/recipe_common/` fixture (Story 2.2) for the combined AC1+AC2+AC3 conformance test: it already mixes a range-only dep (`numpy >=1.20`), a bare no-version dep (`python`), and a name that will not resolve against the conda→pypi map (`${{ name }} ==${{ version }}` → `mypkg==1.2.3`) — a real fixture with zero adjacent `.py` files, so it doubles as AC3 evidence (assert zero `hygiene:DEP002:*` findings post-fix) in the same test.
- The new AC3-isolation fixture's dependency is the SAME known-clean exact pin already used by the `clean`/`pixi_toml_common` fixtures (`requests==2.31.0`) — reuses an already-verified-clean-against-the-offline-test-DB choice instead of introducing an unverified one.

**Block If:** none identified.

**Never:**
- Fix `DeptryEngine`'s `deps_assessed == inventory.count` honesty gap — already explicitly owned by Story 1.7 (`deferred-work.md`: the 1.3-review defer and the 2.2-follow-up-review defer both say so). Touching it here would preempt that story's scoped decision.
- Make `WithholdReason.NATIVE_NONPYPI` reachable — needs a "known has-no-PyPI-equivalent" data signal, which is Story 2.1's ecosystem-identity-predicate territory, not this story's coverage-reporting territory. The token already exists in the enum (models.py), satisfying AC2's "one of these four reasons" bar.
- Widen `discovery.py` to new manifest kinds/spellings, or generalize the Python-source predicate into a configurable exclude-list (beyond `.git`) — both are Story 1.9/3.1 territory.
- Touch `models.py`, `verdict.py`, or `interfaces.py`'s Protocol definitions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Conda manifest, mixed resolvable + indeterminate deps, no adjacent `.py` | `recipe_common` fixture | `status=indeterminate`, exit 1; `coverage` has both axes; hygiene axis `deps_total=0`/`deps_assessed=0` (not-applicable, zero DEP002 findings); vulnerability axis reflects the real partial match | No error |
| Conda manifest, fully resolvable, no adjacent `.py` | new `hygiene_not_applicable` fixture (`requests==2.31.0` only) | `status=clean`, exit 0, zero findings; hygiene axis `deps_total=0`/`deps_assessed=0`; vulnerability axis `deps_total=1`/`deps_assessed=1` | No error |
| pyproject.toml WITH adjacent `.py` source (pre-existing fixtures: `clean`, `deptry_unused`, `sentinel`, `vuln_critical`, …) | unchanged | `DeptryEngine` still runs; existing findings/coverage assertions unaffected | No error (regression-only) |
| Lockfile present (`pixi.lock`/`conda-lock.yml`) vs a bare manifest only | existing lockfile fixtures vs `recipe_common` | `resolution_depth == "locked-closure"` vs `"direct-only"` respectively, end to end | No error |
| Pathological/huge source tree under the scan target | N/A (unit-level) | `has_adjacent_python_source` returns within the bounded entry cap, never hangs or raises | Bounded, no exception |

</intent-contract>

## Code Map

- `src/pyforge/warden/hygiene.py` -- MODIFY: add `has_adjacent_python_source(target: Path) -> bool`, a bounded recursive predicate.
- `src/pyforge/warden/cli.py` -- MODIFY: import `DeptryEngine`; compute the predicate once (before `engines_to_run`); filter `DeptryEngine` out of `engines_to_run` when absent; thread `hygiene_applicable` into the `assemble_report` call.
- `src/pyforge/warden/report.py` -- MODIFY: `assemble_report` gains `hygiene_applicable: bool = True`; overrides the hygiene `AxisCoverage`'s `deps_total`/`deps_assessed`/`resolution_depth` to the not-applicable shape when `False`.
- `tests/fixtures/projects/hygiene_not_applicable/pixi.toml` -- NEW: isolated AC3 fixture (single `[pypi-dependencies] requests = "==2.31.0"` entry, zero `.py` files).
- `tests/unit/test_hygiene.py` -- MODIFY: unit-test `has_adjacent_python_source`'s I/O matrix (root-level `.py`, nested `.py`, none, `.git`-only tree, bounded-cap behavior).
- `tests/unit/test_report.py` -- NEW: unit-test `assemble_report(hygiene_applicable=False)`'s coverage-shape override in isolation from the CLI (default `True` stays byte-for-byte identical to today).
- `tests/conformance/test_scan_harness.py` -- MODIFY: add (1) the `recipe_common`-based combined AC1+AC2+AC3 conformance test, (2) the `hygiene_not_applicable`-based isolated AC3 conformance test, (3) a `locked-closure`-vs-`direct-only` resolution-depth conformance test (verify one doesn't already exist for a real conda/pixi producer before adding), (4) a cheap ratchet test asserting the retired "clean at" phrasing never appears anywhere under `src/pyforge/warden/`.

## Tasks & Acceptance

**Execution:**
- [ ] `hygiene.py` -- add `has_adjacent_python_source(target)` -- the bounded predicate both the AC3 fix and its tests depend on.
- [ ] `cli.py` -- import `DeptryEngine`; compute `hygiene_applicable` before `engines_to_run`; filter it out when False; pass `hygiene_applicable` to `assemble_report` -- the orchestration wiring that actually silences the DEP002 noise wall.
- [ ] `report.py` -- add `assemble_report(..., hygiene_applicable: bool = True)` -- overrides hygiene `AxisCoverage` to the not-applicable shape; default preserves every existing caller.
- [ ] `tests/fixtures/projects/hygiene_not_applicable/pixi.toml` -- new fixture -- isolates the AC3 mechanism from any concurrent indeterminate noise.
- [ ] `tests/unit/test_hygiene.py` -- unit-test the predicate's I/O matrix.
- [ ] `tests/unit/test_report.py` -- unit-test the `hygiene_applicable` coverage override, independent of the CLI.
- [ ] `tests/conformance/test_scan_harness.py` -- the 4 new/verified tests described in the Code Map.

**Acceptance Criteria** *(from `epics.md`, preserved verbatim)*:

**Given** a manifest where some deps resolve and some don't, **When** reported, **Then** coverage is **split** into hygiene vs vulnerability dimensions (FR15) and a partial result renders a **coverage-qualified verdict governed by the FR20 lattice** (partial vuln coverage ⇒ `indeterminate`, non-zero), never bare "clean" — the retired "clean at N%" phrasing is outlawed by FR16. **And** the coverage marks `direct-only` vs `locked-closure` (a loose manifest lists direct deps only; transitive vulns invisible without a lockfile).

**Given** a name-only / range / unmapped dep, **When** classified, **Then** it becomes `indeterminate` with a `WithholdReason` (`no-version`/`unmapped-ecosystem`/`native-nonpypi`/`range-only`) and is **never dropped or defaulted to clean** (C0b — FR13); the verdict exits **red-by-design** without needing E3's waivers. **And** an empty extraction is distinguished from "deps present but unresolved" (FR6).

**Given** a manifest-only repo with **no adjacent Python source** (the fleet's majority shape — feedstocks), **When** the hygiene axis runs, **Then** hygiene coverage is honestly **`not-applicable`/skipped, the reduced scope recorded — never a 100%-DEP002 noise wall** — matching Kedro FR-16's already-specced semantics for this schema's second producer.

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries.
     Each entry records: what finding triggered the change, what was amended, what known-bad state
     the amendment avoids, and any KEEP instructions (what worked well and must survive re-derivation).
     Empty until the first bad_spec loopback. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on EVERY review pass, including loopbacks and blocked exits.
     Each entry records triage decision counts for intent_gap, bad_spec, patch, defer, and reject,
     with per-category severity breakdowns using low/medium/high, plus the findings addressed in
     that pass. Empty until the first review pass. -->

## Design Notes

**Why the skip logic lives in `cli.py`, not `DeptryEngine.run`:** the obvious-looking place to add "skip if no Python source" is inside the engine itself. But `tests/unit/test_engine_env_deptry.py` calls `DeptryEngine().run(tmp_path, inventory)` directly, roughly 20 times, against bare pytest `tmp_path` directories that carry no `.py` files — those tests mock `_engine_env`/`subprocess.run` to verify the engine's OWN argv/coverage/error-handling logic, independent of a real filesystem tree. Putting the predicate inside `DeptryEngine.run` would make every one of those tests exercise the new early-return branch instead of the behavior they're actually testing, forcing an unrelated rewrite of ~20 pre-existing tests for a story whose AC is about the CLI-level report, not the engine's own unit contract. Filtering at the `cli.py` orchestration layer (which already gates the whole engine list on `manifests_parsed > 0`) keeps the change surgical and leaves every existing `DeptryEngine` unit test untouched.

**Why `report.assemble_report` needs a new parameter at all:** `assemble_report`'s coverage-tuple construction (`report.py`, current code) computes `deps_total=inventory.count` uniformly for BOTH axes at the orchestrator level, and only pulls `deps_assessed` (as a max across engines) from each `EngineResult.coverage` — it does not read an engine's own `deps_total`/`resolution_depth` at all. So simply having `DeptryEngine` skip and return `coverage=()` only achieves `deps_assessed=0` for hygiene, which still reads as "0 of N assessed" (a coverage FAILURE) rather than "0 total, not applicable" (an honest scope exclusion) — the AC's literal distinction. Only a caller-supplied signal into `assemble_report` itself (mirroring the existing `has_locked_closure: bool = False` parameter on the same function) can make `deps_total` axis-aware without touching the frozen `AxisCoverage` shape.

**Why `recipe_common` is reused rather than authoring a new fixture for AC1/AC2:** it already contains a range-only dep, a bare no-version dep, and a conda-map-unresolvable dep, entirely by virtue of being Story 2.2's own common-case extraction fixture — and it has zero adjacent `.py` files, so running it through the real `cli.main` pipeline is simultaneously the first real end-to-end proof of the indeterminate/split-coverage machinery (AC1/AC2) AND a live demonstration of the pre-fix DEP002 noise-wall bug this story closes (AC3), in one fixture, one test.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior 1.x/2.x suites unchanged + new tests green; no existing `DeptryEngine` unit test in `tests/unit/test_engine_env_deptry.py` needs modification (confirms the cli.py-layer placement was correct).
- Manual: `git diff --stat` shows zero changes to `verdict.py`, `interfaces.py`, or `models.py`.
- Manual: `grep -ri "clean at" src/pyforge/warden/` returns nothing (mirrors the new ratchet test).

