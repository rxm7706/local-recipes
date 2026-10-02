---
title: "83.1: `steward keys` resolves its `_http` bridge on first use and reports a missing `age` as a duty failure"
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'e537a533144fd0b5f65586ddb5a42b74eb65b62c'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [multiple-goals, oversized]
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two defects in `steward keys`, verified at HEAD a7cdb91fe4:

- `keys.py:113-120` runs the `_http.py` bridge at import time: `_HTTP_SCRIPTS_DIR = str(locate_http_module().parent)`,
  a `sys.path` insert, then `from _http import auth_headers_for, resolve_github_api_urls`. `locate_http_module()`
  (`keys.py:94-110`) raises `RuntimeError` when no local-recipes checkout is above the package, so `steward keys <verb>`
  fails at duty resolution (`cli.py:1339`, `from .keys import KeysDuty`) in a package installed outside a checkout
  (DW-1-3-14). The same bridge breaks `sync.py`: its comment (`sync.py:58-60`) relies on `keys.py` having inserted the
  `_http` directory, but ruff's import sort (commit 6352cc067e, 2026-09-20) moved `from _http import open_url`
  (`sync.py:61`) above `from .keys import ...` (`:64`). A fresh `import pyforge.steward.sync` now raises
  `ModuleNotFoundError: No module named '_http'`, and `main(["sync", "reconcile", "--schedule", "--dry-run", ...])`
  returns 70 with a traceback (both reproduced 2026-10-02 in `-e pyforge-steward`).
- `KeysDuty.run` (`keys.py:1396-1450`) catches only `ValueError` and `subprocess.CalledProcessError`
  (`:1437-1444`). With `age` or `age-keygen` absent, `encrypt_file` (`:462-481`), `decrypt_file` (`:484-501`) and
  `generate_identity` (`:772-799`, used by `rotate`) raise `FileNotFoundError`, which reaches `cli.main()`'s
  `except Exception` (`cli.py:1490-1494`): a raw traceback and `EXIT_INTERNAL` (70) instead of a duty failure
  (DW-1-3-5).

**Approach:**

- Resolve the bridge lazily, in one place in `keys.py`: a cached function that locates `_http.py`, inserts its directory
  and returns the module, called by `resolve_headers` (`:276`), the `resolve_github_api_urls` call (`:1090`) and
  `sync.py`'s transport (`open_url`, `:343`) at first use. Outside a checkout it still raises a `RuntimeError` naming
  the marker path, now at first use rather than at import.
- `sync.py` takes `open_url` through that function instead of a module-level `from _http import`, so import order no
  longer matters.
- `KeysDuty.run` also catches `FileNotFoundError` from the `age` / `age-keygen` subprocesses and returns
  `DutyResult(ok=False, summary="keys <verb>: <binary> not found on PATH ...")` (exit 1 through `cli.main()`).

Ledger key: `83-1-steward-keys-resolves-its-http-bridge-on-first-use-and-reports-a-missing-age-as-a-duty-failure`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-1 (`steward keys`: issue, scope, rotate, audit, inventory; Epic 1, Stories 1.2–1.3) and AD-8 (a duty reports a
  duty failure; only `cli.main()` projects a crash). A defect of shipped behaviour, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a fresh interpreter with no `_http.py` reachable When `import pyforge.steward.keys` and `import pyforge.steward.sync` run Then both succeed
- Given a fresh interpreter in this checkout When `pyforge.steward.sync` is imported before `pyforge.steward.keys` Then the import succeeds and `main(["sync", "reconcile", ...])` no longer returns 70
- Given no checkout above the package When `resolve_headers` is first called Then it raises `RuntimeError` naming `.claude/skills/conda-forge-expert/scripts/_http.py`
- Given a checkout When `resolve_headers` is called twice Then the bridge is located once and `sys.path` gains the `_http` directory once
- Given `age` absent from PATH When `steward keys encrypt` or `decrypt` runs Then `main()` returns 1 and stderr names `age`, with no traceback
- Given `age-keygen` absent from PATH When `steward keys rotate` runs Then `main()` returns 1 and stderr names `age-keygen`, with no traceback
- Given the `FileNotFoundError` clause is removed When the missing-`age` test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:**
- Delegate to `_http.py` (AD-1/AD-2: wrap, never reimplement); the host-scoping decision in `resolve_headers` is
  unchanged.
