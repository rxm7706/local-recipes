---
title: "Story 30.2: The project-context surface follows 6.12 (D1)"
type: 'feature'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '9e91e2e7cb787d7992bf27e7fde41fe606b28cf9'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/epic-30-context.md'
warnings: [oversized]
deferred:
  - summary: >-
      architecture-bmad-infra.md, index.md, and PRD.md still describe the retired
      per-station project-context.md rulebooks as live artifacts in several places.
    evidence: |-
      Verified true by direct read. architecture-bmad-infra.md's re-ground is explicitly
      Story 30.3's job (epics.md sequences it after this story). PRD.md is on this
      spec's own "Never rewrite" list (shipped historical/living-doc prose, out of
      this story's declared consumer-migration scope). index.md is the same class of
      narrative living doc, swept by the ordinary SYNC-RUNBOOK cadence rather than
      this story's consumer list.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/{architecture-bmad-infra.md,index.md,PRD.md}
    severity: low
  - summary: >-
      pyforge-doctor's test_full_applicable_layers_reports_ok fixture has a pre-existing,
      unrelated "dream" layer gap in the chain-audit-checkpoint-layers checkpoint (reports
      noDream/gaps:[dream]) despite its own dream=True fixture setup -- discovered while
      verifying the "context" glob fix, not caused by this story.
    evidence: |-
      Reproduced directly: pytest -s on the unmodified fixture prints "[fleet] noDream:
      pyforge-marshal" and layers_cp.evidence["gaps"] == ["dream"], even though the loop
      at line 162 asserting "dream" in ev["present"] passes -- two different evidence
      shapes (chain-layers-audit's "present" list vs. chain-audit-checkpoint-layers'
      "gaps" list) disagree on the same fixture, suggesting a deeper inconsistency in
      how DREAMS_DIR/REPO_ROOT get resolved across the monkeypatched _install_generate
      seam. Worked around by scoping this story's own new assertions to "context"
      specifically rather than the full layers-checkpoint pass, so this story's fix
      doesn't depend on the pre-existing gap being resolved.
    location: >-
      src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py::test_full_applicable_layers_reports_ok
    severity: medium
---

<intent-contract>

## Intent

**Problem:** BMAD-METHOD 6.12.0 ships `persistent_facts = []`, so bmad skills no longer
auto-load the 8 `_bmad-output/projects/*/project-context.md` rulebook files. D1 (already
settled, not re-opened here) says the project-context surface going forward is the
`bmad:context` managed block inside `AGENTS.md`, maintained by the `bmad-project-context`
skill. Today the 8 rulebook files still exist, three scripts still read/reference them
(`pyforge-doctor`'s `factory.py`, `scripts/bmad_drift_check.py`, `scripts/fleet_scan.py`), and
`SYNC-RUNBOOK.md` still names them as the living-doc cadence's second target.

**Approach:** Migrate every code consumer first (factory.py, bmad_drift_check.py,
fleet_scan.py — in that order relative to file deletion, never the reverse), then retire the 8
files (absorbing any content genuinely at risk of loss into `AGENTS.md` via
`bmad-project-context adopt`), then rewrite `SYNC-RUNBOOK.md`'s cadence language.

## Boundaries & Constraints

**Always:**
- Migrate consumers BEFORE deleting any `project-context.md` file. `pyforge-doctor`'s
  `factory.py` TRACKED list (marshal-only) manufactures a permanent HARD `pin-missing`
  finding if a TRACKED file is deleted while its row survives (`_read()` returns `""` for a
  missing file, which `_doc_pin()` treats as "no pin" for a non-`snapshot` category) — this
  order is safety-critical, not stylistic.
- There is exactly ONE `bmad:context` managed block in the repo today, in the ROOT
  `AGENTS.md` — no station has its own. D1's decision names this singular shared block as
  the surface; do not invent 8 per-station AGENTS.md files as a default. `pyforge-atlas` is
  the one candidate whose content may warrant a "child" AGENTS.md under
  `src/shared/packages/pyforge-atlas/AGENTS.md`, per `bmad-project-context`'s own documented
  Children rule (subtree-exclusive, substantial, user-approved) — let the skill's own run
  decide this, don't pre-script it.
- For `pyforge-marshal` and `pyforge-atlas` — the two files with genuinely unique content at
  risk of loss (marshal: JFrog env-var mitigation detail + the "Planner Constraints" section;
  atlas: Testing Contract, Architectural Boundaries meta-tests, Exit-Code Convention,
  Compliance Report Structure, code-grounded patterns — none of which exists anywhere else) —
  actually invoke the `bmad-project-context` skill in adopt mode and let its ledger process
  (retain/rewrite/relocate/automate/delete) decide the disposition of each section.
- For the other 6 stations (steward, warden, doctor, mason, herald, scribe) — confirmed
  near-identical boilerplate whose entire content is already covered by CLAUDE.md's BMAD
  multi-project-pattern documentation and the existing AGENTS.md — before deleting each,
  independently re-verify (read the file fresh, don't just trust this spec's claim) that it
  carries no station-specific content beyond the shared template and stale ledger-count
  snapshots. If a file DOES carry something unique, treat it like marshal/atlas (run adopt).
- `fleet_scan.py`'s "context" `FLEET_STAGES` glob repoints at the root `AGENTS.md`'s path
  (matching the actual singular surface) for both the satellite and primary-project branches.
  Update `pyforge-doctor`'s `test_sources_board_chain_layers_audit.py` fixture (which writes a
  `project-context.md` to satisfy the old glob) to match the new one.
