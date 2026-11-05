---
title: "113.17: drift refuses a model a spin session can run on"
type: 'fix'
created: '2026-11-04'
status: 'done'
baseline_revision: 'f604a1ab86'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-113-16-a-sonnet-can-challenge-every-station.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 113.16 let a Sonnet challenge by dropping the `[adapter]` baseline from a station's session models, and
accepted a gap it called two rare fail-safe paths. Rendering the live policies showed the gap is larger. bmad-loop has no
Cursor adapter, so a Cursor tier's model drops at render: on marshal, `marshal factory spin` runs dev on `sonnet` and review
on `opus` for every tier but `frontier`. On the seven stations with no catalog, the render writes the Cursor model under the
`claude` adapter instead, and the no-difficulty render is still the baselines. `drift` reads the code those sessions wrote,
so a Sonnet challenger can review Sonnet-authored work.

**Approach (operator ruling 2026-11-04, "close it"):** `drift`'s whole target is what dev sessions wrote, so it compares what
spin runs on. `spin_models` reads the `dev` and `review` models of the policy spin itself renders, for
each tier and for no declared difficulty, through `resolve_tier_launch` and `render_policy_toml`, so it cannot drift from
what spin launches. `--stage drift` refuses a `model` that, aliases normalised, is one of them, and refuses when that policy
cannot render, because spin can still run on the file already on disk. `mint`, `decompose`, `rules` and `readiness` read a
planning or rules file, which a dev session can touch but does not author whole, so they keep Story 113.16's rule. A `fix`
under CAP-301: no CAP, no flag.

Ledger key: `113-17-drift-refuses-a-model-a-spin-session-can-run-on`. Type / Effort / Deps: fix / S / Story 113.16.

## Acceptance Criteria

- **AC1 — Drift refuses.** `--stage drift` with `claude-sonnet-5-5` exits with the usage code before any spawn, and the
  reason names `marshal factory spin` and the model, on all eight live stations.
- **AC2 — The render decides.** `spin_models` reports what spin renders: a Cursor tier's dropped model is absent, a Claude
  tier's model is present, and a run with no declared difficulty is the baselines.
- **AC3 — Other stages keep working.** `mint`, `decompose`, `rules` and `readiness` still render `claude-sonnet-5-5`, so
  `--audit` can run on it.
- **AC4 — A drift model exists.** `claude-fable-5-1` runs `drift` on the seven other stations and refuses on marshal.
- **AC6 — A failed render fails closed.** A spin policy that cannot render refuses `drift`, and is never read as no model.
- **AC5 — The contract follows.** CAP-301 and CAP-299 name the rule, and the cascade and the scoped stamp land.

## Boundaries & Constraints

- `spin.py` and the tier render do not change: no build runs on a different model.
- One `[challenge].model` per station: a station on a Sonnet block cannot run `drift` until it names another model, and
  marshal has no catalog entry that passes `drift` yet. `pyforge.marshal.egm_retro_drift` is off on every station, so
  nothing refuses today.
- Residual, for the operator: this narrows the gap and does not remove it. A file a spin session touched can still reach
  another stage on a Sonnet: a retry's story spec with a dev session's ticks through `readiness`, or a skill or `AGENTS.md` a
  harness checkpoint edited through `rules`. Only a challenger model no session can author with removes it.
- `spin_models` reads the policy as it stands at the run, never what a past spin launched. The journal cannot stand in: its
  `resolved_models` records the tier's model even where the render dropped it.

## Binding

- spec-pyforge-marshal CAP-301 (FR-243), CAP-299 (FR-241); Epic 113. The fix lands in the done epic and at `done`, so
  `epic-113` stays `done`.

## Verification

```bash
pixi run --frozen -e pyforge-marshal pyforge-marshal-test
```

</intent-contract>

## Spec Change Log

- 2026-11-04: minted `done` from the operator's ruling closing the gap Story 113.16 had accepted; landed in the same PR.
- 2026-11-04: independent review (a fresh reviewer, on the diff against this spec) failed the first cut: a failed render read
  as no model and let `drift` pass (fixed, AC6); "the one stage that reads what a dev session wrote" was false (narrowed here,
  with the residual named); and the Cursor-drop sentence held only where a catalog is declared (scoped here).
