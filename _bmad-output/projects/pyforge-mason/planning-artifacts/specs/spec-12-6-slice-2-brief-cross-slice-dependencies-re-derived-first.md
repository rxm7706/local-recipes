---
title: 'Slice 2 brief — cross-slice dependencies re-derived first'
type: feature
created: '2026-08-27'
status: ready
updated: '2026-08-27'
baseline_revision: cc8b3b2b1c09d6e56a5aebf752e25f507c846571
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-4-the-re-scope-gate-measured-cost-recorded-decision.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Slice 2's brief cannot yet be written — `campaign-state.yaml`'s own re-scope
gate (Story 6.4, decision `adjust`) names four concrete pre-conditions, and even once they
close, slice-map.md's own cross-slice-dependency notes for slice 2 need re-confirming against
the live tree, not just re-quoting, before compiling — Story 6.3's precedent for slice 1
found an undocumented cross-slice import that cost a full BLOCKED-then-retry cycle.

**Approach:** Once Stories 12.2-12.5 close the four pre-conditions, run `skf-brief-skill` for
slice 2 with its full cross-slice dependency list re-derived from the live tree (not just
re-confirming the CVE-DB/Slice-3 ordering risk slice-map.md already names), decide
`native-build.sh`/`build-locally.py`'s cutover scope no later than this brief, cite the
relevant gotchas verbatim, and set campaign-state slice 2 to `briefed` with `brief_path` set.

## Acceptance Criteria

- **Given** the gate's pre-conditions closed **Then** skf-brief-skill produces slice 2's
  brief with its full cross-slice dependency list re-derived (not just re-confirming the
  CVE-DB/Slice-3 ordering risk slice-map.md already names, and deciding
  `native-build.sh`/`build-locally.py`'s cutover scope no later than this brief), the relevant
  gotchas as verbatim inputs, and campaign-state slice 2 at `briefed` with `brief_path` set —
  budgeting at least one BLOCKED-and-retry cycle per slice 1's precedent.

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-6-slice-2-brief-cross-slice-dependencies-re-derived-first`.
- **Block If run before Stories 12.2, 12.3, 12.4, and 12.5 land** (this story's own Deps) —
  do not invoke `skf-brief-skill` for slice 2 until all four are confirmed done in the tracked
  ledger, and (once 12.4 lands) until `cfe_rebuild_guard_check`'s new clause (d) would itself
  accept the `brief_path` write.
- Re-derive, not just cite, slice 2's cross-slice dependencies: reconfirm the
  `_cfy_template.py`/`_paths.py`/`_http.py` imports slice-map.md already names still hold
  against the live tree, reconfirm the Slice-2-before-Slice-3 CVE-DB ordering risk
  (`scan_for_vulnerabilities` consumes `cve_manager.py`, per slice-map.md's own "Known
  ordering risk" and Slice 2's "Cross-slice dependencies" notes), and decide
  `native-build.sh`/`build-locally.py`'s cutover scope (both are live Mason callers —
  `build_native`/`build_docker` adapters — sitting outside the counted scripts/wrappers/MCP-tools
  surfaces entirely) no later than this brief.
- Cite slice 2's relevant gotchas verbatim — slice-map.md names SKILL.md G1–G53, G55–G90,
  G92–G97, G99–G108 as a blanket, not-yet-individually-confirmed claim (its own caveat);
  confirm each gotcha's actual relevance to slice 2 rather than trusting that list wholesale.
- Set `campaign-state.yaml`'s `slice-2-recipe-lifecycle` entry: `status: briefed`,
  `brief_path` set to wherever the brief actually lands.
- Physical-path note: slice 1's brief atypically landed under
  `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/cfe-recipe-generation/`
  even though this campaign is a pyforge-mason effort. Under this repo's parallel-agent rule
  (`BMAD_ACTIVE_PROJECT=pyforge-mason`, physical paths, never `bmad-switch`), slice 2's brief
  should land under pyforge-mason's own
  `_bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/` instead — record
  whichever path is actually used in `campaign-state.yaml`'s `brief_path`, and note the
  divergence from slice 1's precedent if it recurs.

**Block If:** Any of the four pre-conditions is not actually closed when this story starts;
also halt if re-checking the CVE-DB/Slice-3 ordering risk finds it has become a real blocker
— slice-map.md itself asks whoever briefs slice 2 to "re-confirm this ordering still holds
up."

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate). A brief cites gotchas and scripts; it never modifies the
  live skill. `skf-brief-skill`'s output is a Tier-3 YAML brief, never a CFE-surface edit.
- Never compile anything in this story — `skf-create-skill` (compilation) is Story 12.7's
  job; this story stops at `briefed`.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pre-conditions all closed | — | Brief produced; slice 2 → `briefed` | — |
| Pre-conditions not yet closed | — | HALT, no brief written | — |
| CVE-DB/Slice-3 ordering risk re-confirmed clean | — | Brief proceeds, notes the re-check | — |
| CVE-DB/Slice-3 ordering risk now a real blocker | — | HALT / escalate rather than briefing around a known-bad ordering | — |
| A new, previously-undocumented cross-slice import surfaces (slice 1's precedent) | — | Brief documents it explicitly; budget for it | Matches Story 6.3's BLOCKED-then-retry precedent |
| `native-build.sh`/`build-locally.py` cutover scope undecided | — | This brief is where it gets decided (AC's own explicit requirement) | Must not defer past this brief |

</intent-contract>

## Code Map

- `_bmad/skf/skf-brief-skill/` — the skill to invoke, scoped to Slice 2's (Recipe Lifecycle)
  canonical-scripts/wrappers/MCP-tools list.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md`
  — Slice 2 section (canonical scripts, wrappers, MCP tools, and "Cross-slice dependencies")
  and the "Slice Ordering (fixed)" section's "Known ordering risk" note — read-only source to
  re-derive from, not just recite.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — `slice-2-recipe-lifecycle` entry (`status`, `brief_path`, `next_action` fields to update).
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` — the sole sanctioned
  Mason→CFE call surface (`_CFE_SCRIPTS`); read-only reference for which 8 of slice 2's
  scripts already have live Mason callers (per slice-map.md's Mason Caller Inventory) —
  relevant context for the brief, not a file this story edits.
- The Tier-3 brief output location itself (`_bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/`
  or wherever `skf-brief-skill`'s forge-data folder resolves to for this project) — gitignored;
  not to be confused with the tracked planning-artifacts specs directory this task's own HARD
  RULE governs.
