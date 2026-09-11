# General documentation map (Diátaxis-adapted)

This map applies to the **general-facing documentation layer** only — the material
a newcomer reads to understand, run, and operate this repo. It is adapted from
[Diátaxis](https://diataxis.fr/) to this repo's actual content volume (14 markdown
files + 1 example toml + 1 template subdirectory under pre-22.4 `docs/reference/`,
not hundreds), not a generic four-folder template.

## Four quadrants

| Quadrant | Path | Role | Population status |
|----------|------|------|---------------------|
| **Tutorials / Getting Started** | [`docs/tutorials/`](tutorials/) | Learning-oriented: first working environment, minimal path to success | Scaffold only — Story 22.5 relocates content from `README.md` "Quick start" and tutorial sections of `developer-guide.md` |
| **How-to Guides** | [`docs/how-to/`](how-to/) | Task-oriented: "how do I do X?" operational instructions | Scaffold only — Story 22.5 relocates scattered how-to material |
| **Reference** | [`docs/reference/`](reference/) | Information-oriented: exact CLI/config/schema surfaces, inventories, examples | Populated — seed from pre-22.4 `docs/reference/` (true reference material retained here) |
| **Explanation** | [`docs/explanation/`](explanation/) | Understanding-oriented: architecture rationale, "why does this work this way?" | Populated — architecture-rationale files relocated from `docs/reference/` in Story 22.4 |

## Outside this map (untouched)

These layers are **explicitly excluded** — they are the spec-and-build pipeline, not
general documentation:

| Layer | Paths | Why excluded |
|-------|-------|--------------|
| Dreams (Tier 0) | `docs/dreams/` | Raw aspirations; Herald/BMAD intake |
| Legacy intake specs (Tier 1) | `docs/specs/` | Superseded hand-authored specs |
| BMAD planning (Tier 2) | `_bmad-output/projects/*/planning-artifacts/` | Active specs, epics, architecture |
| BMAD execution (Tier 3) | `_bmad-output/projects/*/implementation-artifacts/` | Gitignored runtime scratch |
| Tool entry points | `README.md`, `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/` | Agent/human front doors — Story 22.6 corrects pointers into this map, not relocates them |
| Intake inbox | `docs/intake/` | Pre-triage staging; routes elsewhere per [`docs/intake/README.md`](intake/README.md) |
| Governance | `docs/governance/` | Policy corpus; cross-cutting, not Diátaxis-quadrant material |
| Station/package docs | `src/shared/packages/pyforge-*/README.md`, skill dirs | Station-scoped; link *into* this map where general |

## Scattered content accounted for (Story 22.5 targets)

Content that belongs in Tutorials or How-to but still lives elsewhere:

| Current location | Future quadrant | Notes |
|------------------|-----------------|-------|
| `README.md` § Quick start, § Building a single recipe, § Pixi tasks | Tutorials + How-to | Entry-point duplication corrected in Story 22.6 |
| `README.md` § Common Commands | How-to | Operational command surface |
| `docs/reference/developer-guide.md` | **Split** (Tutorial + How-to + Reference) | Mixed file — see per-file table below; Story 22.5 executes the split |
| `docs/reference/antigravity-developer-startup.md` | How-to | Developer startup / surface-selection guide |
| `docs/reference/manticore-studio.md` | How-to | Procedural install + render setup for Herald's manticore studio |

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
| [`sync-jira-github-workflow-templates/`](reference/sync-jira-github-workflow-templates/) | True reference | Reusable GitHub Actions workflow templates for Jira↔GitHub Projects sync (see `docs/intake/jira-github-projects-sync/`) |
| [`test-charter.md`](reference/test-charter.md) | Policy reference | Fleet testing charter (cited by `docs/dreams/pyforge-testing-charter.md`) |
| [`conda-forge-packaging-inventory-operations_prompt.md`](reference/conda-forge-packaging-inventory-operations_prompt.md) | True reference | Standalone re-run prompt for inventory runner |
| [`conda-forge-packaging-inventory-operations_replay.md`](reference/conda-forge-packaging-inventory-operations_replay.md) | True reference | Replay/sync contract for inventory runner |
| [`README.md`](reference/README.md) | Index | Reference-quadrant index (this story updates it) |

### Explanation quadrant (relocated to `docs/explanation/`)

| File | Kind | Notes |
|------|------|-------|
| [`mcp-server-architecture.md`](explanation/mcp-server-architecture.md) | Architecture rationale | FastMCP tool layer design (**still stale** — tool count may drift; refresh tracked separately) |
| [`enterprise-deployment.md`](explanation/enterprise-deployment.md) | Architecture rationale | Air-gap + Artifactory deployment design (**still stale** — refresh tracked separately; procedural §§ 1–4 flagged for How-to split in Story 22.5) |
| [`airgap-distribution-contract.md`](explanation/airgap-distribution-contract.md) | Architecture rationale | Mason air-gap distributable contract ("socket, not installer") |

Redirect stubs remain at the former `docs/reference/` paths for moved files until
Story 22.6 updates entry-point links repo-wide.

### Mixed / pending relocation (Story 22.5)

| File | Classification | Action in 22.5 |
|------|----------------|----------------|
| [`developer-guide.md`](reference/developer-guide.md) | **Split required** | Quick Start → Tutorials; Local Testing / Troubleshooting → How-to; Configuration Reference → Reference |
| [`antigravity-developer-startup.md`](reference/antigravity-developer-startup.md) | How-to | Move to `docs/how-to/` |
| [`manticore-studio.md`](reference/manticore-studio.md) | How-to | Move to `docs/how-to/` |

## Archived reference (unchanged)

| File | Location |
|------|----------|
| `GuildHall_Fleet_Status.md` | `archive/docs/reference/` (superseded static snapshot) |

## Downstream stories

| Story | Builds on this map |
|-------|-------------------|
| **22.5** | Populates `docs/tutorials/` and `docs/how-to/`; executes mixed-file splits and pending relocations |
| **22.6** | Corrects `README.md`, `CLAUDE.md`, `AGENTS.md` pointers; fixes broken internal links after relocation |
