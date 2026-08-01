<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: "Wrap warden's engine-availability self-check (FR-1)"
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: 'e868b607a10a8fbfba046a191d5ac637bde42f80'
final_revision: 'a216c551a1ecfd57c2a0f7d3f25ade19847d12dc'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py',
  '{project-root}/src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
  '{project-root}/src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py',
  '{project-root}/src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py',
  '{project-root}/pixi.toml',
  '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
]
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Doctor has no way to surface `pyforge-warden`'s proven `--doctor` engine/OSV-DB/feed self-check without either reimplementing its probing logic (drift-prone) or shelling out to the `warden` CLI (forbidden by AD-1).

**Approach:** Add `doctor.sources.warden.gather()`, a library-import gather filter that calls `pyforge.warden.engines.run_doctor_checks` directly and normalizes each `DoctorCheck` into a `Finding(source=Source.WARDEN_DOCTOR, ...)`; wire the already-declared `[gate]` extra into `pixi.toml`'s `[feature.pyforge-doctor.*]` block (mirroring `pyforge-atlas`'s identical edge); and narrow Story 1.1's `test_no_warden_import.py`, which currently bans importing `pyforge.warden` anywhere in the package — the architecture spine's actual AD-3 rule only forbids importing warden's `ErrorKind` into `models.py`'s taxonomy, not a blanket ban, and AD-1 explicitly names `sources/warden.py` as the one sanctioned import site.

## Boundaries & Constraints

