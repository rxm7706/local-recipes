---
title: "114.7: steward reads `origin/main` and its own branches by their full refs sits behind a kill switch"
type: 'feature'
created: '2026-10-26'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
flag:
  key: pyforge.steward.workspace_full_refs
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "`steward workspace start|status|clean` refuse with usage code 2; a short ref is never read"
  cleanup: "90 days after ON in every environment (Q4): 2027-01-24, Story 114.9"
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
  - docs/governance/flag-inventory/pyforge-steward.md
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
---

<intent-contract>

## Intent

**Problem:** `spec-pyforge-steward` CAP-158 (steward reads `origin/main` and its own branches by their full refs) was minted before the rule date of 2026-09-28 and reaches a user at runtime through `steward workspace start`, `steward workspace status`, `steward workspace clean`. Doctor's flag inventory (`docs/governance/flag-inventory/pyforge-steward.md`) lists it as a `runtime` row with no flag. The operator ruled on 2026-09-28 that every capability sits behind a flag, with one retrofit flag per capability defaulting ON (Q6), and on 2026-10-26 approved the retrofit sheet as recommended (R1–R8): this row is an invariant switch.

**Approach:**
- The key `pyforge.steward.workspace_full_refs` joins the one tree ON in every environment, with the five flagd metadata fields (steward Story 76.2); the clock runs from 2026-10-26 and Story 114.9 owns its retirement on 2027-01-24.
- Read site: `steward workspace start`, `steward workspace status`, `steward workspace clean`. With the key OFF: `steward workspace start|status|clean` refuse with usage code 2; a short ref is never read.
- The verb stays listed in `--help` marked disabled and refuses with the station's usage code (Q3); no new exit code.

Ledger key: `114-7-steward-reads-origin-main-and-its-own-branches-by-their-full-refs-sits-behind-a-kill-switch`.
Type / Effort / Deps: feature / XS / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-158** — the capability this switch retrofits; the inventory joins this story's flag to it through this line.
- **`spec-feature-flag-governance` CAP-7** — the retrofit; Q3 (a flag-off verb stays listed and refuses with the usage code), Q4 (the 90-day clock), Q6 (one flag per CAP); rulings R1–R3 of 2026-10-26.

## Acceptance Criteria

- **AC1 — The key.** `pyforge.steward.workspace_full_refs` is in `src/platform/config/flags.json` (`defaultVariant: on`) and in every environment of `flag-overlays.json` (`on`), with `owner`, `story`, `created` 2026-10-26, `on_everywhere` 2026-10-26 and `cleanup_by` 2027-01-24; `_SHIPPED_CLOCKS`, `per_environment` and `_SHIPPED_BOOLEANS` carry it.
- **AC2 — ON.** The key is read at `steward workspace start`, `steward workspace status`, `steward workspace clean`, spelled literally, through `pyforge.core.flags` (or `django_pyforge.flags` on the host); ON keeps today's behaviour byte-identical.
- **AC3 — OFF.** `steward workspace start|status|clean` refuse with usage code 2; a short ref is never read.
- **AC4 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-steward/tests/unit/test_retrofit_flags.py`).
- **AC5 — The domain.** The station's frozen exit-code domain is unchanged: a refusal is the usage code 2.

## Boundaries & Constraints

**Always:**
- Read the key only through `pyforge.core.flags` or `django_pyforge.flags`; spell it literally at the read site.

**Never:**
- Never mint a new exit code; never read a second tree or an environment variable as the flag; never re-open the defect the capability closed.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-158.

Parent: `spec-pyforge-steward` CAP-158
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-26 (every pre-rule runtime capability sits behind a kill switch) entry.
- Epic: Epic 114, minted with this story.
- Ledger key: `114-7-steward-reads-origin-main-and-its-own-branches-by-their-full-refs-sits-behind-a-kill-switch`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."114"`.
- Minted 2026-10-26 in one chain commit; built in the same PR (the CAP-7 retrofit effort: marshal Epic 110, steward Epic 114, atlas Epic 42, scribe Epic 29, doctor Epic 51).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- Two-state flag coverage (the testing kit's `flag_states`): `src/shared/packages/pyforge-steward/tests/unit/test_retrofit_flags.py` — `@flag_states("pyforge.steward.workspace_full_refs")`, `test_pyforge_steward_workspace_full_refs`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.

## Auto Run Result

Status: in-progress (hand-built in the retrofit PR).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 at the operator's approval of the CAP-7 retrofit sheet (R1–R8).

## Review Triage Log

- (none yet)
