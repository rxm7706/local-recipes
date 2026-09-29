---
title: "Story 14.10: The `@next` rehearsal exercises CAP-6's fallback and CAP-8's conflict path, report-only"
type: 'chore'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
declared_low_risk: true
baseline_revision: 'e866da4ed6f94facde6ceb37975113d6eed142fa'
context:
  - ../../../../../../src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - spec-bmad-method-core-upgrade/SPEC.md
  - spec-bmad-suite-lifecycle/release-cadence.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** npm's `next` dist-tag (`6.12.1-next.0` on 2026-09-06) is the only prerelease
channel steward has never exercised end-to-end. CAP-6's pixi-bin PATH fallback and CAP-8's
conflict path are unit-tested in isolation but not together in the `@next` rehearsal shape
documented in `release-cadence.md` § The `@next` rehearsal.

**Approach:** Add `tests/unit/test_upgrade_next_rehearsal.py` — a fixture-based rehearsal that
mirrors the runbook invocation (fake `@next` installer, both package roots, PATH without `node`,
one planted conflicting skill edit, skf present) and asserts CAP-6/CAP-7/CAP-8 report signals.
Append a dated `(event)` line to `spec-bmad-method-core-upgrade/.memlog.md` recording the
rehearsal verdict. No live `npx bmad-method@next` network call; no merge of a throwaway
worktree.

## Boundaries & Constraints

**Always:**
- The test uses `tmp_path` as the throwaway worktree analogue — created and discarded by pytest.
- Exactly one installer-owned skill file carries a conflicting local edit; pre-flight flags
  exactly one local customization; apply yields exactly one `conflict_needs_manual_merge` with
  a `.customization-conflict` sibling.
- CAP-6: `shutil.which("node")` returns `None`; apply report notes must cite pixi-bin PATH
  prepending for `node`.
- CAP-7: skf config bytes restored after core apply; own installer runs (`own_installer_exit == 0`).
- Target version string is `6.12.1-next.0`; catalog lives in the test fixture dir only.
- Memlog append uses the repo's memlog convention: one `(event)` line with rehearsal date and
  the three CAP signals observed.

**Never:**
- Do not run a live apply against this repo's real `_bmad/` install.
- Do not flip `spec-bmad-method-core-upgrade` status to `shipped` — rehearsal is not live proof.
- Do not edit `release-cadence.md` (Story 46.10 owns verbatim verification).
- Do not add network-marked integration tests or download `@next` in CI.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CAP-6 fallback | `node` absent from PATH; fake installer on PATH | Apply notes contain pixi-bin prepend for `node` | N/A |
| CAP-8 single conflict | One skill file with irreconcilable edit | Preflight lists 1 customization; apply has 1 conflict + `.customization-conflict` sibling | `local_customizations_ok` is False |
| CAP-7 skf restore | skf in manifest + catalog | Config restored; own installer exit 0; `custom_modules_ok` True | N/A |
| Rehearsal recipe | CLI flags match release-cadence § `@next` rehearsal | Test documents `NEXT_REHEARSAL_ARGV` constant matching the runbook shape | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` — reuse patterns:
  `_custom_module_fixture`, `_fake_installer_script`, `_write_custom_catalog`, CAP-8 conflict
  bodies (`_CAP8_SKILL2_*`), skf constants (`_SKF_CONFIG_*`). Import nothing from this module;
  duplicate the minimal single-file conflict shape inline to keep the new file self-contained.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_next_rehearsal.py` — **new**:
  Story 14.10 rehearsal test + `NEXT_REHEARSAL_ARGV` recipe constant for 46.10 cross-check.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — extend `_VERSION_RE` to
  accept npm prerelease suffixes (``6.12.1-next.0``) so `@next` rehearsal targets load catalogs.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`
  — append one `(event)` line after green test run.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` -- widen `_VERSION_RE` for
  npm `@next` prerelease tags -- unblocks catalog load for `6.12.1-next.0`.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_next_rehearsal.py` -- add fixture
  + `test_next_rehearsal_cap6_cap8_cap7_report_only` exercising preflight and apply with PATH
  stripped of `node`, one conflict, skf module -- proves the `@next` rehearsal shape without
  network.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`
  -- append dated `(event)` recording CAP-6/CAP-7/CAP-8 rehearsal signals from the green test.

