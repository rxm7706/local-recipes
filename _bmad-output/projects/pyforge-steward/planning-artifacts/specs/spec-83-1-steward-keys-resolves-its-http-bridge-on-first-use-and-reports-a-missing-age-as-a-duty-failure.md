---
title: "83.1: `steward keys` resolves its `_http` bridge on first use and reports a missing `age` as a duty failure"
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
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

## Binding

Parent capabilities: CAP-1 (Epic 1, Stories 1.2–1.3), AD-8 (defect of shipped behaviour; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-02 entry.
Closes: DW-1-3-14, DW-1-3-5.
Ledger key: `83-1-steward-keys-resolves-its-http-bridge-on-first-use-and-reports-a-missing-age-as-a-duty-failure`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 by operator ruling: start Phase 2 of the deferral burn-down after the inflow wave.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-steward python -c "import pyforge.steward.sync"` — expected: exit 0.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