- The fix must not depend on import order, which `ruff --select I` rewrites.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not vendor or copy `_http.py` into the package.
- Do not catch `FileNotFoundError` around anything but the `age` / `age-keygen` subprocess calls (a missing input file
  stays the existing `CalledProcessError` / `ValueError` path).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

</intent-contract>

## Code Map

All under `src/shared/packages/pyforge-steward/` (line numbers at HEAD e537a53314).

- `src/pyforge/steward/keys.py:94-120` -- `locate_http_module()` stays as is (also feeds `repo_root()` `:628`); the import-time block `:113-120` (`_HTTP_SCRIPTS_DIR`, `sys.path` insert, `from _http import ...`) is what goes.
- `src/pyforge/steward/keys.py:276` (`resolve_headers`), `:1090` (`enterprise_host`) -- the only two uses of `auth_headers_for` / `resolve_github_api_urls`.
- `src/pyforge/steward/keys.py:474`, `:494`, `:785` -- the three `subprocess.run` calls (`age`, `age`, `age-keygen`); `rotate_identity` `:862` calls `generate_identity` first, so a missing `age-keygen` fails before any file moves. A subprocess `FileNotFoundError` carries `.filename == "age"` / `"age-keygen"` (verified).
- `src/pyforge/steward/keys.py:1274` -- `_run_exec` already catches `OSError` around `_read_payload_token`, so `keys exec` without `age` is already a duty failure; leave it.
- `src/pyforge/steward/keys.py:1396-1445` -- `KeysDuty.run`, the one `try` that gains the clause.
- `src/pyforge/steward/sync.py:58-64` (stale comment, `from _http import open_url`), `:343` (`open_url` use in `_default_transport`) -- no test patches `open_url`.
- `src/pyforge/steward/cli.py:1335-1339` -- lazy `from .keys import KeysDuty`, whose comment says keys resolves `_http` "at import time" (stale after this story); the lazy import stays, `tests/unit/test_keys_encrypt_decrypt.py:165` pins it.
- Other importers of `pyforge.steward.keys` (`dashboard/export.py:58`, `src/platform/ingest/github_projects/*`) are unchanged.
- Test patterns: `tests/unit/test_keys_encrypt_decrypt.py` (`identity` fixture, `main(["keys", ...])`), `tests/unit/test_keys_rotate.py` (`_make_scope`), `tests/unit/test_keys_host_scoping.py` (credential env isolation).

## Tasks & Acceptance

**Execution:**
- `src/pyforge/steward/keys.py` -- replace the import-time block with `http_bridge()`, a `functools.cache`d function that calls `locate_http_module()`, inserts its directory on `sys.path` if absent and returns `importlib.import_module("_http")`; route `resolve_headers` and `enterprise_host` through it -- bridge resolves on first use, once
- `src/pyforge/steward/keys.py` -- add `except FileNotFoundError` to `KeysDuty.run`: re-raise unless `exc.filename` is `age` or `age-keygen`, else `DutyResult(ok=False, summary="keys <verb>: <binary> not found on PATH ...")`; extend the class docstring -- AD-8 duty failure, exit 1
- `src/pyforge/steward/sync.py` -- drop `from _http import open_url` and its comment; import `http_bridge` from `.keys` and call `http_bridge().open_url(...)` in `_default_transport` -- import order stops mattering
- `src/pyforge/steward/cli.py` -- reword the `:1335-1338` comment (the lazy import stays) -- keep it true
- `tests/unit/test_keys_http_bridge.py` (new) -- fresh-interpreter imports with `_http.py` hidden, sync-before-keys import plus `main(["sync", "reconcile", ...])` not 70, `RuntimeError` naming the marker outside a checkout, locate-once / `sys.path`-once; autouse fixture calls `http_bridge.cache_clear()` -- covers contract ACs 1-4
- `tests/unit/test_keys_encrypt_decrypt.py`, `tests/unit/test_keys_rotate.py` -- missing-`age` (encrypt, decrypt) and missing-`age-keygen` (rotate) via `main()` with `PATH` pointed at an empty directory: rc 1, stderr names the binary, no `Traceback`; a `FileNotFoundError` with another filename still propagates; refresh the `:165` docstring -- covers ACs 5-7
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` -- close `DW-1-3-14` and `DW-1-3-5` (`status: closed`, a `resolution:` line naming Story 83.1), mirroring the ledger's closed rows -- the Binding's Closes
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` and each co-governor `python scripts/spec_surface_reconcile.py` names -- append a `Surface reconcile` entry naming every governed path changed, with `_bmad/scripts/memlog.py`; never `--write-baseline` -- the run's own guard

