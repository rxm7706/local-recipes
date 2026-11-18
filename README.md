<!-- marshal-seed:begin region=model-badge model-version=1.0.0 sha=f66b7e29 -->
> **Dream-first repo.** This project follows the Dream → Spec → build model: every
> non-trivial change starts as a Dream in `docs/dreams/`, BMAD distils it into a spec under
> `_bmad-output/projects/<slug>/planning-artifacts/`, and the spec drives the build. See
> `AGENTS.md` for the full cross-tool contract.
<!-- marshal-seed:end region=model-badge -->
# local-recipes

[![Test All Platforms](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml)
[![Test Linux](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml)
[![Test Windows](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml)
[![Test macOS](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml)

This repository is the PyForge control plane and the host of its BMAD-driven development process. It holds three things:

- **The planning chain.** Dreams in `docs/dreams/`, and the Specs, epics and ledgers BMAD derives from them under `_bmad-output/projects/<station>/planning-artifacts/`.
- **The code.** A Django + Wagtail host at `src/platform/`, and the eight station packages (`pyforge-atlas`, `-doctor`, `-herald`, `-marshal`, `-mason`, `-scribe`, `-steward`, `-warden`) with their kernel (`pyforge-core`, `pyforge-testing-kit`) and `django-*` portals under `src/shared/packages/`. Python 3.14, managed by pixi.
- **The conda-forge recipe factory.** A staged-recipes style workspace in `recipes/`, driven by the `conda-forge-expert` skill. It is one part of the repository, not the whole of it.

[`AGENTS.md`](AGENTS.md) is the contract every contributor and coding agent follows. It is the authority where this page and it differ.

## Start here

| You want to | Read |
|---|---|
| Set up and run your first recipe build | [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md) |
| Find any other page | [`docs/MAP.md`](docs/MAP.md), the documentation map |
| See what each station's CLI does | [`docs/reference/station-cheat-sheet.md`](docs/reference/station-cheat-sheet.md) |
| Pick a pixi environment | [`docs/reference/environments.md`](docs/reference/environments.md) |
| Look up a pixi task | [`docs/how-to/pixi-tasks.md`](docs/how-to/pixi-tasks.md) |
| Build and test recipes | [`docs/how-to/recipe-testing-and-builds.md`](docs/how-to/recipe-testing-and-builds.md) |
| Understand the recipe CI behind the badges | [`docs/how-to/github-actions-recipe-ci.md`](docs/how-to/github-actions-recipe-ci.md) |

Two pixi environments cover most work: `pyforge-guild` is the default for station code, detectors and docs; `local-recipes` is the recipe factory.

## Recipes

Recipes are written in either the modern Rattler Build format (`recipe.yaml`) or the legacy conda-build format (`meta.yaml`). Do not mix the two formats in one build run: the tooling rejects it.

The build helpers at the repository root (`build-locally.py`, `test-recipes.py`, `.ci_support/build_all.py`, `.scripts/`, `conda_build_config.yaml`, `environment.yaml`) are explained in the tutorial and the how-to guide linked above.

## Project structure (selected)

```
local-recipes/
├─ AGENTS.md                       # Cross-tool contract for contributors and agents
├─ CLAUDE.md, GEMINI.md            # Per-tool addenda that point at AGENTS.md
├─ pixi.toml, pixi.lock            # Environments, dependencies and tasks
├─ pyforge.toml                    # PyForge workspace settings
├─ docs/
│  ├─ MAP.md                       # Documentation map
│  ├─ tutorials/, how-to/, reference/, explanation/
│  ├─ dreams/                      # Dreams: the starting point of every effort
│  ├─ governance/, foundry/        # Fleet standards; the capability ledger
│  └─ intake/, dashboard/          # Brownfield intake; generated publish root
├─ docs-site/                      # Astro Starlight build of docs/
├─ _bmad/                          # BMAD installation and custom overrides
├─ _bmad-output/
│  ├─ PROJECTS.md                  # Project index
│  └─ projects/<slug>/             # Planning and implementation artifacts per station
├─ src/
│  ├─ platform/                    # Django + Wagtail host
│  └─ shared/packages/             # pyforge-* station and kernel packages, django-* portals
├─ recipes/
│  ├─ <recipe>/recipe.yaml         # Rattler Build format (modern)
│  └─ <recipe>/meta.yaml           # conda-build format (legacy)
├─ .ci_support/                    # build_all.py and per-platform variant configs
├─ .scripts/                       # Platform build runners (Linux, macOS, Windows)
├─ build-locally.py                # Cross-platform build dispatcher
├─ test-recipes.py                 # Direct recipe testing script
├─ environment.yaml                # Bootstrap environment, generated from pixi.toml
├─ conda_build_config.yaml         # Global pinning and variants
├─ scripts/                        # Detectors, generators and repo helpers
├─ presentations/                  # Decks rendered from Dreams
├─ archive/                        # Retired documents, kept for history
└─ .github/workflows/              # CI: recipe builds, station tests, detectors, Pages
```

## License

See `LICENSE` and `LICENSE.txt`.
