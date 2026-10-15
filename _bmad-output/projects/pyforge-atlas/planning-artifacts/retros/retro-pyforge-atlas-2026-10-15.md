---
doc_type: retrospective
project: pyforge-atlas
title: "Station retro — a new dataset, a burned-down ledger and a second type gate (2026-09-20 → 2026-10-15)"
date: 2026-10-15
created: "2026-10-15"
updated: "2026-10-15"
scope: "everything atlas landed since retro-pyforge-atlas-2026-09-20 — Epics 25, 26, 27, 28, 29 and 31 (all done), the Story 20.4 and 27.1 follow-up reviews, the four 2026-10-04 hotfixes, and Epic 30 (minted 2026-10-14, backlog, not reviewed here)"
basis: "git log --first-parent --since=2026-09-20 origin/main -- src/shared/packages/pyforge-atlas _bmad-output/projects/pyforge-atlas, at 17ca13adaa;
  gh pr list (merged atlas PRs since 2026-09-20);
  planning-artifacts/sprint-status-ledger.yaml (tracked twin); planning-artifacts/epics.md (Epics 24-31);
  the tracked story specs spec-25-1 through spec-31-1 (Review Triage Log, Spec Change Log, Auto Run Result);
  planning-artifacts/deferred-work-ledger.md;
  steward spec-103-5 (its review, nit 5); steward spec-98-1;
  live source reads: tests/integration/dashboard/test_dashboard_e2e.py, scripts/lint_types.py, pyforge-steward preflight.py,
  .github/workflows/pyforge-station-tests.yml, pyforge-marshal cli/dispatch.py, both marshal-policy.toml files"
trigger: "chain-currency — chain-audit-checkpoint-staleness fired feeds code (2026-10-14, the package pyproject.toml via Story 31.1, merge e751b79eeb) newer than retro (2026-09-20) on the pyforge-atlas chain"
---

# Retro — pyforge-atlas, 2026-09-20 → 2026-10-15

The 2026-09-20 note recorded one landing: the fleet lint and type gate. This window was bigger. Atlas landed eleven
stories in six epics, ran two owed follow-up reviews and needed four hotfixes. One epic added a capability (the
per-repo dependency history, CAP-61). The other five were fixes: the deferral burn-down, the retired-tier relay,
two test-harness fixes, and a type gate run against the libraries atlas ships with. Under
`src/shared/packages/pyforge-atlas/`, 97 files changed (+7,847 / −914).