**Always:**
- `doctor.sources.warden` imports and calls only `pyforge.warden.engines.run_doctor_checks` — no other warden submodule, no subprocess of its own (AD-1).
- Every `DoctorCheck` normalizes 1:1 to a `Finding(source=Source.WARDEN_DOCTOR, check=check.name, status=OK-or-FAIL, message=check.message, evidence={})` — never dropped, never re-aggregated into one summary Finding.
- If `pyforge.warden.engines` is not importable (gate extra absent), `gather()` catches the `ImportError` and returns exactly one `Finding(status=FAIL, check="pyforge-warden", ...)` naming the missing extra and an install hint — never lets the exception escape.
- Narrow `tests/meta/test_no_warden_import.py`'s scan to exempt `sources/warden.py` only; every other module must still fail the guard on any `pyforge.warden` import. Correct its docstring and `models.py`'s (both currently overstate "Doctor never imports pyforge.warden" as absolute) to state the scoped rule.
- Add a new meta-test (mirrors `test_read_only_guard.py`'s AST-scan idiom) asserting `sources/warden.py` contains no `subprocess` import/call and imports no `pyforge.warden` submodule besides `engines` — with a synthetic-violation positive proof.
- Add `pyforge-warden = { path = "src/shared/packages/pyforge-warden" }` to `[feature.pyforge-doctor.dependencies]` in root `pixi.toml`, mirroring `[feature.pyforge-atlas.dependencies]`'s identical line.
- `gather()` is a plain library function with no CLI dispatch — proven via direct unit tests; `doctor check --engines`'s actual flag wiring is Story 1.5's job (epic-1-context.md Cross-Story Dependencies).

**Block If:** `pyforge.warden.engines.run_doctor_checks`'s signature or `DoctorCheck` shape (`name: str, ok: bool, message: str`) has changed since this spec's investigation — re-verify against the live file before implementing; if it no longer matches, HALT and name the mismatch.

**Never:**
- Never shell out to the `warden` CLI as a subprocess — AD-1 requires a library import, not a reimplementation via subprocess.
- Never import `pyforge.warden.models`/`verdict`/any submodule besides `engines` from `doctor.sources.warden`.
- Never modify `doctor.models`, `doctor.verdict`, or the `DoctorReport` schema — Story 1.1 froze that contract; this story is a producer only.
- Never add the `--engines` CLI flag or wire `doctor check` dispatch — out of scope, Story 1.5's job.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All engines/feeds healthy | `run_doctor_checks` returns 6 all-`ok` `DoctorCheck`s | 6 `Finding(status=OK)`, one per check | No error expected |
| One engine missing (e.g. `osv-scanner`) | one `DoctorCheck(ok=False)` among the 6 | that one `Finding(status=FAIL)`; the other 5 still `OK` | No error expected |
| `pyforge-warden` not installed | `import pyforge.warden.engines` raises `ImportError` | exactly one `Finding(status=FAIL, check="pyforge-warden")` naming the extra + install hint | Caught inside `gather()`, never propagates |
| Equivalence with `warden scan --doctor` | same environment, both `gather()` and `run_doctor_checks` called | per-check `(name, ok, message)` from `run_doctor_checks` equals `gather()`'s per-`Finding` `(check, status==OK, message)`, in order | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` lines 499-517 (`DoctorCheck`) and 706-794 (`run_doctor_checks`) -- the exact function/shape this story wraps; read before writing `sources/warden.py`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py` lines 101-117 (`GateDependencyMissing`/`_load_warden`) -- the established lazy-import-inside-the-function + install-hint pattern to mirror (adapted: Doctor degrades to a `Finding`, never raises).
- `src/shared/packages/pyforge-atlas/tests/policy_gate/test_policy_gate.py` lines 226-242 -- `monkeypatch.setitem(sys.modules, "pyforge.warden", None)`, the idiom for testing the `ImportError` branch without a real uninstall.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `Source.WARDEN_DOCTOR`, `Finding` -- the already-frozen contract this story produces against, unchanged.
- `src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py` -- Story 1.1's guard, over-broad relative to `ARCHITECTURE-SPINE.md` AD-3 (lines 98-111); narrow its exemption list, don't weaken its coverage of every other module.
- `src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py` -- the package-modules/parse/violations/positive-proof AST-scan idiom to mirror for the new sole-warden-import-site guard.
- `pixi.toml` lines 1447-1451 (`[feature.pyforge-doctor.dependencies]`) and line 1373 (`[feature.pyforge-atlas.dependencies]`'s `pyforge-warden` entry) -- add the analogous path dependency.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- new empty package marker.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py` -- `gather(target: Path) -> tuple[Finding, ...]`: imports `pyforge.warden.engines.run_doctor_checks` inside the function body (never at module import time), catches `ImportError` and returns one FAIL `Finding` naming the missing `gate` extra + install hint; otherwise calls `run_doctor_checks(target)` and maps each `DoctorCheck` 1:1 to a `Finding(source=Source.WARDEN_DOCTOR, check=c.name, status=OK-or-FAIL, message=c.message, evidence={})`.
- [x] `src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py` -- exempt `sources/warden.py` from the scan; correct its docstring and `models.py`'s to state the scoped rule (only `sources/warden.py` may import `pyforge.warden`, and only its `engines` submodule).
- [x] `src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py` -- new meta-test scanning `sources/warden.py` only: no `subprocess` import/call, no `pyforge.warden` submodule import besides `engines`; includes a synthetic-violation positive proof.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_warden.py` -- covers the I/O matrix: all-healthy, one-engine-missing, `pyforge-warden` absent (via `monkeypatch.setitem(sys.modules, "pyforge.warden", None)`), and the live equivalence check against `pyforge.warden.engines.run_doctor_checks` called directly.
- [x] `pixi.toml` -- add `pyforge-warden = { path = "src/shared/packages/pyforge-warden" }` to `[feature.pyforge-doctor.dependencies]`.

**Acceptance Criteria:**
- Given an environment where a required engine is missing, when `doctor.sources.warden.gather(target)` runs, then the corresponding `Finding` is `status=FAIL`, `source=Source.WARDEN_DOCTOR`, and every other healthy check still reports `status=OK` -- no check silently dropped.
- Given the same environment, when `pyforge.warden.engines.run_doctor_checks(target)` is called directly, then its per-check `(name, ok, message)` tuples equal `gather(target)`'s per-`Finding` `(check, status==OK, message)` in the same order -- the two never diverge.
- Given the repo, when the new meta-test runs, then it fails against a synthetic `import subprocess` inserted into a parsed copy of `sources/warden.py`'s source and passes against the real file.
- Given `pyforge-warden` is not importable, when `gather(target)` runs, then it returns exactly one FAIL `Finding` naming the missing extra and install hint, and no exception escapes `gather()`.
- Given `pixi.toml`, when inspected, then `[feature.pyforge-doctor.dependencies]` declares `pyforge-warden` as a path dependency, mirroring `[feature.pyforge-atlas.dependencies]`.

## Design Notes

**Resolved contradiction (explicit, not left open):** Story 1.1's review pass added `test_no_warden_import.py` worded as "Doctor never imports pyforge.warden" -- read literally, that blocks this story's entire purpose. `ARCHITECTURE-SPINE.md` AD-3 (lines 98-111) shows the real rule is narrower: it forbids importing warden's `ErrorKind` into `models.py`'s taxonomy, and the spine's own source-tree comment (lines 186-188) explicitly describes an "AD-1 no-reimplementation check (asserts `sources/warden.py` imports, never subprocess-calls, warden)" -- i.e. `sources/warden.py` importing warden is the designed exception, not a violation. This spec narrows the guard rather than escalating, since the architecture spine is authoritative and unambiguous on this point.

Mirror atlas's lazy-import idiom but degrade to a `Finding` instead of raising:

```python
def gather(target: Path) -> tuple[Finding, ...]:
    try:
        from pyforge.warden.engines import run_doctor_checks
    except ImportError:
        return (Finding(
            source=Source.WARDEN_DOCTOR, check="pyforge-warden",
            status=DoctorStatus.FAIL,
            message="pyforge-warden not installed -- install the `gate` "
                    "extra (`pip install pyforge-doctor[gate]`) or add "
                    "pyforge-warden to the environment",
            evidence={},
        ),)
    return tuple(
        Finding(
            source=Source.WARDEN_DOCTOR, check=c.name,
            status=DoctorStatus.OK if c.ok else DoctorStatus.FAIL,
            message=c.message, evidence={},
        )
        for c in run_doctor_checks(target)
    )
```

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full unit + meta suite passes (this worktree's path is 135 chars, well under the ~173-250 byte threshold that panicked `pixi-build-python` for spec-1-1, so this should run to completion; if it still hits that same environmental panic, fall back to the next command and record it as environmental, not a story defect).
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src:src/shared/packages/pyforge-warden/src python3 -m pytest src/shared/packages/pyforge-doctor/tests -q` -- expected: full suite green, substitute verification if the pixi task cannot run.

**Actual results (2026-07-30):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` ran to completion with no `pixi-build-python` panic (worktree path 135 chars, as predicted) -- **85 passed**. Note: the new `pyforge-warden` path dependency required one non-frozen `pixi install -e pyforge-doctor` first to re-solve and update `pixi.lock` (adds warden's own transitive deps: deptry, osv-scanner, cyclonedx-python-lib, etc. -- the same shape `pyforge-atlas`'s environment already carries); `--frozen` then ran clean against the updated lock.
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src:src/shared/packages/pyforge-warden/src python3 -m pytest src/shared/packages/pyforge-doctor/tests -q` -- **85 passed** (matches the pixi run 1:1).
- Post-follow-up-review re-verification (second pass, 2026-07-30): both commands -- **96 passed** each (9 new tests from the follow-up patch set: 3 unit tests for the hardened failure branches in `gather()`, 6 synthetic guard proofs across the two meta-tests).
- One test-authoring correction found and fixed during verification (not a spec deviation, a test-idiom gotcha): a bare `monkeypatch.setitem(sys.modules, "pyforge.warden", None)` doesn't trigger `ImportError` for `gather()`'s `from pyforge.warden.engines import run_doctor_checks` once `pyforge.warden.engines` is already cached in `sys.modules` under its own full dotted key elsewhere in the same test session -- Python's import machinery returns the cached submodule directly without re-consulting the parent's `sys.modules` entry. Fixed by also `monkeypatch.delitem(sys.modules, "pyforge.warden.engines", raising=False)` in `test_pyforge_warden_absent_returns_one_fail_finding_no_exception`. All other tests, including the atlas idiom's own single-level `from pyforge.warden import ...` shape, are unaffected by this gotcha.
- Post-review-pass re-verification: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **87 passed** (2 new tests added during the patch pass below: the `run_doctor_checks`-raises unit test, and the `os.system`/`os.popen` synthetic-guard test).
- Second-follow-up-pass re-verification (third pass, 2026-07-30): both commands -- **103 passed** each (7 new tests: 3 unit -- genuine-absence `ModuleNotFoundError` shape, renamed-symbol plain `ImportError` via an empty-module meta-path loader, truthy-non-bool `ok` fail-safe; 4 meta -- symbol-laundering synthetic proofs, the closed import-surface allowlist test plus its positive and negative proofs).

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 2: (high 0, medium 1, low 1)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `medium` `patch` `gather()` only guarded the `from pyforge.warden.engines import run_doctor_checks` statement in `try/except ImportError` -- the actual `run_doctor_checks(target)` call sat outside that guard, so any future non-`ImportError` exception from warden's own self-check would propagate uncaught and crash the verb, contradicting the module's own "never crashes" docstring claim; a broken-but-installed warden would also have been misdiagnosed as "not installed" had it raised `ImportError` for an unrelated transitive reason. Added a second, separate `try/except Exception` around the `run_doctor_checks(target)` call producing a distinct FAIL `Finding` ("warden's self-check raised an unexpected error: ...") that is never conflated with the missing-extra install-hint message. Added `test_run_doctor_checks_raising_returns_one_fail_finding_no_exception` proving the new branch.
  - `medium` `patch` Both new AST meta-tests' scans missed the `from pyforge import warden` import form (the submodule named as an alias under the parent module, rather than `pyforge.warden`/`pyforge.warden.*`), a real bypass of AD-1's "only `sources/warden.py`, only its `engines` submodule" boundary. Extended `test_no_warden_import.py`'s `_warden_import_violations` and `test_sources_warden_no_subprocess.py`'s `_non_engines_warden_submodule_violations` to catch it, with a synthetic-violation proof added to each guard's existing positive-proof test.
  - `low` `patch` `sources/warden.py` used an absolute import (`from pyforge.doctor.models import ...`) while every sibling module in the package (`verdict.py`, `__main__.py`) uses relative imports -- corrected to `from ..models import DoctorStatus, Finding, Source` to match existing style.
  - `low` `patch` `test_sources_warden_no_subprocess.py`'s subprocess guard only matched `subprocess.*` call sites, missing the `os.system`/`os.popen` alternate shell-out forms AD-1 forbids just as much. Added detection for both, plus `test_guard_fires_on_synthetic_os_system_or_popen_shell_out` proving it fires.
  - `low` `defer` `doctor.sources.warden`'s `_INSTALL_HINT` names `` `pip install pyforge-doctor[gate]` `` even though this monorepo is conda/pixi-distributed and `pyforge-warden` isn't on PyPI -- deliberately mirrors `pyforge.atlas.pipelines.universal_sbom.gate`'s own identical pre-existing hint phrasing verbatim (this story's own Design Notes specified it); a cross-package wording fix belongs in a follow-up touching both packages together, not a unilateral change here. Logged in `deferred-work.md`.
  - `medium` `defer` Even after the `from pyforge import warden` fix, a more convoluted bypass remains theoretically open: a bare `import pyforge.warden` (deliberately treated as a non-violation by itself) followed later by a deep attribute chain into a non-`engines` submodule would evade both guards, since neither tracks name bindings across subsequent attribute access. Consistent with this codebase's own explicitly-stated "best-effort STATIC, dynamic dispatch out of scope" bound for every sibling AST meta-test (`test_read_only_guard.py`'s own stated limitation); closing it fully needs data-flow analysis beyond any existing guard's scope. Logged in `deferred-work.md`.
  - `low` `reject` (x7, noise/already-settled, dropped silently): the missing-extra `Finding`'s `status=FAIL` (not `WARN`) exactly matches epics.md's own explicit AC4 mandate, not a defect to revisit unilaterally; the absent-warden test coverage uses the same `monkeypatch.setitem(sys.modules, ...)` idiom this exact codebase already established and accepts for the identical scenario in `pyforge-atlas`'s test suite; `evidence={}` is correct as written since warden's own `DoctorCheck` dataclass (`name`/`ok`/`message` only) carries no additional structured data to preserve -- there is nothing being discarded; `Finding.check` is a documented free-form `str` field, not a closed enum, so a synthetic `"pyforge-warden"` value outside the 6 real check names is not a contract violation; the live-equivalence test's two real, unmocked `run_doctor_checks` calls in succession is inherent to proving the AC's "never diverge" claim and reads only static/read-only local state (no realistic mutation window); the exemption-path literal duplicated across two test files fails safe in both rename directions (either guard fires loud on a stale path, never silently passes with a gap), so added cross-file coupling isn't worth it; and the "exemption is exempted" test, while self-referential, is not vacuous (a typo in the exemption set would be caught) even though it doesn't independently re-derive correctness.


