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

## Excluded projects (never twinned)

Every Design project the signed-in account can see that is intentionally excluded from the
twin-per-deck loop (`spec-design-sync-loop` CAP-1, Story 23.1) — reconciled by an *exact* match
against this table's `Project` column, never a name heuristic.

| Project | Reason |
|---|---|
| REMOVED-PyForge Unifying Strategy | ad-hoc duplicate Design project (found live proving Story 21.11's pull loop); superseded by the correctly Modernist-bound "PyForge Unifying Strategy deck", renamed with a `REMOVED-` prefix to mark it retired rather than deleted |
| Local recipes repository connection | stale hand-mirrored copy of `presentations/pyforge-atlas/`'s own repo tree — the CAP-3 `stale_mirror` cautionary fixture (`bridge-protocol.md` § Pilot evidence), never a real bridge project |
