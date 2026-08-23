---
title: The pre-flight diff retrodicts a real upgrade
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 3f4b28838bdbca05c7f425450c19d2d8240358f9
deferred:
  - summary: >-
      skill-manifest.csv parsing is a naive quoted-CSV split; skills with commas in
      fields would mis-parse.
    evidence: |-
      `_read_installed_skill_names` splits on commas rather than using the csv
      module. Current skill IDs have no commas; review pass noted the fragility.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** BMAD-METHOD core upgrades are manual one-offs; there is no report-only pre-flight that lists what a target release would change before apply (`spec-bmad-method-core-upgrade` CAP-1).

**Approach:** Add a steward report-only upgrade pre-flight command that, given installed `_bmad/_config/manifest.yaml` and a target bmad-method release, lists skill adds/removes/renames (shim disposition + `removals.txt` deletions), upstream-touched files the repo has locally modified, `_bmad/custom/**` overrides that stop applying (legacy-name unattended-halt trap), and new hard prerequisites. Fixture: pointed at the 6.10.0→6.11.0 pair, retrodicts the 2026-08-21 findings (failure-modes.md traps 1–4, 9, 11).

## Acceptance Criteria

- Report-only command (no apply/mutate) lists skill adds/removes/renames with shim disposition and `removals.txt` deletions.
- Reports upstream-touched files that the repo has locally modified.
- Reports `_bmad/custom/**` overrides that would stop applying (legacy-name unattended-halt trap).
- Reports new hard prerequisites for the target release.
- Fixture test: 6.10.0→6.11.0 pair retrodicts failure-modes.md traps 1–4, 9, 11.

## Boundaries & Constraints

**Never:** Implement apply/branched upgrade (Story 14.2+). Never mutate `_bmad/` or custom surfaces in this story. Verb naming may extend `steward provision` or introduce `steward upgrade bmad-core` — pick one and document. Detection of "you're behind" stays doctor's; this is steward's pre-flight report surface.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — CAP-1 pre-flight engine + `UpgradeDuty`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — seventh duty `upgrade` / verb `bmad-core`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.11.0.yaml` — curated release catalog
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py` — 6.10→6.11 trap retrodiction
- Parent: `spec-bmad-method-core-upgrade/SPEC.md` CAP-1 + `failure-modes.md` traps 1–4, 9, 11

## Design Notes

**Verb naming (SPEC open question):** introduced `steward upgrade bmad-core` as a new seventh duty — not an extension of `provision`. Epic 14's later CAPs (apply, reconcile, pin fan-out, verify) share this surface; crowding Epic 3's environment/module flags would blur first-install vs already-installed-upgrade. Ambient "you're behind" remains doctor's.

**Catalog vs live package:** curated `data/bmad_core_releases/X.Y.Z.yaml` carries trap-calibrated knowledge (renames, legacy custom names, prerequisites, forwarder contract, config-migration). Optional `--package-root` contributes live `removals.txt` + upstream file comparison — still read-only. Unknown targets without a catalog entry fail closed.

## Verification

- `pixi run --frozen -e pyforge-steward pytest` targeting the new pre-flight tests
- Fixture asserts trap retrodiction for 6.10→6.11

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 2, low 1)
- defer: 1: (high 0, medium 0, low 1)
- reject: 2
- addressed_findings:
  - `[medium]` `[patch]` skill_adds duplicated rename targets — skip adds that equal a rename `to`/`from`; catalog lists only net-new `bmad-review`
  - `[medium]` `[patch]` wheel may omit YAML catalogs — hatch `force-include` for `bmad_core_releases/`
  - `[low]` `[patch]` `--package-root` with mismatched `package.json` version was silent — emit warning note

## Auto Run Result

Status: done

Summary: Added report-only `steward upgrade bmad-core --target X.Y.Z` (seventh duty) that lists skill adds/removes/renames with shim disposition, `removals.txt` deletions, locally modified upstream-touched files, legacy `_bmad/custom/**` halt traps, hard prerequisites, forwarder contract changes, and config-migration status. Curated 6.11.0 catalog + fixture retrodicts failure-modes traps 1–4, 9, 11. No apply/mutation.

Files changed:
- `upgrade.py` — pre-flight engine + UpgradeDuty
- `cli.py` / `interfaces.py` / `test_cli.py` — wire seventh duty
- `data/bmad_core_releases/6.11.0.yaml` — release catalog
- `pyproject.toml` — force-include catalogs in wheel
- `tests/unit/test_upgrade_preflight.py` — retrodiction + CLI + no-mutate tests
- this spec — status done + triage/result

Review findings: 3 patches applied; 1 deferred (naive CSV); 2 rejected (README noise; audit-when-already-at-target by design).

Follow-up review recommendation: true (patched medium=2, low=1; score `3×2+1=7` ≥ 5).

Verification: `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests` → **777 passed**. Live smoke: `steward upgrade bmad-core --target 6.11.0` report-only against the real tree.

Residual risks: future releases need a new catalog YAML before `--target` works; trap-1 detection relies on repo-custom markers in touched paths rather than a full installer file inventory.
