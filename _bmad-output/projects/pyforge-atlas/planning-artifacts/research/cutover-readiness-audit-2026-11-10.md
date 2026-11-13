---
chain: pyforge-atlas
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Atlas"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Atlas

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

ATLAS — A→B CUTOVER READINESS AUDIT (read-only; nothing run under pixi, nothing edited)

Prefixes: ROOT=/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes · PKG=ROOT/src/shared/packages/pyforge-atlas · PLAN=ROOT/_bmad-output/projects/pyforge-atlas/planning-artifacts · SPEC=PLAN/specs/spec-pyforge-atlas

VERDICT: Not rebuild-ready. SPEC.md is in sync with its memlog (both 2026-11-05), but it does not describe the code: 14 "shipped" CAPs have no code, four companions froze 2026-07-29 at 7 pipelines/86 datasets (code: 12/147), the parity oracle is hand-authored seeds, and the package still reads A's conda-forge-expert tree.

MUST REFRESH (blocks cutover)
1. CAP-18..31 (Unity + Wasm satellites) are `(shipped 2026-09-09)` and ledger `rebuild`, while SPEC.md:148 says "neither has epics/stories or code". Zero src hits for WASI, FastAPI, dlt, Marquez, OIDC, xlsx, Trusted Committer, attestation; `apps/`, `deploy/` and `pixi run build` do not exist.
2. CAP-7 is `shipped` but its success never happened: `human_sign_off` is still None, 15 parity fixtures are stamped `shape-only-seed-B2-needs-B4-recapture`, DW-B1-1/B4-1/B4-2/B4-3 are open. `parity-diff` green is not legacy parity.
3. CAP-1 success says "exactly seven" pipelines; registry has 12 (9 in `__default__`). catalog-contract.md says 7 pipelines × 86 datasets; test pin is 147. gate-contract.md lists "seven gates" at pre-move `tests/<x>` paths. Spine AD-3 heading still says seven; its own later sections say "eleven" then "nine" of twelve.
4. CAP-51 and CAP-52 are hollow ("the absorbed Spec's success clause is the record"). Their code lives in A-root `scripts/`, not the package. CAP-43, 54, 55, 56, 70, 71 cite companions that exist only under `archive/`.
5. Legacy carry-overs still read by package code: `seed_root` defaults to `.claude/skills/conda-forge-expert/data` (3 catalog seeds); `views/` loads CFE scripts and queries `cf_atlas.db`; `scan_submit.py` and `refresh.py` shell to `-e vuln-db` / `.claude/scripts/conda-forge-expert/env_inspect.py`. CAP-44/45 name `cf_atlas.db` as the query surface while CAP-36 forbids it.
6. live-sources.md floors are "same-day legacy `cf_atlas.db` figure" (1.1 GB at `.claude/data/conda-forge-expert/`, refreshed 2026-11-05). B has no legacy DB, so CAP-64/65 attended success cannot be re-measured.
7. Not named by the Spec: all 13 MCP tool names, CLI verbs `ipython`/`package`, 7 of 11 flag keys (including `pyforge.atlas.live_public_sources`, which gates "live by default": default off, production overlay off, off when no flag tree), 65 of 147 catalog datasets, 30 of 40 modules over 300 LOC, env vars `PYFORGE_ATLAS_SEED_ROOT`, `_LOCAL_RECIPES_DIR`, `_CFE_SCRIPTS_DIR`, `_LOCAL_RECIPES_REPO_SLUG`, `_SCOPE`, `_LIVE_BOKEH_URL`.
8. PRD FR ids collide: satellites reuse FR-1..60 and FR-1..17 with no CAP arrow (78 headings); Story 41.2 (backlog) is the fix. SPEC CAP-18..31 success clauses cite those local ids.

