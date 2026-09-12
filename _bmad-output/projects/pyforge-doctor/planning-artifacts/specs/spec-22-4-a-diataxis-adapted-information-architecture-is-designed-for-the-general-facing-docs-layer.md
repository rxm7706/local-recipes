---
title: 'A Diátaxis-adapted information architecture is designed for the general-facing docs layer'
type: 'feature'
created: '2026-09-11'
status: 'done'
baseline_revision: 'efabb6d912099eda55950f2d8c9d507e35545684'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The general-facing documentation layer (`README.md`, `docs/reference/`,
`docs/intake/`, scattered onboarding/operational content) has no recognizable
information-architecture lens applied to it. A newcomer has no map distinguishing "where do I
start," "how do I do X," "what's the exact config/CLI surface," and "why does this work this
way." `docs/reference/` (14 files today: `airgap-distribution-contract.md`,
`antigravity-developer-startup.md`, `container-base-layer-convention.md`,
`developer-guide.md`, `enterprise-deployment.md`, `github-workflows.md`,
`library-llms-full.md`, `manticore-studio.md`, `mcp-server-architecture.md`,
`pixi-config-jfrog.example.toml`, `station-verify-commands.md`, `test-charter.md`, plus its own
`README.md`) already accidentally covers most of a Diátaxis "Reference" quadrant, but mixes
true reference material (config/CLI/schema specs — e.g. `station-verify-commands.md`,
`container-base-layer-convention.md`, `pixi-config-jfrog.example.toml`) with
architecture-rationale ("why") content (e.g. `mcp-server-architecture.md`,
`enterprise-deployment.md`, `airgap-distribution-contract.md`). Nothing plays the Tutorials or
How-to-Guides role explicitly.

**Approach:** Design and document a four-quadrant map (Tutorials/Getting-Started, How-to
Guides, Reference, Explanation), adapted to this repo's actual content volume, not a generic
four-folder template. This is a **design story** — its deliverable is the documented map and
per-file quadrant assignment for every existing `docs/reference/` file (split by kind: true
reference stays Reference, architecture-rationale content becomes Explanation), not the fully
populated Tutorials/How-to content (Story 22.5) or the corrected entry-point pointers (Story
22.6). The BMAD spec-driven tier is explicitly out of scope — it is a different layer (the
spec-and-build pipeline), not general documentation.

## Boundaries & Constraints

**Always:**
- Classify every existing file in `docs/reference/` into exactly one quadrant, by kind (true
  reference material vs. architecture-rationale/"why" content) — do not leave any file
  unclassified.
- `docs/reference/`'s existing content is preserved as the seed of the Reference quadrant,
  relocated/reorganized, not discarded and rebuilt from scratch.
- Document the map itself (which quadrant lives where, physical paths) so Stories 22.5 and
  22.6 have a concrete target to build against — this story's own success is the map existing
  and being followable, not a live "does everything render" check.
- The BMAD spec-driven tier (`docs/dreams/`, `docs/specs/` legacy Tier 1,
  `_bmad-output/*/planning-artifacts/`, gitignored `implementation-artifacts/`) is named
  explicitly as untouched by the map.

**Never:**
- Do not bolt on a generic `/docs/getting-started/` + `/docs/guides/` + `/docs/reference/`
  scaffold regardless of fit — the structure must grow from what's already here and be sized to
  this repo's actual content volume (14 reference files, not hundreds).
- Do not move or rewrite the 5 already-known self-flagged-stale `docs/reference/*.md` files
  (`github-workflows.md`, `station-verify-commands.md`, `enterprise-deployment.md`,
  `mcp-server-architecture.md`, `library-llms-full.md`) beyond relocating them into the correct
  quadrant — refreshing their content is a separate, already-tracked issue, out of this story's
  scope.
- Do not populate the Tutorials/How-to-Guides quadrants with real content in this story —
  design the map and boundaries only; Story 22.5 does the population.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| True reference file (e.g. `station-verify-commands.md`) | Config/CLI/schema-shaped content | Assigned to the Reference quadrant | n/a |
