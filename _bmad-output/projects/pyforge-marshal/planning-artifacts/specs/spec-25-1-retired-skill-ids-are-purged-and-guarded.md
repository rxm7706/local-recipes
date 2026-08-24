---
title: 'Retired skill IDs are purged and guarded'
type: 'chore'
created: '2026-08-22'
status: 'done'
baseline_revision: '2dc63365fbfd8e2c4de4cf0a430677ff38abf7fe'
final_revision: '7e384adbc6a07ee29328081296119d3a642c0699'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/alignment-inventory.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The memory half of CAP-1 (3 auto-memory entries + MEMORY.md index) is
      partially swept and permanently outside the guard's scan scope.
    evidence: |-
      Dispatch explicitly assigns ~/.claude memory files to the parent session
      ("parent handles those"), so this story did not touch them. Review verified
      live: the four inventory-named entries were glossed out-of-band at
      2026-08-22 04:33 (top-of-file gloss only) but bodies retain bare retired
      IDs; feedback_skill_disambiguation.md lines 17/18/25/40 still carry bare
      LIVE routing instructions (bmad-review-adversarial-general,
      bmad-review-edge-case-hunter, bmad-create-prd/-architecture,
      bmad-document-project); MEMORY.md index lines ~78-80 carry bare
      bmad-dev-auto and were not touched at all. The repo guard cannot reach
      per-user memory by construction; its docstring now states the exclusion.
    location: >-
      ~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/
    severity: medium
---

<intent-contract>

## Intent

