---
title: '138.1: Story 59.2''s capability is re-homed and two Story lines name what they build'
type: 'chore'
created: '2026-11-25'
status: 'done'
story: 138-1-story-59-2-s-capability-is-re-homed-and-two-story-lines-name-what-they-build
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-59-2-detectors-read-one-declaration-in-progress-is-grandfathered.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-111-1-the-steward-spec-s-fold-cut-capability-text-is-restored-and-the-foundry-inherits-the-amended-rule.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/.memlog.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/.memlog.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-136-11-1`. Story 59.2 cites `spec-vocabulary-one-name-one-job CAP-2`, whose status-set half it shipped (doctor's `board.py`, `chain.py` and `status_body_consistency.py` read `docs/governance/guild-roster.json`, commit `fa128090c3`); the 2026-09-17 fold carried that Spec's CAP-1 and CAP-3 to CAP-7 into `spec-pyforge-steward` as CAP-132 to CAP-137 and CAP-2 into none. Story 111.1 cites `spec-foundry-regenerate-not-fold CAP-7`; that Spec defines CAP-1 to CAP-5, and its memlog's entries tagged `CAP-7` record spec-one-chain-per-station CAP-7 (the foundry on-ramp), whose subject is that Spec's CAP-5 (B's starting five-fields). Story 41.4 keeps a bare `CAP-12`; spec-pyforge-unifying-strategy CAP-12 is access and secret delivery, and broker TLS is that Spec's 2026-09-02 red-team Constraint, which names Story 41.4.

**Approach:** Amend CAP-132 through the memlog (operator ruling "Amend CAP-132") so its intent and success carry the declaration being machine-readable and read by doctor's detectors, its marker naming the amendment and Story 59.2; render `SPEC.md` by an anchor-asserting render; re-key the three Story lines in `epics.md` and in the three story specs' bindings, each to the record traced above; add the doctor tests to CAP-132's oracle-map row; resolve the row.

Ledger key: `138-1-story-59-2-s-capability-is-re-homed-and-two-story-lines-name-what-they-build`.

### Living CAP citations

- spec-pyforge-steward CAP-132 (amended with this story: the Spec ladder is declared, and doctor's detectors read the declaration -- the status-set half of the dropped spec-vocabulary-one-name-one-job CAP-2); reads spec-foundry-regenerate-not-fold CAP-5, spec-one-chain-per-station CAP-7 and spec-pyforge-unifying-strategy's 2026-09-02 red-team Constraint and pap:CAP-6 (no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Trace every re-key to the record that defines it, and record the trace in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit `SPEC.md`; never change CAP-132's id or heading.
- Never mint a capability to give a Story line something to cite.
- Never add a flag, a capability or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-136-11-1` reports that Story 59.2 cites `spec-vocabulary-one-name-one-job CAP-2`, which the 2026-09-17 fold carried into no live Spec, that Story 111.1 cites `spec-foundry-regenerate-not-fold CAP-7`, which that Spec (CAP-1 to CAP-5) does not define, and that Story 41.4 keeps a bare `CAP-12` whose intent is not broker TLS
**When** CAP-132 is amended through the memlog to carry the status-set half Story 59.2 shipped, and each of the three Story lines is traced to the record that defines what it builds
**Then** Story 59.2 cites spec-pyforge-steward CAP-132, Story 111.1 cites `spec-foundry-regenerate-not-fold CAP-5` (B's starting five-fields; the memlog's `CAP-7` entries are spec-one-chain-per-station CAP-7's, which the line already cites), and Story 41.4 cites spec-pyforge-unifying-strategy's 2026-09-02 red-team Constraint that names it (`rediss://` verifies the chain) beside pap:CAP-6, with no bare id left on the three lines
**And** CAP-132's heading and id do not change, the capability ledger's row still matches it, and the row reads resolved

- **AC1 — No re-keyed line keeps a dead id.** Expected: prints `0` (the pipe's last command is the count, so read the number, not the exit code).

  ```bash
  awk '/^### Story (59\.2|111\.1|41\.4):/{f=1} f&&/\*\*FR\/AD:\*\*/{print; f=0}' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md | grep -cE 'spec-vocabulary-one-name-one-job CAP-2|spec-foundry-regenerate-not-fold CAP-7|FR/AD:\*\* CAP-12 '
  ```

- **AC2 — The chain and the ledgers hold.** Expected: exit 0 each.

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild capability-ledger-check && pixi run -e pyforge-guild story-status-check
  ```

- **AC3 — The oracle map is total and true.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-132 (amended with this story: the Spec ladder is declared, and doctor's detectors read the declaration -- the status-set half of the dropped spec-vocabulary-one-name-one-job CAP-2); reads spec-foundry-regenerate-not-fold CAP-5, spec-one-chain-per-station CAP-7 and spec-pyforge-unifying-strategy's 2026-09-02 red-team Constraint and pap:CAP-6 (no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (Story 59.2's capability is re-homed); operator rulings of 2026-11-25: "Amend CAP-132" (2026-11-25, in session) and "do the CAP-132 amendment and the story re-keys" (2026-11-25).
- Epic: Epic 138, minted with this story.
- Ledger key: `138-1-story-59-2-s-capability-is-re-homed-and-two-story-lines-name-what-they-build`.
- Deferred-work row: `DW-steward-136-11-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."138"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (Story 59.2's capability is re-homed) and the operator's rulings of the same date. Not implemented.
- 2026-11-25: session lead: AC1 corrected before it ran. As minted it grepped all of `epics.md`, which also matches the file's frontmatter history comment and Story 138.1's own description of the dead ids; it now reads only the FR/AD lines of Stories 59.2, 111.1 and 41.4, the lines this story changes. The criterion is unchanged.
- 2026-11-25: the trace. Story 59.2: the archived `spec-vocabulary-one-name-one-job` memlog records CAP-2's two halves (operator decision of 2026-09-14, ruling Q7 of 2026-09-15); the 2026-09-17 fold carried CAP-1 as `spec-pyforge-steward` CAP-132 and CAP-2 nowhere; Story 59.2 built the status-set half (commit `fa128090c3`: doctor's `board.py`, `chain.py` and `status_body_consistency.py` read `docs/governance/guild-roster.json`), so CAP-132, amended, is its home; the exit-code half is CAP-184. Story 111.1: `spec-foundry-regenerate-not-fold` defines CAP-1 to CAP-5; its memlog's entries tagged `CAP-7` (2026-09-16, 2026-09-17 and 2026-10-26) are `spec-one-chain-per-station` CAP-7 events, whose intent names the foundry Spec's CAP-5 (Dual-root A/B, B's starting five-fields). Story 41.4: `spec-pyforge-unifying-strategy` CAP-12 is IdP roles and secret delivery, and none of its CAP-1 to CAP-20 states broker TLS; the rule is that Spec's 2026-09-02 red-team Constraint, which names Story 41.4.
- 2026-11-25: AC1 prints `0` (three FR/AD lines read); AC2 exit 0 each; AC3 exit 0 (15 passed).
- 2026-11-25: session lead, on the independent review: the story specs of 111.1 (two lines) and 41.4 (its Source section) carry the re-keys too, since the story spec is the source of record; the success clause "no new Spec is written `in-progress`" added to CAP-132 is withdrawn through the memlog and a render, since nothing proves it; CAP-132's oracle-map row names the chain.py test as well; Story 111.1's line no longer says CAP-5 holds the discipline (that is the foundry Spec's Constraint and one-chain CAP-7); the Dream entry's doubled date is removed. That broker TLS is a guarantee with no capability is `DW-steward-138-1-1`, for the operator.
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff, every Acceptance Criterion run), its findings applied; the full local `pr-preflight` gates the PR that lands it (branch `cap-132-and-story-rekeys-2026-11-25`).
