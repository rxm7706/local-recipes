---
title: 'Story 10.1: The declared floor and the installed core are compared and reported'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: 'a629ab0df12f31fb335a5a90fc9c67f7c642bff6'
final_revision: '9823184658'
---

<intent-contract>

## Intent

**Problem:** `pixi.toml` already declares `bmad-method >=6.11.0` while the installed
`_bmad/_config/manifest.yaml` still reports `6.10.0` — Doctor reports staleness for every
other class of fleet dependency but has this one blind spot, undetected until an operator
happens to check by hand.

**Approach:** Add a new closed-taxonomy `Source` (`BMAD_METHOD_VERSION_DRIFT`) whose
`gather(target)` reads both already-tracked files directly (no subprocess, no network),
compares the installed version against the declared floor, and reports one `Finding` —
`warn` on drift, `ok` when they agree — dispatched via
`python -m pyforge.doctor.sources bmad-method-version-drift`, mirroring Story 11.1's
`DUE_FOR_VERIFICATION` precedent (the most recent genuinely-new, non-ported `DISPATCH`
member).

## Boundaries & Constraints

**Always:**
- Read-only: never runs `npx bmad-method install`, never writes to `_bmad/**`.
- Fits the existing closed `Source` `StrEnum` (`models.py`) — no open/stringly-typed source.
- Reads `pixi.toml` and `_bmad/_config/manifest.yaml` as plain files (`tomllib`/`yaml`,
  both already available — stdlib and an existing PyYAML dependency respectively) — no
  subprocess, no `cli_bridge` needed (nothing here reads git history).
- Status is always `ok` or `warn`, never `fail` — this signal informs, it never gates
  (mirrors `DUE_FOR_VERIFICATION`'s own always-warn discipline; CAP-3's non-gating rule is
  enforced downstream by `verdict.exit_code_for`, unaffected by any `warn` Finding).
- Degrades, never crashes: any exception (missing file, unparseable TOML/YAML, an
  unrecognized `bmad-method` constraint form, `bmad-method` absent from `pixi.toml`
  entirely) becomes one `warn` Finding naming the failure — never a silent `ok`, never a
  propagated exception. Wrap `_gather` in `sources.degrade_on_exception` as the outer net
  (mirrors `chain.py`/`factory.py`, not `ledger.py`'s bespoke git-error handling — nothing
  here needs git-specific catching).
- `pixi.toml` declares `bmad-method` in more than one `[feature.*.dependencies]` table
  today (`feature.python`, `feature.local-recipes`, both currently `>=6.11.0`) — read every
  occurrence and use the maximum declared floor, never assume exactly one line.
