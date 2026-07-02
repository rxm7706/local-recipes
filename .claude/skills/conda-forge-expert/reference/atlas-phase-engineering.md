# Atlas Phase Engineering

Patterns and constraints for writing or refactoring `conda_forge_atlas.py`
pipeline phases (B → N) and their per-row workers. These are *engineering*
concerns (rate limits, resumability, RAM, atomic IO) — distinct from the
*intelligence* the atlas surfaces, which lives in
[`atlas-phases-overview.md`](atlas-phases-overview.md) (Part A:
persona-indexed catalog; Part B: phase-indexed overview).

> **Consolidated (2026-07-02).** This file absorbed
> `atlas-phase-p-cost-model.md` — the Phase P cost model + operator
> playbook is now [§ 13](#13-phase-p--cost-model--operator-playbook).

This doc collects the lessons from the 2026-05-12 atlas hardening pass
(v7.8.0) onward. Treat it as the default rule book for any new phase or any
refactor of an existing phase that touches HTTP fanout, batch writes,
cache management, or volume-billed APIs.

---

## 1. Per-host secondary rate limits matter more than primary quotas

When a phase fans out N concurrent HTTP requests to a single host, the
failure mode is almost never the documented primary quota. It's the
secondary / burst-protection limit: GitHub's ~80 concurrent-request
ceiling, crates.io / rubygems.org's documented ~1 req/sec, PyPI's ~30
req/s per-IP, api.anaconda.org's per-IP secondary limit that trips around
8 simultaneous fetchers.

**Rule:** before setting a phase's default concurrency, look up the target
registry's documented or empirically-observed per-host limit. Set defaults
that sit *under* the limit with headroom, not at it.

Documented limits worth memorizing:

| Host | Documented / observed ceiling | Safe atlas default |
|---|---|---|
| `api.github.com` (REST) | 5,000 pts/hr primary; ~80 concurrent secondary | n/a — use GraphQL (see §2) |
| `api.github.com/graphql` | 5,000 pts/hr | 100 repos/request, serialized |
| `pypi.org/pypi/<n>/json` | ~30 req/s per IP | 3 workers |
| `api.anaconda.org` | ~60 req/min per IP (secondary) | 3 workers (Phase F) |
| `crates.io` | 1 req/sec documented | 1 worker |
| `rubygems.org` | ~1 req/sec recommended | 1 worker |
| `gitlab.com/api/v4` | 600 req/min global | 2 workers |
| `search.maven.org` | undocumented; small-volume | 2 workers |
| `registry.npmjs.org` | CDN-backed; tolerates 4–8 | 4 workers |
| `api.nuget.org` (flat-container) | CDN-backed; tolerates 4–8 | 4 workers |
| `fastapi.metacpan.org` | undocumented | 2 workers |
| `crandb.r-pkg.org` | undocumented | 2 workers |
| `luarocks.org` | HTML scraper; small-volume | 2 workers |

Every phase concurrency knob is overridable via env vars. The convention
is `PHASE_<ID>_CONCURRENCY` for the legacy global, plus per-host
overrides where relevant (e.g. `PHASE_L_CONCURRENCY_<SOURCE>`).

**v8.20.0 — sustained-rate scheduler as the canonical pattern when the
GraphQL alternative isn't available.** Concurrency caps alone aren't
enough when the registry's secondary-limit threshold sits at a per-second
rate rather than a concurrent-worker count: an 8-worker pool fired at the
GitHub REST API hit ~70 req/s peak burst (each worker firing one request
at a time, but in lockstep) and tripped a 15% 403 rate on a 4,400-row
Phase K fanout (2026-05-12 incident — auto-memory
`project_phase_k_secondary_rate_limit.md`). The fix is a token-bucket
scheduler that paces total throughput, not per-worker concurrency. The
canonical implementation is `_RateLimitedScheduler` in
`scripts/conda_forge_atlas.py` (single-process, stdlib `time.monotonic()`,
~30 LOC):

```python
class _RateLimitedScheduler:
    def __init__(self, rps: float, bucket_capacity: int = 10):
        if rps <= 0:
            raise ValueError(...)
        self.rps = float(rps)
        self.bucket_capacity = int(bucket_capacity)
        self.bucket = float(bucket_capacity)
        self.last_refill = time.monotonic()

    def acquire(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.bucket = min(self.bucket_capacity,
                          self.bucket + elapsed * self.rps)
        self.last_refill = now
        if self.bucket < 1.0:
            wait = (1.0 - self.bucket) / self.rps
            time.sleep(wait)
            self.bucket = 0.0
            self.last_refill = time.monotonic()
        else:
            self.bucket -= 1.0
```

Caller invokes `scheduler.acquire()` immediately before each HTTP
request; the bucket caps incidental bursts (default capacity 10) while
the sustained rate (default 3.0 req/s) sits ~3× under GitHub's
secondary-limit threshold. Phase K wraps the scheduler with: (1) a
`PHASE_K_AGGRESSIVE=1` opt-in that restores the previous
`ThreadPoolExecutor(max_workers=8)` burst pattern + emits a one-line
stderr warning at Phase K entry (audit trail for operators who see 403
spam later); (2) per-request timing lines to stderr for the first 30 s
so operators verify the scheduler is engaged, then silent unless
`PHASE_K_DEBUG_SCHEDULER=1` is set; (3) a one-shot
`meta.phase_k_403_backfill_pending=1` sentinel installed at `init_schema`
time alongside an install marker `meta.phase_k_first_run_post_v8_20_0=1`
written atomically — the next Phase K run expands its eligibility list
to include all `last_error LIKE '%403%'` rows regardless of TTL, then
DELETEs the sentinel before fanout starts (mid-run crashes recover via
the natural `last_error != NULL` TTL bypass). Pattern reach: any phase
fanning out to a host with documented sustained-rate limits but no
GraphQL alternative (Codeberg, GitLab REST, crates.io, rubygems.org).

**Codeberg note (v8.21.0):** the 3 RPS default is uncited for Codeberg —
auto-memory `project_phase_k_secondary_rate_limit.md` covers GitHub only.
Volume is small (~16 rows in a typical channel-wide Phase K run), and
Codeberg's documented limits are higher than GitHub's; 3 RPS appears
safe. Revisit if Codeberg-hosted feedstocks grow above ~100 OR a
Codeberg HTTP 403 surfaces in `upstream_versions.last_error`.

---

## 2. GraphQL batching beats REST fanout for GitHub

GitHub's REST `/repos/<o>/<r>/releases/latest` requires one HTTP call per
repo. A 4,400-row Phase K with REST + 8 workers + a release/tag fallback
issues ~14,000 HTTP calls and reliably trips GitHub's secondary rate
limit even with a PAT (observed: 15% 403s, 2026-05-12).

The GraphQL alternative: build one aliased query per batch of repos and
POST it to `/graphql`. Each repo's subquery asks for both releases and
tags in the same round-trip:

```graphql
query {
  r0: repository(owner: "...", name: "...") {
    releases(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { tagName }
    }
    refs(refPrefix: "refs/tags/", first: 1,
         orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
      nodes { name }
    }
  }
  r1: repository(...) { ... }
  ...
  rateLimit { cost remaining resetAt }
}
```

The same 4,400 repos become ~44 HTTP POSTs (one per batch of 100). Per-
alias errors come back via `path[0]`; `NOT_FOUND` maps to `HTTP 404` to
preserve existing downstream branching. Per-host complexity ceiling is
~500K nodes; batches of 100 (200 nodes each) stay comfortably under.

**Rule:** when adding a new phase that touches the GitHub API, GraphQL
first. Reach for REST only if the data you need has no GraphQL exposure
(GitLab, Codeberg, etc.).

Reference implementation: `_phase_k_github_graphql_batch` in
`conda_forge_atlas.py`.

---

## 3. `Retry-After` parsing with a hard cap is the default

When a server returns 429 or 503 with a `Retry-After` header, the right
client behavior is to honor the value — but **with a hard cap**. A
buggy or hostile origin can otherwise stall a worker for hours.

The cap is 60 seconds. Anything longer than that, treat the row as
failed and let the next TTL-gated run pick it up.

`Retry-After` per RFC 9110 can be either a delta-seconds integer
(`Retry-After: 30`) or an HTTP-date (`Retry-After: Wed, 12 Nov 2025
14:00:00 GMT`). The shared helper `_parse_retry_after(value, fallback)`
handles both forms and the cap.

When no `Retry-After` is present, fall back to exponential backoff with
**±25% jitter**. Without jitter, a worker pool that all hit 429 at the
same instant retries in lockstep, re-triggering the rate limit. Jitter
desynchronizes them across the next-attempt window.

Reference implementation: `_phase_f_fetch_one` in `conda_forge_atlas.py`.

---

## 4. Per-registry concurrency caps, not a global one

Phase L originally had `PHASE_L_CONCURRENCY=8` applied uniformly to all
seven registries (npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven).
Worst case: 8 × 7 = **56 simultaneous outbound requests at startup**,
which immediately tripped crates.io's 1 req/sec limit and rubygems.org's
~1 req/sec ceiling.

**Rule:** any phase that fans out to multiple hosts must process them
sequentially across hosts, with a per-host concurrency cap reflecting
that host's documented limit. The legacy global env var should still
cap *all* hosts uniformly (so `PHASE_L_CONCURRENCY=1` forces fully
serial), and per-host overrides take precedence.

Pattern:

```python
_PHASE_X_DEFAULT_CONCURRENCY = {"npm": 4, "crates": 1, "rubygems": 1, ...}

def _phase_x_concurrency_for(source: str) -> int:
    # PHASE_X_CONCURRENCY_<SOURCE> wins
    per_source = os.environ.get(f"PHASE_X_CONCURRENCY_{source.upper()}")
    if per_source:
        return max(1, int(per_source))
    # Legacy global caps everything uniformly
    legacy = os.environ.get("PHASE_X_CONCURRENCY")
    if legacy:
        return max(1, int(legacy))
    return _PHASE_X_DEFAULT_CONCURRENCY[source]

# In the phase body:
for source, source_work in work_by_source.items():
    workers = _phase_x_concurrency_for(source)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        ...
```

Reference implementation: `phase_l_extra_registries` in `conda_forge_atlas.py`.

---

## 5. Atomic file writes for any cache or output

Any phase that writes a JSON cache, a tarball cache, or a user-facing
output file must use the atomic-write pattern:

1. Write to a `.tmp` sibling of the final path.
2. `flush()` + `os.fsync(fileno)` (best-effort; some FS don't support it).
3. `os.replace(tmp, final)` — atomic on the same filesystem.

The shared helpers in `_http.py`:

- `atomic_writer(path, mode)` — context manager. Use this for
  streaming writes (`json.dump`, `csv.writer`, etc.).
- `atomic_write_bytes(path, data)` — for callers that already have a
  bytes payload in hand.
- `atomic_write_text(path, text, *, encoding="utf-8")` — text equivalent.

```python
from _http import atomic_writer

with atomic_writer(cache_path, "w") as f:
    json.dump(indexed_db, f)
```

Failure modes the pattern prevents:

- SIGINT mid-`json.dump` → truncated JSON that fails to load next run,
  forcing a full network re-fetch.
- OOM during cache write → ditto.
- Power loss / process crash → ditto.

On exception inside the `with` block, the helper unlinks the `.tmp`
file and re-raises; the prior contents of `path` are untouched.

Affected/migrated call sites (v7.8.0): `cve_manager.py`,
`mapping_manager.py`, `inventory_channel.py` (both cache writes and
`--sbom-out` user output), `phase_e_enrichment` (cf-graph tarball
cache download).

---

## 6. Incremental commits + idempotent SQL

Any phase that issues many INSERT/UPDATE statements (>500) must commit
periodically — not wrap the entire phase in a single transaction. The
default cadence is every 200–500 rows:

```python
commit_every = 200
processed = 0
for row in source_iterable:
    conn.execute("INSERT OR REPLACE INTO ...", (...))
    processed += 1
    if processed % commit_every == 0:
        conn.commit()
conn.commit()  # final
```

This requires every write to be **idempotent on re-run** — interrupts
mean a phase may see the same row twice. Use:

- `INSERT OR REPLACE` (when the unique key catches duplicates).
- `INSERT OR IGNORE` (when re-inserting a fresh row is fine to skip).
- `UPDATE ... SET col = COALESCE(?, col)` (when we want to enrich
  without clobbering existing data).
- `UPDATE ... WHERE COALESCE(fetched_at, 0) < ?` (TTL gating; re-runs
  skip fresh rows).

What NOT to do:

- `INSERT INTO packages (...)` without `OR REPLACE` / `OR IGNORE` —
  a re-run after partial completion gets `UNIQUE constraint failed`.
- `UPDATE ... SET fetched_at = ?` without a WHERE clause that limits
  to "this phase's rows" — costs full-table scans + writes.
- `BEGIN TRANSACTION` / `COMMIT` wrapping the whole phase — a mid-
  phase interrupt rolls everything back.

Phases that hold the iterator open while issuing UPDATEs need to
buffer the SELECT into a list first (`rows = list(conn.execute(...))`)
— otherwise a commit mid-loop can invalidate the cursor.

Reference implementations: phases B, B5, D, F, G, H, K, L, M.

---

## 7. Stream tarfile from disk; don't read into RAM first

When parsing a large compressed archive, the wrong pattern is:

```python
tar_bytes = cache_path.read_bytes()       # 150MB → RAM
with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
    ...
```

The right pattern is:

```python
with tarfile.open(cache_path, "r:gz") as tf:
    ...
```

Saves ~150MB peak RAM on Phase E. The difference matters in container
environments with tight memory limits, and avoids OOM-kills that
otherwise cost the entire phase.

The `BytesIO` form is only correct when the bytes came from a *network
fetch that wasn't cached to disk* — and in that case, write the cache
file before parsing, then close the loop by opening the cache file
directly:

```python
if not cache_path.exists():
    tar_bytes = fetch_with_fallback(urls, ...)
    atomic_write_bytes(cache_path, tar_bytes)
    del tar_bytes  # release the 150MB
with tarfile.open(cache_path, "r:gz") as tf:
    ...
```

Reference implementation: `phase_e_enrichment` in `conda_forge_atlas.py`.

---

## 8. Page-level checkpoints for paginated phases

Any phase that pages through a remote API (GraphQL pagination, REST
cursor pagination, S3 ListObjects) should call `save_phase_checkpoint`
after each page:

```python
cursor = None
items_completed = 0
while True:
    response = fetch_page(cursor)
    cursor = response.next_cursor
    items_completed += len(response.items)
    save_phase_checkpoint(
        conn, "phase_xyz",
        cursor=cursor,
        items_completed=items_completed,
        status="in_progress",
    )
    conn.commit()
    if not response.has_next:
        break
save_phase_checkpoint(conn, "phase_xyz", status="completed")
```

The checkpoint serves two purposes:

1. **Observability**: `SELECT * FROM phase_state WHERE phase_name='phase_xyz'`
   lets an operator see pagination progress mid-run instead of waiting
   for the phase to print its own progress line.
2. **Resume hint**: when the API is genuinely resumable (the cursor
   means something to the server), a re-run can pick up from the saved
   cursor. When it isn't (GitHub's archived-repos query has no side
   effects, so re-pagination is cheap), the checkpoint still provides
   the observability win.

Reference implementations: `phase_e5_archived_feedstocks` (page-level
checkpoint without resume), `phase_n_github_live` (full resume from
cursor).

---

## 9. Enterprise routing: `_BASE_URL` env vars, never committed config

Every host the atlas talks to must be redirect-able via an env var of
the form `<HOST>_BASE_URL`. The pattern is encoded as resolver functions
in `_http.py`:

```python
def resolve_<host>_urls(name: str) -> list[str]:
    """Priority: <HOST>_BASE_URL env → public default."""
    bases = [os.environ.get("<HOST>_BASE_URL")]
    bases.extend(_DEFAULT_<HOST>_FALLBACKS)
    return [f"{b}/<path>/{name}" for b in _dedup_strip(bases)]
```

Callers consume the resolver via `_fetch_with_fallback(urls, ...)`
which iterates the chain and applies the correct auth headers
(via `auth_headers_for(url)`).

Hosts with resolvers as of v7.8.0:

- `CONDA_FORGE_BASE_URL`
- `PYPI_BASE_URL` / `PYPI_JSON_BASE_URL`
- `GITHUB_BASE_URL` / `GITHUB_RAW_BASE_URL`
- `NPM_BASE_URL` (+ honors `npm_config_registry` — npm CLI standard)
- `CRAN_BASE_URL`
- `CPAN_BASE_URL`
- `LUAROCKS_BASE_URL`
- `CRATES_BASE_URL`
- `RUBYGEMS_BASE_URL`
- `MAVEN_BASE_URL`
- `NUGET_BASE_URL`
- `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE`)
- `S3_PARQUET_BASE_URL`