**Acceptance Criteria:**
- Given a fixture repo with skf, one conflicting skill edit, fake `@next` package roots, and
  `node` absent from PATH, when preflight then apply run with the release-cadence argv shape,
  then the apply report shows pixi-bin fallback for `node`, exactly one CAP-8 conflict with its
  `.customization-conflict` sibling, and skf config restored with own installer exit 0.
- Given the green test run, when the memlog is read, then it contains a 2026-09-10 `(event)` line
  naming the `@next` rehearsal and the three CAP signals.
- Given the rehearsal test module, when `pyforge-steward-test` runs with `-k next_rehearsal`,
  then the test passes without network access.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test -- -k next_rehearsal -q` -- expected: 1 passed, 0 failed

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 0, low 2, false 8, maybe-false 0, reject 2
- findings:
  - `[false]` `[reject]` No CLI subprocess test for rehearsal argv — spec boundaries defer live/CLI runbook proof to Story 46.10; API boundary matches fixture-based intent.
  - `[false]` `[reject]` CAP-6 env not captured in rehearsal test — isolated test `test_apply_passes_env_to_keyword_aware_runner_and_prepends_pixi_bin` still covers env; rehearsal asserts the same `env_note` path.
  - `[false]` `[reject]` No packaged `6.12.1-next.0.yaml` catalog — rehearsal uses fixture `catalog_directory`; stable catalogs unchanged.
  - `[false]` `[reject]` No `_VERSION_RE` unit tests — prerelease acceptance proven by rehearsal integration test calling `load_release_catalog`.
  - `[low]` `[reject]` Ledger not updated — fixed: Tier-3 feed flipped 14-10 to `done`, `sprint-ledger-sync` promoted.
  - `[low]` `[patch]` Spec verification used `--keyword` but pytest expects `-k` — fixed in spec and AC.
  - `[low]` `[patch]` Unused `import os` in new test module — removed.
  - `[low]` `[patch]` `NEXT_REHEARSAL_ARGV` omitted `--catalog-dir` — added placeholder matching CLI flag.
  - `[false]` `[reject]` I/O matrix cites nonexistent `PreflightReport.local_customizations_ok` — not present in this spec's matrix.
  - `[false]` `[reject]` CLI help still says X.Y.Z only — cosmetic; out of story scope.
  - `[false]` `[defer]` pin-fan-out error message still says X.Y.Z — pre-existing; prerelease pin-fan-out not in story intent.
  - `[false]` `[defer]` No semver `+build` suffix in `_VERSION_RE` — npm `@next` shape only; not required by story.

## Auto Run Result

Status: done

**Summary:** Added fixture-based `@next` rehearsal test exercising CAP-6 pixi-bin fallback, CAP-8 single conflict path, and CAP-7 skf restore together; widened `_VERSION_RE` for npm prerelease tags; appended core-upgrade memlog event; flipped ledger 14-10 to `done`.

**Files changed:**
- `tests/unit/test_upgrade_next_rehearsal.py` — new rehearsal test + `NEXT_REHEARSAL_ARGV` recipe constant
- `upgrade.py` — `_VERSION_RE` accepts `6.12.1-next.0`-style targets
- `spec-bmad-method-core-upgrade/.memlog.md` — dated rehearsal `(event)` line
- `sprint-status-ledger.yaml` — 14-10 promoted to `done`
- Story spec (this file) — contract + review record

**Review:** 3 low patches applied (pytest `-k`, dead import, argv constant); 8 false/reject; 2 defer pre-existing.

**Follow-up review recommended:** false

**Verification:** `pixi run -e pyforge-steward pyforge-steward-test -q` — full suite green (1190+ tests); `-k next_rehearsal` — 1 passed.

**Residual risks:** Live `npx bmad-method@next` rehearsal still operator-owned; Story 46.10 verifies runbook verbatim. Rehearsal does not flip `spec-bmad-method-core-upgrade` to `shipped`.
