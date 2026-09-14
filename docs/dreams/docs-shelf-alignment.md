---
title: One home for leftover docs — fold into Diátaxis, same page for agents and humans
type: dream
owner: doctor
status: specified
---

# One home for leftover docs — fold into Diátaxis, same page for agents and humans

> **Seed Dream.** Operator asked 2026-09-14 to make the leftover-docs sweep
> repeatable as Dream → Spec → stories, not a chat cleanup. This is the
> **residue** of [[general-docs-consistency]] after Epic 22 shipped — not a
> reopen of that realized campaign. Scribe recall the same morning
> (`scribe recall "general documentation Diátaxis docs alignment shelf fold"
> --mode planning`) → **no grounded answer** beyond the shipped Spec.

## The Dream

The general-facing documentation layer has **one home per fact**, in the
Diátaxis-adapted tree [[general-docs-consistency]] already designed
(`docs/MAP.md`, tutorials / how-to / reference / explanation). Related pages
fold into that one page. `AGENTS.md`, `CLAUDE.md`, `README.md`, and station
`SKILL.md`s are **indexes and wielding notes** — they point, they do not
restate. If a page is useful to a human operator, it is useful to an agent;
there is no second binder "for humans only."

Leftover shelf prose — root notes, intake dumps, dated campaign stamps,
legacy `docs/specs/` husks, and brownfield guides that duplicate the
quadrants — is routed: fold, archive, or keep as a named exception on the
MAP. The routing is a **repeatable capability**, not a one-session canvas.

## Why this is a sibling, not a reopen

[[general-docs-consistency]] is `realized`. Epic 22 (Stories 22.1–22.6)
fixed identity contradictions, shipped `general_docs_consistency`, designed
the map, populated tutorials/how-to, and repointed entry files. Its Spec
`spec-general-docs-consistency` is `shipped`. CAP-4..6 **explicitly forbade**
touching `docs/specs/` and `_bmad-output/*/planning-artifacts/`.

That prohibition is why the leftover shelf is still here. This Dream
**widens** that non-goal for a second campaign: sunset legacy Tier-1 specs
*by their own `status:` frontmatter*, and **extract** unique operational
prose from marshal brownfield binders into `docs/` (the planning tree stays;
the binder becomes a stub). CAP-1..6 stay shipped. Nothing here unships them.

## What is real (measured 2026-09-14, not remembered)

- `docs/MAP.md` exists and names four quadrants plus an "outside this map"
  table. Story 22.6 shipped (`local-recipes#1257`) and still left
  **redirect stubs** at `docs/reference/{manticore-studio,antigravity-developer-startup,mcp-server-architecture,enterprise-deployment}.md`.
- Legacy `docs/specs/*.md` **do** have disposition: YAML `status`
  (`shipped` / `workflow` / `in-progress` / `superseded`). Live split:
  3 `workflow` (presentation-deck, feedstock-platform-expansion,
  feedstock-failure-remediation), 2 `in-progress` (feedstock-refresh, flyte),
  the rest shipped or superseded. `bmad-drift --specs` and `CLAUDE.md`'s
  index still read this folder.
- Intake dumps have **no** per-file `status:` / `disposition:`.
  `docs/intake/README.md` and `docs/intake/gists/INDEX.md` are the ledgers.
  Open folders named there: `agentic-sdlc/` (feeds pitched
  [[agentic-sdlc-autonomy]]), `jira-github-projects-sync/` (Dream
  `specified`), `secure-live-dashboards/` (Dream `specified` — intake is
  leftover). Five `_bmad-output/` root notes already moved to
  `archive/_bmad-output/`; inbound citations still point at the old paths.
- Marshal `development-guide.md` says it is **for humans**; agents should
  read `project-context.md` and `SKILL.md`. That split is the same failure
  mode Epic 22's CAP-2 already punished in README vs CLAUDE. The file is
  also a mixed tutorial+how-to+reference binder whose header disagrees with
  itself on pixi env/task counts.
