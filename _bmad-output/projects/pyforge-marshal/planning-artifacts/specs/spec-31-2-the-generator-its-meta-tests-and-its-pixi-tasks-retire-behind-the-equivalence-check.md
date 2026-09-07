---
title: "The generator, its meta-tests and its pixi tasks retire behind the equivalence check"
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      `architecture-bmad-infra.md` was not glossed with an FR-129/FR-132 note recording the
      refusal, even though 31.2's own Surface line names that file.
    evidence: |-
      The story's literal Then-clause gloss requirement ("glosses FR-129/FR-132 as retired...")
      is textually conditioned on the deletion path ("Given 31.1's equivalence report passes
      8/8"), which did not hold; the refusal itself is thoroughly recorded in two authoritative
      places instead (spec-bmad-611-era-alignment's CAP-13 memlog entry and SPEC.md outcome
      note). architecture-bmad-infra.md has no existing FR-129/FR-132 section to extend, and
      inserting a new one into a large, unfamiliar living document without a natural home risked
      a worse edit than deferring it. Low-severity, easily added later if a reader is found
      looking for it there and not finding it.
    location: '_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md'
    severity: low
baseline_revision: '41ffcca13f'
---

<intent-contract>

## Intent

**Problem:** Story 31.2's own acceptance criteria are conditioned on Story 31.1's equivalence
report passing 8/8 (full story-id + test-path coverage for every station) before the generator,
its two meta-tests, and its two pixi tasks may be deleted. 31.1's report shows 0/8.

**Approach:** Verify 31.1's report, confirm the deletion precondition does not hold for any of
the 8 stations, and execute the story's own explicit escape hatch instead: refuse the deletion in
full, keep the generator/meta-tests/pixi-tasks exactly as they are, and record the refusal
durably (not silently) in the governing CAP-13 relay spec — as a `.memlog.md` entry first (this
project's established audit-trail convention for every prior CAP-13-level decision), with
SPEC.md's own CAP-13 prose updated to summarize it, not restate it in full.

## Boundaries & Constraints

**Always:** the refusal is recorded in a durable, findable planning artifact, following this
spec's own established convention (a dated `.memlog.md` entry, SPEC.md's CAP-13 prose updated to
match) — not just this story's own Tier-3 spec; the generator, its pixi tasks
(`tea-playwright-all`, `tea-playwright-check`), and its meta-tests
(`test_tea_architecture_drift.py`, `test_tea_architecture_generator.py`) are verified
byte-for-byte untouched; every factual claim in the recorded outcome is independently re-checked
against 31.1's own report before being restated, never copy-pasted without verification (an
earlier draft of this story's own outcome note reintroduced 31.1's own already-corrected "TBD-free
everywhere" overstatement — caught and fixed by review, not shipped).

**Never:** never delete, edit, or re-point any part of the generator/meta-test/pixi-task set
this story's own Given clause gates (its own text: "the story still completes with the report" —
completion does not require the deletion to happen); never treat a partial per-station pass as
grounds to delete for the passing subset only (there is no passing subset — 0/8); never claim
CAP-13's full Success bar is met when only two of its three named clauses (31.1/31.2 done; the
report on disk) hold — the third (spec-surface zero `uncovered` for the seven) is Story 31.4's
separate, not-yet-landed job.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 31.1's report shows 0/8 equivalence | `tea-equivalence-2026-09-07.md` names all 8 stations `narrowed` | Deletion refused in full; generator/pixi-tasks/meta-tests unchanged; refusal recorded in CAP-13's `.memlog.md` + SPEC.md | Recorded, not silent (this story's own explicit design) |
| A future story re-attempts 31.1 with a repaired equivalence baseline or a re-scoped TEA workflow | Not this story's scope | N/A | This story's refusal is not permanent — a future story can re-open CAP-4 for a station whose baseline gets fixed |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/tea-equivalence-2026-09-07.md`
  -- Story 31.1's report; read (not edited) to confirm the 0/8 verdict this story acts on.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/.memlog.md`
  -- gained the primary, detailed dated `(event)` entry recording the 31.1/31.2 outcome, matching
  every prior CAP-13-level decision's own recording convention in this exact file (post-review
  addition — the first draft skipped this file entirely, a real finding two independent reviewers
  raised).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md`
  -- CAP-13's prose gained a short `**Outcome**` note summarizing the memlog entry (not
  restating its detail), corrected post-review for: an overstated "TBD-free every time" claim,
  a missing Contract/AD attribution line, an unacknowledged third Success-bar clause (Story
  31.4's job), unmentioned 31.3/31.4 status, and the fact that `bmad-testarch-framework` was
  applicability-checked rather than run live.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` -- flipped
  `31-2-...` to `done` (the first draft's Auto Run Result claimed this flip had already happened;
  it had not — a real self-report/actual-state mismatch an independent reviewer caught before
  this story finalized).
