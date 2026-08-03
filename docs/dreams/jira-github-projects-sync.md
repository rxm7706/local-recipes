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

A full draft technical specification already exists — PRD, architecture (two
candidate modes), data model, epics/stories, and an acceptance checklist —
captured verbatim at
`docs/intake/jira-github-projects-sync/jira-github-projects-sync-v1-spec.md`.
This Dream distills the aspiration and cites that document as the load-bearing
source; the deep technical detail (API payloads, SQL views, workflow YAML
shapes) lives there for `bmad-spec` (or the fuller planning chain) to
distill when this Dream moves past `dreamt`.

## What it looks like when real

- Moving a GitHub Projects V2 item's status reaches the linked Jira issue,
  and moving a Jira issue's status reaches the linked GitHub item — in each
  direction, without the human doing anything on the other side.
- The two systems never loop: an update one side makes because of a sync
  never triggers a sync back the other way. The intake spec's own guard-clause
  design (bot-initiator checks on both ends) is the starting mechanism, not
  necessarily the final one.
- Re-processing the same update payload twice produces the same end state
  both times — no duplicate transitions, no double-counted history.
- An item missing its cross-system link (no `github_item_id`, no
  `custom_jira_key`) fails loud in a log, never silently, and never crashes
  the pipeline for every other item.
- Credentials (GitHub fine-grained PAT, Jira API token) are least-privilege
  and live in secrets storage, never in a repo, never in a log line.
- Whichever architecture mode ships (real-time serverless via GitHub
  Actions + Jira Automations, or scheduled batch via `dlt` + PostgreSQL, or a
  deliberate combination) is a decision the Spec/architecture phase makes
  explicitly — this Dream does not pre-commit to one over the other.

## What is real

- The full v1 draft spec (PRD, both architecture modes, ID-mapping table,
  epic/story breakdown, acceptance checklist) is preserved at
  `docs/intake/jira-github-projects-sync/jira-github-projects-sync-v1-spec.md`,
  authored outside this repo and handed in complete.
- No code, no GitHub Actions workflow, no Jira Automation rule, no `dlt`
  pipeline exists yet anywhere in this repo. Zero execution weight.
- **Owner assigned provisionally to `marshal`** — reasoning: this is
  fundamentally an orchestration/sync-pipeline capability (matches marshal's
  harness-owner and cross-system-visibility mandate), and if this sync ever
  targets *this* repo's own GitHub Projects / sprint tracking rather than an
  external project, marshal is the natural consumer. `steward` (credential
  lifecycle, "holds the keys") is the strongest alternative, given the
  NFRs lead with token/secret handling. Worth a deliberate call, not treated
  as settled by this Dream.
- Not yet clear whether this targets an *external* GitHub/Jira project pair
  or this repo's own tracking — the intake spec is written generically
  ("PROJ" as a placeholder project key) and doesn't say. That's an open
  question for whoever runs `bmad-spec` on this Dream, not resolved here.

## Constraints

- No third-party sync SaaS (Unito, Exalate, etc.) — the intake spec's own
  stated non-goal, carried forward.
- Zero-loop and idempotency are non-negotiable NFRs from the intake spec,
  not aspirational — whatever mode ships must demonstrate both, not just
  claim them.
- Credentials never committed, never logged, least-privilege scoped.

## Non-goals

- Not a request to pick Mode A vs. Mode B here — that decision belongs to
  the architecture phase, informed by real usage patterns (real-time need
  vs. audit-trail/reporting need) this Dream does not have yet.
- Not (necessarily) about this repo's own project tracking — scope
  (external project vs. this repo) is an open question, not a foregone
  conclusion.

## Realization log

- **2026-08-03** — Captured from a complete, externally-authored v1 draft
  spec handed in whole. Intake spec preserved at
  `docs/intake/jira-github-projects-sync/`. Not yet specified, not yet
  scoped to a target project, not yet acted on.
