---
chain: pyforge-steward
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Steward"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Steward

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

## Steward A→B cutover audit (read-only, 2026-11-10)

**Verdict: NOT READY.** The Spec does not describe the code in several load-bearing places, the cutover machinery contradicts its own Spec, and the capability ledger cannot be trusted as a routing map.

Path prefixes: `R/` = `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/`; `P/` = `R/_bmad-output/projects/pyforge-steward/planning-artifacts/`; `SPEC` = `P/specs/spec-pyforge-steward/SPEC.md`; `S/` = `R/src/shared/packages/pyforge-steward/src/pyforge/steward/`; `T/` = `R/src/shared/packages/pyforge-steward/tests/`.

### MUST REFRESH (blocks cutover)

1. **Cutover code is the forbidden fold.** `cutover plan` writes a file-move manifest (`docs/foundry/manifest.json`, never committed), not a ledger. `apply --phase 1a|1b` copies `src/shared/packages/` to `src/packages/`, plus `.claude/skills/`, `_bmad/`, `_bmad-output/projects/`, `docs/dreams/`. 36 tests in `T/unit/test_cutover.py` pin this, so the oracle encodes retired intent.
2. **`pyforge.cutover_root` switches nothing.** Its value is read only by the core reader, a `django_pyforge` wrapper and `flip`'s own summary line. fnd:CAP-8 and Story 44.12 (`done`) promise it switches ledger of record, Mason targets and loop-home remotes.
3. **fnd:CAP-9 success does not hold.** The ledger has only id/spec/station/heading/mode/path (+expiry 93, note 52). No state, dependency or signal field. No generator exists; it is hand-edited. `--append` reports no drift.
4. **Ledger rows for this Spec are unreliable.**
   - The id set matches exactly (178 = 178). The 183-line count is 5 Constraint lines reusing CAP-5/6/166/167/168 labels (SPEC:1036–1060).
   - 108 of 178 rows carry the heading of a different capability (pre-renumber). The detector matches id only.
   - All 178 are `rebuild`, including about 50 host/platform/container CAPs and 12 recipe/channel CAPs. That conflicts with fnd:CAP-2 (host out of Launch) and case-list `k-no-host` / `k-no-root-recipes`.
   - 50 rows from 11 archived specs duplicate folded CAPs; 46 carry the opposite mode (A-only vs rebuild).
   - Zero rows claim `verified-in-foundry`, though 54.2–54.4 and 55.3 are `done`.
5. **Bare CAP ids are ambiguous.** Steward src has 314 bare `CAP-n`, tests 170. CLI help cites pre-fold ids: `upgrade (CAP-1..5)`, `suite (CAP-1/2)`, `deploy static CAP-8` are today's CAP-9..13, 21–22, 116.
6. **Spec text stale against code.**
   - CAP-2 (shipped) specifies `steward deploy dashboard`; the verb is gone, replaced by `pages`.
   - CAP-175 names driver `scripts/station_suite_ci.py`; it never existed.
   - CAP-4 promises three `budget check` exit codes; code only ever returns 3.
   - CAP-7 says eval-quality `1.4.1`; recipe and pins are `4.3.0`. Seven `pixi.toml:<line>` refs point at unrelated lines.
   - "13 suite members" vs 17 in `suite-members.yaml`; "51 Guild tasks" vs 95.
   - Markers: 150 shipped, 23 ready, 5 none (CAP-169..173), 0 retired. 18 of 23 `(ready)` CAPs have every citing story `done` (150, 152–164, 166–168, 174).
7. **Unspecced code.**
   - No CAP text at all: `restore`, top-level `revoke`, `preflight verify-deferred`.
   - Only in the sibling cutover Spec: `cutover`.
   - CAP exists but never names the verb: `track assemble`, `guards *`, `load`, `passport mint`, `glass export`, `quarantine *`, `catalog render|ship|publish`, `deploy perimeter|static`, `deck-drift`, `measure`.
   - MCP face (`start_duty`, `get_duty`; targets `ci-status`, `estate-plan`, `estate-status`) has 0 mentions in the steward SPEC; it lives in unifying CAP-20.
   - 21 of 30 `pyforge.steward.*` flag keys are not named in the SPEC.
   - Non-duty entry points: `python -m pyforge.steward.{frames,preflight,marketplace_pages}`.
   - fnr:CAP-3 promises a `frames` duty; A has none (31 duties, no `frames`).
   - Six external importers of steward internals contradict "CLI is the sole contract": django-atlas, django-pyforge, `src/platform/ingest/github_projects`, `src/platform/config/asgi.py`, `scripts/pages_*`.
8. **Frame cannot seed a rebuild.** 21 lines, 7 of 31 duties, no exit codes, flags or MCP; last commit 2026-09-16.

