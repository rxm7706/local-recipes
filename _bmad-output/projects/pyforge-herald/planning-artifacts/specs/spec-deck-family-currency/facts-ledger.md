# The fact ledger — `presentations/<slug>/facts.yaml`

Companion to `SPEC.md` (CAP-2, CAP-5). One file per deck, tracked in git, re-derived on demand.
The poster is authored *from* this file; the advisory check reads the poster *against* it.

## Shape

```yaml
deck: pyforge-marshal
persona: Marshal
derived_at: 2026-09-13T09:00:00Z
tree: e4eec92bd9                 # git rev the values were derived at
facts:
  - id: stories_done_total
    value: "248/249"
    source: _bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml
    method: count story keys by status via the real parser (parse_sprint_status), retros excluded
    shown_as: ["248/249", "248 of 249"]   # the literal tokens the poster may use for this row
  - id: bmad_core_version
    value: "6.12.0"
    source: _bmad/_config/manifest.yaml
    method: top-level version
```

Rules: `id` is stable snake_case; `value` is a string exactly as shown; `source` is a tracked
path or a pixi task name, never a gitignored Tier-3 path and never another poster; `method`
says how the value was read; `shown_as` lists every literal the poster may print for the row
(default: the value itself). A fact the derivation cannot source is dropped from the poster,
not guessed.

## Source catalog

| Fact class | Source | Method |
|---|---|---|
| Fleet totals — stories, epics, per-station rows | `pixi run -e local-recipes fleet-picture` (read-only) and the eight tracked `sprint-status-ledger.yaml` files | parse with `parse_sprint_status`; count `done` vs total story keys; roll-up `epic-N` rows for epics |
| Station story / epic counts | `_bmad-output/projects/pyforge-<station>/planning-artifacts/sprint-status-ledger.yaml` | same parser, per project |
| Station package version | `src/shared/packages/pyforge-<station>/pyproject.toml` | `version =` |
| BMAD core / suite versions | `_bmad/_config/manifest.yaml`; suite module pins in `pixi.toml` | manifest `version`; pixi dependency pin |
| conda-forge-expert skill version | `.claude/skills/conda-forge-expert/SKILL.md` frontmatter | `version:` |
| MCP tool count, atlas phases, pixi envs, schema version, gotcha max | `pixi run -e local-recipes bmad-groundtruth` | JSON keys |
| Capability counts and status | `_bmad-output/projects/<slug>/planning-artifacts/specs/spec-<x>/SPEC.md` | distinct `CAP-N`; frontmatter `status` |
| Dream status | `docs/dreams/<slug>.md` frontmatter | `status:` |
| CLI verbs | the station's `cli.py` (or `cli/__init__.py`) | `add_parser("<verb>")` set |
| Test counts | `pixi run -e pyforge-<station> pytest --collect-only -q` in the station's own env | last line `N tests collected` |
| Dates (rulings, ships, merges) | `git log` on the cited file, or the Dream's Realization log entry | the entry's own date |
| Feedstock / recipe counts (Mason) | `recipes/` directory and the atlas `my_feedstocks` surface | count; name the surface used |

## Derivation and check

`pixi run -e local-recipes deck-facts <slug>` re-derives `presentations/<slug>/facts.yaml`
(canonical implementation `scripts/deck_facts.py`, the `deck_export.py` precedent: one script,
one pixi task, no CFE three-place rule since it is not a conda-forge-expert script).
`--check` reads the poster, tokenizes every number / version / status literal, resolves each
to a row via `shown_as`, and reports: unresolved tokens (a fact with no row), rows whose live
re-derivation differs from the file, and rows the poster no longer shows. Output is one line per
finding plus a summary; exit code is always 0 (advisory — SPEC.md constraint). The README
ledger's "facts n/n" cell is the check's resolved-over-shown count on the day of the rebuild.
