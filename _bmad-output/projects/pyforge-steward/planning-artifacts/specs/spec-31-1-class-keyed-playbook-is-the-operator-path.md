---
title: Class-keyed playbook is the operator path
type: chore
created: '2026-08-25'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: a3784c33ed55db4b22472f1978d8bd74a538e6dc
---

<intent-contract>

## Intent

**Problem:** The six non-module suite pieces (method, loop, skf, labs, dashboards, template) are not `--module` targets. Operators currently learn how to wire them from session scratchpads instead of a discoverable playbook.

**Approach:** Keep the tracked companion `install-class-playbook.md` as the operator path (pixi, cited native wire, steward verb/task per class). Point `steward provision --help` at that playbook. Native commands stay citations of `install-matrix.md`, never invented in CLI help or the playbook.

## Acceptance Criteria

- Given the six non-module suite pieces, when an operator runs `steward provision --help`, then the help text names the class-keyed playbook (`install-class-playbook.md` under `spec-bmad-suite-install-class-wiring`).
- Given that playbook, then each of the six classes lists a pixi/PATH row, a native-wire citation, and a steward verb/task — no tribal knowledge.
- Native commands in the playbook appear in `install-matrix.md`; tests fail if `--help` no longer names the playbook or if native commands are invented rather than cited.

## Boundaries & Constraints

**Always:** Epic 15 stays done — this is Epic 31 Story 31.1, not 15.5+. Wrap, don't absorb (method first-install = Epic 14; loop = `--runner` only). Template is scaffold-only forever. Dual-path (pixi + native) remains the suite contract.

**Block If:** A change would reopen CAP-3's five (`bmb`, `tea`, `cis`, `utility-skills`, `manticore`) or the WDS skip.

**Never:** `steward provision --module skf`. Grow `_SUPPORTED_MODULES` with non-modules. Invent native commands. Put `pyforge.*` under `src/platform/`. Implement 31.2 (`wired-or-not`) or 31.3 (fresh-clone proof). Run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Help names playbook | `steward provision --help` | stdout includes `install-class-playbook.md` and the `spec-bmad-suite-install-class-wiring` path | argparse `--help` exits 0 |
| Playbook cites matrix | playbook Native-wire cells | every backtick native fragment is a substring of `install-matrix.md` | test fails on invented fragments |
| Six classes complete | playbook table | six pieces each have pixi, native-wire, and steward-surface cells | test fails on empty cells |
| Help does not invent wire | `steward provision --help` | help does not embed `npx ` / `uv tool install` (those live in the cited playbook) | test fails if CLI invents native cmds |
| Modules unchanged | `--module` help / `_SUPPORTED_MODULES` | still the CAP-3 five; WDS skip; skf absent | test fails if skf is registered |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `build_parser` / `_add_provision_subparsers`; add a constant playbook path and `provision` epilog so `steward provision --help` names it. Do not import `provision.py` (existing comment: keep "supported: ..." in sync without importing).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md` — CAP-1 companion already landed; six-row table + cite of parent `install-matrix.md`. Story 31.1 discovers it; do not rewrite native commands.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md` — citation source (read-only).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/SPEC.md` — CAP-1 success: playbook exists, cites matrix, `provision --help` names it.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` — `_SUPPORTED_MODULES` / `_SKIPPED_MODULES` read-only this story.
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` — existing `--help` pattern (`parse_args` + `capsys`).
- `src/shared/packages/pyforge-steward/tests/unit/test_provision_install_class_playbook.py` — new: help pointer + citation lock + six-row completeness.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- export `INSTALL_CLASS_PLAYBOOK` and set the provision subparser epilog (RawDescriptionHelpFormatter) so `--help` names the playbook -- CAP-1 discoverability
- `src/shared/packages/pyforge-steward/tests/unit/test_provision_install_class_playbook.py` -- lock help text, six-row playbook completeness, and native-command citation against `install-matrix.md` -- tests fail on missing pointer or invented natives
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-31-1-class-keyed-playbook-is-the-operator-path.md` -- this spec, tracked in the implementation PR -- durable contract

**Acceptance Criteria:**
- Given the six non-module pieces, when `steward provision --help` runs, then it names `install-class-playbook.md`.
- Given the playbook, when tests extract native-wire fragments, then each fragment is cited from `install-matrix.md`.
- Given this story, when the diff is reviewed, then no `pyforge.*` was added under `src/platform/` and Epic 15 module wiring is untouched.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 3: (low 3)
- addressed_findings:
  - none

Rejected (noise): requiring `main(["provision", "--help"])` in addition to `parse_args` (same argparse path); locking `steward -h` separately from `--help`; splitting mybmad into a seventh table row (spec's six classes keep dashboards on one row).

## Design Notes

Help is a pointer, not a second copy of native commands. Copying `npx`/`uv tool install` into argparse would invent a competing (and stale) wire. The playbook already cites `../spec-bmad-suite-channel-product/install-matrix.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: `steward provision --help` now names the class-keyed playbook path. Tests lock that pointer, the six-row playbook completeness, and native-command citation against `install-matrix.md`. Epic 15 `--module` set and WDS skip are unchanged. No `pyforge.*` under `src/platform/`.

Files:
- `cli.py` — `INSTALL_CLASS_PLAYBOOK` constant + provision epilog
- `test_provision_install_class_playbook.py` — CAP-1 conformance
- `spec-31-1-class-keyed-playbook-is-the-operator-path.md` — tracked story spec

Review: patches 0, deferred 0, rejected 3 (low). Follow-up review recommended: false (patched high=0, score=0).

Verification: 26 passed (`test_provision_install_class_playbook.py` + `test_cli.py`).

Residual: playbook plugin-marketplace ellipsis is prose, not a cited `npx` command; citation lock keys on matrix-owned install commands.