**Problem:** The 20 retired v6 skill IDs (the published shim list: bmad-quick-dev, bmad-dev-auto, bmad-create-story, bmad-dev-story, bmad-create-prd, bmad-edit-prd, bmad-validate-prd, bmad-create-architecture, bmad-market-research, bmad-domain-research, bmad-technical-research, bmad-sprint-status, bmad-document-project, bmad-generate-project-context, bmad-review-adversarial-general, bmad-review-edge-case-hunter, bmad-review-verification-gap, bmad-editorial-review, bmad-editorial-review-prose, bmad-editorial-review-structure) survive in live docs and the seed template every new station inherits; shim removal rides the committed v7 cut, so any surviving bare name becomes a broken instruction (CAP-1; inventory findings #2, #3).

**Approach:** Sweep the live surfaces — 5 epics.md + marshal PRD.md, marshal seed templates, AGENTS.md — glossing historical/narrative text (never rewriting shipped history) and renaming live dispatch-instruction text outright; then land a meta-test in the shared CFE meta-suite that reds any bare reintroduction, proven red-on-plant via fixture.

## Boundaries & Constraints

**Always:** Historical text keeps its recorded name plus a gloss; live instruction text gets the new name outright. The guard's allow rule is ONE mechanical line-based rule, documented in the test. Marker/comment literals parsers depend on (e.g. the Tier-3 "bmad-dev-auto step-04" marker described in doctor epics) are described-with-gloss, never renamed. Reconcile governed-surface edits: memlog append (6.11 `_bmad/scripts/memlog.py`) + scoped `--write-baseline` AFTER `git add`. Physical artifact paths only; `BMAD_ACTIVE_PROJECT=pyforge-marshal` per invocation; never `scripts/bmad-switch`.

**Block If:** A sweep target's occurrence cannot be classified historical-vs-live from story status + surrounding text; or the guard cannot pass without editing a do-not-touch surface.

**Never:** Touch `.claude/skills/**` shims/docs (the new meta-test file is the sole addition there), `docs/specs/**`, CHANGELOGs, `~/.claude` memory files (parent's remit), `_bmad/**`, or this chain's own spec folder (`spec-bmad-611-era-alignment/*` — cites names as evidence). Never plant a retired ID in tracked repo files to prove the guard. Never stage `.idea/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Swept tree | guard scans live surfaces | zero violations, test passes | n/a |
| Planted bare ID | fixture file with `bmad-dev-auto` alone on a line | scanner reports `file:line: id` | test asserts detection |
| Glossed mention | line carries ID + `6.11`/`retired`/`forwarder`/`shim`/`deprecated` | allowed | test asserts allowance |
| Glob rot | scan set resolves empty/shrunken | guard fails loudly (min-count assertion) | prevents silent no-op |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/files/dream-first-workflow.md.j2:9` -- LIVE (ships to every new station): `bmad-dev-auto` → `bmad-build-auto` outright.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml:66` -- rationale block scalar: add "(the retired 6.x name)" gloss; L56 already carries "forwarder" (allowed as-is).
- `AGENTS.md:59` -- LIVE cross-tool entry point, same sentence as the j2: rename outright.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md` -- L804/808/853/892 shipped Epic 7/8 history (7-1..7-3 done) → gloss; L1200 gloss "(retired in 6.11)"; L1218 already carries "6.11" (no-op).
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md:43` -- execution-mode legend → gloss.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md:98` -- 2026-07-12 execution-model note (31/31 shipped) → gloss.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` -- L479 historical sizing → gloss; L993 LIVE guidance for backlog 13.x (`prefer bmad-quick-dev`) → `bmad-build` outright.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md` -- L1492/1494/1505/1510/1522/1534/1554/1576 shipped 5.9/5.10 history (code label is `"not-loop-native"`, never renamed) → gloss; L3171 gloss "(retired in 6.11)"; L3389 (N=22 historical citation) + L3394 (Spec-quoted HARD boundary) → gloss; L3406/L3410 live AC/engine text → `bmad-build-auto` outright; L3483 gloss; L3836 carries "shims" (no-op — also the `[dev] skill = "bmad-dev-auto"` discriminator, kept by Spec constraint).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/PRD.md` -- frontmatter `edit_history` L17/24/26/27: append trailing YAML comment `# skill retired in 6.11` (history untouched; verify frontmatter still parses); L593 table row: inline gloss "(6.11: `bmad-prd`)".
- `CLAUDE.md` -- already glossed on every hit line (L98/105/114/116/180 carry "6.11", L115 "deprecated forwarders") — no edit; guard verifies.
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` -- NEW guard. Conventions from sibling tests: `@pytest.mark.meta` (`--strict-markers`), REPO_ROOT from `Path(__file__)`, incident-narrative docstring. As implemented (post-review tightening): allow markers anchored/word-bounded (`(?<![\d.])6\.11(?!\d)|\b(?:retired|forwarders?|shims?|deprecated)\b`, IGNORECASE); ID regex IGNORECASE with left boundary `(?<![A-Za-z0-9_-])` and right boundary `(?![A-Za-z0-9_])` (trailing hyphen admitted so compounds fire the base ID); per-glob rot floors. Governed by `pyforge-mason/spec-conda-forge-expert-rebuild` surface glob → RECONCILED-BY-NAME memlog entry there.
- Governance: seed template files governed by `pyforge-marshal/spec-pyforge-marshal` → memlog entry + `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-marshal --spec pyforge-mason/spec-conda-forge-expert-rebuild` after `git add`. epics.md/PRD.md/AGENTS.md/CLAUDE.md are allowlisted (no owner) — no memlog obligation.

## Tasks & Acceptance

**Execution:**
- Seed templates (j2 + manifest) -- apply the two edits above -- the template ships to every new station.
- `AGENTS.md` -- rename L59 -- live entry point.
- 5 × epics.md + marshal `PRD.md` -- apply per-line gloss/rename plan from Code Map -- purge without rewriting shipped history.
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` -- create -- scanner + live-tree test + tmp_path planted-ID/glossed-mention proof + non-empty-scan-set floor. Scan scope (include-list): `_bmad-output/projects/*/planning-artifacts/epics.md`, `_bmad-output/projects/*/planning-artifacts/PRD.md`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/**`, `AGENTS.md`, `CLAUDE.md`. Allow rule (the ONE mechanical rule, as implemented after review tightening): an occurrence is allowed iff its line also matches, case-insensitively, anchored `6.11` (`(?<![\d.])6\.11(?!\d)` — not inside `v8.6.11`/`16.11`/`6.111`) or whole-word `retired|forwarders?|shims?|deprecated` (`\b`-bounded — `shimmer` doesn't count). ID match is IGNORECASE with a left boundary `(?<![A-Za-z0-9_-])` (no `x-bmad-quick-dev` false-fire) and a right boundary `(?![A-Za-z0-9_])` that admits a trailing hyphen (a compound like `bmad-dev-auto-driven` fires the base ID); the longest-first alternation keeps `bmad-editorial-review` from double-firing inside its `-prose`/`-structure` variants. Rot guard is per-glob floors (epics>=6, PRD>=1, templates>=8, AGENTS>=1, CLAUDE>=1) plus the empty-glob assertion; templates glob is the version-portable `**/*`.
- Governance reconcile -- `git add` all; memlog append to both owning specs; scoped `--write-baseline`; `python scripts/spec_surface_reconcile.py` → 0 findings.

**Acceptance Criteria:**
- Given the swept tree, when the meta suite runs, then the new guard passes and only the 3 known pre-existing failures (test_recipe_yaml_parse_audit, test_no_redundant_python_min) remain red.
- Given a fixture file with a bare retired ID, when the scanner runs over it, then the violation is reported naming file+line — demonstrated in-test, repo never dirtied.
- Given the marshal suite (`pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests -q`), when run post-sweep, then green (seed-template tests assert markers, not retired names).
- Given `python scripts/spec_surface_reconcile.py` post-stamp, then 0 findings.

## Verification

**Commands:**
- `pixi run -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/ -q` -- expected: new guard green; only the 3 known main failures red.
- `pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests -q` -- expected: green.
- `python scripts/spec_surface_reconcile.py` -- expected: 0 findings.
- `grep` the 20 IDs over scan scope -- expected: every remaining line carries an allow marker.

## Spec Change Log

(empty — no bad_spec loopback occurred; the as-implemented regex-boundary details were amended directly in Code Map / Tasks during the 2026-08-22 review pass, recorded in the Review Triage Log below.)

## Review Triage Log

### 2026-08-22 — Review pass

Four parallel layers: blind-hunter, edge-case-hunter, verification-gap, intent-alignment.

- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 3, low 6)
- defer: 1: (high 0, medium 1, low 0)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` ALLOW_MARKER_RE laxity — `6.11` matched inside `v8.6.11`/`16.11`, `shim` inside `shimmer`; anchored (`(?<![\d.])6\.11(?!\d)`) + word-bounded (`\b(?:retired|forwarders?|shims?|deprecated)\b`), live tree stays green.
  - `[medium]` `[patch]` RETIRED_ID_RE asymmetries — added left boundary (no `x-bmad-quick-dev` false-fire), IGNORECASE (uppercase evasion closed), right boundary `(?![A-Za-z0-9_])` so hyphen-compounds (`bmad-dev-auto-driven`) fire the base ID; variant tests extended to prove all three.
  - `[medium]` `[patch]` Rot guard single global floor → per-glob floors (epics>=6, PRD>=1, templates>=8, AGENTS>=1, CLAUDE>=1) so one surface can't collapse behind another's growth.
  - `[low]` `[patch]` `templates/**` glob was Python>=3.13-only → version-portable `**/*` + comment.
  - `[low]` `[patch]` Added adjacent-line negative test (marker on a neighboring line does not suppress a bare ID).
  - `[low]` `[patch]` Docstring/message fixes: allow pattern no longer wrapped mid-alternation; deliberate scope exclusions documented (per-user memory = parent-owned; code = `[dev] skill` discriminator Spec-mandated); canonical gloss exemplar added to the failure message.
  - `[low]` `[patch]` scan_lines hoists the allow-marker check to once per line.
  - `[low]` `[patch]` Doctor epics gloss defects — broken grammar at Story 8.1 ("a literal parsers match" → "a marker literal that parsers match") and un-backticked glossed name at Story 7.1.
  - `[low]` `[patch]` Baseline-stamp honesty — memlog note appended to spec-pyforge-marshal recording the ~40 stale-baseline hash catch-ups (verified against main, not Story 25.1 content) + scoped re-stamp; reconcile 0 findings.

Rejected on intent authority (dispatch text is the intent): memory sweep here (parent-owned surface, explicit carve-out — residue routed to `deferred` instead), code-surface scanning (`[dev] skill = "bmad-dev-auto"` Spec-mandated to survive), guard location (CFE meta-suite mandated), scan-scope widening beyond the named include-list (other files owned by 25.7 / evidence-citing spec folders), replacing the ONE line-based rule with a proximity window (parent offered line-based; a window would red the PRD's own end-of-line glosses), per-occurrence live-vs-historical split inside marshal Epic 22 / steward (deliberate, recorded in Code Map), Story 5.9 gloss "self-contradiction" (rewriting the shipped AC would violate gloss-don't-rewrite; the gloss documents shipped reality), prefix-less shorthand ("quick-dev-sized") outside the 20-ID universe, shim-less removed skills (bmad-check-implementation-readiness/bmad-index-docs) outside the published 20-shim list, YAML-comment fragility on PRD regeneration (guard reds and the regenerating session re-glosses — working as designed), CLAUDE.md's richer gloss vs the j2/AGENTS.md bare rename (dispatch directed the outright rename), gloss-form variety (rule is marker-based by design; exemplar now in the failure message).

## Auto Run Result

**Summary.** CAP-1 sweep + regression guard landed. The 20 retired v6-shim skill IDs are purged from the repo's live surfaces: live dispatch-instruction text renamed outright to the 6.11 names (`dream-first-workflow.md.j2` + AGENTS.md → `bmad-build-auto`; steward Epic-13 guidance → `bmad-build`; marshal Epic-22 AC/engine text → `bmad-build-auto`); historical/narrative text keeps its recorded name plus a same-line gloss (42 surviving occurrences across 22 scanned files, every one carrying an allow marker; shipped story history never rewritten; doctor's parser-load-bearing "bmad-dev-auto step-04" marker literal kept verbatim). New meta-test `test_no_retired_bmad_skill_ids.py` guards the surfaces from now until the v7 cut.

**Files changed (13 staged):**
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` — NEW guard: 20-ID scanner, ONE line-based allow rule (anchored `6.11` | whole-word `retired|forwarder(s)|shim(s)|deprecated`, case-insensitive), include-list scan scope with per-glob rot floors, red-on-plant + gloss-allowed + adjacent-line + boundary proofs via tmp_path fixtures (7 tests).
- `src/.../seed/templates/files/dream-first-workflow.md.j2` — live rename to `bmad-build-auto` (ships to every new station).
- `src/.../seed/templates/manifest.yaml` — rationale gloss ("the retired 6.x name").
- `AGENTS.md` — live rename to `bmad-build-auto`.
- 5 × `epics.md` (atlas/doctor/steward/warden/marshal) — per-occurrence gloss/rename per the Code Map.
- marshal `PRD.md` — edit_history YAML comments `# skill retired in 6.11` (history untouched; frontmatter re-parsed clean) + R1 table gloss.
- 2 × spec `.memlog.md` (marshal spec-pyforge-marshal; mason spec-conda-forge-expert-rebuild RECONCILED-BY-NAME) + stale-baseline honesty note.
- `scripts/.spec-surface-baseline.json` — scoped re-stamp for both governed specs.

**Review breakdown.** 9 patches applied (3 medium, 6 low — all listed above); 1 deferred (memory-surface residue, parent-owned — see frontmatter `deferred`); 12 rejected on intent authority.

**Follow-up review recommendation:** true. Patched this pass: high 0, medium 3, low 6 → score 3×3 + 6×1 = 15 ≥ 5.

**Verification (re-run after patches, independently confirmed):**
- CFE meta suite: 7549 passed, 2 failed — exactly the pre-existing main reds (`test_recipe_yaml_parse_audit`, `test_no_redundant_python_min`); the guard's 7/7 green. (Dispatch said "three known failures"; on this tree it is these two — the transient third, `test_skill_files_tracked`, clears once the new file is staged.)
- Marshal suite: 5152 passed.
- `python scripts/spec_surface_reconcile.py`: 0 findings.
- Tightened bare-survivor grep over the scan scope: 0 survivors (22 files, 42 allowed occurrences).

**Residual risks.** (1) The memory half of CAP-1 is out-of-band and parent-owned: live routing lines in `feedback_skill_disambiguation.md` (L17/18/25/40) and `MEMORY.md` index (~L78-80) still carry bare retired IDs; the repo guard cannot see them (documented in its docstring). (2) The line-based allow rule exonerates a whole line — on the PRD's very long edit_history lines a future bare ID added to an already-glossed line passes silently; documented design tradeoff of the ONE mechanical rule. (3) `[dev] skill = "bmad-dev-auto"` remains in rendered loop-home policies by Spec constraint (bmad-loop resolves the skill on disk); code surfaces are deliberately outside the guard. (4) The PRD frontmatter glosses are YAML comments — a tool that regenerates the frontmatter drops them, which reds the guard (loud, self-healing on re-gloss).
