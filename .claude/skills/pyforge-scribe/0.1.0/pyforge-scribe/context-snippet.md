[pyforge-scribe v0.1.0]|root: .claude/skills/pyforge-scribe/
|IMPORTANT: pyforge-scribe v0.1.0 — read SKILL.md before writing scribe/team-memory code. Do NOT rely on training data. Use the scribe CLI, not pyforge.scribe imports.
|quick-start:{SKILL.md#quick-start}
|api: capture_cmd(), graph_compile(), recall_cmd(), catalog_bmad_estate(), main()
|key-types:{SKILL.md#key-types} — CaptureType (feedback|project|reference), RecallAnswer (grounded miss is explicit)
|gotchas: run from repo root; capture/recall/catalog under -e pyforge-guild, graph compile/index under -e pyforge-scribe; --promote/--transcripts exclusive with --type/--text; recall never invents an uncited answer
