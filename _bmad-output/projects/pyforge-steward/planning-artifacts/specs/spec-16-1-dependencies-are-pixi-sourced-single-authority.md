---
title: Dependencies are pixi-sourced, single-authority
type: chore
created: '2026-08-23'
status: done
shipped_ref: 'bec9707bf87aed6a8c4c763e5390e9793d3ab0ff'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 4d9c58ae85
---

> **2026-08-25:** `[feature.platform-image-pip]` as an *installer* is superseded by
> `spec-platform-image-one-pixi-env`. Acceptance criteria below are historical (this story shipped).

<intent-contract>

## Intent

**Problem:** `src/platform/requirements/{base,local,production}.txt` still share authority with `[feature.platform-ci-test]` / platform-dev pixi features (guarded by `platform-ci-test-requirements-check`). CAP-5 (`spec-platform-fifteen-factors`) requires pixi.toml as the sole dependency authority — CI lanes and Containerfiles build from pixi alone; requirements files retired; docs updated.

**Approach:** Invert the current mirror: make pixi features the only source of truth for platform Python deps; delete or stop consuming `src/platform/requirements/*.txt`; retarget CI / Containerfile / docs / drift guard so nothing installs via `pip install -r` for the platform host. Suites stay green. Borrow MIT notices if any reference pattern is copied.

## Acceptance Criteria

- Given the platform host tree, when searching for install consumers of `src/platform/requirements/*.txt`, then none remain (`pip install -r` / CI pip backend / Containerfile grep of those files are gone).
- Given Platform CI's `test` job and both Containerfile builder stages, when dependencies are installed, then resolution is via pixi features/envs only.
- Given docs and operator scripts that formerly taught the requirements chain, when read after the change, then they cite pixi features (`platform-ci-test`, `platform-dev` / `python-agent-platform`, `platform-image-pip`).
- Given the former requirements→pixi drift guard, when the story lands, then it is removed or rewritten so pixi is the authority (guard against resurrected requirements txts is OK).
- Given related platform / local-recipes tests, when run, then they are green.
- Given the epic boundary, when this story ships, then 16.2–16.5, steward 12-7, and Epic 17 are untouched.

## Boundaries & Constraints

**Never:** Touch AD-4/pap:AD-17 topology or the 12.1 chart contract (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal 20-2. Skip 12-7 forever.

</intent-contract>

## Code Map

- `src/platform/requirements/{base,local,production}.txt` — delete; leave README tombstone pointing at pixi features
- `pixi.toml` — `[feature.platform-ci-test]` (CI authority), new `[feature.platform-image-pip]` (Containerfile `--no-deps` layer authority); retarget/remove `platform-ci-test-requirements-check` / `fix-platform-ci-test-requirements` tasks
- `scripts/platform_ci_test_requirements_check.py` — rewrite as pixi-authority guard (no requirements→pixi reconciler) or remove + update `tests/scripts/test_platform_ci_test_requirements_check.py`
- `scripts/platform_image_pip_layer.py` — emit pip-layer pins from `[feature.platform-image-pip.pypi-dependencies]` for Containerfile
- `.github/actions/platform-test-setup/action.yml` + `.github/workflows/platform-ci.yml` — pixi-only; drop `PLATFORM_TEST_BACKEND=pip` / workflow_dispatch pip choice
- `src/platform/Containerfile` — stop grepping requirements txts; install pip layer via emitter script
- `src/platform/utility/install_python_dependencies.sh` — stop `pip install -r requirements/local.txt`; point at pixi
- Comment-only call sites: `src/platform/config/urls.py`, `src/platform/tests/meta/test_no_pyforge_import.py`, `src/platform/tests/test_langflow_mount.py`

## Tasks & Acceptance

**Execution:**
- `src/platform/requirements/*.txt` — delete the three authority files; add README tombstone citing pixi features — CAP-5 retirement
- `pixi.toml` — add `[feature.platform-image-pip.pypi-dependencies]` with the Containerfile pip-layer pins (base∪production minus conda-provided + image extras); rewrite platform-ci-test comments; replace requirements-check tasks with pixi-authority guard task — sole authority
- `scripts/platform_ci_test_requirements_check.py` (+ tests) — rewrite: fail if resurrected `base|local|production`.txt exist; drop `--fix` requirements→pixi mutator — invert mirror
- `scripts/platform_image_pip_layer.py` — new emitter reading platform-image-pip from pixi.toml — Containerfile consumer
- `.github/actions/platform-test-setup/action.yml` — pixi-only setup; remove pip backend steps — CI from pixi alone
- `.github/workflows/platform-ci.yml` — remove PLATFORM_TEST_BACKEND / pip workflow_dispatch; always use pixi — CI from pixi alone
- `src/platform/Containerfile` — call emitter instead of grepping requirements txts; refresh comments — image from pixi alone
- `src/platform/utility/install_python_dependencies.sh` — refuse legacy pip-r path; instruct `pixi install -e platform-ci-test` (or platform-dev) — no install consumer
- Docs/comments in urls.py + two tests — cite pixi features — docs updated

**Acceptance Criteria:**
- Given a clean checkout, when `rg -n 'pip install -r .*requirements/(base|local|production)'` is run over platform CI/Containerfile/scripts, then there are no matches.
- Given `pixi run -e local-recipes platform-ci-test-requirements-check` (or its replacement task name), when requirements txts are absent, then exit 0; when a resurrected `base.txt` is present, then exit non-zero.
- Given `python scripts/platform_image_pip_layer.py`, when run, then stdout lists pinned packages drawn only from `[feature.platform-image-pip]`.
- Given platform unit/meta tests that mentioned requirements/local.txt, when run under `platform-ci-test`, then they pass.

## Verification

- `rg` — no install consumers of retired requirements txts
- `pixi run -e local-recipes platform-ci-test-requirements-check` (rewritten guard) — exit 0
- `python -m pytest tests/scripts/test_platform_ci_test_requirements_check.py -q` — green
- `python scripts/platform_image_pip_layer.py | head` — emits pins
- Platform comment-touched tests as available in env


## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/682
Merge SHA: bec9707bf87aed6a8c4c763e5390e9793d3ab0ff
Notes: pixi is sole platform dependency authority; requirements txts retired; CI/Containerfile/docs retargeted; suites green.
