---
title: '30.3: The reference pages are generated — pixi tasks, station CLIs, detectors, skills — and stamped'
type: 'feature'
created: '2026-09-19'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md']
deferred:
  - summary: >-
      spec-pyforge-doctor/SPEC.md's `surface:` list does not yet list the five
      new docs-* generator scripts + shared helper (Story 30.2 precedent:
      scripts/docs_map_render.py was added there directly). SPEC.md is
      hook-blocked from a hand-edit in this session (AGENTS.md: re-derive via
      `bmad-spec`, never hand-edit) and a station-Spec `bmad-spec`
      re-derivation is out of scope for this one story's dispatch.
    evidence: |-
      spec-pyforge-doctor/.memlog.md's 2026-09-24 entry already names the six
      new script paths under "Surface gains (surface: list): ...". Interim
      fix: allowlisted in scripts/spec_surface_allowlist.txt with a reason
      citing this story and the pending SPEC.md re-derivation.
      `python scripts/spec_surface_reconcile.py` reports OK with the
      allowlist entries in place.
    location: >-
      scripts/spec_surface_allowlist.txt
    severity: low
declared_low_risk: false
baseline_revision: '3811d6805cfd6d2e555aed54a769a344517b435d'
---

<intent-contract>

## Intent

**Problem:** the pixi-task reference is hand-written and already stale, the station cheat sheet was typed from memory, and no page lists the detectors or the skills — the pages agents most need are the least exact.

**Approach:** one generator per reference page, each reading its source of truth (`pixi.toml` task tables and `[environments]`, each station CLI's `--help`, `scripts/detectors.py` + `doctor.sources` registrations, `SKILL.md` frontmatter), writing the page plus a `derived_at` + `tree` stamp (herald's `facts.yaml` shape), idempotent on an unchanged tree; `docs-currency` (30.2) gains the generated-page check.

## Boundaries & Constraints

**Always:** generated pages are never hand-edited (a hand edit is a finding, as for `library-llms-full.md`); a generator is a pixi task under `guild-tasks` (or a station duty for that station's CLI page) and is registered as the page's `sources` in `map.yaml`; `library-llms-full.md` keeps its own lane.
**Never:** generate from a model; every value comes from the tree.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| unchanged tree, run a generator twice | byte-identical page, stamp `tree` unchanged |
| a task added to `pixi.toml`, no regeneration | `docs-currency` warn → fail after promotion: pixi-tasks page stale |
| a station CLI gains a verb | `docs-station-cli` rewrites the cheat sheet row; stamp advances |
| a `SKILL.md` frontmatter `description` edited | skills catalog regeneration differs → finding until regenerated |
| a hand edit inside a generated page | finding naming the page |

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-84`.
Surface: generator tasks `docs-pixi-tasks`, `docs-station-cli`, `docs-detectors`, `docs-skills-catalog`, `docs-environments` (`scripts/docs_*.py` or station duties), `docs/how-to/pixi-tasks.md`, `docs/reference/station-cheat-sheet.md`, `docs/reference/detectors.md` (new), `docs/reference/skills-catalog.md` (new), `docs/reference/environments.md` (new), `docs/map.yaml` rows, `docs_currency.py`'s generated-page check + tests.
Ledger key: `30-3-the-reference-pages-are-generated-pixi-tasks-station-clis-detectors-skills-and-stamped`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-19 (night) from `epics.md` so `marshal factory dispatch` can resolve this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:** run every `docs-*` generator twice on a clean tree → no diff; `pixi run -e pyforge-guild detectors-ci` green.

</intent-contract>