| Architecture-rationale file (e.g. `mcp-server-architecture.md`) | "Why this works this way" content | Assigned to the new Explanation quadrant | n/a |
| Mixed-content file (e.g. `developer-guide.md`) | Both reference and how-to/tutorial content in one file | Named in the map as needing a future split (Story 22.5's job to execute), not silently left in one quadrant | Named, not silent |
| BMAD spec-driven tier file | Anything under `docs/dreams/`, `docs/specs/`, `_bmad-output/*/planning-artifacts/` | Explicitly excluded from the map — untouched | n/a |
| One of the 5 already-stale reference docs | e.g. `github-workflows.md` | Relocated into its quadrant; content NOT refreshed (separate tracked issue) | Named in the map as still-stale, not silently fixed |

</intent-contract>

## Code Map

- `docs/MAP.md` — master IA map (chosen over `docs/README.md` section: discoverable at docs
  root alongside `intake/` and `dreams/` without a new top-level index file).
- `docs/tutorials/README.md`, `docs/how-to/README.md` — empty scaffolds for Story 22.5.
- `docs/explanation/` — new Explanation quadrant; receives architecture-rationale relocations.
- `docs/reference/` — Reference quadrant home; true reference retained, redirect stubs for moved
  files, mixed files flagged for 22.5 split.
- `README.md` — read-only; Common Commands / Quick start accounted in MAP as 22.5 targets.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-general-docs-consistency/SPEC.md`
  — CAP-4 success criteria this story satisfies.

## Tasks & Acceptance

**Execution:**
- `feature` — design the four-quadrant map (Tutorials/Getting-Started, How-to Guides,
  Reference, Explanation), naming physical paths for each.
- `feature` — classify all 14 existing `docs/reference/` files into a quadrant, by kind.
- `feature` — relocate `docs/reference/`'s files per the classification (Reference-kind files
  may stay in `docs/reference/`; Explanation-kind files move to their new home).
- `feature` — document the map itself so it is discoverable and followable for Stories 22.5 and
  22.6.

**Acceptance Criteria:**
- Given the general-facing docs layer has no information-architecture lens today, when a
  Diátaxis-adapted map is designed naming four quadrants and what lives where, then the map is
  documented and followable.
- Given `docs/reference/`'s existing content mixes reference and rationale, when the map
  classifies each file by kind, then true reference material stays in/becomes the Reference
  quadrant's home and architecture-rationale content moves to the new Explanation quadrant —
  relocated, not discarded and rebuilt.
- Given the BMAD spec-driven tier is a different layer, when the map is produced, then it names
  that tier explicitly as untouched.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — expected: no new finding
  introduced.
- Manual verification: every file originally in `docs/reference/` is accounted for in the new
  map (none silently dropped); a fresh `git status` confirms no file under `docs/dreams/`,
  `docs/specs/`, or `_bmad-output/*/planning-artifacts/` was touched.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 18 findings — high 0, medium 2, low 4, false 1, maybe-false 0, reject 11
- findings:
  - `[medium]` `[patch]` MAP Reference/Explanation tables had four pipe cells against three-column headers — merged stale flags into Notes column
  - `[medium]` `[patch]` `sync-jira-github-workflow-templates/` omitted from IA map — added to MAP and `docs/reference/README.md`
  - `[low]` `[patch]` `mcp-server-architecture.md` cited old `docs/enterprise-deployment.md` path — fixed relative link
  - `[low]` `[patch]` `enterprise-deployment.md` pixi template copy path wrong after relocation — fixed to `docs/reference/pixi-config-jfrog.example.toml`
  - `[low]` `[patch]` MAP opening file count misleading — corrected to 14 md + 1 toml + 1 template dir
  - `[low]` `[patch]` `docs/explanation/README.md` stale refresh tracking unnamed — cross-referenced Story 22.4 stale-doc bucket
  - `[low]` `[reject]` Scaffold READMEs lack cross-quadrant links — acceptable for empty scaffolds until 22.5
  - `[false]` `[reject]` Verification-gap layer reported no gaps — confirmed; doc-IA story has manual verification only
  - `[defer]` Section-anchor inbound links to relocated docs hit redirect stubs — Story 22.6 entry-point/link sweep
  - `[defer]` `enterprise-deployment.md` procedural sections remain in Explanation until 22.5 split — noted in MAP
  - `[defer]` No automated link-integrity detector for doc relocations — out of story scope
  - `[defer]` `CLAUDE.md` / dreams still cite pre-relocation paths — Story 22.6 explicit scope
  - `[defer]` Parent CAP-4 spec status not updated — story metadata only; CAP-4 spans 22.4–22.6

## Auto Run Result

Status: done

**Summary:** Designed and landed a Diátaxis-adapted general-docs map at `docs/MAP.md`, scaffolded `docs/tutorials/` and `docs/how-to/`, relocated three architecture-rationale files to `docs/explanation/` with redirect stubs, and re-indexed `docs/reference/README.md`.

**Files changed:**
- `docs/MAP.md` — master four-quadrant IA map with per-file classification and BMAD-tier exclusion
- `docs/tutorials/README.md`, `docs/how-to/README.md` — empty scaffolds for Story 22.5
- `docs/explanation/` — README + relocated `mcp-server-architecture.md`, `enterprise-deployment.md`, `airgap-distribution-contract.md`
- `docs/reference/` — updated README; redirect stubs for moved files
- Story spec — status/baseline/code map/review log

**Review:** 6 patches applied (2 medium, 4 low); 4 items deferred to Stories 22.5/22.6; 11 rejected/false.

**Follow-up review recommended:** false — patches applied and re-verified in same pass.

**Verification:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — exit 0 (pre-existing warnings only)
- Manual: all pre-22.4 `docs/reference/` artifacts accounted in MAP including `sync-jira-github-workflow-templates/`; no edits under `docs/dreams/`, `docs/specs/`, or other planning-artifacts beyond this story spec

**Residual risks:** Inbound links to old `docs/reference/*.md` paths (including § anchors) remain until Story 22.6; five stale doc bodies unchanged by design.
