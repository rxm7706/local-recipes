---
title: Five modules wire through the provisioning verb
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 45ad75341feff0378a31d55afb2bae2a6bc02605
deferred:
  - summary: >-
      Conda installer subprocess has no timeout; a hung *-install can block the
      provision duty indefinitely.
    evidence: |-
      Review edge-case finding: subprocess.run for CondaInstallBackend has no
      timeout= argument. Pre-existing pattern also applies to bmb setup-skill
      uv run calls; not uniquely introduced by 15.3 wiring.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
    severity: low
  - summary: >-
      No rollback of copied skill dirs when post-install verification or
      manifest write fails after installer exit 0.
    evidence: |-
      Skills may be copied before manifest record; a later raise leaves orphan
      .claude/skills entries without a module key. Collision check then blocks
      retry until skills are removed manually.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
    severity: medium
  - summary: >-
      --list-modules does not surface _SKIPPED_MODULES (WDS) or skip reasons.
    evidence: |-
      Operators cannot discover from the list verb that WDS is intentionally
      unwired versus simply unsupported; skip is only on --module wds.
    severity: low
  - summary: >-
      Hard-coded _CIS_SKILL_NAMES allowlist is not asserted against the live
      bmad-creative-intelligence-suite share tree.
    evidence: |-
      Drift shows up only as post-install skills-missing RuntimeError.
    severity: low
---

<intent-contract>

## Intent

**Problem:** `steward provision --module` only supports `bmb`; tea, cis, utility-skills, and manticore remain unwired despite being CAP-3 wire-decided modules (spec-bmad-suite-channel-product).

**Approach:** Grow `_SUPPORTED_MODULES` from `{bmb}` to `{bmb, tea, cis, utility-skills, manticore}` using each conda package's installer entry points. Each addition is manifest-recorded, skill-name-collision-checked, retired-ID guard + integrity meta tests green, reproducible on a fresh clone. Record WDS as an explicit skip-decision with the upstream-deprecation citation (absorbing into bmad-ux).

## Acceptance Criteria

- `_SUPPORTED_MODULES` includes bmb, tea, cis, utility-skills, manticore.
- Each new module provisions via `steward provision --module <name>` (manifest, collision check, retired-ID guard).
- Integrity / meta tests green; fresh-clone path covered by fixtures.
- WDS documented as skip with upstream-deprecation citation (not in `_SUPPORTED_MODULES`).
- Does not implement 15.4 native-path spot-checks or install-class wiring for method/loop/skf/labs/dashboards/template.

## Boundaries & Constraints

**Never:** Wire WDS. Never absorb bmad-method core or bmad-loop into `--module`. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only. Do not touch marshal 19-3 / PR #677.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` — `_SUPPORTED_MODULES`, `SetupSkillBackend` / `CondaInstallBackend`, `_SKIPPED_MODULES`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--module` help lists five + WDS skip note
- Conformance: `tests/conformance/test_provision_list_modules.py`, `tests/conformance/test_provision_module_installers.py`

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green for provision module suite
- `steward provision --list-modules` names the five; WDS absent
- CI: detectors, linter, package tests

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 5, low 1)
- defer: 4: (high 0, medium 1, low 3)
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Refuse non-mapping `_bmad/config.yaml` instead of wiping; atomic temp-and-replace write
  - `[medium]` `[patch]` `provision_module` raises skip citation for WDS (API/CLI parity)
  - `[medium]` `[patch]` Soften collision error (no forge-config bypass hint)
  - `[medium]` `[patch]` Tests: sibling manifest keys preserved; CONDA_PREFIX local-share preference; exit-0 skills-missing; fixture discovery disjointness; WDS API skip
  - `[low]` `[patch]` Restore `--list-modules` precedence assert that unsupported `--module nope` was not handled

## Auto Run Result

Status: done

### Summary
Grew `_SUPPORTED_MODULES` to `{bmb, tea, cis, utility-skills, manticore}`. New modules use `CondaInstallBackend` (`bmad-*-install`), skill-name collision checks, and `_bmad/config.yaml` manifest recording. WDS remains skip-only via `_SKIPPED_MODULES` with upstream-deprecation citation.

### Files changed
- `src/.../provision.py` — registry growth, backends, skip set, manifest/collision/prefix helpers
- `src/.../cli.py` — `--module` help for five modules + WDS skip note
- `tests/.../test_provision_list_modules.py` — five-module expectations; WDS absent
- `tests/.../test_provision_module_installers.py` — new installer/collision/skip/fixture suite
- `planning-artifacts/specs/spec-15-3-….md` — status/review/auto-run result

### Review findings
- Patches applied: 7 (1 high, 5 medium, 1 low) — follow-up recommended (high patched → true; score n/a once high present)
- Deferred: 4 (timeout, rollback, list-modules skip surface, CIS allowlist live assert)
- Rejected: 8 (live-installer-required reading, ledger-in-PR, help ordering, TOCTOU, operator README, docstring deletions, bmb `_conda_prefix` unification, editing cited planning docs)

### Follow-up review recommendation
`true` — patched high=1 (any high → recommend follow-up). Patched medium=5, low=1.

### Verification performed
- `pixi run --frozen -e pyforge-steward pytest …/test_provision_module*.py …/test_provision_list_modules.py -q` → **77 passed**
- `steward provision --list-modules` → bmb, cis, manticore, tea, utility-skills (all available); WDS absent
- `steward provision --module wds` → skip citation with install-matrix / bmad-ux
- `pixi run --frozen -e local-recipes pytest …/test_no_retired_bmad_skill_ids.py …/test_bmad_artifacts_in_sync.py -q` → **8 passed**

### Residual risks
- Live `bmad-*-install` against a real local-recipes env not exercised in CI (fixtures + fake installer).
- Partial-failure rollback of copied skills still deferred.
- Installer hang timeout still deferred.
