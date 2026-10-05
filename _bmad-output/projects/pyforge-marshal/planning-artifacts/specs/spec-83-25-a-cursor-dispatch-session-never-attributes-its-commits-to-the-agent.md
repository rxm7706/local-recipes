---
title: "83.25: A Cursor dispatch session never attributes its commits to the agent"
type: 'fix'
created: '2026-10-04'
status: 'done'
baseline_revision: adc14d4b57ddabeb27100d68795365059573d9dc
followup_review_recommended: false
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/skill_invoke_harness.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a Cursor dispatch session writes `Co-authored-by: Cursor <cursoragent@cursor.com>` into the commits it makes, and the repo refuses any AI attribution (AGENTS.md § Policy; the `commit-msg` hook).

- **Measured on 2026-10-04.** Mason Story 27.2's session committed `f8b58d7` (`retro(cfe): v8.91.7 …`) with that trailer. Story 83.17's check refused it at verification (MRS-GATE-019), after the whole build had run. The story parked, and the branch needed a message-only history rewrite and a force push (operator ruling, option a) to land as #1864.
- **The cause is the operator's Cursor config.** `cursor-agent` reads `attribution.attributeCommitsToAgent` (default `true`) from `cli-config.json` in its config directory, which is `$CURSOR_CONFIG_DIR`, else `$XDG_CONFIG_HOME/cursor`, else `~/.cursor`. The live value is `true`.
- **A repo file cannot turn it off.** `cursor-agent` validates a project `.cursor/cli.json` against a strict schema that admits only `permissions`, so an `attribution` key there fails validation.

**Approach:**
- Every Cursor launch marshal makes (the dispatch dev and fix sessions, and the planning-skill invoke in `adapters/skill_invoke_harness.py`) sets `CURSOR_CONFIG_DIR` to a run-scoped directory.
- That directory holds a `cli-config.json` copied from the operator's effective config with `attribution.attributeCommitsToAgent` and `attribution.attributePRsToAgent` set to `false`. The copy carries every other key unchanged (auth, model, permissions).
- The operator's own config is never written.
- If the operator's config cannot be read, the launch refuses with a named finding rather than starting an attributing session.
- Story 83.17's verification check stays as the backstop.

Ledger key: `83-25-a-cursor-dispatch-session-never-attributes-its-commits-to-the-agent`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 83.17 (the dispatch commit-attribution check). A defect of shipped behaviour, so no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given an operator config with `attributeCommitsToAgent: true` When marshal builds a Cursor launch Then its environment carries `CURSOR_CONFIG_DIR` pointing at a run-scoped `cli-config.json` whose `attribution` values are both `false` and whose other keys equal the operator's
- Given `CURSOR_CONFIG_DIR` or `XDG_CONFIG_HOME` already set When the copy is built Then it reads the effective config from the same directory `cursor-agent` would
- Given an unreadable operator config When marshal builds a Cursor launch Then it refuses with a named finding and starts no session
- Given the launch When it finishes Then the operator's own `cli-config.json` is byte-identical to before
- Given the rule removed When the tests run Then its test fails (mutation)

**Manual check:** a dispatched Cursor story's commits (`git log --format=%B origin/main..HEAD`) carry no `Co-authored-by` line.

## Boundaries & Constraints

**Always:**
- Keep Story 83.17's verification check as the backstop.

**Never:**
- Never write the operator's `cli-config.json`.
- Never copy the run-scoped config into the repo or into a tracked path; it holds the operator's auth.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (Cursor attribution) entry.
- Epic: Epic 83.
- Ledger key: `83-25-a-cursor-dispatch-session-never-attributes-its-commits-to-the-agent`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 at the operator's request ("proceed"), from mason 27.2's parked dispatch.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — blind, edge-case, verification-gap, and intent-alignment passes found no actionable gaps against the diff and AC)

## Auto Run Result

Status: done (implementation complete; working tree uncommitted pending operator PR)

Summary: Cursor harness launches (`BmadBuildHarness.launch_argv` for the `cursor` profile and live `HarnessSkillInvoker`) now copy the operator's effective `cli-config.json` into `worktree/.marshal/cursor-config/` with both attribution flags forced off, set `CURSOR_CONFIG_DIR` to that directory, and refuse launch with `MRS-DISP-061` when the operator config cannot be read. Story 83.17's verification gate is unchanged.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/cursor_launch_config.py` — pure path/attribution helpers (AD-4)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/cursor_launch_config.py` — read/copy/write run-scoped config
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` — apply overlay on cursor launches
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/skill_invoke_harness.py` — same for planning-skill live invoke
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `verdict.py` — register `MRS-DISP-061`
- `src/shared/packages/pyforge-marshal/tests/unit/test_cursor_launch_config.py` — AC + mutation guard
- `.gitignore` — ignore `**/.marshal/cursor-config/`
- Memlogs on `spec-pyforge-marshal` and co-governor `spec-pyforge-core`

Review: no patches; nothing deferred.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass (11680 passed)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass (130 passed)
- `pixi run --frozen -e pyforge-guild lint-types` — pass
- `python scripts/spec_surface_reconcile.py` — pass (exit 0)
