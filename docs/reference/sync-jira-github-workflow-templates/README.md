# Steward `sync` — GitHub Projects V2 ↔ Jira Cloud workflow templates

Epic 8, Story 8.1 (bidirectional propagation). These are **templates for the
*external target* repo** — the repo whose GitHub Projects V2 board / Jira
Cloud project you are syncing. They are **never installed into this repo's
own `.github/workflows/`**; this repo (`local-recipes`) only ships `steward`
and this documentation, it is not itself a sync participant.

See `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/
_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` for
the binding invariants (AD-1 through AD-9) referenced throughout this
document.

## What's here

| File | Direction | Trigger(s) |
|---|---|---|
| `github-to-jira.yml.template` | GitHub Projects V2 item changed → propagate to Jira | `schedule` (default) + opt-in `repository_dispatch` |
| `jira-to-github.yml.template` | Jira issue changed → propagate to GitHub | `repository_dispatch` only |

Both call the same underlying command, `steward sync reconcile`, which
**re-reads both linked items' current state** before deciding anything — the
trigger (a schedule tick, a dispatched webhook payload) is only ever a
wake-up, never trusted as the change itself (AD-9, the
event-triggered-reconciliation paradigm).

## Setup, in the target repo

1. **Provision the fields these templates expect.** `steward sync` never
   creates them — you must already have, on both the GitHub Projects V2
   board and the Jira project:
   - GitHub: a project-level custom **text** field for the propagated
     status value, a text field holding the linked Jira issue key, and a
     text field holding this item's own baseline (a JSON-serialized
     per-field map of last-synced values, never a timestamp).
   - Jira: a custom field holding the linked GitHub item's node ID, and a
     custom field holding this issue's own baseline (same JSON-map shape)
     (Jira's built-in `status` field is read/written directly — no custom
     field needed for it).
2. **Copy `.steward/sync-config.example.yaml`** (from this `local-recipes`
   checkout) into the target repo as `.steward/sync-config.yaml`, and fill
   in the real project/field IDs from step 1. Commit it — it is
   non-secret, deployment-specific configuration (AD-2's control plane
   lives on the items themselves; this file only names *where*).
3. **Set the target repo's secrets/variables** the templates reference:
   - `secrets.STEWARD_GITHUB_TOKEN` — a fine-grained GitHub PAT scoped to
     Projects V2 read/write only (AD-8: least-privilege, never widened).
   - `secrets.STEWARD_JIRA_EMAIL` / `secrets.STEWARD_JIRA_API_TOKEN` — the
     Atlassian account email and an API token (Jira auth resolves through
     `_http.py`'s generic `.netrc` fallback: Basic auth, email as login,
     API token as password).
   - `vars.STEWARD_JIRA_HOST` — the Jira Cloud site hostname, no scheme
     (e.g. `your-org.atlassian.net`).
   - `vars.STEWARD_EXAMPLE_ITEM_ID` — (GitHub→Jira template only) one
     GitHub Projects V2 item node ID, used by the `schedule`/manual path
     until you wire real per-item iteration (see the template's own TODO).
4. **Copy the two `.yml.template` files** into the target repo's
   `.github/workflows/`, dropping the `.template` suffix, and fill in each
   file's own `TODO` comments (fork/mirror path for the `local-recipes`
   checkout, schedule cadence, item iteration).

## The opt-in near-real-time path

The **default** trigger is `schedule` (AD-1) — zero infrastructure beyond
the Action itself. Near-real-time is available but **opt-in**, because it
requires infrastructure this story does not provision:

- **GitHub → Jira**: GitHub's `projects_v2_item` webhook exists, but there
  is **no `on: project_v2_item` (or `projects_v2_item`) workflow trigger** —
  verified against GitHub's own "events that trigger workflows"
  documentation (2026-08-09; see ARCHITECTURE-SPINE.md AD-1's amendment
  history). Reaching `github-to-jira.yml.template`'s `repository_dispatch`
  trigger requires an **external receiver** you stand up yourself — a
  GitHub App with org-level Projects read access, or a webhook endpoint —
  that consumes the `projects_v2_item` webhook and calls the GitHub REST
  `repository_dispatch` API with `event_type: github_item_updated` and
  `client_payload: {"node_id": "<the changed item's node ID>"}`.
- **Jira → GitHub**: a **Jira Automation Rule** is the trigger. Create a
  rule scoped to your project:
  - **Trigger**: "Field value changed" (or "Issue transitioned", depending
    on which change you want to react to).
  - **Action**: "Send web request" to
    `https://api.github.com/repos/<owner>/<repo>/dispatches`, method
    `POST`, headers `Authorization: Bearer <a GitHub PAT with
    `repository_dispatch` scope>` and `Accept:
    application/vnd.github+json`, body:
    ```json
    {
      "event_type": "jira_issue_updated",
      "client_payload": { "jira_key": "{{issue.key}}" }
    }
    ```
    This is the same `repository_dispatch` shape the intake document's Flow
    A2 sketch described.

## Manual live-pair verification (operator follow-up, not a build-time gate)

This story's own automated build has **no live GitHub Projects V2 board and
no live Jira Cloud project** — that is expected for an unattended build of a
greenfield external-system integration (this story's spec, "Block If:
none"), not an intent gap. CAP-1's literal acceptance bar ("against a live
GitHub Projects V2 board and a live Jira Cloud project") is verified by the
target repo's **operator**, once, after deploying the setup above:

1. Move a card's tracked status field on the GitHub Projects V2 board (or
   run `steward sync reconcile --github-item <id> --config
   .steward/sync-config.yaml --dry-run` locally first to confirm the
   decision it *would* make).
2. Trigger reconciliation — either wait for the next `schedule` tick, or run
   the workflow manually via `workflow_dispatch`.
3. Confirm the linked Jira issue transitions to match, and that both sides'
   baseline fields update to the new converged value.
4. Repeat in the other direction: transition the Jira issue, trigger
   `jira-to-github.yml.template` (manually, or via the Automation Rule),
   and confirm the GitHub item's tracked field updates to match.
5. If the opt-in near-real-time receivers are deployed, repeat both
   directions again without manually triggering the workflow — the external
   receiver / Automation Rule should fire `repository_dispatch`
   automatically within its own normal latency.

A **known vendor defect** (already named by the architecture): GitHub's
`updateProjectV2ItemFieldValue` can update the underlying data correctly
while leaving the Projects V2 board's grouping/column view stale — a card is
logically moved but looks stuck until a human drags it or reloads the board.
This is expected; it is not a failed write, and step 3 above should confirm
via the Jira side (or the GraphQL API directly) rather than trusting a
possibly-stale board view.
