---
title: "Mason's own env satisfies the CFE import floor"
type: 'fix'
created: '2026-09-10'
status: 'done'
baseline_revision: '57c001c9d7c8864ec235b871c8e3dc024845e414'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Only `truststore` and `conda-forge-metadata` are explicitly pinned in
      `[feature.pyforge-mason.dependencies]`; `requests` and `ruamel.yaml`
      (two of the other four `CFE_IMPORT_FLOOR` entries) rely on transitive
      resolution, so an unrelated future dependency drop could re-break the
      floor.
    evidence: |-
      Verified real: `pixi.toml`'s `[feature.pyforge-mason.dependencies]`
      declares `pyyaml` and (via the package's own `pyproject.toml`)
      `packaging`, but never `requests` or `ruamel.yaml` explicitly -- both
      are currently satisfied only as transitive pulls. Pre-existing (this
      predates Story 16.1, whose Problem statement scoped the fix to
      exactly the two entries `mason doctor` reported missing) and
      substantially mitigated: the new regression test
      (`test_real_environment_satisfies_the_cfe_import_floor`) asserts
      `cfe.probe_import_floor(...).missing == ()` across all six floor
      entries, so it would already catch this exact regression if it ever
      recurred.
    location: >-
      pixi.toml:469-479
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `mason doctor` reports `unavailable_verbs: ('recipe',)` and
`cfe_import_floor_missing: ('truststore', 'conda-forge-metadata')` when run in the `pyforge-mason`
pixi env, because `[feature.pyforge-mason.dependencies]` (`pixi.toml:281-283`/`:469-476`) declares
neither floor dependency while `cfe.py`'s `CFE_IMPORT_FLOOR` (six distribution-name -> import-name
pairs: `pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`, `conda-forge-metadata`)
requires both to be importable before the `recipe` verb family is reported available. This is one
of the twelve `done`-but-not-in-effect capabilities the 2026-09-09 fleet-readiness pass found
(steward Epic 49, C6, evidence row mason-B5): the code exists and is correct, but mason's own
environment cannot exercise it.

**Approach:** Add `truststore` and `conda-forge-metadata` to `[feature.pyforge-mason.dependencies]`
at floors matching what `cfe.py`'s `CFE_IMPORT_FLOOR` actually requires, re-solve the lock, and
regenerate `environment.yaml`. Add a regression test pinning the floor so a future dependency edit
that drops either package reds instead of silently re-disabling the verb family. Re-verify CAP-5's
graceful-degradation path still holds (a deliberately broken floor must still exit 0 with the verb
reported unavailable, never a hard failure).

## Boundaries & Constraints

**Always:**
- This is CFE-floor work — driven directly by `cfe.py`'s `CFE_IMPORT_FLOOR` — so the story runs
  through `conda-forge-expert` (CLAUDE.md Rule 1) and ends with the Rule-2 retro.
- Add dependency floors that actually match what `CFE_IMPORT_FLOOR` requires, not an arbitrary
  version.
- Regenerate `environment.yaml` after any `pixi.toml` dependency change (CLAUDE.md's ungated
  `environment.yaml` sync-check rule) — `pixi project export conda-environment -e build >
  environment.yaml`.
- Add a test that pins the floor so a future edit dropping `truststore` or `conda-forge-metadata`
  fails the suite rather than silently re-disabling `recipe`.
- Re-verify the CAP-5 degradation contract: a deliberately broken floor must still exit 0 with the
  verb reported unavailable, not a hard crash.

**Never:**
- Do not touch verbs or code paths unrelated to the import-floor probe — this is a dependency-floor
  fix, not a `recipe` feature change.
