---
chain: pyforge-marshal
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Core, testing kit and host"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Core, testing kit and host

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

## Kernel + host cutover-readiness audit (A at `82a2b18828`, B at `origin/main` `a762a14`)

**Verdict:** Not ready. B's core is a 7-module snapshot of A at PR #1344. A's core has since become a 17-module package that the core Spec describes about a quarter of, and both Launch stations import modules B does not have.

### MUST REFRESH (blocks cutover)

1. **Core drift since the pin.** 157 commits touch `pyforge-core` (69 are `wip:` checkpoints; 50 touch `src/`); 44 files, +5626/−359. Four modules are new since the pin: `flags.py` (579 LOC), `preserve_refs.py` (1217), `league_measure.py` (105), `roster.py` (43). B lacks 10 A modules: those four plus `assertion`, `atomic_write`, `client`, `landing_evidence`, `published_loop`, `report`.
2. **Launch stations import what B lacks** (non-test imports):
   - steward: `flags` 27, `preserve_refs` 10, `atomic_write` 9, `roster` 1.
   - marshal: `preserve_refs` 46, `flags` 19, `atomic_write` 10, `landing_evidence` 10, `client` 6, `published_loop` 3, `roster` 3, `assertion` 2.
3. **Divergence in the 7 rebuilt modules** (A today vs B):
   - `process`: A adds `BytesProcessResult`, `PosixProcess.run(env=)`, `run_bytes`, `process_start_time` (on `ProcessPort` too). `is_alive` now returns False for a non-leader thread id.
   - `dispatch`: A adds `NOUN_ALIASES`, `FRONT_DOOR_ENVIRONMENT_FLAG_KEY` and the roster-aware not-installed refusal (CAP-11); it now imports `roster` and `flags`. B still carries `PREPARATORY_UNINTROSPECTABLE['atlas'] = 'spec-25-3-…'`, which A corrected to `spec-24-3-…`.
   - `cutover_root`: A composes `flag-overlays.json` per `PYFORGE_ENVIRONMENT`; B reads the raw `defaultVariant`.
   - `errors`, `hooks`, `station_port`: cosmetic only. `verdict`: one error-message text differs.
4. **Oracle coverage on B is thin.** All 17 `k-core-*` nodeids still exist in A under the same names. Sixteen are byte-identical across pin, A and B; `k-core-parity-verbs` was rewritten on B. A core has 366 test functions in 26 files; B has 18 in 6. B has no tests for `process.py` or `hooks.py`, and no leaf-constraint or sole-ownership meta-tests. B's `ab-sync.md` pass rows date from 2026-09-14.
5. **Case-list count is wrong in both copies.** Both say 38 rows ("16 core"); each file has 40 `| k-` rows (17 `k-core-*`, 18 in the core slice).
6. **Core Spec covers 23% of core.** 3323 of 4299 LOC (11 of 17 modules) are described by no core CAP. The Spec still says "six primitives", "not a plugin system", "not the roster, yet", and lists Q1–Q3 open, while `roster.py`, `hooks.py` and the separate kit exist. No CAP carries a `(ready …)` or `(shipped …)` marker, though stories 14.1–14.4, 52.1–52.2, 63.1, 71.1 and 110.1 are `done`. CAP-10 names `coverage-gates.yml`, deleted 2026-10-27. CAP-9 pins the kit exemption to `dependencies == []`, which was retired 2026-09-30.
7. **Ledger gaps.**
   - Core is present as `pyforge-core:CAP-1..11`, station `pyforge-marshal`, all `rebuild`. No row in the whole ledger carries a `verified-in-foundry` claim.
   - `spec-feature-flag-governance` (7 CAPs, governs `core.flags`) has zero rows; the detector globs only `planning-artifacts/specs`.
   - Ledger `pap:CAP-1..20` are the Unifying CAPs. The Spec's own `pap:CAP-1..6` (the host itself) have no distinct rows: 26 headings, 20 rows.
