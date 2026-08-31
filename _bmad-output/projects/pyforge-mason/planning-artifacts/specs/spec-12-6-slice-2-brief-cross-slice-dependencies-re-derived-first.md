---
title: 'Slice 2 brief — cross-slice dependencies re-derived first'
type: feature
created: '2026-08-27'
status: done
updated: '2026-08-28'
baseline_revision: 4717c334e335061ae88f953977dfb2cd79212f86
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-4-the-re-scope-gate-measured-cost-recorded-decision.md
warnings: []
deferred:
  - summary: >-
      campaign-state.yaml's top-of-file "HOW TO RESUME" protocol reads only
      current_focus's own next_action, so a resuming session can miss a still-open
      next_action on a different slice.
    evidence: |-
      Established in Story 6.1, predates this story. campaign.current_focus was
      reassigned from slice-1 to slice-2 by this story; slice-1's own next_action
      (a targeted github_updater.py re-port) remains open and unresolved. This
      story added an adjacent comment flagging it, but the master resume-protocol
      one-liner near the top of the file still only names current_focus's slice.
    location: >-
      _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:11-12
    severity: medium
  - summary: >-
      slice-map.md classifies test-skill.py as one of Slice 2's own canonical
      scripts, but it is a throwaway ad-hoc script unrelated to recipe lifecycle.
    evidence: |-
      slice-map.md documents test-skill.py as a 10-line ad-hoc script hitting
      api.anaconda.org for a single package, with the real test-suite entrypoint
      living elsewhere. This story's brief inherited the entry verbatim from
      slice-map.md, which is this story's documented read-only Code Map source,
      not a file it may correct.
    location: >-
      _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
    severity: low
  - summary: >-
      Slice 2's brief_path lands inside this ephemeral dispatch worktree's
      gitignored implementation-artifacts/ with no promotion-to-durable-storage
      step, mirroring slice 1's own unresolved precedent.
    evidence: |-
      Per this repo's own documented Tier-3-teardown incident (pyforge-warden
      lost 13 of 31 story specs to worktree teardown before a promotion
      convention existed for tracked story specs), a Tier-3 brief with no
      analogous promotion step risks the same fate. This story followed its own
      spec's explicit physical-path directive; the gap is systemic to the
      campaign's Tier-3 brief convention, not something this story introduced.
    location: >-
      _bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/cfe-recipe-lifecycle/skill-brief.yaml
    severity: low
  - summary: >-
      Slice 1's own brief_path still points at pyforge-atlas's implementation-artifacts
      tree rather than pyforge-mason's, a divergence from the parallel-agent
      physical-path rule that this story's spec explicitly flagged as precedent.
    evidence: |-
      Documented in this story's own spec Boundaries section as slice 1's
      atypical landing location. Pre-existing state from Story 12.1, unchanged
      by this story, and out of this story's own boundaries (which govern only
      slice 2's brief_path).
    location: >-
      _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml (slice-1-recipe-generation entry)
    severity: low
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

## Review Triage Log

### 2026-08-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 1, low 2)
- defer: 4 (medium 1, low 3)
- reject: 7
- addressed_findings:
  - `medium` `patch` `skill-brief.yaml`'s `source_repo` field recorded the ephemeral absolute
    dispatch-worktree path (`/home/.../.worktrees/dispatch-pyforge-mason-12.6`) rather than a
    stable repo-relative identity — misleading provenance once the worktree is removed. Fixed
    by re-pointing the implementation subagent to use a stable repo-relative value.
  - `low` `patch` `skill-brief.yaml`'s `created_by` field read `Rxm7706` (capitalized),
    inconsistent with the lowercase `rxm7706` git identity used everywhere else in the repo —
    fixed to lowercase.
  - `low` `patch` `campaign-state.yaml`'s `campaign.callers` note hard-wraps the backtick code
    span `` `campaign.re_scope_gate.pre_conditions.c_cross_slice_rederivation` `` across a line
    break, splitting the identifier mid-word in raw-text reading — rewrapped so the code span
    stays on one line.

Deferred (4): a pre-existing structural gap in the top-of-file "HOW TO RESUME" resume protocol
(reads only `current_focus`'s own `next_action`, so a resuming session can miss slice-1's still
-open item; established in Story 6.1, partially mitigated here by an adjacent comment, medium
severity); slice-map.md's `test-skill.py` classification (a pre-existing, already-questionable
entry inherited verbatim into this brief's `scope.include`, not this story's read-only source
to correct, low); the Tier-3 `brief_path` landing inside this ephemeral dispatch worktree with
no promotion-to-durable-storage step, mirroring slice 1's own unresolved precedent (real
per this repo's own documented Tier-3-teardown incident, but not a new problem this story
introduced, low); slice 1's own `brief_path` physical-location divergence (still pointing at
`pyforge-atlas`'s tree per Story 12.1's precedent) remaining uncorrected — pre-existing state
from a prior story, out of this story's own boundaries, low.

