# Tech Spec: Atlas Phase K — sustained-rate cron runner (secondary rate-limit fix)

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~5 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-k-cron-runner.md
> ```
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this brief MUST
> invoke the `conda-forge-expert` skill before touching atlas code.
> Per Rule 2, the effort closes with a CFE-skill retrospective and a
> `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (no PRD/architecture phase — single-phase operational fix) |
| Scope | Replace Phase K's 8-worker burst with sustained-rate scheduler that respects GitHub's secondary rate limit. Preserve the current behavior as an opt-in via `PHASE_K_AGGRESSIVE=1` for tight-time-budget operators. |
| Out of scope | Phase L (extra registries) — different rate-limit profiles, not in this ship; Phase N (live GitHub) — already runs at a slow per-batch cadence; Phase H (PyPI) — no rate-limit issues. |
| Predecessor | v8.16.5 session retro carryover P2; auto-memory `project_phase_k_secondary_rate_limit.md` (2026-05-12 incident) |
| Successor | none planned |
| Created | 2026-06-13 |

---

## Background and Context

### The empirical problem

On 2026-05-12, a single `atlas-phase K` run with ~4,400 net-new VCS rows produced **15% HTTP 403s (659/4,400)** against authenticated `api.github.com/repos/<o>/<r>/releases/latest`. Primary token quota was barely consumed (32/5,000 used at the same time). The 403s are **GitHub's secondary rate limit** — concurrent-request / burst pattern — which:

- Does NOT surface in `/rate_limit` endpoint output
- Is enforced separately from the 5,000/hour primary quota
- Triggers on sustained high-concurrency or burst patterns, not on total volume
- Penalizes the *next several seconds* of requests, not just the offending one

### What Phase K does today

`_fetch_release_or_tag` in `scripts/conda_forge_atlas.py` runs an 8-worker `ThreadPoolExecutor` against the GitHub REST API. Retries 403/429 with `2**attempt + 2`-second backoff. The retries succeed for transient cases but stretch wall-clock significantly on sustained bursts; rows that don't recover land as `last_error='HTTP 403'` in `upstream_versions`.

Empirically observed (2026-05-12):
- 8 workers × ~9 req/s nominal → ~70 req/s sustained burst peak
- Total Phase K wall-clock: ~30 min for 4,400 net-new rows
- 15% (659) rows failed with `last_error='HTTP 403'` after retry exhaustion
- Primary quota usage: 32/5,000 (~0.6% of available)

The 8-worker burst is the bottleneck — not quota. The pool's aggressive concurrency exceeds GitHub's tolerance for secondary-limit detection.

### What's been ruled out

- **Raising primary quota** — irrelevant; the bottleneck is concurrency, not volume.
- **Switching to GitHub App tokens** — App tokens get the same secondary limit; this isn't a token-tier issue.
- **Increasing per-worker backoff** — current `2**attempt + 2` already retries 4 times for transient cases. The issue is sustained pressure during the next request batch.
- **Dropping to a single worker** — would solve the burst problem but stretches wall-clock to ~75 min for 4,400 rows. Acceptable trade-off but a global drop would also affect incremental TTL-skip runs (which currently are fast). Need a tunable.

### What's available to leverage

- **`_fetch_release_or_tag` already isolates the per-row fetch.** No refactor required to swap the dispatcher.
- **`PHASE_K_TTL_DAYS=7` already filters to expired-or-new rows** — incremental runs typically touch <100 rows and don't trigger the burst.
- **`upstream_versions.last_error` already records the 403 outcome** — recoverable rows can be retried on next Phase K run via TTL bypass.
- **Phase F's existing `PHASE_F_CONCURRENCY` env var pattern** — established convention for operator-tunable per-phase concurrency.

---

## Goals

- **G1.** Reduce sustained Phase K 403 rate from ~15% to <1% on full-channel fanouts.
- **G2.** Preserve incremental (TTL-skip) Phase K speed — runs with <100 new rows should finish in roughly the same time as today.
- **G3.** Operator escape hatch — `PHASE_K_AGGRESSIVE=1` opt-in restores current 8-worker behavior for operators who prefer faster wall-clock at the cost of 403 churn.
- **G4.** No new schema. No new tables. No new persisted state.
- **G5.** Honors existing `PHASE_K_TTL_DAYS=7` semantics; no behavior change to row-eligibility logic.

---

## Non-Goals