### 2026-07-30 — Follow-up review pass (fresh pass on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 0
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `medium` `patch` `gather()`'s `except ImportError` could not distinguish "warden absent" from "warden installed but its own import chain broke" -- a transitive dependency's `ModuleNotFoundError` (warden's `engines.py` imports packaging, feeds, currency, hygiene at module-body time) or a renamed symbol's plain `ImportError` both produced the missing-extra install hint, misdirecting the operator to install an already-installed extra (the exact failure the first pass's fix half-covered). Restructured: `ModuleNotFoundError` whose `.name` is in `{pyforge, pyforge.warden, pyforge.warden.engines}` → install hint; any other import-time exception → a distinct "installed but failed to import: <error>" Finding. Added `test_transitive_module_not_found_reports_broken_not_absent` using a meta-path finder that makes the engines re-import raise, no real uninstall needed.
  - `medium` `patch` A non-`ImportError` raised while executing warden's module body at first import (corrupted install) escaped `gather()` entirely, contradicting the module's own "no exception ever escapes" contract. The same restructure adds `except Exception` as the import guard's final arm, routing to the installed-but-broken Finding. Added `test_non_import_error_during_warden_import_returns_one_fail_finding` (OSError via the same meta-path finder).
  - `medium` `patch` Both AST guards resolved only absolute import forms -- `pyforge` is a namespace package, so `from .. import warden` / `from ..warden.models import X` (in package modules) and `from ...warden import verdict` (in sources/warden.py) reach pyforge.warden while carrying `module="warden…"`/`None` + `level>0` in the AST, matching nothing; the package's own house style IS relative imports, making this the likeliest real bypass form. Added `_resolve_import_from` + per-module package-parts resolution to both guards (the relative spelling of the sanctioned engines import resolves identically and stays sanctioned), with positive synthetic proofs in each file and negative proofs for benign relative imports.
  - `low` `patch` The `tuple(Finding(...) for check in checks)` normalization sat outside the second guard -- a shape-drifted `DoctorCheck` (field renamed/removed in a future warden) would raise `AttributeError` straight out of `gather()`. Moved normalization inside the same `try/except Exception` as the `run_doctor_checks` call; added `test_malformed_doctor_checks_return_one_fail_finding_no_exception` (`[object()]` as the result).
  - `low` `patch` The shell-out guard missed `from os import system` (binds the primitive with no attribute access), `import os as _o; _o.system(...)` (attribute check keyed to the literal name "os"), and the `os.spawn*`/`os.exec*`/`os.posix_spawn*` family. Extended `_subprocess_violations` with an os-alias collection pass, a `from os import <shell-out-name>` check, and a shared `_is_os_shell_out_name` predicate; four new synthetic proofs incl. a benign-os negative (`os.getcwd`, `from os import path` stay clean).
  - `low` `patch` `alias.name.startswith("pyforge.warden.engines")` admitted a hypothetical `pyforge.warden.engines_evil` (no dot boundary), and the `ast.Import` branch permitted `pyforge.warden.engines.sub` while the `ast.ImportFrom` branch flagged the equivalent form -- the two branches disagreed. Now exact-match `== "pyforge.warden.engines"` in both branches (engines is a module, not a package; sub-paths are not sanctioned); synthetic proofs for the sibling, sub-path, and from-sibling forms.
  - `low` `reject` (x9, noise/already-settled, dropped silently): the two failure Findings being machine-indistinguishable (`check="pyforge-warden"`, `evidence={}`) matches the spec's own Design Notes shape -- the free-form message is the designated carrier and no AC requires machine separation; the `_INSTALL_HINT` pip-command wording is ALREADY a deferred-work ledger entry from the first pass (the orchestrator owns existing entries -- not re-raised); AST-machinery duplication across the two meta-test files re-litigates the first pass's settled self-contained-guards disposition, and the two scanners have deliberately different semantics (total ban vs engines-only); the live-equivalence test's clock/cache flake window re-litigates a settled reject -- the residual risk (a staleness boundary crossing between two sub-second-adjacent calls) is negligible and hermeticizing would defeat the test's "live" purpose; the spec's "Never modify doctor.models" vs its Always-clause docstring correction is not a real contradiction (the Never clause scopes to the frozen contract shapes, and the edit is prose-only); `gather()` having no caller yet is the spec's explicit scope (CLI wiring is Story 1.5) and the warden env payload is the spec-mandated pixi path dep; stale spec frontmatter is workflow-managed state, not a code finding; the `importlib.import_module`/`__import__`/`getattr` dynamic-evasion class and the bare-`import pyforge.warden` attribute-chain bypass both sit inside the existing ledger entry's "best-effort STATIC, dynamic dispatch out of scope" bound -- no new entry appended (duplicate coverage).

### 2026-07-30 — Second follow-up review pass (fresh pass on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (high 0, medium 0, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `medium` `patch` Both meta-guards were module-granular while the spec's Always-clause is symbol-granular ("imports and calls only `pyforge.warden.engines.run_doctor_checks`") — warden's `engines.py` holds `os`, `subprocess`, `ErrorKind`, and a name-identical `Finding` in its module namespace, so `from pyforge.warden.engines import subprocess as sp` / `import os as _x` / `import ErrorKind` were all proven to pass both guards with zero violations, laundering forbidden names (including AD-3 vocabulary and a clean shell-out vehicle) through the sanctioned module. Added a symbol-level allowlist to `_non_engines_warden_submodule_violations`: any `from pyforge.warden.engines import <name != run_doctor_checks>` (including `*` and mixed lists) is now flagged; five synthetic-violation proofs added.
  - `medium` `patch` The absent-warden unit test's None-sentinel simulation provably raises `ModuleNotFoundError(name='pyforge.warden.engines')` (CPython's "not a package" branch) while GENUINE absence raises `name='pyforge.warden'` — no test exercised the real shape, so a mutation dropping `"pyforge.warden"` from `_WARDEN_MODULES` survived all 96 tests while misrouting the story's headline warden-not-installed scenario to the wrong message. Added `test_genuine_absence_shape_names_parent_and_gets_install_hint` via the existing `_RaisingEnginesFinder` idiom raising the parent-named `ModuleNotFoundError`; the classification set is now mutation-detectable.
  - `low` `patch` The shell-out denylist was an arms race (two prior passes each grew it, and this pass proved `pty.spawn`, `asyncio`'s subprocess helpers, and `import importlib` still passed) — added a closed positive-allowlist guard: `_SANCTIONED_IMPORTS` = {`__future__`, `pathlib`, `pyforge.doctor.models`, `pyforge.warden.engines`} plus `test_sources_warden_import_surface_is_exactly_the_sanctioned_set`, ending every STATIC import-bypass class at once (pty/asyncio/os/importlib/ctypes synthetic proofs added; the denylist stays as defense-in-depth). Incidentally closes the static half of the previously-rejected dynamic-import class (`import importlib` no longer fits the surface).
  - `low` `patch` Two docstring overclaims corrected: `gather()`'s "No exception ever escapes" is false for `BaseException` (`KeyboardInterrupt`/`SystemExit` propagate — correctly, but Story 1.5's verb assembly will read this contract; now states "no `Exception` escapes; `BaseException` intentionally propagates"), and "never dropped, never re-aggregated" sat directly above the degrade path that replaces all checks with one FAIL `Finding` on normalization failure (now scoped to the success path). An `except SystemExit` handler was considered and rejected — swallowing intentional aborts is worse; the docstring fix is the right repair.
  - `low` `patch` The module docstring's own documented "renamed symbol's plain `ImportError`" failure shape had zero test coverage (the except-Exception import arm was exercised only by `OSError`) — added `test_renamed_symbol_plain_import_error_reports_broken_not_absent` via an empty-module meta-path loader, so the from-import itself raises the real `ImportError` shape a future warden rename would produce.
  - `low` `patch` `DoctorStatus.OK if check.ok else FAIL` false-greened a shape-drifted truthy non-bool `ok` (e.g. the string `"false"`) — now strict `check.ok is True`, failing safe as FAIL on any non-bool drift; `test_truthy_non_bool_ok_fails_safe_as_fail` added. (Real warden bools behave identically; the live-equivalence test is unaffected.)
  - `low` `defer` Warden's ok-with-caveat states ("EPSS feed present but stale", "operating air-gapped" — `ok=True` with the consequence only in message text) flatten to plain OK through the spec-mandated binary mapping, making `DoctorStatus.WARN` unreachable from `Source.WARDEN_DOCTOR`; whether specific warden check shapes deserve WARN promotion is Story 1.3's tri-state design decision, and warden's coarse `ok: bool` encoding is pre-existing. Logged in `deferred-work.md`.
  - `low` `reject` (x8, noise/already-settled/speculative, dropped silently): an empty `run_doctor_checks` result returning `()` is the faithful 1:1 mapping of zero checks, not a defect (fabricating a synthetic FAIL would violate the never-re-aggregate contract on speculative future drift); the bare-`import pyforge.warden`-plus-attribute-chain bypass and its `import pyforge` attribute-spelled twin are both inside the existing ledger entry's "best-effort STATIC, no cross-binding data-flow" bound (orchestrator owns that entry — not re-raised); the `importlib`/`__import__`/`getattr` dynamic-evasion class re-litigates a settled reject from the first follow-up pass (and its static half is now incidentally closed by the allowlist); catching `SystemExit` inside `gather()` (docstring fix taken instead — see above); the unit-test module being uncollectable without warden installed is acceptable in-repo (this story's own pixi path dep guarantees warden in the test env, and no warden-less CI lane exists); `_WARDEN_MODULES`' `"pyforge"` member being unreachable is harmless conservatism, kept; and the PR maintenance-label reminder is workflow-managed process, not an artifact defect (noted in the run result instead).

