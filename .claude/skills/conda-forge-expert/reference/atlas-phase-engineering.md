# Atlas Phase Engineering

Patterns and constraints for writing or refactoring `conda_forge_atlas.py`
pipeline phases (B → N) and their per-row workers. These are *engineering*
concerns (rate limits, resumability, RAM, atomic IO) — distinct from the
*intelligence* the atlas surfaces, which lives in
[`actionable-intelligence-catalog.md`](actionable-intelligence-catalog.md).

This doc collects the lessons from the 2026-05-12 atlas hardening pass
(v7.8.0). Treat it as the default rule book for any new phase or any
refactor of an existing phase that touches HTTP fanout, batch writes, or
cache management.

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

## Cross-references

- `_http.py` — shared resolvers, auth, fetch-with-fallback, atomic-write helpers.
- `conda_forge_atlas.py` — phase implementations; consult `_phase_k_github_graphql_batch` and `phase_l_extra_registries` for canonical examples of patterns §2 and §4.
- `phase_state` SQLite table — checkpoint storage for §8.
- `actionable-intelligence-catalog.md` — separate concern: what the atlas surfaces, not how it computes it.