**Rule:** if you're adding a new resolver, add it to `_http.py`, give
it the same shape as the existing ones, and write at least one
`TestResolve<Host>Urls` case in `test_http_resolvers.py` covering the
external-default and env-var-redirect paths.

---

## 10. Volume-billed APIs need a hard cap, a dry-run, and a documented price

Some atlas phases call paid-by-volume APIs where a single query can
cost real money — BigQuery on-demand at $6.25/TB scanned is the
canonical example; OSV.dev bulk endpoints, GitHub GraphQL points
budget, and ecosyste.ms paid tiers fit the same shape. Three
defences must be in place before any such phase ships:

**(a) Hard server-side cap.** Use the provider's "abort if this query
would cost more than $N" primitive, not a client-side estimate. For
BigQuery this is `bigquery.QueryJobConfig(maximum_bytes_billed=N)` —
if actual processed bytes exceed N, BQ aborts with HTTP 400 `Query
exceeded limit for bytes billed` and **bills $0**. That's the right
failure mode: fail-fast with no spend, not "succeed and bill $500".

```python
# Compute byte ceiling from operator's USD cap.
cap_usd = float(os.environ.get("PHASE_X_MAX_COST_USD", "10"))
usd_per_tb = float(os.environ.get("PHASE_X_USD_PER_TB", "6.25"))
max_bytes = int((cap_usd / usd_per_tb) * 1e12)

client.query(
    sql,
    job_config=bigquery.QueryJobConfig(
        maximum_bytes_billed=max_bytes,
        job_timeout_ms=int(os.environ.get("PHASE_X_JOB_TIMEOUT_MS", "600000")),
    ),
).result()
```

**(b) Dry-run preflight.** If the provider offers a free planning or
quote endpoint, use it to estimate cost before submitting the real
query. BigQuery's dry-run mode returns `total_bytes_processed`
without consuming quota:

