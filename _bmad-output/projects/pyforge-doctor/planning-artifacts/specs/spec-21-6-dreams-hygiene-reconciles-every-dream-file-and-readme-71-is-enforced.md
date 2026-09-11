---
title: '`dreams-hygiene` reconciles every Dream file, and README:71 is enforced'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '8b3d84f325f4fcb48ef324c9821acca5040e4f3c'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Wire the three new dreams-hygiene classes into detectors-ci after steward
      confirms live-tier volume is acceptable.
    evidence: |-
      Spec scopes measurement before joining detectors; checks run only via
      dream-chain --dreams and pyforge-doctor-test live-count tests today.
    severity: low
  - summary: >-
      Refresh docs/dreams/README.md Phase-2b prose to describe file-driven
      reconciliation and the three new finding classes.
    evidence: |-
      README still describes hygiene as README-row-only reconciliation;
      behavior changed in chain.py but tier doc not updated in this story.
    location: >-
      docs/dreams/README.md
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_parse_readme_dream_statuses` reconciles only Dreams that already carry
a `docs/dreams/README.md` row, so **61 of 131** Dream files are invisible to the
detector while it reports `ok`. `readme-table-orphan` is one-directional by design —
it catches rows pointing at missing files, never files missing a row. Three separate
gaps compound this: `docs/dreams/README.md:71`'s own rule (a Dream at `status:
specified` whose Spec is not `ready` or beyond should be reported) is not enforced —
today `django-accelerator-framework` violates it and passes both `dream-chain-check`
and `dream-chain --dreams`; Kinship `[[…]]` wikilinks are never validated against
`docs/dreams/`, so broken links go unnoticed (the 2026-09-09 currency review found
some); and files-without-a-row is simply unmeasured.

**Approach:** Derive reconciliation from the Dream files themselves rather than from
the README's own (incomplete) table, treating the README as the incomplete map it is.
Add three new classes: (1) a Dream file with no README row is a named warn-only
finding; (2) README:71's rule is enforced as a named finding; (3) every `[[…]]`
Kinship wikilink is resolved against `docs/dreams/`, with an unresolvable target
warned by name. Each class ships with a fixture proving it fires **and** a measured
count against the live tier, so a class that would flood the report is narrowed
before it joins `detectors` rather than after.

## Boundaries & Constraints

**Always:**
- Reconciliation is derived from the Dream files themselves, not solely from the
  README table.
- Each of the three new classes (file-missing-a-row, README:71 violation, broken
  Kinship wikilink) is warn-only.
- Each class ships with both a fixture proving it fires and a measured count against
  the live tier before it joins `detectors`, so a flood-prone class is narrowed first.
- README:71's rule (a Dream at `status: specified` whose Spec is not `ready` or beyond
  is reported) is enforced as its own finding, verified against the live
  `django-accelerator-framework` case.
- Every `[[…]]` Kinship wikilink is resolved against `docs/dreams/`; an unresolvable
  target names the source file and the dead link.

**Never:**
- `readme-table-orphan`'s existing one-directional behavior (rows pointing at missing
  files) is not removed or altered by this story — the new classes are additive.
- No new class ships without both a fixture and a measured live-tree count.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dream file with no README row | Any of the 61 Dream files missing a `docs/dreams/README.md` row | Named warn-only finding | n/a |
| README:71 violation | `django-accelerator-framework`: `status: specified`, Spec not `ready` or beyond | Named finding (today passes both `dream-chain-check` and `dream-chain --dreams` silently) | n/a |
| Broken Kinship wikilink | A `[[…]]` target that does not resolve against `docs/dreams/` | Warn naming the source file and the dead link | n/a |
| Dream file with a README row, no violations | Normal, reconciled Dream | No finding | n/a |
| Flood-prone class at measurement time | A candidate class whose live-tree count is too high to be useful | Narrowed before joining `detectors`, not after | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `_parse_readme_dream_statuses` (`:891`) and the `dreams-hygiene` gather around it.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py` — fixtures and measured-count tests for each of the three new classes.

