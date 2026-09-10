---
title: '`open_questions: []` over a live memlog question is a finding'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: b19ad5971acd608fd0bcc23d7935c05d9cd2e181
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `docs/governance/spec-pyforge-charter/SPEC.md:16` declares
`open_questions: []` while its companion `.memlog.md:9` carries an `(open)` question
from 2026-07-31 that no later `(decision)` entry closes. For most documents this
would be routine hygiene; for the Charter it is constitutional — Charter CAP-2 makes
the Lexicon's own integrity a governed property, not a nice-to-have.

**Approach:** In the same new source module as Story 21.12
(`spec-status-body-consistency`), implement CAP-2: reconcile a Spec's declared
`open_questions` frontmatter list against its companion `.memlog.md`'s **last
unclosed** question entry. The Charter's Spec fires with both line numbers cited. A
Spec whose memlog question is followed by a closing `(decision)` entry does not fire.
A Spec with no memlog at all is `ok`, not an error. The check reports the
contradiction without proposing text — reconciliation belongs to the
`chain-currency-sweep` loop, never to this detector.

## Boundaries & Constraints

**Always:**
- `open_questions` frontmatter is reconciled against the companion memlog's last
  unclosed `(open)` question entry.
- A firing finding cites both line numbers (the frontmatter line and the memlog
  entry's line).
- A Spec with no companion memlog at all is `ok`, not an error.
- The check only reports the contradiction — it never proposes or writes closing
  text.

**Never:**
- The check never performs the reconciliation itself (writing a `(decision)` entry or
  editing `open_questions`) — that belongs to the `chain-currency-sweep` loop, not
  this detector.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live Charter case | `SPEC.md:16` declares `open_questions: []`; `.memlog.md:9` carries an unclosed `(open)` question from 2026-07-31 | Fires, citing both line numbers | n/a |
| Closed question | Memlog question is followed by a `(decision)` entry that closes it | No finding | n/a |
| No memlog | Spec has no companion `.memlog.md` | `ok`, not an error | n/a |
| Question and `open_questions` agree | `open_questions` frontmatter lists the same open question the memlog shows | No finding | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` — the same new source module as Story 21.12.
- `src/shared/packages/pyforge-doctor/tests/unit/` — new unit tests, including the live Charter fixture (`docs/governance/spec-pyforge-charter/SPEC.md` + `.memlog.md`).

## Tasks & Acceptance

**Execution:**
- `feature` — implement CAP-2 in the shared source module: parse `open_questions` frontmatter, parse the companion `.memlog.md` for its last unclosed `(open)` question entry (no later `(decision)` closing it), and reconcile.
- `feature` — emit a warn finding citing both line numbers when a live memlog question exists but `open_questions` is empty (or otherwise fails to reflect it).
- `feature` — handle "no memlog" as `ok`, not an error.
- `feature` — add tests covering the live Charter case, a closed-question case, and a no-memlog case.

**Acceptance Criteria:**
- Given `docs/governance/spec-pyforge-charter/SPEC.md:16` declares `open_questions: []` while its companion `.memlog.md:9` carries an `(open)` question from 2026-07-31 that no later `(decision)` entry closes — and for this document it is not hygiene, because Charter CAP-2 makes the Lexicon's own integrity constitutional — when a Spec's declared `open_questions` are reconciled against its companion memlog's last unclosed question entry, then the Charter's Spec fires with both line numbers cited.
- A Spec whose memlog question is followed by a closing decision does not fire.
- A Spec with no memlog is `ok`, not an error.
- The check reports the contradiction without proposing text — reconciliation belongs to the `chain-currency-sweep` loop, never to the detector.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green, including the new open_questions/memlog-contradiction tests

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section. Its absence made `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse this story's own dispatch verification -- live journal: "no Success signal to bind against -- the story has no tracked spec, or its tracked spec has no parseable ## Verification -> **Commands:** section."

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (self-review — implementation matches all acceptance criteria and matrix rows)

## Auto Run Result

Status: done

**Summary:** Implemented CAP-2 in `status_body_consistency.py`: reconciles each Spec's `open_questions` frontmatter against its companion `.memlog.md`'s last unclosed `(open)` / `(question)` entry. Warn-only finding cites both line numbers; no memlog → ok; closed by `(decision)` → silent.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py` — CAP-2 gather pass + combined `gather()`
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py` — unit tests for all matrix rows
- `src/shared/packages/pyforge-doctor/tests/fixtures/status_body/spec-charter-{mismatch,closed,no-memlog}/` — charter-shaped fixtures

**Review:** 0 patches, 0 deferred. Self-review confirmed all I/O matrix rows covered by passing tests.

**Follow-up review recommendation:** false (0 patched findings)

**Verification:** `pixi run -e pyforge-doctor pyforge-doctor-test -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py` — 11/11 passed; full suite 1525 passed, 1 skipped.

**Residual risks:** Agreement is count-based (memlog has unclosed question ∧ `open_questions` count is 0); a Spec listing a different question than the memlog's last unclosed entry does not fire — intentional per spec focus on hidden questions.