```python
dry = client.query(
    sql,
    job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
)
est_bytes = dry.total_bytes_processed or 0
est_usd = (est_bytes / 1e12) * usd_per_tb
if est_usd > cap_usd:
    return {"skipped": True, "reason": f"est ${est_usd:.2f} > ${cap_usd:.2f} cap"}
```

Always print the dry-run estimate to stdout before submitting the
real query. Operators inspecting the run output see the cost
upfront — no surprises. The same pattern fits any provider with a
free quote endpoint (look for `--dry-run` flags, `validateOnly: true`
query params, or `Cost-Preview: yes` headers in REST APIs).

**(c) Documented price + verifiable source.** Every cost claim in
the phase's docstring + the operator-facing reference doc MUST
cite an empirical source: a dry-run output (`as of 2026-06-12,
trailing 90 days = ~2.5–4 TB → ~$15–25 at $6.25/TB`), a measured
benchmark, or `bq show --schema <table>` table-statistics output.
Napkin numbers without provenance drift silently — see § "Verify,
Don't Assume" in SKILL.md. The 2026-06-12 BigQuery invoice surprise
($500+ for one Phase P refresh against a documented "~30 GB / within
free tier" expectation) traced to a 2016 napkin number copied
through ~25 documentation sites over 10 years without anyone re-
verifying.

**(d) Coverage/cardinality claims need a verifiable denominator.**
Cost discipline is well-internalized (v8.15.1+) but coverage claims
escaped the rule until v8.16.2. When a phase ships under a free or
cap-limited backend, the docstring/spec/reference doc MUST state
what fraction of the candidate set the phase actually populates,
expressed as a verifiable ratio with both numerator and denominator.
"Top-1,000 by 90-day downloads" is incomplete; "top-1,000 ≈ 3.3 %
of the ~30k `pypi_intelligence` candidate rows; remaining 96.7 %
have NULL `downloads_30d`/`downloads_90d`" is verifiable. NULL is
not silent — readers acting on missing values without a coverage
caveat reach wrong conclusions ("package has no downloads") instead
of right ones ("package is outside our measurement window").
Implementation rule: phases with partial coverage MUST populate
the relevant `*_source` provenance column (e.g.
`pypi_intelligence.downloads_source = 'clickhouse-clickpy'`) and
the consumer-facing reference doc MUST teach readers to check
that column before treating NULL as zero. Phase P v8.16.0 shipped
the source column but the coverage caveat lived only in the code
docstring — the persona catalog (now `atlas-phases-overview.md` Part A) didn't surface it
until v8.16.2's retro. Don't repeat the gap: the rule is
**numerator + denominator + provenance + consumer-side caveat**,
all four together, at ship time.

**Tunables convention.** Every volume-billed phase ships with the
following operator-tunable env vars:
- `PHASE_X_MAX_COST_USD` — per-run cap (USD); BQ aborts above.
- `PHASE_X_MAX_COST_FIRST_PULL_USD` — separate cap for the cold-
  start case where larger budget is acceptable.
- `PHASE_X_USD_PER_TB` (or `_USD_PER_REQUEST`, etc.) — provider
  price; override for non-US regions.
- `PHASE_X_JOB_TIMEOUT_MS` — wall-clock cap to prevent zombie jobs.

Canonical implementation: `phase_p_pypi_downloads`. Operator-facing
playbook: § 13 below — copy its
structure (TL;DR table + tunables + decision tree + runbook +
alternative-source verification + cost projection) for any future
volume-billed phase.

**(e) Free sources have operational gates too.** When adding a free
public dataset as a Phase data source, the feature docs ("read-only
public access to dataset X") almost never cover the **operational
constraints** that determine whether the source is usable in
production. Probe for each before committing the architecture:

- **Response row caps.** Many providers truncate aggregated query
  responses to fit memory limits. ClickHouse Play caps aggregated
  responses at ~1,000 rows (verified 2026-06-12 — `GROUP BY project`
  with no ORDER BY returns ≤1,000 rows even when underlying data has
  millions). Detect: run a known-large aggregated query, compare
  result row count to a separate `SELECT count() FROM (...)` of the
  same subquery.
- **Sustained-burst rate limits.** "Burst" performance (a few
  concurrent queries) typically tests fine; "sustained" (hundreds of
  concurrent queries over minutes) hits hard limits not in docs.
  ClickHouse Play: 4-concurrent burst works; 4-concurrent sustained
  over 1,500 buckets returned HTTP 500 on ~95% of requests. Detect:
  run the target throughput pattern (parallel × duration), not just
  a single concurrent test.
- **Quota walls (free tiers).** Most free tiers reset monthly but
  have hard caps; the 2026-06-12 BigQuery `unbilled.analysis` error
  surfaced this for the operator's GCP project. Detect: query the
  service's quota endpoint or attempt a small-then-medium query and
  observe the failure mode.
- **Response format quirks.** Servers may stream "OK" responses with
  embedded errors instead of HTTP error codes (ClickHouse plays
  back errors as plain text lines mixed with JSONEachRow data when
  the FORMAT directive is in flight). Plan for graceful parsing
  failure → skip the line, don't crash.
- **Authentication tier limits.** "Public" / "play" / "anonymous"
  users have stricter limits than authenticated ones. ClickHouse
  Cloud's paid tiers have higher caps. Distinguish "the feature
  works for everyone" from "the feature works at production scale
  for everyone with their own account".

The operational constraints determine the actual usable architecture.
Phase P's v8.16.0 design pivoted from bucketed-pagination (architected
around feature docs alone) to single-query top-N (architected around
verified operational constraints) when live testing revealed the cap
+ rate-limit reality. Bucket-pagination would have shipped a system
that takes 25+ minutes wall-clock with 90% retry cost vs. a 4-second
single-query alternative. **Always validate operational behavior
before committing the architecture**, not just feature availability.

**(f) Docstring + reference doc MUST match shipped code at ship time.**
When live testing forces an architecture pivot mid-implementation, the
function docstring, the reference doc (`atlas-phases-overview.md` Phase
description), and the CHANGELOG entry all need a re-read against the
final code before the commit lands. v8.16.0 shipped with three
mutually-contradictory descriptions of Phase P/ClickHouse: the CHANGELOG
entry and reference doc described the original `cityHash64 % 30`
bucket-pagination architecture; the function docstring's "Architecture:"
header repeated the same; only the function body shipped the actual
top-N single-query implementation that live testing forced. v8.16.2's
retro caught and corrected the docstring + reference; the CHANGELOG
entry retains the original language (per immutable-history discipline)
but now carries an erratum banner pointing at v8.16.2. The fix at ship
time would have cost ~5 minutes of re-reading; the retro cost ~2 hours
across two PATCH versions. Discipline rule: **before pushing a ship
commit for any phase with code that diverged from the spec mid-
implementation, re-read docstring + reference doc + CHANGELOG entry
against the actual code** — confirm each describes what shipped, not
what was originally planned. The CHANGELOG-entry erratum-banner pattern
(see v8.16.0 entry's `**ERRATUM (v8.16.5):**` line for the canonical
form) is the recovery mechanism when the at-ship check is skipped.

**(g) `INSERT OR REPLACE` alone doesn't deliver "replace" semantics on
partial reruns.** A many-to-many breakdown table (e.g.
`package_platform_downloads` with PK `(conda_name, pkg_platform)`)
populated via `INSERT OR REPLACE` only touches the (PK) rows present in
the *current* sweep. If a `(numpy, osx-arm64)` row vanishes from a
later parquet window — because that platform's downloads dropped to
zero, because the dataset shape changed, or because the eligible-rows
set shrank under `PHASE_F_LIMIT` — the prior `osx-arm64` row stays in
the table as a zombie. The PK-level "replace" only achieves "replace
existing keys"; it cannot delete keys that disappeared. Spec language
saying "re-running Phase F replaces, doesn't accumulate" implies
*scope-level* replacement, which `INSERT OR REPLACE` does NOT deliver.
**Fix pattern**: `DELETE FROM <table> WHERE <scope_key> IN (<eligible>)`
before the bulk `INSERT OR REPLACE`, in the same transaction. Chunk the
DELETE to fit SQLite's 999 host-parameter cap if eligible-set is large
(canonical: 500-row chunks). v8.18.0's Phase F+ Wave 2 H1 patch is the
canonical implementation; see `_phase_f_via_s3` in
`scripts/conda_forge_atlas.py` around the breakdown-table writes. When
authoring spec Boundaries for many-to-many tables, write **DELETE +
INSERT**, not "INSERT OR REPLACE keyed on PK" — the latter is a
mechanism, not the semantic intent.

**(h) Provenance-column value claims in spec Boundaries must be
verified against the dispatcher's actual write paths.** When a spec
Boundary says "this column populates when `<source_col> ∈ {A, B}`",
grep the writers for both values before approving the spec — not the
column-definition comment. v8.18.0's Wave 2 spec Boundaries claimed
Wave 2 columns populate when `downloads_source ∈ {'s3-parquet',
'merged'}`. The reviewer (H4) caught that the Phase F dispatcher
(`_phase_f_via_auto`) uses `'merged'` only as a *run-summary* label
returned in the `source` field of the result dict — no per-row write
in `packages.downloads_source` ever assigns `'merged'`. The spec
Boundary was based on the v7.6.0 column-DDL comment (which lists three
allowed values as a static enum), not on the live writer behavior.
Fix pattern: before signing off Wave-N spec Boundaries that constrain
on a multi-value column, `grep "<column> *=" scripts/conda_forge_atlas.py`
and enumerate the actual literals written by the running code.
Discrepancies become either spec corrections (this case — `'merged'`
removed from the Wave 2 spec) or code patches (the column-DDL comment
becomes misleading and needs an erratum).

**(i) Step-04 adversarial review is load-bearing for Phase-F-class
changes.** The bmad-quick-dev step-04 three-reviewer protocol (blind
hunter + edge case hunter + acceptance auditor) surfaced 13 patches in
v8.18.0 — 3 HIGH (stale zombie rows, NULL-overwrite of valid prior
data, doc/code divergence on `'merged'`), 5 MED (non-atomic migration,
hidden side-effects in a "read" function, force-refresh + limit
interaction, regex 3.81 known-limitation, exactly-6-months boundary
test), and 5 LOW. Without that pass, all 5 H/M HIGHs would have shipped
silently. For any change that touches schema migration, multi-table
aggregation, or provenance-column writes, **treat the step-04 pass as a
required ship gate, not optional polish**. Single-line code changes
(version bumps, env-var defaults) can skip; anything that adds a column,
writes to multiple tables in one transaction, or introduces a new
provenance label must go through the three-reviewer pass.

**(j) Population-distribution claims in spec ACs need the same
empirical-verification discipline as cost + coverage claims.** v8.15.1
(cost) and v8.16.2 (coverage) established the rule: quantitative claims
in spec/code/docs must cite an empirical source or carry a
"verified $DATE" marker. v8.19.0's Wave 3 extends this to **population-
distribution claims** — acceptance criteria that include a percentage
threshold against a population (e.g., "≥80% of rows have non-NULL
`<column>`"). The Wave 3 AC-1 said "`packages.python_min` is non-NULL
for ≥80% of conda-forge-only packages". The implementer's 5,001-sample
empirical survey of cf-graph `node_attrs/<name>.json` found ~9% of
recipes declare a `python_min` override; the remaining ~91% inherit
the conda-forge global pinning default. The AC was off by ~10×. The
acceptance auditor caught the contradiction between the spec body and
the CHANGELOG's empirical wording. **Discipline rule**: any spec AC
that includes a percentage threshold against a real-world population
(rows in `packages`, feedstocks-per-maintainer, packages-on-defaults,
etc.) MUST cite the empirical source the threshold was derived from,
OR ship the implementation first, measure, then write the AC. Don't
write speculative percentage thresholds. Patterns to use: "≥N% of
rows where `relationship='both_same_name'`, verified $DATE via
`<command>`" or "any non-zero count, with the empirical population
mean expected to land near M% based on $METHOD". The retro is the
recovery mechanism; the at-spec-time empirical citation is the
prevention mechanism.

**(k) "Ask First" boundary clauses trigger investigation, not
necessarily HALT.** When a spec Boundaries clause says "HALT if X
not found, don't guess" and the implementer's first investigation
reveals X exists in a different shape than the spec assumed (nested
deeper, named differently, structurally split), the correct action
is **document the actual shape in CHANGELOG + Design Notes, proceed
if the same data is verifiably present**, NOT HALT. v8.19.0's Wave 3
spec Ask First clause said "HALT if neither `python_min` nor
`noarch_python_min` key is found in `node_attrs/<name>.json`, don't
guess." The implementer's 5,001-sample survey found neither key at
the top level — but the value lives **nested inside the
`raw_meta_yaml` string** (the pre-render recipe source) as a Jinja
context variable. The implementer surveyed, documented the finding
in the CHANGELOG, then proceeded with regex extraction — explicitly
endorsed by the spec's § Design Notes ("cf-graph's
`node_attrs/<name>.json` is the canonical offline source for declared
recipe metadata; reading it at Phase E time is the existing channel").
Strictly HALTing would have been wrong: the data IS there, just in
a different shape than the spec assumed. **Discipline rule**: an
Ask First clause means "investigate before guessing", not "stop on
first non-match". If the investigation finds the same data verifiably
present in a different shape, document the deviation and proceed.
The fail-safe is the documentation + the CHANGELOG, not the HALT.

**(l) Environment-variable boolean parses use strict `== "1"`, not
`bool(os.environ.get(...))`.** A common Python gotcha that v8.20.0's
Phase K implementation surfaced: the first sub-agent wrote
`aggressive_mode = bool(os.environ.get("PHASE_K_AGGRESSIVE"))`.
`bool()` of any non-empty string is True — so `PHASE_K_AGGRESSIVE=0`,
`PHASE_K_AGGRESSIVE=false`, `PHASE_K_AGGRESSIVE=no`, even
`PHASE_K_AGGRESSIVE=` *(with trailing space)* would silently re-arm
the 8-worker burst pattern that the rest of the ship was designed to
escape. The blind hunter caught the bug; the patch was
`aggressive_mode = os.environ.get("PHASE_K_AGGRESSIVE") == "1"` —
strict equality on the literal `"1"`. **Discipline rule**: any phase
env-var that gates "opt-in to behavior X" uses **strict `== "1"`**
not `bool(...)`. Document the convention in the env-var docstring
("set =1 to opt in; anything else is treated as unset"). Apply
uniformly across all `PHASE_*_AGGRESSIVE`, `PHASE_*_DEBUG_*`,
`PHASE_*_ENABLED`, `PHASE_*_DISABLED` etc. flag variables. Numeric
or string-value env vars (`PHASE_*_TTL_DAYS`, `PHASE_*_CONCURRENCY`)
naturally use `int()`/`float()` parses and aren't affected. The
v8.20.0 H4/EC-#7 patch added a sibling rule for numeric envs:
**always validate finite-and-positive on `float()` parses** — wrap
in try/except + `math.isfinite()` + fallback with stderr advisory;
don't let an env-var typo (`nan`, `inf`, empty string) crash a phase
with an unhelpful traceback.

**(m) Spec I/O matrix consistency between "Expected Output" and
"Error Handling" columns.** v8.20.0's Phase K spec I/O matrix row 3
said both "DELETE FROM meta WHERE key='phase_k_403_backfill_pending'
after eligibility-set built but before fanout starts" (Expected
Output) AND "sentinel survives Phase K crash mid-run; next run re-
applies (idempotent)" (Error Handling). These are contradictory: if
the DELETE fires before fanout, a mid-fanout crash leaves the
sentinel already deleted — recovery via sentinel re-application is
impossible. The implementer picked the literal Expected-Output
reading; the edge case hunter caught the contradiction
post-implementation; the patch moved the DELETE to post-fanout-
success (with a second DELETE at the empty-work success early-
return) so mid-crashes correctly preserve the sentinel.
**Discipline rule**: when authoring an I/O matrix row whose
Error-Handling column describes a sentinel-based or marker-based
recovery, the Expected-Output column MUST describe sentinel
persistence consistent with the recovery contract. Don't write
"DELETE before X" alongside "survives mid-X crash" — pick the
recovery you actually want and write both columns to match. If the
two columns describe legitimately different control paths (success
vs. failure), separate them into two matrix rows. A spec contradiction
costs an extra step-04 review cycle to catch; a clean I/O matrix
costs nothing.

**Note on rule (j) scope.** v8.19.1's rule (j) was titled
"population-distribution claims need empirical-verification
discipline". v8.20.0's AC-1 timing band (9.5–12 s vs. the actual
5.5–12 s bucket-math floor) demonstrated the rule applies to
**all quantitative claims**, not just population distributions —
cost, coverage, distribution, timing, performance, throughput. The
implementer caught the spec's math error and amended the AC; rule
(j) is hereby clarified to cover any quantitative claim that can be
derived or measured. The discipline is the same: write the claim
empirically grounded (cite the source, do the math), or ship-first-
measure-then-write-the-claim.