### SHOULD RECHECK

- **Tests as oracle.** Unit 128 files / 2,521 test functions; meta 26 / 187; integration 4 / 28 (attended NKP probes, own task).
  - Split: module-level `pytestmark = pytest.mark.live_tree`, selected by `-m "not slow and not live_tree"` vs `-m "live_tree and not slow"`. `conftest.py` only strips pytest-split flags.
  - Live-tree half: 76 of 154 files, 1,339 functions, 23 of 26 meta files. Package half: 78 files, 1,369 functions.
  - SPEC cites 17 test names; 144 of 178 CAP numbers appear in no test; no CAP→test matrix found.
  - No xfail. 81 skip sites, all environment-conditional. Two depend on `.pixi/envs/local-recipes` share data; two depend on live flag state.
  - Coverage floor 80 unit / 70 integration, set in `R/docs/governance/coverage-thresholds.toml`. Duty count 31 is pinned and correct.
- **Case list.** All 34 nodeids resolve on A. The count line says 38; there are 40 rows (10 steward).
- **Portability.** `src/shared/packages` appears in 8 string literals across 6 files; `rxm7706/local-recipes` in 3. Steward shells to or imports 22 distinct `R/scripts/*` files. `catalog/`, `corridor/`, `measures/` data sit outside the wheel. The flag tree path is `src/platform/config/flags.json`. Direct `pyforge.doctor` imports exist; `station_port` is used 0 times. No module-level Django outside `dashboard/` (6 function-local imports).
- **Epic 44 text.** Intro still says A "is archived read-only"; 44.1 and `cutover.md:19` still list mode `move`.
  - 44.1, 44.2, 44.8, 44.9, 44.11, 44.14, 44.15 `blocked` (operator-held); 44.10 `blocked` (retired); 44.4/5/6 `backlog` (parked); 44.3, 44.7, 44.12, 44.13 `done`. Epics 54, 55, 67 all `done`.
- **Other open keys.** 87.2 blocked (retired); 109.4 backlog; 109.5 in-progress; 114.9 backlog; 117.9 backlog; 118.3 backlog (operator inputs); 29.5 backlog. Ledger now reads 428 done / 8 backlog / 9 blocked / 1 in-progress.
- **A-only expiries.** 63 rows expire 2026-12-31 (51 days). `mcp-factory-stdio-translator:CAP-1/2` expire on `44.7`, which is `done`. `44.8`, `44.9`, `44.15` are blocked.
- **Spec behind memlog.** Four EGM findings accepted 2026-11-05 are not in SPEC (updated 2026-11-01). Cutover SPEC 2026-10-15 vs memlog 2026-10-27. Regenerate-not-fold SPEC 2026-09-17 vs memlog 2026-10-26.
- **Skill.** All `[SRC:]` line refs resolve; one src commit since compile. Exit list omits 3; MCP tools unstated. Persona still names tool `station_face` (last commit 2026-09-07).
- **Deferred work.** 327 open (111 medium, 215 low, 0 high). Cutover-relevant: DW-FU-47-2 family (no skill link-generation step), DW-steward-119-1, DW-steward-119-2 (`estate plan` exits 0 on a failed pixi; oracle bug).

### NICE TO UPDATE

- Package README names 6 duties; `pyproject` omits `pyforge-doctor` and `bmad_loop`.
- `R/pixi.toml:640` says "unit + conformance + meta"; there is no conformance dir.
- Ledger header `updated 2026-11-01` and `source_sha` (2026-10-31, 176 commits behind) vs content edit 2026-11-06.
- Six companions cited by CAPs 38, 70, 93, 117, 122, 139 exist only under `archive/`.
- All 15 `verified:` lines are dated 2026-09-11.
- SPEC Open Questions treat Stories 100.1 and 102.2 as future; both are `done`.
- PRD has FR arrows for 37 CAPs; all 76 arrow refs resolve.
- `preflight_xdist.py` and `five_tier.py` are referenced only by tests. Zero TODO/FIXME.
- No steward flag is past cleanup (earliest 2027-01-24).

### Evidence

