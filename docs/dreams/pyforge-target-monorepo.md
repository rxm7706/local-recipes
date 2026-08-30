---
title: One working tree — python-platform-foundry (the target monorepo)
type: dream
owner: steward
status: specified
---

# One working tree — python-platform-foundry

The **in-repo seed** for the target monorepo directory map. Cursor’s
`.canvas.tsx` is a viewing surface only — it is not git-tracked and must
not be the citation. Fold and cite **this file**. Living *rulings* that
this layout implements sit on [[pyforge-unifying-strategy]] Grounding
2026-08-30.

## The Dream

Stop living in `rxm7706/local-recipes`. The lasting git root is
**`python-platform-foundry`** (Pixi workspace name `pyforge`): eight
stations + the Canopy (`src/platform/`) + spine packages + a **`factory/`**
island for the recipe plant. `local-recipes` is the copy source, then
archive. Do not merge the factory solver farm into the estate `pixi.lock`.
Do not invent a `services/` / `:800x` tree.

## What it looks like when real

- One clone. Agents generate → build → PR without opening `local-recipes`.
- Estate CI never runs the staged-recipes linter on `src/`. Factory CI is
  `paths: factory/**` only.
- Packages live under `src/packages/` (not `src/shared/packages/`). Host
  path-deps django members; no `sys.path` bootstrap, no Containerfile
  `COPY` of django src.
- One skill body under `skills/`; `.claude/skills` and `.cursor/skills`
  are symlinks. Mason’s skill is `skills/domain/conda-forge-expert`.
- Five faces per 03 station. `five_tier` probes the new roots.

## Cutover phases (0–6)

| Phase | Do | Done when |
|---|---|---|
| 0 — Open foundry | Create `rxm7706/python-platform-foundry`. Workspace name `pyforge`. Empty of recipes. Lean pixi. | Clone exists. CI is estate-only. |
| 1 — Move the estate | Fold `src/shared/packages/` → `src/packages/`. Mint django `pixi.toml`. Drop `sys.path`. Skills + BMAD + decks + dreams. | Station envs and host boot in foundry. |
| 2 — Move CFE home | Authoritative skill/scripts/tools → `skills/domain/conda-forge-expert`. Retros land in foundry. | No `MASON_CFE_ROOT` pointing at `local-recipes`. |
| 3 — Factory island | `factory/pixi.toml` + lock (linux/osx/win/build/grayskull/conda-smithy). `factory/recipes/`, `build-locally.py`. | `mason recipe build factory/recipes/…` matches today’s CFE wrap. |
| 4 — Inventory | Move in-flight + sole-maintainer work you still touch. Do not copy the live `recipes/` universe. | `factory/recipes/` is the working set. |
| 5 — Mason → conda-forge | `submit` → staged-recipes (or bot fork). `update` → feedstock maintainer-edit. | An agent PR never opens `local-recipes`. |
| 6 — Archive | README superseded. Disable Azure. Pin last SHA. Keep history. | Default clone is foundry. `.steward` has one git root. |

Gate archive on in-flight Mason CFE rebuild (through-line here; Atlas owns
Slice-3 after 12.8) and Atlas Epic 20 residue. Do not blend Graphify
move-list and the package fold in one story.

## Target tree