**(n) Wrapper-timeout false-negatives are a structural defect, not
a tuning problem.** v8.16.6 raised the `bootstrap-data` cf-atlas
wrapper timeout from 7,200 s → 14,400 s to mitigate a wrapper-level
false-negative: `bootstrap-data --profile admin` printed
`✗ cf-atlas-build` while the Python subprocess kept running and
finished cleanly. Raising the timeout only widens the slack window
before the false-negative recurs — it doesn't fix the underlying
defect that **one operator-facing ✓/✗ aggregates ~21 phases under
one wrapper**, hiding which phase actually slipped past the wall
clock when individual phase durations span 100× (Phase F's
s3-parquet ~30 s vs. Phase K's sustained-rate ~75 min). v8.22.0
fixed it structurally by splitting the wrapper into 4 sub-steps
(`core` / `F` / `K` / `N`) each with its own timeout +
independent ✓/✗ reporting. **Discipline rule**: when a wrapper
around N phases produces a single boolean exit code while
individual phase durations vary by 100×, the wrapper's "did it
succeed" semantics are degenerate. Raise the timeout once to stop
the symptom (v8.16.6-class mitigation buys time), then split the
wrapper (v8.22.0-class structural fix). **Always keep a legacy
escape hatch** (`BOOTSTRAP_CF_ATLAS_TIMEOUT=14400` restores the
v8.16.6 single-subprocess behavior) for operators with log-scrapers
or monitors keyed on the old single-row summary shape. The escape
hatch is cheap to maintain (one env-var check + one fallback
branch) and saves the cross-org coordination cost of a breaking
change to `bootstrap-data` summary output.

**(o) Phase-ordering invariants survive sub-step splits only if
you preserve canonical ordering inside each sub-step.** v8.22.0's
4-sub-step split (`core` / `F` / `K` / `N`) had to preserve the
canonical PHASES execution order INSIDE the `core` sub-step:
B → B.5 → B.6 → C → C.5 → D → O → P → Q → R → S → E → E.5 → G →
G' → H → J → L → M. Phase J (which reads `cf-graph.tar.gz`
populated by Phase E) MUST run after Phase E within the same
sub-step, or it silently produces zero rows. Two new operator
flags shipped with v8.22.0 (`--skip PHASES`, `--only PHASES`)
expose phase selection to the operator; the implementation
preserves operator-specified order under `--only` (the operator is
explicit), but iterates **canonical PHASES order minus the skip
set** under `--skip` so the safe default holds when the operator
doesn't reorder. **Discipline rule**: in any phase-orchestration
refactor that adds operator-facing phase-selection flags, the
canonical PHASES list is the source of truth for ordering UNLESS
the operator's flag explicitly opts out. A wrapper-split refactor
doesn't introduce new schema or tables, but it can silently
violate phase prerequisites by reordering — verify ordering
invariants in tests that seed Phase-E-output and assert Phase J
reads it, not just by inspection of the dispatcher list. The
`test_cmd_build_only_preserves_listed_order` /
`test_cmd_build_skip_excludes_phases` pair in
`tests/unit/test_conda_forge_atlas_build.py` is the v8.22.0
template for this discipline.

