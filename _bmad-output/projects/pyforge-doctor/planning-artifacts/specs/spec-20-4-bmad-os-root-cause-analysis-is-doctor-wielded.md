---
title: '`bmad-os-root-cause-analysis` is doctor-wielded'
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      No `## Allowed actions (CAP-16)` entry names the mechanism by which a
      doctor station task may consult `bmad-os-root-cause-analysis`.
    evidence: |-
      Verified identical across all six wielding stations' persona files
      (warden, marshal, herald, steward, scribe, doctor) -- none of their
      `## Allowed actions (CAP-16)` sections name a mechanism for consulting
      their own routed `bmad-os-*` utility skill either; this is steward
      46.2's own pre-existing pattern, not something this story introduces
      or worsens.
    severity: low
baseline_revision: '32d0971b961c32ab2453fc00a6cb87f6ec711b40'
---

<intent-contract>

## Intent

**Problem:** Steward's Story 46.2 provisioned `bmad-os-root-cause-analysis` and, as a bulk
mechanical rollout across all six wielding stations, added a generic one-line pointer to
`bmad-agent-doctor/SKILL.md` ("Doctor wields `bmad-os-root-cause-analysis` ... see
adoption-register.md § 2."). It does not yet carry the doctor-specific guidance this story's
own Given/When/Then names: WHEN to reach for the skill (a detector finding needs a cause) and
the hard boundary on its use (never to change a verdict) -- the same boundary `bmad-agent-warden`'s
own routing line already states for its two utility skills ("advisory only -- never a second
PR-gate verdict").

**Approach:** Refine the existing routing line in `bmad-agent-doctor/SKILL.md` to state the
condition and the boundary verbatim, mirroring warden's own already-customized pattern. The
adoption-register.md § 2 row already names doctor as `bmad-os-root-cause-analysis`'s sole
wielder (landed in the original planning commit, unchanged by 46.2) and the AD-2 meta-test
(`pyforge-steward/tests/meta/test_adoption_register.py`) already passes -- both are verified,
not edited. `CLAUDE.md` is verified to carry no mention of the skill and stays untouched.

## Boundaries & Constraints

**Always:** Keep the skill name backtick-quoted and unchanged (`bmad-os-root-cause-analysis`) so
the AD-2 meta-test's substring match keeps matching. State the "never to change a verdict"
boundary explicitly, echoing doctor's own Charter (findings stay advisory, never a second PR
gate). Preserve the `## Utility skill routing (AD-2)` heading and the `adoption-register.md § 2`
citation.

**Never:** Do not edit `adoption-register.md`, `CLAUDE.md`, or any other station's persona
`SKILL.md`. Do not touch the ten `bmad-os-*` vendored skill directories. Do not widen doctor's
exit-code domain or introduce a second verdict vocabulary -- this is a documentation-only routing
refinement.

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-doctor/SKILL.md` (lines 12-14, `## Utility skill routing (AD-2)`)
  -- the generic line steward 46.2 added; refine its wording per Intent. Reuse
  `bmad-agent-warden/SKILL.md`'s own line (same section heading) as the customization precedent.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  § 2, row `bmad-os-root-cause-analysis | utility-skills | doctor | ...` -- already correct
  (verified 2026-09-07); read-only, no edit.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` --
  `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` is the AD-2 meta-test;
  already green pre-edit (confirmed via `pixi run -e pyforge-steward python -m pytest
  src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py -v`, 6/6 passed),
  must stay green after the persona-file edit.
- `CLAUDE.md` -- verified (`grep -n "root-cause-analysis" CLAUDE.md` -> no match); read-only,
  must stay that way.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` (key
  `20-4-bmad-os-root-cause-analysis-is-doctor-wielded`, currently `blocked`) -- flip to `done`
  once the story's own acceptance is verified (AD-10 cross-station convention: a `blocked`
  row's dependency has landed, so the row resolves at dispatch, not by a separate story).

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-agent-doctor/SKILL.md` -- replace the routing line under
  `## Utility skill routing (AD-2)` with one that states both the trigger condition ("when a
  detector finding needs a cause") and the boundary ("never to change a verdict"), keeping the
  skill name and the `adoption-register.md § 2` citation.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` -- flip
  `20-4-bmad-os-root-cause-analysis-is-doctor-wielded` from `blocked` to `done`.

**Acceptance Criteria:**
- Given the skill installed by steward 46.2, when `bmad-agent-doctor/SKILL.md` is read, then its
  routing line names `bmad-os-root-cause-analysis` and states both "when a detector finding needs
  a cause" and "never to change a verdict".
- Given the adoption-register.md § 2 table, when the `bmad-os-root-cause-analysis` row is read,
  then it names `doctor` as the sole wielding station (unchanged by this story).
- Given `pixi run -e pyforge-steward python -m pytest
  src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py`, when it runs after
  this story's edit, then all tests still pass (the AD-2 meta-test).
- Given `CLAUDE.md`, when grepped for `root-cause-analysis`, then there is no match, before and
  after this story.
- Given `pixi run -e pyforge-doctor pyforge-doctor-test`, when it runs after this story's edit,
  then it is still green (no doctor package code changed by this story).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 11 findings — high 3, medium 0, low 2, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: the new routing clause used a plain ASCII `--` instead of the em dash `—` used everywhere else in this same file (lines 3, 6, 10, 31-33, 49) and in the sibling `bmad-agent-warden/SKILL.md` line -- evidence: confirmed via direct grep of both files. Action: swapped `--` for `—`.
  - `[false]` `[reject]` Blind Hunter: terminology drift -- "never to change a verdict" is a third phrasing alongside the file's existing "not a second PR gate" (line 10) and "never a competing PR verdict" (line 10) -- refutation: the file already carries two different phrasings of this same invariant before this diff; a third, AC-traceable phrasing for this specific skill's boundary is consistent with, not worse than, the file's existing style, and no concrete harm is named beyond taste.
  - `[false]` `[reject]` Blind Hunter: the shipped wording restructures and adds "advisory only" beyond the epics.md AC's literal quoted phrase ("reach for ... when a detector finding needs a cause, never to change a verdict") -- refutation: the epics.md Given/When/Then is descriptive prose, not a literal string contract; "advisory only" is deliberately lifted from `bmad-agent-warden/SKILL.md`'s own precedent line per this story's spec Design Notes, strengthening rather than contradicting the AC's intent.
  - `[high]` `[patch]` Blind Hunter (grouped with Edge Case Hunter and Intent Alignment Auditor below -- same root cause): `sprint-status-ledger.yaml`'s `20-4-bmad-os-root-cause-analysis-is-doctor-wielded` key was still `blocked` after the implementation subagent's reported ledger flip -- verified true: the flip had landed on the wrong copy of the file (the shared main-checkout path outside this worktree, per this run's own mistaken instruction to the implementation subagent that conflated `sprint-status-ledger.yaml`, a per-worktree tracked file, with the Tier-3 `implementation-artifacts` backlink convention that applies only to the spec file). Action: applied the flip directly to the worktree's own tracked copy (`_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml:52`, `blocked` -> `done`); left the main-checkout copy untouched since it had already reverted to `blocked` on its own by the time this was caught (consistent with that path being shared with other concurrent sessions, not owned by this run).
  - `[false]` `[reject]` Blind Hunter: no CAP-16 wiring names the mechanism for consulting `bmad-os-root-cause-analysis` -- rerouted to `defer` below (real, pre-existing, not this story's to fix) rather than rejected outright; recorded once there, not double-counted.
  - `[false]` `[reject]` Blind Hunter: no durable story-spec artifact exists yet under `pyforge-doctor`'s tracked `planning-artifacts/specs/` -- refutation: this repo's own convention (CLAUDE.md) is explicit that story-spec promotion happens after the story merges, not during the run; identical disposition already recorded on Story 20.3's own review pass for the same non-issue.
  - `[low]` `[patch]` Blind Hunter: the new clause runs on without a comma after the closing parenthesis, unlike `bmad-agent-warden/SKILL.md`'s own comma-separated equivalent -- evidence: confirmed via direct comparison of both lines. Action: added the comma (bundled into the same edit as the em-dash patch above).
  - `[false]` `[reject]` Blind Hunter: "advisory only" is now stated in both the routing line and the file's Overview with no cross-reference between them -- refutation: no concrete harm named beyond restatement; the file already restates its "advisory, not a second PR gate" invariant across multiple sections (Overview and Forbidden Actions) before this diff, an established pattern this diff does not worsen.
  - `[false]` `[reject]` Blind Hunter: scope check on whether `adoption-register.md` § 2's row needed a diff-visible edit -- refutation: verified the row already named doctor as sole wielder before this story was dispatched (landed in the original 2026-09-06 lifecycle-planning commit); the Surface line names it because the AC is anchored on it, not because it needed to change.
  - `[high]` `[patch]` Edge Case Hunter (grouped with Blind Hunter and Intent Alignment Auditor above -- same root cause): claim finding that the ledger still read `blocked` in the diff under review -- verified true, same fix as above.
  - `[high]` `[patch]` Intent Alignment Auditor (grouped with Blind Hunter and Edge Case Hunter above -- same root cause): divergence noted between the intent-contract's Execution list (which names the ledger flip) and the diff (which did not carry it) -- verified true, same fix as above.

## Design Notes

**Why refine rather than leave the generic line as-is.** Steward's 46.2 rollout is a mechanical,
per-station-agnostic template applied to all six wielding stations in one pass; it already
diverges per station where a station's own Charter demands it (warden's line already carries its
own "advisory only" guardrail). This story is doctor's own dedicated relay of the lifecycle
spine's CAP-3 routing requirement, and its Given/When/Then names specific guidance text the
generic line does not yet carry -- landing that refinement is this story's entire scope.

**Why no adoption-register.md edit.** The register's § 2 row already names doctor as sole
wielder and was already correct before this story was dispatched (it was authored in the
original 2026-09-06 lifecycle-planning commit, not by 46.2). The Surface line names the register
row because the AC is anchored on it, not because it needs to change.

## Verification

**Commands:**
- `grep -n "root-cause-analysis" .claude/skills/bmad-agent-doctor/SKILL.md` -- expected: the
  refined routing line, naming the trigger condition and the boundary.
- `grep -c "root-cause-analysis" CLAUDE.md` -- expected: `0`.
- `pixi run -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py -v` -- expected: all tests pass.
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green, no regressions.
## Auto Run Result

**Summary of implemented change:** refined `bmad-agent-doctor/SKILL.md`'s generic steward-46.2
routing line for `bmad-os-root-cause-analysis` to state both the trigger condition ("when a
detector finding needs a cause") and the hard boundary ("advisory only, never to change a
verdict"), mirroring `bmad-agent-warden/SKILL.md`'s own already-customized precedent. Flipped
`sprint-status-ledger.yaml`'s `20-4-bmad-os-root-cause-analysis-is-doctor-wielded` key from
`blocked` to `done`. `adoption-register.md` § 2 and `CLAUDE.md` were verified, not edited.

**Files changed:**
- `.claude/skills/bmad-agent-doctor/SKILL.md` -- routing line refined (trigger + boundary),
  then patched for punctuation (em dash, comma) during review.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` -- `20-4`
  key flipped `blocked` -> `done`, corrected during review to the worktree's own tracked copy
  after the first attempt landed on the wrong (shared, out-of-worktree) copy of the file.

**Review findings breakdown:**
- Patched (2 entries): the grouped ledger-not-flipped finding (high; Blind Hunter + Edge Case
  Hunter + Intent Alignment Auditor, same root cause); the punctuation/comma finding (low; Blind
  Hunter).
- Deferred (1): no CAP-16 action-kind names the mechanism for consulting a routed `bmad-os-*`
  utility skill -- verified identical across all six wielding stations, pre-existing, not this
  story's to fix.
- Rejected/false (5, Blind Hunter unless noted): terminology drift across three phrasings of the
  same advisory-only invariant (pre-existing pattern, no named harm); wording deviates from the
  epics AC's literal quote (AC is descriptive prose, not a string contract, and the added
  "advisory only" is a deliberate, spec-documented choice); no durable story-spec artifact yet
  (post-merge promotion convention, not yet due, identical to Story 20.3's own disposition);
  unreferenced "advisory only" restatement (no concrete harm, pre-existing multi-restatement
  pattern in this file); scope check on `adoption-register.md`'s row (already correct pre-diff).

**Follow-up review recommendation:** `true`. Named unverified risk: this run's implementation
subagent was given a mistaken instruction conflating `sprint-status-ledger.yaml` (a per-worktree
tracked file) with the Tier-3 `implementation-artifacts` backlink convention (which applies only
to the story-spec file), and applied the ledger flip to the shared main-checkout copy outside
this worktree instead. That copy was found reverted to `blocked` by the time this was caught
(consistent with it being shared with other concurrent sessions, not owned by this run), and this
pass corrected the fix to the worktree's own tracked copy -- but whether that stray out-of-worktree
write left any transient or committed-elsewhere drift visible to a concurrent session is
unverified from inside this worktree. Patched counts by verdict: high 1 (grouped), low 1.

**Verification performed:**
- `grep -n "root-cause-analysis" .claude/skills/bmad-agent-doctor/SKILL.md` -- the refined,
  patched routing line.
- `grep -c "root-cause-analysis" CLAUDE.md` -- `0`.
- `pixi run -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py -v` -- 6/6 passed, both before and after the punctuation patch.
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- 1341 passed, 1 skipped, both before and
  after the punctuation patch.
- `grep -n "20-4-bmad-os-root-cause-analysis-is-doctor-wielded" _bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` (worktree copy) -- confirmed `done`, and the
  unified diff against baseline_revision shows exactly the two intended file changes.

**Residual risks:** the named unverified risk above (stray write to a shared out-of-worktree
file, since self-reverted). No code paths changed; this remains a documentation-only routing
refinement with no runtime behavior at stake.
