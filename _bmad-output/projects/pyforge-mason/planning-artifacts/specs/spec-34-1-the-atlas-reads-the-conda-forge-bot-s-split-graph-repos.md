---
title: "34.1: The atlas reads the conda-forge bot's split graph repos"
type: 'fix'
created: '2026-10-26'
status: 'done'
baseline_revision: 'a3cfc63fcd5a33266fb3164ce7cda8f2bf4a0322'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/scripts/_cf_graph_versions.py
  - .claude/skills/conda-forge-expert/scripts/whodepends.py
  - .claude/skills/conda-forge-expert/tests/unit/test_atlas_clis_smoke.py
  - .claude/skills/conda-forge-expert/tests/unit/test_phase_j_m_archived.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-10-26 a local `pr-preflight` failed 1 `test-ci` test, and the same test failed in a second
worktree that day: `tests/unit/test_atlas_clis_smoke.py::test_whodepends_reverse_json`. `whodepends python --reverse
--limit 5 --json` returned `[]`. The `dependencies` table had 0 rows in every local `cf_atlas.db` (the primary
checkout's, built 2026-10-18, and each worktree's copy), while `cf_atlas_meta.json` listed every phase as run. CI never
sees it: `needs_atlas` skips the atlas tests when no DB exists.

Phase J, not Phase D, writes `dependencies`. The `phase_state` row "D completed, 916426 items" is the PyPI
enumeration. Phase J parses `node_attrs` from the archive Phase E downloads, and Phase E downloads
`github.com/regro/cf-graph-countyfair/archive/refs/heads/master.tar.gz`. GitHub now answers that URL with a 301 to
`conda-forge/conda-forge-bot-data`. That archive holds `status/`, `import_to_pkg_maps/` and `mappings/`, and none of the
bot's graph. cf-scripts publishes the graph as four repos, `conda-forge/conda-forge-bot-data-node_attrs`,
`-pr_info`, `-version_pr_info` and `-pr_json`, one `<feedstock>.json` per file under a five-level sha1 shard. Because the
download succeeds, nothing fails. Phase J deletes the table first (full-snapshot semantics), finds no `/node_attrs/`
member and commits 0 edges without a warning. Phases E and M, and Phase H's cf-graph mode, read nothing.
pyforge-atlas fixed its own reader on 2026-10-18 (atlas Story 34.3). CFE's `conda_forge_atlas.py` still reads the old
URL. `git log` shows no change to the atlas scripts since 2026-10-18: the cause is upstream.

Phase J also never wrote a `test` edge. It read `requirements.test`, but the bot keeps test requirements in the
recipe's test section, so `whodepends --type test` always returned nothing:

- a v0 recipe in `test.requires` (12,150 feedstocks), and per output in `outputs[].test.requires` (449 more);
- a v1 recipe in each `outputs[].tests[]` element's `requirements.run` (17,033 elements) and `requirements.build` (675).

**Approach:**
1. A new private module, `scripts/_cf_graph_source.py`, owns the source. `fetch()` downloads one split repo's `main`
   archive into a staging file. The atlas's downloader starts every attempt from byte 0 and never sends a Range
   request: the bot pushes every few minutes, and a resumed file can splice two commits.
   `validate_split_archive()` checks the file before it replaces the cache `cf-graph-<kind>.tar.gz`:
   - the whole gzip stream reads, and its CRC holds;
   - every member sits under `conda-forge-bot-data-<kind>-main/`;
   - it holds a sharded record.

   A failed or rejected download keeps the previous cache. Once all four split caches exist, Phase E removes the
   pre-split cache they supersede.
2. `iter_records()` yields `(key, payload)` from the split cache, or from the pre-split combined
   `cf-graph-countyfair.tar.gz` when no split cache exists. The key is the path below the top directory with the
   shard removed, so a nested node (`conda-forge/label/<name>`) is not merged with another.
3. Phase E fetches all four archives (TTL `ATLAS_CFGRAPH_TTL_DAYS`) and streams `node_attrs`. Phases H (cf-graph
   mode), J and M read the caches, and none of them downloads.