---

## 11. Per-day local cache for rolling-window queries

When a phase queries a rolling N-day window from a paid or rate-
limited source, store per-day rows in a local side table and
recompute rolling aggregates via SQL. Querying only the *new* days
since the last refresh — instead of re-scanning the full window —
drops sustained cost by 1-2 orders of magnitude.

**Schema shape.** One row per `(entity, date)` with a non-zero
filter to avoid bloating the table with implicit zeros:

```sql
CREATE TABLE IF NOT EXISTS phase_x_daily (
    entity_id     TEXT NOT NULL,
    measure_date  TEXT NOT NULL,         -- ISO 'YYYY-MM-DD'
    value         INTEGER NOT NULL,      -- always >= 1; zero rows not stored
    PRIMARY KEY (entity_id, measure_date)
);
CREATE INDEX IF NOT EXISTS idx_phase_x_daily_date ON phase_x_daily(measure_date);
CREATE INDEX IF NOT EXISTS idx_phase_x_daily_id   ON phase_x_daily(entity_id);
```

**Mode selection.** Detect first-pull vs incremental from
`MAX(measure_date)`:

```python
last_row = conn.execute("SELECT MAX(measure_date) FROM phase_x_daily").fetchone()
last_date_str = last_row[0] if last_row else None
today = datetime.date.today()

if last_date_str is None:
    mode = "first-pull"
    window_start = today - datetime.timedelta(days=N)
elif (today - datetime.date.fromisoformat(last_date_str)).days > N:
    mode = "first-pull-after-gap"
    window_start = today - datetime.timedelta(days=N)
else:
    mode = "incremental"
    window_start = datetime.date.fromisoformat(last_date_str) + datetime.timedelta(days=1)

if window_start >= today:
    return {"skipped": True, "reason": "no new data since last refresh"}
```

**Aggregation.** Drive rolling-window outputs from the local table
via INSERT ... ON CONFLICT:

```python
cutoff_window = (today - datetime.timedelta(days=N)).isoformat()
conn.execute("""
    INSERT INTO consumer_table (entity_id, rolling_value, fetched_at, source)
    SELECT entity_id, COALESCE(SUM(value), 0), ?, 'phase-x-incremental'
    FROM phase_x_daily
    WHERE measure_date >= ?
    GROUP BY entity_id
    ON CONFLICT(entity_id) DO UPDATE SET
        rolling_value = excluded.rolling_value,
        fetched_at    = excluded.fetched_at,
        source        = excluded.source
""", (now, cutoff_window))
```

**GC.** Prune rows older than `RETAIN_DAYS` (5-day slack beyond the
window for boundary safety) on each refresh:

```python
retain_days = int(os.environ.get("PHASE_X_RETAIN_DAYS", str(N + 5)))
gc_cutoff = (today - datetime.timedelta(days=retain_days)).isoformat()
conn.execute("DELETE FROM phase_x_daily WHERE measure_date < ?", (gc_cutoff,))
```

**Force-rebootstrap escape hatch.** Operators suspecting cache
corruption need a one-shot way to wipe + re-bootstrap:

```python
if os.environ.get("PHASE_X_FORCE_FIRST_PULL"):
    conn.execute("DELETE FROM phase_x_daily")
    conn.commit()
```

Canonical implementation: `phase_p_pypi_downloads` + schema v26
`pypi_downloads_daily`. Storage profile: ~50–100k active entities
× N=90 days × ~50 bytes/row ≈ 225–450 MB steady state.

---

## 12. Dry-run preflight is free observability

Many paid APIs offer a free planning / quote / validation endpoint
that returns enough information to predict cost or behaviour without
billing for the real query. Use them aggressively — they're the
cheapest possible observability layer.

**Pattern.** Before any paid query:

1. Submit the dry-run / quote variant.
2. Print the predicted cost / latency / row count to stdout.
3. Compare against operator cap.
4. Abort with a clear `skipped` result if over budget; submit
   the real query otherwise.

**Provider examples** (verify current state before relying on these
— they shift over time):

- **BigQuery**: `QueryJobConfig(dry_run=True, use_query_cache=False)`
  returns `total_bytes_processed`. No quota consumed. Used in
  `phase_p_pypi_downloads`.
- **OSV.dev bulk**: REST endpoints return `Content-Length` on HEAD
  requests; useful for estimating download size before committing
  to a multi-GB pull.
- **GitHub GraphQL**: every query returns `rateLimit { cost
  remaining resetAt }` in the response — submit a tiny probe first
  to see remaining points before launching a fanout. Used in
  `_phase_k_github_graphql_batch`.
- **ecosyste.ms** + **deps.dev**: return result-count headers on
  list endpoints; use `?per_page=1` as a free probe before deciding
  how many pages to fetch.

**Rule of thumb.** If a provider charges per request or per byte,
look for the free preflight. If documentation doesn't mention one,
ask the provider — almost all volume-billed APIs ship one because
their own dashboards need it.

The dry-run output is also the right source-of-truth for the
quantitative claims in operator-facing docs (per § "Verify, Don't
Assume" in SKILL.md). Print + document the preflight value, and
the documentation never drifts from reality.

---

## 13. Phase P — cost model + operator playbook

(Absorbed from `atlas-phase-p-cost-model.md`, 2026-07-02 — the operator-facing
application of §§ 10–12 to the one volume-billed phase.)

This reference is the single source of truth for Phase P (PyPI
download counts) cost claims, cap behaviour, and recovery procedures.
It supersedes the "~30 GB / within 1 TB free tier" claims in the
v8.1.0 spec and earlier docs (off by ~1000×).

When updating cost numbers, derive them from a dry-run preflight or
live HTTP probe against the live source, not from memory or copied
napkin math. See § "Dry-run preflight" below for the procedure.

### Source backends (v8.16.0+)

Phase P routes through `PHASE_P_SOURCE`:

| Source | Default | Cost | Auth | Coverage | Latency | Backend |
|---|---|---|---|---|---|---|
| `clickhouse` | ✅ | **$0** | None | Full ~867 k projects | ~30 s | `_phase_p_clickhouse` — hash-bucketed pagination against `sql-clickhouse.clickhouse.com`'s pre-aggregated `pypi.pypi_downloads_per_day` mirror of the same BigQuery table |
| `bigquery` |   | $22–59 / refresh | ADC + billing | Full + raw event data | ~30–60 s | `_phase_p_bigquery` — v8.15.2 incremental refresh against the BigQuery source table directly |

**Default is `clickhouse`** since v8.16.0 — free, no auth, no billing
account required, same source data (ClickHouse Cloud mirrors the BQ
PyPI table daily). Operators who want raw event data (per-installer,
per-platform breakdowns) opt in to BigQuery via `PHASE_P_SOURCE=bigquery`.

The rest of this document covers both backends. § "ClickHouse (free,
default)" below describes the default path. § "Dry-run preflight"
onwards covers BigQuery-specific cap mechanics that don't apply to
the ClickHouse path.

---

### ClickHouse (free, default)

`pypi.pypi_downloads_per_day` is a pre-aggregated materialized view
hosted by ClickHouse Cloud at
`https://sql-clickhouse.clickhouse.com/?user=play`. Schema:

```
date         Date
project      String
count        Int64
```

The view is mirrored daily from
`bigquery-public-data.pypi.file_downloads` by the ClickHouse team.
Same source data, same canonical PyPI download counts.

#### Coverage architecture: top-N by 90-day downloads

The `play` user has two binding constraints (verified 2026-06-12):

1. **Response row cap**: aggregated query responses truncate at
   **~1,000 rows**. Verified via `LIMIT 200000` returning 65k for raw
   queries but `GROUP BY project` queries truncating at ~1,000.
