---
id: SPEC-dream-to-code-model-self-verification
spec: dream-to-code-model-self-verification
status: draft
owner-dream: docs/dreams/dream-to-code-model-self-verification.md
surface:
  - scripts/dream_chain_check.py
  - scripts/bmad_drift_check.py
  - .claude/skills/conda-forge-expert/tests/meta/
sources:
  - ../../../../../../docs/dreams/dream-to-code-model-self-verification.md
  - ../../../../../../_bmad-output/EXEMPLAR-STANDARD.md
  - ../../../../../../scripts/dream_chain_check.py
  - ../../../../../../scripts/bmad_drift_check.py
open_questions:
  - "Scope boundary: does the meta-test obligation cover only dream_chain_check.py and bmad_drift_check.py, or every detector the scripts/detectors.py registry discovers? The registry itself exists because three hand-listed registries disagreed (2026-07-31) — extending fixture coverage registry-wide is the consistent end state, but it is real work per detector and this Spec does not commit to it yet."
  - "Where the incident log lives: a section in this Spec's directory (peer companion) vs. a tracked file next to the detectors in scripts/. Companion-in-kernel-dir is the EXEMPLAR-STANDARD default and the current lean."
  - "Whether the --dreams hygiene mode is a new flag or folded into --inv as a fourth value (the Dream leaves this open; the capability below fixes the boundary, not the CLI spelling)."
---

# dream-to-code-model-self-verification — the detectors get detected

## Problem

The Dream-to-Code model is enforced by detectors — `scripts/dream_chain_check.py`
(INV-0…INV-3 per `_bmad-output/EXEMPLAR-STANDARD.md`) and `scripts/bmad_drift_check.py`
(marshal-doc drift/coverage) — whose findings are treated as the migration backlog and gate
CI. But the detectors themselves are verified only by running them against the live repo and
trusting the output. That is not verification: a detector bug and a real finding are
indistinguishable from the outside, and EXEMPLAR-STANDARD's own recurring lesson is that
**a detector's bugs propagate outward as confident, wrong numbers.**

This is not hypothetical. In `dream_chain_check.py`'s 11 days of life (4 commits total),
its output has been found materially wrong twice:

1. **2026-07-28 — the INV-0 discovery.** The first cut reported 21 Dreams without a Spec;
   the true number was 11. Ten Specs existed but declared no `owner-dream:` link, and one
   (`spec-upstream-discovery`) had unparseable frontmatter that `except: return {}` silently
   converted into "no Spec." The wrong number 21 was repeated into EXEMPLAR-STANDARD itself
   before the exemplar chain was used as a test case.
2. **2026-08-08 — the satellite-consolidation blind spot** (fixed in `e3171bdcc6`). INV-1
   re-flagged Dreams whose whole chain had been legitimately folded into another station's
   Spec under the 2026-08-02 satellite-consolidation convention. The fix added the
   `covers-dreams:` frontmatter mechanism plus a `## Satellite:` heading fallback. Until
   then the detector overcounted the INV-1 backlog (16 reported vs. 10 real).

The sibling has the same shape: `bmad_drift_check.py`'s only meta-test
(`.claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py`) runs it
`--integrity-only` against the live repo — a smoke test of the current tree, not a test of
the detector's logic — and PR #181 (2026-08-02) shipped "a drift-check coverage fix,"
i.e. another detector found wrong in production. `dream_chain_check.py` has **zero** tests
of any kind, and its `frontmatter()` still swallows every parse failure via
`except Exception: return {}` — the exact defect class that caused incident 1 remains a
standing hazard for any future frontmatter it reads.

## Goal

The detectors that enforce the Dream-to-Code model are themselves verified by tests with
known answers, and every time a detector is found wrong the incident is recorded durably —
so the next wrong number is caught by a fixture instead of by an operator noticing.

## Scope (capabilities)