- Do not weaken or remove CAP-5's graceful-degradation behavior while fixing the floor gap.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Floor satisfied after fix | `truststore` + `conda-forge-metadata` added to `[feature.pyforge-mason.dependencies]`, lock re-solved | `pixi run -e pyforge-mason mason doctor` reports `cfe_import_floor_satisfied: True`, empty `cfe_import_floor_missing` | N/A |
| `recipe` verb becomes available | Same as above | `unavailable_verbs` no longer contains `"recipe"` | N/A |
| Regression pin | A future edit removes `truststore` or `conda-forge-metadata` from the env | The new pinning test fails | Test failure, not a silent doctor-report change |
| Degradation still holds | Floor deliberately broken (e.g. simulated missing import) | Process still exits 0; verb reported unavailable via `unavailable_verbs` | No hard failure/crash — CAP-5 contract preserved |
| `environment.yaml` sync | `pixi.toml` dependency table changes | `environment.yaml` regenerated to match | Sync check (ungated by `maintenance` label) reds if stale |

</intent-contract>

## Code Map

- `pixi.toml` — `[feature.pyforge-mason.dependencies]` (~line 469-476) gains `truststore` and
  `conda-forge-metadata` entries at floors matching `cfe.py`'s `CFE_IMPORT_FLOOR`.
- `environment.yaml` — regenerated via `pixi project export conda-environment -e build >
  environment.yaml` after the `pixi.toml` change.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` (read-only reference,
  `CFE_IMPORT_FLOOR` ~line 180-187) — the six-entry floor this fix must satisfy exactly; no code
  change expected here.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/doctor.py` (read-only reference,
  `unavailable_verbs`/`cfe_import_floor_satisfied`/`cfe_import_floor_missing` ~lines 130-183) —
  the report fields this fix must flip; no code change expected here.
- `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` — add the regression assertion
  pinning the floor (real-env probe, or a fixture-driven equivalent matching this file's existing
  conventions).
- `src/shared/packages/pyforge-mason/tests/**` — re-verify (and extend if needed) CAP-5's
  degradation-path coverage: a broken floor still exits 0 with `recipe` reported unavailable.

## Tasks & Acceptance

**Execution:**
- `[fix]` Add `truststore` and `conda-forge-metadata` to
  `[feature.pyforge-mason.dependencies]` in `pixi.toml`, at floors matching `CFE_IMPORT_FLOOR`.
- `[chore]` Re-solve the `pyforge-mason` lock and regenerate `environment.yaml`.
- `[fix]` Add a regression test in `src/shared/packages/pyforge-mason/tests/**` pinning the import
  floor so dropping either dependency fails the suite.
- `[fix]` Re-verify CAP-5's graceful-degradation path (deliberately broken floor still exits 0,
  verb reported unavailable) and add/extend coverage if the existing test does not already prove
  this post-fix.

**Acceptance Criteria:**
- Given `mason doctor` reports `unavailable_verbs: ('recipe',)` and `cfe_import_floor_missing:
  ('truststore', 'conda-forge-metadata')` in the `pyforge-mason` env.
- When `truststore` and `conda-forge-metadata` are added to `[feature.pyforge-mason.dependencies]`
  at floors matching what `cfe.py`'s `CFE_IMPORT_FLOOR` actually requires, the lock is re-solved
  and `environment.yaml` regenerated.
- Then `pixi run -e pyforge-mason mason doctor` reports `cfe_import_floor_satisfied: True`, an
  empty `cfe_import_floor_missing`, and no `recipe` entry in `unavailable_verbs`; a test pins the
  floor so a future dependency edit that drops either package reds instead of silently
  re-disabling the verb family; and CAP-5's degradation path is re-verified (a deliberately broken
  floor still exits 0 with the verb reported unavailable — the graceful-degradation contract must
  not regress into a hard failure).
- Rule 1/2: this is CFE-floor work — the change is driven by `cfe.py`'s import floor, so the story
  runs through `conda-forge-expert` and ends with the Rule-2 retro.

## Spec Change Log