- New `SourceRegistration` row: `scope="repo"`, `subject_station="marshal"` (mirrors
  `BMAD_DRIFT`/`DREAM_CHAIN`/`SPEC_SURFACE`/`FORWARD_DEPENDENCY`'s own "factory apparatus"
  precedent — Marshal owns the repo's tooling-installation surface even though applying a
  fix is steward's territory), `owning_station="doctor"`.

**Block If:** (none — this story is cleared to dispatch per the epic; no unattended-unsafe
decision remains unresolved for CAP-1's own scope)

**Never:**
- Never touches CAP-2 (latest-upstream-release comparison) — that data-source question
  stays open per Story 10.2, out of scope here.
- Never wires into `doctor check`/`monitor`'s own CLI dispatch or `fleet-picture`'s
  ATTENTION block — that is Story 10.3's job specifically (mirrors how `DISPATCH`-only
  sources like `bmad-drift`/`due-for-verification` are NOT wired into `__main__.py`'s three
  verb dispatchers today, per that module's own docstring).
- Never imports `pyforge.marshal` or any other station package, or `bmad_loop` (Charter §6
  independence discipline — `tests/meta/test_source_independence.py` enforces this for
  every registered source).
- Never adds a new runtime dependency (`packaging` et al.) — both version strings observed
  in this repo are plain `X.Y.Z` triples; a minimal tuple-of-ints parser suffices.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real drift (today) | `pixi.toml` max floor `6.11.0`, manifest `6.10.0` | One `warn` Finding naming both versions | No error |
| Agreement | declared floor <= installed version | One `ok` Finding naming both versions | No error |
| Multiple declarations, same floor | `bmad-method` in 2+ `[feature.*.dependencies]` tables, all equal | Treated as one floor (the max) | No error |
| `pixi.toml` missing `bmad-method` entirely | key absent from every `dependencies`/`feature.*.dependencies` table | One `warn` Finding: cannot evaluate, floor undeclared | Degrades via `degrade_on_exception` |
| `pixi.toml` or `manifest.yaml` missing/unreadable | `FileNotFoundError` etc. | One `warn` Finding naming the failure | Degrades via `degrade_on_exception` |
| Unparseable constraint form | e.g. `==6.11.0`, `*`, a git URL | One `warn` Finding: unrecognized constraint form | Degrades via `degrade_on_exception` |
| `manifest.yaml` malformed/missing `installation.version` | bad YAML, wrong shape, missing key | One `warn` Finding naming the failure | Degrades via `degrade_on_exception` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add
  `Source.BMAD_METHOD_VERSION_DRIFT = "bmad-method-version-drift"`, docstring note
  distinguishing it from the existing `BMAD_DRIFT` (different artifact: the installed
  BMAD-METHOD framework version, not `pyforge-marshal`'s project-doc currency).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- append one
  `SourceRegistration` row to `REGISTRY` for the new member.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- NEW.
  Single-purpose module (mirrors `ledger.py`'s shape): `__all__ = ("gather",)`,
  `gather(target: Path) -> tuple[Finding, ...]`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` -- import
  `bmad_method`; add `Source.BMAD_METHOD_VERSION_DRIFT.value: bmad_method.gather` to
  `DISPATCH`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- add
  `"bmad-method-version-drift"` to `$defs.finding.properties.source.enum`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_models.py` -- extend
  `test_source_taxonomy_is_exactly_this_closed_set`'s expected set with the new value +
  one dated comment line (matches every prior story's own addition pattern).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` -- import
  `bmad_method`; add its entry to `_EXPECTED_DISPATCH`.
- `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py` -- add
  `Source.BMAD_METHOD_VERSION_DRIFT: "bmad_method.py"` to `SOURCE_MODULE`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- NEW. Real
  tmp-fixture tests (no mocks, mirrors `test_sources_chain_due_for_verification.py`)
  covering every I/O matrix row.
- `pixi.toml` -- added by the 2026-08-15 review pass (patch): a
  `[feature.local-recipes.tasks.bmad-method-version-drift-check]` entry, mirroring
  `due-for-verification-check`'s exact shape -- the only discoverable, documented way to
  invoke a DISPATCH-only source that `scripts/detectors.py`'s frozen sweep excludes by design.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add the `Source` member -- the closed taxonomy Story 6.2's `REGISTRY`
  extension pattern requires.
- [x] `sources/__init__.py` -- register it in `REGISTRY` -- `test_sources_registry.py`'s
  exhaustiveness test fails without a matching entry.
- [x] `sources/bmad_method.py` -- write `gather`/`_gather` + the two small parse helpers
  (`_parse_version`, `_declared_floors`) -- the actual comparison logic.
- [x] `sources/__main__.py` -- add the `DISPATCH` entry -- makes the source runnable via
  `python -m pyforge.doctor.sources bmad-method-version-drift`.
- [x] `data/report-schema.json` -- add the enum value -- `--json` output would otherwise
  fail `jsonschema.Draft202012Validator` the moment this source's Finding is emitted.
- [x] `tests/unit/test_models.py` -- extend the closed-set assertion.
- [x] `tests/unit/test_sources_dispatch.py` -- extend `_EXPECTED_DISPATCH`.
- [x] `tests/meta/test_source_independence.py` -- extend `SOURCE_MODULE`; the AST-walk
  independence scan then covers the new module automatically.
- [x] `tests/unit/test_sources_bmad_method.py` -- write the I/O-matrix tests using real
  `tmp_path` fixtures (a written `pixi.toml` + `_bmad/_config/manifest.yaml`), not mocks.

**Acceptance Criteria:**
- Given `pixi.toml`'s max declared `bmad-method` floor and `_bmad/_config/manifest.yaml`'s
  installed version disagree (installed older), when `bmad_method.gather(target)` runs,
  then it returns exactly one `warn` Finding whose message names both versions.
- Given they agree (installed >= declared floor), when `gather` runs, then it returns
  exactly one `ok` Finding.
- Given either input file is missing, unreadable, or unparseable, when `gather` runs, then
  it returns exactly one `warn` Finding naming the failure — never raises, never silently
  reports `ok`.
- Given the new `Source` member, when the full test suite runs, then
  `test_sources_registry.py`, `test_source_independence.py`, and
  `test_schema_source_enum_matches_the_source_taxonomy_exactly` all pass without
  modification (their assertions are registry/schema-driven, not hardcoded).

## Spec Change Log

(none -- no bad_spec loopback occurred in this story's review pass)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 2, low 4)
- defer: 4 (medium 1, low 3)
- reject: 5 (low 5)
- addressed_findings:
  - `[medium]` `[patch]` `_declared_floors` never walked `[target.*.dependencies]` or `[feature.*.target.*.dependencies]` -- extended to a new `_dependency_tables` helper covering all four table shapes; added `_declared_floors_reads_top_level_target_scoped_tables`/`_reads_feature_target_scoped_tables` tests.
  - `[medium]` `[patch]` `_parse_version` accepted a leading `-` via bare `int()` (e.g. `"-1.2.3"` parsed cleanly) -- tightened to `str.isdigit()` per segment; added `test_parse_version_rejects_a_leading_minus_sign`.
  - `[low]` `[patch]` Test file docstring claimed "no mocks" unconditionally while `test_gather_degrades_on_unexpected_exception` uses `monkeypatch.setattr` -- reworded to name the one deliberate exception.
  - `[low]` `[patch]` `test_gather_never_raises_on_any_fixture_above` was misleadingly named (tests one case, not a sweep) -- renamed to `test_gather_never_raises_on_a_completely_empty_target_directory`.
  - `[low]` `[patch]` No test exercised `_declared_floors`'s top-level (non-`feature`) `[dependencies]` branch -- added `test_declared_floors_reads_the_top_level_dependencies_table`.
  - `[low]` `[patch]` `gather`'s docstring overstated that IT (not the outer `degrade_on_exception` wrapper) guarantees exactly one Finding -- reworded to attribute the guarantee correctly.
  - `[medium]` `[defer]` `DW-FU-10-1` -- declared floor is the max across every pixi.toml table regardless of which environment is active; a deliberate spec-level Boundaries decision, not a code defect, but worth revisiting if floors ever diverge.
  - `[low]` `[defer]` `DW-FU-10-1-2` -- an inline-table or `[pypi-dependencies]`-shaped constraint degrades to an uninformative WARN rather than being parsed; correct degrade-never-crash behavior today, no live occurrence.
  - `[low]` `[defer]` `DW-FU-10-1-3` -- evidence never names which pixi.toml table produced the winning floor when tables disagree; a usability enhancement beyond this story's stated ACs.
  - `[low]` `[defer]` `DW-FU-10-1-4` -- one table's unparseable constraint aborts the whole comparison instead of using a valid floor found elsewhere; a defensible all-or-nothing design choice consistent with sibling sources, not a live bug.
  - Rejected (noise / already correct / inconsistent with fleet precedent): `subject_station="marshal"`/"Marshal-produced artifact" attribution questioned (consistent with existing `BMAD_DRIFT`/`DREAM_CHAIN`/etc. precedent, self-documented); hardcoded check-name string "duplicating" `Source.BMAD_METHOD_VERSION_DRIFT.value` (universal fleet-wide convention, every sibling source does the same); `tuple[int, int, int]` annotation vs. generator-expression widening under strict mypy (no mypy gate exists for this package); missing test asserting WARN doesn't gate `verdict.exit_code_for` (no such test exists for any structurally-identical sibling source either); version-text round-trip through `int()` losing a hypothetical leading-zero literal (not valid semver, purely cosmetic, unrealistic for this file).

### 2026-08-15 — Review pass (fresh, non-forked Blind Hunter + Edge Case Hunter; independent of the prior pass above)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium 1)
- defer: 3 (low 3)
- reject: 1 (low 1)
- addressed_findings:
  - `[medium]` `[patch]` The new `bmad-method-version-drift` DISPATCH-only source shipped with no `[feature.local-recipes.tasks.*]` pixi entry, unlike every sibling this story's own Intent claims to mirror (`due-for-verification-check` et al.) and unlike `scripts/detectors.py`'s frozen `_DOCTOR_SOURCE_TASKS` sweep (which by design excludes both) -- as merged it was reachable only via the bare `python -m pyforge.doctor.sources bmad-method-version-drift` invocation, invisible to `pixi task list` and undocumented anywhere. Added `[feature.local-recipes.tasks.bmad-method-version-drift-check]` in `pixi.toml` immediately after `due-for-verification-check`, mirroring its exact shape; verified live (`pixi run -e local-recipes bmad-method-version-drift-check` correctly warns on the real drift, exit 0) and confirmed the full `pyforge-doctor` suite still passes unchanged (984 passed, 2 skipped -- no test enumerates pixi tasks, so nothing else needed updating).
  - `[low]` `[defer]` `DW-FU-10-1-5` -- `degrade_on_exception`'s own docstring miscounts its repo-scope call-site count ("three... NOT wired in" vs. 9 actual); pre-existing drift predating this story (`chain.py` already broke the claim), this story's new call site is only the 5th instance on top of an already-stale count -- not caused by this story, so deferred rather than patched here.
  - `[low]` `[defer]` `DW-FU-10-1-6` -- `_FLOOR_RE` only recognizes a bare `>=X.Y.Z`, not the compound-range or internal-whitespace forms this repo's own `pixi.toml` already uses for other dependencies; not live for `bmad-method` today, same "degrades cleanly on an unhandled shape" category as the already-tracked `DW-FU-10-1-2`.
  - `[low]` `[defer]` `DW-FU-10-1-7` -- only the manifest's top-level `installation.version` scalar is compared; `modules[].version` entries (verified present in this repo's own live manifest) could diverge from it during a partial/interrupted upgrade with no signal from this check; not live today, a scope question for a follow-up.
  - Rejected (noise / deliberate, spec-documented design choice): `bmad_method.py` funnels every failure mode (missing-input vs. unexpected-error) through one generic `degrade_on_exception` catch with an undifferentiated check name, unlike `chain.py`'s per-failure-mode differentiated check names -- explicitly named as a deliberate simplification in this story's own I/O & Edge-Case Matrix (a single trivial comparison with one check, not `chain.py`'s many independent checks), not an oversight.

### 2026-08-15 — Verification repair pass (bmad-loop deterministic gate, not a code review)

Landing failed bmad-loop's `spec_surface_reconcile.py` verify command: the two review-pass
commits (`e16a2e0f58`, `0f01997c52`) changed 9 files governed by `pyforge-doctor/spec-pyforge-doctor`'s
surface (`src/shared/packages/pyforge-doctor/**`) and 1 file (`pixi.toml`) governed by
`pyforge-steward/spec-python-agent-platform`'s surface, but neither spec's `.memlog.md` moved to
name the drift -- the standing S-13.7 pattern this repo's own memlogs document repeatedly. No
`<intent-contract>` content, code, or test was touched; this is not a `bad_spec`/`patch`/`defer`/
`reject` finding, since nothing about the implementation was wrong. Reconciled by naming all 10
changed paths in the two owning specs' memlogs (following each spec's own established precedent
for prior stories' incidental-overlap entries) and re-stamping the baseline scoped to exactly
those two specs (`python scripts/spec_surface_check.py --write-baseline --spec
pyforge-doctor/spec-pyforge-doctor --spec pyforge-steward/spec-python-agent-platform`). Verified:
`python scripts/spec_surface_reconcile.py` now exits 0 (`OK: every tracked file governed or
allowlisted; no drift`); baseline diff touched only those two spec keys (9 files + pixi.toml, 0
unexpected additions/removals); full `pyforge-doctor-test` suite still 984 passed, 2 skipped.
Committed as `9823184658`.

## Design Notes

New dedicated module, not an extension of `sources/factory.py`'s existing `BMAD_DRIFT`
(the Spec's own open "exact registry placement" question) — `factory.py` is already a
1300-line module tightly coupled to `bmad_drift_check.py`'s origin-script severity mapping
(HARD/DRIFT/INFO) for a *different* artifact class (`pyforge-marshal`'s project-doc
currency); this capability has no such origin script and a single trivial comparison, so a
small dedicated module (mirroring `ledger.py`) is both simpler to review and avoids
overloading an already-dense file (Simplicity First / Surgical Changes).

Comparison sketch (both parses raise on anything unexpected — caught by the outer
`degrade_on_exception`, never handled ad hoc inline):

```python
_FLOOR_RE = re.compile(r"^>=(\d+\.\d+\.\d+)$")

def _parse_version(text: str) -> tuple[int, int, int]:
    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"expected X.Y.Z, got {text!r}")
    return tuple(int(p) for p in parts)  # raises ValueError on a non-digit segment
```

`_declared_floors` walks `data.get("dependencies", {})` plus every
`data.get("feature", {})[*].get("dependencies", {})` table for a `"bmad-method"` key,
`_FLOOR_RE`-matching each; raises if none found at all. `max()` over the parsed tuples
picks the effective floor when more than one table declares it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `0fc0ec9f71` (2026-08-15, "doctor: promote story 10.1 to done in the tracked ledger"); also `9db4490d66` (2026-08-15, "reconcile spec-surface baseline for doctor 10.1's bmad_method.py + steward's pixi.toml ove"); also `5d9e598c2c` (2026-08-15, "Story 10.1: bmad-method-version-drift Source (CAP-1)"). Ledger row `10-1-the-declared-floor-and-the-installed-core-are-compared-and-reported: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
