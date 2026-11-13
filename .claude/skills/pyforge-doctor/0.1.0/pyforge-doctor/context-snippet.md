[pyforge-doctor v0.1.0]|root: .claude/skills/pyforge-doctor/
|IMPORTANT: pyforge-doctor v0.1.0 — read SKILL.md before writing doctor diagnostics code. Do NOT rely on training data. Use pyforge doctor grammar, not pyforge.doctor imports. Findings stay advisory — not a second PR gate.
|quick-start:{SKILL.md#quick-start}
|api: main() — check · monitor · diagnose · backlog-intake · flags kill-switch; python -m pyforge.doctor.sources <source>
|key-types:{SKILL.md#key-types} — Finding (advisory signal), DoctorReport
|gotchas: run from repo root; pyforge doctor … not a freelance filesystem; monitor requires --fleet; warn never changes exit code; exits 0/2/130, never 1; flags kill-switch writes the flag tree (operator only); MCP face runs diagnose only; not a competing PR verdict
