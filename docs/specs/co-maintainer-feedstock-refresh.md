---
status: ready
implemented_by: bmad-quick-dev
shipped_ref: ""
spec_updated: 2026-06-21
---
# Tech Spec: Co-Maintainer Feedstock Refresh (bulk local-recipe ↔ feedstock sync, co-maintained set)

> **BMAD intake document.** Parameterized, BMAD-consumable. Written for
> `bmad-quick-dev` / `bmad-dev`. The **bulk-orchestration** layer over the
> per-feedstock procedure in `feedstock-platform-expansion.md` — it decides
> *which* co-maintained feedstocks to refresh and *in what order*, and delegates
> the per-feedstock "how" to that guide + the `conda-forge-expert` skill.
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/co-maintainer-feedstock-refresh.md
> ```
>
> **Sibling of `sole-maintainer-feedstock-refresh.md`** (which covered the 537
> sole-maintainer feedstocks). Together the two specs cover **every feedstock
> rxm7706 has the ability to modify** (537 sole + 232 co = the full 769). This
> spec adds the one dimension the sole spec did not need: **co-maintainer
> coordination etiquette** — you co-own these feedstocks, so you preserve other
> maintainers' choices and (at submission time) open PRs rather than self-merge.
>
> **Three pillars (same as the sole spec / feedstock-failure-remediation):**
> (1) **BMAD** drives execution; (2) the **`conda-forge-expert` skill** is the
> authoritative interface for *all* conda-forge work (regen / migrate / build /
> platform-expand); (3) the **conda-forge-atlas** supplies the version-delta +
> maintainer-role facts.

---

## Status

| Field | Value |
| ----- | ----- |
| Status | **READY — intake complete, unimplemented.** Headline counts computed live from cf_atlas (build 2026-06-19 21:55): **232 co-maintained feedstocks**, of which **190 have a local recipe** (62 v1 + 128 v0) and **42 have no `dir==conda` local recipe** (mapping-resolve or net-new); rough version delta among the 190 = **~143 BEHIND, 8 AHEAD, 39 MATCH**. Wave A re-verifies exactly (atlas refresh + GH-numbering guard + dir↔conda mapping). No recipes processed yet. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only) |
| Scope | Every `recipes/<name>/` (and net-new where missing) that backs a **co-maintainer** conda-forge feedstock — i.e. rxm7706 is in the maintainer list but is **not** the sole maintainer. Disjoint from the sole-maintainer spec's set by construction. |
| Goal | Bring each co-maintained local recipe up to its feedstock's published version via **full CFE regenerate (diff-apply)**, modernizing grayskull regressions, folding in **platform expansion where compiled**, migrating **v0→v1**, and creating local mirrors where none exist — so **every** co-maintained feedstock has a local `recipe.yaml` with the full `cfe-*` metadata block that passes build + test + lint + optimize locally. |
| Co-maintainer hard rule | **Preserve every other maintainer's work.** Never drop a co-maintainer from `extra.recipe-maintainers`; never override a *deliberate* maintainer choice (intentional pin, platform exclusion, version cadence) — only fix grayskull regressions + genuine staleness. At submission time (separate wave) **open a PR, do not self-merge** (co-maintainer etiquette), even though write access exists. |
| Hard rule (shared) | **No auto-commit, no push** *by default* — everything stays uncommitted for the user's per-recipe `git diff` review. Per-bucket grouped commit only on explicit user instruction; never push without a separate explicit instruction. |
| Predecessors | `sole-maintainer-feedstock-refresh.md` (SHIPPED — the sole half; mirror its waves/landmines), `feedstock-platform-expansion.md` (per-feedstock how-to — delegated), `feedstock-failure-remediation.md` (reactive sibling). Memory: `project_sole_maintainer_feedstock_update`. |

---

## Parameters (set per run)

```
<batch_size>        : recipes per wave-batch (default 5; ≤3 if rate-limited — see rate-limit landmine)
<wave_filter>       : which bucket(s) this run — v1-refresh | v0-migration | gh-numbering | compiled-platform | no-local-recipe | all
<recipe_filter>     : optional explicit recipe list (overrides the bucket pick)
<commit_mode>       : ALWAYS "none" — never commit/push (hard rule; not operator-overridable without an explicit user instruction in the run prompt)
<platform_targets>  : for the compiled bucket — default [osx-arm64, linux-aarch64] (drop ppc64le), per feedstock-platform-expansion.md
<atlas_max_age_d>   : refresh the atlas if older than this many days (default 3)
<create_missing>    : for the no-local-recipe bucket — "yes" (pull + author local mirrors) | "behind-only" | "no" (default "yes")
<coordination_mode> : submission-phase only — "pr" (open PR for co-maintainer review; DEFAULT) | "pr+ping" (PR + @-mention other maintainers for contentious changes). Never "self-merge".
```

---

## Background

`rxm7706` maintains **769** conda-forge feedstocks. The sole-maintainer spec
covered the **537 sole** ones (SHIPPED, commits `1fe1848b43` + `363537dd43`).
This spec covers the **232 co-maintained** ones — feedstocks where rxm7706 is in
`extra.recipe-maintainers` alongside ≥1 other handle. The local mirror is the
source of truth ([[feedback_local_mirror_first_then_verify_then_push]]), and the
same drift applies: ~half are behind their published feedstock and most carry
grayskull-era regressions. Closing this set **completes total coverage** — every
feedstock rxm7706 can modernize/optimize/platform-expand will then have a
build-green local `recipe.yaml` with full `cfe-*` metadata.

### The CO-MAINTAINED working set (cf_atlas 2026-06-19 21:55; Wave A re-verifies)

Derived live from `cf_atlas.db` (`package_maintainers` ⋈ `maintainers`): packages
where maintainer `rxm7706` (id 32) appears AND the package has >1 distinct
maintainer.

| Slice | Count | What it needs |
| ----- | ----- | ------------- |
| **Co-maintained feedstocks** | **232** | the universe of this spec (disjoint from the 537 sole) |
| → with a local recipe (`dir==conda`) | **190** | 62 v1 + 128 v0 — refresh/modernize/migrate in place |
| → **no** `dir==conda` local recipe | **42** | resolve dir↔conda mapping first (some exist under a different dir name, cf. sole spec's `cookiecutter-django`→`-core`, `py-key-value-aio/shared`→`py-key-value`); the genuinely-missing remainder are **net-new local mirrors** to pull + author |
| rough version delta among the 190 | **~143 BEHIND, 8 AHEAD, 39 MATCH** | (naive `packaging.Version` compare; Wave A re-verifies with the GH-numbering guard) |

> **Caveat (Wave A resolves):** the `dir==conda` heuristic *undercounts* local
> recipes — the 42 "no local" is an **upper bound** on truly-missing mirrors.
> The naive behind count also includes GH-numbering false positives (the
> copilotkit pattern). Wave A produces the authoritative bucketed set, exactly
> as it did for the sole spec.

### Bucket model (mirrors the sole spec + one new bucket)

| Bucket | Source | What it needs |
| ------ | ------ | ------------- |
| **v1-refresh** | the 62 v1 co-local that are behind | regen `recipe.yaml` to published version + modernize. |
| **v0-migration** | the 128 v0 co-local | local recipe is v0 (`meta.yaml`). **Two action-classes by FEEDSTOCK format** (same as sole Wave C): **C1 keep-meta** (feedstock still v0) → author v1 `recipe.yaml`, keep `meta.yaml`, flag `meta-yaml-to-recipe-yaml`; **C2 catch-up** (feedstock already v1) → author `recipe.yaml`, delete local `meta.yaml`. |
| **gh-numbering** | feedstocks sourcing a GitHub **tag** whose number ≠ PyPI/local | re-verify, do not blindly bump (copilotkit `v1.57.2`=PyPI`0.1.88`). Mostly no-ops. |
| **compiled-platform** | the compiled subset of any bucket above | also widen the matrix to `<platform_targets>`. **No `@conda-forge-admin, please add user` gating needed — rxm7706 is already a maintainer** (unlike the graphifyy fan-out). |
| **no-local-recipe** *(NEW vs sole)* | the ≤42 with no local mirror | resolve the dir↔conda mapping; for the genuinely-missing, **pull the deployed feedstock recipe into `recipes/<name>/`** and bring it to the same modern + `cfe-*` + build-green bar. Governed by `<create_missing>`. |

### Total-coverage status — all 769 (sole + co), live working-tree scan 2026-06-21

The end-goal — *every feedstock rxm7706 can modify has a build-green local
`recipe.yaml` with full `cfe-*` metadata, so the only remaining step is submitting
PRs* — is **not yet met**, and behind-focused refreshes alone will not reach it:

| Set | recipe.yaml (v1) | meta.yaml-only (v0) | missing |
| --- | ---------------- | ------------------- | ------- |
| SOLE (537) | 358 | 155 | 24 |
| CO (232) | 62 | 128 | 42 |
| **ALL 769** | **420** | **283** | **66** |

**Gap to "all 769 in recipe.yaml" = 349** (283 v0→v1 migrations + 66 missing/mapping).

**Critical scoping note:** the refreshes target **behind** recipes, but the
total-coverage goal *also* requires migrating **version-current-but-still-v0**
recipes (correct version in `meta.yaml` ≠ submission-ready — it still needs v0→v1)
and creating the **missing** ones. Therefore:
- **CO (this spec):** the `v0-migration` bucket covers **ALL 128 v0 co** (not just
  the ~98 behind) and `no-local-recipe` covers the ≤42 missing → run fully, this spec
  closes the **entire co gap (≈170)**.
- **SOLE:** the shipped sole effort was behind-scoped, leaving **~179 sole** recipes
  (155 not-behind-v0 + 24 missing) un-migrated → needs a **sole total-coverage
  follow-up** (a "Wave H" appended to `sole-maintainer-feedstock-refresh.md`, or a
  combined sweep) before all 769 are recipe.yaml.

Caveats (Wave A resolves): the 66 "missing" is an **upper bound** (dir≠conda mapping
artifacts inflate it); and the cfe-completeness + local-build-green status of the
existing 420 recipe.yaml is a **Wave-A audit** item (some predate the cfe convention).
Submission then splits into version-refresh PRs (feedstock already v1) and **v0→v1
migration PRs** (the C1 keep-meta set) — the `recipe.yaml` is ready for both.

---

## Co-maintainer coordination rules (the dimension the sole spec did not need)

You **co-own** these feedstocks. The local-only effort touches nothing upstream,
but the rules below govern *what edits are legitimate* and how the eventual
submission must behave. They are **always-on** for this spec.

1. **Never drop a co-maintainer.** The deployed feedstock's `extra.recipe-maintainers`
   lists every maintainer; a grayskull/recipe-generator regen often emits only
   `rxm7706`. **Re-merge the full deployed maintainer list** into the local
   `recipe.yaml` — preserve every handle. (Add a meta-test / Wave-A check that the
   local maintainer set ⊇ the deployed set for every co-maintained recipe.)
2. **Modernize regressions, not deliberate choices.** Safe to fix unilaterally:
   grayskull regressions (raw `python >=3.8`, homepage→PyPI drift, junk skip/stub,
   empty description, missing `python_min` machinery, about-field order, CFEP-25
   triad). **Do NOT** silently override what looks like a *deliberate* maintainer
   decision — an intentional upper pin, a platform exclusion with a comment, a
   pinned older version, a custom build script. When unsure, treat it as deliberate:
   keep it, and record the proposed change in the bottom `# CFE comments` block +
   `cfe-forge-recipe-updates-needed` for human/maintainer review rather than applying it.
