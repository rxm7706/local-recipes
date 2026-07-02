---
status: ready
spec_updated: 2026-07-02
---
> **Consolidated 2026-07-02.** This file absorbed `microsoft-conda-forge.md` as
> [Track B](#track-b) — the fixed-source (`github.com/microsoft/*` org) worked instance of
> the same discover→triage→tier→wave-package shape that Track A generalizes to a moving
> target (the GitHub trending feed). The tracks are independent `bmad-quick-dev` entry
> points; run either with the track named in the prompt. Bodies below are the original
> specs verbatim.

<a id="track-a"></a>

# Track A — Trendshift: top GitHub-trending Python repos → conda-forge (the general, recurring engine + workflow)

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

This is exactly the shape the microsoft org audit ([Track B](#track-b) below) solved for
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
- **Precedent specs**: the microsoft org audit ([Track B](#track-b)) (audit→triage→wave
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

- [Track B](#track-b) of this file (the microsoft org audit) — closest precedent: audit→triage→
  wave packaging of an upstream set; wave/parallelism conventions reused.
- `docs/specs/feedstock-platform-expansion.md` — parameterized timeless-
  workflow + appended-worked-examples pattern reused for the recurring layer.
- `docs/specs/cfe-shipped-releases.md` Parts 3 (pypi-intelligence), 8 (Phase F Waves 1–3
  incl. the Wave-3 CLI surface), and 7 (Phase P incremental) — schema-migration + new-phase + new-CLI
  mechanics; the `v_*` view + read-side-CLI patterns.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`
  — § 10 (a)–(k): atomic writes, DELETE+INSERT, provenance, dry-run,
  rate-limit, step-04 adversarial review (load-bearing for Phase T).
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`,
  `atlas-phases-overview.md` Part A — where Phase T slots in; the
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

---

<a id="track-b"></a>

# Track B — Microsoft org audit (fixed-source worked instance, June 2026 snapshot)

> Formerly `microsoft-conda-forge.md`. Original frontmatter: `status: ready; spec_updated: 2026-06-20`

# Tech Spec: Microsoft GitHub Org → conda-forge

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> portfolio packaging effort, ~14 implementation stories spanning 3 waves
> and ~10–14 staged-recipes PRs).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement Track B (the microsoft org audit) of docs/specs/trendshift-conda-forge.md
> ```

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake; 3 open questions (Q1–Q3) noted, none v1-blocking. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Upstream | Multiple `github.com/microsoft/*` repos (per-story); all MIT or Apache-2.0. |
| Target | `conda-forge/staged-recipes` (new feedstocks). Each story = one independently-submittable recipe; PRs land staggered. |
| Distribution | conda-forge (noarch:python for pure-Python; per-platform for Rust CLI + C++ libs). |
| Lifetime | One-shot land + handoff. Feedstocks become autotick-maintained after first PR lands. |

---

## Background and Context

### The problem

Microsoft publishes a large, high-quality OSS portfolio (~200+ active
public repos) including several flagship Python AI/ML projects with
significant user demand. The June 2026 audit (this spec's basis,
documented separately in the parent conversation) cross-checked the top
~120 Microsoft repos by stars against conda-forge feedstocks via
`lookup_feedstock`. The result:

- **Already shipped on conda-forge** (20+ feedstocks): markitdown,
  autogen-agentchat / pyautogen / autogen-core, graphrag,
  presidio-analyzer, pyright, FLAML, LightGBM, DeepSpeed, ONNX Runtime,
  onnxscript, LoRA, LLMLingua, hummingbird-ml, TorchGeo, TypeScript,
  Playwright (+ Python), debugpy, GSL (`ms-gsl`), picologging, the
  Microsoft 365 Agents kiota family (shipped from this repo in
  May 2026), and **`agent-framework-core` v1.8.0** (which arrived
  between the start of the audit and the spec write-up — a positive
  surprise that converts the agent-framework story from
  "2 recipes" to "1 thin umbrella recipe").

- **Material gaps with clear PyPI / Cargo presence and clean MIT/Apache
  license**: ~10–14 candidates across 3 difficulty tiers. This spec
  packages them.

- **Cannot ship** (categorical, not in scope): Windows-only system
  tools (PowerToys, terminal, WSL, winget-cli, …); .NET-heavy
  (`garnet`, `aspire`, `kiota` CLI); research code without library
  shape (TRELLIS, JARVIS, BioGPT, Swin-Transformer, OmniParser,
  table-transformer, …); docs/training repos (every `*-for-beginners`);
  vendor-distributed binaries (vscode, vcpkg, MS-DOS); browser-only
  npm libs (monaco-editor, fluentui, FluidFramework). See § "Out of
  Scope" for the full exclusion list.

### What's been investigated and ruled out

- **Microsoft/typescript-go.** 25.6k★ native Go port of the TS
  compiler — looks like a perfect conda-forge fit (Go, MIT,
  cross-platform). **Repo description says "Staging repo for
  development of native port of TypeScript"**; no 1.0, breaking
  changes expected. Defer until upstream tags a stable release. The
  existing `typescript` feedstock (6.0.2, conda-forge) covers users
  in the interim.

- **Microsoft/VibeVoice.** 49k★ frontier voice AI. Microsoft pulled
  the upstream code in 2025 (per GitHub history); current state is
  research-snapshot, not a maintained library. Out of scope — no
  stable PyPI release to track.

- **Microsoft/BitNet.** 39k★ 1-bit LLM inference. C++ kernels + Python
  wrapper, MIT. **Build is non-trivial** (custom MLIR-like passes,
  hand-tuned per-CPU kernels). Realistic timeline is multi-week, not
  multi-day. Listed in Wave 3 as a stretch target; not commit-required.

- **Microsoft/recommenders.** 28-dep Python lib, MIT, py≥3.6, on PyPI
  as `recommenders` 1.2.1. Dep tree is wide (`cornac`, `transformers`,
  `scikit-learn`, plus optional spark/gpu/nni extras). Feasible but
  the breadth of `[experimental]` / `[gpu]` / `[spark]` extras makes
  the run_constraints block heavy. Listed in Wave 2 as
  effort-pending; not commit-required.

- **Microsoft/semantic-kernel** (Python). 28k★, on PyPI as
  `semantic-kernel` 1.43.0, MIT, py≥3.10. 47 dependencies with **18
  optional extras** (`anthropic`, `aws`, `chroma`, `google`,
  `hugging-face`, `milvus`, `mistralai`, `mongo`, `ollama`, `onnx`,
  `oracledb`, `pandas`, `pinecone`, `postgres`, `qdrant`, `redis`,
  `sql`, `usearch`, `weaviate`). Wide surface but every extra is
  resolvable on conda-forge today. Listed in Wave 2 as a deliberate
  single-recipe submission (extras flatten into `run_constraints:`).

- **Microsoft/PromptWizard.** 3.9k★, MIT. Quick check of PyPI's
  `promptwizard` 1.0.0 returns *a different upstream* (generic "Prompt
  Wizard is a package for evaluating custom prompts") — not
  Microsoft's repo. **Open Q1 below.** Need to confirm whether
  Microsoft's PromptWizard has its own published PyPI artifact before
  promising a recipe.

### What's available to leverage

- **`conda-forge-expert` skill v8.11+** provides
  `generate_recipe_from_pypi`, `validate_recipe`, `optimize_recipe`,
  `check_dependencies`, `scan_for_vulnerabilities`, `trigger_build`,
  `prepare_submission_branch`, `submit_pr`. Each recipe in this spec
  runs the standard 9-step autonomous loop.

- **Rust CLI canonical pattern** (SKILL.md Critical Constraints + the
  v8.7+ Rust template at
  `.claude/skills/conda-forge-expert/templates/rust/cli-recipe.yaml`):
  `cargo auditable install --locked --no-track --bins` +
  `cargo-bundle-licenses` + unix/win install-root split + `script.env`
  for `CARGO_PROFILE_RELEASE_{STRIP, LTO}`. Directly applicable to S1
  (microsoft/edit) without invention.

- **Cocoindex-class precedent** for non-trivial Rust+Python recipes
  (PR #33231 — see SKILL.md G1/G3/G4). Sets the bar for Wave-3
  compiled stories.

- **Microsoft kiota / Agents family** already on conda-forge from this
  repo's May 2026 work (microsoft-kiota-bundle,
  microsoft-agents-m365copilot{,-core}). Sets the precedent that
  Microsoft polyglot-monorepo recipes are reviewable and mergeable
  under existing patterns.

- **Existing canonical templates**:
  `templates/rust/cli-recipe.yaml` (Wave 1 S1),
  `templates/python/noarch-recipe.yaml` (every Wave 1 + Wave 2
  Python story),
  `templates/multi-output/lib-python-recipe.yaml` (Wave 2 promptflow,
  Wave 3 DiskANN).

---

## Goals

- **G1.** Land **microsoft/edit** as a `recipes/microsoft-edit/` Rust
  CLI recipe following the canonical 5-element pattern. Builds clean
  on linux-64, osx-64, osx-arm64, win-64.
- **G2.** Land **microsoft/agent-framework** (the umbrella meta) as a
  thin `noarch: python` recipe whose only run dep is the
  already-shipped `agent-framework-core[all]`. Wave 1 quick win.
- **G3.** Land **microsoft/qlib** (PyPI `pyqlib`) as a `noarch: python`
  recipe. Highest-demand unpackaged Microsoft Python project (44k★).
- **G4.** Land **microsoft/PyRIT** (`pyrit`), **microsoft/promptflow**
  (4 outputs: `promptflow-tracing`, `promptflow-core`,
  `promptflow-devkit`, `promptflow`), **microsoft/semantic-kernel**,
  and **microsoft/torchscale** in Wave 2. All `noarch: python`.
- **G5.** Land **microsoft/SEAL** (C++ homomorphic encryption library
  via CMake) and **microsoft/DiskANN** (C++ ANN library + `diskannpy`
  Python bindings, multi-output) in Wave 3.
- **G6.** Each PR cites the upstream Microsoft repo + license in the
  body; each recipe carries `rxm7706` as a maintainer (additive
  to whoever else co-maintains).
- **G7.** Apply the conda-forge-expert retro rule at end of effort:
  bmad-retrospective updates SKILL.md / CHANGELOG.md with any
  novel gotchas surfaced during the 14 stories.

## Non-Goals

- **NG1.** No CUDA-variant recipes. SEAL and DiskANN ship CPU-only
  recipes first; GPU variants are deferred to follow-on PRs (and to
  whoever picks up the feedstock long-term).
- **NG2.** No `microsoft/BitNet` recipe in this v1 effort. The
  custom-MLIR build is multi-week — separate spec when prioritized.
- **NG3.** No `microsoft/typescript-go` recipe. Upstream not yet 1.0;
  await tagged stable release. Documented in
  `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md`.
- **NG4.** No upstream PRs to Microsoft repos. No README fixes, no
  license corrections, no pyproject loosening. Recipes absorb
  upstream artifacts as published.
- **NG5.** No re-packaging of already-shipped feedstocks. The
  20+ existing Microsoft-origin feedstocks (markitdown, autogen,
  graphrag, …) are out of scope; this spec ships only the gaps.
- **NG6.** No Microsoft semantic-kernel C# / .NET packaging. The
  conda-forge channel does not ship the .NET runtime; this spec
  covers only the Python sibling (`semantic-kernel` PyPI dist).
- **NG7.** No `microsoft-edit` Windows-installer mimicry. The conda
  recipe produces a `edit` (or `msedit` per Q3) shell binary; users
  who want the WinGet experience can keep using WinGet.
- **NG8.** No feedstock-level CI customization beyond what
  staged-recipes provides by default. Standard `.ci_support` matrix
  for every recipe; no `provider:` override.
- **NG9.** No Anaconda-channel mirror. conda-forge only.

---

## Lifecycle Expectations

After each staged-recipes PR merges:

- `regro-cf-autotick-bot` files autotick PRs on each new upstream tag.
  For S2 (agent-framework meta) the autotick is one-line; for
  S6 (DiskANN multi-output) the bot only handles version + sha256, so
  the maintainer (rxm7706) handles structural deps on bump.
- `conda-forge-webservices` runs lint + rerender automatically.
- Each recipe ships with the maintainer set `[rxm7706, <any co-maintainer
  identified during PR review>]`. No commitment to long-term solo
  maintenance — additional maintainers welcome at PR review time.
- The shipped feedstocks become canonical install paths; users on
  conda-managed / air-gapped / JFrog Artifactory environments get the
  packages through their existing channel without falling back to pip.

---

## User Stories

3 waves, 14 stories. Parallelism within a wave is fine. Each wave only
depends on the *previous wave's PRs entering staged-recipes review
queue*, not on them merging — staged-recipes review is multi-day per
PR, and serializing on merges would stretch the effort to months.

| Wave | Stories | Description |
|---|---|---|
| 1 | S1–S4 | Quick wins: 1 Rust CLI + 3 thin Python recipes. Independent leaves. |
| 2 | S5–S11 | Mid-tier Python: PyRIT, promptflow (4 outputs), semantic-kernel, torchscale. |
| 3 | S12–S14 | Native/compiled: SEAL, DiskANN (multi-output), follow-on. |

### Story S1 — Recipe: `microsoft-edit` (Rust CLI)

**Goal**: Land microsoft/edit (Rust terminal text editor, 14.3k★, MIT)
as a per-platform recipe following the v8.7+ canonical Rust CLI
pattern.

**Acceptance criteria**:
- `recipes/microsoft-edit/recipe.yaml` validates clean.
- Source from `github.com/microsoft/edit/archive/refs/tags/v${{ version }}.tar.gz`
  (v2.0.0, released 2026-04-28). Verify sha256.
- Build deps: `${{ compiler('rust') }}`, `${{ compiler('c') }}`,
  `${{ stdlib('c') }}`, `cargo-bundle-licenses`, `cargo-auditable`.
- `script.env`: `CARGO_PROFILE_RELEASE_STRIP: symbols`,
  `CARGO_PROFILE_RELEASE_LTO: fat`.
- `script.content`: unix path uses `--root ${{ PREFIX }}`; win path
  uses `--root %LIBRARY_PREFIX%`. Both invoke
  `cargo auditable install --locked --no-track --bins --path .`.
- `cargo-bundle-licenses --format yaml --output ./THIRDPARTY.yml`
  runs after install.
- `package_contents.strict: true`; primary binary `edit` (or `msedit`
  per Q3) is shipped under `bin/`.
- Tests: `edit --version` returns the recipe version; on Windows,
  `where edit` succeeds.
- License: MIT — already in archive root as `LICENSE`.
- Build matrix: linux-64, linux-aarch64, osx-64, osx-arm64, win-64.
- Builds clean locally via `pixi run -e local-recipes recipe-build
  recipes/microsoft-edit` on at least one host platform.
- `submit_pr(recipe_name="microsoft-edit")` returns a `pr_url`.

**Wave**: 1.

**Estimated effort**: 1–2 h. Direct application of the canonical Rust
CLI template; primary risk is the binary-name decision (see Q3).

### Story S2 — Recipe: `agent-framework` (umbrella meta)

**Goal**: Land microsoft/agent-framework (11.2k★, MIT, py≥3.10) as a
thin `noarch: python` umbrella whose only dep is the already-shipped
`agent-framework-core[all]==<version>`. Sister to the conda-forge
`agent-framework-core` v1.8.0 feedstock that arrived during this
effort's scoping window.

**Acceptance criteria**:
- `recipes/agent-framework/recipe.yaml` validates clean.
- Source from PyPI sdist
  `agent_framework-${{ version }}.tar.gz`. Version starts at 1.8.1
  (current latest).
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Host: `python ${{ python_min }}.*`, `pip`, `flit-core <4,>=3.11`
  (match upstream backend).
- Run: `python >=${{ python_min }}`, `agent-framework-core ==${{ version }}`
  (exact pin — upstream uses `==1.8.1`, this is the version-pinned
  umbrella pattern documented at upstream).
- Tests: `python -c "import agent_framework"` + `pip check`.
- License: MIT.
- `submit_pr(recipe_name="agent-framework")` returns a `pr_url`.

**Wave**: 1.

**Estimated effort**: 30 min.

### Story S3 — Recipe: `pyqlib` (Microsoft qlib)

**Goal**: Land microsoft/qlib (44k★, MIT, on PyPI as `pyqlib` 0.9.7)
as a `noarch: python` recipe. Highest-demand unpackaged Microsoft
Python project.

**Acceptance criteria**:
- `recipes/pyqlib/recipe.yaml` validates clean.
- Source from PyPI (`pyqlib-${{ version }}.tar.gz`).
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Run-deps audited via `check_dependencies` and the PyPI→conda
  mapping rules from SKILL.md G10 (verify 4 spelling forms before
  declaring a dep missing). Expected deps already on conda-forge:
  `pyyaml`, `numpy`, `pandas`, `mlflow`, `lightgbm`, `scikit-learn`,
  `loguru`, `tqdm`, `requests`, `joblib`, `cvxpy`, `redis-py`,
  `python-socks`, `tornado`, `dill`, `gym`, `plotly` (~40 total).
- If `cvxpy` or any other dep surfaces unmapped, flag inline; do
  NOT silently skip.
- `python_min: "3.10"` (conda-forge floor; upstream allows 3.8 but
  conda-forge dropped 3.9 in Aug 2025).
- Tests: `import qlib`, `pip check`. Optional: `qlib --help` if a
  CLI is exposed (check `[project.scripts]` in the sdist's
  pyproject.toml).
- License: MIT — `LICENSE` at root.
- Feedstock-name asymmetry: recipe = `pyqlib`, top-level import =
  `qlib`. Document in recipe header comment.
- `submit_pr(recipe_name="pyqlib")` returns a `pr_url`.

**Wave**: 1.

**Estimated effort**: 1.5–2 h (most of it is the dep audit + any
remediation for unmapped transitives).

### Story S4 — Recipe: `pyrit` (Microsoft PyRIT)

**Goal**: Land microsoft/PyRIT (4k★, MIT, py 3.10–3.14, on PyPI as
`pyrit` 0.14.0) as a `noarch: python` recipe.

**Acceptance criteria**:
- `recipes/pyrit/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Run-deps (72 in upstream `requires_dist`): `aiofiles`, `alembic`,
  `appdirs`, `art`, `av`, `azure-core`, `azure-identity`,
  `azure-ai-contentsafety`, `azure-storage-blob`, `base2048`,
  `colorama`, `confusables`, `confusable-homoglyphs`, `ecoji`,
  `datasets`, `fastapi`, `httpx`, `jinja2`, `numpy`, `openai`,
  `openpyxl`, `pillow`, `pydantic`, `PyJWT`, `pyodbc`, `pypdf`,
  `python-docx`, `python-dotenv`, `reportlab`, `segno`, `scipy`,
  `SQLAlchemy`, `starlette`, `termcolor`, `tenacity`, `tinytag`,
  `tqdm`, `transformers`, `treelib`, `uvicorn`, `websockets`,
  `build`, `pytorch`. Plus `run_constraints:` for the extras
  (`huggingface`, `gcg`, `playwright`, `fairness-bias`, `opencv`,
  `speech`).
- Audit each dep via `check_dependencies` (G10 4-spelling rule).
  `base2048`, `confusables`, `ecoji`, `segno`, `art`, `tinytag`,
  `treelib`, `confusable-homoglyphs`, `pyodbc` are the
  highest-risk unmapped candidates.
- For each missing dep, decide: package it as a S4-prereq mini-PR,
  or drop it from `run:` and document the gap. Default: package
  it (avoids shipping a recipe that fails `pip check`).
- `python_min: "3.10"`. Upstream upper bound `<3.15` is OK to
  declare in `run:` per SKILL.md "upstream-explicit upper bound" rule.
- Tests: `import pyrit`, `pip check`.
- License: MIT.
- `submit_pr(recipe_name="pyrit")` returns a `pr_url`.

**Wave**: 2.

**Blocked by**: Wave 1 PRs (S1–S3) entering staged-recipes review
queue (review-queue throughput, not technical dependency).

**Estimated effort**: 2–4 h, depending on how many of the unmapped
transitives need their own S4-prereq mini-PRs. Worst-case adds 5
trivial pure-Python recipes.

### Story S5 — Recipe: `promptflow-tracing` (leaf)

**Goal**: Land `promptflow-tracing` (Microsoft promptflow's tracing
subpackage) as a `noarch: python` recipe. Required by
`promptflow-core` (S6).

**Acceptance criteria**:
- `recipes/promptflow-tracing/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Run-deps per upstream `requires_dist` (audit).
- `python_min: "3.10"` (upstream `>=3.9, <4.0` → bump to 3.10 floor).
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Estimated effort**: 45 min.

### Story S6 — Recipe: `promptflow-core`

**Goal**: Land `promptflow-core` (depends on `promptflow-tracing`).

**Acceptance criteria**:
- `recipes/promptflow-core/recipe.yaml` validates clean.
- `noarch: python`.
- Run-deps include `promptflow-tracing` (in staged-recipes review
  via S5).
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Blocked by**: S5 PR entering review queue.

**Estimated effort**: 45 min.

### Story S7 — Recipe: `promptflow-devkit`

**Goal**: Land `promptflow-devkit` (depends on `promptflow-core` +
`promptflow-tracing`).

**Acceptance criteria**:
- `noarch: python`.
- Run-deps include `promptflow-core`, `promptflow-tracing`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Blocked by**: S5 + S6 PRs entering review queue.

**Estimated effort**: 1 h.

### Story S8 — Recipe: `promptflow` (umbrella meta)

**Goal**: Land `promptflow` (11.1k★, MIT, py>=3.9,<4.0, on PyPI
`promptflow` 1.18.5) — thin meta over
`promptflow-{tracing,core,devkit}`.

**Acceptance criteria**:
- `noarch: python`.
- Run-deps: `promptflow-tracing`, `promptflow-core`, `promptflow-devkit`
  (all exact pins to S5/S6/S7's versions).
- `python_min: "3.10"`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Blocked by**: S5 + S6 + S7 PRs entering review queue.

**Estimated effort**: 30 min.

### Story S9 — Recipe: `semantic-kernel` (Python)

**Goal**: Land microsoft/semantic-kernel Python SDK (28k★, MIT, py≥3.10,
on PyPI as `semantic-kernel` 1.43.0) as a `noarch: python` recipe.

**Acceptance criteria**:
- `recipes/semantic-kernel/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Run-deps (core, 22 packages): `aiohttp`, `cloudevents`, `pydantic`,
  `pydantic-settings`, `defusedxml`, `azure-identity`, `numpy`,
  `openai`, `openapi_core`, `websockets`, `aiortc`,
  `opentelemetry-api`, `opentelemetry-sdk`, `prance`, `pybars4`,
  `jinja2`, `nest-asyncio`, `scipy`, `typing-extensions`, `mcp`,
  `azure-ai-projects`, `azure-ai-agents`.
- `run_constraints:` for the 18 extras: `anthropic`,
  `autogen-agentchat`, `boto3`, `azure-ai-inference`,
  `azure-core-tracing-opentelemetry`, `azure-search-documents`,
  `azure-cosmos`, `chromadb`, `microsoft-agents-copilotstudio-client`,
  `faiss-cpu`, `google-cloud-aiplatform`, `google-genai`,
  `transformers`, `sentence-transformers`, `pytorch` (for HF),
  `pymilvus`, `mistralai`, `pymongo`, `motor`, `ipykernel`,
  `ollama`, `onnxruntime`, `oracledb`, `pandas`, `pinecone`,
  `psycopg`, `qdrant-client`, `redis`, `redisvl`, `pyodbc`,
  `usearch`, `pyarrow`, `weaviate-client`.
- `microsoft-agents-copilotstudio-client` is not yet on conda-forge
  — drop from `run_constraints:` with a TODO, or package as a
  S9-prereq mini-PR if the user wants it. Default: drop with TODO.
- `python_min: "3.10"`.
- Tests: `import semantic_kernel`, `pip check`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Estimated effort**: 2–3 h (the extras audit is the meat of it).

### Story S10 — Recipe: `torchscale`

**Goal**: Land microsoft/torchscale (3.1k★, MIT) — foundation
architecture for (M)LLMs — as a `noarch: python` recipe. On PyPI.

**Acceptance criteria**:
- `recipes/torchscale/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Run-deps: `pytorch`, plus any others surfaced by audit (expected
  small dep tree — research-flavored library).
- `python_min: "3.10"`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Estimated effort**: 1 h.

### Story S11 — Recipe: `promptwizard` (Microsoft PromptWizard) — gated on Q1

**Goal**: Land microsoft/PromptWizard (3.9k★, MIT) if Q1 confirms it
has a Microsoft-published PyPI artifact. The bare PyPI `promptwizard`
1.0.0 belongs to a different upstream — packaging it would mis-attribute.

**Acceptance criteria** (conditional on Q1 = "yes, distinct
Microsoft package"):
- Recipe sourced from the correct PyPI distribution (name TBD per Q1).
- `noarch: python`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2 (or deferred to follow-on spec if Q1 resolves
negative — e.g., Microsoft ships PromptWizard only as `git clone +
pip install -e .`).

**Estimated effort**: 1 h (if PyPI artifact exists) / N/A (if not).

### Story S12 — Recipe: `microsoft-seal` (C++ HE library)

**Goal**: Land microsoft/SEAL (4k★, MIT, C++, CMake) as a C++ library
recipe. Cross-platform via CMake; no Python bindings upstream (the
ecosystem `python-seal` is third-party and out of scope here).

**Acceptance criteria**:
- `recipes/microsoft-seal/recipe.yaml` validates clean.
- Source from `github.com/microsoft/SEAL/archive/refs/tags/v${{ version }}.tar.gz`.
  Current latest is v4.1.x.
- Build via CMake: `cmake -GNinja %CMAKE_ARGS% -DSEAL_BUILD_DEPS=OFF
  -DSEAL_USE_INTRIN=ON -DSEAL_BUILD_EXAMPLES=OFF -DSEAL_BUILD_TESTS=OFF`.
- Bundled deps OFF — install `zlib`, `zstd`, `gsl` (microsoft/GSL,
  already on conda-forge as `ms-gsl`), `hexl` from conda-forge.
- Build deps: `${{ compiler('cxx') }}`, `${{ stdlib('c') }}`,
  `cmake`, `ninja`, `pkg-config`.
- Host deps: `ms-gsl`, `zlib`, `zstd`. (HEXL is optional.)
- Run deps: usual library run-exports.
- `package_contents` lists the installed `include/SEAL-*/seal/seal.h`
  + `lib/cmake/SEAL-*/SEALConfig.cmake` + the shared/static library.
- Build matrix: linux-64, linux-aarch64, osx-64, osx-arm64, win-64.
- Builds clean locally on at least one platform.
- `submit_pr` succeeds.

**Wave**: 3.

**Estimated effort**: 4–8 h (first C++/CMake recipe in this spec;
risk centers on CMake config-package layout, dep-toggle flags,
Windows MSVC compatibility).

### Story S13 — Recipe: `diskannpy` + `libdiskann` (multi-output)

**Goal**: Land microsoft/DiskANN (1.8k★, MIT) as a 2-output recipe:
the C++ shared library (`libdiskann`) + the Python bindings
(`diskannpy`).

**Acceptance criteria**:
- `recipes/diskann/recipe.yaml` validates clean.
- Source from GitHub tag.
- Output 1 — `libdiskann`: C++ shared library via CMake. Build deps
  `${{ compiler('cxx') }}`, `${{ stdlib('c') }}`, `cmake`, `ninja`,
  Intel MKL or OpenBLAS, Boost. Per-platform.
- Output 2 — `diskannpy`: Python bindings via pybind11.
  `${{ pin_subpackage('libdiskann', exact=True) }}` in run-deps.
  Per-platform.
- Build matrix: linux-64, osx-64, osx-arm64 (skip win-64 in v1 if
  upstream's Windows story has known gaps; document the skip with
  a TODO).
- Tests: `import diskannpy`, smoke test (build a small index).
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 3.

**Estimated effort**: 6–12 h (multi-output + native compile +
pybind11; nontrivial but precedented by faiss / hnswlib feedstocks).

### Story S14 — Closeout retro

**Goal**: Run `bmad-retrospective` once Wave 1 + Wave 2 PRs have all
either merged or entered review-on-hold state. Per the SKILL.md
always-on Rule 2.

**Acceptance criteria**:
- Retro file written at
  `_bmad-output/projects/local-recipes/implementation-artifacts/retro-microsoft-conda-forge-<date>.md`.
- Identifies corrections / refinements / additions surfaced across
  S1–S13. Particular attention to:
  - Whether any of the four Rust CLI canonical-pattern elements
    needed tweaking for microsoft/edit.
  - Whether the agent-framework meta pattern is reusable for
    similar Microsoft umbrella-packages.
  - Whether qlib's dep audit surfaced new PyPI→conda mapping gaps
    that should land in `feedback_pypi_conda_mapping_unreliable.md`.
  - Whether the semantic-kernel extras audit produced a reusable
    pattern (e.g., "drop unmapped extras with TODO + open
    follow-on") worth codifying.
  - Any new gotchas to add to SKILL.md G16+ (Microsoft-specific or
    general).
- `CHANGELOG.md` PATCH bump (or MINOR if a new gotcha-section was
  added).
- Spec marked **Shipped** at top with merge SHAs for each landed PR.

**Wave**: 3 (closeout).

**Estimated effort**: 1.5–2 h.

---

## Functional Requirements

### FR-1. Each recipe carries `rxm7706` as a maintainer

Additive — preserve any existing maintainers if the recipe is being
refreshed; for new recipes, sole maintainer is `rxm7706` unless the
PR review surfaces a community co-maintainer.

### FR-2. Each recipe uses v1 `recipe.yaml` format

`schema_version: 1` + the schema-header comment per SKILL.md Critical
Constraints. v0 `meta.yaml` is only acceptable when migrating an
existing v0 feedstock — irrelevant here since all stories are new
recipes.

### FR-3. PyPI source URL uses the literal `pypi.org/packages/...` pattern

Per SKILL.md "PyPI `source.url` Must Use..." critical constraint.
Path segments literal; only `${{ version }}` interpolates.

### FR-4. `python_min` defaults to `"3.10"` (conda-forge floor)

Override only when upstream's `python_requires` declares a strictly
higher floor (e.g., pyrit's `>=3.10,<3.15` is fine at 3.10; if it
were `>=3.11`, the recipe declares `python_min: "3.11"` in
context).

### FR-5. CFEP-25 dual-version test matrix for every noarch:python recipe

`tests[].python.python_version: [${{ python_min }}.*, "*"]`. Avoids
the TEST-002 optimizer warning. The generator emits this by default
as of v8.8.0.

### FR-6. Run-dep audit via `check_dependencies` before submission

Every recipe runs `check_dependencies` against conda-forge before
`submit_pr`. Any "missing" hit triggers the 4-spelling
verification per SKILL.md G10. Truly-missing deps either get a
prerequisite mini-recipe in the same wave or get dropped from `run:`
with a documented TODO (preferred default: package the prerequisite,
unless the dep is genuinely peripheral).

### FR-7. License compliance per SKILL.md "Canonical License-File Placement"

Pattern 1 (`license_file: LICENSE` from extracted source) when
upstream's archive ships LICENSE — true for every story here.
No secondary-source LICENSE fetches expected (none of the stories
match G4 — sdist-missing-license — based on the audit).

### FR-8. PR body cites upstream Microsoft repo + license + the conda-forge-expert version that authored the recipe

Standard PR body template — already encoded in the skill's `submit_pr`
behavior; included in this FR for explicitness.

---

## Technical Approach

### Recipe slug convention

| Story | Recipe slug | PyPI/crate name | Conda package name | Top-level import (Python) |
|---|---|---|---|---|
| S1 | `microsoft-edit` | `edit` (crate) | `microsoft-edit` (or `msedit` per Q3) | n/a (CLI) |
| S2 | `agent-framework` | `agent-framework` | `agent-framework` | `agent_framework` |
| S3 | `pyqlib` | `pyqlib` | `pyqlib` | `qlib` |
| S4 | `pyrit` | `pyrit` | `pyrit` | `pyrit` |
| S5 | `promptflow-tracing` | `promptflow-tracing` | `promptflow-tracing` | `promptflow.tracing` |
| S6 | `promptflow-core` | `promptflow-core` | `promptflow-core` | `promptflow.core` |
| S7 | `promptflow-devkit` | `promptflow-devkit` | `promptflow-devkit` | `promptflow.devkit` (verify) |
| S8 | `promptflow` | `promptflow` | `promptflow` | `promptflow` |
| S9 | `semantic-kernel` | `semantic-kernel` | `semantic-kernel` | `semantic_kernel` |
| S10 | `torchscale` | `torchscale` | `torchscale` | `torchscale` |
| S11 | `promptwizard` | TBD per Q1 | TBD | TBD |
| S12 | `microsoft-seal` | n/a (CMake) | `microsoft-seal` | n/a (C++ lib) |
| S13 | `diskann` | n/a (CMake + pybind11) | `libdiskann` + `diskannpy` | `diskannpy` |

The `microsoft-edit` and `microsoft-seal` slugs disambiguate from
generic names already taken or likely to collide elsewhere on
conda-forge. The `pyqlib` slug matches PyPI canonical (recipe author
does NOT silently rename to `qlib` — that would diverge from upstream
and break autotick).

### Wave 1 execution order (parallel-safe)

S1, S2, S3, S4 have **no internal dependencies**. Submit in parallel.
S2's run-dep on `agent-framework-core` is already satisfied (existing
feedstock at 1.8.0; upstream is 1.8.1 so an autotick lands in days —
or S2 can include a same-PR bump request via a feedstock PR).

### Wave 2 dependency graph

```
S5 (promptflow-tracing) ──┐
                          ├──> S6 (promptflow-core) ─┐
                          │                          ├──> S8 (promptflow umbrella)
                          └─────────────────────────┐│
                                                    ├─> S7 (promptflow-devkit) ────┘
                                                    │
S9 (semantic-kernel)   — independent of S5–S8
S10 (torchscale)       — independent of S5–S9
S11 (promptwizard)     — gated on Q1, independent of S5–S10
```

Wave 2 cannot merge S6 / S7 / S8 until S5 lands on conda-forge
(autotick won't help; `check_dependencies` requires it). But
*submission* of S6 / S7 / S8 to staged-recipes can proceed as soon as
S5 is in review (the staged-recipes review queue is multi-day per PR
anyway).

### Wave 3 sequencing

S12 (SEAL) before S13 (DiskANN) — DiskANN may benefit from
SEAL-precedent for CMake-style C++ recipes in this repo's history.
S14 retro waits on all of Wave 1 + Wave 2 + S12 + S13 reaching a
terminal state (merged / on-hold / explicitly deferred).

### Sub-workflow for each Python story

Standard 9-step autonomous loop from `conda-forge-expert` SKILL.md.
No deviations. The skill's `generate_recipe_from_pypi` does the
heavy lifting for steps 1–3; the per-story acceptance criteria above
spell out the manual edits expected after generation (mostly:
dep-name fixes per G10, CFEP-25 test triad if generator missed it,
LICENSE handling).

### Sub-workflow for each Rust / C++ story

S1 follows the canonical Rust CLI template directly. S12 + S13
require manual hand-authoring — the existing skill template
`templates/rust/library-recipe.yaml` doesn't cover CMake C++
projects. S14 retro should consider adding a `templates/cpp/cmake-library-recipe.yaml`
based on whatever pattern S12 settles on (handoff for future
similar packaging efforts).

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** 10–14 staged-recipes PRs are open or merged
  (depending on Q1 outcome for S11 and whether S13's Windows skip
  becomes a 2-PR split): one per story S1–S13. Each addresses every
  bot-lint, conda-smithy-lint, and reviewer comment.
- **AC-2.** All Python recipes build green on at least `linux-64`
  in conda-forge CI. S1 (microsoft-edit) builds green on linux-64,
  osx-64, osx-arm64, win-64. S12 (SEAL) and S13 (DiskANN) build green
  on the platforms in their respective matrices (S13 may legitimately
  skip win-64 in v1).
- **AC-3.** `pip check` passes for every noarch:python recipe's test
  stage.
- **AC-4.** Each shipped recipe is installable in a fresh pixi env:
    - `pixi add microsoft-edit && edit --version` succeeds.
    - `pixi add agent-framework && pixi run python -c "import agent_framework"` succeeds.
    - `pixi add pyqlib && pixi run python -c "import qlib"` succeeds.
    - `pixi add pyrit && pixi run python -c "import pyrit"` succeeds.
    - …same for every other shipped recipe and its primary import.
- **AC-5.** S11 has either (a) shipped (Q1 resolves to "yes, packageable"
  and the PR lands), or (b) been explicitly deferred with rationale
  filed in `deferred-work.md`.
- **AC-6.** S14 retro is filed at
  `_bmad-output/projects/local-recipes/implementation-artifacts/retro-microsoft-conda-forge-<date>.md`.
  Any novel gotchas land in SKILL.md / reference/ / guides/ + a
  CHANGELOG entry.
- **AC-7.** Spec status at top updated to **Shipped <date>** with
  merge SHAs / PR links for each landed recipe.

---

## Open Questions

### Q1 (gates S11) — Does Microsoft PromptWizard ship a PyPI artifact?

The bare PyPI `promptwizard` 1.0.0 belongs to a different upstream
(summary: "Prompt Wizard is a package for evaluating custom prompts
using various evaluation methods"). Microsoft's PromptWizard
(`github.com/microsoft/PromptWizard`, 3.9k★) needs investigation:

- Does Microsoft publish under a different PyPI name? (e.g.,
  `ms-promptwizard`, `microsoft-promptwizard`, `pyromptwizard`.)
- Is it intended as `git clone + pip install -e .` only? (Common
  for research-attached repos.)
- Does upstream maintain a wheel anywhere?

**Default if Q1 resolves negative**: defer S11 to a follow-on spec
(filed in `deferred-work.md`). Do not silently mis-package the bare
PyPI `promptwizard`.

**Investigation**: in S5's first 30 min, run
`WebFetch https://pypi.org/simple/?q=promptwizard` and
`gh search code 'pyproject.toml name "promptwizard"' repo:microsoft/PromptWizard`
to confirm.

### Q2 (gates S13) — Does microsoft/DiskANN have a clean Windows build path?

Upstream's README claims Windows support, but the build invokes Intel
MKL paths that may need recipe-side massaging on conda-forge's MSVC
toolchain. Three options:

- **A**: Skip win-64 in v1; document; add as a follow-on PR when MKL
  CMake config is confirmed.
- **B**: Block S13 on win-64 working — risks the entire DiskANN
  packaging effort on a Windows-only obstacle.
- **C**: Drop MKL dependency; fall back to OpenBLAS on every
  platform — uniform but may underperform vs. upstream.

**Default**: **A**. Document the win-64 skip in the recipe's
top-of-file comment + the PR body. Follow-on Windows PR is a
separate effort.

### Q3 (gates S1) — `microsoft-edit` binary name + recipe slug

Upstream's WinGet manifest installs the binary as `msedit`. Linux/macOS
Homebrew install it as `edit`. The conda recipe must pick one:

- **Option A**: Recipe slug `microsoft-edit`; binary `edit`. Matches
  the linux/macOS convention. Risks shadowing whatever other `edit`
  is in the user's PATH (typically system POSIX `ed`/`ex`/`vi` —
  not actually conflicting).
- **Option B**: Recipe slug `microsoft-edit`; binary `msedit`.
  Matches the Windows convention. Avoids any PATH conflict risk.
- **Option C**: Ship both — `bin/edit` + `bin/msedit` (symlink one
  to the other). Most user-friendly; minor recipe complexity.

**Default**: **C**. The Cargo build emits one binary; the recipe
post-install drops a `msedit` → `edit` symlink (or vice versa on
Windows where symlinks need privilege; alt: ship `msedit.cmd` that
calls `edit.exe`). Document the rationale in the recipe header
comment.

---

## Dependencies and Constraints

### External dependencies that must already exist on conda-forge

Verified via spot-check during the June 2026 audit; subject to
re-verification per-story:

Common across stories: `numpy`, `pandas`, `pydantic`, `pydantic-settings`,
`pytorch`, `transformers`, `tiktoken`, `openai`, `azure-core`,
`azure-identity`, `aiohttp`, `httpx`, `fastapi`, `starlette`,
`uvicorn`, `websockets`, `tenacity`, `jinja2`, `pyyaml`,
`python-dotenv`, `typing-extensions`, `opentelemetry-api`,
`opentelemetry-sdk`, `cmake`, `ninja`, `pkg-config`, `ms-gsl`,
`zlib`, `zstd`, `boost`, `mkl` (optional), `openblas`.

Specific to stories: `agent-framework-core` (S2, exact-version
pin); `mlflow`, `lightgbm` (S3); `azure-ai-projects`,
`azure-ai-agents`, `mcp`, `aiortc`, `pybars4`, `prance` (S9);
`Microsoft.GSL` (= `ms-gsl`, S12); `pybind11` (S13).

### External dependencies likely NOT on conda-forge — handled per-story

| Likely missing | Story | Resolution |
|---|---|---|
| `base2048`, `ecoji`, `segno`, `art`, `tinytag`, `treelib`, `confusable-homoglyphs` | S4 (pyrit deps) | Audit during S4; package as S4-prereq mini-PRs if needed |
| `microsoft-agents-copilotstudio-client` | S9 (semantic-kernel extra) | Drop from `run_constraints:` with TODO; document |
| Any DiskANN-specific BLAS shim | S13 | Investigate during S12 → S13 transition; may need a recipe-side patch |

### Upstream constraints

- All listed upstreams are MIT or Apache-2.0 (verified June 2026).
- All Python recipes target `python_min: "3.10"` (conda-forge floor;
  upstream py_min may be lower but conda-forge dropped 3.9 in Aug
  2025).
- microsoft/edit ships GitHub release binaries; conda recipe
  source-builds from the tag tarball (standard for Rust CLIs).
- microsoft/SEAL v4.1.x is the chosen baseline. CMake 3.22+.
- microsoft/DiskANN's current main is the baseline; tag a recent
  release at story start.

### conda-forge constraints

- Standard staged-recipes review queue (multi-day per PR).
- linux-64 is mandatory; per-platform recipes (S1, S12, S13) also
  build osx-64, osx-arm64, and (per Q2) win-64.
- macOS deployment target ≥ 11.0 (conda-forge floor, Feb 2026 policy).
- Build time limit 6 h on Azure Pipelines (none of these stories
  approach it).

---

## Out of Scope (Explicit)

The following are deliberately excluded from this spec, with reason:

| Repo | Reason |
|---|---|
| microsoft/vscode | Vendor-distributed (own installer + auto-updater); not appropriate for conda-forge. |
| microsoft/TypeScript | Already on conda-forge (`typescript` 6.0.2). |
| microsoft/playwright + playwright-python | Already on conda-forge. |
| microsoft/onnxruntime | Already on conda-forge. |
| microsoft/LightGBM | Already on conda-forge. |
| microsoft/DeepSpeed | Already on conda-forge. |
| microsoft/autogen (all variants) | Already on conda-forge (`autogen-agentchat`, `autogen-core`, `pyautogen`). |
| microsoft/markitdown | Already on conda-forge. |
| microsoft/graphrag | Already on conda-forge. |
| microsoft/presidio | Already on conda-forge. |
| microsoft/pyright | Already on conda-forge. |
| microsoft/FLAML | Already on conda-forge. |
| microsoft/torchgeo | Already on conda-forge (community-maintained). |
| microsoft/agent-framework-core | Already on conda-forge (1.8.0) — only the umbrella `agent-framework` needs adding (= S2). |
| microsoft/Agents (M365), microsoft/kiota* | Already on conda-forge from this repo's May 2026 work. |
| microsoft/typescript-go | Upstream not yet 1.0; defer. |
| microsoft/BitNet | Multi-week C++ build; separate spec when prioritized. |
| microsoft/recommenders | Wide extras tree; evaluate post Wave-2 closure (Wave-3 candidate). |
| microsoft/VibeVoice | Upstream withdrew code in 2025; no stable artifact to track. |
| microsoft/PowerToys + every Windows-only repo (terminal, calculator, WSL, winget-cli, react-native-windows, microsoft-ui-xaml, WindowsAppSDK, wil, sudo, coreutils, hcsshim, …) | Native Win32; no Linux/macOS build path. |
| microsoft/garnet, aspire, kiota (CLI), perfview, fluentui-blazor, every .NET-centric repo | conda-forge doesn't ship the .NET runtime. |
| microsoft/JARVIS, Swin-Transformer, Bringing-Old-Photos-Back-to-Life, BioGPT, MMdnn, OmniParser, CodeBERT, fara, Webwright, SkillOpt, LMOps, table-transformer, TRELLIS, promptbase, muzic, unilm | Research code without library shape; users `git clone` rather than `pip install`. |
| Every `*-for-beginners`, mcp-for-beginners, RustTraining, ai-edu, AcademicContent, Mastering-GitHub-Copilot-for-Paired-Programming, workshop-library, AI-System | Docs/training; no installable artifact. |
| microsoft/monaco-editor, fluentui, fast, FluidFramework, SandDance, reactxp | Browser-only npm libs; npm is the right channel. |
| microsoft/cascadia-code, fluentui-emoji | Fonts/assets; separate distribution channels apply; some licensing complications. |
| microsoft/azurelinux | Linux distribution, not a package. |
| microsoft/AirSim, DirectX-Graphics-Samples, DirectXShaderCompiler | Game-engine / graphics-stack specific; channel-fit mismatch. |
| microsoft/SPTAG | Alternative to DiskANN; cover one ANN library this round (DiskANN). SPTAG is a future-spec candidate if user demand surfaces. |
| microsoft/retina | Kubernetes eBPF; operator-channel territory, not conda-forge. |
| microsoft/pg_durable | Postgres extension; different channel ecosystem. |
| microsoft/ethr | Single-binary Go CLI — viable conda-forge candidate but `iperf3` already covers the use case; defer unless user demand surfaces. |
| Archived repos (CNTK, nni, TaskWeaver, com-rs, napajs, cpprestsdk, bond, BosqueLanguage, ELL, …) | Upstream signals do-not-package. |

---

## References

### Internal

- `.claude/skills/conda-forge-expert/SKILL.md` — Operating Principles,
  Critical Constraints, 10-step autonomous loop, Build Failure
  Protocol, G1–G15 gotchas, Rust CLI standards, Python Version Policy.
- `.claude/skills/conda-forge-expert/templates/rust/cli-recipe.yaml`
  — S1 template.
- `.claude/skills/conda-forge-expert/templates/python/noarch-recipe.yaml`
  — S2–S11 base template.
- `.claude/skills/conda-forge-expert/templates/multi-output/lib-python-recipe.yaml`
  — S8 (promptflow umbrella shape), S13 (DiskANN multi-output shape).
- `docs/specs/db-gpt-conda-forge.md` — closest-precedent packaging
  effort spec; multi-recipe wave pattern adopted here.
- `_bmad-output/projects/local-recipes/implementation-artifacts/retro-npm-and-microsoft-bundles-2026-05-17.md`
  — prior retro from the Microsoft Agents bundle; informs S2 patterns.
- `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/feedback_pypi_conda_mapping_unreliable.md`
  — live cross-skill reference for G10 dep-name verification, gates
  S3/S4/S9 audits.

### Upstream

- `github.com/microsoft/edit` v2.0.0 — S1.
- `github.com/microsoft/agent-framework` + PyPI `agent-framework`
  1.8.1 — S2.
- `github.com/microsoft/qlib` + PyPI `pyqlib` 0.9.7 — S3.
- `github.com/microsoft/PyRIT` + PyPI `pyrit` 0.14.0 — S4.
- `github.com/microsoft/promptflow` + PyPI `promptflow` 1.18.5 +
  `promptflow-{tracing,core,devkit}` — S5–S8.
- `github.com/microsoft/semantic-kernel` + PyPI `semantic-kernel`
  1.43.0 — S9.
- `github.com/microsoft/torchscale` — S10.
- `github.com/microsoft/PromptWizard` — S11 (gated on Q1).
- `github.com/microsoft/SEAL` v4.1.x — S12.
- `github.com/microsoft/DiskANN` — S13.

### conda-forge

- `conda-forge.org/docs/maintainer/example_recipes/rust/` — canonical
  Rust CLI pattern (S1).
- `conda-forge.org/docs/maintainer/example_recipes/pure-python/` —
  canonical noarch:python pattern (S2–S11).
- `conda-forge.org/docs/maintainer/example_recipes/cpp/` (or the
  general CMake guidance) — S12 / S13.
- `conda-forge/staged-recipes` — submission target for every story.

---

## Suggested BMAD Invocation

```
@bmad-quick-dev — implement Track B (the microsoft org audit) of docs/specs/trendshift-conda-forge.md.

Wave 1 first (S1–S4 in parallel). Confirm Q3 (microsoft-edit binary
name) before S1 lands. Run the conda-forge-expert 10-step autonomous
loop per recipe.

When Wave 1 PRs are all in staged-recipes review, proceed to Wave 2
(S5–S11). Investigate Q1 (PromptWizard PyPI presence) during S5; if
negative, defer S11 to deferred-work.md and reduce Wave 2 to 6
stories.

When Wave 2 is in review, proceed to Wave 3 (S12–S13). Resolve Q2
(DiskANN win-64) at S13 start; default to skipping win-64 with TODO.

After all PRs reach terminal state, run S14 closeout retro per
SKILL.md always-on Rule 2. Update this spec's Status header to
Shipped <date> with merge SHAs.
```
