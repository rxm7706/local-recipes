---
title: Build a conda-forge packaging inventory from scratch as a continuous intake engine
type: dream
owner: atlas
status: specified   # 2026-08-22 — spec + station decomposition landed same day
---

# Build a conda-forge packaging inventory from scratch as a continuous intake engine

## The Dream

A repeatable intake engine that starts from raw sources and rebuilds the packaging
inventory end to end: normalize identity, verify PyPI and conda-forge, assign
priority and provenance, and hand execution-ready queues to conda-forge workflows
and OpenTeams. Never consume a previous consolidated inventory as input.

It binds Master Prompt v3.0 (*Consolidated Verified Package Inventory
Specification*) and runs through the existing quartet — runner, prompt, config,
replay — not a second toolchain.

## What it looks like when real

- A from-scratch run in a clean workspace regenerates the full inventory from the
  workbook, live indexes, and curated feeds.
- Every package has one PEP 503 identity, source provenance, and a timestamped
  verify decision. Ranking stays inspectable: proposed `P1`–`P10`, a
  1–100 use `Score`, and a work label (not A/B/C).
- `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` is the OpenTeams universe: one issue titled
  `[Conda-Forge Packaging] {name}` per library, plus a dated handoff tab Mason
  can consume (`Fix vulnerability` / `Create recipe` /
  `File OpenTeams tracking issue [Conda-Forge Packaging]` /
  `Already tracked`).
- Google AOSS Free names that are on PyPI, not on conda-forge, and not in CDO
  consumption are an extra Mason queue. They do not expand the OpenTeams universe.
- Identity rows (PURLs, issue URL, feedstock, metadata, staged-recipes PR, local
  recipe, live CFE `Local_Build_Status`) are a **dated** workbook tab
  (`identity-YYYY-MM-DD`) and a pinned secret gist. New snapshots get a new
  dated tab; do not overwrite an older identity tab. The gist id is never in
  git (`OPENTEAMS_IDENTITY_GIST_ID` or gitignored local env).
- Three dashboard views exist for the live identity tab (catalog, ops, Artifactory
  / workbook). Humans read them beside the chat; machines read the same numbers
  from gist YAML + GFM. A run that ranks identity is not done until those three
  views and the gist companion are rebuilt.
- Drift is visible: net-new names, status flips, stale sources.

## Sources

Primary workbook: `docs/Analysis_Dataset-2026-08-12.xlsx` (local, gitignored;
do not commit). Parse every source tab.
Live collection endpoints are primary; workbook tabs are the offline fallback.

**Must-include (100% of parseable names in the final inventory):**

