---
title: "85.3: The fix turn is safe to switch on in dev and staging"
type: 'feature'
created: '2026-10-03'
status: 'done'
baseline_revision: 712b45809c253baea1d5175872f7afb23170f66e
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.verify_fix_loop
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "a verification refusal parks the story for the operator (Story 83.10), with no fix turn"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Before the fix turn can run on operator hosts, the safety findings from the two Story 85.1 reviews must close: redaction misses `DATABASE_PASSWORD=`, `AWS_SECRET_ACCESS_KEY=`, short `sk-ant-` keys, YAML and JSON `password:`, `Authorization: Basic`, URL passwords containing `/`, and it runs after the tail is cut, so a cut mid-URL leaks part of a credential; the prompt travels on argv (visible in `ps`) (M7). The timeout kill sends SIGTERM to the session's process group only (since Story 85.2), with no bounded wait, SIGKILL or reap (M4). No publisher heartbeat is sent during the turn or the second verification, so the portal marks the run `heartbeat_lost` after 300 s, while the journal heartbeat writes every second (M3). `--continue` resumes the most recent session, not this one, and the `{{session_id}}` token is always empty (L1); the resolved profile is not compared with the launch profile before resume (L3); MRS-GATE-018 still feeds a pseudo-command into the prompt (L4). An unreadable or malformed `flags.json` journals nothing (M2). Unset `PYFORGE_ENVIRONMENT` reads `dev`, so turning the flag on in dev turns it on for every operator host (N8). A fix session that exits while no supervisor is alive leaves its INTENT open: the run reads FAILED, resume refuses MRS-DISP-023, the story parks and the turn's edits are never re-verified (85.2 final landing review, 2026-10-04). The tick loop's liveness check on the original session (`process.is_alive(session_pid)` in `dispatch_supervisor/__main__.py`) has no start-time check, so a reused pid could let the idle checkpoint commit a running fix session's tree (85.2 final landing review, 2026-10-04).

**Approach:** Close those findings, then set the flag ON in dev and staging (OFF in production), as the CAP-286 rollout says.

Ledger key: `85-3-the-fix-turn-is-safe-to-switch-on-in-dev-and-staging`.
Type / Effort / Deps: feature / M / S-85.2.

### Living CAP citations

- `spec-pyforge-marshal` CAP-286 (FR-233), split by operator ruling 2026-10-03 after two independent reviews of Story 85.1; same flag `pyforge.marshal.verify_fix_loop`.

## Acceptance Criteria

- Given output tails carrying each credential shape above, including one cut mid-URL When the tail is journaled and the prompt is built Then no credential survives, and the prompt is passed by file or stdin, never argv
- Given a fix session that ignores SIGTERM and has children When its budget runs out Then its process group is terminated, waited on, killed and reaped, and the outcome is journaled
- Given the flag on and a fix turn whose session exited while no supervisor was alive When the operator resumes the run Then resume does not refuse MRS-DISP-023 for it, and the supervisor closes the open INTENT, commits the turn's edits and re-verifies once (land on green, MRS-DISP-060 on red)
- Given the original session's pid is reused by an unrelated process When the tick loop checks liveness Then the start-time check reads it dead and no checkpoint commits a live fix session's tree
- Given a fix turn of more than 300 s When the portal sweeps Then the run is not `heartbeat_lost`; the journal heartbeat writes at the tick rate
- Given a profile that declares resume When the fix turn runs Then it resumes the recorded session id with the launch profile's own harness, else it launches a fix-only session
- Given an unreadable or malformed flag tree When verification refuses Then a warning is journaled and no turn runs
- Given the change When the flag is read with `PYFORGE_ENVIRONMENT` unset, `dev`, `staging` and `production` Then it reads on, on, on and off, and pyforge-core's `test_flags.py` and Platform CI's `test_openfeature_file_flags.py` pin that

## Boundaries & Constraints

**Always:** Redact before truncating. Keep production OFF. Fix each defect where it lives and pin it with a test that fails without the fix.

**Never:** Never put a prompt or a credential on argv. Never resume a session other than the one recorded at launch.

</intent-contract>

## Design notes (non-binding)