**Acceptance Criteria:**
- Given the seven criteria in the intent contract, when the new tests run, then each is asserted by a named test and the missing-`age` test fails with the `FileNotFoundError` clause removed
- Given a `FileNotFoundError` whose filename is neither `age` nor `age-keygen`, when `KeysDuty.run` raises it, then it propagates unchanged

## Spec Change Log

## Binding

Parent capabilities: CAP-1 (Epic 1, Stories 1.2–1.3), AD-8 (defect of shipped behaviour; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-02 entry.
Closes: DW-1-3-14, DW-1-3-5.
Ledger key: `83-1-steward-keys-resolves-its-http-bridge-on-first-use-and-reports-a-missing-age-as-a-duty-failure`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 by operator ruling: start Phase 2 of the deferral burn-down after the inflow wave.

## Design Notes

- `functools.cache` does not cache a raised exception, so outside a checkout every call re-raises the named `RuntimeError`; a test clears the cache (`http_bridge.cache_clear()`) before and after.
- The clause discriminates on `exc.filename` rather than wrapping the three `subprocess.run` calls: the spec fixes the clause in `KeysDuty.run`, and the filename check keeps the Never (no `FileNotFoundError` catch around anything but `age` / `age-keygen`) true for every other path in that `try`.
- Out of scope: `repo_root()` and `default_inventory_path()` still raise the `RuntimeError` at first use outside a checkout (verbs given an explicit path no longer need them), and `generate_identity`'s own `RuntimeError` (exit 0, no public key) stays an internal error.
- Test shape for "no `_http.py` reachable": a subprocess that patches `pathlib.Path.is_file` to return False for `_http.py` before importing both modules, then asserts both import and `"_http"` is absent from `sys.modules`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 once every governed path is named on the owning Spec's `.memlog.md`.

**Manual checks:**
- `pixi run --frozen -e pyforge-steward python -c "import pyforge.steward.sync"` — expected: exit 0.

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 28 findings — high 1, medium 0, low 16, false 11, maybe-false 0 (four layers: Blind Hunter 12, Edge Case Hunter 8, Verification Gap 2 "other findings" and no gap findings, Intent Alignment 6 divergences)
- findings:
  - `[false]` `[reject]` Blind Hunter: on Windows a failed spawn leaves `exc.filename` as `None`, so the `FileNotFoundError` clause never fires — `keys.py:68` does `import fcntl` at module top (and `_run_exec` uses `PosixProcess`), so `pyforge.steward.keys` cannot be imported on Windows at all; the clause never runs there with or without this change.
  - `[low]` `[reject]` Blind Hunter: the `exc.filename in _AGE_BINARIES` discriminator would misreport a missing relative file literally named `age` or `age-keygen` in `rotate`/`list`/`audit`/`revoke` as "not found on PATH" — real, but it needs a path with that exact name; the spec's Design Notes fix this shape, `test_a_file_not_found_for_any_other_name_propagates_unchanged` pins the other direction, and the only fix (wrap the three spawn sites and raise a new typed error) adds public surface for a case nobody meets in everyday use.
  - `[low]` `[reject]` Blind Hunter: outside a checkout, `http_bridge()`'s `RuntimeError` reaches `keys exec` and `sync reconcile` as a traceback and exit 70 — the intent contract says it "still raises a `RuntimeError` naming the marker path, now at first use" and AC 3 asserts exactly that; the failure is loud and names the missing path, and mapping it needs new `except` clauses in two duties the intent does not ask for.
  - `[low]` `[patch]` Blind Hunter: `test_sync_imported_before_keys_still_imports_and_reconcile_does_not_crash` passes a missing config, so nothing runs the real `_http` through the new path — and lazy resolution lost the import-time failure that used to catch a renamed delegate name; grouped with the Edge Case Hunter and Intent Alignment rows on the same root cause. Fix applied: appended `test_real_bridge_exposes_every_name_keys_and_sync_delegate_to` to `tests/unit/test_keys_http_bridge.py` (the real `http_bridge()` carries callable `auth_headers_for`, `resolve_github_api_urls`, `open_url`).
  - `[low]` `[reject]` Blind Hunter: `http_bridge()` never checks which `_http` it imported, and its `sys.path.insert(0, …)` is permanent — the removed import-time block did the same insert and the same `import _http`, so this change introduces neither; no one has met a shadowed `_http`.
  - `[false]` `[reject]` Blind Hunter: ledger rows `DW-1-3-14` / `DW-1-3-5` closed while the story is `in-review` — the spec's Execution tasks and its Binding ("Closes: DW-1-3-14, DW-1-3-5") prescribe closing them in this change; the rows land with this branch, and a loopback would revert them together with the code.
  - `[false]` `[reject]` Blind Hunter: surface reconcile incomplete and no stamp — `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` both exit 0 after the final edit with both memlog entries present; this run's instructions forbid `--write-baseline`.
  - `[low]` `[patch]` Blind Hunter: `test_cli_module_import_does_not_trigger_the_keys_bridge` names an import-time bridge that no longer exists. Fix applied: renamed to `test_cli_module_import_does_not_import_keys` (body and docstring unchanged; no other file referenced the old name).
  - `[false]` `[reject]` Blind Hunter: test hygiene (`re.escape` on Windows, no output-file assertion on the encrypt/decrypt missing-`age` tests, `monkeypatch.delitem` leaving `_http` in `sys.modules`) — `keys` cannot import on Windows (see the first row); a spawn that fails never writes output, so the return code and stderr assertions already prove the outcome; a leftover `_http` is the same real module the bridge imports anyway.
  - `[false]` `[reject]` Blind Hunter: failure message, module docstring and skill gotcha miss the new behaviour — the message names the binary and the remedy, the docstring's per-story slices stay true, and "crash is exit 70 not 1" stays true for crashes; no harm shown.
  - `[false]` `[reject]` Blind Hunter: `http_bridge() -> ModuleType` erases static checking — `pyproject.toml` sets `ignore_missing_imports = true` with `mypy_path = "src"`, so mypy never resolved `_http`; the old `from _http import …` names were already `Any`; `lint-types` exits 0.
  - `[false]` `[reject]` Blind Hunter: the spec's Code Map line numbers drift, its `warnings` are unexplained and `## Spec Change Log` is empty — the only fix edits this build's spec, and the warnings are the workflow's own output.
  - `[high]` `[patch]` Edge Case Hunter: `tests/packaging/test_dependency_completeness.py` `BASELINE_UNDECLARED_IMPORTS["pyforge-steward"]["_http"]` describes the import-time `_http` import this story removed, so `test_baseline_entries_are_still_violated` fails — reproduced here, `-e pyforge-ci`, exit 1; a red CI lane the station suite does not run. Fix applied: deleted that entry, and reworded the `django_pyforge` entry that compared itself to "`_http` above"; the test file now gives 85 passed, exit 0.
  - `[low]` `[reject]` Edge Case Hunter: `rotate` with `age-keygen` present and `age` absent leaves the new identity file, so "install age and retry" then fails on `age-keygen`'s refusal to overwrite — `rotate_identity`'s docstring already records this non-atomicity for every partial failure, and the case needs the two binaries (shipped together) to be split.
  - `[low]` `[reject]` Edge Case Hunter: `http_bridge()` outside a checkout is not mapped to a duty failure in `keys exec` / `sync` — same root cause and same reason as the third row.
  - `[low]` `[reject]` Edge Case Hunter: a non-executable `age` (`PermissionError`) or a dangling shebang is not handled — speculative environment outside the story's "binary missing" scope, and the fix adds branches.
  - `[low]` `[reject]` Edge Case Hunter: the clause is under the whole `try` and compares a string — same root cause and same reason as the second row.
  - `[low]` `[patch]` Edge Case Hunter: `DW-1-3-14` closed as RESOLVED while `repo_root()` / `default_inventory_path()` still raise outside a checkout — grouped with the Intent Alignment "reading B" row. Fix applied: the row's `resolution:` now states that `keys list|rotate|revoke|audit` without `--inventory` still need a checkout, while encrypt, decrypt and any verb given explicit paths work.
  - `[low]` `[patch]` Edge Case Hunter: no fresh-interpreter test reaches the real transport — same root cause as the fourth row; fixed by the same appended test.
  - `[low]` `[patch]` Edge Case Hunter: `deploy.py:79-84` still says `keys.py`'s top-level import refuses to load outside a checkout — grouped with the Verification Gap row. Fix applied: comment reworded to say `keys.py` resolves `_http` at first use through `http_bridge()` and `resolve_duty` still imports it lazily.
  - `[low]` `[patch]` Verification Gap (other finding): the same stale `deploy.py` comment — fixed with the row above.
  - `[false]` `[reject]` Verification Gap (other finding): `dashboard/export.py` `maybe_encrypt_export` still lets a missing `age` surface as a raw `FileNotFoundError` — its docstring documents that contract and the spec scopes the clause to `KeysDuty.run`; the reviewer itself calls it not a defect.
  - `[false]` `[reject]` Intent Alignment: ACs 1–2 simulate "outside a checkout" by hiding `_http.py` from `locate_http_module`'s walk-up in a fresh interpreter rather than installing the package elsewhere — that is the observable the criterion names, and `_http` is asserted absent from `sys.modules` after both imports.
  - `[low]` `[patch]` Intent Alignment: the sync-before-keys test stops before any transport call — same root cause as the fourth row; fixed by the same appended test.
  - `[false]` `[reject]` Intent Alignment: the mutation criterion (AC 7) is a claim the diff's tests do not encode — it is a verification-time check, and I ran it: with the clause renamed to `except KeyError` the three missing-binary tests fail (3 failed), and `keys.py` was restored byte-identical (sha256 compared).
  - `[low]` `[reject]` Intent Alignment: clause placement (`KeysDuty.run`, discriminated by `exc.filename`) versus the Never's "around the subprocess calls" — same root cause and same reason as the second row.
  - `[low]` `[patch]` Intent Alignment: reading B (every verb works outside a checkout) is only partly implemented — grouped with the Edge Case Hunter ledger row; the Design Notes already scope `repo_root()` out, and the ledger now states the residual.
  - `[false]` `[reject]` Intent Alignment: the diff changes the ledger, memlog and story status, which no acceptance criterion names — the spec's Execution tasks and Binding prescribe each.

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** `keys.py` no longer runs the `_http.py` bridge at import time: `http_bridge()` is a `functools.cache`d function that locates `_http.py`, puts its directory on `sys.path` once and imports `_http` at first use. `resolve_headers`, `enterprise_host` and `sync.py`'s `_default_transport` call it, so `import pyforge.steward.keys` and `import pyforge.steward.sync` succeed with no `_http.py` reachable and in any import order, and outside a checkout the first call raises the `RuntimeError` naming `.claude/skills/conda-forge-expert/scripts/_http.py`. `KeysDuty.run` reports an absent `age` or `age-keygen` as `DutyResult(ok=False, ...)` naming the binary (exit 1, no traceback); a `FileNotFoundError` for any other name propagates. `DW-1-3-14` and `DW-1-3-5` are closed in the tracked ledger.

**Files changed** (all under `src/shared/packages/pyforge-steward/` unless noted)
- `src/pyforge/steward/keys.py` — `http_bridge()` replaces the import-time block; `KeysDuty.run` gains the `FileNotFoundError` clause and `_AGE_BINARIES`.
- `src/pyforge/steward/sync.py` — drops the module-level `from _http import open_url`; `_default_transport` calls `http_bridge().open_url`.
- `src/pyforge/steward/cli.py`, `src/pyforge/steward/deploy.py` — comments reworded to match the lazy bridge; no behaviour change.
- `tests/unit/test_keys_http_bridge.py` (new) — fresh-interpreter imports with `_http.py` hidden, `sync` before `keys`, the named `RuntimeError`, located-once / `sys.path`-once, the transport through the bridge, and the real bridge's three delegate names.
- `tests/unit/test_keys_encrypt_decrypt.py`, `tests/unit/test_keys_rotate.py` — missing `age` (encrypt, decrypt) and missing `age-keygen` (rotate) through `main()` with `PATH` at an empty directory; a non-age `FileNotFoundError` propagates; the lazy-import test renamed.
- `tests/packaging/test_dependency_completeness.py` (repo root `tests/`) — the `_http` entry of `BASELINE_UNDECLARED_IMPORTS["pyforge-steward"]` deleted, and the `django_pyforge` entry no longer points at it.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — `DW-1-3-14` and `DW-1-3-5` closed, each with a `resolution:` and a `verified:` line citing `path:line`; the `DW-1-3-14` resolution states the residual.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` — two `Surface reconcile 2026-10-02` entries naming every governed path changed; no baseline stamp.

**Review findings.** 28 findings, one pass. Patches applied: 5 entries, high 1 and low 4 (medium 0) — the stale `tests/packaging` baseline entry (high), the missing real-bridge test, the stale test name, the `DW-1-3-14` residual note, and the stale `deploy.py` comment. Deferred: none (`deferred: []`). Rejected: 8 `low` findings (the `exc.filename` discriminator, the unmapped outside-a-checkout `RuntimeError`, `http_bridge()` shadowing, the rotate leftover identity, `PermissionError`) and 11 `false` findings, each with its recorded reason in the Review Triage Log.

**Follow-up review recommendation: `false`.** This is a first pass and one patched entry was `high`, so the score would be `true` only if a specific unverified risk remained. None does: the high finding was a red `tests/packaging` lane the station suite does not run; after the fix the whole lane passes (`pyforge-deps-test`, 130 passed, 3 skipped), the only red detector in `detectors-ci` is the unrelated `ledger-direction` (below), and nothing else in the repo keys on the removed import. Patched counts by verdict: high 1, medium 0, low 4.

**Verification performed** (every verdict read from the exit code)
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 1929 passed, 2 skipped (after the last edit).
- `pixi run -e pyforge-guild lint-types` — exit 0.
- `python scripts/spec_surface_reconcile.py` — exit 0; `pixi run -e pyforge-guild spec-surface-check` — exit 0; `deferred-work-check` — exit 0.
- `pixi run --frozen -e pyforge-steward python -c "import pyforge.steward.sync"` — exit 0 (it failed with `ModuleNotFoundError: No module named '_http'` before the change).
- `pixi run --frozen -e pyforge-steward pyforge-steward-coverage-gate` — exit 0, touched modules at or above the 80% unit floor.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — exit 0, 130 passed, 3 skipped.
- Mutation check (AC 7): with the clause renamed to `except KeyError`, the three missing-binary tests fail (3 failed); `keys.py` restored byte-identical.
- `pixi run -e pyforge-guild pr-preflight` — exit 1, and not clean: see the first residual.

**Residual risks**
- `pr-preflight` exits 1 on one detector, `ledger-direction`, naming `pyforge-marshal/82-1-gate-evaluate-finds-the-real-repository-under-an-installed-package-and-never-passes-having-run-nothing` as `landed-but-unpromoted`. It is not caused by this change: that merge is on `main` (`6d4de8e484`) but not in this branch, `main`'s tracked marshal ledger already reads `done`, this branch's older copy reads `backlog`, and the detector compares `main`'s merge history with the branch's ledger. It should clear when this branch is merged with `main`; this run did not touch another station's ledger, which is harness-owned. The red lane stopped `pr-preflight` before its remaining station lanes, so I ran the lanes this diff can affect individually (above).
- `repo_root()` and `default_inventory_path()` still raise the `RuntimeError` outside a checkout, so `keys list|rotate|revoke|audit` without `--inventory` still need one; the spec scopes this out and the ledger row states it.
- The clause matches on `exc.filename`, so a missing relative file literally named `age` or `age-keygen` in a non-spawn path would be reported as a missing binary; the spec's Design Notes choose this shape.
- The harness checkpointed the work as `wip: 83.1` commits; the history wants a proper merge subject at landing (`Merge pyforge-steward/83.1 into main`).
