---
title: "27.2: CFE, its failure catalog and the closed rebuild campaign's records close their open deferrals"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py
  - scripts/failure_catalog_check.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 25 open rows (8 medium, 17 low) sit on conda-forge-expert, the failure catalog it generates and the script that checks it, the db-gpt recipe, and the records of the CFE-rebuild campaign Story 15.1 closed. In CFE, the failure catalog's symptom signatures carry tokens that cannot diagnose, its fenced-block and enforced-by heuristics are narrow, and the YAML has no schema version. Its check matches one spelling of a check code and tells drift by a stderr string. The commands cheatsheet misses `test-ci`, strip-on-push was never re-checked against a real published feedstock, the SM-4 free-inheritance record waits on a re-run, and marshal's sync baseline lags CFE's version. In the records, the resume header points a session at one slice, the slice map and `spec-12-5` carry stale or unsourced text, and the rebuild Spec's ruling cites an unqualified CAP-19. Seven rows name surfaces Story 15.1 retired or a fix already on main.

**Approach:** Go through `conda-forge-expert` (Rule 1). Fix each CFE row in code with a test that fails without it, and land every CFE-surface edit in one commit whose subject starts `retro(cfe):` and whose CFE `CHANGELOG.md` gets a semver entry (AD-15, FR-47). Correct the campaign records in place with dated notes; the rebuild Spec's `SPEC.md` changes only through its `.memlog.md` and a `bmad-spec` re-derive. Close a row whose surface Story 15.1 retired, or whose fix is already on main, on the cited line that records it.