- **NG1.** No cross-process scheduling or daemon — this is a single-process per-phase fix; no `cron` daemon, no separate worker process.
- **NG2.** No retry strategy changes for Phase L / Phase H / Phase N — those phases have different rate-limit profiles and ship as-is.
- **NG3.** No GitHub-only optimization that breaks GitLab + Codeberg branches — the same scheduler must work for all three VCS hosts (though only GitHub has the secondary-rate-limit issue at scale; GitLab + Codeberg fan-outs are smaller).
- **NG4.** No dynamic rate detection from response headers — GitHub's `X-RateLimit-Remaining` reports primary quota, not secondary. We use a hard-coded sustained-rate target instead.
- **NG5.** No retry strategy for already-403'd rows from prior runs — the existing TTL bypass on `last_error != NULL` already handles this.

---

## Lifecycle Expectations

- **One-time wall-clock impact**: cold full-channel Phase K grows from ~30 min → ~60-75 min (matches the observed single-worker rate target).
- **Steady-state cost**: incremental runs (<100 new rows) finish in roughly the same time as today — they don't trigger the burst pattern anyway.
- **Per-run quota cost**: primary quota usage unchanged (Phase K never exceeds ~5% of primary quota).
- **Recovery**: any 403 that does occur lands in `upstream_versions.last_error`; next Phase K run picks it up via existing TTL bypass on `last_error != NULL`.

---

## User Stories

### Story 1 — Replace the worker pool with a sustained-rate scheduler

In `scripts/conda_forge_atlas.py` `_fetch_release_or_tag` (or the enclosing Phase K driver), replace the `ThreadPoolExecutor(max_workers=8)` with a single-token-bucket scheduler that:

- Issues at most `PHASE_K_REQUESTS_PER_SECOND` requests per second (default `3.0` — well under GitHub's secondary-limit threshold; empirically safe for sustained bursts).
- Uses a **single worker** in non-aggressive mode (or `PHASE_K_CONCURRENCY` workers if set, but capped at the rate-per-second budget).
- Honors a token-bucket pattern: tokens replenish at `RPS` rate; each request consumes one token; when tokens are depleted, the scheduler sleeps until the next token is available.
- Continues to handle GitLab + Codeberg with the same scheduler (no host-specific carve-out — the rate is well within all three providers' limits).

Implementation: a small `_RateLimitedScheduler` class in `scripts/conda_forge_atlas.py` (or a new helper file if it grows). ~50 LOC.

### Story 2 — `PHASE_K_AGGRESSIVE=1` opt-in restoring current behavior

For operators who prefer the 8-worker burst (faster wall-clock at the cost of higher 403 churn), `PHASE_K_AGGRESSIVE=1` switches back to the current `ThreadPoolExecutor(max_workers=8)` path. Document the trade-off in the env-var docs + reference doc.

The default (`PHASE_K_AGGRESSIVE` unset) is the new sustained-rate scheduler.

### Story 3 — Surface new env vars in `bootstrap_data.py` docstring

`scripts/bootstrap_data.py` already documents per-step timeouts. Extend the docstring with:

```
  PHASE_K_REQUESTS_PER_SECOND     default 3.0  (sustained-rate target;
                                                 well below GitHub's
                                                 secondary-rate-limit
                                                 threshold)
  PHASE_K_AGGRESSIVE              unset (=use sustained-rate scheduler);
                                  =1 to restore the previous 8-worker
                                  burst behavior (faster wall-clock,
                                  ~15% 403 rate on full-channel fanouts)
```

Update the `cf_atlas` timeout comment at `_DEFAULT_TIMEOUTS` to note Phase K's expected ~60-75 min wall-clock under the new default (the v8.16.6 14,400s = 4h cap still has slack).

### Story 4 — Tests

Add `tests/unit/test_phase_k_scheduler.py`:

- **TestRateLimitedScheduler**:
  - 3.0 RPS bucket: 30 requests take ≥10 s under the scheduler (within 10% tolerance).
  - Token-bucket math: bucket starts at full capacity; depletes correctly; replenishes at RPS rate.
  - `PHASE_K_REQUESTS_PER_SECOND` env-var override is honored.
- **TestPhaseKDispatch**:
  - Default mode: uses `_RateLimitedScheduler` (verifiable by mock).
  - `PHASE_K_AGGRESSIVE=1` mode: uses `ThreadPoolExecutor(max_workers=8)` (verifiable by mock).
  - Both modes write to `upstream_versions` correctly (no schema change).

### Story 5 — Docs, CHANGELOG, retro

- Update `reference/atlas-phases-overview.md` Phase K section with the new scheduler + env vars + expected ~60-75 min cold-fanout wall-clock.
- Update `reference/atlas-phase-engineering.md` § 1 (Per-host secondary rate limits) — add a concrete example referencing the v8.20.0 implementation as the canonical pattern.
- Update `quickref/commands-cheatsheet.md` if it has a Phase K example.
- `CHANGELOG.md` v8.20.0 entry per CLAUDE.md Rule 2.
- Retro at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-cfe-phase-k-cron-runner-2026-06-13.md`.

---

## Functional Requirements

### FR-1: Sustained-rate default behavior

When `PHASE_K_AGGRESSIVE` is unset, Phase K issues at most `PHASE_K_REQUESTS_PER_SECOND` requests per second (default 3.0). Verified by a timing test in `test_phase_k_scheduler.py` (30 requests ≥ 10s).

### FR-2: Aggressive opt-in

When `PHASE_K_AGGRESSIVE=1`, Phase K restores the previous 8-worker `ThreadPoolExecutor` behavior. Verified by mock + timing test (30 requests complete in <5s).

### FR-3: Empirical 403 rate target

After a full-channel admin run, `SELECT COUNT(*) FROM upstream_versions WHERE last_error LIKE '%403%'` divided by total Phase K rows ≤ 1% on the new default. (Verifiable manually after a live run; not blocking the ship since live measurement requires admin profile.)

### FR-4: No row-eligibility behavior change

`PHASE_K_TTL_DAYS` semantics unchanged; the row-selection query is untouched. The scheduler only replaces the fetch dispatcher.

### FR-5: GitLab + Codeberg parity

The same scheduler dispatches to all three VCS hosts. No host-specific rate; same 3.0 RPS default applies. (GitLab + Codeberg fan-outs are much smaller and wouldn't trigger their own rate limits even at the previous 8-worker rate.)

---

## Technical Approach

### Where the code lands

- **`scripts/conda_forge_atlas.py`** — new `_RateLimitedScheduler` class; `_fetch_release_or_tag` (or the Phase K driver function) gains a branch: aggressive mode uses ThreadPoolExecutor, default uses the new scheduler.
- **`scripts/bootstrap_data.py`** — docstring update for new env vars; comment update on `cf_atlas` timeout.
- **`tests/unit/test_phase_k_scheduler.py`** — NEW; covers scheduler correctness + env-var handling + dispatch routing.
- **`reference/atlas-phases-overview.md`** — Phase K section update.
- **`reference/atlas-phase-engineering.md`** — § 1 augmented with v8.20.0 reference.
- **`CHANGELOG.md`** — v8.20.0 entry.
- **`config/skill-config.yaml`** — 8.19.1 → 8.20.0.

### Token-bucket math (canonical)

```python
class _RateLimitedScheduler:
    def __init__(self, rps: float, bucket_capacity: int = 10):
        self.rps = rps
        self.bucket = bucket_capacity
        self.bucket_capacity = bucket_capacity
        self.last_refill = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.bucket = min(
            self.bucket_capacity,
            self.bucket + elapsed * self.rps,
        )
        self.last_refill = now
        if self.bucket < 1.0:
            # Sleep until 1 token available
            wait = (1.0 - self.bucket) / self.rps
            time.sleep(wait)
            self.bucket = 0.0
            self.last_refill = time.monotonic()
        else:
            self.bucket -= 1.0
```

Caller invokes `scheduler.acquire()` immediately before each HTTP request.

### Env-var matrix

| Env var | Default | Purpose |
|---|---|---|
| `PHASE_K_REQUESTS_PER_SECOND` | `3.0` | Sustained-rate target; well below GitHub's secondary-limit threshold |
| `PHASE_K_AGGRESSIVE` | unset (=use sustained-rate) | Set `=1` to restore previous 8-worker burst behavior |
| `PHASE_K_TTL_DAYS` | `7` | Unchanged |
| `PHASE_K_CONCURRENCY` | unset | Unchanged; only consulted under `PHASE_K_AGGRESSIVE=1` |

### Key decisions

- **Single worker in non-aggressive mode by default.** Even with the rate limiter, multiple workers competing for the same token bucket adds complexity without benefit at 3 RPS. If a future workload demands higher throughput, set `PHASE_K_REQUESTS_PER_SECOND` higher (up to ~10 RPS appears safe based on auto-memory observations) — or use `PHASE_K_AGGRESSIVE=1`.
- **Hard-coded sustained-rate target, not dynamic.** GitHub's secondary limit isn't exposed via headers; dynamic detection requires probing the limit, which itself triggers the limit. A conservative hard-coded default is simpler.
- **No persistent cross-process state.** Single-process scheduler. If two admin runs collide (rare), they're each at 3 RPS = 6 RPS combined, still well within limits.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Given the new scheduler with `PHASE_K_REQUESTS_PER_SECOND=3.0`, when 30 requests are issued, then the total elapsed time is ≥10 s (within 10% tolerance). Verified by `test_phase_k_scheduler.py`.
- **AC-2.** Given `PHASE_K_AGGRESSIVE=1`, when Phase K runs, then `ThreadPoolExecutor(max_workers=8)` is used (verifiable by mock).
- **AC-3.** Given the default scheduler, when Phase K runs against the live GitHub API in a full-channel sweep, then the 403 rate is <1% of total rows (manual verification; not gating the ship).
- **AC-4.** Given the v8.16.6 14,400s (`cf_atlas` step timeout), when Phase K runs ~60-75 min under the new default, then the wrapper does not time out and `bootstrap-data --profile admin` reports `✓ cf-atlas-build` with `rc=0`.
- **AC-5.** Given the test suite, when `pixi run -e local-recipes test` runs, then 1,423 → ≥1,430 passing (≥7 new tests). 0 failed, 0 errors.
- **AC-6.** Given the v8.18.1 § 10 (i) discipline, when this ship reaches step-04, then the three-reviewer adversarial pass runs and HIGH/MED findings are classified.
- **AC-7.** Given closeout per CLAUDE.md Rule 2, when v8.20.0 ships, then CHANGELOG entry + retro artifact + Phase K row note in `atlas-phases-overview.md` are all landed.

---

## Open Questions

### Pre-resolved (recommendations)

- **OQ-1.** Default RPS value? **Recommendation: `3.0`.** Empirically: the v8.5.2 8-worker burst hit ~70 req/s peak with 15% 403s; observation hints that GitHub's secondary-limit threshold for the per-IP-per-token combination sits around ~10 req/s sustained. 3.0 RPS leaves a 3× safety margin and was a known-good value in the GitHub docs for "polite" applications.
- **OQ-2.** Bucket capacity? **Recommendation: `10`.** Allows brief 10-request bursts (e.g., catching up after a brief delay) without sustained burst risk.
- **OQ-3.** Should the scheduler be host-aware (different RPS per host)? **Recommendation: no.** GitLab + Codeberg have higher tolerances and smaller fan-outs; the same 3.0 RPS applied to all three hosts is below all their limits.

### Genuinely open (surface at intake)

- **OQ-4.** Should `PHASE_K_AGGRESSIVE=1` print a stderr warning at run start? Operators opting in to the burst pattern know what they're doing, but a one-line warning helps debugging when admins see 403 spam later. **Recommendation: yes — one stderr line on Phase K entry**.
- **OQ-5.** Should the scheduler log per-request timing for the first ~30 seconds, then go silent? Useful for verifying the rate is actually being applied; noisy in steady state. **Recommendation: no — keep the implementation silent; add a `PHASE_K_DEBUG_SCHEDULER=1` opt-in for diagnostics**.
- **OQ-6.** Should we ship a backfill tool that re-runs all `last_error LIKE '%403%'` rows after the migration? The existing TTL bypass on `last_error != NULL` already handles this on the next natural Phase K run. **Recommendation: no — let the natural TTL recovery happen**.

---

## Dependencies and Constraints

- **No new top-level deps.** Token-bucket scheduler uses stdlib `time.monotonic()` only.
- **CLAUDE.md Rules 1 + 2** apply.
- **v8.18.1 § 10 (i)** — step-04 adversarial review is load-bearing for any change touching a phase's dispatcher. Verified by spec FR-6.
- **v8.19.1 § 10 (j) + (k)** — population-distribution claims (`<1% 403 rate`) carry empirical citation (2026-05-12 incident); Ask First clauses (none in this brief) — the spec is concrete enough to not need any.

---

## Out of Scope (Explicit)

- **OoS-1.** Phase L (extra registries) rate-limit work — different profiles, ships separately if needed.
- **OoS-2.** A `PHASE_K_REQUESTS_PER_SECOND` calibration tool that probes GitHub's actual current threshold — too risky (probing triggers the limit).
- **OoS-3.** Cross-process / distributed rate limiting — single-process scheduler only.
- **OoS-4.** GitHub App authentication switchover — orthogonal; would need its own spec.
- **OoS-5.** Retry-budget changes for already-403'd rows — existing TTL recovery is sufficient.

---

## References

### Code (entry points)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — `_fetch_release_or_tag` (Phase K per-row fetch); enclosing Phase K driver function (locate by grep "Phase K" or "phase_k").
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` — env-var docstring + `cf_atlas` timeout comment.

### Tests

- `.claude/skills/conda-forge-expert/tests/unit/test_phase_k_scheduler.py` — NEW.

### Documentation to update

- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — Phase K section.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` — § 1 (Per-host secondary rate limits) gains v8.20.0 reference.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — if Phase K examples exist.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.20.0 entry.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — version bump.

### Auto-memory

- `project_phase_k_secondary_rate_limit.md` — empirical 2026-05-12 incident; cite as the source for the 15% 403 baseline and the "single-digit per-second" target.
