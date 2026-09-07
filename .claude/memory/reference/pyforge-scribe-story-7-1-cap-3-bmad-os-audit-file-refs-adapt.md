---
name: "pyforge-scribe-story-7-1-cap-3-bmad-os-audit-file-refs-adapt"
description: "pyforge-scribe Story 7.1 (CAP-3): bmad-os-audit-file-refs adapted pass over docs/reference/ -- 13 files audited, 7 stal…"
metadata:
  type: reference
---

pyforge-scribe Story 7.1 (CAP-3): bmad-os-audit-file-refs adapted pass over docs/reference/ -- 13 files audited, 7 stale-reference violations across 5 files, 8 files clean.

Method: extracted backtick-wrapped path-like tokens from all docs/reference/*.md (skipping fenced code blocks), checked each against the live repo tree, and classified true violations vs. deliberate historical/generated-output mentions -- adapted from bmad-os-audit-file-refs's convention (built for src/bmm|src/core|src/utility) since docs/reference/ has no {project-root}/_bmad/ convention of its own; the check here is simply "does the referenced path exist."

Violations found (file:line -> broken reference -> real target):
- developer-guide.md:438 -> `docs/library-llms-full.md` -> real path is docs/reference/library-llms-full.md (missing reference/ segment)
- mcp-server-architecture.md:33 -> `docs/enterprise-deployment.md` -> real path is docs/reference/enterprise-deployment.md (missing reference/ segment)
- enterprise-deployment.md:321 -> `docs/pixi-config-jfrog.example.toml` -> real path is docs/reference/pixi-config-jfrog.example.toml (missing reference/ segment)
- github-workflows.md:46 and :60 -> `scripts/linter.py` -> real path is .github/workflows/scripts/linter.py (missing .github/workflows/ prefix; confirmed against staged-recipes-linter.yml's actual invocation); also github-workflows.md:85 -> `recipes/example-v1/recipe.yaml` -> no such path ever existed in this repo's tracked history, real v1-format example lives at recipes/examples/recipe.yaml
- test-charter.md:274 and :326 -> `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md` -> real filename is test-architecture.md (no "-tea" suffix); also test-charter.md:328 -> `_bmad-output/projects/pyforge-herald/planning-artifacts/tea-playwright-addendum.md` -> file does not exist anywhere in the repo

5 distinct files carry violations: developer-guide.md, mcp-server-architecture.md, enterprise-deployment.md, github-workflows.md, test-charter.md. The other 8 audited files are clean: README.md, airgap-distribution-contract.md, antigravity-developer-startup.md, conda-forge-packaging-inventory-operations_prompt.md, conda-forge-packaging-inventory-operations_replay.md, container-base-layer-convention.md, library-llms-full.md, station-verify-commands.md.

Deliberate historical/non-violation mentions excluded (verified, not flagged): conda-forge-packaging-inventory-operations_{prompt,replay}.md's retired docs/Analysis_Dataset-2026-08-12.xlsx workbook references (Story 23.9 workbook-free path) and their derived/*.parquet pipeline-output paths (generated at run time, not committed); github-workflows.md's own explicit "removed as orphans" list (scripts/create_feedstocks[.py], scripts/print_tokens.py, scripts/linter_make_comment.py, .github/workflows/README.md); library-llms-full.md's gitignored runtime paths (.claude/data/conda-forge-expert/vdb/, build_artifacts/); station-verify-commands.md's `core/gate.py::check_spec_binding` module-shorthand (resolves to a real function in pyforge-marshal's src/pyforge/marshal/core/gate.py).

Remediation is explicitly out of pyforge-scribe Story 7.1's scope (proves the scribe routing + capture loop, not a docs cleanup) -- these 5 findings are left for a follow-up docs-fix task.
