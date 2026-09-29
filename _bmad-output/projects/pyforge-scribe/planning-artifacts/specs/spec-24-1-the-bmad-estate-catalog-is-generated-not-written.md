---
title: '24.1: The BMAD estate catalog is generated, not written'
type: 'feature'
created: '2026-09-29'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-bmad-suite-lifecycle-agent-knowledge-surface-research-2026-09-12.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  - recipes/bmad-suite/suite-members.yaml
  - docs/reference/library-llms-full.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The estate writes down almost everything about the BMAD Method it runs on (installed core in `_bmad/_config/manifest.yaml`, 127 skill dirs each with a `description:`, `bmad-help.csv`, the 13-member `suite-members.yaml` and steward's adoption register, the harness range, the release cadence), but a session gets one pointer line. No agent-facing file states the installed core version or the suite verbs; upstream stopped publishing `llms-full.txt` at 6.12.0; the same version numbers are hand-carried in four places and disagree.

**Approach:** A scribe CLI verb, `scribe catalog bmad-estate --write`, renders `docs/reference/bmad-estate-llms-full.md` from those in-tree sources — the shape `library-llms-full.md` already proved — with every fact followed by its source path. The first render is committed with the story.

## Boundaries & Constraints

**Always:**
- Read the adoption register and `suite-members.yaml` as data; render a verdict, wielder, provisioning path or hazard only as read (AD-2: the register is the one durable home).
- Render a disagreement between the register, a Spec header and `pixi.toml` as a disagreement naming its sources; relay it to steward as a deferred-work row; never resolve it in the generator.
- Read constants as text (regex over `HARNESS_VERSION_RANGE_TEXT` in `harness_bmadloop.py`, YAML over `suite-members.yaml`, frontmatter over `SKILL.md`); no `pyforge.<station>` import.
- Offline-safe: no registry or network call; steward's `pipeline-truth --json` is an optional `--pipeline-truth <file>` input.
- Fixture-driven unit tests under `src/shared/packages/pyforge-scribe/tests/unit/`.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then a scoped `--write-baseline --spec` per named Spec; re-run the check and read its exit code.

**Never:**
- Do not hand-edit `docs/reference/bmad-estate-llms-full.md`, `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not touch `docs/reference/library-llms-full.md` or `scripts/llms_full_check.py`.
- Do not write into `AGENTS.md` (Story 24.3's surface).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| first render | live tree | catalog written with header (date, regeneration command, detector name) + sections: core/modules/`installShims`; skills by family with counts; 13-member roster; `bmad-*` pins; harness range; cadence steps | n/a |
| register vs pixi disagreement | TEA 1.24.0 in the register, `>=1.26.0` in `pixi.toml` | a "sources disagree" row naming both files | never resolved |
| a member has no local recipe | `suite-members.yaml` row without `recipes/<name>/` | rendered with "no local recipe" marker | not an error |
| a source is missing | `manifest.yaml` absent | exit 2, no partial file written | fail loud |
| `--pipeline-truth` given | steward JSON | six-stage columns added per member | absent file → exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-32`.
Dream: `docs/dreams/pyforge-scribe.md` § *2026-09-29 — Every session knows the BMAD estate it stands on*.
Ledger key: `24-1-the-bmad-estate-catalog-is-generated-not-written`.
Ledger status at mint: `backlog`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-scribe CAP-32 • Dream 2026-09-29
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py` (new), `cli.py` (`scribe catalog bmad-estate [--write|--check|--pipeline-truth <json>]`), `tests/unit/test_catalog_bmad_estate.py` (new), `docs/reference/bmad-estate-llms-full.md` (first committed render).
See `epics.md` § Story 24.1 for the full Given / When / Then / And.
