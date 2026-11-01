---
title: "113.6: an accepted finding travels the chain's only write path"
type: 'feature'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.marshal.egm_resolve_bridge
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "marshal factory challenge resolve refuses with the usage code; the operator appends accepted findings to the memlog by hand with memlog.py"
  cleanup: "90 days after ON in every environment (Q4); the date is set when the switch turns ON everywhere"
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad/scripts/memlog.py
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
---

<intent-contract>

## Intent

**Problem:** a challenge report is prose under Tier 3. The chain has one write path — a memlog line, then a `bmad-spec` re-derive, or a story-spec edit — and a finding the operator accepts must travel it without a hand edit of `SPEC.md`, a ledger write or a status move.

**Approach:**
- `marshal factory challenge resolve --report <path> --accept <id>... --reject <id>...` reads the report as data, appends one `_bmad/scripts/memlog.py` entry (`--type event`) per accepted finding to the owning Spec's `.memlog.md` — the operator's acceptance text, the finding id and the report path — and writes the rejected ids and their reasons back into the report.
- The subverb names, in its output, the `bmad-spec` re-derive that must follow in the same change, so `chain-currency` reads the memlog line and the render together.
- It never edits `SPEC.md`, a ledger or a story spec's `status` (behavioural guidelines 6 and 7); the pre-shell hook's governed-path denials stay in force.

Ledger key: `113-6-an-accepted-finding-travels-the-chain-s-only-write-path`.
Type / Effort / Deps: feature / M / 113.1.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-303** — the capability this story realizes.
- **CAP-298** — the verb and the report shape (Story 113.1).
- **`spec-feature-flag-governance:CAP-1`** — the flag block; Q3, Q4, Q6.

## Acceptance Criteria

- **AC1 — The key.** `pyforge.marshal.egm_resolve_bridge` is in `flags.json` (`defaultVariant: off`) and `flag-overlays.json` (`off` everywhere) with the clock fields; `test_flags.py` and `flag-inventory` name it against CAP-303.
- **AC2 — ON.** With the key on, `resolve` appends one memlog event per accepted id through `memlog.py` (never a direct file write), writes the rejected ids and reasons into the report, prints the re-derive instruction, and exits 0.
- **AC3 — Untouched.** `SPEC.md`, every ledger and every story spec `status` are byte-identical before and after; a test pins it.
- **AC4 — Unknown ids refuse.** An `--accept` or `--reject` id not in the report refuses with the usage code before any write.
- **AC5 — OFF.** With the key off the subverb refuses with the usage code.
- **AC6 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`) on a fixture report and spec folder.

## Boundaries & Constraints

**Always:**
- Write the memlog through `memlog.py`; treat the report as data; name the owning Spec from the report, never guess it.

**Never:**
- Never edit `SPEC.md`, a ledger or a story spec's `status`; never accept an id the operator did not name; never mint a new exit code.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-303.

Parent: `spec-pyforge-marshal` CAP-303

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-6-an-accepted-finding-travels-the-chain-s-only-write-path`.
- Deps: 113.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass.

**Run before the push:**
- Two-state flag coverage: `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — `@flag_states("pyforge.marshal.egm_resolve_bridge")`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.

## Auto Run Result

Status: done

Summary: built by hand in the single Epic 113 PR (2026-11-01, operator direction: one PR, the 113.1 dispatch stopped before any push); independently reviewed, review findings fixed.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger).
- 2026-11-01: built. A finding already resolved in the report is refused rather than appended twice (review nit).

## Review Triage Log

- 2026-11-01: independent review (fresh subagent, read the diff against this spec) returned FAIL with blockers B1 (two named test files absent) and B2 (the audit refused six stations with no glossary) and should-fix S1-S11; every finding was fixed in the same PR except S7 (`marshal watch` display), recorded as DW-marshal-113-3-1. See the Spec memlog's 2026-11-01 review entry.