Ledger key: `27-2-cfe-its-failure-catalog-and-the-closed-rebuild-campaign-s-records-close-their-open-deferrals`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-14 (the slice map), CAP-17 (campaign state), CAP-19 (per-recipe internal metadata), CAP-21 (the generated catalog), CAP-22 (the lint and drift gate), CAP-23 (recipe lifecycle machinery) and CAP-34 (CFE's tests give the same verdict in any environment): the capabilities that shipped each behaviour; a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the regenerated failure catalog When its signatures are read Then no row's signature is a single common word or a whole sentence, no token is shared by more than the set number of rows, and G98's signature is no longer `["fails"]`
- Given a Symptom paragraph with no trailing colon followed by a fenced block When the generator runs Then the block's text joins the signature; given a near-miss enforced-by sentence Then stderr warns
- Given `failure-catalog.yaml` When it is read Then it carries `schema_version: 1`, and the check refuses a missing or unknown version
- Given a check code written `code = "X"` or `"code": "X"` When the pointers lint runs Then the pointer resolves; given the generator failing for a reason other than drift When `check_drift` runs Then it reports a broken generator by the generator's exit code 2, without reading stderr text
- Given the commands cheatsheet When the CFE meta suite runs Then it reds a CFE test task the cheatsheet does not name, and `test-ci` is named
- Given a fixture copy of a real published feedstock recipe When the strip-on-push path runs on a local recipe carrying `cfe-*` keys Then none survives
- Given `mason recipe optimize` re-run When the SM-4 record in `epics.md` § Story 5.4 is read Then it carries the observed verb-level delta and its date
- Given this story's CFE bump When `_bmad-output/projects/pyforge-marshal/.sync-baseline.json` is re-stamped Then its `skill_version` equals the CFE version this story lands
- Given the campaign records When a session resumes Then `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`'s header says the campaign is closed; and `slice-map.md`, `spec-12-5` and the rebuild Spec carry the corrections DW-12-6-2, DW-12-4-1 and DW-12-5-1 to DW-12-5-5 name, with dated notes and the ruling's own words kept
- Given `DW-12-1-2`, `DW-12-3-2`, `DW-12-6-3`, `DW-12-6-4`, `DW-12-7-1`, `DW-12-7-2`, `DW-13-2-3` When this story closes them Then each `verified:` line cites the live line that records the retirement or the fix
- Given this story lands When its CFE-surface commit is read Then its subject starts `retro(cfe):`, it moves `.claude/skills/conda-forge-expert/CHANGELOG.md` with a semver entry and the version carriers, and it touches no `src/shared/packages/pyforge-mason/` path; CFE's own suite (`test-ci`) stays green
- Given this story lands When its deferred-work rows are read Then each of `DW-7-1-1`, `DW-7-1-2`, `DW-7-1-3`, `DW-7-1-4`, `DW-7-2-1`, `DW-7-2-2`, `DW-12-2-3`, `DW-17-2-1`, `DW-5-4-1`, `DW-15-1-1`, `DW-13-2-3`, `DW-12-1-2`, `DW-12-6-1`, `DW-12-6-4`, `DW-12-6-3`, `DW-12-6-2`, `DW-12-4-1`, `DW-12-5-1`, `DW-12-5-2`, `DW-12-5-3`, `DW-12-5-4`, `DW-12-5-5`, `DW-12-7-1`, `DW-12-7-2`, `DW-12-3-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed
- Given this story's changes When `pixi run --frozen -e pyforge-mason pyforge-mason-test` runs Then it passes

## Boundaries & Constraints

**Always:** Invoke `conda-forge-expert` before any CFE edit (Rule 1); where this spec conflicts with the skill, the skill wins and this spec records the deviation. Land every CFE-surface edit (`.claude/skills/conda-forge-expert/**`) in one commit whose subject starts `retro(cfe):` and which moves the CFE `CHANGELOG.md` with a semver entry and its version carriers (`SKILL.md`, `config/skill-config.yaml`, `MANIFEST.yaml`); four station guards red a CFE touch without both (AD-15, FR-47). `scripts/failure_catalog_check.py` and its test may ride in that commit; the campaign records and ledger edits go in a separate commit, and no commit of this story touches Mason's package. Change the rebuild Spec's `SPEC.md` only through its `.memlog.md` (`uv run _bmad/scripts/memlog.py append`) and a `bmad-spec` re-derive; if the pre-shell hook refuses the render, stop and ask the operator. Keep each operator ruling's own words: corrections are dated notes or bracketed readings. Name every governed path you change on the owning Spec's `.memlog.md` and on each co-governor `spec-surface` names (`spec-packaging-factory` governs the CFE surface), then run `python scripts/spec_surface_reconcile.py`.

**Never:** Never touch `src/shared/packages/pyforge-mason/**`: those rows are Story 27.1's, and no commit may touch both Mason's package and the CFE surface (`mason-cfe-surface-check`). Never push to a feedstock or open a feedstock, staged-recipes or upstream PR. Never re-open the CFE-rebuild campaign or restore a retired mirror. Never hand-edit a `SPEC.md`. Never close a row without a cited `verified:` line.

</intent-contract>

## Deferred-work rows this story closes (25: 8 medium, 17 low; deferral burn-down Phases 4 and 5)

Each line is the row, its severity, and the fix that closes it. Line numbers are as of main on 2026-10-03; re-read the
code before editing.

### The failure catalog: CFE's generator and the check script (6)

- `DW-7-1-1` (medium) — `.claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py` `_signature_tokens` drops tokens that cannot diagnose (a single common word, a whole sentence, a token shared by more than a set number of rows); `config/failure-catalog.yaml` regenerated; a test pins G98's `["fails"]` and one repeated token.
- `DW-7-1-2` (low) — `_symptom_paragraph` folds a fenced block that immediately follows the Symptom paragraph whether or not the prose ends in a colon; test.
- `DW-7-1-3` (low) — `extract_enforced_by` warns on stderr when a sentence nearly matches the declarative "The optimizer's **CODE** check" form (for example "checks"), so phrasing drift is told apart from "not yet enforced"; test.
- `DW-7-1-4` (low) — `config/failure-catalog.yaml` carries `schema_version: 1`, written by the generator and checked by `scripts/failure_catalog_check.py`; test.
- `DW-7-2-1` (low) — `scripts/failure_catalog_check.py` `_code_present` accepts `code = "X"` with spaces and a `"code": "X"` dict literal, sharing one pattern with the generator's registry match; test.
- `DW-7-2-2` (low) — `check_drift` tells drift from a broken generator by exit code: `failure_catalog_generator.py --check` exits 1 on drift and 2 on its own failure, and the check stops reading the "DRIFT DETECTED" string; test.

### Elsewhere on the CFE surface (4)

- `DW-12-2-3` (low) — `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` lists `test-ci` beside test / test-all / test-coverage / test-recipes, and a CFE meta-test reds a CFE test task the cheatsheet does not name.
- `DW-17-2-1` (medium) — Re-check the strip-on-push path (`SKILL.md` step 8b, G60, G62) against a real published feedstock recipe, by read-only fetch with no push: no `cfe-*` key survives; pin it with a test over a fixture copy of that recipe.
- `DW-5-4-1` (low) — CFE MINORs from efforts outside Mason's chain have landed since v8.82.0: re-run `mason recipe optimize` on a recipe and append the observed verb-level delta to the SM-4 record in `epics.md` § Story 5.4.
- `DW-15-1-1` (low) — `_bmad-output/projects/pyforge-marshal/.sync-baseline.json` reads `skill_version` 8.90.5 against CFE 8.91.3: re-stamp it with `python scripts/bmad_drift_check.py --write-baseline` after this story's CFE bump (AGENTS.md § Keeping the BMAD planning docs accurate).

### The db-gpt recipe (1)

- `DW-13-2-3` (medium) — `recipes/db-gpt/recipe.yaml:16` applies the onnxruntime-cap patch and `:309` declares `onnxruntime >=1.14.1` with no ceiling (steward 43.6's 3.14 solve is green): re-verify and close. The feedstock PR named at `:488` is an operator ask; this story opens none.

### The closed CFE-rebuild campaign's records (14)

- `DW-12-1-2` (medium) — Both compiled slices are `retired` (`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:547`, `:679`) and clause (a) does not gate `retired`: close on those lines. The guard still refuses a gated status whose equivalence is not green.
- `DW-12-6-1` (medium) — The HOW TO RESUME header (`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:11`) says the campaign is closed and that every slice's `next_action` is history, instead of sending a session to `current_focus` alone.
- `DW-12-6-4` (low) — Slice 1's `brief_path` is null since Story 15.1 retired the slice (`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:657`): close on that line.
- `DW-12-6-3` (low) — Slice 2's Tier-3 brief went with the retirement and its `brief_path` is null (`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:830`): close on that line.
- `DW-12-6-2` (low) — `slice-map.md` gains a dated correction: `test-skill.py` is an ad-hoc script outside Slice 2's canonical set, and `failure_catalog_generator.py` (added after the map) is named.
- `DW-12-4-1` (medium) — `spec-12-5`'s Code Map names the nested `campaign.re_scope_gate.pre_conditions.d_ownership_decision` field Story 12.4 landed, as a dated Spec Change Log entry.
- `DW-12-5-1` (low) — The operator ruling's "authored on and its stories carried by" gets a bracketed reading in `spec-12-5` and `campaign-state.yaml`, and the rebuild Spec's memlog records the reading for its `SPEC.md` copy; the ruling's own words stay.
- `DW-12-5-2` (low) — The ruling's "CAP-19" is qualified as `spec-pyforge-steward` CAP-19 in `spec-12-5` and, through the rebuild Spec's memlog and a `bmad-spec` re-derive, in its `SPEC.md`.
- `DW-12-5-3` (low) — The rebuild Spec's Open Questions item 1 and Non-goals §3 cross-reference each other (memlog entry, then a `bmad-spec` re-derive).
- `DW-12-5-4` (low) — `spec-12-5`'s Code Map (`:80`) describes the in-place annotation the story used instead of citing Story 5.4's resolution-record pattern.
- `DW-12-5-5` (low) — `spec-12-5`'s `context:` lists the sources the ruling's rationale rests on (steward's CAP-19 material, the Phase-T / Epic-13 claim).
- `DW-12-7-1` (medium) — The compiled `cfe-recipe-lifecycle` package is retired (absent from `.claude/skills/`; `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:679`), and the live CFE scripts resolve the repo root through `_paths.get_repo_root()`'s marker walk: close on those lines.
- `DW-12-7-2` (low) — The retired package's Design Notes went with it: close on `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:679`.
- `DW-12-3-2` (medium) — The compiled `cfe-recipe-generation` package and its `metadata.json` are retired (`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:547`): close on that line.

## Binding

Parent: `spec-pyforge-mason` CAP-14 (the slice map), CAP-17 (campaign state), CAP-19 (per-recipe internal metadata), CAP-21 (the generated catalog), CAP-22 (the lint and drift gate), CAP-23 (recipe lifecycle machinery) and CAP-34 (CFE's tests give the same verdict in any environment): the capabilities that shipped each behaviour.
Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-2-cfe-its-failure-catalog-and-the-closed-rebuild-campaign-s-records-close-their-open-deferrals`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 ruling of 2026-10-03 (open medium and low deferrals fixed where they sit; fewer, larger stories of at most about 30 rows, split by package area, the CFE-surface rows in their own story).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03: Operator ruling (2026-10-03): a row that only an independent follow-up review of an already-landed story can close (a DW-FRR "follow-up review still recommended" row, or a row asking for a follow-up review of a landed story) is not in the Phase 4+5 fix stories, because an implementation session can never close it; those reviews run later as separate per-station review batches. Removed from this story's scope: `DW-FRR-7-1`, `DW-FRR-7-2`, `DW-FRR-24-1`, `DW-FU-5-5`, `DW-FRR-12-5`, `DW-FRR-12-6` (6 low; the follow-up reviews of Stories 7.1, 7.2, 24.1, 5.5, 12.5 and 12.6), with the follow-up-review acceptance criterion and the "Follow-up reviews owed" list. The rows stay open in the deferred-work ledger. 31 rows (8 medium, 23 low) became 25 (8 medium, 17 low).

## Review Triage Log

- No review has run yet.