- Both live CLIs offer a session-id form (`claude --session-id/--resume <id>`, `cursor-agent --resume [chatId]`); verify the form on each before declaring it, else keep fix-only.
- Story 80.1's `_WaitHeartbeat` is the pattern for the publisher heartbeat during a wait.
- Deploy note: OFF in production relies on `PYFORGE_ENVIRONMENT=production` being set on production hosts.
- Flag-independent change (recorded, accepted by the 2026-10-04 landing review): with the flag OFF too, the Claude launch argv now carries `--session-id <uuid>` (a uuid minted per dispatch), and the launch OUTCOME journals `harness_session_id` whenever the rendered launch argv carried it -- so a later fix turn can resume that session. A profile whose launch never passes `{session_id}` (Cursor) journals none and its fix turn is fix-only.
- CLI forms, verified live 2026-10-04 with harmless prompts (no secrets): claude 2.1.284 -- `claude -p --resume <id> < prompt-file` read the prompt from stdin and answered from the session pinned by `--session-id <id>` at launch; `--session-id <id> --resume <id>` exits 1 ("--session-id can only be used with --continue or --resume if --fork-session is also specified"). cursor-agent 2026.10.01 -- `cursor-agent -p --trust --workspace <dir> < prompt-file` reads the prompt from stdin; `--resume <chatId>` with a stdin prompt also resumes, but the launch cannot pin the chat id and the text-mode launch never prints it, so Cursor stays fix-only. A fix template declares its prompt form: `{prompt_stdin}` (the 0600 prompt file is the session's stdin) or `{prompt_file}` (its path, inside a fixed instruction); `{prompt}` is refused there, and a profile with no fix template (copilot, gemini, devin) refuses the turn with MRS-DISP-058 naming the profile.

## Binding

Parent: `spec-pyforge-marshal` CAP-286 (Story 85.1, split 2026-10-03).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (85.1 split) entry.
Ledger key: `85-3-the-fix-turn-is-safe-to-switch-on-in-dev-and-staging`.
Ledger status at mint: `backlog`.
Deps: S-85.2.
Minted 2026-10-03 at the operator's request (split 85.1, keep Cursor).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Tests that carry the criteria (run by `pyforge-marshal-test` above):**
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py` — the two-state flag test: the supervisor reads `pyforge.marshal.verify_fix_loop` for real from two flagd trees, one `"on"` and one `"off"`. On: the fix turn resumes the recorded session id only with the launch profile's own harness, else fix-only (AC6); the run publisher's heartbeat is called during the fix wait, while a restarted supervisor settles an in-flight turn, and from a progress thread during the re-verification, throttled to one call per 30 s under one lock (AC5); the verification OUTCOME's `output_tail` is redacted before it is cut, with the cut inside a URL credential (AC1); a broken flag tree journals one warning and runs no turn (AC7); `dispatch resume` re-spawns the supervisor for a fix turn whose session exited while no supervisor was alive, with no MRS-DISP-023 (AC3); an open INTENT reads LIVE to `dispatch status`, `marshal status` and the in-flight guard alike; the tick loop reads a reused session pid as dead and checkpoints nothing (AC4). Off: a refusal parks exactly as `main` does, and a turn found in flight is only stopped, journaled and parked.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py` — every credential shape the AC names plus the landing review's five, redacted before truncation at both sites (AC1); no shipped fix template (claude, cursor, the repo's cursor overlay) carries a prompt on argv, the launch feeds the 0600 prompt file on stdin, `{prompt}` in a fix template is refused, a profile without a fix template refuses naming itself (AC1); the packaged Claude resume argv names `--resume <id>` without `--session-id`; `terminate_process_group` against real processes: SIGTERM then reap, SIGKILL then reap for a leader that ignores SIGTERM, and a SIGTERM-ignoring child swept after its leader obeys (AC2).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — the launch journals `harness_session_id` only when the rendered launch argv carried it (AC6).
- `src/shared/packages/pyforge-core/tests/unit/test_flags.py` and `src/platform/tests/test_openfeature_file_flags.py` — the flag reads on, on, on and off with `PYFORGE_ENVIRONMENT` unset, `dev`, `staging` and `production` (AC8).

## Review Triage Log

### 2026-10-04 — Review pass (the harness's own pass; corrected by the landing review below)
- verdicts: reported 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0. That verdict was wrong: the independent landing review below found 5 high, 3 medium and 8 low findings in the same diff, and `detectors-ci` was red on this spec (`flag-verification-names-no-test`).
- findings: (none recorded by this pass)