- Air-gap facts live in at least three places:
  `docs/explanation/enterprise-deployment.md`,
  `docs/how-to/air-gapped-mirror-setup.md`, marshal `deployment-guide.md`,
  plus the `docs/reference/enterprise-deployment.md` stub.
- `docs/dashboard/` is a **publish root**, not a quadrant. The live tree is
  already `docs/dashboard/kedro-viz/` (generated Pages upload). Vizro is a
  different product ([[secure-live-dashboards]]). Do not rename kedro-viz
  to vizro.
- Operator pass-2 rule, accepted in the shelf-sweep canvas: **one owner per
  fact, in `docs/`**. Fold clusters, not thirty one-off moves.

## What it looks like when real

- A newcomer and an agent hit the same tutorial / how-to / reference /
  explanation page for the same fact. Entry points are thin pointers.
- The three `workflow` legacy specs have become how-tos (or a how-to plus
  archived husk). Shipped and superseded Tier-1 files live under
  `archive/docs/specs/`. The two in-progress files stay until those
  efforts close, then archive.
- Intake is empty of anything a Dream already specified or absorbed.
  Gist leftovers follow `INDEX.md`.
- Marshal brownfield binders are stubs that point at `docs/`. Unique
  steps were folded, not copied a third time.
- `archive/_bmad-output/` citations resolve. Redirect stubs are gone
  after the pointer sweep.
- A Doctor check (or an extension of `general_docs_consistency` / MAP
  hygiene) fails when a new leftover-shelf file appears outside the map
  and the intake/archive rules — warn-only, fail-open, never a second
  PR gate.

## Non-goals

- Reopening or rewriting Epic 22 / CAP-1..6. Identity fixes and the
  existing detector stay as shipped.
- Moving Dreams, active Tier-2 Specs, or gitignored Tier-3 output into
  Diátaxis. Extracting *duplicate operational prose* from a brownfield
  guide is in scope; relocating `epics.md` is not.
- Regenerating accurate prose "for consistency." Fold and correct;
  do not rewrite from scratch.
- Renaming `docs/dashboard/kedro-viz/` to vizro.
- Minting Dream YAML onto raw gist dumps.
- A full editorial pass of every skill, presentation, or recipe README.

## Kinships

- [[general-docs-consistency]] — parent; realized; this is the residue.
- [[bmad-output-hygiene]] — archived; same class of leftover
  `_bmad-output/` debris, already campaigned once.
- [[secure-live-dashboards]] — specified; owns the Vizro pattern, not
  the kedro-viz publish tree.
- [[agentic-sdlc-autonomy]] — pitched/specified; owns `docs/intake/agentic-sdlc/`.
- [[jira-github-projects-sync]] — specified; owns that intake folder
  until the operator decision.
- [[enterprise-airgap]] — realized; air-gap fold must not invent a
  second contract.
- [[pyforge-marshal]] — brownfield binders live under its planning tree.
- [[pyforge-doctor]] — owning station; detector half.

## Settled 2026-09-14 (Spec `ready`)

1. **Workflow specs — stub, not a full move.** Archive shipped/superseded
   to `archive/docs/specs/`. Keep `in-progress` in place. Move each
   `workflow` body to `docs/how-to/`; leave `docs/specs/<name>.md` as a
   stub with `status: workflow` so `bmad_drift_check.py --specs` and the
   CLAUDE.md filename index still see them.
2. **Brownfield — extract, then stub.** Unique operational steps go to
   Diátaxis. Binders become pointers to `docs/` plus `SYNC-RUNBOOK.md`
   for pin re-ground. Do not keep a humans-vs-agents pair.
3. **New Doctor source**, not an extension of `general_docs_consistency`
   (that module is identity-only).
4. **Doctor Epic 23.** Steward stays kinship only.
5. **Do not mint `docs/dashboard/vizro/` now.** MAP states the rule;
   the directory appears when that board publishes.

`spec-docs-shelf-alignment` is `ready`. Epic 23 decomposes CAP-1..7.
