---
status: in-progress
implemented_by: bmad-quick-dev
shipped_ref: "Waves B–F (behind set, 252 recipes) SHIPPED: 363537dd43 + 1fe1848b43 (pushed origin/main, not submitted to cf). REOPENED 2026-06-21 for Wave H — total-coverage follow-up (155 not-behind-v0→v1 + 24 missing = 179 sole) per the 769-coverage analysis in co-maintainer-feedstock-refresh.md."
spec_updated: 2026-06-21
---
# Tech Spec: Sole-Maintainer Feedstock Refresh (bulk local-recipe ↔ feedstock version sync)

> **BMAD intake document.** Parameterized, BMAD-consumable. Written for
> `bmad-quick-dev` / `bmad-dev`. The **bulk-orchestration** layer over the
> per-feedstock procedure in `feedstock-platform-expansion.md` — it decides
> *which* feedstocks to refresh and *in what order*, and delegates the
> per-feedstock "how" to that guide + the `conda-forge-expert` skill.
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/sole-maintainer-feedstock-refresh.md
> ```
>
> **Three pillars (same as feedstock-failure-remediation):** (1) **BMAD** drives
> execution; (2) the **`conda-forge-expert` skill** is the authoritative interface
> for *all* conda-forge work (regen / migrate / build / platform-expand); (3) the
> **conda-forge-atlas** supplies the version-delta + sole-maintainer facts.

---

## Status

| Field | Value |
| ----- | ----- |
| Status | **SHIPPED (local-only) 2026-06-21.** All waves complete + committed. Wave A re-baselined to **256 BEHIND**. **Wave B (v1-refresh, 55)** — `1fe1848b43`. **Waves C–F (197 recipes: C 174 v0-migration, D 10 compiled/host-blocked, E 13 gh-numbering) + CFE skill v8.40.0 (G46–G51)** — `363537dd43`. Build tally: 190 success, 4 build-clean-test-blocked, 3 not-attempted (osx/win host-blocked). Committed + pushed to `origin/main`; **NOT submitted to conda-forge** (deliberate — no-push hard rule + Q2 defers feedstock v0→v1 PRs to a separate wave). Per-recipe results in the Review Digest below; deferred work in Follow-ups. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only) |
| Scope | Every `recipes/<name>/` that backs a **sole-maintainer** conda-forge feedstock and is **behind** the feedstock's published version. |
| Goal | Bring each local recipe up to its feedstock's published version via **full CFE regenerate (diff-apply)**, modernizing grayskull regressions, folding in **platform expansion where the recipe is compiled**, and migrating **v0 feedstocks** to v1. |
| Hard rule | **No auto-commit, no push** *by default* — everything stays uncommitted for the user's per-recipe `git diff` review. **Exception (Q1 resolved):** the user may explicitly authorize a **per-bucket grouped commit after reviewing** (Wave B was committed `1fe1848b43` on explicit instruction); even then, do NOT push without a separate explicit instruction. |
| Predecessors | `feedstock-platform-expansion.md` (per-feedstock how-to — delegated), `feedstock-failure-remediation.md` (reactive sibling). Memory: `project_sole_maintainer_feedstock_update`. |

---

## Parameters (set per run)

```
<batch_size>      : recipes per wave-batch (default 5; ≤3 if rate-limited — see G-rate note)
<wave_filter>     : which bucket(s) to process this run — v1-refresh | v0-migration | gh-numbering | compiled-platform | all
<recipe_filter>   : optional explicit recipe list (overrides the bucket pick)
<commit_mode>     : ALWAYS "none" — never commit/push (hard rule; not operator-overridable without an explicit user instruction in the run prompt)
<platform_targets>: for the compiled bucket — default [osx-arm64, linux-aarch64] (drop ppc64le), per feedstock-platform-expansion.md
<atlas_max_age_d> : refresh the atlas if older than this many days (default 3)
```

---

## Background

`rxm7706` maintains **769** conda-forge feedstocks; **537 are sole-maintainer**
(535 active). **512** local recipes in `recipes/` back a sole-maintainer feedstock.
The local mirror is the source of truth ([[feedback_local_mirror_first_then_verify_then_push]]),
but ~half drifted behind their published feedstock and ~80% carry grayskull-era
regressions (raw `python >=3.8` instead of `python_min` machinery, homepage→PyPI
drift, junk skip/stub blocks, empty descriptions). This effort closes that drift.

### The BEHIND working set — RE-BASELINED 2026-06-19 (256 entries)

Persisted at **`.claude/data/conda-forge-expert/feedstock-update/behind_verified.json`**
(256 entries; fields `dir, conda, feedstock, local, target, fmt, fs_fmt, bucket, gh_numbering`),
plus `sole_maint.txt` (the 535), `behind.json` (raw delta), `behind_summary.md` (bucket
tables), and `behind_verified.prev_2026-06-13.json` (the prior 258 snapshot). The 256 split
(against cf_atlas rebuilt 2026-06-19 21:55):

| Bucket | Count | Status | What it needs |
| ------ | ----- | ------ | ------------- |
| **v1-refresh** | **55** | ✅ **DONE** (Wave B, commit `1fe1848b43`) | feedstock already v1; regen `recipe.yaml` to published version + modernize. |
| **v0-migration** | **184** | ✅ **DONE** (Waves C+D, commit `363537dd43`) — 174 noarch in Wave C + 10 compiled/host-blocked re-routed to Wave D | local recipe is v0 (`meta.yaml`). **Two action-classes by FEEDSTOCK format — see Wave C.** |
| **gh-numbering** | **13** | ✅ **DONE** (Wave E, commit `363537dd43`) — re-verified + refreshed | feedstock sources a GitHub **tag** whose number ≠ PyPI/local (copilotkit `v1.57.2`=PyPI`0.1.88`). **NOT actually behind** — re-verify, do not blindly bump. |
| **fs-unknown** | **4** | ✅ resolved at processing (folded into the buckets above) | newly-behind dirs, feedstock format unverified — live-checked at processing. |
| (AHEAD) | 9 | — | local newer than published (in-flight, e.g. cocoindex). Out of scope. |

**Wave-C critical refinement (discovered 2026-06-20):** the "v0-migration" bucket is keyed
on the **local** recipe being v0, but the **feedstock** format varies and *determines whether
meta.yaml is kept or deleted* ([[feedback_keep_meta_yaml_until_feedstock_migrates]]):
- **C1 — KEEP-meta (feedstock still v0): 141** → author v1 `recipe.yaml` AND keep the (latest-pulled) `meta.yaml`; both coexist; `cfe-forge-recipe-updates-needed: meta-yaml-to-recipe-yaml`.
- **C2 — catch-up (feedstock ALREADY v1): 43** → the feedstock completed v0→v1 but our local mirror lags at v0; author `recipe.yaml` to match the v1 feedstock and **DELETE the local `meta.yaml`** (mirror catches up). This is effectively a v1-refresh where the local was stale.

### Landmines (from the 2026-06-19 pilot-of-5 `ovld/copilotkit/a2wsgi/django-auditlog/selectolax`)

1. **GitHub-tag-numbering false positives** — `generate_recipe_from_pypi(version=<feedstock-tag>)` 404s when the feedstock tag ≠ PyPI version. **Live-verify each candidate against the feedstock + PyPI before any regen** (Wave A does this for the whole set).
2. **Atlas staleness** — the delta is only as fresh as the atlas build; refresh first.
3. **Grayskull regressions are the norm**, not the exception — the regen modernizes them; expect large-but-correct diffs.
4. **Pure-Python ≠ platform expansion** — most of the 512 are noarch Django/Wagtail; platform-widen ONLY the compiled subset ([[feedback_noarch_platforms_pure_python_waste]]).
5. **Rate-limit zombies (Wave-B lesson).** Launching **6 regen+build agents at once** stalled 4 of them at the server-side 429 wall; they never recovered — output frozen at the 169-byte launch header for ~56 min, **no completion notification ever fired**. Detection: `stat -c %Y` the agent output file; stale (>1800s) + tiny = zombie. Recovery: `TaskStop` (often already dead), `git checkout HEAD --` the partially-edited recipes, re-run. **Hold a strict ≤4-concurrent cap for regen/build agents** (heavier than the metadata-rollout agents that tolerated 4–6).
6. **`'releases' KeyError` in the version-pinned generator.** `generate_recipe_from_pypi(version=X)` can raise `KeyError: 'releases'`; the **latest-version path works** — fall back to it (or hand-edit version+sha256) when the published target == PyPI latest (usually true for a feedstock-version refresh).
7. **conda-smithy v1 lint renders jinja inside `#` comments.** A `# CFE comment` containing literal `${{ name|lower }}` (e.g. describing a legacy chain) crashes `validate` with `'name' is undefined`. cfe-comments must avoid renderable `${{ }}` — rephrase (e.g. `name-lower`).
8. **Recipe-local CBC must be passed LAST.** When a recipe ships a `conda_build_config.yaml` to raise `python_min` (G31/G41 hidden floor), pass it AFTER the repo-pinning CBC on the `rattler-build --variant-config` chain — variant config is last-wins, else the repo default (3.10) overrides it.
9. **`cfe-forge-recipe-updates-needed` token discipline.** Agents drift into coined values (`recipe-modernization`, `drop-context-name`, `run-deps-stale-on-feedstock`). Pin the canonical vocabulary in every prompt: modernization debt → `recipe-regenerate`; stale deps → `dependency-fix`; else `none`. Normalize post-hoc if drift slips through.