### 2026-10-04 — Landing review (independent reviewer); verdict SEND BACK; fixed by the operator's fixer
- verdicts: 16 findings — high 5, medium 3, low 8, false 0. All fixed on the branch; none deferred. Production stays OFF; with the flag off the supervisor's behaviour is identical to `main` apart from the recorded Claude `--session-id` launch change (Design notes).
- findings:
  - `[high]` `[fix]` H1 The Claude `resume_argv` passed `--session-id {sid} --resume {sid}`, which claude 2.1.284 refuses. Fixed: `--resume {session_id}` only; `--session-id` stays in the launch argv. Test: the packaged resume argv rendered has no `--session-id` and names the id after `--resume`; the launch argv pins it.
  - `[high]` `[fix]` H2 A session uuid was minted and journaled for every profile, though the Cursor launch never passes it, so a Cursor fix turn would resume an id the session never had. Fixed: `harness_session_id` is journaled only when the rendered launch argv carries it; Cursor (packaged and overlay) declares no `resume_argv` and is fix-only; the dead Cursor log parse (`parse_harness_session_id_from_log`) and the unread `DispatchJournalFacts.harness_session_id` / `launch_harness_profile` fields are removed. Tests: dispatch journals the id with an argv that carries it and omits it with one that does not; the shipped Cursor profiles declare no resume template.
  - `[high]` `[fix]` H3 JSON `"password": "x"`, short `sk-ant-` keys, `POSTGRES_PASSWORD=`, `GITHUB_TOKEN=` and `db_password:` leaked. Fixed: one key=value / key: value rule over quoted or bare keys naming password, passwd, secret, token, api key or access key (any prefix or suffix: `DATABASE_PASSWORD`, `AWS_SECRET_ACCESS_KEY`, `client_secret`), quoted values taken to their closing quote (escapes included); `sk-ant-` matches one or more characters; URL, Bearer and Basic shapes kept. Test: 23 shapes, every AC shape plus these.
  - `[high]` `[fix]` H4 `detectors-ci` red on `flag-verification-names-no-test`. Fixed: `## Verification` names the tests that carry the criteria, the two-state test first.
  - `[high]` `[fix]` H5 `{prompt_file}` put the prompt file's path on argv as the prompt, which neither CLI reads, and profiles without fix templates fell back to the launch argv with an empty prompt. Fixed: a fix template declares `{prompt_stdin}` (the launch opens the 0600 prompt file as the session's stdin) or `{prompt_file}`; `parse_profile` refuses `{prompt}` in `resume_argv` / `fix_only_argv` and refuses either fix form in the launch `argv`; a profile with no fix template refuses with MRS-DISP-058 naming it. Claude and Cursor stdin reads were verified live (Design notes). Tests: the launch's stdin holds the prompt and no argv token does, for claude resume, claude fix-only and the Cursor overlay; copilot, gemini and devin refuse; the template parse cases.
  - `[medium]` `[fix]` M1 Children that ignore SIGTERM survived a leader that obeyed it. Fixed: the group id is read before SIGTERM; once the leader is gone, `killpg(pgid, 0)` finds any member left and the group is SIGKILLed (never a group `<= 1` or the supervisor's own). Real-process test: a SIGTERM-obeying leader with a SIGTERM-ignoring child.
  - `[medium]` `[fix]` M2 Surviving mutants pinned: redact-before-truncate at both sites with the cut inside a URL credential (M01, M02); Basic auth (M05); the prompt never on argv at the renderer, both profiles and the launch (M08); the reap (M10); the tick loop's start-time check (M11); the session-id journal and the resume with `resolution.profile` (M13, M18); the publisher heartbeat during the fix wait and while finalize settles an in-flight turn (M14, M19); the re-verification progress thread by an assertion on its calls (M15). The vacuous `"DATABASE" in scrubbed` assertion is gone. A `run_dispatch_resume` test covers AC3.
  - `[medium]` `[fix]` M3 `marshal status` called the verdict resolver without `run_dir`, so it disagreed with `dispatch status` and resume on an open INTENT with a dead session. Fixed: LIVE is keyed on `journal.verify_fix_started_at` (set exactly while an INTENT is open) and the refold is gone. Test: `marshal status`'s overlay, `dispatch status` and the in-flight guard all read LIVE.
  - `[low]` `[fix]` The in-flight guard assertion is restored for every case and the test renamed (`test_an_open_fix_turn_reads_live_to_every_reader_until_a_supervisor_settles_it`).
  - `[low]` `[fix]` The supervisor passes `resolution.profile`, not `getattr(...)`.
  - `[low]` `[fix]` The fix turn's publisher heartbeat is throttled to one call per 30 s (`_FixTurnPublisherHeartbeat`); the journal heartbeat keeps the tick rate.
  - `[low]` `[fix]` Every fix-turn publisher call is made under one lock, and the progress thread is joined without a timeout once stopped, so no call overlaps the supervisor's next one.
  - `[low]` `[fix]` The prompt file is written 0600, also when it already exists.
  - `[low]` `[fix]` The spec states the flag-off Claude `--session-id` launch change (Design notes).
  - `[low]` `[fix]` The spec-pyforge-core memlog names `cli/dispatch.py` and `dispatch_supervisor/__main__.py` by full path.
  - `[low]` `[fix]` This log's first entry is corrected.
- mutation (scratch copies, current tests): all 34 mutants killed; the unmutated control passes (578 tests). The reviewer's survivors re-expressed against the fixed code -- M01, M02 (tail before scrub, both sites), M05 (no Basic), M08 as three (prompt appended to argv, stdin not fed, `{prompt}` back in the Claude template), M10 (no reap), M11 (tick loop without the start-time check), M13 (`resolved_profile=None`), M14 (no publish in the fix wait), M15 (progress thread never started -- now failed by the assertion on its calls), M18 (session id never journaled), M19 (no publish while finalize settles an in-flight turn) -- and its killed ones (M06, M07, M09, M12, M16, M17) all fail the new tests; plus 15 for the fixes themselves: H1 (`--session-id` back in the resume argv), H3 x6 (no `token`, no `access key`, no quoted key, no key prefix, `sk-ant-` needing 8, no `:` separator -- the last three standing in for the reviewer's M03 and M04, whose text the one rule replaced), H5 x3 (fallback to the launch argv, `{prompt}` allowed in a fix template, prompt file 0644), M1 (no group sweep), M18b (session id journaled for every launch), M3 (facts-keyed LIVE only with a run dir), and the throttle and lock removed.

