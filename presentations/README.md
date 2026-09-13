# presentations/ — the deck family

One folder per deck (`pyforge-<slug>/`), each mirroring a Claude Design project
("PyForge <Name> deck") and carrying the same artifact family: deck prototype,
built React deck, exec summary, infographic trio, marp sources, pptx exports.

**Before editing anything here, read
[`docs/specs/presentation-deck.md`](../docs/specs/presentation-deck.md)
§ *Artifact dependency tree & editing surfaces*** — it defines which file is
each branch's head, where text vs. visual design gets edited, how edits
propagate, and the pull-to-git discipline. Per-deck `README.md`s hold the
Design-project sync ledgers (project IDs, etags).

**Infographic posters** (`project/<Name> Infographic standalone.html`) follow the standard in
[`spec-deck-family-currency/infographic-standard.md`](../_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/infographic-standard.md)
— six acts, full depth, inline diagrams, every fact a `facts.yaml` row (Unifying Strategy =
structure, Warden = visual form).
