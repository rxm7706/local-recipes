# Manual checklist — Round 0 and the Wizard-of-Oz pilot

Automation of install and publish waits on this list (Story 109.5, CAP-173).

## Round 0 desk test (one person, one project)

Do this in a repository that is not local-recipes.

- [ ] Read `site/index.html` (or `/marketplace/` on the docs site while the flag is on) and open one skill card without a local server. In `site/` the card's relative links into the skill folder do not resolve (no folder sits beside the card there): open `skills/<scope>/<slug>/` by hand
- [ ] Copy that skill's folder into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`
- [ ] Confirm your tool picks the folder up from the directory in the README's tool table (`tool-support-matrix.md` in the design-thinking folder is the source; it records a `Driveable` outcome per tool)
- [ ] Claude Code only: `/plugin marketplace add <checkout>/docs/foundry/marketplace`, then `/plugin install <scope>-<slug>@pyforge-bmad-marketplace`, then `/skills`. Record whether the skill appears. If it does not, `marketplace.json` stays a discovery pointer and the folder copy is the install
- [ ] Codex only: `codex plugin marketplace add <checkout>/docs/foundry/marketplace`. The install and list verbs are unverified: record the exact commands you ran (the Codex CLI's own help names them) and whether `<scope>-<slug>` appears as a skill. If it does not, `.agents/plugins/marketplace.json` stays a discovery pointer and the folder copy is the install
- [ ] Follow `steps.md` from the top
- [ ] Record which step ran, and which step stopped because a `pyforge-*` package is unpublished
- [ ] Record a tool that cannot be driven at all as `tool: <name> — not driveable: <reason>` (an auth wall, a login loop). That is a tool outcome, not a skill failure
- [ ] Confirm no step asked for `pixi run -e` or a path inside local-recipes
- [ ] Confirm the card's unpublished-package list matches what the desk test hit

## Wizard-of-Oz pilot (P4)

Who: two or three teammates, not rxm7706, drawn from this audience: Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin (Cognition AI), and a teammate with no AI tool yet. P4's examples are T1 Cursor and conda or pip, T2 Copilot or Gemini who publishes packages, and T3 no AI tool. Claude Code and Devin are the same audience.

Script: `planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/prototypes/p4-wizard-of-oz-pilot.md`.

Real: the three skill folders in this monorepo, the static cards at `/marketplace/` on the docs site, one Artifactory package when one exists, and a real pull request.

Faked until the exit criteria below: `bmp install`, search, lint and CI, review and promotion, `@bmp/skillify` (a person helps shape `templates/SKILL.md`), and outdated notices.

- [ ] A teammate asks to find a skill. A person replies with the card URL or the folder path. No CLI is required for the reply
- [ ] A teammate asks to install it. A person copies the folder into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/` and says which package is still unpublished
- [ ] A teammate follows `steps.md` on a real task. T3 does that from the steps alone
- [ ] A teammate asks to add a skill. A person uses `templates/SKILL.md`, `templates/steps.md` and the PR template, applied as the README's § Contribute says, and does not publish. That stand-in is `@bmp/skillify` until `bmp new` exists
- [ ] Fill one feedback grid per teammate per task (likes, questions, ideas, changes), plus completed y/n, stuck point, tool, source, and operator interventions
- [ ] Write down the questions the person had to answer that the card did not

## Exit criteria (do not automate before these)

Build only after:

- [ ] `bmp install`: two or more teammates installed a skill with the manual copy and used it in their own tool
- [ ] Lint and clean-machine CI: the manual checks ran on three or more pull requests and caught at least one real problem
- [ ] `bmp publish` / `bmp new`, including `@bmp/skillify`: one teammate other than rxm7706 has merged a skill
- [ ] Search or MCP: people looked for a skill inside their tool first
- [ ] Generated manifests or adapters: a pilot tool failed to pick up the plain folder

Stop if:

- [ ] No teammate uses a seed skill on a real task, or nobody contributes after being asked: stop or rethink

Success:

- [ ] A second teammate installs and uses a skill a first teammate contributed

## Still open from Epic 60

- [ ] `DW-FU-60-1` — recipe and frame inputs still do not trigger a catalog render. This checklist does not close it
- [ ] `DW-FU-60-1-4` — `bmad-method install --custom-source` still finds 0 modules. Copying a skill folder is a different path and does not close it
- [ ] `DW-FRR-60-1` — Story 60.1 still wants an independent follow-up review. This checklist is not that review

## Runbooks

The current Round 0 and Round 1 runbooks are `planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/analysis-against-main-2026-10-27.md`; this file's own history is git's and the 109.3 story spec's.
