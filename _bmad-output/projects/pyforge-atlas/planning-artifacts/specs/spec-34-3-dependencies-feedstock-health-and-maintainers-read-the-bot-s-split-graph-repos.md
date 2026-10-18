---
title: "34.3: Dependencies, feedstock health and maintainers read the bot's split graph repos"
type: 'fix'
created: '2026-10-18'
status: 'done'
baseline_revision: 'bdffa4c135'
review_loop_iteration: 3
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/nodes.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/nodes.py
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `core_dependencies`, `core_feedstock_health`, `vcs_maintainers` and `vcs_package_maintainers` were 0 rows
after the unattended refresh of 2026-10-17, and legacy's Phases E, J and M read 0 rows the same night (R1).

- **The source moved.** `core_cf_graph_raw` fetched `github.com/regro/cf-graph-countyfair/archive/refs/heads/master.tar.gz`.
  That repo now redirects to `conda-forge/conda-forge-bot-data`, whose tarball (48 MB) holds `import_to_pkg_maps/`,
  `status/`, `mappings/`, `graph.json` and `all_feedstocks.json`, but no `node_attrs/`, `pr_info/` or `version_pr_info/`.
  cf-scripts' `settings.py` names their homes: `conda-forge/conda-forge-bot-data-node_attrs`, `-pr_info`,
  `-version_pr_info`, and `-pr_json` for live PR records. Each is sharded by cf-scripts' `get_sharded_path` with the
  top directory trimmed: `<repo>-main/<5 sha1 hex dirs>/<feedstock>.json`.
- **The parser never emitted maintainers.** `enrich_maintainers` needs a `maintainers` list per row; the parser had no
  such column, so the maintainer tables stayed empty even when node_attrs existed.
- **The health parser read a shape the bot never publishes.** `_health_from_pr_info` read `prs`, `issues` and `checks`.
  The bot's `pr_info` holds `PRed` (`{"PR": {...}, "data": {"version"}}`), `bad` and migrator fields; legacy Phase M
  (`phase_m_feedstock_health`, CFA:6263) reads `PRed`, `bad` and `version_pr_info.new_version_errors`.
- **Live PRs are references.** Measured over the 30,525 `pr_info` files on 2026-10-18: inline `PR` records are all
  `closed` (443,606), and 18,166 are `{"__lazy_json__": "pr_json/<id>.json"}`. The `-pr_json` tarball (3.6 MB) holds
  18,214 records, 18,213 of them `open`.
- **A few nodes nest.** 4 of the 30,529 node_attrs files sit under `conda-forge/label/<shard>/<name>.json` (archived
  label nodes); each shares its basename with a different, un-nested node.
- **Sizes, 2026-10-18:** node_attrs 36.8 MB (30,529 files, 9 s), pr_info 7.0 MB, version_pr_info 2.0 MB, pr_json 3.6 MB.

**Approach:**
1. `parse_cf_graph_tarballs(node_attrs, pr_info, version_pr_info, pr_json)` keys every record by its node name: the
   path below the top directory with the five shard directories and `.json` removed, so a nested label node never merges
   with its basename twin. It reads the small bot records first, then streams node_attrs member by member into rows, so
   the decoded node_attrs records are never held at once. `parse_cf_graph_tarball` keeps the pre-split combined layout
   for fixtures and mirrors, in two passes the same way.
2. One frame for Phases E, J and M: an edge row per dependency, plus an anchor row (`depends_on` NA) per output name
   (every name in the requirements blocks and in `outputs_names`, else the feedstock), so every output keeps its
   maintainers and health with or without edges, plus a row per feedstock with bot data but no node_attrs. New columns:
   `maintainers` (`meta_yaml.extra.recipe-maintainers`, legacy Phase E, CFA:2335) and legacy Phase M's
   `bot_last_pr_state`, `bot_last_pr_version`, `bot_version_errors_count` and `feedstock_bad`. `open_prs` is the open
   bot-PR count, with references resolved through `pr_json`; an unresolvable reference is unknown, never open.
   `ci_status` and `open_issues` stay NA: they are live GitHub signals (Phase N, Story 35.3). `open_issues` was a
   made-up `0` (int64) before and is a null column now; the dashboard loaders read it unchanged.
