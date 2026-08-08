---
stepsCompleted: [1, 5]
inputDocuments:
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-code-bridge/SPEC.md (settled kernel — not researched)'
  - 'docs/dreams/pyforge-herald.md'
  - 'docs/dreams/ecosystem-crew.md § 1 Herald'
workflowType: 'research'
lastStep: 5
research_type: 'market'
research_topic: 'Herald''s unspecced half: `herald updates compile` (release-notes/changelog automation from run telemetry) and `herald broadcast` (omnichannel delivery of compiled updates)'
research_goals: 'Light, focused grounding (3-4 analogues, not a full market study) for the product brief''s scope of the two Herald capabilities not yet covered by the settled Design-Code Bridge spec. The bridge (CAP-1..5) is intentionally NOT researched here.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
---

# Research Report: market

> **Refreshed 2026-08-08** — findings confirmed still valid, with one inversion (the
> telemetry-native-sourcing differentiator did **not** ship; v1 sources from operator-typed
> flags) and a category shift now that Moments 2–4 shipped scaled-down. See
> `market-herald-post-ship-landscape-research-2026-08-08.md` §2.

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** market (light/express — analogue scan, not a full market study)

---

## Research Overview

Herald's flagship capability, the Design↔Code bridge CLI, is fully specced with zero open
questions (`planning-artifacts/specs/spec-design-code-bridge/`) and is out of scope here. This
report covers only the **unspecced half** of Herald's charter — `herald updates compile`
(turning pyforge's own build telemetry into weekly notables/executive highlights) and
`herald broadcast` (delivering those compiled updates across Slack/email/wiki channels) — per
the Dream's "frontier" and the CLI cadence sketched in `ecosystem-crew.md` § 1. Four analogues
were surveyed across the two capability classes: **commit/fragment-driven changelog automation**
(release-please, towncrier) and **cross-repo digest + omnichannel release-comms delivery**
(AI weekly-digest tools in the Gitmore class, Slack Workflow Builder + LaunchNotes-style
multi-channel release announcements). Headline finding: none of the four analogues source from
a project's own *internal* pipeline telemetry (sprint-status.yaml, gate reports, build-artifact
JSON) the way Herald's Dream specifies — they all source from **git/PR history** or a
**generic activity feed**. Herald's differentiator is telemetry-native sourcing (Warden/Atlas/
Mason JSON, sprint-status, gate reports) rather than commit-message parsing — this is the one
pattern to explicitly diverge from, not borrow.

---

## Analogue Landscape

### 1. release-please (Google) — commit-driven changelog + version-bump automation

