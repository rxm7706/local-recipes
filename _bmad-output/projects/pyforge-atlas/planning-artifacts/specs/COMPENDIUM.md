# pyforge-atlas — story-spec compendium (all 32 stories, one file)

> **Compilation, not source of truth** (assembled 2026-07-25). Every BMAD spec used to build
> pyforge-atlas — the Dream-level `bmad-spec` kernel plus all 32 per-story specs (Waves 0,
> A–H) — collected verbatim into one durable file. The canonical copies remain the individual
> files in this directory (`planning-artifacts/specs/`); if one changes, regenerate this
> compendium from them. Provenance of the recovered set (2 originals + 30 regenerated
> contract-specs, contract intact 32/32) is documented in `README.md` here; ground truth for
> what shipped is the merged PRs **#58–#105** (migration COMPLETE, 32/32, shipped 2026-07-18).
> Each section folds the source file's YAML frontmatter into a provenance blockquote; bodies
> are byte-verbatim.

## Index — wave order

| Story | Canonical file | Provenance | Title |
|---|---|---|---|
| 0.1 | `spec-0-1-generate-legacy-contextual-skill.md` | original | Story 0.1: Generate legacy contextual skill |
| A1 | `spec-a1-scaffold-the-kedro-pixi-project-via-nebi.md` | regenerated | Story A1 (2.1): Scaffold the Kedro + pixi project via `nebi` |
| A2 | `spec-a2-define-the-data-catalog-for-all-sources-outputs.md` | regenerated | Story A2 (2.2): Define the Data Catalog for all sources + outputs |
| A3 | `spec-a3-implement-incrementalparquetdataset-for-ttl-gating.md` | regenerated | Story A3 (2.3): Implement `IncrementalParquetDataset` for TTL gating |
| B1 | `spec-b1-port-the-conda-side-backbone-phases-into-kedro-nodes.md` | original | Story B1: Port the conda-side backbone phases into Kedro nodes |
| B2 | `spec-b2-port-the-pypi-vulnerability-pipelines.md` | regenerated | Story B2 (3.2): Port the PyPI & Vulnerability pipelines |
| B3 | `spec-b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md` | regenerated | Story B3 (3.3): Re-expose the data surface as Kedro-API-native MCP tools |
| B4 | `spec-b4-verify-dataset-parity-against-the-legacy-orchestrator.md` | regenerated | Story B4 (3.4): Verify dataset parity against the legacy orchestrator |
| B5 | `spec-b5-port-the-external-refresh-assets-3-4.md` | regenerated | Story B5 (3.5): Port the external-refresh assets (§ 3.4) |
| B6 | `spec-b6-port-the-seed-gaps-pipeline.md` | regenerated | Story B6 (3.6): Port the Seed-Gaps pipeline |
| B7 | `spec-b7-extend-the-universal-sbom-intake-resolver-formats-universe-bom-buckets.md` | regenerated | Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets) |
| B8 | `spec-b8-basilisk-conda-native-vulnerability-ingestion.md` | regenerated | Story B8 (3.8): Basilisk conda-native vulnerability ingestion |
| B9 | `spec-b9-release-to-availability-velocity-columns.md` | regenerated | Story B9 (3.9): Release-to-availability velocity columns |
| B10 | `spec-b10-migration-readiness-datasets-classification-node.md` | regenerated | Story B10 (3.10): Migration-readiness datasets + classification node |
| C1 | `spec-c1-integrate-kedro-dagster-for-scheduling-execution.md` | regenerated | Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution |
| C2 | `spec-c2-integrate-kedro-viz-expose-a-pixi-task.md` | regenerated | Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task |
| D1 | `spec-d1-define-the-boring-semantic-layer-bsl-models.md` | regenerated | Story D1 (5.1): Define the Boring Semantic Layer (BSL) models |
| D2 | `spec-d2-build-the-vizro-dashboard-port-the-28-clis-to-pages.md` | regenerated | Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages |
| D3 | `spec-d3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool.md` | regenerated | Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool |
| E1 | `spec-e1-implement-the-a2a-communication-interfaces.md` | regenerated | Story E1 (6.1): Implement the A2A communication interfaces |
| E2 | `spec-e2-integrate-openlineage-opentelemetry.md` | regenerated | Story E2 (6.2): Integrate OpenLineage + OpenTelemetry |
| F1 | `spec-f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim.md` | regenerated | Story F1 (7.1): Complete the DuckDB consolidation + prove the cold-start claim |
| F2 | `spec-f2-implement-the-data-validation-hook-and-inline-pandera-contracts.md` | regenerated | Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts |
| F3 | `spec-f3-implement-vector-similarity-search-rag-via-duckdb-vss.md` | regenerated | Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss` |
| F4 | `spec-f4-dependency-hygiene-node-unified-ci-policy-gate.md` | regenerated | Story F4 (7.4): Dependency-hygiene node + unified CI policy gate |
| G1 | `spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md` | regenerated | Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM |
| G2 | `spec-g2-emit-parquet-artifacts-to-a-static-web-host.md` | regenerated | Story G2 (8.2): Emit Parquet artifacts to a static web host |
| G3 | `spec-g3-implement-dagster-sensors-for-near-real-time-ingestion.md` | regenerated | Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion |
| H1 | `spec-h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas.md` | regenerated | Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas |
| H2 | `spec-h2-implement-agno-compilation-linting-and-q-a-crews.md` | regenerated | Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews |
| H3 | `spec-h3-integrate-la-suite-docs-rest-api-sync.md` | regenerated | Story H3 (9.3): Integrate La Suite Docs REST API Sync |
| H4 | `spec-h4-orchestrate-crews-via-dagster.md` | regenerated | Story H4 (9.4): Orchestrate Crews via Dagster |

---

# Kernel — Dream-level bmad-spec

> Source: `specs/spec-pyforge-atlas/SPEC.md` (canonical file — still lives there).

---
spec: pyforge-atlas
status: shipped
owner-dream: docs/dreams/pyforge-atlas.md
program: regenerable-factory (Wave 5 chain-verify)
surface:
  - src/**
  - conf/**
companions:
  - ../../prds                 # adopted: the PRD set (authoritative)
  - ../../architecture         # adopted: the architecture set (authoritative)
  - ../../epics.md             # adopted: epics/stories record
open_questions: []
---

# SPEC — pyforge-atlas (chain-verify kernel)

## Why

The atlas Kedro/Dagster/DuckDB migration shipped with a full BMAD chain
(PRD, architecture, epics; 32 stories merged, PRs #58–#105). This kernel adds
the one missing piece — a machine-readable surface manifest — binding
`src/**` + `conf/**` into the repo-wide `spec_surface_check`, so future atlas
code changes must move this project's contract. It adds NO new contract
content; the adopted companions remain authoritative.

## Capabilities

- **CAP-1 — surface binding.** Intent: the migration's code surface is
  governed; a change without contract movement is a checker finding.
  Success: `spec_surface_check` lists `spec-pyforge-atlas` with src/conf
  files governed; drift arm active (memlog mode).

## Constraints

- Changes to atlas behavior flow through the pyforge-atlas BMAD project
  (stories/correct-course), not through this kernel.

## Non-goals

- Restating the PRD/architecture.

## Success signal

Checker green with the atlas surface governed; the next atlas story's merge
moves this project's artifacts alongside the code.


---

> Source: `specs/spec-0-1-generate-legacy-contextual-skill.md` (canonical file — still lives there).

<!-- RECOVERED 2026-07-25: original spec, survived intact in implementation-artifacts/0-1-generate-legacy-contextual-skill.md; promoted to tracked planning-artifacts/specs/ for durability. -->
# Story 0.1: Generate legacy contextual skill

Status: done (attended sign-off by rxm7706, 2026-07-17)

<!-- Primary key: frozen spec ID **0.1** (epics.md D-2 — the Epic.Story alias "1.1" is
     informational only). Sprint key: 0-1-generate-legacy-contextual-skill.
     Epic 1 / Wave 0 — Legacy Translation via Skill Forge (SKF).
     EXECUTION MODE: **ATTENDED** (wave-boundary event, human present — never loop-driven;
     spec § 2.5 / PRD § 6.1 / sprint feed story_meta). A human IS present at implementation:
     asking is allowed and expected at the decision points marked [ATTENDED-DECISION] below.
     Drafted unattended 2026-07-17 by bmad-create-story; pixi unavailable in the drafting
     container — all pixi-dependent steps are marked ENVIRONMENT-DEFERRED and MUST run in
     the attended session. -->

## Story

As a Wave-B developer agent,
I want the legacy `conda_forge_atlas.py` orchestrator converted into an `agentskills.io`-compliant skill via Skill Forge (SKF),
so that I can query hallucination-free legacy provenance while porting phases.

## Acceptance Criteria

Spec § 9 Story 0.1 is the binding authority (restated verbatim below; tightenings only —
never weaker). Goal (spec § 9): *"Convert the legacy `conda_forge_atlas.py` orchestrator
into an `agentskills.io` compliant skill using Skill Forge."*

1. **(spec, verbatim)** The SKF module outputs a structured skill repository modeling the legacy logic.
   - *Tightened:* "the legacy logic" = the full ~10,000-LOC orchestrator surface defined by spec §§ 2.4/3: `conda_forge_atlas.py` (8,902 lines) **plus** `bootstrap_data.py` (1,094 lines) — not the orchestrator file alone. The output layout is `agentskills.io`-compliant (spec § 9 Goal line).
   - *Tightened (coverage floor, from spec § 3.3 — the authoritative surface enumeration):* the skill models, at minimum: all **23 cataloged phases** (22 registered in the `PHASES` list at `conda_forge_atlas.py:8679` **plus the unregistered Phase I** side-effect of Phase F's anaconda-api path), the `phase_state`/TTL/`_TTL_GATED` checkpoint machinery (`atlas_phase.py`), the `bootstrap_data.py` sub-step driver (profiles, the 1800 s `cf_atlas_core` coarse cap), the 6 `cf_atlas.db` write paths, the § 3.3 per-phase engineering contracts (AD-10 list in Dev Notes), and the § 3.4 migration boundary (3 in-scope refresh stores; declared-input classes that are out of scope).
2. **(spec, verbatim)** Developer agents can query this skill for hallucination-free provenance during Wave B.
   - *Tightened (provable provenance, spec § 2.4):* every provenance answer traces to `file:line` (or function/symbol) at the grounding commit — verified by the AC-2 query battery in Task 5, whose answers are checked against the live source, not against the skill's own text.
3. **(spec, verbatim)** Wave-0 enabler (no FR — the skill artifact is execution scaffolding per § 2.4, not product surface).
   - *Restated (epics.md D-13):* story 0.1 is deliberately FR-less; FR-1..FR-22 coverage is complete without it. The skill artifact is Tier-3 execution scaffolding, not part of the migrated product surface and not part of the B4 parity scope.
4. **(mode/gate, from epics.md + sprint feed — completion semantics, tightening not weakening):** the story completes as an ATTENDED event with human sign-off on the queryable artifact; there is no pre-existing verify gate (`verify_gate: none — pre-harness`); the Wave-0 preconditions checklist (Dev Notes) is executed alongside and recorded as done.

## Tasks / Subtasks

- [x] Task 0 — ATTENDED session setup + Wave-0 preconditions (AC: 4; AD-18, spec § 14 preconditions block, PRD § 6.2)
  - [x] 0.1 One-time hooks approval for the loop stack (bmad-loop v0.8.1 / tmux sessions) — human approves in this session.
  - [x] 0.2 Active-project switch: `scripts/bmad-switch pyforge-atlas`, then `scripts/bmad-switch --current` to confirm marker + both `_bmad-output/{planning,implementation}-artifacts` symlinks agree. **This supersedes the spec § 2.5/§ 14 literal `bmad-switch local-recipes`** (recorded deviation: PRD § 9.11 → AD-18 → epics.md D-4). Never hand-edit the marker.
  - [x] 0.3 ENVIRONMENT-DEFERRED (pixi required — run now, in this attended session): `pixi run -e local-recipes bmad-groundtruth` (live re-check; intake verification was git-surface-only, see `intake-groundtruth-2026-07-17.md`), `pixi run -e local-recipes bmad-drift-check`, `pixi run -e local-recipes llms-full-check`. If groundtruth diverges from the § 3.3 snapshot (23 phases / 28 read CLIs / schema v29 / 46 MCP tools), the live output wins — feed the live enumeration to SKF, and note the divergence here and in the wave record.
  - [x] 0.4 Re-check conditional Phase T (trendshift Track A, `docs/specs/trendshift-conda-forge.md`) shipped/not-shipped (D-15, PRD § 6.1). If shipped: Phase T (tables `github_trending_repos` + `trending_classification`, view `v_trending_candidates`, schema v30) joins the legacy surface the skill must model.
  - [x] 0.5 Worktree symlink bootstrap prepared (the AD-18 bootstrap that recreates the two `_bmad-output` symlinks inside loop worktrees) — prepared here, validated later by Story A3 (the designated worktree smoke). Not a 0.1 deliverable to *prove*, only to stage.
  - [x] 0.6 Heaviest-story budget review: record pre-flight `session_timeout_min`/token raises for keystones B1/B2/F1 (AD-18; pyforge pilot learnings), plus the F1 `dev_stall_grace_s` raise.
  - [x] 0.7 Stage `policy.toml` `[verify]` additions for Wave A (`kedro-test`, `kedro-catalog-check` land as A1/A2 deliverables; nothing exists to add for Wave 0 itself — record that explicitly).
- [x] Task 1 — Provision Skill Forge (AC: 1) **[ATTENDED-DECISION]**
  - [x] 1.1 GAP (verified 2026-07-17): no SKF tooling exists in the repo — repo-wide grep for `skill-forge|skill_forge|skillforge|agentskills` matches only the spec and epics; it is not in `pixi.toml`, not under `.claude/skills/`, not under `_bmad/`. Spec § 13.2 slots it **Committed** ("Skill Forge (SKF) · CIS · bmad-loop v0.8.1 · bmad-dev-auto — BMAD execution tooling"). The human decides the acquisition route (BMAD module install / pixi dependency / vendored tool) — record the route, version/pin, and the `agentskills.io` spec revision targeted, in this file's Dev Agent Record.
  - [x] 1.2 If SKF turns out unavailable/unusable in acceptable time: the fallback is a manually-driven translation to the same `agentskills.io`-compliant artifact shape with the same AC-2 provenance bar (the ACs bind the *artifact*, not the tool). Record the fallback decision if taken.
- [x] Task 2 — Enumerate the legacy translation surface (AC: 1) — read-only; per CLAUDE.md Rule 1, invoke the `conda-forge-expert` skill before touching/reading atlas tooling
  - [x] 2.1 Primary sources (read-only, never modified by this story):
        `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` (8,902 LOC; `PHASES` registry at line 8679; `SCHEMA_VERSION = 29` at line 139),
        `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` (1,094 LOC; sub-step driver, profiles, 1800 s cap),
        `.claude/skills/conda-forge-expert/scripts/atlas_phase.py` (TTL reset, `_TTL_GATED` map),
        `.claude/skills/conda-forge-expert/scripts/_http.py` (19 `resolve_*_urls` helpers, `atomic_writer`, JFrog credential defect FR-1 fixes-not-ports).
  - [x] 2.2 Write-path satellites (the other `cf_atlas.db` writers § 3.3 names): `.claude/skills/conda-forge-expert/scripts/mapping_gap.py` (`g10_spelling` no-clobber), `cisa_kev_fetcher.py`, `epss_fetcher.py`, `cwe_catalog_fetcher.py` (same dir).
  - [x] 2.3 Contextual references SKF should ingest as documentation context (not code): `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`, `reference/atlas-phase-engineering.md` (the shipped *how* behind each phase, incl. § 13 Phase P cost model), `guides/atlas-operations.md` (profiles, cadence table, recovery playbook), and the spec's § 3.3/§ 3.4 sections themselves.
  - [x] 2.4 MCP surface for provenance queries about tools: `.claude/tools/conda_forge_server.py` (46 `@mcp.tool()`, 23 atlas-relevant; `gemini_server.py` is out of scope per § 3.3).
- [x] Task 3 — Run SKF and land the skill repository (AC: 1) **[ATTENDED-DECISION on output location]**
  - [x] 3.1 Proposed default output location `[ASSUMPTION — confirm with human]`: a new sibling skill directory `.claude/skills/cf-atlas-legacy/` with an `agentskills.io`-compliant layout. Rationale: must NOT live inside `.claude/skills/conda-forge-expert/` (that tree is a migration *input*, read-only for this story, and is pinned by the repo's meta-tests/three-place rule) and must NOT live in `.claude/data/` (gitignored runtime data — the skill is context, not data). If the human prefers a standalone repo (spec says "skill repository"), record the location and add a pointer file in-repo.
  - [x] 3.2 Stamp the artifact with its grounding: generation timestamp + the grounding commit hash (intake HEAD or the live HEAD at generation — whichever Task 0.3 verified) + skill v8.78.0 pin. This is the AD-17 advisory-snapshot discipline applied to the skill itself.
  - [x] 3.3 The skill must encode the § 3.3 registry as queryable structure (phases with registration status, TTL-gated set, credentialed set, write paths, view discipline, per-phase engineering contracts), and the § 3.4 boundary (in-scope refresh stores vs declared-input classes) — this is the content Wave-B stories B1/B2/B5/B6 will interrogate.
  - [x] 3.4 Run the repo test suite (ENVIRONMENT-DEFERRED: `pixi run -e local-recipes test-all` or at minimum the meta tests) to prove the new skill directory breaks no meta-test (docs integrity / three-place rule pin the *CFE* skill; a new sibling dir must stay out of their scope).
- [x] Task 4 — Verify AC-2: provenance query battery (AC: 2)
  - [x] 4.1 Execute a recorded query battery against the skill (a fresh agent session queries the skill, answers checked against live source). Minimum battery — one probe per AD-10 contract family: (a) "Which phases are TTL-gated and where is the map?" → `atlas_phase.py` `_TTL_GATED`: F, G, G', H, K, L; (b) "What are Phase P's cost gates?" → dry-run preflight + `PHASE_P_MAX_COST_USD` + `maximum_bytes_billed` + job timeout + `_PARTITIONDATE` literal bounds; (c) "Who writes `cf_atlas.db`?" → exactly the 6 § 3.3 writers; (d) "What is Phase B.5 `_pick_feedstock`?" → dedicated-feedstock attribution; (e) "Is Phase I registered?" → no — side-effect of Phase F, feeds `version-downloads`/`release-cadence`/G'; (f) "What is the `v_current_version_vulns` rule?" → the ONLY query-time-correct vuln source, `packages.vuln_*` is report-only; (g) one negative probe: a question whose answer is NOT in the legacy surface must yield "not modeled / not found", never a fabricated answer.
  - [x] 4.2 Each answer must carry a `file:line`/symbol citation that checks out against the live tree (AC-2 tightening). Record the battery + results in the Dev Agent Record.
- [x] Task 5 — Sign-off and Wave-A handoff (AC: 3, 4)
  - [x] 5.1 Human sign-off on the queryable artifact (this IS the acceptance — no verify gate exists yet, pre-harness).
  - [x] 5.2 Record the Wave-A handoff (see Dev Notes "What done hands to Wave A") in this file's Completion Notes; update `sprint-status.yaml` (`0-1-generate-legacy-contextual-skill` → done at completion; epic-1 stays in-progress until then).
  - [x] 5.3 Note for the effort-closeout ledger: CLAUDE.md Rule 2 (CFE retro) accrues at effort close, not per story — but if this story surfaced CFE-skill findings (e.g., stale atlas docs discovered during enumeration), log them now for the closeout retro.

## Dev Notes

### Execution mode + Wave-0 preconditions (binding)

- **ATTENDED** (spec § 2.5, PRD § 6.1, epics.md, sprint feed `story_meta`). Wave-0 is an attended harness-building wave; this story is never loop-driven. Q-gate: none. Depends on: nothing (first story of the effort).
- The Wave-0 preconditions (Task 0) are the AD-18/spec-§ 14 checklist and run **alongside** this story, in this session: hooks approval · `scripts/bmad-switch pyforge-atlas` (supersedes the spec's `local-recipes` literal — D-4/PRD § 9.11) · live `bmad-groundtruth` + `bmad-drift-check` + `llms-full-check` runs · worktree symlink bootstrap staged (A3 validates) · heaviest-story budget review (B1/B2/F1 keystones; F1 also `dev_stall_grace_s`) · Phase T conditional re-check (D-15) · `policy.toml [verify]` staging.
- pixi was NOT available in the drafting container; every `pixi run` above is carried as ENVIRONMENT-DEFERRED and is a hard prerequisite of this attended session, not optional.

### SKF approach (spec §§ 2.1–2.2, 2.4)

- SKF's job: translate ~10k LOC of legacy orchestrator into an **ingestible agent context skill with provable provenance** (§ 2.4). The output must itself meet the § 2.1 agent-legibility bar: machine-queryable structure, deterministic layout, hyper-clear error/absence semantics (the negative-probe requirement in Task 4.1g).
- The § 2.2 persona frame applies at execution: Ingester reads the raw legacy source; Compiler structures it into the skill; Linker connects phases↔tables↔CLIs↔contracts; Linter validates the query battery; Oracle is the query interface Wave-B agents hit.
- Consumers: Wave-B stories B1 (conda-side ports), B2 (PyPI+vuln ports), B5 (refresh assets), B6 (seed-gaps) query this skill instead of re-deriving legacy behavior from model memory.

### § 3.3 snapshot pointer + groundtruth rule (binding)

- The **authoritative enumeration** of the legacy surface is spec § 3.3 (grounding commit `58a6dcc`, skill v8.78.0, 2026-07-16), re-verified valid at intake HEAD `4cf1b74` via `planning-artifacts/intake-groundtruth-2026-07-17.md` — but that check was **git-surface-only** (pixi unavailable). **Rule: re-enumerate live at implementation** — run `bmad-groundtruth` in this session (Task 0.3) and treat its output, not the inline literals, as what SKF ingests. Volatile counts (23 phases / 28 read CLIs / schema v29 / 46 MCP tools) are cited via the snapshot + groundtruth, never free-standing.
- Drafting-session live spot-checks (2026-07-17, this container): `conda_forge_atlas.py` = 8,902 lines with `PHASES` at line 8679 and `SCHEMA_VERSION = 29` at line 139; `bootstrap_data.py` = 1,094 lines; `conda_forge_server.py` = 46 `@mcp.tool()`. All match § 3.3.

### AD bindings

- **AD-10 (legacy behavioral contracts bind the ports)** — this skill is the delivery vehicle for AD-10: it must model, faithfully and queryably, the contract list AD-10 freezes: Phase P two-layer cost gate (+ `test_no_thirty_gb_lie`), Phase K 3-RPS single-worker token bucket (`PHASE_K_AGGRESSIVE` opt-out), Phase F provenance discipline (`downloads_source` semantics, s3-only breakdown tables, DELETE-by-scope-key, calendar-month `downloads_30d`), Phase H serial gate (never re-include pypi-only denominators), B.5 `_pick_feedstock` attribution, `g10_spelling` no-clobber writeback, KEV overlay + `_coerce_cvss_score`, `cfe:*` namespace + `?channel=conda-forge` qualifier, EPSS 0–100 normalization, `v_pypi_intelligence_valid`/`v_current_version_vulns` view discipline, single-write-path (`add-handoff` helpers), post-v25 schema shape (dropped tables stay dropped). A BMAD story instruction never overrides these (CLAUDE.md Rule 1 authority).
- **AD-17 (snapshots advisory, never a substitute for live re-verification)** — applies twice: (a) the generated skill is itself an advisory snapshot — it carries its build timestamp + grounding commit (Task 3.2), and Wave-B agents treat it as provenance context, re-verifying against live source for anything load-bearing; (b) nothing in this story may position any dataset/skill content as a substitute for the authoring loop's live checks.
- **AD-18 (execution seam)** — the preconditions above; all BMAD artifact writes (including THIS file) resolve through the `_bmad-output` symlinks; switch only via `scripts/bmad-switch`; keystone budget raises recorded here for B1/B2/F1.
- **AD-19 (scope)** — the skill's modeled universe is fixed by § 3.3 + § 3.4; anything not listed there is outside the migration's universe and outside the skill's claimed coverage (must answer "not modeled").

### What "done" hands to Wave A

1. The queryable, provenance-grade SKF skill artifact (grounded + stamped), signed off — Wave-B's hallucination-free legacy reference; A1's dependency edge (`depends_on: [0-1-…]`) clears.
2. All Wave-0 preconditions green and recorded: hooks approved; active project = `pyforge-atlas` (marker + symlinks agree); live groundtruth/drift/llms-full runs clean (or divergences recorded); Phase T conditional status recorded; worktree bootstrap staged for A3; keystone budget raises documented; `policy.toml [verify]` plan staged for Wave A's gates.
3. Any SKF-provisioning decision (route, pin, output location) recorded here so A1's scaffold story and later loop sessions inherit it.

### Testing standards summary

- No verify gate exists yet (pre-harness — `kedro-test` is born at A1). Acceptance = the Task 4 query battery + attended human sign-off (AC 2/4).
- Guard: the repo's existing meta-tests must stay green after the skill lands (Task 3.4) — they pin the CFE skill's docs integrity and three-place rule; the new artifact must not enter their scope.
- Gates are never weakened/added ad hoc (NFR-12/AD-11); this story adds none.

### Project Structure Notes

- Story file location (this file): `_bmad-output/projects/pyforge-atlas/implementation-artifacts/` — Tier-3, gitignored, correct and expected; never commit it (drift-check HARD finding otherwise).
- Legacy tree is **read-only input** for this story: nothing under `.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/`, or `.claude/tools/` is modified. The only new file surface is the skill artifact itself (Task 3.1 location decision).
- Per CLAUDE.md Rule 1: reading/analyzing the atlas tooling requires invoking the `conda-forge-expert` skill in the implementation session before producing conclusions about it.

### Drafting assumptions + gaps found (unattended, recorded per protocol)

- **A-1 (GAP):** SKF is not provisioned anywhere in the repo (verified by repo-wide grep + `.claude/skills/` + `_bmad/` listing + `pixi.toml`); spec § 13.2 slots it Committed. Task 1 makes acquisition an explicit attended decision with a manual-translation fallback bound to the same ACs. No pixi task or install route was invented here.
- **A-2 (ASSUMPTION):** proposed skill output location `.claude/skills/cf-atlas-legacy/` — an inference, not a planning-artifact fact; flagged [ATTENDED-DECISION] for human confirmation (spec says "skill repository" without fixing a path; Spine's structural seed doesn't place it either).
- **A-3 (GAP, informational):** `prototypes/cf-atlas-kedro-viz` — referenced by spec § 3.4 (seed_gaps mirror) and § 14 (refresh-as-follow-up note) — does not exist at intake HEAD. No impact on 0.1 (nothing in this story consumes it); recorded so Wave-B/B6 sessions don't chase a phantom path.
- **A-4:** no `project-context.md` exists for this project; the `local-recipes` rulebook (`_bmad-output/projects/local-recipes/project-context.md`, v8.78.0-era) was carried as background repo law (volatile-count discipline, Rule 1/2) — its recipe-authoring rules do not bind this story.
- **A-5:** AC-1's inclusion of `bootstrap_data.py` is a tightening derived from spec §§ 2.4/3 ("~10,000 lines", 8,902 + 1,094) even though the § 9 Goal line names only `conda_forge_atlas.py`; tightening is permitted, weakening is not.
- **A-6:** previous-story intelligence and git-pattern analysis: none applicable — this is the first story of the effort; the epic went in-progress with this draft.

### References

- Spec (binding ACs + surface): `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` — § 9 Wave 0/Story 0.1, §§ 2.1–2.2 (agent workforce), § 2.4 (SKF), § 2.5 (graduated autonomy + preconditions), § 3.3 (live-surface snapshot), § 3.4 (migration boundary), § 13.2 (SKF slot), § 14 (Wave-0 preconditions block).
- Epics: `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md` — Epic 1/Story 0.1, D-2 (spec-ID keys), D-4 (bmad-switch supersession), D-13 (FR-less enabler), D-15 (Phase T re-check).
- Architecture: `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md` — AD-10, AD-17, AD-18, AD-19.
- PRD: `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md` — § 6.1 (wave table), § 6.2 (execution model), § 9.11 (switch-target deviation), § 12 (verification debt).
- Groundtruth: `_bmad-output/projects/pyforge-atlas/planning-artifacts/intake-groundtruth-2026-07-17.md`.
- Sprint feed: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml` (`story_meta.0-1-generate-legacy-contextual-skill`).
- Legacy source (read-only): `.claude/skills/conda-forge-expert/scripts/{conda_forge_atlas.py,bootstrap_data.py,atlas_phase.py,_http.py,mapping_gap.py,cisa_kev_fetcher.py,epss_fetcher.py,cwe_catalog_fetcher.py}`; `.claude/tools/conda_forge_server.py`; `reference/{atlas-phases-overview.md,atlas-phase-engineering.md}`; `guides/atlas-operations.md`.

## Dev Agent Record

### Agent Model Used

claude-fable-5 (remote Claude Code session, 2026-07-17), attended by rxm7706; forge executed via an orchestrating subagent + 4 parallel extraction subagents (each invoking conda-forge-expert per Rule 1) + 1 independent battery verifier.

### Task 0 — Wave-0 preconditions ledger (2026-07-17)

- 0.1 hooks: wired in `.claude/settings.json` (bmad_loop_hook.py); trust prompt is per-machine → **workstation-deferred** (approve at first loop run).
- 0.2 switch: `pyforge-atlas` active; marker + both symlinks agree (verified).
- 0.3 live checks (this container, pixi 0.73.0 conda-pkg install, `--frozen`): bmad-groundtruth = v8.78.0 / schema v29 / 46 MCP tools / 23 phases (matches § 3.3); bmad-drift-check = 0 findings (re-run green again AFTER the skill landed); llms-full-check = clean. NOTE: unfrozen re-solve fails on the `bmad-ui` env's local `build_artifacts/` channel (stubbed) and a `bmad-dashboard` pkg — use `--frozen` in fresh containers.
- 0.4 Phase T: trendshift spec `status: ready` → NOT shipped → surface stays 23 phases / schema v29.
- 0.5 worktree bootstrap: staged (A3 validates).
- 0.6 keystone budgets: already in `.bmad-loop/policy.toml` (session_timeout_min=180, dev_stall_grace_s=600, max_tokens_per_story=2M) — pyforge pilot raises carried; no further raise needed pre-B1/B2; F1 stall-grace revisit at Wave F.
- 0.7 `[verify]` staging: nothing to add for Wave 0 (pre-harness); `kedro-test`/`kedro-catalog-check` land as A1/A2 deliverables (recorded explicitly).

### Task 1 — SKF provisioning decision (ATTENDED)

- Owner decision: provision SKF (not the manual fallback). Route: **npm `bmad-module-skill-forge@2.0.1`** (armelhbobdad/bmad-module-skill-forge, MIT) — identified by the owner; vetted via tarball inspection before execution. agentskills spec revision: as vendored in the module (`src/knowledge/agentskills-spec.md`).
- Search record: PyPI `skillforge` 1.2.0 (preference-skill generator — rejected, no codebase ingestion); tripleyak/SkillForge + AgriciDaniel/skill-forge (generic skill-creator methodologies — rejected).
- Install: interactive-only CLI driven non-interactively via a driver script calling the package's `Installer` class with the promptInstall config shape (scratchpad `skf-install-driver.js`); config: skills_output_folder=`.claude/skills`, forge_data_folder=Tier-3 pyforge-atlas implementation-artifacts, ides=[claude-code], learning=true. Committed `b18cbb5`.
- Container notes: `npx` of the remote package was classifier-blocked → tarball fetched from registry.npmjs.org (allowed host) and inspected first; GitHub release downloads are egress-blocked (403) in this environment.

### Task 3 — output location (ATTENDED) + grounding

- Owner decision: `.claude/skills/cf-atlas-legacy/` (in-repo). SKF emitted its versioned layout: `cf-atlas-legacy/active -> 8.78.0/cf-atlas-legacy/{SKILL.md, context-snippet.md, metadata.json, provenance-map.json, references/*5}`.
- Grounding stamp (AD-17): 2026-07-17 · commit `b18cbb5` · CFE pin v8.78.0 · schema v29. SKF tier: Quick (ast-grep/gh/qmd/ccc absent) → all provenance T1-low source-reads with grep-verified anchors.
- SKF gates: skill-check 100/100 (0 err/0 warn); numerator 130/130 (first run 121/130 inflated → fixed); export coverage 100%; structure gates pass after api_surface heading fix; compute-score 100 ≥ 80 → PASS. Repo meta-tests: 1009 passed / 4 skipped (pre-existing) / 0 failed. Forge workspace + evidence-report + test-report under `forge-data/cf-atlas-legacy/`.

### Task 4 — provenance battery (independent, fresh agent)

- **PASS.** Probes a–f: all citations CONFIRMED line-exact against live source (~40 anchors incl. `_TTL_GATED`@atlas_phase.py:44, PHASES@:8679–8701, Phase P bounds@:7690–7705); 0 DRIFTED / 0 WRONG. Probe g (negative): correct "not modeled / not found" for both halves (Phase Z fabrication bait; gemini_server.py carved out by spec:175–177). `git diff b18cbb5..HEAD` over modeled sources: empty. Full transcript: forge-data test-report + this session's verifier report.
- Cosmetic nit only: metadata `generation_date` is a midnight placeholder vs provenance map's 09:15:33Z timestamp.

### Task 5.3 — CFE-retro ledger items (for effort closeout, Rule 2)

- D1: spec/docs prose describes `_PARTITIONDATE` pruning, but code REJECTS it (BigQuery `Unrecognized name` — literal TIMESTAMP bounds used, CFA:7690–7705). Spec § 3.3/engineering-doc correction candidate.
- D3: `_parse_retry_after` lives in conda_forge_atlas.py:2668, not `_http.py` (story Task 2.1 hint was imprecise).
- D4: `_coerce_cvss_score` lives in detail_cf_atlas.py:295 (read-side), only referenced at the boundary.
- Env gotcha: fresh-container pixi re-solve requires the `build_artifacts/linux64` stub + `--frozen` (bmad-ui env local channel; bmad-dashboard pkg).

### Debug Log References

- Forge evidence-report + fix log: `forge-data/cf-atlas-legacy/8.78.0/evidence-report.md`
- SKF test result envelopes: `forge-data/cf-atlas-legacy/8.78.0/skf-test-skill-result-*.json`
- Description-guard incident (operator mis-invocation, restored hash-identical): evidence-report § Description Guard.

### Completion Notes List

- Story context created by bmad-create-story (unattended draft, 2026-07-17). Ultimate context engine analysis completed — comprehensive developer guide created; attended decisions explicitly marked.
- 2026-07-17: Tasks 0–4 complete. SKF provisioned (2.0.1) and pipeline run end-to-end; cf-atlas-legacy forged, validated (SKF 100/100; independent battery PASS), meta-tests green, drift-check green post-landing. Commits: `b18cbb5` (SKF provisioning), `f6a0dc0` (WIP snapshot), `6658049` (forge complete). Awaiting Task-5.1 human sign-off.
- Wave-A handoff (per Dev Notes): artifact grounded+stamped at `.claude/skills/cf-atlas-legacy/`; preconditions ledger above (hooks = workstation-deferred is the one open item); SKF decisions recorded here for A1 inheritance.

### File List

- `.claude/skills/cf-atlas-legacy/**` (NEW, tracked — the deliverable)
- `_bmad/skf/**`, `_bmad/_config/skf-manifest.yaml`, `.claude/skills/skf-*/**`, `_skf-learn/**`, `.gitignore` (+`_bmad/_memory/`) (NEW, tracked — SKF module provisioning)
- `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/**` (NEW, Tier-3 gitignored — forge workspace, evidence, test reports)
- `_bmad/_memory/forger-sidecar/**` (gitignored — sidecar)
- This story file + `sprint-status.yaml` (Tier-3, updated)
- Legacy tree: ZERO modifications (read-only input, verified)

---

> Source: `specs/spec-a1-scaffold-the-kedro-pixi-project-via-nebi.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story A1 (2.1): Scaffold the Kedro + pixi project via `nebi`'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story A1 (2.1): Scaffold the Kedro + pixi project via `nebi`

As the operator,
I want the Kedro project structure and pixi wiring initialized by `nebi` with its own lean env and `kedro-test` gate,
So that every later story lands in a provisioned, verifiable, worktree-affordable project.

**Acceptance Criteria:** (spec § 9 Story A1, binding)

**Given** the FR-15 stack already resolved in the `local-recipes` env
**When** `nebi` scaffolds the project
**Then** a Kedro project skeleton exists, scaffolded by `nebi`
**And** the FR-15 stack resolves at its pins on Python 3.14 (all conda-forge, no standalone binaries / JVM) and `pixi run` activates cleanly
**And** `pixi run -e local-recipes llms-full-check` passes after any dependency change (library catalog updated in the same PR)
**And** air-gapped provisioning is documented for both routing layers (`.pixi/config.toml [pypi-config]` and the `_http.py` overrides)
**And** the scaffolded project ships its own lean pixi env (loop worktrees never materialize the fat `local-recipes` env) and the `kedro-test` verify task — Wave A's deterministic gate — including the import smoke for py3.14-unclassified glue (e.g. `kedro_dagster`, AD-16)
**And** *(correct-course 2026-07-17)* the scaffold root is `src/shared/packages/pyforge-atlas/` — a pixi build workspace member mirroring `pyforge-warden` (hatchling; dual conda + wheel/sdist artifacts; dedicated `[feature.pyforge-atlas]` env + `pyforge-atlas-build-conda`/`-build-dist` tasks)
**And** *(correct-course 2026-07-17)* the Python package is the `pyforge.atlas` namespace package (`src/pyforge/atlas/`, imports `pyforge.atlas.*` beside `pyforge.warden.*`); `kedro-test`'s import smoke covers the Kedro-project-in-namespace-package seam, with flat `pyforge_atlas` as the recorded fallback if nebi/Kedro tooling rejects the dotted form
**And** *(correct-course 2026-07-17)* `pyforge-warden` is wired as the optional extra `pyforge-atlas[gate]` — the only cross-package code dependency (ComplianceReport schema/validators, consumed at F4); installed in the atlas env by default; no reverse warden→atlas import exists (both tools stay independently installable).

- **FRs:** FR-15.
- **Invariants:** AD-16, AD-11 (gate is a named story deliverable), AD-18, Packaging & namespace convention (warden-aligned — Spine Deferred slot RESOLVED 2026-07-17).
- **Mode:** DEV-AUTO (harness-building, § 2.5).
- **Gating question:** none.
- **Verify gate:** **builds `kedro-test`**.
- **Depends on:** 0.1.

### Story A2 (2.2): Define the Data Catalog for all sources + outputs

As a pipeline node author,
I want every API source and Parquet output declared as a Kedro dataset in `conf/base/catalog.yml`,
So that no data-access logic ever lives in node functions and credentials scope per host.

**Acceptance Criteria:** (spec § 9 Story A2, binding)

**Given** the legacy `_http.py` / `init_schema()` data-access surface
**When** the catalog is authored
**Then** all current data access is represented declaratively in `catalog.yml`
**And** no data-access logic remains inline in (future) node functions
**And** a `kedro-catalog-check` verify task exists (catalog resolves, no inline IO) — a § 2.5 loop gate — shipping the AD-1 import-direction meta-test
**And** credentials attach per destination host only (a non-JFrog host never receives `X-JFrog-Art-Api`) and all 20 `resolve_*_urls` override points survive as dataset-level endpoint config (FR-1 consequences).

- **FRs:** FR-1.
- **Invariants:** AD-2, AD-1 (meta-test), AD-13 (endpoint override convention).
- **Mode:** DEV-AUTO (harness-building, § 2.5).
- **Gating question:** none.
- **Verify gate:** **builds `kedro-catalog-check`**.
- **Depends on:** A1.

### Story A3 (2.3): Implement `IncrementalParquetDataset` for TTL gating

As a pipeline node author,
I want the `*_fetched_at` TTL incremental logic encapsulated in one reusable dataset class with per-dataset TTLs,
So that no node ever re-implements checkpoint/TTL/backoff and resumability is Kedro-native.

**Acceptance Criteria:** (spec § 9 Story A3, binding)

**Given** the catalog from A2
**When** `IncrementalParquetDataset` is implemented
**Then** it exists and round-trips TTL state
**And** a unit test proves stale rows are re-fetched and fresh rows are skipped
**And** TTLs are declared per dataset in the catalog (Phase D 7 d, Phase P 30 d, EPSS 1 d, CWE 90 d, …) — never a global constant (FR-3).

- **FRs:** FR-3, FR-4 (the dataset class is the resumability primitive).
- **Invariants:** AD-5, AD-18 (this story validates the worktree symlink bootstrap and measures worktree env-materialization cost), AD-11.
- **Mode:** LOOP-S — **the designated first loop-driven story and worktree smoke** (§ 2.5 preconditions).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (unit suite; also proves the loop-in-worktree seam before Wave B commits to loop execution).
- **Depends on:** A1, A2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-a2-define-the-data-catalog-for-all-sources-outputs.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story A2 (2.2): Define the Data Catalog for all sources + outputs'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story A2 (2.2): Define the Data Catalog for all sources + outputs

As a pipeline node author,
I want every API source and Parquet output declared as a Kedro dataset in `conf/base/catalog.yml`,
So that no data-access logic ever lives in node functions and credentials scope per host.

**Acceptance Criteria:** (spec § 9 Story A2, binding)

**Given** the legacy `_http.py` / `init_schema()` data-access surface
**When** the catalog is authored
**Then** all current data access is represented declaratively in `catalog.yml`
**And** no data-access logic remains inline in (future) node functions
**And** a `kedro-catalog-check` verify task exists (catalog resolves, no inline IO) — a § 2.5 loop gate — shipping the AD-1 import-direction meta-test
**And** credentials attach per destination host only (a non-JFrog host never receives `X-JFrog-Art-Api`) and all 20 `resolve_*_urls` override points survive as dataset-level endpoint config (FR-1 consequences).

- **FRs:** FR-1.
- **Invariants:** AD-2, AD-1 (meta-test), AD-13 (endpoint override convention).
- **Mode:** DEV-AUTO (harness-building, § 2.5).
- **Gating question:** none.
- **Verify gate:** **builds `kedro-catalog-check`**.
- **Depends on:** A1.

### Story A3 (2.3): Implement `IncrementalParquetDataset` for TTL gating

As a pipeline node author,
I want the `*_fetched_at` TTL incremental logic encapsulated in one reusable dataset class with per-dataset TTLs,
So that no node ever re-implements checkpoint/TTL/backoff and resumability is Kedro-native.

**Acceptance Criteria:** (spec § 9 Story A3, binding)

**Given** the catalog from A2
**When** `IncrementalParquetDataset` is implemented
**Then** it exists and round-trips TTL state
**And** a unit test proves stale rows are re-fetched and fresh rows are skipped
**And** TTLs are declared per dataset in the catalog (Phase D 7 d, Phase P 30 d, EPSS 1 d, CWE 90 d, …) — never a global constant (FR-3).

- **FRs:** FR-3, FR-4 (the dataset class is the resumability primitive).
- **Invariants:** AD-5, AD-18 (this story validates the worktree symlink bootstrap and measures worktree env-materialization cost), AD-11.
- **Mode:** LOOP-S — **the designated first loop-driven story and worktree smoke** (§ 2.5 preconditions).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (unit suite; also proves the loop-in-worktree seam before Wave B commits to loop execution).
- **Depends on:** A1, A2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-a3-implement-incrementalparquetdataset-for-ttl-gating.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story A3 (2.3): Implement `IncrementalParquetDataset` for TTL gating'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story A3 (2.3): Implement `IncrementalParquetDataset` for TTL gating

As a pipeline node author,
I want the `*_fetched_at` TTL incremental logic encapsulated in one reusable dataset class with per-dataset TTLs,
So that no node ever re-implements checkpoint/TTL/backoff and resumability is Kedro-native.

**Acceptance Criteria:** (spec § 9 Story A3, binding)

**Given** the catalog from A2
**When** `IncrementalParquetDataset` is implemented
**Then** it exists and round-trips TTL state
**And** a unit test proves stale rows are re-fetched and fresh rows are skipped
**And** TTLs are declared per dataset in the catalog (Phase D 7 d, Phase P 30 d, EPSS 1 d, CWE 90 d, …) — never a global constant (FR-3).

- **FRs:** FR-3, FR-4 (the dataset class is the resumability primitive).
- **Invariants:** AD-5, AD-18 (this story validates the worktree symlink bootstrap and measures worktree env-materialization cost), AD-11.
- **Mode:** LOOP-S — **the designated first loop-driven story and worktree smoke** (§ 2.5 preconditions).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (unit suite; also proves the loop-in-worktree seam before Wave B commits to loop execution).
- **Depends on:** A1, A2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b1-port-the-conda-side-backbone-phases-into-kedro-nodes.md` (canonical file — still lives there).

<!-- RECOVERED 2026-07-25: original spec, survived intact in implementation-artifacts/b1-port-the-conda-side-backbone-phases-into-kedro-nodes.md; promoted to tracked planning-artifacts/specs/ for durability. -->
# Story B1: Port the conda-side backbone phases into Kedro nodes

Status: done (closed by owner direction, 2026-07-17; DEV-AUTO + independent follow-up review; closer re-verified member tree 137/137, catalog-check 38, parity 14, drift 0 integrity)

<!-- Frozen spec ID: B1 (epics.md D-2 — the spec § 9 ID is the primary key; the
     Epic.Story alias "3.1" is informational only). Story key:
     b1-port-the-conda-side-backbone-phases-into-kedro-nodes. -->

## Story

As a **BMAD execution agent**,
I want **the conda-forge enumeration + graph-building + VCS/health phases (B, B.5, B.6, E, E.5, F, J, K, L, M, N per § 3.3) as pure-function Kedro nodes split across the `core` and `vcs_health` pipelines of § 5.2**,
so that **the conda-side backbone resolves from the DAG (no procedural call order) with its shipped, fixture-guarded legacy behavioral contracts intact**.

## Acceptance Criteria

Restated from **epics.md § Story B1 (3.1)** and **spec § 9 Story B1 (binding)** — verbatim or tightened. Each phase→node→dataset→contract binding is in the **Port Map** (Dev Notes) and is load-bearing for these ACs.

1. **Pure-function nodes + auto-resolving DAG.** Each of the 11 conda-side phases (B, B.5, B.6, E, E.5, F, J, K, L, M, N) is a pure-function node with **explicit declared inputs/outputs** (DataFrame in → DataFrame out; no data-access logic in the node body, AD-2). The DAG **resolves execution order automatically** from the declared input/output dataset names — no procedural call order, no `PHASES` list driver (FR-2, AD-3). The two pipelines are the `core` and `vcs_health` snake_case packages of § 5.2 (AD-3).
2. **Phase B.5 `_pick_feedstock` attribution survives** with its umbrella-vs-dedicated semantics (split-out output → its dedicated feedstock, e.g. `dbt-bigquery` → the `dbt-bigquery` feedstock, not `dbt`); **its unit tests carry over as node tests** (AD-10).
3. **Phase I becomes an explicit node** (`compute_version_download_history`) with **declared outputs** (`core_version_download_history`) — no longer an unregistered side-effect of Phase F's anaconda-api path (FR-2, AD-3).
4. **The § 3.3 per-phase engineering contracts are fixture-tested in the node suite** (AD-10): **Phase K's single-worker 3-RPS token bucket** (secondary-rate-limit defense; `PHASE_K_AGGRESSIVE` opt-out) **and Phase F's provenance discipline** (`downloads_source` semantics; s3-only breakdown tables; DELETE-by-scope-key writes; calendar-month `downloads_30d` — **not** a rolling window; one consolidated pyarrow sweep; dirty `pkg_python` regex-filter). Fixtures are stubbed/injected — **never a live endpoint** (AD-11).
5. **The Phase E maintainer-universe delta is reconciled or explicitly documented** — the ~44-feedstock disagreement between atlas `package_maintainers` (769 = 537 sole + 232 co) and cf-graph `node_attrs` discovery (813 = 558 + 255) (spec:287–292). Tightened disposition (this story): **DOCUMENT the delta with provenance in the `enrich_maintainers` node and the parity notes; defer full reconciliation to B4** (the AC's "or explicitly documents" branch; see Deferred-Item Dispositions).
6. **Phase B.6 ports with its lite semantics** — presence-in-current-repodata → `latest_status` (all parity requires). Full per-version yanked detection is an **optional follow-on, explicitly NOT part of this story** (spec § 12; Spine Deferred "Phase B.6 full yanked detection").
7. **`kedro-test` stays green** (verify gate, consumed — must remain green; A1/A2/A3's 74 + 38 tests must not regress). **The `parity-diff` gate BEGINS here** (B1 builds the harness skeleton + the Core/VCS parity fixtures for the 11 phases ported here; B2–B3 extend it; B4 consumes it at the attended event — see Parity-Diff Harness Scope).
8. **Maps to FR-2.** Invariants: AD-3, AD-10, AD-4 (Parquet canonical from Wave A), AD-5 (no node-local checkpointing — the dataset owns TTL), AD-13 (offline degradation).

## Tasks / Subtasks

> Real repo root for the scaffold: `src/shared/packages/pyforge-atlas/` (the pixi-build workspace member; `pyforge.atlas` namespace package under `src/pyforge/atlas/`). Legacy source of every port: `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` (`CFA` below) at the cited lines (commit `b18cbb5`).

- [x] **Task 0 — Create the two pipeline packages (they do NOT exist yet; see Gap G-1).** (AC: 1)
  - [x] Create `src/pyforge/atlas/pipelines/core/` with `__init__.py` (exports `create_pipeline`), `nodes.py`, `pipeline.py`.
  - [x] Create `src/pyforge/atlas/pipelines/vcs_health/` with the same three files.
  - [x] `register_pipelines()` (`src/pyforge/atlas/pipeline_registry.py`) already uses `find_pipelines(raise_errors=True)` + an empty-`__default__` seed — **do not edit it**; `find_pipelines()` auto-discovers the new packages. Verify both register.
  - [x] Every ported node carries a `# legacy: Phase <ID>` provenance comment (spine naming convention).

- [x] **Task 1 — Core pipeline nodes (Phases B, B.5, B.6, F, I, J, M → 7 nodes).** (AC: 1, 2, 3, 4)
  - [x] `enumerate_conda_packages` (**# legacy: Phase B**, `phase_b_conda_enumeration` CFA:1408): reads `core_repodata_raw` + `core_channeldata_raw` → writes `core_packages_enumerated`.
  - [x] `attribute_feedstocks` (**# legacy: Phase B.5**, `phase_b5_feedstock_outputs` CFA:1593): reads `core_feedstock_outputs_raw` → writes `core_feedstock_attribution`. Port `_pick_feedstock` (CFA:1572; logic CFA:1586–1590; call site CFA:1632) as a pure helper; **carry over its unit tests as node tests** (AC-2). NOTE the catalog comment: the live route is `resolve_github_urls` (GITHUB_BASE_URL archive zip), not GITHUB_RAW (catalog.yml:52–58, corrected in A2's Dev Agent Record).
  - [x] `detect_latest_status` (**# legacy: Phase B.6**, `phase_b6_yanked_detection` CFA:1665): reads `core_repodata_raw`/`core_channeldata_raw` → writes `core_latest_status`. **Lite semantics only** (presence-in-repodata → `latest_status`); no per-version yanked scan (AC-6).
  - [x] `compute_downloads` (**# legacy: Phase F**, `phase_f_downloads` CFA:3560): reads `core_anaconda_downloads_raw` + `core_s3_download_stats_raw` → writes `core_downloads` + `core_downloads_platform_breakdown` + `core_downloads_pyver_breakdown` + `core_downloads_channel_breakdown`. **Provenance discipline fixture-tested** (AC-4): `downloads_source` ∈ {`anaconda-api`,`s3-parquet`,`merged`} correlated-but-distinct (CFA:188); breakdown tables written **only on the s3-parquet path** (CFA:538/549/572); DELETE-by-scope-key + INSERT in one transaction, chunked ≤500 for SQLite's 999-param limit → in Parquet this is a **replace-by-scope-key** write (CFA:3423–3450); `downloads_30d` = latest **calendar month**, not a rolling window (CFA:3162); one consolidated pyarrow sweep for all F+ metrics (do not split passes); regex-filter the dirty `pkg_python` column before aggregation.
  - [x] `compute_version_download_history` (**# legacy: Phase I**, promoted from Phase F side-effect — anaconda-api site CFA:2931, s3 site CFA:3402; table schema CFA:312–316): reads `core_anaconda_downloads_raw` → writes **`core_version_download_history`** as a **declared output** (AC-3). Consumed downstream by Phase G' (CFA:6861), `version-downloads`, `release-cadence` — declare the output name so those consumers resolve by catalog name (AD-3).
  - [x] `build_dependency_graph` (**# legacy: Phase J**, `phase_j_dependency_graph` CFA:6067): reads `core_cf_graph_raw` → writes `core_dependencies`. Preserve the **archived-feedstock skip-set filter at the write site** (v7.9.0 fix — Phase J builds an `inactive_feedstocks` skip-set before opening the cf-graph tarball; spec § 3.3 "Phases J + M archived-feedstock filter").
  - [x] `compute_feedstock_health` (**# legacy: Phase M**, `phase_m_feedstock_health` CFA:6263): reads `core_cf_graph_raw` → writes `core_feedstock_health`. Same archived-feedstock scope filter at the write SELECT.
  - [x] **Flip `core_anaconda_downloads_raw`** (catalog.yml:69–74, marked `# FLIP(B1)`): from the interim single-URL `api.APIDataset` to a factory/partitioned dataset expressing per-package `/package/<owner>/<name>` request parameterization — **nodes may NOT build request URLs** (AC-2). Fetch/parameterization is dataset-owned; the node consumes resolved DataFrames.

- [x] **Task 2 — VCS & Health pipeline nodes (Phases E, E.5, K, L, N → 5 nodes).** (AC: 1, 4, 5)
  - [x] `enrich_maintainers` (**# legacy: Phase E**, `phase_e_enrichment` CFA:2188): reads `core_cf_graph_raw` (**cross-pipeline — produced by `core`, referenced by catalog name per AD-3**) → writes `vcs_maintainers` + `vcs_package_maintainers`. **Document the maintainer-universe delta** in the node docstring + parity notes (AC-5; Deferred-Item Dispositions).
  - [x] `detect_archived_feedstocks` (**# legacy: Phase E.5**, `phase_e5_archived_feedstocks` CFA:2504): reads `vcs_github_api_raw` → writes `vcs_archived_feedstocks`.
  - [x] `track_upstream_versions` (**# legacy: Phase K**, `phase_k_vcs_versions` CFA:5039): reads `vcs_github_api_raw`/`vcs_gitlab_api_raw`/`vcs_codeberg_api_raw` → writes `vcs_upstream_versions`. **3-RPS token bucket fixture-tested** (AC-4): single-worker default (`_RateLimitedScheduler` CFA:1345; 3.0 RPS default CFA:1333/5117; refill CFA:1393); `PHASE_K_AGGRESSIVE=1` opt-out restores 8 workers, non-"1" does NOT re-arm burst (CFA:5114–5115/5132); 403 → `upstream_versions.last_error` + re-pick via TTL bypass; `Retry-After` via `_parse_retry_after` (CFA:2668). **Rate-limiting lives in the dataset/injected fetcher, NOT the node body** (see Pure-Node-vs-Fetching Resolution).
  - [x] `track_registry_versions` (**# legacy: Phase L**, `phase_l_extra_registries` CFA:5841): reads the 8 `vcs_registry_*_raw` sources → writes `vcs_registry_versions`. Preserve per-registry concurrency caps + per-source TTL treatment (dataset-owned).
  - [x] `fetch_live_health` (**# legacy: Phase N**, `phase_n_github_live` CFA:6525): reads `vcs_github_api_raw` → writes `vcs_live_health`.
  - [x] **Resolve the GitHub-API request-dataset flip (Gap G-2).** `vcs_github_api_raw` (catalog.yml:411–420) is an interim single-URL POST placeholder whose comment says the per-query factory dataset "lands with the vcs port (B2)" — **that attribution is wrong: E.5/K/N are B1 phases** in `vcs_health`. Author the GitHub request-parameterized dataset (one dataset = one request body, POST GraphQL / REST) **in this story**, with the rate-limit discipline attached at dataset/resource level. Record the corrected attribution.

- [x] **Task 3 — Wire both pipelines' DAGs.** (AC: 1)
  - [x] `core/pipeline.py` + `vcs_health/pipeline.py` build `Pipeline([node(...), ...])` binding each node's `inputs=`/`outputs=` to the catalog names above; the cross-pipeline `core_cf_graph_raw` edge (core → vcs_health Phase E) resolves by name (AD-3).
  - [x] Confirm `kedro run` resolves topological order with **no procedural sequencing** (AC-1) and no two pipelines writing one dataset (AD-3).

- [x] **Task 4 — Node unit tests on `pandas.DataFrame` IO.** (AC: 1, 2, 4)
  - [x] `tests/pipelines/core/` + `tests/pipelines/vcs_health/` — each node independently unit-tested on DataFrame in/out (no live network).
  - [x] Carry over Phase B.5 `_pick_feedstock` unit tests as node tests (AC-2): empty→None; `len>1 and pkg_name in feedstocks`→`pkg_name`; else `feedstocks[0]` (CFA:1586–1590).
  - [x] Fixture-test Phase K 3-RPS bucket + Phase F provenance discipline against a **stubbed/injected client** (AC-4, AD-11) — never a live endpoint.

- [x] **Task 5 — Begin the `parity-diff` harness (see Parity-Diff Harness Scope).** (AC: 7)
  - [x] Author the harness skeleton under `tests/parity/` + register the `parity-diff` pixi task (fixture-mode; `--frozen`, non-credentialed, AD-11).
  - [x] Capture-once legacy output fixtures for the 11 Core/VCS phases (generated attended per AD-11 / spine "Tests & fixtures" row — committed to the tracked test tree, **never read from `.claude/data/` at gate time**). Diff each migrated node's output DataFrame against its legacy fixture snapshot.
  - [x] Scope guard: B1 does NOT run the full B4 credentialed live-parity run (attended B4 event).

- [x] **Task 6 — Resolve the 3 B1-bound deferred-work items (see Deferred-Item Dispositions).** (AC: 5, 8)
  - [x] **DW-A3-P10 (epoch-ms guard):** guarantee node outputs stamp `fetched_at` in **epoch seconds**; normalize any ms-sourced timestamp (repodata per-build timestamps are ms) to seconds **at the dataset boundary** (spine Identity&formats: "convert once, at the dataset boundary"). Decide + record whether to add the magnitude guard to `IncrementalParquetDataset` (recommended: add it now — Phase F/I are the first real ms-source writers, so it is no longer dead code).
  - [x] **DW-A3-P11 (kedro_datasets private-internal pin):** re-verify `IncrementalParquetDataset._inner._describe()`/`._exists()` against the in-env `kedro_datasets` version (was 9.5.0); B1 is the first story to exercise the flipped datasets through nodes — confirm, add a compat check or switch to a public accessor if a bump landed.
  - [x] **DW-A3-TTL-parity (fresh-at-exactly-ttl):** confirm the intended boundary against legacy `_TTL_GATED` (`age >= ttl` = stale at exactly ttl) vs the new `stale_mask` (`fetched_at < now - ttl` = **fresh** at exactly `now-ttl`). Make the parity call deliberately; adjust `<`→`<=` in `stale_mask` (`datasets/incremental_parquet.py:269`) **iff** parity requires, and update `test_stale_mask_gates_old_stale_recent_fresh`.
  - [x] (NOT B1: the A2-P4 dynamic-JFrog-credential item is assigned to **B5**, not this story.)

- [x] **Task 7 — Gates green.** (AC: 7, 8)
  - [x] `PYTHONPATH=src/shared/packages/pyforge-atlas/src:src/shared/packages/pyforge-warden/src pixi run --frozen -e local-recipes python -m pytest src/shared/packages/pyforge-atlas/tests -q` (fat-env interim, A1/A2/A3 pattern) — or `pixi run --frozen -e pyforge-atlas kedro-test` once the workstation re-lock lands the env (DW-A1 blocker below). Keep A1/A2/A3's suites green.
  - [x] If dependencies change, update `docs/library-llms-full.md` in the same PR (`llms-full-check`, AD-16) — likely **no** dep change (all phase logic ports onto in-env pandas/kedro).

## Dev Notes

### The Port Map (the implementer's contract — follow this table)

11 phases + the promoted Phase I = **12 nodes** across two pipelines. Every phase → target pipeline (§ 5.2 / AD-3) → node (`<verb>_<subject>`) → catalog datasets it reads/writes (from `conf/base/catalog.yml`, Story A2) → AD-10 contract(s) it must preserve → legacy `file:line` (`CFA` = `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` @ `b18cbb5`).

| Phase | Pipeline | Node | Reads (catalog) | Writes (catalog) | AD-10 / § 3.3 contract to preserve | Legacy `CFA` line(s) |
|---|---|---|---|---|---|---|
| **B** | core | `enumerate_conda_packages` | `core_repodata_raw`, `core_channeldata_raw` | `core_packages_enumerated` | `v_actionable_packages` scope discipline (raw `packages` reads carry the persona-filter triplet or a `# scope:` note) | `phase_b_conda_enumeration` 1408; view 376 |
| **B.5** | core | `attribute_feedstocks` | `core_feedstock_outputs_raw` | `core_feedstock_attribution` | `_pick_feedstock` umbrella-vs-dedicated attribution; unit tests carried over (AC-2) | `phase_b5_feedstock_outputs` 1593; `_pick_feedstock` 1572 (logic 1586–1590, call 1632) |
| **B.6** | core | `detect_latest_status` | `core_repodata_raw`, `core_channeldata_raw` | `core_latest_status` | **lite** presence→`latest_status`; NO per-version yanked scan (AC-6) | `phase_b6_yanked_detection` 1665 |
| **F** | core | `compute_downloads` | `core_anaconda_downloads_raw` (**FLIP B1**), `core_s3_download_stats_raw` | `core_downloads`, `core_downloads_platform_breakdown`, `core_downloads_pyver_breakdown`, `core_downloads_channel_breakdown` | provenance discipline: `downloads_source` distinct; s3-only breakdowns; replace-by-scope-key; calendar-month `downloads_30d`; single pyarrow sweep; `pkg_python` regex-filter | `phase_f_downloads` 3560; contracts 188/538/549/572/3162/3423–3450 |
| **I** | core | `compute_version_download_history` | `core_anaconda_downloads_raw` | `core_version_download_history` | **promote to explicit node w/ declared output** (AC-3) | side-effect sites 2931 (api) / 3402 (s3); table 312–316; consumed by G' 6861 |
| **J** | core | `build_dependency_graph` | `core_cf_graph_raw` | `core_dependencies` | archived-feedstock skip-set filter at the write site | `phase_j_dependency_graph` 6067 |
| **M** | core | `compute_feedstock_health` | `core_cf_graph_raw` | `core_feedstock_health` | archived-feedstock scope filter at write SELECT | `phase_m_feedstock_health` 6263 |
| **E** | vcs_health | `enrich_maintainers` | `core_cf_graph_raw` (cross-pipeline, core-produced) | `vcs_maintainers`, `vcs_package_maintainers` | **maintainer-universe ~44 delta documented** (AC-5) | `phase_e_enrichment` 2188; delta spec:287–292 |
| **E.5** | vcs_health | `detect_archived_feedstocks` | `vcs_github_api_raw` | `vcs_archived_feedstocks` | — | `phase_e5_archived_feedstocks` 2504 |
| **K** | vcs_health | `track_upstream_versions` | `vcs_github_api_raw`, `vcs_gitlab_api_raw`, `vcs_codeberg_api_raw` | `vcs_upstream_versions` | **3-RPS single-worker token bucket**; `PHASE_K_AGGRESSIVE` opt-out; 403→`last_error`+TTL bypass; `Retry-After` jitter | `phase_k_vcs_versions` 5039; `_RateLimitedScheduler` 1345 (rps 1333/5117; AGGRESSIVE 5132); `_parse_retry_after` 2668 |
| **L** | vcs_health | `track_registry_versions` | `vcs_registry_{npm,cran,cpan,luarocks,crates,rubygems,maven,nuget}_raw` (8) | `vcs_registry_versions` | per-registry concurrency caps; per-source TTL | `phase_l_extra_registries` 5841 |
| **N** | vcs_health | `fetch_live_health` | `vcs_github_api_raw` | `vcs_live_health` | rate-limit-stderr detection; live-signal 1 d TTL | `phase_n_github_live` 6525 |

Catalog TTLs the flipped datasets consume (`conf/base/parameters.yml` `ttls:`): `core_downloads*` + `core_version_download_history` = 7 d; `core_cf_graph_raw` = 1 d cached tarball; `vcs_upstream_versions`/`vcs_registry_versions` = 7 d; `vcs_live_health` = 1 d. Injected at runtime by `pyforge.atlas.hooks.ProjectHooks` from `params:ttls.<name>` (nodes never read TTLs).

### THE CRUX — Pure-node-vs-fetching resolution (get this right; it is the whole migration's thesis)

Nodes are **pure functions**: `pandas.DataFrame` in → `pandas.DataFrame` out, no inline IO. A2's `test_no_inline_io.py` (part of `kedro-catalog-check`) structurally bans HTTP/DB clients inside `pipelines/`, `datasets/`, `hooks/`, `mcp/`.

The **one tension** in porting these 11 phases is that Phase K's **3-RPS token bucket** and Phase F's HTTP fetches are, in the legacy monolith, imperative code *inside* the phase function. They cannot live in a pure node body. **Resolution (per AD-2 / AD-5 / AD-13 + the spine "State & errors" row — binding):**

- **The fetching + rate-limiting is a DATASET/RESOURCE concern, not a node concern.** The HTTP request, the `_RateLimitedScheduler` token bucket, `Retry-After` + jittered backoff, per-registry concurrency caps, and the 403→`last_error`→TTL-bypass re-pick all move into the **catalog API dataset** (the flipped/factory datasets: `core_anaconda_downloads_raw`, the new `vcs_github_api_raw` request dataset, the `vcs_registry_*` datasets) **or an injected fetcher-client passed to the node as a catalog input**. The **node body stays pure** — it receives already-fetched DataFrames (or a client handle whose IO is dataset-owned) and does only transform/aggregate/attribute logic.
- **The contract is fixture-tested against a stub/injected client, NEVER a live endpoint** (AD-11, AD-10). The 3-RPS bucket behavior, the `PHASE_K_AGGRESSIVE` toggle, and Phase F's provenance discipline are proven by fixtures that stub the client and assert the discipline — no network in any gate.
- **TTL/checkpointing is `IncrementalParquetDataset`, never node-local** (AD-5): the node calls `stale_mask`/`fresh_mask` on the loaded frame to decide which rows to re-fetch, then hands the re-fetch set to the dataset — but the node implements no checkpoint, no `phase_state`, no backoff. `phase_state` is gone (FR-4).

If any AC or convenience tempts an inline `requests`/`urllib` call in a node, **stop** — that is the exact failure the migration exists to remove. Route it through the catalog.

### Parity-Diff Harness Scope (B1 begins it; B4 consumes it)

`parity-diff` is the Wave-B verify gate; it is **built incrementally B1→B3 and consumed at the attended B4 event** (AD-11, epics.md § Epic 3). B1's contribution:

- **Harness skeleton:** `tests/parity/` structure + a registered `parity-diff` pixi task that, in **fixture mode**, diffs a migrated node's output DataFrame against a captured-once legacy output snapshot. `--frozen`, non-credentialed, lives in the tracked test tree (AD-11).
- **Core + VCS parity fixtures** for the **11 phases ported here only** — legacy output samples generated **attended, once, from operator runtime data** (spine "Tests & fixtures" row) and committed; the gate never reads `.claude/data/`.
- **NOT in scope for B1:** the full B4 credentialed live-parity run (the exact row-count + value parity on the `v_actionable_packages`-family views under Q1 default — that is the attended B4 event, AD-19). B1 builds the machinery + seeds the conda-side fixtures; B2 adds PyPI/vuln fixtures; B3 completes the harness; B4 runs it credentialed with human sign-off.

### AD-10 contract-preservation list (the 11 phases' binding contracts)

Full detail: `cf-atlas-legacy` skill `references/engineering-contracts.md` (the shipped *how* behind each phase, all citations at `b18cbb5`). The B1-relevant subset:

- **Phase K scheduler** — `_RateLimitedScheduler` single-worker 3.0-RPS default (~3× safety margin, CFA:1333); host-agnostic (GitHub/GitLab/Codeberg); `PHASE_K_AGGRESSIVE=1` → `ThreadPoolExecutor(max_workers=8)`, non-"1" values do NOT re-arm burst (CFA:5114–5115); 403 → `upstream_versions.last_error`, re-pick via TTL bypass; `_parse_retry_after` (CFA:2668) — note it is **in CFA, not `_http.py`**.
- **Phase F provenance discipline** — `downloads_source` ∈ {`anaconda-api`,`s3-parquet`,`merged`} correlated-but-distinct (CFA:188); breakdown tables (`package_platform_downloads`/`package_python_downloads`/`package_channel_downloads`) written **only on the s3-parquet path** (CFA:538/549/572); DELETE-by-scope-key+INSERT one transaction, chunked ≤500 (CFA:3423–3450) → **replace-by-scope-key** in Parquet; `downloads_30d` = latest calendar month not rolling (CFA:3162); one consolidated pyarrow sweep; `pkg_python` regex-filtered before aggregation.
- **Phase B.5 attribution** — `_pick_feedstock` (CFA:1572): empty→`None`; `len>1 and pkg_name in feedstocks`→`pkg_name`; else `feedstocks[0]` (CFA:1586–1590).
- **View/scope discipline** — every raw `packages` read passes the `v_actionable_packages` scope meta-test (the canonical persona-filter triplet at CFA:379–381) or carries a `# scope:` justification. Post-**v25** schema shape only: never resurrect dropped tables (`package_hardening`, `vuln_total_active`, …).
- **Archived-feedstock filter (J + M)** — build the `inactive_feedstocks` skip-set at the write site (v7.9.0 fix; spec § 3.3).
- **Cross-phase invariants** — timestamps normalized to **epoch seconds** at the dataset boundary (repodata per-build timestamps are ms — convert once); join keys fixed (conda-side datasets key on `conda_name`, +`feedstock_name` where B.5 attribution applies).
- **Two code-vs-spec divergences to follow the CODE on** (engineering-contracts.md § Code-vs-spec): **D1** — Phase P's `_PARTITIONDATE` is a spec-prose error (out of B1 scope, but the discipline applies: follow the code, not spec prose, on any divergence); **D2** — "AD-10" is the spine's label for the spec:250–286 contract list, not a spec term.

### Deferred-Item Dispositions (the 3 B1-bound ledger entries + the Phase-E delta)

From `implementation-artifacts/deferred-work.md` — B1 makes these calls:

1. **DW-A3-P10 — epoch-ms magnitude guard (SPECULATIVE at A3; B1 owns the `fetched_at` unit).** Disposition: B1 nodes stamp `fetched_at` in **epoch seconds**; normalize any ms-sourced timestamp to seconds **at the dataset boundary** (Phase F/I are the first real ms-source writers — repodata per-build timestamps are ms). **Recommended:** add the cheap order-of-magnitude assertion to `IncrementalParquetDataset.save`/`stale_mask` now — it is no longer dead code once Phase F/I write these datasets. Record the decision in the Dev Agent Record.
2. **DW-A3-P11 — `kedro_datasets` private-internal pin.** Disposition: B1 (first story to exercise the flipped datasets through nodes) re-verifies `self._inner._describe()`/`._exists()` against the in-env `kedro_datasets` (was 9.5.0); add a compat check or switch to a public accessor if a version bump landed. Non-blocking if 9.5.0 holds.
3. **DW-A3-TTL-parity — fresh-at-exactly-ttl.** Disposition: B1 confirms the boundary against legacy `_TTL_GATED` (`age >= ttl` = stale at exactly ttl) vs the new `stale_mask` (`fetched_at < now - ttl` = fresh at exactly `now-ttl`, `incremental_parquet.py:269`). Make the parity call deliberately; flip `<`→`<=` **iff** parity evidence requires, and update `test_stale_mask_gates_old_stale_recent_fresh`.
4. **Phase E maintainer-universe delta (AC-5) → DOCUMENTED (not fully reconciled).** Record the delta with provenance in the `enrich_maintainers` node docstring + parity notes: atlas `package_maintainers` = **769** (537 sole + 232 co, build 2026-06-19) vs cf-graph `node_attrs` discovery = **813** (558 + 255, `conda-forge-tracker.md`), Δ≈44 (spec:287–292). Full reconciliation is a data-quality investigation beyond one story — **defer to B4** (the AC explicitly allows "reconciles — or explicitly documents"; B1/B4 both named as owners in § 3.3).

### Keystone budget note (loop-run concern for the workstation)

This is a **KEYSTONE** story (largest yet — 12 nodes / 11 phases) run **LOOP-S** (`sprint-status.yaml` story_meta). Per **AD-18**, keystone stories (B1/B2/F1) get **pre-flight budget raises** — this DEV-AUTO-in-container drafting run does NOT set them; **the loop-run operator must raise the pre-flight budget on the workstation before driving B1** (and consider raising `dev_stall_grace_s` for the long node suite). REVIEW sessions are constrained to correctness-affecting findings only (AD-18 — the verified over-engineering failure mode of long unattended runs). Recommended split guidance is below.

### What "done" hands to B2 / B3 / B4

- **B2** (PyPI + Vulnerability port; `depends_on: [b1]`): consumes the `core` pipeline datasets (`core_packages_enumerated`, `core_feedstock_attribution`, etc.) by catalog name (AD-3); extends the `parity-diff` harness B1 skeleton with PyPI/vuln fixtures; **owns the Phase H port** (VCS&Health's velocity FR-20 consumes it — producer=PyPI Intelligence).
- **B3** (MCP re-exposure; `depends_on: [b1,b2]`): reads the `core`/`vcs_health` datasets through Kedro-API-native MCP tools (passthrough only, AD-7); `parity-diff` **build completes at B3**.
- **B4** (ATTENDED parity boundary; `depends_on: [b1,b2,b3]`): **consumes** the `parity-diff` harness B1 began; runs the credentialed live-parity comparison (Q1 default: exact row-count + value parity on `v_actionable_packages`-family views); human sign-off gates legacy-orchestrator retirement (AD-19). B4 also finalizes the Phase-E delta reconciliation B1 documented.

### Gaps found during drafting (resolve during implementation)

- **G-1 — Pipeline package stubs do NOT exist.** The task framing said "the seven pipeline package stubs from A1," but on disk `src/pyforge/atlas/pipelines/` contains only an empty `__init__.py`. B1 **creates** the `core/` and `vcs_health/` packages from scratch (Task 0). `find_pipelines()` in `pipeline_registry.py` auto-discovers them; `register_pipelines()` needs no edit.
- **G-2 — `vcs_github_api_raw` FLIP is mis-attributed to B2.** `catalog.yml:408–410` says the GitHub request-parameterized factory dataset "lands with the vcs port (B2)" — but **B2 is the PyPI & Vulnerability port; the vcs_health phases (E.5/K/N) are B1.** The GitHub request dataset + its rate-limit discipline must be authored **in this story** (Task 2). (Two other FLIP labels — `pypi_bigquery_downloads_raw` says B3 though Phase P is a B2 pypi phase — are B2/B3's to reconcile, not B1's.)
- **G-3 — `kedro-test` env not yet materializable under `--frozen`** (DW-A1 blocker): `pixi.lock` has zero `pyforge-atlas` entries until the workstation re-lock lands; the interim gate is the **fat-env** `PYTHONPATH=…/pyforge-atlas/src:…/pyforge-warden/src pixi run --frozen -e local-recipes python -m pytest …` pattern (A1/A2/A3). Do NOT weaken the gate (NFR-12).

### Recommended split (assumption for the implementing session — but keep ONE story file)

If the keystone proves too large for one clean LOOP-S story, the implementing session MAY split the **loop execution** into two sub-efforts along the pipeline boundary — **(a) Core phases** (B, B.5, B.6, F, I, J, M → 7 nodes) then **(b) VCS & Health phases** (E, E.5, K, L, N → 5 nodes) — landing them as sequential commits. This is a natural seam: Core produces `core_cf_graph_raw` and the enumeration/attribution datasets that VCS&Health's Phase E consumes cross-pipeline, so Core-first is the correct order. **This remains ONE story file** per the frozen spec ID B1 (epics.md D-2) — do not fork the story key. Record the split (if taken) in the Dev Agent Record.

### Project Structure Notes

- Scaffold root: `src/shared/packages/pyforge-atlas/` (pixi-build workspace member, `pyforge.atlas` namespace, hatchling; spine "Packaging & namespace" row). New code: `src/pyforge/atlas/pipelines/{core,vcs_health}/{__init__,nodes,pipeline}.py`; tests: `tests/pipelines/{core,vcs_health}/` + `tests/parity/`.
- Naming (spine Consistency row): pipelines = snake_case packages (`core`, `vcs_health`); nodes = `<verb>_<subject>` pure functions with a `# legacy: Phase <ID>` comment; datasets = `<domain>_<entity>` (already declared in A2's catalog — B1 does not rename, only flips types on the FLIP-marked entries).
- No conflict with unified structure; the seven-pipeline decomposition is spine-fixed (AD-3). The only catalog edits are the two FLIP-marked entries (`core_anaconda_downloads_raw`, `vcs_github_api_raw`) — additive, do not rename existing datasets (spine "Dataset schema evolution": additive-first).

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story B1 (3.1)] — the 11 phases, 6 AC clauses, FR-2, invariants, LOOP-S + keystone.
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#9 Story B1] — binding ACs; #3.3 Live-Surface Snapshot (the authoritative phase registry + per-phase engineering contracts, spec:250–286); #5.2 modular pipelines; #5.3 checkpointing/idempotency; FR-2 (spec:590).
- [Source: ARCHITECTURE-SPINE.md#AD-3] producer-owns-dataset / 7 snake_case pipelines; #AD-10 legacy-contract list; #AD-4 Parquet canonical; #AD-5 no node-local checkpointing; #AD-13 offline degradation; Consistency Conventions (naming, join keys, timestamps=epoch seconds); Structural Seed (core/vcs_health phase→pipeline mermaid).
- [Source: .claude/skills/cf-atlas-legacy/8.78.0/cf-atlas-legacy/provenance-map.json] — every phase function's `file:line` (`conda_forge_atlas.py` @ b18cbb5).
- [Source: .claude/skills/cf-atlas-legacy/8.78.0/cf-atlas-legacy/references/engineering-contracts.md] — the binding per-phase contract detail + code anchors + D1/D2 divergences.
- [Source: src/shared/packages/pyforge-atlas/conf/base/catalog.yml] — every Core/VCS dataset name + the `FLIP(B1)`/FLIP markers (A2).
- [Source: src/shared/packages/pyforge-atlas/conf/base/parameters.yml] — the `ttls:` the flipped datasets consume.
- [Source: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/incremental_parquet.py] — the `fetched_at`/`stale_mask` contract B1 nodes satisfy (AD-5).
- [Source: _bmad-output/projects/pyforge-atlas/implementation-artifacts/deferred-work.md] — the 3 B1-bound A3 items + the A2-P4 (B5, not B1) item.
- [Source: _bmad-output/projects/pyforge-atlas/implementation-artifacts/{a1,a2,a3}-*.md] — Wave-A Dev Agent Records (scaffold, catalog, IncrementalParquetDataset), all merged green at HEAD 14eac15.

## Dev Agent Record

### Context Reference

- Rule 1 (CLAUDE.md): the `conda-forge-expert` skill + the `cf-atlas-legacy` provenance skill are the authoritative references for the legacy behavioral contracts; a BMAD story instruction never overrides an AD-10 contract (AD-10, CLAUDE.md Rule 1 authority).
- Rule 2 (CLAUDE.md): this effort ends with a CFE Rule-2 retro at Wave-B/effort closeout (attended, non-deferrable, AD-18) — not this story.

### Agent Model Used

claude-fable-5 (DEV-AUTO, `bmad-dev-auto` unattended loop). Baseline `14eac15`.
Fat-env interim gate: `PYTHONPATH=…/pyforge-atlas/src:…/pyforge-warden/src pixi run --frozen -e local-recipes python -m pytest …`.

### Debug Log References

- Legacy TTL semantics VERIFIED against code (not prose) — `conda_forge_atlas.py:2803` (Phase F) + `:5167` (Phase K): `COALESCE(fetched_at,0) < cutoff`, `cutoff = now - ttl` (strict `<`). See Review Triage Log.
- DAG proof: `kedro registry list` → `__default__` / `core` / `vcs_health`; `find_pipelines()` auto-discovers with no `register_pipelines()` edit.

### Completion Notes List

**Nodes complete: 12 of 12** — Core (7): enumerate_conda_packages (B), attribute_feedstocks (B.5), detect_latest_status (B.6-lite), compute_downloads (F), compute_version_download_history (I), build_dependency_graph (J), compute_feedstock_health (M). VCS&Health (5): enrich_maintainers (E), detect_archived_feedstocks (E.5), track_upstream_versions (K), track_registry_versions (L), fetch_live_health (N). Each carries a `# legacy: Phase <ID>` comment.

**Pure-node/dataset-IO boundary as built (THE CRUX):** node bodies are pure `DataFrame -> DataFrame`, zero denylist imports (`test_no_inline_io` green across the new modules). Rate-limit + fetch discipline lives in `datasets/rate_limit.py` (`RateLimitedScheduler` 3-RPS single-worker token bucket, `FetcherClient` Protocol, `StubFetcherClient`, `parse_retry_after`, `resolve_worker_count`) + `datasets/request_datasets.py` (`AnacondaDownloadsDataset` / `GitHubRequestDataset` own the per-{package,query} parameterization + carry the scheduler). The Phase K contract is fixture-tested against the STUB (never a live endpoint, AD-11).

**Catalog FLIPs:** `core_anaconda_downloads_raw` flipped `api.APIDataset` → `AnacondaDownloadsDataset` (B1 landed it; `# FLIP(B1)` marker removed + dropped from `conftest.EXPECTED_FLIP_MARKERS`). `vcs_github_api_raw` flipped → `GitHubRequestDataset` with the **G-2 attribution corrected** (E.5/K/N are B1, not B2). Both kept `url`/`method`/`credentials` so the tightly-pinned `kedro-catalog-check` (38) stays green.

**Judgment calls (recorded):**
- J1: cross-pipeline `core_cf_graph_raw` is a shared RAW SOURCE (regro/cf-graph tarball), consumed by J/M (core) + E (vcs_health) — NOT a core-node output. No producer conflict, no inter-pipeline data edge; the story's "Core produces core_cf_graph_raw" is a naming/ownership statement (single declaration, AD-3). Core-first sequencing is therefore not load-bearing; still implemented Core first.
- J2: the concrete per-{package,query} request FAN-OUT is dataset-owned + deferred (the node consumes already-fetched frames — story CRUX); B1 seeds the parameterization surface + rate-limit ownership.

**Deferred-item dispositions (actioned):**
- DW-A3-P10 (epoch-ms guard): ADDED to `IncrementalParquetDataset` (`_has_ms_magnitude`/`_to_epoch_seconds`; save + stale_mask normalize ms→s at the boundary — Phase F/I are the first real ms-writers, no longer dead code).
- DW-A3-P11 (kedro_datasets private-internal pin): re-verified `_inner._describe()`/`_exists()` work on kedro_datasets 9.5.0 (they do); added public-first `_inner_describe()`/`_inner_exists()` accessors as future-proofing. Non-blocking.
- DW-A3-TTL-parity: DELIBERATE call — **verified against the legacy CODE** (`CFA:2803/5167` strict `<`) that the disposition's `age >= ttl` PROSE was wrong; KEPT the original strict `<` (fresh at exactly `now-ttl`). The review's initial `<`→`<=` flip was reverted (see Triage Log).
- Phase E maintainer delta (AC-5): DOCUMENTED (769 vs 813, Δ≈44) in `enrich_maintainers` docstring + `tests/parity/PARITY_NOTES.md`; full reconcile → B4.

**Parity harness:** `tests/parity/` — `harness.py` (dispatch registry + fixture loader + order-independent frame-diff), 12 captured Core/VCS fixtures (representative legacy-shaped seeds encoding the per-phase contracts), `test_parity_{core,vcs_health}.py`, `PARITY_NOTES.md`. `parity-diff` pixi task registered (fixture-mode, offline, non-credentialed). B4 replaces the seeds with real operator snapshots + runs credentialed (AD-19).

**Residual risk (declared, for B4):** the composed request datasets currently delegate `load()` to `APIDataset` (returns a `requests.Response`); the Response→DataFrame bridge for the concrete fetch fan-out is deliberately DEFERRED to B4 (B1 nodes consume already-fetched frames). The parameterization METHODS (`request_path`/`with_query`) are now unit-tested. The parity gate is self-certifying in B1 (seeds hand-authored) — real legacy equivalence is the attended B4 event; a green `parity-diff` here is NOT evidence of legacy parity.

**Gates (all green):** full member tree 137 passed (A1/A2/A3's 74 kept green + 63 new) · kedro-catalog-check 38 · parity-diff 14 · `kedro registry list` (core + vcs_health) · llms-full-check clean (no dep changes) · bmad-drift-check 0 integrity (expected pixi_envs 11→12 currency finding only) · meta test_bmad_artifacts_in_sync pass.

### File List

New (src): `datasets/rate_limit.py`, `datasets/request_datasets.py`, `pipelines/core/{__init__,nodes,pipeline}.py`, `pipelines/vcs_health/{__init__,nodes,pipeline}.py`.
Modified (src): `datasets/__init__.py` (exports), `datasets/incremental_parquet.py` (DW-A3-P10 ms-guard + DW-A3-P11 accessors + DW-A3-TTL strict-`<` parity comment).
Modified (conf): `conf/base/catalog.yml` (2 FLIPs + G-2 comment fix).
New (tests): `tests/pipelines/{__init__,test_dag_resolves}.py`, `tests/pipelines/core/{__init__,test_nodes}.py`, `tests/pipelines/vcs_health/{__init__,test_nodes,test_rate_limit_contract}.py`, `tests/parity/{__init__,harness,test_parity_core,test_parity_vcs_health,PARITY_NOTES}.md/.py`, `tests/parity/fixtures/{core,vcs_health}/*.json` (12), `tests/datasets/test_request_datasets.py`.
Modified (tests): `tests/catalog/conftest.py` (EXPECTED_FLIP_MARKERS), `tests/datasets/test_incremental_parquet.py` (TTL boundary + ms-coercion regression).
Modified (root): `pixi.toml` (`parity-diff` task).

### Workstation remainder

None — all 12 nodes complete + all gates green in the fat-env interim. The workstation must: (1) run the same gates under the real `pyforge-atlas` env once the `pixi.lock` re-lock lands (DW-A1 blocker G-3) — `pixi run --frozen -e pyforge-atlas kedro-test` / `kedro-catalog-check` / `parity-diff`; (2) commit/push (this DEV-AUTO run does NOT commit, per orchestrator ownership); (3) per AD-18, raise the keystone pre-flight budget was N/A for this container run. Follow-up independent review recommended (see Triage Log).

## Review Triage Log

### 2026-07-17 — Review pass (Blind Hunter + Edge Case Hunter, both completed; findings deduped)
- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 1, medium 4, low 8)
- defer: 0
- reject: 4: (low 4)
- addressed_findings:
  - `[high]` `[patch]` **TTL boundary comparator** — verified the DW-A3-TTL-parity disposition's `age >= ttl` prose against the legacy CODE (`CFA:2803` Phase F, `:5167` Phase K: `COALESCE(fetched_at,0) < now-ttl`, strict `<`); the prose was wrong. Per engineering-contracts D1/D2 ("follow the code"), REVERTED the interim `<`→`<=` flip back to strict `<` (would otherwise have shipped an off-by-one across all 15 flipped datasets). Boundary test restored.
  - `[medium]` `[patch]` `IncrementalParquetDataset.save` — `needs_fill` computed pre-coercion; a non-numeric cell that `_to_epoch_seconds` coerces to NaN was persisted → perpetual re-fetch (P1). Re-check `isna()` AFTER coercion + fill. Regression test added.
  - `[medium]` `[patch]` `_pick_feedstock` — a NaN feedstocks cell (truthy) fell through to `len(nan)` → TypeError; normalize non-sequence→None, bare-string→single-element list. Test added.
  - `[medium]` `[patch]` `enrich_maintainers` — a NaN maintainers cell crashed `for m in nan`; iterate only real sequences. Test added.
  - `[medium]` `[patch]` string-boolean archived flags — `.fillna(False).astype(bool)` turns `"false"`→True (silent inversion of the J/M/E.5 archived filter); added `_as_bool_series` robust coercion. Tests added.
  - `[low]` `[patch]` `RateLimitedScheduler.acquire(n>capacity)` — infinite loop (tokens cap below n); guard raises ValueError. Test added.
  - `[low]` `[patch]` `enumerate_conda_packages` NaN-timestamp ordering — `na_position="first"` so a missing timestamp can't win `latest_version`; reused the ms-threshold constant.
  - `[low]` `[patch]` `parse_retry_after` naive HTTP-date — pin `tzinfo=UTC` so `.timestamp()` doesn't assume local time. Test added.
  - `[low]` `[patch]` `fetch_live_health` — projected onto the full `base_cols` for a stable output schema.
  - `[low]` `[patch]` missing-required-column guards across nodes (enumerate/attribute/compute_downloads/build_dependency_graph/compute_feedstock_health) — return a columned-empty frame instead of KeyError on mis-shaped input.
  - `[low]` `[patch]` `track_upstream_versions`/`track_registry_versions` — consistent missing-column defaults.
  - `[low]` `[patch]` parity `harness._normalize` — deterministic sort over a stringified key of ALL columns (list cells no longer leave ties input-order-dependent for B2-B4); `run_fixture` guards a missing expected-output key with a clear message.
  - `[low]` `[patch]` request-dataset parameterization surface (`request_path`/`with_query`) was untested — added `tests/datasets/test_request_datasets.py`.
- rejected (dropped, with rationale recorded in code comments where load-bearing):
  - merged `downloads_total` prefers granular s3 (not additive — the two sources are correlated measurements of the same downloads; summing would double-count, CFA:188). Clarifying comment added; behavior kept.
  - "parity fixtures are self-certifying in B1" — this is the intended scope (seeds now, real operator capture at B4 per AD-19); documented in PARITY_NOTES + residual risk, not a defect.
  - J/M archived skip-set sources from `core_cf_graph_raw` (v7.9.0 fix "build the skip-set before opening the cf-graph tarball") — faithful to legacy; wiring it from E.5's `vcs_archived_feedstocks` would DEVIATE from the contract.
  - `RateLimitedScheduler._refill` on a backwards clock — `_last` only advances when `elapsed>0`, safe for the monotonic-clock contract.

followup_review_recommended: true (a shipped-off-by-one TTL comparator across the whole flip surface + two crash fixes + a re-fetch-loop regression + broad hardening — breadth and data-impact warrant an independent pass).

### Independent follow-up review (2026-07-17, post-DEV-AUTO, owner-requested)
Fresh-eyes adversarial review (repro-first) of commit c90a44e across 5 axes.
Result: 1 CONFIRMED must-fix + 3 tracked mediums; everything else clean.
- MUST-FIX (fixed, commit 8878ba4): compute_downloads wrote downloads_source=
  'merged' per row vs legacy contract CFA:189-193 ({anaconda-api,s3-parquet}
  only); the parity fixture endorsed it (so B4's gate was calibrated to the
  bug). Node + docstring + test + fixture + PARITY_NOTES corrected; repro
  confirms s3-parquet, zero 'merged'.
- Tracked to ledger: DW-B1-1 (parity harness needs legacy-captured fixtures +
  column/dtype tightening before B4), DW-B1-2 (scheduler unwired to fetch
  path + fake-clock coupling), DW-B1-3 (enumerate tie-break, B.5 placeholders).
- Verified CLEAN: pure-node/dataset-IO crux (all 12 nodes pure, no hidden IO,
  no input mutation), AD-10 rate-limit parsing/worker-gate fidelity, and all
  five prior-review fixes (TTL strict <, save() re-fetch fix, 2 NaN crashes,
  string-'false' inversion).
Gates after fix: member tree 137 passed, kedro-catalog-check 38, parity 14,
drift 0 integrity. Story sound to close.

---

> Source: `specs/spec-b2-port-the-pypi-vulnerability-pipelines.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B2 (3.2): Port the PyPI & Vulnerability pipelines'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B2 (3.2): Port the PyPI & Vulnerability pipelines

As a BMAD execution agent,
I want the PyPI intelligence phases (C, C.5, D, H, O–S incl. the shared single-write-path helpers) and vulnerability phases (G / G') ported into their domain pipelines,
So that PyPI and vulnerability intelligence run as unit-testable DAG nodes with all shipped guards intact.

**Acceptance Criteria:** (spec § 9 Story B2, binding)

**Given** the § 5.2 pipeline decomposition
**When** the PyPI + vulnerability phases are ported
**Then** the PyPI Intelligence and Vulnerability pipelines exist per § 5.2 and each node unit-tests on `pandas.DataFrame` IO
**And** the `add-handoff` single-write-path property and the `v_pypi_intelligence_valid` / `v_current_version_vulns` view contracts are preserved
**And** the vulnerability read-path contract is preserved: the atlas `cisa_kev` KEV overlay and the `_coerce_cvss_score` ScoreType unwrap survive in the migrated read surface
**And** Phase P ports with its two-layer cost gate intact (dry-run preflight + `maximum_bytes_billed` + job timeout, `_PARTITIONDATE` literal bounds), stays opt-in/admin-only, and `test_no_thirty_gb_lie.py` carries over
**And** Phase H's serial gate ports without re-including the pypi-only denominator; EPSS percentiles stay normalized 0–100; `pypi_intelligence.notes` operator overrides survive Phase S re-runs.

- **FRs:** FR-2.
- **Invariants:** AD-3, AD-10, AD-6 (Phase P admin-opt-in, never a default schedule), AD-5, AD-13.
- **Mode:** LOOP-S. **Keystone story — pre-flight budget raise (AD-18).**
- **Gating question:** none.
- **Verify gate:** `kedro-test` + `parity-diff` (building).
- **Depends on:** B1 (Core pipeline datasets).

### Story B3 (3.3): Re-expose the data surface as Kedro-API-native MCP tools

As a CFE authoring agent,
I want the 23 atlas-relevant MCP tools re-authored over Kedro session/catalog APIs with pipeline triggers and dataset reads,
So that I can trigger named pipelines and read datasets via MCP with no load-bearing plugin dependency.

**Acceptance Criteria:** (spec § 9 Story B3, binding)

**Given** the 46 existing MCP tools (23 atlas-relevant) in `conda_forge_server.py`
**When** the audit + re-authoring completes
**Then** BMAD agents can trigger a named pipeline (e.g. `run_vulnerability_pipeline`) via MCP
**And** BMAD agents can read a resulting dataset natively via MCP
**And** `kedro-mcp` is not a load-bearing dependency of the trigger/read surface — the surface works with it absent
**And** non-atlas recipe-authoring tools stay on the legacy FastMCP server; `library-futures` / `add-handoff` stay CLI-only
**And** MCP tool bodies carry no metric/business logic (dataset passthrough + triggers only, AD-7); triggered runs ride the same Kedro job machinery (AD-23).

- **FRs:** FR-7.
- **Invariants:** AD-7, AD-23, AD-17 (payloads advisory + timestamped), AD-1.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` + `parity-diff` (build completes at B3).
- **Depends on:** B1, B2 (datasets to expose).

### Story B4 (3.4): Verify dataset parity against the legacy orchestrator

As the operator,
I want the Kedro pipeline run in parallel with legacy `bootstrap-data` and proven output-equivalent,
So that the legacy orchestrator (and `phase_state`) can be retired on recorded evidence, not hope.

**Acceptance Criteria:** (spec § 9 Story B4, binding)

**Given** the `parity-diff` harness built through B1–B3
**When** the full credentialed parity run executes as an attended wave-boundary event
**Then** the parity check compares Kedro Parquet outputs against legacy `cf_atlas.db` tables and reports zero material drift per Q1's default (exact row-count + value parity on the `v_actionable_packages`-family views; timestamp/ordering-only diffs documented benign)
**And** the harness itself is a fixture-based, loop-callable `parity-diff` pixi task
**And** parity evidence is recorded with human sign-off; only then is the legacy orchestrator marked for retirement
**And** B4 compares legacy-surface outputs only — B8/B9/B10 signals are out of parity scope (AD-14).

- **FRs:** FR-4 (the `phase_state` table retires with the legacy orchestrator), whole-migration AC-1.
- **Invariants:** AD-19 (retirement gate + abort ramp bounding sunk cost at Waves 0–B), AD-11 (attended event, credentialed run attended-only), AD-4.
- **Mode:** ATTENDED (parity boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q1** (parity tolerance) — § 11 default adopted: exact row-count + value parity on actionable views, benign-diff documentation. Comparison granularity beyond the Q1 views resolves in the B4 evidence record (Spine Deferred).
- **Verify gate:** **consumes `parity-diff`** (fixture mode in-loop; credentialed full run at the event).
- **Depends on:** B1, B2, B3.

### Story B5 (3.5): Port the external-refresh assets (§ 3.4)

As the operator,
I want `vdb-refresh`, `update-cve-db`, and `update-mapping-cache` wrapped as scheduled external-refresh assets in their domain pipelines,
So that the three separately-built stores refresh with retries and observability across all three bootstrap profiles.

**Acceptance Criteria:** (spec § 9 Story B5, binding)

**Given** the three § 3.4 separately-built local stores and the legacy tasks' TTLs
**When** the refresh assets are ported
**Then** each refresh runs as a Dagster-scheduled asset with retries + observability, cadence matching the legacy TTLs
**And** Phases G / G' and `scan-project` offline mode consume the refreshed stores exactly as before — the pipeline never writes them outside the refresh assets
**And** the vuln-db environment dependency is a declared resource requirement, not an implicit shell-out
**And** Q6's decision is recorded **before** porting `update-mapping-cache` (consolidation may retire it instead); `g10_spelling` provenance + no-clobber survive regardless
**And** the consumer profile keeps working air-gapped.

- **FRs:** FR-2, FR-6.
- **Invariants:** AD-6, AD-13, AD-10 (mapping contract), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q6** (mapping-source consolidation) — § 11 default adopted: consolidate on migrated Phase C (DuckDB), re-point `name_resolver.py`/`recipe-generator.py`; keep the flat-cache refresh only if authoring-time reads prove to need a standalone file. Must be recorded before this story's mapping asset work.
- **Verify gate:** `kedro-test` (+ `dagster-dryrun` once C1 exists; schedule assertions land as fixtures here).
- **Depends on:** B4 sequence position per § 14 (runs after parity; needs B1/B2 pipelines; Q6 drained first).

### Story B6 (3.6): Port the Seed-Gaps pipeline

As the operator,
I want the four report-only gap suggesters as terminal report nodes of the Seed-Gaps pipeline,
So that seed-freshness reports regenerate after every rebuild without ever mutating the curated seeds.

**Acceptance Criteria:** (spec § 9 Story B6, binding)

**Given** the external seed datasets and the § 3.4 Seed-freshness report nodes table
**When** `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` are ported
**Then** each suggester is a report node reading exactly the inputs in that table, emitting a `derived`-layer freshness report
**And** the nodes are strictly read-only — the byte-identical-seed guarantee survives as a pipeline test
**And** the pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts
**And** `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback — it is not a Seed-Gaps node.

- **FRs:** FR-2.
- **Invariants:** AD-15, AD-3, AD-10.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (byte-identical-seed fixture + report-node fixtures).
- **Depends on:** B1, B2 (upstream datasets); § 14 position after B5.

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B3 (3.3): Re-expose the data surface as Kedro-API-native MCP tools'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B3 (3.3): Re-expose the data surface as Kedro-API-native MCP tools

As a CFE authoring agent,
I want the 23 atlas-relevant MCP tools re-authored over Kedro session/catalog APIs with pipeline triggers and dataset reads,
So that I can trigger named pipelines and read datasets via MCP with no load-bearing plugin dependency.

**Acceptance Criteria:** (spec § 9 Story B3, binding)

**Given** the 46 existing MCP tools (23 atlas-relevant) in `conda_forge_server.py`
**When** the audit + re-authoring completes
**Then** BMAD agents can trigger a named pipeline (e.g. `run_vulnerability_pipeline`) via MCP
**And** BMAD agents can read a resulting dataset natively via MCP
**And** `kedro-mcp` is not a load-bearing dependency of the trigger/read surface — the surface works with it absent
**And** non-atlas recipe-authoring tools stay on the legacy FastMCP server; `library-futures` / `add-handoff` stay CLI-only
**And** MCP tool bodies carry no metric/business logic (dataset passthrough + triggers only, AD-7); triggered runs ride the same Kedro job machinery (AD-23).

- **FRs:** FR-7.
- **Invariants:** AD-7, AD-23, AD-17 (payloads advisory + timestamped), AD-1.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` + `parity-diff` (build completes at B3).
- **Depends on:** B1, B2 (datasets to expose).

### Story B4 (3.4): Verify dataset parity against the legacy orchestrator

As the operator,
I want the Kedro pipeline run in parallel with legacy `bootstrap-data` and proven output-equivalent,
So that the legacy orchestrator (and `phase_state`) can be retired on recorded evidence, not hope.

**Acceptance Criteria:** (spec § 9 Story B4, binding)

**Given** the `parity-diff` harness built through B1–B3
**When** the full credentialed parity run executes as an attended wave-boundary event
**Then** the parity check compares Kedro Parquet outputs against legacy `cf_atlas.db` tables and reports zero material drift per Q1's default (exact row-count + value parity on the `v_actionable_packages`-family views; timestamp/ordering-only diffs documented benign)
**And** the harness itself is a fixture-based, loop-callable `parity-diff` pixi task
**And** parity evidence is recorded with human sign-off; only then is the legacy orchestrator marked for retirement
**And** B4 compares legacy-surface outputs only — B8/B9/B10 signals are out of parity scope (AD-14).

- **FRs:** FR-4 (the `phase_state` table retires with the legacy orchestrator), whole-migration AC-1.
- **Invariants:** AD-19 (retirement gate + abort ramp bounding sunk cost at Waves 0–B), AD-11 (attended event, credentialed run attended-only), AD-4.
- **Mode:** ATTENDED (parity boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q1** (parity tolerance) — § 11 default adopted: exact row-count + value parity on actionable views, benign-diff documentation. Comparison granularity beyond the Q1 views resolves in the B4 evidence record (Spine Deferred).
- **Verify gate:** **consumes `parity-diff`** (fixture mode in-loop; credentialed full run at the event).
- **Depends on:** B1, B2, B3.

### Story B5 (3.5): Port the external-refresh assets (§ 3.4)

As the operator,
I want `vdb-refresh`, `update-cve-db`, and `update-mapping-cache` wrapped as scheduled external-refresh assets in their domain pipelines,
So that the three separately-built stores refresh with retries and observability across all three bootstrap profiles.

**Acceptance Criteria:** (spec § 9 Story B5, binding)

**Given** the three § 3.4 separately-built local stores and the legacy tasks' TTLs
**When** the refresh assets are ported
**Then** each refresh runs as a Dagster-scheduled asset with retries + observability, cadence matching the legacy TTLs
**And** Phases G / G' and `scan-project` offline mode consume the refreshed stores exactly as before — the pipeline never writes them outside the refresh assets
**And** the vuln-db environment dependency is a declared resource requirement, not an implicit shell-out
**And** Q6's decision is recorded **before** porting `update-mapping-cache` (consolidation may retire it instead); `g10_spelling` provenance + no-clobber survive regardless
**And** the consumer profile keeps working air-gapped.

- **FRs:** FR-2, FR-6.
- **Invariants:** AD-6, AD-13, AD-10 (mapping contract), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q6** (mapping-source consolidation) — § 11 default adopted: consolidate on migrated Phase C (DuckDB), re-point `name_resolver.py`/`recipe-generator.py`; keep the flat-cache refresh only if authoring-time reads prove to need a standalone file. Must be recorded before this story's mapping asset work.
- **Verify gate:** `kedro-test` (+ `dagster-dryrun` once C1 exists; schedule assertions land as fixtures here).
- **Depends on:** B4 sequence position per § 14 (runs after parity; needs B1/B2 pipelines; Q6 drained first).

### Story B6 (3.6): Port the Seed-Gaps pipeline

As the operator,
I want the four report-only gap suggesters as terminal report nodes of the Seed-Gaps pipeline,
So that seed-freshness reports regenerate after every rebuild without ever mutating the curated seeds.

**Acceptance Criteria:** (spec § 9 Story B6, binding)

**Given** the external seed datasets and the § 3.4 Seed-freshness report nodes table
**When** `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` are ported
**Then** each suggester is a report node reading exactly the inputs in that table, emitting a `derived`-layer freshness report
**And** the nodes are strictly read-only — the byte-identical-seed guarantee survives as a pipeline test
**And** the pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts
**And** `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback — it is not a Seed-Gaps node.

- **FRs:** FR-2.
- **Invariants:** AD-15, AD-3, AD-10.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (byte-identical-seed fixture + report-node fixtures).
- **Depends on:** B1, B2 (upstream datasets); § 14 position after B5.

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b4-verify-dataset-parity-against-the-legacy-orchestrator.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B4 (3.4): Verify dataset parity against the legacy orchestrator'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B4 (3.4): Verify dataset parity against the legacy orchestrator

As the operator,
I want the Kedro pipeline run in parallel with legacy `bootstrap-data` and proven output-equivalent,
So that the legacy orchestrator (and `phase_state`) can be retired on recorded evidence, not hope.

**Acceptance Criteria:** (spec § 9 Story B4, binding)

**Given** the `parity-diff` harness built through B1–B3
**When** the full credentialed parity run executes as an attended wave-boundary event
**Then** the parity check compares Kedro Parquet outputs against legacy `cf_atlas.db` tables and reports zero material drift per Q1's default (exact row-count + value parity on the `v_actionable_packages`-family views; timestamp/ordering-only diffs documented benign)
**And** the harness itself is a fixture-based, loop-callable `parity-diff` pixi task
**And** parity evidence is recorded with human sign-off; only then is the legacy orchestrator marked for retirement
**And** B4 compares legacy-surface outputs only — B8/B9/B10 signals are out of parity scope (AD-14).

- **FRs:** FR-4 (the `phase_state` table retires with the legacy orchestrator), whole-migration AC-1.
- **Invariants:** AD-19 (retirement gate + abort ramp bounding sunk cost at Waves 0–B), AD-11 (attended event, credentialed run attended-only), AD-4.
- **Mode:** ATTENDED (parity boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q1** (parity tolerance) — § 11 default adopted: exact row-count + value parity on actionable views, benign-diff documentation. Comparison granularity beyond the Q1 views resolves in the B4 evidence record (Spine Deferred).
- **Verify gate:** **consumes `parity-diff`** (fixture mode in-loop; credentialed full run at the event).
- **Depends on:** B1, B2, B3.

### Story B5 (3.5): Port the external-refresh assets (§ 3.4)

As the operator,
I want `vdb-refresh`, `update-cve-db`, and `update-mapping-cache` wrapped as scheduled external-refresh assets in their domain pipelines,
So that the three separately-built stores refresh with retries and observability across all three bootstrap profiles.

**Acceptance Criteria:** (spec § 9 Story B5, binding)

**Given** the three § 3.4 separately-built local stores and the legacy tasks' TTLs
**When** the refresh assets are ported
**Then** each refresh runs as a Dagster-scheduled asset with retries + observability, cadence matching the legacy TTLs
**And** Phases G / G' and `scan-project` offline mode consume the refreshed stores exactly as before — the pipeline never writes them outside the refresh assets
**And** the vuln-db environment dependency is a declared resource requirement, not an implicit shell-out
**And** Q6's decision is recorded **before** porting `update-mapping-cache` (consolidation may retire it instead); `g10_spelling` provenance + no-clobber survive regardless
**And** the consumer profile keeps working air-gapped.

- **FRs:** FR-2, FR-6.
- **Invariants:** AD-6, AD-13, AD-10 (mapping contract), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q6** (mapping-source consolidation) — § 11 default adopted: consolidate on migrated Phase C (DuckDB), re-point `name_resolver.py`/`recipe-generator.py`; keep the flat-cache refresh only if authoring-time reads prove to need a standalone file. Must be recorded before this story's mapping asset work.
- **Verify gate:** `kedro-test` (+ `dagster-dryrun` once C1 exists; schedule assertions land as fixtures here).
- **Depends on:** B4 sequence position per § 14 (runs after parity; needs B1/B2 pipelines; Q6 drained first).

### Story B6 (3.6): Port the Seed-Gaps pipeline

As the operator,
I want the four report-only gap suggesters as terminal report nodes of the Seed-Gaps pipeline,
So that seed-freshness reports regenerate after every rebuild without ever mutating the curated seeds.

**Acceptance Criteria:** (spec § 9 Story B6, binding)

**Given** the external seed datasets and the § 3.4 Seed-freshness report nodes table
**When** `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` are ported
**Then** each suggester is a report node reading exactly the inputs in that table, emitting a `derived`-layer freshness report
**And** the nodes are strictly read-only — the byte-identical-seed guarantee survives as a pipeline test
**And** the pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts
**And** `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback — it is not a Seed-Gaps node.

- **FRs:** FR-2.
- **Invariants:** AD-15, AD-3, AD-10.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (byte-identical-seed fixture + report-node fixtures).
- **Depends on:** B1, B2 (upstream datasets); § 14 position after B5.

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b5-port-the-external-refresh-assets-3-4.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B5 (3.5): Port the external-refresh assets (§ 3.4)'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B5 (3.5): Port the external-refresh assets (§ 3.4)

As the operator,
I want `vdb-refresh`, `update-cve-db`, and `update-mapping-cache` wrapped as scheduled external-refresh assets in their domain pipelines,
So that the three separately-built stores refresh with retries and observability across all three bootstrap profiles.

**Acceptance Criteria:** (spec § 9 Story B5, binding)

**Given** the three § 3.4 separately-built local stores and the legacy tasks' TTLs
**When** the refresh assets are ported
**Then** each refresh runs as a Dagster-scheduled asset with retries + observability, cadence matching the legacy TTLs
**And** Phases G / G' and `scan-project` offline mode consume the refreshed stores exactly as before — the pipeline never writes them outside the refresh assets
**And** the vuln-db environment dependency is a declared resource requirement, not an implicit shell-out
**And** Q6's decision is recorded **before** porting `update-mapping-cache` (consolidation may retire it instead); `g10_spelling` provenance + no-clobber survive regardless
**And** the consumer profile keeps working air-gapped.

- **FRs:** FR-2, FR-6.
- **Invariants:** AD-6, AD-13, AD-10 (mapping contract), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q6** (mapping-source consolidation) — § 11 default adopted: consolidate on migrated Phase C (DuckDB), re-point `name_resolver.py`/`recipe-generator.py`; keep the flat-cache refresh only if authoring-time reads prove to need a standalone file. Must be recorded before this story's mapping asset work.
- **Verify gate:** `kedro-test` (+ `dagster-dryrun` once C1 exists; schedule assertions land as fixtures here).
- **Depends on:** B4 sequence position per § 14 (runs after parity; needs B1/B2 pipelines; Q6 drained first).

### Story B6 (3.6): Port the Seed-Gaps pipeline

As the operator,
I want the four report-only gap suggesters as terminal report nodes of the Seed-Gaps pipeline,
So that seed-freshness reports regenerate after every rebuild without ever mutating the curated seeds.

**Acceptance Criteria:** (spec § 9 Story B6, binding)

**Given** the external seed datasets and the § 3.4 Seed-freshness report nodes table
**When** `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` are ported
**Then** each suggester is a report node reading exactly the inputs in that table, emitting a `derived`-layer freshness report
**And** the nodes are strictly read-only — the byte-identical-seed guarantee survives as a pipeline test
**And** the pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts
**And** `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback — it is not a Seed-Gaps node.

- **FRs:** FR-2.
- **Invariants:** AD-15, AD-3, AD-10.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (byte-identical-seed fixture + report-node fixtures).
- **Depends on:** B1, B2 (upstream datasets); § 14 position after B5.

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b6-port-the-seed-gaps-pipeline.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B6 (3.6): Port the Seed-Gaps pipeline'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B6 (3.6): Port the Seed-Gaps pipeline

As the operator,
I want the four report-only gap suggesters as terminal report nodes of the Seed-Gaps pipeline,
So that seed-freshness reports regenerate after every rebuild without ever mutating the curated seeds.

**Acceptance Criteria:** (spec § 9 Story B6, binding)

**Given** the external seed datasets and the § 3.4 Seed-freshness report nodes table
**When** `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` are ported
**Then** each suggester is a report node reading exactly the inputs in that table, emitting a `derived`-layer freshness report
**And** the nodes are strictly read-only — the byte-identical-seed guarantee survives as a pipeline test
**And** the pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts
**And** `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback — it is not a Seed-Gaps node.

- **FRs:** FR-2.
- **Invariants:** AD-15, AD-3, AD-10.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (byte-identical-seed fixture + report-node fixtures).
- **Depends on:** B1, B2 (upstream datasets); § 14 position after B5.

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b7-extend-the-universal-sbom-intake-resolver-formats-universe-bom-buckets.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b8-basilisk-conda-native-vulnerability-ingestion.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B8 (3.8): Basilisk conda-native vulnerability ingestion'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b9-release-to-availability-velocity-columns.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B9 (3.9): Release-to-availability velocity columns'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-b10-migration-readiness-datasets-classification-node.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story B10 (3.10): Migration-readiness datasets + classification node'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-c1-integrate-kedro-dagster-for-scheduling-execution.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution

As the operator,
I want the Kedro DAG compiled into a Dagster repository with schedules, retries, profiles, and per-node timeouts,
So that I watch runs in the Dagster UI and the 1800 s silent-phase-drop defect is structurally retired.

**Acceptance Criteria:** (spec § 9 Story C1, binding)

**Given** the migrated Kedro DAG
**When** `kedro-dagster` compiles it
**Then** schedules exist as Dagster Schedules encoding the `guides/atlas-operations.md` cadence table (bootstrap weekly; F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6 h; N hourly per maintainer; refresh assets weekly)
**And** the three bootstrap profiles (maintainer / admin / consumer) exist as named Dagster job configurations with the guide's override precedence (explicit run-config/env beats profile defaults)
**And** retries + phase state are observable in the Dagster UI
**And** timeouts are per-node: a cold-run Phase R overrun can no longer abort Phase F/K/N — the legacy 1800 s `cf_atlas_core` defect is demonstrably retired
**And** a `dagster-dryrun` verify task exists (definitions load, schedules enumerate — no live execution); the schedule bring-up itself is an attended event (Q2)
**And** Phase P stays `PHASE_P_ENABLED=1`, admin-config-only, never a default schedule.

- **FRs:** FR-6.
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

### Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task

As the operator,
I want the topological DAG rendered by `kedro-viz` behind a dedicated pixi task,
So that I inspect dataset schemas and lineage in the browser instead of reading orchestrator source.

**Acceptance Criteria:** (spec § 9 Story C2, binding)

**Given** the compiled DAG
**When** `pixi run viz` executes
**Then** it launches the Kedro-Viz server
**And** operators can inspect dataset schemas + data lineage in the browser.

- **FRs:** FR-6 (structural observability), whole-migration AC-3.
- **Invariants:** AD-1, AD-6.
- **Mode:** LOOP-E.
- **Gating question:** none (Q2 drained at C1).
- **Verify gate:** `dagster-dryrun` + `kedro-test` (existing gates; viz task smoke lands in the pixi task inventory).
- **Depends on:** C1.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-c2-integrate-kedro-viz-expose-a-pixi-task.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task

As the operator,
I want the topological DAG rendered by `kedro-viz` behind a dedicated pixi task,
So that I inspect dataset schemas and lineage in the browser instead of reading orchestrator source.

**Acceptance Criteria:** (spec § 9 Story C2, binding)

**Given** the compiled DAG
**When** `pixi run viz` executes
**Then** it launches the Kedro-Viz server
**And** operators can inspect dataset schemas + data lineage in the browser.

- **FRs:** FR-6 (structural observability), whole-migration AC-3.
- **Invariants:** AD-1, AD-6.
- **Mode:** LOOP-E.
- **Gating question:** none (Q2 drained at C1).
- **Verify gate:** `dagster-dryrun` + `kedro-test` (existing gates; viz task smoke lands in the pixi task inventory).
- **Depends on:** C1.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-d1-define-the-boring-semantic-layer-bsl-models.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story D1 (5.1): Define the Boring Semantic Layer (BSL) models'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story D1 (5.1): Define the Boring Semantic Layer (BSL) models

As a downstream consumer (page, MCP read, agent),
I want the 28 read CLIs' metric logic declared once as BSL dimensions + measures over the catalog (Ibis → DuckDB),
So that every read surface translates through one semantic interface with proven metric parity.

**Acceptance Criteria:** (spec § 9 Story D1, binding)

**Given** the metric/business logic embedded in the 28 read CLIs
**When** the BSL models are declared
**Then** BSL declares the core metrics (staleness, adoption stage, feedstock health, …)
**And** maintainer-role facts (`package_maintainers ⋈ maintainers`) are first-class BSL dimensions — the raw-SQL JOINs live consumers write today become declared queries
**And** the BSL layer is the single translation interface for downstream consumers
**And** a `bsl-metric-check` verify task exists: metric-parity fixtures proving BSL answers match the legacy CLI outputs for the core metrics (the AD-7 metric-semantics handover anchor).

- **FRs:** FR-8.
- **Invariants:** AD-8, AD-4 (Ibis → DuckDB only).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `bsl-metric-check`**.
- **Depends on:** Epic 4 (stable orchestrated datasets); B4 (canonical Parquet store).

### Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages

As the operator,
I want a BSL-driven Vizro app reproducing the 28 read CLIs as pages, including a factory-status page,
So that every read-only question is answerable from a page meeting the agent-legibility bar.

**Acceptance Criteria:** (spec § 9 Story D2, binding)

**Given** the D1 BSL models and the CIS two-spine design specs
**When** the Vizro app is built
**Then** a Vizro dashboard serves the core KPIs currently locked in CLIs
**And** a "factory status" page reads the BMAD artifact state (sprint-status.yaml, epics frontmatter, `bmad-drift-check --specs` JSON) — agent-readable per § 13.2
**And** each read-only legacy CLI question is answerable from a Vizro page, where for the three FR-9 exceptions (`add-handoff`, `inventory-match`, `library-futures`) "answerable" means the latest-report artifact is surfaced read-only — the bar covers all 28
**And** the live-confirmed consumer set ports first: `behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`
**And** pages meet the § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts; NFR-8) and public-facing breadth stays at the factory-status page (SM-C4).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-17 (authoring-feeding pages carry build timestamps).
- **Mode:** DEV-AUTO (visual judgment, § 9 preamble).
- **Gating question:** none.
- **Verify gate:** `bsl-metric-check` (+ `kedro-test`); D2 page inventory detail resolves in the CIS specs (Spine Deferred).
- **Depends on:** D1.

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-d2-build-the-vizro-dashboard-port-the-28-clis-to-pages.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages

As the operator,
I want a BSL-driven Vizro app reproducing the 28 read CLIs as pages, including a factory-status page,
So that every read-only question is answerable from a page meeting the agent-legibility bar.

**Acceptance Criteria:** (spec § 9 Story D2, binding)

**Given** the D1 BSL models and the CIS two-spine design specs
**When** the Vizro app is built
**Then** a Vizro dashboard serves the core KPIs currently locked in CLIs
**And** a "factory status" page reads the BMAD artifact state (sprint-status.yaml, epics frontmatter, `bmad-drift-check --specs` JSON) — agent-readable per § 13.2
**And** each read-only legacy CLI question is answerable from a Vizro page, where for the three FR-9 exceptions (`add-handoff`, `inventory-match`, `library-futures`) "answerable" means the latest-report artifact is surfaced read-only — the bar covers all 28
**And** the live-confirmed consumer set ports first: `behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`
**And** pages meet the § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts; NFR-8) and public-facing breadth stays at the factory-status page (SM-C4).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-17 (authoring-feeding pages carry build timestamps).
- **Mode:** DEV-AUTO (visual judgment, § 9 preamble).
- **Gating question:** none.
- **Verify gate:** `bsl-metric-check` (+ `kedro-test`); D2 page inventory detail resolves in the CIS specs (Spine Deferred).
- **Depends on:** D1.

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-d3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-e1-implement-the-a2a-communication-interfaces.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story E1 (6.1): Implement the A2A communication interfaces'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story E1 (6.1): Implement the A2A communication interfaces

As a CFE authoring agent,
I want a structured A2A surface between the cf_atlas analytical agent and the conda-forge execution agents,
So that insights, contract violations, and policy breaches arrive as structured payloads, not prose.

**Acceptance Criteria:** (spec § 9 Story E1, binding)

**Given** the two agents (cf_atlas analytical, `conda-forge-expert` authoring)
**When** the A2A surface is built
**Then** the `cf_atlas` analytical agent can hand a structured payload to the `conda-forge-expert` agent (publish/subscribe or direct-message — transport resolves in this story's spec, Spine Deferred)
**And** payload schemas live in the `a2a/` module — the single schema source for alerts and insights (AD-20)
**And** payloads feeding authoring decisions carry their build timestamp (AD-17).

- **FRs:** FR-11.
- **Invariants:** AD-20 (sole structured inter-agent channel), AD-17.
- **Mode:** LOOP-E.
- **Gating question:** none (A2A transport is a story-spec decision, not a Q-gate).
- **Verify gate:** existing gates + payload round-trip fixture in `kedro-test`.
- **Depends on:** B3 (MCP surface), Epic 5 (BSL insights to carry).

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-e2-integrate-openlineage-opentelemetry.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story E2 (6.2): Integrate OpenLineage + OpenTelemetry'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story F1 (7.1): Complete the DuckDB consolidation + prove the cold-start claim'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story F1 (7.1): Complete the DuckDB consolidation + prove the cold-start claim

As the operator,
I want all legacy-`cf_atlas.db` residue migrated or deleted and the performance claims honestly benchmarked,
So that DuckDB/Parquet is the sole store and AC-7's claims are evidence, not promises.

**Acceptance Criteria:** (spec § 9 Story F1, binding)

**Given** B4's legacy retirement and the Wave-A-onward Parquet path
**When** the residue cleanup + benchmark run
**Then** no SQLite read or write path remains anywhere in the migrated surface (grep-gated: no `sqlite3` import outside the retired legacy tree)
**And** the attended benchmark records both a warm incremental refresh (the headline — only affected nodes re-run) and the cold full-build wall-clock vs the legacy 3–4 h network-bound baseline, with evidence recorded per AC-7's honest scoping
**And** the pass threshold was fixed in this story's spec **before** the benchmark ran (SM-3); pass is adjudicated at the attended event by operator sign-off.

- **FRs:** FR-5.
- **Invariants:** AD-4 (grep gate), AD-19, SM-C1 (do not chase cold-start).
- **Mode:** ATTENDED (benchmark boundary event — one of the five § 2.5 attended events). **Keystone story — pre-flight budget raise + `dev_stall_grace_s` raise (AD-18/Spine).**
- **Gating question:** none (threshold is a story-spec decision, Spine Deferred).
- **Verify gate:** grep gate + `kedro-test`; benchmark evidence at the attended event; wave-boundary `test-all`.
- **Depends on:** B4 (retirement decided), Epics 4–6 (surfaces that might still read legacy).

### Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts

As the operator,
I want inline pandera contracts behind a validator-agnostic `AfterNodeRunHook` with version-capped GX as boundary layer,
So that bad data halts the pipeline before persisting, with an A2A alert.

**Acceptance Criteria:** (spec § 9 Story F2, binding)

**Given** a malformed-payload fixture (e.g. PyPI JSON missing a version field)
**When** the node runs under the validation hook
**Then** the validation failure halts execution by raising a native Python exception
**And** the failure propagates to Dagster, halting the pipeline and raising an A2A alert
**And** the hook interface is validator-agnostic: swapping/adding the GX backend requires no node changes (fixture-proven with a stub second validator)
**And** GX participates only at conda-forge 1.18.2 (no ≥1.19 features); the `kedro-great-expectations`/`kedro-pandera` plugins are banned (AD-9).

- **FRs:** FR-10.
- **Invariants:** AD-9, AD-20 (alert channel), AD-23 (hook rides every entry point).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (halt fixture + stub-validator fixture).
- **Depends on:** E1 (A2A alert channel), C1 (Dagster halt propagation).

### Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`

As a CFE authoring agent,
I want RAG embeddings + similarity search via DuckDB's `vss` extension,
So that semantic retrieval over embedded artifacts runs in the same single engine.

**Acceptance Criteria:** (spec § 9 Story F3, binding)

**Given** embedded artifacts in the DuckDB store
**When** a similarity query runs
**Then** it returns ranked results from DuckDB via `vss`
**And** the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-f2-implement-the-data-validation-hook-and-inline-pandera-contracts.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts

As the operator,
I want inline pandera contracts behind a validator-agnostic `AfterNodeRunHook` with version-capped GX as boundary layer,
So that bad data halts the pipeline before persisting, with an A2A alert.

**Acceptance Criteria:** (spec § 9 Story F2, binding)

**Given** a malformed-payload fixture (e.g. PyPI JSON missing a version field)
**When** the node runs under the validation hook
**Then** the validation failure halts execution by raising a native Python exception
**And** the failure propagates to Dagster, halting the pipeline and raising an A2A alert
**And** the hook interface is validator-agnostic: swapping/adding the GX backend requires no node changes (fixture-proven with a stub second validator)
**And** GX participates only at conda-forge 1.18.2 (no ≥1.19 features); the `kedro-great-expectations`/`kedro-pandera` plugins are banned (AD-9).

- **FRs:** FR-10.
- **Invariants:** AD-9, AD-20 (alert channel), AD-23 (hook rides every entry point).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (halt fixture + stub-validator fixture).
- **Depends on:** E1 (A2A alert channel), C1 (Dagster halt propagation).

### Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`

As a CFE authoring agent,
I want RAG embeddings + similarity search via DuckDB's `vss` extension,
So that semantic retrieval over embedded artifacts runs in the same single engine.

**Acceptance Criteria:** (spec § 9 Story F3, binding)

**Given** embedded artifacts in the DuckDB store
**When** a similarity query runs
**Then** it returns ranked results from DuckDB via `vss`
**And** the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-f3-implement-vector-similarity-search-rag-via-duckdb-vss.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`

As a CFE authoring agent,
I want RAG embeddings + similarity search via DuckDB's `vss` extension,
So that semantic retrieval over embedded artifacts runs in the same single engine.

**Acceptance Criteria:** (spec § 9 Story F3, binding)

**Given** embedded artifacts in the DuckDB store
**When** a similarity query runs
**Then** it returns ranked results from DuckDB via `vss`
**And** the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-f4-dependency-hygiene-node-unified-ci-policy-gate.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story F4 (7.4): Dependency-hygiene node + unified CI policy gate'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM

As a dashboard consumer,
I want the Vizro-AI dashboard + BSL layer running in-browser via Pyodide / DuckDB-WASM,
So that the intelligence surface needs no backend at all.

**Acceptance Criteria:** (spec § 9 Story G1, binding)

**Given** the D-wave dashboard + BSL layer
**When** the WASM build runs
**Then** the dashboard loads and queries run client-side in the browser with no backend
**And** a `wasm-smoke` verify task exists (Playwright headless load-and-query against the built artifact — Chromium pre-provisioned).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-11 (gate is the wave's first deliverable).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `wasm-smoke`**.
- **Depends on:** Epic 5 (dashboard + BSL), F1 (canonical store).

### Story G2 (8.2): Emit Parquet artifacts to a static web host

As a dashboard consumer,
I want Parquet artifacts published to a static host and pulled via HTTP Range,
So that the WASM runtime reads live data with zero backend.

**Acceptance Criteria:** (spec § 9 Story G2, binding)

**Given** the G1 WASM runtime
**When** the emitter publishes
**Then** Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
**And** the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
**And** the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

### Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion

As the operator,
I want the pipeline event-driven via Dagster Sensors on upstream events (PyPI/GitHub webhooks or RSS),
So that ingestion is near-real-time and incremental instead of purely scheduled.

**Acceptance Criteria:** (spec § 9 Story G3, binding)

**Given** the C1 Dagster repository
**When** a simulated upstream event fires
**Then** it triggers the relevant pipeline incrementally via a Dagster Sensor
**And** the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-g2-emit-parquet-artifacts-to-a-static-web-host.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story G2 (8.2): Emit Parquet artifacts to a static web host'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story G2 (8.2): Emit Parquet artifacts to a static web host

As a dashboard consumer,
I want Parquet artifacts published to a static host and pulled via HTTP Range,
So that the WASM runtime reads live data with zero backend.

**Acceptance Criteria:** (spec § 9 Story G2, binding)

**Given** the G1 WASM runtime
**When** the emitter publishes
**Then** Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
**And** the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
**And** the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

### Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion

As the operator,
I want the pipeline event-driven via Dagster Sensors on upstream events (PyPI/GitHub webhooks or RSS),
So that ingestion is near-real-time and incremental instead of purely scheduled.

**Acceptance Criteria:** (spec § 9 Story G3, binding)

**Given** the C1 Dagster repository
**When** a simulated upstream event fires
**Then** it triggers the relevant pipeline incrementally via a Dagster Sensor
**And** the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-g3-implement-dagster-sensors-for-near-real-time-ingestion.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion

As the operator,
I want the pipeline event-driven via Dagster Sensors on upstream events (PyPI/GitHub webhooks or RSS),
So that ingestion is near-real-time and incremental instead of purely scheduled.

**Acceptance Criteria:** (spec § 9 Story G3, binding)

**Given** the C1 Dagster repository
**When** a simulated upstream event fires
**Then** it triggers the relevant pipeline incrementally via a Dagster Sensor
**And** the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas

As the operator,
I want the `wiki/raw/ → compiled/ → outputs/` tree and the 5 BMAD personas (Ingester, Compiler, Linker, Linter, Oracle) defined,
So that the knowledge-base factory has its storage shape and workforce.

**Acceptance Criteria:** (spec § 9 Story H1, binding)

**Given** the scaffolded project
**When** the wiki scaffold lands
**Then** the three-stage wiki tree exists with a scaffold-layout test
**And** the 5 persona definitions resolve through the § 2 customization layers
**And** PostgreSQL/MinIO storage services are conda-forge-provisioned per AD-16 (MinIO server provisioning resolved as this story's precondition).

- **FRs:** FR-22(a).
- **Invariants:** AD-22, AD-16.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** scaffold-layout test + persona-resolution test in `kedro-test`.
- **Depends on:** Epic 8 complete (wave order); pipeline outputs to consume exist from Epic 3+.
- **DELIVERED (2026-07-18 — opens Wave H):** new `pyforge.atlas.factory` package. `factory/wiki.py` = the single-owner `raw/→compiled/→outputs/` layout contract (`WIKI_STAGES`/`WikiLayout`/`scaffold_wiki`) with a per-segment `stage_path` traversal guard enforcing the AD-22 write-boundary; `factory/personas.py` = the 5 § 2.2 personas + `resolve_personas(*overlays)` (BMAD customization layers, highest-priority-last; overlay may only refine — unknown name / rename rejected; workforce frozen at five); `factory/storage.py` = env-driven resolver defaulting to the OFFLINE filesystem backend (MinIO selected only when `ATLAS_WIKI_S3_ENDPOINT` set; host-agnostic AD-2). MinIO/PostgreSQL SERVER bring-up DEFERRED (DW-H1). Gate `tests/factory/` (26). AD-1 import-ban green. PR #99.

### Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews

As the operator,
I want `agno` crews that compile raw docs, lint the wiki, and answer questions,
So that the wiki maintains itself with agent labor.

**Acceptance Criteria:** (spec § 9 Story H2, binding)

**Given** the H1 scaffold and a fixture wiki
**When** each crew runs end-to-end
**Then** compile transforms raw → compiled, lint reports violations, and Q&A answers grounded in compiled content
**And** wiki outputs carry their source datasets' staleness markers forward (AD-13/AD-22 — republication never launders freshness).

- **FRs:** FR-22(b).
- **Invariants:** AD-22, AD-13.
- **Mode:** DEV-AUTO (spec § 9 explicit: crew design needs judgment).
- **Gating question:** none (crew design detail is a story-spec decision, Spine Deferred).
- **Verify gate:** crews-on-fixture-wiki tests in `kedro-test`.
- **Depends on:** H1.
- **DELIVERED (2026-07-18):** `factory/crews.py` — `CompileCrew` (raw→compiled, per-doc-resilient, forwards source staleness from BOTH the inline `stale:` frontmatter AND the `.staleness.json` sidecar into compiled frontmatter + a visible body banner — AD-13/AD-22, republication never launders freshness), `LintCrew` (reports `missing-frontmatter`/`missing-title`/`empty-body`/`broken-link` [path-resolved, recursive]/`laundered-staleness`/`malformed-frontmatter`; never raises), `QACrew` (grounded answers over compiled content; deterministic keyword retriever + extractive synthesizer defaults). agno-Agent/LLM synthesis + F3-vss production retriever are injectable seams, offline by default — live bring-up DEFERRED (DW-H2). Gate `tests/factory/test_crews.py` (26). AD-1 import-ban green (yaml+stdlib only). An independent adversarial review found 2 MUST-FIX (inline-staleness laundering; lint/QA crash-on-malformed) + 1 SHOULD-FIX (leaf-only broken-link) — all fixed + regression-tested before merge.

### Story H3 (9.3): Integrate La Suite Docs REST API Sync

As the operator,
I want `LaSuiteClient` + `WikiSyncer` pushing compiled wiki files to the Layer-1 CMS via the Wagtail/Django REST API,
So that humans read the factory's knowledge in the presentation layer.

**Acceptance Criteria:** (spec § 9 Story H3, binding)

**Given** the H2 compiled wiki output and a mock Wagtail API
**When** the sync runs
**Then** a round-trip fixture test passes against the mock (push, update, idempotent re-push).

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-h2-implement-agno-compilation-linting-and-q-a-crews.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews

As the operator,
I want `agno` crews that compile raw docs, lint the wiki, and answer questions,
So that the wiki maintains itself with agent labor.

**Acceptance Criteria:** (spec § 9 Story H2, binding)

**Given** the H1 scaffold and a fixture wiki
**When** each crew runs end-to-end
**Then** compile transforms raw → compiled, lint reports violations, and Q&A answers grounded in compiled content
**And** wiki outputs carry their source datasets' staleness markers forward (AD-13/AD-22 — republication never launders freshness).

- **FRs:** FR-22(b).
- **Invariants:** AD-22, AD-13.
- **Mode:** DEV-AUTO (spec § 9 explicit: crew design needs judgment).
- **Gating question:** none (crew design detail is a story-spec decision, Spine Deferred).
- **Verify gate:** crews-on-fixture-wiki tests in `kedro-test`.
- **Depends on:** H1.
- **DELIVERED (2026-07-18):** `factory/crews.py` — `CompileCrew` (raw→compiled, per-doc-resilient, forwards source staleness from BOTH the inline `stale:` frontmatter AND the `.staleness.json` sidecar into compiled frontmatter + a visible body banner — AD-13/AD-22, republication never launders freshness), `LintCrew` (reports `missing-frontmatter`/`missing-title`/`empty-body`/`broken-link` [path-resolved, recursive]/`laundered-staleness`/`malformed-frontmatter`; never raises), `QACrew` (grounded answers over compiled content; deterministic keyword retriever + extractive synthesizer defaults). agno-Agent/LLM synthesis + F3-vss production retriever are injectable seams, offline by default — live bring-up DEFERRED (DW-H2). Gate `tests/factory/test_crews.py` (26). AD-1 import-ban green (yaml+stdlib only). An independent adversarial review found 2 MUST-FIX (inline-staleness laundering; lint/QA crash-on-malformed) + 1 SHOULD-FIX (leaf-only broken-link) — all fixed + regression-tested before merge.

### Story H3 (9.3): Integrate La Suite Docs REST API Sync

As the operator,
I want `LaSuiteClient` + `WikiSyncer` pushing compiled wiki files to the Layer-1 CMS via the Wagtail/Django REST API,
So that humans read the factory's knowledge in the presentation layer.

**Acceptance Criteria:** (spec § 9 Story H3, binding)

**Given** the H2 compiled wiki output and a mock Wagtail API
**When** the sync runs
**Then** a round-trip fixture test passes against the mock (push, update, idempotent re-push).

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-h3-integrate-la-suite-docs-rest-api-sync.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story H3 (9.3): Integrate La Suite Docs REST API Sync'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story H3 (9.3): Integrate La Suite Docs REST API Sync

As the operator,
I want `LaSuiteClient` + `WikiSyncer` pushing compiled wiki files to the Layer-1 CMS via the Wagtail/Django REST API,
So that humans read the factory's knowledge in the presentation layer.

**Acceptance Criteria:** (spec § 9 Story H3, binding)

**Given** the H2 compiled wiki output and a mock Wagtail API
**When** the sync runs
**Then** a round-trip fixture test passes against the mock (push, update, idempotent re-push).

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

---

> Source: `specs/spec-h4-orchestrate-crews-via-dagster.md` (canonical file — still lives there).
> Original frontmatter: `title: 'Story H4 (9.4): Orchestrate Crews via Dagster'; type: 'feature'; status: 'regenerated'; regenerated: '2026-07-25'; source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'; original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'`

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.