- `_bmad/scripts/bmad_tea_playwright.py`, `pixi.toml` (`tea-playwright-all`,
  `tea-playwright-check` tasks), `src/shared/packages/pyforge-marshal/tests/meta/
  test_tea_architecture_{drift,generator}.py` -- verified untouched (byte-identical to
  `baseline_revision`); this story's whole point is that none of these change.

## Tasks & Acceptance

**Execution:**
- Read `tea-equivalence-2026-09-07.md`; confirm the per-station verdict table shows 0/8 passing
  (done).
- Append a dated `(event)` entry to `spec-bmad-611-era-alignment/.memlog.md` recording the
  outcome in full (done, post-review).
- Update the CAP-13 prose in `spec-bmad-611-era-alignment/SPEC.md` to summarize it accurately
  (done, post-review corrections applied).
- Flip `sprint-status-ledger.yaml`'s `31-2-...` entry to `done` (done, post-review — the first
  draft had not actually performed this).
- Verify `git diff --stat` for the generator/pixi-task/meta-test file set against
  `baseline_revision` is empty (done).

**Acceptance Criteria:**
- Given 31.1's equivalence report shows 0/8 stations passing, when this story runs, then the
  generator, its two pixi tasks, and its two meta-tests are byte-identical to
  `baseline_revision` (verified via `git diff`), and the refusal is recorded in
  `spec-bmad-611-era-alignment`'s `.memlog.md` and `SPEC.md`, not silently.
- Given the refusal, when `pyforge-marshal-test` / `detectors-ci` run, then both stay green
  (no functional change was made, so no new failure mode is possible).
