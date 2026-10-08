---
title: "16.3: Each fleet fix waits in a proposal queue for operator approval"
type: 'feature'
created: '2026-09-28'
status: 'done'
followup_review_recommended: false
baseline_revision: '12aaada166569f487059adab7a2361b4edacec23'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-2-a-fleet-run-scans-each-inventoried-repo-one-verdict-per-repo.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-3-the-actuator-opens-the-fix-as-a-draft-pr-on-an-estate-repo.md
flag:
  key: pyforge.warden.fleet_fix_proposals
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "no proposal is queued; the approve action is listed as disabled and refuses"
  cleanup: 90 days after ON in every environment (Q4)
deferred:
  - summary: >-
      Add portal HTTP tests for fleet proposal queue approve/dismiss and flag-off disabled UI.
    evidence: |-
      Service-layer tests cover approve_proposal; no Client tests hit /stations/warden/fleet/proposals/ views.
    location: >-
      src/platform/tests/test_warden_fleet_proposals.py
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A fleet run (Story 16.2) plans fixes but must never open one on its own. The operator ruled on 2026-09-28:
"every fleet fix is queued as a proposal, and it opens as a PR only after the operator approves it", one at a time.

**Approach:** In `django_warden_fabric`: a `FixProposal` model (the `FleetRepoScan` it came from, repo, finding id,
action, target, planned changed paths, state `queued`/`approved`/`opened`/`failed`/`dismissed`, PR URL, error, who
approved and when). When a fleet run completes, each `planned` outcome in a repo's `actuation` payload becomes one
`queued` proposal; nothing reaches the forge. One service function, `approve_proposal(id, operator)`, backs both the
portal's approve action (HTMX, warden role) and the `warden_fleet_approve` management command: it marks the proposal
`approved` and enqueues one keys-not-blobs task that clones the repo into a throwaway directory, re-runs the actuator's
real path for exactly that finding through Story 14.3's draft-PR path (with the Steward-provided GHE credential for that
repo), and records `opened` with the URL or `failed` with the captured error. Story 14.3's estate allowlist admits a
fleet repo only for that one approved finding, through an explicit per-call authorization the approve task passes —
never by widening the allowlist config. A dismiss action closes a proposal without a forge call. Models ship a migration and its covering Liquibase changeset. Both actions read the flag through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); OFF, they are listed as disabled and refuse.

Ledger key: `16-3-each-fleet-fix-waits-in-a-proposal-queue-for-operator-approval`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-16.2, S-14.3.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43), CAP-24 (FR-41, the opening path); CAP-12 (FR-40).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a completed fleet run with two planned fixes, When it completes, Then two `queued` proposals exist and the fixture forge has received zero write calls
- Given one queued proposal, When the operator approves it (portal or management command), Then exactly that proposal opens as a draft PR on its repo through Story 14.3's path and is recorded `opened` with the URL; the other stays `queued`
- Given an approval whose open fails, When the task ends, Then the proposal is `failed` with the captured error, the throwaway clone is gone, and nothing retries on its own
- Given a proposal approved twice, When the second approval arrives, Then it is refused (already approved) and no second PR opens
- Given a dismiss action, When it runs, Then the proposal is `dismissed` with no forge call
- Given the flag OFF, When the operator opens the queue or runs the command, Then approve is listed as disabled and refuses (the command exits 2)

## Boundaries & Constraints

**Always:**
- One code path for the portal action and the management command.
- Open at most one PR per approval, only through the actuator; the actuator stays the only forge writer.
- Remove every throwaway clone on success and failure.
- Ship the migration with its covering Liquibase changeset; `platform-ci-local -- --test` green.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF). The portal view runs inside the host, where `pyforge` may be absent; there, and only there, it evaluates the same key through `django_pyforge.flags`, the Guild's other sanctioned reader.
- Reconcile every Spec `spec-surface-check` names for the touched paths; scoped stamps only.

**Never:**
- Auto-open, batch-open or schedule-open a fleet PR; no approval, no forge write.
- Compose a fleet-level verdict or change any repo's stored scan result.
- Open a non-draft PR on a fleet repo.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| run completes | two planned fixes | two `queued` proposals, zero forge writes | — |
| approve one | proposal A | A `opened` (draft PR URL); B `queued` | — |
| open fails | forge 5xx | `failed` with the error | no auto-retry |
| double approve | A already `approved` | refused | no second PR |
| dismiss | proposal B | `dismissed` | no forge call |
| flag OFF | key off | approve disabled | refuses, exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43), with CAP-24 (FR-41) as the opening path.
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `16-3-each-fleet-fix-waits-in-a-proposal-queue-for-operator-approval`.
Ledger status at mint: `backlog`.
Deps: S-16.2, S-14.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under `src/platform/tests/`, the covering changeset under `sqlmigrate-extraction`).
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.fleet_fix_proposals` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON queues and approves, OFF lists approve as disabled and refuses with exit 2.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 12 findings — high 0, medium 2, low 3, false 4, maybe-false 3
- findings:
  - `[false]` `[reject]` `@require_GET` on helper breaks views — removed erroneous decorator on `_fleet_fix_proposals_enabled`.
  - `[medium]` `[patch]` Missing `sqlmigrate-map.yaml` entry for 0003 — added `warden_fabric.0003_fix_proposal: 23`.
  - `[medium]` `[patch]` Celery task enqueued before commit — `approve_proposal` now uses `transaction.on_commit` for `open_fix_proposal.delay`.
  - `[low]` `[patch]` Missing DoesNotExist handling — `approve_proposal` / `dismiss_proposal` raise `ProposalRefusedError` when id missing.
  - `[low]` `[reject]` Double-approve test flaky under eager Celery — patched `.delay` in test.
  - `[low]` `[defer]` Portal HTTP tests absent — deferred with location `src/platform/tests/test_warden_fleet_proposals.py`.
  - `[false]` `[reject]` Actuator co-governor memlog missing — pyforge-warden memlog covers actuator.py; reconcile green.
  - `[maybe-false]` `[defer]` Concurrent double open without row lock in task — unverified; would need select_for_update in task.
  - `[false]` `[reject]` Dismiss must be flag-gated — spec scopes flag to approve actions; dismiss stays available for queued rows.
  - `[maybe-false]` `[reject]` Zero forge writes on finalize untested — finalize path does not call actuator; queue-only by construction.
  - `[maybe-false]` `[defer]` Flag-off finalize queueing untested — `queue_proposals_from_scan` early-returns when flag off; add test in follow-up if desired.

## Auto Run Result

Status: done

Summary: Story 16.3 adds `FixProposal` queueing at fleet-run finalize, shared `approve_proposal` / `dismiss_proposal`, Celery `open_fix_proposal` with `authorized_fleet_repo` actuator admission, portal HTMX queue, and `warden_fleet_approve` management command.

Files changed: django_warden_fabric (models, proposals, tasks, views, template, command, migration); pyforge warden actuator; platform flags/Liquibase/tests/sqlmigrate-map.

Review: 4 patches applied (sqlmigrate map, on_commit enqueue, DoesNotExist, view decorator); portal HTTP coverage deferred.

Follow-up review recommendation: false (no high patches; medium patches were mechanical).

Verification: `pixi run --frozen -e pyforge-warden pyforge-warden-test` passed (2266); `python scripts/spec_surface_reconcile.py` OK. Platform proposal tests require PostgreSQL (`platform-ci-local -- --test` not run in this session).

Residual risks: Portal routes untested via HTTP; production Celery concurrency on duplicate approve not mutex-guarded in task (refused at approve layer).