SHOULD RECHECK
- 8 of 9 `(ready)` CAPs (61–67, 69) have every story done. Marker is stale or held by an unrecorded attended leg (CAP-66: no Basilisk token, DW-atlas-36-1-1). Only CAP-68 is open (Story 36.3 blocked, no steward export).
- Ledger: CAP id sets equal (72 = 72; the 76 = 72 + 4 open-question bullets for CAP-62/63/66/68). 6 headings drifted (CAP-21, 22, 23, 25, 29, 59). The 3 A-only rows duplicate `pyforge-atlas:CAP-58..60` (mode `rebuild`); the archived path exists but its body is "Derived body disposed", headings are empty, and no story or Dream line carries the 2026-12-31 expiry.
- Story ledger is 155 done, 3 backlog (41-2, 41-3, 42-4), 2 blocked (24-2 attended Artifactory credentials; 36-3). The pre-measured "2 backlog" misses 42-4, whose key contains "retro" (retrofit). Epics 24, 36, 41, 42 each wait on exactly those stories. 36-3 has no story spec.
- CAP-72 "from conda-forge": the `pyforge-atlas` env lock takes git-pkgs 0.21.0, kedro-skills, opengrep from `SelfExplainML`. wasm build uses `/opt/node22/bin`, npm and extensions.duckdb.org; `package-lock.json` is gitignored.
- No atlas live-tree split: Story 117.4's `live_tree` marker exists only for steward/doctor; atlas tests use no `slow` marker either (`-m "not slow"` is a no-op). 44 of 190 test files name paths outside the package; all 5 meta files read planning artifacts, pixi.toml, workflows, `.claude/skills`, django-atlas or pyforge-doctor src.
- Gates `dashboard-dryrun`, `dashboard-serve`, `publish`, `publish-range`, `vizro-ai-dryrun`, `wasm-build`, `wasm-smoke` sit in the `local-recipes` feature; SPEC.md:307, 399, 556 cite `-e local-recipes`.
- Would-break literals: `query_plane_boot.py:79`, `dashboard/identity_gist.py:204`, `dashboard/factory_status.py:58,63` (reads `_bmad-output`), `conf/base/globals.yml:165,187`, CAP-69's "member is `src/shared/packages/pyforge-atlas`". Legit: package-relative `parents[4]`, User-Agent, `rxm7706/about` (a data source).
- Direct cross-station import: `pipelines/universal_sbom/gate.py:118-171,251` imports `pyforge.warden` (declared optional `[gate]` extra). AD-1 scan: 0 violations. Django imports in atlas: 0. `semantic/query_helpers.py:14` imports pandas against the subtree "pure Ibis" rule.
- Data root resolved in four places (globals.yml, `admission.py:296`, `dashboard/data.py:141`, `tools/bootstrap.py:95`); Spec states precedence only in CAP-69.
- `views/` (792 LOC, CAP-44..47) has no runtime importer: tests only.
- Deferred work: 137 open of 280 (25 low, 3 medium, 109 with no severity field, some titled HIGH). Touching sources/Pages/oracle: DW-B1-1, B4-1..6, B5-1..3, B8-1/3, DW-G2-1, DW-12-2-1..6, DW-atlas-36-1-1, DW-atlas-27-1.

NICE TO UPDATE
- Subtree AGENTS.md (verified 2026-09-06): binding Spec path is archived; `tests/catalog/…`, `tests/fixtures/parity/`, `tests/fixtures/credentials/` do not exist; says fastmcp, code loads the official `mcp` SDK; `kedro-test` is now the full suite.
- 86 of 109 `tests/…` citations inside the package point at the pre-`tests/unit/` layout; 123 `spec §` citations point at the archived intake spec.
- SKILL.md: every line citation checked resolves; one scoped commit since. context-snippet and root AGENTS block list 11 of 13 tools.
- Frame: 4 bullets; names `cf-atlas-legacy`; silent on env, data root, flags, exit domain.
- SPEC.md:921,953,1064 still say "32 stories", "status: shipped", Story 25.3 "backlog". PRD/spine `updated` 2026-11-05 are 16–17 re-stamps; `currency_review` 2026-08-01/02.
- `observability.py:84` PRODUCER URL path does not exist; ledger header says `-e local-recipes sprint-ledger-sync`; `tests/durations/pyforge-atlas.json` cited by CI is absent.