3. **Platform expansion is welcome but announced.** Adding `osx-arm64` /
   `linux-aarch64` to a co-maintained compiled feedstock is generally
   non-controversial, but the submission PR description must state the rationale so
   co-maintainers can review. No add-user issue is needed (already a maintainer).
4. **Submission = PR, never self-merge** (`<coordination_mode>` default `pr`).
   Even with write access, open a PR so co-maintainers can review; `@`-mention them
   for contentious changes (major bumps, dep changes affecting their workflows).
   This is a **submission-phase** rule — out of scope for the local-only effort,
   documented here so the later submission wave inherits it.
5. **cfe metadata records co-ownership.** `extra.recipe-maintainers` carries the full
   list; the `cfe-*` block is local-only and stripped before push as usual
   ([[feedback_extra_is_local_internal_metadata]]).

---

## Landmines (inherit the sole spec's 1–9; co-specific additions below)

Inherit **all 9** landmines from `sole-maintainer-feedstock-refresh.md`
(GH-tag-numbering false positives; atlas staleness; grayskull-regressions-are-the-norm;
pure-Python ≠ platform expansion; rate-limit zombies → **strict ≤4 concurrent**;
`'releases' KeyError`; jinja-in-`#`-comments crashes v1 lint; recipe-local CBC passed
LAST; `cfe-forge-recipe-updates-needed` token discipline). Plus:

