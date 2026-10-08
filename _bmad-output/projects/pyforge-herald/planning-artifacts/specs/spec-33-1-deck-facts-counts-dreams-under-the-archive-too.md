---
title: "33.1: deck-facts counts Dreams under the archive too"
type: 'chore'
created: '2026-09-29'
status: 'done'
followup_review_recommended: false
baseline_revision: '1bf6c5a138cb55ad4da80598789eaf5ef917e056'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/deck_facts.py
  - tests/scripts/test_deck_facts.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scripts/deck_facts.py` derives a deck's fact ledger (`presentations/<slug>/facts.yaml`). For the
`pyforge-genesis` deck it counts Dreams by frontmatter status (line ~626): `dreams_total` and one `dreams_<status>` fact per
status, all from `docs/dreams/*.md`. `spec-one-chain-per-station` CAP-11 (operator ruling 2026-09-29) moves archived Dreams
to `archive/docs/dreams/`. After the move `dreams_archived` would fall toward zero and `dreams_total` would fall with it,
although no Dream was removed. CHAIN-STANDARD §11 requires every reader that lists Dreams to follow them before the first
fold PR moves a file.

**Approach:** the `pyforge-genesis` branch also counts `archive/docs/dreams/*.md` files that carry a frontmatter `status`,
and each fact's source names both globs (`docs/dreams/*.md + archive/docs/dreams/*.md`). A slug in both places is counted
once, from `docs/dreams/`. A Dream read from `archive/docs/dreams/` counts as archived whatever its frontmatter `status` (CHAIN-STANDARD §11: location is the archive signal; amended 2026-09-30, operator ruling). Nothing else in `deck_facts.py` changes.

Ledger key: `33-1-deck-facts-counts-dreams-under-the-archive-too`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station` CAP-11 (the Guild's; Herald mints no CAP and no FR, the relay shape doctor's Epics 24, 25,
  32 and 34 use); CHAIN-STANDARD §11.
- `spec-deck-family-currency` CAP-2 (the facts ledger).
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings: doctor Stories 36.1 and 36.2, marshal Story 75.1.

## Acceptance Criteria

- Given today's tree When `deck-facts pyforge-genesis` runs Then every count derived from `docs/dreams/` is unchanged, and the six Dreams already under `archive/docs/dreams/` (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis`, `video-scripts`) are added to `dreams_total` and `dreams_archived` (none of them to its frontmatter status bucket); each fact's source text names both globs
- Given a fixture archived Dream moved to `archive/docs/dreams/` When it runs Then `dreams_total` and `dreams_archived` keep their values
- Given an archive file with no frontmatter `status` When it runs Then it is not counted, as a live file with no status is not
- Given one slug in both directories When it runs Then it is counted once
- Given the archive count is removed When the moved-Dream test runs Then it fails (mutation)

## Tasks

1. Read the `pyforge-genesis` branch of `scripts/deck_facts.py` and `tests/scripts/test_deck_facts.py`.
2. Count both globs, de-duplicate by slug with `docs/dreams/` first, and name both globs in each fact's source.
3. Add tests for every acceptance criterion to `tests/scripts/test_deck_facts.py`.
4. Run `pixi run -e pyforge-guild python -m pytest tests/scripts/test_deck_facts.py -q` and
   `pixi run --frozen -e pyforge-herald pyforge-herald-test`, and read each exit code.
5. Reconcile every Spec `spec-surface-check` names for `scripts/deck_facts.py`: memlog first, `git add`, then a scoped
   `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep every count derived from `docs/dreams/` unchanged on today's tree; only the archive's six are added, as archived.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit the deck's poster or re-derive `presentations/pyforge-genesis/facts.yaml` in this story.
- Do not move any Dream in this story.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| today's tree | nothing moved | `docs/dreams/` counts unchanged; the archive's six added to total and archived; source text names both globs | — |
| Dream moved | archived Dream moved under the archive | counts unchanged by the move | — |
| no status | archive file without `status` | not counted | — |
| slug in both | two copies | counted once | — |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station` CAP-11 (Guild relay; no herald CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `33-1-deck-facts-counts-dreams-under-the-archive-too`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_deck_facts.py -q` — expected: pass.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 1, false 0, maybe-false 0
- findings:
  - `[low]` `[patch]` `dreams_total` method text did not mention archive-only slugs — updated method string in `scripts/deck_facts.py`.

## Auto Run Result

Status: done

Summary: `pyforge-genesis` Dream fact derivation now reads `archive/docs/dreams/` alongside `docs/dreams/`, deduplicates by slug with live winning, counts archive-only files toward `dreams_archived` regardless of frontmatter status, and names both globs in every dreams_* fact source.

Files changed:
- `scripts/deck_facts.py` — `genesis_dream_status_counts`, `GENESIS_DREAMS_SOURCE`, genesis branch wiring
- `tests/scripts/test_deck_facts.py` — acceptance tests and archive-read mutation guard
- `spec-pyforge-herald/.memlog.md` and `spec-deck-family-currency/.memlog.md` — surface reconcile (no `--write-baseline`)

Review: one low patch (method copy for `dreams_total`); no deferrals.

Verification:
- `pytest tests/scripts/test_deck_facts.py -q` — 70 passed
- `pyforge-herald-test` — 1638 passed, 4 skipped
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile

Residual risk: none identified; live-tree counts unchanged except adding the six archive-only Dreams already on disk.
