# Conda-Forge Ecosystem Reference

The submission-to-feedstock workflow spans two GitHub orgs: **conda-forge** (the "Forge" — review, build infrastructure, automation) and **prefix-dev** (the modern Rust-based "Tooling" — pixi, rattler-build). This reference maps the repos and docs you'll touch when working on a recipe in this project.

## Local Tooling (this project's stack)

| Repo / Tool | Purpose | Docs |
|-------------|---------|------|
| [`prefix-dev/pixi`](https://github.com/prefix-dev/pixi) | Manages this project's `pixi.toml` env; installs `rattler-build` and other build tools without a separate conda/mamba install | https://pixi.sh/latest/ |
| [`prefix-dev/rattler-build`](https://github.com/prefix-dev/rattler-build) | Build engine for v1 `recipe.yaml` recipes — replaces `conda-build` and is significantly faster | https://rattler-build.prefix.dev/latest/ |
| [`conda/rattler`](https://github.com/conda/rattler) | Underlying Rust library that provides core conda logic for both pixi and rattler-build | https://docs.rs/rattler |
| [`conda-forge/rattler-build-conda-compat`](https://github.com/conda-forge/rattler-build-conda-compat) | Shim that lets rattler-build interoperate with `conda-smithy` linting and feedstock workflows | (README in repo) |
| [`conda-forge/miniforge`](https://github.com/conda-forge/miniforge) | Community installer used to bootstrap build environments inside CI | https://conda-forge.org/miniforge/ |
| [`conda/grayskull`](https://github.com/conda/grayskull) | Recipe generator from PyPI/CRAN metadata — used by `generate_recipe_from_pypi` and the autotick bot | (README in repo) |
| [`conda/conda-build`](https://github.com/conda/conda-build) | Legacy Python-based build engine; still required for v0 `meta.yaml` feedstocks that haven't migrated to v1 | https://docs.conda.io/projects/conda-build/ |
| [`mamba-org/mamba`](https://github.com/mamba-org/mamba) | Fast C++ conda solver; pixi and CI flows use `micromamba` for fast env setup | https://mamba.readthedocs.io/ |
| [`prefix-dev/setup-pixi`](https://github.com/prefix-dev/setup-pixi) | GitHub Action that installs pixi in CI; standard for next-gen feedstock workflows | (README in repo) |
| [`prefix-dev/pixi-build-backends`](https://github.com/prefix-dev/pixi-build-backends) | Collection of pixi build backends (`pixi-build-cmake`, `pixi-build-python`, `pixi-build-rust`, `pixi-build-rattler-build`) — the rattler-build crate referenced under Documentation is one entry in this repo | (README in repo) |
| [`prefix-dev/pixi-pack`](https://github.com/prefix-dev/pixi-pack) | Bundle a pixi env into a portable archive; relevant for the air-gapped flow in `docs/enterprise-deployment.md` | (README in repo) |

## Conda-Forge Submission Pipeline

| Repo | Role |
|------|------|
| [`conda-forge/staged-recipes`](https://github.com/conda-forge/staged-recipes) | Entry point for new recipes. Holds them until they're merged and converted into a feedstock. Ships `pixi.toml` + `build-locally.py` so contributors can build with the same toolchain CI uses. [Docs](https://conda-forge.org/docs/maintainer/adding_pkgs/) |
| [`conda-forge/conda-smithy`](https://github.com/conda-forge/conda-smithy) | Lints recipes (`conda-smithy recipe-lint`), rerenders feedstock CI configs, registers feedstocks with CI providers. Supports both `meta.yaml` and v1 `recipe.yaml`. [Docs](https://conda-forge.org/docs/maintainer/infrastructure/#conda-smithy) |
| [`conda-forge/conda-forge-pinning-feedstock`](https://github.com/conda-forge/conda-forge-pinning-feedstock) | Source of truth for global pins (Python 3.10–3.14, NumPy 2, GCC 14, Clang 19, CUDA 12.9, OpenSSL 3.5, Boost 1.88, …). Both conda-build and rattler-build resolve these. [Docs](https://conda-forge.org/docs/maintainer/pinning_deps/) |
| [`conda-forge/conda-forge.github.io`](https://github.com/conda-forge/conda-forge.github.io) | Source for the conda-forge documentation site itself |
| [`conda-forge/cdt-builds`](https://github.com/conda-forge/cdt-builds) | Core Dependency Tree (CDT) recipes for Linux system libraries (X11, glibc, mesa-libGL); cited as build-only deps in feedstocks linking against system packages |
| [`conda-forge/conda-forge-ci-setup-feedstock`](https://github.com/conda-forge/conda-forge-ci-setup-feedstock) | Helper conda package installed in build envs that configures channels, fetches pinning, and sets CI-specific paths |

## Automation, Bots & Backend

| Repo | Role |
|------|------|
| [`conda-forge/admin-requests`](https://github.com/conda-forge/admin-requests) | Cron jobs and admin scripts that turn merged staged-recipes PRs into standalone feedstock repos and handle ad-hoc admin tasks (mark-broken, transfer ownership, etc.) |
| [`regro/cf-scripts`](https://github.com/regro/cf-scripts) | Codebase for the **autotick bot** (`regro-cf-autotick-bot`) — monitors upstream releases, opens version-bump PRs against feedstocks |
| [`regro/cf-graph-countyfair`](https://github.com/regro/cf-graph-countyfair) | Dependency graph the autotick bot uses to plan migrations across the ecosystem |
| [`conda-forge/conda-forge-metadata`](https://github.com/conda-forge/conda-forge-metadata) | Python package providing API access to conda-forge metadata (PyPI↔conda mappings, feedstock metadata) — used by bots and the local `mapping_manager.py` |
| [`conda-forge/webservices`](https://github.com/conda-forge/webservices) | Backend that handles `@conda-forge-admin` PR commands (rerender, restart ci, lint, add user, …) and Heroku-hosted automation |
| [`conda-forge/feedstock-tokens`](https://github.com/conda-forge/feedstock-tokens) | Manages per-feedstock CI upload tokens |
| [`conda-forge/feedstock-outputs`](https://github.com/conda-forge/feedstock-outputs) | Registry mapping each feedstock to the package outputs it publishes; prevents two feedstocks from claiming the same output name |
| [`conda-forge/conda-forge-repodata-patches-feedstock`](https://github.com/conda-forge/conda-forge-repodata-patches-feedstock) | Post-publish fix mechanism — yanks, dep-pin tweaks, and metadata corrections applied to published packages without rebuilding |
| [`regro/conda-forge-feedstock-check-solvable`](https://github.com/regro/conda-forge-feedstock-check-solvable) | Tool used by webservices/CI to confirm a feedstock's dep tree is satisfiable before merging migration PRs |
| [`conda-forge/conda-forge-feedstock-ops`](https://github.com/conda-forge/conda-forge-feedstock-ops) | Shared Python toolkit for feedstock automation (rerendering, version updates, lint, solvability); imported by webservices, conda-smithy, and the autotick bot |
| [`regro/regro-cf-autotick-bot-action`](https://github.com/regro/regro-cf-autotick-bot-action) | GitHub Action wrapper that runs autotick-bot logic inside a feedstock's own CI workflow |
| [`prefix-dev/parselmouth`](https://github.com/prefix-dev/parselmouth) | PyPI ↔ conda-forge name-mapping data service; powers `mapping_manager.py` in this project's skill (`pypi_mapping_source: parselmouth` in `skill-config.yaml`) |

## Post-Submission

| Pattern | What It Is |
|---------|-----------|
| `<package>-feedstock` | The standalone repo created automatically when a staged-recipes PR is merged. All future updates, builds, and releases happen here — `staged-recipes` is no longer involved for that package. New v1 feedstocks are configured to use rattler-build as the default build tool in CI. |
| `repodata-patches` | When a published package needs a small fix (yank a bad build, tighten an upper bound, correct metadata), file a PR to `conda-forge-repodata-patches-feedstock` to amend the published metadata in-place — no rebuild required |

## Documentation & Knowledge Bases

| Source | Use For |
|--------|---------|
| [conda-forge Maintainer Docs](https://conda-forge.org/docs/maintainer/) | Authoritative reference for recipe authoring, pinning, infrastructure, and CI |
| [conda-forge News](https://conda-forge.org/news/) | Migration announcements, infrastructure changes, policy updates |
| [conda-forge Status Dashboard](https://conda-forge.org/status/) | Currently active migrations |
| [conda-forge Knowledge Base](https://conda-forge.org/docs/maintainer/knowledge_base/) | Common patterns: NumPy, BLAS/LAPACK, multi-output, CUDA, MPI |
| [v1 Recipe Support Announcement](https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/) | Why and how conda-forge adopted rattler-build / `recipe.yaml` |
| [Rattler-Build on Conda-Forge](https://prefix.dev/blog/rattler_build_in_conda_forge) | Practical walkthrough for migrating recipes to v1 |
| [CFEPs](https://github.com/conda-forge/cfep) | Conda-Forge Enhancement Proposals — accepted policy decisions (e.g., CFEP-25 `python_min`, CFEP-26 naming) |
| [Recipe Format Schema](https://github.com/prefix-dev/recipe-format) | JSON schema for `recipe.yaml` — referenced via `# yaml-language-server: $schema=...` at the top of v1 recipes |
| [Publishing to conda-forge (Rattler-Build docs)](https://rattler-build.prefix.dev/latest/publishing/) | End-to-end publishing walkthrough using the Rust toolchain |
| [pixi-build-rattler-build](https://github.com/prefix-dev/pixi-build-backends/tree/main/crates/pixi-build-rattler-build) | Configure pixi to call rattler-build as a build backend in `pixi.toml` |
| [conda-forge Blog](https://conda-forge.org/blog/) | Long-form posts (deep-dives, retrospectives); distinct from News (terse announcements) |
| [conda-forge User Docs](https://conda-forge.org/docs/user/) | End-user channel docs (install, configure); distinct from Maintainer Docs |
| [conda-forge Governance](https://conda-forge.org/docs/orga/) | Org structure, decision-making, code of conduct, CFEP process |
| [conda-forge/by-the-numbers](https://github.com/conda-forge/by-the-numbers) | Source for the conda-forge ecosystem-level statistics dashboard (package counts, build times, contributor data) |

## Community Roles & Personas

The conda-forge + prefix-dev ecosystem is governed by specialized sub-teams and engaged via well-defined personas. When an action needs a human, the table below shows whose lane it falls in.

| Persona / Team | Responsibility Level | Goals | Primary Platform/Tool |
|---|---|---|---|
| [Admin (Core Team)](https://conda-forge.org/community/governance/) | Organization | Governance, security, long-term project health | GitHub Org & Zulip |
| [Security & Systems Sub-team](https://conda-forge.org/community/subteams/) | Infrastructure | Manage bot credentials, API keys, secure system access | GitHub Secrets & API keys |
| [Bot Sub-team](https://conda-forge.org/community/subteams/) | Automation | Maintain the autotick bot; drive mass migrations | `regro/cf-scripts` |
| [Staged-Recipes Team](https://conda-forge.org/community/subteams/) | Gatekeeping | Review and approve new package submissions | `conda-forge/staged-recipes` |
| [Prefix.dev Team (Pixi)](https://github.com/prefix-dev/pixi) | Main Development | Build high-performance pixi/rattler tooling | `prefix-dev/pixi`, `prefix-dev/rattler-build` |
| [Documentation Sub-team](https://conda-forge.org/community/subteams/) | Knowledge | Keep docs accurate; expand onboarding | `conda-forge/conda-forge.github.io` |
| [Financial Sub-team](https://conda-forge.org/community/subteams/) | Budget | Track funds; coordinate with NumFOCUS | Core budget items |
| [Feedstock Maintainer](https://conda-forge.org/docs/maintainer/) | Package | Keep specific package builds functional and current | Individual `<pkg>-feedstock` repo |
| [Package Requester](https://conda-forge.org/docs/maintainer/adding_pkgs/) | Contribution | Submit new recipes via staged-recipes | YAML recipes |
| [Consumer (User)](https://pixi.sh/) | Usage | Solve environments; run project code | pixi, conda, mamba CLI |

### Role Descriptions

- **Security & Systems** — Keymaster for the org; performs ongoing maintenance and provisions new core members with access to internal systems.
- **Bot Sub-team** — Manages the automated workforce. When a major library (NumPy 2, GCC 14, …) updates, this team triggers the migration that opens version-bump PRs across every dependent feedstock.
- **Prefix.dev (Pixi development)** — Conda-forge provides packages; this team builds the engine. Focus is "faster, faster, faster" and cross-platform stability for complex stacks (e.g., ROS).
- **Staged-Recipes Reviewers** — The front desk. Every Package Requester passes through review to ensure metadata and build scripts are safe and high-quality before a feedstock is created.
- **Feedstock Maintainer** — Day-to-day owner of one or more `<pkg>-feedstock` repos. Reviews autotick PRs, fixes CI failures, manages co-maintainers via `@conda-forge-admin add user @x`, and rerenders when CI configs need refresh.

## Community Channels

| Channel | Status |
|---------|--------|
| [Zulip](https://conda-forge.zulipchat.com/) | **Primary** real-time channel for help, troubleshooting, announcements |
| [conda-forge News](https://conda-forge.org/news/) | Posted announcements (also surfaced in Zulip) |
| [Discourse](https://conda.discourse.group/) | **Read-only** since Oct 15, 2025 — search archive only |
| Gitter | Decommissioned; replaced by Zulip |

## Channel Storefronts

| Storefront | Use For |
|------------|---------|
| [Anaconda.org/conda-forge](https://anaconda.org/conda-forge) | Original front-end; package search, build status badges, owner info |
| [prefix.dev/channels/conda-forge](https://prefix.dev/channels/conda-forge) | Modern front-end; faster search, cleaner UI |
