# The installed-surface inventory

Derived from the tree 2026-07-31 (the Dream's seeding date). This is the
evidence base CAP-1..5 and Q1..3 cite — the list to argue with, per the
source Dream.

| # | Installed surface | What it is | Marshal's role |
|---|---|---|---|
| 1 | `bmad-loop` 0.9.0 | The engine — run/resume/resolve/sweep/status/attach/stop/clean | **wrap** (never absorb) |
| 2 | `bmad-method` 6.10.0 | 51 skills: planning · dev · review · sprint · personas · research · docs | route + context |
| 3 | BMB `bmad-builder` 2.1.0 | Author custom agents & workflows | route |
| 4 | TEA `…test-architecture-enterprise` 1.19.1 | Risk-based test strategy | route |
| 5 | CIS `…creative-intelligence-suite` 0.2.1 | Brainstorming, design thinking | route |
| 6 | `bmad-manticore` · `bmad-labs-skills` · `bmad-utility-skills` · `bmad-method-wds-expansion` · `bmad-module-template` | Installed, largely unexercised here | **triage — keep, wrap, or remove? (Q2)** |
| 7 | Skill Forge — 16 `skf-*` skills | Skill authoring, campaigns, audits | route |
| 8 | `bmad-dashboard` 1.2.2.dev0 + `docs/dashboard/` | The Guildhall board | own — governed by `spec-factory-console` |
| 9 | Multi-project wiring — `bmad-switch`, marker, two symlinks, six-layer config | Which project is active | own — governed by `spec-multi-loop-isolation` |
| 10 | Loop homes — `bmad-loop-worktree`, `marshal init/homes` | Isolated worktrees per station | own — shipped, governed by `spec-pyforge-marshal` |
| 11 | 10 detectors + the derived registry | drift · chain · surface · story-status · stall · layout · unpushed · … | own (invoke; Doctor judges Marshal's row — [[fidelity-enforcement]] CAP-9) |
| 12 | Tier layout — `docs/dreams/`, `_bmad-output/projects/<station>/` | Dream → Spec → chain → stories | own |
| 13 | Repo gates — linter, `maintenance` label, `environment.yaml` sync, PR lifecycle | What landing requires | own — [[pr-lifecycle]] |
| 14 | `conda-forge-expert` 8.81.0 | The packaging craft (Rule 1: any BMAD agent doing conda work must wield it) | route — **Mason's craft, not Marshal's (boundary test)** |

Rows 8–13 are already owned by Marshal via other specs (noted above) and
are not re-claimed here. Row 6 is Q2. Row 14 is the constraint on craft
ownership. Rows 1–5, 7 are `route` — this Spec's CAP-1..4 are how routing
happens; the skills themselves stay where they are.
