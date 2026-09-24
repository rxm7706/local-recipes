---
title: '24.2: An import-linter contract catches the class structurally'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '42f4b5e9b53118f59e1c9e64f18164db4eaab77a'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The defect Story 24.1 removes survived because nothing asked whether a station package evaluates that station's CI gate.

**Approach:** A contract forbids any pyforge.<station> module from importing or defining the gate evaluator. A meta-test fails on a planted reintroduction and passes on the moved layout. The docstring names Charter §5/§6 and this Spec.

## Boundaries & Constraints

**Always:**
- Planted pyforge.<station>.coverage_gate shim fails the contract.
- Moved layout passes.
- Docstring names Charter §5/§6 and this Spec.

**Never:**
- Do not leave the rule undocumented as an arbitrary layering check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| planted shim | temp pyforge.<station>.coverage_gate | contract fails | fail |

</intent-contract>

## Binding

Parent Spec capability: `spec-coverage-gate-independence CAP-3`.
Surface: src/shared/packages/pyforge-marshal/pyproject.toml [tool.importlinter] and/or a fleet-level contract; marshal tests/meta/test_ad3_ad4_import_linter.py or a sibling; a fixture that fires..
Ledger key: `24-2-an-import-linter-contract-catches-the-class-structurally`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-2-an-import-linter-contract-catches-the-class-structurally.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-24 — Review pass
- verdicts: 18 findings — high 1, medium 4, low 7, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` Docstring claimed this file "matches every other pyforge-core/pyforge-doctor meta test's convention" for scanning source trees, but every OTHER pyforge-doctor sibling (`test_no_warden_import.py` et al.) scans the INSTALLED package via `pyforge.doctor.__file__`, not a source tree — the claim was backwards for doctor's own siblings (true only for pyforge-core's). — Fixed: docstring rewritten to state the divergence from doctor's own sibling convention explicitly and explain why (this file must reach seven other stations' source trees, which the installed `pyforge.doctor` package cannot do).
  - `[low]` `[reject]` This file re-implements station-enumeration/AST-parse logic that `pyforge-core`'s `tests/meta/conftest.py` centralizes; suggested moving it to `pyforge-testing-kit`. — Rejected: the hand-copy is the established repo-wide convention for this exact situation (`pyforge-core`'s own conftest docstring: centralized only after three in-package copies; every OTHER cross-package consumer, e.g. `pyforge-atlas`'s and `pyforge-warden`'s own guards, still hand-copies because no cross-package pytest import path exists). Moving shared logic into `pyforge-testing-kit` — a declared stdlib leaf (`dependencies = []`) — is a nontrivial cross-package refactor outside this story's scope, not a direct correction.
  - `[medium]` `[patch]` `_imports_evaluator` only walks `ast.Import`/`ast.ImportFrom`; a station module using `importlib.import_module("...coverage_gate")` or `__import__("...coverage_gate")` to load the relocated evaluator as a library would scan clean. — Fixed: `_imports_evaluator` now also flags `importlib.import_module(...)`/`__import__(...)` calls whose string-literal argument's last dotted component is `coverage_gate`, in both the canonical file and the new `pyforge-core` companion; proven by `test_guard_fires_on_a_dynamic_import_module_call`/`test_guard_fires_on_a_dunder_import_call`/`test_guard_does_not_fire_on_an_unrelated_dynamic_import`.
  - `[false]` `[reject]` `pyforge-core` and `pyforge-testing-kit` are excluded from the scan roster, and are named as "where the risk is largest" (a `coverage_gate` shipped inside `pyforge-core` would be transitively reachable by every station). — Refuted: CAP-3's own intent text scopes the prohibition to "any `pyforge.<station>` module"; `station` is this repo's defined term for one of the eight Smiths (`guild-roster.json`), and neither `pyforge-core` nor `pyforge-testing-kit` is one — the Spec's own "Why" section already reasons about `pyforge-core` separately ("governed by marshal's own planning tree") for the DIFFERENT question of where the evaluator may live, not whether this scan must cover it. Out of this contract's stated subject, not an oversight.
  - `[low]` `[patch]` Docstring said "a file at the module path `pyforge.<station>.coverage_gate`" (implying a direct child), but `_defines_evaluator` matches `coverage_gate.py` at any depth under the station's tree. — Fixed: docstring reworded to state explicitly that a nested reintroduction is caught too, and why (same violation, one directory deeper).
  - `[low]` `[reject]` The "not just marshal-specific" non-vacuous proof is parametrized across all eight stations for the "defines" check, but the "imports" guard-fires tests (absolute/from/relative import, unrelated-module negative) are hardcoded to `pyforge-marshal` only — inconsistent breadth. — Rejected: neither `_defines_evaluator` nor `_imports_evaluator`/`_module_violations` branches on station name at all; the existing 8-way parametrized "defines" test already proves the shared `_module_violations` entry point is station-name-agnostic, so a second 8-way sweep over the "imports" branch of the SAME function exercises no new code path — a cosmetic consistency nit, not a missed code path, and adding it is more than a direct correction (four new parametrized test groups).
  - `[medium]` `[patch]` No `sprint-status-ledger.yaml`/`epics.md`/`.memlog.md` companion change was evidenced alongside the spec-status frontmatter edit. — Partially real: the ledger/`epics.md` promotion is legitimately a separate, later, post-merge commit in this project's own established convention (Story 24.1's own landing: ledger promoted by a dedicated commit `b32e4e766d` AFTER the merge `78f5b33c56`, not inside the reviewed diff) — not fixed here. The `.memlog.md` surface-reconcile entries, however, were genuinely still pending at review time (this dispatch's own required S-13.7 guard) and are fixed now: entries appended to `spec-pyforge-doctor/.memlog.md` (owning) and `spec-pyforge-steward/spec-pyforge-unifying-strategy/.memlog.md` (co-governor of the new `pyforge-core` file), verified via a clean `python scripts/spec_surface_reconcile.py` run.
  - `[false]` `[reject]` `_module_violations`'s `path.read_text(encoding="utf-8")` + `ast.parse(...)` are unguarded; a non-UTF-8 or syntactically invalid station file would raise instead of producing a clean assertion failure. — Refuted: unreachable in this repo — every file under a scanned `src/pyforge/<station>/` tree must already be valid, parseable, UTF-8 Python to pass `lint-types` (ruff/mypy) before it can land, and the identical unguarded pattern is `pyforge-core`'s own established `parse_module` precedent (`tests/meta/conftest.py`) this file explicitly mirrors — not a new gap introduced here. No scanned file (486 real files, confirmed clean) triggers it.
  - `[low]` `[patch]` A docstring line wrap split the hyphenated identifier `pyforge-<station>-coverage-gate` across two lines inside its own inline-code span, rendering as a broken literal in a non-reflowing viewer. — Fixed: rewrapped as part of the same docstring edit above.
  - `[medium]` `[patch]` (Edge Case Hunter) Dynamic `importlib.import_module()`/`__import__()` reintroduction bypasses the static-AST-only import guard. — Same defect as the row above; fixed together (see that row's evidence).
  - `[low]` `[patch]` A `coverage_gate/` PEP 420 namespace package (no `__init__.py`) holding the evaluator under differently-named files bypasses `_defines_evaluator` (which only recognized `coverage_gate.py` or `coverage_gate/__init__.py`). — Fixed: `_defines_evaluator` now flags ANY file whose immediate parent directory is named `coverage_gate`, `__init__.py` or not; proven by `test_guard_fires_on_a_planted_coverage_gate_namespace_package`. Verified no directory named `coverage_gate` exists anywhere under `src/shared/packages/*/src/pyforge` today, so this widening introduces no false positive on the real tree.
  - `[false]` `[reject]` A non-UTF-8 station file would raise `UnicodeDecodeError` during collection instead of a controlled result. — Same claim as the `_module_violations` error-handling row above; refuted on the same evidence (unreachable given `lint-types`, matches established `pyforge-core` precedent).
  - `[false]` `[reject]` A syntactically invalid station file would raise `SyntaxError` instead of a controlled assertion result. — Same claim and refutation as the two rows above.
  - `[false]` `[reject]` A reintroduced module inside a SYMLINKED subdirectory of a station's `src/pyforge/<station>/` tree would not be traversed (`rglob` does not follow symlinked directories by default). — Refuted: verified zero symlinks exist anywhere under `src/shared/packages` today (`find -type l`, 0 hits); the identical `rglob("*.py")` pattern with no symlink-following is `pyforge-core`'s own established `station_source_files` precedent this file mirrors, not a new gap.
  - `[medium]` `[patch]` (Edge Case Hunter, "claim" form) Restates the dynamic-import gap as an intent-vs-implementation claim. — Same defect as the two dynamic-import rows above; fixed together.
  - `[low]` `[patch]` (Edge Case Hunter, "claim" form) Restates the namespace-package gap as an intent-vs-implementation claim. — Same defect as the namespace-package row above; fixed together.
  - `[high]` `[patch]` (Verification Gap, pre-verified) `.github/workflows/pyforge-station-tests.yml`'s `doctor-test` job only fires when `src/shared/packages/pyforge-doctor/**` (or the shared surface) changed, so a PR touching exactly one OTHER station (atlas/herald/mason/scribe/steward/warden) never runs this new fleet-wide guard — CAP-3's own success signal ("reintroducing this shape fails a test rather than waiting for a future audit") is unmet in the normal CI path for 6 of the 8 stations it protects. — Fixed: a companion test (`pyforge-core/tests/meta/test_coverage_gate_ci_trigger_companion.py`, duplicating the same violation-detection logic, reusing `pyforge-core`'s own `conftest.py` helpers) added — `pyforge-core-test` already runs on any single-station change (Story 52.2, CAP-8), closing the gap without widening `doctor-test`'s own broader (2395-test) CI trigger. Verified: `pixi run --frozen -e pyforge-core pyforge-core-test` — 1914 passed.
  - `[false]` `[reject]` (Intent Alignment Auditor) The diff implements a bespoke `ast`-based scanner rather than the literal `import-linter` tool / `[tool.importlinter]` contract the Spec's title, CAP-3's own intent line, and this story's own Binding section all name. — Refuted: the `<intent-contract>` block itself — the workflow's declared sole source of truth — says only "A contract forbids..." / "A meta-test fails...", never naming the `import-linter` tool; only the surrounding document framing (title, Binding, both outside `<intent-contract>`) uses the more specific phrasing, and the Binding section itself already allows "and/or a fleet-level contract home the story chooses." Independently: a literal import-linter contract cannot express the "or defining" half of the requirement at all (it is an import-graph tool, not a filesystem/module-existence check), so a pure import-linter implementation was never sufficient on its own terms regardless of this diff's choice.

