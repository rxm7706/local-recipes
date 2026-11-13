---
chain: pyforge-marshal
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Marshal"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Marshal

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

## Marshal A→B cutover audit (read-only)

**Verdict: NOT READY for a from-Spec rebuild of the full station.** The 9-row thin oracle is intact; the Spec does not describe the 114.6k-LOC code as built.

Corrections to pre-measures: CAP markers are shipped 150 / ready 49 / none 104 / retired 0 (the "2 retired" were title words). Ledger is 525 done / 2 backlog / 1 blocked.

### MUST REFRESH (blocks cutover)
1. **Status markers unusable.** 104 CAPs carry no marker. All 49 `(ready)` CAPs (244–292) have every citing story `done`. The unmarked set mixes built work (CAP-159–170, Epic 22 21/21 done; CAP-298–303, Epic 113 19/19 done) with never-built or retired work (CAP-80–83).
2. **Retired artifacts specced as live, all `rebuild` in the ledger.** CAP-84–86 and 93–96 `(shipped)`, plus 80–83, 121, 229, 230, describe the Guildhall console (`data.js`, `generate.py`), deleted 2026-08-25; `retired-console-check` reds its return. CAP-55, 68, 83, 121, 230 name `scripts/forward_dependency_check.py` and `dashboard_drift_check.py`, deleted 2026-08-10.
3. **Public contract is not in the Spec.**
   - 26 of 66 verb paths are never named in SPEC.md: `gate evaluate`, `factory attach|resume|dispatch-attach`, five `deploy` verbs, all seven `adapters` verbs, `seed kit|accept`, `context refresh|retrieve|advisory|pack`, `benchmark structure-graph-dispatch`, `preserve list|push|retire`.
   - 91 flags are absent. The 11 `marshal-mcp` tool names have 0 hits.
   - Source defines 333 distinct `MRS-*` codes; SPEC names 32 (PRD 23, spine 10, epics 62).
   - 10 of 303 CAPs name a test. 152 name no marshal verb, code, path or identifier.
   - 53% of LOC sits in modules the Spec names by file. 17 modules ≥400 LOC (13.2k) appear in neither SPEC body nor companions: `adapters/vcs_git.py` 2095, `dispatch_verify.py` 1845, `core/chain_regen.py` 1438, `cli/drain_plan.py` 960, `core/dispatch_landing.py` 872.
4. **A's tree and remote are hard-coded; the cutover flag is unread.**
   - `_FORGE_REPO = "rxm7706/local-recipes"` in three modules plus `cli/watch.py`; no policy field.
   - Marshal imports only `resolve_flags_path`, never `read_cutover_root`. The cutover Spec says the flip switches loop-home remotes; marshal's SPEC, glossary and companions have 0 cutover/foundry hits.
   - `Path(__file__).parents[8]` as repo root ×3; `("src","shared","packages")` ×4.
   - `dispatch_land.py` imports `pyforge.doctor.sources.chain` via `sys.path`, the one station-port bypass. On ImportError it degrades to non-blocking MRS-DISP-047.
5. **Capability ledger.** Id set matches exactly (303 = 303). 144 headings are junk (133 `"from spec-…"`, 11 one-letter) and CAP-252 is stale. 62 rows from 9 archived specs duplicate folded CAPs 21–24, 64–66, 75–79, 102–106, 159–170, 174–197, 220–228. 11 `pyforge-core` rows carry `station: pyforge-marshal`. The 5 A-only rows (testing-charter, expiry 2026-12-31) cover `pyforge.testing_kit`, which marshal's tests import 26 times.

### SHOULD RECHECK
- **Hollow oracles.**
  - `test_no_loop_home_run_state_read.py` exempts every line holding any string constant, so it cannot fire. `cli/watch.py` reads `~/.bmad-loops` untagged and ignores the root override `cli/init.py` honours.
  - `mcp/tools.py` has 11 TOOL_SPECS; `mcp/server.py` registers 8. The three preserve tools are unreachable, and the `k-marshal-tool-parity` test never checks the server.
  - Seed exit codes 5 and 10 are outside `GUARDED_EXIT_CODES`, so `main` returns 2. Tests assert 10 at handler level only.
- **No package-local/live-tree split for marshal.** `pyforge-marshal-test` has no `live_tree` marker; Story 117.4 covers steward and doctor only. 56 of 274 test files resolve the repo root. About 17 `pytest.skip` sites fire when a live-tree file is absent, which false-greens on B.
- **Stale CAP text.**
  - CAP-299 cites a renamed test.
  - CAP-17 says `genesis_version`; code has `seed_model_version`.
  - CAP-18 names `--template <url>`; no such flag.
  - CAP-166 says "provisional `marshal factory dispatch --fleet` or `marshal drain`"; the verb is `factory drain`.
  - CAP-159 says `bmad-dev-auto`.
  - CAP-51 `allow_ancestor_baseline` and CAP-199 `story_blocked_reason` are nowhere in the repo.
