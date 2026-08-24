---
title: 'Story 14.1: The leaf exists and is provably a leaf'
type: 'feature'
created: '2026-08-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/planning-artifacts/specs/spec-pyforge-core/SPEC.md']
warnings: ['oversized']
baseline_revision: '1c3a5aa7011ecb3ccece67388916b41b65d8d72b'
final_revision: '27704b980a9158d04545e61c43a165c168eb319e'
---

<intent-contract>

## Intent

**Problem:** Five primitives (atomic write, verdict lattice, report envelope, exception root,
subprocess guard) are copied 3-20x across eight stations with no shared home, and Epic 7's
upcoming Stories 7.2/7.3 are about to mint copy #21 and copy #6 inside the very effort meant to
consolidate them — no `pyforge-core` package exists yet to land those extractions in.

**Approach:** Scaffold `src/shared/packages/pyforge-core/` as a new pixi build workspace member
(mirrors the pyforge-scribe/pyforge-warden pattern exactly) with an empty, pure-stdlib
`pyforge.core` package, wired into root `pixi.toml` with its own lean environment, and add a
meta-test that structurally fails the build if any module under it ever imports from another
pyforge station. No primitive extraction happens in this story — that is Stories 14.2-14.4.

## Boundaries & Constraints

**Always:**
- `pyforge-core` follows the exact `src/shared/packages/<name>` convention every existing
  station uses: its own `[package]` table in a member `pixi.toml` (no `[workspace]` table),
  a hatchling `pyproject.toml`, `src/pyforge/core/` as an implicit-namespace subpackage, and no
  `src/pyforge/__init__.py` (would shadow the eight sibling stations, PEP 420).
