# General documentation map (Diátaxis-adapted)

This map applies to the **general-facing documentation layer** only — the material
a newcomer reads to understand, run, and operate this repo. It is adapted from
[Diátaxis](https://diataxis.fr/) to this repo's actual content volume (14 markdown
files + 1 example toml + 1 template subdirectory under pre-22.4 `docs/reference/`,
not hundreds), not a generic four-folder template.

## Four quadrants

| Quadrant | Path | Role | Population status |
|----------|------|------|---------------------|
| **Tutorials / Getting Started** | [`docs/tutorials/`](tutorials/) | Learning-oriented: first working environment, minimal path to success | Populated — [`getting-started.md`](tutorials/getting-started.md) (Story 22.5), [`local-platform-development.md`](tutorials/local-platform-development.md) |
| **How-to Guides** | [`docs/how-to/`](how-to/) | Task-oriented: "how do I do X?" operational instructions | Populated — recipe/pixi/CI/troubleshooting/air-gap + relocated antigravity/manticore (Story 22.5); BMAD station-operations series added 2026-09-17, including one-chain lock/mop; [`troubleshoot-bmad-agent-loops.md`](how-to/troubleshoot-bmad-agent-loops.md) |
| **Reference** | [`docs/reference/`](reference/) | Information-oriented: exact CLI/config/schema surfaces, inventories, examples | Populated — seed from pre-22.4 `docs/reference/` (true reference material retained here); [`station-cheat-sheet.md`](reference/station-cheat-sheet.md), [`agent-memory-lifecycle.md`](reference/agent-memory-lifecycle.md) |
| **Explanation** | [`docs/explanation/`](explanation/) | Understanding-oriented: architecture rationale, "why does this work this way?" | Populated — architecture-rationale files relocated from `docs/reference/` in Story 22.4; one-chain lock/mop rationale added 2026-09-17; [`pyforge-ecosystem-architecture.md`](explanation/pyforge-ecosystem-architecture.md), [`the-tier-model-and-data-flow.md`](explanation/the-tier-model-and-data-flow.md) |

## Outside this map (untouched)

These layers are **explicitly excluded** — they are the spec-and-build pipeline, not
general documentation:

| Layer | Paths | Why excluded |
|-------|-------|--------------|
| Dreams (Tier 0) | `docs/dreams/` | Raw aspirations; Herald/BMAD intake |
| Legacy intake specs (Tier 1) | `docs/specs/` | Superseded hand-authored specs; `shipped`/`superseded` ones now live under `archive/docs/specs/` (Story 23.3) |
| BMAD planning (Tier 2) | `_bmad-output/projects/*/planning-artifacts/` | Active specs, epics, architecture |
| BMAD execution (Tier 3) | `_bmad-output/projects/*/implementation-artifacts/` | Gitignored runtime scratch |
| Tool entry points | `README.md`, `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/` | Agent/human front doors — Story 22.6 corrects pointers into this map, not relocates them |
| Intake inbox | `docs/intake/` | Pre-triage staging; routes elsewhere per [`docs/intake/README.md`](intake/README.md) |
| Governance | `docs/governance/` | Policy corpus; cross-cutting, not Diátaxis-quadrant material |
| Foundry | `docs/foundry/` | Foundry registry, frames and guards — machine-read by detectors, not authored documentation |
| Station/package docs | `src/shared/packages/pyforge-*/README.md`, skill dirs | Station-scoped; link *into* this map where general |
| Publish roots (generated) | `docs/dashboard/` | GitHub Pages upload root, not authored documentation — one subfolder per published dashboard board (see [`docs/dashboard/README.md`](dashboard/README.md)). The PyForge dossier/infographic site (`docsite/build.py`, deployed by `dashboard.yml`) is the one exception, publishing directly at this root rather than its own subfolder. Today only `kedro-viz/` (atlas Kedro-Viz) publishes as a subfolder; a subfolder for another board is created only when that board actually publishes, never minted empty ahead of time |

## One-chain operator layer (2026-09-17)