2. **Sustained-burst rate limit**: bucket-paginated full-coverage
   refresh (1,500 buckets at 4 concurrent workers) triggers HTTP 500s
   from ~95% of buckets, then exponential backoff retries → effective
   ~1 bucket/sec total throughput → 25+ minute wall-clock with 90%
   retry-driven cost.

Given these caps, v8.16.0 ships as a **single top-N query**:

```sql
SELECT project,
       toUInt64(sumIf(count, date >= today() - 30)) AS d30,
       toUInt64(sum(count))                          AS d90
FROM pypi.pypi_downloads_per_day
WHERE date >= today() - 90 AND date < today()
GROUP BY project
ORDER BY d90 DESC LIMIT 1000
FORMAT JSONEachRow
```

That's the ranking signal Phase P's consumers actually need —
`conda_forge_readiness` ranking and `pypi-only-candidates` sort care
about the **most-downloaded** packages, not the long tail. Top-1000
covers everything from boto3 (2.5B downloads/yr) to mid-tier popular
packages.

#### Verified benchmarks (2026-06-12, live production atlas)

| Operation | Wall-clock | Wire transfer | Cost |
|---|---|---|---|
| Top-1000 query | **~3.8 s** end-to-end (query + parse + upsert) | ~80 KB JSON | **$0** |
| Top-100 query | ~2 s | ~10 KB | $0 |
| Total table rows | 1,009,637,598 | — | — |
| Date range | 2016-01-22 → today | — | — |
| pypi_intelligence rows upserted | 1,000 (production atlas, full E2E) | — | — |

#### Why we don't do full-coverage on ClickHouse

We explored 1,500-bucket pagination via `cityHash64(project) % N`.
Real-world wall-clock at 4 parallel workers:
- 100 buckets: 417 sec (~7 min)
- 300 buckets: 1,239 sec (~21 min)
- 1,500 buckets projected: ~25 min, **assuming retries succeed**

With sustained 4-parallel burst, all buckets fail their HTTP requests
(verified: 60/60 buckets exhausted 5-retry budget on a 60-bucket
test). The `play` user's rate limiter is too aggressive for bulk
pagination. Full-coverage from a free source is **not available** on
ClickHouse Play. Operators wanting it must use BigQuery (paid) or
wait for the BigQuery free tier monthly reset.

#### Tunables (ClickHouse backend)

| Env var | Default | Purpose |
|---|---|---|
| `PHASE_P_SOURCE` | `clickhouse` | Backend selector; `bigquery` opts into the paid path |
| `PHASE_P_CH_BASE_URL` | `https://sql-clickhouse.clickhouse.com/?user=play` | Endpoint override (enterprise mirror, fork) |
| `PHASE_P_CH_LIMIT` | 1000 | Top-N projects to fetch (`ORDER BY d90 DESC LIMIT N`). Raising beyond 1000 is a no-op — ClickHouse Play caps aggregated responses at ~1,000 rows. |
| `PHASE_P_CH_TIMEOUT_S` | 60 | HTTP timeout (s) |

#### Trade-offs vs. BigQuery

| Property | ClickHouse | BigQuery |
|---|---|---|
| Cost | $0 | $22–59 / refresh |
| Auth | None | ADC + billing |
| Refresh time | ~30 s | ~30–60 s |
| Data freshness | Daily (~24 h lag) | Daily (~24 h lag) |
| Raw events | ❌ aggregated only | ✅ per-row events |
| Per-installer / per-platform | ❌ | ✅ via raw events |
| Single point of failure | Yes (ClickHouse Inc) | Yes (Google) |

If raw event data isn't needed (which is the case for Phase P's
current consumers — `conda_forge_readiness` ranking, `pypi-only-candidates`
sort), ClickHouse is strictly better.

#### Fallback procedure

If ClickHouse becomes unavailable (host change, scope reduction, etc.):

```bash
PHASE_P_SOURCE=bigquery \
PHASE_P_BQ_PROJECT=<your-gcp-project> \
PHASE_P_MAX_COST_USD=25 \
pixi run -e local-recipes bootstrap-data --profile admin
```

That falls back to the v8.15.2 BigQuery incremental path. Same data,
costs money. See § "BigQuery (paid)" below for full BQ docs.

---

### BigQuery (paid)

The BigQuery backend is now **opt-in** via `PHASE_P_SOURCE=bigquery`.
The rest of this document — TL;DR table, cap behaviour, dry-run
preflight, modes, operator runbook — describes the BigQuery path.

Use BigQuery instead of ClickHouse only when you genuinely need:
- Raw event data (per-installer, per-platform, per-Python-minor)
- Independence from ClickHouse Cloud's continued hosting
- The v8.15.2 `pypi_downloads_daily` incremental cache pattern (for
  daily/weekly/monthly cadence tuning)

For most consumer use cases (`conda_forge_readiness` ranking,
`pypi-only-candidates` sorting, `pypi-intelligence` reports) the
ClickHouse backend's pre-aggregated `(date, project, count)` data is
sufficient and free.

---

### TL;DR (BigQuery backend)

| Mode | Window scanned | Cost estimate (verified 2026-06-12) | Default cap | Cap fits? |
|---|---|---|---|---|
| first-pull (`pypi_downloads_daily` empty) | trailing 90 d (~9.5 TB) | **~$59** at $6.25/TB | $100 (`PHASE_P_MAX_COST_FIRST_PULL_USD`) | ✅ |
| incremental refresh — monthly cadence | last ~30 d (~3.5 TB) | **~$22** | $10 (`PHASE_P_MAX_COST_USD`) | ❌ **must raise to ~$25** |
| incremental refresh — weekly cadence | last ~7 d (~0.86 TB) | **~$5.37** | $10 | ✅ |
| incremental refresh — daily cadence | last 1 d (~140 GB) | **~$0.88** | $10 | ✅ comfortably |
| gap > 90 days since last refresh | trailing 90 d (reverts to first-pull) | ~$59 | $100 | ✅ |
| no new partitions since last run | 0 | $0 (BQ never queried) | n/a | ✅ |

All caps are operator-overridable via the env vars listed in
§ "Tunables" below. Worst case under any combination is a
`maximum_bytes_billed`-aborted job that bills $0.

**Verification provenance**: numbers above measured 2026-06-12 via
the dry-run preflight procedure in § "Dry-run preflight" below.
Table size verified at 1.14 PB. Re-run that procedure to refresh
the table when significant time has passed — the BigQuery PyPI table
grows ~30% YoY (verified empirically, not from a napkin number).

**Critical: the default $10 refresh cap does NOT fit monthly cadence
at current table size.** Two options:
- (a) Use **weekly cadence** (`PHASE_P_TTL_DAYS=7`) — fits the $10 cap
  with headroom. Annual cost ~$280.
- (b) Use **monthly cadence with raised cap** (`PHASE_P_MAX_COST_USD=25
  PHASE_P_TTL_DAYS=30`) — operator-explicit opt-in. Annual cost ~$260.
- (c) Use **daily cadence** (`PHASE_P_TTL_DAYS=1`) — fits the $10 cap
  with massive headroom. Annual cost ~$320 but ~365 small jobs/year
  instead of ~12 medium jobs.

The pre-v8.15.0 single-shot architecture (v8.1.0–v8.14.3) re-scanned
the full 90-day window on every refresh: 12 monthly refreshes × $59 =
**~$710/year**. The v8.15.0 incremental architecture saves on the
re-scan part — monthly refreshes drop to ~$22/run, saving $37/run
or ~$440/year. That's the real architectural win.

---

### Why the v8.1.0 number was wrong (and v8.14.3 + v8.15.0 were also wrong)

**v8.1.0**: the spec claimed "~30 GB scanned per query, within the
free tier monthly budget". A ~2016-era napkin number copied through
the spec, code docstring, CHANGELOG, three reference docs, and the
quickref cheatsheet without re-verification. Live verification on
2026-06-12 showed real cost was ~$59 per first-pull run — off by
~3,000×, and a 2026-06-12 operator invoice of $500+ for ~3 Phase P
runs surfaced the discrepancy.

**v8.14.3 hot-patch + v8.15.0 incremental architecture**: the skill
author corrected the spec but introduced *two new errors*, both
caught by the same retro action item (L1) that mandated live BQ
verification:

1. **Numerical underestimate (off by ~3–4×).** v8.14.3's cost-model
   doc and v8.15.0's spec claimed first-pull = "~2.5–4 TB / ~$15–25"
   and monthly refresh = "~$0.30–2". The verified 2026-06-12 reality:
   first-pull ~9.5 TB / ~$59 and monthly refresh ~3.5 TB / ~$22. The
   skill author estimated based on rough table-growth math without
   running the dry-run preflight that v8.14.3 itself shipped. **Exact
   same failure mode as the v8.1.0 author.**
2. **SQL bug (would have prevented any real run from working).**
   v8.14.3 and v8.15.0 switched the partition filter from `WHERE
   timestamp >= TIMESTAMP_SUB(...)` to `WHERE _PARTITIONDATE >= DATE
   '...'`. The intent was to use literal dates for guaranteed prune-
   safety. The bug: `_PARTITIONDATE` is a pseudo-column that only
   exists on **ingestion-time-partitioned** tables. This table is
   **column-partitioned** on the `timestamp` column (verified via
   `bq show --schema bigquery-public-data:pypi.file_downloads` →
   `TimePartitioning(field='timestamp', type_='DAY')`). The literal
   form raised `Unrecognized name: _PARTITIONDATE` at submit time;
   no real run could ever have succeeded against v8.14.3 / v8.15.0.

