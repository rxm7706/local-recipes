# Manual checklist — Round 0 and the Wizard-of-Oz pilot

Automation of install and publish waits on this list (Story 109.5, CAP-173).
The pages are a reading surface. They are not an install button.

## Round 0 desk test (one person, one project)

Do this in a repository that is not local-recipes.

- [ ] Read `site/index.html` and open one skill card without a local server
- [ ] Copy that skill's folder into `.agents/skills/<name>/` and `.claude/skills/<name>/`
- [ ] Follow `steps.md` from the top
- [ ] Record which step ran, and which step stopped because a `pyforge-*` package is unpublished
- [ ] Confirm no step asked for `pixi run -e` or a path inside local-recipes
- [ ] Confirm `conda-lock`, `pyproject-build` or `python -m build`, `pixi build`, `deptry`, and `osv-scanner` are the only published commands the three pilot skills ask a teammate to run, and that `warden scan` / `pyforge mason` stay behind the unpublished packages
- [ ] Confirm the card's unpublished-package list matches what the desk test hit

## Wizard-of-Oz pilot (a second person asks, a person answers)

- [ ] A teammate asks to find a skill. A person replies with the card URL or the folder path. No CLI is required for the reply
- [ ] A teammate asks to install it. A person copies the folder into both skill directories and says which package is still unpublished
- [ ] A teammate asks to add a skill. A person uses `templates/SKILL.md` and `.github/PULL_REQUEST_TEMPLATE.md` and does not publish
- [ ] Write down the questions the person had to answer that the card did not
- [ ] Only after those notes exist does Story 109.4 (`bmp`) or a publish lane start

## Still open from Epic 60

- [ ] `DW-FU-60-1` — recipe and frame inputs still do not trigger a catalog render. This checklist does not close it
- [ ] `DW-FU-60-1-4` — `bmad-method install --custom-source` still finds 0 modules. Copying a skill folder is a different path and does not close it
- [ ] `DW-FRR-60-1` — Story 60.1 still wants an independent follow-up review. This checklist is not that review
