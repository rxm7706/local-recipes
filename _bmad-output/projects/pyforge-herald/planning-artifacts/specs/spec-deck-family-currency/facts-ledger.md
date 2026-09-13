# The fact ledger — `presentations/<slug>/facts.yaml`

Companion to `SPEC.md` (CAP-2, CAP-5). One file per deck, tracked in git, re-derived on demand.
The poster is authored *from* this file; the advisory check reads the poster *against* it.

## Shape

```yaml
deck: pyforge-marshal
persona: "PyForge Marshal"       # the poster filename's prefix
derived_at: "2026-09-13T01:50:22-05:00"   # HEAD commit date (not wall-clock), so an unchanged tree re-derives identically
tree: "ac3761abc550fdf25374618235a07793e6a719b3"   # HEAD sha; suffixed "-dirty" when tracked files were uncommitted at derive time
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
| Fleet totals — stories, epics, and one pair of per-station rows on every deck | the tracked `sprint-status-ledger.yaml` of every guild-roster station (never `fleet-picture`, a report over Tier-3 feeds that can differ) | parse with `parse_sprint_status`; stories = non-`epic-` keys, epics = `epic-N` keys minus `-retrospective`, `done` is the literal (fleet-picture infers epics-done from stories, so the two may differ by design) |
| Station story / epic counts | `_bmad-output/projects/pyforge-<station>/planning-artifacts/sprint-status-ledger.yaml` | same parser, per project |
| Station package version | `src/shared/packages/pyforge-<station>/pyproject.toml` | `version =` |
| BMAD core / bmad-loop versions | `_bmad/_config/manifest.yaml`; `pixi.lock` | manifest `installation.version`; the single locked `bmad-loop` conda package version (omitted when the lock holds more than one) |
| conda-forge-expert skill version | `.claude/skills/conda-forge-expert/SKILL.md` frontmatter | `version:` |
| MCP tool count, atlas phases, pixi envs, schema version, gotcha max | `pixi run -e local-recipes bmad-groundtruth` | JSON keys |
| Capability counts and status | `_bmad-output/projects/<slug>/planning-artifacts/specs/spec-<x>/SPEC.md` | capability *definition* lines in the spec's own id scheme (`- **CAP-N**` or `- **HER-N**`), never prose mentions; frontmatter `status` |
| Dream status | `docs/dreams/<slug>.md` frontmatter | `status:` |
| CLI verbs | the module named by the station's `[project.scripts]` console entry, or its whole `cli/` sub-package | distinct literal `add_parser("<verb>")` first arguments (static scan) |
| Test counts | `pixi run -e pyforge-<station> pytest --collect-only -q` in the station's own env | last line `N tests collected` |
| Dates | the poster's own `git log -1`, HEAD's commit date, and every dated entry of the deck's Dream Realization log | `poster_last_commit_date`, `tree_commit_date`, one `dream_log_<date>` row per entry; a date outside the chain stays `unmarked` by design |
| Feedstock / recipe counts (Mason) | `recipes/` directory and the atlas `my_feedstocks` surface | count; name the surface used |

## Derivation, check and refresh

`pixi run -e local-recipes deck-facts <slug>` re-derives `presentations/<slug>/facts.yaml`
(canonical implementation `scripts/deck_facts.py`, the `deck_export.py` precedent: one script,
one pixi task, no CFE three-place rule since it is not a conda-forge-expert script).
`--check` reads the poster's visible text, sweeps `n/n`, `x.y.z` (optional leading `v`) and
`YYYY-MM-DD` tokens, checks every `data-fact="<id>"` mark, and reports: `unmarked` (a swept token
with no row), `mismatch` (a mark whose text is not the row's value or a `shown_as` literal),
`drifted` (a row whose live re-derivation differs), `unsourced` (a row the current run could not
derive), and `unshown` (a row neither marked nor shown). Bare integers and status words are not
swept — mark them. Output is one line per finding plus a summary; exit code is always 0
(advisory — SPEC.md constraint). The README
ledger's "facts n/n" cell is the check's resolved-over-shown count on the day of the rebuild.

`--refresh` (CAP-6, Story 20.14) re-derives the ledger, then rewrites every plain `data-fact`
mark whose text is neither the fresh row's `value` nor one of its `shown_as` literals. The
replacement keeps the OLD literal's shape: the previous ledger's `value` maps to the fresh
`value`, its `shown_as[k]` to the fresh `shown_as[k]`; when the old text is in neither (the
ledger was already re-derived, or the row is new) the first fresh literal with the same digit
pattern is used (`848 of 878` → `852 of 878`), else the fresh `value` — the result is always one
of the fresh row's own literals, never an invented one. A leading `v` is restored. Marks whose
span holds another tag, sit inside comments / `<script>` / `<style>` / `<title>`, carry HTML
entities, or have no row are reported as `skipped <id> <reason>` and left alone. Lines:
`refreshed <id> "<old>" -> "<new>"`, `skipped <id> <reason>`, `summary <slug>: N refreshed, M
skipped`; exit 0 always. `--refresh --check` runs the check afterwards. The standing currency
sweep is: land a ledger-moving change → `deck-facts <slug> --refresh --check` per rebuilt deck →
re-push the rewritten posters → commit.