3. `CfGraphTarballDataset(url, pr_info_url, version_pr_info_url, pr_json_url, filepath)` composes one `APIDataset` per
   repo. With `filepath`, a frame that holds node_attrs-derived rows is kept as `last_good.parquet` and clears the
   marker. It serves last-good under the AD-13 marker on a fetch failure (`DatasetError`), a body that is not a gzip
   tarball, a configured bot repo with no records (a partial redirect), or a frame with no node_attrs; any other error is
   a bug and raises. The copy reads back with `maintainers` as `list[str]`, exactly as the fresh frame. `staleness()`
   and `last_good_path` let `provenance.py` report the copy and the marker. Without `filepath` a failure raises.
4. `compute_feedstock_health` carries the four bot columns additively, and an empty input returns all eight columns;
   the catalog points at the four repos through the existing `GITHUB_BASE_URL` override. The semantic layer's notes
   that called these columns absent are corrected; the `stuck` / `bad` filters stay undeclared until D2.

Ledger key: `34-3-dependencies-feedstock-health-and-maintainers-read-the-bot-s-split-graph-repos`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md` row 4): a `fix` restoring a source meant to work; no flag.
- **AD-2, AD-13, AD-11** (fixtures only; every tarball in the tests is built in memory). Additive schema (the Spec's
  "additive-first" constraint).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R1. The legacy CFE copy has the same break; its fix
  is the mason-chain story after this effort (operator ruling "Kedro first, legacy after").

## Acceptance Criteria

- **AC1 — Split layout.** Sharded `<repo>-main/a/b/c/d/e/<feedstock>.json` members across the four tarballs parse into
  edges, health and maintainers; a nested `conda-forge/label/<name>` node stays a separate node; the combined layout
  still parses through the dataset.
- **AC2 — Legacy Phase M semantics.** Open bot PRs count resolved `pr_json` references; an unresolvable reference is not
  open; `bot_last_pr_state` / `_version` come from the last `PRed` entry; `bot_version_errors_count` counts
  `new_version_errors`; `bad` on either record flags the feedstock; bot-only feedstocks get a health row; self-references,
  jinja targets and archived feedstocks never become edges.
- **AC3 — Maintainers.** `enrich_maintainers` gets a maintainer per output, including outputs with no edges and outputs
  named only in `outputs_names`.
- **AC4 — AD-13.** A good fetch writes `last_good.parquet` and clears the marker; a failed fetch, a non-tarball body, a
  bot repo with no records, or a frame with no node_attrs serves last-good (or the empty frame) under the marker, and
  the served copy gives `enrich_maintainers` the same frames as the fresh one; provenance reports the copy's mtime and
  the marker; a parser bug raises.
- **AC5 — Live (recorded 2026-10-18 08:03, live fetch, scratch data root, `--nodes build_dependency_graph,
  compute_feedstock_health,enrich_maintainers`, exit 0, 63 s, peak RSS 1.26 GB):**
  - `core_dependencies` 0 → 313,888 edges over 31,356 conda names. Legacy Phase J reads 0 since the split, so it is not
    the oracle; the independent review matched a word-for-word port of it, edge for edge.
  - `core_feedstock_health` 0 → 28,932 feedstocks: node_attrs' 30,529 nodes less the 1,597 it flags archived. 7,820 have
    open bot PRs, 17,210 in all; 615 have version-update errors; 2 are flagged `bad`.
  - The same counts on the 07:22 tarballs, re-derived by the review: 17,209 open (18,164 open across all feedstocks, 955
    of them on archived ones; 18,165 of `pr_info`'s 18,166 references resolve; 49 `pr_json` records are referenced by
    none), and 4 `bad` (`proj4`, `py-graphviz`, `rpaths`, `usagestats`; legacy's `cf_atlas.db` also has 4). The bot
    cleared `rpaths` and `usagestats` between the two fetches.
  - `vcs_maintainers` 0 → 8,516 and `vcs_package_maintainers` 0 → 60,264. Legacy's tables hold 8,303 and 62,411, last
    written before the split stopped its Phase E.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate and `lint-types` exit
  0; governing Specs reconciled and stamped scoped.

## Boundaries & Constraints

**Never:** a credential on the bot's hosts; an HTTP client import in the package; a test that touches the network;
a schema change that drops a column consumers read.

**Residual risk:**
- **Phase E fields beyond maintainers** (repo, dev and homepage URLs, registry names) are read from the same node_attrs
  by Story 35.2, which builds the VCS population from them.
- **`ci_status` and `open_issues`** stay NA until Story 35.3's live GitHub fetch.
- **The legacy CFE copy** still reads the old tarball; its fix is the mason-chain story after Epic 36.
- **The bot's own feedstock list** (`all_feedstocks.json`: 28,902 active, 902 archived) is not this frame's universe;
  node_attrs flags 1,597 nodes archived, and its 117 nodes with no `feedstock_name` keep a health row, as before.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run | tarball has no node_attrs → every table 0 rows | four split repos → edges, health, maintainers |
| A live bot PR | — (read `prs`) | a `pr_json` reference, resolved; open |
| An unresolvable reference | — | unknown, not open |
| Feedstock with no requirements | no row → no maintainers | anchor row per output name carries maintainers and health |
| A nested `conda-forge/label/<name>` node | — | its own node, never merged with `<name>` |
| A repo unreachable | raises | last-good under a marker |
| The redirect again (no node_attrs) | 0 rows written | last-good kept, marker "no node_attrs" |
| A bot repo answers with no records | — | last-good kept, marker "<repo> yielded no records" |
| A parser bug | — | raises; never a silent stale serve |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a `fix`.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R1.
- Epic 34 / Story 34.3 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-3-cf-graph-split-repos`); the `pr_json` repo and
  the inline/reference split were found while measuring.