10. **Maintainer-list clobber.** The single most co-specific defect: a regen drops
    co-maintainers from `extra.recipe-maintainers`. ALWAYS reconcile against the
    deployed feedstock's maintainer list and re-merge (rule 1). Verify before
    leaving any co-maintained recipe.
11. **dir↔conda mapping for the 42 "no local".** Some are mapping artifacts (recipe
    exists under a different dir name) — resolve via `lookup_feedstock` / the atlas
    `conda_name` before declaring a recipe net-new. Only the genuine remainder are
    `<create_missing>` work.
12. **Deliberate-vs-regression ambiguity.** Co-maintained recipes are more likely to
    carry *another maintainer's* intentional choices than sole ones. Bias
    conservative (rule 2); when a "fix" would change behavior another maintainer set
    on purpose, park it in `# CFE comments` + a `cfe-forge-recipe-updates-needed`
    token instead of applying it.
13. **Local-channel pollution during the bulk sweep (= skill gotcha G52).** Building
    every recipe into one shared `--output-dir` lets a locally-built NEWER version
    shadow the OLDER conda-forge version a *different* recipe's deps need → a FALSE
    test-env block. Build each recipe into an isolated per-recipe
    `--output-dir build_artifacts/cosweep/<name>`. If a test-env solve fails on a dep
    that IS on conda-forge, suspect pollution and rebuild isolated before recording
    `build-clean-test-blocked`. Surfaced by the azure-monitor-opentelemetry pilot.

