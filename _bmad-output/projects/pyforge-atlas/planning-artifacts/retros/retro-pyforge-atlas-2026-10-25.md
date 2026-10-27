---
doc_type: retrospective
project: pyforge-atlas
title: "Station retro — atlas fills its own data, the boards read it, and an undeclared import reds main again (2026-10-15 → 2026-10-25)"
date: 2026-10-25
created: "2026-10-25"
updated: "2026-10-25"
scope: "everything atlas landed since retro-pyforge-atlas-2026-10-15 — Epics 30 (30.1, 30.2), 32 (32.1), 33 (33.1), 34 (34.1-34.12), 35 (35.1-35.4), 36 (36.1, 36.2; 36.3 blocked), 37 (37.1-37.13), 38 (38.1) and Story 27.6; the chain and closure PRs #2250, #2259, #2273, #2297 and #2304; marshal Story 103.1's numpy declaration in atlas's manifests (#2307)"
evidence:
  - "git log --merges --since=2026-10-15 origin/main (grepped for atlas) and gh pr list --state merged, at b0753539a3"
  - "git diff --shortstat 66e6189f8e b0753539a3 -- src/shared/packages/pyforge-atlas"
  - "the tracked story specs spec-27-6 and spec-30-1 through spec-38-1 (Review Triage Log, Spec Change Log, Run results, Auto Run Result)"
  - "planning-artifacts/deferred-work-ledger.md (the DW-atlas-retro-2026-10-15 rows and every row promoted since)"
  - "specs/spec-pyforge-atlas/.memlog.md, entries of 2026-10-15 through 2026-10-25"
  - "pyforge-marshal specs/spec-103-1 (Spec Change Log, Review Triage Log; dev pass 4) and merge 67a4ae014c (pyproject.toml, pixi.toml, pixi.lock)"
  - ".claude/memory/project/ 2026-10-18-operator-rulings-atlas-fills-its-own-data-spec-py, 2026-10-19-operator-rulings-atlas-vizro-boards-spec-pyforge, 2026-10-21-operator-ruling-atlas-story-37-2-spec-pyforge-atl, 2026-10-23-operator-ruling-atlas-story-37-6-spec-pyforge-atl"
  - "live reads at b0753539a3: pixi.toml (pr-preflight-lanes, pyforge-atlas-test, pyforge-deps-test), both marshal-policy.toml files, .github/workflows/kedro-viz-publish.yml, register_pipelines() loaded against this tree, tests/packaging/test_dependency_completeness.py run in pyforge-ci (85 passed)"
trigger: "chain-currency — chain-audit-checkpoint-staleness fired feeds code (2026-10-25, the package pyproject.toml via marshal Story 103.1, merge 67a4ae014c) newer than retro (2026-10-15), with behind-code on the PRD and the spine (2026-10-22)"
---

# Retro — pyforge-atlas, 2026-10-15 → 2026-10-25

The 2026-10-15 window was fixes; this one turned the data on. Atlas landed 37 stories in nine epics. Epics 34–36 made
the public sources fill the stores in-package (CAP-64..CAP-68); Epic 37 and Story 38.1 pointed the Vizro boards at what
the pipelines write and published them on Pages (CAP-63, CAP-69). Under the package, 153 files changed (+25,705 /
−1,056; `src/` 55 files, +8,770 / −766). On 2026-10-17, 40 of 57 datasets held 0 rows and 31 of 34 boards were empty
(PRD reconciliations of 2026-10-18 and 2026-10-19); after Story 37.4, Pages showed 21 of 34 with data (memlog decision
2026-10-22), and 37.5–37.10 fed the last six. Written by hand, as on 2026-10-15: `bmad-retrospective -H` reviews one
epic and writes Tier 3.

## What happened