**Method.** Written by hand in the shape of the 2026-09-14 station retro, not by `bmad-retrospective -H`. That skill
reviews one epic, writes into Tier-3 `implementation-artifacts/` and marks its own retro key with `sprint_status.py`.
This retro covers six epics, lands tracked under `planning-artifacts/retros/` (see this directory's README), and
moves ledger keys through the Tier-3 feed and `sprint-ledger-sync`. It keeps the skill's rules: every finding names its
source, and each epic gets a verdict in the skill's spelling.

## What shipped (from the ledger, the merge log and the PRs)

| Epic | Stories, merges | Verdict |
|---|---|---|
| **25** — each scanned repo's dependency history (CAP-61, FR-69) | 25.2 (#1882, `3f2744da9e`, 2026-10-05); 25.1 (#2104, `96dbe8a03a`, 2026-10-11). Minted by #1659; 25.1 moved off `blocked` by #2071 after mason's git-pkgs package landed | accepted-with-open-items: `DW-atlas-25-1-1`..`-6` open (all low); live Warden wiring follows warden 16.1 |
| **26** — the factory-status page stops reading `docs/specs` (`spec-one-chain-per-station:CAP-11`) | 26.1 (#1947, `5d91c5648b`, 2026-10-08); relay minted by #1674 | accepted |
| **27** — Phase 4+5 deferral burn-down | 27.1 (#1798, `a1f20bcdab`), 27.2 (#1832), 27.3 (#1836), 27.4 (#1839), 27.5 (#1846), all 2026-10-04; 27.1's follow-up review #1950 (`fa984aa325`, 2026-10-08). Minted by #1781 | accepted-with-open-items: 87 rows closed, `DW-atlas-27-1` open (low), four hotfixes the same day (Finding 2), 27.3's review still owed |
| **28** — the live-attach fixture Postgres starts under any basetemp (fix, CAP-6) | 28.1 (#2139, `c696667613`, 2026-10-12); chain #2136 | accepted |
| **29** — the range test server records each response before the client reads it (fix, CAP-16) | 29.1 (#2188, `617692cf71`, 2026-10-13) | accepted-with-open-items: no review recorded |
| **31** — atlas passes mypy in `pyforge-foundry-full`, and a lane keeps it so (fix, CAP-20) | 31.1 (#2221, `e751b79eeb`, 2026-10-15); chain #2217 | accepted-with-open-items: the shared `.mypy_cache`, an implementer-only review |
| 30 — the DAG export and the Vizro boards reach Pages (CAP-62, CAP-63) | minted 2026-10-14 by #2197; 30.1 and 30.2 `backlog` | not reviewed: no story has landed |
| 24 — turn on what is built | unchanged since 2026-09-14: 24.2 `blocked` (the attended, credentialed Artifactory run) | carried |

Also in the window: the Story 20.4 follow-up review (#1951, `791030287c`, 2026-10-08) found a real defect and fixed it: the
Basilisk walk read an empty page after the first as a complete catalog; `DW-FRR-20-4` and `DW-FRR-27-1` closed.

- **Epic 25** gives Atlas a `repo_dependency_history` dataset on the `vcs_health` pipeline. It clones into Atlas's own
  cache, runs `git pkgs init --no-hooks` with its database in a temporary path, and reads the result with DuckDB. A
  parser covers pixi manifests. The dataset carries no verdict; Warden's `spec-pyforge-warden:CAP-24` and `spec-pyforge-warden:CAP-26` read it. 25.2's poll-cursor
  sensor decides from Warden's fleet inventory which repos moved.
- **Epic 27** placed 87 of the ledger's 96 open medium and low rows in four stories (the operator's ruling of
  2026-10-03 moved nine owed follow-up reviews out). Each closed row carries a `resolution:` and a `verified:` line
  citing the `path:line` it fixed, and 27.4 made that a test:
  `tests/meta/test_planning_record.py::test_closed_deferred_verified_citations_resolve_to_real_lines`. 27.5 fixed the
  facet filter that 27.3's e2e test had exposed (`DW-atlas-27-3-1`) and removed its quarantine.
- **Epic 31** runs `mypy` in `pyforge-foundry-full`, the environment that installs Vizro, Dagster, Kedro,
  OpenLineage and Bokeh. There it found 72 errors in 8 files; in `pyforge-guild`, where those libraries read as `Any`,
  it found none. The lane is `{ task = "mypy", environment = "pyforge-foundry-full" }` in `pr-preflight-lanes`
  (`pixi.toml:1639`) plus one step in `lint-types.yml`.

## Findings (each sourced)

1. **Self-review found almost nothing; independent review found the defects.** Story 25.1's in-session review
   recorded one maybe-false finding. Its dispatch session's own review step never ran: the supervisor recorded
   completion one second after launch. A separate reviewer then sent the story back five times and passed it on the
   sixth (`2bb9909d8b`). Iteration 1 alone found 2 high and 7 medium: a repo name of `..` wiped a sibling cache
   directory, an `INSTALL sqlite` was a network install, and the flag-off path crashed the weekly bootstrap job
   (spec-25-1 § Review Triage Log). Four stories in this window landed with no independent review in their specs:
   25.2 ("self-review against acceptance criteria"), 27.3 ("No review has run yet"; its landing then needed hotfix
   #1840), 29.1 (no Review Triage Log at all) and 31.1 ("implementer verification"). AGENTS.md § Behavioural
   guidelines item 8 keeps implementation and review apart. → `DW-atlas-retro-2026-10-15-6`.

2. **2026-10-04: four hotfixes; three were caught by checks the landing PR did not run.**
   - #1809: 27.1 imported `numpy` without declaring it, and `pyforge-deps-test` went red on main.
   - #1851: 27.3 imported `from dash import html, no_update` at module level, and `pyforge-deps-test` went red again.
     It refused every marshal landing at the merge-tree preview (MRS-DISP-044 on #1848) until fixed.
   - #1840: 27.3 shelled `env-inspect` through `-e local-recipes`. Steward's
     `test_no_station_assumes_local_recipes.py` refuses that, but 27.3's PR ran no `steward-test`.
   - #1842: the facet-filter e2e test, flaky in CI on #1836 and #1838, was quarantined; 27.5 fixed the filter the
     same day.

   The two gaps behind the first three are still open at `17ca13adaa`. First, `pyforge-deps-test` runs in no workflow
   (no `.github/workflows/*.yml` step names it), in no `pr-preflight` lane (`pixi.toml:1639`), and not in atlas's
   `verify_commands` (`planning-artifacts/marshal-policy.toml:51`-`:54`). Only marshal's own policy runs it. It passes on
   main today (130 passed, 3 skipped). → `DW-atlas-retro-2026-10-15-4`. Second, steward Story 98.1 (#2159) derives each
   suite's triggers from what its tests read, but `steward_paths` (`pyforge-station-tests.yml:367`-`:406`) still names no
   station's `src/`. The guild-env test reads every `pyforge-*/src`
   (`test_no_station_assumes_local_recipes.py:90`-`:91`), but `git ls-files` over the steward pathspecs lists no file
   under `pyforge-atlas/src/`. An atlas-only PR can still break that test unseen. → `DW-atlas-retro-2026-10-15-5`.

3. **Atlas's test harnesses are sensitive to timing and paths, and load and concurrency are what expose it.**
   Two fixes in this window were test-only, and a third raised the waits. 28.1: the fixture's Unix socket path passed the 107-byte limit under
   preflight's per-lane `--basetemp`, so the `spec-pyforge-unifying-strategy:CAP-19` live-attach tests errored at setup. 29.1: `_RangeServer` logged a
   response only after writing it, which failed a pre-push preflight lane with `assert (200 not in [] and 206 in [])`.
   27.3/27.5: the facet-filter waits went to 15 s after CI runs on #1836 and #1838 took longer than Playwright's 5 s
   default. One wait was missed. In `tests/integration/dashboard/test_dashboard_e2e.py`, `:238`-`:240` wait 15 s, but
   `:242` (`expect(grid).to_contain_text("linux-64")`) still uses the 5 s default. That test flaked under host load
   during the 31.1 landing. → `DW-atlas-retro-2026-10-15-1`.

4. **Real library types found a real defect, and the second lane found two harness gaps.** Of 31.1's 72 errors, 54
   were Vizro defaults declared inside `Annotated[..., Field(default=...)]`. One per-module, per-code override
   (`call-arg` on `pyforge.atlas.dashboard.app`) covers them, because passing those defaults explicitly changes
   Vizro's behaviour (spec-31-1 § Intent). Seventeen more took typed fixes, and one was a runtime defect:
   `observability.py` emitted the OpenLineage `outputStatistics` facet under `facets` instead of `outputFacets`, so a
   strict consumer never found the row count, and four test assertions pinned the wrong key.
   - *Lane identity.* The second `mypy` lane failed CI's `steward-test`
     (`assert 20 == (37 - 16)`). Steward's preflight listed lanes per task and environment but recorded results by
     task name alone. Steward Story 103.5 (#2225, `c1a788982a`) fixed that before 31.1 could land.
   - *Shared cache.* The Guild `mypy` lane and the foundry-full lane both run `mypy -p` with the package as the working
     directory and no `--cache-dir` (`scripts/lint_types.py:181`). Preflight runs lanes in a thread pool sized to the
     logical core count (`preflight.py:843`, `:954`), so the two can write the same `<package>/.mypy_cache` at once.
     103.5's review raised this as nit 5, "tracked separately", but nothing tracked it until this retro.
     → `DW-atlas-retro-2026-10-15-2`.

5. **A local `pr-preflight` on a loaded host fails lanes on timeouts, and the journal cannot say so.** During the 31.1
   landing, a local `pr-preflight` on a heavily loaded host timed out in several lanes. Preflight sizes its pool to
   the core count whatever else is running (`preflight.py:843`). Its journal records `jobs` and `logical_cores` but no
   load, so a load timeout reads like a real red. For example, on the steward-only 103.5 branch, run `0dfe01dc`
   (2026-10-15T00:42Z, 16 jobs on 16 cores) went red on `pyforge-atlas-test` after 380 s, a lane that diff cannot
   change, and the journal does not say why. → `DW-atlas-retro-2026-10-15-3`.

6. **A story landed before its declared dependency.** 25.2 declares `**Deps:** S-25.1`. It landed on 2026-10-05
   against a placeholder node ("Residual risk: Story 25.1 still replaces the placeholder", spec-25-2 § Auto Run
   Result), six days before 25.1. 25.1 then had to drop the inventory input, which left the sensor's link to Warden's
   inventory nominal (`DW-atlas-25-1-1`). A single-story dispatch checks Deps only against stories in flight
   (`cli/dispatch.py:2374`, `story_transitively_depends_on(..., in_flight, ...)`). The not-`done` check
   (`dispatch_prelaunch.unmet_deps`) is read only by the drain (`cli/drain_plan.py:657`). 25.2's spec does not record
   how its launch was chosen. → `DW-atlas-retro-2026-10-15-7`.

7. **Two parallel chains took the same epic number.** 31.1 was minted as 30.1 on
   `chain-atlas-30-1-foundry-mypy-2026-10-14`. The Pages chain (`6db9855387`, #2197) took Epic 30 first, and the
   story was renumbered the same day (`ec2e4652e6`). The merge conflict caught it, and chain-completeness INV-B would
   have caught it too. No row is filed, because the renumber was clean. When two chains for one station are open at
   once, assign their epic numbers up front.

## What held

- **No gate was weakened.** 28.1 and 29.1 each banned adding a skip, `xfail`, retry or sleep, and each recorded a
  mutation that reds the fixed test when the fix is reverted (28.1 `MUT_EXIT 1`; 29.1 `1 failed`). 27.5 removed the
  quarantine `xfail` instead of keeping it.
- **Closure means evidence.** Epic 27 closed 87 rows by citation, not by assertion, and 27.4 made a fabricated
  `verified:` line fail a test.
- **Atlas measures; Warden judges.** Epic 25's hard boundaries held through six reviews: no hook or file written
  into a scanned repo, no `subprocess` or `sqlite3` under `src/pyforge/atlas` (git runs through
  `pyforge.core.process`), no import of `pyforge.warden`, every story behind its flag.
- **Owed reviews pay.** 20.4's follow-up review, owed since its landing, found the Basilisk partial-walk defect.

## What changed course

- **From building to paying down the record.** Epic 27 was minted from the ledger, not from a feature: the operator
  ruled on 2026-10-03 that every open medium and low row is fixed where it lives, in fewer, larger stories.
- **The type gate now checks atlas against the libraries it ships with.** Before 31.1, CI checked atlas in an
  environment where its libraries read as `Any`. The laptop install (`sbom-laptop-gate`) and CI now agree.
- **Pages moves to artifacts.** Epic 30 hands the Kedro-Viz export and static Vizro boards to the Pages build as
  workflow artifacts instead of committing export bytes to `main`. It is specified, not built.

## Strategy convergence

The Unifying Strategy (`spec-pyforge-unifying-strategy`) makes Atlas the one Kedro home (canopy:AD-21) and the owner
of the one DuckDB plane (`spec-pyforge-unifying-strategy:CAP-19`, "Atlas owns the engine; steward owns the through-line"). This window converges with
it:

- Epic 25's dataset is a named Atlas pipeline output read through DuckDB, with no second engine and no `sqlite3`.
  It is the plane extended to the fleet's own repos, not a private store.
- Epic 28 restored the evidence the `verified:` line of `spec-pyforge-unifying-strategy:CAP-19` cites.
  `test_read_only_live_attach.py` errored under preflight's basetemp until 28.1; it passes now.
- Epic 30, as specified, keeps the live Vizro server on Lane 1 `/console/` and puts only static, air-gap-clean
  exports on Pages. That follows the strategy's lane placement and herald AD-21 (zero third-party origins).
- Epic 31 brings atlas in line with fnd:CAP-12: `pyforge-foundry-full`, the SBOM and default laptop install, now type-checks
  atlas in CI.

The residue is unchanged from 2026-09-14 and is about *ordering*, not direction. Story 24.2's credentialed run is
still blocked, and the retirement chain (Cluster A) still has no owner.

## Action items (each an open deferred-work row)

| Row | Owner | Severity | Item |
|---|---|---|---|
| `DW-atlas-retro-2026-10-15-1` | atlas | medium | Give the e2e grid assertion (`test_dashboard_e2e.py:242`) the 15 s its neighbours have |
| `DW-atlas-retro-2026-10-15-2` | steward | low | One `.mypy_cache` per environment, or serialize the two `mypy` lanes |
| `DW-atlas-retro-2026-10-15-3` | steward | low | Journal host load with each preflight run and size `--jobs` from free cores |
| `DW-atlas-retro-2026-10-15-4` | atlas (steward for a fleet lane) | medium | Run `pyforge-deps-test` for atlas changes |
| `DW-atlas-retro-2026-10-15-5` | steward | medium | `steward-test` runs when any station's `src/` changes |
| `DW-atlas-retro-2026-10-15-6` | atlas | low | Independent reviews for 25.2, 27.3, 29.1 and 31.1 |
| `DW-atlas-retro-2026-10-15-7` | marshal | low | A single-story dispatch holds (or warns) on declared Deps that are not `done` |

## Open items carried (verified against the ledger, not new)

1. **Story 24.2** — `blocked`; `epic-24` stays `in-progress`.
2. **Cluster A — the retirement chain** (`DW-B4-3` → `DW-B4-1` → `DW-B4-2`) — open, no owner.
3. **`DW-C1-1`** (Dagster bring-up), **`DW-B2-4` / `DW-B4-4`** (Phase-P cost-gate routing), **`DW-H1` / `DW-H3`**
   (La Suite bring-up), **`DW-F1-1`** (the cold/warm benchmark), **`DW-D2-3`** (the data-present visual pass) — open,
   all attended events.
4. **Eight owed follow-up reviews** moved out of Story 27.4 by the 2026-10-03 ruling — `DW-FU-13-3`, `DW-13-3-7`,
   `DW-10-5-9`, `DW-10-6-4`, `DW-FRR-16-1`, `DW-FRR-19-1`, `DW-FRR-20-2`, `DW-FRR-20-3` — open.
5. **`DW-atlas-25-1-1`..`-6`** and **`DW-atlas-27-1`** — open lows from 25.1's sixth review and 27.1's spec.
6. **Epic 30** — `backlog`; its retro follows its stories.

Closed in this window: Epic 27's 87 rows; `DW-FU-23-5` (Story 27.1, though the 2026-09-14 retro expected it to close
with 24.2); `DW-atlas-27-3-1` (Story 27.5); `DW-FRR-20-4` and `DW-FRR-27-1` (2026-10-08).

## Ledger

`epic-25-retrospective`, `epic-26-retrospective`, `epic-27-retrospective`, `epic-28-retrospective`,
`epic-29-retrospective` and `epic-31-retrospective` move `optional` → `done`. Every story in each of those epics is
`done`. Not moved: `epic-24-retrospective` (24.2 `blocked`), `epic-30-retrospective` (no story landed) and
`epic-20-retrospective` (only 20.4's follow-up review falls in this window).

## Rule 2 note (AGENTS.md § Where things are)

No atlas landing in this window touched `recipes/`, `.claude/skills/conda-forge-expert/`,
`.claude/scripts/conda-forge-expert/` or `.claude/data/conda-forge-expert/`. 27.3's scan page *calls*
`.claude/scripts/conda-forge-expert/env_inspect.py`; it does not edit it. No conda-forge-expert retro is due.
