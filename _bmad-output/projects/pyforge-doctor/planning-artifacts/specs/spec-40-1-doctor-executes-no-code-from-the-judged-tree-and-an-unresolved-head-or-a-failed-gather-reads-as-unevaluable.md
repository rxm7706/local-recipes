---
title: "40.1: Doctor executes no code from the judged tree, and an unresolved head or a failed gather reads as unevaluable"
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: '885f2a1de1a0963b4abb788c15d03be134001dd5'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/score.py
warnings: [multiple-goals, oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three detector-correctness defects, verified at HEAD a7cdb91fe4 (paths under
`src/shared/packages/pyforge-doctor/src/pyforge/doctor/`):

- `sources/board.py:1524-1538` `_load_dashboard_generate(target)` `exec_module`s `target / "scripts" / "fleet_scan.py"`
  through `_load_foreign_module` (`:1437-1494`), and `_gather_chain_layers_audit` (`:1181-1183`) calls it on the live
  `chain-completeness --layers --project <slug>` path (`sources/__main__.py:277`). `sources/factory.py:1464-1473`
  `_load_pixi_env_matrix_module(target)` does the same with `target / "scripts" / "pixi_env_matrix.py"` for
  `check_pixi_env_matrix` (`:1476-1484`), leaving it in `sys.modules`. Code is resolved from the tree being judged, so any
  caller handing `gather(target)` another tree runs that tree's Python with Doctor's privileges (DW-FU-6-5-9).
- `sources/ledger.py` `gather()` probes only `base` with `rev-parse --verify --quiet` (`:409`) and reads `head` with a
  plain `rev-parse` (`:430`). With `base` resolvable and `head` not, `head_sha` is empty, neither the same-commit branch
  (`:433`) nor the merge-base branch (`:450`) runs, and `_check(target, effective_base, head)` (`:494`) lists no ledgers
  at `head` (`_ledger_paths`, `:229-233`, `:262`), so every base ledger holding a `done` key becomes a
  `ledger-deleted` FAIL (DW-FU-6-4-3).
- `score.py:51` `_GATHER_FAILURE_CHECK = "doctor.sources.atlas"` and `_is_gather_failure` (`:123-124`) match only an
  evidence-less atlas finding. `degrade_on_exception` (`sources/__init__.py:578-619`) emits a WARN with the source's own
  `check` and `evidence={"exception": ...}`, so a gather that failed outright grades its axis C, not `incomplete`, and
  the composite takes a letter (`score.py:181`, `:198-203`) (DW-FU-6-6-11).

**Approach:**

- Both loaders resolve the file from Doctor's own checkout, located by walking up from the module's own `__file__` (the
  pattern `steward`'s `keys.locate_http_module` uses), never from `target`. `target` keeps supplying the data: the
  chain-layers gather already re-points `REPO_ROOT` / `DREAMS_DIR` at `target` (`board.py:1203-1210`), and
  `check_pixi_env_matrix` already passes `target`'s Dream and lock as arguments. With no checkout above Doctor, the load
  fails with an `OSError` naming the missing file, which the existing `chain-layers-audit-unevaluable` WARN
  (`board.py:1184-1198`) and the env-matrix check's `except OSError` -> `_unevaluable` path (`factory.py:1496-1497`)
  already report. `_load_pixi_env_matrix_module` gets the same `sys.path` / `sys.modules` cleanup
  `_load_foreign_module` has.
- `ledger.gather` probes `head` with `rev-parse --verify --quiet` next to `base`, and an unresolvable `head` returns one
  `ledger-regression` WARN naming it (evidence `base`, `head`, `target`, like the other cannot-evaluate WARNs).
- `_is_gather_failure` also returns true for a WARN whose evidence carries `exception` (the `degrade_on_exception`
  shape); the atlas shape keeps matching.

Ledger key: `40-1-doctor-executes-no-code-from-the-judged-tree-and-an-unresolved-head-or-a-failed-gather-reads-as-unevaluable`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- FR-15 (Stories 6.4–6.6, the ledger, board and chain verdicts), marshal Story 17.3 (the chain-layers audit), steward
  Story 43.5 (the env-matrix check, canopy:AD-23), and CAP-5 ("an incomplete axis gather degrades the grade to
  explicitly `incomplete`, never a false `A`"). Defects of shipped behaviour, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a tmp `target` whose `scripts/fleet_scan.py` writes a probe file when executed When `board.gather_chain_layers_audit(target, project)` runs Then the probe file does not exist and the layers are computed from `target`'s files
- Given a tmp `target` whose `scripts/pixi_env_matrix.py` writes a probe file when executed When `factory.check_pixi_env_matrix(target)` runs Then the probe file does not exist
- Given the existing chain-layers fixtures (a tmp `target` with the real `fleet_scan.py` copied in) When their tests run Then they pass unchanged in outcome
- Given a repo where `base` resolves and `head` does not When `ledger.gather(target, base=..., head="no-such-ref")` runs Then it returns exactly one WARN naming the head and no FAIL
- Given a `Finding(source=Source.DREAM_CHAIN, check="dream-chain", status=WARN, evidence={"exception": "OSError"})` When `score.grade` runs Then that axis is `incomplete` and the composite grade is `incomplete`
- Given an ordinary WARN with no `exception` evidence When `score.grade` runs Then its axis still takes a letter grade
- Given either loader reverted to resolve from `target` When the probe test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:**
- Findings stay advisory; no detector becomes a second PR gate.
- `degrade_on_exception` keeps catching `Exception`, never `BaseException`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not copy `scripts/fleet_scan.py` or `scripts/pixi_env_matrix.py` into the package.
- Do not change which ledger transitions count as regressions when both refs resolve.
- Do not delete or weaken an existing test.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

</intent-contract>

## Code Map

Package root `src/shared/packages/pyforge-doctor/` (`P` below = `src/pyforge/doctor/`; tests under `tests/unit/`).

- `P/sources/board.py:1181-1198` `_gather_chain_layers_audit` -- already turns any loader `Exception` into the `chain-layers-audit-unevaluable` WARN; no change.
- `P/sources/board.py:1437-1494` `_load_foreign_module(path, mod_name)` -- keep the signature (`test_fleet_scan_pitch_roster.py`, `test_fleet_scan_currency_feeds.py` call it with an explicit path).
- `P/sources/board.py:1524-1538` `_load_dashboard_generate(target)` -- the fix site: `target / "scripts" / "fleet_scan.py"` becomes the located checkout script; the `REPO_ROOT` / `DREAMS_DIR` / `_PIXI_TASKS` re-point at `target` stays. Its `# pragma: no cover -- retired Guildhall console` and the comment block above it (`:1497-1522`) are stale (the loader is live and covered); correct them.
- `P/sources/factory.py:1464-1473` `_load_pixi_env_matrix_module(target)` -- the second fix site; `:1476-1498` `check_pixi_env_matrix` already passes `target`'s dream and lock to `mod.matrix_is_stale(dream, lock)` and maps `OSError` to `_unevaluable`.
- `P/sources/__init__.py:578-620` `degrade_on_exception` -- sole producer of `evidence={"exception": <class name>}`; the home for the shared locator, next to it.
- `P/sources/ledger.py:376-494` `gather` -- base probe `:409`, plain `rev-parse` of base/head `:429-430`; `_git` (`:102`) returns `None` on any failure.
- `P/score.py:44-51`, `:123-124`, `:181` -- `_GATHER_FAILURE_CHECK`, `_is_gather_failure`, the per-axis `any(...)`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py:97-113` `locate_http_module` -- the walk-up-from-`__file__` pattern to mirror (read-only; never import it).
- `scripts/fleet_scan.py:81-95` (`_discover_repo_root`, import-time `sys.path.insert`) and `scripts/pixi_env_matrix.py:29` (`REPO_ROOT` from its own file) -- the scripts being located; read-only, never copied.
- `tests/unit/test_sources_board_chain_layers_audit.py` (`_install_generate` copies the real `fleet_scan.py` into a tmp target; `_live_scan()` `:296` passes the live root), `test_sources_factory.py` (no env-matrix test today), `test_sources_ledger.py:212` (`test_unresolvable_base_ref_reports_warn`, the model for the head test), `test_score.py` (`_gather_failure`, `_finding`).

## Tasks & Acceptance

**Execution:**
- `P/sources/__init__.py` -- add `locate_checkout_script(name)`: walk `Path(__file__).resolve().parents` for `scripts/<name>` as a file; no match raises `FileNotFoundError` (an `OSError`) naming the file -- one locator both loaders share, never `target`
- `P/sources/board.py` -- `_load_dashboard_generate` loads `locate_checkout_script("fleet_scan.py")`; drop the stale pragma, fix the comment block
- `P/sources/factory.py` -- `_load_pixi_env_matrix_module` loads `locate_checkout_script("pixi_env_matrix.py")`, snapshots and restores `sys.path`, pops `sys.modules` on a failed `exec_module`
- `P/sources/ledger.py` -- probe `head` with `rev-parse --verify --quiet` after the base probe; unresolvable returns one `ledger-regression` WARN naming it (evidence `base`, `head`, `target`)
- `P/score.py` -- `_is_gather_failure` also true for a WARN whose evidence carries `exception`; atlas shape still matches; update the docstring/comment that names the sentinel
- `tests/unit/test_sources_board_chain_layers_audit.py`, `test_sources_factory.py`, `test_sources_ledger.py`, `test_score.py` -- one test per contract AC (probe-file tests for both loaders, each with a sensitivity twin that re-points the locator at `target` and sees the probe; the head WARN; the exception-evidence `incomplete`; the ordinary WARN still graded); existing tests untouched
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` -- close DW-FU-6-5-9, DW-FU-6-4-3, DW-FU-6-6-11 in the file's own row format
- Spec `.memlog.md` -- name every governed path changed on `spec-pyforge-doctor` and each co-governor `spec-surface` names, before the reconcile guard runs

**Acceptance Criteria:**
- The seven Given/When/Then rows in the intent contract's own `## Acceptance Criteria`; `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` exit 0.

## Spec Change Log

## Design Notes

Why the checkout and not `target`: Doctor judges trees it does not own, so a judged `scripts/*.py` must stay data. The only legitimate source of a script Doctor runs is the checkout Doctor itself lives in; outside any checkout (an installed wheel) the locator raises and both callers already report "unevaluable".

```python
def locate_checkout_script(name: str) -> Path:
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "scripts" / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"scripts/{name} not found above {Path(__file__).resolve()}")
```

## Binding

Parent capabilities: FR-15 (Stories 6.4–6.6), CAP-5 (defects of shipped behaviour; no new CAP).
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-02 entry.
Closes: DW-FU-6-5-9, DW-FU-6-4-3, DW-FU-6-6-11.
Ledger key: `40-1-doctor-executes-no-code-from-the-judged-tree-and-an-unresolved-head-or-a-failed-gather-reads-as-unevaluable`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 by operator ruling: start Phase 2 of the deferral burn-down after the inflow wave.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