---

## Implementation Plan (waves)

### Wave A — Re-baseline (do first, every resume)
- **A1 — refresh the atlas** if older than `<atlas_max_age_d>` (`build-cf-atlas`, maintainer profile). Records the current published versions.
- **A2 — recompute sole-maintainer + version-delta** → regenerate `sole_maint.txt` + `behind.json` + `behind_verified.json` under `.claude/data/conda-forge-expert/feedstock-update/`.
- **A3 — live re-verify** each BEHIND candidate against its feedstock + PyPI (GH-numbering guard): confirm `local < published` is REAL and `generate_recipe_from_pypi(version=published)` resolves (no 404). Re-bucket: v1-refresh / v0-migration / gh-numbering / compiled-platform / drop-false-positive.
- **A4 — subtract the already-done** (~25 from the prior effort; check working-tree vs the list). Output the accurate remaining set + per-bucket counts. **Gate:** present the re-baselined counts before Wave B.

### Wave B — v1-refresh bucket (~103)
Per recipe, via the CFE skill: `generate_recipe_from_pypi` (or `update_recipe`) at the published version → modernize (python_min machinery, about-order, CFEP-25 triad, cfe-* FINAL-schema block, comments-at-bottom) → `validate` + `optimize` + `scan` → **build locally** (rattler-build for v1) → leave uncommitted. Batch in `<batch_size>`; **the user reviews every diff.**

