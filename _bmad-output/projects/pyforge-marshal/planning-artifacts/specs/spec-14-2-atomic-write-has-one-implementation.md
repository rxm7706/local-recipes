---
title: 'Story 14.2: Atomic write has one implementation'
type: 'feature'
created: '2026-08-12'
status: 'done'
review_loop_iteration: 2
followup_review_recommended: false
context: ['{project-root}/_bmad-output/planning-artifacts/specs/spec-pyforge-core/SPEC.md']
warnings: ['oversized']
baseline_revision: '2cd08f7e76ac8afd5589f26d0d14a90a601cef06'
final_revision: '1d60da0193a9bc7042b8d2f87eac78b9bbee2bf4'
---

<intent-contract>

## Intent

**Problem:** The tmp-in-dir + `os.replace` atomic-write pattern is hand-written 20 times across
6 stations (herald 6, atlas 5, marshal 5, steward 2, scribe 1, warden 1 — 3 of those 20 are
duplicate bodies within one warden file), each copy self-aware ("mirrors `state.write`") but none
sharing code. Two of those 20 are `Protocol` declarations with no body (marshal's `ports/fs.py` /
`ports/record.py`) — 18 files hold a real implementation.

**Approach:** Add `pyforge.core.atomic_write` (`atomic_write`/`atomic_write_bytes`/
`atomic_write_text`, `mkstemp`-based) to the `pyforge-core` leaf scaffolded by Story 14.1. Every
one of the 18 real copies is rewritten to call it and retired in this same story (no parallel
path). `pyforge-core` becomes a genuine run-dependency of the 6 stations that use it (atlas,
herald, marshal, scribe, steward, warden — doctor and mason have no copy, untouched).

## Boundaries & Constraints