4. A source with no record never replaces data:
   - Phase J rolls back its `DELETE` and returns `skipped` with the reason.
   - Phase M writes nothing unless `pr_info` and `version_pr_info` both hold records and `pr_json` resolves the live
     PRs. A partial set would reset the columns the missing part feeds.
   - Phase H skips instead of tagging rows.
   - Phase E returns an `error` and keeps its force-refresh trigger.
5. Phase M resolves `{"__lazy_json__": "pr_json/<id>.json"}` references from `-pr_json`, decoding only the referenced
   ids. An unresolvable reference counts as unknown, never open.
6. `_with_test_reqs()` folds a recipe's test section into Phase J's `test` edges: v0 `test.requires`, and v1
   `tests[].requirements.{run,build}`. An explicit `requirements.test` list wins. A v1 `python` element names no package
   and a `downstream` element names a dependent, so neither adds an edge.
7. `test_whodepends_reverse_json` gains a `needs_dependencies` skip. A built atlas skips when its table is empty and it
   has no split `node_attrs` cache yet, which means it predates this fix; the reason names the rebuild. Every such
   atlas keeps an empty table until Phases E and J run again. With the split cache present, an empty table fails the
   test with an explicit message, so the skip cannot hide a recurrence.
8. `conda_forge_atlas.py` resolves its data dir through `_paths`, as `_cf_graph_versions.py` does, so Phase E writes
   the caches where Phase H reads them.

Ledger key: `34-1-the-atlas-reads-the-conda-forge-bot-s-split-graph-repos`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-24 (atlas intelligence): "`cf_atlas.db` answers what to work on, whether it is safe, and
  what depends on it." This story restores the third answer. It is a fix, so no new CAP. A `fix` needs no flag
  (`spec-feature-flag-governance` Q1).

## Acceptance Criteria

- **AC1 — Writer.** On a real atlas, `PHASE_E_ENABLED=1 atlas-phase E`, then `atlas-phase J`, fill `dependencies`.
  `whodepends python --reverse --limit 5 --json` returns rows, and `test_whodepends_reverse_json` passes.
- **AC2 — Bad download rejected.** `fetch()` keeps the previous cache when the archive:
  - has a member outside `conda-forge-bot-data-<kind>-main/` (even when it holds JSON);
  - is truncated;
  - is not gzip.

  A retried download starts from byte 0 and sends no Range header.
- **AC3 — Empty source.** With only the redirected bot-data archive cached:
  - Phase J keeps a pre-seeded table and reports `skipped`;
  - Phase M leaves pre-seeded health columns alone;
  - Phase H tags no row;
  - Phase E reports an `error` and keeps `phase_e_force_refresh_pending`.
- **AC4 — Bot health.** Phase M counts a live PR as open only when `-pr_json` resolves it. A reference that does not
  resolve leaves `bot_last_pr_state` NULL. With `pr_json` or `version_pr_info` missing, Phase M writes nothing.
- **AC5 — Test edges.** Phase J writes `test` edges from `test.requires`, `outputs[].test.requires` and v1
  `tests[].requirements.{run,build}`.
- **AC6 — Honest skip.** On a built atlas with an empty `dependencies` table and no split `node_attrs` cache,
  `test_whodepends_reverse_json` skips. The reason names `PHASE_E_ENABLED=1 pixi run -e local-recipes build-cf-atlas`
  and the `atlas-phase E` / `atlas-phase J` refresh. The smoke file exits 0. With the split cache present, an empty
  table fails the test.
- **AC7 — Offline.** The new and existing Phase E/H/J/M tests pass with the network blocked (`unshare -rn`).
- **AC8 — Retro.** One `retro(cfe):` commit lands the code, the tests, the docs, gotcha G123, a CFE `CHANGELOG.md`
  MINOR entry (v8.102.0), the version carriers and the regenerated failure catalog.

## Boundaries & Constraints

