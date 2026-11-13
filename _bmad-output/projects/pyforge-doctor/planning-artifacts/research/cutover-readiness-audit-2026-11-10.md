---
chain: pyforge-doctor
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Doctor"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Doctor

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

## Doctor: A→B cutover readiness (read-only audit)

Path prefixes: `R` = `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes`; `D` = `R/src/shared/packages/pyforge-doctor/src/pyforge/doctor`; `T` = `R/src/shared/packages/pyforge-doctor/tests`; `S` = `R/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md`; `X` = `/tmp/claude-1000/-home-rxm7706--claude-spares-spare-nW1L3i/552e28f7-6060-4942-926f-c593d0973dbf/scratchpad/doctor`.

**Verdict:** not rebuild-ready. The Spec trails the code and tests, doctor's detectors pass without measuring (or fail) on a B-shaped tree, and the frozen-path guard cannot fire.

### MUST REFRESH (blocks cutover)
1. **`detectors-ci` on B proves nothing yet.** I ran the 29 doctor sources in `detectors-ci` in-process against two scratch trees.
   - Empty B tree: 27 exit 0 with nothing measured (14 "unevaluable" WARN, 11 vacuous OK, 2 empty); `spec-surface` and `docs-map-hygiene` FAIL. The aggregate maps WARN to `pass`.
   - Doctor-only tree at `src/packages/`: `spec-surface` 473 FAIL (Spec `surface:` names `src/shared/packages/…`), `deferred-work` FAIL (baseline file missing), `docs-map-hygiene` FAIL. `capability-effect` gives 120 WARN and passes; `bmad-drift` is unevaluable without `pyforge-marshal`.
2. **`frozen-path-changed` cannot fire.** It reads `docs/foundry/manifest.*` and states `rebuilding`/`moving`; the real file is `capability-ledger.yaml` with `mode`. With the ledger present it reported "no capability ledger found (pre-cutover)". It has no CAP of its own.
3. **Sequencing gap.** `detectors-ci` needs `pyforge.doctor` importable, else 29 `unknown` rows and exit 2. Cutover Launch engines are core, steward, marshal. Doctor also imports `pyforge.warden.engines` and six `pyforge.core` modules.
4. **Status markers are stale.** 36 shipped, 17 ready, 23 `in-progress` (a retired value), 5 `draft`, 12 with none. That is 57 of 93 CAPs without a shipped marker, while 171/171 stories and 54/54 epics are done. Code exists for ready/draft CAP-54, 69, 72–76, 77–81.
5. **Spec contradicts code and tests.** NFR-1 and Non-goals say no actuator and no file write. `doctor flags kill-switch` writes a flag file, and the read-only meta-test exempts it. That verb has no CAP in any Spec. The Spec says three verbs; the CLI has five. Two Open Questions are already decided in code (env-hygiene is always WARN; the fleet surface is a file).
6. **CAP text describes A's state, not behaviour.** CAP-1..76 date from the 2026-09-17 fold; only CAP-89..93 were re-derived.
   - CAP-17's "zero callers" case now has callers.
   - CAP-50/51/53 name `docs/specs/`, `gists/INDEX.md`, `docs/dashboard/kedro-viz/` (gone) and `bmad_drift_check.py --specs` (flag gone).
   - CAP-69 says "recorded date"; the code counts 30 `pixi.toml` commits against an archived Dream.
   - Only 7 of 93 CAPs name a test.
7. **Tests are mostly A-tree assertions.** 2,164 test functions; 1,247 (58%) sit in 43 `live_tree` modules that read A's tree. 41 files use `parents[N]`; about 38 skip sites skip silently off the monorepo. 11 `test_live_tree_*` tests assert A's state. There is no conformance or integration lane.

### SHOULD RECHECK
- **Capability ledger.** CAP id sets are equal (93). The "97" are four Constraint bullets (`S:351,364,366,367`). All 94 rows are `rebuild`, including tombstone CAP-33, the archived `sibling-dreams-drift:CAP-1` (duplicate of CAP-71), and A-bound CAPs 37–41, 45–53, 55–56, 60–61, 65–68, 70–71, 82 (INFERRED). 16 headings differ; ledger `updated` 2026-11-01 is older than the Spec's 2026-11-05.
- **No CAP in any live Spec:** sources `chain-layers-audit`, `platform-policy-suite`, `bmad-render-config-ambiguity`, `fold-complete`, `frontmatter-duplicate-keys`; scripts `mason_cfe_surface_check`, `memlog_fidelity_check`; MCP tools `start_scan`/`get_scan`/`run_scan`.
- **Doctor CAPs realized outside the Spec `surface:`:** `scripts/detectors.py`, `fleet_picture.py`, `deferred_work_promote.py`, `spec_surface_check.py`, `fr_baseline.py`.
- **Bridges (all targets exist):** warden import; atlas axes through CFE `.claude/tools/conda_forge_server.py` plus seven `.claude/scripts/conda-forge-expert/*.py`, not `pyforge atlas`; `steward ci status --json`; `.pixi/envs/platform-ci-test` pytest; repo scripts executed (`fleet_scan.py`, `pixi_env_matrix.py`, `docs_*.py`). `station_port` has 0 uses. `django_pyforge.flags` is imported in the CLI; there is no `dashboard/`.
- **A-tree literals in src:** 269 (62 `_bmad-output`, 41 `docs/dreams`, 20 governance, 19 `pyforge-<station>`, 10 `recipes`, 8 package root). Repo identity is hard-coded: Pages URL, the OpenTeams sibling repo, schema `$id urn:local-recipes:…`.
- **Station list sits in three places:** `pyforge.core.roster`, `guild-roster.json`, a fallback tuple.
- **Baselines:** five files, keyed on eight slugs and A sha `e630e43330`. The spec-surface baseline holds 6,578 paths, 93 orphaned, plus one orphan Spec key. The deferred-work baseline was last committed 2026-08-28.
- **Traceability:** 13 folded CAPs carry 23 bare `CAP-n` in pre-fold numbering. Source comments hold 306 bare CAP refs, 12 FR ids outside FR-1..24, and 30 non-doctor story ids.
- **Chain dates:** PRD, spine and epics all read `updated: 2026-11-05`. No arrow points at a missing CAP; about 71 CAPs have no FR. No memlog entry postdates the last re-derive.
- **Deferred work:** 33 open (30 low, 2 medium, 1 partial). None names B portability. 14 recommended follow-up reviews never ran.
- **Story specs** 24.2 and 34.2 read `in-review`.