- `CDO-ENT-JFROG` — CDO JFrog / Artifactory consumption inventory (`name`).
- `CDO-ENT-CONDA` — CDO enterprise conda-forge feedstocks (`Package_Name`,
  `Role` = Maintainer / Co-Maintainer, `Feedstock`). Live list:
  [rxm7706/about](https://github.com/rxm7706/about).

**Other source tabs:** `GAOSS-Free`, `GAOSS-Premium`, `Anaconda-Main`,
`Conda-Forge`, `Basilisk`, `Anaaconda-Dist` (Anaconda Distribution 2026.x),
`OpenTeams`, `10kOpen`, `10kClosed`.

- `10kOpen` is a clone of `CDO-ENT-JFROG`. Do not double-count it.
- `10kOpen` / `10kClosed` are name lists only (`Package_Name`,
  `Source_Organization`, `Primary_Domain`). Derive PyPI, conda-forge, and source
  repo from live indexes, never from leftover hint columns.
- `GAOSS-Free` ⊂ `GAOSS-Premium`. Free-tier Python is Google-assured and an extra
  packaging queue when missing from conda-forge and from CDO consumption.

**Do not ingest** these output snapshot tabs (`OUTPUT_TABS`):

| Tab | What it is |
|---|---|
| `verified-all-packages` | Full inventory (deliverable A; 14 columns) |
| `inventory-2026-08-12` | OpenTeams universe handoff (14 + 8 columns) |
| `identity-2026-08-12` | Frozen identity snapshot. Do not overwrite. |
| `identity-YYYY-MM-DD` | Dated identity output (live: `identity-2026-08-20`). Never ingest. |

Refresh those tabs from a run. Do not keep repo-root CSVs as the stored copy.

**OpenTeams tracker.** Live board is org project 1, **full** `[Conda-Forge
Packaging]` titles (no OSS-milestone slice). View for humans:
https://github.com/orgs/OpenTeams-WFT-CDO/projects/1/views/6?sliceBy%5Bvalue%5D=OSS+Enhancements+%28Conda+Forge%2C+Pixi%2C+ect%29
Workbook `OpenTeams` is the offline snapshot of the full board. Optional `.tsv`
only if the tab is absent. CVE titles (`CVE-… | pkg`) are a different tracker
and do not count.

**External endpoints:**

1. Anaconda Distribution 2026.x —
   [release docs](https://www.anaconda.com/docs/getting-started/anaconda/release/2026.x)
2. Anaconda main — [anaconda.org/channels/main](https://anaconda.org/channels/main)
   (`https://repo.anaconda.com/pkgs/main/channeldata.json`)
3. conda-forge —
   [anaconda.org/channels/conda-forge](https://anaconda.org/channels/conda-forge)
   (`https://conda.anaconda.org/conda-forge/channeldata.json`)
4. Basilisk `view=all` — [basilisk.prefix.dev](https://basilisk.prefix.dev/?view=all)
   ([API](https://prefix-dev.github.io/basilisk/docs/api/); prefer
   `GET https://api.basilisk.prefix.dev/v1/packages`, not the HTML SPA)
5. Google AOSS free Python —
   [supported packages](https://docs.cloud.google.com/assured-open-source-software/docs/supported-packages#python)
6. Google AOSS premium Python —
   [Wayback snapshot](https://web.archive.org/web/20260419090548/https://docs.cloud.google.com/security-command-center/docs/aoss-supported-packages-premium#python)
7. Maintained + co-maintained feedstocks —
   [rxm7706/about](https://github.com/rxm7706/about)
8. Curated groups — live org URL, then workbook
   `10kClosed.Source_Organization`, then
   `conf/conda-forge-packaging-inventory-operations_curated_groups.json` (sample fallback, not membership
   of record). Starting URLs: Apache, Django, LF AI & Data, NumFOCUS, Jazzband,
   FINOS, PSF ([about](https://github.com/rxm7706/about) goal 3), plus PyPA,
   Trendshift, Google, Microsoft, Kedro, BMAD org pages. Org homepages and GitHub
   repo lists are membership starting points, not “ingest every repo as a package.”

A fetch that is an order of magnitude off (Basilisk 0 from HTML, conda-forge
tens instead of tens of thousands) is a fetch bug.

## Build surface

| Path | Role |
|---|---|
| `scripts/conda-forge-packaging-inventory-operations_metrics.py` | Inventory runner |
| `scripts/conda-forge-packaging-inventory-operations_priority.py` | Proposed `P`, `Score`, `Work` on a dated identity tab (`--tab`); optional inventory sync (`--skip-inventory-sync` to leave `Priority_Bucket` alone); writes the catalog canvas (`--canvas`) |
| `docs/reference/conda-forge-packaging-inventory-operations_prompt.md` | Prompt the runner must obey |
| `conf/conda-forge-packaging-inventory-operations_curated_groups.json` | Curated-group sample fallback |
| `docs/reference/conda-forge-packaging-inventory-operations_replay.md` | Replay / sync contract |
| `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` | Identity tab (`--tab-out identity-YYYY-MM-DD`) + gist publish (`--gist-only` after a priority pass) |
| `scripts/openteams_identity_dashboards.py` | Gist companion markdown for the three dashboard views |
| `conf/conda-forge-packaging-inventory-operations.local.env.example` | Template for the gitignored gist id |

A rule, source, column, or metric change updates runner + prompt + replay in the
same commit. Identity-column changes update
`conda-forge-packaging-inventory-operations_openteams_identity.py`. Priority /
work-label / bucket-rule changes update
`conda-forge-packaging-inventory-operations_priority.py` **and** the three
dashboard views **and** `openteams_identity_dashboards.py` (gist YAML `rule` /
`meaning` must stay byte-identical to the priority script). Do not overwrite
`docs/reference/conda-forge-packaging-inventory-operations_prompt.md`
unless that is the task.

**From scratch:** empty outputs; ingest the workbook + live endpoints + curated
JSON; write new tabs / optional CSV / Markdown / stdout. Do not read a prior
consolidated inventory CSV or Markdown as seed or oracle.

## Ingestion and identity

- Extract package-name columns (`name`, `Package_Name`, `raw_names`, `Item`,
  `package`, equivalents).
- OpenTeams titles: **(a)** text after `|` split on comma (CVE tracker; does not
  count toward 1:1); **(b)** `[Conda-Forge Packaging] {name}` — one name per
  issue; **(c)** ignore other titles.
- Strip issue numbers, brackets, version constraints, extras, whitespace.
- Dedup is PEP 503 only (lowercase; `_` and `.` → `-`). It must not drop a
  JFROG or CONDA library.
- `CDO-ENT-JFROG` keeps consumption evidence on the record for priority/handoff
  (`risk_level`, `vuln_status`, `platform_env_count`, `internal_app_count`,
  `internal_component_count`, `internal_lob_count`, `artifactory_downloads`,
  `artifactory_version_count`). Those fields do not become columns of
  deliverable A. Ignore JFROG `packaging_tier` — recalculate `P` here.
- From about (or `CDO-ENT-CONDA`): convert `conda-forge/<pkg>-feedstock` to
  `<pkg>`; `Repository_Source` = `Conda Enterprise Core`; `Role` = Maintainer
  or Co-Maintainer.
- Track overlapping curated-group attributions explicitly.
- Drop a `10kClosed` / `10kOpen` name from deliverable A only when
  `PyPI_Verified=No` **and** no derived VCS URL **and** the name is not on
  JFROG or CONDA. `10kOpen` names already enter via JFROG.

## Verification and PURLs

Offline-safe: skip + last-good + documented fallback when unreachable.

- `PyPI_Verified` via PyPI simple and/or `https://pypi.org/pypi/{package}/json`.
  Fast-mode must not treat conda-forge presence as PyPI Yes.
- `CondaForge_Verified` via conda-forge `channeldata.json` plus Parselmouth
  (`compressed_mapping.json`) so a PyPI name that maps to a different conda
  name still counts as Yes.
- `Source_Repository_URL` — upstream VCS, never feedstock, never `pypi.org` /
  `anaconda.org`. Order: (1) channeldata `dev_url` / git-like `home` /
  `source_url`; (2) PyPI JSON `project_urls` then git-host `home_page`. Accept
  GitHub, GitLab, Bitbucket, Codeberg, and other published VCS hosts. `N/A`
  only when neither publisher lists a VCS URL. Do not skip PyPI JSON for
  PyPI-verified names that are not on conda-forge.

| Status | Rule |
|---|---|
| `Already Packaged` | PyPI Yes AND conda-forge Yes |
| `High Priority Candidate` | PyPI Yes AND conda-forge No AND P1–P8 |
| `Low Priority Candidate` | PyPI Yes AND conda-forge No AND P9 or P10 |
| `Conda-Forge Only` | PyPI No AND conda-forge Yes |
| `Not on PyPI` | PyPI No AND conda-forge No |

OpenTeams-universe `Priority_Bucket` is the proposed `P` from the priority pass
(below). Do not keep the old default (`P4` if on `CDO-ENT-CONDA`, else `P9`).
The floor is `P10` (not `P0`).

## Priority, work, and score

Assigned by `scripts/conda-forge-packaging-inventory-operations_priority.py` onto
the live dated identity tab (`--tab identity-2026-08-20`; default still
`identity-2026-08-12`). Do not overwrite a frozen older identity tab. Inventory
`Priority_Bucket` / `OpenTeams_Batch` sync is optional (`--skip-inventory-sync`
when the live identity is ahead of inventory). Board packaging issues with
existing **P2** or **P3** are not overwritten. Current-version vulnerabilities
become **P1** (`Fix vulnerability`) even if they also need an issue. JFROG
`packaging_tier` is ignored. There is no `P0`.

**Work** (`OpenTeams_Batch` / identity `Work`) is what Mason does, not A/B/C:

| Work | Was | Meaning |
|---|---|---|
| `Fix vulnerability` | (new) | Current-version HIGH / `affected_latest`. Wins over recipe/issue/tracked. |
| `Create recipe` | A | JFROG consumed, not on conda-forge (`JFROG_NEW`). |
| `File OpenTeams tracking issue [Conda-Forge Packaging]` | B / C | Already on conda-forge, no OpenTeams tracking issue yet (`JFROG_ON_CF` or `CONDA_ONLY`). |
| `Already tracked` | TRACKED | `[Conda-Forge Packaging] {name}` issue already exists. |

`OpenTeams_Cohort` stays `JFROG_NEW` / `JFROG_ON_CF` / `CONDA_ONLY`. Components
and LOBs never appear without apps, so they do not get their own `P` lane.

**Proposed `P`** (highest first):

| P | Rule |
|---|---|
| **P1** | Current-version vulnerability (`risk_level=HIGH` or `vuln_status=affected_latest`). Existing OpenTeams board P1 also stays here. |
| **P2** | Existing OpenTeams board P2. Not overwritten. |
| **P3** | Existing OpenTeams board P3. Not overwritten. |
| **P4** | `platform_env_count` > 0. |
| **P5** | `internal_app_count` > 0, no platform. |
| **P6** | 100+ Artifactory downloads **or** 100+ Artifactory versions, and not already P1–P5. |
| **P7** | 10+ downloads **or** 10+ versions, below the P6 floor. |
| **P8** | Leftover `Create recipe` (below the P7 floor). |
| **P9** | Leftover `File OpenTeams tracking issue [Conda-Forge Packaging]` for `JFROG_ON_CF`. |
| **P10** | Leftover `File OpenTeams tracking issue [Conda-Forge Packaging]` for `CONDA_ONLY`, plus leftover `Already tracked`. |

Each row carries `Priority_Bucket_Description` with that rule in prose.

**Score** (1–100, percentile of the use formula; work type does not inflate it):

```text
100×platforms + 10×apps + 3×components + 2×LOBs
+ log10(1+downloads) + log10(1+Artifactory versions)
```

Within a `P`, sort `Fix vulnerability` then `Create recipe` then already-tracked
then issue work, then by Score descending.

When the matching verify flag is No, emit `N/A`:

- `PyPI_PURL` — `pkg:pypi/{name}`
- `PyPI_Package_URL` — `https://pypi.org/project/{name}/`
- `Conda-forge_PURL` — `pkg:conda/{name}?channel=conda-forge`
- `Conda-Forge_Package_URL` — `https://anaconda.org/conda-forge/{name}/`
- `Conda-Forge_FeedStock_URL` — prefer CONDA tab slug or Parselmouth conda name,
  else `https://github.com/conda-forge/{name}-feedstock`

## Deliverables

Google Shared Drive for humans; workbook tabs for the local source of record.

**A. Full inventory** — tab `verified-all-packages` (optional CSV export). Exactly
these 14 columns, in order:

1. `Repository_Source`
2. `Role`
3. `Package_Input_Name`
4. `Core_Python_Package_Name`
5. `PyPI_Verified`
6. `CondaForge_Verified`
7. `Priority_Bucket`
8. `Packaging_Candidate_Status`
9. `PyPI_PURL`
10. `PyPI_Package_URL`
11. `Conda-forge_PURL`
12. `Conda-Forge_Package_URL`
13. `Conda-Forge_FeedStock_URL`
14. `Verification_Timestamp_UTC`

**OpenTeams handoff** — tab `inventory-2026-08-12`. Same 14 columns, then:

15. `OpenTeams_Title` — `[Conda-Forge Packaging] {name}`
16. `OpenTeams_Cohort` — `JFROG_NEW` / `JFROG_ON_CF` / `CONDA_ONLY`
17. `OpenTeams_Batch` — work label (`Fix vulnerability` / `Create recipe` /
    `File OpenTeams tracking issue [Conda-Forge Packaging]` /
    `Already tracked`; was A / B / C / TRACKED)
18. `OpenTeams_Labels`
19. `OpenTeams_Milestone` — `OSS Enhancements (Conda Forge, Pixi, ect)`
20. `OpenTeams_Coverage` — `Have_Issue` / `Missing_Issue`
21. `OpenTeams_Issue_URL`
22. `Source_Repository_URL`

`Priority_Bucket` (column 7) is the proposed `P` from the priority pass.
`Priority_Bucket_Description` is appended after the handoff columns so Mason
can read the rule without opening identity.

One row per unique name in parseable JFROG ∪ CONDA. Labels always include
`Conda Forge Packaging` and `No WF org info`; add `WF List 2` if in JFROG;
add `Packaging: New package` if not on conda-forge.

**Identity** — dated tab `identity-YYYY-MM-DD` (live: `identity-2026-08-20`;
frozen: `identity-2026-08-12`). Pass `--tab-out` so a new snapshot does not
overwrite an older one. Identity URLs come from
`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`
(one row per universe name plus **board-only** `[Conda-Forge Packaging]` extras
from the full OpenTeams project 1 join — no milestone slice). Prefer PURL
Associator (`--refresh-associator`) when the conda name exists; otherwise mint
from `PyPI_PURL` + `Source_Repository_URL`. Overlay live `Local_Recipes_URL` and
`Local_Build_Status` from `recipes/` at write and at gist publish. Then the
priority pass (`--tab` matching `--tab-out`) writes ranking columns **first**:

1. `P`
2. `Rank`
3. `Score`
4. `Package`
5. `Work`
6. `Platforms`
7. `Apps`
8. `Downloads`
9. `Versions`
10. `Vuln`
11. `Core_Python_Package_Name` (primary key)
12. `OpenTeams_Title`
13. `identity_source`
14. `associator_key`
15. `associator_status`
16. `primary_purl`
17. `primary_type`
18. `alternative_purls`
19. `cpes`
20. `conda_purl`
21. `source_repository_url`
22. `OpenTeams_Issue_URL`
23. `Conda-Forge_FeedStock_URL`
24. `Conda-Forge_Metadata_URL`
25. `Staged_Recipes_PR_URL`
26. `Local_Recipes_URL`
27. `Local_Build_Status` (`success` / `failed` / `build-clean-test-blocked` / `not-attempted`; blank if no CFE stamp)
28. `Verification_Timestamp_UTC`
29. `Priority_Bucket_Description`
30. `Priority_Source`
31. `Priority_Reason`
32. `JFROG_risk_level`
33. `JFROG_latest_vuln_count`
34. `internal_component_count`
35. `internal_lob_count`

A full identity regen wipes ranking columns. After identity regen, re-run the
priority pass on **that** dated tab, rebuild the three dashboard views, then
publish the gist with **`--gist-only --tab-out <that-tab>`** (reads the current
tab; does not regenerate). Do not run a full identity regen solely to refresh
the gist. Do not overwrite `identity-2026-08-12` to refresh `identity-2026-08-20`.

Feedstock + metadata from [conda-forge.org/packages](https://conda-forge.org/packages/);
staged-recipes PR from
[conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes/pulls?q=is%3Apr);
local recipe from
[rxm7706/local-recipes/recipes](https://github.com/rxm7706/local-recipes/tree/main/recipes).
Blank means missing.

After every inventory rerun: regenerate identity onto a **new** dated tab if the
previous snapshot must be kept, run the priority pass, rebuild the three
dashboard views, then **edit in place** the pinned secret gist files
`mgmt-wf-python-modernization-identity.md` (row catalog) and
`mgmt-wf-python-modernization-dashboards.md` (the three views as GFM + YAML)
with `--gist-only --tab-out <live-tab>`. The gist id comes from
`OPENTEAMS_IDENTITY_GIST_ID`,
`conf/conda-forge-packaging-inventory-operations.local.env` (gitignored; copy
the tracked `.example`), or `--gist-id`. Do not create a new gist. Do not
commit the id. `--skip-gist` is offline tests, or when no id is configured.
The catalog file carries the same 35 identity columns (ranking first), including live `Local_Recipes_URL` and `Local_Build_Status` overlaid from `recipes/` at publish time. Frontmatter also splits those stamps by priority (`local_build_by_p`), recipe type (`local_build_by_type`: `noarch-python` / `noarch-generic` / `compiled` / `arch` / `none`), and successful builds (`local_build_success_by_p_type`). The dashboards file must include machine YAML `priority_buckets` / `work_labels` (each with `n` + `rule` / `meaning`) and human tables with those same rules — a count-only P table is not enough.

**Three dashboard views** (required; a ranked identity tab without them is
incomplete). Cursor canvases beside the chat are the interactive rendering;
gist `mgmt-wf-python-modernization-dashboards.md` is the portable copy of the
ops + Artifactory/workbook views; gist `mgmt-wf-python-modernization-identity.md`
is the portable copy of the catalog. Rebuild all three after every priority
pass.

| View | Canvas (Cursor) | What it shows |
|---|---|---|
| **Catalog** | `identity-2026-08-20.canvas.tsx` | Searchable row browser: every live identity package with `P`, `Work`, `Score`, use signals. Written by `priority.py --canvas`. |
| **Ops** | `identity-ops.canvas.tsx` | Four panes: **Priority** (P1–P10 + work, with rules), **Issues** (packaging-issue gap), **Builds** (CFE stamp by P × noarch/other), **Census** (feedstock / staged-recipes / local build cube). |
| **Artifactory / workbook** | `jfrog-workbook.canvas.tsx` | Five panes: **Map** (CDO-ENT-JFROG → PyPI / conda-forge), **Staged gap** (need staged-recipes PR), **Board gap** (PyPI-only names still missing a packaging issue), **Workbook** (all tabs), **External** (live index counts vs workbook). |

Canvas files live in the Cursor workspace `canvases/` directory (IDE-owned, not
git). Do not spawn extra canvases for slices of these three. Do not keep a
duplicate of the catalog under another name. Bucket **Rule** / work **Meaning**
on the ops Priority pane and in gist YAML must match
`PRIORITY_DESC` / work labels in `priority.py`.

**B. Markdown** `cdao_consolidated_inventory_verified_all_packages.md` — totals,
status breakdown, per-tab and per-source inclusion matrices (100% where
required), overlaps, OpenTeams parse summary, OpenTeams 1:1 coverage (have /
missing / surplus), net-new vs live feeds.

**C.** `docs/reference/conda-forge-packaging-inventory-operations_prompt.md` — self-contained re-run prompt.

**D. Stdout**

```text
=== MASTER PROMPT V3.0 EXECUTION SUMMARY METRICS ===

Total final unique packages processed: <number>
Count not on conda-forge: <number>
Count from analysis-dataset portion not on conda-forge: <number>
Count parsed from OpenTeams-style portion:
  - rows used by rule (a): <number>
  - rows used by rule (b): <number>
  - rows ignored by rule (c): <number>
  - unique packages extracted from that portion: <number>
```

**E. Quality gates**

1. Deliverable A has exactly those 14 columns in order. The handoff tab keeps
   them first, then the 8 OpenTeams columns, then `Priority_Bucket_Description`.
2. `Core_Python_Package_Name` is unique.
3. Markdown includes every required section.
4. Inclusion matrices match totals. JFROG, CONDA, `GAOSS-Free`, and
   `GAOSS-Premium` are 100% of parseable names. `10kClosed` is not a 100%
   inclusion tab.
5. Stdout numbers match the outputs.
6. Markdown reports OpenTeams 1:1 coverage. 100% have-issue is the **goal**,
   not a pass/fail of the inventory rebuild.
7. Handoff `Source_Repository_URL` is filled from channeldata **and** PyPI JSON.
   Skipping PyPI JSON for names not on conda-forge fails the gate.
8. Identity ranking columns `P`, `Rank`, `Score`, `Work` are filled. `P` uses
   `P1`–`P10` (no `P0`). `OpenTeams_Batch` is a work label, not
   A/B/C/TRACKED. Leftover file-issue work is one label:
   `File OpenTeams tracking issue [Conda-Forge Packaging]`.
9. The three dashboard views exist for the live identity tab (catalog, ops,
   Artifactory/workbook). Gist dashboards YAML `priority_buckets` / `work_labels`
   carry `n` plus the rule/meaning. Count-only P tables fail the gate.
10. Gist publish edits **both** files in place (`…-identity.md` and
    `…-dashboards.md`). No new gist. Frozen `identity-2026-08-12` is untouched.

## Constraints

- One package, one PEP 503 name, unless an alias is explicit.
- Provenance end to end; no priority without evidence.
- Same raw inputs and versions produce the same results from an empty output dir.
- Offline-safe from repo-tracked inputs plus declared refresh sources.
- Handoff is consumable by existing conda-forge / Mason workflows.
- Do not rename or reorder deliverable A's 14 columns. The handoff tab may only
  append after them.
- Dropping 10k junk must not remove a JFROG or CONDA name.
- Do not overwrite OpenTeams board P2/P3 on packaging issues.
- Do not use JFROG `packaging_tier` as proposed `P`.
- Do not invent `P0`. Floor is `P10`.
- Do not overwrite a frozen dated identity tab (`identity-2026-08-12`) when
  building a newer snapshot.
- Do not join OpenTeams on the OSS-milestone slice; packaging-issue match is
  every `[Conda-Forge Packaging] {name}` title on project 1.
- Do not skip the three dashboard views after a priority pass.
- Do not commit `OPENTEAMS_IDENTITY_GIST_ID` or create a new identity gist.

## Non-goals

- Not replacing conda-forge-expert recipe authoring, build, or submit.
- Not a real-time web service; batch refresh is enough.
- Not an opaque rank: `Score` is the documented use formula; `P` is the
  documented hierarchy; `Work` is the documented Mason action.
- Not pushing proposed `P` onto the OpenTeams board until asked.
- Not bootstrapping from a prior consolidated inventory.
- Not a second runner beside the v3 quartet.
- Not extra canvases beyond the three views (no per-slice duplicates of catalog
  / ops / Artifactory-workbook).

## Kinships

[[packaging-factory]] · [[upstream-discovery]] · [[pyforge-atlas]] · [[pyforge-mason]]

## Realization log

- **2026-08-16** — Seeded (`0f0b75232e`).
- **2026-08-22** — `spec-conda-forge-packaging-inventory-operations` derived under pyforge-atlas and
  decomposed into the station backlog (`a20192dd84`). The Spec now reads `in-progress`: CAP-1
  (Story 17.1) chartered; CAP-2 (Story 17.2) code landed, live-execution verification deferred
  pending an attended, credentialed run.
