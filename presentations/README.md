# presentations/ — the deck family

One folder per deck (`pyforge-<slug>/`), each mirroring a Claude Design project
("PyForge <Name> deck") and carrying the same artifact family: deck prototype,
built React deck, exec summary, infographic trio, marp sources, pptx exports.
Three presentation twins outside that `pyforge-*` naming — `agentic-sdlc/`,
`six-quarter-roadmap/`, `llm-knowledge-bases/` — each still resolves through
`registry.py`'s `read()` (their own `README.md`'s § *Design project* section)
but do not follow the deck-family build pipeline; see each one's own
`README.md` for what it actually contains.

**Before editing anything here, read
[`docs/specs/presentation-deck.md`](../docs/specs/presentation-deck.md)
§ *Artifact dependency tree & editing surfaces*** — it defines which file is
each branch's head, where text vs. visual design gets edited, how edits
propagate, and the pull-to-git discipline. Per-deck `README.md`s hold the
Design-project sync ledgers (project IDs, etags).

**To sync the whole family (or one deck), run `herald deck sync-all [--slug
<slug>] [--dry-run]`** (pixi: `deck-sync-all`) rather than the individual steps by
hand — see `docs/how-to/presentation-deck.md` § *The MCP bridge*.

**Infographic posters** (`project/<Name> Infographic standalone.html`) follow the standard in
[`spec-deck-family-currency/infographic-standard.md`](../_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/infographic-standard.md)
— six acts, full depth, inline diagrams, every fact a `facts.yaml` row (Unifying Strategy =
structure, Warden = visual form).

## Design systems (mirrored libraries, `_design-systems/`)

`Modernist`, `Broadsheet`, and `Nocturne` are Claude Design **design-system**
projects (`type: PROJECT_TYPE_DESIGN_SYSTEM`) the decks bind to, not decks
themselves — mirrored byte-exact into `presentations/_design-systems/<name>/`
(`spec-design-sync-loop` CAP-2, Story 23.2) rather than given a deck twin,
ledger, or Pages page. They never resolve through `registry.read` (that
section is scoped to a deck's own single bridge, per `registry.py`'s module
doc) — classification is by exact project name alone
(`registry.DESIGN_SYSTEM_PROJECT_NAMES`). No deck glob (`presentations/
pyforge-*/…`, the three non-`pyforge-*` twins above) matches this home, and
`scripts/fleet_scan.py`'s `scan_pitch()` skips it explicitly, so it is never
scored against the 6-artifact deck-family standard.

Each library's binary assets (a `.thumbnail`, one `assets/*.jpg`) are not
mirrored — `read_file` cannot return binary content at all; every text,
token, and component file is.

| Design system | Home | Design project |
|---|---|---|
| Modernist | `_design-systems/modernist/` | [`fbc1d6c8-b35f-4df6-9044-a64d2675427b`](https://claude.ai/design/p/fbc1d6c8-b35f-4df6-9044-a64d2675427b) |
| Broadsheet | `_design-systems/broadsheet/` | [`8952a2f6-0865-443d-8758-e903057208d5`](https://claude.ai/design/p/8952a2f6-0865-443d-8758-e903057208d5) |
| Nocturne | `_design-systems/nocturne/` | [`13076e88-3749-49f8-9989-8c6df7328d70`](https://claude.ai/design/p/13076e88-3749-49f8-9989-8c6df7328d70) |

## Excluded projects (never twinned)

Every Design project the signed-in account can see that is intentionally excluded from the
twin-per-deck loop (`spec-design-sync-loop` CAP-1, Story 23.1) — reconciled by an *exact* match
against this table's `Project` column, never a name heuristic.

| Project | Reason |
|---|---|
| REMOVED-PyForge Unifying Strategy | ad-hoc duplicate Design project (found live proving Story 21.11's pull loop); superseded by the correctly Modernist-bound "PyForge Unifying Strategy deck", renamed with a `REMOVED-` prefix to mark it retired rather than deleted |
| Local recipes repository connection | stale hand-mirrored copy of `presentations/pyforge-atlas/`'s own repo tree — the CAP-3 `stale_mirror` cautionary fixture (`bridge-protocol.md` § Pilot evidence), never a real bridge project |