Parses `git log` for Conventional Commit messages (`feat:`, `fix:`, …) and maintains a
standing "Release PR" with an auto-generated `CHANGELOG.md` + version bump; merging the PR cuts
the release. Over 20 language strategies, monorepo-aware via manifest config. **Ingests:** git
commit history (structured message convention required). **Delivers to:** a GitHub PR + tag —
single-channel, repo-native.
_Source: [release-please](https://github.com/googleapis/release-please), [release-please-action](https://github.com/googleapis/release-please-action)_

### 2. towncrier — fragment-file changelog aggregation

Rejects commit-message parsing entirely: contributors drop one small "news fragment" file per
change (`changelog.d/<issue>.feature.md`), and a release step concatenates them into the
changelog, avoiding both merge-conflict-prone shared CHANGELOG edits and the rigidity of a
commit-message convention. Used by Twisted, pytest, pip, attrs. **Ingests:** hand-authored
fragment files (curated, not derived). **Delivers to:** a single `CHANGELOG.md`.
_Source: [towncrier](https://github.com/twisted/towncrier)_

**Pattern for Herald:** both tools prove that "derive strictly from git history" and "curate
by hand" are the two poles of changelog automation, and both stop at a single markdown file —
neither compiles a *narrative* update (notables + infographics) or pushes it anywhere. Herald's
`updates compile` sits architecturally closer to towncrier's curated-fragment model than
release-please's commit-parse model, except the "fragments" are Herald's own structured
telemetry (sprint-status deltas, gate-pass/fail events, Warden/Atlas run summaries) rather than
hand-authored files — i.e., machine-authored fragments from telemetry, not commits or humans.

### 3. AI cross-repo weekly-digest tools (Gitmore class)

A newer (2025-2026) tool class — Gitmore is the representative example — connects to
GitHub/GitLab/Bitbucket, monitors commits/PRs/issues across *all* repos in scope, and produces
an AI-summarized narrative digest ("the team focused on the checkout-flow refactor…") rather
than a raw commit list, with automatic work categorization (feature/bugfix/refactor/devops/
docs) and scheduled Slack or email delivery on a daily/weekly/custom cadence. Positioned
explicitly for both distributed-team coordination and leadership visibility.
**Ingests:** git/PR/issue activity via OAuth+webhooks (cross-repo). **Delivers to:** Slack
channel or email, on a schedule.
_Source: [GitHub Activity Digest & Notification Tools 2026](https://gitmore.io/blog/github-activity-digest-notification-tools)_

**Pattern for Herald:** the categorization + narrative-over-raw-list approach is the right shape
for `updates compile --include notables,infographics` — but Gitmore-class tools still source
from git/PR activity, never from a factory's own structured pipeline output (gate reports,
compliance scores, epic/story completion). Herald should borrow the narrative-digest UX and
explicitly diverge on sourcing: pyforge's `sprint-status.yaml`, Warden `ComplianceReport`,
Atlas run summaries, and `docs/dashboard/data.js`-shaped telemetry are the source of record, not
commit messages — this keeps `updates compile` deterministic and traceable to the artifacts
Marshal's loop already produces, rather than re-deriving intent from prose commit subjects.

### 4. Omnichannel release-announcement delivery (Slack Workflow Builder + LaunchNotes)

Two complementary patterns for the `broadcast` half:
- **Slack Workflow Builder (webhook trigger):** a CI/CD step POSTs a JSON payload to a
  Slack-generated webhook URL, which fires a pre-built workflow (e.g. "post release notes to a
  selected channel"). Slack's own developer docs ship this as a named example — "post release
  announcements." **Limitation:** webhook step failures are silent — no built-in retry or error
  surfacing, and workflow definitions live only in Slack's UI, not as exportable code.
  _Source: [Slack docs — post release announcements](https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-webhook-slack-workflow/post-release-announcements/), [Slack Workflow Builder guide](https://slack.com/help/articles/360035692513-Guide-to-Slack-Workflow-Builder)_
- **LaunchNotes-style release-communication platforms:** "write once, reach subscribers
  wherever they are" — in-app widget, Slack, Microsoft Teams, email, and RSS from one compiled
  update, with per-audience customizable digest cadence.
  _Source: [LaunchNotes](https://www.launchnotes.com/release-notes-tool)_

**Pattern for Herald:** `broadcast slack,email --channel … --file weekly_brief.json` should
adopt LaunchNotes' "compile once, fan out per-channel adapter" shape (a channel is a thin
delivery adapter over one canonical compiled artifact) rather than Slack Workflow Builder's
UI-only, single-channel, silently-failing webhook model — and should explicitly plan for
structured delivery failure (each channel adapter reports success/failure, no silent drops),
which none of the surveyed tools handle well.

---

## Divergence Summary (what NOT to borrow)

- **Do not** adopt commit-message parsing (release-please) or hand-authored fragment files
  (towncrier) as Herald's primary source — pyforge already produces richer structured telemetry
  (sprint-status, gate reports, ComplianceReports) that a commit-message convention would
  discard.
- **Do not** adopt Slack Workflow Builder's UI-only, non-exportable, silently-failing webhook
  model for `broadcast` — Herald's bridge half already established a deterministic,
  structured-failure discipline (SPEC-design-code-bridge's etag/conflict handling); `broadcast`
  should hold the same bar (explicit per-channel success/failure, no silent no-ops).
- **Do** borrow: towncrier's "small structured units aggregate into one release artifact" shape,
  Gitmore-class narrative categorization over raw event lists, and LaunchNotes' one-canonical-
  artifact/many-channel-adapters delivery shape.

---

## Sources

- [release-please](https://github.com/googleapis/release-please)
- [release-please-action](https://github.com/googleapis/release-please-action)
- [towncrier](https://github.com/twisted/towncrier)
- [GitHub Activity Digest & Notification Tools (2026)](https://gitmore.io/blog/github-activity-digest-notification-tools)
- [Slack docs — post release announcements](https://docs.slack.dev/tools/slack-github-action/sending-techniques/sending-data-webhook-slack-workflow/post-release-announcements/)
- [Slack Workflow Builder guide](https://slack.com/help/articles/360035692513-Guide-to-Slack-Workflow-Builder)
- [LaunchNotes](https://www.launchnotes.com/release-notes-tool)

---

**Market Research Completion Date:** 2026-07-25
**Scope:** Light/express — 4 analogues across 2 capability classes, per orchestrator directive
to not re-research the settled Design-Code Bridge half.
