---
title: The dreams hygiene mode exists
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 0c5002f42f705b43582e677a1b0db5f1f7915cc1
---

<intent-contract>

## Intent

**Problem:** The `--dreams` hygiene mode promised by the 2026-07-23 restructure (FR-147 / `spec-dream-to-code-model-self-verification` capability 4) does not exist; Dream-tier hygiene checks (vocab, table sync, realization-log presence / per-Dream frontmatter validity) still run by hand.

**Approach:** Add a read-only dreams-hygiene mode on the doctor dream-chain surface that reports Dream-tier hygiene findings. Boundary (fixed in the parent Spec): hygiene = per-Dream-file frontmatter validity (`status` from README vocabulary, `owner:` in known station set or `guild`, `title:` present) plus the epic's Phase-2b checks (vocab, table sync, realization-log presence) — distinct from chain completeness (INV-1/2/3). Fixture-covered from day one.

## Acceptance Criteria

- A dreams-hygiene mode exists and is invocable (CLI spelling may be `--dreams` or folded into `--inv` as a fourth value — pick one, document it).
- Reports Dream-tier hygiene findings: frontmatter validity (status vocab, owner in station/`guild`, title present) and Phase-2b hygiene (vocab / table sync / realization-log presence as applicable).
- Distinct from chain-completeness INV-1/2/3 — does not reimplement those checks.
- Fixture suite covers the mode from day one (no untested ship).

## Boundaries & Constraints

**Never:** Change INV-1/2/3 semantics. Never mutate the live Dream tree in tests (temp fixtures only). Detectors stay stdlib + PyYAML if implemented in detector scripts. Surface: `pyforge.doctor.sources` (dream-chain) / related CLI. Finalize marshal ledger only (doctor code surface).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `gather_dreams_hygiene` / `_gather_dreams_hygiene`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — `dream-chain --dreams` flag
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — `Source.DREAMS_HYGIENE`
- `pixi.toml` — `dreams-hygiene-check` task
- Tests: `tests/unit/test_sources_chain_dreams_hygiene.py`, dispatch CLI cases
- Parent: `spec-dream-to-code-model-self-verification/SPEC.md` capability 4

## Design Notes

- **CLI spelling:** `--dreams` on `python -m pyforge.doctor.sources dream-chain` (not a fourth `--inv` value). Documented in argparse help + `dreams-hygiene-check` pixi task. Chosen because the ported CLI never grew `--inv`; folding into a new flag matches the Dream's preferred name.
- **Source member:** `dreams-hygiene` (Finding.source) is REGISTRY-registered but **not** a DISPATCH name — invocation is exclusively via `--dreams` on `dream-chain`, so INV default runs stay byte-identical.
- **Vocabulary:** read from `docs/governance/guild-roster.json` (same as factory `check_dream_vocab` / `check_dream_owners`); missing roster → unevaluable WARN.
- **Realization log:** required for `pitched` / `specified` / `realized` / `archived` (Phase-2b evidence statuses); `dreamt` exempt. Heading accepts `## Realization`, `## Realization log`, `## Realization Log`, `## The Realization`.
- **Severity:** warn-only (matches factory dream-vocab; does not gate CI via `exit_code_for`).

## Verification

- `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py -q`
- Live: `python -m pyforge.doctor.sources dream-chain` unchanged INV semantics; `dream-chain --dreams` emits only `dreams-hygiene` findings

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` SOURCE_MODULE missing DREAMS_HYGIENE → mapped to chain.py (meta independence)
  - `[low]` `[patch]` Documented CLI spelling + Design Notes on the story spec; pixi task `dreams-hygiene-check`


## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/663
Merge: 14b8c061784ad6b0cf73b6b825779f48de97ad6a
CLI spelling: `dream-chain --dreams` (not `--inv`).
Verification: unit + meta independence PASS; CI green on #663; INV path unchanged.