8. **Testing kit is `A-only` (expiry 2026-12-31) but Launch suites need it.** 22 steward and 23 marshal test files import it. The kit's own suite imports `django_pyforge`, and `cfe_surface.py` hard-codes `.claude/skills/conda-forge-expert`.
9. **Frames have forked, with A ahead.** A edited Frames on 2026-09-14, 09-16 and 10-08, after B's last commit, despite the writer lock naming B.
   - Company Frame: A has `type: frame`, `identifier: pyforge/company`, `name: PyForge`, `maintainer` as a list, no `owner`. B has `frame [0.3]`, `identifier: pyforge`, `name: pyforge`, `owner: steward/guild`, scalar `maintainer`. Bodies are identical.
   - `frames/README.md` differs by 103 lines; all 8 station Frames differ.
   - A has no `docs/foundry/PIN.md`. B carries two pins: `PIN.md` at `9e9f6854` and `SPEC.md` at `08f75c2b`.

### SHOULD RECHECK

- **`pyforge.cutover_root` switches nothing.** The only value readers are:
  - `core/cutover_root.py:57`, the reader itself;
  - `django_pyforge/flags.py:195-205`, called only from platform tests;
  - `steward/cutover.py:241-290` (writes it) and `:343` (echoes it).
  
  Every other hit calls `resolve_flags_path` to locate the tree. B's `flags.json` entry has no `metadata` block.
- **Kernel guarantees exclude steward.** `test_process_sole_ownership` puts six stations out of scope, and `test_exception_root_sole_ownership` excludes doctor and steward. Steward has 20 modules importing `subprocess`, 26 builtin-rooted exception classes and zero `PyforgeError` imports.
- **Meta-tests bound to A's layout** (break or go vacuous on B): `test_conformance_lane_wired`, `test_preserve_refs_sole_grammar` (`parents[6]`), `test_cli_parity_matrix` (`_bmad-output/projects`), `test_atomic_write_sole_ownership:369`, `test_process_sole_ownership:289-328`, `test_plugin_registration_conformance`, both `*_ci_trigger_companion` tests, `test_roster.py` (needs `.claude` and `docs/governance/guild-roster.json`), and `test_flags.py`'s `_SHIPPED_CLOCKS` table of all 103 flags.
- **Portability literals that would break on B:** `league_measure.py:18` (`_bmad-output/…/measure-catalog.md`; the module has no importer), `preserve_refs.py:75` (`docs/governance/preserve-purge-list.json`; `load_purge_list` does not guard a missing file), `landing_evidence.py:158-170` (three A commit SHAs). Legitimate: the cutover variants, `LOCAL_DEV_RELATIVE`, the `urn:local-recipes:` `$id`, `dispatch.py:148` `parents[4]`.
- **The leaf is not pure stdlib in behaviour.** `flags.py:408,424-426` loads OpenFeature through `importlib`. The core env has no OpenFeature, so that path's test is skipped there (inferred).
- **Platform reaches `pyforge.*` outside the carve-out by dynamic import:** `config/asgi.py:224`, `mcp_host/app.py:48,61`, `config/settings/base.py:57`. The carve-out is the four allowlisted files (`graphql.py`, `pipeline.py`, `source.py`, `test_github_metrics_dlt.py`); `pipeline.py:12` imports the private `_default_transport`. `django-atlas/board.py:18-20` imports `pyforge.steward.dashboard`.
- **The 87 rows expiring 2026-12-31** got a blanket date on 2026-09-13. By spec: unifying-strategy 15, bmad-method-core-upgrade 9, secure-live-dashboards 8, pyforge-warden 8, testing-charter 5, jira-github-projects-sync 5, local-ocp-hybrid-environment 5, platform-fifteen-factors 5, scratch-worktree-lifecycle 5, golden-path-conda-blind-spot 5, python-foundry-cutover 4, wagtail-corporate-brain 3, ocp-as-a-portability-profile 3, suite-scaffold 3, package-inventory-eligibility 3, platform-dev-boots-local 1. The detector checks only that an expiry is present. With B idle for 57 days the date is not credible (inferred).
- **Package `pixi.toml` floors.** Core and kit declare `python >=3.12`; pyproject says `>=3.14`, and `process.py:287,339,363` uses 3.14-only `except A, B:` syntax.
- **Portals declare only `django`** but import `pyforge.core` or `pyforge.<station>` (django-pyforge, -warden, -atlas, -herald, -mason).

