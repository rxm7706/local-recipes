---
title: 'Implement CLI-Triggered Draft Creation & Review Gate (Scaled Down)'
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

**Problem:** Epic 9's original Story 9.2 (`epics-with-stories.md` lines 616-676) specs a
webhook endpoint (`/api/herald/webhooks/on-pr-close`) CI calls automatically on PR close,
which extracts `project_name` from the PR title/labels, queries a test-job URL and a
dashboard API for metrics, searches for downstream PRs as adoption signals, and creates a
draft `Claim` -- all with retry/backoff and operator alerting on extraction failure. There
is no CI integration point, no dashboard API, and no webhook receiver anywhere in this
repo's Herald architecture to build any of that against.

**Approach:** `herald success create <project-name>` -- a CLI command an operator runs by
hand, supplying directly the fields the webhook payload would have carried after its own
extraction: project name (positional), `--shipped-date` (default: today), and up to three
`--evidence-{test-results,metrics,adoption}` URL flags. It calls `claims.create` (Story
9.1) and prints the new claim's id plus a `herald success review <id>` hint. The review
half of this story -- `herald success review <claim-id>`, read-only display of a draft's
evidence ahead of publish -- is Story 9.3's command, described here because this story's
own AC bundles "review gate" with "auto-extract."

## Boundaries & Constraints

**Always:**
- `herald success create <project_name> [--shipped-date YYYY-MM-DD]
  [--evidence-test-results <url>] [--evidence-metrics <url>] [--evidence-adoption <url>]`.
  Only the three evidence flags this AC's payload names (`test_results`/`metrics`/
  `adoption`) are exposed -- `evidence.type="other"` has no CLI flag yet (no AC asks for
  one; `claims.create` itself accepts any `EVIDENCE_TYPES` member, so adding a fourth flag
  later is additive).
- Prints `created draft claim <id> for '<project_name>'` then
  `review with: herald success review <id>` -- the AC's "CLI shows: 'Review claim
  <claim-id> before publishing'" equivalent.
- Routes through `dispatch()` (AD-6) like every other subcommand.

**Block If:** N/A -- local file write only, no network call, no live gate.

**Never:**
- **No operator-role gate on `create`.** Creating a *draft* is the scaled-down equivalent
  of the original spec's webhook firing automatically the moment CI reports
  `gates_passed=true` -- the original spec never gated that on a role either (only
  *publishing*, Story 9.3, is gated per AD-16). Gating `create` would be inventing a
  restriction the source AC never asked for.
- No test-job-URL query, no dashboard-API query, no downstream-PR search, no
  retry/backoff, no operator-alert delivery -- all only meaningful against a live
  webhook receiver that does not exist; deferred to
  `docs/dreams/herald-moments-2-4-live-backend.md` in full.
- No `gates_passed` concept at all -- there is no CI payload to carry that flag; an
  operator who runs `herald success create` has implicitly already decided the ship
  qualifies.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| Minimal create | `herald success create warden` | draft claim, `shipped_date` = today | |
| Explicit shipped-date | `--shipped-date 2026-08-01` | claim's `shipped_date` matches | |
| One evidence flag | `--evidence-test-results <url>` | one `Evidence(type="test_results", ...)` | |
| All three evidence flags | all three given | three `Evidence` entries, one per type | |
| No operator role set | `HERALD_TOKEN` unset | still exits 0 -- create never checks auth | proves the gate boundary |
| Output | any successful create | stdout names the id and the `review` follow-up command | |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- adds the
  `success create` subparser (`project_name`, `--shipped-date`,
  `--evidence-{test-results,metrics,adoption}`) and `_run_success_create`; adds the
  `success review` subparser (`claim_id`) and `_run_success_review` (Story 9.3 wires
  `publish`/`list`/`get`/`validate` alongside these in the same edit); adds a `--repo-root`
  flag on the `success` parser itself (shared by every `success` subcommand, resolving
  `.herald/claims.json`'s location -- mirrors `deck`'s existing per-subcommand
  `--repo-root` convention, but declared once at the `success` parser level since every
  `success` subcommand reads the same local file, not a per-slug one).
- `src/shared/packages/pyforge-herald/tests/test_cli_success.py` -- create -- `create`
  (this story) plus `review`/`publish`/`list`/`get`/`validate` (Stories 9.3/9.5, same file
  -- the whole `success` CLI surface is one cohesive test module rather than five).

## Design Notes

**Judgment call: exact flag naming.** The original spec's webhook payload names
`pr_url`/`commit_sha`/`test_job_url`/`close_at`/`gates_passed`. None of those map cleanly
to a hand-typed CLI flag an operator would want to type -- `--evidence-test-results <url>`
reads naturally as "here is the link to point at," which is what the AC's *downstream*
`Evidence` entry actually needs, regardless of how it got there. This is a deliberate
re-interpretation of the payload shape into an operator-ergonomic flag shape, not a literal
field-for-field port.

**Judgment call: no auth gate on `create`.** Documented above in Boundaries & Constraints
-- restated here because it is the single most consequential deviation from Story 6.3's
established "every write subcommand checks `auth.require_operator_role`" pattern this
package has followed since Epic 6. The distinguishing fact: `create` produces a *draft*,
which under the original spec's own design was never operator-gated (only the eventual
`publish` was). Scaling the trigger mechanism down from a webhook to a CLI command does not
change what already wasn't gated.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 611 passed, 2 skipped
  (whole-package total; this story's own coverage: `test_create_*` in
  `test_cli_success.py`).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `herald success create warden --evidence-test-results https://example/tests` against a
  scratch `--repo-root` -- prints the created id and review hint; `.herald/claims.json`
  under that root holds one draft claim with one evidence entry.

## Spec Change Log

## Review Triage Log
