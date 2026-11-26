---
title: '137.1: One declaration names every exit-code domain'
type: 'feature'
created: '2026-11-25'
status: 'done'
story: 137-1-one-declaration-names-every-exit-code-domain
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # the exit-code declaration every verdict and the aggregator read; a gated declaration is a silent green (roster list)
surface:
  - 'docs/governance/guild-roster.json'
  - 'src/shared/packages/pyforge-core/src/pyforge/core/exit_domains.py'
  - 'src/shared/packages/pyforge-core/tests/unit/test_exit_domains.py'
  - 'src/shared/packages/pyforge-core/tests/unit/test_exit_domains_match_the_guild_roster.py'
  - 'scripts/detectors.py'
  - 'tests/scripts/test_exit_code_domains_are_declared.py'
  - 'docs/reference/judgement-vocabulary.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
  - docs/reference/judgement-vocabulary.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-VOCAB-2026-09-14-8`. Five exit-code domains are live and each is spelled in its own module: doctor's `{0, 2, 130}` (2 = FAIL), warden's `{0, 1, 2, 130}`, marshal's `{0, 1, 2, 3, 4, 130}`, marshal `seed`'s `{1, 2, 3, 4, 5, 10}` and the aggregator's `{0, 1, 2}` (2 = could not run). `docs/reference/judgement-vocabulary.md` declares the first four in prose and `tests/scripts/test_exit_code_domains_are_declared.py` pins them against private constants; no machine-readable declaration exists, so the 2026-09-14 misread of a doctor `2` as could-not-run can recur wherever a reader trusts one surface's number for another's.

**Approach:** Add `exit_code_domains` (domain -> member name -> exit code) and `exit_code_domains_narrowing` (`doctor` narrows `warden`) to `guild-roster.json` with a `$comment_exit_code_domains` that defines each domain and names the inversion of `2`. Add `pyforge.core.exit_domains` with the same table as read-only mappings plus `exit_code(domain, name)` and `domain_codes(domain)`, holding no filesystem read (the `pyforge.core.roster` pattern, CAP-137), and a live-tree test that fails when the two differ. `scripts/detectors.py` reads the aggregator's three codes from the JSON key. The pinning test compares every module and the glossary page against the declaration.

Ledger key: `137-1-one-declaration-names-every-exit-code-domain`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (one declaration names every exit-code domain, and each verdict module reads it; minted with this story), works with spec-pyforge-core:CAP-3 (the shared `Lattice` mechanism; no text change) and spec-pyforge-steward:CAP-137 (the roster's in-process mirror is the pattern; no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Show on the unchanged tree what each constant returns, and show the same values after the change; record both in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change an exit number on any surface.
- Never make an installed package read `docs/governance/guild-roster.json`; in-process code reads `pyforge.core.exit_domains`.
- Never add a flag, a second declaration or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-VOCAB-2026-09-14-8` reports four exit-code domains spelled in four modules, declared only in prose, and an aggregator whose `2` means the opposite of a doctor source's
**When** `guild-roster.json` gains `exit_code_domains` and `exit_code_domains_narrowing`, and `pyforge.core.exit_domains` carries the same table
**Then** the five domains are declared by member name and number, a live-tree test fails when the Python table and the JSON key differ, `scripts/detectors.py` takes its 0, 1 and 2 from the `detectors` domain, and `test_exit_code_domains_are_declared.py` fails when a module's exit constants or the glossary page's domains differ from the declaration
**And** no exit number on any surface changes, and the row reads resolved once Stories 63.1 (doctor), 30.1 (warden) and 122.1 (marshal) land

- **AC1 — The core table and its match with the governance file hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests/unit/test_exit_domains.py src/shared/packages/pyforge-core/tests/unit/test_exit_domains_match_the_guild_roster.py -q
  ```

- **AC2 — The pinning test reads the declaration.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_exit_code_domains_are_declared.py -q
  ```

- **AC3 — The aggregator spells no exit number of its own in its verdict.** Expected: exit 1 (no line matches).

  ```bash
  grep -nE '^\s+return [012]$' scripts/detectors.py
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward:CAP-184 (one declaration names every exit-code domain, and each verdict module reads it; minted with this story), works with spec-pyforge-core:CAP-3 (the shared `Lattice` mechanism; no text change) and spec-pyforge-steward:CAP-137 (the roster's in-process mirror is the pattern; no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (one declaration names every exit-code domain); operator ruling of 2026-11-25: "Unify for real".
- Epic: Epic 137, minted with this story.
- Ledger key: `137-1-one-declaration-names-every-exit-code-domain`.
- Deferred-work row: `DW-VOCAB-2026-09-14-8`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."137"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (one declaration names every exit-code domain) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: before and after: each verdict module's exit constants were recorded on the unchanged tree and again after the change, in each station's own environment (doctor `{ok: 0, warn: 0, fail: 2}` and 130; warden's seven rungs, warn-as-error 1, SIGINT 130; marshal's six rungs, `EXIT_OK` 0, `EXIT_USAGE` 2, SIGINT 130, `GUARDED_EXIT_CODES` `{0, 1, 2, 3, 4, 130}`; seed 1, 2, 3, 4, 5, 10); every value is equal. AC1 exit 0 (15 passed), AC2 exit 0 (13 passed, warden skipped in `-e pyforge-guild`; it exits 0 in `-e pyforge-warden`), AC3 exit 1 (no line matches).
- 2026-11-25: session lead, on the review: pyforge-core's public contract (`spec-pyforge-core/contract.md`) listed no `pyforge.core.exit_domains`, so `pyforge-core-test` exited 1 on `test_contract_and_source_agree`; the module and its four public names are listed and the `pyforge.core.verdict` paragraph says the exit values come from the declaration (`pyforge-core-test` exit 0, 466 and 2,235 passed). `scripts/detectors.py` compared a doctor row's code to a bare `0` and read `if rc:`; it now compares to doctor's declared `ok` (read from the same file) and to `EXIT_PASS`, and the pinning test checks that form. The glossary names `seed/errors.py` among the readers. Kept: an unreadable declaration makes `scripts/detectors.py` exit 2 (could-not-run) at import, which is correct for the aggregator; no workflow runs it on a sparse tree.
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff, every Acceptance Criterion run and read from its exit code), its findings applied; the full local `pr-preflight` gates the PR that lands it (branch `exit-code-vocabulary-2026-11-25`).
