# Tech Spec: Trendshift — Top GitHub-Trending Python Repos → conda-forge

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track).
> **Hybrid shape**: a *timeless, re-runnable* discovery→triage→package
> **workflow** (parameterized, like `feedstock-platform-expansion.md`),
> built on a **new cf_atlas discovery engine** (Phase T + a
> `trending-candidates` CLI/MCP tool), **plus** a concrete **first
> worked-example batch** packaging the current trending snapshot
> (the 2026-06-20 run, seeded by `HKUDS/CLI-Anything`).
>
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/trendshift-conda-forge.md
> ```
>
> **Rule-1 reminder:** every recipe-touching sub-task here MUST go through
> the `conda-forge-expert` skill (CLAUDE.md BMAD↔CFE Rule 1). The skill's
> 10-step autonomous loop, Critical Constraints, and Build-Failure Protocol
> are authoritative over any story text below. **Rule-2 reminder:** the
> effort closes with a CFE-skill retrospective (Wave D, S-retro).

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake. 5 open questions (Q1–Q5); Q1 (source robustness) gates Wave A, the rest non-blocking. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only; no PRD/architecture phase) |
| Codename | **trendshift** |
| Upstream | The top GitHub-trending Python repositories (a *moving target*, re-sampled each batch). First batch = 2026-06-20 snapshot. |
| Target | (a) cf_atlas **Phase T** discovery engine + `trending-candidates` CLI/MCP tool (this repo); (b) `conda-forge/staged-recipes` new feedstocks for each Tier-1/Tier-2 candidate. |
| Distribution | conda-forge (noarch:python for pure-Python/CLI; per-platform for compiled/Rust/Go). |
| Lifetime | **Recurring.** The engine + workflow are permanent; each *batch* is a one-shot land-and-handoff. New batches re-run the same workflow on a cadence (Q4). |

---

## Background and Context

### The problem

GitHub's trending feed is where high-velocity Python projects surface
*before* they are widely packaged. Today there is **no systematic path**
from "repo is trending" → "is it conda-actionable?" → "ship the gap to
conda-forge." The result is a recurring, manual, lossy scramble: a human
eyeballs `github.com/trending/python`, guesses which repos have a PyPI
artifact and a clean license, and re-checks `lookup_feedstock` by hand —
every time, from scratch, with no memory between sessions.

This is exactly the shape the `microsoft-conda-forge.md` audit solved for
*one fixed org* (`github.com/microsoft/*`): enumerate → cross-check
against conda-forge → triage the gap → wave-package. **Trendshift
generalizes that audit to a moving target** and makes it *repeatable* by
encoding the discovery + triage as a first-class cf_atlas pipeline phase
instead of a one-time manual sweep.

The codename nods to **trendshift.io**, a UI that tracks GitHub repos "as
they rise." (It has **no public JSON API** — see § Dependencies — so it is
a human cross-reference, never a data source.)

### Why this is *not* just "another packaging spec"

The microsoft spec froze a hand-audited list into fixed stories. Trending
shifts daily; a frozen list is stale the day after it is written. So this
spec has **two layers**:

1. **The engine (Wave A)** — a new cf_atlas **Phase T** that ingests the
   trending feed, cross-filters it against everything the atlas already
   knows (shipped feedstocks, the PyPI universe, PyPI intelligence:
   license / `requires_python` / packaging-shape / downloads), and emits a
   **tiered, conda-actionable candidate list**. Exposed as a
   `trending-candidates` CLI + MCP tool. Offline-after-fetch, re-runnable,
   air-gap-safe like every other read-side atlas CLI.

2. **The workflow (Waves B–D)** — the timeless discover→triage→package
   loop that *consumes* the engine's output, plus a **concrete first
   batch** (the 2026-06-20 snapshot) that ships real recipes and proves
   the engine end-to-end. CLI-Anything is the named first recipe.

### What "trending" actually means here (and the source reality)

There is **no official GitHub Trending API**. The machine-readable options,
ranked by robustness:

| Source | Form | Auth | Robustness | Role |
|---|---|---|---|---|
| `github.com/trending/python?since={daily,weekly,monthly}` | HTML scrape | none | **Fragile** (layout can change; unofficial) | **Primary** trending signal |
| GitHub Search API (`/search/repositories?q=language:python created:>DATE sort:stars`) | JSON | token | **Robust** (official, rate-limited) | **Fallback / corroboration** — approximates star-velocity for *new* repos |
| `trendshift.io` | HTML, **no JSON API** | none | n/a | **Human cross-reference only** — never scraped programmatically |
| cf_atlas existing signals (`adoption-stage`, `pypi-intelligence` downloads, `release-cadence`) | local SQL | none | Robust | **Enrichment**, not discovery (these measure *popular*, not *trending*) |

**Design stance:** Phase T treats the HTML scrape as the primary feed and
the Search API as a corroborating fallback (Q1). It never depends on
`trendshift.io`. The existing atlas signals enrich and rank — they do not
*discover*, because "popular" ≠ "rising."

### What's been investigated (first-batch triage, 2026-06-20)

A WebFetch of `github.com/trending/python?since=daily` on 2026-06-20
returned 17 repos. A first-pass manual triage (the kind Phase T will
automate) splits them:

- **Already on conda-forge → skip**: `yt-dlp/yt-dlp`,
  `microsoft/presidio` (`presidio-analyzer`).
- **Not a package (awesome-list / dataset / skills-collection / app) →
  skip**: `public-apis/public-apis`, `mukul975/Anthropic-Cybersecurity-Skills`,
  `zubair-trabzada/geo-seo-claude`, `mikumifa/biliTickerBuy` (GUI tool),
  `home-assistant/core` (application + mega-dep tree),
  `onyx-dot-app/onyx` (platform app), `Alishahryar1/free-claude-code`
  (wrapper), `calesthio/OpenMontage` (agentic app).
- **Tier-1 candidates (PyPI lib/CLI, OSI license, not on cf — verify)**:
  `google-research/timesfm`, `stanford-oval/storm`
  (`knowledge-storm`), `santinic/audiblez`, **`HKUDS/CLI-Anything`**
  (`cli-anything-hub`, Apache-2.0, Py≥3.10 — the named first recipe).
- **Tier-2 candidates (compiled / heavy / prereq-closure — verify)**:
  `unslothai/unsloth`, `Lightricks/LTX-2`, `THUDM/slime`,
  `chopratejas/headroom`.

> **Honesty marker:** the PyPI-presence / license / not-on-cf assertions
> above are *first-pass heuristics*, not verified facts. Each becomes a
> verified row only when Phase T runs and `check_dependencies` /
> `lookup_feedstock` / `generate_recipe_from_pypi` confirm it at
> execution. The spec deliberately does **not** bake precise versions or
> licenses into stories beyond CLI-Anything (whose facts were fetched).

### What's available to leverage

- **cf_atlas at schema v28**, phases B→S, 17+ read-side CLIs. Phase T is
  the next sequential phase letter (T-for-Trending). The engineering
  patterns are codified in
  `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`
  (§ 10 (a)–(k): atomic writes, `DELETE+INSERT` over `INSERT OR REPLACE`
  on partial reruns, verified provenance columns, dry-run preflight,
  rate-limit discipline, step-04 adversarial review is load-bearing for
  dispatcher-touching changes).
- **Phase N** (`phase_n_github_live`) already does authenticated live
  GitHub with the Phase-K-class rate-limit handling — Phase T reuses its
  HTTP + token plumbing (`_http.py`) rather than inventing new fetch code.
- **PyPI intelligence (Phases O–S, schema v22+)** already computes, per
  `pypi_name`: license, `requires_python`, packaging-shape classifier,
  `downloads_30d/90d`, cross-channel presence, and a
  `conda_forge_readiness` score (0–100). Phase T's classifier *joins*
  these — it does not recompute them.
- **Feedstock enumeration (Phase B / B.5)** + `lookup_feedstock` give the
  authoritative "already on conda-forge?" answer for the skip filter.
- **`conda-forge-expert` skill** (`generate_recipe_from_pypi`,
  `validate_recipe`, `optimize_recipe`, `check_dependencies`,
  `scan_for_vulnerabilities`, `trigger_build`, `prepare_submission_branch`,
  `submit_pr`) drives every recipe story via its 10-step loop.
- **Canonical templates**: `templates/python/noarch-recipe.yaml` (Tier-1),
  `templates/rust/cli-recipe.yaml` + `templates/multi-output/*` (Tier-2
  compiled), and the `cli-anything-hub` Click-CLI shape matches the
  pure-Python noarch template directly.
- **Precedent specs**: `microsoft-conda-forge.md` (audit→triage→wave
  packaging), `feedstock-platform-expansion.md` (parameterized timeless
  workflow + appended worked examples), the `atlas-phase-*` specs
  (schema-migration + new-CLI mechanics, three-places rule).

---

## Goals

- **G1.** Ship a cf_atlas **Phase T** that ingests GitHub-trending Python
  repos (daily/weekly/monthly) into a new `github_trending_repos` table
  (schema v28→v29), with atomic writes + provenance + rate-limit
  discipline per `atlas-phase-engineering.md`.
- **G2.** Ship a **tier classifier** that joins each trending repo against
  feedstock enumeration + `pypi_universe` + `pypi_intelligence` and labels
  it `tier` ∈ {1, 2, skip} with a machine-readable `skip_reason`, surfaced
  via a `v_trending_candidates` view.
- **G3.** Ship a **`trending-candidates` CLI + `trending_candidates` MCP
  tool** (the canonical operator surface) with `--period`, `--tier`,
  `--top`, `--not-on-cf`, `--min-stars`, `--json` flags. Offline-safe,
  read-side, idempotent. Registered in all three places (pixi task + meta
  test SCRIPTS list + wrapper) per the auto-memory three-places rule.
- **G4.** Run the **first batch** (2026-06-20 snapshot) end-to-end:
  produce the verified tiered candidate list, then land **CLI-Anything
  (`cli-anything-hub`)** as the named first `recipes/<name>/` recipe.
- **G5.** Land the remaining **Tier-1 curated-gap recipes** from the first
  batch (the verified subset of timesfm / knowledge-storm / audiblez /
  …) — each `noarch:python`, leaves-first.
- **G6.** Land the **Tier-2 broad/compiled recipes** from the first batch
  that survive verification (unsloth / LTX-2 / slime / headroom subset),
  including any prerequisite-recipe closures and per-platform builds.
- **G7.** Encode the **timeless workflow** as a CFE guide
  (`guides/trending-discovery.md`) so future batches re-run without
  re-reading this spec, and (Q4) optionally wire a **cadence**
  (`/schedule` or the Phase-K cron-runner pattern) for monthly re-sampling.
- **G8.** Each recipe carries `rxm7706` as a maintainer (additive); each
  PR cites the upstream repo + license + the CFE version that authored it.
- **G9.** Close with the **CFE-skill retro** (Rule 2): SKILL.md /
  reference / CHANGELOG deltas for any novel gotcha surfaced across the
  engine build + first batch.

## Non-Goals

- **NG1.** No dependence on `trendshift.io` scraping. No public API; ToS
  risk; the codename is homage, not a data source.
- **NG2.** No packaging of repos that are not libraries/CLIs: awesome-lists,
  datasets, skills-collections, docs/training repos, GUI desktop apps, or
  applications with a mega-dependency tree (e.g. `home-assistant/core`).
  These are classified `skip` with a reason and never become stories.
- **NG3.** No re-packaging of already-shipped feedstocks. The skip filter
  removes anything `lookup_feedstock` already resolves.
- **NG4.** No upstream PRs to the trending repos (no README fixes, no
  license corrections, no pyproject loosening). Recipes absorb artifacts
  as published.
- **NG5.** No CUDA-variant recipes in v1. GPU-heavy Tier-2 candidates
  (unsloth, LTX-2) ship CPU/`pytorch`-generic recipes first; GPU variants
  defer to follow-on PRs.
- **NG6.** No new external data source beyond the GitHub Trending HTML +
  the GitHub Search API (both already reachable via `_http.py`). No
  BigQuery, no paid feed. (Phase T adds *zero* new firewall-blocking
  dependency — important for the air-gapped/JFrog story.)
- **NG7.** Phase T does **not** auto-submit recipes. It produces a
  *candidate list*; a human (or `bmad-quick-dev`) decides what to package.
  Discovery ≠ submission.
- **NG8.** No schema redesign of the existing PyPI-intelligence tables.
  Phase T *joins* them read-only; it adds its own table + view only.

---

## Parameters (per-batch)

This spec is parameterized like `feedstock-platform-expansion.md`. A batch
run binds these; defaults in **bold**.

| Param | Meaning | Default |
|---|---|---|
| `<batch_date>` | The snapshot date the batch is sampled on | run date |
| `<period>` | Trending window to ingest | **`weekly`** (less noisy than daily, fresher than monthly) |
| `<top_n>` | How many trending repos to ingest before tiering | **100** |
| `<tier_scope>` | Which tiers to actually package this batch | **`1,2`** |
| `<min_stars>` | Floor to drop micro-repos | **500** |
| `<fork_owner>` | staged-recipes fork owner for submissions | `rxm7706` |
| `<cadence>` | Re-sample interval (Q4) | **`monthly`** (or manual) |

> **Ingest depth vs display limit:** `<top_n>` is how many trending rows
> Phase T *stores* (default 100). The `trending-candidates --top` flag is a
> *display* cap over the already-ingested set (default 25). Independent
> knobs — ingest wide, show narrow.

First batch binding: `<batch_date>=2026-06-20`, `<period>=daily`
(the snapshot already fetched), `<top_n>=17` (what trending returned),
`<tier_scope>=1,2`, `<min_stars>=500`.

---

## Tier Definitions

The classifier (G2) is the heart of the engine. Tiers are
**data-driven and extensible** — the user's explicit guidance is "add
other tiers based on actual data later," so the schema stores `tier` as a
small int and `skip_reason`/`tier_reason` as free text; new tiers are a
classifier-logic change, not a migration.

| Tier | Label | Inclusion test | Recipe shape | First-batch examples |
|---|---|---|---|---|
| **1** | **Curated gap** | PyPI-published **AND** library-or-CLI shape **AND** OSI license **AND** not-on-cf **AND** small/moderate dep tree (no compiled prereq closure) | `noarch:python`, one recipe | cli-anything-hub, knowledge-storm, audiblez, timesfm* |
| **2** | **Broad / compiled** | Packageable but: Rust/Go CLI, native/compiled, multi-output, GPU/heavy, **or** needs a prerequisite-recipe closure | per-platform and/or multi-output, possibly +prereq recipes | unsloth, LTX-2, slime, headroom |
| **skip** | **Not actionable** | no PyPI artifact & no clean lib/CLI shape; awesome-list / dataset / skills / docs / GUI app / mega-dep app; **or** already on conda-forge | — (never a story) | public-apis, home-assistant/core, yt-dlp (shipped), presidio (shipped) |
| **3+** | *(reserved, data-driven)* | Defined empirically after ≥3 batches — likely "monorepo-subpackage", "app-with-embedded-lib", "research-snapshot-no-release". Placeholder only in v1. | TBD | — |

`timesfm*` may demote to Tier-2 if its `jax`/`pytorch` dep surface forces
a heavy closure — the classifier decides at execution, not here.

---

## Lifecycle Expectations

- **The engine is permanent.** Phase T + `trending-candidates` become part
  of the standard atlas build (`bootstrap_data.py` phase list) and ship
  forever. Like every read-side CLI, they are offline-safe after the
  fetch.
- **Each batch is one-shot.** A batch samples trending on `<batch_date>`,
  triages, ships the Tier-1/Tier-2 gap to staged-recipes, and hands the
  feedstocks to `regro-cf-autotick-bot`. The batch is "done" when its PRs
  reach a terminal state (merged / on-hold / deferred).
- **Cadence (Q4).** Future batches re-run the same workflow monthly
  (default) via `/schedule` or the Phase-K cron-runner pattern. Each new
  batch appends a row to § Worked Examples; the timeless "how" lives in
  the CFE guide, not in re-reads of this spec.
- **Maintainer posture.** Each new feedstock ships
  `[rxm7706, <any co-maintainer surfaced at PR review>]`. No commitment to
  long-term solo maintenance; community co-maintainers welcome at review.

---

## User Stories

4 waves. Wave A builds the engine; Waves B–C are the first batch
(parallel-safe within a wave; each wave depends only on the previous
wave's PRs *entering* the review queue, not merging); Wave D is
cadence + closeout.

**Envelope: ~10–18 stories / ~25–45 h** — 5 engine (A1–A5) + 2 closeout
(D1–D2) are fixed; the **first-batch recipe count is open** (≈3–11) and is
finalized by B1's verified triage. Treat the Bn/Cn seeds below as a
starting list, not a committed count.

| Wave | Stories | Description |
|---|---|---|
| A | A1–A5 | **Engine**: schema v29 + Phase T ingest + tier classifier + `trending-candidates` CLI/MCP + tests. |
| B | B1, **B-CLI-Anything**, B2…Bn | **First batch, Tier-1**: B1 runs the engine + triage; B-CLI-Anything ships `cli-anything-hub` (named, parallel-safe with B1); B2…Bn ship the verified curated-gap `noarch:python` recipes. |
| C | C1–C? | **First batch, Tier-2**: ship broad/compiled recipes + any prereq closures. |
| D | D1 (guide+cadence), D2 (retro) | **Cadence + closeout**: CFE guide, optional `/schedule`, CFE-skill retro (Rule 2). |

### Wave A — The discovery engine

#### Story A1 — Schema v28→v29: `github_trending_repos` + `v_trending_candidates`

**Goal**: Add the storage layer for trending ingestion.

**Acceptance criteria**:
- `SCHEMA_VERSION` bumped 28 → 29 in `conda_forge_atlas.py` with a
  forward migration that creates:
  - **`github_trending_repos`** — columns: `full_name` (PK part),
    `owner`, `repo`, `description`, `language`, `stars`, `stars_delta`,
    `rank`, `period` (PK part: daily|weekly|monthly), `snapshot_date`
    (PK part), `source` (`github-trending`|`search-api`), `captured_at`.
    Composite PK `(full_name, period, snapshot_date)`.
  - **`trending_classification`** — the **materialized** classifier
    output (resolves the view-vs-stored ambiguity: tiers are *stored*,
    not computed in the view, so the CLI/MCP read is a plain SELECT and
    reruns are DELETE+INSERT per § 10 (g)). Keyed
    `(full_name, period, snapshot_date)` (FK to `github_trending_repos`);
    columns `on_conda_forge`, `pypi_name`, `pypi_published`, `license`,
    `requires_python`, `packaging_shape`, `downloads_30d`,
    `conda_forge_readiness`, `tier`, `tier_reason`, `skip_reason`,
    `classified_at`. Written by A3.
  - **`v_trending_candidates`** — a VIEW that LEFT JOINs
    `github_trending_repos` to `trending_classification` (so a freshly
    ingested but not-yet-classified row still appears, with null tier).
    This is the operator-facing surface the `trending-candidates` CLI +
    MCP tool read.
- Migration is **idempotent** and uses the project's standard
  `CREATE TABLE IF NOT EXISTS` + `user_version` bump path (mirror an
  existing migration, e.g. the v27→v28 one).
- A structural meta-test asserts the new table + view exist after a
  migration of a v28 fixture DB.

**Wave**: A. **Effort**: 1.5–2 h.

#### Story A2 — Phase T: trending ingestion

**Goal**: Implement `phase_t_github_trending(conn)` that fetches the
trending feed and writes `github_trending_repos`.

**Acceptance criteria**:
- New `phase_t_github_trending` in `conda_forge_atlas.py`, registered in
  the dispatcher + `bootstrap_data.py` phase list + `atlas_phase.py`
  selectable phases, **gated to the `admin` profile by default** (and
  `maintainer` if cheap — it is one HTML GET per period, so enable it for
  `maintainer` too; `consumer` off).
- Primary fetch: `github.com/trending/python?since=<period>` via
  `_http.make_request` (reusing Phase N's plumbing). Parse the repo
  rows (owner/name, description, language, total stars, period-delta,
  rank) from the HTML.
- **Fallback / corroboration (Q1)**: if the scrape yields < `min_rows`
  (layout drift) or `TRENDSHIFT_USE_SEARCH_API=1`, query the GitHub
  Search API (`language:python created:>{date-30d} sort:stars`,
  authenticated) and tag those rows `source=search-api`.
- **Rate-limit discipline**: single sustained request rate (reuse the
  Phase-K token-bucket pattern, default ≤ 3 req/s); no burst pool. One
  scrape + at most one Search-API page per period.
- **Atomic writes**: `DELETE` the `(period, snapshot_date)` slice then
  `INSERT` (per § 10 (g) — *not* `INSERT OR REPLACE`, so a partial rerun
  doesn't leave stale rows).
- **Provenance**: `source` + `captured_at` populated on every row;
  verified against the actual writer (§ 10 (h)).
- Phase T is **skippable** in lean builds (like F/K/N) and **never blocks**
  the daily atlas build if the scrape 404s/changes — it logs a WARN and
  leaves the prior snapshot intact (no hard failure).
- A test fixture with a saved trending-HTML sample parses to the expected
  row count + fields (so the parser is regression-guarded against the
  fragile-scrape risk).

**Wave**: A. **Blocked by**: A1. **Effort**: 3–5 h (HTML parser + the
fallback path + the rate-limit/atomic-write discipline are the meat).

#### Story A3 — Tier classifier

**Goal**: Compute `tier` / `tier_reason` / `skip_reason` + the actionable
join columns for every trending row.

**Acceptance criteria**:
- A classifier (a phase-T sub-step or a `phase_t` post-pass) that, per
  trending repo, derives:
  - `on_conda_forge` via feedstock enumeration / `lookup_feedstock`
    (the repo's likely `pypi_name`, checked with the **4-spelling rule**
    from `feedback_pypi_conda_mapping_unreliable.md` — bare, hyphen↔under,
    `-py`, `-python`).
  - `pypi_name` + `pypi_published` via `pypi_universe`.
  - `license`, `requires_python`, `packaging_shape`, `downloads_30d`,
    `conda_forge_readiness` via `pypi_intelligence` (join on `pypi_name`).
  - `tier` ∈ {1, 2, skip} + a human-readable reason, per the § Tier
    Definitions table.
- **Skip reasons are explicit and enumerated** (e.g.
  `already-on-conda-forge`, `no-pypi-artifact`, `awesome-list`,
  `not-osi-license`, `application-not-library`, `mega-dep-tree`). No
  silent drops — every ingested repo gets a tier or a skip_reason.
- The classifier is **pure SQL + local data** (no new network) so it is
  offline-safe and re-runnable.
- Empirical safety valve: repos the classifier can't confidently place —
  **including any run where the PyPI-intelligence phases (O–S) were skipped**
  (a lean / air-gapped build, so the join columns are null) — land
  `tier=2, tier_reason='unclassified-needs-human'` rather than being
  silently skipped (so nothing high-velocity is lost to a classifier gap
  or a degraded build).
- Test: a fixture of ~10 hand-labeled trending repos classifies to the
  expected tiers (incl. one already-on-cf skip, one awesome-list skip, one
  clean Tier-1, one compiled Tier-2).

**Wave**: A. **Blocked by**: A1, A2. **Effort**: 3–4 h.

#### Story A4 — `trending-candidates` CLI + MCP tool + pixi task

**Goal**: The operator surface over `v_trending_candidates`.

**Acceptance criteria**:
- New CLI `trending_candidates.py` in
  `.claude/skills/conda-forge-expert/scripts/` (canonical impl) +
  thin wrapper in `.claude/scripts/conda-forge-expert/` (the public
  entrypoint layer).
- Flags: `--period {daily,weekly,monthly}` (default weekly),
  `--tier {1,2,skip,all}` (default `1,2`), `--top N` (default 25),
  `--not-on-cf/--all` (default `--not-on-cf`), `--min-stars N`,
  `--json`. Output: a ranked table (rank, repo, stars, Δ, pypi_name,
  tier, readiness, reason) or JSON.
- **Read-side, offline-safe, idempotent** — queries the local DB only;
  no fetch. (Phase T does the fetch; the CLI reads its output.)
- `download_pr_artifacts`-style **MCP tool** `trending_candidates`
  registered in `.claude/tools/conda_forge_server.py`, same args.
- **Three-places rule** (auto-memory `feedback_cfe_new_script_three_places`):
  - `pixi.toml` task `trending-candidates`,
  - `SCRIPTS` list in `tests/meta/test_all_scripts_runnable.py`,
  - wrapper (or `no_task_allowlist` entry).
  The existing meta-tests must stay green.
- `commands-cheatsheet.md` + `mcp-tools.md` document the new surface.

**Wave**: A. **Blocked by**: A1–A3. **Effort**: 2–3 h.

#### Story A5 — Engine tests + adversarial review

**Goal**: Lock the engine behind tests; run the load-bearing step-04
adversarial review (§ 10 (i): mandatory for dispatcher-touching changes).

**Acceptance criteria**:
- Unit tests: HTML parser (A2 fixture), classifier (A3 fixture), CLI
  output shape + `--json` schema, MCP tool round-trip.
- Meta-tests green: `test_all_scripts_runnable.py` includes the new
  script; schema-version test recognizes v29; phase-list test includes T.
- **Adversarial self-review** of the Phase-T writer + dispatcher wiring
  per `atlas-phase-engineering.md` § 10 (i) (the atomic-write slice
  semantics, the never-hard-fail-the-build guarantee, the provenance
  columns) — documented in the story's closeout note.
- A regression guard mirroring `test_no_thirty_gb_lie.py`: grep the spec
  + docs + code to assert no claim that Phase T scrapes `trendshift.io`
  programmatically (structural enforcement of NG1).

**Wave**: A. **Blocked by**: A1–A4. **Effort**: 2–3 h.

### Wave B — First batch, Tier-1 (curated gaps)

#### Story B1 — Run the engine; produce the verified first-batch triage

**Goal**: Execute Phase T on the 2026-06-20 snapshot and emit the *real*
tiered candidate list (replacing the first-pass heuristics in § Background).

**Acceptance criteria**:
- `pixi run -e local-recipes trending-candidates --period daily --top 17
  --tier all --json` produces a triage with every repo labeled.
- The triage is recorded in
  `_bmad-output/projects/local-recipes/implementation-artifacts/trendshift-batch-2026-06-20.md`
  (the worked-example artifact), and § Worked Examples below is updated
  with the verified tier assignments + per-repo `pypi_name`, license,
  and not-on-cf confirmation.
- Each Tier-1/Tier-2 row that survives gets its own Bn/Cn story appended
  (the story list below is seeded, not exhaustive — B1 finalizes it).

**Wave**: B. **Blocked by**: Wave A. **Effort**: 1 h.

#### Story B-CLI-Anything — Recipe: `cli-anything-hub` (the named first recipe)

**Goal**: Land `HKUDS/CLI-Anything` (`cli-anything-hub` on PyPI,
Apache-2.0, Py≥3.10, Click≥8) as a `noarch:python` recipe — the
first-recipe proof that the engine→package path works.

**Acceptance criteria**:
- `recipes/cli-anything-hub/recipe.yaml` validates clean (v1 schema +
  the local-recipes schema-header comment).
- Source from PyPI sdist (`cli_anything_hub-${{ version }}.tar.gz`);
  verify sha256. Version = current latest at execution.
- `noarch: python`; build `pip install . --no-deps --no-build-isolation`.
- Host: `python ${{ python_min }}.*`, `pip`, the upstream build backend
  (verify setuptools/hatchling from the sdist `pyproject.toml`).
- Run: `python >=${{ python_min }}`, `click >=8`, + any others surfaced by
  `check_dependencies` (the harness/back-end deps like `lxml` are
  *optional per-CLI* extras — flatten into `run_constraints:` unless a
  hard import, per the audit).
- `python_min: "3.10"` (upstream floor = conda-forge floor; omit from
  `context:` per `feedback_omit_python_min_at_default_floor`).
- Tests: `import` of the top-level package + the `cli-anything-hub`
  console-script `--help` (verify the entry-point name from
  `[project.scripts]`), + `pip check`.
- License: Apache-2.0 — `LICENSE` at sdist root (Pattern 1).
- `extra.cfe-*` internal metadata block present (per
  `feedback_extra_is_local_internal_metadata`); stripped before push.
- Builds clean locally via `pixi run -e local-recipes recipe-build
  recipes/cli-anything-hub`.
- `submit_pr(recipe_name="cli-anything-hub")` returns a `pr_url`.

**Wave**: B. **Blocked by**: B1 *(soft — CLI-Anything's facts are already
known, so it may run in parallel with B1's triage; B1 only corroborates
the tier)*. **Effort**: 1.5–2 h.

> **Open verification (Q5)**: CLI-Anything's README implies a "hub"
> package manager (`cli-anything-hub`) plus *generated* per-software CLIs
> installed via `pip install -e .`. Only the **hub** is a stable PyPI
> artifact; the generated harnesses are not. The recipe packages the hub
> only. Confirm the exact PyPI dist name + that the generated-CLI
> machinery degrades gracefully without the optional backend deps.

#### Stories B2…Bn — Tier-1 curated-gap recipes (seeded; finalized by B1)

For each verified Tier-1 repo from B1, one `noarch:python` story
following the same shape as B-CLI-Anything. Seeds (subject to B1
verification — do **not** treat as committed until verified):

- **B2 — `knowledge-storm`** (`stanford-oval/storm`). LLM knowledge-
  curation library; verify PyPI name (`knowledge-storm`), license, dep
  tree (likely `dspy`, `wikipedia`, LLM clients — audit for unmapped).
- **B3 — `timesfm`** (`google-research/timesfm`). Time-series foundation
  model. **Risk**: `jax`/`pytorch` + possible compiled deps may demote it
  to Tier-2 at classify time. If demoted, it moves to Wave C.
- **B4 — `audiblez`** (`santinic/audiblez`). e-book→audiobook CLI; verify
  PyPI name, the TTS backend dep (kokoro/`soundfile`/`ffmpeg`) — the
  audio stack may add a `run_constraints:` block or demote to Tier-2.

Each: PyPI source, `noarch:python`, dep audit via `check_dependencies`
(4-spelling rule), `python_min` per upstream floor, OSI license Pattern 1,
`pip check` test, `extra.cfe-*` block, local build, `submit_pr`.

**Wave**: B. **Blocked by**: B1. **Effort**: 1–2 h each.

### Wave C — First batch, Tier-2 (broad / compiled)

#### Stories C1…Cn — Tier-2 recipes + prereq closures (seeded; finalized by B1)

For each verified Tier-2 repo, a per-platform / multi-output / prereq-
closure story. Seeds (verify at B1; some may prove unpackageable and
demote to `skip` with a documented reason):

- **C1 — `headroom`** (`chopratejas/headroom`). Token-compression
  tool. Likely pure-Python CLI but classified Tier-2 if it carries a
  compiled tokenizer or a prereq closure; audit at B1. If it's clean
  pure-Python, promote to Tier-1.
- **C2 — `unsloth`** (`unslothai/unsloth`). LLM fine-tuning. Heavy:
  `pytorch`, `triton`, `transformers`, `bitsandbytes`, `xformers`. CPU/
  generic recipe first (NG5). Expect a non-trivial dep audit + possible
  unmapped/GPU-only deps dropped to `run_constraints:` with TODOs.
- **C3 — `LTX-2`** (`Lightricks/LTX-2`). Video-gen inference + LoRA
  trainer. Heavy torch/diffusers stack; verify PyPI dist name + license;
  CPU recipe first.
- **C4 — `slime`** (`THUDM/slime`). LLM RL post-training framework;
  verify PyPI presence (many research frameworks are clone-only → would
  `skip` with `no-pypi-artifact`).

Each Tier-2 story: leaves-first prereq closure (any missing dep gets its
own mini-recipe in the same wave or a documented drop), per-platform build
matrix where compiled, `pip check` (or `pip_check: false` with a
documented external-bug reason, e.g. the db-gpt `pdfminer.six` precedent),
`extra.cfe-*` block, local build, `submit_pr`.

**Wave**: C. **Blocked by**: B1 (triage) + Wave B PRs entering review.
**Effort**: 2–6 h each depending on closure depth.

### Wave D — Cadence + closeout

#### Story D1 — Timeless guide + optional cadence

**Goal**: Make future batches re-run without re-reading this spec.

**Acceptance criteria**:
- New CFE guide
  `.claude/skills/conda-forge-expert/guides/trending-discovery.md`:
  the timeless discover→triage→package procedure (run Phase T →
  `trending-candidates` → tier-by-tier packaging via the 10-step loop →
  worked-example append). Mirrors the structure of
  `guides/feedstock-platform-expansion.md`.
- (Q4) Optional cadence: a `/schedule` routine **or** a Phase-K-style
  cron entry that re-runs Phase T monthly and surfaces the new
  `trending-candidates` list for human review. **Discovery only — never
  auto-submits** (NG7).
- This spec's § Worked Examples documents how new batches append.

**Wave**: D. **Effort**: 1.5–2 h.

#### Story D2 — Closeout CFE retro (Rule 2)

**Goal**: Mandatory CFE-skill retrospective.

**Acceptance criteria**:
- `bmad-retrospective` run; retro filed at
  `_bmad-output/projects/local-recipes/implementation-artifacts/retro-trendshift-<date>.md`.
- Corrections / refinements / additions across Wave A (new phase
  engineering — does `atlas-phase-engineering.md` need a Phase-T-specific
  sub-rule? e.g. fragile-scrape parser-fixture discipline) and Waves B–C
  (any new PyPI→conda mapping gaps → `feedback_pypi_conda_mapping_unreliable.md`;
  any new Tier-2 closure gotcha → SKILL.md G-series).
- SKILL.md / reference / guides edits + `CHANGELOG.md` version bump
  (MINOR if a new gotcha-section or the new guide is added).
- This spec's Status header flipped to **Shipped <date>** with the engine
  commit SHA + merge SHAs/PR links for each landed recipe.

**Wave**: D. **Effort**: 1.5–2 h.

---

## Functional Requirements

- **FR-1.** Phase T adds **zero new firewall-blocking dependency**. Both
  sources (Trending HTML, Search API) route through `_http.py` and are
  already reachable in the enterprise/JFrog path. (Air-gap story: Phase T
  is skippable; `trending-candidates` reads the last snapshot offline.)
- **FR-2.** Phase T **never hard-fails the atlas build**. Scrape 404 /
  layout drift → WARN + keep the prior snapshot. (The daily build's
  correctness does not depend on a fragile third-party page.)
- **FR-3.** Atomic-write discipline: `DELETE (period, snapshot_date)` then
  `INSERT` (§ 10 (g)). Provenance (`source`, `captured_at`) on every row,
  verified against the writer (§ 10 (h)).
- **FR-4.** The classifier never silently drops a repo. Every ingested row
  gets a `tier` or an enumerated `skip_reason`; unconfident rows land
  `tier=2, 'unclassified-needs-human'`.
- **FR-5.** `trending-candidates` + the MCP tool are read-side, offline-
  safe, idempotent. No fetch in the read path.
- **FR-6.** New script registered in all three places; meta-tests stay
  green (`feedback_cfe_new_script_three_places`).
- **FR-7.** Every recipe story runs the CFE 10-step loop via the skill
  (Rule 1), uses v1 `recipe.yaml` + the schema-header, the literal
  `pypi.org/packages/...` source URL, `python_min` defaulting to `"3.10"`
  (omitted from `context:` at the floor), the CFEP-25 dual-version test
  matrix, a `check_dependencies` audit before submission, Pattern-1
  license placement, and an `extra.cfe-*` internal-metadata block stripped
  before push.
- **FR-8.** Each PR body cites the upstream repo + license + the CFE
  version that authored the recipe; each recipe carries `rxm7706` as a
  maintainer (additive).

---

## Technical Approach

### Layering

```
            ┌──────────────────────────── Wave A: ENGINE ──────────────────────────┐
            │  Phase T (fetch)            classifier (local SQL)        operator     │
github.com/trending/python  ─► github_trending_repos ─► v_trending_candidates ─► trending-candidates CLI/MCP
   (HTML, primary)                 (schema v29)        (join: feedstocks +         (--period/--tier/--top/--json)
GitHub Search API                                       pypi_universe +
   (JSON, fallback Q1)                                  pypi_intelligence)
            └───────────────────────────────────────────────────────────────────────┘
                                              │  candidate list (tiered)
            ┌──────────────────── Waves B–C: WORKFLOW (consumes the list) ──────────┐
            │  Tier-1 noarch:python recipes  +  Tier-2 compiled/multi-output/closure │
            │  each via the CFE 10-step loop → staged-recipes PR                     │
            └───────────────────────────────────────────────────────────────────────┘
```

### Phase T placement in the build

Insert `T` after the PyPI-intelligence cluster (O–S), because the
classifier *joins* `pypi_intelligence` — T must run after S. Add to the
`bootstrap_data.py` phase string (admin: full; maintainer: include T since
it's one cheap GET; consumer: skip). T is in the **skippable** set
(like F/K/N) so lean builds and air-gapped runs omit it cleanly.

### Reuse, don't reinvent

- **Fetch + auth + rate-limit**: reuse `phase_n_github_live`'s `_http`
  plumbing + the Phase-K token-bucket (default ≤ 3 req/s). No new HTTP
  client.
- **Already-on-cf**: reuse feedstock enumeration (Phase B/B.5) +
  `lookup_feedstock`. No new feedstock crawl.
- **PyPI facts**: join `pypi_universe` (name/published) + `pypi_intelligence`
  (license / requires_python / shape / downloads / readiness). No new
  PyPI fetch in the classifier.
- **Recipe generation**: `generate_recipe_from_pypi` per story. The
  per-story acceptance criteria spell out the manual post-gen edits
  (dep-name fixes per G10, CFEP-25 triad, LICENSE, `extra.cfe-*`).

### Per-recipe sub-workflow

Standard CFE 10-step autonomous loop. Tier-1 = pure noarch path. Tier-2 =
the compiled/multi-output path (Rust CLI template, multi-output template,
prereq-closure leaves-first), per the skill's Critical Constraints.

### Scrape-fragility mitigation (the main engineering risk)

- The HTML parser is pinned behind a **saved-fixture regression test**
  (A2/A5), so a GitHub layout change is caught by a red test, not silent
  empty snapshots.
- FR-2 guarantees a parse failure degrades to "keep last snapshot + WARN,"
  never a build break.
- Q1's Search-API fallback is the robust corroboration path when the
  scrape thins out.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** `pixi run -e local-recipes build-cf-atlas` (admin profile)
  runs Phase T, populating `github_trending_repos`; schema is v29.
- **AC-2.** `pixi run -e local-recipes trending-candidates --json`
  returns a tiered, ranked candidate list; the MCP tool returns the same.
  Both are offline-safe (work with no network after the snapshot).
- **AC-3.** All engine meta-tests + unit tests green; the
  `no-trendshift-scrape` and parser-fixture guards pass.
- **AC-4.** The 2026-06-20 batch triage artifact exists, and § Worked
  Examples records the verified tiers.
- **AC-5.** `cli-anything-hub` is shipped (PR open or merged) and
  installs in a fresh pixi env: `pixi add cli-anything-hub && cli-anything-hub --help`.
- **AC-6.** Every verified Tier-1 + Tier-2 first-batch candidate is either
  (a) shipped (PR open/merged) or (b) explicitly deferred with a reason in
  `deferred-work.md`. No verified candidate silently dropped.
- **AC-7.** `pip check` passes for every noarch:python recipe (or
  `pip_check: false` carries a documented external-bug reason).
- **AC-8.** The `guides/trending-discovery.md` guide exists; (Q4) the
  cadence is wired or explicitly deferred.
- **AC-9.** D2 retro filed; SKILL.md/reference/CHANGELOG updated; this
  spec marked **Shipped <date>** with engine SHA + per-recipe PR links.

---

## Open Questions

### Q1 (gates A2) — Trending source robustness: scrape, Search API, or both?

`github.com/trending/python` is an unofficial HTML page; its layout can
change without notice, and there is no SLA. The GitHub Search API is
official + authenticated but only *approximates* trending (it ranks by
total stars among recently-created repos, missing fast-rising *old*
repos).

- **Option A (recommended)**: Scrape-primary + Search-API-fallback.
  Scrape is the true trending signal; the Search API covers scrape drift
  and corroborates. Parser pinned behind a fixture test (FR-2 + A5).
- **Option B**: Search-API only. Robust + official, but misses
  fast-rising established repos (the most interesting packaging targets).
- **Option C**: Scrape-only. Truest signal, most fragile; no fallback.

**Default: A.**

### Q2 (gates A3) — How aggressive is the "application, not library" skip?

`home-assistant/core`, `onyx`, `OpenMontage` are clearly apps; but some
trending repos are app+embedded-lib (the lib is packageable, the app is
not). Does the classifier (a) skip the whole repo, or (b) flag it
`tier=2, 'app-with-embedded-lib'` for human judgment?

**Default: (b)** — flag for human judgment rather than auto-skip, so a
packageable inner library isn't lost. (This is a candidate "Tier 3"
once enough batches show the pattern.)

### Q3 (non-blocking) — Should Phase T also ingest non-Python trending?

The workflow is Python-scoped, but Rust/Go CLIs trend too and are
conda-actionable (e.g. the canonical Rust CLI template). v1 stays
Python-only (`/trending/python`); a follow-on could add `/trending/rust`,
`/trending/go`.

**Default: Python-only in v1**; note the extension point in the guide.

### Q4 (gates D1 cadence) — Manual re-run or scheduled?

- **Option A (recommended)**: `/schedule` a monthly cloud routine that
  re-runs Phase T and posts the new `trending-candidates` list for review.
  Discovery-only (NG7).
- **Option B**: Phase-K-style local cron runner (no cloud).
- **Option C**: Manual — operator re-runs `build-cf-atlas` + the CLI when
  they want a batch.

**Default: A**, with C always available.

### Q5 (gates B-CLI-Anything) — CLI-Anything PyPI dist shape

Confirm `cli-anything-hub` is the stable PyPI dist, that its entry-point
console-script name matches the recipe test, and that the optional
per-backend deps (Pillow/bpy/lxml/sox…) are genuinely optional (→
`run_constraints:`) and not hard imports of the hub package.

**Investigation**: `WebFetch https://pypi.org/pypi/cli-anything-hub/json`
+ inspect the sdist `pyproject.toml` `[project.scripts]` /
`[project.optional-dependencies]` during B-CLI-Anything's first 30 min.

---

## Dependencies and Constraints

### External services

- **GitHub Trending HTML** (`github.com/trending/python`) — unofficial, no
  API, scrape. Fragile (mitigated by FR-2 + fixture test).
- **GitHub Search API** — official, authenticated, rate-limited (reuse
  Phase N's token + Phase K's rate discipline).
- **`trendshift.io`** — **no public JSON API** (verified 2026-06-20).
  Human cross-reference only; **never scraped** (NG1).

### cf_atlas internals Phase T joins (must exist; they do at v28)

- Feedstock enumeration (Phase B/B.5) + `lookup_feedstock`.
- `pypi_universe` (name/published; schema v20).
- `pypi_intelligence` (license / requires_python / packaging_shape /
  downloads_30d/90d / conda_forge_readiness; schema v22+, Phases O–S).

### Per-recipe external deps

Determined per-story by `check_dependencies`. High-risk-unmapped suspects
seeded above (audio stack for audiblez; `dspy`/LLM clients for
knowledge-storm; the `triton`/`bitsandbytes`/`xformers` GPU stack for
unsloth; torch/diffusers for LTX-2). Each missing dep → a prereq mini-PR
in the same wave or a documented `run_constraints:` drop.

### conda-forge constraints

- Standard staged-recipes review queue (multi-day per PR); waves serialize
  on *review-queue entry*, not merges.
- linux-64 mandatory; Tier-2 compiled recipes add osx-64/osx-arm64
  (and win-64 where the upstream build supports it — document any skip).
- macOS deployment target ≥ 11.0; 6 h Azure build cap (none expected to
  approach it except possibly the heaviest GPU Tier-2 closures).

### Project conventions (load-bearing)

- Three-places rule for the new CLI (`feedback_cfe_new_script_three_places`).
- `atlas-phase-engineering.md` § 10 (g)/(h)/(i) for the new phase.
- 4-spelling PyPI→conda mapping rule (`feedback_pypi_conda_mapping_unreliable`).
- `extra.cfe-*` internal-metadata block, stripped before push
  (`feedback_extra_is_local_internal_metadata`).
- `python_min` omitted from `context:` at the 3.10 floor
  (`feedback_omit_python_min_at_default_floor`).

---

## Out of Scope (Explicit)

| Category | Reason |
|---|---|
| `trendshift.io` programmatic scraping | No public API; ToS risk; homage only (NG1). |
| Non-Python trending feeds | v1 is Python-scoped (Q3); Rust/Go are a follow-on. |
| Awesome-lists / datasets / skills-collections / docs repos | Not installable artifacts (public-apis, Anthropic-Cybersecurity-Skills, geo-seo-claude, *-for-beginners). |
| GUI desktop apps / mega-dep applications | No library shape / un-packageable closure (home-assistant/core, onyx, OpenMontage, biliTickerBuy). |
| Already-shipped feedstocks | Skip filter removes them (yt-dlp, presidio, …). |
| CUDA-variant recipes (v1) | CPU/generic first; GPU variants are follow-on PRs (NG5). |
| Auto-submission of recipes | Phase T is discovery-only; a human decides what to package (NG7). |
| Upstream PRs to trending repos | Recipes absorb artifacts as published (NG4). |
| Research-snapshot repos with no PyPI release | Classified `skip` (`no-pypi-artifact`); revisit only if upstream tags a release. |

---

## Worked Examples

> Append one block per batch. The timeless "how" lives in
> `guides/trending-discovery.md`; this section is the running ledger.

### Batch 2026-06-20 (first batch — seeds Waves B–C)

- **Params**: `<period>=daily`, `<top_n>=17`, `<tier_scope>=1,2`,
  `<min_stars>=500`. Source: WebFetch of `github.com/trending/python`.
- **First-pass triage (heuristic — to be replaced by B1's verified run)**:

| Repo | Stars (+Δ today) | First-pass tier | Note |
|---|---|---|---|
| HKUDS/CLI-Anything | — | **Tier 1** | `cli-anything-hub`, Apache-2.0, Py≥3.10, Click≥8. **Named first recipe (B-CLI-Anything).** |
| stanford-oval/storm | 28.9k (+196) | Tier 1 | `knowledge-storm`; verify deps (dspy/LLM clients). |
| google-research/timesfm | 24.3k (+432) | Tier 1→? | jax/torch may demote to Tier 2. |
| santinic/audiblez | 7.8k (+139) | Tier 1→? | audio/TTS backend may demote to Tier 2. |
| chopratejas/headroom | 40.6k (+3,786) | Tier 2→? | promote to Tier 1 if clean pure-Python. |
| unslothai/unsloth | 66.9k (+116) | Tier 2 | GPU stack; CPU/generic first. |
| Lightricks/LTX-2 | 7.7k (+170) | Tier 2 | torch/diffusers; CPU first. |
| THUDM/slime | 6.5k (+195) | Tier 2→skip? | verify PyPI presence (may be clone-only). |
| yt-dlp/yt-dlp | 172.0k | **skip** | already on conda-forge. |
| microsoft/presidio | 9.3k (+421) | **skip** | already on conda-forge. |
| public-apis/public-apis | 443.1k | **skip** | awesome-list, not a package. |
| home-assistant/core | 87.9k | **skip** | application + mega-dep tree. |
| onyx-dot-app/onyx | 30.4k | **skip** | platform application. |
| calesthio/OpenMontage | 6.6k (+677) | **skip** | agentic app, not a library. |
| mukul975/Anthropic-Cybersecurity-Skills | 16.9k (+336) | **skip** | skills dataset. |
| Alishahryar1/free-claude-code | 35.8k (+241) | **skip** | wrapper tool. |
| zubair-trabzada/geo-seo-claude | 8.4k (+196) | **skip** | Claude Code skill, not a package. |
| mikumifa/biliTickerBuy | 3.6k (+122) | **skip** | GUI ticket tool. |

- **Status**: pending Wave A (engine) → B1 (verified triage) → recipes.
- **Verified triage**: *(filled in by B1 at execution.)*

---

## References

### Internal

- `docs/specs/microsoft-conda-forge.md` — closest precedent: audit→triage→
  wave packaging of an upstream set; wave/parallelism conventions reused.
- `docs/specs/feedstock-platform-expansion.md` — parameterized timeless-
  workflow + appended-worked-examples pattern reused for the recurring layer.
- `docs/specs/atlas-pypi-intelligence.md`, `atlas-phase-f-wave3-cli-surface.md`,
  `atlas-phase-p-incremental.md` — schema-migration + new-phase + new-CLI
  mechanics; the `v_*` view + read-side-CLI patterns.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`
  — § 10 (a)–(k): atomic writes, DELETE+INSERT, provenance, dry-run,
  rate-limit, step-04 adversarial review (load-bearing for Phase T).
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`,
  `atlas-actionable-intelligence.md` — where Phase T slots in; the
  persona-profile gating.
- `.claude/skills/conda-forge-expert/SKILL.md` — 10-step loop, Critical
  Constraints, Build-Failure Protocol, G-series gotchas.
- Auto-memory: `feedback_cfe_new_script_three_places`,
  `feedback_pypi_conda_mapping_unreliable`,
  `feedback_extra_is_local_internal_metadata`,
  `feedback_omit_python_min_at_default_floor`.

### Upstream

- `github.com/HKUDS/CLI-Anything` + PyPI `cli-anything-hub` — B-CLI-Anything.
- `github.com/stanford-oval/storm` (`knowledge-storm`) — B2.
- `github.com/google-research/timesfm` (`timesfm`) — B3.
- `github.com/santinic/audiblez` (`audiblez`) — B4.
- `github.com/chopratejas/headroom`, `unslothai/unsloth`,
  `Lightricks/LTX-2`, `THUDM/slime` — Wave C seeds.
- `github.com/trending/python` — Phase T primary feed.
- GitHub Search API `/search/repositories` — Phase T fallback (Q1).

### conda-forge

- `conda-forge/staged-recipes` — submission target for every recipe story.
- `conda-forge.org/docs/maintainer/example_recipes/pure-python/` — Tier-1.
- `conda-forge.org/docs/maintainer/example_recipes/{rust,cpp}/` — Tier-2.

---

## Suggested BMAD Invocation

```
@bmad-quick-dev — implement the intent in docs/specs/trendshift-conda-forge.md.

Wave A first (the engine): A1 schema v29 → A2 Phase T ingest → A3 tier
classifier → A4 trending-candidates CLI + MCP tool → A5 tests + the
step-04 adversarial review. Invoke conda-forge-expert for all atlas-touching
work (Rule 1). Resolve Q1 (source robustness; default scrape+Search-fallback)
before A2 lands.

Then Wave B (first batch, Tier-1): B1 runs the engine on the 2026-06-20
snapshot and finalizes the triage; B-CLI-Anything lands cli-anything-hub as
the named first recipe (resolve Q5 in its first 30 min); B2..Bn land the
verified Tier-1 gaps. Run the CFE 10-step loop per recipe.

When Wave B PRs are in review, Wave C (Tier-2 compiled/closure). CPU/generic
first (NG5). Demote unverifiable candidates to skip with a reason.

Wave D: write guides/trending-discovery.md, wire the cadence (Q4; default
monthly /schedule, discovery-only), then run the closeout CFE retro (Rule 2).
Flip this spec's Status to Shipped <date> with the engine SHA + per-recipe
PR links.
```
