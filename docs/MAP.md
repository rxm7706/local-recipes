# General documentation map (Diátaxis-adapted)

This map applies to the **general-facing documentation layer** only — the material
a newcomer reads to understand, run, and operate this repo. It follows
[Diátaxis](https://diataxis.fr/): four quadrants under `docs/`, each with a `README.md`
index. Every page is registered in [`docs/map.yaml`](map.yaml), and the
[page registry](#page-registry-generated) at the end of this file is rendered from it.
The sections between describe what sits outside the map and group some pages by topic;
they are not a complete list.

## Four quadrants

| Quadrant | Path | Role | Index |
|----------|------|------|-------|
| **Tutorials / Getting Started** | [`docs/tutorials/`](tutorials/) | Learning-oriented: first working environment, minimal path to success | [`tutorials/README.md`](tutorials/README.md) |
| **How-to Guides** | [`docs/how-to/`](how-to/) | Task-oriented: "how do I do X?" operational instructions | [`how-to/README.md`](how-to/README.md) |
| **Reference** | [`docs/reference/`](reference/) | Information-oriented: exact CLI/config/schema surfaces, inventories, examples; several pages are generated | [`reference/README.md`](reference/README.md) |
| **Explanation** | [`docs/explanation/`](explanation/) | Understanding-oriented: architecture rationale, "why does this work this way?" | [`explanation/README.md`](explanation/README.md) |

## Outside this map (untouched)

These layers are **explicitly excluded** — they are the spec-and-build pipeline, not
general documentation:

| Layer | Paths | Why excluded |
|-------|-------|--------------|
| Dreams (Tier 0) | `docs/dreams/` | Raw aspirations; Herald/BMAD intake |
| Legacy intake specs (Tier 1, retired) | `archive/docs/specs/` | The hand-authored spec tier is retired: doctor Story 37.1 emptied the old folder on 2026-10-10; its specs were archived under `archive/docs/specs/` (Story 23.3) or carried into a station chain as a Spec companion |
| BMAD planning (Tier 2) | `_bmad-output/projects/*/planning-artifacts/` | Active specs, epics, architecture |
| BMAD execution (Tier 3) | `_bmad-output/projects/*/implementation-artifacts/` | Gitignored runtime scratch |
| Tool entry points | `README.md`, `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/` | Agent/human front doors; they point into this map |
| Intake inbox | `docs/intake/` | Pre-triage staging; routes elsewhere per [`docs/intake/README.md`](intake/README.md) |
| Governance | `docs/governance/` | Policy corpus; cross-cutting, not Diátaxis-quadrant material |
| Foundry | `docs/foundry/` | Foundry registry, frames and guards — machine-read by detectors, not authored documentation |
| Station/package docs | `src/shared/packages/pyforge-*/README.md`, skill dirs | Station-scoped; link *into* this map where general |
| Publish roots (generated) | `docs/dashboard/` | One Pages artifact built at `docs-site/build/site/` — the Starlight shelf at `/`, herald's dossier site under `/herald/`, the status pages under `/status/`, Kedro-Viz under `/dashboard/kedro-viz/` and the Vizro boards under `/dashboard/vizro/`, mounted from `docs/dashboard/` (the exports gitignored: atlas's workflow artifacts, skipped and hidden when absent) — deployed by `pages.yml`, the sole `deploy-pages` caller (see [`docs/dashboard/README.md`](dashboard/README.md)) |
| Pages site | `docs-site/` | The one generator of the Pages artifact (Astro + Starlight): the shelf, herald's pages and content (`docs-site/src/content/`), the status pages and the machine surfaces; `pages-build` / `pages-check` (pyforge-herald CAP-61 Story 43.7 retired `docsite/`); never renamed |
| Deck sources | `presentations/` | Herald's deck sources and `facts.yaml`, published under `/herald/`; not documentation |

## One-chain operator layer (2026-09-17)

Operators and coding agents keep a station at one Dream, one Spec, one PRD, one spine, and one epic chain with two Diátaxis pages. Those pages **point at** [`CHAIN-STANDARD.md`](governance/spec-one-chain-per-station/CHAIN-STANDARD.md) (and Spec CAP-10). They do not move Dreams or `docs/governance/` into this map; those layers stay in the exclusion table above.

| Page | Quadrant | Role |
|------|----------|------|
| [`how-to/one-chain-station-ops.md`](how-to/one-chain-station-ops.md) | How-to | Lock, satellite rewrite, mop, parallel work, environment |
| [`explanation/one-chain-lock-and-mop.md`](explanation/one-chain-lock-and-mop.md) | Explanation | Why 1:1 is minting plus `chain-sprawl-check`, not a periodic fold |

Dispatch of already-minted stories stays in [`how-to/driving-a-pyforge-station-backlog.md`](how-to/driving-a-pyforge-station-backlog.md).

## Recipe-factory and agent-hygiene how-tos

The recipe, pixi, CI and troubleshooting pages, plus the concurrent-activity check.

| Page | Quadrant | Role |
|------|----------|------|
| [`how-to/recipe-testing-and-builds.md`](how-to/recipe-testing-and-builds.md) | How-to | Building and testing individual recipes locally (rattler-build route, Mason-backed route) |
| [`how-to/troubleshooting-recipe-builds.md`](how-to/troubleshooting-recipe-builds.md) | How-to | Fixes for common local recipe build failures |
| [`how-to/pixi-tasks.md`](how-to/pixi-tasks.md) | How-to | Generated list of every pixi task and the environments that run it |
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
| [`how-to/launch-a-cost-saving-interactive-session.md`](how-to/launch-a-cost-saving-interactive-session.md) | How-to | `caveman-install` + `headroom wrap claude` for the interactive session path — the manual equivalent of the savings `marshal factory dispatch` applies automatically |
| [`explanation/the-detector-framework.md`](explanation/the-detector-framework.md) | Explanation | Rationale for dynamic AST-discovery and the 'unknown, never green' inversion |

## Relocated pages

| Former location | New home | Notes |
|-----------------|----------|-------|
| `README.md` § Quick start, § Building, § Pixi tasks, § GitHub Actions | [`docs/tutorials/getting-started.md`](tutorials/getting-started.md) + [`docs/how-to/`](how-to/) | README links to these pages |
| `docs/reference/developer-guide.md` (mixed) | Split across tutorials, how-to, and reference | Reference file retains formats + config |
| `docs/reference/antigravity-developer-startup.md` | [`docs/how-to/antigravity-developer-startup.md`](how-to/antigravity-developer-startup.md) | Redirect stub at old path |
| `docs/reference/manticore-studio.md` | [`docs/how-to/manticore-studio.md`](how-to/manticore-studio.md) | Redirect stub at old path |
| `docs/explanation/enterprise-deployment.md` §1 procedural steps | [`docs/how-to/air-gapped-mirror-setup.md`](how-to/air-gapped-mirror-setup.md) | Explanation doc retains architecture rationale |

## Per-file classification: `docs/reference/`

The hand-classified files of `docs/reference/`, and the ones that moved out of it. The generated reference pages are in the page registry.

### Reference quadrant (stay in `docs/reference/`)

| File | Kind | Notes |
|------|------|-------|
| [`container-base-layer-convention.md`](reference/container-base-layer-convention.md) | True reference | Base-tag pinning, multi-stage pixi, secret-mount rules |
| [`pixi-config-jfrog.example.toml`](reference/pixi-config-jfrog.example.toml) | True reference | JFrog pixi config example |
| [`station-verify-commands.md`](reference/station-verify-commands.md) | True reference | Verify-command lookup table, generated from each station's `marshal-policy.toml` by `docs-station-verify` |
| [`library-llms-full.md`](reference/library-llms-full.md) | True reference | Library catalog derived from `pixi.toml`; the `llms-full-check` detector reports drift |
| [`bmad-estate-llms-full.md`](reference/bmad-estate-llms-full.md) | True reference | Generated BMAD-estate catalog (`bmad-estate-check` gate; regenerate with `scribe catalog bmad-estate --write`) |
| [`github-workflows.md`](reference/github-workflows.md) | True reference | Generated workflow inventory (regenerate with `docs-github-workflows`) |
| [`sync-jira-github-workflow-templates/README.md`](reference/sync-jira-github-workflow-templates/README.md) | True reference | Steward `sync` GitHub Projects V2 ↔ Jira Cloud workflow templates for the *external target* repo, never installed here (see `archive/docs/intake/jira-github-projects-sync/`, archived doctor 23.4) |
| [`test-charter.md`](reference/test-charter.md) | Policy reference | Fleet testing charter (cited by `archive/docs/dreams/pyforge-testing-charter.md`) |
| [`judgement-vocabulary.md`](reference/judgement-vocabulary.md) | Policy reference | What `verdict` / `gate` / `detector` / `check` / `preflight` / `advisory` / `lens` each mean, stated **positively**; the four exit-code domains and the `2` inversion. Restates the Charter's Gate/Track/kernel rulings; rules nothing itself (cited by `docs/dreams/pyforge-charter.md` § The Lexicon) |
| [`conda-forge-packaging-inventory-operations_prompt.md`](reference/conda-forge-packaging-inventory-operations_prompt.md) | True reference | Standalone re-run prompt for inventory runner |
| [`conda-forge-packaging-inventory-operations_replay.md`](reference/conda-forge-packaging-inventory-operations_replay.md) | True reference | Replay/sync contract for inventory runner |
| [`README.md`](reference/README.md) | Index | Reference-quadrant index |

### Explanation quadrant (relocated to `docs/explanation/`)

| File | Kind | Notes |
|------|------|-------|
| [`pyforge-estate-overview.md`](explanation/pyforge-estate-overview.md) | Architecture rationale | The 8 stations, Canopy architecture, and BMAD methodology |
| [`mcp-server-architecture.md`](explanation/mcp-server-architecture.md) | Architecture rationale | MCP tool layer design |
| [`enterprise-deployment.md`](explanation/enterprise-deployment.md) | Architecture rationale | Air-gap + Artifactory deployment design (procedural §§ 1–4 flagged for How-to split in Story 22.5, done; §1 "What actually deploys", the mirror-provisioning checklist, and JFROG_API_KEY Pattern D refreshed from the marshal binders in Story 23.2; the whole page re-verified 2026-11-17) |
| [`airgap-distribution-contract.md`](explanation/airgap-distribution-contract.md) | Architecture rationale | Mason air-gap distributable contract ("socket, not installer") |

`mcp-server-architecture.md` keeps a redirect stub at its former `docs/reference/` path.
`enterprise-deployment.md` and `airgap-distribution-contract.md` do not: their stubs were
deleted (Story 23.2) once their inbound references pointed at `docs/explanation/`.

### Redirect stubs still at the old `docs/reference/` paths

| Stub | Kind | Points at |
|------|------|-----------|
| [`antigravity-developer-startup.md`](reference/antigravity-developer-startup.md) | Redirect stub (Story 22.5) | [`how-to/antigravity-developer-startup.md`](how-to/antigravity-developer-startup.md) |
| [`manticore-studio.md`](reference/manticore-studio.md) | Redirect stub (Story 22.5) | [`how-to/manticore-studio.md`](how-to/manticore-studio.md) |
| [`mcp-server-architecture.md`](reference/mcp-server-architecture.md) | Redirect stub (Story 22.4) | [`explanation/mcp-server-architecture.md`](explanation/mcp-server-architecture.md) |

### Split or relocated

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

## Sections (site mounts)

The optional `sections:` list in [`docs/map.yaml`](map.yaml) orders every non-docs mount on the
GitHub Pages site. Each section requires five fields: `key` (slug), `label`, `href`
(site-root-relative directory with trailing slash), `owner` (station slug), and `order`
(integer). Optional `entries` carry `{key, label, href}` sub-items. A row is added when its
section publishes, by the station that publishes it, through the same surface reconcile that
adds a `pages:` row (the Publish roots rule). Herald Story 43.7 reads this list into the docs
sidebar, the top menu every page carries and the home's doors, in `order`, and retired `site.yml`'s
nav; a section whose `href` is a mounted export shows only when the export is present, `status`
only with `pyforge.herald.status_pages` on, and `marketplace` (steward Story 109.3, the BMAD
marketplace mounted from `docs/foundry/marketplace/`) only with `pyforge.steward.marketplace_pages` on.

## Page registry (generated)

<!-- docs-map:registry:begin -- generated by `pixi run -e pyforge-guild docs-map-render` from docs/map.yaml. Do not hand-edit between the markers; docs-currency (Story 30.2) treats a mismatch as a finding. -->
### Tutorials

| Page | Owner | Kind |
|---|---|---|
| [`tutorials/README.md`](tutorials/README.md) | fleet | pointer |
| [`tutorials/getting-started.md`](tutorials/getting-started.md) | fleet | authored |
| [`tutorials/local-platform-development.md`](tutorials/local-platform-development.md) | fleet | authored |

### How-to

| Page | Owner | Kind |
|---|---|---|
| [`how-to/README.md`](how-to/README.md) | fleet | pointer |
| [`how-to/adopt-the-operating-model-with-marshal-seed.md`](how-to/adopt-the-operating-model-with-marshal-seed.md) | marshal | authored |
| [`how-to/ai-engine-operations.md`](how-to/ai-engine-operations.md) | fleet | authored |
| [`how-to/air-gapped-mirror-setup.md`](how-to/air-gapped-mirror-setup.md) | fleet | authored |
| [`how-to/antigravity-developer-startup.md`](how-to/antigravity-developer-startup.md) | fleet | authored |
| [`how-to/bootstrap-a-machine-with-steward.md`](how-to/bootstrap-a-machine-with-steward.md) | steward | authored |
| [`how-to/configure-your-coding-agent.md`](how-to/configure-your-coding-agent.md) | scribe | authored |
| [`how-to/deploy-the-docs-site-to-github-enterprise-pages.md`](how-to/deploy-the-docs-site-to-github-enterprise-pages.md) | herald | authored |
| [`how-to/detect-concurrent-agent-activity.md`](how-to/detect-concurrent-agent-activity.md) | fleet | authored |
| [`how-to/diagnose-with-doctor.md`](how-to/diagnose-with-doctor.md) | doctor | authored |
| [`how-to/disaster-recovery.md`](how-to/disaster-recovery.md) | fleet | authored |
| [`how-to/driving-a-pyforge-station-backlog.md`](how-to/driving-a-pyforge-station-backlog.md) | fleet | authored |
| [`how-to/feedstock-failure-remediation.md`](how-to/feedstock-failure-remediation.md) | fleet | pointer |
| [`how-to/feedstock-platform-expansion.md`](how-to/feedstock-platform-expansion.md) | fleet | pointer |
| [`how-to/github-actions-recipe-ci.md`](how-to/github-actions-recipe-ci.md) | fleet | authored |
| [`how-to/host-nebari.md`](how-to/host-nebari.md) | pyforge-steward | authored |
| [`how-to/launch-a-cost-saving-interactive-session.md`](how-to/launch-a-cost-saving-interactive-session.md) | fleet | authored |
| [`how-to/manage-worktrees-with-bmad.md`](how-to/manage-worktrees-with-bmad.md) | fleet | authored |
| [`how-to/manticore-studio.md`](how-to/manticore-studio.md) | fleet | authored |
| [`how-to/monitor-the-fleet.md`](how-to/monitor-the-fleet.md) | fleet | authored |
| [`how-to/move-vendor-extracts-through-the-corridor.md`](how-to/move-vendor-extracts-through-the-corridor.md) | steward | authored |
| [`how-to/ocp-cluster-bringup.md`](how-to/ocp-cluster-bringup.md) | fleet | authored |
| [`how-to/one-chain-station-ops.md`](how-to/one-chain-station-ops.md) | doctor | authored |
| [`how-to/pause-ci.md`](how-to/pause-ci.md) | pyforge-steward | authored |
| [`how-to/pixi-tasks.md`](how-to/pixi-tasks.md) | steward | generated |
| [`how-to/presentation-deck.md`](how-to/presentation-deck.md) | fleet | authored |
| [`how-to/purge-preserved-refs.md`](how-to/purge-preserved-refs.md) | marshal | authored |
| [`how-to/reach-a-station-mcp-endpoint.md`](how-to/reach-a-station-mcp-endpoint.md) | steward | authored |
| [`how-to/read-steward-registers.md`](how-to/read-steward-registers.md) | steward | authored |
| [`how-to/recipe-testing-and-builds.md`](how-to/recipe-testing-and-builds.md) | fleet | authored |
| [`how-to/reconcile-spec-surface.md`](how-to/reconcile-spec-surface.md) | doctor | authored |
| [`how-to/record-progress-claims-and-notices-with-herald.md`](how-to/record-progress-claims-and-notices-with-herald.md) | herald | authored |
| [`how-to/refresh-the-estate.md`](how-to/refresh-the-estate.md) | steward | authored |
| [`how-to/restore-operations.md`](how-to/restore-operations.md) | fleet | authored |
| [`how-to/rotate-platform-secrets.md`](how-to/rotate-platform-secrets.md) | steward | authored |
| [`how-to/run-and-read-pr-preflight.md`](how-to/run-and-read-pr-preflight.md) | steward | authored |
| [`how-to/run-and-understand-detectors.md`](how-to/run-and-understand-detectors.md) | doctor | authored |
| [`how-to/run-atlas-pipelines-and-read-datasets.md`](how-to/run-atlas-pipelines-and-read-datasets.md) | atlas | authored |
| [`how-to/run-herald-live-backend-locally.md`](how-to/run-herald-live-backend-locally.md) | herald | authored |
| [`how-to/scan-for-compliance-with-warden.md`](how-to/scan-for-compliance-with-warden.md) | warden | authored |
| [`how-to/schedule-the-scribe-nightly-compile.md`](how-to/schedule-the-scribe-nightly-compile.md) | scribe | authored |
| [`how-to/station-cli-operations.md`](how-to/station-cli-operations.md) | fleet | authored |
| [`how-to/track-upstream-todos.md`](how-to/track-upstream-todos.md) | steward | authored |
| [`how-to/troubleshoot-bmad-agent-loops.md`](how-to/troubleshoot-bmad-agent-loops.md) | fleet | authored |
| [`how-to/troubleshoot-herald-moments.md`](how-to/troubleshoot-herald-moments.md) | herald | authored |
| [`how-to/troubleshooting-recipe-builds.md`](how-to/troubleshooting-recipe-builds.md) | fleet | authored |
| [`how-to/upgrade-bmad-core.md`](how-to/upgrade-bmad-core.md) | steward | authored |
| [`how-to/use-marshal-in-an-air-gapped-site.md`](how-to/use-marshal-in-an-air-gapped-site.md) | marshal | authored |
| [`how-to/use-steward-duties-that-need-operator-consent.md`](how-to/use-steward-duties-that-need-operator-consent.md) | steward | authored |

### Reference

| Page | Owner | Kind |
|---|---|---|
| [`reference/README.md`](reference/README.md) | fleet | pointer |
| [`reference/agent-instruction-notes.md`](reference/agent-instruction-notes.md) | scribe | authored |
| [`reference/agent-memory-lifecycle.md`](reference/agent-memory-lifecycle.md) | fleet | authored |
| [`reference/antigravity-developer-startup.md`](reference/antigravity-developer-startup.md) | fleet | pointer |
| [`reference/bmad-estate-llms-full.md`](reference/bmad-estate-llms-full.md) | scribe | generated |
| [`reference/conda-forge-packaging-inventory-operations_prompt.md`](reference/conda-forge-packaging-inventory-operations_prompt.md) | fleet | authored |
| [`reference/conda-forge-packaging-inventory-operations_replay.md`](reference/conda-forge-packaging-inventory-operations_replay.md) | fleet | authored |
| [`reference/container-base-layer-convention.md`](reference/container-base-layer-convention.md) | fleet | authored |
| [`reference/detectors.md`](reference/detectors.md) | doctor | generated |
| [`reference/developer-guide.md`](reference/developer-guide.md) | fleet | authored |
| [`reference/environments.md`](reference/environments.md) | steward | generated |
| [`reference/github-workflows.md`](reference/github-workflows.md) | fleet | generated |
| [`reference/herald-web-dashboard.md`](reference/herald-web-dashboard.md) | herald | authored |
| [`reference/herald-webhook-endpoint.md`](reference/herald-webhook-endpoint.md) | herald | authored |
| [`reference/judgement-vocabulary.md`](reference/judgement-vocabulary.md) | doctor | authored |
| [`reference/library-llms-full.md`](reference/library-llms-full.md) | fleet | authored |
| [`reference/manticore-studio.md`](reference/manticore-studio.md) | fleet | pointer |
| [`reference/marshal-seed-findings.md`](reference/marshal-seed-findings.md) | marshal | authored |
| [`reference/marshal-seed-managed-regions.md`](reference/marshal-seed-managed-regions.md) | marshal | authored |
| [`reference/mcp-server-architecture.md`](reference/mcp-server-architecture.md) | fleet | pointer |
| [`reference/skills-catalog.md`](reference/skills-catalog.md) | steward | generated |
| [`reference/station-cheat-sheet.md`](reference/station-cheat-sheet.md) | fleet | generated |
| [`reference/station-verify-commands.md`](reference/station-verify-commands.md) | fleet | authored |
| [`reference/story-spec-flag-block.md`](reference/story-spec-flag-block.md) | doctor | authored |
| [`reference/sync-jira-github-workflow-templates/README.md`](reference/sync-jira-github-workflow-templates/README.md) | fleet | authored |
| [`reference/test-charter.md`](reference/test-charter.md) | fleet | authored |

### Explanation

| Page | Owner | Kind |
|---|---|---|
| [`explanation/README.md`](explanation/README.md) | fleet | pointer |
| [`explanation/airgap-distribution-contract.md`](explanation/airgap-distribution-contract.md) | fleet | authored |
| [`explanation/enterprise-deployment.md`](explanation/enterprise-deployment.md) | fleet | authored |
| [`explanation/herald-four-moments.md`](explanation/herald-four-moments.md) | herald | authored |
| [`explanation/mcp-server-architecture.md`](explanation/mcp-server-architecture.md) | fleet | authored |
| [`explanation/one-chain-lock-and-mop.md`](explanation/one-chain-lock-and-mop.md) | doctor | authored |
| [`explanation/platform-deployment-architecture.md`](explanation/platform-deployment-architecture.md) | fleet | authored |
| [`explanation/platform-requirements.md`](explanation/platform-requirements.md) | fleet | authored |
| [`explanation/pyforge-ecosystem-architecture.md`](explanation/pyforge-ecosystem-architecture.md) | fleet | authored |
| [`explanation/pyforge-estate-overview.md`](explanation/pyforge-estate-overview.md) | fleet | authored |
| [`explanation/the-detector-framework.md`](explanation/the-detector-framework.md) | doctor | authored |
| [`explanation/the-tier-model-and-data-flow.md`](explanation/the-tier-model-and-data-flow.md) | fleet | authored |
<!-- docs-map:registry:end -->