## Tasks & Acceptance

**Execution:**
- `feature` — derive Dream reconciliation from the files under `docs/dreams/` themselves, not only from the README table rows.
- `feature` — add a "Dream file with no README row" warn-only finding class.
- `feature` — enforce `docs/dreams/README.md:71`'s rule as a named finding, verified against the live `django-accelerator-framework` case.
- `feature` — resolve every `[[…]]` Kinship wikilink against `docs/dreams/`; warn-name unresolvable targets.
- `feature` — add a fixture and a measured live-tier count for each of the three new classes before wiring it in.

**Acceptance Criteria:**
- Given `_parse_readme_dream_statuses` reconciles only Dreams that already carry a README row, so 61 of 131 Dream files are invisible while the detector reports `ok`, when reconciliation is derived from the Dream files themselves and the README is treated as the incomplete map it is, then a Dream file with no README row is a named warn-only finding.
- `docs/dreams/README.md:71` is enforced — a Dream at `status: specified` whose Spec is not at `ready` or beyond is reported (today `django-accelerator-framework` violates it and passes both `dream-chain-check` and `dream-chain --dreams`).
- Every `[[…]]` Kinship wikilink is resolved against `docs/dreams/` and an unresolvable target is a warn naming the source file and the dead link.
- Each of the three new classes ships with a fixture proving it fires and a measured count against the live tier, so a class that would flood the report is narrowed before it joins `detectors` rather than after.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.
- 2026-09-11: corrected Code Map test path to `test_sources_chain_dreams_hygiene.py` after review.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 28 findings — high 0, medium 2, low 6, false 8, maybe-false 0, reject 12
- findings:
  - `[false]` `[reject]` django-accelerator-framework live oracle missing — dream is `archived`, not `specified`; README:71 check correctly skips it; fixture retains slug coverage.
  - `[false]` `[reject]` dream-chain-check should emit new findings — intent scopes hygiene to `--dreams` gather; default dream-chain must stay INV-only per existing test contract.
  - `[false]` `[reject]` Kinship-only scope required — intent says "every [[…]] Kinship wikilink"; body scan matches repo wikilink convention; defer section-scoping unless product narrows.
  - `[false]` `[reject]` specified with no covering Spec should warn here — INV-1 owns dream-without-spec; hygiene README:71 applies when a covering Spec exists.
  - `[false]` `[reject]` blocked Spec should not satisfy ready — `blocked` is a valid post-ready Spec state in BMAD vocabulary.
  - `[false]` `[reject]` frontmatter wikilinks must be scanned — no live dead links observed in frontmatter; body scan is the operational surface.
  - `[false]` `[reject]` OSError during kinship read silently skips — same read path as realization-log; unreadable file already loses other hygiene checks.
  - `[false]` `[reject]` body `---` truncates kinship scan — no live reproducer; split follows established frontmatter strip pattern.
  - `[medium]` `[patch]` `_collect_specs(target, [])` discarded collection WARNs — wired `spec_collect_findings` and emit `specified-spec-not-ready` when expected spec failed collection.
  - `[medium]` `[patch]` satellite `covers-dreams` path untested for README:71 — added `test_specified_spec_not_ready_via_covers_dreams`.
  - `[low]` `[patch]` no negative test for ready Spec suppressing finding — added `test_specified_spec_ready_suppresses_finding`.
  - `[low]` `[patch]` no test for resolving kinship wikilink — added `test_kinship_wikilink_resolves_existing_dream` incl. `.md` suffix.
  - `[low]` `[patch]` Spec status whitespace could misread readiness — strip on `_spec_entry` and readiness comparison.
  - `[low]` `[patch]` wikilink `.md` suffix false dead — strip `.md` before slug lookup.
  - `[low]` `[patch]` OK message under-reports checks — updated aggregate OK copy.
  - `[low]` `[reject]` extension-point exclusion untested — `_SPEC_READY_FOR_SPECIFIED` excludes it by construction; draft fixture covers non-ready path.
  - `[low]` `[defer]` detectors-ci wiring — deferred; measurement gate satisfied, CI join is follow-on.
  - `[low]` `[defer]` docs/dreams/README.md stale Phase-2b prose — deferred to steward doc pass.
  - `[low]` `[reject]` pixi task description stale — out of story scope; defer if needed separately.
  - `[low]` `[reject]` live counts hard-coded — intentional measurement pins per spec; update when tier changes.
  - `[low]` `[reject]` intent 61/131 vs live 63 — snapshot drift in intent-contract (read-only); live test documents current tier.
  - `[reject]` `[reject]` Code Map pointed at wrong test file — fixed in Code Map and Spec Change Log.