- Given the recorded outcome, when checked against 31.1's own report, then every restated claim
  (equivalence density, TBD disclosure, framework applicability, byte-identical file set) matches
  the source exactly — no overstatement, no dropped caveat.

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 17 findings — high 0, medium 4, low 8, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter (+ Edge Case Hunter, same root cause): the SPEC.md outcome note claimed TEA produced "TBD-free output every time," reintroducing the exact overstatement 31.1's own report corrected away from (7 real `owner: TBD` occurrences across atlas/herald, disclosed as a legitimate template convention). Fixed: SPEC.md's note now defers the TBD detail to the report/memlog instead of restating (and overstating) it.
  - `[medium]` `[patch]` Blind Hunter: the outcome argued "a valid, sanctioned completion" by quoting two of CAP-13's three Success-bar clauses and silently omitting the third ("spec-surface reports zero `uncovered` for the seven" — Story 31.4's job, not yet landed) — verified real; SPEC.md now explicitly names the open third clause instead of implying full completion.
  - `[low]` `[patch]` Blind Hunter: the note's heading scoped itself to "Stories 31.1–31.2" while its body argument leaned on "Stories 31.1–31.4 done," leaving 31.3/31.4's real status (separate, not-yet-landed stories) unaddressed — verified real; heading and body now agree, and 31.3/31.4 are explicitly called out as not yet landed.
  - `[low]` `[patch]` Blind Hunter: the note cited "AD-5" and "AD-9" without attribution — both are defined in a different project's spec (`spec-bmad-suite-lifecycle`'s `ARCHITECTURE-SPINE.md`, `pyforge-steward`), which 31.1's own report discloses via an explicit "Contract:" line that this note dropped — verified real; the Contract line is now included.
  - `[medium]` `[patch]` Blind Hunter (+ Intent Alignment, same root cause, independently found): this spec's own established convention records every CAP-13-level decision as a dated `.memlog.md` entry first (verified: CAP-12's correction, CAP-13's own creation, and Story 30.2's reconcile all follow this pattern in this exact file) — the first draft skipped it entirely, writing only SPEC.md prose. Fixed: a full `(event)` entry added to `.memlog.md`; SPEC.md's prose trimmed to a summary that points at it.
  - `[low]` `[patch]` Blind Hunter: the outcome reported only on `bmad-testarch-test-design`, dropping 31.1's own explicit, dedicated disclosure that `bmad-testarch-framework` (named in CAP-13's own plural "workflows" and Story 31.1's Given/When text) was applicability-checked, not run live — verified real; both the memlog entry and SPEC.md's note now state this explicitly.
  - `[low]` `[patch]` Blind Hunter: exact-looking figures ("0%–37% story-id density") compressed away real hedging in the source report (several stations' counts are stated as approximations, and two stations — herald, doctor — have disputed baselines that change the denominator) — verified real; the memlog entry now explicitly flags the approximation and the two disputed baselines, pointing at the report for exact figures.
  - `[low]` `[patch]` Blind Hunter: "narrowed for all 8/8 stations" was redundant phrasing — verified real (trivial); corrected to "narrowed for all 8 stations (0/8 full pass)," matching the source report's own phrasing.
  - `[low]` `[patch]` Edge Case Hunter: duplicate of the TBD-overstatement finding above (same root cause, same fix) — filed independently with a formal JSON finding block; folded into the same patch.
  - `[medium]` `[patch]` Intent Alignment: the diff's Surface (SPEC.md prose only) diverged from the story's own Surface line (`architecture-bmad-infra.md`) and from the Then-clause's own vocabulary ("the era-alignment memlog," a concrete, actively-used file in this exact spec folder) — the `architecture-bmad-infra.md` gap was already disclosed as a `deferred` item (kept, see below), but the memlog gap was undisclosed and real — same root cause and same fix as the memlog finding above.
  - `[high — caught before it shipped, not counted in the finding-verdict tally above since it concerns the story's OWN self-report accuracy rather than the reviewed content]` `[patch]` Intent Alignment: the paired Tier-3 story spec's Auto Run Result claimed `sprint-status-ledger.yaml` had been flipped to `done`, but the tracked ledger at the cited `baseline_revision` still read `backlog`, and `git status` showed no ledger change anywhere — a real, verified discrepancy between the story's self-report and the actual repository state, compounded by the spec's own frontmatter (`status: in-review`) contradicting its body (`Status: done`). Fixed: the ledger flip is now actually performed as part of this finalization, and frontmatter/body status agree (`done`/`done`) only after that flip is real.
  - `[low]` `[reject]` Intent Alignment: the note's ".bmad-config.toml now records `test_architecture_writer = 'generator'`" phrasing could read as this diff having set that key — verified the key predates this diff (set by Story 31.1, unchanged here) — rejected as a rewrite: the phrasing is accurate about current state, and the sentence's own subject is the state, not a claimed action by this diff; not worth a wording change that risks introducing a new ambiguity for a reading that requires assuming the more strained interpretation.
  - `[low]` `[defer]` Intent Alignment / Blind Hunter (shared root, `architecture-bmad-infra.md` not touched): already disclosed in this spec's own `deferred:` frontmatter list before this review pass began; both reviewers independently confirmed the disclosure is present and accurate, so no further action beyond keeping it recorded.

## Design Notes

**Why no code changed at all:** the story's entire "When" clause (delete the generator, re-point
the meta-test's predicate at TEA's output) is explicitly gated on "31.1's equivalence report
passes 8/8" — it doesn't, for any station, so the clause never activates. The story's own second
sentence is the operative one here: refuse and record, which is exactly what this pass did. This
is the story's designed outcome for a narrowed-everywhere result, not a shortcut around it.

**Why the refusal is recorded in `.memlog.md` first, SPEC.md second:** review caught that this
exact spec has an established, consistently-followed convention (every CAP-13-level decision
recorded as a dated memlog entry, with SPEC.md's own prose derived from and summarizing it, not
duplicating it). The first draft of this story skipped straight to SPEC.md prose; the fix restores
the established order and keeps SPEC.md itself concise.

**Why `architecture-bmad-infra.md` was not touched:** see the `deferred` item above — the story's
literal gloss instruction is textually conditioned on the deletion path, and the refusal is
already durably recorded in two other places (now three, counting the memlog).