### 2026-10-04 — Post-landing delta review (independent reviewer, after #1812 merged); verdict FIX FORWARD as Story 85.4
- verdicts: all 16 send-back fixes verified (H1–H5, M1–M3 and the LOWs). New findings: medium 1, low 7. Mutants: 24 of 29 killed; X02, X11 and X12 survived as test gaps, X09 is near-equivalent and X14 is harmless.
- findings:
  - `[medium]` `[defer: Story 85.4]` The `_SECRET_KEY_VALUE` quoted-value branch backtracks exponentially on an unclosed quote followed by backslashes. The scrub runs on full outputs in the supervisor thread, so a run can hang (dev and staging).
  - `[low]` `[defer: Story 85.4]` `_URL_CREDENTIALS` is quadratic on long separator-free runs.
  - `[low]` `[defer: Story 85.4]` A compiler location `file.py:42:5:` loses its line and column.
  - `[low]` `[defer: Story 85.4]` Five shapes leak: `--password x`, `Authorization: token`, bare `ghp_`, an empty-user URL, `Cookie:`.
  - `[low]` `[defer: Story 85.4]` The fix wait's journal heartbeat writes at 1 Hz, not the tick rate (AC5).
  - `[low]` `[fix]` Correction to the landing-review entry above: "flag off identical to main" also excepts the AC4 liveness changes. The tick loop judges the session by start time and zombie state on every run, and `_is_dispatch_session_alive` gained the zombie check. Both are intended.
  - `[low]` `[defer: Story 85.4]` X02, X11 and X12 have no test.
  - `[low]` `[defer: Story 85.4]` The SIGTERM-ignoring-grandchild test relies on a fixed 0.3 s sleep.

## Auto Run Result

Status: done

Summary: Story 85.3 closes Story 85.1 review safety gaps and turns `pyforge.marshal.verify_fix_loop` on in dev and staging (off in production). Fix-turn tails are scrubbed before truncation; prompts go through a run-dir file, not argv; timeout kill SIGTERM/SIGKILL/reaps; publisher heartbeats during fix wait; session resume uses recorded `harness_session_id` with profile match; open fix INTENT with a dead session stays resumable (no MRS-DISP-023); original session liveness uses start-time check in the tick loop.

Files changed (vs baseline `712b45809c`):
- `src/platform/config/flag-overlays.json` — verify_fix_loop on dev/staging, off production
- `src/platform/tests/test_openfeature_file_flags.py`, `pyforge-core/tests/unit/test_flags.py` — per-environment pins
- `core/dispatch_verify_fix.py`, `dispatch_verify.py` — scrub, SIGKILL/reap, prompt file constant
- `dispatch_supervisor/__main__.py`, `cli/dispatch.py` — heartbeat, pending INTENT LIVE, session liveness
- `adapters/harness_bmadbuild.py`, harness profiles (claude/cursor + overlay) — prompt on stdin (`{prompt_stdin}`), session id argv (Claude launch only); landing-review send-back fixes 2026-10-04 (see the Review Triage Log)
- Unit tests in `test_dispatch_verify_fix.py`, `test_dispatch_supervisor_verify_fix.py`, etc.

Review: the harness's own pass reported 0 items; the independent landing review sent the story back with 16 findings, all fixed (Review Triage Log).

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 11162 passed
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK

Governed paths reconciled in memlogs:
- Owning `spec-pyforge-marshal/.memlog.md`: all marshal + platform flag paths above (full list in memlog event 2026-10-04 Story 85.3)
- Co-governor `spec-pyforge-core/.memlog.md`: marshal `src/` surfaces + `test_flags.py`
- Co-governor `spec-pyforge-unifying-strategy/.memlog.md`: `flag-overlays.json`, `test_openfeature_file_flags.py`

Residual risks: Cursor fix turns are fix-only (its launch records no session id); production still relies on `PYFORGE_ENVIRONMENT=production` for flag off.
