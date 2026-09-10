---
title: 'Output (caveman) compresses dispatch sessions too, not just spin'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 28.3 deployed the caveman output-compression skill into every loop home (`<home>/.claude/skills/caveman/SKILL.md`), but a dispatch worktree — the fleet's primary engine (`we are always primarily using dispatch`) — never got the same treatment: `seed/`'s AD-11 write boundary is scoped to a loop home, so `run_kit`/`_apply_caveman_skill` cannot reach a dispatch worktree, and `bmad-build-auto`'s own skill files had zero references to caveman at all (unlike `derived-context`/`planning-graph`, both wired into `step-01-clarify-and-route.md`). `[context].output` was already `enabled = true` for `pyforge-marshal` (the Story 33.2 "enable all five layers" flip), so every dispatch since then silently got zero benefit from a layer its own policy already turned on.

**Approach:** Reuse `seed/verbs/kit.py`'s own packaged-payload resolution (`probe_instrument`) and render step (`render_deployed_skill`) from a new `cli/dispatch.py::_seed_dispatch_output_layer`, called once per dispatch right after the worktree is provisioned, writing through the same `FsPort` `dispatch_once` already threads (not `seed/`'s AD-11-scoped port, since a dispatch worktree is not a loop home). Add a new instruction block to `step-01-clarify-and-route.md`, placed before the intent check so it governs the whole session regardless of which early-exit branch fires, telling the agent to invoke the deployed skill via the Skill tool when present.

## Boundaries & Constraints

**Always:** A layer declared off deploys nothing — today's behavior, byte-identical. An unavailable instrument or any write failure degrades with a named WARN finding (never blocks the dispatch). Reuse the SAME packaged payload and render step the loop-home path uses — one source of truth for the carve-out region.

**Never:** Reach into `seed/`'s AD-11-scoped write path for a dispatch worktree — it is structurally the wrong boundary. Renumber `step-01-clarify-and-route.md`'s existing numbered INSTRUCTIONS list (heavily cross-referenced by number elsewhere in the same file) to fit the new block in.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| LAYER_OFF | `context_payload["output"]["enabled"]` is `False` or the key is absent | Nothing deployed, no finding | N/A |
| INSTRUMENT_UNAVAILABLE | Layer on, `caveman-install` not on PATH | Named `MRS-DISP-042` WARN finding, session proceeds unwrapped | Never blocks |
| REAL_DEPLOY | Layer on, caveman installed (verified live on this machine) | `<worktree>/.claude/skills/caveman/SKILL.md` deployed with the articulate carve-out region | N/A |
| MODEL_VERSION_FAILURE | `packaged_seed_model_version()` raises (broken install) | Named `MRS-DISP-042` WARN finding | Never raises past the caller |
| WRITE_FAILURE | `fs.write_text_atomic` raises `OSError` | Named `MRS-DISP-042` WARN finding | Never raises past the caller |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `_seed_dispatch_output_layer` (new), called from `dispatch_once` right after `data["worktree_path"]` is set
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` — new registered code `MRS-DISP-042` (WARN)
- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` — new "Output compression" section, before the intent check
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py` / `seed/detect/kit.py` / `seed/model/kit.py` — reused unchanged (`probe_instrument`, `render_deployed_skill`, `KitItemId.CAVEMAN_SKILL`, `CAVEMAN_SKILL_RELPATH`)

## Tasks & Acceptance

**Execution:**
- `cli/dispatch.py` — `_seed_dispatch_output_layer` + call site — feature
- `core/findings.py` / `core/verdict.py` — register `MRS-DISP-042` — feature
- `step-01-clarify-and-route.md` — new instruction block — feature
- `tests/unit/test_dispatch_output_layer.py` (new) — 6 tests covering the full matrix above

**Acceptance Criteria:**
- Given a dispatch worktree for a project with `[context].output.enabled = true`, when the worktree is created, then `<worktree>/.claude/skills/caveman/SKILL.md` is deployed from the same packaged payload `seed/verbs/kit.py` uses, and `bmad-build-auto`'s own skill files reference it
- Given a project with the layer declared off, when a worktree is created, then nothing is deployed — today's behavior, byte-identical
- Given an unavailable/unresolvable caveman payload, when dispatch runs, then the layer disables with a named finding and dispatch proceeds unwrapped

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** Dispatch worktrees now get the same caveman deployment loop homes already did, gated on the same `[context].output` flag — which was already `enabled = true` for `pyforge-marshal`, so this closes a real, silent zero-benefit gap on the fleet's primary engine. Live-verified end to end against the real, installed caveman instrument (not just mocked unit tests): a scratch worktree got a 7732-byte `SKILL.md` with the `token-economy-articulate` carve-out region present, and `_seed_dispatch_output_layer` returned no finding.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `_seed_dispatch_output_layer` + call site
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — registered `MRS-DISP-042`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — classified `MRS-DISP-042` as WARN
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_output_layer.py` (new) — 6 tests
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` — registry-completeness list updated
- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` — new "Output compression" section
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — 28-30 → done

**Review:** Implementation verified directly against the spec's own I/O matrix, unit tests with an injected probe, and one live end-to-end run against the real installed instrument; no separate review-loop pass for this story.

**Verification:** `pyforge-marshal-test` → 7704 passed. Live: a real `_seed_dispatch_output_layer` call against a scratch worktree with the actual `caveman-install` on PATH deployed a working skill file with the carve-out marker present and returned no finding.

**Residual risks:** No automated test proves a model actually honours the skill's compression instruction or the new step-01 block's own invocation instruction — this is the same residual Story 28.3 already recorded honestly for the loop-home path: what is proven is that the instruction is deployed and correctly named, not that a session followed it. The new step-01 block places the check before the intent check (so it governs every early-exit branch); this was not exercised against a real multi-step dispatch session in this pass, only unit-tested at the deployment-function level.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_output_layer.py -v` — expected: 6 passed
- `pixi run -e pyforge-marshal pyforge-marshal-test` — expected: all pass
- Live: instantiate `_seed_dispatch_output_layer` against a scratch worktree with real `LocalFs()` and confirm the deployed file + carve-out marker