**v8.15.2 hot-fix** corrects both: SQL uses `WHERE timestamp >=
TIMESTAMP '...' AND timestamp < TIMESTAMP '...'` literals (the v8.1.0
form, but with literal bounds instead of `TIMESTAMP_SUB(CURRENT_TIMESTAMP(),
INTERVAL)`), and `DATE(timestamp)` for the per-day GROUP BY. Cost
numbers throughout this doc are verified-2026-06-12 via the dry-run
preflight in § "Dry-run preflight" below.

**Empirical 2026-06-12 baseline:**

- Table size: **1.14 PB** (2,904 billion rows), partitioned by the
  `timestamp` column with DAY granularity, clustered on `project`.
- 90-day query at `file.project + DATE(timestamp)` projection:
  **~9.5 TB scanned**, ~$59 at $6.25/TB.
- 30-day query: **~3.5 TB**, ~$22.
- 7-day query: **~860 GB**, ~$5.37.
- 1-day query: **~140 GB**, ~$0.88.

**Discipline going forward** (per SKILL.md § "Verify, Don't Assume"
4th bullet — added in v8.15.1 and validated by this very retro
action): cost claims in spec / code / docs MUST be paired with a
dry-run preflight output as the source of truth, dated. Napkin
numbers without provenance — even a careful skill author's rough math —
are bugs. The cross-skill auto-memory rule
`feedback_bmad_verifies_spec_cost_claims.md` requires future BMAD
agents implementing CFE-area specs to re-verify quantitative claims
at intake against the live tables.

The v8.15.1 retro's R1+R2+R3 deltas predicted exactly this class of
failure; the very next session caught it. **The principle works.**

---

### Dry-run preflight

BigQuery returns `total_bytes_processed` for free via a dry-run job
(no quota consumed, no cost billed). Phase P uses this internally
before every real query and aborts if the estimate exceeds the
operator cap. Operators can run the same preflight manually to
verify cost expectations against the current table:

```bash
# Resolve the dates Phase P will use today.
today=$(date -u +%Y-%m-%d)
d90=$(date -u -d '90 days ago' +%Y-%m-%d)

# Dry-run only; no quota consumed.
pixi run -e gcloud bq query --dry_run --use_legacy_sql=false \
  --project_id=<your-gcp-project-id> "$(cat <<EOF
SELECT
    REGEXP_REPLACE(LOWER(file.project), r'[-_.]+', '-') AS pypi_name,
    DATE(timestamp) AS download_date,
    COUNT(*) AS downloads
FROM \`bigquery-public-data.pypi.file_downloads\`
WHERE timestamp >= TIMESTAMP '$d90 00:00:00 UTC'
  AND timestamp <  TIMESTAMP '$today 00:00:00 UTC'
GROUP BY pypi_name, download_date
EOF
)"
```

**Why these date forms?** This table is column-partitioned on the
`timestamp` column (verified via `bq show --schema
bigquery-public-data:pypi.file_downloads` →
`TimePartitioning(field='timestamp', type_='DAY')`). `_PARTITIONDATE`
is *not* a valid pseudo-column on column-partitioned tables — using
it raises `Unrecognized name: _PARTITIONDATE`. The correct form
filters on `timestamp` directly with `TIMESTAMP` literals (which the
planner can prune against), and projects `DATE(timestamp)` for the
per-day GROUP BY. v8.14.3 and v8.15.0 shipped with the broken
`_PARTITIONDATE` form (verified 2026-06-12); v8.15.2 hot-fixes.

`bq query --dry_run` prints `Total bytes processed`. Divide by
`1e12` and multiply by `$6.25` (US on-demand) to get the cost
estimate in USD. If you're on a non-US region with different
on-demand pricing, override Phase P's `PHASE_P_USD_PER_TB`.

When Phase P runs it prints the same preflight output:

```
  Phase P: PyPI download counts via BigQuery (incremental v8.15.0)
  mode=incremental; window=[2026-05-13, 2026-06-12) (30 d);
  dry-run: ~280 GB scan, est ~$1.75 (cap $10.00)
  submitting query against bigquery-public-data.pypi.file_downloads
    (maximum_bytes_billed=1,600,000,000,000, job_timeout_ms=600000)
```

The two `est` and `cap` numbers are the audit trail. If `est`
exceeds `cap` the run aborts and prints the same numbers in the
skip reason.

---

### Hard cap behaviour (`maximum_bytes_billed`)

The generic mechanics are § 10 (a) above: `maximum_bytes_billed` is a
server-side hard ceiling — if actual processed bytes would exceed it,
BigQuery aborts with HTTP 400 `Query exceeded limit for bytes billed`
and **bills $0**. Phase-P specifics: the dry-run preflight is a *softer*
gate — it aborts the run *before* submitting the real job, with a
printable estimate; the real query also carries `maximum_bytes_billed`
as defence-in-depth in case the planner re-estimates upward between
dry-run and live run. Both gates respect the same operator-set cap.
Tuning is one env var per mode (refresh vs first-pull).
---

### Wall-clock cap (`job_timeout_ms`)

`bigquery.QueryJobConfig(job_timeout_ms=N)` prevents zombie jobs from
accumulating slot time on flat-rate billing accounts. On-demand
billing accounts don't pay for slot time, but the timeout also
prevents pathological hung queries from running indefinitely. Default
10 minutes is generous — real queries complete in 30–60 s.

Override via `PHASE_P_JOB_TIMEOUT_MS` (milliseconds). Set higher on
slow regions where a first-pull might need 5+ minutes of wall-clock
to complete the GROUP BY.

---

### Tunables

| Env var | Default | Purpose |
|---|---|---|
| `PHASE_P_DISABLED` | (unset) | "1" → skip Phase P unconditionally |
| `PHASE_P_ENABLED` | (unset) | "1" required for opt-in; admin profile sets this automatically |
| `PHASE_P_BQ_PROJECT` | (unset) | GCP project override; defaults to ADC project |
| `PHASE_P_TTL_DAYS` | 30 | Driver-side cadence gate (monthly default) |
| `PHASE_P_RETAIN_DAYS` | 95 | GC threshold for `pypi_downloads_daily` (5d slack beyond 90d window) |
| `PHASE_P_MAX_COST_USD` | 10 | Refresh-mode cap (USD); BQ aborts above |
| `PHASE_P_MAX_COST_FIRST_PULL_USD` | 100 | First-pull cap (USD) |
| `PHASE_P_JOB_TIMEOUT_MS` | 600000 | Wall-clock cap on the real query (10 min) |
| `PHASE_P_USD_PER_TB` | 6.25 | BQ on-demand price; override for non-US regions |
| `PHASE_P_FORCE_FIRST_PULL` | (unset) | "1" wipes `pypi_downloads_daily` + forces 90-day re-bootstrap |
| `PHASE_P_BQ_WINDOW_DAYS` | DEPRECATED | Logs warning if set; ignored (v8.15.0) |

#### Tuning recipes

**Tighter refresh discipline ($5 instead of $10):**

```bash
PHASE_P_MAX_COST_USD=5 pixi run -e local-recipes bootstrap-data --profile admin
```

**One-off catch-up after a missed cycle (60 days of gap, want $30):**

```bash
PHASE_P_MAX_COST_USD=30 pixi run -e local-recipes bootstrap-data --profile admin
```

**Force a clean re-bootstrap (suspect daily-table corruption):**

```bash
PHASE_P_FORCE_FIRST_PULL=1 pixi run -e local-recipes bootstrap-data --profile admin
```

**Tighter timeout on a flat-rate slot account (5 min instead of 10):**

```bash
PHASE_P_JOB_TIMEOUT_MS=300000 pixi run -e local-recipes bootstrap-data --profile admin
```

**Override for an EU multi-region project ($7.25/TB):**

```bash
PHASE_P_USD_PER_TB=7.25 pixi run -e local-recipes bootstrap-data --profile admin
```

---

### Modes — decision tree

```
                    pypi_downloads_daily empty?
                    /                          \
                 YES                            NO
                  ↓                              ↓
              first-pull            MAX(download_date) gap > 90d?
              (90-day window)        /                            \
              cap = $100           YES                            NO
                                    ↓                              ↓
                            first-pull-after-gap         incremental
                            (90-day window)              (window = last_date+1 → today)
                            cap = $100                   cap = $10
                            + warning logged             ↓
                                                      window empty?
                                                      /          \
                                                    YES          NO
                                                     ↓            ↓
                                                  no-op       submit query
                                                  (no BQ      → dry-run preflight
                                                   traffic)   → if est < cap, run
                                                              → else abort with reason
```

---

### Operator runbook

#### Routine refresh — monthly cadence (recommended default)

Monthly cadence at current table size costs ~$22/refresh, which
exceeds the $10 default cap. **The default config will dry-run-abort
without an explicit cap override.** This is the deliberate operator-
respect default per the user's $10/refresh tolerance — Phase P opts
out of spending until the operator explicitly approves a higher
budget. Recommended config:

```bash
# Monthly cadence with cap raised to match the empirical cost.
# The $25 cap gives ~$3 of headroom for table growth between refreshes.
export PHASE_P_MAX_COST_USD=25
export PHASE_P_TTL_DAYS=30   # explicit; matches the default

pixi run -e local-recipes bootstrap-data --profile admin
```