| Epic | Stories, merges | Verdict |
|---|---|---|
| **30** — the DAG export and the Vizro boards reach Pages (CAP-62, CAP-63) | 30.1 (#2236, with herald 42.2: the PR went red on four consumers its spec had not named, spec-30-1 § Spec Change Log); 30.2 (#2240) | accepted |
| **32**, **33** — the DAG export builds in CI (CAP-62); the CLI reaches its verbs (CAP-9) | 32.1 (#2248; CAP-62 re-derived by #2250); 33.1 (#2258) | accepted |
| **34** — public sources fill in-package (CAP-64) | 34.1–34.11 (#2260–#2269, #2271), 34.12 (#2298); chain #2259 | accepted-with-open-items: `DW-atlas-34-5-1`, `DW-atlas-34-6-1` |
| **35** — VCS and registry fetches cover the universe (CAP-65) | 35.1 (#2270), 35.2–35.4 (#2279–#2281) | accepted-with-open-items: `DW-atlas-35-1-2` |
| 36 — Basilisk, OpenTeams identity, estate source (CAP-66..CAP-68) | 36.1 (#2272), 36.2 (#2277); 36.3 `blocked` (operator, 2026-10-18: a steward export through `pyforge.core.station_port` first) | carried: `DW-atlas-36-1-1` (the operator's Basilisk token) |
| **37** — the boards read what the pipelines write, on Pages too (CAP-63, CAP-69) | 37.1–37.13 (#2275, #2276, #2278, #2282, #2286, #2288, #2290, #2291, #2293–#2295, #2299, #2300); chain #2273; #2304 | accepted-with-open-items: `DW-atlas-37-2-1`, `-37-4-1`, `-37-7-3`; main red twice after 37.7 (Finding 2) |
| **38** — the semantic store reads its upload times (CAP-69) | 38.1 (#2296); #2297 | accepted |
| 27 (one story added) — the e2e grid waits for its mount (CAP-8) | 27.6 (#2301) | accepted; closes `DW-atlas-retro-2026-10-15-1` |

1. **Every story now records a review, and the first round usually fails.** All 35 specs from 32.1 on record review
   verdicts: 26 name the reviewer independent; nine (35.2–35.4, 36.1, 36.2, 37.1–37.4) record numbered rounds without
   saying who ran them. The gap behind `DW-atlas-retro-2026-10-15-6` (no review in the spec) did not recur; that row's
   four older stories stay open. 31 of 35 failed their first round (34.12, 37.1, 37.5, 37.9 passed). First rounds
   caught a `~/.netrc` credential sent by `fetch_text` (34.6 S1), wrong data (34.3 B1 zeroed maintainers; 34.11 B1
   gave 78 native packages an unrelated PyPI name; 37.2 B3, charts summed the capped rows; 37.7 R2-B1, 135–137 of 828
   maintainer lists off legacy), a flag read once at import (34.5 B1), unmeasured spec claims (33.1 AC7, 34.9 B1, 34.10 B1) and mypy against
   real libraries (34.1, 34.4 B1, 37.4 B1). Surviving mutants became tests (34.10: 13 of 49; 34.11: 11 of 36). Cost:
   36.2 took eight rounds; 37.12 five, reviews 2–4 failing with no blocker (spec-37-12 § Review Triage Log).
2. **Story 37.7 left main red twice, and neither check runs before an atlas merge.**
   - *Undeclared numpy.* `pipelines/derived_artifacts/alternatives.py:19` has imported numpy at module level since
     `7dbcbb056c` (37.7 review 2); at the merge (`20621275f2`, #2294) `pyproject.toml` did not declare it.
     `pyforge-deps-test` (`tests/packaging/test_dependency_completeness.py`, AUD-ATLAS-010) stayed red on main through
     eight atlas merges (#2295–#2304), one of them 38.1 with a full `pr-preflight` at exit 0 (spec-38-1 § Run results).
     Marshal Story 103.1, which runs that check, found it ("unrelated and not this story's", dev pass 4) and declared
     `numpy>=2.5.3` in `pyproject.toml:37` and `pixi.toml:57` (spec-103-1 § Spec Change Log; #2307, `67a4ae014c`): the
     code stage this retro answers. It passes at `b0753539a3`.
   - *Pages Vizro build.* From the 37.7 merge the vizro job failed on main (`semantic_packages: Failed while loading
     data`) until 38.1 put `semantic_packages` in the bootstrap DAG (spec-38-1 review 2 B-2; #2296). The workflow never
     runs on a PR (`kedro-viz-publish.yml:23`–`:35`); only 38.1's reviewer, checking live, saw it.
   - *The 2026-10-15 row named this gap and is still open.* `DW-atlas-retro-2026-10-15-4` has no story. This is the
     third such red (27.1's numpy #1809 and 27.3's `dash` #1851 on 2026-10-04). Its proposed fix, atlas's
     `verify_commands` (`marshal-policy.toml:51`–`:54`), would have caught none of this window: 36 of 37 stories landed
     from hand branches; only 30.1 came through `dispatch/pyforge-atlas/30.1`. The check is in no `pr-preflight-lanes`
     leg (`pixi.toml:1680`), no workflow, and not in `pyforge-atlas-test` (`pixi.toml:2842` runs another
     `tests/packaging/` file); only marshal's policy runs it (`pyforge-marshal/.../marshal-policy.toml:96`). It cannot
     see `brotli` either, imported through `importlib` (`datasets/tier3_sources.py:98`) and undeclared
     (`DW-atlas-34-5-1`).
   - *A wrong memlog claim.* 103.1's entry on the `spec-pyforge-atlas` memlog says no `pixi.lock` change; the merge
     moved the lock's atlas `conda_source` hash and `numpy` depends (spec-103-1 § Review Triage Log).
3. **On Pages, last-good needs a cache.** The Pages producer starts from an empty data root, so AD-13 had no copy to
   keep. A cwe.mitre.org outage failed the whole build five times (`DW-atlas-38-1-1`) until 34.12 gave the three
   vulnerability feeds one fallback base (`datasets/vulnerability_feeds.py:213`; #2298). 37.12 keeps the public stores
   in `actions/cache` (#2299); its first review found the cache over its 10 GB limit with entries evicted after hours,
   and the operator ruled to raise the limit and raised it to 40 GB / 45 days (#2304). 37.13 stopped the cve-watcher
   showing an earlier run's diff as current (#2300).
4. **Live runs against legacy found what fixtures could not.** 34.7's first live scan lacked the PyPI names and
   minted 34.11; 34.10's parity check found two missing legacy mapping tiers (`DW-atlas-34-10-1`, high, closed by
   34.11); measuring found 34.3's `pr_json` repo and 34.2's Cause 3; legacy Phases E, J and M had read 0 rows since
   conda-forge split the bot's repos (memory 2026-10-18). 38.1's parity with legacy `cf_atlas.db`: 95.7% of upload
   times exact, 99.99% of archived flags agree.
5. **Stacked branches and the shared Tier-3 feed leaked state; reviews caught it, not tooling.** 34.4–34.6 and 34.8,
   35.3–35.4 were cut from earlier stories' branches; 34.8's third blocker was red gates inherited from 34.6's;
   34.11's second was a `main` merge carrying the 34.9 ledger row the shared feed had promoted.
6. **A plain run on a fresh data root still fails.** FR-72 promises it fills every public dataset, but `__default__`
   includes `query_plane_cache`, whose input has no producer until 36.3 (`DW-atlas-37-2-1`, open, medium). 38.1 fixed
   the same kind of defect for the bootstrap and pinned it (`tests/unit/pipelines/test_dag_resolves.py:425`).
7. **The written contract trails the code.** AD-3 counts ten pipelines; twelve are registered (`semantic_packages`,
   Story 20.3; `catalog_index`, Story 37.10). The rule holds: no dataset has producers in two pipelines. The MCP face
   lists eight by design (`test_audit_mapping.py:73`), but `mcp/tools.py:88`–`:92` and `:246` call them the registry.
   Both are recorded in the spine's reconciliation of this date, not repaired.

**What held.** No gate was weakened: 27.6 measured the cause (the grid mounted up to 22.3 s after `goto`) and waits
60 s for the mount rather than lengthening the row check; its load harness went from 4 failures per batch to none
(`DW-atlas-retro-2026-10-15-1`, `verified:`). Pages stayed public-only, with no secret and no
`PYFORGE_ATLAS_CREDENTIALED`. Every new live behaviour is flagged, off by default and on in `dev`
(`src/platform/config/flags.json`, `flag-overlays.json`).

## What we changed

- **Review.** Each spec records every round's verdict and the mutation results; naming the reviewer is not yet
  consistent (Finding 1).
- **Last-good on Pages.** The vizro job restores and saves the public stores (37.12), the vulnerability feeds degrade
  instead of failing (34.12), and a stale cve-watcher diff is marked stale (37.13).
- **Test egress.** 36.2's eighth review found two tests looking up `heapanalytics.com` through Kedro telemetry; the
  suite sets `KEDRO_DISABLE_TELEMETRY` (`tests/conftest.py:74`) and refuses non-loopback lookups, though not in
  subprocesses or the task's second pytest run.
- **The bootstrap needs nothing else.** `semantic_packages` joined the bootstrap DAG (38.1), and `catalog_index` runs
  after a build (`AFTER_RUN_PIPELINES`, `pipeline_registry.py:10`; 37.10).
- **Operator rulings.** 2026-10-18 (atlas fills its own data, full universe, Phase P via ClickHouse, the estate source
  waits for steward); 2026-10-19 (data first plus ten rewires, public-only Pages, weekly and on push); 2026-10-21 (the
  identity boards publish public-derived rows); 2026-10-23 (upload times from `repodata.json.zst`); 2026-10-24 (cache
  and raise its limit). "Keep moving, be autonomous" covers the memlog decisions for 37.5, 37.8, 37.9 and 37.10.
- **The 2026-10-15 rows.** `-1` closed (27.6, #2301), `-2` closed (steward 106.1, #2243); `-3` to `-7` open, and `-4`
  recurred (Finding 2).
- **Strategy convergence.** Atlas stays the one DuckDB plane (`spec-pyforge-unifying-strategy:CAP-19`); Epics 34–36
  fill it in-package through `APIDataset` or `pyforge.core.process`. Static boards reach Pages as workflow artifacts
  (AD-21), the live Vizro server stays on Lane 1, and 36.3 waits for a steward export through
  `pyforge.core.station_port`, so atlas never reads platform OLTP. Unchanged residue: 24.2 `blocked`; Cluster A
  (`DW-B4-3` → `DW-B4-1` → `DW-B4-2`) open with no owner.

## Candidate fix stories (not minted here)

| # | Owner | Candidate | Source |
|---|---|---|---|
| 1 | steward (lane), atlas (call) | Add `{ task = "pyforge-deps-test", environment = "pyforge-ci" }` to `pr-preflight-lanes` (`pixi.toml:1680`) and a CI step, so hand-landed atlas branches run it; `verify_commands` reaches dispatched stories only | `DW-atlas-retro-2026-10-15-4` (recurred) |
| 2 | atlas | Declare `brotli>=1.2`; the row asks for it beside the next retro, since it moves the code stage | `DW-atlas-34-5-1` |
| 3 | atlas, steward | Show a red `kedro-viz-publish` run on main to the next landing, or run the vizro build on PRs touching `pipelines/` | Finding 2 |
| 4 | atlas | Amend AD-3 to name the twelve pipelines (`bmad-architecture`) | Finding 7 |
| 5 | atlas | Reword `mcp/tools.py:88`–`:92`, `:246` and `test_audit_mapping.py:8`–`:9` to "the MCP-triggerable pipelines" | Finding 7 |
| 6 | atlas (Spec owner) | A memlog correction: 103.1's "no `pixi.lock` change" is wrong | Finding 2 |

Carried: `DW-atlas-37-2-1` (waits for 36.3), `DW-atlas-36-1-1`, and the eight owed follow-up reviews of 2026-10-15.

## Ledger and Rule 2 note

`epic-30`, `-32`, `-33`, `-34`, `-35`, `-37` and `-38` have every story `done`, and this retro covers them, so their
`-retrospective` keys move `optional` → `done` through the Tier-3 feed and `sprint-ledger-sync` (this file moves
none). `epic-36` (36.3 blocked) and `epic-24` (24.2 blocked) do not; `epic-27-retrospective` is already `done`. No
atlas landing touched `recipes/` or the conda-forge-expert directories, so no CFE retro is due.