- **Harness.** `>=0.11.0,<0.13` agrees across code, pyproject, package pixi, spine, PRD and estate catalog; 0.12.0 is installed. SPEC.md never states it, and root `pixi.toml` has a floor only. The Claude Code 2.1.271 floor lives in `core/challenge.py` and CAP-298. Profiles were verified 2026-08-27 and 2026-10-04; `devin.toml` is `verified = false`. The cost catalog has 8 models, newest note 2026-11-04; openai and google rows are undated.
- **Flags.** None overdue: 37 are due 2027-01-24. 9 are default-off with no cleanup date: `preserve_refs` and six `egm_*` off everywhere, `verify_fix_loop` off in production, `landing_ci_pauses` dev-only.
- **Chain.**
  - Spec, PRD, spine and epics are all `2026-11-05`; 245/245 FR arrows resolve.
  - Two memlog entries post-date the last render. The 2026-11-06 one says `start_loop` on marshal's face now runs `marshal factory dispatch`; SPEC has 0 hits.
  - Renders since 2026-11-04 are anchored substitutions, not full re-derives.
  - Open keys: 108.2 backlog (33 NFRs lack arrows), 110.38 backlog, 33.11 blocked on "the Foundry cutover flag".
  - Story-spec drift: `spec-74-2` `in-review` and `spec-46-2` `backlog` against ledger `done`; orphans `spec-33-8-wave-probe-a`, `spec-33-9-wave-probe-b`; 55.1 has no tracked spec.
- **Deferred work.** 633 rows, 359 open (129 medium, 230 low, 0 high). Cutover-relevant: DW-FU-4-4-2, DW-FU-53-2-2, DW-FU-22-9-2, DW-FU-46-1-5.

### NICE TO UPDATE
- SKILL.md was compiled at `03a7aff5d9`; 8 commits (+1490) since. `run_challenge` is cited at L772, real L1029; `--section`/`--dream-section` are missing. Verb list and exit domain hold.
- `marshal-run-watch` (2026-09-15) uses `-e local-recipes` and hand-reads `~/.bmad-loops`.
- README covers seed only. The Frame is 4 bullets (2026-09-16).
- Package `pixi.toml` says python `>=3.12`; pyproject says `>=3.14`.
- epics.md frontmatter says 110 epics / 508 stories; real is 111 / 528. It has 692 bare `CAP-n` cites and 140 into 29 archived specs.
- Loose `PRD.md` and `architecture.md` in the project dir are the old local-recipes factory docs.
- `integration-layers.md` says caveman 2.4.0; installed is 4.0.0.
- `adapters/published_plane.py` is unreferenced. Source has 0 TODO/FIXME.

### Evidence
| Finding | path:line | V/I | How |
|---|---|---|---|
| Markers 150/49/104 | SPEC.md:231–1137 | V | parse script |
| Ready CAPs all done | epics.md + ledger | V | CAP→story script |
| Console deleted | docs/dashboard/README.md:3; pixi.toml:1755 | V | read, `git log --diff-filter=D` |
| Verbs unnamed | argparse walk vs SPEC | V | env python walk, `--help` |
| 333 vs 32 codes | core/findings.py; SPEC | V | grep -o, sort -u |
| `_FORGE_REPO` | dispatch_land.py:72; cli/deploy.py:408; cli/land.py:166; cli/watch.py:661 | V | AST literal scan |
| Cutover flag unread | cli/preserve.py:10; cli/retrofit_flags.py:28; cutover SPEC:123–124 | V | grep |
| `parents[8]` | cli/land.py:1377,1448; cli/deploy.py:3598 | V | grep |
| Doctor import | dispatch_land.py:481–484 | V | read |
| Ledger headings | capability-ledger.yaml:1661 | V | yaml diff |
| Guard vacuous | test_no_loop_home_run_state_read.py:26–35,57; cli/watch.py:586,596,694 | V read / I outcome | not run |
| MCP 11 vs 8 | mcp/tools.py:20–83; mcp/server.py:27–62 | V | read |
| Seed exit clamp | seed/errors.py:33; cli/main.py handler relay | I | read, not run |
| Renamed test | test_factory_challenge.py:691 | V | grep |
| Harness range | harness_bmadloop.py:1129–1131; spine:544; estate:396 | V | grep |
| Case-list nodeids | test_cli.py, test_verdict.py, test_cli_tool_parity.py | V | grep `def` |
| Test counts 7776/370/42 | tests/{unit,meta,integration} | V | grep `def test_` |

### NOT CHECKED
- No tests, detectors or marshal verbs were run; only `--help` and a read-only argparse walk.
- Close reading: CAP-298, 300, 301, 303 in full; 24 shipped success clauses skimmed; 34 mechanism greps. The 49 ready CAPs were checked by reference resolution, not read in full.
- "Named" and "no-anchor" shares are regex heuristics.
- The 2334-line memlog (tail only), 531 story specs (frontmatter only), test assertion quality, B, and `django-marshal` beyond tool names were not read.
- Catalog prices were not verified (offline).

Scratch data: `/tmp/claude-1000/-home-rxm7706--claude-spares-spare-nW1L3i/552e28f7-6060-4942-926f-c593d0973dbf/scratchpad/marshal_audit/` (`unresolved.txt`, `cli_tree.json`, `caps.json`). Another agent overwrote my first `caps.json` at the scratchpad root; parallel audits need per-station subfolders.