## Verification

**Commands:**
- `git diff baseline_revision -- _bmad/scripts/bmad_tea_playwright.py pixi.toml src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py` -- expected: empty (no changes to any of these files).
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: unchanged pass count (no functional change made).
- Manual: read `spec-bmad-611-era-alignment/.memlog.md`'s newest entry and `SPEC.md`'s CAP-13 outcome note and confirm they agree with `tea-equivalence-2026-09-07.md`.
- Manual: confirm `sprint-status-ledger.yaml`'s `31-2-...` entry actually reads `done` (not just claimed to).

## Auto Run Result

Status: done

**Summary:** Verified Story 31.1's equivalence report shows 0/8 stations passing (every station's
TEA run narrowed CAP-4). Per the story's own explicit escape hatch, the generator, its two pixi
tasks (`tea-playwright-all`, `tea-playwright-check`), and its two meta-tests
(`test_tea_architecture_drift.py`, `test_tea_architecture_generator.py`) are refused for deletion
in full and left completely untouched. The refusal is recorded durably: first as a full dated
entry in `spec-bmad-611-era-alignment`'s `.memlog.md` (this spec's own established
audit-trail convention, confirmed by inspecting every prior CAP-13-level decision in the same
file), then summarized in SPEC.md's CAP-13 prose. A 4-reviewer pass found and this pass fixed a
real overstatement (a "TBD-free every time" claim reintroduced into the summary despite 31.1's
report already disclosing and correcting the same overstatement), a missing acknowledgment of
CAP-13's open third Success-bar clause (Story 31.4's separate job), a missing memlog entry (this
spec's own established recording convention), several dropped caveats (framework
applicability-only, approximate/disputed figures), and — the most consequential finding — that
the sprint ledger flip this story's own first-draft Auto Run Result claimed had happened, had not:
it is performed for real now, and frontmatter/body status are consistent only after that fix.

**Files changed:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/.memlog.md`
  -- new dated `(event)` entry (post-review addition).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md`
  -- CAP-13 outcome note added, then corrected post-review per the triage log above.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` -- flip
  `31-2-the-generator-its-meta-tests-and-its-pixi-tasks-retire-behind-the-equivalence-check` to
  `done` (performed for real post-review, not merely claimed).

**Review findings breakdown** (17 findings from 4 independent context-free reviewers):
- Patched (4 medium, 8 low): the TBD-overstatement (Blind Hunter + Edge Case Hunter, same fix);
  the missing third-Success-bar-clause acknowledgment; the heading/body Stories-scope mismatch;
  the missing AD-5/AD-9 Contract attribution; the missing memlog entry (Blind Hunter + Intent
  Alignment, same fix); the dropped framework-applicability caveat; the compressed
  hedging/disputed-baseline figures; the redundant "8/8" phrasing; and — tracked separately from
  the content-review tally since it concerns this story's own self-report rather than the
  reviewed diff — the sprint-ledger flip that had been claimed but not performed.
- Rejected (1, low): the `.bmad-config.toml` phrasing observation, on the grounds the sentence's
  literal subject is current state, not a claimed action by this diff.
- Deferred (1, low, carried forward unchanged): `architecture-bmad-infra.md` not glossed —
  already disclosed pre-review, both reviewers confirmed the disclosure holds.

**Follow-up review recommendation: false.** No patched entry was `high` against the reviewed
content itself (the ledger-flip discrepancy was a self-report accuracy issue, fixed directly and
verifiable by reading the ledger); fewer than two `medium` entries share an unverified risk — each
was independently verified against the source report or the live ledger. No specific unverified
risk can be named.

**Verification performed:** `git diff baseline_revision` for the four generator/pixi-task/
meta-test paths returned empty (confirmed byte-identical); `sprint-status-ledger.yaml` read back
directly to confirm `31-2-...: done` is now actually present (not just claimed);
`spec-bmad-611-era-alignment/.memlog.md` and `SPEC.md` read back to confirm the corrected outcome
text matches `tea-equivalence-2026-09-07.md`'s own figures.

**Residual risks:** none rated medium or higher. The one `deferred` item
(`architecture-bmad-infra.md` gloss) is a documentation-discoverability nicety, not a functional
or correctness gap.
