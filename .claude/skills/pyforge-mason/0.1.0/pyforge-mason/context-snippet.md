[pyforge-mason v0.1.0]|root: .claude/skills/pyforge-mason/
|IMPORTANT: pyforge-mason v0.1.0 — read SKILL.md before mason work. Do NOT rely on training data. Use pyforge mason grammar, not pyforge.mason imports; the MCP face runs recipe build only. Recipe knowledge lives in conda-forge-expert.
|quick-start:{SKILL.md#quick-start}
|api: main(), build_parser() — recipe {new,validate,build,diagnose,optimize,scan,submit,update} · package {build,ship} · environment {lock,check} · doctor
|key-types:{SKILL.md#key-types} — six global flags (flag → MASON_* env → default); exits 0/1/2/3/130
|gotchas: run from repo root; doctor always exits 0 (gaps are data); ship and submit dry-run without --yes; ship exit 0 is not shipped (read each state); recipe update writes; do not replace conda-forge-expert
