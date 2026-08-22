---
title: 'The from-scratch run is a chartered capability'
type: 'chore' # feature | bugfix | refactor | chore
created: '2026-08-22'
status: 'done' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: 'fd5c16c16aee5550fd9b18e06a64d6f127a279f1'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      CAP-1's "a clean run reproduces the inventory" success bar is not
      freshly re-verified by this story — no quartet runtime code was
      executed end to end during this change.
    evidence: |-
      This diff touches zero lines in the quartet's four scripts; no cached
      external sources (/tmp/ext-src/*) or live OPENTEAMS_IDENTITY_GIST_ID
      credentials exist in this environment to run a from-scratch pass
      unattended. The claim is evidenced by the pre-existing
      identity-2026-08-20 dated tab (2 days old at story time), produced by
      this same toolchain before this story began — not by fresh execution
      in this diff. Flagged by the intent-alignment review pass: epics.md's
      Given/Then for 16.1 is compound (a behavioral regeneration clause plus
      a governance clause), and only the governance clause is built and
      verified here.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** The packaging-inventory quartet (`scripts/conda-forge-packaging-inventory-operations_metrics.py`, `..._openteams_identity.py`, `..._priority.py`, `scripts/openteams_identity_dashboards.py`) plus its two `conf/` data files already run in production but sit on `scripts/spec_surface_allowlist.txt` under an explicit "delete the line when a Spec claims them" rule — four stations independently flagged them ungoverned. The owning Spec (`spec-conda-forge-packaging-inventory-operations`, CAP-1) now exists but its `surface:` was still `[]`, and its `open_questions` parselmouth fold-placement question was undecided.

**Approach:** Claim the quartet + data files in the Spec's `surface:` (per-file, matching the allowlist's own established per-file precedent), delete the corresponding allowlist blocks, resolve the parselmouth fold-placement question with a dated entry, and re-stamp the spec-surface baseline scoped to this spec.

## Boundaries & Constraints

**Always:** Per-file `surface:` entries, never a blanket glob (the allowlist's own 2026-08-08 split precedent for this exact quartet). No functional changes to the quartet's scripts — CAP-1's behavior already exists; this is governance, not new engineering. Re-stamp the baseline scoped to `--spec pyforge-atlas/spec-conda-forge-packaging-inventory-operations` only, after `git add`ing the changed files first (the baseline reads `git ls-files`).

**Block If:** None identified — self-contained governance action with a clear resolution path.

**Never:** Do not touch the unrelated Wagtail "Epic 16" story files (`spec-16-1-instance-deploy-definition.md`, `spec-16-2-httpx-opener-and-rehearsal.md`) — a different epic that collides on the same number due to an `epics.md` authoring defect (two separate `## Epic 16:` headings). Do not modify the quartet's Python logic. Do not create a second toolchain. Do not execute a full live network run against real credentials/gist as part of this change — CAP-1's "clean run reproduces the inventory" claim is evidenced by the already-live `identity-2026-08-20` dated tab the Dream cites, not re-executed here.

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md` -- owning Spec; `surface:` now claims the quartet (was `[]`); the parselmouth resolution lives in `## Constraints` (`open_questions:` cleared to `[]` per review pass); `companions:` now cross-references the prompt/replay docs.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/.memlog.md` -- dated entries recording the fold-placement decision + the governance action (spec_surface_check's drift detector keys off this file's hash).
- `scripts/spec_surface_allowlist.txt` -- the two conda-forge-packaging-inventory-operations blocks (quartet scripts + data files, with their explanatory headers) deleted per the file's own rule.
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to this spec only.
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` / `..._openteams_identity.py` / `..._priority.py` / `openteams_identity_dashboards.py` -- the governed quartet; read for behavior confirmation, unmodified.
- `docs/dreams/conda-forge-packaging-inventory-operations.md` -- Dream (source of the CAP-1 contract); read-only.
- Auto-memory `project_prefix_dev_mapping_upstreams.md` -- un-deferred 2026-08-22, names the fold target explicitly (`mapping_manager`/`name_resolver`) — the evidence behind the open-question resolution.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md` (lines ~1600 and ~1640) -- contains two unrelated `## Epic 16:` headings (Wagtail corporate brain; packaging-inventory quartet). Noted, not fixed here — out of this story's scope; flagged for a future correct-course pass.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md` -- populate `surface:` with the 6 quartet paths; append the parselmouth resolution to `open_questions` -- closes CAP-1's "surface claims the quartet" criterion. DONE.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/.memlog.md` -- append dated decision + governance-event entries -- gives spec_surface_check's memlog-based drift detector a moved memlog to key off. DONE.
- `scripts/spec_surface_allowlist.txt` -- delete both conda-forge-packaging-inventory-operations blocks (comments + per-file lines) -- executes the allowlist's own delete-when-specced rule. DONE.
- `scripts/.spec-surface-baseline.json` -- re-stamp scoped to this spec (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-atlas/spec-conda-forge-packaging-inventory-operations`, after `git add`) -- clears the drift-presumed warning. DONE.

**Acceptance Criteria:**
- Given the updated SPEC.md and allowlist, when `pixi run -e local-recipes spec-surface-check` runs, then the overall verdict is `spec-surface: ok` and no finding names `pyforge-atlas/spec-conda-forge-packaging-inventory-operations` or the quartet's file paths. VERIFIED.
- Given `scripts/spec_surface_allowlist.txt`, when grepped for `conda-forge-packaging-inventory-operations`, then zero lines match. VERIFIED.
- Given the SPEC's `## Constraints`, when read, then the parselmouth fold-placement decision is stated explicitly, naming the core `mapping_manager`/`name_resolver` chain as the fold target, not this quartet (moved here from `open_questions` during the review pass; `open_questions:` is now `[]`). VERIFIED.
- Given the quartet's four scripts, when import-compiled, then none raise -- confirms no accidental edits crept in alongside the governance change. VERIFIED.

## Design Notes

Scope was deliberately kept to governance (surface claim + allowlist deletion + the one open question the SPEC explicitly assigns to this story), not a re-implementation of the quartet. The Dream and SPEC both describe the quartet as an already-running capability ("already run in scripts/+conf/"); CAP-1's job here is to make that capability *chartered*, not to rebuild it. The parselmouth fold-placement question resolved to the core `pyforge-atlas` `mapping_manager`/`name_resolver` chain (not this quartet's own identity script) based on auto-memory `project_prefix_dev_mapping_upstreams.md`, which was itself un-deferred on 2026-08-22 (today) and names that chain explicitly as the fold target across three converging pieces of evidence (FABRIC's production use, the OpenTeams `python-supply-lens` dream, and this item). No code change follows from that decision in this story — it is recorded so a later story doesn't re-litigate it.

A pre-existing defect was found and left alone (in scope for a future pass, not this story): `epics.md` has two unrelated `## Epic 16:` H2 headings (Wagtail corporate brain vs. this packaging-inventory epic), which also caused a stale cached `epic-16-context.md` (compiled for the wrong epic) to be regenerated as part of this story's planning step.

## Spec Change Log

_None. No `bad_spec` finding triggered a repair loopback in this run._

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 0, medium 1, low 6)
- defer: 1 (medium 1)
- reject: 9 (low 9)
- addressed_findings:
  - `[low]` `[patch]` SPEC.md `companions:` populated with the `..._prompt.md` / `..._replay.md` docs the "Why" section's "runner/prompt/config/replay" phrase names as quartet members but `surface:` doesn't claim (blind-hunter)
  - `[low]` `[patch]` SPEC.md: same fix above also closes the "the deleted `..._metrics.py` allowlist comment's replay.md contract-binding rule has no equivalent home" finding (blind-hunter + edge-case-hunter, same required action)
  - `[low]` `[patch]` SPEC.md `status:` bumped `ready` -> `in-progress` — CAP-1 is chartered by this story, CAP-2 (16.2) is still `backlog` (blind-hunter)
  - `[low]` `[patch]` SPEC.md `open_questions:` cleared to `[]`; the parselmouth resolution now lives durably in `.memlog.md` and a new `## Constraints` line instead of sitting appended inside a field literally named "open" (blind-hunter + edge-case-hunter)
  - `[low]` `[patch]` SPEC.md `## Constraints` gained an explicit parselmouth fold-placement decision line — previously the decision lived only inside the `open_questions` string, easy to miss when skimming Constraints (blind-hunter)
  - `[low]` `[patch]` `.memlog.md` governance-event entry now names `scripts/.spec-surface-baseline.json` as a touched artifact (it previously only named the allowlist deletion) (blind-hunter)
  - `[medium]` `[patch]` Fixed auto-memory index line for `project_prefix_dev_mapping_upstreams.md`: it still read "DEFERRED" while its own topic file carries a 2026-08-22 "UN-DEFERRED" addendum this story's decision cites — contradicted itself and could mislead a future session into re-litigating the evaluation (blind-hunter; fixed directly in `~/.claude/…/memory/MEMORY.md`, outside this PR's diff)
  - `[medium]` `defer` CAP-1's "a clean run reproduces the inventory" is not freshly re-executed by this diff (zero quartet runtime lines touched); evidenced only by the pre-existing `identity-2026-08-20` tab, not fresh execution — epics.md's Given/Then for 16.1 is a compound clause and only its governance half is built/verified here (intent-alignment auditor). Recorded in frontmatter `deferred:` and `.memlog.md`; no code reverted — the governance work is independently correct and complete regardless of this residual.
  - `[low]` `reject` (x9) — rich per-file allowlist-comment detail already lives in the Dream doc or is git-recoverable (blind-hunter x2, edge-case-hunter x2); the "spec-surface-check wasn't shown re-run" claim is false (it ran 3x and is recorded in this file's own Verification section, just outside the diff scope the reviewer saw) (blind-hunter); a pre-existing carried-over comment the reviewer itself flagged as "not a new problem" (blind-hunter); the hand-rolled surface: parser and the tool-generated baseline hashes were both empirically exercised and confirmed correct via live `spec-surface-check` runs, not just inspected (edge-case-hunter x2); the gist-id-never-committed caution is already stated in SPEC.md `## Constraints` (edge-case-hunter); the parselmouth decision is correctly decision-only with no code anywhere yet to verify against (intent-alignment auditor)

## Auto Run Result

**Summary:** Chartered the packaging-inventory-operations quartet (4 scripts + 2 conf data files) under `spec-conda-forge-packaging-inventory-operations`'s `surface:` (was `[]`), deleted the two corresponding `scripts/spec_surface_allowlist.txt` blocks per that file's own "delete-the-line" rule, resolved the parselmouth fold-placement open question (core `mapping_manager`/`name_resolver` chain, not this quartet), and re-stamped the spec-surface baseline scoped to this spec. Zero quartet runtime code changed — governance only.

**Files changed:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md` — `surface:` populated (6 paths); `companions:` populated (2 docs); `status:` ready → in-progress; `open_questions:` cleared to `[]`; `## Constraints` gained the parselmouth decision line.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/.memlog.md` — dated decision + governance-event entries, plus a deferred-item note from the review pass.
- `scripts/spec_surface_allowlist.txt` — both conda-forge-packaging-inventory-operations blocks deleted (6 lines + their explanatory headers).
- `scripts/.spec-surface-baseline.json` — re-stamped, scoped to this spec only (verified: diff touches only this spec's entry).

**Review findings breakdown:** 17 findings across 4 parallel reviewers (blind-hunter, edge-case-hunter, verification-gap, intent-alignment). 7 patched (1 medium, 6 low — all applied in this pass), 1 deferred (medium — CAP-1's fresh-execution proof, recorded in frontmatter `deferred:` and memlog), 9 rejected (already true, already preserved elsewhere, or git-recoverable — see Review Triage Log for the per-item reasoning), 0 intent_gap, 0 bad_spec.

**Follow-up review recommendation:** `true`. Score = 3×medium(1) + 1×low(6) = 9 ≥ 5. Patched-finding counts: high 0, medium 1, low 6.

**Verification performed:**
- `pixi run -e local-recipes spec-surface-check` — `spec-surface: ok -- every tracked file governed or allowlisted; no drift`; zero findings named this spec or the quartet's paths. Run 3× across the pass (initial, post-dev-subagent, post-review-patches), all clean.
- `grep -c conda-forge-packaging-inventory-operations scripts/spec_surface_allowlist.txt` → 0 matches, exit 1.
- `python -m py_compile` over all four quartet scripts → exit 0, no output.
- `python3 -c "yaml.safe_load(...)"` over SPEC.md's frontmatter after every edit — parses cleanly, all fields present as intended (guards against the "stray unquoted `:` silently collapses frontmatter" class of mistake).
- Baseline diff scoped-check: `git diff scripts/.spec-surface-baseline.json` touches only the `pyforge-atlas/spec-conda-forge-packaging-inventory-operations` entry, no other spec's baseline.
- Independently re-run by the dev subagent (fresh, no shared context) and by the verification-gap reviewer (also fresh) — both got the same clean result.

**Residual risks:**
- CAP-1's full behavioral claim ("a clean run reproduces the inventory") rests on a 2-day-old pre-existing artifact, not fresh execution in this change — see the deferred item above. Low risk to landing this PR (the governance action is independently correct and verified), but a future attended, credentialed pass should close it.
- `epics.md` has two unrelated `## Epic 16:` H2 headings (this packaging-inventory epic and an unrelated, already-`done` "Wagtail corporate brain" epic) — a pre-existing authoring defect, noted but not fixed here (out of this story's surgical scope); it caused a stale cached `epic-16-context.md` to be found and corrected during planning. Worth a future correct-course pass.

## Verification

**Commands:**
- `pixi run -e local-recipes spec-surface-check` -- expected: `spec-surface: ok -- every tracked file governed or allowlisted; no drift`, no finding for this spec. RAN, PASSED.
- `grep -c conda-forge-packaging-inventory-operations scripts/spec_surface_allowlist.txt` -- expected: 0 matches (grep exit 1). RAN, PASSED.
- `python -m py_compile` over the four quartet scripts -- expected: exit 0, no output. RAN, PASSED.
