---
title: "Story 30.3: Documentation pointers follow 6.12"
type: 'docs'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'cc5a85981f60665076b9d723cff5f36199bdbe7a'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/epic-30-context.md'
warnings: []
deferred:
  - summary: >-
      architecture-bmad-infra.md's "Installed Skills" section (~lines 408-585) states 94
      directories in .claude/skills/ (90 real skills: 52 bmad-*, 16 skf-*, 21
      engineering-practice, 1 conda-forge-expert). A spot-check during this story found the
      live tree now holds well over that, driven by additions since the 2026-09-05 pass: 8 new
      bmad-agent-<station> personas, 10 new bmad-cis-* Creative Intelligence Suite skills, 7 new
      pyforge-<station> skills, and cfe-recipe-lifecycle.
    evidence: |-
      `find .claude/skills -maxdepth 1 -mindepth 1 -type d | wc -l` = 121 (not 94);
      `find .claude/skills -maxdepth 2 -name SKILL.md | wc -l` = 109 (not 90); bare `bmad-*`
      dirs alone = 71 (not 52). Out of this story's declared scope: the Code Map names only
      `source_pin` + the "BMAD-METHOD version" table row + the "Installed modules" row + the
      `manifest.yaml` file-tree comment as the mentions to bump. Flagged as a residual in the
      new "Re-grounded 2026-09-06" note instead of rewritten, per this story's own
      "verification, not new edits" framing and to avoid an unplanned full re-audit of the
      Installed Skills section (its subsection tables and every skill-family count) inside a
      story scoped to the BMAD-core/CFE version pin.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md
      (## Installed Skills, ~lines 408-585)
    severity: low
  - summary: >-
      test_bmad_artifacts_in_sync.py (the only test touching architecture-bmad-infra.md's
      source_pin) checks structural pin parseability only, never semantic pin-behind currency
      at patch-version granularity -- a stale-but-parseable source_pin never fails this test.
    evidence: |-
      Confirmed by the Verification Gap Reviewer and Intent Alignment Auditor independently:
      pyforge.doctor.sources.factory::check_pins compares (major, minor) only, so v8.86.1 vs
      live v8.86.4 never fires pin-behind as a HARD/FAIL finding. Fixing the detector's own
      comparison granularity is out of this docs-only story's scope.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py::check_pins
    severity: low
# A third item originally deferred here ("sprint-status ledger still lists 30.3/30.4 as
# backlog") is CLOSED as of step 11's ledger sync (2026-09-06) and removed from this list
# rather than carried forward as a phantom tracked-work item.
---

<intent-contract>

## Intent

**Problem:** BMAD-METHOD 6.12.0 discontinued `llms.txt`/`llms-full.txt`. Prior investigation
(this story) confirms most of this story's Given/Then is ALREADY satisfied by an earlier
unrelated commit (`8906bfbb22`, steward's core-upgrade follow-up): `CLAUDE.md`'s "BMAD Method
Documentation" section already correctly names the frozen local snapshot + live docs site, no
live doc cites the dead upstream URL, and `bmad-checkpoint-preview`/`bmad-walkthrough` in
living docs was already fixed by Story 30.1. The two genuinely remaining gaps are: (1) the
frozen `.claude/docs/bmad-method-llms-full.txt` snapshot has no header note marking it as a
frozen historical artifact, and (2) `architecture-bmad-infra.md`'s `source_pin` still reads
`BMAD 6.11.0 / conda-forge-expert v8.86.1`, behind the now-installed BMAD 6.12.0 and CFE v8.86.4.

**Approach:** Add the missing header note to the frozen snapshot file. Re-ground
`architecture-bmad-infra.md` following its own established "Re-grounded `<date>`" convention
(visible in its own history, e.g. the 2026-08-24 and 2026-09-05 entries): bump `source_pin`,
verify and update every live fact the doc states (BMAD version, installed modules, schema/MCP
tool/atlas-phase/gotcha/pixi-env counts, CFE version), and record what changed since the last
re-ground in a new dated note.

## Boundaries & Constraints

**Always:**
- Verify every fact stated in the re-ground note against the LIVE repo state at the time of
  writing (run `pixi run --frozen -e local-recipes bmad-groundtruth` for the machine-checked
  figures: schema version, MCP tool count, atlas phase count, gotcha max, pixi env count, CFE
  skill version; check `_bmad/_config/manifest.yaml` for the installed BMAD core/module
  versions) — never copy forward a stale number from the doc's own prior entry without
  re-checking it.
- Follow the doc's own established re-ground format exactly (a new `> **Re-grounded
  <date>**...` blockquote note, in the same style and location as the 2026-08-24 / 2026-09-05
  entries already in the file) so the doc's own internal history stays consistent and
  greppable.
- State the installed `skf` module's ACTUAL current version/source honestly (as of this
  story, it is still `version: main` / `source: custom`, not yet pinned to `v2.1.0` — that
  pin lands later, in Story 46.7, a different repo's pixi env; do not claim it is already
  pinned).
- State `installShims: true` honestly (as of this story, the `--no-shims` retirement apply,
  Story 14.9, has not yet run — do not claim shims are already retired from the installed
  core).
- CLAUDE.md's BMAD Method Documentation section, the llms-full.txt discontinuation framing,
  and the `bmad-checkpoint-preview`→`bmad-walkthrough` living-doc fixes are ALREADY correct —
  verify them (re-read, confirm no drift), do not re-edit them without a found discrepancy.

**Never:**
- Do not regenerate or delete `.claude/docs/bmad-method-llms-full.txt`'s body content — it is
  a frozen, dated historical snapshot; only add a short header note.
- Do not claim the steward `--no-shims` apply (Story 14.9) or the skf `v2.1.0` pin (Story
  46.7) have already happened — both are later steps in this same session's sequence, not yet
  run as of this story.
- Do not touch `development-guide.md` further — Story 30.1 already fixed its two stale
  mentions; re-verify only, don't re-edit unless a NEW discrepancy is found.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Frozen snapshot header | `.claude/docs/bmad-method-llms-full.txt` | Gains a short note marking it frozen/historical, discontinued upstream at 6.12.0, generated 2026-08-17 | N/A |
| architecture-bmad-infra.md source_pin | Currently `BMAD 6.11.0 / conda-forge-expert v8.86.1` | Reads `BMAD 6.12.0 / conda-forge-expert v8.86.4` (or whatever CFE version is current at execution time — re-verify, don't hardcode from this spec) | N/A |
| CLAUDE.md / development-guide.md / dead-URL check | Already correct per investigation | Re-verified unchanged (no edit needed unless a new discrepancy is found) | N/A |

</intent-contract>

## Code Map

- `.claude/docs/bmad-method-llms-full.txt` — lines 1-5 (header: title, "Complete documentation
  for AI consumption", "Generated: 2026-08-17", repo URL). Add ONE short note line/block
  directly after this header stating: frozen historical snapshot, BMAD 6.12.0 (2026-09-03)
  discontinued `llms.txt`/`llms-full.txt` upstream, no live source to re-fetch, see CLAUDE.md
  § BMAD Method Documentation for the live-docs pointer. Do not touch anything below the
  header.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` —
  line 7 (`source_pin: 'BMAD 6.11.0 / conda-forge-expert v8.86.1'`) and the surrounding
  header blockquote area (lines ~12-50, where the 2026-08-24 and 2026-09-05 "Re-grounded"
  notes already live) — bump `source_pin`, add a new dated "Re-grounded 2026-09-06" note
  summarizing the actual delta since the 2026-09-05 pass (verified via
  `pixi run --frozen -e local-recipes bmad-groundtruth` at execution time: as investigated,
  schema/MCP/atlas-phase/gotcha/pixi-env counts are UNCHANGED since 2026-09-05 — 29/46/22/113/28
  — but re-verify, don't trust this spec's numbers as of a later execution time; the CFE
  version and BMAD core version ARE the real deltas: CFE v8.86.1→(current, re-verify) and BMAD
  6.11.0→6.12.0, installed per `_bmad/_config/manifest.yaml`). Also check lines 80-82 and
  ~598 (the "BMAD-METHOD version" table row and the installed-modules row, and the file-tree
  comment showing `installation.version 6.11.0`) — these also need the version bump.
- `CLAUDE.md` § BMAD Method Documentation (lines 51-58) — read-only reference; already
  correct, verify only.
- `development-guide.md` — read-only reference; Story 30.1 already fixed its two stale
  mentions, verify only.

## Tasks & Acceptance

**Execution:**
- `.claude/docs/bmad-method-llms-full.txt` -- ADD a short frozen-snapshot header note --
  closes the one remaining Given/Then clause this file needed.
- `architecture-bmad-infra.md` -- RE-GROUND (source_pin bump + dated note + the 2-3 version
  mentions in its body that cite 6.11.0) -- the substantive remaining work; clears the
  pin-behind drift between the doc's recorded CFE/BMAD versions and the live installed ones.

**Acceptance Criteria:**
- Given the frozen snapshot file, when its header is read, then it states plainly that it is
  historical/frozen and where to find live docs instead.
- Given `architecture-bmad-infra.md` after the re-ground, when `source_pin` is read, then it
  states BMAD 6.12.0 and the current CFE version (verified live, not copied from this spec).
- Given the doc's body BMAD-version mentions (the "BMAD-METHOD version" table row, installed
  modules row, file-tree comment), when re-read, then none still states 6.11.0 as the CURRENT
  installed version (historical narrative about the 6.10→6.11 or 6.11→6.12 transition itself
  may keep those numbers with context, per this repo's established gloss convention).
- Given `pixi run -e local-recipes detectors-ci` and `pixi run -e local-recipes bmad-drift-check`,
  when run after this story, then both stay green (or carry only the pre-existing unrelated
  `dream-chain` finding).

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 10 findings — high 0, medium 1, low 6, false 3, maybe-false 0
- findings:
  - `[low]` `[defer]` Blind Hunter: the sprint-status ledger still lists Stories 30.3/30.4 as `backlog` despite this diff (and 30.4's own already-landed commit) — verified true. Deferred: ledger sync is explicitly a step-11 (PR-landing) task per this session's own plan, not a per-story requirement; will be synced for all touched stories together before the PR opens.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (grouped, same root cause): the new "known-stale" disclosure scoped itself to the "Installed Skills" section only, but the identical stale 94/52/20 figures also appear, unflagged, in the "At a Glance" table (lines 109-110, immediately adjacent to rows this diff DID update) and two other spots (~600, ~1229) — verified true by direct grep. Fixed: widened the disclosure to name all four locations explicitly, added the live spot-check counts (121 dirs / 109 SKILL.md / 71 bare `bmad-*`), and separately flagged that the "20 deprecated forwarders" sub-count is stale on its own terms (now 21, per Story 30.1) without attempting to recompute the compound 52/32 totals with uncertain confidence.
  - `[low]` `[patch]` Blind Hunter: the v8.86.3 bullet's "retired-BMAD-skill-ID guard" language could be misread as saying `bmad-checkpoint-preview` is retired/gone, when it is in fact an installed, live forwarding shim (per `installShims: true` two sentences earlier) — verified true, a real ambiguity. Fixed: reworded to clarify the guard tracks bare mentions of an id that is installed as a live shim, not a removed one.
  - `[low]` `[reject]` Blind Hunter: "bump" (present tense) vs "bumped" (past tense) tense inconsistency in the same paragraph — verified true but cosmetic; no named reader-facing harm, unlikely to cause confusion, and fixing tense consistency is a purely stylistic nit. Rejected as low value.
  - `[false]` `[reject]` Blind Hunter: the frozen-snapshot note lacks a citable external source for the "6.12.0 discontinued llms.txt" claim — refuted: this matches the identical, already-accepted convention in `CLAUDE.md`'s own equivalent note (added by prior commit `8906bfbb22`), which also states the fact without an external citation; consistent house style, not a gap this diff introduces.
  - `[false]` `[reject]` Blind Hunter: this docs-only diff needs the `maintenance` PR label — true but not a diff-level finding; the `maintenance` label is applied at PR-open time (step 11 of this session's plan), not per-story, and is already accounted for in that step.
  - `[false]` `[reject]` Verification Gap Reviewer: no gaps found — the `source_pin` change stays parseable by `check_pins`, and every fact in the new note (BMAD 6.12.0, CFE v8.86.4, `skf: main`, `installShims: true`, commit `4fa185be56`) was independently verified against live ground truth.
  - `[low]` `[patch]` Intent Alignment Auditor: two legacy `docs/specs/*.md` files (`claude-team-memory.md`, `conda-forge-tracker.md`) still cite the dead `docs.bmad-method.org/llms-full.txt` URL as "(live)" — outside this story's declared 4-file Surface, but the story's literal Given/Then says "no live doc cites the dead URL" (unqualified). Verified true by direct read; severity low given these are legacy, rarely-consulted intake specs (one already marked `superseded`), not actively-used documentation. Fixed anyway since the correction was trivial: same-line update in both, matching the established frozen-snapshot/live-docs-site pattern.
  - `[low]` `[defer]` Intent Alignment Auditor: `development-guide.md`, named in the story's Surface line, receives no edit in this diff — verified true, but its only prior action item (the `bmad-checkpoint-preview` rename) was already discharged by Story 30.1, and its own `source_pin` is CFE-only (not BMAD-core), not currently pin-behind at the detector's major.minor granularity. No further action warranted; noted for the record.
  - `[low]` `[defer]` Intent Alignment Auditor: the only test touching this diff's surface (`test_bmad_artifacts_in_sync.py`) checks structural integrity only, never semantic pin-behind currency at patch-version granularity — a real, pre-existing detector-coverage gap (matches Story 30.2's own analogous finding about `pyforge.doctor.sources`), but fixing the detector's own comparison granularity is out of this docs-only story's scope. Recorded as a residual for a future doctor-side story.

## Design Notes

This story's own text, taken literally, implies more work than is actually left — most of its
Given/Then was already satisfied by an unrelated prior commit (`8906bfbb22`) and by Story
30.1's own fixes. The epic's own closing note anticipated this: "30.3's re-ground half lands
after steward's 6.12 apply... which this epic never performs" — that apply landed before this
session started, so the re-ground can proceed now; the rest of the story's surface just needed
verification, not new edits.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes bmad-groundtruth` -- expected: JSON with the live facts
  to re-ground the doc against; re-run this AT EXECUTION TIME, don't trust this spec's cached
  numbers if time has passed.
- `pixi run -e local-recipes detectors-ci` -- expected: clean (or unchanged pre-existing
  findings only).
- `pixi run -e local-recipes bmad-drift-check` -- expected: clean, no HARD findings.
- `grep -n "llms.txt\|llms-full.txt" CLAUDE.md AGENTS.md _bmad-output/projects/pyforge-marshal/planning-artifacts/{architecture-bmad-infra.md,development-guide.md}` -- expected: only the sanctioned local-snapshot-path mentions, no dead upstream URL.

## Auto Run Result

**Summary:** Added a frozen-snapshot header note to `.claude/docs/bmad-method-llms-full.txt`
directly after its existing header block (body content untouched). Re-grounded
`architecture-bmad-infra.md`: bumped `source_pin` to `BMAD 6.12.0 / conda-forge-expert
v8.86.4`; added a new dated "Re-grounded 2026-09-06" note (verified live against
`_bmad/_config/manifest.yaml`, `pixi run --frozen -e local-recipes bmad-groundtruth`, and the
CFE `CHANGELOG.md`, not copied from this spec's cached numbers); and bumped the three
explicitly-scoped body mentions from 6.11.0 to 6.12.0 (the "BMAD-METHOD version" table row, the
"Installed modules" row — also correcting that row's claimed `skf` `2.1.0` to its actual live
`main` / `source: custom` state, honestly not-yet-pinned per Story 46.7 — and the
`_bmad/_config/manifest.yaml` file-tree comment). Re-verified CLAUDE.md's BMAD Method
Documentation section, the llms-full.txt discontinuation framing, and
`development-guide.md`'s `bmad-checkpoint-preview`→`bmad-walkthrough` fix: all already correct
per the story's own investigation, no edits made.

**Files changed:**
- `.claude/docs/bmad-method-llms-full.txt` — added a short frozen/historical header note.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` —
  `source_pin` bump, new dated re-ground note, 3 body-fact bumps (BMAD-METHOD version row,
  installed-modules row incl. skf honesty fix, manifest.yaml file-tree comment).
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-30-3-documentation-pointers-follow-6-12.md`
  (this file) — status, a `deferred` entry for the Installed-Skills-section residual, this
  section.

**Verification performed:**
- `pixi run --frozen -e local-recipes bmad-groundtruth` — schema v29, MCP 46, atlas phases 22,
  gotchas G1–G113, pixi envs 28, CFE skill_version 8.86.4 — all five factory counts unchanged
  since 2026-09-05 except CFE, matching the story's own prediction.
- `cat _bmad/_config/manifest.yaml` — confirmed core/bmm `6.12.0`, skf `version: main` /
  `source: custom`, `installShims: true`.
- `pixi run -e local-recipes detectors-ci` — 18 detectors: 17 pass, 1 pre-existing unrelated
  `dream-chain` finding (`bmad-cursor-interactive-routing` has no Spec) — matches this story's
  stated acceptance tolerance exactly.
- `pixi run -e local-recipes bmad-drift-check` — exit 0; only informational `pin-behind` /
  `count-stale` findings (all "ok"), no HARD or DRIFT findings.
- `python -m pyforge.doctor.sources spec-surface` — clean, no drift; no memlog reconcile or
  baseline re-stamp was needed.
- `grep -n "llms.txt\|llms-full.txt" CLAUDE.md AGENTS.md architecture-bmad-infra.md
  development-guide.md` — only the sanctioned local-snapshot-path mentions remain, no dead
  upstream URL.
- `grep -rn "bmad-checkpoint-preview\|bmad-walkthrough" CLAUDE.md AGENTS.md
  development-guide.md` — confirms Story 30.1's fix already landed; no stale reference outside
  the intentional deprecated-shim table in `architecture-bmad-infra.md`.

**Residual risks / left incomplete:** three `deferred` items recorded in frontmatter — the
"Installed Skills" section's skill-count facts (now confirmed to also leak into the "At a
Glance" table and two other spots, widened in the review pass); the sprint-status-ledger sync
for Stories 30.3/30.4 (deferred to step 11); and a pre-existing `pyforge.doctor` detector-
granularity gap (pin-behind never fires at patch-version resolution). No HARD findings; no
regression introduced; `bmad-drift-check` and `detectors-ci` both stay green (modulo the
pre-existing `dream-chain` finding).

**Review pass (2026-09-06):** found and fixed 2 medium + 1 low patch-worthy issues: the
"known-stale" disclosure's incomplete scope (widened to 4 locations + the live counts),
`bmad-checkpoint-preview` retired-vs-installed wording ambiguity, and two legacy `docs/specs/`
files still citing the dead upstream URL as "(live)". 3 findings rejected as false (matches
established house style / not a diff-level finding / no verification gap), 1 rejected as low
value (tense cosmetics), 3 deferred (see frontmatter). Follow-up review recommendation:
`false` — 1 medium-verdict patch, below the "two or more medium" threshold.