---

## Implementation Plan (waves)

### Wave A — Discovery + baseline (do first, every resume)
- **A1 — refresh the atlas** if older than `<atlas_max_age_d>` (`build-cf-atlas`, maintainer profile).
- **A2 — compute the co-maintained set** from `cf_atlas.db`: packages where `rxm7706` is a maintainer AND `COUNT(DISTINCT maintainer_id) > 1`. Persist `co_maint.txt` + `co_behind_verified.json` under `.claude/data/conda-forge-expert/feedstock-update/` (mirror the sole artifacts; reuse `_rebaseline_2026-06-19.py` adapted to the co list).
- **A3 — resolve dir↔conda mapping** for the ~42 "no local" (atlas `conda_name` / `lookup_feedstock`); split into *mapping-artifact* (recipe exists elsewhere) vs *genuinely-missing* (net-new).
- **A4 — live re-verify** each BEHIND candidate (GH-numbering guard; `local < published` is REAL; `generate_recipe_from_pypi(version=published)` resolves). Re-bucket: v1-refresh / v0-migration (C1/C2) / gh-numbering / compiled-platform / no-local-recipe / drop-false-positive.
- **A5 — maintainer-list snapshot:** record each feedstock's deployed `extra.recipe-maintainers` so Waves B–F can verify the local set ⊇ deployed set (rule 1). **Gate:** present the bucketed counts before Wave B.

### Wave B — v1-refresh bucket
Per recipe, via the CFE skill: `generate_recipe_from_pypi`/`update_recipe` at the published version → modernize (python_min machinery, about-order, CFEP-25 triad, full `cfe-*` v8.40.0 block, comments-at-bottom) → **re-merge the full deployed maintainer list** (rule 1) → `validate` + `optimize` + `check_dependencies` + `scan` → **build locally** → leave uncommitted. Batch `<batch_size>`, strict ≤4 concurrent; review every diff.

### Wave C — v0-migration bucket — TWO action-classes by feedstock format
Read each recipe's `fs_fmt` (or live-check via `lookup_feedstock`):
- **C1 — keep-meta (feedstock v0):** author v1 `recipe.yaml` + keep `meta.yaml`; `cfe-forge-recipe-updates-needed: [meta-yaml-to-recipe-yaml, …]`; build/test/lint target `recipe.yaml` explicitly; STD-002 is expected/harmless.
- **C2 — catch-up (feedstock already v1):** author `recipe.yaml` to match the deployed v1; **delete** local `meta.yaml`.
Both: re-merge maintainers (rule 1); modernize regressions only (rule 2); cache `cfe-import-names` (G7); canonical tokens; review every diff.

### Wave D — compiled-platform bucket
For compiled co-maintained recipes, widen the matrix to `<platform_targets>` per
`feedstock-platform-expansion.md`. **No add-user gating** (already a maintainer).
Platform additions get a rationale line for the eventual PR (rule 3).

### Wave E — gh-numbering bucket
Re-map GitHub-tag versions correctly (or confirm not-behind) before any change.
Most will be no-ops (copilotkit pattern).

