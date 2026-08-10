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
| `--period` | `daily` \| `weekly` \| `monthly` \| `all` ingestion window | `weekly` |
| `--tier` | comma-list of `1` \| `2` \| `skip`, or the literal `all` | `1,2` |
| `--top` | Display cap over the already-ingested set (independent of ingest depth) | `25` |
| `--not-on-cf` / `--all` | Filter to not-yet-on-conda-forge candidates | `--not-on-cf` |
| `--min-stars` | Floor to drop micro-repos | `500` |
| `--json` | Machine-readable output | off (table by default) |

Read-side, offline-safe, idempotent: no fetch happens in the read path —
ingestion (CAP-1) and query (CAP-3) are separate operations.

As-built (Story 13.3, 2026-08-09): `--period` gained the 4th value `all` — the Search
API fallback stamps its rows with the literal `period="all"`
(`datasets/upstream_discovery.py::_SEARCH_API_FALLBACK_PERIOD`), so the three
enumerated windows alone could never reach them. `--period all` means "no period
filter" and is the explicit opt-in that also surfaces a repo's up-to-3x multi-window
duplicates. `--tier` accepts a comma-list because the default is the two-tier set
`1,2`. The shipped surface (`python -m pyforge.atlas.trending_candidates`, MCP
`query_trending_candidates`) is the authority on behaviour; this table is its contract.

## Downstream handoff (CAP-5)

As-built (Story 13.5, 2026-08-10): `trending-handoff`
(`python -m pyforge.atlas.trending_candidates.handoff_main`,
`pyforge.atlas.trending_candidates.handoff.hand_off_candidate`) is the CAP-5 gate that
turns ONE queryable candidate into a structured record for the packaging factory
(Mason) — never a recipe, never a staged-recipes PR. It is a plain read + CLI, the
identical non-pipeline shape CAP-3 already established: no new fetch, no new catalog
entry, no new Kedro node.

- **Flags:** `--repo OWNER/REPO` (required, case-insensitive), `--verdict {pass,fail}`
  (required), `--abandonment-signal TEXT` (required, non-empty), `--license-clarity
  TEXT` (required, non-empty). Output is unconditionally JSON — there is no table
  mode, unlike `trending-candidates`.
- **The health-screen gate runs on EVERY call** — there is no `--force`/skip flag.
  Only the PRESENCE of both evidence fields is validated (non-empty after `.strip()`),
  never their TRUTH: the verdict is a caller-supplied recorded input, not a computed
  one (pyforge-doctor's actual abandonment/license screen logic is explicitly out of
  this kernel's scope — SPEC.md's CAP-5 non-goal). `--verdict fail` always refuses.
- **Eligibility gates on `tier` directly, never on `not_on_cf`.** `_classify_row`
  (`pipelines/upstream_discovery/nodes.py`) only ever pairs tier `"1"`/`"2"` with a
  resolved OSI-license reason string — `"already-on-conda-forge"` and
  `"unclassified-needs-human"` are ALWAYS tier `"skip"`. Gating on `tier in {"1","2"}`
  therefore excludes both by construction, resolving the ambiguity a deferred-work
  item raised against `--not-on-cf`'s reason-based semantics (a repo whose on-cf
  status is genuinely UNKNOWN, not confirmed not-on-cf, could otherwise reach a
  programmatic consumer under `--tier all`/`--tier skip` — see
  `deferred-work.md`'s `spec-13-3-trending-candidates-operator-surface.md` entry) —
  without touching `query_trending_candidates`'s own `--not-on-cf` filter semantics at
  all.
- **Multi-window dedup:** a repo appearing under more than one trending window
  (`daily`/`weekly`/`monthly`) resolves to exactly ONE handoff record, via the same
  deterministic sort `query_trending_candidates` already uses (`stars_total` desc /
  `repo_full_name` asc / `period` asc, first row wins) — closes the deferred-work item
  CAP-2's own review pass raised against multi-window duplicates.
- **Schema:** `handoff.HANDOFF_ENVELOPE_SCHEMA` is a plain Python dict authored in
  real JSON-Schema-draft-2020-12 vocabulary (no new `jsonschema` pixi dependency),
  versioned independently via `handoff.HANDOFF_SCHEMA_VERSION` (an int, NOT
  `_provenance.SCHEMA_VERSION` — a different envelope entirely). Required keys:
  `schema_version`, `repo_full_name`, `tier`, `health_screen` (itself requiring
  `verdict`/`abandonment_signal`/`license_clarity`); the record also carries the
  selected row's own columns (repo identity, `reason`, `pypi_name`, …), a `provenance`
  block (mirrors `query_trending_candidates`'s own staleness envelope), and an
  epoch-seconds `handed_off_at`.
- **NFR-6 exit codes:** 0 pass, 1 policy-fail (`ValueError` — ineligible candidate,
  failing/missing health screen, dataset not yet ingested), 2 error (an unexpected
  bootstrap failure is never swallowed as a policy-fail), 130 interrupted.