**Always:** Go through `conda-forge-expert` (Rule 1). Land the CFE files in one `retro(cfe):` commit that moves
`CHANGELOG.md` (Rule 2). Name every governed path on the memlogs of the Specs that govern it, then stamp scoped
(AGENTS.md pre-PR item 5). Read every verdict from the exit code.

**Never:** Touch `src/shared/packages/` (pyforge-atlas keeps its own reader), `pixi.toml`, `pixi.lock` or `recipes/**`.
Rebuild the full atlas. Make Phases H, J or M download (they stay offline readers of Phase E's caches).

**Residual risk:**
- Every existing local atlas keeps its empty table until Phases E and J run again. The smoke test skips meanwhile;
  it does not refresh the DB.
- If cf-scripts moves the graph again, `fetch()` rejects the new archive and keeps the old cache. The atlas then
  serves an aging graph. Each phase's result names the error, but no detector watches it.
- `pr_json` holds a record per PR the bot ever opened. Phase M decodes only the referenced ids, but it still
  decompresses the whole archive (4 MB today).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior |
|----------|---------------|----------------------------|
| fresh split caches | Phase J | edges from every active feedstock, `test` edges included |
| only the redirected bot-data archive cached | Phase J | `skipped`, table unchanged |
| download returns another repo's archive | `fetch()` | `rejected download`, previous cache kept |
| download raises | `fetch()` | `download failed`, previous cache kept |
| no split cache, legacy combined cache present | Phases E, H, J, M | read the legacy layout |
| split and legacy caches both present | any phase | the split cache wins |
| live PR reference with no pr_json record | Phase M | unknown: not open, `bot_last_pr_state` NULL |
| live PRs but no pr_json cache | Phase M | `skipped`, health columns unchanged |
| pr_info present, version_pr_info missing | Phase M | `skipped`, health columns unchanged |
| truncated download | `fetch()` | `rejected download`, previous cache kept |
| empty `dependencies`, no split cache | smoke test | skipped, reason names the rebuild |
| empty `dependencies`, split cache present | smoke test | fails, names Phase J and G123 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-mason` CAP-24 (atlas intelligence). No CAP is minted, and no `SPEC.md` text
  changes.
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-26 entry (the atlas's dependency graph and bot
  health read the conda-forge bot's split repos again).
- Epic: Epic 34 (new, `done`). Story 34.1 is minted `done`, implemented and verified in the same change.
- Ledger key: `34-1-the-atlas-reads-the-conda-forge-bot-s-split-graph-repos`; status at mint `done`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."34"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `unshare -rn pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/unit/test_cf_graph_split_repos.py .claude/skills/conda-forge-expert/tests/unit/test_phase_j_m_archived.py .claude/skills/conda-forge-expert/tests/unit/test_phase_e_python_min.py .claude/skills/conda-forge-expert/tests/unit/test_phase_h_dispatch.py -q` — expected: pass (AC2–AC5, AC7).
- `pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/unit/test_atlas_clis_smoke.py -q -rs` — expected: exit 0; on an empty table 1 skip with the rebuild reason, on a refreshed one no skip (AC1, AC6).

**Run before the push (not dispatch gates):**
- `PHASE_E_ENABLED=1 pixi run --frozen -e local-recipes atlas-phase E`, then `atlas-phase J` and `atlas-phase M`, on
  the worktree's own atlas copy — expected: non-zero records, edges and resolved references (AC1, AC4).
- `pixi run --frozen -e local-recipes test-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.

## Run results

Run 2026-10-26 in the worktree on `a3cfc63fcd`, every verdict read from its exit code.

- **Before the fix:** the smoke file gave 1 failed (`test_whodepends_reverse_json`, `assert 0 >= 1`), 2 passed for
  `-k whodepends` (exit 1). The cached `cf-graph-countyfair.tar.gz` (48 MB) had 247,057 members and 0 `node_attrs`
  files. Its top directory was `conda-forge-bot-data-main`. `curl -sI` on the old URL returned
  `301 location: https://github.com/conda-forge/conda-forge-bot-data/...`.
- **AC2–AC5, AC7, after the review fixes:** network blocked, the new file plus the existing Phase E/H/J/M/D tests
  gave 69 passed (exit 0). Four mutations each failed their test, and the restored files passed:
  - dropping the gzip read-through: `test_a_truncated_archive_is_rejected`;
  - dropping Phase M's `pr_json` guard: `test_missing_pr_json_writes_nothing`;
  - dropping the v1 fold: `test_v1_recipe_tests_become_test_edges`;
  - append mode, with the failed attempt's file no longer deleted: `test_the_downloader_restarts_from_byte_zero`.

  Append mode alone survives, because the failed attempt's file is deleted first.
- **AC6:** on the empty table, before any split cache existed, the smoke file gave 20 passed, 1 skipped, with the
  rebuild reason (exit 0).
- **AC1, AC4, first port:** on the worktree's own atlas copy:

  | Phase | Result |
  |---|---|
  | E | downloaded the four archives (37, 7, 2 and 4 MB); 30,600 `node_attrs` records; enriched 33,434 rows in 20.5 s |
  | J | 28,936 feedstocks, 336,072 edges (23,430 `test`) in 6.1 s |
  | M | 30,596 `pr_info` records; 18,159 of 18,159 live-PR references resolved; 32,313 rows updated in 6.4 s |

  `whodepends python --reverse` returned rows (42,942 `python` dependents), and the smoke file gave 21 passed (exit 0).
- **AC1, AC4, after the review fixes** (forced refetch, `ATLAS_CFGRAPH_TTL_DAYS=0`):

  | Phase | Result |
  |---|---|
  | E | all four archives passed the whole-stream validation; the superseded `cf-graph-countyfair.tar.gz` was removed; 30,602 records |
  | J | 343,280 edges (30,619 `test`, v1 recipes included) |
  | M | 18,146 of 18,146 live-PR references resolved; 32,313 rows updated |
- **AC8:** CFE v8.102.0, a MINOR entry in `CHANGELOG.md` with gotcha G123. The version moves in `SKILL.md`,
  `MANIFEST.yaml` and `config/skill-config.yaml`. `config/failure-catalog.yaml` is regenerated (123 rows).

## Spec Change Log

- 2026-10-26, independent review (PASS, no blocker), fixed on the same branch:
  - S1: the downloader used `_http.fetch_to_file_resumable`, which resumes with a Range request inside one call, and
    validation stopped at the first record, so a truncated or spliced download could replace a good cache. Downloads
    now start from byte 0 on every attempt, and validation reads the whole gzip stream and every member.
  - S2: Phase M zeroed `bot_open_pr_count` and `bot_last_pr_state` when `pr_json` was missing. It now writes nothing
    unless `pr_info`, `version_pr_info` and, for live PRs, `pr_json` are all present.
  - S3: v1 recipes' test requirements (`tests[].requirements`) gave no `test` edge. Phase J now reads them.
  - Nits:
    - the atlas and `_cf_graph_versions.py` resolve the data dir the same way (`_paths`);
    - the smoke-test skip applies only before the split cache exists, so a recurrence fails;
    - a failed download leaves no staging or `.part` file;
    - Phase E removes the superseded legacy cache;
    - `pyforge-marshal`'s `project-parts.json` lists the new module.
- 2026-10-26: minted `done`, implemented and verified in the same change.

## Review Triage Log

- 2026-10-26, review 1 (independent subagent, read the diff against this spec): PASS, 0 blockers, 3 should-fix,
  4 nits. It reproduced the offline tests (51 passed) and 188 neighbouring atlas tests. It ran 8 mutations, each of
  which broke a test. It reproduced S1 (a half-length archive validated, then raised `EOFError` mid-read) and S2 (a
  seeded row went from (3, 'open') to (0, None)), and measured S3 (8,677 v1 nodes, 2,710 with test dependencies).
  Every finding is fixed on the branch (Spec Change Log) except one part of a nit: `bmad-drift-check`'s
  `surface-changed` warning. Its baseline is at CFE 8.91.8, ten releases before this story, so re-stamping it here
  would launder other stories' drift. It stays with marshal's SYNC-RUNBOOK re-ground.
