---
title: "40.1: Doctor executes no code from the judged tree, and an unresolved head or a failed gather reads as unevaluable"
type: 'fix'
created: '2026-10-02'
status: 'done'
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
deferred:
  - summary: >-
      A cannot-evaluate WARN that carries no `exception` evidence (the new unresolvable-head ledger WARN, `chain-layers-audit-unevaluable`, `bmad-drift-unevaluable`) still grades its axis as a letter (C), not `incomplete`.
    evidence: |-
      Verified live by the intent-alignment review layer: each of those three shapes grades C, while a real `degrade_on_exception` WARN grades `incomplete`. Not caused by this story (they graded C before) and this story's Approach and ACs pin the predicate to the `exception` evidence shape. The head WARN's evidence keys are pinned to `base`/`head`/`target`, and `ledger-regression` is also the check name of the ordinary verdicts, so a shared marker needs a contract decision across sources. Latent today: `score.grade` is fed only atlas and warden findings in production. Settle it with a decision on one evidence marker (or check-name convention) for "this axis could not be evaluated" that every cannot-evaluate WARN carries, then generalise `_is_gather_failure`.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/score.py:125
    severity: medium
  - summary: >-
      `docs_currency` runs the judged tree's own declared generator script (`target / <generator from the target's docs/map.yaml> --check`, `cwd=target`) at Doctor's privileges, by subprocess rather than `exec_module`.
    evidence: |-
      `sources/docs_currency.py:452-468` builds `generator_path = target / generator` and runs it through `cli_bridge.run_check_script`. Pre-existing and outside the two loader sites this story's intent names. Unverified whether it is a defect: the module's own design note says it deliberately treats each generator as "an opaque, already-decided verdict" because a generator's source of truth lives in `scripts/`, and `tests/meta/test_source_independence.py` governs textual import/exec references, not this subprocess. What would settle it: an operator ruling on whether Doctor may run the judged tree's declared generators, or a conformance test that names the trust model either way.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py:452
    severity: high (unverified)
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

### 2026-10-02 — Review pass
- verdicts: 30 findings — high 0, medium 8, low 13, false 8, maybe-false 1
- findings (Blind Hunter BH1-10, Edge Case Hunter EH1-7, Verification Gap VG1-3, Intent Alignment IA-a..j, in the order the layers reported):
  - `[medium]` `[patch]` BH1 `_load_dashboard_generate` re-points `REPO_ROOT`/`DREAMS_DIR`/`_PIXI_TASKS` but not `ARCHIVE_DREAMS_DIR` (`scripts/fleet_scan.py:953`) — verified: it is fixed at import from the checkout's root and `_dream_files()` (`:956-971`, reached through `scan_fleet` -> `_fleet_chains`) reads it, so auditing another tree reads the Doctor checkout's archived Dreams; before this change the target's own script computed it from the target. Fix applied: `board._load_dashboard_generate` re-points `ARCHIVE_DREAMS_DIR` to `target.resolve() / "archive" / "docs" / "dreams"` beside the other re-points (`hasattr`-guarded), the block comment names it, and `test_the_loader_points_every_data_path_at_the_target_not_the_checkout` pins it (re-run with the re-point removed: it fails on the checkout's `archive/docs/dreams`).
  - `[low]` `[patch]` BH2 the env-matrix loader's docstring claims "the same guards" as `board._load_foreign_module` but has no `SystemExit` conversion — the docstring overclaims (the code has the two guards the intent names: `sys.path` restore, `sys.modules` pop). Fix applied: the docstring now names exactly those two guards and says the third is not applied. The suggested dedupe into one shared loader and a `SystemExit` guard are not taken: the checkout's `pixi_env_matrix.py` raises `SystemExit` only inside `update_dream` and under `__main__`, never at import, so the escape is not reachable, and a shared loader is more than a direct correction (factory importing board would couple two independent sources).
  - `[low]` `[reject]` BH3 `locate_checkout_script` is an unanchored walk (a stray `~/scripts/...`, or Doctor installed inside a judged tree) — the intent's Approach specifies exactly this walk, mirroring `keys.locate_http_module`; reaching the judged tree needs it to be an ancestor of Doctor's own install, i.e. the tree whose environment Doctor already runs from, so no new privilege is shown; the anchor would add a marker rule the intent did not ask for. Residual risk recorded in Auto Run Result.
  - `[medium]` `[defer]` BH4 `_is_gather_failure` matches only the `degrade_on_exception` shape, so `chain-layers-audit-unevaluable`, `bmad-drift-unevaluable` and the new head WARN still grade C — verified live by the Intent Alignment layer (each grades C); not caused by this story (they graded C before) and the intent's Approach and ACs pin the exception shape; the head WARN's evidence keys are pinned to `base`/`head`/`target`, so a shared marker needs a contract decision across sources. Latent: `score.grade` is fed only atlas and warden today.
  - `[low]` `[reject]` BH5 the predicate keys on a duplicated bare `"exception"` string, and an axis holding a real FAIL plus an exception WARN grades `incomplete` and hides the FAIL's letter — the literal is already tied to the key `degrade_on_exception` writes by `test_a_real_degrade_on_exception_warn_grades_its_axis_incomplete`, and a grep of `src` finds no other producer of that key, so a marker or shared constant is more than a direct correction; the mixed-axis outcome is by design (`score.py`'s module docstring: any gather-failure sentinel makes the axis `incomplete`, which outranks every letter; the atlas sentinel behaves the same and the reason string names the axis).
  - `[low]` `[reject]` BH6 `rev-parse --verify --quiet` accepts any object (a blob or tree SHA, a well-formed 40-hex SHA with no object), and a leading-`-` `head` parses as an option — the outcome is still one WARN naming `head` via the no-common-ancestor branch, never the `ledger-deleted` FAILs (the base probe has the same property); no live caller passes `head`, so it is unlikely to be met, and peeling with `^{commit}` plus `--end-of-options` on both probes is more than a direct correction.
  - `[false]` `[reject]` BH7 the three closed ledger rows contradict themselves — the file's own resolved rows (e.g. DW-FU-7-1-4) keep their original `evidence:` and older `verified:` lines and add `resolution:`/`verified:`, and cite `file:line`; the new rows follow that format.
  - `[low]` `[reject]` BH8 brittle new tests (the `lock-sha256=` marker and 16-char digest slice, inconsistent skip gating, two near-duplicate probe helpers) — developer-only, the tests fail loudly if the script's format moves, and the package suite runs inside the checkout; consolidating helpers is more than a direct correction.
  - `[low]` `[reject]` BH9 nothing outside the code records the trust-model change — the stale `pyforge.doctor.sources.fleet_scan` phrase in `docs/how-to/pixi-tasks.md:79` is pre-existing and comes from a generated page's `pixi.toml` description; no doc or skill states the old target-resolved behaviour, and `pyforge-doctor` ships no CHANGELOG.
  - `[false]` `[reject]` BH10 bundles three defects, a stale Code Map line, an empty Spec Change Log, no AC-to-test map — the fix is to edit this build's spec; `multiple-goals` is a declared warning and the story is one ledger row by the operator's mint.
  - `[medium]` `[patch]` EH1 same root cause as BH1 (guard: re-point `ARCHIVE_DREAMS_DIR`) — see BH1; fixed with it.
  - `[medium]` `[defer]` EH2 same root cause as BH4 (unevaluable WARNs grade C) — see BH4.
  - `[low]` `[reject]` EH3 same as BH6 (a nonexistent 40-hex SHA passes the head probe and reads as "no common ancestor") — see BH6.
  - `[low]` `[reject]` EH4 same as BH3 (a locator accepting any ancestor with `scripts/<name>`) — see BH3.
  - `[medium]` `[patch]` EH5 same root cause as BH1 (the claim "target supplies the data" is false for `ARCHIVE_DREAMS_DIR`) — see BH1; fixed with it.
  - `[medium]` `[defer]` EH6 same root cause as BH4 (a missing checkout script yields C, not `incomplete`) — see BH4.
  - `[low]` `[reject]` EH7 same as BH3 (the docstring says an installed wheel raises) — see BH3; the docstring says "outside any checkout", which a wheel under a checkout is not.
  - `[maybe-false]` `[defer]` VG1 `sources/docs_currency.py:452-468` runs `target / <generator from target's docs/map.yaml> --check` with `cwd=target` through `cli_bridge.run_check_script` — a judged tree's code at Doctor's privileges, by subprocess rather than `exec_module`; pre-existing and outside the two sites the intent names. Unverified whether it is a defect: the module's own design note says it deliberately treats each generator as "an opaque, already-decided verdict" (a generator's source of truth lives in `scripts/`), and `tests/meta/test_source_independence.py` governs textual import/exec references, not this subprocess. What would settle it: an operator ruling on whether Doctor may run the judged tree's declared generators, or a conformance test naming the trust model.
  - `[medium]` `[defer]` VG2 same root cause as BH4 (the head WARN and the two `-unevaluable` WARNs carry no `exception` evidence) — see BH4.
  - `[low]` `[reject]` VG3 same as BH6 (a nonexistent 40-hex SHA passes the probe; the test covers only a ref name) — see BH6.
  - `[false]` `[reject]` IA-a `score.grade` is fed only atlas and warden in production, so the `exception` branch is reached by direct callers and tests — true, and the intent says so (the DW-FU-6-6-11 entry: "Latent today rather than live"); the ACs observe `score.grade`, the surface the intent names, so nothing diverges.
  - `[medium]` `[defer]` IA-b the table: the missing-checkout outcome, the env-matrix `OSError` outcome and the new head WARN each grade C — same root cause as BH4; the real `degrade_on_exception` WARN grades `incomplete`, as the AC asks.
  - `[low]` `[reject]` IA-c `sources/__main__.py:277` hardcodes `target = Path(".")`, no test drives the dispatcher, and "no checkout" is tested by monkeypatching — the change at that surface (a cwd's `scripts/fleet_scan.py` no longer runs) is the intended one; the ACs name the library functions, and a dispatcher test is extra rather than a defect.
  - `[false]` `[reject]` IA-d no production caller passes `head=`, so the head fix is reachable live only for an unresolvable `HEAD` — descriptive; the AC names `ledger.gather(..., head="no-such-ref")`, which the test exercises.
  - `[false]` `[reject]` IA-e the factory loader drops its `target` parameter — its only callers are `check_pixi_env_matrix` and the new tests (grep), and a parameter that must never select the file has no use.
  - `[low]` `[patch]` IA-f the factory docstring says "the same guards" but the code has no `SystemExit` conversion — same root cause as BH2; fixed with it (docstring reworded).
  - `[false]` `[reject]` IA-g `_install_generate` still copies `fleet_scan.py` into the tmp target and the loader now ignores that copy — AC3 requires the existing fixtures to pass unchanged, so leaving them is required; they pass because the checkout's file is the same.
  - `[false]` `[reject]` IA-h the sensitivity twins monkeypatch the locator instead of reverting the source line, "by inspection" the probe tests would fail under a revert — settled by running it: reverting `board.py`'s loader to `target / "scripts" / "fleet_scan.py"`, `factory.py`'s to `target`, removing the head probe, and reverting `_is_gather_failure` to the atlas-only predicate each fail the matching new test (`AssertionError: the judged tree's scripts/fleet_scan.py was executed`; `AttributeError ... no attribute 'matrix_is_stale'`; `'ledger-deleted' == 'ledger-regression'`; `Grade.C is Grade.INCOMPLETE`), tree restored clean after each.
  - `[low]` `[reject]` IA-i the walk-up trusts the first ancestor with `scripts/<name>` — same as BH3.
  - `[false]` `[reject]` IA-j the diff also closes three DW rows with a "mutation-checked" claim, moves the spec to `in-review` and appends a memlog entry — the epic text requires the row closures and the task's reconcile step requires the memlog entry; the "mutation-checked" claim holds (IA-h run).

## Auto Run Result

Status: done

**Summary of implemented change.** Doctor no longer executes code from the tree it judges, an unresolvable ledger `head` reads as "cannot evaluate", and a gather that failed outright grades its axis `incomplete`.

- `sources.locate_checkout_script(name)` returns `scripts/<name>` of the checkout Doctor lives in (walked up from the module's own `__file__`, the `keys.locate_http_module` pattern); outside any checkout it raises `FileNotFoundError`, which both callers already report as unevaluable.
- `board._load_dashboard_generate` and `factory._load_pixi_env_matrix_module` load through it, never from `target`; `target` keeps supplying the data. The factory loader gained the `sys.path` restore and the `sys.modules` pop on a failed load.
- `ledger.gather` probes `head` with `rev-parse --verify --quiet`; an unresolvable `head` is one `ledger-regression` WARN naming it (evidence `base`, `head`, `target`), never the `ledger-deleted` FAILs.
- `score._is_gather_failure` also matches a WARN whose evidence carries `exception` (the `degrade_on_exception` shape); the atlas shape still matches.
- DW-FU-6-5-9, DW-FU-6-4-3 and DW-FU-6-6-11 are closed in the station's `deferred-work-ledger.md`.

**Files changed** (all under `src/shared/packages/pyforge-doctor/` unless noted):
- `src/pyforge/doctor/sources/__init__.py` -- new `locate_checkout_script`, exported.
- `src/pyforge/doctor/sources/board.py` -- loader resolves from the checkout; re-points `REPO_ROOT`, `DREAMS_DIR`, `ARCHIVE_DREAMS_DIR`, `_PIXI_TASKS` at `target`; stale retired-console pragma and comment corrected.
- `src/pyforge/doctor/sources/factory.py` -- env-matrix loader resolves from the checkout, with the `sys.path` / `sys.modules` guards; its docstring names exactly those two guards.
- `src/pyforge/doctor/sources/ledger.py` -- the `head` probe and its WARN.
- `src/pyforge/doctor/score.py` -- the widened `_is_gather_failure`, with its docstrings.
- `tests/unit/test_sources_board_chain_layers_audit.py`, `test_sources_factory.py`, `test_sources_ledger.py`, `test_score.py`, `test_sources_registry.py` -- 22 new tests (probe-file tests with sensitivity twins for both loaders, the loader data-path test, the head WARN, the exception-evidence grading and its ordinary-WARN counterparts, the locator); no existing test touched.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` -- the three rows set to `resolved` in the file's own format.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- the surface-reconcile entry naming every governed path above; no baseline stamped.

**Review findings breakdown.** 30 findings from four layers (Blind Hunter 10, Edge Case Hunter 7, Verification Gap 3 and 0 gaps, Intent Alignment 10 divergences). Patches applied: 2 entries (5 findings) — high 0, medium 1 (`ARCHIVE_DREAMS_DIR` not re-pointed at `target`: BH1, EH1, EH5), low 1 (the env-matrix loader's docstring overclaiming its guards: BH2, IA-f). Deferred: 2 entries — the cannot-evaluate WARNs that still grade C (medium; BH4, EH2, EH6, VG2, IA-b) and `docs_currency` running the judged tree's declared generator (high, unverified; VG1); both are in the frontmatter `deferred` list with a `location:`. Rejected, each with its recorded reason (full text in the Review Triage Log):
- BH3, EH4, EH7, IA-i (the walk-up is unanchored): the intent specifies exactly this walk; reaching the judged tree needs it to be an ancestor of Doctor's own install.
- BH5 (duplicated `"exception"` literal; mixed axis): already tied by a test, no other producer; the mixed axis is by design.
- BH6, EH3, VG3 (head probe accepts any object or a nonexistent full SHA): still one WARN naming `head`, never the FAIL storm; no live caller passes `head`.
- BH7 (closed rows keep old prose): matches the file's own resolved-row format.
- BH8 (brittle tests, duplicate helpers): loud failure, developer-only, consolidation is more than a direct correction.
- BH9 (docs): the stale `fleet_scan` phrase is pre-existing and generated from `pixi.toml`; no doc states the old behaviour.
- BH10 (bundling, stale Code Map): the fix edits this build's spec.
- IA-a, IA-d, IA-e, IA-g, IA-h, IA-j, IA-c: the ACs name the library surface; the signature change has no other caller; the AC3 fixtures must stay; the mutation twins were settled by running the source reverts; the row closures and memlog entry are required.

**Follow-up review recommendation:** `false`. This pass patched 1 medium entry and 1 low entry (patched counts: high 0, medium 1, low 1); no high and fewer than two mediums, so the work has converged.

**Verification performed** (every verdict from the exit code, none through a pipe), after the last edit:
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` exit 0, 3183 passed, 1 skipped.
- `python scripts/spec_surface_reconcile.py` exit 0 ("every tracked file governed or allowlisted; no drift").
- `deferred-work-check`, `story-status-check`, `ledger-regression-check` and `lint-types` (`-e pyforge-guild`) each exit 0.
- Source-revert mutations, each failing its matching new test: the `fleet_scan.py` loader back to `target`, the env-matrix loader back to `target`, the head probe removed, `_is_gather_failure` back to atlas-only, and the `ARCHIVE_DREAMS_DIR` re-point removed. The tree was restored after each.
- Not run: `pr-preflight` (a push-time lane), the other stations' suites.

**Residual risks.**
- `locate_checkout_script` trusts the first ancestor of Doctor's own file that has `scripts/<name>`, as the intent specifies. A Doctor installed inside the very tree it judges would resolve to that tree's script; that tree already owns the environment Doctor runs from, so no new privilege is shown, but the ledger key's "no code" is stated more absolutely than the walk guarantees.
- `check_pixi_env_matrix` reports `pixi-env-matrix-stale` on this repo today because the Dream's matrix is older than `pixi.lock` (`scripts/pixi_env_matrix.py --check` agrees); unrelated to this story.
- `scripts/fleet_scan.py` prints `[fleet] ...` lines to stdout, which pollutes `--json` output of the layers command; unrelated, not recorded as a row.
- The two deferred entries above stay open.
