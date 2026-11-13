---
title: "51.1: No dossier figure is typed: every stats band and the scale table are counted at build"
type: 'fix'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate   # the measurer and the schema refusal are the build's gate on what the dossier may show; a flag-off path would be the typed-figure path this story ends (spec-feature-flag-governance Q1). Story 43.5 put the measurer behind Epic 43's shared flag, which Story 43.7 retired; no herald flag gates the dossier today
difficulty: heavy
story: '51.1'
spec: pyforge-herald
surface:
  - docs-site/scripts/verify_claims.py
  - docs-site/src/loaders/dossier-loader.ts
  - docs-site/src/content.config.ts
  - docs-site/src/content/dossier/dossier.yml
  - src/shared/packages/pyforge-herald/tests/meta/pages_astro.py
  - src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py
  - src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/dreams/pyforge-herald.md
  - docs-site/scripts/verify_claims.py
  - docs-site/src/loaders/dossier-loader.ts
  - docs-site/src/content.config.ts
  - docs-site/src/content/dossier/dossier.yml
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-52.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** 31 of the dossier's 42 stats and the whole § 09.6 scale table are typed, so stale figures reach the page:
'47 / 12', '15 duties', 4,049 lines for core (audit SHOULD: stale typed figures, part of MUST 7). The measurer is the
build's gate on dossier figures, but it counts only `src_lines`. spec-pyforge-herald CAP-46, as the mint amended it
on 2026-11-10, says every band figure and every scale-table row is counted at build and the build refuses a typed
stat.

**Approach:** This story widens what the measurer counts, makes the build refuse a typed stat, and brings the bands
and the table under it in the same change, because the refusal cannot land before the content conforms.

- **The measurer** (`verify_claims.py`) gains only closed, structural counts. Each is a static read under `--root`:
  plain filesystem, no git call, so a fixture root that is not a work tree measures the same way.
  1. `stories_epics`, for a station section, read from
     `_bmad-output/projects/pyforge-<id>/planning-artifacts/sprint-status-ledger.yaml`: `development_status` keys
     shaped `<E>-<S>-…` at `done`, over `epic-<n>` keys at `done`. Retrospective keys are ignored.
  2. The hero keys `fleet_test_lines`, `fleet_stories_epics` and `stations`, beside `fleet_src_lines`.
  3. A table block carrying `check: src_lines`: each row's `section:` (a station id or `core`; `core` resolves to
     `pyforge-core`) supplies its Source-lines and Files cells.
- **No free-form key.** There is no `count: {glob, pattern}` key: a pattern over another station's source can publish
  0 as a measured figure when that station renames a symbol.
- **The loader** (`dossier-loader.ts`) applies the measured rows beside `applyMeasured`. **The schema**
  (`content.config.ts`) gains one refusal: a stat with no `check:`, in the hero or in a stats block.
- **`dossier.yml`**, this story's part only: the hero `stats:`, each section's `stats` block, and the § 09.6 table's
  `check:` and `section:` keys and counted cells.
  - Every station band becomes the same four counted tiles: lines and files, test lines, stories / epics done, and
    the Python floor. The hero gets four: stations, lines, test lines, stories / epics.
  - Of the 31 typed tiles, three gain a key (the hero's Stations, atlas's floor, herald's stories / epics). The 28
    that nothing can count leave the band. The operator accepted this on 2026-11-10 (second addendum).
  - No typed figure is added anywhere to replace them. Their facts stay where the section prose already states them,
    under that section's `measured:` date.
  - The prose, the Shape column and every other block are Story 51.2's.
- **The fixture tree.** In `tests/meta/pages_astro.py`, `station_packages` also writes each station's fixture ledger
  with known counts and returns them, and plants `pyforge-core`. `fixture_tree` is otherwise unchanged, so every
  existing fixture build keeps passing.
- **Environments and workflows.** The `site` env still needs PyYAML only. `pages.yml`'s path filter lists neither
  station source nor the sprint ledgers, so no workflow request is filed: Story 102.2's daily refresh bounds how old a
  counted figure can be, and every page names its build.
- **Out of scope.** The `src/shared/packages` literal at `verify_claims.py:91` stays (`DW-herald-52-2-1`).
- **Markers.** `test_verify_claims_emit.py` and `test_one_generator.py` carry the `live_tree` marker from Story 52.1,
  hence the dependency. This story adds no read of the live tree to a Python test.

Ledger key: `51-1-no-dossier-figure-is-typed-every-stats-band-and-the-scale-table-are-counted-at-build`.
Type / Effort / Deps: fix (`flag-exempt: detector-or-gate`) / L / S-52.1.

## Boundaries & Constraints

**Always:**
- Keep the measurer's keys closed and structural, and make every read static under `--root`.
- Make the refusals exit non-zero, naming the section, the label or the key.
- Keep bespoke Python under `docs-site/` below 300 lines (herald:AD-23; `test_one_generator.py:129`).

**Never:**
- Never add a free-form pattern key, never type a figure to replace a removed tile, and never call git from the
  measurer.
- Never touch the dossier's prose, the Shape column or any other block (Story 51.2's).
- Never write `SPEC.md` or the PRD; CAP-46 and FR-12.5 were amended at mint, and Story 50.2 writes the reconcile
  line.

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — The capability text precedes the code.**
  `grep -c 'stories_epics' _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`.
  Expected: prints at least `1` (the mint's CAP-46 amendment). A `0` blocks the story.
- **AC2 — The measurer's new keys are covered, on fixture trees.**
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py -q`.
  Expected: exit 0, with these new cases:
  - `stories_epics` reads '3 / 1' from a fixture ledger that also holds one `backlog` story, one `blocked` story and
    an `epic-1-retrospective: optional` key, none of them counted;
  - a station with no ledger exits 2, naming the section;
  - `fleet_test_lines`, `fleet_stories_epics` and `stations` are emitted under `fleet`;
  - a table block with `check: src_lines` is emitted under `rows`, with lines and files per `section:`;
  - `core` resolves to `pyforge-core`;
  - a checked table row with no `section:` exits 2 naming it, and so does an unknown key.
- **AC3 — The live dossier measures, with every new key present.** Expected: exit 0, with eight station sections and
  nine scale-table rows (the stations and `pyforge-core`).

```bash
pixi run -q -e site python docs-site/scripts/verify_claims.py --emit "${TMPDIR:-/tmp}/herald-claims.json" && python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('TMPDIR','/tmp'),'herald-claims.json'))); need={'src_lines','test_lines','python_floor','stories_epics','fleet_src_lines','fleet_test_lines','fleet_stories_epics','stations','rows'}; assert need<=set(d), sorted(need-set(d)); assert len(d['stories_epics'])==8 and len(d['rows'])==9, (len(d['stories_epics']),len(d['rows']))"
```

- **AC4 — Every stat is checked, and so is the scale table.** Every stat in the hero and in every stats block carries
  `check:`, and the scale table is a checked table whose rows each name a section. Expected: exit 0, printing
  `1 []`.

```bash
python3 - <<'EOF'
import yaml,sys
d=yaml.safe_load(open('docs-site/src/content/dossier/dossier.yml'))
bad=[('hero',s['label']) for s in d['stats'] if 'check' not in s]
tables=0
for sec in d['sections']:
    for b in sec.get('blocks',[]):
        if b['type']=='stats': bad+=[(sec['id'],s['label']) for s in b['stats'] if 'check' not in s]
        if b['type']=='table' and b.get('headers',[])[:2]==['Station','Source lines']:
            tables+=1
            if b.get('check')!='src_lines': bad.append((sec['id'],'scale table has no check'))
            bad+=[(sec['id'],r['cells'][0]) for r in b['rows'] if 'section' not in r]