Operators and coding agents keep a station at one Dream, one Spec, one PRD, one spine, and one epic chain with two Diátaxis pages. Those pages **point at** [`CHAIN-STANDARD.md`](governance/spec-one-chain-per-station/CHAIN-STANDARD.md) (and Spec CAP-10). They do not move Dreams or `docs/governance/` into this map; those layers stay in the exclusion table above.

| Page | Quadrant | Role |
|------|----------|------|
| [`how-to/one-chain-station-ops.md`](how-to/one-chain-station-ops.md) | How-to | Lock, satellite rewrite, mop, parallel work, environment |
| [`explanation/one-chain-lock-and-mop.md`](explanation/one-chain-lock-and-mop.md) | Explanation | Why 1:1 is minting plus `chain-sprawl-check`, not a periodic fold |

Dispatch of already-minted stories stays in [`how-to/driving-a-pyforge-station-backlog.md`](how-to/driving-a-pyforge-station-backlog.md).

## Recipe-factory and agent-hygiene how-tos (Story 22.5 seed)

The recipe/pixi/CI/troubleshooting pages the How-to quadrant was seeded with in Story 22.5, plus the concurrent-activity check.

| Page | Quadrant | Role |
|------|----------|------|
| [`how-to/recipe-testing-and-builds.md`](how-to/recipe-testing-and-builds.md) | How-to | Building and testing individual recipes locally (rattler-build route, Mason-backed route) |
| [`how-to/troubleshooting-recipe-builds.md`](how-to/troubleshooting-recipe-builds.md) | How-to | Fixes for common local recipe build failures |
| [`how-to/pixi-tasks.md`](how-to/pixi-tasks.md) | How-to | Task-oriented reference for the pixi task surface (`local-recipes` recipe-factory env) |
| [`how-to/github-actions-recipe-ci.md`](how-to/github-actions-recipe-ci.md) | How-to | On-demand recipe CI workflows and the repo workflow inventory |
| [`how-to/detect-concurrent-agent-activity.md`](how-to/detect-concurrent-agent-activity.md) | How-to | Telling whether another agent or session is already working on the files you're about to touch |

## Operator and Framework guides (2026-09-19)

These guides map the internal PyForge scripts to their corresponding human operator commands and provide architecture rationale for the underlying frameworks.

| Page | Quadrant | Role |
|------|----------|------|
| [`how-to/run-and-understand-detectors.md`](how-to/run-and-understand-detectors.md) | How-to | Running `detectors-ci` locally and interpreting exit codes |
| [`how-to/reconcile-spec-surface.md`](how-to/reconcile-spec-surface.md) | How-to | Reconciling `spec-surface-check` drift and stamping baselines |
| [`how-to/monitor-the-fleet.md`](how-to/monitor-the-fleet.md) | How-to | Generating a real-time fleet picture and scanning the estate |
| [`how-to/configure-your-coding-agent.md`](how-to/configure-your-coding-agent.md) | How-to | Per-harness setting or command so every coding agent starts from `AGENTS.md`; Claude Code's `agents-md` mode pin and host check |
| [`how-to/manage-worktrees-with-bmad.md`](how-to/manage-worktrees-with-bmad.md) | How-to | Managing worktrees, branch sweeping, and `bmad-switch` caveats |
| [`explanation/the-detector-framework.md`](explanation/the-detector-framework.md) | Explanation | Rationale for dynamic AST-discovery and the 'unknown, never green' inversion |

## Relocated in Story 22.5 (entry-point pointers remain until 22.6)

| Former location | New home | Notes |
|-----------------|----------|-------|
| `README.md` § Quick start, § Building, § Pixi tasks, § GitHub Actions | [`docs/tutorials/getting-started.md`](tutorials/getting-started.md) + [`docs/how-to/`](how-to/) | README now holds temporary pointers only |
| `docs/reference/developer-guide.md` (mixed) | Split across tutorials, how-to, and reference | Reference file retains formats + config |
| `docs/reference/antigravity-developer-startup.md` | [`docs/how-to/antigravity-developer-startup.md`](how-to/antigravity-developer-startup.md) | Redirect stub at old path |
| `docs/reference/manticore-studio.md` | [`docs/how-to/manticore-studio.md`](how-to/manticore-studio.md) | Redirect stub at old path |
| `docs/explanation/enterprise-deployment.md` §1 procedural steps | [`docs/how-to/air-gapped-mirror-setup.md`](how-to/air-gapped-mirror-setup.md) | Explanation doc retains architecture rationale |

