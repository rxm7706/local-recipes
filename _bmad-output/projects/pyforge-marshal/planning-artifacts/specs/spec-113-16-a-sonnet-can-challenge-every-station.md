---
title: "113.16: a Sonnet can challenge every station"
type: 'fix'
created: '2026-11-04'
status: 'done'
baseline_revision: 'f604a1ab86'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-113-9-the-challenger-model-is-a-claude-entry-of-marshal-s-own-catalog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the first pilot had to run on `claude-fable-5-1` ($10 / $50 per MTok), though a Sonnet ($2 / $10) was wanted.
Two causes. `session_models` counts the template's `[adapter]` baseline `sonnet` on all eight stations, and alias
normalisation makes every Sonnet that model, although every tier of every station sets `dev`. And the catalog's `sonnet-5` is no launchable id: `claude --model sonnet-5` exits 1 with
`claude-code:unrecognized_model`, while `claude-sonnet-5-5` and the alias `sonnet` both run `claude-sonnet-5-5`. On marshal,
which `--audit` reads by default, no Anthropic entry could pass at all.

**Approach (operator ruling 2026-11-04):** a station's session models are the models its sessions can run on.
`adapter_models` keeps a baseline only for a stage some tier leaves unset, and keeps both when the station declares no tier
map. `session_models` reads it, and reads every candidate of a fallthrough-list tier stage. With a tier map and no launch
model, `MRS-DISP-043` dropped the run's override, so `readiness_for_dispatch` refuses the review. The catalog entry is renamed `claude-sonnet-5-5` at the same rates, and the
`[challenge]` comment's example names it. This supersedes the session-owner ruling of 2026-11-01 (Story 113.9 AC4). The
operator's answer of 2026-11-01 stands: the challenger is never the author session's model. A `fix` under CAP-299: no CAP,
no flag.

Ledger key: `113-16-a-sonnet-can-challenge-every-station`. Type / Effort / Deps: fix / S / —.

## Acceptance Criteria

- **AC1 — A Sonnet renders.** `claude-sonnet-5-5` draws no refusal on any of the eight stations' live policies, for every
  stage but `drift` (Story 113.17).
- **AC2 — A live baseline still counts.** A station with no tier map, or a tier that leaves `dev` unset, counts `sonnet`;
  a tier that leaves `review` unset counts `opus`, so an `opus` id stays refused on the live stations.
- **AC3 — The author's model still refuses.** `claude-fable-5-1` stays refused on marshal, and a dispatch's launch model is
  still compared: a `sonnet` launch refuses a Sonnet challenger, and a dispatch that dropped its model override refuses its
  readiness review (`MRS-DISP-067`, the dispatch proceeds).
- **AC4 — The id launches.** The catalog names `claude-sonnet-5-5`, not `sonnet-5`, at the same four rates, and the re-run
  pilot runs on it.
- **AC5 — The contract follows.** CAP-299 and the `[challenge]` comment name the new rule and example, and the cascade and
  the scoped stamp land.

## Boundaries & Constraints

- `same_model`, `alias_of` and `render_refusals` do not change: only what the station's session models are.
- No station's `[challenge]` block, flag or tier map changes.
- `drift` is Story 113.17's: its whole target is what dev sessions wrote, so it compares what `marshal factory spin` really
  runs on.

## Binding

- spec-pyforge-marshal CAP-299 (FR-241); Epic 113. The fix lands in the done epic and at `done`, so `epic-113` stays `done`.

## Verification

```bash
pixi run --frozen -e pyforge-marshal pyforge-marshal-test
```

</intent-contract>

## Spec Change Log

- 2026-11-04: minted from the operator's ruling after the first EGM pilot; landed with Story 113.15 in one PR.
- 2026-11-04: `done` on the re-run pilot, run `pyforge-atlas-20261105T003923891Z-1b2adcaa`: the session and its three
  reviewers ran on `claude-sonnet-5-5` (AC4), exit 0 in 198 s, 26 findings, $1.03 at catalog rates against $5.78 for the
  failed Fable run.
- 2026-11-04: independent review (a fresh reviewer, on the diff against this spec) failed the first cut on three counts,
  all fixed here: "a stage every tier sets never falls to its baseline" overstated the code (the accepted gap now names the
  paths past the tiers), a dispatch that dropped its model override compared nothing (it now refuses), and a fallthrough-list
  tier stage's models were not session models (they now are).
- 2026-11-04: the operator ruled the accepted gap closed. It was misdescribed here as rare fail-safe paths: bmad-loop has no
  Cursor adapter, so on marshal every tier but `frontier` runs `marshal factory spin` on the baselines, and `drift` does read
  what those sessions wrote. Story 113.17 narrows it, and that story's spec carries what remains.