| Finding | Where | V/I | How |
|---|---|---|---|
| plan = move manifest; apply copies | `S/cutover.py:35-44,78-81,133-223` | V | read |
| Manifest never committed | `git log -- docs/foundry/manifest.json` = 0 | V | git |
| No consumer of flag value | `S/cutover.py:343`; `django_pyforge/flags.py:205` | V | grep `read_cutover_root` over `src` |
| Ledger fields, no state | `R/docs/foundry/capability-ledger.yaml` | V | yaml parse, key counter |
| 108 heading mismatches | same, e.g. line 3501 | V | script vs SPEC titles |
| Detector matches id only | `pyforge-doctor/.../sources/capability_ledger.py:179-184` | V | read |
| 50 duplicate rows | ledger vs SPEC `← spec-x CAP-m` heads | V | script |
| Constraint CAP labels | `SPEC:1036,1037,1042,1047,1060` | V | regex |
| `deploy dashboard` gone | `SPEC:177`; `S/cli.py:66-67` | V | parser dump |
| Missing driver script | `SPEC:871` | V | `ls`, `git log` |
| budget returns 3 only | `SPEC:185`; `S/cli.py:30-38`; `S/budget.py:300-305` | V | read |
| eval-quality pin stale | `SPEC:194-195`; `R/pixi.toml:620,964,2310` | V | grep |
| 18 stale `(ready)` | epics FR/AD lines + ledger | I (mapping) | regex + yaml |
| Unspecced duties | `SPEC:173-1022` | V | grep per verb |
| MCP tools | `django_pyforge/station_cli.py:98-102`; `mcp_start_get.py:52-66` | V | read |
| Pre-fold ids in help | `S/cli.py:149,164-173` | V | grep |
| Test split | `R/pixi.toml:639-650`; `pyproject.toml` markers | V | read + AST count |
| Cross-station imports | `S/session.py:98-99`; `S/upgrade.py:3569-3570` | V | grep |
| A-tree literals | `S/corridor.py:53`, `measures.py:24`, `catalog.py:68`, `preflight_ci.py:1698`, `upgrade.py:141` | V | AST string scan |
| Case-list count | `P/specs/spec-foundry-regenerate-not-fold/case-list.md` | V | script |
| Epic 44 stale text | `P/epics.md:2740,2749`; `P/specs/spec-python-foundry-cutover/cutover.md:19` | V | read |

### NOT CHECKED

- No tests, detectors, sync or stamps run. B not inspected.
- Close reading covered about 30 of 178 CAP blocks (1–9, 54–55, 114–123, 139–145, 175) plus all fnd, fnr and fcl CAPs. The other ready and top-25 CAPs were token-resolved only (386 backticked tokens), not read against code.
- The 447 story specs were not opened. The architecture spine was read for frontmatter only. `django-steward` (106 LOC) was only skimmed.
- SBOM solve claims, memlog re-derivability (Story 44.13) and the CAP-175 timing budgets were not verified.
- The CAP→story map is regex over FR/AD lines and may over-attribute.

---

## Cross-cutting findings (main session, 2026-11-10)

