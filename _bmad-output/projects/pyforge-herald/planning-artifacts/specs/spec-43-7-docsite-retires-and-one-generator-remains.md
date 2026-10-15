---
title: '43.7: docsite/ retires and one generator remains'
type: 'feature'
created: '2026-10-14'
status: 'done'
flag-exempt: flag-infrastructure   # the story retires the flag that gated Epic 43, pyforge.herald.pages_one_generator (spec-feature-flag-governance Q2)
retires-flag: pyforge.herald.pages_one_generator   # doctor Story 34.7's retirement path: the owner's story declares it
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-1-astro-renders-the-dossier-from-dossier-yml.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-3-astro-assembles-the-artifact-mounts-redirects-and-search.md
  - docsite/README.md
  - docsite/build.py
  - docsite/tools/assemble_pages.py
  - docsite/tools/verify_claims.py
  - docsite/content/dossier.yml
  - docsite/content/site.yml
  - docs-site/README.md
  - docs-site/scripts/sidebar_from_map.py
  - docs-site/astro.config.mjs
  - docs/map.yaml
  - pixi.toml
  - environment.yaml
  - AGENTS.md
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/flag-inventory/pyforge-herald.md
  - scripts/.spec-surface-baseline.json
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py
  - src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After Stories 43.1 to 43.6 every herald page renders through Astro behind
`pyforge.herald.pages_one_generator`, and the Jinja renderer (`docsite/build.py`, 883 lines on 2026-10-14), the
assembler (`docsite/tools/assemble_pages.py`, 720), the templates, the vendored fonts and the `dist/` second build path
still exist for the flag's off state. Two generators remain in the tree, the `docsite` / `docs-site` name clash
remains, and the foundry (B) would rebuild both from the Spec. The design-thinking success metrics for M3 are one
top-level site directory, under 300 bespoke lines, and `docsite/` gone.

**Approach:** the Jinja path, the assembler, the second build path and the `docsite/` directory go; the content moves
beside the generator; the nav comes from doctor's registry.

- **Deleted.** `docsite/build.py`, `docsite/tools/assemble_pages.py` (and the 300-line cross-origin scanner inside it),
  every template under `docsite/templates/`, `docsite/assets/` (the fonts, their sha256 table, `_dossier.css`,
  `_site-chrome.css`), and `docsite/README.md` after its still-true content (the block types, the refresh rituals of
  Stories 39.1 and 41.1) folds into `docs-site/README.md`. `docsite/tools/ci_surfaces_tile.py` and the export scripts
  go with the Jinja path once their Astro readers exist (Stories 42.1, 43.1).
- **Moved.** `docsite/tools/verify_claims.py` to `docs-site/scripts/`; `docsite/content/dossier.yml` and the other
  content YAML to `docs-site/src/content/` (the dossier at `docs-site/src/content/dossier/`), with the Story 43.1
  loader re-pointed; the committed `ci-status.json` snapshot (CAP-59) and the gitignored build inputs
  (`fleet-status.json`, the exports) to the location the generator reads. The `docsite` / `docs-site` name clash ends
  without a rename.
- **The nav from the registry.** `docs-site/scripts/sidebar_from_map.py` reads `docs/map.yaml` `sections:` (doctor
  Story 48.1, `pyforge-doctor:CAP-90`) for the Herald, Status, Pipelines, Dashboards and Changes entries beside the
  four quadrants; `site.yml`'s nav list retires, and every prefix's menu comes from the one registry (AD-21 amended
  2026-10-14: one registry). The home's four doors (Docs, Overview, Status, Decks; the design preview the operator
  approved on 2026-10-14) are generated from the same registry.
- **The tasks.** `site`, `site-check`, `site-verify` and `site-serve` leave `pixi.toml`; `pages-build` and `pages-check`
  stay and `pages-check` is the one build check. `environment.yaml` is regenerated in the same PR (expected
  byte-identical); `pyforge-station-tests` runs because `pixi.toml` changed.
- **The flag.** `pyforge.herald.pages_one_generator` leaves `flags.json` and every overlay; its reader leaves the herald
  package; the flag inventory regenerates.
- **The budget.** `wc -l` over `docs-site/**/*.py` is under 300. On 2026-10-14 `sidebar_from_map.py` alone is 297 lines
  and `verify_claims.py` is 237, so the budget is met by moving the sidebar and nav generation into the generator
  (TypeScript reading `docs/map.yaml` at build) or shrinking both scripts, with Story 43.3's origin check (under 40) and
  the `publicDir` population script inside the same 300.
- **The record.** `spec-pyforge-herald`'s `surface:` loses `docsite/**` through a memlog entry and the script render
  (never a hand edit of `SPEC.md`); `scripts/.spec-surface-baseline.json` is re-stamped scoped; `AGENTS.md`'s citation
  of `docsite/content/dossier.yml` (§ *Where things are*, Cutover state) moves to the new path, and `scribe`'s
  instruction-surface parity test and `governance-currency` stay green.

Ledger key: `43-7-docsite-retires-and-one-generator-remains`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / 43.2, 43.3, 43.4, 43.5, 43.6, doctor 48.1 (`docs/map.yaml` `sections:`).

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.4): `docsite/` dissolves, the content moves, the nav comes from the registry,
  one generator remains under 300 bespoke lines. AD-23's rule (one generator; bespoke Python under `docs-site/` stays
  under 300 lines) and AD-21 amended 2026-10-14 (one registry orders every prefix).
- **`pyforge-doctor:CAP-90`** (Story 48.1): `docs/map.yaml` `sections:`. Read as data.
- **`spec-feature-flag-governance` Q2 and Q4**: `flag-exempt: flag-infrastructure`; the owning station files the
  removal — this is it.
