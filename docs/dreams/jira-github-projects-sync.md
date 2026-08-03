---
title: A ticket moves once, both boards know
type: dream
owner: marshal
status: dreamt
---

# A ticket moves once, both boards know

## The Dream

Two boards, one truth. Whoever moves a card — a developer dragging a GitHub
Projects V2 item to "Done," a PM transitioning a Jira issue from a Cloud
dashboard — the other board reflects it without a human re-typing anything,
without a third-party SaaS bridge (Unito, Exalate) in the loop, and without
the two systems ever chasing their own tail (Jira updates GitHub updates
Jira updates GitHub...). Status, assignee, and the identity link between a
GitHub item and its Jira issue stay synchronized close to real-time, and the
sync engine is boring in exactly the way infrastructure should be: cheap to
run, idempotent, and impossible to accidentally DDoS itself with.

A full technical write-up already exists — PRD, both candidate
architectures (including a concrete normalized PostgreSQL schema for both
systems plus a control-plane bridge layer for Mode B), epics/stories, and an
acceptance checklist — captured and kept current at
`docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md`
(now v1.1, after two follow-up drops of real technical detail were distilled
in place). This Dream distills the aspiration and cites that single document
as the load-bearing source; the deep technical detail (API payloads, SQL
DDL, workflow YAML shapes) lives there for `bmad-spec` (or the fuller
planning chain) to distill when this Dream moves past `dreamt`.

## What it looks like when real

- Moving a GitHub Projects V2 item's status reaches the linked Jira issue,
  and moving a Jira issue's status reaches the linked GitHub item — in each
  direction, without the human doing anything on the other side.
- The two systems never loop: an update one side makes because of a sync
  never triggers a sync back the other way. The intake document now documents
  two candidate mechanisms — Mode A's bot-identity guard clauses, and Mode
  B's time-based check (compare an item's own `updated_at` against the
  sync engine's own `last_sync_timestamp`) — either is a viable starting
  point, not a foregone conclusion.
- Re-processing the same update payload twice produces the same end state
  both times — no duplicate transitions, no double-counted history.
- An item missing its cross-system link fails loud in a log, never
  silently, and never crashes the pipeline for every other item.
- Credentials (GitHub fine-grained PAT, Jira API token) are least-privilege
  and live in secrets storage, never in a repo, never in a log line.
- Status *vocabulary* differences between the two systems ("Done" vs.
  "Closed") are translated explicitly, never assumed to match — a wrong
  exact string sent to either API fails outright.
- Whichever architecture mode ships (real-time serverless via GitHub
  Actions + Jira Automations, or scheduled batch via `dlt` + PostgreSQL, or
  a deliberate combination) is a decision the Spec/architecture phase makes
  explicitly — this Dream does not pre-commit to one over the other.

## What is real

- **The intake material is a single, current document** (v1.1) at
  `docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md`
  — PRD, NFRs, both architecture modes, a concrete normalized PostgreSQL
  schema for both GitHub and Jira, a three-table control-plane bridge layer
  (entity linking, per-field sync-direction config, value translation),
  epics/stories, and an acceptance checklist. Everything from the original
  v1.0 handoff plus two follow-up technical drops, merged in place rather
  than scattered across separate files.
- No code, no GitHub Actions workflow, no Jira Automation rule, no `dlt`
  pipeline exists yet anywhere in this repo. Zero execution weight.
- **Two due-diligence findings already on record, not to re-litigate**:
  **Steampipe** (SQL over both APIs, no dedicated DB needed) was evaluated
  and rejected — its plugins are read-only, ruling it out as Mode B's
  reverse-ETL write path, though it may still be worth a look purely as a
  read-side convenience. **Octosync** (an existing open-source, Dockerized
  GitHub↔Jira sync tool — the closest off-the-shelf match to this Dream's
  own goal) was also evaluated and rejected: unmaintained ~5 years, real
  risk of incompatibility with current API authentication.
