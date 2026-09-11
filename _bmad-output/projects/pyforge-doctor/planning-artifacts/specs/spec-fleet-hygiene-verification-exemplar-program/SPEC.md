---
id: SPEC-fleet-hygiene-verification-exemplar-program
status: shipped   # added 2026-09-09: the key was absent, which silently exempted this Spec
                  # from chain-completeness (board.py:715-716). CAP-1..5 are decomposed as
                  # doctor Epic 12 (12.1-12.5, all done); 0 uncovered CAPs.
owner-dream: docs/dreams/fleet-hygiene-verification-exemplar-program.md
companions:
  - hygiene-gap-catalog.md
sources:
  - docs/dreams/fleet-hygiene-verification-exemplar-program.md
open_questions:
  - "Should the source catalog's remaining not-yet-scoped items (audit methodology ->
     repeatable check; which manual exemplars graduate to mechanical enforcement, and
     via which shape) become their own future Dreams/Specs, or fold into a later
     revision of this one? Left open by the source Dream itself."
  - "Where does the catalog live as a maintained artifact going forward -- does
     docs/dreams/fleet-hygiene-verification-exemplar-program.md remain the catalog,
     updated in place, or does it graduate to a dedicated tracked location once enough
     items have a real status to track?"
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. The source document is for traceability only.

# Fleet hygiene, verification & exemplar-standard catalog

## Why

Tonight's deferred-work audit found a real gap (58+ Tier-3 findings invisible to the detector meant to catch exactly that) and a pattern: this fleet has repeatedly needed a one-off, by-hand sweep to catch something no always-on gate watches for, and named tooling gaps go unfixed for weeks until independently rediscovered — `normalize_deferred_ledgers.py`'s heading-less-entry blind spot was named 2026-07-30 and hit again, independently, on 2026-08-15. The goal is not to build every item the source Dream catalogs (its own text: "Not a commitment to build all of this... none of these categories are sized, prioritized, or scoped for implementation here") — it is to stop re-discovering the same shape of gap in isolated sessions by making the landscape visible in one place, plus fix the handful of items the source flags as already concrete and ready. Full catalog in `hygiene-gap-catalog.md`.

**Scope note:** a convergence check against already-owned work, done before drafting capabilities, found most of the source Dream's Category 2/3/4 content already belongs to other specs — `deferred-work-audit-completeness` (folded into `spec-deferred-work-visibility` CAP-4..7), `deferred-work-resolution-sweep` (this session's sibling Spec), `spec-deferred-work-visibility`'s own CAP-8/9/10 (Epic 9, in progress — Story 9.1 is running as this Spec is being authored), and `bmad-loop-liveness-footgun` (marshal-owned). This Spec's capabilities are deliberately the leftover items: not yet owned elsewhere, and flagged by the source text itself as concrete and ready.

## Capabilities

- **CAP-1 — the catalog stays a maintained, current artifact.**
  - **intent:** An operator or agent facing a "nothing actually checks for X" moment can check one document first and get one of three answers — already catalogued and specced, catalogued but not yet built, or genuinely new — rather than rediscovering it as a fresh, isolated finding.
  - **success:** Given a newly-discovered hygiene/verification/audit gap, checking the catalog against its six categories (`hygiene-gap-catalog.md`) returns a match or confirms genuine novelty; the catalog stays cross-referenced with which items have moved from cataloged to specced to shipped.
  - **verified:** 2026-09-11 — FAIL (genuine, pre-existing, already self-documented) — mechanical re-verification at HEAD a0aba94b0a: `hygiene-gap-catalog.md` last touched 2026-08-21 per `git log`, 21 days stale as of this check — the capability's own "stays a maintained, current artifact" success criterion does not currently hold. Not a new finding: this Spec's own Assumptions section already names this exact gap (two `Status:` tags provably wrong) and explicitly frames it as "a standing maintenance duty," not a reason to hold `shipped` open. Leaving unresolved here — re-currency-ing the catalog is a content task for whoever next uses it, out of proportion for a verification sweep to take on unilaterally.

- **CAP-2 — `EXEMPLAR-STANDARD.md`'s conformance table is refreshed and re-verified.**
  - **intent:** The fleet's designated reference for what "done and clean" means stops reporting a stale, wrong table — flagged by the source Dream as the single most concrete, ready-now item.
  - **success:** Given the DW-ledger column currently shows only `pyforge-atlas` compliant while 7 other projects now carry real, git-tracked `deferred-work-ledger.md` files (warden 43, atlas 122, marshal 109, mason 48, steward 74, herald 45, doctor 20, scribe 7, as of this session), running the refresh corrects the table to the live state, and every other column is checked for the same staleness.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: `git log` confirms `b3d63dc415 doctor: story 12.2 -- refresh EXEMPLAR-STANDARD.md conformance table` landed, and the stale "only pyforge-atlas compliant" claim is gone from the file entirely (grep for the old per-project figures returns nothing); a live governance mechanism now guards against the table going stale again — `pixi run -e local-recipes governance-currency` (spec-fleet-consistency-standard CAP-6, checks every skill/script/path EXEMPLAR-STANDARD.md cites still resolves) runs clean today: "every skill, script and path named in 4 governed document(s) resolves".