**Always:**
- One primitive: `atomic_write(path, write_fn, *, mode=None)` (`write_fn(tmp_path)` populates an
  unopened `mkstemp`-created temp file in `path`'s own directory; `os.replace`s on success;
  removes the temp file and re-raises unchanged on any failure — no new exception type).
  `atomic_write_bytes`/`atomic_write_text` are thin convenience wrappers. `mode: int | None`
  `os.chmod`s the temp file before the replace (herald's `registry.py` is the one caller that
  needs this, to preserve a tracked file's pre-existing permission bits).
- Every call site keeps its OWN pre-existing behavior around the call: exception wrapping
  (`HeraldError`/`FsError`/`HarnessPolicyWriteError`/`PolicyIOError` — 4 stations wrap; scribe,
  steward, warden raise raw, and the primitive raising raw preserves that unchanged), advisory
  locking (herald's `locking.locked`, scribe's own `_locked`), pre-write sorting
  (`progress.py`), and any pre-write short-circuit (`config.py::materialize`'s content-addressed
  idempotent-skip, AD-35 — untouched, only its final "write these bytes" call moves).
  `refresh.py::_atomic_write`'s existing `write_fn: Callable[[Path], None]` callback shape maps
  directly onto the primitive's own callback form (used for both JSON text and parquet binary).
- `mkstemp`'s guaranteed-unique, `O_EXCL`-backed naming replaces every hand-rolled tmp-naming
  scheme (marshal's pid+thread-id names in `fs_local.py`/`harness_bmadloop.py`/`config.py`,
  steward's pid+thread-id names, atlas's fixed `.tmp` suffix, refresh.py's fixed suffix) — a
  strict safety improvement (mkstemp cannot collide even across pid recycling, unlike two of
  those hand-rolled schemes) that changes no happy-path observable behavior. `mkdir(parents=True,
  exist_ok=True)` runs unconditionally, adding it to the 2 sites that omitted it
  (`admission.py`, `lasuite.py` — every other site, including `budget.py`/`keys.py`, already had
  it) and adding cleanup-on-failure to 3 sites that previously orphaned the temp file on error
  (`lasuite.py::_save_mapping`, `budget.py::save_budget`, `keys.py::save_inventory`) — both are
  additive robustness, not a behavior change on the success path.
- `fs_local.py::_tmp_sibling` and its `O_EXCL`+pre-unlink dance STAY — `repoint_symlink_atomic`
  (a different primitive: atomic symlink repoint, not content write) still uses it and is out of
  scope. Only `write_text_atomic`'s body changes.
- `marshal/tests/unit/test_fs_local.py::test_write_text_atomic_survives_a_stale_temp_file` tests
  `_tmp_sibling`-specific naming behavior that no longer applies to `write_text_atomic` once it
  delegates to `mkstemp`-based `atomic_write_text` (a stale file at `_tmp_sibling`'s old name can
  no longer collide with anything) — delete it; the other two `write_text_atomic` tests in that
  file are unaffected and must still pass.
- `pyforge-core` becomes a mandatory `[project].dependencies` / `[package.run-dependencies]` entry
  for exactly the 6 stations gaining a call site (atlas, herald, marshal, scribe, steward,
  warden), plus a `pyforge-core = { path = "src/shared/packages/pyforge-core" }` entry in each of
  their root `pixi.toml` `[feature.pyforge-<station>.dependencies]` blocks (mirrors the existing
  `pyforge-doctor`→`pyforge-warden` path-dependency pattern, the only precedent in this workspace
  for one member depending on another). Verify the wiring on ONE station (scribe — smallest, one
  call site) with a real `pixi install`/test pass before repeating it on the other 5; this exact
  member-to-member path-dependency shape has no working precedent in this repo yet.
- `pixi.toml` changes → regenerate `environment.yaml` (repo-wide ungated rule).
- CAP-7: add `pyforge-core/tests/meta/test_atomic_write_sole_ownership.py`, scanning every sibling
  station's SOURCE tree (not just pyforge-core's own) for a function containing both a temp-file
  write-open and an `os.replace` call — fails the build on a second implementation anywhere under
  `src/shared/packages/`. Must NOT fire on `repoint_symlink_atomic` (creates a symlink via
  `os.symlink`, never opens a file for writing) — prove both the positive and this negative case
  with synthetic fixtures, mirroring `test_leaf_constraint.py`'s non-vacuous-proof convention.

**Block If:** none identified — the primitive's shape, the retirement mandate, and the
sole-ownership pattern are fully specified by AD-67/FR-158/CAP-2/CAP-7 and this session's own
call-site census.

**Never:**
- No change to doctor or mason (no atomic-write copy in either).
- No new primitive from Stories 14.3/14.4 (verdict lattice, envelope, exception root, subprocess
  guard) — out of scope.
- No new exception type introduced in `pyforge.core` — every station keeps translating raw
  failures into its own error type (or raw) exactly as before.
- No change to `ports/fs.py`/`ports/record.py` Protocol signatures — only `fs_local.py`'s
  concrete body changes.
- No deprecation window — each of the 18 real copies is retired in this story, not deprecated
  alongside a new call.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Text happy path | `atomic_write_text(path, "x")`, parent exists | `path` contains `"x"`, no temp file left | No error expected |
| Bytes happy path | `atomic_write_bytes(path, b"x", mode=0o644)` | `path` contains `b"x"` with mode `0o644` | No error expected |
| Callback happy path | `atomic_write(path, lambda p: df.to_parquet(p))` | `path` is the parquet file; unopened `tmp` passed to callback | No error expected |
| Missing parent dir | `path.parent` does not exist | Created via `mkdir(parents=True, exist_ok=True)` before the temp file | No error expected |
| `write_fn` raises mid-write | Callback raises `ValueError` | Temp file removed (best-effort), original exception re-raised unchanged | Caller's own except clause still catches it |
| `os.replace` fails (e.g. cross-device) | Destination on a different filesystem | Temp file removed, `OSError` re-raised unchanged | Caller wraps as before |
| Sole-ownership guard vs. symlink repoint | `fs_local.py::repoint_symlink_atomic`'s real body fed to the detector | NOT flagged (no write-open call, only `os.symlink`) | Guard would be over-broad otherwise |
| Sole-ownership guard vs. a synthetic second copy | Synthetic source with `tempfile.mkstemp` + `os.replace` in one function | Flagged as a violation | Proves the guard is alive, not vacuous |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/atomic_write.py` -- NEW: `atomic_write`,
  `atomic_write_bytes`, `atomic_write_text`. `mode=None` computes a umask-respecting default
  internally (see Design Notes) rather than leaving `mkstemp`'s private `0o600` uncompensated,
  guarded by a module-level `threading.Lock()` (review pass 2 — the probe-and-restore pair is
  not safe unguarded once nearly every call site shares it); the temp-file `os.close(handle)`
  sits inside the same cleanup `try/except` as the rest of the function, not before it. The
  module docstring's copy count must read **20** (3 within warden's one file), not 18 — 18 is the
  FILE count, matching this spec's own Intent language, and must not be conflated with the copy
  count in the primitive's own docstring.
- `src/shared/packages/pyforge-core/tests/unit/test_atomic_write.py` -- NEW: primitive's own
  behavior (happy paths, failure cleanup, explicit `mode`, the umask-respecting DEFAULT when
  `mode` is omitted, parent-dir creation, no-temp-file-left-behind, and — review pass 2 — that two
  threads calling with `mode=None` concurrently never corrupt the process umask).
- `src/shared/packages/pyforge-core/tests/meta/test_atomic_write_sole_ownership.py` -- NEW: CAP-7
  fleet-wide guard (see Boundaries). Detection must cover both `os.replace(...)` AND a bare-name
  call bound via `from os import replace [as x]`, AND any `<name>.replace(...)` call whose
  receiver is a temp-path-shaped local (not only `os`-bound names) — a future `tmp_path.replace(
  path)` is functionally identical to `os.replace` and must not evade the guard. Symmetrically
  (review pass 2), the WRITE-OPEN side of the detector must cover bare-name-bound calls too —
  `from tempfile import mkstemp; mkstemp(...)` and `from os import fdopen`/`open` used as bare
  names — the same evasion class already closed on the `os.replace` side.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/{admission.py,factory/lasuite.py,datasets/basilisk.py,datasets/migration_status.py,datasets/refresh.py}`
  -- retire each `_write_holder`/`_save_mapping`/`_atomic_write` body; delegate to
  `pyforge.core.atomic_write*`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/{claims.py,deck_pipeline.py,notices.py,progress.py,registry.py,state.py}`
  -- same; `registry.py` passes `mode=original_mode & 0o7777`; each keeps its own
  `HeraldError`-wrapping try/except and (except `registry.py`) its `locking.locked` call.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/fs_local.py` --
  `write_text_atomic` delegates to `pyforge.core.atomic_write_text`; `_tmp_sibling` and
  `repoint_symlink_atomic` unchanged. Review pass 2: `_tmp_sibling`'s and
  `write_redacted_atomic`'s own docstrings still narrate `write_text_atomic`'s OLD
  `O_EXCL`-open/pre-unlink/stale-file behavior — update both to reflect that `write_text_atomic`
  no longer calls `_tmp_sibling` at all (only `repoint_symlink_atomic` still does).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` --
  `write_policy_toml` delegates to `pyforge.core.atomic_write_bytes` (pre-encoded UTF-8 bytes,
  same as today); keeps its `HarnessPolicyWriteError` wrap and `target_path` return.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py` -- `materialize` keeps
  its AD-35 content-addressed idempotent-skip check; only the final write call delegates to
  `pyforge.core.atomic_write_bytes` with **no `mode=`** (relies on the primitive's own
  umask-respecting default -- do not reintroduce a standalone `os.umask` probe here).
- `pixi.toml` (root) -- also update the `pyforge-core` feature block's comment, which currently
  says "No station depends on it yet -- that wiring belongs to the extraction stories
  (14.2-14.4)" -- stale once this story's 6 dependency entries land.
- `src/shared/packages/pyforge-marshal/tests/unit/test_fs_local.py` -- delete
  `test_write_text_atomic_survives_a_stale_temp_file` (tests a scenario that can no longer occur;
  see Boundaries).
- `src/shared/packages/pyforge-marshal/tests/meta/test_manifest_sync.py` -- its pixi/pyproject
  dependency-sync comparison needs a dict-valued (path) `[package.run-dependencies]` entry
  normalized to the empty-string spec `pyproject.toml`'s bare `"pyforge-core"` already parses to.
  Review pass 2: gate this normalization on the dict actually having a `path` key, not on it
  merely being a dict — a future dict-shaped dependency that also carries a real `version=` key
  must not be silently exempted from the sync check.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` -- `FileGraphStore.commit`
  delegates to `pyforge.core.atomic_write_text`; its own `_locked` context manager unchanged.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/{budget.py,keys.py}` --
  `save_budget`/`save_inventory` delegate via the callback form (`yaml.safe_dump` into the
  unopened tmp path); both gain failure-cleanup they previously lacked.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/feeds.py` -- all three
  `write_{kev,endoflife,epss}_cache` delegate to `pyforge.core.atomic_write_text`.
- `src/shared/packages/{pyforge-atlas,pyforge-herald,pyforge-marshal,pyforge-scribe,pyforge-steward,pyforge-warden}/pixi.toml`
  -- add `pyforge-core = { path = "../pyforge-core" }` to each `[package.run-dependencies]`.
- same 6 packages' `pyproject.toml` -- add `"pyforge-core"` to `[project].dependencies`.
- `pixi.toml` (root) -- add `pyforge-core = { path = "src/shared/packages/pyforge-core" }` to each
  of the 6 stations' `[feature.pyforge-<station>.dependencies]`.
- `environment.yaml` -- regenerate (`pixi project export conda-environment -e build`).

## Tasks & Acceptance

**Execution:**
- [x] `pyforge-core/src/pyforge/core/atomic_write.py` + `tests/unit/test_atomic_write.py` --
  implement and unit-test the primitive in isolation, INCLUDING the umask-respecting default
  when `mode=None` guarded by a `threading.Lock()` (Design Notes), the
  `os.close(handle)`-inside-cleanup fix, and an accurate "20 copies" docstring count -- establishes
  the one CORRECT implementation before anything is pointed at it
- [x] `pyforge-core/tests/meta/test_atomic_write_sole_ownership.py` -- CAP-7 fleet-wide guard,
  proven both non-vacuous and non-firing on `repoint_symlink_atomic`, with detection extended to
  `from os import replace`/`<name>.replace(...)` on the replace side AND `from tempfile import
  mkstemp`/`from os import fdopen`/`open` bare-name calls on the write-open side (see Code Map)
  -- makes "no second copy" structural before the retirements below start landing
- [x] Wire + retire scribe's one copy (`graph_store.py` + its 3-manifest pixi wiring) end to end,
  `pixi install -e pyforge-scribe` + `pyforge-scribe-test` green -- proves the member-to-member
  path-dependency shape actually resolves before repeating it 5 more times
- [x] Wire + retire steward's 2 copies (`budget.py`, `keys.py`) + its pixi wiring -- no explicit
  `mode=` needed at either site (relies on the primitive's umask-respecting default)
- [x] Wire + retire warden's 1 file / 3 copies (`feeds.py`) + its pixi wiring
- [x] Wire + retire herald's 6 copies + its pixi wiring -- `registry.py` keeps its explicit
  `mode=original_mode & 0o7777` override; the other 5 need none
- [x] Wire + retire atlas's 5 copies + its pixi wiring -- no explicit `mode=` needed at any site
- [x] Wire + retire marshal's 3 real copies (`fs_local.py`, `harness_bmadloop.py`, `config.py`) +
  delete the now-inapplicable `test_fs_local.py` case + fix `fs_local.py`'s 2 stale docstrings
  (`_tmp_sibling`, `write_redacted_atomic`) + its pixi wiring -- none pass an explicit `mode=`;
  `materialize` must NOT reintroduce its own standalone umask probe
- [x] `test_manifest_sync.py` -- gate the dict-spec normalization on the dict actually having a
  `path` key, not on it merely being a dict
- [x] `pixi.toml` -- add all 6 `[feature.pyforge-<station>.dependencies]` entries (if not already
  folded into the per-station tasks above), and update the `pyforge-core` feature block's stale
  "no station depends on it yet" comment
- [x] `environment.yaml` -- regenerate and commit

**Acceptance Criteria:**
- Given the 18 real copies, when this story lands, then each delegates to
  `pyforge.core.atomic_write*` and `grep -rn "os\.replace" src/shared/packages --include="*.py"`
  outside `pyforge-core` and outside `fs_local.py::repoint_symlink_atomic` returns nothing.
- Given each of the 6 affected stations' own existing test suites, when they run after the
  refactor, then all pass unchanged (minus the one deleted `test_fs_local.py` case) — durability
  semantics preserved per call site.
- Given `herald/registry.py::register`, when it rewrites an existing tracked README, then the
  replaced file's permission bits match the original's (the `mode` parameter exercised).
- Given any call site that passes no explicit `mode=` (all real copies minus `registry.py`), when
  it writes a file under a non-default umask, then the resulting file's permission bits are
  umask-respecting (`0o666 & ~umask`) — never `mkstemp`'s private `0o600`, regardless of whether
  that site historically got `0o600` (incidentally, via raw `mkstemp` with no chmod) or a wider
  mode (via `Path.write_text`/`os.open(path, ..., 0o666)`) before this story.
- Given two threads calling `atomic_write` (or any wrapper) concurrently with no explicit `mode=`,
  when both race, then the process umask is never left in a corrupted state afterward, and both
  writes still land with the correct umask-respecting mode.
- Given `marshal/cli/config.py::materialize`, when called twice with identical content, then the
  second call is still a true no-op (AD-35 unchanged) — only the actual-write path changed.
- Given the sole-ownership meta-test, when it scans every sibling station, then it fires on a
  synthetic second copy (both a bare `os.replace`/`tempfile.mkstemp` pair AND a
  bare-name-imported equivalent) and does not fire on `repoint_symlink_atomic`'s real body.
- Given the 6 stations' `pixi.toml`/`pyproject.toml`, when inspected, then each declares
  `pyforge-core` as a real run-dependency; doctor's and mason's manifests are untouched.
- Given root `pixi.toml` changed, when `pixi project export conda-environment -e build` runs,
  then the regenerated `environment.yaml` is committed alongside it.

## Spec Change Log

- **Pilot pixi wiring VERIFIED as specified (no fallback needed).** The spec flagged the
  member-to-member `[package.run-dependencies]` path-dependency shape (station's OWN
  `pixi.toml` depending on `pyforge-core` via `{ path = "../pyforge-core" }`) as unproven in
  this workspace. Wired it on scribe (its own `pixi.toml` `[package.run-dependencies]` +
  `pyproject.toml` `[project].dependencies` + root `pixi.toml`
  `[feature.pyforge-scribe.dependencies]`), then ran `pixi install -e pyforge-scribe`: clean
  resolve, `pixi.lock` gained `pyforge-core` as a real `conda_source` dependency under the
  `pyforge-scribe` environment, and the BUILT conda package's own
  `conda-meta/pyforge-scribe-*.json` `depends` list includes literal `"pyforge-core"` --
  confirmed baked into the package metadata, not just the pixi env. `pixi run --frozen -e
  pyforge-scribe pyforge-scribe-test` -- 89 passed. No deviation from the spec's proposed
  shape was needed; repeated verbatim on the other 5 stations.
- **`marshal/cli/config.py::materialize` needed an explicit `mode=` override to keep an
  existing passing test green.** `materialize` historically created its temp file via
  `os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)` -- letting the KERNEL
  apply the process umask, deliberately avoiding an `os.umask(0)`/restore probe (a
  process-global toggle that would briefly zero the umask for every other thread). The shared
  primitive is `tempfile.mkstemp`-based, which always creates the temp file at a private
  `0o600` regardless of umask -- switching `materialize` to a bare
  `atomic_write_bytes(target_path, expected_bytes)` with no `mode=` would silently change the
  materialized artifact's permission bits from "umask-respecting" to a fixed `0o600`, breaking
  `tests/unit/test_cli.py::test_materialized_artifact_gets_umask_respecting_permissions`
  (asserts `written.stat().st_mode & 0o777 == 0o666 & ~current_umask`) -- a test this story's
  Design Notes did not name and did not intend to break ("without changing any test-visible
  outcome on the success path" only accounted for the one named `test_fs_local.py` deletion).
  Deviated: `materialize` computes the umask-respecting mode itself
  (`os.umask(0)` immediately followed by `os.umask(current_umask)` to restore it, then
  `0o666 & ~current_umask`) and passes it as `atomic_write_bytes`'s `mode=` -- reintroducing
  the exact probe the prior implementation deliberately avoided, because it is the only way to
  keep this passing test green while still routing the final write call through the shared
  mkstemp-based primitive as the Code Map requires. The probe now runs once per `materialize`
  call (not per write site fleet-wide) and is scoped to this one caller.
- **warden's own dogfood self-scan needed `.warden-baseline.yaml` entries for the new
  `pyforge-core` dependency.** `pyforge-warden` scans ITS OWN manifest as part of
  `tests/conformance/test_dogfood.py` (`test_dogfood_scan_of_the_real_package_exits_zero`).
  Adding `pyforge-core` as a real dependency surfaced two NEW finding classes against it that
  are not covered by the existing baseline (which lists every OTHER dependency's findings
  individually, by id): (1) the same `currency:unknown` / `indeterminate:no-version` /
  `indeterminate:offline-db-unavailable` trio every other unpinned dependency already carries
  (expected -- warden's own manifest ships no lockfile); and (2) two genuinely new deptry
  false positives, `hygiene:DEP002:pyforge-core` ("defined as a dependency but not used") and
  `hygiene:DEP003:pyforge` ("imported but it is a transitive dependency") -- deptry's
  package-name-to-import-name mapping does not recognize `from pyforge.core... import ...` as
  satisfying a declared `pyforge-core` dependency, because `pyforge-core` ships under the
  shared PEP 420 `pyforge` namespace rather than a `pyforge_core`-prefixed one. Both are
  WARN-tier by `hygiene.py`'s own `DEFAULT_HYGIENE_POLICY` (exactly the "deptry
  false-positive-prone" class DEP002-005 are demoted for) and did not themselves drive the
  exit code -- the gate failed on the (correctly expected) `indeterminate:no-version:
  pyforge-core` finding instead, since that id was not yet in the baseline. Regenerated via
  the file's own documented procedure (`python scripts/dogfood_scan.py --emit-baseline` from
  `src/shared/packages/pyforge-warden/`), added 5 new entries mirroring the existing
  per-dependency pattern (same `expires_at` as every other entry, to preserve the file's
  "every entry expires simultaneously" invariant). `pyforge-warden-test` now passes 1936/1936
  (was 1935/1936 red on this one dogfood assertion before the baseline update). This is
  warden-specific (its own conformance suite dogfoods itself); no other of the 5 remaining
  stations runs an equivalent self-scan gate, so this class of fix is not expected to recur
  for atlas/herald/marshal.
- **One herald test needed its `monkeypatch.setattr` target adjusted (not deleted) --
  `test_registry.py::test_register_wraps_a_failed_replace_and_leaks_no_temp_file`.** It
  patched `"pyforge.herald.registry.os.replace"` to inject a failure; `registry.py` no longer
  imports `os` at all post-delegation (the `os.replace` call now lives inside
  `pyforge.core.atomic_write`), so the dotted monkeypatch path no longer resolves
  (`ImportError`, not a meaningful assertion failure). Retargeted the patch to
  `"pyforge.core.atomic_write.os.replace"` -- the test's OBSERVABLE assertions (a
  `HeraldError` is raised, the original README is byte-identical, no temp file is left behind)
  are unchanged; only the internal seam the mock attaches to moved, which is an unavoidable,
  mechanical consequence of the extraction. This is a narrower category than the spec's one
  named test DELETION (`test_fs_local.py`'s stale-temp-file case, whose scenario can no longer
  occur) -- here the scenario still occurs and is still proven, just via a relocated seam.
  Grep confirmed no other of the 6 stations' test suites monkeypatches an internal
  `<module>.os`/`<module>.tempfile` attribute this way, so this class of fix should not recur
  for atlas/marshal (not yet wired at the time of this entry).
- **marshal's `tests/meta/test_manifest_sync.py` needed a path-dependency-aware comparison.**
  `test_package_run_dependencies_match_project_dependencies` asserts `pixi.toml`'s
  `[package.run-dependencies]` and `pyproject.toml`'s `[project].dependencies` name the same
  deps with the same version-spec strings, comparing every pixi value via `spec.replace(" ",
  "")` -- which assumes every value is a plain TOML string. `pyforge-core = { path =
  "../pyforge-core" }` is a TABLE, not a string, so the bare `.replace()` raised
  `AttributeError: 'dict' object has no attribute 'replace'` (this is the ONLY station with
  this particular sync meta-test; not present in the other 5). Fixed by normalizing a
  dict-valued (path) entry to the empty-string spec `pyproject.toml`'s bare, unversioned
  `"pyforge-core"` name already parses to (a workspace member has no PyPI version) -- both
  sides now compare as `{"pyforge-core": ""}`. `pyforge-marshal-test` now passes 3537/3537.

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 4: (high 1, medium 1, low 2)
- patch: 0
- defer: 1: (low 1) — moot this pass per cascading rule (bad_spec present); not minted now, re-surface after re-derivation if still applicable: `test_manifest_sync.py`'s pixi/pyproject dependency-sync guard exists only for `pyforge-marshal`, not the other 5 stations now also carrying a `pyforge-core` path dependency (pre-existing absence, not caused by this story).
- reject: 4: (low 4) — moot/dropped: scope-creep incidental `ruff --fix` cleanups in already-touched files (behavior-preserving, no defect); herald's streaming-`json.dump`→build-full-string-then-write memory-profile change (theoretical, no evidence of harm at this codebase's actual payload sizes); the new primitive's test suite not separately re-proving `mkstemp`'s own stale-collision-immunity guarantee (testing stdlib, not our logic); the new `.warden-baseline.yaml` entries being "unverified" (false alarm — the Spec Change Log's own entry documents they were regenerated by actually running `scripts/dogfood_scan.py --emit-baseline`, not hand-typed).
- addressed_findings:
  - `[high]` `[bad_spec]` Blind Hunter + Edge Case Hunter, independently, no shared context:
    switching every call site to the shared `atomic_write` primitive silently narrows file
    permissions from "umask-respecting" (what `Path.write_text`/`Path.open("w")`/
    `os.open(path, ..., 0o666)` produced at 9 of the 18 real pre-refactor call sites) to
    `tempfile.mkstemp`'s fixed private `0o600`, because `mode` defaults to `None` and nothing
    compensates except at the 2 sites (`registry.py`, `config.py::materialize`) that got
    call-site-specific fixes during implementation. Confirmed real and high-consequence for at
    least `steward/keys.py` (Edge Case Hunter: the file's own docstring documents a concurrent
    reader as the reason atomic replace matters at all) and `marshal/harness_bmadloop.py`
    (inconsistent with its sibling `materialize()`'s deliberately-preserved permissions in the
    same diff). This directly contradicts this spec's own Boundaries/Design Notes claim that the
    `mkstemp` consolidation "changes no happy-path observable behavior." Root cause is the
    primitive's OWN default design, not any individual call site — amended below so `mode=None`
    means "compute a umask-respecting default internally," which fixes all 9 sites at once and
    also lets `materialize()` drop the racy standalone `os.umask(0)`/restore probe it had grown
    to reproduce this manually (medium-severity finding, subsumed here: that probe briefly
    zeroed the process-wide umask for every thread, exactly the hazard `materialize()`'s
    ORIGINAL pre-story implementation was written to avoid).
  - `[medium]` `[bad_spec]` Edge Case Hunter, confirmed by direct inspection: the sole-ownership
    meta-test's AST detector only recognizes `os.replace(...)` bound via `import os`, and only
    `tempfile.mkstemp`/`os.open`/`.write_text`/`.write_bytes`/`.open("w"...)` as write-open
    signals — a future second implementation using `from os import replace as x; x(tmp, path)`
    or `tmp_path.replace(path)` (both real, common Python idioms, functionally identical to
    `os.replace`) evades CAP-7's guarantee entirely. Amended below to extend detection.
  - `[low]` `[bad_spec]` Blind Hunter: `atomic_write()`'s `os.close(handle)` call sits outside
    its own cleanup `try/except` — if `close` itself raises, the just-created temp file is never
    unlinked. Narrow (a fresh fd's `close` essentially never fails) but real and cheap to fix in
    the same file already being re-derived.
  - `[low]` `[bad_spec]` Blind Hunter: root `pixi.toml`'s comment block for the `pyforge-core`
    feature still reads "No station depends on it yet -- that wiring belongs to the extraction
    stories (14.2-14.4)," now stale since this very story wires six stations to it. Folded into
    this story's own Tasks so it lands with the re-derivation rather than needing a second pass.

**KEEP instructions for re-derivation (validated, must survive unchanged):**
- The callback-first primitive shape `atomic_write(path, write_fn, *, mode=None)` with
  `atomic_write_bytes`/`atomic_write_text` as thin wrappers — correct, keep exactly.
- `tempfile.mkstemp`-based collision-free temp-file NAMING (the bug is only the PERMISSION
  default applied to that name, not the naming/creation mechanism itself) — keep.
- The per-station call-site mapping and refactor approach: every call site keeps its own
  exception wrapping, advisory locking, pre-write sorting, and pre-write short-circuits
  (`materialize`'s AD-35 idempotent-skip) exactly as before — validated by every station's own
  test suite passing unchanged (minus the one named deletion) — keep.
- The 3-manifest pixi wiring pattern, empirically verified via a real `pixi install` on the
  scribe pilot and confirmed baked into the built conda package's own `depends` metadata: member
  `pixi.toml` `[package.run-dependencies]` gets `pyforge-core = { path = "../pyforge-core" }`;
  member `pyproject.toml` `[project].dependencies` gets `"pyforge-core"`; root `pixi.toml`
  `[feature.pyforge-<station>.dependencies]` gets `pyforge-core = { path =
  "src/shared/packages/pyforge-core" }` — keep exactly, no fallback needed.
- The sole-ownership meta-test's overall structure: derived (not hardcoded) sibling-station
  roster, function-scoped dual-signal (write-open AND `os.replace`) detection, non-vacuous
  proofs in both directions, and a real-file negative check against
  `fs_local.py::repoint_symlink_atomic` — keep the structure, only widen the two signal
  detectors per the finding above.
- The `test_fs_local.py::test_write_text_atomic_survives_a_stale_temp_file` deletion — keep;
  correct and necessary (the scenario it tested cannot occur under `mkstemp`).
- The `herald/test_registry.py` monkeypatch retarget to `pyforge.core.atomic_write.os.replace`
  — keep; a mechanical, correct consequence of the extraction.
- The `test_manifest_sync.py` path-dependency-aware comparison fix (normalizing a dict-valued
  path dependency to an empty-string spec on both sides) for `pyforge-marshal` — keep.
- The `.warden-baseline.yaml` regeneration via the file's own documented
  `scripts/dogfood_scan.py --emit-baseline` procedure — keep; verified against the real tool,
  not guessed.
- The verification discipline (each station's own full test suite run after its wiring lands,
  the scribe pilot proven before propagating) — keep as the approach.

**Known-bad state avoided:** landing a primitive whose silent permission-narrowing default
would have shipped to 9 files including a documented concurrent-reader artifact
(`keys-inventory.yaml`) and a policy artifact inconsistent with its own sibling function's
explicitly-preserved permissions in the same diff — exactly the "verified per call site rather
than assumed uniform" failure AD-67/this spec's own Design Notes were written to prevent.

**Reference:** the full prior (95%-correct) implementation is preserved in
`git stash list` as `story-14-2-pre-bad-spec-loopback-reference` (not dropped) for the
re-derivation agent to consult via `git stash show -p` rather than re-deriving from zero.

### 2026-08-12 — Review pass 2
- intent_gap: 0
- bad_spec: 5: (high 1, medium 1, low 3)
- patch: 0
- defer: 1: (low 1) — moot this pass per cascading rule; not minted now: warden's
  `.warden-baseline.yaml` expiry/grandfathering mechanism isn't tied to a dependency's CURRENT
  footprint (pre-existing characteristic of the whole baseline system, not something this story
  introduced — every prior entry in that file has the same property).
- reject: 3: (low 3) — dropped: (1) permission WIDENING for the ~9-11 sites that previously used
  raw `mkstemp` with no chmod at all (herald's non-`registry.py` copies, scribe, warden) now get
  the same umask-respecting default as everywhere else instead of an incidental private `0o600`
  — none of those files hold sensitive content (JSON claims/progress/notices metadata, a shared
  team-memory graph, public CISA-KEV/endoflife/EPSS caches), no test or documented requirement
  asserts privacy for any of them, and a single consistent default across all ~20 sites is an
  intended, not accidental, outcome of this consolidation; (2) an added `os.chmod` syscall per
  write — negligible, none of these are hot paths; (3) `json.dumps`-then-write replacing
  streaming `json.dump` at ~8 sites — re-raised independently in this pass with no new evidence
  of actual harm at these codebases' real (small, bounded) payload sizes; same reasoning as
  pass 1.
- addressed_findings:
  - `[high]` `[bad_spec]` Blind Hunter, confirmed by a forced reproduction (not hypothetical):
    the centralized `_umask_respecting_default_mode()` probe-and-restore (`os.umask(0)` then
    `os.umask(current)`) has no synchronization, and a legal two-thread interleaving
    (`T1:umask(0), T2:umask(0), T1:restore(old), T2:restore(0)`) leaves the PROCESS UMASK
    PERMANENTLY corrupted at `0`, not merely transiently wrong for one write. This is now
    exercised by every one of the ~17 call sites that pass no explicit `mode=` (the prior pass's
    fix moved this probe from 0-1 call sites into the one shared primitive, unintentionally
    widening its blast radius). Amended below: guard the probe-and-restore pair with a
    module-level `threading.Lock()` — confirmed via `grep` that no other code anywhere in the
    fleet calls `os.umask()`, so this lock is sufficient to close the race for every real caller.
  - `[medium]` `[bad_spec]` Blind Hunter: the CAP-7 sole-ownership guard's write-open detector
    (unlike its already-fixed `os.replace` detector) has no handling for bare-name-bound
    write-open calls (`from tempfile import mkstemp; mkstemp(...)`, `from os import fdopen`),
    an evasion class structurally identical to the one already closed on the replace side.
    Amended below to extend detection symmetrically.
  - `[low]` `[bad_spec]` Blind Hunter: `atomic_write.py`'s own module docstring says "Eighteen
    real copies... warden 1," undercounting warden's 3 separate `write_*_cache` functions as
    one and contradicting the sole-ownership test's own correct "20 pre-refactor copies" count
    in the same diff. Amended below: the docstring must count copies (20, 3 within warden's one
    file), not files (18), matching this spec's own Intent language which already draws that
    distinction correctly.
  - `[low]` `[bad_spec]` Blind Hunter: `fs_local.py`'s `_tmp_sibling` and `write_redacted_atomic`
    docstrings still narrate `write_text_atomic`'s OLD `O_EXCL`-open/pre-unlink/stale-file
    behavior, which no longer applies now that `write_text_atomic` delegates to the shared
    primitive. Amended below: update both docstrings as part of this story's own `fs_local.py`
    edit (a file already being touched).
  - `[low]` `[bad_spec]` Edge Case Hunter: `test_manifest_sync.py`'s new dict-spec normalization
    (`"" if isinstance(spec, dict) else ...`) treats ANY dict-shaped pixi dependency as
    equivalent to "no version," not only a path dependency specifically — a future dict-shaped
    dependency that also carries a real `version =` key would silently stop being checked.
    Amended below: normalize only when the dict actually has a `path` key.

**KEEP instructions for re-derivation, pass 2 (everything from pass 1's KEEP list still holds,
PLUS):**
- The core design decision from pass 1 — `mode=None` computes a umask-respecting default
  internally rather than leaving `mkstemp`'s private `0o600` uncompensated — is CORRECT and
  stays; only the probe itself needs a lock, not a different design.
- `os.chmod(tmp_path, effective_mode)` running unconditionally before `os.replace`, and
  `os.close(handle)` living inside the function's own cleanup `try/except` — both keep exactly.
- `registry.py`'s explicit `mode=original_mode & 0o7777` override, and `materialize`'s reliance
  on the primitive's default with no `mode=` of its own — both keep exactly (measured correct
  in pass 2's independent verification: `registry.py` still wins over the default under a
  non-default umask).
- All pass-1 KEEP items (primitive shape, mkstemp naming, per-station call-site mapping, the
  3-manifest pixi wiring — re-verified working in pass 2 — the sole-ownership guard's overall
  structure and its already-correct `os.replace`-side bare-name detection, the `test_fs_local.py`
  deletion, the `test_registry.py` monkeypatch retarget, the warden baseline regeneration
  procedure, the root `pixi.toml` stale-comment fix) — unaffected by this pass's findings, keep.

**Known-bad state avoided:** landing a shared primitive whose own internal umask probe — now
exercised on nearly every write across the fleet instead of the 0-1 call sites that touched
`os.umask()` before this story — can permanently corrupt the process-wide umask under ordinary
multi-threaded use, silently producing world-writable or unexpectedly-restrictive files fleet-wide
for the remainder of a process's lifetime after the first race.

**Reference:** the pass-2 implementation (before this loopback) is preserved in `git stash list`
as `story-14-2-pre-bad-spec-loopback-reference-pass2` for the re-derivation agent to consult.

### 2026-08-12 — Review pass 3

- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 0, low 3)
- defer: 0
- reject: 10: (low 10) — dropped: (1+2) the sole-ownership guard's `<name>.replace(...)`/write-open
  heuristics can theoretically false-positive on unrelated future code (both hunters independently
  named this; it is an inherent, already-conceded tradeoff of any AST heuristic — the module's own
  docstring already calls the receiver check "deliberately narrow" — and there is no live collision
  today); (3) `atomic_write`'s callback receiving an already-`mkstemp`-created path is an
  "unannounced" precondition change — false, it is stated explicitly in both the primitive's own
  docstring and the spec's I/O matrix ("unopened `tmp` passed to callback"); (4) `cli/config.py`'s
  `tomllib` import-grouping doesn't match either of the package's other two styles — true, but there
  is no single existing convention to match (three different styles already coexist), so this is
  cosmetic noise, not a defect; (5) the umask-probe's safety argument resting on a point-in-time
  `grep` rather than an enforced invariant, and (6, Edge Case Hunter's twin framing) the probe
  window briefly affecting unrelated file-creation by other threads, both restate the SAME residual
  risk pass 2's Design Notes already named explicitly and accepted as irreducible ("cannot protect
  against a hypothetical third-party library calling `os.umask()` outside this lock... regardless of
  implementation") — no new, actionable mitigation was identified beyond what pass 2 already
  KEEP-locked as correct; (7) no dedicated test for `os.chmod` itself failing mid-write — the
  cleanup-and-reraise-unchanged guarantee it would exercise is the identical code path already
  proven by the existing `write_fn`-raises and `os.replace`-fails tests, so a chmod-specific test is
  redundant coverage of stdlib failure modes, not new logic; (8, Edge Case Hunter) `atomic_write` no
  longer raises a fast, clean `ValueError` for a nameless path (e.g. `Path("/")`) the way the old
  `_tmp_sibling`-based `write_text_atomic` did — verified this is a pre-existing gap, not a
  regression: the old `_tmp_sibling` `ValueError` was never caught by `write_text_atomic`'s own
  `except OSError`, so it already escaped raw before this story; no real call site in this codebase
  ever passes a nameless path; (9, Edge Case Hunter) `os.close(handle)` failing would leak the raw
  fd, since the `except` cleanup only unlinks the temp file — real in principle but no safe retry
  exists for a failed `close()` (POSIX leaves fd state undefined after), and this is definitionally
  the last, near-impossible-in-practice failure mode in the function; (10) the sole-ownership guard's
  non-vacuous negative proof relies on one hardcoded real file
  (`fs_local.py::repoint_symlink_atomic`) rather than scanning all 19 real migrated call sites — this
  is the exact structure the spec's own Boundaries/Code Map and pass-1/pass-2 KEEP lists mandate
  ("a real-file negative check against `fs_local.py::repoint_symlink_atomic`"), not a gap.
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter, confirmed by direct execution (`pytest
    tests/packaging/test_dependency_completeness.py -q` → 6 of 9 `test_shared_dependency_pins_agree`
    cases red): the repo-wide manifest-parity gate's `_run_dependencies()` stringifies a pixi
    run-dependency spec with a bare `str(spec)`, so the new `pyforge-core = { path = "..." }` TABLE
    entry (all 6 touched stations) stringifies to the literal `"{'path': '../pyforge-core'}"` instead
    of the empty pin `pyproject.toml`'s bare, unversioned `"pyforge-core"` normalizes to — this is
    the SAME class of bug the in-package `pyforge-marshal/tests/meta/test_manifest_sync.py` was
    already fixed for during implementation, but the repo-level gate in `tests/packaging/` was never
    touched. Fixed: added `_run_dep_spec_str()`, normalizing a path-keyed dict spec to `""` (mirrors
    the in-package fix) while leaving any OTHER dict-shaped spec as its `str()` form so it still
    compares (and fails loudly on real drift) rather than crashing or being silently exempted.
    Re-ran: 67/67 passed.
  - `[low]` `[patch]` Edge Case Hunter, confirmed by inspection: `test_manifest_sync.py`'s own
    pass-2 dict-spec fix (`"" if isinstance(spec, dict) and "path" in spec else ...`) falls through
    to a bare `spec.replace(" ", "")` for any OTHER dict-shaped value, which would raise
    `AttributeError: 'dict' object has no attribute 'replace'` instead of comparing and failing
    loudly as the adjacent docstring already promises. Fixed: guarded the fallback with
    `isinstance(spec, str)`, matching the same robustness fix applied to the repo-wide gate above.
    Re-ran `pyforge-marshal-test`: 3537/3537 passed.
  - `[low]` `[patch]` Blind Hunter, confirmed by counting: the module docstring's justification for
    the umask-probe lock says "roughly 17 call sites," undercounting by 2 — of the 20 migrated call
    sites, only `herald/registry.py` passes an explicit `mode=`, so 19 (not 17) share the lock.
    Fixed the comment to state 19 and name the one exception.
  - `[low]` `[patch]` Blind Hunter, confirmed by inspection: `cli/config.py::materialize` kept its
    own explicit `target_dir.mkdir(parents=True, exist_ok=True)` even though `atomic_write_bytes`
    now performs the identical `mkdir` internally on every call, and the early `target_path.exists()`
    no-op-return path never needed it (`Path.exists()` tolerates a missing parent). Removed the
    redundant call; re-ran `pyforge-marshal-test`: 3537/3537 passed (unchanged pass count, confirming
    no behavior change).

## Design Notes

**Why a callback (`write_fn(tmp_path)`) as the primitive's core shape, with bytes/text as thin
wrappers, rather than the reverse.** `refresh.py`'s existing `_atomic_write(target, write_fn)`
already serves both JSON text and `DataFrame.to_parquet` (binary, written by pandas itself, not by
this code) through one signature — pandas needs an unopened path, not a pre-built bytes blob. A
bytes-first primitive can't express that without a second parameter shape; a callback-first one
subsumes both text and bytes as one-line wrappers:
```python
def atomic_write_text(path, text, *, encoding="utf-8", mode=None):
    return atomic_write(path, lambda tmp: tmp.write_text(text, encoding=encoding), mode=mode)