- 2026-10-18: independent review FAIL (1 blocker, 6 should-fix, 6 nits). Resolved: the parquet copy read `maintainers`
  back as numpy arrays, so a degraded run zeroed the maintainer tables (B1); every `outputs_names` entry anchors (S1);
  AC5 recounted (S2); the semantic notes that called the Phase M columns absent are corrected (S3); tests for
  `version_pr_info.bad`, the marker clearing, self-references, jinja targets, the archived flag and the combined layout
  through the dataset (S4); a configured bot repo with no records degrades (S5); node_attrs streams (S6, peak RSS
  2.5 GB → 1.26 GB for the run); all eight health columns on empty input (N1); the `open_issues` type change noted
  (N2); only fetch and tarball errors degrade, with the cause in the reason (N3); `_tar_json_members` annotated (N4);
  provenance reads the marker (N5). Found while re-measuring: 4 nested label nodes merged with their basename twins;
  records are keyed by node name.
- 2026-10-18: re-review FAIL on one new blocker: the S3 docs edit made `semantic/metrics.py` a touched module, and its
  unit coverage read 71.9% against the 80% floor (the classifiers and identity ops ran only in integration tests).
  `tests/unit/semantic/test_metric_classifiers.py` runs them on DuckDB against verbatim ports of legacy `_classify` and
  `policy_check_status`; a malformed `python_min` is a documented departure (legacy keys it `(99, 99)`, the metric says
  `unknown`). Every earlier finding verified fixed; 26 of 26 mutants killed.
- 2026-10-18: round 3 FAIL on one blocker the full preflight also caught: `_SourceEmpty` lacked `PyforgeError` as a
  base (`spec-pyforge-core` CAP-5, `test_exception_root_sole_ownership`). Fixed; the new classifier test verified
  against the legacy originals (7 of 7 mutants killed) and the coverage gate green CI's way. Verdict PASS with the fix;
  promoted to `done`.
