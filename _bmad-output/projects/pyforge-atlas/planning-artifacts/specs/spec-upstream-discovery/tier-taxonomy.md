# Tier taxonomy, skip reasons, and operator-surface parameters

Reference detail for CAP-2 (tier classification) and CAP-3 (operator surface).
Carried over from the legacy `docs/specs/trendshift-conda-forge.md` Tier
Definitions / classifier sections — the taxonomy and the operator contract
survive the Kedro reframe unchanged; only the storage/registration mechanics
(§ dropped in SPEC.md) do not.

## Tiers

Tiers are data-driven and extensible: store `tier` as a small int and
`tier_reason`/`skip_reason` as free text so new tiers are a classifier-logic
change, not a schema migration (this is now the *default* posture anyway —
the shipped dataflow's schema evolution is additive-first per dataset, not
versioned).

| Tier | Label | Inclusion test | Shape once packaged |
|---|---|---|---|
| **1** | Curated gap | PyPI-published AND library-or-CLI shape AND OSI license AND not-on-cf AND small/moderate dep tree (no compiled prereq closure) | `noarch:python`, one recipe |
| **2** | Broad / compiled | Packageable but: Rust/Go CLI, native/compiled, multi-output, GPU/heavy, or needs a prerequisite-recipe closure | per-platform and/or multi-output, possibly + prereq recipes |
| **skip** | Not actionable | No PyPI artifact and no clean lib/CLI shape (awesome-list / dataset / skills / docs / GUI app / mega-dep app); or already on conda-forge | — never a story |
| **3+** | *(reserved)* | Defined empirically after enough batches show a repeatable pattern (e.g. "monorepo-subpackage", "app-with-embedded-lib") | TBD |

## Skip reasons (enumerated, never silent)

Every ingested repo resolves to a tier or one of these reasons (extend the
enum as new patterns emerge — never let a repo fall through unlabeled):

`already-on-conda-forge`, `no-pypi-artifact`, `awesome-list`,
`not-osi-license`, `application-not-library`, `mega-dep-tree`,
`app-with-embedded-lib` (flag for human judgment rather than auto-skip — an
inner packageable library should not be lost inside an app repo),
`unclassified-needs-human` (the classifier's safety valve when a joined
signal is unavailable, e.g. a degraded/partial run with PyPI-intelligence
data missing).

## Trending source robustness

| Source | Form | Auth | Robustness | Role |
|---|---|---|---|---|
| `github.com/trending/python?since={daily,weekly,monthly}` | HTML scrape | none | Fragile (unofficial, layout can change) | **Primary** trending signal |
| GitHub Search API (`/search/repositories?q=language:python created:>DATE sort:stars`) | JSON | token | Robust (official, rate-limited) | **Fallback / corroboration** when the scrape thins out or drifts |
| `trendshift.io` | HTML, no JSON API | none | n/a | Human cross-reference only — never scraped programmatically |
| Existing atlas signals (feedstock health, downloads, release cadence) | local data | none | Robust | Enrichment only, not discovery — these measure *popular*, not *rising* |

Degradation contract: a scrape failure (404, layout drift, row count below a
floor) falls back to the Search API and/or keeps the prior snapshot with a
WARN — it never hard-fails the run.

## Operator-surface parameters (CAP-3)

| Flag | Meaning | Default |
|---|---|---|
| `--period` | `daily` \| `weekly` \| `monthly` ingestion window | `weekly` |
| `--tier` | `1` \| `2` \| `skip` \| `all` | `1,2` |
| `--top` | Display cap over the already-ingested set (independent of ingest depth) | `25` |
| `--not-on-cf` / `--all` | Filter to not-yet-on-conda-forge candidates | `--not-on-cf` |
| `--min-stars` | Floor to drop micro-repos | `500` |
| `--json` | Machine-readable output | off (table by default) |

Read-side, offline-safe, idempotent: no fetch happens in the read path —
ingestion (CAP-1) and query (CAP-3) are separate operations.