## Relocated in Story 23.3

| Former location | New home | Notes |
|-----------------|----------|-------|
| `docs/specs/feedstock-failure-remediation.md` | [`docs/how-to/feedstock-failure-remediation.md`](how-to/feedstock-failure-remediation.md) | Redirect stub at old path |
| `docs/specs/feedstock-platform-expansion.md` | [`docs/how-to/feedstock-platform-expansion.md`](how-to/feedstock-platform-expansion.md) | Redirect stub at old path |
| `docs/specs/presentation-deck.md` | [`docs/how-to/presentation-deck.md`](how-to/presentation-deck.md) | Redirect stub at old path |

## Per-file classification: `docs/reference/` (Story 22.4)

Every file that lived in `docs/reference/` before Story 22.4 is accounted for below.

### Reference quadrant (stay in `docs/reference/`)

| File | Kind | Notes |
|------|------|-------|
| [`container-base-layer-convention.md`](reference/container-base-layer-convention.md) | True reference | Base-tag pinning, multi-stage pixi, secret-mount rules |
| [`pixi-config-jfrog.example.toml`](reference/pixi-config-jfrog.example.toml) | True reference | JFrog pixi config example |
| [`station-verify-commands.md`](reference/station-verify-commands.md) | True reference | Derived verify-command lookup table (**still stale** — refresh tracked separately) |
| [`library-llms-full.md`](reference/library-llms-full.md) | True reference | Generated library catalog (`llms-full-check` gate; **still stale** — regenerate via catalog header prompt) |
| [`github-workflows.md`](reference/github-workflows.md) | True reference | Workflow inventory (**still stale** — audited 2026-07-26; omits/adds workflows vs live tree) |
| [`sync-jira-github-workflow-templates/README.md`](reference/sync-jira-github-workflow-templates/README.md) | True reference | Steward `sync` GitHub Projects V2 ↔ Jira Cloud workflow templates for the *external target* repo, never installed here (see `archive/docs/intake/jira-github-projects-sync/`, archived doctor 23.4) |
| [`test-charter.md`](reference/test-charter.md) | Policy reference | Fleet testing charter (cited by `docs/dreams/pyforge-testing-charter.md`) |
| [`judgement-vocabulary.md`](reference/judgement-vocabulary.md) | Policy reference | What `verdict` / `gate` / `detector` / `check` / `preflight` / `advisory` / `lens` each mean, stated **positively**; the four exit-code domains and the `2` inversion. Restates the Charter's Gate/Track/kernel rulings; rules nothing itself (cited by `docs/dreams/pyforge-charter.md` § The Lexicon) |
| [`conda-forge-packaging-inventory-operations_prompt.md`](reference/conda-forge-packaging-inventory-operations_prompt.md) | True reference | Standalone re-run prompt for inventory runner |
| [`conda-forge-packaging-inventory-operations_replay.md`](reference/conda-forge-packaging-inventory-operations_replay.md) | True reference | Replay/sync contract for inventory runner |
| [`README.md`](reference/README.md) | Index | Reference-quadrant index (this story updates it) |

### Explanation quadrant (relocated to `docs/explanation/`)