### Wave C — v0-migration bucket (184, the bulk) — TWO action-classes by feedstock format
First read each recipe's `fs_fmt` from `behind_verified.json` (or live-check via `lookup_feedstock`):
- **C1 — KEEP-meta (feedstock v0, 141):** pull the feedstock's latest `meta.yaml` and **keep it** alongside a new v1 `recipe.yaml` ([[feedback_keep_meta_yaml_until_feedstock_migrates]]); the `recipe.yaml` carries `cfe-forge-recipe-updates-needed: [meta-yaml-to-recipe-yaml, …]`; build/test/lint target `recipe.yaml` **explicitly** (`rattler-build --recipe …/recipe.yaml`); STD-002 "both files present" is an expected, harmless warning — do NOT delete meta.yaml to silence it.
- **C2 — catch-up (feedstock already v1, 43):** the feedstock finished v0→v1; author `recipe.yaml` to match the deployed v1 feedstock and **DELETE the local `meta.yaml`** (mirror catches up). Treat like Wave B otherwise.

Both: batch in `<batch_size>` (**strict ≤4 concurrent** — see Wave-B rate-limit lesson); modernize grayskull regressions; cache `cfe-import-names` (G7); strictly-canonical `cfe-forge-recipe-updates-needed` tokens; review every diff; no commit (unless the user authorizes a per-bucket commit).

### Wave D — compiled-platform bucket (subset of B/C that are compiled)
For compiled BEHIND recipes, also widen the matrix to `<platform_targets>` per
`feedstock-platform-expansion.md` (the per-feedstock decision matrix + Wave A/B/C
procedural detail live there — do not duplicate). Gate each behind a
`@conda-forge-admin, please add user` issue only if the feedstock has co-maintainers
(here: sole-maintainer, so no gating needed).

### Wave E — gh-numbering bucket (13)
Special-case: the feedstock tracks a GitHub tag, not PyPI. Re-map the version
correctly (or confirm not-behind) before any change. Most will be **no-ops**.

### Wave F — Closeout
- Per-recipe diffs sit uncommitted for the user's review + manual commit/push.
- **CFE-skill retro** (Rule 2) folds in whatever the bulk refresh surfaces (new
  gotchas, recurring grayskull-regression patterns worth a `recipe-generator.py` fix).

### Wave H — total-coverage follow-up (added 2026-06-21; Waves B–F were behind-scoped)
Waves B–F closed the **behind** sole recipes; the total-coverage goal — *every* sole
feedstock in build-green `recipe.yaml` so the only remaining step is submitting PRs —
additionally needs the **version-current-but-still-v0** recipes migrated and the
**missing** ones created. Live scan 2026-06-21: **155 sole meta.yaml-only (v0)** +
**24 sole missing** = **179** remaining. (A recipe at the correct version in `meta.yaml`
is NOT submission-ready — it still needs v0→v1.)
- **H1 — migrate the 155 not-behind v0:** author a modern v1 `recipe.yaml` (same C1/C2
  rule by feedstock format), full v8.40.0 cfe-* block, build-green — the migration is
  format + modernization, not a version bump.
- **H2 — create the 24 missing:** resolve dir↔conda mapping FIRST (some exist under a
  different dir name — upper-bound count); pull + author the genuine net-new mirrors.
- Work-list: `.claude/data/conda-forge-expert/feedstock-update/total_coverage_queue.json`
  (`role=sole` AND `action∈{v0-migrate, create-missing}`). Same hard rules, ≤4 concurrent,
  review every diff, no commit/push without explicit instruction. Runs alongside the
  co-maintainer sweep (`co-maintainer-feedstock-refresh.md`) toward all-769 coverage.

---

## Open Questions

- **Q1 — commit cadence. RESOLVED (2026-06-20):** per-bucket grouped commit after the
  user reviews, on explicit instruction (Wave B → `1fe1848b43`). No push without a
  separate explicit instruction. Default remains uncommitted between authorized commits.
- **Q2 — v0-migration depth.** Do we migrate the **feedstock** too (open the v0→v1 PR),
  or only the local mirror now and defer the feedstock PR? Spec default: local mirror
  only this effort; feedstock v0→v1 PRs are a separate, later submission wave (the
  `meta-yaml-to-recipe-yaml` flag tracks the debt).
- **Q3 — AHEAD-10 handling.** Confirm the 10 AHEAD are all intentional in-flight work
  (leave alone) vs. any that are accidental local-only bumps to reconcile.
- **Q4 — scale/automation.** 258 recipes is large; run as paced multi-agent batches
  (≤3–5 concurrent per the rate-limit calibration) over multiple sessions, or a subset
  per run via `<recipe_filter>`?

---

## Worked Examples

