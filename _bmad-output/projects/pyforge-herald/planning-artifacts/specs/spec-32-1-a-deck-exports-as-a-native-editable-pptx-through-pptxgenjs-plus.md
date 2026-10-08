---
title: '32.1: A deck exports as a native, editable pptx through pptxgenjs-plus'
type: 'feature'
created: '2026-09-28'
status: 'ready-for-dev'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.herald.deck_export_native
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need feature-flag-governance:CAP-5 (steward); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: 'herald deck pptx-native stays listed as disabled and exits 2; decks export through marp --pptx and the python-pptx fill only, as today'
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-28-2-a-new-export-replaces-the-version-it-supersedes.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/exporters.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py
  - recipes/pptxgenjs-plus/recipe.yaml
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every standard `.pptx` export comes from `marp --pptx` (`scripts/deck_export.py`),
which writes image-only slides and needs Chrome. A presenter who opens one in PowerPoint cannot
edit its text. The python-pptx fill (Story 15.1) is editable but needs a hand-written content plan,
and only pyforge-warden has one. `pptxgenjs-plus >=4.2.1` is packaged (`recipes/pptxgenjs-plus`)
but sits only in `[feature.local-recipes.dependencies]` (`pixi.toml:2089`). The operator ruled on
2026-09-28 that `pptxgenjs-plus` becomes an *additional* export kind, native and editable, beside
`marp --pptx` and the python-pptx fill, and that neither of those retires.

**Approach:**
- A fourth export plugin, `PptxgenjsExportPlugin` (format id `pptxgenjs`), registers on
  `DECK_EXPORT_HOOK_SPEC` beside marp, pptx and dc.html (Epic 16).
- `pyforge.herald.pptx_native` derives a slide model from the deck's current Marp source,
  `<slug>-deck-<date>.md` (the file `marp --pptx` reads): per slide, the title, bullets, tables and
  speaker notes. It writes the model as JSON and calls a Node driver shipped as herald package
  data, `node/pptx_native.mjs`.
- The driver renders the model with `pptxgenjs-plus` as native text boxes, tables and notes,
  resolved through `NODE_PATH=$CONDA_PREFIX/lib/node_modules`.
- The output is its own dated kind, `src/pptx/<slug>-deck-native-<date>.pptx`, so it never
  supersedes the Marp export. After a successful write, `retire_superseded` (Story 28.2) retires
  the older version of that kind.
- `herald deck pptx-native <slug>` runs it, behind `pyforge.herald.deck_export_native`.
- `pptxgenjs-plus >=4.2.1` joins `[feature.pyforge-guild.dependencies]`, where Node already comes
  in through the python feature. It also joins `[feature.pyforge-herald.dependencies]`, with
  `nodejs` at the python feature's spec, so `pyforge-herald-test` runs the driver instead of
  skipping it (D7).

Ledger key: `32-1-a-deck-exports-as-a-native-editable-pptx-through-pptxgenjs-plus`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-28.2.

### Living CAP citations

- `spec-pyforge-herald` CAP-57 (FR-10.6; decision D7 in `.memlog.md`); AD-3 (amended 2026-09-28 (night)); CAP-53 (the kind rule and `retire_superseded`).
- canopy:AD-21 (hooks and plugins: a new format is another plugin).
- `feature-flag-governance:CAP-1`.
- Kinship, not a dependency: mason Story 21.5 (the `pptxgenjs-plus-jsx` recipe, needed only for JSX-authored decks).

## Acceptance Criteria

- Given the flag ON and a fixture deck When `pixi run -e pyforge-guild herald deck pptx-native <slug>` runs Then it exits 0 and writes `src/pptx/<slug>-deck-native-<date>.pptx`
- Given that file When python-pptx reads it Then it has one slide per Marp slide, titles and bullet text as text frames, tables as table graphic frames, the speaker notes in each notes slide, and no picture shape standing in for a slide
- Given a second run on a later date When it finishes Then exactly one version of the `-deck-native` kind remains
- Given the Marp and pptx-fill exports When the story lands Then they are byte-unchanged
- Given the flag OFF When `herald --help` and `herald deck pptx-native <slug>` run Then the verb is listed as disabled and exits 2 with a "flag off" message, writing nothing
- Given `pixi.toml` When it is read Then `pptxgenjs-plus >=4.2.1` is in `[feature.pyforge-guild.dependencies]` and `[feature.pyforge-herald.dependencies]`, and `environment.yaml` was regenerated in the same PR

## Tasks

