---
title: "25.18: Wave A's no-refresh recipes are re-bucketed live from the atlas"
type: 'fix'
created: '2026-11-01'
status: 'done'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror.md
deferred:
  - id: epic-25-refreshed-mirrors-behind-again
    summary: "55 of the 99 co-maintained feedstocks that Epic 25 stories had already refreshed or re-mirrored (25.2 pilots, 25.5-25.12, 25.13, 25.14, 25.16) are behind their published version again on the 2026-11-01 atlas snapshot (the otel family at 1.45.1/0.66b1 vs 1.45.2/0.66b2, selectolax 0.4.13 vs 1.0.2, django-allauth, tox, sentry-sdk, graphifyy, bmad-method, cachetools, fastmcp and more). Story 25.18 was bounded to Wave A's no-refresh set and did not refresh them; the run record lists every one with its feedstock, local and published version."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-18-wave-a-s-no-refresh-recipes-are-re-bucketed-live-from-the-atlas.md:200
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Wave A (Story 25.2, 2026-10-09) bucketed every co-maintained package by matching it to a
`recipes/<name>/` directory and reading the first version line it found. That is how it misread the four `lfx-*`
bundles as `v1-ahead`: it read duplicate directories and their first output's version. Story 25.14 re-checked only
its 22 names. So the rest of Wave A's no-refresh buckets were never re-verified: 162 `v1-current`, the 4 `v1-ahead`
left after the `lfx-*` bundles, and 2 `other-non-pep440` (168 in all; 25.2's spec, Wave A table). Any multi-output
recipe in them was judged by its first version line, not by each output. The station memlog's line that
"`v1-ahead` (8) and `other-non-pep440` (2) get no story" was an agent's decision, not an operator ruling.
`DW-mason-25-14` records the mapping rule (use the atlas's `packages.feedstock_name`, never the directory name) and
stays open.

Wave A cannot be replayed: its baseline (`.cursor/track_b_baseline.json`, `.cursor/track_b_baseline.md`) and its script
(`.cursor/track_b_wave_a.py`) were never committed and are gone.

Found by the EGM fleet audit of 2026-11-01 (marshal Story 113.7): **MAS-D-C4**, cluster `mason-c09-wave-a-residue`.
Residue: `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** re-derive the 168 live. Invoke `conda-forge-expert` first (Rule 1) and work in `-e local-recipes`, local
only.

- Map each co-maintained package to its feedstock through the atlas's `packages.feedstock_name` (`DW-mason-25-14`;
  Wave A step A3 of the companion `feedstock-refresh.md`), never by directory name.
- Compare each output's own `context` version with its feedstock's published version, so a multi-output recipe is
  judged output by output.
- Record every one of the 168 with its bucket and the reason in this spec.
- Refresh each one found behind with `pixi run -e local-recipes refresh-wave`, to an end state in CAP-35's outcome
  set (cluster `mason-c03`'s re-derive).

**Parked (operator ruling 2026-11-01):** it stays `backlog`, and `DW-mason-25-14` stays open until it lands.

Ledger key: `25-18-wave-a-s-no-refresh-recipes-are-re-bucketed-live-from-the-atlas`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (the feedstock refresh campaign is Mason's), FR-57: each track re-counts its scope live
  from the atlas; every recipe in scope reaches its feedstock's published version; no co-maintainer is dropped.
- No new CAP. `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag; `flag-exempt: recipe-build` records
  the class.
- AD-1, AD-15: no Mason package change; every CFE-surface edit lands in a `retro(cfe):` commit.

## Acceptance Criteria

1. **The scope is re-derived, not replayed.** Given the atlas refreshed within its `<atlas_max_age_d>` window, When the
   story maps Wave A's no-refresh packages through `packages.feedstock_name`, Then the spec records the live count
   before any refresh starts, and names every package with its feedstock.
2. **Every output is judged.** Then each recipe is bucketed by every output's own `context` version against its
   feedstock's published version (current, behind, ahead or non-PEP 440), with the reason recorded; no bucket rests on
   the first version line of a multi-output recipe.
3. **Behind recipes are refreshed.** Each recipe found behind is refreshed through
   `pixi run -e local-recipes refresh-wave <manifest> --gates --build --report-dir <dir>` and ends in CAP-35's outcome
   set (a green linux-64 build, a recorded G95 block, or `needs-review` with its reason). Its `recipe-maintainers` stays
   a superset of the deployed feedstock's (G53); a G72 suite's bundle pins move with its version.
4. **Ahead and non-PEP 440 are explained.** Each recipe bucketed ahead or non-PEP 440 carries the reason it stays.
5. **The deferral closes.** `DW-mason-25-14` in
   `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` gains a `verified:` line citing this
   spec's mapping, and closes.
6. **Local only.** No push, PR, fork, issue or comment outside `rxm7706/local-recipes`; no `mason recipe submit`,
   `mason package ship`, CFE `submit_pr` or `prepare_submission_branch`.
7. **Retro.** A `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry, shared with Story 25.17's if both land
   together.
8. **Green.** `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Boundaries & Constraints

**Always:**

- Invoke `conda-forge-expert` before any recipe edit.
- Read every verdict from the exit code, never through a pipe.
- Build each recipe into an isolated output directory (G52).

**Never:**

- Bucket a package by its `recipes/<name>/` directory name alone.
- Refresh a recipe outside Wave A's no-refresh buckets; Story 25.17 owns the build records of Epic 25's built recipes.
- Hand-write a `cfe-local-build-*` field, or hand-edit any `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| single output, current | `context.version` = published | bucket `current`, no refresh | — |
| multi-output, one output behind | first output current, another behind | bucket `behind`, refreshed | — |
| ahead | local > published | bucket `ahead`, reason recorded | — |
| non-PEP 440 version | e.g. a date or tag form | bucket `non-pep440`, reason recorded | — |
| directory name differs from feedstock | atlas maps to another feedstock | judged against the atlas's feedstock | — |
| refresh still red | build fails after diagnosis | `needs-review` with the reason | — |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-mason` CAP-35 (the feedstock refresh campaign is Mason's), FR-57. A fix, no new
  CAP.

Parent: CAP-35

- Dream: `docs/dreams/pyforge-mason.md` § Realization log, the 2026-11-01 entry (the EGM fleet audit).
- Audit finding carried: MAS-D-C4 (cluster `mason-c09-wave-a-residue`); residue
  `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 25 (the feedstock refresh campaign), done; a new not-done story reopens it (doctor Story 41.5).
- Ledger key: `25-18-wave-a-s-no-refresh-recipes-are-re-bucketed-live-from-the-atlas`.
- Deps: —.
- Surface: `recipes/<name>/recipe.yaml` for each recipe the re-bucket finds behind; this spec's bucket record;
  `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` (`DW-mason-25-14`); the CFE retro
  surface (`.claude/skills/conda-forge-expert/CHANGELOG.md` and its version carriers), committed alone as
  `retro(cfe): …`.
- Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1); `flag-exempt: recipe-build`.
- Mode: parked at `backlog` (operator ruling 2026-11-01).
- Minted 2026-11-01 by marshal Story 113.7's landing PR, on the operator's acceptance of the audit's recommendations.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**

- `pixi run -e local-recipes refresh-wave <manifest> --gates --build --report-dir <dir>` over the recipes found behind
  — expected: a report row per recipe, each in the outcome set.
- `grep -n "DW-mason-25-14:" -A12 _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` —
  expected: a `verified:` line and a closed status.
- `pixi run -e pyforge-guild deferred-work-check` and `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0.

## Run record (2026-11-01)

### Atlas freshness (AC 1)

Read-only (`file:…/cf_atlas.db?mode=ro`) while `build-cf-atlas` was still running in the primary checkout (its
build env sets `PHASE_E_ENABLED=1`). `phase_state` and the cache files show every phase this story reads ran today:

| Phase | What 25.18 reads from it | Evidence (2026-11-01, CST) |
|---|---|---|
| B | `packages.latest_conda_version`, the package rows | `phase_state` B completed 18:19:35 (34,849 packages) |
| B.5 | `packages.feedstock_name` | runs between B (done 18:19:35) and D (started 18:19:43) |
| C | conda↔PyPI match | same window as B.5 |
| D | PyPI enumeration | `phase_state` D completed 18:19:55 |
| E | `maintainers`, `package_maintainers` | the four bot-graph archives (`cf-graph-*.tar.gz`) were fetched 18:20:23–18:20:34, and Phase E finished before E.5 started at 18:20:42 |
| E.5 | `feedstock_archived` | `phase_state` phase_e5 completed 18:20:53 |

Phase K (upstream GitHub versions) was still `running` (started 19:27:20) when the bucket pass read the atlas, and
Phase N followed; neither feeds this story. The build has since finished: `cf_atlas_meta.json` reads
`built_at` 2026-11-02T03:04:03Z (UTC; 21:04 on 2026-11-01 local) with every phase B to N run.

### Method

1. **Co-maintained set.** `package_maintainers ⋈ maintainers` where `rxm7706` (id 34) maintains the package and the
   package has more than one distinct maintainer: **318 packages on 293 feedstocks** (all `active`, none archived).
   Phase E only inserts maintainer rows, so a handle a feedstock dropped can linger; the bucket pass re-reads each
   deployed recipe's `extra.recipe-maintainers` through `feedstock_lookup` (live) and records any drift.
2. **Mapping (`DW-mason-25-14`).** Each package maps to its feedstock through `packages.feedstock_name`, and the
   feedstock to its mirror `recipes/<feedstock_name>/` (case-insensitive). All 293 feedstocks have a mirror. Declared
   `package.name`s were parsed from every `recipes/*/recipe.yaml` (v1) or `meta.yaml` (v0) to find the directory that
   declares each package. Directories that re-declare a feedstock's package beside its mirror (`django-compressor`,
   `draftjs-exporter`, `fastmcp-slim`, `fastmcp-v4`, `graphify`, `openlineage-suite`, `pillow_heif`,
   `urllib3.future`) are not the feedstock's mirror and were not judged or edited here.
3. **Wave A's no-refresh scope, re-derived.** Wave A's baseline and script are gone, so its 168 cannot be replayed.
   The live equivalent is the 293 co-maintained feedstocks, minus the 99 whose mirrors an Epic 25 story refreshed or
   re-mirrored (the 25.2 pilots, Track B batches 25.5–25.12, the 25.13 mirrors, 25.14's `db-gpt`, the 25.16
   adapters), minus the three Story 25.17 owns that no batch refreshed (`django-grpc`, `py-yaml12`, `solvor`;
   bucketed below for the record, marked owned and not refreshed). That subtraction trusts story history: those
   stories brought each mirror to the version published *then*, and 55 of the 99 are behind again on today's
   snapshot (§ Behind again, below). They stay outside this story's scope and are not refreshed here.

**Live count of the re-derived no-refresh set: 191 feedstocks** (recorded before any refresh). The difference from
Wave A's 168 is the live set's growth (288 → 293 feedstocks) and Wave A's directory-name matching, which missed
mirrors whose directory differs from the package name and counted Wave F outputs as missing.

### Behind again, outside this story's scope

Re-bucketed on the same atlas snapshot (Phase B, 2026-11-01 18:19 CST) and the same per-output method: 55 of the 99
excluded feedstocks (56 outputs; `fastmcp` ships `fastmcp` and `fastmcp-slim`) are behind their published version
again. An independent review counted 54; the difference is `dbt`: the atlas also lists a legacy `dbt` package (1.0.0)
under the `dbt` feedstock that `recipes/dbt` does not declare, while the mirror's declared output `dbt-core` is behind
(1.12.5 vs 1.12.6), so this per-output computation counts the feedstock. None was refreshed here (25.18's boundary is Wave A's
no-refresh set); they are carried as the deferral `epic-25-refreshed-mirrors-behind-again` in this spec's frontmatter.

| Package | Feedstock | Local version | Published | Refreshed by |
|---|---|---|---|---|
| `airflow-code-editor` | `airflow-code-editor` | 8.3.1 | 8.3.2 | Story 25.5 |
| `azure-storage-file-share` | `azure-storage-file-share` | 12.27.0 | 12.27.1 | Story 25.5 |
| `bmad-method` | `bmad-method` | 6.12.1 | 6.12.4 | Story 25.2 |
| `cachetools` | `cachetools` | 7.2.1 | 7.2.8 | Story 25.5 |
| `cron-descriptor` | `cron-descriptor` | 2.1.1 | 2.2.1 | Story 25.2 |
| `dbt-core` | `dbt` | 1.12.5 | 1.12.6 | Story 25.5 |
| `dbt-snowflake` | `dbt-snowflake` | 1.12.1 | 1.12.4 | Story 25.13 |
| `django-allauth` | `django-allauth` | 65.19.7 | 65.21.1 | Story 25.5 |
| `django-mptt-admin` | `django-mptt-admin` | 3.0.0 | 3.1.1 | Story 25.6 |
| `fastmcp-slim` | `fastmcp` | 4.1.0 | 4.1.4 | Story 25.6 |
| `fastmcp` | `fastmcp` | 4.1.0 | 4.1.4 | Story 25.6 |
| `graphifyy` | `graphifyy` | 0.9.84 | 0.9.100 | Story 25.6 |
| `grimp` | `grimp` | 3.17 | 3.18 | Story 25.6 |
| `headroom-ai` | `headroom-ai` | 0.39.1 | 0.42.0 | Story 25.6 |
| `milvus-lite` | `milvus-lite` | 3.2.1 | 3.2.2 | Story 25.7 |
| `office2pdf` | `office2pdf` | 0.8.1 | 0.10.0 | Story 25.8 |
| `openlineage-dbt` | `openlineage-dbt` | 1.53.0 | 1.54.0 | Story 25.8 |
| `openlineage-integration-common` | `openlineage-integration-common` | 1.53.0 | 1.55.0 | Story 25.8 |
| `openlineage-python` | `openlineage-python` | 1.53.0 | 1.55.0 | Story 25.8 |
| `openlineage-sql` | `openlineage-sql` | 1.53.0 | 1.55.0 | Story 25.8 |
| `opentelemetry-api` | `opentelemetry-api` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-distro` | `opentelemetry-distro` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-exporter-prometheus` | `opentelemetry-exporter-prometheus` | 0.66b1 | 0.66b2 | Story 25.10 |
| `opentelemetry-exporter-zipkin` | `opentelemetry-exporter-zipkin` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-exporter-zipkin-json` | `opentelemetry-exporter-zipkin-json` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-exporter-zipkin-proto-http` | `opentelemetry-exporter-zipkin-proto-http` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-instrumentation` | `opentelemetry-instrumentation` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-aiopg` | `opentelemetry-instrumentation-aiopg` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-asgi` | `opentelemetry-instrumentation-asgi` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-botocore` | `opentelemetry-instrumentation-botocore` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-celery` | `opentelemetry-instrumentation-celery` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-dbapi` | `opentelemetry-instrumentation-dbapi` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-django` | `opentelemetry-instrumentation-django` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-falcon` | `opentelemetry-instrumentation-falcon` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-flask` | `opentelemetry-instrumentation-flask` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-grpc` | `opentelemetry-instrumentation-grpc` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-httpx` | `opentelemetry-instrumentation-httpx` | 0.66b1 | 0.66b2 | Story 25.11 |
| `opentelemetry-instrumentation-mysql` | `opentelemetry-instrumentation-mysql` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-psycopg2` | `opentelemetry-instrumentation-psycopg2` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-pymongo` | `opentelemetry-instrumentation-pymongo` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-pyramid` | `opentelemetry-instrumentation-pyramid` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-requests` | `opentelemetry-instrumentation-requests` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-sqlalchemy` | `opentelemetry-instrumentation-sqlalchemy` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-sqlite3` | `opentelemetry-instrumentation-sqlite3` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-system-metrics` | `opentelemetry-instrumentation-system-metrics` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-tornado` | `opentelemetry-instrumentation-tornado` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-urllib3` | `opentelemetry-instrumentation-urllib3` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-instrumentation-wsgi` | `opentelemetry-instrumentation-wsgi` | 0.66b1 | 0.66b2 | Story 25.12 |
| `opentelemetry-propagator-jaeger` | `opentelemetry-propagator-jaeger` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-proto` | `opentelemetry-proto` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-sdk` | `opentelemetry-sdk` | 1.45.1 | 1.45.2 | Story 25.10 |
| `opentelemetry-semantic-conventions` | `opentelemetry-semantic-conventions` | 0.66b1 | 0.66b2 | Story 25.10 |
| `opentelemetry-util-http` | `opentelemetry-util-http` | 0.66b1 | 0.66b2 | Story 25.10 |
| `selectolax` | `selectolax` | 0.4.13 | 1.0.2 | Story 25.9 |
| `sentry-sdk` | `sentry-sdk` | 2.71.0 | 2.73.0 | Story 25.9 |
| `tox` | `tox` | 4.64.10 | 4.67.5 | Story 25.9 |

### Buckets (AC 2, AC 4)

Each recipe was judged output by output: every `package.name` in the mirror's `recipe.yaml` (or the v0 `meta.yaml`
when no v1 recipe existed) took its own version from `context` (per-output version keys resolved), and was compared
with that package's `latest_conda_version` on the channel (atlas Phase B, today) and with the deployed feedstock
recipe read live through `feedstock_lookup`. The two published sources agreed for every output. Every in-scope
mirror turned out single-output; `django_compressor`'s second atlas package, `django_compressor` (last upload 2.3 in
2019), is a retired legacy name no recipe declares and was not judged.

| Bucket | Count (of 191) | Notes |
|---|---:|---|
| current | 156 | plus the three Story 25.17 owns (`django-grpc`, `py-yaml12`, `solvor`), all current |
| behind | 34 | all refreshed below |
| ahead | 1 | `Office365-REST-Python-Client` |
| non-PEP 440 | 0 | every local and published version parsed; Wave A's two `other-non-pep440` no longer occur live |

**Ahead, and why it stays.** `Office365-REST-Python-Client`'s local `recipe.yaml` carries upstream 3.0.0 (built green
2026-08-17, `cfe-forge-recipe-updates-needed: version-update-to-3.0.0`) while its feedstock has not merged the
autotick PRs #23-#26 (3.0.0 to 3.3.0), so the channel still serves 2.6.2; the local `meta.yaml` mirror stays at 2.6.2.
The local recipe is the pending update, not a defect. Upstream is now at 3.3.0, which that PR queue already covers.

**G53 on the current set.** 16 current recipes lacked a handle the deployed feedstock lists (most often a co-maintainer
added after the mirror was taken). Each list was extended line by line with the missing handles, local order first,
and nothing else changed (`yaml.safe_load` equal apart from the list). After this pass every one of the 194 bucketed
recipes holds a `recipe-maintainers` superset of its deployed feedstock's.

**Mirror fidelity on the current set (review round).** A version match does not prove the mirror matches the
feedstock. `meta.yaml` was re-copied byte-for-byte from the feedstock for `prophecy-build-tool` (it held 1.3.4 against
1.4.6), `wagtailmedia` (0.18.1 against 0.19.1), `skranger` and `timelib` (build number), and `docstring_parser_fork`,
`python-openid2`, `wagtail-factories` (a maintainer handle). The leftover `meta.yaml` of `basedmypy`, `dacite`, `dice-ml`,
`dlt`, `pipdeptree`, `pytest-robotframework` and `sqlmesh` was deleted after checking each feedstock live: each has only
`recipe/recipe.yaml` (G94); `dacite` also gained the feedstock's `LICENSE`. `django-libsass` was structurally stale
(not noarch, no tests, no setuptools, no `LICENSE` or `run_test.py`; `validate` exited 1): its `recipe.yaml` now
follows the v0 feedstock (noarch, setuptools, python_min machinery, `django-compressor`, the feedstock's
`run_test.py` as two CFEP-25 Django script tests with pip check, because a bare import raises `ImproperlyConfigured`),
the feedstock files are mirrored, a canonical CFE block was added, and it built green through the driver (`b6`) after
one Build Failure Protocol iteration (`b5` failed on the bare import). `repoze.lru` declared `package.name: repoze-lru`,
a name the channel does not carry (so the first pass read its published version as None); it now declares
`repoze.lru` like the feedstock, with the dotted source path and purl, and rebuilt green (`b5`).

**Build numbers and the last red record (second review round).** Re-copying `meta.yaml` left `skranger` at `build.number`
5 against the feedstock's 6, and `timelib` at 2 against 3; each `recipe.yaml` now carries the feedstock's number, and both
rebuilt green (`b7`). `prophecy-build-tool` still held the `failed` record of 2026-10-09 in a recipe this story touched.
Its rebuild went red once (`b7`, `pip_check`, Build Failure Protocol iteration 1): the run requirements were older than
the deployed 1.4.6 feedstock, so they were synced to it (G96: `databricks-sdk >=0.20,<0.73` with the feedstock's comment,
`rich >=12.5.1,<15`, `pydantic-yaml >=1.4,<2`, `twine <7`), and it built green (`b8`).

| Package(s) | Feedstock | Local dir | Outputs judged | Local version | Published | Bucket | Reason | Action / outcome |
|---|---|---|---|---|---|---|---|---|
| `agno` | `agno` | `recipes/agno/` | `agno` | 2.6.22 | 2.6.22 | current | local = published (channel and feedstock recipe agree) | none |
| `airflow-provider-great-expectations` | `airflow-provider-great-expectations` | `recipes/airflow-provider-great-expectations/` | `airflow-provider-great-expectations` | 1.0.0 | 1.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `airflow-provider-xlsx` | `airflow-provider-xlsx` | `recipes/airflow-provider-xlsx/` | `airflow-provider-xlsx` | 1.0.1 | 1.0.1 | current | local = published (channel and feedstock recipe agree) | none |
| `alang` | `alang` | `recipes/alang/` | `alang` | 0.0.4 | 0.0.4 | current | local = published (channel and feedstock recipe agree) | none |
| `anaconda-catalogs` | `anaconda-catalogs` | `recipes/anaconda-catalogs/` | `anaconda-catalogs` | 0.2.0 | 0.2.0 | current | local = published (channel and feedstock recipe agree) | none |
| `askbot` | `askbot` | `recipes/askbot/` | `askbot` | 0.11.7 | 0.11.7 | current | local = published (channel and feedstock recipe agree) | none |
| `azure-core-tracing-opentelemetry` | `azure-core-tracing-opentelemetry` | `recipes/azure-core-tracing-opentelemetry/` | `azure-core-tracing-opentelemetry` | 1.0.0b13 | 1.0.0b13 | current | local = published (channel and feedstock recipe agree) | none |
| `azure-monitor-opentelemetry` | `azure-monitor-opentelemetry` | `recipes/azure-monitor-opentelemetry/` | `azure-monitor-opentelemetry` | 1.8.9 | 1.8.9 | current | local = published (channel and feedstock recipe agree) | none |
| `bandit` | `bandit` | `recipes/bandit/` | `bandit` | 1.9.4 | 1.9.4 | current | local = published (channel and feedstock recipe agree) | none |
| `basedmypy` | `basedmypy` | `recipes/basedmypy/` | `basedmypy` | 2.10.0 | 2.10.0 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live) |
| `behave` | `behave` | `recipes/behave/` | `behave` | 1.3.3 | 1.3.3 | current | local = published (channel and feedstock recipe agree) | none |
| `bentoml` | `bentoml` | `recipes/bentoml/` | `bentoml` | 1.4.39 | 1.4.40 | behind | local 1.4.39 < published 1.4.40 | refresh-wave 1.4.39 -> 1.4.40; build `success`; meta.yaml mirrored; hand: CFE block added; literal source.url; host/test python pin .* |
| `caveman-installer` | `caveman-installer` | `recipes/caveman-installer/` | `caveman-installer` | 2.7.0 | 4.0.1 | behind | local 2.7.0 < published 4.0.1 | refresh-wave 2.7.0 -> 4.0.1; build `success`; G53 +pb01ka; hand: run synced (no `nodejs >=18`, G103; the commented host `nodejs 24.*` hold kept); license_file LICENSE.BSL -> LICENSE-MIT (feedstock) |
| `channels_redis` | `channels_redis` | `recipes/channels_redis/` | `channels_redis` | 4.3.0 | 4.3.0 | current | local = published (channel and feedstock recipe agree) | none |
| `click-repl` | `click-repl` | `recipes/click-repl/` | `click-repl` | 0.3.0 | 0.4.1 | behind | local 0.3.0 < published 0.4.1 | refresh-wave 0.3.0 -> 0.4.1; build `success`; G53 +jsmolic; meta.yaml removed; hand: run synced to the feedstock (G96); sdist filename moved to `click_repl-` at 0.4.x |
| `clickclick` | `clickclick` | `recipes/clickclick/` | `clickclick` | 20.10.2 | 20.10.2 | current | local = published (channel and feedstock recipe agree) | none |
| `codegraph` | `codegraph` | `recipes/codegraph/` | `codegraph` | 1.6.0 | 1.6.2 | behind | local 1.6.0 < published 1.6.2 | refresh-wave 1.6.0 -> 1.6.2; build `success`; G53 +pb01ka; hand: BFP: write `pnpm-workspace.yaml` (ui workspace) before `pnpm install`, as the feedstock build.sh does; host `nodejs >=20,<25` hold kept; review round: on-conda-forge status confirmed (G78) |
| `collectfast` | `collectfast` | `recipes/collectfast/` | `collectfast` | 2.2.0 | 2.2.0 | current | local = published (channel and feedstock recipe agree) | none |
| `compress-pickle` | `compress-pickle` | `recipes/compress-pickle/` | `compress-pickle` | 2.1.0 | 2.1.0 | current | local = published (channel and feedstock recipe agree) | none |
| `confection` | `confection` | `recipes/confection/` | `confection` | 1.3.3 | 1.3.4 | behind | local 1.3.3 < published 1.3.4 | refresh-wave 1.3.3 -> 1.3.4; build `success`; meta.yaml mirrored; hand: BFP: host/test python pin .*; mirrored the missing feedstock `patches/` file |
| `contextvars` | `contextvars` | `recipes/contextvars/` | `contextvars` | 2.4 | 2.4 | current | local = published (channel and feedstock recipe agree) | none |
| `culsans` | `culsans` | `recipes/culsans/` | `culsans` | 0.11.0 | 0.11.0 | current | local = published (channel and feedstock recipe agree) | none |
| `dacite` | `dacite` | `recipes/dacite/` | `dacite` | 1.9.2 | 1.9.2 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live); feedstock LICENSE mirrored |
| `dash-ag-grid` | `dash-ag-grid` | `recipes/dash-ag-grid/` | `dash-ag-grid` | 35.3.0 | 35.3.0 | current | local = published (channel and feedstock recipe agree) | none |
| `dataclasses-json` | `dataclasses-json` | `recipes/dataclasses-json/` | `dataclasses-json` | 0.6.7 | 0.6.7 | current | local = published (channel and feedstock recipe agree) | none |
| `dbt-adapters` | `dbt-adapters` | `recipes/dbt-adapters/` | `dbt-adapters` | 1.24.5 | 1.24.5 | current | local = published (channel and feedstock recipe agree) | none |
| `dbt-common` | `dbt-common` | `recipes/dbt-common/` | `dbt-common` | 1.39.0 | 1.39.0 | current | local = published (channel and feedstock recipe agree) | none |
| `dbt-spark` | `dbt-spark` | `recipes/dbt-spark/` | `dbt-spark` | 1.11.0 | 1.11.0 | current | local = published (channel and feedstock recipe agree) | none |
| `dice-ml` | `dice-ml` | `recipes/dice-ml/` | `dice-ml` | 0.12 | 0.12 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live) |
| `django-appconf` | `django-appconf` | `recipes/django-appconf/` | `django-appconf` | 1.2.0 | 1.2.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-autocomplete-light` | `django-autocomplete-light` | `recipes/django-autocomplete-light/` | `django-autocomplete-light` | 5.0.0 | 5.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-avatar` | `django-avatar` | `recipes/django-avatar/` | `django-avatar` | 9.0.0 | 9.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-bakery` | `django-bakery` | `recipes/django-bakery/` | `django-bakery` | 0.13.5 | 0.13.5 | current | local = published (channel and feedstock recipe agree) | none |
| `django-braces` | `django-braces` | `recipes/django-braces/` | `django-braces` | 1.17.0 | 1.17.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-cachalot` | `django-cachalot` | `recipes/django-cachalot/` | `django-cachalot` | 2.9.1 | 2.9.1 | current | local = published (channel and feedstock recipe agree) | none |
| `django-configurations` | `django-configurations` | `recipes/django-configurations/` | `django-configurations` | 2.5.1 | 2.5.1 | current | local = published (channel and feedstock recipe agree) | none |
| `django-cors-headers` | `django-cors-headers` | `recipes/django-cors-headers/` | `django-cors-headers` | 4.9.0 | 4.9.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-environ` | `django-environ` | `recipes/django-environ/` | `django-environ` | 0.14.0 | 0.14.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-filer` | `django-filer` | `recipes/django-filer/` | `django-filer` | 3.4.4 | 3.4.4 | current | local = published (channel and feedstock recipe agree) | none |
| `django-followit` | `django-followit` | `recipes/django-followit/` | `django-followit` | 0.7.0 | 0.7.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-foundation-formtags` | `django-foundation-formtags` | `recipes/django-foundation-formtags/` | `django-foundation-formtags` | 0.1.0 | 0.1.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-fsm` | `django-fsm` | `recipes/django-fsm/` | `django-fsm` | 3.0.1 | 3.0.1 | current | local = published (channel and feedstock recipe agree) | none |
| `django-fsm-admin` | `django-fsm-admin` | `recipes/django-fsm-admin/` | `django-fsm-admin` | 1.2.5 | 1.2.5 | current | local = published (channel and feedstock recipe agree) | none |
| `django-grpc` | `django-grpc` | `recipes/django-grpc/` | `django-grpc` | 1.2.20 | 1.2.20 | current | local = published | owned by Story 25.17; not refreshed here; HEAD was 1.2.15; 1.2.20 is Story 25.17's uncommitted rebuild in the worktree |
| `django-haystack` | `django-haystack` | `recipes/django-haystack/` | `django-haystack` | 3.4.0 | 3.4.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-health-check` | `django-health-check` | `recipes/django-health-check/` | `django-health-check` | 4.8.0 | 4.11.3 | behind | local 4.8.0 < published 4.11.3 | refresh-wave 4.8.0 -> 4.11.3; build `success`; G53 +jsmolic; hand: literal source.url; run synced (optional integrations dropped, django >=6, httpx >=0.27); context python_min 3.14 (feedstock) |
| `django-jinja` | `django-jinja` | `recipes/django-jinja/` | `django-jinja` | 2.11.0 | 2.11.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-jsonstore` | `django-jsonstore` | `recipes/django-jsonstore/` | `django-jsonstore` | 26.8.0 | 26.8.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-keyedcache3` | `django-keyedcache3` | `recipes/django-keyedcache3/` | `django-keyedcache3` | 1.5.4 | 1.5.4 | current | local = published (channel and feedstock recipe agree) | none |
| `django-libsass` | `django-libsass` | `recipes/django-libsass/` | `django-libsass` | 0.9 | 0.9 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka; review round: recipe.yaml brought in line with the v0 feedstock (noarch, setuptools, python_min, run_test.py as CFEP-25 Django script tests); meta.yaml, LICENSE, run_test.py mirrored; canonical CFE block added; rebuilt through the driver: success (first rebuild failed on a bare Django import; BFP iteration 1 moved the test to the CFEP-25 Django script form) |
| `django-livesettings3` | `django-livesettings3` | `recipes/django-livesettings3/` | `django-livesettings3` | 1.7.0 | 1.7.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-material` | `django-material` | `recipes/django-material/` | `django-material` | 1.12.0 | 1.12.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-model-utils` | `django-model-utils` | `recipes/django-model-utils/` | `django-model-utils` | 5.0.0 | 5.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-modelcluster` | `django-modelcluster` | `recipes/django-modelcluster/` | `django-modelcluster` | 6.5 | 6.5 | current | local = published (channel and feedstock recipe agree) | none |
| `django-mptt` | `django-mptt` | `recipes/django-mptt/` | `django-mptt` | 0.18.0 | 0.21.0 | behind | local 0.18.0 < published 0.21.0 | refresh-wave 0.18.0 -> 0.21.0; build `success`; meta.yaml mirrored; hand: CFE block added; literal source.url; host python pin .* |
| `django-picklefield` | `django-picklefield` | `recipes/django-picklefield/` | `django-picklefield` | 3.4.0 | 3.4.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-redis` | `django-redis` | `recipes/django-redis/` | `django-redis` | 7.0.0 | 7.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-reversion` | `django-reversion` | `recipes/django-reversion/` | `django-reversion` | 6.3.0 | 6.5.0 | behind | local 6.3.0 < published 6.5.0 | refresh-wave 6.3.0 -> 6.5.0; build `success`; meta.yaml mirrored; hand: CFE block added; literal source.url; run django >=5.2 (feedstock); host python pin .* |
| `django-robots` | `django-robots` | `recipes/django-robots/` | `django-robots` | 6.1 | 6.1 | current | local = published (channel and feedstock recipe agree) | none |
| `django-simple-history` | `django-simple-history` | `recipes/django-simple-history/` | `django-simple-history` | 3.13.0 | 3.13.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-storages` | `django-storages` | `recipes/django-storages/` | `django-storages` | 1.14.6 | 1.14.6 | current | local = published (channel and feedstock recipe agree) | none |
| `django-test-plus` | `django-test-plus` | `recipes/django-test-plus/` | `django-test-plus` | 2.6.2 | 2.7.0 | behind | local 2.6.2 < published 2.7.0 | refresh-wave 2.6.2 -> 2.7.0; build `success`; meta.yaml mirrored; hand: CFE block added; literal source.url; host/test python pin .* |
| `django-viewflow` | `django-viewflow` | `recipes/django-viewflow/` | `django-viewflow` | 2.4.0 | 2.4.0 | current | local = published (channel and feedstock recipe agree) | none |
| `django-webpack-loader` | `django-webpack-loader` | `recipes/django-webpack-loader/` | `django-webpack-loader` | 3.2.4 | 3.2.4 | current | local = published (channel and feedstock recipe agree) | none |
| `django-compressor`, `django_compressor` | `django_compressor` | `recipes/django_compressor/` | `django-compressor` | 4.6.0 | 4.6.0 | current | local = published (channel and feedstock recipe agree) | none; G53: added cshaley, sannykr |
| `django_coverage_plugin` | `django_coverage_plugin` | `recipes/django_coverage_plugin/` | `django_coverage_plugin` | 3.1.0 | 3.2.2 | behind | local 3.1.0 < published 3.2.2 | refresh-wave 3.1.0 -> 3.2.2; build `success`; meta.yaml mirrored; hand: v1 recipe.yaml authored from the v0 feedstock (C1); feedstock LICENSE and run_test.py copied |
| `djangorestframework-filters` | `djangorestframework-filters` | `recipes/djangorestframework-filters/` | `djangorestframework-filters` | 1.0.0.dev2 | 1.0.0.dev2 | current | local = published (channel and feedstock recipe agree) | none |
| `djangorestframework-jsonapi` | `djangorestframework-jsonapi` | `recipes/djangorestframework-jsonapi/` | `djangorestframework-jsonapi` | 8.1.0 | 9.0.0 | behind | local 8.1.0 < published 9.0.0 | refresh-wave 8.1.0 -> 9.0.0; build `success`; meta.yaml mirrored; hand: run synced (+django-filter, djangorestframework >=3.17, django >=5.2); license BSD-3-Clause -> BSD-2-Clause (sdist LICENSE text, feedstock) |
| `dlt` | `dlt` | `recipes/dlt/` | `dlt` | 1.30.0 | 1.30.0 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live) |
| `docstring_parser_fork` | `docstring_parser_fork` | `recipes/docstring_parser_fork/` | `docstring_parser_fork` | 0.0.16 | 0.0.16 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka; review round: meta.yaml re-copied byte-for-byte from the feedstock |
| `docx2txt` | `docx2txt` | `recipes/docx2txt/` | `docx2txt` | 0.9 | 0.9 | current | local = published (channel and feedstock recipe agree) | none |
| `dpd_components` | `dpd_components` | `recipes/dpd_components/` | `dpd_components` | 0.2.0 | 0.2.0 | current | local = published (channel and feedstock recipe agree) | none |
| `draftjs_exporter` | `draftjs_exporter` | `recipes/draftjs_exporter/` | `draftjs_exporter` | 7.1.0 | 7.3.1 | behind | local 7.1.0 < published 7.3.1 | refresh-wave 7.1.0 -> 7.3.1; build `success`; meta.yaml removed; hand: CFE block added; literal source.url |
| `drf-spectacular` | `drf-spectacular` | `recipes/drf-spectacular/` | `drf-spectacular` | 0.30.0 | 0.30.0 | current | local = published (channel and feedstock recipe agree) | none |
| `dsnparse` | `dsnparse` | `recipes/dsnparse/` | `dsnparse` | 0.4.0 | 0.4.0 | current | local = published (channel and feedstock recipe agree) | none |
| `easy-thumbnails` | `easy-thumbnails` | `recipes/easy-thumbnails/` | `easy-thumbnails` | 2.10.1 | 2.10.1 | current | local = published (channel and feedstock recipe agree) | none |
| `ebcdic-parser` | `ebcdic-parser` | `recipes/ebcdic-parser/` | `ebcdic-parser` | 3.4.0 | 3.4.0 | current | local = published (channel and feedstock recipe agree) | none |
| `fs.googledrivefs` | `fs.googledrivefs` | `recipes/fs.googledrivefs/` | `fs.googledrivefs` | 2.6.2 | 2.6.3 | behind | local 2.6.2 < published 2.6.3 | refresh-wave 2.6.2 -> 2.6.3; build `success`; G53 +pb01ka; meta.yaml mirrored; hand: literal source.url; host python pin .* |
| `gotenberg-client` | `gotenberg-client` | `recipes/gotenberg-client/` | `gotenberg-client` | 1.0.0 | 1.1.0 | behind | local 1.0.0 < published 1.1.0 | refresh-wave 1.0.0 -> 1.1.0; build `success`; G53 +jsmolic; review round: host hatchling >=1.27,<2 and the CFEP-25 test triad synced to the feedstock (CFE comment corrected); rebuilt: success |
| `gprof2dot` | `gprof2dot` | `recipes/gprof2dot/` | `gprof2dot` | 2025.4.14 | 2025.4.14 | current | local = published (channel and feedstock recipe agree) | none |
| `graphene-django` | `graphene-django` | `recipes/graphene-django/` | `graphene-django` | 3.2.3 | 3.2.3 | current | local = published (channel and feedstock recipe agree) | none |
| `hurry.filesize` | `hurry.filesize` | `recipes/hurry.filesize/` | `hurry.filesize` | 0.9 | 0.9 | current | local = published (channel and feedstock recipe agree) | none |
| `kanaries-track` | `kanaries-track` | `recipes/kanaries-track/` | `kanaries-track` | 0.0.5 | 0.0.5 | current | local = published (channel and feedstock recipe agree) | none |
| `kedro-airflow` | `kedro-airflow` | `recipes/kedro-airflow/` | `kedro-airflow` | 0.11.0 | 0.11.0 | current | local = published (channel and feedstock recipe agree) | none |
| `kedro-pack` | `kedro-pack` | `recipes/kedro-pack/` | `kedro-pack` | 0.18.12.1 | 0.18.12.1 | current | local = published (channel and feedstock recipe agree) | none |
| `kedro-telemetry` | `kedro-telemetry` | `recipes/kedro-telemetry/` | `kedro-telemetry` | 0.8.0 | 0.8.0 | current | local = published (channel and feedstock recipe agree) | none |
| `kedro-vertexai` | `kedro-vertexai` | `recipes/kedro-vertexai/` | `kedro-vertexai` | 1.0.0 | 1.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `langchain-milvus` | `langchain-milvus` | `recipes/langchain-milvus/` | `langchain-milvus` | 0.4.0 | 0.4.0 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka; review round: cfe-on-conda-forge-status confirmed-on-conda-forge, feedstock set (verified live, G78) |
| `langchain-unstructured` | `langchain-unstructured` | `recipes/langchain-unstructured/` | `langchain-unstructured` | 1.0.1 | 1.0.1 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka; review round: cfe-on-conda-forge-status confirmed-on-conda-forge, feedstock set (verified live, G78) |
| `markov_draftjs` | `markov_draftjs` | `recipes/markov_draftjs/` | `markov_draftjs` | 2.0.0 | 2.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `micropip` | `micropip` | `recipes/micropip/` | `micropip` | 0.11.1 | 0.11.1 | current | local = published (channel and feedstock recipe agree) | none |
| `minio` | `minio` | `recipes/minio/` | `minio` | 7.2.20 | 7.2.20 | current | local = published (channel and feedstock recipe agree) | none |
| `mssql-django` | `mssql-django` | `recipes/mssql-django/` | `mssql-django` | 1.8.0 | 1.8.0 | current | local = published (channel and feedstock recipe agree) | none |
| `nbqa` | `nbqa` | `recipes/nbqa/` | `nbqa` | 1.9.0 | 1.9.1 | behind | local 1.9.0 < published 1.9.1 | refresh-wave 1.9.0 -> 1.9.1; build `success`; G53 +rxm7706, jsmolic; meta.yaml removed; hand: CFE block added; literal source.url; host/run synced to the feedstock; review round: script gains --no-deps --no-build-isolation, entry point and CFEP-25 test triad synced to the feedstock; rebuilt: success |
| `office365-rest-python-client` | `office365-rest-python-client` | `recipes/Office365-REST-Python-Client/` | `office365-rest-python-client` | 3.0.0 | 2.6.2 | ahead | local recipe.yaml carries upstream 3.0.0 (`version-update-to-3.0.0`); the feedstock has not merged its autotick PRs #23-#26 (3.0.0-3.3.0), so the channel is still 2.6.2 | kept: the local v1 recipe is the pending update; meta.yaml mirror stays 2.6.2 |
| `openfeature-flagd-core` | `openfeature-flagd-core` | `recipes/openfeature-flagd-core/` | `openfeature-flagd-core` | 1.0.0 | 2.0.0 | behind | local 1.0.0 < published 2.0.0 | refresh-wave 1.0.0 -> 2.0.0; build `success`; G53 +pb01ka, jsmolic; hand: run +cbor2 (feedstock); review round: on-conda-forge status confirmed (G78) |
| `openfeature-provider-flagd` | `openfeature-provider-flagd` | `recipes/openfeature-provider-flagd/` | `openfeature-provider-flagd` | 0.5.0 | 0.6.1 | behind | local 0.5.0 < published 0.6.1 | refresh-wave 0.5.0 -> 0.6.1; build `success`; G53 +jsmolic; hand: BFP: host/run pins synced to the feedstock (protobuf >=7.35.1, grpcio >=1.82.1, flagd-core >=2) after the test failed on a protobuf gencode/runtime mismatch; review round: on-conda-forge status confirmed (G78); conda_build_config.yaml comment corrected |
| `openfeature-sdk` | `openfeature-sdk` | `recipes/openfeature-sdk/` | `openfeature-sdk` | 0.10.0 | 0.10.0 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka; review round: cfe-on-conda-forge-status confirmed-on-conda-forge, feedstock set (verified live, G78) |
| `openllm-client` | `openllm-client` | `recipes/openllm-client/` | `openllm-client` | 0.5.7 | 0.5.7 | current | local = published (channel and feedstock recipe agree) | none |
| `openllm-playground` | `openllm-playground` | `recipes/openllm-playground/` | `openllm-playground` | 0.4.44 | 0.4.44 | current | local = published (channel and feedstock recipe agree) | none |
| `openmetadata-airflow-managed-apis` | `openmetadata-airflow-managed-apis` | `recipes/openmetadata-airflow-managed-apis/` | `openmetadata-airflow-managed-apis` | 0.11.5.3 | 0.11.5.3 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-exporter-jaeger` | `opentelemetry-exporter-jaeger` | `recipes/opentelemetry-exporter-jaeger/` | `opentelemetry-exporter-jaeger` | 1.21.0 | 1.21.0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-exporter-jaeger-proto-grpc` | `opentelemetry-exporter-jaeger-proto-grpc` | `recipes/opentelemetry-exporter-jaeger-proto-grpc/` | `opentelemetry-exporter-jaeger-proto-grpc` | 1.21.0 | 1.21.0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-exporter-jaeger-thrift` | `opentelemetry-exporter-jaeger-thrift` | `recipes/opentelemetry-exporter-jaeger-thrift/` | `opentelemetry-exporter-jaeger-thrift` | 1.21.0 | 1.21.0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-exporter-opencensus` | `opentelemetry-exporter-opencensus` | `recipes/opentelemetry-exporter-opencensus/` | `opentelemetry-exporter-opencensus` | 0.52b1 | 0.52b1 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-exporter-otlp` | `opentelemetry-exporter-otlp` | `recipes/opentelemetry-exporter-otlp/` | `opentelemetry-exporter-otlp` | 1.44.0 | 1.45.1 | behind | local 1.44.0 < published 1.45.1 | refresh-wave 1.44.0 -> 1.45.1; build `success`; G53 +xhochy; meta.yaml removed; hand: BFP: run pins `==1.44.0` -> `<version>.*` (feedstock); the driver moves context.version only |
| `opentelemetry-exporter-otlp-proto-grpc` | `opentelemetry-exporter-otlp-proto-grpc` | `recipes/opentelemetry-exporter-otlp-proto-grpc/` | `opentelemetry-exporter-otlp-proto-grpc` | 1.44.0 | 1.45.1 | behind | local 1.44.0 < published 1.45.1 | refresh-wave 1.44.0 -> 1.45.1; build `success`; G53 +xhochy; meta.yaml removed; hand: run synced to the feedstock |
| `opentelemetry-instrumentation-asyncio` | `opentelemetry-instrumentation-asyncio` | `recipes/opentelemetry-instrumentation-asyncio/` | `opentelemetry-instrumentation-asyncio` | 0.65b0 | 0.66b1 | behind | local 0.65b0 < published 0.66b1 | refresh-wave 0.65b0 -> 0.66b1; build `success` |
| `opentelemetry-instrumentation-boto` | `opentelemetry-instrumentation-boto` | `recipes/opentelemetry-instrumentation-boto/` | `opentelemetry-instrumentation-boto` | 0.61b0 | 0.61b0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-instrumentation-boto3sqs` | `opentelemetry-instrumentation-boto3sqs` | `recipes/opentelemetry-instrumentation-boto3sqs/` | `opentelemetry-instrumentation-boto3sqs` | 0.64b0 | 0.64b0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-instrumentation-click` | `opentelemetry-instrumentation-click` | `recipes/opentelemetry-instrumentation-click/` | `opentelemetry-instrumentation-click` | 0.64b0 | 0.66b1 | behind | local 0.64b0 < published 0.66b1 | refresh-wave 0.64b0 -> 0.66b1; build `success`; G53 +jsmolic |
| `opentelemetry-instrumentation-confluent-kafka` | `opentelemetry-instrumentation-confluent-kafka` | `recipes/opentelemetry-instrumentation-confluent-kafka/` | `opentelemetry-instrumentation-confluent-kafka` | 0.65b0 | 0.66b1 | behind | local 0.65b0 < published 0.66b1 | refresh-wave 0.65b0 -> 0.66b1; build `success`; G53 +jsmolic |
| `opentelemetry-instrumentation-elasticsearch` | `opentelemetry-instrumentation-elasticsearch` | `recipes/opentelemetry-instrumentation-elasticsearch/` | `opentelemetry-instrumentation-elasticsearch` | 0.64b0 | 0.64b0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-instrumentation-kafka-python` | `opentelemetry-instrumentation-kafka-python` | `recipes/opentelemetry-instrumentation-kafka-python/` | `opentelemetry-instrumentation-kafka-python` | 0.65b0 | 0.66b1 | behind | local 0.65b0 < published 0.66b1 | refresh-wave 0.65b0 -> 0.66b1; build `success`; G53 +jsmolic |
| `opentelemetry-instrumentation-pymemcache` | `opentelemetry-instrumentation-pymemcache` | `recipes/opentelemetry-instrumentation-pymemcache/` | `opentelemetry-instrumentation-pymemcache` | 0.33b0 | 0.33b0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-instrumentation-sklearn` | `opentelemetry-instrumentation-sklearn` | `recipes/opentelemetry-instrumentation-sklearn/` | `opentelemetry-instrumentation-sklearn` | 0.46b0 | 0.46b0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-instrumentation-tortoiseorm` | `opentelemetry-instrumentation-tortoiseorm` | `recipes/opentelemetry-instrumentation-tortoiseorm/` | `opentelemetry-instrumentation-tortoiseorm` | 0.64b0 | 0.64b0 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-resource-detector-azure` | `opentelemetry-resource-detector-azure` | `recipes/opentelemetry-resource-detector-azure/` | `opentelemetry-resource-detector-azure` | 0.1.5 | 0.1.5 | current | local = published (channel and feedstock recipe agree) | none |
| `opentelemetry-resourcedetector-gcp` | `opentelemetry-resourcedetector-gcp` | `recipes/opentelemetry-resourcedetector-gcp/` | `opentelemetry-resourcedetector-gcp` | 1.12.0a0 | 1.14.0 | behind | local 1.12.0a0 < published 1.14.0 | refresh-wave 1.12.0a0 -> 1.14.0; build `success`; G53 +jsmolic; meta.yaml removed; hand: literal source.url; host hatchling (feedstock); review round: test python_version synced to the feedstock CFEP-25 triad; rebuilt: success |
| `pdfplumber` | `pdfplumber` | `recipes/pdfplumber/` | `pdfplumber` | 0.11.10 | 0.11.10 | current | local = published (channel and feedstock recipe agree) | none |
| `pgjdbc` | `pgjdbc` | `recipes/pgjdbc/` | `pgjdbc` | 42.7.13 | 42.7.14 | behind | local 42.7.13 < published 42.7.14 | refresh-wave 42.7.13 -> 42.7.14; build `success`; G53 +pb01ka; review round: shade patch dropped and build.sh/build.bat mirrored from the feedstock (42.7.14); rebuilt: success, jar carries 55 org/postgresql/shaded/com/ongres classes; on-conda-forge status confirmed (G78) |
| `pigar` | `pigar` | `recipes/pigar/` | `pigar` | 2.2.0 | 2.2.0 | current | local = published (channel and feedstock recipe agree) | none |
| `pip-audit` | `pip-audit` | `recipes/pip-audit/` | `pip-audit` | 2.10.1 | 2.10.1 | current | local = published (channel and feedstock recipe agree) | none |
| `pipdeptree` | `pipdeptree` | `recipes/pipdeptree/` | `pipdeptree` | 3.1.1 | 3.1.1 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live) |
| `pngquant` | `pngquant` | `recipes/pngquant/` | `pngquant` | 3.0.3 | 3.0.3 | current | local = published (channel and feedstock recipe agree) | none; G53: added izahn, killua156, soapy1, owenlamont |
| `poetry-conda` | `poetry-conda` | `recipes/poetry-conda/` | `poetry-conda` | 0.1.7 | 0.1.7 | current | local = published (channel and feedstock recipe agree) | none |
| `pptxgenjs-plus` | `pptxgenjs-plus` | `recipes/pptxgenjs-plus/` | `pptxgenjs-plus` | 4.3.4 | 4.3.5 | behind | local 4.3.4 < published 4.3.5 | refresh-wave 4.3.4 -> 4.3.5; build `success`; G53 +pb01ka; hand: run nodejs bare (G103, feedstock); review round: on-conda-forge status confirmed (G78) |
| `primp` | `primp` | `recipes/primp/` | `primp` | 2.0.1 | 2.0.1 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka |
| `prometheus-fastapi-instrumentator` | `prometheus-fastapi-instrumentator` | `recipes/prometheus-fastapi-instrumentator/` | `prometheus-fastapi-instrumentator` | 8.1.0 | 8.1.0 | current | local = published (channel and feedstock recipe agree) | none |
| `prophecy-build-tool` | `prophecy-build-tool` | `recipes/prophecy-build-tool/` | `prophecy-build-tool` | 1.4.6 | 1.4.6 | current | local = published (channel and feedstock recipe agree) | none; G53: added pb01ka; review round: meta.yaml re-copied byte-for-byte from the feedstock (was 1.3.4), run synced to it (G96), rebuilt `success` (`b8`) |
| `py-yaml12` | `py-yaml12` | `recipes/py-yaml12/` | `py-yaml12` | 0.2.0 | 0.2.0 | current | local = published | owned by Story 25.17; not refreshed here |
| `pydeck` | `pydeck` | `recipes/pydeck/` | `pydeck` | 0.9.3 | 0.9.3 | current | local = published (channel and feedstock recipe agree) | none |
| `pygwalker` | `pygwalker` | `recipes/pygwalker/` | `pygwalker` | 0.5.0.1 | 0.5.0.1 | current | local = published (channel and feedstock recipe agree) | none |
| `pyicu` | `pyicu` | `recipes/pyicu/` | `pyicu` | 2.16.2 | 2.16.2 | current | local = published (channel and feedstock recipe agree) | none |
| `pylint-django` | `pylint-django` | `recipes/pylint-django/` | `pylint-django` | 2.8.0 | 2.8.0 | current | local = published (channel and feedstock recipe agree) | none |
| `pylint-plugin-utils` | `pylint-plugin-utils` | `recipes/pylint-plugin-utils/` | `pylint-plugin-utils` | 0.9.0 | 0.9.0 | current | local = published (channel and feedstock recipe agree) | none |
| `pytest-instafail` | `pytest-instafail` | `recipes/pytest-instafail/` | `pytest-instafail` | 0.5.0 | 0.5.0 | current | local = published (channel and feedstock recipe agree) | none |
| `pytest-robotframework` | `pytest-robotframework` | `recipes/pytest-robotframework/` | `pytest-robotframework` | 4.6.3 | 4.6.3 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live) |
| `python-flanker` | `python-flanker` | `recipes/python-flanker/` | `python-flanker` | 0.9.11 | 0.9.11 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic |
| `python-openid2` | `python-openid2` | `recipes/python-openid2/` | `python-openid2` | 3.2 | 3.2 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic; review round: meta.yaml re-copied byte-for-byte from the feedstock |
| `radon` | `radon` | `recipes/radon/` | `radon` | 6.0.1 | 6.0.1 | current | local = published (channel and feedstock recipe agree) | none |
| `rcssmin` | `rcssmin` | `recipes/rcssmin/` | `rcssmin` | 1.2.2 | 1.3.0 | behind | local 1.2.2 < published 1.3.0 | refresh-wave 1.2.2 -> 1.3.0; build `success`; meta.yaml mirrored; hand: literal source.url |
| `redis-py` | `redis-py` | `recipes/redis-py/` | `redis-py` | 8.1.0 | 8.1.0 | current | local = published (channel and feedstock recipe agree) | none |
| `repoze.lru` | `repoze.lru` | `recipes/repoze.lru/` | `repoze.lru` | 0.8 | 0.8 | current | local = published 0.8 under the corrected name (the old local name repoze-lru is not on the channel, so the first pass read published as None) | none; review round: package.name repoze-lru -> repoze.lru (mirror identity), source path and pypi purl dotted; rebuilt through the driver: success |
| `rise` | `rise` | `recipes/rise/` | `rise` | 5.7.1 | 5.7.1 | current | local = published (channel and feedstock recipe agree) | none |
| `rjsmin` | `rjsmin` | `recipes/rjsmin/` | `rjsmin` | 1.2.5 | 1.3.0 | behind | local 1.2.5 < published 1.3.0 | refresh-wave 1.2.5 -> 1.3.0; build `success`; meta.yaml mirrored; hand: literal source.url |
| `robocorp` | `robocorp` | `recipes/robocorp/` | `robocorp` | 3.1.1 | 3.1.6 | behind | local 3.1.1 < published 3.1.6 | refresh-wave 3.1.1 -> 3.1.6; build `success`; meta.yaml mirrored; hand: CFE block added; literal source.url; run floors synced; host python pin .* |
| `robocorp-tasks` | `robocorp-tasks` | `recipes/robocorp-tasks/` | `robocorp-tasks` | 4.1.1 | 4.1.1 | current | local = published (channel and feedstock recipe agree) | none |
| `robotframework-browser` | `robotframework-browser` | `recipes/robotframework-browser/` | `robotframework-browser` | 19.7.2 | 19.7.2 | current | local = published (channel and feedstock recipe agree) | none |
| `ruamel.yaml.jinja2` | `ruamel.yaml.jinja2` | `recipes/ruamel.yaml.jinja2/` | `ruamel.yaml.jinja2` | 0.2.7 | 0.2.7 | current | local = published (channel and feedstock recipe agree) | none |
| `skranger` | `skranger` | `recipes/skranger/` | `skranger` | 0.8.0 | 0.8.0 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic; review round: meta.yaml re-copied byte-for-byte from the feedstock, recipe.yaml build number synced to it, rebuilt `success` (`b7`) |
| `solvor` | `solvor` | `recipes/solvor/` | `solvor` | 0.6.3 | 0.6.3 | current | local = published | owned by Story 25.17; not refreshed here |
| `sphinx-external-toc` | `sphinx-external-toc` | `recipes/sphinx-external-toc/` | `sphinx-external-toc` | 1.1.0 | 1.1.0 | current | local = published (channel and feedstock recipe agree) | none |
| `splunk-opentelemetry` | `splunk-opentelemetry` | `recipes/splunk-opentelemetry/` | `splunk-opentelemetry` | 2.12.1 | 2.12.1 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic, soapy1 |
| `sqlalchemy-dremio` | `sqlalchemy-dremio` | `recipes/sqlalchemy-dremio/` | `sqlalchemy-dremio` | 3.0.5 | 3.0.5 | current | local = published (channel and feedstock recipe agree) | none |
| `sqlmesh` | `sqlmesh` | `recipes/sqlmesh/` | `sqlmesh` | 0.231.1 | 0.231.1 | current | local = published (channel and feedstock recipe agree) | none; review round: stale local meta.yaml deleted (feedstock is v1-only, verified live) |
| `textstat` | `textstat` | `recipes/textstat/` | `textstat` | 0.7.13 | 0.7.13 | current | local = published (channel and feedstock recipe agree) | none |
| `tika-client` | `tika-client` | `recipes/tika-client/` | `tika-client` | 1.0.0 | 2.0.0 | behind | local 1.0.0 < published 2.0.0 | refresh-wave 1.0.0 -> 2.0.0; build `success`; G53 +jsmolic; review round: test python_version synced to the feedstock CFEP-25 triad; rebuilt: success |
| `timelib` | `timelib` | `recipes/timelib/` | `timelib` | 0.3.0 | 0.3.0 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic; review round: meta.yaml re-copied byte-for-byte from the feedstock, recipe.yaml build number synced to it, rebuilt `success` (`b7`) |
| `tree-sitter-c` | `tree-sitter-c` | `recipes/tree-sitter-c/` | `tree-sitter-c` | 0.24.2 | 0.24.2 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-cpp` | `tree-sitter-cpp` | `recipes/tree-sitter-cpp/` | `tree-sitter-cpp` | 0.23.4 | 0.23.4 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-elixir` | `tree-sitter-elixir` | `recipes/tree-sitter-elixir/` | `tree-sitter-elixir` | 0.3.5 | 0.3.5 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-fortran` | `tree-sitter-fortran` | `recipes/tree-sitter-fortran/` | `tree-sitter-fortran` | 0.6.0 | 0.6.0 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-go` | `tree-sitter-go` | `recipes/tree-sitter-go/` | `tree-sitter-go` | 0.25.0 | 0.25.0 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-groovy` | `tree-sitter-groovy` | `recipes/tree-sitter-groovy/` | `tree-sitter-groovy` | 0.1.2 | 0.1.2 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-java` | `tree-sitter-java` | `recipes/tree-sitter-java/` | `tree-sitter-java` | 0.23.5 | 0.23.5 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-javascript` | `tree-sitter-javascript` | `recipes/tree-sitter-javascript/` | `tree-sitter-javascript` | 0.25.0 | 0.25.0 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-json` | `tree-sitter-json` | `recipes/tree-sitter-json/` | `tree-sitter-json` | 0.24.8 | 0.24.8 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-julia` | `tree-sitter-julia` | `recipes/tree-sitter-julia/` | `tree-sitter-julia` | 0.25.0 | 0.25.0 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-kotlin` | `tree-sitter-kotlin` | `recipes/tree-sitter-kotlin/` | `tree-sitter-kotlin` | 1.1.0 | 1.1.0 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-lua` | `tree-sitter-lua` | `recipes/tree-sitter-lua/` | `tree-sitter-lua` | 0.5.0 | 0.5.0 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-markdown` | `tree-sitter-markdown` | `recipes/tree-sitter-markdown/` | `tree-sitter-markdown` | 0.5.3 | 0.5.3 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-objc` | `tree-sitter-objc` | `recipes/tree-sitter-objc/` | `tree-sitter-objc` | 3.0.2 | 3.0.2 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-powershell` | `tree-sitter-powershell` | `recipes/tree-sitter-powershell/` | `tree-sitter-powershell` | 0.26.5 | 0.26.6 | behind | local 0.26.5 < published 0.26.6 | refresh-wave 0.26.5 -> 0.26.6; build `success`; hand: CFE block added |
| `tree-sitter-ruby` | `tree-sitter-ruby` | `recipes/tree-sitter-ruby/` | `tree-sitter-ruby` | 0.23.1 | 0.23.1 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-rust` | `tree-sitter-rust` | `recipes/tree-sitter-rust/` | `tree-sitter-rust` | 0.24.2 | 0.24.2 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-scala` | `tree-sitter-scala` | `recipes/tree-sitter-scala/` | `tree-sitter-scala` | 0.26.2 | 0.26.4 | behind | local 0.26.2 < published 0.26.4 | refresh-wave 0.26.2 -> 0.26.4; build `success`; hand: CFE block added |
| `tree-sitter-typescript` | `tree-sitter-typescript` | `recipes/tree-sitter-typescript/` | `tree-sitter-typescript` | 0.23.2 | 0.23.2 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-verilog` | `tree-sitter-verilog` | `recipes/tree-sitter-verilog/` | `tree-sitter-verilog` | 1.0.3 | 1.0.3 | current | local = published (channel and feedstock recipe agree) | none |
| `tree-sitter-zig` | `tree-sitter-zig` | `recipes/tree-sitter-zig/` | `tree-sitter-zig` | 1.1.2 | 1.1.2 | current | local = published (channel and feedstock recipe agree) | none |
| `trufflehog` | `trufflehog` | `recipes/trufflehog/` | `trufflehog` | 2.2.1 | 2.2.1 | current | local = published (channel and feedstock recipe agree) | none |
| `trufflehogregexes` | `trufflehogregexes` | `recipes/trufflehogregexes/` | `trufflehogregexes` | 0.0.7 | 0.0.7 | current | local = published (channel and feedstock recipe agree) | none |
| `types-lxml` | `types-lxml` | `recipes/types-lxml/` | `types-lxml` | 2026.2.16 | 2026.2.16 | current | local = published (channel and feedstock recipe agree) | none |
| `urllib3-future` | `urllib3-future` | `recipes/urllib3-future/` | `urllib3-future` | 2.10.902 | 2.25.905 | behind | local 2.10.902 < published 2.25.905 | refresh-wave 2.10.902 -> 2.25.905; build `success`; meta.yaml removed; hand: v1 recipe.yaml authored from the v1 feedstock (C2); local meta.yaml removed by the driver |
| `visions` | `visions` | `recipes/visions/` | `visions` | 0.8.2 | 0.8.2 | current | local = published (channel and feedstock recipe agree) | none |
| `vulture` | `vulture` | `recipes/vulture/` | `vulture` | 2.16 | 2.16 | current | local = published (channel and feedstock recipe agree) | none |
| `wagtail-bakery` | `wagtail-bakery` | `recipes/wagtail-bakery/` | `wagtail-bakery` | 0.8.0 | 0.8.0 | current | local = published (channel and feedstock recipe agree) | none |
| `wagtail-factories` | `wagtail-factories` | `recipes/wagtail-factories/` | `wagtail-factories` | 4.5.0 | 4.5.0 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic; review round: meta.yaml re-copied byte-for-byte from the feedstock |
| `wagtail-tinytableblock` | `wagtail-tinytableblock` | `recipes/wagtail-tinytableblock/` | `wagtail-tinytableblock` | 0.5.0 | 0.5.0 | current | local = published (channel and feedstock recipe agree) | none |
| `wagtailmedia` | `wagtailmedia` | `recipes/wagtailmedia/` | `wagtailmedia` | 0.19.1 | 0.19.1 | current | local = published (channel and feedstock recipe agree) | none; G53: added jsmolic; review round: meta.yaml re-copied byte-for-byte from the feedstock (was 0.18.1) |
| `weasel` | `weasel` | `recipes/weasel/` | `weasel` | 1.0.0 | 1.0.1 | behind | local 1.0.0 < published 1.0.1 | refresh-wave 1.0.0 -> 1.0.1; build `success`; meta.yaml mirrored; hand: run synced (+click, confection >=1.3.4,<2); host/test python pin .* |
| `weasyprint` | `weasyprint` | `recipes/weasyprint/` | `weasyprint` | 69.0 | 69.0 | current | local = published (channel and feedstock recipe agree) | none |
| `webassets` | `webassets` | `recipes/webassets/` | `webassets` | 3.0.0 | 3.0.0 | current | local = published (channel and feedstock recipe agree) | none |
| `whitenoise` | `whitenoise` | `recipes/whitenoise/` | `whitenoise` | 6.12.0 | 6.12.0 | current | local = published (channel and feedstock recipe agree) | none |

### Refresh (AC 3)

Report directories (Tier 3): `_bmad-output/projects/pyforge-mason/implementation-artifacts/refresh-waves/25-18/`
(`dryrun`, `b2-dry`, `b2-dry2`, `b1`, `b2`, `b3`, `b4`, gate re-runs `g1`, `g2`, and the review round's `b5`,
`b6`, `b7`, `b8`). Driver exit codes recorded in a file: `dryrun` 0, `b1` 0, `b2` 1 (the `click-repl` `failed` below),
`b3` 0, `b5` 0, `b6` 0, `b7` 1 (`prophecy-build-tool` red, below), `b8` 0; not recorded (no `.rc` file was written) for
`b2-dry`, `b2-dry2`, `b4`, `g1`, `g2`. Before CFE v8.103.0 a run exited 0 even when a build failed, so read `b1`, `b2`, `b3`
and `b5` by the build status in each report row (`b2`'s 1 came from `click-repl` alone); `b7` ran with the fix and exited 1
on its red build. Every refresh ran
`refresh_wave.py <manifest> --apply --gates --build --report-dir <dir>` from the worktree with the primary checkout's
`local-recipes` env; every build is isolated in `build_artifacts/<name>/` (G52). Rebuilds after a hand fix used
`--rebuild`, so each `cfe-local-build-*` field below was written by its own build (the driver stamps UTC, so the
fields read `2026-11-02T…Z`, the evening of 2026-11-01 local).

First dry-run of the 34: 11 `would-refresh`, 21 `needs-review` (9 `no-cfe-block`, 5 `url-unrenderable`,
7 `dependency-fix`), 2 `blocked` (`no-recipe-yaml`: `django_coverage_plugin`, `urllib3-future`). The hand steps the
skill names as safe cleared them: a canonical CFE block added by hand where none existed, the `source.url` rewritten to
the literal `pypi.org/packages/source/…` form, host/run synced to the deployed feedstock (G96) unless a commented hold
marked a deliberate choice (kept: `caveman-installer`'s host `nodejs 24.*`, `codegraph`'s host `nodejs >=20,<25`),
and a v1 `recipe.yaml` authored at the mirror's old version from the feedstock body for the two v0-only mirrors, so the
driver itself performed the bump (C1 `django_coverage_plugin` keeps the mirrored `meta.yaml`; C2 `urllib3-future` lost
its local `meta.yaml`). A second and third dry-run left all 34 `would-refresh`.

First apply: 33 refreshed and one `failed` before any write (`click-repl`: its sdist filename changed between
versions, so the driver's hash fetch 404'd; the URL was fixed and the next run refreshed it). Of the 33 builds, 22 were
green and 11 red. Build Failure Protocol, one iteration each, root cause per recipe:

- `python ${{ python_min }}` without `.*` is not a v1 match spec (`bentoml`, `confection`, `django-mptt`,
  `django-reversion`, `django-test-plus`; fixed before their build in `fs.googledrivefs`, `robocorp`, `weasel`):
  given `.*`.
- The mirror lacked a feedstock file the recipe names: `confection` and `weasel` `patches/`, `django-test-plus`
  `LICENSE` and `run_test.py` (G94); mirrored verbatim.
- The driver moves `context.version` only, and its G96 diff compares dependency names, not pins:
  `openfeature-provider-flagd` 0.6.1 failed its test on a protobuf gencode 7.35 / runtime 6.33 mismatch, and
  `opentelemetry-exporter-otlp` kept `==1.44.0` sibling pins; both synced to the feedstock's pins.
- `django-health-check` 4.11.3 needs Python >= 3.14: the feedstock's `python_min: "3.14"` added to `context`.
- `caveman-installer` 4.0.1 renamed `LICENSE.BSL` to `LICENSE-MIT` ("No license files were copied"): synced.
- `codegraph` 1.6.2 builds a `ui` workspace (`vite: not found`): write `pnpm-workspace.yaml` before `pnpm install`,
  as the feedstock's `build.sh` does.
- `djangorestframework-jsonapi` declared `BSD-3-Clause`; the sdist's LICENSE has two clauses and the feedstock says
  `BSD-2-Clause`: corrected.

Final state: **34 of 34 build green on linux-64** (CAP-35 outcome: green build); none needed a G95 block or a
`needs-review` end state. Gates after the last edit: `validate` 0 on all 34 (at first apply it exited 1 on exactly the
18 recipes where the driver had added a maintainer; see below), `check-deps` 0 and `scan` 0 on all 34. `optimize`
exits 1 on 19 of the 34, and every remaining code mirrors the deployed feedstock:

- STD-002 on the 12 C1 mirrors (`meta.yaml` kept beside `recipe.yaml`, expected);
- TEST-002 on `bentoml`, `django-mptt`, `django-reversion`, `fs.googledrivefs`, `robocorp` (their v0 feedstocks test
  on `python {{ python_min }}` only) and on `urllib3-future` (its v1 feedstock pins `python_version` to python_min);
- DEP-002 (`python … ,<4`) on `django-health-check`, `gotenberg-client`, `nbqa`, `robocorp`, `tika-client`, each in
  the feedstock's run;
- SEL-002 on `django-health-check` and `django-test-plus`, whose feedstocks test Django through script tests;
- DEP-001 on `django-test-plus` (the feedstock's run carries `pytest`; the package is a test helper);
- PIN-001 on `openfeature-flagd-core` and `opentelemetry-exporter-otlp-proto-grpc` (the feedstock's exact pins).

The first version of this record said every code was carried by the feedstock. It was not true for TEST-002 on
`gotenberg-client`, `tika-client` and `opentelemetry-resourcedetector-gcp`, nor for SEL-002 on `nbqa`: those feedstocks
test on the CFEP-25 triad. The review round synced those tests (plus `gotenberg-client`'s host `hatchling >=1.27,<2`
and `nbqa`'s `--no-deps --no-build-isolation`) and rebuilt all four through the driver (`b5`, green). Hand-step
reasons sit in each recipe's `# CFE comments` header.

**Files changed after their final build (disclosed).** The 34 refreshed `recipe.yaml` files changed after their last
driver build only in non-body text: the driver's comment dates (2026-11-02 rewritten to 2026-11-01), maintainer lines
moved back above `#### CFE metadata` (same list, same order), hand-step and review-round comment lines, and CFE
metadata (`cfe-on-conda-forge-*`, `cfe-generated-at-datetime`). The recipe each build packaged
(`info/recipe/recipe.yaml`) carries the same body, so the report rows' `recipe_sha256` values no longer match the
files. Every recipe whose body changed in the review round was rebuilt through the driver (`b5`, `b6`), and its four
`cfe-local-build-*` fields equal its new report row.

| Recipe | Version | linux-64 build | validate | optimize | check-deps | scan | G53 added | meta.yaml |
|---|---|---|---|---|---|---|---|---|
| `bentoml` | 1.4.39 -> 1.4.40 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `caveman-installer` | 2.7.0 -> 4.0.1 | success | 0 | 0 | 0 | 0 | pb01ka | - |
| `click-repl` | 0.3.0 -> 0.4.1 | success | 0 | 0 | 0 | 0 | jsmolic | removed |
| `codegraph` | 1.6.0 -> 1.6.2 | success | 0 | 0 | 0 | 0 | pb01ka | - |
| `confection` | 1.3.3 -> 1.3.4 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `django-health-check` | 4.8.0 -> 4.11.3 | success | 0 | 1 | 0 | 0 | jsmolic | - |
| `django-mptt` | 0.18.0 -> 0.21.0 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `django-reversion` | 6.3.0 -> 6.5.0 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `django-test-plus` | 2.6.2 -> 2.7.0 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `django_coverage_plugin` | 3.1.0 -> 3.2.2 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `djangorestframework-jsonapi` | 8.1.0 -> 9.0.0 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `draftjs_exporter` | 7.1.0 -> 7.3.1 | success | 0 | 0 | 0 | 0 | - | removed |
| `fs.googledrivefs` | 2.6.2 -> 2.6.3 | success | 0 | 1 | 0 | 0 | pb01ka | mirrored |
| `gotenberg-client` | 1.0.0 -> 1.1.0 | success | 0 | 1 | 0 | 0 | jsmolic | - |
| `nbqa` | 1.9.0 -> 1.9.1 | success | 0 | 1 | 0 | 0 | rxm7706, jsmolic | removed |
| `openfeature-flagd-core` | 1.0.0 -> 2.0.0 | success | 0 | 1 | 0 | 0 | pb01ka, jsmolic | - |
| `openfeature-provider-flagd` | 0.5.0 -> 0.6.1 | success | 0 | 0 | 0 | 0 | jsmolic | - |
| `opentelemetry-exporter-otlp` | 1.44.0 -> 1.45.1 | success | 0 | 0 | 0 | 0 | xhochy | removed |
| `opentelemetry-exporter-otlp-proto-grpc` | 1.44.0 -> 1.45.1 | success | 0 | 1 | 0 | 0 | xhochy | removed |
| `opentelemetry-instrumentation-asyncio` | 0.65b0 -> 0.66b1 | success | 0 | 0 | 0 | 0 | - | - |
| `opentelemetry-instrumentation-click` | 0.64b0 -> 0.66b1 | success | 0 | 0 | 0 | 0 | jsmolic | - |
| `opentelemetry-instrumentation-confluent-kafka` | 0.65b0 -> 0.66b1 | success | 0 | 0 | 0 | 0 | jsmolic | - |
| `opentelemetry-instrumentation-kafka-python` | 0.65b0 -> 0.66b1 | success | 0 | 0 | 0 | 0 | jsmolic | - |
| `opentelemetry-resourcedetector-gcp` | 1.12.0a0 -> 1.14.0 | success | 0 | 0 | 0 | 0 | jsmolic | removed |
| `pgjdbc` | 42.7.13 -> 42.7.14 | success | 0 | 0 | 0 | 0 | pb01ka | - |
| `pptxgenjs-plus` | 4.3.4 -> 4.3.5 | success | 0 | 0 | 0 | 0 | pb01ka | - |
| `rcssmin` | 1.2.2 -> 1.3.0 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `rjsmin` | 1.2.5 -> 1.3.0 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `robocorp` | 3.1.1 -> 3.1.6 | success | 0 | 1 | 0 | 0 | - | mirrored |
| `tika-client` | 1.0.0 -> 2.0.0 | success | 0 | 1 | 0 | 0 | jsmolic | - |
| `tree-sitter-powershell` | 0.26.5 -> 0.26.6 | success | 0 | 0 | 0 | 0 | - | - |
| `tree-sitter-scala` | 0.26.2 -> 0.26.4 | success | 0 | 0 | 0 | 0 | - | - |
| `urllib3-future` | 2.10.902 -> 2.25.905 | success | 0 | 1 | 0 | 0 | - | removed |
| `weasel` | 1.0.0 -> 1.0.1 | success | 0 | 1 | 0 | 0 | - | mirrored |

### Findings for the CFE retro

- `refresh_wave.py`'s G53 union appends new handles with `recipe_editor` `add_to_list`, which ruamel places after the
  comment block attached to the last list item: the new `    - <handle>` lines land under `#### CFE metadata` /
  `# CFE metadata`. YAML still parses them into the list and the write check passes, but conda-smithy's lint (via
  conda-recipe-manager) then fails `validate` (all 18 recipes here that gained a handle; Story 25.7 hit the same on two). Moving the lines back
  above the marker restored `validate` 0 with no other change.
- `_dependency_diff` (G96) compares names, and pins only where a maintainer comment sits on the item, so a version-only
  bump keeps stale pins (`openfeature-provider-flagd` protobuf 6 vs gencode 7; `opentelemetry-exporter-otlp`
  `==1.44.0`). A pin-level diff against the feedstock would have reported both as `dependency-fix`.
- The driver's `url-unrenderable` check also fires on `${{ name[0] }}` with `name` absent from `context`, but a
  sdist filename that changes between versions (`click-repl-0.3.0` to `click_repl-0.4.1`) surfaces only as an
  `edit-failed` 404 on `files.pythonhosted.org`; the failure message names the hashed host, not the canonical URL.
- The driver dates its `# CFE comments` line with the UTC calendar date (`2026-11-02` for a run at 20:31 CST); the
  lines were rewritten to the operator's date.
- Mirrors still miss feedstock files the recipe names (`patches/`, `LICENSE`, `run_test.py`); a listing check of the
  feedstock's `recipe/` against the mirror before the build would catch them (G94).
- `refresh_wave.py` exits 0 when a build fails: a build failure leaves the outcome `refreshed` or `already-current`,
  and only a `failed` outcome sets exit 1. `b1` exited 0 with four red builds, `b3` with `weasel` red, and `b5` with `django-libsass`
  red. The build status lives only in each report row, so a caller reading the exit code alone sees green.
- A version match does not prove mirror fidelity: current-bucket mirrors carried a `meta.yaml` two releases old
  (`prophecy-build-tool`, `wagtailmedia`), a `meta.yaml` the v1-only feedstock no longer has (7 recipes), a structurally
  stale `recipe.yaml` (`django-libsass`) and a `package.name` the channel does not carry (`repoze.lru`). A
  re-bucket that compares versions only cannot see any of them; a byte compare of each mirrored file against the
  feedstock's `recipe/` can.
- Subtracting the stories that already refreshed a mirror trusts history: 55 of those 99 were behind again on the same
  snapshot. A re-bucket of a set should re-derive every member live, not only the ones no story touched.

## Auto Run Result

Status: done

Summary (2026-11-01, landed in one PR with marshal 113.14, mason 25.17 and steward 118.7/118.8, operator 2026-11-01):
- AC1: the live scope is 191 feedstocks, recorded before any refresh, with every package named by its feedstock (§ Run record).
- AC2: every output of 194 recipes is bucketed by its own version with its reason: 156 current, 34 behind, 1 ahead, 0 non-PEP 440.
- AC3: the 34 behind recipes refreshed through `refresh-wave --apply --gates --build`, and all 34 are green on linux-64; every touched recipe's maintainer list is a superset of the deployed feedstock's (G53).
- AC4: the one ahead recipe (`Office365-REST-Python-Client`) carries its reason: the local recipe is the feedstock's pending update.
- AC5: `DW-mason-25-14` closed with its `verified:` line.
- AC6: local only; nothing left `rxm7706/local-recipes`.
- AC7: the `retro(cfe):` commit lands CFE v8.103.0, shared with Story 25.17.
- AC8: `pyforge-mason-test` runs in the landing PR's preflight once the retro commit exists (its CFE-surface guards refuse an uncommitted CFE edit).
- Deferrals: `DW-mason-25-18` (55 refreshed feedstocks behind again; outside this story's boundary).
- Independent review: three rounds, every finding fixed (see the Review Triage Log).

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding MAS-D-C4, cluster
  `mason-c09-wave-a-residue`; fix under `spec-pyforge-mason` CAP-35, no new CAP; parked at `backlog`.
- 2026-11-01: § Run record added: 191 live no-refresh feedstocks bucketed per output (156 current, 34 behind,
  1 ahead, 0 non-PEP 440); the 34 behind refreshed through refresh-wave, 34 of 34 green on linux-64; G53 superset
  restored on 16 current recipes; `DW-mason-25-14` closed against § Method step 2.
- 2026-11-01: review round: 55 of the 99 excluded feedstocks listed as behind again and deferred
  (`epic-25-refreshed-mirrors-behind-again`); mirror fidelity fixed on 15 current recipes (7 `meta.yaml` re-copied,
  7 deleted, `django-libsass` rebuilt), `repoze.lru` identity fixed, `pgjdbc` patch dropped, four tests synced to their
  feedstocks; 8 recipes' on-conda-forge fields confirmed live; optimize claim corrected; all rebuilds green.
- 2026-11-01: second review round: the 55-versus-54 difference is named (`dbt`), the missing exit codes are stated as not
  recorded, `skranger` and `timelib` carry the feedstock's build number, `prophecy-build-tool` rebuilt green after its run
  sync; status `done`.

## Review Triage Log

- 2026-11-01 — independent review 1 (separate agent, read-only): findings, all fixed: the 55 feedstocks behind again were unlisted (listed, deferred as `DW-mason-25-18`); `meta.yaml` mirrors stale on 7 current recipes and left beside v1-only feedstocks on 7 (re-copied, deleted); `django-libsass` structurally stale (rebuilt from its feedstock); CFEP-25 tests behind their feedstocks on four recipes (synced, rebuilt) and an optimize claim that overreached (rewritten); `repoze.lru` package name wrong (fixed, rebuilt); `pgjdbc` carried a stale patch (dropped; build scripts from the feedstock); eight recipes' on-conda-forge fields stale (set from live feedstocks); nits on times, duplicate CFE comments and exit codes.
- 2026-11-01 — re-review 2: every fix verified by blob sha, record field and `deferred-work-check`; nits taken: the 55-versus-54 difference named (`dbt`), driver exit codes stated as recorded or not, `skranger` and `timelib` build numbers synced and rebuilt, `prophecy-build-tool`'s `failed` record replaced by a real green build (`b8`).
- 2026-11-04 — review 3 of that last round (separate agent, read-only): `build.number`, `prophecy-build-tool`'s run list and every record checked against `meta.yaml` and the newest report rows; all hold. One nit taken: `b3` and `b2`'s red builds named beside `b1` and `b5`.