- `pyforge-core` declares zero third-party runtime dependencies — `python = ">=3.12"` only
  (matches every existing station's floor), in both `pixi.toml`'s `[package.run-dependencies]`
  and `pyproject.toml`'s `[project].dependencies`. `hatchling` stays a host/build-only
  dependency, never a runtime one.
- A meta-test under `tests/meta/` enumerates every `.py` module in the installed `pyforge.core`
  package (AST-based, not a text scan — matches the established convention in
  `pyforge-warden/tests/meta/test_verdict_sole_ownership.py` and
  `pyforge-steward/tests/meta/test_invariants.py`) and fails if any imports from `pyforge.<X>`
  for any `X != "core"` — the general form of "for any of the eight," and correct regardless of
  whether a ninth station is ever added.
- The same meta-test proves it is not vacuous: it asserts a synthetic violation (e.g. a source
  string containing `from pyforge.warden import x`) IS flagged by its own detector function,
  since the real package has nothing to violate it yet.
- Root `pixi.toml` gains `[feature.pyforge-core.dependencies]` (path dep + `hatchling` +
  `python-build` + `pytest`, mirroring every sibling station's block exactly),
  `[feature.pyforge-core.tasks.pyforge-core-{test,build-conda,build-dist,build}]`, and a lean
  `pyforge-core = { features = ["pyforge-core"], no-default-feature = true }` environment entry
  — same shape as `pyforge-scribe`'s.
- Because `pixi.toml` changes, regenerate and commit `environment.yaml` via
  `pixi project export conda-environment -e build > environment.yaml` (repo-wide, ungated rule
  — independent of the `maintenance` PR label).

**Block If:** none identified — package layout, the leaf rule, and the meta-test pattern are
fully specified by AD-66/FR-157 and already-shipped sibling stations.

**Never:**
- No primitive extraction (atomic write, verdict lattice, report envelope, exception root,
  subprocess guard) and no removal of any existing station's copies — that is Stories 14.2,
  14.3, and 14.4.
- No `[project.scripts]` / console entry point and no CLI module — `pyforge-core` is a leaf
  library, not a station; it holds no Dream and casts no verdict (SPEC.md Non-goals).
- No edit to any of the seven other stations' `pixi.toml` or `pyproject.toml` — none of them
  depends on `pyforge-core` yet; that wiring belongs to the extraction stories.
- No addition to `pyforge-container`'s composed `features` list in root `pixi.toml` —
  `pyforge-core` is not a station CLI and that env only composes what already exists.
- No station-roster data or module inside `pyforge-core` (Q1 in SPEC.md is explicitly
  deferred — "Not the station roster, yet").
- No import-linter (`lint-imports`) contract — that is Marshal's own internal-seam tool; the
  leaf constraint here follows the AST-meta-test convention every other station's
  cross-cutting invariant already uses.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean install | `pixi install -e pyforge-core` on this checkout | Resolves and installs the built `pyforge-core` conda package into a fresh env | No error expected |
| Package import | `python -c "import pyforge.core; print(pyforge.core.__version__)"` in the `pyforge-core` env | Prints `0.1.0`, exits 0, no side effects | No error expected |
| Leaf-violation probe | Synthetic source `"from pyforge.warden import x\n"` fed to the detector function | Detector reports it as a violation | A guard that never fires on this is vacuous — test fails |
| Legitimate self-import | Synthetic source `"from pyforge.core import something\n"` fed to the detector function | Detector reports no violation | False positive would block every future extraction story |
| Namespace shadow probe | `src/pyforge/__init__.py` existence check (mirrors steward's PEP 420 guard) | Asserted absent | Presence would silently break every sibling station's install |
| Third-party import probe | Synthetic source `"import requests\n"` fed to the pure-stdlib detector | Detector reports it as a violation | A guard that never fires on this is vacuous — test fails |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/pixi.toml` -- NEW: `[package]` table (pixi-build-python
  backend), mirrors `pyforge-scribe/pixi.toml` minus any third-party run-dependency.
- `src/shared/packages/pyforge-core/pyproject.toml` -- NEW: hatchling build backend,
  `dependencies = []`, `packages = ["src/pyforge"]`.
- `src/shared/packages/pyforge-core/README.md` -- NEW: what the leaf is, why it exists, how to
  run its test task (mirrors `pyforge-scribe/README.md`'s shape).
- `src/shared/packages/pyforge-core/.gitignore` -- NEW: build-artifact ignores, copied from an
  existing station (`dist/`, `dist-conda/`, `*.conda`, `*.whl`, `__pycache__/`, etc.).
- `src/shared/packages/pyforge-core/src/pyforge/core/__init__.py` -- NEW: module docstring +
  `__version__ = "0.1.0"` only, no other exports (mirrors `pyforge-scribe`'s `__init__.py`).
- `src/shared/packages/pyforge-core/src/pyforge/core/py.typed` -- NEW: empty PEP 561 marker.
- `src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py` -- NEW: the AST-based
  no-station-import guard + the pure-stdlib guard + their non-vacuous synthetic-fixture proofs
  + the PEP 420 namespace guard.
- `pixi.toml` -- add `[feature.pyforge-core.dependencies]`, four
  `[feature.pyforge-core.tasks.pyforge-core-*]` entries (insert alongside the other stations'
  blocks, ~line 1611-1700), and one `pyforge-core` lean environment entry in `[environments]`
  (~line 383, beside the other lean per-station envs).
- `environment.yaml` -- regenerate via `pixi project export conda-environment -e build` (the
  repo's ungated pixi.toml-change rule).

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-core/{pixi.toml,pyproject.toml,README.md,.gitignore}` --
  scaffold the workspace-member manifests -- establishes `pyforge-core` as a buildable,
  installable pixi package with zero third-party runtime deps
- [x] `src/shared/packages/pyforge-core/src/pyforge/core/{__init__.py,py.typed}` -- scaffold the
  empty leaf package -- gives every later extraction story (14.2-14.4) a stable importable home
- [x] `src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py` -- AST-based guard:
  no module under `pyforge.core` imports `pyforge.<X>` for any `X != "core"`; no module imports
  a non-stdlib third-party package; no `src/pyforge/__init__.py` exists; each guard proven
  non-vacuous against a synthetic violation -- makes AD-66/FR-157's leaf rule structural, not a
  convention
- [x] `pixi.toml` -- add the `pyforge-core` feature (dependencies + four tasks) and its lean
  environment entry, following the pyforge-scribe block exactly -- wires the new member into
  the workspace without touching any existing station's block
- [x] `environment.yaml` -- regenerate (`pixi project export conda-environment -e build`) --
  keeps the ungated env-sync CI gate green

**Acceptance Criteria:**
- Given the workspace, when `pixi install -e pyforge-core` runs on a clean checkout, then it
  resolves and installs the built `pyforge-core` conda package with no third-party runtime
  dependency pulled in beyond `python`.
- Given the installed `pyforge.core` package, when the leaf-constraint meta-test runs, then no
  module imports from `pyforge.<station>` for any of the eight stations, and the guard is
  proven alive by a synthetic-violation fixture, not just by scanning an (currently near-empty)
  real package.
- Given the same meta-test, when a legitimate self-import (`pyforge.core` importing its own
  submodules) is fed to the detector, then it is NOT flagged — the guard narrows to
  cross-station imports only.
- Given `pyforge-core`'s manifests, when `pyproject.toml`'s `dependencies` and `pixi.toml`'s
  `[package.run-dependencies]` are inspected, then neither declares any package beyond
  `python`.
- Given the seven pre-existing stations, when this story lands, then none of their own
  `pixi.toml` or `pyproject.toml` files changed — each remains independently conda-installable
  exactly as before.
- Given root `pixi.toml` changed, when `pixi project export conda-environment -e build` runs,
  then the regenerated `environment.yaml` is committed alongside it.

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 1, medium 0, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter, independently confirmed by direct reproduction:
    `_station_import_violations` blanket-skipped every relative import (`node.level > 0`) on
    the theory that a relative import "resolves within `pyforge.core` itself." False —
    `from .. import warden` placed in `pyforge/core/__init__.py` resolves to `pyforge.warden`
    and imports it successfully at runtime whenever both packages share an environment (e.g.
    `pyforge-container`), because `pyforge` is a merged PEP 420 namespace across every
    station. This is a complete, exploitable bypass of the exact guarantee this story exists
    to ship. Fixed by resolving relative imports against each scanned file's own package path
    (`_resolved_module`, mirrors `pyforge-steward`'s identical helper in
    `tests/meta/test_invariants.py`), reporting a climb past the top-level package as a
    violation too rather than silently truncating it. Added two new tests covering the fixed
    shape and the unresolvable-climb case; mutation-tested by planting the exact bypass line
    in the real `__init__.py`, confirming red, then restoring and confirming green again.
  - `[low]` `[patch]` Blind Hunter: the station-import and stdlib guards scanned the
    *installed* package (via `pyforge.core.__file__`) while the namespace guard scanned the
    *source tree* — an internal inconsistency within one file, risking a stale-installed-copy
    false green if source is edited without reinstalling first. Unified all scanning to the
    source tree (`PKG_ROOT`), matching `pyforge-steward`'s convention across its entire
    meta-test suite; dropped the now-unneeded real `import pyforge.core`.
  - `[low]` `[patch]` Blind Hunter: the module docstring claimed four import shapes —
    including aliased `import pyforge.<X> as y` — were proven non-vacuous by synthetic
    fixture, but the aliased form was never actually exercised by any test. Added the missing
    assertion.
  - `[low]` `[defer]` Blind Hunter: `pyforge-core/.gitignore`'s `/dist/`/`/dist-conda/` lines
    carry inline comments `.gitignore` cannot parse, so both patterns are dead (confirmed via
    `git check-ignore`/`git add -n`). Pre-existing, byte-for-byte copied from
    `pyforge-scribe/.gitignore` per this spec's own mirroring instruction, and the identical
    defect for `pyforge-doctor`/`pyforge-warden` is already recorded as still-open in this
    file's own 2026-07-29 reconciliation note. Deferred as `DW-FU-14-1` — a fleet-wide,
    one-sweep fix across every package's `.gitignore`, outside this story's scaffolding-only
    surface.

## Design Notes

**Why "any `pyforge.X` where `X != core`" instead of enumerating the eight station names.**
AD-66/FR-157 say "for any of the eight," but SPEC.md's own Q1 explicitly defers whether the
station roster belongs anywhere near `pyforge-core`. Hardcoding eight literal names would (a)
take an implicit position on Q1 by embedding roster knowledge in the leaf's own test suite, and
(b) go stale the moment a ninth station is ever added — the exact failure mode the project's own
"derive, don't declare" convention exists to prevent. Banning every `pyforge.*` import except
`pyforge.core` itself is a strictly more conservative implementation of the same rule: it is a
superset of "the eight," requires zero cross-repo file reads, and needs no update if the roster
ever changes.

**Why a synthetic-fixture proof, not just scanning the real package.** This story ships an
empty `pyforge.core` — there is nothing in it yet for the AST scanner to legitimately flag.
Without a synthetic violation asserted separately, the test would be vacuously green forever
(passing whether or not the detector logic actually works), which is exactly the failure the
`pyforge-warden` sole-ownership test's own `test_guard_is_alive_...` case guards against.
Example shape:

```python
def test_detector_fires_on_a_synthetic_station_import():
    assert _station_import_violations(
        ast.parse("from pyforge.warden import something\n")
    )

def test_detector_does_not_fire_on_a_self_import():
    assert not _station_import_violations(
        ast.parse("from pyforge.core import something\n")
    )
```

## Verification

**Commands:**
- `pixi install -e pyforge-core` -- expect a clean resolve + install, no errors
- `pixi run --frozen -e pyforge-core pyforge-core-test` -- expect all tests pass
- `pixi run --frozen -e pyforge-core python -c "import pyforge.core; print(pyforge.core.__version__)"`
  -- expect `0.1.0`, exit 0
- `pixi run --frozen -e pyforge-core pyforge-core-build-conda` -- expect the `.conda` artifact
  builds cleanly under `dist-conda/`
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-core` -- expect zero
  findings
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-core` -- expect zero findings
- `git diff --stat -- 'src/shared/packages/pyforge-*/pixi.toml' 'src/shared/packages/pyforge-*/pyproject.toml'`
  excluding `pyforge-core` -- expect empty (no sibling station manifest touched)
- `pixi project export conda-environment -e build > environment.yaml && git diff --stat environment.yaml`
  -- run after the `pixi.toml` edit; commit if it reports a diff

**Manual checks (if no CLI):**
- Confirm `pixi.toml`'s new `[feature.pyforge-core.*]` blocks and `pyforge-core` environment
  entry follow the exact `pyforge-scribe` block's shape (comment header, dependency set, task
  names) so the workspace stays visually consistent across all nine members.

## Auto Run Result

Status: done

**Summary:** Scaffolded `pyforge-core` as a 9th pixi build workspace member — a pure-stdlib
leaf package no station depends on yet, with a structural (AST-based) meta-test proving it
imports nothing from any other pyforge station and no third-party package. No primitive
extraction lands here; that is Stories 14.2-14.4.

**Files changed:**
- `src/shared/packages/pyforge-core/pixi.toml` (new) -- `[package]` table, `pixi-build-python`
  backend, `python>=3.12` in host+run-deps, `hatchling` host-only
- `src/shared/packages/pyforge-core/pyproject.toml` (new) -- hatchling backend, `dependencies
  = []`, no `[project.scripts]`
- `src/shared/packages/pyforge-core/README.md` (new) -- what the leaf is, how to run its tests
- `src/shared/packages/pyforge-core/.gitignore` (new) -- build-artifact ignores (same
  pre-existing inline-comment defect as several sibling packages -- deferred, see below)
- `src/shared/packages/pyforge-core/src/pyforge/core/__init__.py` (new) -- module docstring +
  `__version__ = "0.1.0"` only
- `src/shared/packages/pyforge-core/src/pyforge/core/py.typed` (new) -- empty PEP 561 marker
- `src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py` (new) -- AST-based
  leaf-constraint guard (no `pyforge.<station>` import, including resolved relative imports),
  pure-stdlib guard, and a PEP 420 namespace guard, each proven non-vacuous by synthetic
  fixture
- `pixi.toml` -- added `[feature.pyforge-core.dependencies]`, four
  `[feature.pyforge-core.tasks.pyforge-core-*]` entries, and the lean `pyforge-core`
  environment; no existing station's block touched
- `pixi.lock` -- regenerated by `pixi install -e pyforge-core`
- `environment.yaml` -- regenerated; no diff (the `build` environment does not compose any
  per-station lean feature, including the new one)

**Review findings breakdown:** 2 reviewers (Blind Hunter, Edge Case Hunter) in parallel, no
shared context. 4 distinct findings survived triage. 3 patched (1 high: the station-import
guard blanket-skipped relative imports, but `from .. import warden` inside
`pyforge/core/__init__.py` resolves to and successfully imports `pyforge.warden` at runtime
whenever both share an environment -- a complete, exploitable bypass of this story's central
guarantee, independently reproduced and mutation-tested before and after the fix; 2 low: an
installed-vs-source scanning inconsistency between guards in the same file, and an
aliased-import shape claimed proven but never actually tested). 1 deferred (low: the new
`.gitignore`'s `/dist/`/`/dist-conda/` lines are dead due to inline comments `.gitignore`
cannot parse -- a pre-existing fleet-wide pattern, already tracked for two other stations in
this same ledger; recorded as `DW-FU-14-1`). 0 rejected, 0 intent gaps, 0 bad-spec loopbacks.

**Follow-up review recommendation:** false. The one high-severity patch is narrowly scoped to
a single detector function plus its tests, has no runtime-behavior/API/security/data impact
on any shipped code (the package is still empty), and was independently mutation-tested in
this same pass (planted the exact bypass, confirmed red, restored, confirmed green) --
materially reducing the value of a second independent review pass. The two low-severity
patches are cosmetic/coverage-only.

**Verification performed:**
- `pixi run --frozen -e pyforge-core pyforge-core-test`: 10 passed (8 original + 2 added by
  the review-pass fix)
- `python -c "import pyforge.core; print(pyforge.core.__version__)"`: printed `0.1.0`, exit 0
- `pixi run --frozen -e pyforge-core pyforge-core-build-conda`: `.conda` artifact built under
  `dist-conda/`
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-core`: all checks passed
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-core`: 1 pre-existing,
  repo-wide error class (installed-package resolution against the `local-recipes` env, not a
  per-package isolated env -- reproduced identically against `pyforge-scribe`, 21 errors of
  the same class there; no CI workflow invokes pyright today)
- `git diff --stat` against the sibling-manifest glob, excluding `pyforge-core`: empty --
  confirmed no other station's `pixi.toml`/`pyproject.toml` changed
- Mutation test: planted `from .. import warden` in the real `__init__.py`, confirmed the
  leaf-constraint test failed with the exact violation reported, then restored and confirmed
  all 10 tests green again

**Residual risks:** None identified for this story's own scope. The leaf-constraint guard now
correctly resolves relative imports, but remains a best-effort static AST check by design
(dynamic import via `importlib.import_module`/`__import__` is out of scope, stated in the
file's own docstring, matching every sibling meta-test's identical limitation) -- acceptable
since no code exists yet to exploit that gap and the extraction stories (14.2-14.4) inherit
the same guard unchanged.