```
python-platform-foundry/               # NEW git root — migrate PyForge here from rxm7706/local-recipes
│
├── pixi.toml                           # Workspace OS. Name: pyforge. Lean station envs. No factory linux/osx/win build farm.
├── pixi.lock                           # Estate lock only (stations + host). factory/pixi.lock is separate.
├── environment.yaml                    # Derived export. Regenerate; do not hand-edit.
├── AGENTS.md                           # Neutral entry for every runner. Dream → spec → build.
├── CLAUDE.md, GEMINI.md, …             # Thin pointers TO AGENTS.md. Not a second source of truth.
├── CODEOWNERS                          # Trusted Committer per CLI+UI package and factory/recipes/
├── factory/                            # Recipe plant ISLAND. Own pixi.toml+lock. Not in the pyforge lock.
│   ├── recipes/                        # Working set only — do not clone the live recipes/ universe.
│   ├── pixi.toml + pixi.lock           # linux/osx/win/build/grayskull/conda-smithy only.
│   ├── build-locally.py, .ci_support/  # Staged-recipes-shaped. CI paths: factory/** only.
│   └── conda-forge.yml                 # Factory overlay. Estate CI never reads this.
├── .github/                            # Estate CI. No staged-recipes linter / azure-pipelines factory.
├── .steward/                           # After archive: one git root.
│
├── config/                             # Deploy overlays only. Secrets stay in env / cluster.
│   ├── airgap/
│   ├── stages/                         # all-in-one / local-pod / openshift — not extra Pixi env names.
│   └── feature-flags/
│
├── Containerfile                       # Whole-guild image.
├── src/platform/Containerfile          # Canopy host image.
│
├── src/
│   ├── platform/                       # Canopy. Never import pyforge.*.
│   ├── packages/                       # TARGET packages root. Not Unity src/shared/packages/.
│   │   ├── pyforge-core/               # Spine leaf. Console script pyforge.
│   │   ├── pyforge-<station>/          # CLI cell × 8.
│   │   ├── pyforge-atlas/              # Only Kedro project + Vizro dashboard.
│   │   ├── pyforge-testing-kit/
│   │   ├── django-pyforge/             # Chrome. Mint pixi.toml on migrate.
│   │   └── django-<station>/           # UI + MCP. warden module: django_warden_fabric.
│   ├── ides/                           # Editor adapters. Not Python dists.
│   ├── sentinel/
│   └── domains/<slug>/                 # LATER — Atlas data products. Not a ninth station.
│
├── templates/                          # Copier: station-package / portal / skill / persona.
├── presentations/pyforge-<station>/
├── docs/dreams/                        # This file + unifying strategy.
├── skills/
│   ├── stations/<station>/SKILL.md     # × 7. Mason → domain/conda-forge-expert.
│   ├── personas/<station>/SKILL.md
│   └── domain/conda-forge-expert/
├── .claude/skills/                     # ADAPTER: symlinks → ../../skills/
├── .cursor/skills/                     # ADAPTER: same.
└── .claude/                            # Runtime leftovers only (scripts/tools/data).
```

## Organizing rule

| Face | Path |
|---|---|
| CLI | `src/packages/pyforge-<station>/` |
| UI | `src/packages/django-<station>/` |
| Service | portal `mcp_asgi_app()` on `POST /stations/<name>/mcp` |
| Skill | `skills/stations/<station>/` (mason: `skills/domain/conda-forge-expert`) |
| Agent | `skills/personas/<station>/` |

`pyforge-core` and `django-pyforge` are shared, not a ninth station.

## Do not create / do not carry

`.claude/skills/pyforge-mason/` · a second SKILL.md per IDE · lasting
`bmad-agent-<station>` as the body name · lasting `src/shared/packages/` ·
`src/platform/compliance_face/` as the portal · `src/prototype/` ·
Guildhall `generate.py` · `.appveyor.yml.notused` · `helm/lasuite-docs/` ·
Unity `*-server` farm · nested `src/shared/staged-recipes/` · WFT
`src/tech-domains/` · `services/` or `:800x` · root `docker-compose.yml` ·
`sys.path` for django-* · Containerfile `COPY` of django src.

## Constraints

- **Not a ninth station.** Factory is an island, not a Smith.
- **Not a hexagonal regen.** Fold the same modules onto new paths. Hide
  Unity/Guildhall leftovers only. Sub-agents must see `five_tier.py`,
  `settings/base.py`, and CFE.
- **Layout detail vs ruling.** Tree and phases live here. Hub-and-Spoke =
  one ASGI, Kedro-required, Scribe three ports, fleet conventions — those
  rulings live on [[pyforge-unifying-strategy]].
- **Do not run `bmad-spec` against this file** as a second product chain.
  The Unifying Strategy already bound it (2026-08-30).

## Kinships

[[pyforge-unifying-strategy]] (absorbs the rulings; cites this tree) ·
[[fleet-convention-consistency]] (vocabulary evidence) · [[pyforge-core]] ·
[[pyforge-steward]] (owner of the Canopy through-line) ·
[[pyforge-mason]] (CFE wrap; factory paths).

## Realization log

- **2026-08-28** — Drafted as a Cursor canvas
  (`pyforge-target-directory-map.canvas.tsx`) while the operator forbade
  Dream edits. Live-checked against `local-recipes`.
- **2026-08-30** — Unifying Strategy Grounding bound the rulings. This
  file is the **tracked seed** so clones, BMAD, and `[[wikilinks]]` can
  cite the tree without the canvas. Canvas remains a viewer, not the
  source of record.
