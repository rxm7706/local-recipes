---
title: "83.1: `steward keys` resolves its `_http` bridge on first use and reports a missing `age` as a duty failure"
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
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

- No independent review has run yet (implementation and review stay separate).