```

**Why `mkstemp` replaces every hand-rolled naming scheme instead of preserving each one.** Three
different naming philosophies exist today (pid+thread-id with pre-unlink in `fs_local.py`;
pid+thread-id with no pre-unlink and an explicit umask rationale in `config.py::materialize`; a
fixed, non-unique `.tmp` suffix in `atlas`/`refresh.py`). `tempfile.mkstemp` is `O_EXCL`-backed,
stdlib-guaranteed collision-free even across pid recycling, and is already what 10 of the 20
copies use. Consolidating on it strictly closes the collision window `fs_local.py`'s own
docstring names as a known limitation of its scheme (confirmed against the one test —
`test_fs_local.py`'s stale-temp-file case — that probes the old naming scheme directly; it is
deleted because the scenario it guards against cannot occur under `mkstemp`, not because
coverage is dropped).

**Review-pass correction (superseding this Design Note's prior text — see Spec Change Log):
`mkstemp` alone does NOT preserve every call site's observable behavior; the PRIMITIVE's default
permission handling must too.** `tempfile.mkstemp` always creates its temp file at a fixed,
private `0o600` — unlike `Path.write_text`/`Path.open("w")`/`os.open(path, ..., 0o666)`, which 9
of the 18 real pre-refactor call sites used and which the kernel makes umask-respecting (typically
`0o644`/`0o664`) automatically. A first implementation attempt left `mode` defaulting to `None`
with no compensation, silently narrowing permissions at those 9 sites — caught by review, not by
any test (none of the 18 stations' existing suites assert permission bits except the one that
already got a bespoke fix). **The fix belongs in the primitive itself, not at each call site**:
when `mode` is `None`, `atomic_write` must compute a umask-respecting default internally (read the
umask via `os.umask(0)` immediately followed by `os.umask(current)` to restore it — a well-known,
brief, single-probe idiom with no safe getter-only alternative in POSIX — then `0o666 &
~current_umask`) and `os.chmod` the temp file to that value before the replace, exactly as if the
temp file had been created with `os.open(..., 0o666)` in the first place. This is a strict
superset of the original behavior at every site that cared about umask-respecting permissions:
the 9 `Path.write_text`-style sites get their mode back for free; `registry.py` keeps overriding
with its own explicit `mode=original_mode & 0o7777` (an exact match to a pre-existing tracked
file, unrelated to umask); and `config.py::materialize` — which had grown its OWN separate
`os.umask(0)`/restore probe to reproduce the old `os.open(..., 0o666)` behavior by hand — now
calls `atomic_write_bytes(target_path, expected_bytes)` with no `mode=` at all, relying on the
same centralized default. The sites that previously used raw `mkstemp` with no chmod at all
(herald's 5 non-`registry.py` copies, scribe, warden's 3) get the SAME umask-respecting default
instead of their previous incidental private `0o600` — a deliberate, accepted widening: none of
those files hold sensitive content (JSON metadata, a shared team-memory graph, public
CISA-KEV/endoflife/EPSS caches), and one consistent default across every site is the intended
outcome of consolidating three previously-inconsistent naming/permission philosophies into one.

**Review-pass-2 correction: the umask probe-and-restore pair must be lock-guarded — it is not
merely "brief," it is a real, reproducible race once centralized into a primitive nearly every
call site now shares.** Moving this probe from the 0-1 call sites that had it before this story
into the ONE shared primitive means it now runs on every `atomic_write` call that omits `mode=`
— roughly 17 call sites instead of the 1 (`materialize`) that used to touch `os.umask()` at all.
Two threads racing `os.umask(0)` / `os.umask(restore)` in an interleaved order can leave the
PROCESS UMASK PERMANENTLY corrupted (not just one write affected — every subsequent file creation
in the process, by any code, inherits the corrupted value), confirmed by review via a forced
interleaving reproduction. `atomic_write.py` must guard `_umask_respecting_default_mode`'s
probe-and-restore with a module-level `threading.Lock()`, serializing the two-syscall critical
section across threads within the process. This fully closes the race for this codebase (`grep
-rn "os\.umask" src/shared/packages` confirms no other module anywhere in the fleet calls
`os.umask()`) — it cannot protect against a hypothetical third-party library calling `os.umask()`
outside this lock, which POSIX offers no primitive to guard against regardless of implementation.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm each of the 6 stations' `pixi.toml`/`pyproject.toml` `pyforge-core` entries follow one
  consistent shape across all 6 (same key ordering/style as the existing per-station blocks).

## Auto Run Result

**Summary.** Re-derived the implementation from the pass-2-corrected spec (session start found
`status: in-review` but a clean working tree at `baseline_revision` — the prior session's
bad_spec-loopback revert had completed but the re-derivation via step-03 had not; resumed there).
Added `pyforge.core.atomic_write`/`atomic_write_bytes`/`atomic_write_text` (mkstemp-based,
umask-respecting default when `mode=None`, lock-guarded probe) plus its CAP-7 sole-ownership
meta-test to the `pyforge-core` leaf, and rewired all 20 real copies across the 6 affected stations
(atlas, herald, marshal, scribe, steward, warden) to delegate to it, retiring every hand-written
tmp-in-dir + `os.replace` implementation in the same story. Went through one further review pass
(pass 3) that found and patched a real, execution-confirmed regression in a repo-wide CI gate the
implementation had not touched.

**Files changed** (40 total; see `git diff --stat 2cd08f7e76ac8afd5589f26d0d14a90a601cef06`):
- `pyforge-core/src/pyforge/core/atomic_write.py` (new) — the one shared primitive.
- `pyforge-core/tests/unit/test_atomic_write.py` (new) — primitive unit tests, incl. the
  concurrent-umask-no-corruption test review pass 2 required.
- `pyforge-core/tests/meta/test_atomic_write_sole_ownership.py` (new) — CAP-7 fleet-wide guard
  with symmetric bare-name-import detection on both the write-open and `os.replace` sides.
- `pyforge-{atlas,herald,marshal,scribe,steward,warden}` — 20 call sites across
  `admission.py`/`lasuite.py`/`basilisk.py`/`migration_status.py`/`refresh.py` (atlas),
  `claims.py`/`deck_pipeline.py`/`notices.py`/`progress.py`/`registry.py`/`state.py` (herald),
  `fs_local.py`/`harness_bmadloop.py`/`cli/config.py` (marshal), `graph_store.py` (scribe),
  `budget.py`/`keys.py` (steward), `feeds.py` (warden, 3 copies in one file) — each now delegates
  to `pyforge.core.atomic_write*`, keeping its own exception wrapping / locking / pre-write
  short-circuit unchanged.
- Each of the 6 stations' `pixi.toml` + `pyproject.toml` — added `pyforge-core` as a real
  run-dependency (3-manifest pattern); root `pixi.toml` — 6 new
  `[feature.pyforge-<station>.dependencies]` entries + refreshed stale comment; `pixi.lock` —
  regenerated.
- `pyforge-marshal/tests/unit/test_fs_local.py` — deleted the now-inapplicable stale-temp-file
  case; `pyforge-marshal/tests/meta/test_manifest_sync.py` — path-dependency-aware pin comparison
  (dict-with-`path`-key normalizes to the empty spec pyproject's bare name parses to; any other
  dict-shaped spec compares via `str()` instead of crashing — review pass 3 fix).
- `pyforge-warden/.warden-baseline.yaml` — 5 new entries for `pyforge-core`'s expected
  currency/hygiene findings (regenerated via the file's own documented procedure).
- `tests/packaging/test_dependency_completeness.py` — review pass 3 fix: the repo-wide
  manifest-parity gate needed the same path-dependency normalization as the in-package
  `test_manifest_sync.py` (it stringified the new path-dependency TABLE literally, breaking
  `test_shared_dependency_pins_agree` for all 6 touched stations).

**Review findings breakdown (pass 3, this session):** 4 patched (1 high, 3 low), 10 rejected (all
low — inherent heuristic tradeoffs, already-documented-and-accepted residual risks from pass 2, or
findings that mischaracterized already-covered behavior), 0 deferred, 0 bad_spec, 0 intent_gap.
Full detail in the Review Triage Log above. Cumulative across all 3 passes: 2 bad_spec loopbacks
(9 findings fixed via spec amendment + re-derivation), 4 patches this pass, 2 defers logged as
moot/pre-existing, 17 total rejects.

**Verification performed** (all commands actually run this session, not just the two prior
loopback passes' recorded output):
- `pixi run --frozen -e pyforge-core pyforge-core-test` → 300 passed
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` → 89 passed
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` → 393 passed
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` → 1936 passed, 11 deselected
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` → 784 passed, 2 skipped
- `pixi run --frozen -e pyforge-atlas kedro-test` → 1063 passed, 15 skipped (4 failed + 1 error
  confirmed pre-existing/unrelated: unprovisioned DuckDB `httpfs` extension, an unbuilt WASM
  artifact, evolving `sprint-status.yaml` content — none touch story-relevant files)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 3537 passed, 9 deselected (re-run
  twice: once post-re-derivation, once post-pass-3-patches — identical pass count both times)
- `python3 -m pytest tests/packaging/test_dependency_completeness.py -q` → 67 passed (0 before the
  pass-3 patch; 6 of 9 `test_shared_dependency_pins_agree` cases were red)
- `pixi install -e <station>` for all 6 stations → clean resolves; built conda packages' own
  `depends` metadata confirmed to include `pyforge-core`
- `grep -rn "os\.replace(" src/shared/packages --include="*.py" | grep -v pyforge-core/ | grep -v
  fs_local.py` → empty (the two remaining textual hits are docstring prose, not code)
- `pixi project export conda-environment -e build > environment.yaml && git diff --stat
  environment.yaml` → no diff (already current)
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-core` → all checks passed;
  same command against the other touched files in this pass surfaced only pre-existing,
  unrelated `I001` import-sort debt (confirmed identical at `baseline_revision` via `git stash`),
  not introduced by this story
