# Manual checklist — Round 0 and the Wizard-of-Oz pilot

Automation of install and publish waits on this list (Story 109.5, CAP-173).
The pages are a reading surface. They are not an install button.

Re-checked 2026-10-25 against `origin/main` (`81f66ee411`). The steps are the same.
Re-checked 2026-10-27 against `origin/main` (`b306864227`). The steps are the same.
The current runbooks are `planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/analysis-against-main-2026-10-27.md`.
Atlas's CVE boards, `marshal-mcp`, the new flags, and the conda-forge graph split are not listings. Do not invent a GHES mirror.

## Round 0 desk test (one person, one project)

Do this in a repository that is not local-recipes.

- [ ] Read `site/index.html` and open one skill card without a local server
- [ ] Copy that skill's folder into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`
- [ ] Confirm Claude Code picks the folder up from `.claude/skills/` (its documented project skill path; the tool matrix marks `.agents/skills/` as uncertain for Claude Code)
- [ ] Confirm Devin (Cognition AI) picks the folder up from `.agents/skills/` (the matrix does not list `.claude/skills/` for Devin)
- [ ] Confirm Cursor, GitHub Copilot in VS Code, and Google Gemini pick the same folder up. Cursor and Copilot read both directories. Gemini CLI reads `.agents/skills/`
- [ ] Follow `steps.md` from the top
- [ ] Record which step ran, and which step stopped because a `pyforge-*` package is unpublished
- [ ] Confirm no step asked for `pixi run -e` or a path inside local-recipes
- [ ] Confirm `conda-lock`, `pyproject-build` or `python -m build`, `pixi build`, `deptry`, and `osv-scanner` are the only published commands the three pilot skills ask a teammate to run, and that `warden scan` / `pyforge mason` stay behind the unpublished packages
- [ ] Confirm the card's unpublished-package list matches what the desk test hit

## Wizard-of-Oz pilot (P4)

Who: two or three teammates, not rxm7706, drawn from this audience: Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin (Cognition AI), and a teammate with no AI tool yet. P4's examples are T1 Cursor and conda or pip, T2 Copilot or Gemini who publishes packages, and T3 no AI tool. Claude Code and Devin are the same audience. The full script is `planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/prototypes/p4-wizard-of-oz-pilot.md`. The path each tool reads is `tool-support-matrix.md` in that folder: Claude Code `.claude/skills/`, Devin `.agents/skills/`.

Real: the three skill folders in this monorepo, the static cards at `/marketplace/` on the docs site, one Artifactory package when one exists, and a real pull request. The open question is which internal mirror of local-recipes, not a separate marketplace repository. Faked until the gates below: `bmp install`, search, lint and CI, review and promotion, `@bmp/skillify` (a person helps shape `templates/SKILL.md`), and outdated notices.

- [ ] A teammate asks to find a skill. A person replies with the card URL or the folder path. No CLI is required for the reply
- [ ] A teammate asks to install it. A person copies the folder into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/` and says which package is still unpublished
- [ ] A teammate follows `steps.md` on a real task. T3 does that from the steps alone
- [ ] A teammate asks to add a skill. A person uses `templates/SKILL.md` and `.github/PULL_REQUEST_TEMPLATE.md` and does not publish. That stand-in is `@bmp/skillify` until `bmp new` exists
- [ ] Fill one feedback grid per teammate per task (likes, questions, ideas, changes), plus completed y/n, stuck point, tool, source, and operator interventions
- [ ] Write down the questions the person had to answer that the card did not

### Exit criteria (do not automate before these)

- [ ] Build `bmp install` only after two or more teammates installed a skill with the manual copy and used it in their own tool
- [ ] Build lint and clean-machine CI only after the manual checks ran on three or more pull requests and caught at least one real problem
- [ ] Build `bmp publish` / `bmp new`, including `@bmp/skillify`, only after one teammate other than rxm7706 has merged a skill
- [ ] Build search or MCP only if people looked for a skill inside their tool first
- [ ] Build generated manifests or adapters only if a pilot tool failed to pick up the plain folder
- [ ] Stop or rethink if no teammate uses a seed skill on a real task, or nobody contributes after being asked
- [ ] Success moment: a second teammate installs and uses a skill a first teammate contributed

## Still open from Epic 60

- [ ] `DW-FU-60-1` — recipe and frame inputs still do not trigger a catalog render. This checklist does not close it
- [ ] `DW-FU-60-1-4` — `bmad-method install --custom-source` still finds 0 modules. Copying a skill folder is a different path and does not close it
- [ ] `DW-FRR-60-1` — Story 60.1 still wants an independent follow-up review. This checklist is not that review