| File | Kind | Notes |
|------|------|-------|
| [`pyforge-estate-overview.md`](explanation/pyforge-estate-overview.md) | Architecture rationale | The 8 stations, Canopy architecture, and BMAD methodology |
| [`mcp-server-architecture.md`](explanation/mcp-server-architecture.md) | Architecture rationale | FastMCP tool layer design (**still stale** — tool count may drift; refresh tracked separately) |
| [`enterprise-deployment.md`](explanation/enterprise-deployment.md) | Architecture rationale | Air-gap + Artifactory deployment design (procedural §§ 1–4 flagged for How-to split in Story 22.5, done; §1 "What actually deploys", the mirror-provisioning checklist, and JFROG_API_KEY Pattern D refreshed from the marshal binders in Story 23.2 — remaining sections not re-verified this pass) |
| [`airgap-distribution-contract.md`](explanation/airgap-distribution-contract.md) | Architecture rationale | Mason air-gap distributable contract ("socket, not installer") |

Redirect stubs remain at the former `docs/reference/` paths for moved files until
Story 22.6 updates entry-point links repo-wide. `enterprise-deployment.md` and
`airgap-distribution-contract.md` are the exception — their stubs were deleted (Story 23.2) once
their remaining live inbound references were repointed at `docs/explanation/`.
`mcp-server-architecture.md`'s stub remains (different cluster, untouched).

### Redirect stubs still at the old `docs/reference/` paths

| Stub | Kind | Points at |
|------|------|-----------|
| [`antigravity-developer-startup.md`](reference/antigravity-developer-startup.md) | Redirect stub (Story 22.5) | [`how-to/antigravity-developer-startup.md`](how-to/antigravity-developer-startup.md) |
| [`manticore-studio.md`](reference/manticore-studio.md) | Redirect stub (Story 22.5) | [`how-to/manticore-studio.md`](how-to/manticore-studio.md) |
| [`mcp-server-architecture.md`](reference/mcp-server-architecture.md) | Redirect stub (Story 22.4) | [`explanation/mcp-server-architecture.md`](explanation/mcp-server-architecture.md) |

### Split / relocated in Story 22.5 (complete)

| File | Classification | Result |
|------|----------------|--------|
| [`developer-guide.md`](reference/developer-guide.md) | Reference (split) | Formats, platform matrix, config reference only; pointers to tutorials/how-to |
| [`antigravity-developer-startup.md`](how-to/antigravity-developer-startup.md) | How-to | Moved; redirect stub at old `reference/` path |
| [`manticore-studio.md`](how-to/manticore-studio.md) | How-to | Moved; redirect stub at old `reference/` path |

## Per-file classification: `src/platform/` (Estate Alignment)

Every documentation file relocated from `src/platform/` to align with the central map.

### How-to quadrant (relocated to `docs/how-to/`)

| File | Kind | Notes |
|------|------|-------|
| [`disaster-recovery.md`](how-to/disaster-recovery.md) | How-to | Moved from `src/platform/deploy/DR.md` |
| [`restore-operations.md`](how-to/restore-operations.md) | How-to | Moved from `src/platform/deploy/restore.md` |
| [`ocp-cluster-bringup.md`](how-to/ocp-cluster-bringup.md) | How-to | Moved from `src/platform/deploy/overlays/ocp/cluster-bringup.md` |
| [`ai-engine-operations.md`](how-to/ai-engine-operations.md) | How-to | Operations guide for DB-GPT and Agent platform engines |
| [`station-cli-operations.md`](how-to/station-cli-operations.md) | How-to | Unified PyForge CLI usage and duty discovery |

### Explanation quadrant (relocated to `docs/explanation/`)

| File | Kind | Notes |
|------|------|-------|
| [`platform-deployment-architecture.md`](explanation/platform-deployment-architecture.md) | Architecture rationale | Moved from `src/platform/deploy/README.md` |
| [`platform-requirements.md`](explanation/platform-requirements.md) | Architecture rationale | Moved from `src/platform/requirements/README.md` |

## Archived reference (unchanged)

| File | Location |
|------|----------|
| `GuildHall_Fleet_Status.md` | `archive/docs/reference/` (superseded static snapshot) |

## Downstream stories

| Story | Builds on this map |
|-------|-------------------|
| **22.5** | Populated `docs/tutorials/` and `docs/how-to/`; executed mixed-file splits and pending relocations (done) |
| **22.6** | Corrects `README.md`, `CLAUDE.md`, `AGENTS.md` pointers; fixes broken internal links after relocation |