**Run 1 — 2026-06-19 (partial, pre-pause).** Pilot-of-5 (`ovld, copilotkit,
a2wsgi, django-auditlog, selectolax`) invalidated the naive bump plan (copilotkit
GH-numbering false-positive) and set the live-re-verify rule. **Applied:** Wave-1
Batch-1 (`a2wsgi`, `condense-json`, `collate-data-diff`, `antlr4-tools`,
        `collate-sqllineage` — all v0→v1, build-green) + ~20 recipes swept into the cfe-*
        metadata/full-loop pass (incl. `db-gpt` built 7/7 green; `podman` reverted to v0).
        All uncommitted; HEAD stayed `d8f3c8a3cb`. ~230 BEHIND never reached. See memory
        `project_sole_maintainer_feedstock_update`.

**Run 2 — 2026-06-19/20 (this resume).**
- **Wave A:** atlas rebuilt (2026-06-19 21:55); re-baselined 258→**256 BEHIND** (6 resolved, 4 newly-behind, 9 AHEAD). Buckets: 55 v1-refresh / 184 v0-migration (141 keep-meta + 43 catch-up) / 13 gh-numbering / 4 fs-unknown.
- **Schema work folded in alongside:** shipped cfe-* fields **v8.36.0** (`cfe-local-build-*` verified-build record) + **v8.37.0** (Tier-1 `cfe-import-names`/`-source-kind`/`-noarch`/`-pip-check` + design principle + retired dead SBOM placeholders), from a 4-analyst deep-analysis. Wave B recipes carry the full v8.37.0 block.
- **Wave B (v1-refresh, 55) DONE** — 53 build-green, 1 build-clean-test-blocked (ydata-profiling, G34 setuptools-81), 1 not-attempted (openmetadata-ingestion, heavy). Committed `1fe1848b43` (user-authorized per-bucket commit; not pushed). 18 stale meta.yaml deleted; 13 recipes flag feedstock debt.
  - **`cfe-import-names` proved its worth:** ~12 G7 import divergences cached, incl. a *pre-existing wrong import* on `django-soft-delete` (`django_soft_delete`→`django_softdelete`); also `md2conf`, `wagtailseo`, `issues`, `flags`, `treenode`, `sqlfluff`, `key_value.*` (dotted), `opentelemetry.instrumentation.kafka`.
  - **High-value feedstock-defect catches:** `wagtail-draftail-plugins` deployed feedstock ships the **WRONG license** (`MIT`; upstream relicensed `ISC`) + stale `wagtail` pin + G31 ci_support skew; `gibr`/`ydata-profiling` caught **impending feedstock rebuild breakages** (G26 exact-pin drift; G34 setuptools-81); `mcp-django`/`django-components` found latent missing deps live feedstocks carry.
  - **Process retro:** landmines 5–9 above (rate-limit zombies, `'releases'` KeyError, jinja-in-comments, last-wins CBC, token drift) all surfaced here.
- **Waves C–F (v0-migration 174 + compiled/host-blocked 10 + gh-numbering 13 = 197) COMPLETE** — committed `363537dd43` (2026-06-21), pushed to `origin/main`, **nothing submitted to conda-forge**. C split into C1 keep-meta + C2 catch-up-delete-meta; both action-classes validated. Build tally: **190 success, 4 build-clean-test-blocked, 3 not-attempted** (osx/win host-blocked: pyobjc-framework-{applicationservices,systemconfiguration}, uiautomation). Per-recipe detail in the **Review Digest** above. **Wave F closeout = CFE skill retro shipped v8.40.0 (G46–G51)**, plus 8 human-triage follow-ups (see Follow-ups below). Wave-C catches: dataprofiler G34(setuptools-82)+G26(requests-metadata); basedtyping py3.14-incompat → drop `"*"` test leg; cucumber-expressions uv-build drift; ag-ui-protocol G7 `ag_ui`; h2o-lightwave-web empty-package (G51); h2o stale-CBC cruft (G47).

**Run 3 — 2026-06-21 (Wave H total-coverage follow-up; STARTED, PAUSED at weekly limit).**
The behind-scoped Waves B–F left **179 sole** recipes un-migrated (155 not-behind-v0
+ 24 missing) — surfaced by the 769-coverage analysis in
`co-maintainer-feedstock-refresh.md`. Wave H reopened this spec and ran alongside the
co-maintainer sweep: pilot `amundsen-common` + batch `amundsen-metadata` / `amundsen-search`
(all sole Wave H, C2 format-migrations — version-current v0→v1 + modernize, GREEN,
uncommitted). Shared work-queue
`.claude/data/conda-forge-expert/feedstock-update/total_coverage_queue.json`
(`role=sole` AND `action∈{v0-migrate, create-missing}`); resume from `co_sweep_progress.md`.
Goal: all 769 (sole + co) in build-green `recipe.yaml`. Retro folded into CFE skill v8.41.0 (G52, G53).


---

## Review Digest — Waves C/D/E (2026-06-21)

> Per-recipe summary of the 197 local refreshes produced this effort. All UNCOMMITTED at generation time. Columns: version (old→new), class (C1 keep-meta / C2 no-meta), cfe-source-kind, cfe-noarch, local build status, updates-needed.


### Wave C — v0-migration (noarch), 174