- **Implemented as specced, no deviations.** Added `truststore = ">=0.10.4"` (mirroring
  `[feature.python.dependencies]`'s identical pin) and `conda-forge-metadata = ">=2026.9.5"`
  (mirroring `[feature.vuln-db.dependencies]`'s identical pin) to
  `[feature.pyforge-mason.dependencies]` in `pixi.toml`; re-solved with `pixi install -e
  pyforge-mason`; regenerated `environment.yaml` via `pixi project export conda-environment -e
  build`.
- Added `test_real_environment_satisfies_the_cfe_import_floor` to
  `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` — runs the real, unmocked
  `cfe.probe_import_floor(sys.executable)` probe against mason's own pixi env and asserts
  `.missing == ()`. This is the regression pin the acceptance criteria calls for.
- **CAP-5 degradation re-verified live**, not just via the existing mocked unit tests (which
  were unaffected by this fix and continued to pass throughout): `pixi run -e pyforge-mason
  mason doctor --cfe-python /usr/bin/python3` (a system interpreter genuinely missing the
  floor) still exits 0 and reports `unavailable_verbs: ('recipe',)` — no crash, no regression
  in the graceful-degradation contract.
- Live-verified the acceptance criteria's exact wording:
  `pixi run -e pyforge-mason mason doctor` now reports `cfe_import_floor_satisfied: True`, an
  empty `cfe_import_floor_missing`, and no `recipe` entry in `unavailable_verbs`.
- Rule 1/2 honored: invoked the `conda-forge-expert` skill before starting (this is CFE-floor
  work per `cfe.py`'s `CFE_IMPORT_FLOOR`), and closed with a Rule-2 retro — CFE skill v8.90.2
  → v8.90.3 (PATCH), CHANGELOG entry stating "no skill changes; verified existing guidance held"
  (the finding is entirely in mason's own environment configuration, not in any CFE
  script/gotcha/pattern).
- **Side effect, reconciled in the same pass**: the `pixi.toml` edit tripped
  `pyforge-marshal/spec-pyforge-core`'s spec-surface drift gate (that spec's `surface:` claims
  the whole `pixi.toml` file). Reconciled per the repo's established foreign-spec-surface
  procedure — a `(note by claude)` entry recording the unrelated touch in that spec's own
  `.memlog.md`, then `python scripts/spec_surface_check.py --write-baseline --spec
  pyforge-marshal/spec-pyforge-core` (scoped, not a bare `--write-baseline`).
- **Left alone, pre-existing and out of scope**: `test_conda_forge_expert_not_replaced_or_skf_
  nested` and `test_cfe_not_replaced_and_claude_agents_untouched`
  (`tests/meta/test_persona_consults_cfe.py` / `test_portal_last_diagnose.py`) fail because the
  branch's own merge commit `57c001c9d7` (landing the prior story 15.2's Rule-2 retro) has a
  subject that doesn't match the sanctioned `retro:`/`retro(<scope>):` pattern the
  `unsanctioned_commits` guard expects — confirmed via `git stash` that this failure predates
  every change in this story. Also pre-existing/unrelated: 5 `test_script_responds_to_help[...]`
  failures (a `ModuleNotFoundError: No module named '_sbom'` import bug in
  `add_handoff.py`/`inventory_match.py`/`library_futures.py`/`recommend_2027.py`/
  `universe_sbom.py`) and `test_bmad_artifacts_integrity` (unrelated `uncovered` spec-surface
  findings against other in-flight specs). None of these touch the import-floor probe or verbs
  this story's Never boundary protects.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 15 findings — high 0, medium 0, low 9, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` SKILL.md's `## Version History` section has no bullet for v8.90.3 though the frontmatter version and `CHANGELOG.md` both show 8.90.3, and every prior release (through v8.90.2) has a mirrored bullet — verified live (`grep` found only the v8.90.2 bullet). Action: add a mirrored v8.90.3 bullet.
  - `[low]` `[defer]` Only `truststore`/`conda-forge-metadata` are explicitly pinned in `[feature.pyforge-mason.dependencies]`; `requests`/`ruamel.yaml` (and `packaging`, already covered via the package's own `pyproject.toml`) rely on transitive resolution, so an unrelated future dep drop (e.g. `twine`) could re-break the floor — verified real but pre-existing (predates this story; the Problem statement scoped the fix to exactly the two entries that were actually missing) and substantially mitigated: the new regression test asserts `cfe.probe_import_floor(...).missing == ()` across all six floor entries, so it would already catch this exact regression. Recorded as deferred, not patched — declaring all six explicitly is out of this story's stated scope.
  - `[false]` `library-llms-full.md` claimed not updated for the two new deps ("no mention of truststore/conda-forge-metadata") — refuted: live `pixi run -e local-recipes llms-full-check` (the repo's sanctioned drift detector) reports 0 findings for either package; both are already documented at matching floors (`>=0.10.4`, `>=2026.9.5`) from their pre-existing use in `[feature.python.dependencies]`/`[feature.vuln-db.dependencies]` (verified via grep, lines 116-117 and 789-792 of the catalog).
  - `[low]` `[patch]` CHANGELOG.md's v8.90.3 entry states `environment.yaml` "lands in the mason story's own commit(s)," but it never changed (`git diff` across both commits is empty for that file, since the `build` pixi env excludes the `pyforge-mason` feature) — verified true, the claim is inaccurate. Action: reword to state it was re-exported and confirmed unchanged, not that it landed in a commit. (Same root cause as the Intent Alignment Auditor's point (a) below — grouped, one action.)
  - `[low]` `[patch]` `pixi.toml`'s new `conda-forge-metadata = ">=2026.9.5"` line's trailing `#` comment starts at column 38, three columns out of step with every sibling line in the block (column 35, confirmed via direct inspection, including this diff's own `truststore` line). Action: realign to column 35.
  - `[low]` `[reject]` Adding `conda-forge-metadata` transitively pulls in `conda-oci-mirror`/`oras-py` — a chain `pixi.toml` elsewhere flags as blocked for CVE-DB-snapshot use — verified true via `pixi.lock` diff, but rejected: mason never invokes that code path (dead weight only, no functional harm), unlikely to be encountered in everyday use, and there is no trivial fix (excluding/pinning around a transitive dep adds complexity rather than being a direct correction).
  - `[low]` `[patch]` New test-file section-separator comment (`# --- Story 16.1: ... -----`) is 78 characters; every other `# --- ... ---` divider in `test_doctor.py` is 79 (verified: lines 57/105/253/291 all 79, new line 337 is 78). Action: pad to 79.
  - `[low]` `[patch]` The new test's `from pyforge.mason import cfe` import sits inside the function body — verified via direct read (line 353) — the only local import in an otherwise fully top-imported test file. Action: move to the module-level import block.
  - `[low]` `[patch]` The new regression test pins the floor only at the probe surface (`cfe.probe_import_floor(sys.executable).missing == ()`), one layer beneath the `mason doctor` report surface the acceptance criteria literally quote (`cfe_import_floor_satisfied`, `unavailable_verbs`) — verified real: no test calls the real, unmocked `build_report()` for the now-fixed environment (the existing `test_root_resolved_and_floor_satisfied_reports_no_unavailable_verbs` covers the same surface but with mocks; the existing real-env test only covers the broken case). Action: add one more real-env assertion/sibling test mirroring `test_build_report_never_raises_against_a_real_unresolved_environment`'s pattern, asserting `unavailable_verbs == ()` for the real, current (now-fixed) environment.
  - `[false]` Claimed gating spec-surface FAIL for `pyforge-mason/spec-pyforge-mason` over the unreconciled `test_doctor.py` change — refuted: live `pixi run -e pyforge-doctor python -m pyforge.doctor.sources spec-surface` (exit 0) reports final verdict "spec-surface: ok -- every tracked file governed or allowlisted; no drift" with zero `FAIL` lines anywhere in the output and no mention of `spec-pyforge-mason` at all.
  - `[false]` Claimed gating spec-surface FAIL for 8 other specs governing the root `pixi.toml` (besides the correctly-reconciled `pyforge-marshal/spec-pyforge-core`) — refuted by the same live run: the only `pixi.toml`-related `drift-presumed: warn` lines concern a different file (`src/shared/packages/pyforge-atlas/pixi.toml`), pre-existing and unrelated to this story's root-`pixi.toml` edit; the root `pixi.toml` shows no drift finding under any other spec.
  - `[low]` `[patch]` (Intent Alignment point (a)) `environment.yaml`'s regeneration is claimed in the spec's own Change Log and the CHANGELOG but the diff contains no corresponding hunk, with no note explaining the (legitimate) zero-diff outcome — same root cause and action as the CHANGELOG.md row above; grouped.
  - `[low]` `[patch]` (Intent Alignment point (b)) Same underlying gap as the probe-vs-report-surface finding above — grouped with that row; same action.
  - `[false]` (Intent Alignment point (c)) Claimed CAP-5 re-verification "lives entirely in narrative, not in a runnable artifact" — refuted: an existing automated (mocked) test (`test_doctor.py` ~lines 76-85, asserting `cfe_import_floor_missing == ("pyyaml", "requests")` and `unavailable_verbs == ("recipe",)`) already encodes the exact degradation contract and remains green, unaffected by this diff; the live manual CLI re-verification (`--cfe-python /usr/bin/python3`) supplements but does not solely constitute the coverage.
  - `[false]` (Intent Alignment point (d), foreign-spec-surface touch outside the intent's named scope) — refuted by the auditor's own text: "not a contradiction of the Never bullets ... defensible under a separate, repo-wide convention."
  - `[false]` (Intent Alignment point (e), lockfile-wide footprint vs the intent's two-line description) — refuted by the auditor's own text: "normal fallout of 're-solve the lock' and isn't a contract violation."

## Auto Run Result

**Summary:** `[feature.pyforge-mason.dependencies]` was missing two of `cfe.py`'s six-entry `CFE_IMPORT_FLOOR` (`truststore`, `conda-forge-metadata`), so `mason doctor` reported `unavailable_verbs: ('recipe',)` in mason's own pixi env. Both were added at floors matching the identical pins already used elsewhere in the repo, the lock was re-solved, `environment.yaml` was re-exported (confirmed byte-unchanged — the `build` env excludes the `pyforge-mason` feature), and a regression test now pins the real environment against the floor. A review pass found and fixed six documentation/test-coverage issues; the CFE Rule-2 retro landed with the fix.

**Files changed:**
- `pixi.toml` — `truststore >=0.10.4` + `conda-forge-metadata >=2026.9.5` added to `[feature.pyforge-mason.dependencies]`, aligned to the block's comment column.
- `pixi.lock` — re-solved for the `pyforge-mason` and `pyforge-container` (composite) environments.
- `environment.yaml` — re-exported; confirmed byte-identical to baseline (the `build` env doesn't include the `pyforge-mason` feature).
- `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` — two new tests: `test_real_environment_satisfies_the_cfe_import_floor` (real, unmocked probe-level pin) and `test_real_environment_and_root_report_recipe_as_available` (real, unmocked `build_report()`-level pin, added during review to match the acceptance criteria's report surface); import cleanup.
- `.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,MANIFEST.yaml,config/skill-config.yaml}` — Rule-2 retro, v8.90.2 → v8.90.3 (PATCH; no skill-behavior changes — the finding is entirely in mason's own environment declaration).
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_md_consistency.py` — allowlisted mason's `cfe.py` (a repo-internal, non-CFE-skill file the new Version History bullet cites).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` + `scripts/.spec-surface-baseline.json` — foreign-spec-surface reconciliation (`pyforge-marshal/spec-pyforge-core` claims all of `pixi.toml`), scoped-stamped twice (once for the dependency addition, once for the review pass's comment-alignment follow-up).
- This spec file — Review Triage Log, `deferred` entry, this section.

**Review findings breakdown** (15 findings across 4 layers; 0 high, 0 medium, 9 low, 6 false, 0 maybe-false):
- **Patched (6 distinct fixes, 7 rows):** SKILL.md missing a v8.90.3 Version History bullet; CHANGELOG.md's misleading "environment.yaml lands in a commit" wording (grouped with the Intent Alignment auditor's matching point); `pixi.toml`'s misaligned trailing comment (fixed to the closest TOML-feasible column — exact column 35 is unreachable for this key's length); a test-file separator comment one character short; a test's local (function-scoped) import moved to module scope; the regression test's surface gap (probe-level only) closed with a new sibling test at the `mason doctor` report surface the acceptance criteria quote.
- **Deferred (1):** only `truststore`/`conda-forge-metadata` are explicitly pinned; `requests`/`ruamel.yaml` rely on transitive resolution — pre-existing, out of this story's stated scope, and already substantially mitigated by the new regression test (which checks all six floor entries, not just the two added). See frontmatter `deferred:`.
- **Rejected, low (1):** `conda-forge-metadata` transitively pulls in `conda-oci-mirror`/`oras-py` (a chain flagged elsewhere as blocked for CVE-DB-snapshot use) — real but inert (mason never invokes that code path); no trivial fix exists that wouldn't add complexity.
- **Rejected, false (6):** two Edge Case Hunter claims of gating spec-surface `FAIL`s (refuted live — the actual check reports `ok`, zero `FAIL` lines, and the cited specs/paths were either unaffected or a different file entirely); the `library-llms-full.md` "undocumented dependency" claim (refuted — the live drift detector shows both new deps already cataloged at matching floors); the Intent Alignment auditor's CAP-5-narrative-only claim (refuted — an existing automated mocked test already covers it, unaffected by this diff) and its two purely-descriptive divergence points ((d) foreign-spec-surface touch, (e) lockfile footprint), both explicitly non-violations by the auditor's own text.

**Follow-up review recommendation: false.** All patched entries were `low` severity (0 `high`, 0 `medium`) — below both the first-pass and follow-up thresholds.

**Verification performed:**
- Live `pixi run -e pyforge-mason mason doctor`: `cfe_import_floor_satisfied: True`, `cfe_import_floor_missing: ()`, `unavailable_verbs: ()`.
- Live CAP-5 re-check (`mason doctor --cfe-python /usr/bin/python3`): exits 0, `unavailable_verbs: ('recipe',)` — graceful degradation intact.
- `diff <(pixi project export conda-environment -e build) environment.yaml`: in sync.
- `python -m pyforge.doctor.sources spec-surface` (via `pyforge-doctor` env): exit 0, `spec-surface: ok — every tracked file governed or allowlisted; no drift`.
- `pixi run -e pyforge-mason pyforge-mason-test`: 1579 passed, 3 deselected, 2 pre-existing/unrelated failures (see Residual risks).
- `pixi run -e local-recipes test-skill --meta`: 7664 passed, 3 skipped, 6 pre-existing/unrelated failures (see Residual risks).
- Matrix Test Audit: all five I/O & Edge-Case Matrix rows covered by a test that ran and passed (the "Regression pin" and "Floor satisfied"/"recipe verb available" rows now covered at both the probe and `mason doctor` report surfaces).

**Residual risks:**
- Two pre-existing meta-test failures (`test_persona_consults_cfe.py::test_conda_forge_expert_not_replaced_or_skf_nested`, `test_portal_last_diagnose.py::test_cfe_not_replaced_and_claude_agents_untouched`) were already failing before this story — root cause: the baseline merge commit (`57c001c9d7`, this spec's own `baseline_revision`) has a subject that doesn't match the sanctioned `retro:`/`retro(<scope>):` pattern `unsanctioned_commits()` requires. **This pass adds a second, disclosed contributing cause to the same pre-existing failure**: commit `7660a5c851` (the `test_skill_md_consistency.py` allowlist fix, made during the review pass) also has a non-`retro:` subject and touches the CFE path. The verdict of these two tests is unchanged by this (already red, still red) — but fixing it cleanly requires removing/rewriting a local commit (amend or non-interactive history rewrite), which this workflow's git-safety constraints reserve for an explicit user request. Flagging honestly rather than working around it silently.
- Five pre-existing, unrelated `test_script_responds_to_help[...]` failures (`add_handoff.py`, `inventory_match.py`, `library_futures.py`, `recommend_2027.py`, `universe_sbom.py`) — a `ModuleNotFoundError: No module named '_sbom'` import bug, confirmed unrelated to the import-floor probe.
- One pre-existing, unrelated `test_bmad_artifacts_integrity` failure — 3 "uncovered" findings against `pyforge-marshal` planning-artifact files (`spec-33-3`, `spec-33-8`, `spec-33-9`), confirmed via `git log` to predate this story's baseline commit; nothing to do with mason or the CFE import floor.