Admin profile sets `PHASE_P_ENABLED=1`. Phase P:
1. Detects mode = `incremental` from `pypi_downloads_daily.MAX(download_date)`.
2. Dry-runs the query for the new days since last refresh (~30 d).
3. If estimate ≤ $25, submits real query with `maximum_bytes_billed`.
4. INSERTs new rows into `pypi_downloads_daily`.
5. Recomputes `pypi_intelligence.downloads_30d/90d` via local SQL aggregation.
6. GCs rows older than 95 days.

Typical wall-clock: 60–120 s per monthly refresh.
Annual cost: ~$322 (12 × ~$22 refresh + $59 first-pull).

#### Routine refresh — weekly cadence (alternative; fits default cap)

If you prefer to keep the $10 default cap unchanged, switch to weekly
cadence — fits the cap with ~$5/run of headroom:

```bash
export PHASE_P_TTL_DAYS=7
pixi run -e local-recipes bootstrap-data --profile admin
```

Annual cost: ~$338 (52 × ~$5.37 + $59 first-pull). Roughly comparable
to monthly; primary trade-off is data freshness — weekly's `downloads_30d`
window is at most 7 days stale; monthly's is at most 30 days stale.
For `conda_forge_readiness` ranking purposes, either is fine.

#### Routine refresh — daily cadence (alternative; cheapest per-run)

Daily cadence costs ~$0.88/run. Fits the $10 default cap with massive
headroom. Best choice if you want fresh data and don't mind 365 small
jobs/year:

```bash
export PHASE_P_TTL_DAYS=1
pixi run -e local-recipes bootstrap-data --profile admin
```

Annual cost: ~$380 (365 × ~$0.88 + $59 first-pull). Most expensive
total but offers a 1-day-stale-max window.

#### Cost-spike investigation

If a Phase P run reports an unexpected cost:

1. Inspect the printed `dry-run: ~N GB scan, est ~$X` line — the
   estimate at submission time. Compare against the table size you
   expect.
2. Check `bq query --dry_run` from the operator runbook above for an
   independent estimate.
3. If estimates differ between Phase P and the manual `bq` command,
   one of the input dates is off — verify the system clock and
   `PHASE_P_FORCE_FIRST_PULL` state.
4. If estimates agree and seem high, the partition-pruning may have
   degraded. Re-run with `bq query --dry_run` and inspect the table
   sizes — `bq show --schema bigquery-public-data:pypi.file_downloads`
   for current partition statistics.

#### Recovery from suspected daily-table corruption

```bash
PHASE_P_FORCE_FIRST_PULL=1 pixi run -e local-recipes bootstrap-data --profile admin
```

Costs one first-pull ($15–25 typical, capped at $100). Resets the
table to a clean trailing-90-day state.

#### Air-gap operator (no BQ access)

Disable Phase P entirely; the consumer profile already does this:

```bash
pixi run -e local-recipes bootstrap-data --profile consumer
```

Existing `pypi_intelligence.downloads_30d/90d` data (last populated
when Phase P last ran) remains available for read-side CLIs and the
MCP tool. The `downloads_fetched_at` column lets consumers detect
staleness independently of the data being air-gapped.

---

### Verification against alternative sources

Phase P uses `bigquery-public-data.pypi.file_downloads` as canonical.
Operators wanting an independent cross-check have two options:

#### ClickHouse `clickpy` public dataset

The ClickHouse Cloud team mirrors the BigQuery dataset to a free
public ClickHouse instance. Query via HTTPS SQL:

```bash
curl 'https://play.clickhouse.com/?user=play' --data-binary "$(cat <<'EOF'
SELECT
    project,
    countIf(date >= today() - 30) AS downloads_30d,
    countIf(date >= today() - 90) AS downloads_90d
FROM pypi.pypi_downloads
WHERE date >= today() - 90
  AND project IN ('numpy', 'pandas', 'rich')
GROUP BY project
ORDER BY downloads_90d DESC
EOF
)"
```

Reasonable for verification queries on a small slice of packages.
Not a primary because operator-trust depends on a third party we
don't control. Note: dataset name and access details may drift —
verify at https://clickpy.clickhouse.com/ before using.

#### ecosyste.ms PyPI bulk export

`https://packages.ecosyste.ms/api/v1/registries/pypi.org` exposes
per-package metadata including download counts. Bulk dumps at
`https://packages.ecosyste.ms/open-data` carry monthly snapshots.

Reasonable as a v8.16.0+ fallback path for operators without BQ
credentials. `downloads_period` field semantics need verification
before substituting into Phase P's pipeline.

#### Manual `bq` CLI verification

For a single package's exact daily counts:

```bash
pixi run -e gcloud bq query --use_legacy_sql=false \
  --project_id=<your-gcp-project-id> "$(cat <<'EOF'
SELECT DATE(timestamp) AS day, COUNT(*) AS downloads
FROM `bigquery-public-data.pypi.file_downloads`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND file.project = 'numpy'
GROUP BY day
ORDER BY day DESC
EOF
)"
```

Costs ~$0.20 for a 30-day single-project query. Useful for
spot-checking the SQL aggregation against Phase P's bulk result.

---

### Storage profile

`pypi_downloads_daily` adds steady-state DB storage:

- Only rows where `downloads >= 1` are stored (zero-count days are
  implicit absence).
- ~50k–100k packages have any daily activity (the long tail is
  inactive at any given moment).
- × 90 days retention → ~5M–9M rows × ~50 bytes/row = **~225–450 MB
  steady state**.
- 95-day retention (`PHASE_P_RETAIN_DAYS` default) gives 5-day slack
  beyond the 90d window for boundary safety.

DB size delta is significant relative to a typical `cf_atlas.db`
(~200–500 MB pre-v8.15.0). Tradeoff: ~225 MB of storage in exchange
for ~$200/year saved on BQ queries.

To shrink at the cost of losing the 90-day window's precision:

```bash
PHASE_P_RETAIN_DAYS=30 pixi run -e local-recipes bootstrap-data --profile admin
```

The next aggregation cycle will produce `downloads_90d` values that
match `downloads_30d` (since only 30 days of data survive). This
trade-off is operator-tunable, not enforced.

---

### Annual cost projection (verified 2026-06-12)

| Architecture | Per-refresh | Annual | Notes |
|---|---|---|---|
| Pre-v8.14.3 (no caps, 90-d single-shot BQ) | ~$59 | ~$710 (12 monthly) | The cost that triggered the 2026-06-12 invoice surprise |
| v8.14.3 hot-patch (caps, but BQ SQL broken) | $0 — query fails | $0 invoice; $0 data | Cost-cap aborts work; but the `_PARTITIONDATE` SQL bug means no real data ever lands |
| v8.15.0 incremental (BQ SQL still broken) | $0 — query fails | $0 invoice; $0 data | Same bug; tests passed because they grep source, never hit live BQ |
| v8.15.2 BQ incremental — daily cadence | ~$0.88 | ~$320 (365 × $0.88) + $59 first-pull | Fits $10 cap with massive headroom |
| v8.15.2 BQ incremental — weekly cadence | ~$5.37 | ~$280 (52 × $5.37) + $59 first-pull | Fits $10 cap |
| v8.15.2 BQ incremental — monthly cadence | ~$21.92 | ~$263 (12 × $21.92) + $59 first-pull | Exceeds $10 cap; operator must raise to ~$25 |
| **v8.16.0 ClickHouse — any cadence** | **$0** | **$0** | Free public mirror; same source data; ~30 s wall-clock; default since v8.16.0 |

**The architectural value of v8.15.x is real but smaller than the
v8.15.0 doc claimed.** Pre-v8.15.x re-scanned the full 90-day window
every refresh ($59/run). v8.15.x's incremental refresh only scans the
new days since the previous run — saving ~$37/run at monthly cadence,
or ~$54/run at weekly cadence. Annual savings vs. the pre-v8.15.x
architecture: ~$440 at monthly cadence, ~$640 at weekly cadence.

**The pre-fix $30/year claim was wrong on two counts**: (a) the per-
refresh cost was off by 20×; (b) the actual savings vs. single-shot
were calculated against a wrong baseline. The verified numbers above
supersede.

The v8.15.2 hot-fix (SQL correction) is what makes any of the above
real — without it, no architecture works. v8.14.3's caps are still
the safety net.

---

### See also

- `docs/specs/atlas-phase-p-incremental.md` — the v8.15.0 spec.
- `docs/specs/atlas-pypi-intelligence.md` — v8.1.0 predecessor; carries
  a top-of-document erratum banner pointing here.
- `reference/atlas-phases-overview.md` § Phase P — phase-indexed
  catalog entry.
- `quickref/commands-cheatsheet.md` § Phase P run — operator quickref.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.14.3 + v8.15.0
  entries — shipping notes.

---

## Cross-references

- `_http.py` — shared resolvers, auth, fetch-with-fallback, atomic-write helpers.
- `conda_forge_atlas.py` — phase implementations; consult `_phase_k_github_graphql_batch` and `phase_l_extra_registries` for canonical examples of patterns §2 and §4.
- `phase_state` SQLite table — checkpoint storage for §8.
- [`atlas-phases-overview.md`](atlas-phases-overview.md) — separate concern: what the atlas surfaces (Part A: persona × goal × CLI) and what each phase does + writes (Part B), not how it computes it.
- [`../guides/atlas-operations.md`](../guides/atlas-operations.md) — how to run it: profiles, cadence, cron, recovery.
