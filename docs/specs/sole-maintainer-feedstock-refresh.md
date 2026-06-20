---
status: in-progress
implemented_by: bmad-quick-dev
shipped_ref: "Wave B done; Wave C paused 18/184"
spec_updated: 2026-06-20
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
| Status | **Wave B COMPLETE; Wave C in progress — PAUSED 60min at 18/184 (2026-06-20).** Wave A re-baselined to **256 BEHIND**. **Wave B (v1-refresh, 55) DONE** — committed `1fe1848b43`. **Wave C (v0-migration, 184): 18 done** (C1-keepmeta=5, C2-delmeta=13; 17 build-green, 1 build-clean-test-blocked). Both action-classes validated. 166 remaining — resume from `v0_queue.txt`/`wave_c_progress.md` at strict ≤4 concurrent. Remaining waves: D compiled-platform, E gh-numbering (13), F closeout retro. |
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
| **v0-migration** | **184** | ⏳ Wave C (in progress) | local recipe is v0 (`meta.yaml`). **Two action-classes by FEEDSTOCK format — see Wave C.** |
| **gh-numbering** | **13** | ⏳ Wave E | feedstock sources a GitHub **tag** whose number ≠ PyPI/local (copilotkit `v1.57.2`=PyPI`0.1.88`). **NOT actually behind** — re-verify, do not blindly bump. |
| **fs-unknown** | **4** | ⏳ | newly-behind dirs, feedstock format unverified — live-check at processing. |
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
- **Wave C (v0-migration, 184): IN PROGRESS — paused 60min at 18/184** (2026-06-20). Split into C1 keep-meta (141) + C2 catch-up-delete-meta (43). Pilot (4) validated both classes; **18 done** (C1=5, C2=13; 17 build-green, 1 build-clean-test-blocked). Progress + done-list persisted at `wave_c_progress.md`; resume from `v0_queue.txt` at strict ≤4 concurrent. Wave-C catches so far: dataprofiler G34(setuptools-82)+G26(requests-metadata); basedtyping py3.14-incompat → drop `"*"` test leg; cucumber-expressions uv-build drift; ag-ui-protocol G7 `ag_ui`.