| recipe | version | class | source-kind | noarch | build | updates-needed |
|---|---|---|---|---|---|---|
| `ag-ui-protocol` | 0.1.13 → 0.1.19 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `airfly` | 1.0.0 → 1.1.0 | C2 | pypi-sdist | python | success | none |
| `amundsen-databuilder` | 7.4.3 → 7.5.1 | C1 | pypi-sdist | python | build-clean-test-blocked | meta-yaml-to-recipe-yaml |
| `asttrs` | 1.0.0 → 1.3.0 | C2 | pypi-sdist | python | success | none |
| `basedtyping` | 0.0.3 → 0.1.10 | C2 | pypi-sdist | python | success | none |
| `behave-django` | 1.5.0 → 2.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `burr` | 0.37.0 → 0.40.2 | C2 | pypi-sdist | python | success | none |
| `bynder-sdk` | 1.1.5 → 2.0.2 | C2 | pypi-sdist | python | success | - test-python_version-to-canonical-two-entry-list |
| `cmudict` | 1.0.32 → 1.1.3 | C2 | pypi-sdist | python | success | none |
| `crispy-bootstrap4` | 2022.1 → 2026.2 | C2 | pypi-sdist | python | success | none |
| `crispy-bootstrap5` | 2024.10 → 2026.3 | C2 | pypi-sdist | python | success | none |
| `cssbeautifier` | 1.15.0 → 1.15.4 | C2 | pypi-sdist | python | success | none |
| `cucumber-expressions` | 18.1.0 → 20.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `customersatisfactionmetrics` | 1.0.8 → 1.0.9 | C2 | pypi-sdist | python | success | none |
| `daff` | 1.3.46 → 1.4.2 | C2 | pypi-sdist | python | success | none |
| `dagster-async-executor` | 0.0.1 → 0.0.3 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `dataprofiler` | 0.10.7 → 0.13.4 | C2 | pypi-sdist | python | success | - setuptools-lt-81-cap-G34 |
| `datasette-configure-fts` | 1.1.2 → 1.1.4 | C2 | pypi-sdist | python | success | none |
| `datasette-enrichments` | 0.4 → 0.5.1 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `datasette-search-all` | 1.1.2 → 1.1.4 | C2 | pypi-sdist | python | success | none |
| `datastar-py` | 0.4.3 → 1.0.2 | C2 | pypi-sdist | python | success | dependency-fix |
| `dbt-dremio` | 1.7.0 → 1.10.1 | C1 | pypi-sdist | python | build-clean-test-blocked | meta-yaml-to-recipe-yaml, dependency-fix |
| `detect-test-pollution` | 1.1.1 → 1.2.0 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `diazo` | 2.0.0 → 2.0.6 | C2 | pypi-sdist | python | success | none |
| `django-admin-rangefilter` | 0.13.2 → 0.13.5 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-approval` | 0.11.4 → 0.15.1 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml, dependency-fix |
| `django-auditlog` | 2.3.0 → 3.4.1 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml, dependency-fix |
| `django-celery-beat` | 2.5.0 → 2.9.0 | C2 | pypi-sdist | python | success | none |
| `django-cms` | 4.1.4 → 5.0.5 | C2 | pypi-sdist | python | success | none |
| `django-colorful` | 1.3 → 1.4.0 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-comments-xtd` | 2.10.6 → 2.10.11 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-data-browser` | 4.2.5 → 4.2.14 | C2 | pypi-sdist | python | success | none |
| `django-dbbackup` | 4.0.2 → 5.3.0 | C2 | pypi-sdist | python | success | none |
| `django-entangled` | 0.6.2 → 0.7 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-excel-tools` | 1.1.0 → 1.1.1 | C2 | pypi-sdist | python | success | none |
| `django-extra-views` | 0.14.0 → 0.16.0 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-formtools` | 2.5.1 → 2.6.1 | C2 | pypi-sdist | python | success | none |
| `django-hosts` | 5.2 → 7.0.0 | C2 | pypi-sdist | python | success | dependency-fix |
| `django-linear-migrations` | 2.11.0 → 2.19.0 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml, dependency-fix |
| `django-log-request-id` | 2.1.0 → 2.1.2 | C2 | pypi-sdist | python | success | none |
| `django-log-viewer` | 1.1.7 → 1.1.8 | C2 | pypi-sdist | python | success | none |
| `django-mongodb-backend` | 5.2.2 → 6.0.3 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-mptt2` | 0.2.0 → 0.2.1 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-nyt` | 1.3 → 1.5.0 | C2 | pypi-sdist | python | success | none |
| `django-orghierarchy` | 0.3.0 → 0.6.2 | C2 | pypi-sdist | python | success | none |
| `django-registration` | 5.1.0 → 5.2.1 | C2 | pypi-sdist | python | success | none |
| `django-schema-viewer` | 0.4.1 → 0.5.3 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-sesame` | 3.2.2 → 3.2.3 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-socio-grpc` | 0.20.3 → 0.24.1 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml, dependency-fix |
| `django-solo` | 2.2.0 → 2.5.1 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `django-sql-explorer` | 5.0.2 → 5.3 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-streamfield` | 2.1.2 → 2.4.0 | C2 | pypi-sdist | python | success | none |
| `django-structlog` | 8.0.0 → 10.1.0 | C2 | pypi-sdist | python | success | none |
| `django-survey-and-report` | 1.4.10 → 1.4.12 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml, dependency-fix |
| `django-tastypie` | 0.15.0 → 0.15.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `django-tenant-schemas` | 1.12.0 → 2.0.0 | C2 | pypi-sdist | python | success | dependency-fix |
| `django-tenant-users` | 1.2.0 → 2.2.1 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-tenants` | 3.7.0 → 3.10.1 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-tex` | 1.1.10 → 1.1.12 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-timezone-field` | 6.0 → 7.2.2 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml, dependency-fix |
| `django-todo` | 2.5.0 → 2.5.6 | C1 | pypi-sdist | python | build-clean-test-blocked | meta-yaml-to-recipe-yaml |
| `django-tree-queries` | 0.15.0 → 0.24.0 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `django-vite` | 3.0.6 → 3.1.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `django-vite-plugin` | 3.0.0 → 4.1.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `django-wildewidgets` | 0.16.13 → 1.6.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `django-yugabytedb` | 4.0.0.post1 → 4.2.0.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djangocms-attributes-field` | 4.0.0 → 4.1.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djangocms-frontend` | 2.0.0 → 2.3.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djangocms-icon` | 2.1.0 → 2.1.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djangocms-link` | 5.0.0 → 5.1.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djangocms-text-ckeditor` | 5.1.5 → 5.1.7 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djangorestframework-dataclasses` | 1.3.0 → 1.4.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `djlint` | 1.35.3 → 1.39.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `docstring_parser_fork` | 0.0.5 → 0.0.14 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `drf-pydantic` | 2.7.0 → 2.9.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `drf-standardized-errors` | 0.12.5 → 0.16.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `duckdb-server` | 0.12.0 → 0.27.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `fixedint` | 0.1.6 → 0.2.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `flake8-logging` | 1.2.0 → 1.8.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `flake8-no-pep420` | 2.7.0 → 2.9.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `flake8-pylint` | 0.2.0 → 0.2.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `flake8-tidy-imports` | 4.10.0 → 4.12.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `fs.googledrivefs` | 2.5.0 → 2.6.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `gekko` | 1.0.6 → 1.3.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `gita` | 0.16.6.6 → 0.16.8.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `google-cloud-bigquery-connection` | 1.16.0 → 1.22.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `google-cloud-functions` | 1.18.0 → 1.23.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `google-cloud-ndb` | 2.4.2 → 2.5.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `google-cloud-scheduler` | 2.17.0 → 2.20.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `grunnur` | 0.5.0 → 0.6.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `hatch-build-scripts` | 0.0.4 → 1.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `heroicons` | 2.6.0 → 2.14.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `hubspot-api-client` | 4.0.6 → 12.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `inertia-django` | 0.6.0 → 1.2.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `install-jdk` | 1.0.2 → 1.1.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `intake-dataframe-catalog` | 0.2.4 → 0.5.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `jinja2-simple-tags` | 0.5.0 → 0.6.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `json_stream` | 2.3.2 → 2.5.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `kantoku` | 0.18.1 → 0.18.3 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `kedro-datasets` | 9.0.0 → 9.4.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `kedro-pandera` | 0.1.0 → 0.2.3 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `laces` | 0.1.0 → 0.1.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `lazy-imports` | 0.3.1 → 1.2.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `lm-format-enforcer` | 0.11.2 → 0.11.3 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `loki-logger-handler` | 1.0.0 → 1.1.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `natural-keys` | 2.1.0 → 2.1.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `okta-jwt-verifier` | 0.3.0 → 0.5.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `openllm-core` | 0.5.2 → 0.5.7 | C1 | pypi-sdist | python | success | - recipe-regenerate |
| `openmetadata-managed-apis` | 1.9.9.0 → 1.13.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `opentelemetry-exporter-gcp-monitoring` | 1.8.0a0 → 1.12.0a0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `opentelemetry-exporter-gcp-trace` | 1.6.0 → 1.12.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `opentelemetry-exporter-prometheus-remote-write` | 0.44b0 → 0.63b1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `opentelemetry-propagator-gcp` | 1.6.0 → 1.12.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `opentelemetry-resourcedetector-gcp` | 1.6.0a0 → 1.12.0a0 | C1 | pypi-sdist | python | success | - recipe-regenerate |
| `peewee-migrate` | 1.12.2 → 1.15.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `propelauth_py` | 4.2.4 → 4.3.2 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `prophecy-build-tool` | 1.3.0 → 1.3.4 | C1 | pypi-sdist | python | build-clean-test-blocked | - meta-yaml-to-recipe-yaml |
| `pss` | 1.44 → 1.45 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `pydantic-yaml` | 1.1.1 → 1.6.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `pyecharts` | 2.0.4 → 2.1.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `pygount` | 3.1.0 → 3.2.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `pytest-deadfixtures` | 2.2.1 → 3.1.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `pytest-excel` | 1.6.0 → 1.8.1 | C2 | pypi-sdist | python | success | none |
| `pytest-playwright` | 0.5.2 → 0.8.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `pytest-pythonpath` | 0.7.3 → 0.7.4 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `robocorp-http` | 0.4.0 → 0.4.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `robocorp-log` | 3.1.0 → 3.1.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `robotframework-assertion-engine` | 3.0.3 → 5.0.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `seedir` | 0.5.0 → 0.5.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `shillelagh` | 1.2.24 → 1.4.4 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `sketch` | 0.5.0 → 0.5.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `smartsheet-python-sdk` | 3.0.2 → 3.5.3 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `tabcmd` | 2.0.12 → 2.0.18 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `tableauscraper` | 0.1.2 → 0.1.29 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `tabpy` | 2.10.0 → 2.14.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `taipy-config` | 3.0.0 → 3.1.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `taipy-templates` | 3.0.0 → 4.1.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `tastymap` | 0.4.0 → 0.4.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `tox-uv` | 1.15.0 → 1.35.2 | C2 | pypi-sdist | python | success | none |
| `uvicorn-worker` | 0.2.0 → 0.4.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `validate-pyproject` | 0.23 → 0.25 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `verlib2` | 0.1.0 → 0.3.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `vizro` | 0.1.54 → 0.1.59 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `vizro-mcp` | 0.1.1 → 0.1.4 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-ab-testing` | 0.9 → 0.14 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `wagtail-ai` | 3.0.0 → 3.1.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-color-panel` | 1.5.0 → 1.8.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-dynamic-dropdown` | 0.0.4 → 0.0.5 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-experiments` | 0.3.1 → 0.4 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-feedback` | 1.1.6 → 1.3.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-flexible-forms` | 2.0.0 → 2.1.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-font-awesome-svg` | 1.0.1 → 2.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-footnotes` | 0.10.0 → 0.15.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-grapple` | 0.25.0 → 0.31.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-headless-preview` | 0.7.0 → 0.9.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-markdown` | 0.12.1 → 0.14.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-meta-preview` | 4.0.0 → 4.2.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-metadata` | 4.0.3 → 5.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-modeladmin` | 1.0.0 → 2.4.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-nav-menus` | 3.13.1 → 3.14.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-periodic-review` | 0.2.0 → 0.5.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-plotly` | 0.0.3 → 0.0.4 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-rangefilter` | 0.2.0 → 0.2.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-review` | 0.4 → 0.5 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-sharing` | 2.12.1 → 2.16 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-storages` | 1.0.0 → 2.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-surveyjs` | 0.1.0 → 0.3.0 | C1 | pypi-sdist | python | success | meta-yaml-to-recipe-yaml |
| `wagtail-transfer` | 0.9.3 → 0.11 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-trash` | 3.0.0 → 3.2.0 | C2 | pypi-sdist | python | success | recipe-regenerate |
| `wagtailcharts` | 0.6.2 → 0.6.3 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtailgridder` | 1.0.4 → 2.0.0 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtailmath` | 1.3.0 → 1.3.1 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtailmedia` | 0.14.5 → 0.17.2 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |
| `wagtailstreamforms` | 4.1.0 → 5.2.6 | C1 | pypi-sdist | python | success | - meta-yaml-to-recipe-yaml |

### Wave D — compiled / host-blocked, 10

| recipe | version | class | source-kind | noarch | build | updates-needed |
|---|---|---|---|---|---|---|
| `datasketches` | 5.0.2 → 5.2.0 | C1 | pypi-sdist | compiled | success | meta-yaml-to-recipe-yaml |
| `hll` | 2.1.7 → 3.0.0 | C1 | pypi-sdist | compiled | success | - meta-yaml-to-recipe-yaml |
| `jh2` | 5.0.3 → 5.0.13 | C1 | pypi-sdist | compiled | success | - meta-yaml-to-recipe-yaml |
| `json-stream-rs-tokenizer` | 0.4.29 → 0.5.1 | C1 | pypi-sdist | compiled | success | - meta-yaml-to-recipe-yaml |
| `psycopg2-yugabytedb` | 2.9.3.post0 → 2.9.3.5 | C1 | pypi-sdist | compiled | success | - meta-yaml-to-recipe-yaml |
| `pyobjc-framework-applicationservices` | 9.2 → 10.1 | C1 | pypi-sdist | compiled | not-attempted | meta-yaml-to-recipe-yaml |
| `pyobjc-framework-systemconfiguration` | 9.2 → 12.1 | C1 | pypi-sdist | compiled | not-attempted | - meta-yaml-to-recipe-yaml |
| `skranger` | 0.7.0 → 0.8.0 | C1 | pypi-sdist | compiled | success | - meta-yaml-to-recipe-yaml |
| `uiautomation` | 2.0.24 → 2.0.29 | C1 | pypi-sdist | python | not-attempted | - meta-yaml-to-recipe-yaml |
| `wasmtime-py` | 40.0.0 → 45.0.0 | C1 | pypi-sdist | compiled | success | meta-yaml-to-recipe-yaml |

### Wave E — gh-numbering re-verify, 13

| recipe | version | class | source-kind | noarch | build | updates-needed |
|---|---|---|---|---|---|---|
| `acachecontrol` | 0.3.5 → 0.3.7 | C2 | github-tag | python | success | none |
| `collectfasta` | 3.2.0 → 3.3.3 | C2 | github-tag | python | success | none |
| `cookiecutter-django` | 2025.05.02 → 2025.07.27 | C1 | github-tag | python | success | none |
| `copilotkit` | 0.1.88 → 1.57.2 | C1 | github-tag | python | success | - meta-yaml-to-recipe-yaml |
| `h2o-lightwave-web` | 1.0.0 → 1.8.9 | C1 | pypi-wheel:github-source-ships-no-www-assets | python | success | - meta-yaml-to-recipe-yaml |
| `h2o-wave` | 1.0.0 → 1.8.9 | C1 | github-tag | python | success | - meta-yaml-to-recipe-yaml |
| `kedro-boot` | 0.2.0 → 0.3.0 | C1 | github-tag | python | success | meta-yaml-to-recipe-yaml |
| `mailpit` | 1.28.0 → 1.30.2 | C1 | github-tag | compiled | success | - meta-yaml-to-recipe-yaml |
| `pypac` | 0.16.4 → 0.18.3 | C1 | github-tag | python | success | - meta-yaml-to-recipe-yaml |
| `spec-kit` | 0.1.4 → 0.11.3 | C1 | github-tag | python | success | - meta-yaml-to-recipe-yaml |
| `wagtail-cache` | 2.4.0 → 3.0.0 | C1 | github-tag | python | success | meta-yaml-to-recipe-yaml |
| `wagtail-pdf` | 0.2.1 → 2.0.0 | C1 | github-tag | python | success | - meta-yaml-to-recipe-yaml |
| `wagtailmenus` | 4.0.1 → 4.0.7 | C1 | github-tag | python | success | meta-yaml-to-recipe-yaml |

---

## Follow-ups discovered (for human triage — flagged, not auto-fixed)

These surfaced during Waves C/D/E and are recorded here so they aren't lost. None were acted on beyond flagging (locked no-git policy / out of per-recipe scope).

1. **h2o-lightwave-web: deployed feedstock likely ships a BROKEN empty package.** The GitHub monorepo subdir has zero `www/` web assets (generated at release time, present only in the PyPI wheel) → from-source build = empty ~15 KiB shell. Local v1 now sources the PyPI wheel (423 assets); the feedstock needs the same fix. Tracked via `cfe-forge-recipe-updates-needed: recipe-regenerate`. (CFE gotcha **G51**.)
2. **Stale git-tracked recipe-dir `conda_build_config.yaml` cruft** in `recipes/hll/` + `recipes/jh2/`. **RESOLVED 2026-06-21** — both `git rm`'d in this closeout pass (staged, uncommitted). **Correction to the original flag:** only `jh2` was a verbatim global-pinning copy (933 lines; the source of the `duplicate entry "libitk_devel"` collision + the conda-smithy lint errors). `hll`'s was a *different* artifact — a 20-line py3.7-reinstating + numpy-1.20 pin matrix ("exceptionally reinstate python 3.7 support"), obsolete after the modern python_min refresh, **not** a global-pinning copy. Both date to "first commit" and are absent from the deployed feedstocks. **Still TODO:** audit the other compiled recipe dirs for the same verbatim-global-pinning-copy pattern. (CFE gotcha **G47**.)
3. **cookiecutter-django has NO conda-forge feedstock** (the behind-list misclassified it as on-cf). It is local-only `pending-submission-to-conda-forge`; PyPI is abandoned at 1.11.9; sources the GitHub CalVer tag. Stray files in the dir (`meta-2024.yaml`, `README.rst`, `{{cookiecutter.project_slug}}/`) for triage. (CFE refinement, guide Wave A.)
4. **spec-kit two-feedstock collision:** our `spec-kit-feedstock` (github-tag, sole-maintainer) vs a competing `conda-forge/specify-cli-feedstock` (pypi-sdist, maintainer xhochy) for the same upstream. Decide consolidation. Also: spec-kit's vestigial deps (`httpx`/`socksio`/`truststore`, not imported in 0.11.3) mirrored faithfully, flagged for a maintenance PR.
5. **pypac:** the redundant recipe-dir `LICENSE` was removed (the source archive ships it; matches the feedstock) — a reviewable deletion slightly beyond the meta.yaml-only rm rule.
6. **django-yugabytedb:** hard-imports `psycopg2` at module load but the feedstock omits it from `run:` — parked in CFE comments, not silently added.
7. **Platform-expansion candidates** (recorded as `cfe-forge-recipe-updates-needed: platform-expansion`) — compiled feedstocks shipping only linux-64/osx-64/win-64 (no aarch64/arm64): `hll`, `jh2`, `json-stream-rs-tokenizer`, `psycopg2-yugabytedb`, `skranger`, `pyobjc-framework-systemconfiguration`. `mailpit` noted (own effort). `datasketches`/`wasmtime-py`/`pyobjc-framework-applicationservices` already ship the wider matrix.
8. **Pre-existing failing meta-test** `test_skill_md_lists_existing_scripts_only` — flags 7 scripts cited by *existing* gotchas G21/G23/G24/G39; git-stash-verified as predating this effort (not introduced by the v8.40.0 retro). Worth a separate look.

> **`cfe-generated-by-version` cosmetic note:** the 197 recipes carry `cfe-generated-by-version: 8.37.0` (the value in effect when authoring began); the skill subsequently advanced to 8.40.0. This is a strip-before-push local field — not re-stamped across 197 files unless normalization is desired.
