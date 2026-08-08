---
title: 'Wire Evidence Validation Into Publish + Add Operator-Run Re-Validation (Scaled Down)'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 6.4 (Epic 6) already built the full evidence-validation library
(`evidence.py`: `validate_link`, `validate_for_publish`, `schedule_async_validation`) but
deliberately left it unwired -- "wiring it into an actual publish command is Epic 9's
scope" (that story's own spec, Boundaries & Constraints). Epic 9's original Story 9.5
(`epics-with-stories.md` lines 786-849) specs sync validation at publish time (already
built) plus a **weekly async validation cron** (APScheduler/Celery Beat) that re-checks
every published claim's evidence and alerts the operator on staleness. There is no
scheduler, no cron runner, and no alert-delivery channel (email/in-app) anywhere in this
repo's Herald architecture to hang a real weekly job on.

**Approach:** Two changes, both thin wiring over Story 6.4's already-built library. (1)
`claims.publish` (Story 9.1) calls `evidence.validate_for_publish` on every evidence link
before persisting -- a broken link raises `EvidenceLinkError`, propagated unchanged by
`herald success publish` (Story 9.3), rejecting the publish with nothing written. (2) a new
`herald success validate <claim-id> | --all` command replaces the weekly cron with an
operator-run, on-demand re-check via `evidence.validate_link` (never raises; the whole
point is to surface breakage, not reject it), updating `validated`/`validated_at` in place.
No alerting is built -- an operator who runs `validate` sees the result directly in the
command's own output.

## Boundaries & Constraints

**Always:**
- `claims.publish`'s evidence loop calls `validate(e.url)` for every evidence entry (default
  `evidence.validate_for_publish`) *before* any field is mutated or anything is written to
  disk -- the first broken link's `EvidenceLinkError` aborts the whole publish, the claim
  stays `draft` on disk, unchanged.
- A successful publish marks every evidence entry `validated=True`,
  `validated_at=<publish timestamp>` -- the sync-validation half of AD-15's contract,
  already true the moment a claim becomes published.
- `herald success validate <claim-id>` and `herald success validate --all` (mutually
  exclusive -- exactly one required, enforced at runtime as a plain `HeraldError` rather
  than an `argparse` usage error, since the AC calls for exit 1 here, matching this
  package's existing `--date-range` post-parse-validation convention) re-check every
  evidence link via `evidence.validate_link`, updating `validated`/`validated_at` whether
  the link is currently broken or not -- never raises on a broken link.
- `--all` shares one `now()` timestamp across the whole batch (`claims.revalidate_all`),
  mirroring `evidence.schedule_async_validation`'s own "one run, one timestamp"
  discipline.
- `validate` never checks `auth.require_operator_role` -- re-checking evidence links is a
  read-observe-and-record operation, not a publish-equivalent write requiring the operator
  role (AD-16 gates *publishing claims*, not *maintaining evidence link health*).
- Staleness (>7 days since `validated_at`, AD-15's `evidence.STALE_AFTER`) is surfaced via
  `claims.is_stale`/`to_dict` (Story 9.1) -- the web tab's yellow-warning badge (Story 9.4)
  is this story's actual "flagged for operator review" delivery mechanism, replacing the
  original spec's email/in-app alert.

**Block If:** N/A -- both `claims.publish` and `claims.revalidate`/`revalidate_all` accept
an injectable `validate` callable, so every test in this story runs offline against a
hand-written fake, honoring the package's `deny_network` autouse fixture.

**Never:**
- No APScheduler/Celery Beat dependency, no cron entry, no background job of any kind --
  `herald success validate` *is* the schedulable unit an operator (or, later, an actual
  cron entry once one exists to hang it on) invokes directly, same pattern Story 6.4's own
  `schedule_async_validation` already established as "a plain synchronous callable, not a
  real background job."
- No operator-alert delivery (email/in-app) -- the AC's "operator alerted" is satisfied by
  `validate`'s own command-line output (a summary count of valid/broken links) plus the web
  tab's stale badge; no notification channel is built.
- `evidence.py` itself is **not modified** by this story -- Story 6.4 already built
  everything this story needed; this story is wiring only.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| `publish`, all links valid | `validate_for_publish` never raises | claim published, every evidence entry `validated=True` | |
| `publish`, one broken link | `validate_for_publish` raises on the first broken url | `EvidenceLinkError` propagates; claim stays `draft`, unchanged on disk | Story 9.3's `herald success publish` surfaces this as exit 1, "Evidence link broken" |
| `validate <id>`, mixed links | one live, one dead | `validated` per-link reflects each `is_valid`; neither raises | |
| `validate --all`, two claims | each with evidence | both claims' evidence re-stamped with one shared timestamp | |
| `validate`, neither `<id>` nor `--all` | bare `herald success validate` | exit 1, "exactly one of \<claim-id\> or --all" | |
| `validate`, both `<id>` and `--all` | conflicting flags | exit 1, same message | |
| `validate`, no auth context | `HERALD_TOKEN` unset | exits 0 -- never gated | proves the AD-16 boundary explicitly |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/claims.py` -- edit -- `publish`'s
  evidence-validation loop (calls `validate(e.url)` per entry, marks `validated=True` on
  success); `revalidate`/`revalidate_all` (new: on-demand re-check, never raises).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit --
  `_run_success_validate` and the `success validate` subparser (`claim_id` optional
  positional, `--all` flag).
- `src/shared/packages/pyforge-herald/tests/test_claims.py` -- edit -- `publish`'s
  broken-link/valid-link cases; `revalidate`/`revalidate_all` cases.
- `src/shared/packages/pyforge-herald/tests/test_cli_success.py` -- edit (shared file,
  Stories 9.2/9.3) -- `validate` CLI coverage, including the exactly-one-of-two-args
  runtime check and the never-gated-on-auth proof.

## Design Notes

**Judgment call: `herald success validate` replaces the weekly cron entirely, with no
scheduler dependency at all.** This mirrors Story 6.4's own explicit precedent
(`schedule_async_validation`'s docstring: "adding a scheduler dependency ... for one weekly
re-check is exactly the kind of speculative weight this repo's 'lean dependency' doctrine
argues against"). This story does not even wire `evidence.schedule_async_validation` in --
`claims.revalidate`/`revalidate_all` call `evidence.validate_link` directly per entry,
which is simpler and does not need `schedule_async_validation`'s "was this already stale
before this run" bookkeeping (that bookkeeping matters for a recurring job comparing
run-over-run; an on-demand operator command has no "previous run" to compare against in
the same sense -- `claims.is_stale` at read time already answers "is this overdue," making
`schedule_async_validation`'s specific contract redundant for this call shape).

**Judgment call: no operator alerting.** The original AC's "operator alerted... via email
or in-app notification (TBD)" was already marked "TBD" in the source spec -- i.e.
unresolved even under the original live-backend design. This story does not invent a
resolution; the web tab's stale badge (Story 9.4) is the closest analog this scaled-down
pass ships, and `validate`'s own printed summary is the CLI-side equivalent for an operator
who runs it directly.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 611 passed, 2 skipped
  (whole-package total).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `herald success publish <id> --thesis x` against a claim with a deliberately-broken
  evidence URL (via a monkeypatched `validate_for_publish` in tests, since this suite never
  reaches real network) -- exits 1, claim unchanged on disk.
- `herald success validate --all` against a scratch `claims.json` with two claims -- prints
  a per-claim-count summary; both claims' evidence entries share one `validated_at`.

## Spec Change Log

## Review Triage Log