print(tables,bad); sys.exit(1 if bad or tables!=1 else 0)
EOF
```

- **AC5 — The build shows what was counted and refuses a typed stat.**
  `HERALD_DOCS_SITE_REQUIRED=1 pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py -q -k '43_5 or typed_stat or scale_table'`.
  Expected: exit 0:
  - the existing `test_43_5_*` cases pass over `fixture_tree`, which now plants one `sprint-status-ledger.yaml` per
    station and a `pyforge-core` package;
  - a new case shows that the stories / epics tile and the scale-table cells equal the planted counts;
  - a fixture dossier with one stat lacking `check:` fails the build, naming the section and the label.
- **AC6 — The stale typed tiles are gone.**
  `git grep -nE '47 / 12|Duties \(README documents 6\)|Claims this pass found stale|MCP server routes found in-source|Claims reverified, all holding' -- docs-site/src/content/dossier/dossier.yml`.
  Expected: exit 1 (no match).
- **AC7 — Bespoke Python under `docs-site/` stays under 300 lines.** `cat docs-site/scripts/*.py | wc -l`. Expected:
  a number below 300 (175 before this story).
- **AC8 — The site builds, and the built-site suite and lint gate hold.**
  `pixi run -e site pages-check && HERALD_DOCS_SITE_REQUIRED=1 pixi run -e pyforge-herald pyforge-herald-test-built && pixi run -e pyforge-guild lint-types`.
  Expected: exit 0.
- **AC9 — Post-condition, run by steward:S-124.2.**
  `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`.
  Expected: exit 0 once steward-station has added the station sprint ledgers to herald's trigger paths. Before that
  it fails by design, naming exactly the difference this story introduced.

</intent-contract>

## Binding

- Capability: spec-pyforge-herald CAP-46 (amended 2026-11-10 at mint: dossier figures are counted from the tree at
  build; `(ready 2026-11-10; amended 2026-11-10: Story 51.1)` until this story lands, and Story 50.2 flips it). FR-12.5
  ← CAP-61, CAP-46 (amended in place). herald:AD-23 bounds the measurer (no AD moves).
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry. Ruling: the operator accepted the
  removal of the 28 typed tiles (2026-11-10, second addendum).
- Epic 51. Ledger key `51-1-no-dossier-figure-is-typed-every-stats-band-and-the-scale-table-are-counted-at-build`.
- Cross-station: steward:S-124.2 (herald's trigger paths gain the station sprint ledgers). It is a post-condition, not
  a gate.
- Findings closed: SHOULD: stale typed figures.

## Spec Change Log

- 2026-11-10: minted (backlog) with the CAP-46 amendment and FR-12.5's amended arrow. The design drops the reviewed
  plan's free-form `count:` key.
- 2026-11-10: status set to blocked (forward dependency on a later epic; unblocked only with operator confirmation).