1. **Fixture-based meta-test suite for `dream_chain_check.py`.** Unit tests that build
   known-good and known-bad Dream/Spec trees in a temp directory (via monkeypatched
   `ROOT`/`DREAMS`/`PROJECTS`/`GOVERNANCE` or an injectable root) and assert exact findings
   — not just "the live repo passes." Minimum fixture cases, each derived from a real
   incident or invariant:
   - a Spec with no `owner-dream:` → exactly one INV-0 finding (with the implied-slug remedy);
   - a Dream with no Spec → INV-1; a Dream covered via `covers-dreams:` → **no** INV-1;
     a Dream covered only via a `## Satellite: <Title>` heading → no INV-1 (the 2026-08-08
     blind spot, regression-pinned forever);
   - a Spec with **unparseable frontmatter** → surfaced as a finding or warning, never
     silently treated as absent (fixes the standing `except: return {}` hazard from
     incident 1);
   - `owner: guild` beyond the two constitutive Dreams → INV-2 `owner-unassigned`;
     a Spec filed under the wrong station → INV-2 `spec-location-mismatch`;
   - flat `prd.md` / missing `epics.md` → the three INV-3 kinds;
   - a fully conformant tree → zero findings, exit 0.
2. **Fixture-based meta-tests for `bmad_drift_check.py`'s deterministic checks** (the
   finding classes its docstring enumerates: pin-missing, archive-misplaced, stray-file,
   spec-status-stale at minimum), replacing "run it against the live repo and trust it" as
   the only verification. The existing live-repo integrity meta-test stays — it gates the
   tree; the new tests gate the detector.
3. **A detector-incident log** — a tracked companion in this Spec's directory recording
   every occasion a detector's output was found wrong: date, detector, wrong claim, true
   value, root cause, fixing commit, and the fixture that now pins it. Seeded with the
   three real entries above (2026-07-28 INV-0 / frontmatter-swallow, 2026-08-02 PR #181
   drift-check coverage, 2026-08-08 satellite blind spot). New entries are mandatory in the
   same change that fixes a detector.
4. **The `--dreams` hygiene mode** promised by the 2026-07-23 restructure, with the
   boundary fixed here: hygiene = per-Dream-file frontmatter validity (status drawn from
   the README vocabulary, `owner:` in the known station set or `guild`, `title:` present)
   — as distinct from chain completeness, which stays INV-1/2/3. Covered by the same
   fixture suite from day one; it does not ship untested like its siblings did.

## Success signals

- Both detectors have meta-tests that fail on a deliberately reintroduced version of each
  logged incident (mutation-check the suite once at delivery: revert `e3171bdcc6`'s
  satellite logic locally → the suite goes red).
- Unparseable Spec frontmatter can no longer masquerade as an absent Spec.
- The incident log exists with its three seed entries, and the next detector fix (there
  will be one) lands with a log entry and a pinning fixture in the same commit.
- `pixi run -e local-recipes python scripts/dream_chain_check.py` behavior on the live
  repo is unchanged for conformant trees — this Spec hardens the detectors, it does not
  move the goalposts they measure.

## Constraints

- **The detectors stay stdlib + PyYAML only** — their docstrings declare this deliberately
  ("so it runs in bare CI like the other detectors"), and nothing here may add a runtime
  dependency to them. The *meta-tests* may use pytest (the repo's existing meta-test layer
  in `.claude/skills/conda-forge-expert/tests/meta/` already does); the detectors
  themselves may not import it.
- Fixtures are self-contained temp trees, never mutations of the live repo; the suite must
  pass in a bare checkout with no Tier-3 state.
- Exit-code contracts (0 clean / non-zero findings; the registry's 0/1/2 semantics) are
  frozen — CI and the dashboard consume them.
- Any change to a detector's *findings vocabulary* (new `kind`, changed `inv` set) updates
  the fixtures in the same commit, per the registry's own derive-don't-declare principle.

## Non-goals

- **Re-litigating the model itself.** INV-0…INV-3, the ownership rules, the satellite
  convention, and the constitutive/`docs/governance/` special-case are settled in
  EXEMPLAR-STANDARD and the Charter; this Spec verifies the *detectors' implementation of*
  those rules, not the rules. The content model's own contract is
  `docs/governance/spec-pyforge-genesis/` territory.
- Not a rewrite or framework migration of either detector; changes to detector code are
  limited to what testability and the frontmatter-swallow fix require.
- Not (yet) fixture coverage for every detector in `scripts/detectors.py` — see
  `open_questions`; the runtime-scoped detectors in particular have nowhere to run in CI
  (`docs/dreams/fidelity-enforcement.md`'s gap).
- Not the dashboard's or CI's consumption of detector output — downstream surfaces are
  unchanged.
