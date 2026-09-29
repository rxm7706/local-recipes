---
title: '24.2: The catalog cannot drift silently'
type: 'feature'
created: '2026-09-29'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-1-the-bmad-estate-catalog-is-generated-not-written.md
  - scripts/detectors.py
  - scripts/llms_full_check.py
  - scripts/scribe_graph_freshness_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A generated catalog that nothing checks is a hand-written catalog with extra steps: the next core apply, suite refresh or skill re-forge leaves it stale and no gate notices — the same way `library-llms-full.md` drifted before `llms-full-check` existed.

**Approach:** `scripts/bmad_estate_check.py` — a thin `DETECTOR = {"scope": "repo"}` wrapper over `scribe catalog bmad-estate --check` — exits 1 naming the drifted section and its source, 0 on a fresh render, 2 when a source cannot be read. `scripts/detectors.py` discovers it by the `*_check.py` glob, so `detectors-ci` and `pr-preflight` run it with no registry edit. A `bmad-estate-check` pixi task under `guild-tasks` runs it alone.

**Decision this story owns (OQ-CAP-32-1):** compare a structured diff of the derived facts (versions, counts, member rows, pins, range) with prose exempt — recommended — or a byte-exact re-render. Record the decision as a memlog entry on `spec-pyforge-scribe`.

## Boundaries & Constraints

**Always:**
- Exit-code domain 0 / 1 / 2, never a false green; `-- --json` for machine output.
- The reconcile is the regeneration command stated once in the catalog header.
- `scripts/bmad_estate_check.py` joins `spec-pyforge-scribe`'s `surface:` (INV-4: the detector is owned), the same shape as `scripts/scribe_graph_freshness_check.py`.
- Co-governor reconcile before landing, as in Story 24.1.

**Never:**
- Do not import `pyforge.scribe` internals from the wrapper beyond the CLI entry; do not import any other station.
- Do not register the detector by hand anywhere (`detectors.py` discovers it).
- Do not touch `llms_full_check.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| fresh render on main | catalog matches sources | exit 0 | n/a |
| manifest version moved | `manifest.yaml` 6.12.0 → 6.13.0, catalog unchanged | exit 1, names "installed core" and `_bmad/_config/manifest.yaml` | n/a |
| skill description edited | one `SKILL.md` frontmatter changed | exit 1, names the family and the skill | n/a |
| prose tweak in the template only | derived facts unchanged | exit 0 under the structured-diff decision | n/a |
| unreadable source | `suite-members.yaml` malformed | exit 2 | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-32`.
Dream: `docs/dreams/pyforge-scribe.md` § *2026-09-29 — Every session knows the BMAD estate it stands on*.
Ledger key: `24-2-the-catalog-cannot-drift-silently`.
Ledger status at mint: `backlog`.

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-24.1 • **FR/AD:** spec-pyforge-scribe CAP-32 • OQ-CAP-32-1
**Surface:** `scripts/bmad_estate_check.py` (new), `pixi.toml` (`bmad-estate-check` under `guild-tasks`), `catalog.py` (`--check` mode), `docs/reference/bmad-estate-llms-full.md` (header names the detector), `tests/unit/test_catalog_bmad_estate.py` (drift cases).
See `epics.md` § Story 24.2 for the full Given / When / Then / And.