- **CAP-3 — `chain-completeness`'s INV-A parses capability ids, not a bare substring match.**
  - **intent:** "This open Spec is decomposed" is judged by whether the Spec's real `CAP-N` ids trace to actual stories, not by whether the Spec's slug merely appears somewhere in PRD/epics prose.
  - **success:** Given a Spec that grew from 3 capabilities to 10 with only 3 ever decomposed into stories, the detector reports the real 7-capability gap instead of `ok` — reproduces and fixes `DW-CHAIN-COMPLETENESS-1`, logged against `spec-deferred-work-visibility` this session.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: INV-A parses declared CAP ids via `_parse_declared_cap_ids` (falls back to bare-substring only when a Spec declares no CAP ids at all — documented, not the general path); `tests/unit/test_sources_board_chain_completeness.py::test_multi_cap_spec_partial_coverage_names_uncovered_ids` reproduces exactly the described defect class and passes; 54/54 tests in that file green.

- **CAP-4 — `dream-chain`'s gap count surfaces in `fleet-picture`'s ambient ATTENTION block.**
  - **intent:** An unspecced Dream nags quietly in the report an operator already checks every landing pass, instead of waiting for a separate `dream-chain` run.
  - **success:** Given N Dreams fleet-wide with no Spec, `fleet-picture`'s ATTENTION block names the count without a separate detector invocation.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: live `pixi run -e local-recipes fleet-picture` ATTENTION block reads "1 Dream(s) with no Spec (e.g. marshal-launch-environment-integrity) -- run `pixi run -e local-recipes dream-chain-check` for the full list" — no separate invocation needed to see the count.

- **CAP-5 — `spec_surface_check.py --write-baseline`'s read-modify-write race is closed.**
  - **intent:** Two concurrent `--write-baseline` invocations against `scripts/.spec-surface-baseline.json` do not silently clobber each other's write.
  - **success:** Given two concurrent `--write-baseline` calls, the race is closed such that neither write is silently lost — reproduces and fixes `DW-13-5-2`.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: `scripts/spec_surface_check.py::_baseline_lock` holds an advisory `fcntl.flock(fd, fcntl.LOCK_EX)` on a sidecar `.spec-surface-baseline.json.lock` around the read-modify-write, with an explicit comment ruling out the inode-swap footgun (`os.replace` would defeat a lock held on the baseline file itself) and the unlink-while-others-wait footgun (lockfile never unlinked) — both real races a naive fix would have reintroduced.

## Constraints

- **Must not duplicate scope already claimed elsewhere.** This Spec's capabilities are deliberately the leftover items the source catalog names as concrete and not-yet-owned — never a re-specification of Epic 9 (CAP-8/9/10) or the sibling `deferred-work-resolution-sweep` Spec's CAP-7.
- **Category 5's exemplar-graduation question and Category 3's "audit methodology → repeatable check" question stay explicitly unscoped here**, per the source Dream's own "not sized, prioritized, or scoped for implementation" disclaimer — captured as Open Questions, never invented as capabilities.

## Non-goals

- Not a commitment to build everything in the source Dream's Categories 1–6 — its own text says so explicitly; this Spec extracts only the not-yet-claimed, flagged-ready items.
- Not re-specifying deferred-work promotion, deferred-work resolution, the generalized hygiene sweep, loop-home branch staleness, or `bmad-loop-liveness-footgun` — all already have their own Dream/Spec/Epic.
- Not deciding whether or how the purely-manual exemplars (six-act deck framework, warden-standalone infographic reference, recipe-domain patterns, CFE branch-naming convention) graduate to mechanical enforcement — explicitly punted by the source Dream to be decided per-exemplar later, via one of two shapes it names (bake-into-generator, or repeatable-apply-script).

## Success signal

The next time someone hits a "nothing actually checks for X" moment that rhymes with one of the six catalogued categories, the catalog names it as already-known rather than a fresh discovery — and the fleet's own conformance/detector surface (`EXEMPLAR-STANDARD.md`'s table, `chain-completeness`, `dream-chain` visibility, `spec-surface-check`'s race) no longer contradicts itself on the specific points this session already found wrong.

## Assumptions

- CAP-1's residual is live and is **not** covered by the `shipped` status: `hygiene-gap-catalog.md`
  has not been touched since 2026-08-21 (`69ba11329f`) across doctor Epics 13–20, and two of its own
  `Status:` tags are provably wrong (`:38` calls Story 12.4 "backlog, not yet landed" while the
  ledger reads done). The capability shipped; keeping the catalog current is a standing maintenance
  duty, recorded here as a companion-currency residual rather than a reason to hold the status open.

## Open Questions

- Should the source catalog's remaining not-yet-scoped items (audit methodology → repeatable check; which manual exemplars graduate to mechanical enforcement, and via which shape) become their own future Dreams/Specs, or fold into a later revision of this one? Left open by the source Dream itself.
- Where does the catalog live as a maintained artifact going forward — does `docs/dreams/fleet-hygiene-verification-exemplar-program.md` remain the catalog, updated in place, or does it graduate to a dedicated tracked location once enough items have a real status to track?