- **A known GitHub API limitation is on record**: `updateProjectV2ItemFieldValue`
  (used by both Mode A's Flow A2 and Mode B's reverse-ETL) can update the
  underlying data correctly while leaving the board UI's grouping index
  stale — a moved card can visually appear "stuck" until a manual
  drag-drop. An accepted, documented UX quirk to design around, not a bug
  in this system's own logic (verify against GitHub's issue tracker at
  implementation time whether it's since been fixed).
- **Two competing data-model shapes exist for Mode B, unreconciled on
  purpose**: the original flat single-table sketch (a direct
  `custom_status` column, simpler diff view) versus a fully normalized,
  EAV-style schema plus control plane (more general, handles arbitrary
  custom fields uniformly, needs the bridge tables to make the join
  tractable). Which one Mode B actually ships — and whether the
  control-plane's entity-bridge table *replaces* the original document's
  simpler `custom_jira_key`/`github_item_id` custom-field linking, or the
  two coexist — is an explicit open question for the architecture phase,
  not resolved by either draft existing.
- Not yet clear whether this targets an *external* GitHub/Jira project pair
  or this repo's own tracking — the intake document is written generically
  ("PROJ" as a placeholder project key) and doesn't say. Also an open
  question for whoever runs `bmad-spec` on this Dream.
- **Owner assigned provisionally to `marshal`** — reasoning: this is
  fundamentally an orchestration/sync-pipeline capability (matches
  marshal's harness-owner and cross-system-visibility mandate), and if this
  sync ever targets *this* repo's own GitHub Projects / sprint tracking
  rather than an external project, marshal is the natural consumer.
  `steward` (credential lifecycle, "holds the keys") is the strongest
  alternative, given the NFRs lead with token/secret handling. Worth a
  deliberate call, not treated as settled by this Dream.

## Constraints

- No third-party sync SaaS (Unito, Exalate, etc.) — the intake document's own
  stated non-goal, reinforced by due diligence (Octosync, the closest
  existing off-the-shelf tool, was evaluated and rejected as unmaintained,
  not merely dismissed on principle).
- Zero-loop and idempotency are non-negotiable NFRs, not aspirational —
  whatever mode ships must demonstrate both, not just claim them.
- Credentials never committed, never logged, least-privilege scoped.
- The `updateProjectV2ItemFieldValue` grouping-index limitation must be
  designed around as a known, accepted UX quirk — not silently assumed
  away, and not mistaken for a bug in this system's own logic if it
  surfaces during implementation.

## Non-goals

- Not a request to pick Mode A vs. Mode B here — that decision belongs to
  the architecture phase, informed by real usage patterns (real-time need
  vs. audit-trail/reporting need) this Dream does not have yet.
- Not a request to pick the flat vs. normalized Mode B schema shape either
  — same reasoning, same phase.
- Not (necessarily) about this repo's own project tracking — scope
  (external project vs. this repo) is an open question, not a foregone
  conclusion.

## Realization log

- **2026-08-03** — Captured from a complete, externally-authored PRD/
  architecture write-up (v1.0) handed in whole. Preserved at
  `docs/intake/jira-github-projects-sync/`.
- **2026-08-03** — Two follow-up drops (a recap with a known GitHub API bug
  + Steampipe/Octosync evaluation, and two rounds of concrete PostgreSQL
  DDL — GitHub schema, Jira schema, then the control-plane bridge tables
  that reconcile them) were distilled and merged directly into the intake
  document in place (now v1.1), after first drafting them as a separate
  addendum and then consolidating on explicit instruction: one updated
  intake file, one updated Dream, no satellite documents. The intake file
  was also renamed off "-v1-spec.md" — this repo's Lexicon reserves capital-S
  "Spec" for the BMAD Tier-2 five-field contract, and this document is
  Tier-0 grounding material, not that — to
  "-prd-and-architecture.md", matching what the document actually is per
  its own header. Still not specified, not scoped to a target project, not
  acted on.