EVIDENCE
| Finding | path:line | V/I | How |
|---|---|---|---|
| Satellites "no code" yet shipped | SPEC/SPEC.md:148, 209-250 | VERIFIED | read + grep src |
| Parity seeds, no sign-off | PKG/tests/unit/parity/fixtures/*; PKG/src/pyforge/atlas/parity/evidence.py:51,64 | VERIFIED | grep |
| 12 pipelines, 9 default | PKG/src/pyforge/atlas/pipeline_registry.py:10-17; SPEC/SPEC.md:160 | VERIFIED | read |
| 147 datasets vs 86 | PKG/tests/unit/catalog/conftest.py:106-120; SPEC/catalog-contract.md:22-33 | VERIFIED | yaml count |
| Companions frozen 2026-07-29 | SPEC/{catalog,gate,degradation}-contract.md, signals.md | VERIFIED | git log |
| Hollow CAP-51/52 | SPEC/SPEC.md:308-313 | VERIFIED | read |
| Archive-only cites | SPEC/SPEC.md:286,318,321,324,567,574 | VERIFIED | script vs git ls-files |
| Stale test path in CAP-59 | SPEC/SPEC.md:334; SPEC/catalog-contract.md:120 | VERIFIED | script |
| seed_root → CFE skill | PKG/conf/base/globals.yml:165 | VERIFIED | read |
| cf_atlas.db bridge | PKG/src/pyforge/atlas/views/cli_bridge.py:1-22,64 | VERIFIED | read |
| vuln-db / env_inspect shell-outs | PKG/src/pyforge/atlas/dashboard/scan_submit.py:45-47; datasets/refresh.py:460 | VERIFIED | read |
| 13 tools, 8 triggers | PKG/src/pyforge/atlas/mcp/tools.py:33-108 | VERIFIED | read |
| Flags unnamed, live default off | ROOT/src/platform/config/flags.json; PKG/src/pyforge/atlas/datasets/public_sources.py:17-23 | VERIFIED | json + grep |
| SelfExplainML in atlas lock | ROOT/pixi.lock:10280 | VERIFIED | lock parse |
| Ledger diff, A-only rows | ROOT/docs/foundry/capability-ledger.yaml:18-24 | VERIFIED | yaml script |
| 3 backlog, 2 blocked | PLAN/sprint-status-ledger.yaml; PLAN/epics.md:2051,2790,3113,3129,3201 | VERIFIED | yaml script |
| Ready CAPs with done stories | PLAN/epics.md epic headings 25,30,32,34-38 | INFERRED | heading→ledger map |
| FR id collision | PLAN/prds/prd-pyforge-atlas-2026-07-17/prd.md:859,1094,2229 | VERIFIED | heading count 117/77 |
| No FR arrow to missing CAP | same prd.md, epics.md | VERIFIED | regex, max CAP 72 |
| Test counts | PKG/tests | VERIFIED | `def test_` grep: unit 169 files/2610, meta 5/45, integration 15/132, tools 1/4; plus ROOT/tests/packaging 59, ROOT/scripts/tests 21 |
| 22 skip sites, 0 xfail | PKG/tests (e.g. integration/wasm/test_wasm_smoke.py:83-100; integration/publish/test_emit_range.py:206) | VERIFIED | grep; needs duckdb-server, vss, postgres ext, httpfs, playwright+Chromium (`/opt/pw-browsers`), git-pkgs, brotli, kedro_viz |
| Browser gate fails under CI | PKG/tests/integration/wasm/test_wasm_smoke.py:89-100 | VERIFIED | read |
| Coverage floor 80/70, touched modules | ROOT/docs/governance/coverage-thresholds.toml:22-23 | VERIFIED | read |
| Subtree AGENTS.md stale | PKG/AGENTS.md:42,45,79,81 | VERIFIED | ls + read |
| AD-1 / Django clean | PKG/src | VERIFIED | AST scan (my own agent-lib list) |

NOT CHECKED
- No test collected or run; counts are static. Meta-test pins other than 147 and 12/9 not recomputed.
- CAPs read closely: 1, 4–13, 16–36, 43–52, 55, 58–72. Others only through the reference script (513 backticked refs across SPEC + 8 companions).
- ~160 story specs: status tally only. Dream (2641 lines): headings only. Spine and PRD bodies: sampled.
- django-atlas: file list and imports only. Dagster definitions, Vizro page content, the 44 MB local `data/` root, and B's repo: not inspected.
- Deferred-work severity is parsed from a `severity:` field; 109 open rows have none.
