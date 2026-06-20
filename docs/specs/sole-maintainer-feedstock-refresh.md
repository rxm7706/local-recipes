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
| Status | **Re-baselining (resume of a 2026-06-19 effort)** — 258 confirmed-BEHIND sole-maintainer recipes identified; only ~25 applied before the cfe-* convention + langflow absorbed the session. The atlas + the 258-list are now ~1 week stale → Wave A re-baselines before any new work. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only) |
| Scope | Every `recipes/<name>/` that backs a **sole-maintainer** conda-forge feedstock and is **behind** the feedstock's published version. |
| Goal | Bring each local recipe up to its feedstock's published version via **full CFE regenerate (diff-apply)**, modernizing grayskull regressions, folding in **platform expansion where the recipe is compiled**, and migrating **v0 feedstocks** to v1. |
| Hard rule | **No auto-commit, no push.** Everything stays uncommitted for the user's per-recipe `git diff` review. (The prior effort kept HEAD at `d8f3c8a3cb` throughout.) |
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

### The 258-BEHIND working set (2026-06-19 snapshot — to be re-verified in Wave A)

Persisted at **`.claude/data/conda-forge-expert/feedstock-update/behind_verified.json`**
(258 entries; fields `dir, conda, feedstock, local, target, fmt, fs_fmt, branch`),
plus `sole_maint.txt` (the 537) and `behind.json` (raw delta). The 258 split:

| Bucket | Count | What it needs |
| ------ | ----- | ------------- |
| **v1-refresh** | ~103 | feedstock is already v1; regen `recipe.yaml` to the published version + modernize. Simplest. |
| **v0-migration** | ~142 | feedstock is still `meta.yaml` (v0); regen to v1 `recipe.yaml` **and keep `meta.yaml` mirror** ([[feedback_keep_meta_yaml_until_feedstock_migrates]]), cfe metadata sets `cfe-forge-recipe-updates-needed: meta-yaml-to-recipe-yaml`. The bulk. |
| **gh-numbering** | 13 | feedstock sources a GitHub **tag** whose number ≠ PyPI/local (copilotkit: feedstock `v1.57.2` = PyPI `0.1.88`). **NOT actually behind** — re-verify, do not blindly bump. |
| (AHEAD) | 10 | local newer than published (in-flight work, e.g. cocoindex 1.0.10). Out of scope — leave alone. |

### Landmines (from the 2026-06-19 pilot-of-5 `ovld/copilotkit/a2wsgi/django-auditlog/selectolax`)

1. **GitHub-tag-numbering false positives** — `generate_recipe_from_pypi(version=<feedstock-tag>)` 404s when the feedstock tag ≠ PyPI version. **Live-verify each candidate against the feedstock + PyPI before any regen** (Wave A does this for the whole set).
2. **Atlas staleness** — the delta is only as fresh as the atlas build; refresh first.
3. **Grayskull regressions are the norm**, not the exception — the regen modernizes them; expect large-but-correct diffs.
4. **Pure-Python ≠ platform expansion** — most of the 512 are noarch Django/Wagtail; platform-widen ONLY the compiled subset ([[feedback_noarch_platforms_pure_python_waste]]).

---

## Implementation Plan (waves)

### Wave A — Re-baseline (do first, every resume)
- **A1 — refresh the atlas** if older than `<atlas_max_age_d>` (`build-cf-atlas`, maintainer profile). Records the current published versions.
- **A2 — recompute sole-maintainer + version-delta** → regenerate `sole_maint.txt` + `behind.json` + `behind_verified.json` under `.claude/data/conda-forge-expert/feedstock-update/`.
- **A3 — live re-verify** each BEHIND candidate against its feedstock + PyPI (GH-numbering guard): confirm `local < published` is REAL and `generate_recipe_from_pypi(version=published)` resolves (no 404). Re-bucket: v1-refresh / v0-migration / gh-numbering / compiled-platform / drop-false-positive.
- **A4 — subtract the already-done** (~25 from the prior effort; check working-tree vs the list). Output the accurate remaining set + per-bucket counts. **Gate:** present the re-baselined counts before Wave B.

### Wave B — v1-refresh bucket (~103)
Per recipe, via the CFE skill: `generate_recipe_from_pypi` (or `update_recipe`) at the published version → modernize (python_min machinery, about-order, CFEP-25 triad, cfe-* FINAL-schema block, comments-at-bottom) → `validate` + `optimize` + `scan` → **build locally** (rattler-build for v1) → leave uncommitted. Batch in `<batch_size>`; **the user reviews every diff.**

### Wave C — v0-migration bucket (~142, the bulk)
Per recipe: pull the feedstock's latest `meta.yaml` and **keep it** alongside a new v1 `recipe.yaml` ([[feedback_keep_meta_yaml_until_feedstock_migrates]]); the `recipe.yaml` carries `cfe-forge-recipe-updates-needed: meta-yaml-to-recipe-yaml`; build/test/lint target `recipe.yaml` explicitly. Batch; review every diff; no commit.

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

- **Q1 — commit cadence.** Hard rule is no-commit; but for 258 recipes, does the user
  want periodic *grouped* commits (per-bucket, after reviewing a batch) to avoid one
  258-recipe working tree? Spec default: keep all uncommitted; user commits in their
  own groupings. (Recommend offering per-batch grouped commits after review.)
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

**Run 2 — (this resume).** Wave A re-baseline → … (append per-run state here).
