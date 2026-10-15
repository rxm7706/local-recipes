---
title: '43.7: docsite/ retires and one generator remains'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
flag-exempt: flag-infrastructure   # the story retires the flag that gated Epic 43, pyforge.herald.pages_one_generator (spec-feature-flag-governance Q2)
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

- **AC1 — `docsite/` is gone.** `test -e docsite; echo $?` prints 1; `git ls-files docsite | wc -l` prints 0.
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
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` (or its meta subset) — expected: `test_instruction_surface_parity.py` passes (AC9).
- `pixi run --frozen -e pyforge-guild governance-currency` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `uv run _bmad/scripts/memlog.py append --workspace _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald --type event --text "Surface reconcile <date>: docsite/** leaves the surface ..."`, the script render of `SPEC.md`'s `surface:`, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec pyforge-herald/spec-pyforge-herald` and one scoped stamp per co-governor the detector names, then `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Re-add a `tasks.site-check` entry to `pixi.toml` — expected: AC4 fails.
- Remove the Changes entry from a fixture registry — expected: AC3's three-menu test fails naming the entry.
- Restore one `.woff2` under `docsite/assets/fonts/` — expected: AC1 fails.

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

## Spec Change Log

- 2026-10-15 (carry-in from Story 43.4's re-review, nit 6): **the OFL-1.1 licence text stays in the artifact.** The five
  `@fontsource` packages are OFL-1.1 (`docs-site/README.md` § *Theme and fonts*); until this story the artifact carries
  the licence text only through the Jinja path's `herald/assets/fonts/OFL-*.txt`. Deleting `docsite/assets/fonts/`
  must carry the text into the artifact from each package's own `LICENSE` (no hand-vendored copy), and the
  `test_ofl_sidecars_present` check follows it there.
- 2026-10-14: specced at mint from Epic 43's Story 43.7 text, `spec-pyforge-herald` CAP-61, FR-12.4, AD-23 and the
  Dream's 2026-10-13 entry (M3), against the tree of 2026-10-14 (`docsite/` 4,543 lines across `build.py`, the tools,
  the content and the templates; `docs-site/scripts/sidebar_from_map.py` 297 lines). The 300-line budget's arithmetic
  is stated so the implementing session plans the sidebar's move before it starts.