## Auto Run Result

Status: done (third pass -- second follow-up review, 2026-07-30)

**Summary:** Fresh adversarial + edge-case review of the completed Story 1.2 diff (baseline `e868b607` → `da978d83`) found no live defect in the shipping code path but six hardening gaps, all patched in this pass: the two AST meta-guards were module-granular where the spec's contract is symbol-granular (a proven laundering bypass through the sanctioned `engines` import), the headline warden-absent scenario was only tested via a simulation that raises a different `ModuleNotFoundError` shape than genuine absence, the shell-out denylist was an open arms race (now closed with a positive import-surface allowlist), two docstring contract overclaims, one uncovered documented failure shape, and a truthy-non-bool `ok` false-green (now strict `is True`).

**Files changed (this pass, commit `a216c551a1`):**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py` -- docstring contract corrections (BaseException propagation; degrade-path scoping) + strict `check.ok is True` mapping.
- `src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py` -- symbol-level allowlist on the sanctioned engines import; closed `_SANCTIONED_IMPORTS` surface guard; 3 new proof tests.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_warden.py` -- genuine-absence shape, renamed-symbol plain `ImportError`, and truthy-non-bool `ok` tests.

**Review breakdown:** 6 patched (2 medium, 4 low), 1 deferred (WARN-flattening design question → new `deferred-work.md` entry for Story 1.3), 8 rejected (speculative drift, settled re-litigations, ledgered classes).

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and the PYTHONPATH substitute both **103 passed** (96 prior + 7 new).

**Follow-up review recommendation: false** -- of the six patches, five are test/docstring-only; the single production behavior change is the one-token strict-identity `ok` mapping, provably fail-safe and covered by a dedicated test. Three passes show converging severity (taxonomy restructure → guard-bypass closures → symbol-level tightening); nothing here warrants a fourth.

**Residual risks:** the attribute-chain and dynamic-dispatch guard-bypass classes remain open by explicit ledgered disposition ("best-effort STATIC" bound -- the orchestrator owns that entry); the eventual PR to `rxm7706/local-recipes` touches `pixi.toml` + `src/**` (outside `recipes/`), so it needs the `maintenance` label at open time (the `environment.yaml` sync gate is NOT triggered -- `feature.pyforge-doctor` is not part of the `build` environment).