## Auto Run Result

Status: done

**Summary:** Extended `gather_dreams_hygiene` with three warn-only finding classes derived from Dream files on disk: `dream-readme-missing`, `specified-spec-not-ready` (README:71), and `kinship-wikilink-dead`. Each ships with fixture tests and live-tree count pins (63 / 3 / 24 as of 2026-09-11).

**Files changed:**
- `chain.py` — README:71 enforcement, missing-row reconciliation, kinship scan, spec status on `_spec_entry`, helpers `_specs_covering_dream` / `_dream_body_after_frontmatter`.
- `test_sources_chain_dreams_hygiene.py` — Story 21.6 fixtures, live counts, review-driven negative-path tests.
- This spec — status, triage log, deferred items, Code Map correction.

**Review:** 5 patches applied (2 medium, 3 low); 2 items deferred; 12 findings rejected as false or out of scope.

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1571 passed, 1 skipped.

**Residual risks:** Live-count tests will need updating when Dreams/README rows change; detectors-ci does not yet run `--dreams` hygiene (by design until volume accepted).

### 2026-09-11 — Review pass
- verdicts: 28 findings — high 0, medium 0, low 2, false 14, maybe-false 12
- findings:
  - `[false]` `[reject]` Code Map points at `test_sources_chain.py` but tests live in `test_sources_chain_dreams_hygiene.py` — doc drift only; tests exist and pass at the actual path.
  - `[false]` `[reject]` Spec Problem still cites 61/131 invisible Dreams — historical intent-contract text; live count test pins 63 as measured 2026-09-11.
  - `[false]` `[reject]` Live oracle must remain `django-accelerator-framework` — Dream archived 2026-09-09; live test correctly substitutes three current violators.
  - `[low]` `[defer]` No fixture proving `extension-point` does not satisfy `specified` — README:71 live pins use extension-point subjects; draft fixture covers the core path.
  - `[false]` `[reject]` No negative pass-path fixtures for README:71 — diff adds `test_specified_spec_ready_suppresses_finding` and `test_specified_spec_not_ready_via_covers_dreams`.
  - `[maybe-false]` `[defer]` `blocked` included in `_SPEC_READY_FOR_SPECIFIED` — no live SPEC.md uses `status: blocked`; would need repo-wide audit before changing semantics.
  - `[false]` `[reject]` Hard-coded live counts brittle — spec requires measured live-tier counts before wiring; pins are intentional regression guards.
  - `[false]` `[reject]` No narrowing documentation for flood-prone classes — story scope is dreams-hygiene gather only; detectors wiring is out of scope.
  - `[low]` `[defer]` `pixi.toml` dreams-hygiene-check description stale — maintenance doc, not story deliverable.
  - `[false]` `[reject]` Test module docstring says fixture-only — Story 21.6 live-count tests are documented in their own docstrings.
  - `[false]` `[reject]` `_collect_specs(target, [])` silently drops collection warnings — hygiene mode intentionally reports README:71 only when covering specs are collected; INV-0 handles missing specs in dream-chain-check.
  - `[false]` `[reject]` Kinship resolution ignores archive/ subdir — intent requires resolution against top-level `docs/dreams/` slugs only.
  - `[maybe-false]` `[defer]` `_dream_body_after_frontmatter` naive `---` split — pre-existing frontmatter pattern shared with other hygiene checks.
  - `[false]` `[reject]` Spec missing implementation changelog — Auto Run Result records decisions below.
  - `[maybe-false]` `[defer]` OSError on Dream read skips kinship scan — same silent-skip pattern as other per-file reads in this gather.
  - `[maybe-false]` `[defer]` Unparseable frontmatter skips kinship — file already emits `unparseable-frontmatter` finding first.
  - `[maybe-false]` `[defer]` Unclosed frontmatter fence truncates kinship body — malformed files already flagged unparseable.
  - `[maybe-false]` `[defer]` Missing opening `---` fence scans frontmatter wikilinks — all conformant Dreams use standard frontmatter fences.
  - `[false]` `[reject]` Wikilink `.md` suffix false positives — code uses `.removesuffix('.md')`; `test_kinship_wikilink_resolves_existing_dream` covers it.
  - `[maybe-false]` `[defer]` Wikilink case sensitivity — Dream slugs are kebab-case lowercase by convention; no live case found.
  - `[false]` `[reject]` Claim: live test must use django-accelerator-framework — archived; substituted subjects verified.
  - `[false]` `[reject]` Claim: tests must live in test_sources_chain.py — wrong Code Map line, not a runtime defect.
  - `[false]` `[reject]` Verification gap: covers-dreams path untested — `test_specified_spec_not_ready_via_covers_dreams` added in diff.
  - `[maybe-false]` `[defer]` Verification gap: malformed covering Spec silently skips README:71 — edge case; INV-0 covers missing/unreadable specs in chain mode.
  - `[false]` `[reject]` Verification gap: multi-Spec any-ready untested — `test_specified_spec_ready_suppresses_finding` covers ready-for-dev suppression.
  - `[maybe-false]` `[defer]` Duplicate `_specs_covering_dream` vs INV-1 logic — intentional local copy with docstring parity claim; shared helper is future refactor.
  - `[false]` `[reject]` Intent: must update dream-chain-check — spec title scopes dreams-hygiene / `dream-chain --dreams` only; dream-chain-check mention is background.
  - `[false]` `[reject]` Intent: must wire into detectors registry — story delivers gather + measured counts; detectors wiring is a separate integration step.
  - `[false]` `[reject]` Intent: specified with no covering Spec must warn — README:71 text targets Specs that exist but are not ready; INV-1 handles absent Specs.

## Auto Run Result

- Summary: Extended `gather_dreams_hygiene` to reconcile from Dream files (not README rows alone), adding three warn-only finding classes: `dream-readme-missing`, `specified-spec-not-ready` (README:71), and `kinship-wikilink-dead`. Each ships with a fixture test and a measured live-tree count test.
- Files changed:
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — Story 21.6 helpers and three new finding loops in `_gather_dreams_hygiene`; `_spec_entry` now carries spec `status` for README:71.
  - `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py` — fixtures, live counts (63 / 3 / 24), pass-path and covers-dreams coverage.
  - `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-21-6-…md` — baseline revision, review triage, done status.
- Review: 0 patches applied; 14 rejected as false/already addressed; 2 low deferred (pixi task description, extension-point-only fixture); 12 maybe-false deferred pending live evidence.
- Follow-up review recommended: **false** (0 patch entries this pass).
- Verification: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1568 passed, 1 skipped.
- Residual risks: Live-tree count pins will need updating when Dreams/README/kinship links change; ~87 new WARN findings when running `dream-chain --dreams` on the full repo (63 missing README rows + 24 dead wikilinks + 3 specified-spec-not-ready).