Rejected (7): `campaign-state.yaml`'s `next_story` text reading "12.1-12.6 done" while this
spec's own frontmatter was still `in-review` at review time — self-resolving, since both files
land in the same finalize commit once this story's `status` becomes `done`; the claim that the
next_action text "understates" the slice-2 equivalence-harness gap — Story 12.7's own spec
(`spec-12-7-slice-2-compiled-and-equivalence-validated.md`) already scopes authoring/running
that harness, so nothing is silently assumed; the `failure_catalog_generator.py`
slice-map.md-correction "has no tracked owner" — it is flagged in `next_action` for Story 12.7,
this campaign's own established ownership mechanism, matching how every other open item in
this file is tracked; the full ~104-entry gotcha corpus embedded verbatim in the brief — this
is exactly what the AC's own "cite slice 2's relevant gotchas verbatim" requirement asks for;
the "confirm each gotcha individually" divergence flagged by the intent-alignment audit — the
brief does check every ID against live in-code references and reasons explicitly about ~8
borderline/refined ones, applying categorical judgment only to the narrative-only majority,
which is a disclosed and defensible reading, not a violation; the BLOCKED-then-retry AC
ambiguity — the I/O matrix's own "Expected Output/Behavior" column reads "Brief documents it
explicitly; budget for it" (not "must enter an actual BLOCKED state"), and the scenario that
row models (a new cross-slice *import*) did not actually occur this run (the surprise found was
an unclassified *script*, not a new import), so no single reading is forced and none was
violated; coverage counts (`scripts: 22, wrappers: 17, mcp_tools: 19`) "not reconciled" against
the corrected live-tree totals (69/58/46) — those totals are campaign-wide across all 5 slices,
not slice-2's own count, and the newly-found script was deliberately NOT added to slice 2's
scope, so the unchanged count is correct, not stale.

## Auto Run Result

**Summary:** Re-derived Slice 2's (Recipe Lifecycle) cross-slice dependencies against the live
tree (CFE v8.84.0, not slice-map.md's frozen v8.82.3 snapshot), ran `skf-brief-skill`'s real
canonical writer to produce a schema-valid `skill-brief.yaml`, decided `native-build.sh`/
`build-locally.py`'s cutover scope (permanently out of campaign scope), cited slice 2's
relevant SKILL.md gotchas verbatim, and set `campaign-state.yaml`'s slice-2 entry to `briefed`
with `brief_path` set — closing the re-scope gate's fourth and final pre-condition
(`c_cross_slice_rederivation`).

**Files changed:**
- `_bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/cfe-recipe-lifecycle/skill-brief.yaml`
  (new, gitignored Tier-3) — the slice-2 brief: scope.include/exclude, cross-slice-dependency
  re-derivation write-up, and verbatim gotcha citations.
- `specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` — pre-condition (c) flipped
  `open` → `closed`; slice-2 entry set to `status: briefed` with `brief_path`/
  `brief_mirrored_through`; `campaign.callers`' previously-open native-build.sh/build-locally.py
  cutover-scope question resolved; `current_focus`/`next_story` advanced to Story 12.7.
- `spec-12-6-slice-2-brief-cross-slice-dependencies-re-derived-first.md` (this file) —
  frontmatter status cycle, Review Triage Log, deferred list, this Execution record.

**Review findings breakdown:** 3 patches applied (medium 1, low 2) — `skill-brief.yaml`'s
`source_repo` pointing at an ephemeral absolute worktree path (fixed to `.`), its `created_by`
capitalization mismatch (fixed to lowercase `rxm7706`), and a hard-wrapped backtick identifier
in `campaign-state.yaml`'s new note (rewrapped). 4 deferred (medium 1, low 3) — see frontmatter
`deferred:` and Review Triage Log above; all pre-existing or systemic, not introduced by this
story. 7 rejected — see Review Triage Log above; each either self-resolves via this workflow's
own finalize step, is already covered by a downstream story's own spec, matches the AC's
explicit requirements, or reflects a reviewer misreading corrected by re-checking the source.

**Follow-up review recommendation:** `true` (patch severities: 1 medium + 2 low →
3×1 + 1×2 = 5 ≥ 5).

**Verification performed:** `pixi run -e local-recipes cfe-rebuild-guard-check` exits clean
before and after every edit in this run (all four clauses); `python scripts/mason_cfe_surface_check.py`
exits clean (no CFE-surface edit); `skf-validate-brief-schema.py` on the brief reports
`valid: true`, 0 errors, 0 warnings (re-confirmed after the patch pass, with `source_repo: "."`
and `created_by: "rxm7706"`); `python3 -c "import yaml"` parse-checks on both `campaign-state.yaml`
and this spec's frontmatter (deferred list included) pass clean; `pixi run -e local-recipes
python -m pytest tests/scripts/test_cfe_rebuild_guard_check.py -q` — 39 passed (pre-existing
clause-(d) coverage, incl. the gate-bypassed positive/negative cases the I/O matrix's rows 1-2
correspond to); `git status --porcelain` confirms only the two intended tracked files changed
throughout, plus this spec file.

**Residual risks:** the 4 deferred items above (resume-protocol blind spot, `test-skill.py`
misclassification, Tier-3 brief durability, slice-1's own physical-path divergence) — all
pre-existing or systemic, none blocking Story 12.7. Story 12.7's own next_action (recorded in
`campaign-state.yaml`) already flags the `failure_catalog_generator.py` slice-map.md
classification gap as work to resolve before or alongside compiling.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