### Wave F — no-local-recipe bucket (net-new mirrors) — governed by `<create_missing>`
For the genuinely-missing (post-A3): pull the deployed feedstock recipe into
`recipes/<name>/`, bring it to the modern + full-`cfe-*` + maintainer-preserving +
build-green bar. `behind-only` restricts to those whose feedstock has moved; `no`
skips this wave.

### Wave G — Closeout
- Per-recipe diffs sit uncommitted for the user's review + manual commit/push.
- **Maintainer-list audit:** confirm every processed co-maintained recipe's local
  maintainer set ⊇ the deployed set (rule 1) — no co-maintainer dropped.
- **CFE-skill retro** (Rule 2) folds in whatever the bulk refresh surfaces.

---

## Definition of Done (per recipe)

A co-maintained recipe is DONE when its local `recipe.yaml`:
1. is at the feedstock's published version (or correctly confirmed not-behind);
2. carries the full **v8.40.0 `cfe-*`** metadata block (identity + `cfe-local-build-*`);
3. preserves the **complete deployed maintainer list** in `extra.recipe-maintainers`;
4. passes `validate_recipe` (lint), `optimize_recipe` (only expected STD-002 for C1),
   `check_dependencies` (0 missing), `scan_for_vulnerabilities` (clean);
5. **builds locally green** (or honestly records `build-clean-test-blocked` /
   `not-attempted` for prerequisite-gap / host-blocked cases);
6. leaves any deliberate-maintainer-choice un-overridden, with proposed changes parked
   in `# CFE comments` + `cfe-forge-recipe-updates-needed`.

---

## Open Questions

- **Q1 — commit cadence.** Default (mirror sole, RESOLVED there): uncommitted between
  authorized per-bucket commits; never push without a separate explicit instruction.
- **Q2 — no-local-recipe depth (`<create_missing>`).** Create local mirrors for ALL 42
  net-new, only the behind ones, or none this effort? Spec default: `yes` (all), after
  A3 prunes the mapping-artifacts. Confirm at Wave A gate.
- **Q3 — deliberate-vs-regression threshold.** Where exactly is the line between a
  grayskull regression (fix) and a deliberate co-maintainer choice (preserve + flag)?
  Spec default: bias conservative (landmine 12); refine with worked examples.
- **Q4 — submission model.** When these go upstream (separate later wave),
  `<coordination_mode>` default `pr` (open PR for co-maintainer review, never
  self-merge). Confirm per-feedstock whether to `@`-ping for contentious changes.
- **Q5 — v0→v1 feedstock-migration depth.** Same as sole Q2: local mirror only this
  effort; feedstock v0→v1 PRs are a separate later submission wave (`meta-yaml-to-recipe-yaml`
  tracks the debt).

---

## Worked Examples

**Run 1 — 2026-06-21 (pilot + first scaled batch; PAUSED at weekly limit).**
Wave A discovery computed the 769 total-coverage queue
(`total_coverage_queue.json`): primary work **398** (283 v0-migrate + 66
create-missing + 49 v1-refresh) + 371 audit-existing. **8 recipes done, all GREEN**
(uncommitted, isolated build dirs under `build_artifacts/cosweep/`):
- **Pilot (4):** airflow-code-editor (co C2 — **re-merged dropped maintainer `xylar`**),
  airflow-provider-great-expectations (co C2, MAJOR 1.0.0, dropped `sqlalchemy` per sdist),
  azure-monitor-opentelemetry (co C2 v1-refresh, kept opentelemetry `==` pins —
  **surfaced the G52 channel-pollution landmine**), amundsen-common (sole Wave H C2
  format-migration).
- **First batch (4):** alang (co C1 — **re-merged dropped maintainer `praeclarum`**),
  avro (co C1 1.12.0→1.12.1), amundsen-metadata (sole Wave H C2), amundsen-search
  (sole Wave H C2).

**Rules validated:** the maintainer-preservation rule caught + restored **2 dropped
co-maintainers** (xylar, praeclarum) → landed as skill **G53**; deliberate exact-pin
preservation held; the sole Wave H version-current format-migration works; isolated
per-recipe build dirs fixed the local-channel pollution → skill **G52**. Retro shipped
**conda-forge-expert v8.41.0 (G52, G53)**. Resume from
`.claude/data/conda-forge-expert/feedstock-update/co_sweep_progress.md` — refill the
≤4 pipeline from `total_coverage_queue.json` (the 66 create-missing await a dir↔conda
mapping pass first).

---
