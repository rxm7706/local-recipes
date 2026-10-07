---
title: "22.17: A land-only refusal names the gate that refused it"
type: 'fix'
created: '2026-10-07'
status: 'ready-for-dev'
baseline_revision: '966b166f76797916b96286b88587aa6f10f8240d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** when a harness-done story's land-only verification refuses, the operator is told only that it refused.
The CLI does not say which gate, command or exception caused it, and nothing is written to the run dir.

- **Where it happens.** On the harness-done CAP-4 land-only path, `cli/dispatch.py` `_verification_verdict_for_cap4`
  (about :1031-:1064) calls `evaluate_dispatch_verification` and returns only a `DispatchVerificationVerdict`. It
  discards `envelope.findings`. It also maps any `ProcessError`, `VcsCommandError`, `OSError`, `TypeError` or
  `AttributeError` to `REFUSED` with no message. `dispatch_land.py` `execute_dispatch_land` (about :1050-:1068) then
  returns `SKIPPED_UNVERIFIED` with only `MRS-DISP-014`'s generic text. `_attempt_harness_done_cap4` (about
  :1067-:1117) and the CLI branch that calls it (about :3000-:3040) carry forward only the land verdict, the named
  target and the check-wait record. The CLI prints `land_verdict: skipped-unverified` and `MRS-DISP-040`
  ("awaiting-operator"). Unlike the supervisor's `_run_and_journal_verification` (`dispatch_supervisor/__main__.py`,
  about :2320-:2470), this path journals no `dispatch-verification` entry in the run dir.
- **The live case.** On 2026-10-07 the warden 14.2 and steward 74.2 land-only dispatches, launched at the same time,
  both returned `skipped-unverified`. A few minutes later the operator replayed `evaluate_dispatch_verification` by
  hand on warden's worktree and got verdict `warn` (scope advisories only), so the landing would have gone ahead. The
  likely cause was that the two runs' `platform-ci-local` gates collided: fixed ports 15432/16379, a fixed work dir
  `/tmp/platform-ci-local`, and no lock in `scripts/platform-ci-local.sh`. The operator had to reconstruct that by hand
  because no output named the gate.

**Approach:** the land-only path keeps the whole verification result, not only the verdict:

- `_verification_verdict_for_cap4` returns the verdict together with the verification's findings. A caught exception
  becomes one ERROR finding whose message names the exception type and its text. The verdict stays `refused` (AD-8).
- Those findings, and the land envelope's `MRS-DISP-014`, reach the dispatch CLI envelope beside `MRS-DISP-040`, so the
  printed output names the failing gate and command.
- The land-only verification is journaled in the story's latest run dir as a `dispatch-verification` INTENT/OUTCOME
  pair with the payload the supervisor writes (`verdict`, `ok`, `failed_gate`, `failed_message`,
  `scope_violation_advisories`). The supervisor's payload builder is shared rather than copied, and the pair uses its
  own journal writer id.

The `platform-ci-local` lock is out of scope here. It belongs to the script's owner and is chained separately.

Ledger key: `22-17-a-land-only-refusal-names-the-gate-that-refused-it`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-162 (← `spec-marshal-single-story-dispatch` CAP-4; Story 22.4, a
  verified story lands through the existing machinery), on the harness-done land-only path of CAP-169 (←
  `spec-marshal-single-story-dispatch` CAP-11; Story 29.2). Its independent verification is CAP-161's (Story 22.3).
  This is a gap in shipped behaviour, so no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-07 (landing gaps, again), item 3.

## Acceptance Criteria

- Given a harness-done story whose land-only verification refuses because a verify command exits non-zero (a fake
  process port in which `pixi run -e pyforge-guild platform-ci-local -- --test` exits 1 with stderr
  `port 15432 already in use`) When `marshal factory dispatch <slug> <key>` takes the CAP-4 land-only path Then the CLI
  envelope's findings include the verification's own failing-gate finding, naming that command and its exit code,
  beside `MRS-DISP-014` and `MRS-DISP-040`, and the CLI's printed output contains the command string.
- Given `evaluate_dispatch_verification` raises `OSError("boom")` (and, by parametrization, each of `ProcessError`,
  `VcsCommandError`, `TypeError`, `AttributeError`) When the land-only path runs Then `land_verdict` is
  `skipped-unverified`, and the envelope carries one ERROR finding whose message contains the exception's type name and
  `boom`.
- Given either refusal and a story with a prior dispatch run dir When the land-only path finishes Then that run dir's
  journal ends with a `dispatch-verification` INTENT/OUTCOME pair whose OUTCOME payload has `verdict: refused`,
  `ok: false` and the failing gate's code and message. `gather_dispatch_journal_facts` reads them as the run's
  `verification_verdict`, `verification_failed_gate` and `verification_failed_message`.
- Given a land-only verification that passes (`verified`, or `warn` with scope advisories only) When the story lands
  Then the landing behaves as today, and the journaled OUTCOME records that verdict with its advisories. The run dir's
  latest verification is always the one the landing acted on.
- Given no prior run dir for the story When the land-only path refuses Then nothing is journaled, the envelope still
  carries the findings, and the missing run dir is not itself a finding.
- Given the findings pass-through removed (mutation) When the station suite runs Then the test that asserts the
  failing gate's finding reaches the CLI output fails.

## Boundaries & Constraints

**Always:**
- A non-`verified` land-only verification never lands, and an exception is still `refused` (AD-8). Only what is
  reported changes.
- One payload shape for every `dispatch-verification` OUTCOME: the supervisor's builder, shared, not a second copy.
  The entries go through the same journal-entry builder, so the same redaction and offload rules apply.
- Findings keep their own codes (AD-15). Add no new code unless the exception finding needs one, and if it does,
  register it in `core/findings.py` and `core/verdict.py`.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never change `scripts/platform-ci-local.sh` in this story (its lock is chained separately).
- Never renumber or rewrite the supervisor's own journal entries. The land-only pair is appended with its own writer
  id.
- Never let a journal write failure fail the land-only command. It becomes a WARN finding in the envelope.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-07 (landing gaps, again) entry.
- Epic: Epic 22 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `22-17-a-land-only-refusal-names-the-gate-that-refused-it`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: drop the findings pass-through in `_verification_verdict_for_cap4` and re-run the station suite. The CLI-output test fails. Restore it.
- On the next real land-only refusal: the CLI output names the failing gate, and the run dir's `journal.jsonl` ends with its `dispatch-verification` OUTCOME.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