### NICE TO UPDATE

- Core README and `__init__` docstring omit 10 modules. Core and B core both read `0.1.0`.
- Kit README omits `branch_diff_guard` and `cfe_surface`; the charter Spec surface comment still says "not yet created".
- No core module defines `__all__`. No station imports an underscored core name.
- Core and kit have no coverage floor (their tasks run without `--cov`). Core mypy is strict with 0 overrides; kit is non-strict with 0 overrides.
- `src/platform/uv.lock` is a 3-line stub saying `>=3.12`; `utility/requirements-*.apt` are template leftovers.
- Flags: 103 total (52 on, 50 off, 1 string). None is past due or due within 30 days; the earliest `cleanup_by` is 2027-01-24. 51 have no clock. Every key has a runtime reader, and no code-read key is missing from the tree.
- Host: 224 py files, 46.6k LOC (9.5k non-test), 1172 test functions; py3.14; PostgreSQL 17 held everywhere.
- Portals (non-migration LOC): pyforge 8908, warden 2254, herald 657, marshal 256, atlas 214, mason 213, doctor 202, scribe 161, steward 106. All have zero in-package tests, version 0.1.0 and no mypy config. Owner is `spec-pyforge-unifying-strategy` (ledger `pap:CAP-1`, `pap:CAP-3`, A-only 2026-12-31).

### Evidence

| Finding | Where | Status | How |
|---|---|---|---|
| 157 commits, +5626/−359 | `git log`/`diff --stat 9e9f6854..HEAD -- …/pyforge-core` | VERIFIED | git |
| API and body divergence | `/tmp/kaudit/api.py`, AST dump diff | VERIFIED | ast |
| 17 nodeids exist; 16 identical | `/tmp/kaudit/cases2.py` | VERIFIED | ast across pin, HEAD, B |
| Case-list 40 rows, not 38 | `case-list.md:57`; `grep -c '^\| k-'` | VERIFIED | grep, A and B |
| Station import counts | `/tmp/kaudit/imports.out` | VERIFIED | ast scan |
| 77% of core outside core CAPs | core `SPEC.md` CAP-1..11 vs `wc -l` | VERIFIED | read + count |
| CAP-10 stale workflow | `SPEC.md` CAP-10; deleted in `7e2ab1cb17` | VERIFIED | `git log --diff-filter=D` |
| Ledger scope, `pap:` collision | `capability_ledger.py:38,75,274` | VERIFIED | read + yaml |
| Kit use and mode | AST scan; ledger `pyforge-testing-charter:CAP-3` | VERIFIED | ast + yaml |
| Frame fork | `diff` A vs `git show origin/main:` | VERIFIED | diff |
| `cutover_root` readers | `git grep` excluding md | VERIFIED | grep |
| Steward exclusions | `test_process_sole_ownership.py:124-135`; `test_exception_root_sole_ownership.py:69` | VERIFIED | read |
| Platform dynamic imports | `/tmp/kaudit/plat.py` | VERIFIED | ast |
| Flag clocks and readers | `/tmp/kaudit/flags.py`, `flagread2.py` | VERIFIED (exact-string match) | json + grep |
| OpenFeature path untested in core env | `test_flags.py:1290`; `pixi.toml:3177-3181` | INFERRED | read |
| Expiry not credible | blame `0d9d6d51b7`; B idle | INFERRED | judgement |

### NOT CHECKED

- No suite, detector, mypy or ruff was run. Test counts are `def test_` functions by AST, not collected cases.
- B's steward and marshal were not diffed. Station Frames: all 8 compared by diffstat, 1 read.
- The core memlog (851 lines) was grepped, not read.
- CAP success clauses were checked for path and name existence, not behaviour.
- The architecture spine was grepped only.
- django-* internals were not reviewed beyond imports, deps and size.
- The flag reader check would miss a key built by concatenation.
- Platform dynamic imports cover `import_module`, `find_spec`, `__import__` and `import_string` only.

Scratch scripts are in `/tmp/kaudit/`.