- [ ] Read `pyforge.herald.deck_export_native` through `pyforge.core.flags.read_boolean` (steward Story 75.1); if 75.1 is unlanded, add it to `pyforge.core` in exactly 75.1's shape
- [ ] `pptx_native.py`: the Marp-to-slide-model parser (stdlib), the JSON handoff, the Node call, `retire_superseded`
- [ ] `node/pptx_native.mjs` as package data; declare it in the package build
- [ ] `PptxgenjsExportPlugin` in `exporters.py`
- [ ] `cli.py`: `herald deck pptx-native <slug>` behind the flag
- [ ] `pixi.toml` hand edit, then `pixi lock`; `pixi project export conda-environment -e build > environment.yaml`
- [ ] `src/platform/config/flags.json`: `pyforge.herald.deck_export_native`, `defaultVariant` off
- [ ] Tests: the slide model, a fixture render read back with python-pptx, the ON/OFF test
- [ ] `pixi run -e pyforge-guild pyforge-station-tests` before the push (AGENTS.md checklist item 7)
- [ ] Spec-surface reconcile for every Spec the detector names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- **The flag reader** (coordinator ruling 2026-09-28): `herald deck pptx-native` reads `pyforge.herald.deck_export_native` through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract (`75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`). If 75.1 has not landed when this story runs, add it to `pyforge.core` in exactly 75.1's shape -- `read_boolean(key, default=False)` in `src/shared/packages/pyforge-core/src/pyforge/core/flags.py`: it resolves the tree as `cutover_root.resolve_flags_path` does, returns False for `state: DISABLED`, returns the `defaultVariant`'s value when it is a bool, and reads False with a named WARN on stderr for a missing tree, a missing key or a non-bool value, never True; with `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, reconciled on `spec-pyforge-core` -- and never write a station-local reader.
- The `pixi.toml` change is a hand edit followed by `pixi lock`, because the pre-shell hook refuses a live `pixi add` or `pixi update`. `environment.yaml` is regenerated in the same PR, and `pyforge-station-tests` runs before the push, since the shared-surface rule fires every station suite in CI.
- The export runs from the Guild env; station code names `-e pyforge-guild`, never `-e local-recipes`.
- Retire only after a successful write, and only the older version of the `-deck-native` kind (Story 28.2's rule).
- The PR carries the `maintenance` label.

**Never:**
- Do not write a station-local flag reader, and do not parse the flag tree from herald code.
- Do not change `marp --pptx`, `PptxTemplateExporter`, the python-pptx fill or their outputs.
- Do not render slides as images, and do not require Chrome.
- Do not add a mason dependency or edit a mason file; `pptxgenjs-plus-jsx` is out of scope.
- Do not remove `pptxgenjs-plus` from `[feature.local-recipes.dependencies]`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| plain deck | title and bullets per slide | one native slide each, text frames | exit 0 |
| table | a Markdown table on a slide | a table graphic frame | exit 0 |
| notes | `<!-- speaker notes -->` blocks | text in the notes slide | exit 0 |
| image-only slide | a slide with only an image | the image placed as a picture on a native slide, with its title if any | exit 0 |
| second day | `-deck-native-<older>.pptx` exists | only the new file remains | exit 0 |
| Node missing | `node` not on PATH | named error, nothing written | exit 1 |
| driver fails | `pptxgenjs-plus` throws | named error, nothing retired | exit 1 |
| no Marp source | a slug without `<slug>-deck-<date>.md` | named refusal | exit 1 |
| flag OFF | any | verb listed as disabled; "flag off" | exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-57 (FR-10.6; D7).
Architecture: AD-3 (amended 2026-09-28 (night)).
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `32-1-a-deck-exports-as-a-native-editable-pptx-through-pptxgenjs-plus`.
Ledger status at mint: `backlog`.
Deps: S-28.2 (`retire_superseded`). Not blocked on mason.
Flag: `pyforge.herald.deck_export_native` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-28.2 • **FR/AD:** spec-pyforge-herald CAP-57 (FR-10.6; D7); AD-3 (amended 2026-09-28 (night)) • flag: `pyforge.herald.deck_export_native`

**Given** every standard `.pptx` comes from `marp --pptx` as image slides that need Chrome, and `pptxgenjs-plus` sits only in the `local-recipes` env
**When** the plugin, the Node driver, the verb and the environment change land
**Then** `pixi run -e pyforge-guild herald deck pptx-native <slug>` exits 0 on a fixture deck and writes `<slug>-deck-native-<date>.pptx`; python-pptx reads it back with one slide per Marp slide, titles and bullet text as text frames, tables as table graphic frames, speaker notes in each notes slide, and no picture shape standing in for a slide; a second run on a later date leaves one version of the kind; the Marp and pptx-fill exports are byte-unchanged
**And** with the flag OFF the verb is listed as disabled and exits 2 with a "flag off" message; `environment.yaml` is regenerated in the same PR; `pyforge-station-tests` and `pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; the slide-model tests, the fixture render read back with python-pptx and the ON/OFF test run inside it).

**Manual checks:**
- ON/OFF: the flag test writes two flagd trees (one with `pyforge.herald.deck_export_native` ON, one OFF), like `src/platform/tests/test_openfeature_file_flags.py`, and asserts the verb writes ON and exits 2, listed as disabled, OFF. Replace it with the testing-kit fixture once `feature-flag-governance:CAP-4` lands.
- `pixi run -e pyforge-guild herald deck pptx-native pyforge-herald` on the real deck, then open the file in PowerPoint or LibreOffice and edit a title.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` and `pixi.lock` changed).
- `pixi project export conda-environment -e build > environment.yaml`, then `git diff --exit-code environment.yaml` after committing it — expected: no further change.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log