- **`spec-pyforge-scribe` CAP-27** (one `AGENTS.md`, pointers elsewhere): the citation moves, the parity test judges.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("`build.py`, `assemble_pages.py`, the
  Jinja templates and `docsite/` retire, the dossier content moving to `docs-site/src/content/dossier/` ... Done when
  `docsite/` is gone and the bespoke Python under `docs-site/` is under 300 lines"); design-thinking § *Success
  Metrics* (M3: < 300 bespoke lines, 1 top-level site dir); `brainstorm-intent.md` § M3, Retired.

## Acceptance Criteria

- **AC1 — `docsite/` is gone** (oracle amended 2026-10-15, the independent review). `git ls-files docsite | wc -l`
  and `git ls-files --others --exclude-standard docsite | wc -l` each print 0, and `.gitignore` holds `/docsite/`: a
  checkout that merged the deletion keeps its ignored leftovers, so `test -e docsite` no longer judges it.
- **AC2 — The content lives beside the generator.** `docs-site/src/content/dossier/` holds the dossier YAML and the
  Story 43.1 loader reads it there; `grep -rn "docsite/" docs-site/src docs-site/scripts docs-site/astro.config.mjs`
  finds nothing.
- **AC3 — The nav from the registry.** Given `docs/map.yaml` with `sections:` for Herald, Status, Pipelines, Dashboards
  and Changes, Then the docs sidebar, the shared top menu and the home's doors list those entries in the registry's
  order, and a fixture registry with one entry added shows it in all three with no other edit; `site.yml` has no `nav`
  list (or no `site.yml` remains).
- **AC4 — The tasks.** `grep -c 'tasks\.site\]\|tasks\.site-check\]\|tasks\.site-verify\]\|tasks\.site-serve\]' pixi.toml`
  prints 0; `tasks.pages-build]` and `tasks.pages-check]` remain; `environment.yaml` regenerated and byte-identical to
  the committed file (or committed if not).
- **AC5 — The flag is gone.** `flags.json` and every overlay environment hold no `pyforge.herald.pages_one_generator`;
  no module under `src/shared/packages/pyforge-herald/src/` reads it; the flag inventory is regenerated;
  `flag-gate-check` exits 0.
- **AC6 — The budget.** `find docs-site -name '*.py' -not -path '*/node_modules/*' | xargs wc -l | tail -1` reports a
  total under 300.
- **AC7 — Every URL.** The built artifact holds every URL the 2026-10-13 artifact held — `/`, `/herald/`,
  `/herald/dossier/`, `/herald/infographics/`, `/herald/decks/<slug>/` for the ten families, `/dashboard/kedro-viz/` when
  the export is present, the 44 redirect paths and `/kedro-viz/` — plus `/status/`, `/status/ci/`, `/status/runs/`,
  `/changes/`, `/changes/rss.xml`, `/llms.txt`, `/llms-full.txt` and `/facts.json` (CAP-61's success list); a test
  enumerates the list and fails naming any missing path.
- **AC8 — The five files.** The five vendored upstream files keep their recorded hashes; `grep -rl
  'fonts.googleapis\|cdn\.' docs-site/build/site` finds nothing.
- **AC9 — The record.** `AGENTS.md` cites the dossier at its new path and names no `docsite/`; `scribe`'s
  `test_instruction_surface_parity.py` passes; `pixi run --frozen -e pyforge-guild governance-currency` exits 0;
  `spec-surface-check` exits 0 after the memlog names every moved and deleted path and the scoped stamps.
- **AC10 — The gates.** `pixi run --frozen -e site pages-check`, `pixi run --frozen -e site docs-site-validate`,
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` and `pixi run --frozen -e pyforge-guild
  pyforge-station-tests` exit 0.

## Boundaries & Constraints

**Always:**
- Land only after Stories 43.2 to 43.6 are `done` and doctor Story 48.1 is `done` on `main`
  (`git merge-base --is-ancestor` on its merge commit); until then `site.yml`'s list stands.
- Keep every URL (AC7) and the 44 redirects (operator ruling 2026-10-13); `docs/` never moves.
- Keep the five vendored files byte-identical (AD-21 rule 5); everything else under `docs-site/` is herald's and counts
  toward the 300 lines.
- Route the `SPEC.md` surface change through the memlog and the script render; stamp scoped for every Spec the detector
  names (`spec-pyforge-herald`; the co-governors of `pixi.toml`, `AGENTS.md`, the flag tree and `src/` as named).
- Regenerate `environment.yaml` and run `pyforge-station-tests` because `pixi.toml` changed (AGENTS.md § Policy and
  pre-PR item 7); the PR carries the `maintenance` label.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not rename `docs-site/` (the brainstorm's rule: never rename `docs-site/`; the clash ends by dissolving `docsite/`).
- Do not edit `docs/map.yaml` `sections:` (doctor's) or `docs/MAP.md`; name a needed row in the report.
- Do not keep a Jinja template, a `dist/` path or a `site-*` task "for safety"; the flag's off state ends here.
- Do not hand-edit `SPEC.md`, `sprint-status-ledger.yaml` or `scripts/.spec-surface-baseline.json` outside a scoped
  stamp.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| full build | the tracked tree + fixture export | every URL of AC7; one generator; `docsite/` absent | exit 0 |
| registry gains an entry | fixture `map.yaml` `sections:` | sidebar, top menu and doors show it | exit 0 |
| registry lacks `sections:` | `map.yaml` as before doctor 48.1 | — | build exit 1, names the key (the story waits on 48.1) |
| a `docsite/` path still referenced | planted import | — | AC2's grep fails; `governance-currency` reds a stale citation |
| `site-check` still declared | regression in `pixi.toml` | — | AC4 fails |
| bespoke Python over budget | 300 lines or more | — | AC6 fails |
| the flag key still present | regression | — | AC5 fails |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.4), minted 2026-10-14; works with
  `pyforge-doctor:CAP-90`; supersedes CAP-44's and CAP-52's two-generator shape.
- Architecture: AD-23 (adopted 2026-10-14) and AD-21 amended 2026-10-14 (one registry).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.7.
- Ledger key: `43-7-docsite-retires-and-one-generator-remains`.
- Ledger status at mint: `backlog`.
- Deps: Stories 43.2, 43.3, 43.4, 43.5, 43.6 (station-local) and doctor Story 48.1 (`docs/map.yaml` `sections:`),
  `done` on `main` before this story's PR opens. Named here and in `epics.md`, never as a `blocked` row. `marshal
  factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: none — `flag-exempt: flag-infrastructure` (`spec-feature-flag-governance` Q2); retires
  `pyforge.herald.pages_one_generator`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 43.2, 43.3, 43.4, 43.5, 43.6, doctor 48.1 (`docs/map.yaml` `sections:`) • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.4), AD-23; retires the `pyforge.herald.pages_one_generator` flag
**Flag:** none — `flag-exempt: flag-infrastructure` (`spec-feature-flag-governance` Q2): the story retires the flag that gated Epic 43

**Given** Stories 43.1 to 43.6 render every herald page through Astro behind the flag, and doctor Story 48.1 has given
`docs/map.yaml` its `sections:` list
**When** the story lands
**Then** `docsite/` does not exist; the dossier and site content live under `docs-site/src/content/`; the nav of every
prefix comes from `docs/map.yaml`; no `site`, `site-check`, `site-verify` or `site-serve` task remains and
`pages-check` is the one build check; the flag and its reader are gone; `wc -l` over `docs-site/**/*.py` is under 300;
the five vendored files keep their hashes
**And** the built artifact holds every URL the 2026-10-13 artifact held plus the new prefixes (CAP-61's success list);
`AGENTS.md` cites the dossier at its new path; `spec-surface-check`, `governance-currency`, `pages-check`,
`docs-site-validate` and `pyforge-herald-test` exit 0; `scribe`'s instruction-surface parity test is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `git merge-base --is-ancestor <doctor 48.1 merge commit> origin/main; echo $?` — expected: 0 before the PR opens.
- `pixi run --frozen -e site pages-check` — expected: exit 0 (AC7, AC8, AC10).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `find docs-site -name '*.py' -not -path '*/node_modules/*' | xargs wc -l` — expected: total under 300 (AC6).
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0 (AC5).
- `pixi project export conda-environment -e build > environment.yaml` then `git diff --stat -- environment.yaml` — expected: empty (byte-identical) or committed.
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` — expected: exit 0 (`pixi.toml` changed; the shared-surface rule).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` (or its meta subset) — expected: `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` passes (AC9).
- `pixi run --frozen -e pyforge-guild governance-currency` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `uv run _bmad/scripts/memlog.py append --workspace _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald --type event --text "Surface reconcile <date>: docsite/** leaves the surface ..."`, the script render of `SPEC.md`'s `surface:`, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec pyforge-herald/spec-pyforge-herald` and one scoped stamp per co-governor the detector names, then `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Re-add a `tasks.site-check` entry to `pixi.toml` — expected: AC4 fails.
- Remove the Changes entry from a fixture registry — expected: AC3's three-menu test fails naming the entry.
- Restore one `.woff2` under `docsite/assets/fonts/` and `git add -f` it — expected: AC1 fails (an ignored leftover
  alone does not, by design: `/docsite/` is ignored; the review's AC1 oracle, see the change log).

### Verification run (2026-10-15)

On the Pages branch at `ffb2fb8801` plus this change, from the worktree root, each command alone, each verdict read
from its exit code:

- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- exit 0: 2001 passed, 5 skipped (the live claude-design
  and daphne opt-ins). The story's own files:
  `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py` 25 passed (the built tests ran: docs-site was
  installed), `src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py`,
  `src/shared/packages/pyforge-herald/tests/unit/test_docs_site_nav.py`,
  `src/shared/packages/pyforge-herald/tests/unit/test_status_pages_flag_states.py`,
  `src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py`.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- exit 0: 2813 passed, 2 skipped (the trigger map
  included).
- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests -n auto` -- exit 0: 3789 passed,
  1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` -- exit 0: 1618 passed, 28 skipped.
- `pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py` -- exit 0: 161
  passed; `pixi run --frozen -e pyforge-scribe pytest
  src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` -- exit 0: 32 passed (AC9).
- `pixi run --frozen -e site pages-check` -- exit 0 three times: the flags off and no build input; the status pages and
  the tile on with the fixture inputs (`fleet-status.json` and Story 43.6's three) and CI's variables; and for a second
  host (`PAGES_HOST_BASE_URL=https://pages.ghe.example`, `PAGES_HOST_BASE_PATH=/org/local-recipes`: every link under
  `/org/local-recipes/`). The fixture inputs were removed afterwards.
- `pixi run --frozen -e site docs-site-validate` -- exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0. `flag-gate-check` -- exit 0 (0 fail, the retired key read
  nowhere). `flag-inventory` -- exit 0 (herald's report kept; the others, unchanged in substance, left as committed).
- `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` -- exit 0 (1352 passed, 14 skipped; the flag tree and
  the platform's flag pin moved).
- `find docs-site -name '*.py' -not -path '*/node_modules/*' | xargs wc -l` -- 175 (AC6).
- `pixi project export conda-environment -e build` -- byte-identical to `environment.yaml` (`cmp` exit 0; AC4).
- `pixi run --frozen -e pyforge-guild detectors-ci` -- exit 1 on `spec-surface` alone: `spec-pyforge-scribe` drift
  (`AGENTS.md` changed; its memlog has not moved) and `spec-pyforge-herald`'s drift-presumed warnings and its stale
  `docsite/**` glob -- the surface reconcile the orchestrator runs at the end. `governance-currency`, `docs-map-hygiene`,
  `docs-currency`, `chain-completeness`, `dream-chain`, `flag_gate_check`, `ad_citation_check` (after the base finding
  above was fixed) pass.
- **Mutations, each restored:** a `tasks.site-check` entry added to `pixi.toml` -- `test_ac4_...` fails; the `changes`
  row removed from `docs/map.yaml` -- `test_the_live_registry_gives_the_three_menus_in_its_order` fails naming
  `["Changes", "changes/"]` (the fixture-registry case is `test_ac3_one_registry_edit_..._drop`); a `.woff2` restored
  under `docsite/assets/fonts/` -- `test_ac1_docsite_is_gone` fails.
- **In the browser** (the flag-on artifact served under `/local-recipes/`, 1280x900 and 375x812, light and dark): the
  docs home shows the doors (Docs with its quadrants, Herald with Overview, Dossier, Infographics and Decks, Status,
  Changes), each link under the base path; the top menu is Docs, Overview, Dossier, Infographics, Decks, Status, Changes
  on every page; the dossier renders measured numbers in the dark theme; a family page shows its three previews and its
  downloads; `/status/` shows the eight stations with their bars and the attention list, `/status/ci/` 63 rows with
  `live` last, `/changes/` the five fixture merges; `/llms.txt` lists the docs, the herald pages, ten infographics and
  ten families; the search dialog finds the dossier and the theme toggle works under the CSP, no violation reported; at
  375 px the home has no horizontal scroll. One request fails, as before this story: each deck view twin's `support.js`
  (§ *Named, not fixed here*).
- Not run here: `pyforge-station-tests` (all eight suites; herald, steward, doctor, core's flag tests and the platform
  ran above) and `pr-preflight` -- the orchestrator's push gates, after the surface reconcile.

### Verification run (2026-10-15, the independent reviews resolved)

On the Pages branch at `fa6e11d4e4` plus the review fixes, from the worktree root, each command alone, each verdict read
from its exit code:

- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- exit 0: 2030 passed, 5 skipped. New or widened:
  `src/shared/packages/pyforge-herald/tests/meta/test_herald_pages_model.py` (4, node only),
  `src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py` (93),
  `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py` (29, the built tests ran).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- exit 0: 2813 passed, 2 skipped; the trigger map alone
  (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`) -- exit 0, 45 passed.
- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests -n auto` -- exit 0: 3789 passed,
  1 skipped. `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` -- exit 0: 1618 passed, 28 skipped.
- `pixi run --frozen -e site pages-check` -- exit 0 three times: the flags off and no build input; the status pages and
  the tile on with the fixture inputs and CI's variables (the inputs removed afterwards); the second host
  (`PAGES_HOST_BASE_URL=https://pages.ghe.example`, `PAGES_HOST_BASE_PATH=/org/local-recipes`). Every page now passes
  the per-page script check; the docs root's CSP meta follows `<meta charset>`.
- `pixi run --frozen -e site docs-site-validate` -- exit 0; its three legs with `--skip-deps`, as `pages.yml` now runs
  them -- exit 0, no second `npm ci`.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0. `pixi run --frozen -e pyforge-guild flag-gate-check` --
  exit 0 (0 fail, 840 warn).
- **The flag gate at `done`** (review B's landing blocker): a copy of the tree (tracked plus new files) with all
  fourteen of the PR's in-review specs set to `done` -- herald 42.1, 42.3, 43.2-43.7, steward 102.3-102.5, doctor 48.2
  and 34.7, atlas 30.2 -- and steward 102.3's two Verification paths given their package prefix there (that fix lands
  from the other lane): `python scripts/flag_gate_check.py` -- exit 0 (0 fail, 840 warn); before the fix, exit 1 on
  102.3's `flag-test-file-missing` alone.
- `pixi run -e site pages-build`, as `sync_all`'s publisher runs it -- exit 0 in 8.2 s (npm ci 3 s, 85 pages in 4 s).
- **Mutations, each restored:** a herald page given an inline `<script>` and an `onclick=`, and a shelf page an
  `onclick=` -- `pages-check` exits 1 naming each; the CAP-53 refusal disabled, the gallery's `order` sort reversed, and
  `GOOGLE_FONT_LINK` widened to eat the next tag -- each fails the model test above (the last on the Genesis poster's
  real twin); an ignored `docsite/` leftover (a `.pyc`, a `.woff2`) -- AC1 passes; the `.woff2` added with
  `git add -f` -- AC1 fails.
- **In the browser** (the second-host artifact served under `/org/local-recipes/`): the docs root's CSP meta follows its
  `<meta charset>`; the search dialog finds the dossier (Pagefind's WASM under `'wasm-unsafe-eval'`); the gallery's ten
  preview `onload` handlers all run under `HERALD_CSP`; no CSP violation and no failed request on either page.

## Named, not fixed here

- **`docs/map.yaml` `sections:`** and the `docs/MAP.md` rows that name `docsite/` (the "outside this map" table, line
  34 on 2026-10-14): doctor (`pyforge-doctor:CAP-90`, Story 48.1); a stale row after `docsite/` is deleted is doctor's
  one-line edit, named in this story's report with the exact text if `docs-map-hygiene` reds on it.
- **`pages.yml`** (the paths it filters, the Guild steps, the `site` env name): steward (`pyforge-steward:CAP-168`);
  the retirement of `docsite/**` from its path filter is steward's edit, named in the report.
- **`pyforge.herald.ci_surfaces_tile`** (CAP-59's flag): its reader moves with the tile's Astro home (Story 43.1's
  § *Named, not fixed here*); its own 90-day cleanup (Story 39.1) is a separate removal.
- **The artifact twin** `herald/artifact/dossier.html` (CAP-47) and its republish ritual: rendered by the generator
  from here, the ritual line moving into `docs-site/README.md` with the rest of the still-true content.
- **AD-21's text** still describing `docsite/build.py` as the owner of `/herald/`: the next spine re-stamp carries the
  change (the memlog decision of 2026-10-14 already records AD-23); a story spec does not edit the spine.
- **"Measured on"** (carried from Story 43.5, the 2026-10-15 re-review's nit 5): each dossier section renders its
  `measured:` date as "Measured on <date>", as 43.5's AC3 words it; the wording is the operator's open question
  (the coordinating session took it to the operator). AC3's wording stands unless the operator rules.
- **`jinja2` in `[feature.site.dependencies]`**: no reader since this story; removing it changes `pixi.lock`, which a
  story may not do, so it leaves at the next estate refresh (steward, `pyforge-steward:CAP-167`). The comment on the
  line says so.
- **The Guild steps that would write `changes.json`, `marshal-status.json` and `herald-progress.json`** (Story 43.6's
  inputs, now under `docs-site/src/content/`): still steward's deferred-work row; until they land, `/changes/` and
  `/status/runs/` say their input is absent.
- **The `dashboards` registry row** (`docs/map.yaml`, `owner: atlas`, `dashboard/vizro/`): added here so AC3's given
  holds (see the change log); atlas owns its label and order.
- **`support.js`**: each deck view twin (a Design `.dc.html` export, never edited, CAP-55) asks for a `support.js` that
  no export ships, a 404 in the browser on every family page's preview frames; it predates this story (the retired
  assembler skipped `./support.js` by name) and is a Design-export fix, not the generator's.

## Spec Change Log

- 2026-10-15 (independent reviews A and B: FAIL, 8 should-fix and their nits; resolved, builder A6; status stays
  `in-review`). Review B's second and third should-fix (the open deferred-work rows and the active Specs' CAP text that
  name moved paths) are the other lane's (the `SPEC.md` re-derives and the ledgers), not changed here.
  - **F1 -- the CSP decision is enforced.** `pages-check` reads each page's own CSP meta and requires the sha256 of
    every inline `<script>` in its `script-src-elem` / `script-src` / `default-src`, and of every `on*=` handler with
    `'unsafe-hashes'` in its `script-src-attr` / `script-src` / `default-src`, unless `'unsafe-inline'` holds (and no
    hash or nonce makes the browser ignore it); a data block (`*json`) and a `src` script are not judged
    (`pages.mts`'s `blockedScripts`). So a herald layout gaining a script `HERALD_CSP` does not list, or a Starlight
    upgrade adding a handler, fails the check naming the page. Tests: `test_43_7_every_inline_script_and_handler_...`
    (five planted failures) and `test_43_7_allowed_scripts_and_data_blocks_pass`; the review's mutation now fails.
  - **The meta's place (nit 2).** `addCsp` writes it right after `<meta charset>` (else first in the head), ahead of
    every script, so the charset stays inside the 1024-byte prescan however many hashes the policy lists.
  - **Astro's `security.csp` (nit 3) is not adopted here.** Astro 7.3.2 ships it stable: it hashes inline scripts and
    styles itself and would replace `addCsp` and the herald layouts' own meta (with a `'wasm-unsafe-eval'` script
    resource for Pagefind). Named as the future option; this story keeps the post-build pass, now checked per page.
  - **F2 -- the model's oracles, back as literals.** `test_herald_pages_model.py` (node only, so it runs in CI where
    the built tests skip): the tracked gallery's ten titles and names in order and its ten families; the fixture
    tree's override and `order` sort (Beta 10 by file name, Alpha 20 by path), `beta-co.html`, `fx-gamma` with no
    family, `fx-beta` with `infographic_deck` only, the sidecar stamp cut to twelve, `{tree: 'unstamped', etag:
    sha256[:12]}` for every file without one; `MoreThanOneCurrentExport` naming both pptx files
    (`fixture_tree(second_pptx=True)` is used again).
  - **F3 -- the twin oracle over every real twin.** `populate-public`'s twin writer moved into `herald-pages.ts`
    (`publishedTwin`, node builtins only), and the same test file runs the vendoring-only line diff
    (`pages_astro.font_vendoring_only`, moved from `test_one_generator.py`) over all thirty tracked twins against their
    sources, in CI. The previous entry's "the rest are kept" holds again with this.
  - **F4 -- `refusePublicCollisions` is tested.** A node unit test (no collision; one route output `public/` serves,
    named; two, named sorted) and a static assertion that `astro.config.mjs` takes `populatePublic`'s list at
    `astro:build:start` and runs the guard first at `astro:build:done`, before the stubs.
  - **F5.** `docs/dashboard/README.md` no longer promises the pipelines page: `/dashboard/` holds exactly what
    `docs/dashboard/` mounts, and the Kedro-Viz export's commit and date are on the overview's tile (`neighbours`).
  - **AC1's oracle (review B, should-fix 1)** reads `git ls-files docsite` and `git ls-files --others
    --exclude-standard docsite`, both printing nothing, in place of `test -e docsite`: a checkout that merged the
    deletion keeps its ignored leftovers (`docsite/tools/__pycache__/`, the old build inputs), which reded the herald
    suite there. `/docsite/` is ignored in `.gitignore`, so the leftovers stay out of `git status` and of a `git add
    -A`; the test asserts the line. The Verification's `.woff2` mutation now needs `git add -f` to fail AC1.
  - **AC8's recorded exception (nit 1).** With the exports mounted, AC8's literal grep names
    `dashboard/vizro/assets/plotly.min.js` (`cdn.plot.ly`, for map traces no exported page draws) and can name the
    Kedro-Viz build: exactly `pages.mts`'s `VENDORED` paths, which the origin check exempts by name (AD-21 rule 5). The
    AC8 test exempts those two and nothing else, and also runs over the fixture build with the exports mounted.
  - **The checks the retired assembler had (nit 5)**: "no shelf page found" is restored; `_menu_target`'s refusal is
    restored and widened -- every menu link must land on a file of the artifact (an empty, fragment-only or off-site
    href fails); the docs root's Herald sidebar-link check stays retired, the registry's sidebar being pinned by
    `test_docs_site_nav.py`.
  - **More of AC7 in CI (nit 6).** `pages-check` requires every family page the decks index links, and fails a decks
    index that links none.
  - **Smaller (nits 4, 7, 9, 10).** The RSS check accepts only XML's five named entities and refuses a `<` or a bare
    `&` in an attribute value; a malformed percent-encoding is a named broken link, not a crash; the status board's bar
    carries no fallback text, so the percentage reads once ("99% 99%" was the bar's text and its label); the stale
    names `scripts/pages.ts`, `populate-public.ts` and `site-check` are corrected.
  - **`/llms-full.txt`'s infographic text (nit 8), the reading taken:** each infographic's text is the build's own
    sentences -- its `site.yml` description and where it is published from -- not the poster's text: a poster is a
    Design export (markup and scripts, CAP-55: never edited), and the page itself is linked. The family entries list
    their views, downloads and facts.
  - **A correction (nit 11).** This story's commit message says an unmoved tree from a later commit no longer
    redeploys. That holds for the family pages (their stamps no longer carry the commit) and for a build with the
    status pages off; the public deploy builds them on, and the board's `generated_at` is HEAD's commit time (Story
    43.5 recorded it as measured data), so a new HEAD still moves `/status/` and redeploys. The PR body says so.
  - **Review B's nits.** `pages.yml`'s path filter, steward's `_EXPECTED_PATHS` and steward's job in
    `pyforge-station-tests.yml` name `pyforge/herald/pages_env.py` (the build's flag export); `pages.yml` runs the
    three legs of `docs-site-validate` with `--skip-deps` after `pages-check`, so CI installs docs-site once (steward's
    test pins the legs to the task's closure); `sync_all`'s `pages-build` measured at 8 s against its 300 s bound,
    kept and recorded on the publisher; a herald test pins steward's `FLEET_STATUS_REL` to `INPUTS_DIR_REL` +
    `FLEET_STATUS_INPUT`.
  - **The landing blocker (review B).** The flag gate over a copy with the PR's fourteen specs at `done` failed only on
    steward 102.3's two relative test paths (fixed in the other lane); 43.2's and 43.5's Verification named the parity
    test this story deleted and now name its replacements, and this spec's Verification names every test by its repo
    path. See *Verification run (2026-10-15, the independent reviews resolved)*.
- 2026-10-15 (built, builder A5; status `in-review`). **What changed, by AC:**
  - **AC1.** `docsite/` is deleted with `git rm` (55 tracked files: `build.py`, the assembler, the templates, the
    vendored fonts, their sha256 table and OFL copies, `_dossier.css`, `_site-chrome.css`, the export scripts, the tools,
    `README.md`). `docs-site/scripts/sidebar_from_map.py` and `docs-site/.gitignore` go too.
  - **AC2.** Moved with `git mv`: `docsite/content/dossier.yml` to `docs-site/src/content/dossier/dossier.yml`,
    `site.yml` and the committed `ci-status.json` to `docs-site/src/content/`, `verify_claims.py` to
    `docs-site/scripts/`. The gitignored build inputs (`fleet-status.json` and Story 43.6's three) are read from
    `docs-site/src/content/` (`agent-surface.ts`'s `INPUTS_DIR_REL`). The loaders read the new paths
    (`dossier-loader.ts`'s `DOSSIER_REL` and `MEASURER`, `herald-pages-loader.ts`'s `SITE_YML`). No tracked file under
    `docs-site/src`, `docs-site/scripts` or `astro.config.mjs` names `docsite/`.
  - **AC3.** One registry (`src/lib/nav.ts`, read once per build by `src/lib/site-nav.ts`): `docs/map.yaml`'s `pages`
    give the sidebar its quadrants, its `sections` give the sidebar, the top menu (`SiteTitle.astro`, both herald
    layouts) and the home's doors (`components/MarkdownContent.astro`, a Starlight override on the docs root only)
    their entries, in `order`. A section whose `href` is a mounted export shows only when the export holds a file; the
    `status` section only with `pyforge.herald.status_pages` on. A map without `sections` fails the build naming the
    key. `site.yml` has no `nav`. `docs-site-sidebar` and the generated `sidebar.generated.json` /
    `topnav.generated.json` retire; `docs-site-validate-sidebar` runs `node docs-site/scripts/nav-check.mts`.
  - **AC4.** `site`, `site-check`, `site-verify`, `site-serve` and `docs-site-sidebar` leave `pixi.toml`; `pages-build`
    is `node docs-site/scripts/pages.mts build`, `pages-check` its `check` after `pages-build`. `environment.yaml`
    exported again: byte-identical. `pixi.lock` untouched (task tables only).
  - **AC5.** `pyforge.herald.pages_one_generator` leaves `flags.json` and the three overlays; this spec declares
    `retires-flag:` (doctor Story 34.7's path); its herald reader module (`pyforge/herald/pages_one_generator.py`),
    the docs-site reader (`flags.ts`'s `pagesOneGenerator`) and every gate on it (the herald pages, the agent surface,
    the dossier collection, the theme, the footer, `populate-public`) are gone, so the Astro path is the only path. The
    two remaining build flags reach the build through one export, `python -m pyforge.herald.pages_env` (replacing
    `docsite/tools/export_*_env.py`), read by `flags.ts` alone. Herald's flag inventory is regenerated.
  - **AC6.** Bespoke Python under `docs-site/`: 175 lines (`verify_claims.py` 102, `origin_check.py` 73).
  - **AC7, AC8.** The tracked tree builds every URL of the list (`test_one_generator.py` enumerates it: the root, the
    four herald pages and the ten families, the 44 redirect paths, `/status/`, `/status/ci/`, `/status/runs/`,
    `/changes/` with its feed, `/llms.txt`, `/llms-full.txt`, `/facts.json`; `/dashboard/kedro-viz/` and `/kedro-viz/`
    with the export present). No file of the built artifact matches `fonts.googleapis|cdn\.`. The five vendored files
    keep their recorded hashes (`test_docs_site_validators.py`).
  - **AC9.** `AGENTS.md` cites `docs-site/src/content/dossier/dossier.yml`; the scribe parity test and
    `governance-currency` pass. The `SPEC.md` `surface:` change and the scoped stamps are the orchestrator's (memlog,
    script render, stamp), named in the report.
  - **AC10.** See *Verification run (2026-10-15)* below.
- 2026-10-15 (built; **the ported pages and the build, the carry-ins**):
  - **The status pages** are Astro pages (`src/pages/status/`), Starlight pages like Story 43.6's `/status/runs/`, over
    `src/lib/status.ts` (the board, the attention note, the guild rows, the CI tile -- `status_pages.py` and
    `ci_surfaces_tile.py` ported rule for rule). They carry the built-from line through the footer and **no date or
    commit of their own**: neither the Jinja footer's "Site rebuilt <date>" nor the Jinja shell's nav stamp
    `Built <date> · <commit>` (the coordinator's carry-in) survives; the dead `.stamp` rule leaves `herald.css`.
  - **No Pipelines page stays.** `/dashboard/index.html` (Story 42.2, rendered only with the export) had no inbound link
    -- the menu, the registry's `pipelines` section and the overview's tile link the mount itself, and the tile carries
    the same provenance -- and was not in the 2026-10-13 artifact; `/dashboard/` now holds exactly what
    `docs/dashboard/` mounts (AD-21 rule 1).
  - **The two-build proof over the whole artifact** (`test_43_5_two_builds_two_days_runs_and_commits_apart_...`):
    the tracked tree with the status pages and the tile on, built twice two days, two runs **and two commits** apart,
    is byte-identical once the built-from text is dropped. It found a commit stamp: a family download or view with no
    `.stamp.json` sidecar was stamped with the build's commit (most of the ten families), so every family page moved
    on every commit; such a file is now stamped `unstamped` and its content hash (`herald-pages.ts`'s `artifactStamp`).
  - **The built-from check** (`pages.mts`) exempts only the twins, `herald/artifact/`, redirect stubs and the mounted
    `dashboard/` entries of the build input -- a page under `dashboard/` the input does not mount is a collision and is
    judged. **Three things change together**: the built-from markup (`built-from.ts`'s `BUILT_FROM_OPEN`), steward's
    `BUILT_FROM_TEXT` (byte-exact) and `pages-check`'s pattern, built from `BUILT_FROM_OPEN`; stated in `built-from.ts`,
    pinned by `test_43_7_the_line_is_matched_as_built_from_ts_writes_it`.
  - **One build time per build.** `pages.mts build` sets `PAGES_BUILT_AT` once in the build's own environment dict;
    nothing writes `process.env`.
  - **The measurer** moved and kept only `--emit` (338 lines to 102): the typed-value compare, `--page`, `page_stats`
    and `with_page_values` retire with `site-verify` and the workflow's advisory step. `dossier.yml`'s verified row on
    the advisory is reworded to the past and says the figures are measured at build.
  - **The OFL-1.1 text** ships in the artifact from each `@fontsource` package's own `LICENSE` at
    `/fonts/<package>.LICENSE.txt` (`populate-public.mts`); `test_ofl_licences_ship_from_each_fontsource_package`
    follows it there.
  - **`/llms.txt` and `/llms-full.txt`** list each gallery infographic and each deck family with its text, from
    `loadHeraldPages()`; the Data section names the guild status page too.
  - **The artifact build** `herald/artifact/dossier.html` (CAP-47) is made at build end from the built dossier page
    (`src/lib/artifact.ts`): its title, its bundled stylesheets with the three faces it reads inlined as data URIs, and
    its body between the menu and the built-from line; no `<html>`, `<head>`, `<body>` or script. Its republish ritual
    is in `docs-site/README.md`.
- 2026-10-15 (built; **decisions**):
  - **The CSP: the default, extended to every page.** Every HTML page the build renders carries one CSP meta: the herald
    layouts and reader pages write `HERALD_CSP` (now `cspWith(...)`), and every Starlight page -- the shelf, `/changes/`,
    `/status/**`, the 404 -- gets the same policy at build end, its own inline scripts allowed by hash and
    `'wasm-unsafe-eval'` for the Pagefind search (`artifact.ts`'s `addCsp`). Checked in the browser: the theme toggle,
    the search dialog and its results work under it, with no violation reported. Redirect stubs, the twins, the
    artifact build and the mounted `dashboard/` tree carry none.
  - **The flag retires here**, as this spec's frontmatter and Approach say (`flag-exempt: flag-infrastructure`):
    `retires-flag: pyforge.herald.pages_one_generator`; `flag-gate-check` exits 0 with no reader left.
- 2026-10-15 (built; **deviations**, each with its reason):
  - **`docs/map.yaml` gains `status` (20), `dashboards` (40, `owner: atlas`) and `changes` (50), and `docs/MAP.md`'s rows
    that named `docsite/` are rewritten**, against *Never: do not edit `docs/map.yaml` `sections:` or `docs/MAP.md`*.
    Doctor Story 48.1's § *Named, not fixed here* assigns these rows to "the herald, steward and atlas stories that
    publish those sections", AC3's given needs them, and without `status` the go-live menu would lose the Status entry
    Story 42.1 shipped; the orchestrating brief lists both files among the consumers to fix in this PR. Cross-station
    (doctor's registry and map).
  - **`pages-check` is TypeScript** (`docs-site/scripts/pages.mts`, node builtins only), the origin rule staying in
    Python (`origin_check.py`, given a command line: 64 to 73 lines). The retired assembler's checks that only compared
    two generators (the one-writer check, the Jinja parity, the flag-state checks) retire; the rest are kept.
  - **The node scripts are `.mts`** (`pages.mts`, `nav-check.mts`, and `populate-public.ts` renamed): `scripts/`
    is a CommonJS scope (for the vendored validators), so a `.ts` there could not run alone -- `populate-public`'s own
    "runnable alone" line was false until the rename.
  - **`docs-site-validate-sidebar` now needs `npm ci`** (`depends-on` `docs-site-install`): the map check reads YAML
    with the `yaml` package in TypeScript, the budget the spec's Approach chose.
  - **The home's doors** are the docs shelf (its four quadrants) and one door per registry section, each listing its
    entries -- Docs, Herald (Overview, Dossier, Infographics, Decks), Status, Changes, plus Kedro-Viz and Dashboards when
    mounted -- rather than exactly the four of the 2026-10-14 preview, so AC3's "one registry entry reaches all three"
    holds.
  - **`favicon.svg`** is written into `public/` from `site.yml`'s `favicon`: Starlight links `/favicon.svg` on every
    docs page and nothing ever wrote it (a live 404, found by the new link check).
  - **The CI surfaces tile on the Astro dossier** now lists only the surfaces that are not live, in CAP-59's order and
    wording, as the retired Jinja tile did; the Astro tile since Story 43.1 had listed every row as `id: verdict`.
  - **`sync_all`'s publisher** runs `pixi run -e site pages-build` (it ran the retired `site` task).
  - **Retired tests, and what replaced them.** Deleted: `test_herald_pages_parity.py`, `test_docsite_build.py`,
    `test_docs_site_menu.py`, `test_docs_site_sidebar.py`, `test_pages_shelf_check.py`,
    `test_pages_one_generator_flag_states.py`. Rewritten under their names (the flagged specs name them):
    `test_pages_artifact.py` (`pages.mts check` over planted artifacts), `test_status_pages_flag_states.py`,
    `test_ci_surfaces_tile_flag_states.py`, `test_ci_surfaces_import_boundary.py`,
    `test_ci_surfaces_steward_schema_contract.py`, `test_pages_site_url.py`. New: `test_one_generator.py` (this
    story's ACs and the built artifact), `test_docs_site_nav.py` (AC3). The Jinja path's font families, colour tokens
    and block renders are frozen as fixtures (`jinja-theme-2026-10-15.json`, `dossier-block-goldens-2026-10-15.json`)
    for the theme and golden tests.
  - **A detector red on the base, fixed here:** `ad_citation_check` reded `spec-43-5`'s change log for a
    `pyforge-steward:CAP-168` citation split across two lines (proved on an export of `ffb2fb8801`); the line is
    rejoined.
- 2026-10-15 (built; **cross-station changes**, each recorded for its owner):
  - steward: `.github/workflows/pages.yml` (path filter drops `docsite/**`; one flag export; the fleet-board input
    written to `docs-site/src/content/fleet-status.json`; the `site-verify` step removed),
    `.github/workflows/pyforge-station-tests.yml` (drops `docsite`; the steward job fires on
    `docs-site/src/lib/status.ts`, which `test_ci_status.py` now reads), `scripts/pages_fleet_status.py`,
    `pyforge.steward.pages.FLEET_STATUS_REL` and the docstrings of `pages.py`, `pages_duty.py` and the `pages build`
    help, and the tests `test_pages_workflow.py`, `test_pages_release.py`, `test_pages_duty.py`, `test_ci_status.py`
    (the herald half of its contract now runs `status.ts` through node), `test_preflight.py`,
    `test_preflight_selection.py`, `test_station_tests_trigger_map.py` (the herald root handoffs).
  - doctor: `pages_liveness.PUBLISHED_INPUTS` drops `docsite` (and its test); `docs/map.yaml` rows and `docs/MAP.md`.
  - core and platform: the tree pins in `pyforge-core`'s `test_flags.py` and the platform's
    `test_openfeature_file_flags.py` drop the retired key.
- 2026-10-15 (built; **Consumer grep**: `git grep -n` over the whole tree for every deleted, moved or renamed path --
  `docsite/` and each file under it, `sidebar_from_map.py`, `populate-public.ts`, `topnav.generated.json`,
  `sidebar.generated.json`, the `site`/`site-check`/`site-verify`/`site-serve`/`docs-site-sidebar` tasks, the flag key
  and `PYFORGE_PAGES_ONE_GENERATOR` / `pagesOneGenerator`). Found, and how each was fixed:
  - **docs-site sources** (`astro.config.mjs`, `SiteTitle.astro`, `Footer.astro`, both herald layouts, `Shot.astro`,
    `agent-data.ts`, `agent-surface.ts`, `built-from.ts`, `dossier-blocks.ts`, `flags.ts`, `herald-pages.ts`,
    `md-inline.ts`, `redirects.ts`, `shelf.mjs`, both loaders, `content.config.ts`, every herald, agent and changes
    route, the three stylesheets, `content/site.yml`, `content/dossier/dossier.yml`, `README.md`): repointed, ungated or
    reworded as above.
  - **pixi.toml** (the site tasks, the site feature comments, the `pr-preflight-lanes` description's `site-check` and
    "node only" sentences, the herald feature's PyYAML comment): rewritten; `docs/how-to/pixi-tasks.md` regenerated.
  - **workflows**: `pages.yml`, `pyforge-station-tests.yml` (above).
  - **`.gitignore`**: the four input ignores move to `docs-site/src/content/`; `sidebar.generated.json` dropped.
  - **herald package**: `sync_all.py` (the publisher), `status_pages.py`, `ci_surfaces_tile.py` docstrings,
    `pages_one_generator.py` deleted, `pages_env.py` new; tests as listed above, plus `pages_astro.py`,
    `test_agent_surface_and_changes.py`, `test_docsite_zero_origin.py`, `test_dossier_golden.py`,
    `test_dossier_structure.py`, `test_docs_site.py`, `test_docs_site_validators.py`, `test_verify_claims_emit.py`,
    `test_bridge.py` (module list, docstring).
  - **steward, doctor, core, platform**: as under *cross-station changes*.
  - **docs**: `AGENTS.md` (the dossier citation), `docs/MAP.md`, `docs/map.yaml`, `docs/dashboard/README.md`,
    `docs/how-to/presentation-deck.md`, `docs/reference/github-workflows.md`, `docs/reference/story-spec-flag-block.md`;
    herald's flag inventory regenerated. `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules`
    and the skills name none of these paths.
  - **governance and planning surfaces**: herald's `marshal-policy.toml` Epic 43 surface widened to the paths this story
    touches (it keeps `docsite/**` for the deletions); `scripts/spec_surface_allowlist.txt` names none.
  - **Left as they are, with the reason**: the planning and history record (`_bmad-output/**` specs, epics, PRDs,
    spines, ledgers, memlogs; `docs/dreams/**`; `docs/intake/**`; `.claude/memory/**`; `.steward/estate-refresh/*`);
    `SPEC.md` surfaces and `scripts/.spec-surface-baseline.json` (the orchestrator's reconcile); the retired
    `docsite-check` rows of `docs/governance/ci-surfaces.yaml` (`state: retired`, a workflow id); the generated
    capability-ledger heading "the docsite has a PR gate" (from CAP-49's heading); `docs/governance/flag-rule-baseline.json`
    (spec file names); fixture names in tests that build a temporary repository (`test_sources_docs_map_hygiene.py`,
    `test_sources_live_proof_surfaces.py`, `tests/scripts/test_flag_gate_check.py`, steward's `test_preflight_scope.py`
    and `test_preflight.py`'s synthetic `pixi.toml`), which never read the real path; and the other stations' done epic
    surfaces in `marshal-policy.toml` (history).

- 2026-10-15 (carry-ins from Story 43.5 and its review; the coordinating session's rule: a finding in a file this
  story deletes or ports is fixed in the port, not twice):
  - **The built-from line on the ported pages.** Story 43.5 puts one plain-text line on every page,
    `<p class="built-from" data-pages-built-from data-pagefind-ignore>...</p>` (`docs-site/src/lib/built-from.ts`;
    `docsite/tools/status_pages.built_from_html` is its Python twin for the Jinja status pages and retires here). When
    `/status/`, `/status/ci/` and the pipelines page (`dashboard/index.html`, if a Pipelines page stays) move to Astro,
    each carries the line **in place of** its "Site rebuilt <date>" span -- no page keeps a wall-clock date of its own,
    or the Pages tree hash moves every UTC day.
  - **The two-day proof over the whole artifact.** Extend 43.5's
    `test_43_5_a_build_two_days_later_of_an_unmoved_tree_differs_only_in_the_built_from_line` (Astro only today) to
    the artifact with `pyforge.herald.status_pages` on: two builds two days and two runs apart are byte-identical
    once the line's text is dropped.
  - **The built-from check** (`assemble_pages._check_built_from` today; it moves wherever `pages-check`'s checks land)
    exempts only the twins, `herald/artifact/` (CAP-47's self-contained artifact build, a deliverable copied out of the
    site), redirect stubs and the mounted exports -- `dashboard/kedro-viz/`, `dashboard/vizro/` and any other mounted
    board -- **not** all of `dashboard/`; a test covers the pipelines page.
  - **One build time per build.** `PAGES_BUILT_AT` (ISO 8601 with seconds and an offset; both twins refuse anything
    else) is set once per build and handed to the build's environment, never written into `os.environ` by an
    in-process helper (43.5's review, nit 7; `assemble()` does that today).
  - **The budget.** `docsite/tools/verify_claims.py` is 338 lines after 43.5 (the Approach's 237 is the mint-day
    figure), over the 300-line budget on its own: its `--page` compare (roughly 100 lines with `page_stats` and
    `with_page_values`) leaves with the `site-verify` task this story retires, if the advisory retires with it.
  - **What the measured dossier reads.** The Astro dossier runs `verify_claims.py --emit` at build
    (`docs-site/src/loaders/dossier-loader.ts`, under `HERALD_PYTHON || 'python'`); moving the script to
    `docs-site/scripts/` moves the loader's `MEASURER` path with it.
- 2026-10-15 (carry-in from Story 43.4's re-review, nit 6): **the OFL-1.1 licence text stays in the artifact.** The five
  `@fontsource` packages are OFL-1.1 (`docs-site/README.md` § *Theme and fonts*); until this story the artifact carries
  the licence text only through the Jinja path's `herald/assets/fonts/OFL-*.txt`. Deleting `docsite/assets/fonts/`
  must carry the text into the artifact from each package's own `LICENSE` (no hand-vendored copy), and the
  `test_ofl_sidecars_present` check follows it there.
- 2026-10-14: specced at mint from Epic 43's Story 43.7 text, `spec-pyforge-herald` CAP-61, FR-12.4, AD-23 and the
  Dream's 2026-10-13 entry (M3), against the tree of 2026-10-14 (`docsite/` 4,543 lines across `build.py`, the tools,
  the content and the templates; `docs-site/scripts/sidebar_from_map.py` 297 lines). The 300-line budget's arithmetic
  is stated so the implementing session plans the sidebar's move before it starts.
