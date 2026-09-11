---
title: 'A Diátaxis-adapted information architecture is designed for the general-facing docs layer'
type: 'feature'
created: '2026-09-11'
status: 'backlog'
baseline_revision: 'a7752e7f91015b81d79a979bfca61a0dc8c8c8bb'
review_loop_iteration: 0
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

- `docs/reference/` — all 14 existing files, to be classified and (if the map calls for
  physical relocation) moved.
- `README.md` — read-only reference for currently-scattered onboarding content this map must
  account for (the "Common Commands" section).
- New: the map document itself — path and name are this story's own design decision (e.g. a new
  `docs/README.md` section, or a dedicated `docs/MAP.md` — the story should state which and
  why).

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