- Manual umask check under `umask 022` on `steward/keys.py::save_inventory`,
  `atlas/admission.py::_write_holder` → `0o644` (umask-respecting); `herald/registry.py`'s
  explicit override → `0o640` preserved, not widened
- Concurrent-umask-corruption test (32 threads, `mode=None`) → passes, umask reads back unchanged
  before/after

**Residual risks:** the umask probe-and-restore idiom remains an irreducible, POSIX-mandated,
process-global critical section — the module-level lock closes the only race an in-repo caller can
trigger (confirmed by `grep -rn "os\.umask" src/shared/packages` finding no other caller), but
cannot protect against a hypothetical future third-party dependency calling `os.umask()` outside
this lock, nor against another thread's unrelated file-creation syscall landing inside the brief
probe window. Both are pre-existing characteristics of this idiom (not newly introduced — the
window merely recurs at more call sites now, 19 instead of 0-1) and were explicitly evaluated and
accepted as irreducible across passes 2 and 3. `pyforge-atlas`'s `kedro-test` carries 4
pre-existing failures + 1 error unrelated to this story (environment provisioning / build
artifacts / evolving fixture content); not this story's to fix (Surgical Changes).

Follow-up review recommendation: **false** — pass 3's changes were 4 small, independently
execution-verified patches (one high-severity but mechanically simple and directly analogous to an
already-correct in-package fix), with no design, API, or security-relevant changes and no bad_spec
loopback triggered.
