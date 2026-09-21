# `pixi.toml` compose to apply (Phase 1)

This PR's primary doc is [`pyforge-foundry-full-sbom.md`](./pyforge-foundry-full-sbom.md).

The `pixi.toml` env line change (large-file upload via API hit size/auth limits in this agent session).
Apply this on branch `sbom/pyforge-foundry-full-compose` (or follow-up commit):

```toml
# pyforge-foundry-full (steward Story 63.5 + SBOM 2026-09-21): estate SBOM / bill of materials —
# one solved, locked, checkable closure for every station/library surface PLUS recipe-generation
# and local-build tooling. Composes the prior station union with build + grayskull + crm +
# conda-smithy. Deliberately NOT the fat `local-recipes` feature (~200 library pins). Channel gaps
# (SelfExplainML BMAD/caveman/kedro-skills, pip sqlite-vec, herald/atlas npm) remain declared here
# but are not "on conda-forge" until Phase 3 feedstocks — see docs/foundry/pyforge-foundry-full-sbom.md.
# Several GB; install deliberately (`pixi install -e pyforge-foundry-full`), never by default.
pyforge-foundry-full = { features = ["python", "pyforge-guild", "guild-tasks", "pyforge-core", "pyforge-testing-kit", "pyforge-marshal", "pyforge-steward", "pyforge-atlas", "pyforge-warden", "pyforge-doctor", "pyforge-mason", "pyforge-herald", "pyforge-scribe", "build", "grayskull", "crm", "conda-smithy"], no-default-feature = true }
```

Replace the existing `pyforge-foundry-full = { features = [...] }` block (and its comment) with the above.
Then refresh lock: `pixi lock` / `pixi install -e pyforge-foundry-full` (watch `crm`/`click` solve).
