---
title: "dbgpt-client sqlalchemy cap admits Python 3.14"
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
  - "docs/specs/db-gpt-conda-forge.md"
  - "recipes/db-gpt/recipe.yaml"
  - ".claude/skills/conda-forge-expert/SKILL.md"
warnings:
  - "Rule 1: invoke `conda-forge-expert` first. G26 case study is DB-GPT itself: the `dbgpt-core` / `dbgpt-ext` build scripts already sed `==` pins in `pyproject.toml`; this cap lives on `dbgpt-client` and needs the same treatment or `pip check` fails."
  - "`docs/specs/db-gpt-conda-forge.md` is TERMINAL for BMAD (consume-not-submit, G58). This story is a feedstock maintainer-edit, not a re-run of that spec."
deferred:
  - "Upstream: ask DB-GPT to lift `sqlalchemy <2.0.29` (the platform already runs 2.0.52 with dbgpt core and serve)."
---

<intent-contract>

## Intent

**Problem:** `dbgpt-client` (in `conda-forge/db-gpt-feedstock`) pins
`sqlalchemy >=2.0.25,<2.0.29`; that range has no `cp314` build. `dbgpt-app` (the
platform's DB-GPT sidecar) requires `dbgpt-client`, so the sidecar image cannot move
to 3.14 even though `dbgpt` and `dbgpt-serve` solve clean there (measured
2026-09-02). Steward 43.6 is blocked on this.

**Approach:** Loosen the cap to `sqlalchemy >=2.0.25,<2.1` on `dbgpt-client`, patch
the wheel METADATA the same way the core/ext outputs already do (G26), runtime-validate
`dbgpt-app` against sqlalchemy 2.0.5x (the sidecar's own SQLite metadata store and the
REST round-trip `dbgpt_integration/tasks.py` drives), land as a maintainer-edit PR,
mirror into `recipes/db-gpt/`, and re-verify with a `pixi lock` probe
(`python=3.14.* + dbgpt + dbgpt-serve + dbgpt-app + django`).

## Acceptance Criteria

- Given the feedstock recipe, when read, then `dbgpt-client`'s sqlalchemy run-dep is
  `>=2.0.25,<2.1` with a `# TODO: tighten if upstream re-caps` comment, and the
  `dbgpt-client` build script applies the METADATA patch.
- Given the built outputs, when `pip check` runs on 3.12 and 3.14, then it passes.
- Given `pixi lock` on `python = "3.14.*" + dbgpt + dbgpt-serve + dbgpt-app + django`,
  when run against the published build, then it solves.
- Given the sidecar image rebuilt on 3.14, when the platform's Celery task drives a
  DB-GPT REST round-trip, then it succeeds and the sidecar's SQLite metadata store
  initialises.
- Given `docs/specs/db-gpt-conda-forge.md` § Current State, when updated, then it
  records the loosening with the feedstock PR number.

## Boundaries & Constraints

**Always:**
- `BMAD_ACTIVE_PROJECT=pyforge-mason`; physical paths.
- `conda-forge-expert` first; convention + G26 authoritative.
- Maintainer-edit on `conda-forge/db-gpt-feedstock`.
- Keep the `fastapi <0.113` pin as is (it is why the sidecar exists; not this story).
- Rule 2 retro at closeout.

**Never:**
- Re-run BMAD against `docs/specs/db-gpt-conda-forge.md`.
- Fold `dbgpt-app` into `python-agent-platform` (disjoint fastapi ranges, AD-14 Pattern B).

</intent-contract>

## Code Map

- `recipes/db-gpt/recipe.yaml` — `dbgpt-client` output run-deps + build script
- `conda-forge/db-gpt-feedstock` — the PR
- `src/platform/compose/dbgpt/Containerfile` — consumer (no change here)

## Tasks

- [ ] Invoke `conda-forge-expert`; confirm G26 patch shape on the client output.
- [ ] Feedstock PR; local build + `pip check` on 3.12 and 3.14.
- [ ] Sidecar runtime validation on 3.14.
- [ ] Mirror into `recipes/db-gpt/`; `pixi lock` probe green.
- [ ] Spec Current State + Rule 2 retro.

## Verification

`pixi run -e local-recipes recipe-build recipes/db-gpt`; the 3.14 probe;
`pixi run -e pyforge-mason pyforge-mason-test`.