### NICE TO UPDATE
- `SKILL.md` was compiled at `865b95dc95` (2026-08-25, 269 src commits ago): anchors are off, and it omits `flags` and the sources dispatcher.
- README says "95 stories, 22 epics, 22 sources".
- The Frame's four bullets name no sources dispatcher, exit domain or bridges.
- `check-layout` and `dashboard-drift` are tombstone detectors for retired A files.
- `scripts/bmad_drift_check.py` and `factory.py` both define `classify`, `_classify_tier`, `ground_truth`, `_is_kept_tier`.
- `pyforge.doctor.sources.fleet_scan` is a phantom module name in help text and evidence.
- CAP-11/20/46 cite `-e local-recipes`. Headings for CAP-45/47/51/65 are truncated. There is no Epic 52.
- These match: `judgement-vocabulary.md` exit table and `verdict.py`; schema enums and models (45/3/3); 38 cited test ids resolve; TODO/FIXME count is 0.

### Evidence
| Finding | path:line | V/I | How |
|---|---|---|---|
| WARN maps to `pass` | `R/scripts/detectors.py:378-381` | VERIFIED | read |
| Empty-B probe: 27 exit 0, 2 FAIL | `X/probe.py` on `X/treeE` | VERIFIED | ran |
| Doctor-only probe: 473 FAIL | `X/treeP`; `S:2-16` | VERIFIED | ran |
| Frozen-path reads `manifest.*` | `D/sources/frozen_path.py:80-83` | VERIFIED | read, probe |
| Doctor unimportable gives 29 unknown | `R/scripts/detectors.py:360` | VERIFIED | read |
| Doctor not a Launch engine | `R/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md:63` | INFERRED | read |
| Marker counts | `S:69-345` | VERIFIED | script |
| No-actuator rule vs write | `S:358,371`; `D/actuators/flag_kill_switch.py:32`; `D/__main__.py:314-319`; `T/meta/test_read_only_guard.py:46` | VERIFIED | read, `--help` |
| Stale Open Questions | `S:400,402`; `D/checks/env_hygiene.py:94`; `D/fleet_surface.py:84` | VERIFIED | read |
| CAP-17 callers exist | `S:119`; `R/src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_low_risk.py` | VERIFIED | grep |
| CAP-69 mismatch | `S:273`; `D/sources/pixi_currency.py:28-30` | VERIFIED | read |
| `live_tree` split | `R/pixi.toml` task `pyforge-doctor-test`; `R/src/shared/packages/pyforge-doctor/pyproject.toml:61-63` | VERIFIED | script |
| Ledger rows | `R/docs/foundry/capability-ledger.yaml:39-44,5587-5592` | VERIFIED | script |
| Atlas bridge is CFE | `D/sources/atlas.py:163-168` | VERIFIED | read |
| Warden, django_pyforge imports | `D/sources/warden.py:84`; `D/__main__.py:901` | VERIFIED | grep |
| Station fallback tuple | `D/sources/one_chain.py:129` | VERIFIED | read |
| Pages URL | `D/sources/pages_liveness.py:46` | VERIFIED | read |
| Baseline orphans | `R/scripts/.spec-surface-baseline.json` | VERIFIED | script |
| Skill provenance | `R/.claude/skills/pyforge-doctor/0.1.0/pyforge-doctor/metadata.json` | VERIFIED | `git log` |
| README counts | `R/src/shared/packages/pyforge-doctor/README.md:10` | VERIFIED | read |

### NOT CHECKED
- No test or detector was run on A. The probe used scratch git trees and the guild env's python, without `pixi run`.
- Coverage was not measured. The floor is the fleet default (unit above 80% on touched modules); doctor has no override.
- The 20 script detectors got a literal scan only, no probe.
- Runtime and opt-in sources were not probed: `ci-pause-drift`, `pages-liveness`, `sibling-dreams-drift`, `bmad-method-version-drift`, `due-for-verification`.
- I read intent against code for the 17 ready CAPs, CAP-71..93 and about 15 shipped ones; the rest were checked by script only.
- Test bodies, the Dream body (3,144 lines) and the portal beyond `mcp_asgi.py` were not read.
- Duplicate script/source function bodies were not diffed.
