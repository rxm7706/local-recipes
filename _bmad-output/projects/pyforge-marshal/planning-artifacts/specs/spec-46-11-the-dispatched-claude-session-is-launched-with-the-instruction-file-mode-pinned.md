---
title: '46.11: The dispatched Claude session is launched with the instruction-file mode pinned'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '08c466b8256359386772797845a4f3cd9408b2ed'
final_revision: 'pending — the merge commit of the fleet/agents-md-mod PR'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Claude Code 2.1.277's built-in `agents-md` mod reads its `instructionFiles` option from user settings or `--settings`, never the project, and its default mode stays out of any project with a `CLAUDE.md`. A dispatched `claude -p` session therefore depended on the launching operator's machine for whether nested `AGENTS.md` files (the atlas child) load.

**Approach:** the claude harness profile's launch argv carries `--settings` with the option inline as one JSON token. `render_dispatch_argv` substitutes placeholders by literal `str.replace`, so the braces are inert; an older Claude Code ignores an unknown plugin option and still reads `AGENTS.md` through the import.

## Boundaries & Constraints

**Always:**
- `{prompt}` appears exactly once; the wire-wrapped launch keeps the same tokens; authcheck and model translation unchanged
- The JSON is one whole argv token, never split, never formatted

**Never:**
- Do not read the operator's user settings at launch — the pin is the profile's, so every host behaves the same
- Do not add the option to any other harness profile — only Claude Code has the mod

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| plain launch | model opus | `… --settings <json> --model opus <prompt>`; JSON parses to the pinned mode | n/a |
| prompt with braces | prompt contains `{prompt}` / `}` | settings token unchanged; prompt delivered verbatim | n/a |
| older Claude Code | < 2.1.277 | unknown plugin option ignored; import still applies | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-262`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml`, `src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py`.
Ledger key: `46-11-the-dispatched-claude-session-is-launched-with-the-instruction-file-mode-pinned`.
Hand-driven 2026-09-20 in the fleet PR with scribe 19.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The next dispatched Claude session's journal `dispatch-launch` argv carries `--settings` with the pinned mode.

## Review Triage Log

### 2026-09-20 — hand-driven pass
  - `[medium]` `[patch]` the launch depended on the operator's user settings for the mod's mode. Pinned in the profile argv.
  - `[low]` `[reject]` ship a settings file and pass its path — one inline token needs no new placeholder and no packaged data file; the renderer's literal substitution makes it safe (tested with a brace-laden prompt).

## Auto Run Result

**Status:** done
**Summary:** `claude.toml` argv gains `--settings` + the inline JSON token; two tests pin the shape and the brace safety.
**Verification:** `test_harness_profile.py` 101 passed; `pyforge-marshal-test` / `pyforge-deps-test` — see the PR body.
**Files changed:** see Binding.
**Residual risks:** none from this change.
**Follow-up review recommendation:** false
