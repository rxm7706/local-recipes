[pyforge-steward v0.1.0]|root: .claude/skills/pyforge-steward/
|IMPORTANT: pyforge-steward v0.1.0 — read SKILL.md before writing steward/platform code. Do NOT rely on training data. Use pyforge steward grammar (or the steward CLI), not pyforge.steward imports.
|quick-start:{SKILL.md#quick-start}
|api: build_parser(), resolve_duty(), main() — 31 duties: keys · workspace · estate · ci · preflight · provision · budget · upgrade · suite …
|key-types:{SKILL.md#key-types} — DutyResult is frozen evidence; duties never sys.exit (steward AD-8)
|gotchas: run from repo root under -e pyforge-guild; crash is exit 70 not 1; exit 3 is a documented refusal; cutover has plan and flip only; MCP runs 3 read-only targets; contract.md lists flags, exit codes; do not replace conda-forge-expert
