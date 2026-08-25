---
title: Fresh clone class-path is proven
type: feature
created: '2026-08-25'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 5bbfc3752713e39468877e808ba275ff76c97ea0
---

<intent-contract>

## Intent

**Problem:** The six non-module suite pieces have a class-keyed playbook (31.1) and class-correct wired-or-not (31.2), but a fresh clone still has no recorded/scripted path that proves method core, loop `--runner`, skill-forge via its own installer, labs plugin docs, dashboard runnable, and template N/A without a chat transcript driving npm `Installer` classes.

**Approach:** Document the CAP-3 walk in `install-class-playbook.md` using only native commands cited from `install-matrix.md`, plus steward surfaces that already exist. Prove it with `steward provision --prove-class-path`, tests that fail on improvised npm Installer / `--module skf` / resurrected Guildhall generator tasks, and a CI job on a checkout (the CI equivalent of a recorded run). After 30.2, "dashboard install task runnable" is Kedro-Viz / `steward deploy dashboard`; operator console is Lane 1 `/console/`.

## Acceptance Criteria

- Given a fresh clone (this checkout), when the scripted path is proven, then method core is installed, loop is provisionable via `--runner` (flag + runner-home predicate), skill-forge skills are present via its own installer, labs plugin path is documented, dashboard install task is runnable as Kedro-Viz / `steward deploy dashboard`, and template is N/A unless scaffolding.
- Given the documented path, when tests extract native commands, then each is cited from `install-matrix.md` / the playbook — never invented.
- Given an improvised npm `Installer` transcript, `--module skf`, or `dashboard-gen`/`dashboard-watch`/`dashboard-check`/`dashboard-drift-check` in the path docs, then tests fail.

## Boundaries & Constraints

**Always:** Epic 15 stays done. Wrap, don't absorb (method first-install = Epic 14; loop = `--runner` only). Template is scaffold-only forever. Dual-path remains. Native commands cited from `install-matrix.md` / `install-class-playbook.md`. After 30.2 do not resurrect Guildhall `dashboard-gen` / watch / check / drift-check. Operator console is Lane 1 `/console/`.

**Block If:** A change would reopen CAP-3's five (`bmb`, `tea`, `cis`, `utility-skills`, `manticore`) or the WDS skip.

**Never:** `steward provision --module skf`. Put `pyforge.*` under `src/platform/`. Run `scripts/bmad-switch`. Start Story 32.2. Invent native npm/uv/pnpm commands. Drive npm `Installer` classes from a chat transcript.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live checkout prove | this clone | six class outcomes: present / provisionable / present / documented / runnable / n/a | DutyResult ok=False if any miss |
| Native citation | playbook fresh-clone section | every `npx`/`uv tool install`/`corepack`/`pnpm` fragment is in install-matrix.md | test fails on invented fragment |
| Improvised Installer | path docs contain `new Installer` | prove fails / test fails | named refusal |
| `--module skf` | path docs mention it | prove fails / test fails | Spec non-goal |
| Guildhall tasks | pixi.toml or path docs revive dashboard-gen/watch/check/drift-check | test fails | 30.2 HARD |
| Template into repo | template class | always n/a, never wired | test fails if wired |
| Help pointer | `steward provision --help` | names `--prove-class-path` and still names the playbook; no `npx ` in help | argparse exit 0 |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md` — add CAP-3 scripted walk; dashboard steward surface = `steward deploy dashboard` / Kedro-Viz / `/console/` (not Guildhall generate.py). Native-wire cells stay matrix citations (31.1 lock).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md` — citation source (read-only).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/fresh_clone.py` — `prove(repo)` + forbidden-pattern scan; reuse `suite.probe_wired` for class predicates; extra dashboard checks (kedro-viz, no four pixi tasks, deploy help).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--prove-class-path` on provision; keep `INSTALL_CLASS_PLAYBOOK` pointer; do not embed `npx` in help (31.1).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` — dispatch `--prove-class-path` (after `--module`, before `--verify`); do not change `_SUPPORTED_MODULES`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py` — read-only (31.2 predicates).
- `src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py` — matrix + live prove + improvised-Installer fail.
- `.github/workflows/pyforge-steward-fresh-clone.yml` — CI recorded run (stdlib + pytest + pyforge-core/steward, like five-tier).

