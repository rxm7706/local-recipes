---
title: '34.1: The flag rule has a closed exemption list, a rule-date baseline and one block shape'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
flag-exempt: flag-infrastructure   # the rule's own infrastructure (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - docs/governance/guild-roster.json
  - docs/governance/chain-sprawl-baseline.json
  - scripts/chain_sprawl_baseline.py
  - docs/reference/station-verify-commands.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-09-28 the operator ruled that every capability ships behind a flag and that a gate no station owns
enforces it (`docs/governance/spec-feature-flag-governance/SPEC.md`, `ready`, rule date 2026-09-28). CAP-1 is the rule
itself: every story spec of `type: feature` minted on or after the rule date carries either a `flag:` block (key, provider,
default per environment, scope, fallback, cleanup) or a `flag-exempt:` value from a closed list in
`docs/governance/guild-roster.json`. Today nothing declares that list, nothing can tell a pre-rule spec from a post-rule
one, and no page tells a story author the block's shape. Every story spec is dated by a `created:` string it declares
about itself, and several `type: feature` specs were minted on 2026-09-28 before the Spec reached `ready` (for example
doctor 33.1 and marshal 66.1-73.2), so a date alone cannot draw the line.

**Approach:** four pieces, all outside every `pyforge.<station>` package (Charter §6):
- `docs/governance/guild-roster.json` gains `flag_exemptions` — exactly `flag-infrastructure`, `docs-only`,
  `recipe-build`, `planning-ledger-only`, `detector-or-gate` — and a `$comment_flag_exemptions` that names a change to the
  list a governance act, in the `fold_exemptions` shape beside it.
- `docs/governance/flag-rule-baseline.json` is the pre-rule population: every tracked
  `_bmad-output/projects/*/planning-artifacts/specs/spec-<E>-<S>-*.md` at the merge SHA of the PR that took the Spec to
  `ready` (PR #1654; record the SHA in the file). `scripts/flag_rule_baseline.py` stamps it (`--snapshot` once;
  `--prune` only removes a path that no longer exists), the `scripts/chain_sprawl_baseline.py` shape. A spec is post-rule
  exactly when it is absent from the baseline.
- `scripts/flag_rule.py` is pure: `classify(path)` reads one story spec's frontmatter and returns `flag`, `exempt` or
  `neither` with its reasons. `flag` needs all six fields of the block (`key`, `provider`, `default`, `scope`,
  `fallback`, `cleanup`); `exempt` needs a `flag-exempt:` value on the roster's list; anything else is `neither`, with one
  reason per missing field and per unknown value. `is_post_rule(path)` reads the baseline; `in_scope(spec)` is `type:
  feature` (Q1). Stdlib and PyYAML only.
- `docs/reference/story-spec-flag-block.md` writes the block's one shape (the six fields, the rule date, the exemption
  values by pointer to the roster, a flagged and an exempt example, and the Q3 rule for an OFF CLI verb), registered in
  `docs/map.yaml`, and `docs/reference/station-verify-commands.md` — the page Marshal's spec gates send a story author
  to — gains one pointer line. bmad-build's copy is marshal Story 74.3's `_bmad/custom/` persistent fact, which points
  here.

Ledger key: `34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-feature-flag-governance` CAP-1 (the Guild's Spec; doctor's `epics.md` Epic 34 and the Spec's `.memlog.md`
  enumerate its stories — the doctor Epic 24/25/32 relay; no doctor CAP or FR).
- Kinship: marshal Story 74.3 (bmad-build's copy of the shape); doctor Story 34.2 (the gate that reads all of this).

## Acceptance Criteria

- Given the roster after this story When it is loaded Then `flag_exemptions` equals the five values in the Spec's Q2, in that order, and `$comment_flag_exemptions` names a change a governance act
- Given a spec whose frontmatter carries a `flag:` block with all six fields When `classify` runs Then it returns `flag` with no reasons
- Given the same block missing `cleanup` and `fallback` When `classify` runs Then it returns `neither` with two reasons, one per field
- Given `flag-exempt: docs-only` When `classify` runs Then it returns `exempt`; given `flag-exempt: no-flag-needed` Then it returns `neither` naming the unknown value
- Given a spec with both a `flag:` block and a `flag-exempt:` value When `classify` runs Then it returns `neither` naming the conflict
- Given a spec listed in the baseline When `is_post_rule` runs Then it is false; given one minted after the rule SHA Then it is true
- Given `type: fix`, `chore` or `docs` When `in_scope` runs Then it is false (Q1)
- Given the five values hard-coded in `scripts/flag_rule.py` When the unit suite runs Then a test fails (the roster is the one declared source)
- Given the new page When `pixi run -e pyforge-guild docs-currency-check` runs Then it exits 0 with the page registered in `docs/map.yaml` and `docs/MAP.md` re-rendered by `docs-map-render`
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep every new file outside every `pyforge.<station>` package: `scripts/`, `docs/governance/`, `docs/reference/`,
  `tests/scripts/` (Charter §6; the coverage-gate-independence resolution, Story 24.1).
- Read the exemption list from the roster at run time; the code holds no copy.
- Add one reason-tagged line per new script to `scripts/spec_surface_allowlist.txt`, in the `scripts/coverage_gate.py`
  shape (the owning Spec is guild-owned under `docs/governance/`, so it cannot declare a surface that detector reads).
- Record the new paths in the Guild Spec's `.memlog.md` with `uv run _bmad/scripts/memlog.py append` (the surface
  declaration in its `SPEC.md` is re-rendered later through the approved route, never hand-edited).

**Never:**
- Do not add a value to the exemption list, or rename one; that is a governance act.
- Do not import any `pyforge.<station>` module from `scripts/flag_rule.py`.
- Do not judge any spec yet (no finding, no exit code): that is Story 34.2's gate.
- Do not edit `SPEC.md`, `sprint-status-ledger.yaml` or an installer-owned skill file; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flagged | six fields present | `flag` | — |
| partial block | `key`, `provider` only | `neither`, four reasons | — |
| exempt | `flag-exempt: recipe-build` | `exempt` | — |
| unknown exemption | `flag-exempt: later` | `neither`, one reason | — |
| both | block and exemption | `neither`, the conflict | — |
| pre-rule | path in the baseline | `is_post_rule` false | — |
| no frontmatter | a spec without a fence | `neither`, "no frontmatter" | never a crash |
| unreadable roster | file missing | — | raises a named error Story 34.2 turns into exit 2 |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-1 and its Q1/Q2 rulings (memlog 23),
`docs/dreams/feature-flag-governance.md`, and the chain-sprawl baseline precedent (doctor Story 25.1), decomposed
2026-09-28 (night) as Epic 34's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-1 (Guild-owned; Doctor as mechanism
Smith, the Epic 24 relay).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"` admits the `scripts/`, `docs/governance/`, `docs/reference/` and
`tests/scripts/` paths beside the default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_rule.py -q` — expected: pass.
- `pixi run -e pyforge-guild docs-currency-check` — expected: exit 0 (after `pixi run -e pyforge-guild docs-map-render`).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 (each new script allowlisted).

## Review Triage Log
