[pyforge-steward v0.1.0]|root: .claude/skills/pyforge-steward/
|IMPORTANT: pyforge-steward v0.1.0 — read SKILL.md before writing steward/platform code. Do NOT rely on training data. Use pyforge steward grammar (or the steward CLI), not pyforge.steward imports.
|quick-start:{SKILL.md#quick-start}
|api: build_parser(), resolve_duty(), main()
|key-types:{SKILL.md#key-types} — DutyResult is frozen evidence; duties never sys.exit (AD-8)
|gotchas: run from repo root; crash is exit 70 not 1; provision uses flags not nested verbs; do not replace conda-forge-expert