## Tasks & Acceptance

**Execution:**
- `install-class-playbook.md` -- scripted CAP-3 walk + post-30.2 dashboard steward surface -- operator path
- `fresh_clone.py` -- prove + citation/forbidden scan -- CI-equivalent recorded run
- `cli.py` / `provision.py` -- `--prove-class-path` -- discoverable steward verb
- `test_fresh_clone_class_path.py` -- lock matrix, live clone, improvised npm refusal -- tests fail if path is a transcript
- `.github/workflows/pyforge-steward-fresh-clone.yml` -- run the test module on PR/push -- CI proof
- `spec-31-3-fresh-clone-class-path-is-proven.md` -- this spec in the implementation PR

**Acceptance Criteria:**
- Given a fresh clone, when `steward provision --prove-class-path` runs, then the six class outcomes match CAP-3.
- Given path docs, when native fragments are extracted, then each is in `install-matrix.md`.
- Given this story, when the diff is reviewed, then no `pyforge.*` was added under `src/platform/` and Epic 15 module wiring is untouched.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 4: (low 4)
- addressed_findings:
  - `[medium]` `[patch]` `prove()` now prefers cwd when it is a checkout so CI `pip install --no-deps` into site-packages still proves the GitHub workspace, not a missing walk from the wheel
  - `[low]` `[patch]` provision `--help` test also locks `--runner` so CAP-3's wrap surface cannot vanish silently

Rejected (noise): requiring live `npx`/`uv tool install` on every CI job; changing 31.2's vscode-extension pixi-task predicate; putting `pyforge.*` under `src/platform/`; reopening Epic 15 `--module` five / WDS.

## Design Notes

`--runner` remains the wrap (playbook / Epic 31 HARD). Story 5.1 made the flag report rather than materialize; CAP-3 still proves the flag exists and the runner-home file `scripts/bmad-loop-worktree` is present (31.2 `provisionable`). Dashboard CAP-3 does not use `pixi run bmad-dashboard-install` as the Guildhall generator stand-in; that pixi task may remain for the VS Code extension class (31.2). Kedro-Viz + `steward deploy dashboard` is the surviving console-adjacent install task.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py src/shared/packages/pyforge-steward/tests/unit/test_provision_install_class_playbook.py src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py -q` -- expected: all passed
- `git grep -n 'pyforge\.' -- src/platform/` on this story's diff -- expected: no new `pyforge.*` under `src/platform/`

## Auto Run Result

Status: done

Summary: Documented and proved the six-class fresh-clone path. `steward provision --prove-class-path` (plus CI job `pyforge-steward-fresh-clone`) records method present, loop `--runner`/runner-home provisionable, skill-forge present via its own installer, labs documented, dashboard runnable as Kedro-Viz / `steward deploy dashboard` (Lane 1 `/console/`), template N/A. Native commands stay citations of `install-matrix.md`. Tests fail on improvised npm `Installer`, `--module skf` in the CAP-3 walk, and resurrected Guildhall pixi tasks. Epic 15 module set untouched. No `src/platform/` changes.

Files:
- `install-class-playbook.md` — CAP-3 scripted walk; dashboard steward surface after 30.2
- `fresh_clone.py` — prove + citation/forbidden scan
- `cli.py` / `provision.py` — `--prove-class-path`
- `test_fresh_clone_class_path.py` — CAP-3 conformance
- `pyforge-steward-fresh-clone.yml` — CI recorded run
- `spec-31-3-fresh-clone-class-path-is-proven.md` — tracked story spec

Review: 2 patches (1 medium, 1 low); deferred 0; rejected 4 (low). Follow-up review recommended: false (patched high=0; score 3×1+1=4 < 5).

Verification: 49 passed (`test_fresh_clone_class_path.py` + playbook + wired-class + `test_cli.py`); 31 passed (`test_provision_list_modules.py` + `test_provision_runner.py`). Diff has no `src/platform/` files.

Residual: `--runner` still reports retired (Story 5.1) rather than materializing; CAP-3 proves the flag + runner-home file. VS Code `bmad-dashboard-install` pixi task remains for 31.2 class scoring.
