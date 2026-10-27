---
title: "42.3: A developer runs one command that executes every check CI executes sits behind a kill switch"
type: 'feature'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
flag-exempt: detector-or-gate   # a gate is never flagged (the Guild Spec's fidelity Constraint); read as this CAP's cover by the inventory
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
  - docs/governance/flag-inventory/pyforge-atlas.md
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
---

<intent-contract>

## Intent

**Problem:** `spec-pyforge-atlas` CAP-20 (A developer runs one command that executes every check CI executes) was minted before the rule date of 2026-09-28 and reaches a user at runtime through none: the capability is the local CI check-set and its parity gate (AD-32). Doctor's flag inventory (`docs/governance/flag-inventory/pyforge-atlas.md`) lists it as a `runtime` row with no flag. The operator ruled on 2026-09-28 that every capability sits behind a flag, with one retrofit flag per capability defaulting ON (Q6), and on 2026-10-26 approved the retrofit sheet as recommended (R1–R8): this row is an exempt row.

**Approach:**
- The capability is the local CI check-set and its parity gate: a flag-OFF gate would be a silent green, so the row is covered by this exempt story (`detector-or-gate`) and the roster's `flag_retrofit_cover_exemptions` lets the inventory read it as covered.
- Nothing in code changes.
- The gate's exemption check judges the value against the roster's closed list.

Ledger key: `42-3-a-developer-runs-one-command-that-executes-every-check-ci-executes-sits-behind-a-kill-switch`.
Type / Effort / Deps: feature / XS / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-20** — the capability this switch retrofits; the inventory joins this story's flag to it through this line.
- **`spec-feature-flag-governance` CAP-7** — the retrofit; Q3 (a flag-off verb stays listed and refuses with the usage code), Q4 (the 90-day clock), Q6 (one flag per CAP); rulings R1–R3 of 2026-10-26.

## Acceptance Criteria

- **AC1 — No key.** The tree gains nothing for this row.
- **AC2 — The capability is a gate.** Its check-set runs as before; nothing reads a flag.
- **AC3 — Exempt.** The story carries `flag-exempt: detector-or-gate`, a value on the roster's closed list, and the inventory reads the row as covered.
- **AC4 — Both states.** One test runs the key ON and OFF.
- **AC5 — The domain.** The station's frozen exit-code domain is unchanged: a refusal is the usage code 2.

## Boundaries & Constraints

**Always:**
- Read the key only through `pyforge.core.flags` or `django_pyforge.flags`; spell it literally at the read site.

**Never:**
- Never mint a new exit code; never read a second tree or an environment variable as the flag; never re-open the defect the capability closed.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-atlas` CAP-20.

Parent: `spec-pyforge-atlas` CAP-20

- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-26 (every pre-rule runtime capability sits behind a kill switch) entry.
- Epic: Epic 42, minted with this story.
- Ledger key: `42-3-a-developer-runs-one-command-that-executes-every-check-ci-executes-sits-behind-a-kill-switch`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."42"`.
- Minted 2026-10-26 in one chain commit; built in the same PR (the CAP-7 retrofit effort: marshal Epic 110, steward Epic 114, atlas Epic 42, scribe Epic 29, doctor Epic 51).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- No flag, so no two-state test: the exempt story is judged by the gate's exemption check.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's cover.

## Auto Run Result

Status: done

Summary: built and reviewed in the CAP-7 retrofit PR (2026-10-26).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 at the operator's approval of the CAP-7 retrofit sheet (R1–R8).

## Review Triage Log

- (none yet)
