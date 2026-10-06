---
title: "22.14: The cross-surface gate runs each touched surface's own check"
type: 'fix'
created: '2026-10-06'
status: 'in-progress'
baseline_revision: '6321ff198deb517ebaabc9dee4399f2b397db4cc'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - docs/reference/story-spec-flag-block.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the cross-surface gate knows one surface, so a story can land a change that a different repo check guards.

- **The gate today.** `core/gate.py` (about :621-:639) defines `SHARED_SURFACE_PREFIX = "src/platform/"` and one
  `CROSS_SURFACE_VERIFY_COMMAND` (`pixi run -e pyforge-guild platform-ci-local -- --test`).
  `dispatch_verify.py` (about :954) runs that command when the diff touches the prefix and refuses under
  `MRS-GATE-015` when it fails.
- **What slipped through.** On 2026-10-05 mason 19.1 landed `.claude/skills/pyforge-mason/` without regenerating
  `docs/reference/bmad-estate-llms-full.md`, and `bmad_estate_check` stayed red on `main` until a hand PR (#1884) ran
  `scribe catalog bmad-estate --write`. Atlas 25.2 and warden 14.1 declared flags `dev: on, staging: on` while the
  tree rendered `off`; nothing in dispatch verification ran `flag-gate-check`, so its `flag-default-env-mismatch` was
  found only by a hand preflight.

**Approach:** turn the single prefix/command pair into a small, ordered rule table of `(path prefixes, command)`:

| Paths (any changed path starting with) | Command |
|---|---|
| `src/platform/` | `pixi run -e pyforge-guild platform-ci-local -- --test` (unchanged) |
| `.claude/skills/` | `pixi run -e pyforge-guild bmad-estate-check` |
| `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, `_bmad-output/projects/` + `/planning-artifacts/specs/spec-` | `pixi run -e pyforge-guild flag-gate-check` |

Run every matching rule's command once, keyed on the diff alone, all under the same `MRS-GATE-015` code. A failing
command's output reaches the fix turn as today, so `bmad_estate_check`'s own remedy line (`run pixi run -e
pyforge-guild scribe catalog bmad-estate --write`) and `flag-gate-check`'s finding are in front of the session.

Ledger key: `22-14-the-cross-surface-gate-runs-each-touched-surface-s-own-check`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-170 (← `spec-marshal-single-story-dispatch` CAP-12; Story
  22.12, a shared-surface diff clears its own full suite). An extension of an existing gate; no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-06 (landing gaps), item 3.

## Acceptance Criteria

- Given a diff touching only `.claude/skills/pyforge-mason/0.1.0/pyforge-mason/SKILL.md` When verification runs Then
  `bmad-estate-check` runs and `platform-ci-local` does not.
- Given a diff touching `src/platform/config/flags.json` When verification runs Then both `platform-ci-local` and
  `flag-gate-check` run, each once.
- Given a diff touching a story spec under `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/` When
  verification runs Then `flag-gate-check` runs.
- Given `bmad-estate-check` exits non-zero When verification runs Then it refuses under `MRS-GATE-015` with that
  command's output, exactly as `platform-ci-local` refuses today.
- Given a diff touching none of the prefixes When verification runs Then no cross-surface command runs.
- Given a rule removed from the table (mutation) When the station suite runs Then its new test fails.

## Boundaries & Constraints

**Always:**
- Keep `platform-ci-local`'s rule and its behaviour exactly as today (Story 22.12's tests stay green unchanged).
- One table, in `core/gate.py`, pure; `dispatch_verify.py` only iterates it.
- Commands are the existing pixi tasks (`bmad-estate-check`, `flag-gate-check`); add no new task.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`).

**Never:**
- Never key a rule on the dispatching station.
- Never mint a new finding code; every cross-surface refusal stays `MRS-GATE-015`.
- Never run `scribe catalog bmad-estate --write` from the gate; the gate verifies, the session fixes.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-06 (landing gaps) entry.
- Epic: Epic 22 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `22-14-the-cross-surface-gate-runs-each-touched-surface-s-own-check`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: drop the `.claude/skills/` rule and re-run the station suite; its test fails. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