Measured by the session that ran the nine audits, at A `82a2b18828` and B `origin/main` `a762a14`.
The nine station reports live beside each station's chain:
`_bmad-output/projects/pyforge-<station>/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
(core, the testing kit and the host: `pyforge-marshal/.../cutover-readiness-audit-core-host-2026-11-10.md`).

### The two roots

- B's `main` is `a762a14`, unchanged since 2026-09-14: 84 files, a kernel of about 1,400 lines
  (thin `pyforge-core`, steward and marshal leaves), a 40-row case list (the file's count line says
  38), and one factory recipe. Its `docs/foundry/PIN.md` pins A at `9e9f6854` (PR #1344).
- A is 8,526 commits past that pin. Since the pin, `pyforge-core/src` gained 2,394 lines, steward
  23,824 and marshal 40,800.
- B wrote no Dream, Frame or Spec after 2026-09-14; A wrote all of them. B holds no station Spec and
  no memlog. Open on B: Renovate PR #20 (Python 3.15), PR #19 (since 2026-09-25), an unmerged branch
  at `157e5e7` (the 2026-09-28 Mason-skills ruling on the Frames). These are outward and operator-owned.
- The Frames are four-bullet stubs and differ between A and B in every file. A's copy is the newer
  one (2026-09-14, 2026-09-16, 2026-10-08). A's company Frame still says "never a mason skill tree",
  against the 2026-09-28 ruling. `docs/foundry/frames/upstream-pin.yaml` pins frame-spec PR #28 at
  `d7213c1` and PR #29 at `4596579`; both PRs are open and moved to `219bff7` and `89dffdd` on
  2026-10-05.

### The cutover machinery on A

- `pyforge.cutover_root` is read by `pyforge.core.cutover_root`, one `django_pyforge` wrapper and
  the summary line of `steward cutover flip`. Nothing else switches on it (marshal and mason: zero
  readers of the value).
- `steward cutover plan|apply` writes a move manifest and copies trees (`cutover.py`, phase rules
  `1a` and `1b`). `spec-python-foundry-cutover/SPEC.md` and `cutover.md` use `move`, `moved` or
  `moving` 27 times.
- The capability ledger (`docs/foundry/capability-ledger.yaml`, 1,021 rows): 923 `rebuild`, 93
  `A-only`, 5 `retire`; fields are id, spec, station, heading, mode, path, plus expiry on 93 rows and
  note on 52. No state, dependency, signal or claim field. Every live Spec's CAP-id set equals its
  ledger rows (15 Specs). 162 rows sit on 42 archived Specs: 98 duplicate a folded station row in
  the same mode, 49 are `A-only` against a `rebuild` twin, 8 `A-only` against `A-only`, 2 `retire`
  against `retire`, 5 have no twin. The four governance Specs (30 capabilities) and
  conda-forge-expert have no rows.
- The 87 rows that expire 2026-12-31: 55 on archived Specs, 32 on live Specs (15
  `spec-pyforge-unifying-strategy` host rows, 8 warden, 5 testing charter, 4 cutover).
- Stories 44.4, 44.5 and 44.6 sat at `backlog` with their dependencies (44.3, 44.12) `done` and no
  parked marker in their text. Story 44.14 (the rebuild harness) is `blocked`.
- `steward`'s `epics.md` carries 30 lines that bind an epic to `CAP-1..145`, an artifact of the
  fold's remint note, whatever the size of the Spec named.

### Detectors and fleet state (run on the primary checkout the same day)

- `detectors` (57 run): exit 1. Findings: `chain_currency_sweep_check` (atlas, doctor, herald, mason,
  scribe, warden stale; marshal and steward current), `unpushed_work_check` (383 dangling commits, 44
  local-only refs), `scribe_graph_freshness_check` (graph 112 hours old), `missing_preserve_check`
  (herald 21.2). Warnings: four pixi currency ledgers 239 to 268 commits behind,
  `docs/reference/skills-catalog.md` stale against its generator, three ambiguous BMAD config keys.
- `frozen-path-changed` reports "no capability ledger found (pre-cutover)" because it reads
  `docs/foundry/manifest.*`. `story-status` audits 1,690 stories and checks none ("no run record").
- `fleet-picture`: 1,690 of 1,720 stories done, 14 blocked; every loop home 380 to 514 commits behind
  `origin/main`; bmad-loop 0.12.0 installed against 0.13.2 upstream (marshal caps `<0.13`);
  bmad-method 6.12.2 against 6.12.4.
- CI on `82a2b188`: station tests, lint and types, detectors and Pages all succeeded.

### Faults shared by every station Spec

1. Status markers do not track reality: `(ready …)` on capabilities whose stories are all `done`
   (marshal 49, herald 37, scribe 23, steward 18, atlas 8, warden 4), and no marker at all on others
   (marshal 104, mason 22, doctor 12 plus 28 with retired marker values, the core Spec all 11).
2. Deleted or never-built work is marked `shipped` (marshal's console capabilities, atlas's
   satellites, mason's Presenton and retired-campaign capabilities, steward's `deploy dashboard`,
   herald's docsite capabilities). Mason's SPEC defines fourteen CAP ids twice.
3. The public contract is mostly absent from the Specs: CLI verbs, flags, MCP tools, feature-flag
   keys, environment variables and diagnostic codes (marshal: 333 `MRS-*` codes in source, 32 in the
   Spec). No station Spec names its own MCP tools. conda-forge-expert has no Spec.
4. Tests bind to A's tree. The `live_tree` marker exists in steward and doctor only. No station's
   source imports `pyforge.core.station_port`.
5. Every `pyproject.toml` requires Python 3.14; six package `pixi.toml` files and three Specs say 3.12.

### Spot-checks and corrections

- Confirmed by the main session: mason's duplicate CAP definitions and missing flag reader;
  atlas's `shipped` satellites and "exactly seven" pipelines; warden's nine unnamed flags; core's 17
  modules; steward's fold code and the placeholder ledger headings (96 to 108 of 178 by two
  measures); marshal's four hard-coded remotes, the 333 against 32 codes and the console capabilities.
- Not confirmed: marshal's "11 MCP tools specced" (8 registered was confirmed). The mason report says
  none of five Presenton recipes exist; `recipes/presenton` does.
- The pre-measured "retired" counts given to the agents were word matches on CAP titles; no CAP in
  any station Spec carries a retired marker.

### The rulings and the order of work

The operator's four rulings of 2026-11-10 are on `docs/dreams/pyforge-unifying-strategy.md`
§ Realization log and in `.claude/memory/project/2026-11-10-operator-rulings-on-the-cutover-after-a-nine-audi.md`.
The recommended order: an honest control plane (cutover Spec, ledger, flag consumers, the two
detectors, Frames), then a Spec truth sweep (core, steward, marshal, doctor, then the rest), then the
oracle (`live_tree` split for the six stations that lack it, a larger case list), then portability
and pins. All of it lands as one PR from `cutover-readiness-2026-11-10`.
