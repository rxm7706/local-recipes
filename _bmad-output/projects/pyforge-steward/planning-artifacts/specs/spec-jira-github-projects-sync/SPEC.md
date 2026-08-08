---
spec: jira-github-projects-sync
status: draft
owner-dream: docs/dreams/jira-github-projects-sync.md
surface: []          # frontier — no sync code, workflow, or Jira/Projects integration exists anywhere in this repo yet (verified by grep 2026-08-08)
companions: []
sources:
  - ../../../../../../docs/dreams/jira-github-projects-sync.md
  - ../../../../../../docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md
open_questions:
  - "Q2 — no authoritative side is named. The Dream demands zero-loop bidirectional propagation but never says which system wins when the two boards disagree at sync time (simultaneous conflicting moves); the intake document's per-field sync-direction config is a mechanism for expressing an answer, not the answer itself."
  - "Q3 — Mode A (real-time serverless: GitHub Actions + Jira Automations) vs Mode B (scheduled batch: dlt + PostgreSQL) vs a deliberate combination is an architecture-phase decision the Dream refuses to pre-commit."
  - "Q4 — Mode B's data-model shape is unreconciled on purpose: flat single-table (direct custom_status column) vs normalized EAV schema + three-table control-plane bridge, and whether the bridge's entity-linking table replaces or coexists with the simpler custom-field linking."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/jira-github-projects-sync.md` is the aspiration;
> `docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md`
> (v1.1) carries the deep technical grounding — PRD, both candidate architectures, PostgreSQL
> DDL, control-plane bridge tables, epics/stories, acceptance checklist — that this contract
> intentionally does not duplicate.

# SPEC — jira-github-projects-sync

## Why

Two boards, one truth. When a developer drags a GitHub Projects V2 item to "Done" or a PM
transitions the linked Jira issue from a Cloud dashboard, the other board should reflect it
without a human re-typing anything, without a third-party SaaS bridge (Unito, Exalate) in the
loop, and without the two systems chasing their own tail. Today nothing does this: this repo
has no Jira integration and no GitHub Projects integration of any kind (verified 2026-08-08 —
the only matches for either term are the Dream, its intake document, and unrelated
recipe-fixture names); story status lives in per-project `sprint-status-ledger.yaml` files and
GitHub is driven directly via `gh` Issues/PRs. The complete technical write-up already exists
as intake material; what does not exist is a contracted, buildable sync engine that is boring
in exactly the way infrastructure should be — cheap to run, idempotent, and impossible to
accidentally DDoS itself.

## Capabilities

- **CAP-1 — bidirectional propagation of status, assignee, and identity link.**
  - **intent:** Moving a GitHub Projects V2 item's status reaches the linked Jira issue, and
    transitioning a Jira issue reaches the linked GitHub item — each direction, with the
    item↔issue identity link and assignee kept synchronized close to real-time, and no human
    action required on the receiving side.
  - **success:** a status change made on either board appears on the other without manual
    intervention, in both directions, against a live GitHub Projects V2 board and a live Jira
    Cloud project.

- **CAP-2 — zero-loop guarantee.**
  - **intent:** An update one side makes *because of a sync* never triggers a sync back the
    other way. The intake document offers two candidate mechanisms — Mode A's bot-identity
    guard clauses, and Mode B's time-based check (item `updated_at` vs the engine's own
    `last_sync_timestamp`) — either is a viable starting point, neither is pre-chosen here.
  - **success:** a demonstrated (not merely claimed) test in which a synced update provably
    does not echo: N round-trips of a single human change produce exactly one propagation, not
    N.

- **CAP-3 — idempotent update processing.**
  - **intent:** Re-processing the same update payload twice produces the same end state both
    times — no duplicate transitions, no double-counted history — so retries and redelivered
    webhooks are safe by construction.
  - **success:** delivering an identical payload twice leaves both systems byte-identical to
    delivering it once.

- **CAP-4 — fail loud, fail alone on broken links.**
  - **intent:** An item missing its cross-system link fails loudly in a log — never silently
    skipped — and never crashes the pipeline for every other item in the batch.
  - **success:** a batch containing one unlinked item completes for all other items and emits
    a named, greppable error for the unlinked one.

- **CAP-5 — explicit status-vocabulary translation.**
  - **intent:** Status vocabulary differences between the two systems ("Done" vs "Closed") are
    translated through an explicit, reviewable mapping, never assumed to match — a wrong exact
    string sent to either API fails outright rather than silently creating a phantom state.
  - **success:** every status value crossing the boundary passes through the translation
    table; an unmapped value is a hard, logged failure, not a pass-through.

## Constraints

- **No third-party sync SaaS.** Unito, Exalate, and kin are out by the intake document's own
  stated non-goal. Two due-diligence findings are on record and not to be re-litigated:
  **Steampipe** rejected as the write path (plugins are read-only; possibly still useful
  read-side), **Octosync** rejected (unmaintained ~5 years, real auth-incompatibility risk).
- **Zero-loop and idempotency are demonstrated, not claimed.** CAP-2 and CAP-3 are
  non-negotiable NFRs; whichever mode ships must carry tests that prove both.
- **Credentials are env-var-only, least-privilege, never committed, never logged.** GitHub
  fine-grained PAT and Jira API token live in secrets storage / environment variables
  following this repo's existing runtime-driven convention for external-API credentials
  (`_http.py`'s truststore + auth-chain pattern — env vars only, never committed config). Note
  the recorded `_http.py` JFROG_API_KEY unconditional-injection incident as the cautionary
  example: any new API client must scope each credential to exactly its own host.
- **Design around the known `updateProjectV2ItemFieldValue` quirk.** The GitHub API can update
  data correctly while leaving the Projects V2 board UI's grouping index stale (card visually
  "stuck" until a manual drag). This is an accepted, documented UX quirk to design around —
  not a bug in this system's own logic; re-verify against GitHub's issue tracker at
  implementation time.
- **Greenfield, and the intake document is grounding, not the contract.** No sync code, no
  GitHub Actions workflow, no Jira Automation rule, no `dlt` pipeline exists in this repo.
  The intake document's API payloads, SQL DDL, and workflow YAML are candidate material for
  the PRD/architecture phase; this SPEC binds only what appears above.
- **No conflict-resolution design is invented here.** The Dream calls for zero-loop and
  idempotency; it does not specify a two-way merge/conflict policy for simultaneous opposing
  edits. That gap is held open in Q2, not papered over with an assumed last-write-wins.

## Non-goals

- **Not picking Mode A vs Mode B here** — real-time serverless vs scheduled batch (or a
  deliberate combination) belongs to the architecture phase, informed by real usage patterns
  this contract does not yet have (Q3).
- **Not picking Mode B's flat vs normalized schema shape** — same reasoning, same phase (Q4).
- **Not this repo's own project tracking.** *(Q1 resolved 2026-08-08 — see § Resolved
  Questions.)* The target is an external GitHub Projects V2 / Jira Cloud pair. This engine
  never reads or writes `sprint-status-ledger.yaml`, the dashboard feed, or any build-line
  artifact; wiring it to them would move it back across the seam into Marshal's tree.
- **Not syncing fields beyond status, assignee, and the identity link.** Comments,
  descriptions, attachments, sprints, and estimates are out of scope for this contract.
- **Not re-evaluating Steampipe or Octosync.** Both verdicts are on record in the Dream.

## Success signal

A card moved once — on either board — shows up on the other board without a human touching
the second system, and the operator can prove three things on demand: the change never echoed
back (zero-loop), replaying the delivery changed nothing (idempotency), and every credential
involved lives in the environment, not the repo or the logs. "Either board" means the
external GitHub Projects V2 board and Jira Cloud project named at configuration time
(Q1, resolved) — never this repo's own ledger or dashboard.

## Resolved Questions

- **Q1 — target scope. RESOLVED 2026-08-08 (operator): an external GitHub Projects V2 /
  Jira Cloud pair**, independent of this repo's own `sprint-status-ledger.yaml`, dashboard
  or story flow. The engine is not wired to the build line and must not assume it.
- **Q5 — owner station. RESOLVED 2026-08-08 as a consequence of Q1, not independently.**
  This Spec previously framed Q1 and Q5 as two open questions; they are one. Under the
  Marshal/Steward seam (build line vs. the estate it stands on, ratified 2026-08-08),
  syncing *this repo's own tracking* would make the engine a second consumer of the build
  line's ledger — Marshal's. Syncing an *external* pair makes it an integration service
  running on the estate — **Steward's**. Q1 therefore determines Q5 mechanically, and with
  Q1 answered the ownership call follows: **owner `steward`**, chain relocated from
  `pyforge-marshal` to `pyforge-steward` per INV-2. The credential-led NFRs land on
  Steward's existing `keys` surface rather than needing a new one, which is corroborating
  evidence rather than the reason.

## Open Questions

- Q2 — no authoritative side is named. The Dream demands zero-loop bidirectional propagation
  but never says which system wins when the two boards disagree at sync time (simultaneous
  conflicting moves); the intake document's per-field sync-direction config is a mechanism
  for expressing an answer, not the answer itself.
- Q3 — Mode A (real-time serverless: GitHub Actions + Jira Automations) vs Mode B (scheduled
  batch: `dlt` + PostgreSQL) vs a deliberate combination is an architecture-phase decision
  the Dream refuses to pre-commit.
- Q4 — Mode B's data-model shape is unreconciled on purpose: flat single-table (direct
  `custom_status` column) vs normalized EAV schema + three-table control-plane bridge, and
  whether the bridge's entity-linking table replaces or coexists with the simpler
  custom-field linking.
- Q5 — owner station is provisional: marshal (orchestration / cross-system visibility, and
  the natural consumer if the sync ever targets this repo's own tracking) vs steward
  (credential lifecycle — the NFRs lead with token/secret handling). The Dream asks for a
  deliberate call, not silent inheritance.
