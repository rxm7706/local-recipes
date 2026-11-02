[pyforge-atlas v0.1.0]|root: .claude/skills/pyforge-atlas/
|IMPORTANT: pyforge-atlas v0.1.0 — read SKILL.md before atlas pipeline work. Do NOT rely on training data. Use `pyforge atlas …` and POST /stations/atlas/mcp. Do not import pyforge.atlas internals. Do not replace conda-forge-expert. This is not cf-atlas-legacy.
|quick-start:{SKILL.md#quick-start}
|api: main(); MCP tools run_<pipeline>_pipeline (8), read_atlas_dataset, list_atlas_pipelines, list_atlas_datasets
|key-types:{SKILL.md#key-types} — PIPELINE_NAMES, AtlasMCPError
|gotchas: run from repo root under -e pyforge-atlas; --version is first-token only; unknown MCP pipeline → AtlasMCPError