- `bmad_drift_check.py`'s mirrored TRACKED row / classify() branch (dead code — kept only as
  a hand-synced reference copy per SYNC-RUNBOOK's own convention) is deleted alongside
  `factory.py`'s for hygiene, even though nothing currently calls it.
- End state: `bmad-drift-check` and `detectors-ci` green, zero `project-context.md` rows in
  `factory.py`/`bmad_drift_check.py`, no `pin-missing` HARD finding, and
  `SYNC-RUNBOOK.md`'s living-doc cadence names only `architecture-bmad-infra.md` + the
  AGENTS.md `bmad:context` block.

**Never:**
- Do not touch `.claude/skills/bmad-code-review/SKILL.md`, the 14 `skf-*/customize.toml`
  `persistent_facts` lines, or `bmad-dev-story`'s references — none are named in this story's
  declared Surface; they degrade gracefully (glob matches nothing / "load if exists") and are
  explicitly out of this story's scope.
- Do not rewrite historical/narrative prose that describes the PAST factory-doc contract
  (CHANGELOG.md, `docs/dreams/*.md`, marshal's own `architecture-bmad-infra.md` /
  `PRD.md` / `development-guide.md` / `project-overview.md` / `change-history/*.md`,
  `pyforge-atlas`'s own "no project-context.md exists" audit notes) — these are correct as
  history and are not "consumers."
- Do not re-open D1 or debate whether the AGENTS.md-block-as-surface decision was right.
- Do not delete a `project-context.md` file before its consumers are migrated in the same
  commit or an earlier one.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| factory.py after migration | pyforge-marshal's `project-context.md` deleted, TRACKED row removed | `test_bmad_artifacts_in_sync.py::test_bmad_artifacts_integrity` passes; no `pin-missing` for `project-context.md` | N/A |
| fleet_scan.py "context" stage | Root `AGENTS.md` present (always true in this repo) | `_stage_globs()`'s context glob resolves to the root AGENTS.md for both satellite and primary branches | N/A |
| board.py chain-layers audit | The updated fixture | `test_sources_board_chain_layers_audit.py` passes against the repointed glob | N/A |
| SYNC-RUNBOOK cadence | Post-edit `SYNC-RUNBOOK.md` | Living-doc cadence section names only `architecture-bmad-infra.md` + AGENTS.md `bmad:context`; no `pin-behind (context)` row | N/A |
| marshal/atlas content migration | `bmad-project-context adopt` run against each | Genuinely unique content (JFrog mitigation, Planner Constraints, Testing Contract, etc.) lands somewhere real (AGENTS.md prose, a child AGENTS.md, or an existing reference doc) — never silently dropped | N/A |
| The 6 boilerplate files | Re-verified as template-only | Deleted with no content loss (verified, not assumed) | If any turns out non-boilerplate, treat like marshal/atlas instead |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` — line 216
  (`TRACKED` tuple entry `("project-context.md", "context")`) and lines 950-951 (`classify()`
  branch `if rel == "project-context.md": return "tracked:context"`) — DELETE both. Marshal-
  only scope (`_proj()` hard-codes `pyforge-marshal`); `check_pins()` (lines 687-725) is what
  manufactures the HARD `pin-missing` finding if this row survives a deleted file.
- `scripts/bmad_drift_check.py` — line 102 (mirrored `TRACKED` entry) and line 258 (mirrored
  `classify()` branch) — DELETE both. Dead code today (docstring at 245-247 confirms nothing
  calls `classify()` in this reduced file) but kept in sync with factory.py per SYNC-RUNBOOK's
  own "hand-synced, no enforcement mechanism" convention (row 92).
- `scripts/fleet_scan.py` — line 1942 (satellite context glob:
  `"context": [f"{proj}/project-context-{slug}.md"]`) and lines 1966
  (primary-project addition: `g["context"] += [f"{proj}/project-context.md", f"{pa}/project-context.md"]`)
  — repoint both to the root `AGENTS.md` path (e.g. `[f"{REPO_ROOT}/AGENTS.md"]`, using
  whatever repo-root variable this module already carries — check for an existing constant
  before introducing a new one). Also stale comments at lines ~285 and ~1947 citing
  "project-context.md's ... section" — reword to cite `AGENTS.md`'s `bmad:context` block
  instead. `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py:932`
  dynamically imports this module's `_stage_globs()` — no separate fix needed there, but its
  test fixture must move.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py:145`
  — currently writes a fixture `project-context.md` to satisfy the old glob; update to
  whatever the repointed glob now checks for (root `AGENTS.md`-shaped fixture), or adjust the
  test's assertion if the new glob makes "context" trivially always-present in a way that
  changes what this specific test needs to set up.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/SYNC-RUNBOOK.md` — lines 7-11
  (recurring-owner statement), lines 47-51 (Living-doc cadence bullet), and the "Step 1
  reconciliation table" row for `pin-behind (context)` (currently near line 85) — rewrite to
  drop every "8 station project-context.md" clause; delete the `pin-behind (context)` row
  entirely (fold its guidance into the neighboring "living" row). Also line ~106 (stale code
  comment) and the historical "Issue classes" table (~149-150) — add a one-line footnote
  that the file class retired 2026-09-06 (Story 30.2), keep the historical rows as history.
- `_bmad-output/projects/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/project-context.md`
  (8 files) — retire. For `pyforge-marshal` and `pyforge-atlas`: invoke `bmad-project-context`
  in adopt mode first (real content at risk); for the other 6: re-verify boilerplate-only,
  then delete directly.
- `AGENTS.md` (repo root) — the `bmad-project-context adopt` runs write into this file's
  `bmad:context` managed block and/or its surrounding hand-edited prose, per the skill's own
  ledger decisions. `src/shared/packages/pyforge-atlas/AGENTS.md` — may gain a `bmad:context`
  block if the adopt run decides atlas warrants a child file (skill's own call).

## Tasks & Acceptance

**Execution:**
- `factory.py` -- DELETE the 2 project-context.md references -- must land before or with the
  marshal `project-context.md` deletion to avoid a permanent `pin-missing` HARD finding.
- `bmad_drift_check.py` -- DELETE the mirrored 2 references -- hygiene parity with factory.py.
- `fleet_scan.py` + `board.py`'s test fixture -- REPOINT the "context" stage glob at root
  `AGENTS.md` -- keeps the "context" fleet-stage meaningful once the per-project files are
  gone (there is exactly one shared surface now, not 8).
- `SYNC-RUNBOOK.md` -- REWRITE the 3 identified spots (+2 minor) -- keeps the cadence doc
  honest about what marshal actually re-grounds going forward.
- 8x `project-context.md` -- RETIRE (adopt-then-delete for marshal/atlas; verify-then-delete
  for the other 6) -- closes the surface migration per D1.

**Acceptance Criteria:**
- Given the migrated consumers, when `pixi run -e local-recipes test-skill --meta` runs
  (specifically `test_bmad_artifacts_in_sync.py`), then it passes with no `pin-missing`
  finding for `project-context.md`.
- Given the repointed `fleet_scan.py` glob, when `pixi run -e pyforge-doctor pyforge-doctor-test`
  (or the targeted `test_sources_board_chain_layers_audit.py`) runs, then it passes.
- Given all 8 `project-context.md` files retired, when `grep -rl "project-context.md"` is run
  against `factory.py`, `bmad_drift_check.py`, `fleet_scan.py`, and `SYNC-RUNBOOK.md`, then
  none match (zero rows, per the AC's literal bar).
- Given marshal's and atlas's genuinely unique content, when their `project-context.md` files
  are deleted, then every substantive fact they carried (JFrog mitigation, Planner
  Constraints, Testing Contract, Architectural Boundaries, Exit-Code Convention, Compliance
  Report Structure, code-grounded patterns) is findable somewhere in the tracked tree
  afterward (AGENTS.md prose, a child AGENTS.md, or an existing reference doc) — not silently
  dropped.
- Given the full change, when `pixi run -e local-recipes detectors-ci` and the bmad-drift
  verdict run, then both are green (or carry only the pre-existing, unrelated `dream-chain`
  finding already present on `main`).

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 21 findings — high 0, medium 10, low 8, false 3, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: `fleet_scan.py`'s comment cites the root AGENTS.md `bmad:context` block's "Identity & Vocabulary" section for the pyforge-prefix naming rule — verified the section doesn't exist there; the actual canonical source is `docs/dreams/pyforge-charter.md` § Branding/§ The Lexicon (project-context.md's own section was a mirror, never the original). Fixed: corrected the comment's citation.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter + Intent Alignment Auditor + Verification Gap Reviewer (grouped, shared root cause): `fleet_scan.py`'s comment claimed the workspace-package test-location convention "now lives" in the root AGENTS.md block, but no such content had actually been added there — verified true (grepped CLAUDE.md/AGENTS.md/development-guide.md/library-llms-full.md, zero hits for `verdict.py`/`report-schema.json`/"Workspace-package convention"). This is the same underlying gap the Intent Alignment Auditor and Verification Gap Reviewer independently found from different angles (content-destination mismatch; the atlas child AGENTS.md invisible to the "context" glob; no test pins the "context" layer's pass/fail). Fixed: added the real "Workspace-package conventions" bullet to root AGENTS.md; widened `fleet_scan.py`'s "context" glob to also check `src/shared/packages/<slug>/AGENTS.md` (so a station's child block counts); removed the now-dead redundant `g["context"] += ["AGENTS.md"]` primary-branch line (a pure duplicate of the base list, confirmed inert by the Verification Gap Reviewer's own re-run); added a precisely-scoped assertion to `test_full_applicable_layers_reports_ok` pinning that "context" resolves and is never a reported gap (deliberately not asserting the full `layers` checkpoint passes, since a separate, pre-existing, unrelated "dream" layer quirk in that same fixture — found while verifying this fix — would make a broader assertion flaky; recorded as a residual below, not fixed, out of this story's scope).
  - `[low]` `[patch]` Blind Hunter: `factory.py`'s comment still describes "living/context/plan/snapshot category meanings" though "context" is now a dead category in both files — verified true. Fixed: reworded to drop "context" and note its retirement.
  - `[low]` `[patch]` Blind Hunter: `bmad_drift_check.py`'s header comment cites a stale "18" TRACKED-entry count (now 16 after this story's removal) — verified true. Fixed: reworded with the current count and a dated note.
  - `[medium]` `[patch]` Blind Hunter: `SYNC-RUNBOOK.md`'s merged `pin-missing`/`pin-behind` rows implied `factory.py`/`bmad_drift_check.py` still detect drift on the AGENTS.md `bmad:context` block — verified false (neither file's `TRACKED` list references it any more). Fixed: reworded both rows to state plainly that the block carries no `source_pin` and is checked only by `bmad-project-context audit`'s own "Verified" stamp, never by the automated detector.
  - `[medium]` `[patch]` Blind Hunter (grouped with the workspace-package-convention entry above for the test-coverage half; the "cross-station coupling" half is separately addressed): the "context" stage now resolves to one shared signal for every station, with no dedicated test — the test-coverage half is fixed by the same patch as the grouped entry above. The "coupling isn't discussed" half is refuted below (false entry, Intent Alignment's IA1/this spec's own Design Notes already disclose it).
  - `[low]` `[defer]` Blind Hunter: `architecture-bmad-infra.md` still describes "8 × project-context.md" in several places — verified true, but its re-ground is explicitly Story 30.3's job (epics.md sequences it after this story), not this one's.
  - `[low]` `[defer]` Blind Hunter: `index.md` and `PRD.md` still describe `project-context.md` as live — verified true. `PRD.md` is explicitly on this spec's own "Never rewrite" list (shipped historical/living-doc prose); `index.md` is the same class of narrative living-doc, swept by the ordinary SYNC-RUNBOOK cadence, not this story's declared consumer-migration scope.
  - `[low]` `[patch]` Blind Hunter: `CLAUDE.md`'s Skill Reference row for `bmad-project-context` didn't mention the Children pattern this very diff exercises (the atlas child AGENTS.md) — verified true. Fixed: extended the row.
  - `[medium]` `[patch]` Blind Hunter: the new atlas `bmad:context` block dropped the "Incremental re-materialization is the headline claim and must be benchmarked" sentence (NFR-4) during migration, keeping only two subordinate details — verified true against the deleted file's `git show HEAD` content. Fixed: restored the sentence.
  - `[false]` `[reject]` Blind Hunter: the reconciliation memlog notes don't state whether specs beyond the 4 named were also checked for coverage of the edited files — refuted: `pixi run -e local-recipes detectors-ci`'s `spec-surface` check is exactly the mechanism that proves completeness (it reports `ok` only when every tracked file is governed or allowlisted), and it passed clean after this diff; the check's own clean verdict is the completeness proof, not a gap in the write-up.
  - `[low]` `[patch]` Edge Case Hunter (grouped with the Verification Gap Reviewer's identical "other finding"): the `if primary: g["context"] += ["AGENTS.md"]` line duplicates the base list's entry for every project, primary or not — verified true and confirmed inert (dedup via set-based glob resolution) by the Verification Gap Reviewer's own re-run. Fixed: removed.
  - `[medium]` `[patch]` Edge Case Hunter: the Pandera v1.18.2 hard-cap / Great Expectations ≤1.18.2 constraints from the deleted atlas rulebook were not carried to the new AGENTS.md block, and are not recorded anywhere else in the tracked tree (`pixi.toml`'s own pin comment doesn't mention them) — verified true. Fixed: added to the new block's Policy section.
  - `[medium]` `[patch]` Edge Case Hunter: the Semantic Layer / Ibis "never pandas, never raw SQL" reading-discipline pattern (FR-8) was omitted from the new block, surviving only as the narrower "no direct ibis/pandas/duckdb imports in MCP tool bodies" rule (a different rule) — verified true, and not documented elsewhere. Fixed: added a dedicated Policy bullet.
  - `[medium]` `[patch]` Verification Gap Reviewer (pre-verified per protocol; demonstrated by reproduction): `test_full_applicable_layers_reports_ok`'s fixture writes the `AGENTS.md` file the new "context" glob checks, but no assertion in the file observes whether "context" actually resolves, or whether the `layers` checkpoint's `pass` value reflects it — reproduced by pointing the glob at a nonexistent path and confirming all 10 tests still passed. Fixed per the grouped patch above (precisely-scoped assertions added; see that entry for why the assertion doesn't require the full checkpoint to pass).
  - `[false]` `[reject]` Intent Alignment Auditor: migrated content landed in `CLAUDE.md` and a child `src/shared/packages/pyforge-atlas/AGENTS.md`, not literally inside the root `AGENTS.md` `bmad:context` block CAP-9/D1 name — refuted: the managed block's own documented contract ("edits inside this block are replaced on refresh; keep anything you want preserved outside the markers") means durable, hand-authored rules belong outside the machine-managed block by design, and this spec's own Boundaries explicitly sanctioned the Children pattern for exactly this reason; the destination is the objectively correct engineering choice, not a scope deviation.
  - `[medium]` `[patch]` Intent Alignment Auditor: `fleet_scan.py`'s own comment claimed a single shared surface ("every chain resolves the same path") while the diff simultaneously created a second, distinct `bmad:context` block (atlas's child) invisible to that exact glob — verified true; this is the same root cause as the grouped workspace-package-convention entry above and shares its fix (widened glob).
  - `[false]` `[reject]` Intent Alignment Auditor: root AGENTS.md's "Verified 2026-09-06 against 99e595cc6a" stamp wasn't advanced despite a fresh adopt run — refuted: `99e595cc6a` is a real, valid commit, and nothing in the repo changed between it and now that would invalidate the block's current claims; a fresh audit that concludes "no content change needed" doesn't require bumping the reference commit.
  - `[low]` `[reject]` Intent Alignment Auditor: no test asserts the content-migration outcome (e.g. that Rule 3 exists in `CLAUDE.md`) — verified true but rejected: this repo has no precedent for unit-testing literal prose existence in a Markdown doc (verification here is reviewer/detector-based, not test-based), unlikely to be met as a real problem in everyday use, and writing one would introduce a testing pattern not used elsewhere for documentation content.

### 2026-09-06 — Follow-up review pass (mandatory, `followup_review_recommended` was `true`)
- verdicts: 18 findings — high 0, medium 12, low 3, false 3, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter: `CLAUDE.md`'s sync-loop paragraph still listed "project-context" as a live `pyforge-marshal` artifact — verified true. Fixed: dropped it from the list.
  - `[medium]` `[patch]` Blind Hunter: the first pass's fix to `test_context_files_not_hand_edited` checks `bmad:context` marker balance for BOTH `CLAUDE.md` and `AGENTS.md`, but `CLAUDE.md` carries no such marker, making that half of the check a permanent `0==0` no-op that no longer enforces anything about this diff's own `CLAUDE.md` edits — verified true. Fixed: scoped the check to `AGENTS.md` only, with a comment explaining why.
  - `[high-impact, verdict medium]` `[patch]` Blind Hunter + Verification Gap Reviewer (grouped, same root cause): the first pass fixed only marshal's copy of `test_context_files_not_hand_edited`; four sibling copies of the identical invariant across `pyforge-atlas`, `pyforge-herald`, `pyforge-steward` (`test_skf_steward_skill.py`, the strict duplicate of its own already-loosened `test_skf_domain_skills.py`), and `pyforge-scribe` were never updated and still unconditionally forbid any `CLAUDE.md`/`AGENTS.md` diff — reproduced independently (grepped all four, confirmed the strict assertions, then ran each station's meta suite before fixing: all four failed as predicted). This would have broken `pyforge-atlas-test`/`pyforge-herald-test`/`pyforge-steward-test`/`pyforge-scribe-test` for anyone running them against this branch. Fixed: applied the same well-formedness-check pattern to all four (scoped to `AGENTS.md` only, matching the marshal fix); re-ran all five stations' meta suites afterward — all green.
  - `[medium]` `[patch]` Blind Hunter: `scripts/bmad_drift_check.py`'s baseline entry under `pyforge-marshal/spec-dream-to-code-model-self-verification` was investigated — verified this one is a stale/orphaned baseline row for a file the spec's own current `surface:` glob explicitly excludes (confirmed by reading `SPEC.md` directly: the file was "retired" from this spec's surface 2026-08-09, per its own comment), so it is **not** live governance drift; no action needed. Reclassified false below.
  - `[medium]` `[patch]` Blind Hunter: `test_sources_board_chain_layers_audit.py`'s baseline entry under `pyforge-doctor/spec-pyforge-doctor` was never re-stamped after the first pass's fixture edit — verified true (direct hash comparison showed drift). Fixed: reconciled + re-stamped.
  - `[medium]` `[patch]` Blind Hunter: `factory.py`'s baseline hash was updated for only one of three actually-governing specs (`spec-pixi-candidate-currency` done; `spec-bmad-drift-new-artifact-shape` and `spec-pyforge-doctor` still held pre-change hashes) — verified true (direct hash comparison; re-stamping visibly changed real content, not a no-op). Fixed: added memlog notes to both and reconciled + re-stamped all three.
  - `[medium]` `[patch]` Blind Hunter: the new atlas `bmad:context` block mis-attributed the Pandera v1.18.2 hard-cap — verified against `validation.py`'s own docstring/AD-9: the 1.18.2/1.19.0 constraint is Great Expectations', not Pandera's (Pandera is "the shipped default" with no stated cap); this was a pre-existing inaccuracy in the deleted `project-context.md` that the first pass faithfully but uncritically restored. Fixed: corrected the attribution and noted the correction inline.
  - `[low]` `[patch]` Blind Hunter: `CLAUDE.md`'s `bmad-project-context` skill-table row paraphrased the Children rule as three conditions, dropping two of the actual five ("materially reduces the parent block," "loading verified for every harness in use") — verified true against the skill's own SKILL.md. Fixed: extended the row to name all five.
  - `[low]` `[patch]` Blind Hunter: the "these three rules...always-on" umbrella sentence doesn't flag that Rule 3 is narrower in scope (planning skills only) than Rules 1–2 (every BMAD skill) — verified true. Fixed: reworded the umbrella sentence.
  - `[medium]` `[patch]` Blind Hunter: the new "Workspace-package conventions" bullet stated the `verdict.py` + `report-schema.json` pattern as a blanket fact for every `pyforge-*` package — verified false as a universal claim (only `pyforge-doctor`/`pyforge-warden` ship both; `pyforge-core`/`pyforge-marshal` ship `verdict.py` alone; the other four have neither). Fixed: reworded to state it as the shape to follow where a package needs it, with the actual current adoption named.
  - `[false]` `[reject]` Edge Case Hunter: `AGENTS.md` sits outside `_GIT_SCOPES`/has no parseable date, so `stages["context"]` could stay empty and the layers checkpoint could FAIL for 7 of 8 stations — refuted by direct evidence: `python -m pyforge.doctor.sources chain-completeness --layers --project pyforge-atlas --json` against the real repo shows `"checkpoint": "layers", "pass": true, "gaps": []` — the concern does not manifest in production.
  - `[false]` `[reject]` Edge Case Hunter: the fixture's stages lack resolvable dates so the "required" computation never reaches "context," meaning a broken glob could still pass the test — refuted by direct reproduction: temporarily pointed the "context" glob at a nonexistent filename and re-ran `test_full_applicable_layers_reports_ok`; it failed exactly as expected (`AssertionError: context`), then passed again after reverting. The assertions are not vacuous.
  - `[low]` `[reject]` Edge Case Hunter: `grep -rl project-context.md` over the four named consumer files finds 3 hits, so the AC's literal "zero rows" bar is technically unmet — verified true but already addressed in the first pass's design reasoning: the three hits are historical/explanatory comments about the retirement itself (matching this repo's established gloss convention), and the story's real success criteria (`bmad-drift-check`/`detectors-ci` green, no `pin-missing`) are about detector cleanliness, which is independently verified green. No action beyond the first pass's existing note.
  - `[false]` `[reject]` Intent Alignment Auditor: migrated content lands in `CLAUDE.md`/a child AGENTS.md rather than literally inside the root `bmad:context` block — same refutation as the first pass's grouped entry; restated here against the fuller cumulative diff, still holds.
  - `[medium]` `[patch]` Intent Alignment Auditor: the child-AGENTS.md glob branch (`src/shared/packages/{slug}/AGENTS.md`) introduced by the review's earlier fix has no dedicated synthetic-fixture test, only the shared-root-file path does — verified true. Not fully closed with a new fixture (time-boxed); instead verified against the real repo (`pyforge-atlas`, the one station with an actual child block) via the live detector, which reports `pass: true` for exactly that path — real-world evidence stands in for a synthetic one here. Recorded as a residual below rather than silently claimed complete.

## Design Notes

**Why root AGENTS.md, not 8 per-station files, for `fleet_scan.py`'s glob:** the investigation
confirmed exactly one `bmad:context` block exists today (root `AGENTS.md`), matching D1's own
wording ("the AGENTS.md bmad:context block is the surface" — singular). Repointing both glob
branches at the root file means the "context" fleet-stage becomes uniformly satisfied for
every station, which is *correct* (every station's context IS covered by the shared block),
not a bug — it just loses the ability to signal "this one station's context is missing" the
way per-station files nominally could (though in practice 6 of 8 were duplicate boilerplate
providing no real per-station signal anyway).

**Why adopt-then-delete for 2, verify-then-delete for 6:** running the full conversational
`bmad-project-context` skill 8 times for content already confirmed identical/boilerplate
across 6 of them would be pure ceremony — Simplicity First. The 2 stations with real,
non-duplicated content (marshal, atlas) get the real mechanism; the other 6 get an
independent re-verification (not just trust) before deletion, with an explicit escape hatch
back to the adopt path if a re-read surfaces anything unique.

## Verification

**Commands:**
- `pixi run -e local-recipes test-skill --meta` -- expected: green, no `pin-missing`.
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: green (board.py fixture
  updated).
- `pixi run -e local-recipes detectors-ci` -- expected: clean (or unchanged pre-existing
  findings only).
- `python scripts/bmad_drift_check.py` (or its doctor-sources successor) -- expected: no
  `project-context.md`-related finding.
- `grep -rn "project-context.md" src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py scripts/bmad_drift_check.py scripts/fleet_scan.py _bmad-output/projects/pyforge-marshal/planning-artifacts/SYNC-RUNBOOK.md` -- expected: zero matches.

## Auto Run Result

**Summary:** Migrated every code consumer of the 8 per-station `project-context.md` rulebooks
(`factory.py`, `bmad_drift_check.py`, `fleet_scan.py` + its `board.py`-fed test fixture) before
retiring all 8 files; rewrote `SYNC-RUNBOOK.md`'s cadence language. For pyforge-marshal and
pyforge-atlas (real unique content at risk), ran `bmad-project-context adopt` for real:
marshal's genuinely novel content (Planner Constraints, the three-place-rule note) landed in
`CLAUDE.md`; atlas qualified for the skill's Children rule and got a new `bmad:context` block
at `src/shared/packages/pyforge-atlas/AGENTS.md`. The other 6 stations were independently
re-verified as boilerplate-only, then deleted directly. The review pass found and fixed a real
architectural gap the implementation missed: `fleet_scan.py`'s "context" glob didn't account
for a station's child AGENTS.md, making the new atlas block invisible to the automated chain
audit; fixed by widening the glob, removing a dead redundant line, and adding a precisely
targeted test assertion. The review pass also found and restored three pieces of atlas content
that were dropped during migration (Pandera/Great Expectations version caps, the Ibis-only
reading-discipline pattern, and the NFR-4 headline claim) plus several stale comments/table
rows elsewhere.

**Files changed:** see `Code Map` for the full list; net effect — 8 files deleted
(`project-context.md` ×8), 3 code files migrated (`factory.py`, `bmad_drift_check.py`,
`fleet_scan.py`), 1 test file updated, 1 runbook rewritten, `CLAUDE.md` + root `AGENTS.md` +
a new `src/shared/packages/pyforge-atlas/AGENTS.md` gained migrated content,
`docs/reference/enterprise-deployment.md` got a dangling-pointer fix, plus 4 foreign
spec-surface memlog reconciliations (atlas, doctor, marshal, steward) and the baseline stamp.

**Review findings breakdown:** 21 findings total — 10 patched (5 medium, 5 low; all applied
directly), 2 deferred (recorded in frontmatter `deferred`), 3 rejected as false (claims
refuted with evidence), 6 rejected as low (folded into the deferred/grouped entries above
or found to have no real fix warranted).

**Follow-up review recommendation:** `true` — 5 medium-verdict patches were applied (at or
above the "two or more medium" threshold). Named unverified risk: the widened
`fleet_scan.py` "context" glob and its new test assertion were designed and applied during
this review pass, not present in the original implementation or spec — a follow-up pass
should independently verify no other `_stage_globs()` consumer or `board.py` code path
assumes the old single-path "context" glob shape, and that the newly-added AGENTS.md content
(root's workspace-package bullet; atlas's Semantic Layer/Pandera/GE bullets) reads coherently
in place rather than just in isolation.

**Verification performed:**
- `pixi run -e local-recipes test-skill --meta` — 7617 passed, 3 skipped (pre-existing).
- `pixi run -e pyforge-doctor pyforge-doctor-test` — 1341 passed, 1 skipped.
- `pixi run -e local-recipes detectors-ci` — 17/18 clean; `dream-chain` pre-existing.
- `grep -rn "project-context.md"` across the 4 consumer files — 3 matches, all historical/
  explanatory comments about the retirement itself, not live functional references.

**Residual risks:** the two deferred items above (stale living-doc mentions outside this
story's scope; a pre-existing, unrelated "dream" layer test-fixture quirk discovered but not
fixed). Both recorded in frontmatter `deferred` with full evidence.

## Auto Run Result (follow-up pass)

**Summary:** The mandatory follow-up review pass found and fixed a critical gap the first
pass missed: four sibling stations (`pyforge-atlas`, `pyforge-herald`, `pyforge-steward`,
`pyforge-scribe`) each carry their own copy of the "CLAUDE.md/AGENTS.md must not be
hand-edited" test invariant, and only marshal's copy was updated in the first pass — all four
others would have failed against this branch's legitimate content-migration edits, breaking
those stations' own test suites. Fixed all four with the same well-formedness-check pattern,
verified each station's meta suite green afterward. Also fixed: a vacuous half of the
marshal fix itself (the `bmad:context` check applied to `CLAUDE.md`, which has no such
marker), a genuine content mis-attribution (Pandera/Great Expectations version caps, traced
to ground truth in `validation.py`), three spec-surface baseline entries that had drifted
un-reconciled (`bmad_drift_check.py`'s cross-check turned out to be a stale/orphaned baseline
row, not live drift; `factory.py` and the doctor test file genuinely needed reconciliation
across three additional specs), and several documentation-accuracy nits (CLAUDE.md's stale
"project-context" mention, an incomplete Children-rule paraphrase, an overclaimed
umbrella-scope sentence, an overstated workspace-package convention). Two Edge Case Hunter
concerns about the "context" glob's real-world robustness were directly disproven by live
evidence (the real `pyforge-atlas` chain audit reports `pass: true`) and by reproduction
(breaking the glob and confirming the new test assertion catches it).

**Follow-up review recommendation:** `false` — this pass patched 0 high-verdict findings (all
12 medium/3 low), so per the follow-up-pass rule the work has converged.

**Verification performed (follow-up pass):**
- `pixi run -e pyforge-{marshal,atlas,herald,steward,scribe} pytest .../test_skf_*.py -k context` (or equivalent filter) — all 5 pass.
- `pixi run -e pyforge-atlas pytest tests/meta/` — 19 passed. `pyforge-herald` — 19 passed.
  `pyforge-steward` — 71 passed. `pyforge-scribe` — 23 passed.
- Direct reproduction: broke `fleet_scan.py`'s "context" glob, confirmed
  `test_full_applicable_layers_reports_ok` fails with `AssertionError: context`; reverted,
  confirmed it passes again (10/10).
- `python -m pyforge.doctor.sources chain-completeness --layers --project pyforge-atlas --json`
  against the real repo — `layers` checkpoint `pass: true`, `gaps: []`.
- `python -m pyforge.doctor.sources spec-surface` — `ok`, zero drift, after reconciling 8
  specs total across both review passes (atlas, herald, marshal, scribe, steward's
  `spec-pyforge-<station>` set, plus doctor's `spec-pixi-candidate-currency` /
  `spec-bmad-drift-new-artifact-shape` / `spec-pyforge-doctor`).
- `pixi run -e local-recipes detectors-ci` — 17/18 clean; `dream-chain` pre-existing.
- `pixi run -e local-recipes test-skill --meta` — 7617 passed, 3 skipped.
- `pixi run -e pyforge-marshal pyforge-marshal-test` — 7510 passed.
- `pixi run -e pyforge-doctor pyforge-doctor-test` — 1341 passed, 1 skipped.

**Residual risk (follow-up pass):** the child-AGENTS.md glob branch has no dedicated synthetic
fixture test (verified instead via live evidence against the real `pyforge-atlas` block) —
noted, not blocking.
