---
title: "langflow-base onnxruntime pin admits Python 3.14"
type: "feature"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_revision: "637f4158"
review_loop_iteration: 0
followup_review_recommended: false
context:
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-43-5-one-interpreter-story.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md"
  - "docs/specs/langflow-conda-forge.md"
  - "recipes/langflow-base/recipe.yaml"
  - ".claude/skills/conda-forge-expert/SKILL.md"
warnings:
  - "Rule 1: invoke `conda-forge-expert` before touching the recipe or running recipe tooling. G26 applies — loosening a run-dep does not change the wheel METADATA; with `pip_check` the source pyproject must be patched too."
deferred:
  - "Upstream: ask langflow to drop the `onnxruntime <1.24; python_version < \"3.14\"` split (it exists for a magika win32 quirk already handled by `magika !=0.6.3`)."
---

<intent-contract>

## Intent

**Problem:** `langflow-base` (recipe line 376, `conda-forge/langflow-feedstock`) pins
`onnxruntime >=1.20,<1.24`. Upstream 1.12.0 declares
`onnxruntime<1.24,>=1.20; python_version < "3.14"` and
`onnxruntime>=1.26; python_version >= "3.14"`; a `noarch: python` recipe cannot carry
the marker, so the feedstock collapsed to the low branch and silently dropped 3.14.
conda-forge has no `cp314` onnxruntime below 1.25.1. Measured 2026-09-02: this is the
**only** remaining langflow blocker to a 3.14 solve (bcrypt was loosened by steward
10.4). Tracked as steward `DW-FU-10-4`.

**Approach:** Per the project pin-loosening convention and G26: (1) run-dep becomes
`onnxruntime >=1.20` (no cap) so the solver picks the newest available per
interpreter (1.28 on 3.12, ≥1.25.1 on 3.14); (2) patch the source `pyproject.toml`
at build time so the wheel METADATA carries the same single range for both
markers, or `pip check` on 3.14 will demand `>=1.26` and on 3.12 will demand
`<1.24`; (3) runtime-validate: `import langflow.main`, the magika/markitdown path,
and the platform's Langflow `/health` on both 3.12 and 3.14. Land as a
maintainer-edit PR on the feedstock, mirror into `recipes/langflow-base/`, and
re-verify with a real `pixi lock` probe (`python=3.14.* + langflow + dbgpt + django`).

## Acceptance Criteria

- Given the feedstock recipe, when read, then the `onnxruntime` run-dep is
  `>=1.20` with a `# TODO: tighten once upstream drops the py<3.14 cap` comment, and
  the build script patches both marker branches in `pyproject.toml` (and `PKG-INFO`
  if present) to the same range.
- Given the built package, when `pip check` runs in the test phase on 3.12 and
  3.14, then it passes.
- Given `pixi lock` on `python = "3.14.*" + langflow >=1.11.4 + dbgpt + django`
  (linux-64 and osx-arm64), when run against the published build, then it solves.
- Given `import langflow.main` and the markitdown → magika path on 3.14, when
  executed, then they import and a document conversion round-trips.
- Given `docs/specs/langflow-conda-forge.md` and steward `DW-FU-10-4`, when updated,
  then the addendum records the loosening and the DW entry is `resolved` with the
  feedstock PR number.

## Boundaries & Constraints

**Always:**
- `BMAD_ACTIVE_PROJECT=pyforge-mason`; write under
  `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
- `conda-forge-expert` skill invoked first; its pin-loosening convention and G26
  are authoritative over this spec.
- Maintainer-edit on `conda-forge/langflow-feedstock` (you are a maintainer);
  never a staged-recipes resubmission.
- Rule 2 retro at closeout lands in the CFE skill CHANGELOG.

**Never:**
- Drop `noarch: python` or split per-interpreter builds to express the marker.
- Loosen anything else "while here" (the `mcp <2.0` pin is upstream's and stays).
- Vendor onnxruntime.

</intent-contract>

## Code Map

- `recipes/langflow-base/recipe.yaml:376` — the run-dep
- `recipes/langflow-base/` build script — G26 pyproject patch
- `conda-forge/langflow-feedstock` — the PR
- `docs/specs/langflow-conda-forge.md` — addendum

## Tasks

- [ ] Invoke `conda-forge-expert`; confirm the convention and G26 shape.
- [ ] Feedstock PR: run-dep + METADATA patch; local `rattler-build` + `pip check` on 3.12 and 3.14.
- [ ] Runtime validation on 3.14 (import, markitdown/magika, platform `/health`).
- [ ] Mirror into `recipes/langflow-base/`; `pixi lock` probe green.
- [ ] `DW-FU-10-4` resolved; spec addendum; Rule 2 retro.

## Verification

`pixi run -e local-recipes recipe-build recipes/langflow-base` (3.12 and 3.14
variants); the 3.14 `pixi lock` probe; `pixi run -e pyforge-mason pyforge-mason-test`.
